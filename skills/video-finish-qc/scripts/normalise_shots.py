#!/usr/bin/env python3
"""normalise_shots.py — the per-shot NORMALISE that runs BEFORE the look, the flats the hero pass grades, and the read-back of
every hero against its flat. A look cube or a `.drx` is the GRADE step and assumes normalised input: on flat sources (overcast
light, full-range phone footage, a re-encode) the look alone reads pale beside a hand-normalised chain (an auction spot,
2026-09-16; video-finish-qc § 2). Per shot, in 16-bit RGB: the black and white points from the 0.5/99.5 luma percentiles
mapped to 0.02/0.88 (headroom for the look's own gain — mapping to 0/1 clipped 7-30 % of the brightest shots under ads-clean),
then a saturation factor that lands the shot's chroma on a target measured on footage the operator approved.

  normalise_shots.py measure --root <project> --shots <shots.json> (--target-chroma 0.030 | --target-ref <video> --target-at 3.2,9.8,…)
                             [--t-scale 0.91] [--min-short 1080]
  normalise_shots.py flatten --root <project> --shots <shots.json> --out-dir edit/flat [--only id,…]
  normalise_shots.py chain   --shots <shots.json> --id <id>          # the -vf chain, for a builder that grades with a cube instead
  normalise_shots.py verify  --root <project> --shots <shots.json> --flat-dir edit/flat --hero-dir edit/hero --look ads-clean
  normalise_shots.py --selftest

shots.json — one window per shot, frames of the SOURCE, handles included: [{"id": "s03", "src": "assets/C5325.mp4", "f0": 150,
"n": 99}, …]. `measure` adds W, H (the square-pixel display shape, scaled UP to --min-short on its short side, never down: an
anamorphic 9:16 clip stored 1920x1080 at SAR 81:256 becomes 1080x1920; a 4K source keeps its pixels for the crops downstream),
lo, hi, sat, and writes a .bak first. A resample is lanczos — nothing is redrawn; a source that needs detail REBUILT is the
upscale arm's (video-finish § 1), before this step.
--t-scale: the chroma target is t-scale x the reference's median. 0.91 for the Dehancer `ads-clean.drx` hero (250D/2383, TI 35
lands ~27 % less saturated than the cube's estimate: heroes at 0.75 read 0.0249 against a 0.0302 target, at 0.91 the client
shots' median read 0.0301); 0.75 when the grade is the cube alone.
flatten writes ProRes 422 HQ 10-bit, limited range, BT.709 tags, STARTING AT PTS 0: a flat that started at 0.041 s made Resolve
render one extra leading frame, and every hero cut from it sat one frame late.
verify, per hero: 10-bit, the flat's raster, the frame count, the flat's start at 0, the look applied (mean |dY| > 1/255 at
three points), NO geometric change (phase correlation of the luma = (0, 0) — a crop, scale, weave or warp moves it), and the
temporal alignment (the hero's middle frame matches the flat's frame m, not m +- 1, by gradient NCC). Exit 1 on any CHECK.
Cutting a hero into a plan: the target frame is the one NEAREST the plan's in-time, f_in = round(in x fps) (never ceil: that
leaves the picture up to a frame ahead of its synced sound), and the seek is that frame's OWN start, floored at the decimals
the plan keeps: in = floor((f_in - f0) / fps). A seek between frames followed by a builder's fps filter doubles the first
frame whenever the next frame starts more than half a frame after the seek point — the filter rounds it into output slot 1
and the muxer copies it into slot 0. Measured on one spot: in-points at x.2 and x.4 of a frame doubled 4 of 22 first frames
in the APPROVED version itself, and a half-frame seek into the heroes, quantised by their 1/12288 s timebase to an exact
0.5-frame tie that rounded up, doubled 14 of 22 — while every per-hero check passed. `setpts=PTS-STARTPTS` before the fps
filter closes it in a builder; qc_deliverable.py --prev <the pre-finish version> --prev-expect finish is the row that sees it.
"""
import argparse, json, math, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import numpy as np

KR, KG, KB = 0.2126, 0.7152, 0.0722
B_OUT, W_OUT, SAT_RANGE, MAX_STRETCH = 0.02, 0.88, (0.70, 1.80), 1.8


def run(cmd, binary=False):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=not binary)
    if r.returncode: sys.exit(f"FAILED {' '.join(map(str, cmd))[:300]}\n{(r.stderr if not binary else r.stderr.decode(errors='replace'))[-1500:]}")
    return r.stdout


def probe(p):
    s = json.loads(run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,sample_aspect_ratio,'
                        'pix_fmt,nb_frames,r_frame_rate,color_space,color_range:format=start_time', '-of', 'json', p]))
    st = s['streams'][0]; st['start_time'] = float(s['format'].get('start_time') or 0.0)
    n, d = (st.get('r_frame_rate') or '24/1').split('/'); st['fps'] = float(n) / float(d or 1); return st


def display(st, min_short):   # the square-pixel display shape, scaled up (never down) so its short side is >= min_short
    sar = (st.get('sample_aspect_ratio') or '1:1').replace('N/A', '1:1')
    if not sar[:1].isdigit() or sar.startswith('0'): sar = '1:1'
    a, b = (sar.replace('/', ':') + ':1').split(':')[:2]; w, h = st['width'] * int(a) / int(b), st['height']
    k = max(1.0, min_short / min(w, h)); return 2 * round(w * k / 2), 2 * round(h * k / 2)


def in_matrix(st):   # an untagged source: BT.709 at HD and above, BT.601 below — swscale's own default is BT.601 at every size
    cs = st.get('color_space') or ''
    return cs if cs in ('bt709', 'bt470bg', 'smpte170m', 'bt2020nc') else ('bt709' if st['height'] >= 720 or st['width'] >= 1280 else 'bt601')


def scale_in(w, st):
    return f"scale={w['W']}:{w['H']}:flags=lanczos+accurate_rnd+full_chroma_int:in_color_matrix={in_matrix(st)},setsar=1"


def frames(src, st, t0, n, W, H, count=5, pre=''):   # RGB 0..1 of `count` frames spread over [t0, t0 + n/fps)
    out = []
    for k in range(count):
        t = t0 + (k + 0.5) * (n / st['fps']) / count
        b = run(['ffmpeg', '-v', 'error', '-ss', f'{t:.4f}', '-i', src, '-frames:v', '1', '-vf',
                 (pre or f"scale={W}:{H}:flags=lanczos:in_color_matrix={in_matrix(st)}") + ',format=rgb48le', '-f', 'rawvideo', '-'], binary=True)
        out.append(np.frombuffer(b, np.uint16).reshape(H, W, 3).astype(np.float32) / 65535)
    return out


def luma(f): return KR * f[..., 0] + KG * f[..., 1] + KB * f[..., 2]


def chroma(f):   # mean BT.709 chroma magnitude (Cb, Cr in -0.5..0.5)
    y = luma(f); return float(np.mean(np.hypot((f[..., 2] - y) / 1.8556, (f[..., 0] - y) / 1.5748)))


def levels(y):   # the 0.5/99.5 luma percentiles, guarded: never a creative contrast push
    lo, hi = (float(v) for v in np.percentile(y, [0.5, 99.5]))
    lo = min(lo, 0.30); hi = max(hi, 0.70)
    if 1 / (hi - lo) > MAX_STRETCH: hi = lo + 1 / MAX_STRETCH
    return lo, hi


def chain(w):   # the normalise as an ffmpeg chain on 16-bit planar RGB: levels, then saturation about BT.709 luma
    lo, hi, s = w['lo'], w['hi'], w['sat']; a = 1 - s
    mix = (f"colorchannelmixer=rr={KR*a+s:.5f}:rg={KG*a:.5f}:rb={KB*a:.5f}:gr={KR*a:.5f}:gg={KG*a+s:.5f}:gb={KB*a:.5f}"
           f":br={KR*a:.5f}:bg={KG*a:.5f}:bb={KB*a+s:.5f}")
    return (f"format=gbrp16le,colorlevels=rimin={lo}:gimin={lo}:bimin={lo}:rimax={hi}:gimax={hi}:bimax={hi}"
            f":romin={B_OUT}:gomin={B_OUT}:bomin={B_OUT}:romax={W_OUT}:gomax={W_OUT}:bomax={W_OUT},{mix}")


def target(a, root):
    if a.target_chroma: return a.target_chroma
    if not (a.target_ref and a.target_at): sys.exit('a chroma target: --target-chroma, or --target-ref <video> --target-at <s,s,…>')
    ref = root / a.target_ref; st = probe(ref); W, H = display(st, a.min_short)
    vals = [chroma(frames(ref, st, float(t), 1, W, H, 1)[0]) for t in a.target_at.split(',')]
    print(f"target: median chroma {np.median(vals):.4f} of {len(vals)} frames of {a.target_ref}"); return float(np.median(vals))


def measure(a, root, shots):
    T = target(a, root) * a.t_scale; print(f"chroma target {T:.4f} (t-scale {a.t_scale})")
    for w in shots:
        src = root / w['src']; st = probe(src); w['W'], w['H'] = display(st, a.min_short)
        fr = frames(src, st, w['f0'] / st['fps'], w['n'], w['W'], w['H'])
        lo, hi = levels(np.concatenate([luma(f).ravel() for f in fr]))
        lev = [B_OUT + (W_OUT - B_OUT) * np.clip((f - lo) / (hi - lo), 0, 1) for f in fr]
        c0 = float(np.mean([chroma(f) for f in lev])); sat = float(np.clip(T / max(c0, 1e-4), *SAT_RANGE))
        w.update({'lo': round(lo, 4), 'hi': round(hi, 4), 'chroma_levelled': round(c0, 4), 'sat': round(sat, 3), 'target': round(T, 4)})
        print(f"{w['id']:6s} {w['W']}x{w['H']}  lo {lo:.3f} hi {hi:.3f}  chroma levelled {c0:.4f} -> sat x{sat:.2f}"
              + ('  (clamped)' if sat in SAT_RANGE else ''))
    return shots


def flatten(a, root, shots):
    out_dir = root / a.out_dir; out_dir.mkdir(parents=True, exist_ok=True); only = set(filter(None, (a.only or '').split(',')))
    for w in shots:
        if only and w['id'] not in only: continue
        src = root / w['src']; st = probe(src); out = out_dir / f"{w['id']}.mov"
        if out.exists(): sys.exit(f"{out} exists: a new flat is a new --out-dir (the heroes cut from the old one stay valid)")
        run(['ffmpeg', '-v', 'error', '-ss', f"{max(0.0, (w['f0'] - 0.5) / st['fps']):.5f}", '-i', src, '-frames:v', w['n'], '-vf',
             f"{scale_in(w, st)},{chain(w)},scale=out_color_matrix=bt709:out_range=tv,format=yuv422p10le,setpts=PTS-STARTPTS",
             '-an', '-c:v', 'prores_ks', '-profile:v', '3', '-vendor', 'apl0', '-color_range', 'tv', '-colorspace', 'bt709',
             '-color_primaries', 'bt709', '-color_trc', 'bt709', '-r', f"{st['fps']:g}", out])
        o = probe(out); ok = o['start_time'] == 0.0 and int(o.get('nb_frames') or 0) == w['n'] and o['pix_fmt'] == 'yuv422p10le'
        print(f"FLAT {w['id']:6s} {o['width']}x{o['height']} {o['pix_fmt']} {o.get('nb_frames')}/{w['n']} start {o['start_time']}  {'OK' if ok else 'CHECK'}", flush=True)
        if not ok: sys.exit('a flat must be 10-bit, frame-exact and start at pts 0 (Resolve renders an extra leading frame otherwise)')
    print('FLATTEN-END')


def idx(p, k, W, H):   # frame k by exact index, luma 0..1
    b = run(['ffmpeg', '-v', 'error', '-i', p, '-vf', f'select=eq(n\\,{k}),scale={W}:{H},format=gray16le', '-frames:v', '1', '-f', 'rawvideo', '-'], binary=True)
    return np.frombuffer(b, np.uint16).reshape(H, W).astype(np.float64) / 65535


def grad(g): gy, gx = np.gradient(g); return np.hypot(gx, gy)


def ncc(x, y): x = x - x.mean(); y = y - y.mean(); return float((x * y).sum() / (np.sqrt((x * x).sum() * (y * y).sum()) + 1e-12))


def phase_shift(x, y):   # a pure grade shifts nothing; a crop, scale, weave or warp does
    F = np.fft.fft2(x - x.mean()) * np.conj(np.fft.fft2(y - y.mean())); F /= np.abs(F) + 1e-9
    c = np.abs(np.fft.ifft2(F)); iy, ix = np.unravel_index(np.argmax(c), c.shape)
    return (int(iy if iy < c.shape[0] // 2 else iy - c.shape[0]), int(ix if ix < c.shape[1] // 2 else ix - c.shape[1]))


def verify_pair(flat, hero, n):
    sf, sh = probe(flat), probe(hero); W, H = sf['width'], sf['height']
    a, b = frames(flat, sf, 0, n, W, H, 3, 'null'), frames(hero, sh, 0, n, W, H, 3, f'scale={W}:{H}')
    dy = float(np.mean([np.mean(np.abs(luma(x) - luma(y))) for x, y in zip(a, b)]) * 255)
    shifts = [phase_shift(luma(x), luma(y)) for x, y in zip(a, b)]
    m = n // 2; hm = grad(idx(hero, m, W, H)); cc = [ncc(hm, grad(idx(flat, m + d, W, H))) if 0 <= m + d < n else -1.0 for d in (-1, 0, 1)]
    checks = {'10-bit': sh['pix_fmt'].endswith('10le'), 'raster': (sh['width'], sh['height']) == (W, H),
              'frames': int(sh.get('nb_frames') or 0) == n, 'flat starts 0': sf['start_time'] == 0.0, 'look applied': dy > 1.0,
              'no shift': all(s == (0, 0) for s in shifts), 'aligned': int(np.argmax(cc)) == 1}
    return checks, dy, shifts, cc


def verify(a, root, shots):
    bad = 0
    for w in shots:
        f, h = root / a.flat_dir / f"{w['id']}.mov", root / a.hero_dir / f"{w['id']}__{a.look}.mov"
        if not (f.exists() and h.exists()): print(f"{w['id']:6s} MISSING {'flat' if not f.exists() else 'hero'}"); bad += 1; continue
        checks, dy, shifts, cc = verify_pair(f, h, w['n']); ok = all(checks.values()); bad += not ok
        print(f"{w['id']:6s} mean|dY| {dy:5.2f}/255  shift {shifts}  align m-1/m/m+1 {cc[0]:.3f}/{cc[1]:.3f}/{cc[2]:.3f}  "
              + ('OK' if ok else 'CHECK: ' + ', '.join(k for k, v in checks.items() if not v)))
    print('VERIFY', 'PASS' if not bad else f'CHECK ({bad})'); return bad


def selftest():
    d = Path(tempfile.mkdtemp()); H, W, N = 320, 180, 24
    yy, xx = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
    base = np.stack([0.20 + 0.60 * xx, 0.20 + 0.60 * yy, 0.25 + 0.50 * xx * yy], -1)          # luma ~0.20-0.80: no guard binds
    vid = np.stack([np.roll(base, k * 3, axis=0) for k in range(N)])                           # a moving picture, 3 px a frame
    raw = d / 'src.rgb'; raw.write_bytes((vid * 65535).astype('<u2').tobytes())
    run(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-s', f'{W}x{H}', '-r', '24', '-i', raw, '-vf',
         'scale=out_color_matrix=bt709:out_range=tv,format=yuv422p10le', '-c:v', 'prores_ks', '-profile:v', '3', '-colorspace', 'bt709', d / 'src.mov'])
    st = probe(d / 'src.mov'); lo, hi = levels(np.concatenate([luma(f).ravel() for f in frames(d / 'src.mov', st, 0, N, W, H)]))
    for sat, sub in ((1.0, 'flat1'), (1.5, 'flat')):
        flatten(argparse.Namespace(out_dir=sub, only=''), d, [{'id': 't', 'src': 'src.mov', 'f0': 0, 'n': N, 'W': W, 'H': H, 'lo': lo, 'hi': hi, 'sat': sat}])
    fl = d / 'flat/t.mov'; sf = probe(fl); y = np.concatenate([luma(f).ravel() for f in frames(d / 'flat1/t.mov', sf, 0, N, W, H, 5, 'null')])
    p05, p995 = np.percentile(y, [0.5, 99.5])
    c1, c15 = (np.mean([chroma(f) for f in frames(d / f'{x}/t.mov', sf, 0, N, W, H, 5, 'null')]) for x in ('flat1', 'flat'))
    r1 = abs(p05 - B_OUT) < 0.02 and abs(p995 - W_OUT) < 0.02; print(f"selftest levels: p0.5 {p05:.3f} (want {B_OUT}) p99.5 {p995:.3f} (want {W_OUT})  {'OK' if r1 else 'FAIL'}")
    r2 = 1.40 <= c15 / c1 <= 1.60; print(f"selftest saturation x1.5: chroma {c1:.4f} -> {c15:.4f} (x{c15 / c1:.2f})  {'OK' if r2 else 'FAIL'}")
    common = ['-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le']
    run(['ffmpeg', '-v', 'error', '-i', fl, '-vf', 'eq=contrast=1.15:brightness=0.03', *common, d / 'good.mov'])
    run(['ffmpeg', '-v', 'error', '-i', fl, '-vf', f'eq=contrast=1.15,crop={W}:{H - 4}:0:4,pad={W}:{H}:0:0', *common, d / 'shifted.mov'])
    run(['ffmpeg', '-v', 'error', '-i', fl, '-vf', 'eq=contrast=1.15,setpts=PTS-STARTPTS,trim=start_frame=1,setpts=PTS-STARTPTS,tpad=stop=1:stop_mode=clone', *common, d / 'offset.mov'])
    run(['ffmpeg', '-v', 'error', '-i', fl, '-c', 'copy', d / 'same.mov'])
    res = {k: verify_pair(fl, d / f'{k}.mov', N)[0] for k in ('good', 'shifted', 'offset', 'same')}
    r3 = all(res['good'].values()); r4 = not res['shifted']['no shift']; r5 = not res['offset']['aligned']; r6 = not res['same']['look applied']
    print(f"selftest verify: graded {'OK' if r3 else 'FAIL'} · a 4 px shift caught {'OK' if r4 else 'FAIL'} · one frame off caught "
          f"{'OK' if r5 else 'FAIL'} · no look caught {'OK' if r6 else 'FAIL'}")
    good = r1 and r2 and r3 and r4 and r5 and r6; shutil.rmtree(d, ignore_errors=True); print('SELFTEST', 'PASS' if good else 'FAIL'); return 0 if good else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', nargs='?', choices=['measure', 'flatten', 'chain', 'verify'])
    ap.add_argument('--root', default='.'); ap.add_argument('--shots'); ap.add_argument('--id'); ap.add_argument('--only')
    ap.add_argument('--target-chroma', type=float); ap.add_argument('--target-ref'); ap.add_argument('--target-at')
    ap.add_argument('--t-scale', type=float, default=0.91); ap.add_argument('--min-short', type=int, default=1080)
    ap.add_argument('--out-dir', default='edit/flat'); ap.add_argument('--flat-dir', default='edit/flat'); ap.add_argument('--hero-dir', default='edit/hero')
    ap.add_argument('--look', default='ads-clean'); ap.add_argument('--selftest', action='store_true'); a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    if not (a.cmd and a.shots): ap.error('a command and --shots')
    root = Path(a.root).resolve(); sp = Path(a.shots) if Path(a.shots).is_absolute() else root / a.shots; shots = json.loads(sp.read_text())
    if a.cmd == 'measure':
        measure(a, root, shots); shutil.copy2(sp, sp.with_name(sp.name + f'.bak-{time.strftime("%Y%m%d-%H%M%S")}-measure'))
        sp.write_text(json.dumps(shots, indent=1)); print('MEASURE-END', sp)
    elif a.cmd == 'flatten': flatten(a, root, shots)
    elif a.cmd == 'chain':
        w = next(x for x in shots if x['id'] == a.id); print(f"scale={w['W']}:{w['H']}:flags=lanczos,setsar=1,{chain(w)}")
    else: sys.exit(1 if verify(a, root, shots) else 0)


if __name__ == '__main__':
    main()
