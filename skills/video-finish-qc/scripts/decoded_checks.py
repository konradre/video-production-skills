#!/usr/bin/env python3
"""decoded_checks.py — the delivery QC rows that read the DECODED picture and sound, not the tags or the plan. Imported by
qc_deliverable.py (one row each); runnable alone for one check. Sources: product-film-skill `verify.py` (frame 0 against the
background within 2 code values; the loop seam), brag (the poster baked into frame 0 — X, Slack and Discord take the
thumbnail from frame 0), video-shotcraft's final review (every SFX audible in the RENDERED file; strong-beat cuts ≤ 3 frames).

  frame0_bg   frame 0's median RGB, DECODED as a player would (the range tag honoured), within 2 code values of the EDL's
              qc.frame0_bg — a limited-range master read as full range lifts black to 16 and fails here while every tag
              row passes
  range       INFO: the Y code values over sampled frames against the colour-range tag (full-range content tagged tv
              clips; limited content tagged pc lifts the blacks)
  loop_seam   with qc.loop: the last frame against the first, beside the clip's median frame-to-frame step
  poster      frame 0 is the platform thumbnail: not near-black — or, with poster_at, equal to that frame (the finisher bakes
              it); qc.poster: "none" declares a black first frame on purpose
  poster_flash with poster_at: the baked frame 0 against frame 1, beside the clip's median step — a poster unlike the
              opening flashes for one frame at autoplay (showtime's bake guard); a WARN line, never a FAIL
  sfx         every audio.sfx cue found in the delivered mix at its time: normalised cross-correlation of the cue (at its
              vol) with the mix over ±20 ms, and its level against the mix; a sample over 5 s with no `dur` is flagged
              (bound it to its action)
  beat_cuts   every event declaring on_beat: its cut within 3 frames of the nearest beat of qc.beat_data
              (spot-audio-assembly/scripts/beat_grid.py JSON — the checked grid, or the beat map)

  decoded_checks.py --selftest
"""
import glob, json, os, subprocess, sys, tempfile
import numpy as np


def _run(c): return subprocess.run(c, capture_output=True)


def fps_of(p):
    r = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', p]).stdout.decode().strip()
    try: n, d = r.split('/'); return float(n) / float(d)
    except (ValueError, ZeroDivisionError): return 24.0


def frame_gray(p, t=None, n=None, s=64):
    """one frame as an s×s luma array: the frame ON SCREEN at time t, or frame index n, decoded with the tags honoured.
    -ss t returns the first frame STARTING at or after t — the next frame for a t inside one — so t goes to its frame's start"""
    if t is not None: f = fps_of(p); t = max(0.0, np.floor(t * f + 1e-6) / f - 0.25 / f)
    pre = ['-ss', f'{t:.4f}'] if t is not None else []
    vf = (f"select='eq(n\\,{n})'," if n is not None else '') + f'scale={s}:{s},format=gray'
    raw = _run(['ffmpeg', '-v', 'error', *pre, '-i', p, '-vf', vf, '-frames:v', '1', '-f', 'rawvideo', '-']).stdout
    return np.frombuffer(raw[:s * s], np.uint8).reshape(s, s).astype(float) if len(raw) >= s * s else None


def nframes(p):
    r = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', p]).stdout
    try: return int(r.decode().strip())
    except ValueError: return 0


def frame0_bg(p, want_hex, tol=2):
    raw = _run(['ffmpeg', '-v', 'error', '-i', p, '-frames:v', '1', '-vf', 'scale=64:64,format=rgb24', '-f', 'rawvideo', '-']).stdout
    if len(raw) < 64 * 64 * 3: return False, 'could not decode frame 0'
    got = np.median(np.frombuffer(raw[:64 * 64 * 3], np.uint8).reshape(-1, 3), axis=0).astype(int)
    h = want_hex.lstrip('#'); want = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)])
    d = int(np.abs(got - want).max())
    return d <= tol, f"median RGB {tuple(got)} vs qc.frame0_bg {tuple(want)}: {d} code value(s) off (tolerance {tol})" + (
        '' if d <= tol else ' — a limited-range master read as full range lifts black to 16; check the range tag against the content')


def range_read(p, tag, k=8):
    """Y code values straight from the decoder (no conversion) over k frames spread through the file"""
    info = _run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,pix_fmt', '-of', 'json', p]).stdout
    st = json.loads(info or b'{}').get('streams', [{}])[0]; w, h = st.get('width'), st.get('height')
    if not w or st.get('pix_fmt') not in ('yuv420p', 'yuvj420p'): return True, f"not read (pix_fmt {st.get('pix_fmt')})"
    n = max(1, nframes(p)); step = max(1, n // k)
    raw = _run(['ffmpeg', '-v', 'error', '-i', p, '-vf', f"select='not(mod(n\\,{step}))'", '-vsync', '0', '-frames:v', str(k), '-f', 'rawvideo', '-pix_fmt', st['pix_fmt'], '-']).stdout
    fs = w * h * 3 // 2; ys = [np.frombuffer(raw[i:i + w * h], np.uint8) for i in range(0, len(raw) - fs + 1, fs)]
    if not ys: return True, 'no frames decoded'
    y = np.concatenate(ys); lo, hi = np.percentile(y, [0.1, 99.9]); out = float(((y < 16) | (y > 235)).mean())
    if tag == 'tv' and out > 0.01: return False, f"{out * 100:.1f} % of Y outside 16–235 under a tv (limited) tag: full-range content — it will clip"
    if tag == 'pc' and lo >= 14 and hi <= 237 and np.percentile(y, 2) < 40:
        return False, f"Y spans {lo:.0f}–{hi:.0f} under a pc (full) tag: limited-range content — players will show its black as grey"
    return True, f"Y 0.1–99.9 % = {lo:.0f}–{hi:.0f}, {out * 100:.2f} % outside 16–235, tag {tag or 'untagged'}"


def loop_seam(p):
    n = nframes(p)
    if n < 4: return False, 'too few frames to read a seam'
    first, last = frame_gray(p, n=0), frame_gray(p, n=n - 1)
    steps = [np.abs(frame_gray(p, n=i + 1) - frame_gray(p, n=i)).mean() for i in np.linspace(0, n - 2, 6).astype(int)]
    seam = float(np.abs(last - first).mean()); med = float(np.median(steps)); lim = max(4.0, 3 * med)
    return seam <= lim, f"last→first frame mean |dY| {seam:.1f} vs the clip's median step {med:.1f} (limit {lim:.1f})"


def poster(p, poster_at=None, declared=None, black=16.0):
    if declared == 'none': return True, 'qc.poster: none — a black first frame declared on purpose'
    f0 = frame_gray(p, n=0)
    if f0 is None: return False, 'could not decode frame 0'
    if poster_at is not None:   # NCC, not a difference: the baked frame is the clean master's, a caption may sit on the frame at poster_at
        pa = frame_gray(p, t=float(poster_at))
        if pa is None: return False, f'could not decode the frame at {poster_at} s'
        if f0.std() < 2 or pa.std() < 2:   # a flat frame has no correlation to measure: compare the levels
            d = abs(float(f0.mean() - pa.mean())); return d <= 6, f"frame 0 vs the poster frame at {poster_at} s (flat): mean luma {f0.mean():.0f} vs {pa.mean():.0f} (≤ 6 apart: baked)"
        A, B = f0 - f0.mean(), pa - pa.mean(); n = float((A * B).sum() / (np.sqrt((A * A).sum() * (B * B).sum()) + 1e-9))
        return n >= 0.85, f"frame 0 vs the poster frame at {poster_at} s: NCC {n:.3f} (≥ 0.85: baked)"
    m = float(f0.mean())
    return m >= black, f"frame 0 mean luma {m:.1f}/255" + ('' if m >= black else
        ' — the platform thumbnail is black: set poster_at in the EDL (the finisher bakes that frame into frame 0), or declare qc.poster: "none"')


def poster_flash(p):
    """the baked poster against the opening: frame 0 vs frame 1 beside the clip's median frame-to-frame step (loop_seam's
    statistic). A poster unlike the opening shows for one frame at autoplay before the film — a WARN, never a FAIL"""
    n = nframes(p)
    if n < 4: return True, 'too few frames to read'
    f0, f1 = frame_gray(p, n=0), frame_gray(p, n=1)
    if f0 is None or f1 is None: return True, 'could not decode frames 0 and 1'
    steps = [np.abs(frame_gray(p, n=i + 1) - frame_gray(p, n=i)).mean() for i in np.linspace(1, n - 2, 6).astype(int)]
    jump = float(np.abs(f1 - f0).mean()); med = float(np.median(steps)); lim = max(4.0, 3 * med)
    return jump <= lim, f"frame 0 (the poster) → frame 1 (the opening): mean |dY| {jump:.1f} vs the clip's median step {med:.1f} (limit {lim:.1f})" + (
        '' if jump <= lim else ' — the poster flashes for one frame at autoplay; pick the poster from the opening, or compose the opening as the hook')


def _pcm(p, ss=0.0, d=None):
    c = ['ffmpeg', '-v', 'error', '-ss', f'{ss:.4f}', '-i', p] + (['-t', f'{d:.4f}'] if d else []) + [
        '-af', 'aresample=48000:async=1:first_pts=0', '-ac', '1', '-ar', '48000', '-f', 'f32le', '-']
    return np.frombuffer(_run(c).stdout, np.float32).astype(float)


def sfx(p, root, sfx_map):
    """[(name, ok, detail)] — each cue located in the delivered mix at its time"""
    rows = []
    for name, s in (sfx_map or {}).items():
        if not isinstance(s, dict) or 'at' not in s: continue
        f = next((g for pat in str(s.get('file', '')).split('|') for g in sorted(glob.glob(os.path.join(root, pat)))), None)
        if not f: rows.append((name, False, f"no file for {s.get('file')}")); continue
        cue = _pcm(f, float(s.get('src_in') or 0.0), s.get('dur')) * float(s.get('vol', 1)); fd = len(cue) / 48000
        long_note = ' · a sample over 5 s with no dur — bound it to its action' if fd > 5 and not s.get('dur') else ''
        L = min(len(cue), int(0.6 * 48000)); cue = cue[:L]
        if L < 480 or not np.abs(cue).max(): rows.append((name, False, 'the cue is silent')); continue
        mix = _pcm(p, max(0.0, float(s['at']) - 0.02), L / 48000 + 0.04)
        if len(mix) < L: rows.append((name, False, f"the mix ends before {s['at']} s")); continue
        best = 0.0
        for k in range(0, len(mix) - L + 1, 24):   # ±20 ms in 0.5 ms steps
            seg = mix[k:k + L]; den = np.linalg.norm(seg) * np.linalg.norm(cue)
            if den: best = max(best, float(np.dot(seg, cue) / den))
        rel = 20 * np.log10((np.sqrt((cue ** 2).mean()) + 1e-12) / (np.sqrt((mix[:L] ** 2).mean()) + 1e-12))
        ok = best >= 0.2   # presence IS the correlation (a cue 14 dB under the mix still reads ~0.2); its level is context only
        rows.append((name, ok, f"at {s['at']} s: correlation {best:.2f} with the mix, its level {rel:+.1f} dB against the mix" + long_note
                     + ('' if ok else ' — buried or missing in the delivered file')))
    return rows


def beat_cuts(events, beat_json, fps, root='.', tol_frames=3):
    B = json.load(open(beat_json if os.path.isabs(beat_json) else os.path.join(root, beat_json)))
    beats = np.array(B['beats'], float); off = []
    decl = [e for e in events if e.get('on_beat')]
    if not decl: return True, 'no event declares on_beat'
    for e in decl:
        t = float(e['tl'][0]); d = float(np.abs(beats - t).min()) * fps
        if d > tol_frames: off.append(f"{e['id']} cut at {t:.3f} s is {d:.1f} frames off the nearest beat")
    return not off, f"{len(decl) - len(off)}/{len(decl)} declared beat cuts within {tol_frames} frames of the {B.get('verdict', '?')} ({B.get('bpm', '?')} bpm)" + (
        '' if not off else ': ' + '; '.join(off))


def selftest():
    def mk(p, vf, extra=(), d=2):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=black:s=64x64:r=24:d={d}', '-vf', vf, *extra, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', p], check=True)
    chk = []
    with tempfile.TemporaryDirectory() as r:
        a = os.path.join(r, 'tv.mp4'); b = os.path.join(r, 'lifted.mp4')
        mk(a, 'format=yuv420p', ['-color_range', 'tv']); mk(b, 'scale=in_range=pc:out_range=tv,format=yuv420p', ['-color_range', 'pc'])
        chk.append(('frame 0 black on a tv-tagged file reads 0,0,0', frame0_bg(a, '#000000')[0]))
        chk.append(('limited content under a pc tag lifts black → FAIL', not frame0_bg(b, '#000000')[0]))
        lp = os.path.join(r, 'loop.mp4'); sp = os.path.join(r, 'seam.mp4')
        mk(lp, "geq=lum='128+60*sin(2*PI*N/48)':cb=128:cr=128")          # one full cycle in 48 frames: frame 47 ≈ frame 0
        mk(sp, "geq=lum='40+4*N':cb=128:cr=128")                          # a ramp: the last frame is far from the first
        chk.append(('a clip that closes its cycle passes the seam', loop_seam(lp)[0]))
        chk.append(('a ramp fails the seam', not loop_seam(sp)[0]))
        chk.append(('a black frame 0 fails the poster row', not poster(a)[0]))
        chk.append(('declared qc.poster none passes', poster(a, declared='none')[0]))
        pb = os.path.join(r, 'baked.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', "color=c=black:s=64x64:r=24:d=2,drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='eq(n\\,0)+eq(n\\,24)'",
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', pb], check=True)
        chk.append(('frame 0 equal to the poster frame at 1.0 s passes', poster(pb, poster_at=1.0)[0]))
        chk.append(('a poster unlike the opening is flagged as a flash', not poster_flash(pb)[0]))
        chk.append(('frame 0 that flows into frame 1 reads no flash', poster_flash(lp)[0]))
        os.makedirs(os.path.join(r, 'sfx'))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', "aevalsrc='0.8*sin(2*PI*1500*t)*exp(-12*t)':s=48000:d=0.4", os.path.join(r, 'sfx', 'hit.wav')], check=True)
        mixp = os.path.join(r, 'mix.mp4'); quiet = os.path.join(r, 'quiet.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anoisesrc=a=0.05:d=3:r=48000', '-i', os.path.join(r, 'sfx', 'hit.wav'), '-filter_complex',
                        '[1:a]adelay=1200|1200[h];[0:a][h]amix=inputs=2:normalize=0', '-c:a', 'aac', '-b:a', '192k', mixp], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anoisesrc=a=0.05:d=3:r=48000', '-c:a', 'aac', '-b:a', '192k', quiet], check=True)
        cues = {'hit': {'file': 'sfx/hit.wav', 'at': 1.2, 'vol': 1}}
        chk.append(('a cue in the mix at its time is found', all(ok for _, ok, _ in sfx(mixp, r, cues))))
        chk.append(('a cue missing from the mix is flagged', not any(ok for _, ok, _ in sfx(quiet, r, cues))))
        json.dump({'verdict': 'grid', 'bpm': 120, 'beats': [i * 0.5 for i in range(20)]}, open(os.path.join(r, 'beats.json'), 'w'))
        ev = [{'id': 'A', 'tl': [0.0, 1.0]}, {'id': 'B', 'tl': [1.0, 2.04], 'on_beat': True}, {'id': 'C', 'tl': [2.04, 3.0]}]
        chk.append(('a declared cut on the beat passes', beat_cuts(ev, 'beats.json', 24, r)[0]))
        ev[2]['on_beat'] = True; ev[2]['tl'] = [2.2, 3.0]
        chk.append(('a declared cut 4.8 frames off the beat fails', not beat_cuts(ev, 'beats.json', 24, r)[0]))
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return 0 if ok else 1


if __name__ == '__main__':
    if '--selftest' in sys.argv: sys.exit(selftest())
    print(__doc__)
