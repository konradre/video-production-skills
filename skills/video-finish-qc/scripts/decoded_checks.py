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

The motion rows read every frame on an area proxy (long side 320 px), whole frame — WARN lines, never a FAIL:
  pops        a one-frame flash: frame n unlike both neighbours while they match — min(d[n-1], d[n]) > 2.0 and
              mean|f[n+1] - f[n-1]| < 0.35 × that min (claude-motion-design's two-sided test; a cut cannot fire it).
              Measured floor: a step in the frame mean of ~2 levels — ~1.5 % of the frame at a 135-level flash in a
              quiet scene, worse with motion elsewhere; 0 fires on 39 designed renders and 7 shipped spots
  steps       a one-frame step: the change into frame n over 3 × both neighbouring changes and over 2.0 — what two
              tweens fighting over one property leave (HYPERFRAMES-CONTRACT § Silent traps). Every frame the EDL says
              changes on purpose is set aside on the EXACT frame (declared_edges: joins, accepted_cuts, captions on and
              off, qc.accepted_flashes); on three shipped spots that left only a worded card's own word lines, which
              the card's event declares as accepted_cuts
  flash rate  WCAG 2.3.1 general flashes (showtime's flash_risk): a transition is a ≥ 0.1 change of relative
              luminance over ≥ 25 % of the frame with its darker side under 0.8; a flash is a pair of opposite
              transitions; more than 3 in any one second WARNs
  floor       the frozen-frame row's blind spot (freeze_floor): freezedetect's statistic at sampled still frame pairs;
              over its −60 dB tolerance (0.26 code values) a frozen shot under that texture does not register

  decoded_checks.py motion <render.mp4 | frames-dir> [--fps 24] [--accepted s,s,…] [--tiles]
      a designed render's motion read: pops, steps and the flash rate; --accepted = the element's own hard changes in its
      own seconds (a worded card's word lines — the numbers its EDL event declares as accepted_cuts); --tiles adds the
      per-tile step read (4×4), a LEAD: it reaches a small element's snap, and designed slams, wipes, bar slashes and
      shakes fire it too (on one kit every tile hit was designed; on one shipped card it caught one of three real snaps,
      5 % over its threshold)
  decoded_checks.py --selftest
"""
import argparse, glob, json, math, os, subprocess, sys, tempfile
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


# ---- the motion rows: every frame, on an area proxy ----
PROXY_LONG = 320                           # long side of the proxy in px, the aspect kept, never upscaled
STEP_T, POP_RATIO = 2.0, 0.35
FLASH_AREA, FLASH_DELTA, FLASH_DARK = 0.25, 0.1, 0.8
FREEZE_TOL = 10 ** (-60 / 20) * 256        # freezedetect n=-60dB on 8 bits, in code values: 0.256
STILL_SHARE = 0.0012                       # a frame pair under this share of luma changed by > 25 levels moved nothing


def _proxy(W, H):
    s = min(1.0, PROXY_LONG / max(W, H)); return max(2, round(W * s)), max(2, round(H * s))


def motion_frames(p, fps=None):
    """every frame as grey on the area proxy: a video decoded with its tags honoured, or a folder of PNG layers
    composited over black → (frames [n, h, w] float32, fps, (W, H))"""
    if os.path.isdir(p):
        from PIL import Image
        out = []; W = H = 0
        for f in sorted(glob.glob(os.path.join(p, '*.png'))):
            im = Image.open(f).convert('RGBA'); W, H = im.size; a = np.asarray(im).astype(np.float32)
            g = (a[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)) * a[..., 3] / 255.0
            out.append(np.asarray(Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).resize(_proxy(W, H), Image.BOX), np.uint8))
        return (np.stack(out) if out else np.zeros((0, 2, 2), np.uint8)), float(fps or 24.0), (W, H)
    st = json.loads(_run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', p]).stdout or b'{}').get('streams', [{}])[0]
    W, H = int(st.get('width') or 0), int(st.get('height') or 0)
    if not W: return np.zeros((0, 2, 2), np.uint8), float(fps or 24.0), (0, 0)
    pw, ph = _proxy(W, H)
    raw = _run(['ffmpeg', '-v', 'error', '-i', p, '-vf', f'scale={pw}:{ph}:flags=area,format=gray', '-f', 'rawvideo', '-']).stdout
    n = len(raw) // (pw * ph)
    return np.frombuffer(raw[:n * pw * ph], np.uint8).reshape(n, ph, pw), float(fps or fps_of(p)), (W, H)   # uint8: 58 KB a frame


def _d(a, b): return float(np.abs(a.astype(np.float32) - b).mean())


def frame_changes(g):   # d[i] = mean |g[i+1] - g[i]|: the change INTO frame i + 1, one pair at a time (memory stays flat)
    return np.array([_d(g[i + 1], g[i]) for i in range(len(g) - 1)], np.float32)


def pops(g, skip=(), T=STEP_T, ratio=POP_RATIO):
    """[(frame, change, skip-change)] — one-frame flashes; a frame in `skip` is a declared flash"""
    d = frame_changes(g); out = []
    for n in range(1, len(g) - 1):
        m = min(d[n - 1], d[n])
        if m > T and n not in skip:
            sk = _d(g[n + 1], g[n - 1])
            if sk < ratio * m: out.append((n, round(float(m), 2), round(sk, 2)))
    return out


def steps(g, skip=(), T=STEP_T, k=3.0, floor=0.3):
    """[(frame, change, larger neighbouring change)] — one-frame steps; a frame in `skip` changes on purpose"""
    d = frame_changes(g); out = []
    for i in range(1, len(d) - 1):
        if d[i] > k * max(d[i - 1], d[i + 1], floor) and d[i] > T and i + 1 not in skip:
            out.append((i + 1, round(float(d[i]), 2), round(float(max(d[i - 1], d[i + 1])), 2)))
    return out


def tile_steps(g, skip=(), grid=4):
    """[(frame, row, col, change, neighbour)] — the step read per tile of a grid × grid split: a lead, never a verdict"""
    n, h, w = g.shape; hs, ws = h // grid, w // grid; out = []
    for r in range(grid):
        for c in range(grid):
            out += [(f, r, c, dv, nb) for f, dv, nb in steps(g[:, r * hs:(r + 1) * hs, c * ws:(c + 1) * ws], skip)]
    return sorted(out)


def flash_rate(g, fps):
    """(the most general flashes in any one second, where it starts in s, transitions) — WCAG 2.3.1 on luma as an
    approximate relative luminance ((v/255)^2.2)"""
    dirs = []; prev = None
    for i in range(len(g)):
        cur = (g[i].astype(np.float32) / 255.0) ** 2.2
        if prev is not None:
            dl = cur - prev; dark = np.minimum(cur, prev) < FLASH_DARK
            if float(((dl >= FLASH_DELTA) & dark).mean()) >= FLASH_AREA: dirs.append((i, 1))
            elif float(((dl <= -FLASH_DELTA) & dark).mean()) >= FLASH_AREA: dirs.append((i, -1))
        prev = cur
    win = max(1, int(round(fps))); best, at = 0, None
    for k, (i0, _) in enumerate(dirs):
        seq = []
        for i, dd in dirs[k:]:
            if i - i0 >= win: break
            if not seq or seq[-1] != dd: seq.append(dd)
        if len(seq) // 2 > best: best, at = len(seq) // 2, i0
    return best, (round(at / fps, 2) if at is not None else None), len(dirs)


def declared_edges(edl, fps, root='.'):
    """{frame: [why, …]} — every frame at which the EDL says the picture changes on purpose: each join (the finisher cuts
    at round(tl·fps)), each event's accepted_cuts (take seconds, at round((tl0 + c − in)·fps)), every caption card's on
    and off (overlaid half-open: an edge is the first frame at or after its time), and qc.accepted_flashes (timeline
    seconds, by hand — a post layer that cuts in hard is declared there too)"""
    E = {}

    def add(k, why): E.setdefault(int(k), []).append(why)

    def up(t): return math.ceil(float(t) * fps - 1e-6)
    for i, x in enumerate(edl.get('events') or []):
        t0 = float(x['tl'][0])
        if i: add(round(t0 * fps), f"join {x.get('id')}")
        for c in x.get('accepted_cuts') or []:
            add(round((t0 + float(c) - float(x.get('in', 0))) * fps), f"accepted cut {x.get('id')}")
    mf = os.path.join(root, (edl.get('audio') or {}).get('captions_dir', 'edit/captions'), 'manifest.json')   # the finisher's own default
    if os.path.exists(mf):
        for c in json.load(open(mf, encoding='utf-8')):
            add(up(c['tl'][0]), 'caption on'); add(up(c['tl'][1]), 'caption off')
    for t in (edl.get('qc') or {}).get('accepted_flashes') or []:
        add(round(float(t) * fps), 'declared flash')
    return E


def freeze_floor(p, t0, t1, k=12):
    """(floor or None, tolerance, detail) — the frozen-frame row's blind spot. freezedetect calls a frame frozen when the
    mean |difference| over all planes, ÷ 2^bits, is ≤ 10^(n/20): 0.256 code values at −60 dB on 8 bits. The same
    statistic at k frame pairs over [t0, t1), on the pairs that moved nothing (under 0.12 % of luma changed by more than
    25 levels). A stalled source repeats its frame and reads 0 whatever its own noise, so the row goes blind only where
    texture is laid over the picture AFTER the stall — a grain pass, a living-grain ground — and that lifts every still
    pair: the floor is the QUIETEST still pair, read from at least 3 (None otherwise). One noisy shot is not a floor: on
    three shipped spots with no grain pass the still pairs read 0.00–0.43, the high ones a take's own noise and a
    chroma-only change. Texture laid on some shots only is not caught; the pairs over the tolerance are listed"""
    st = json.loads(_run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,pix_fmt', '-of', 'json', p]).stdout or b'{}').get('streams', [{}])[0]
    w, h = int(st.get('width') or 0), int(st.get('height') or 0)
    if not w or st.get('pix_fmt') not in ('yuv420p', 'yuvj420p'): return None, FREEZE_TOL, f"not read (pix_fmt {st.get('pix_fmt')})"
    fs = w * h * 3 // 2; quiet = []
    for t in np.linspace(t0, max(t0, t1 - 2.0 / fps_of(p)), k):
        raw = _run(['ffmpeg', '-v', 'error', '-ss', f'{t:.4f}', '-i', p, '-frames:v', '2', '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-']).stdout
        if len(raw) < 2 * fs: continue
        a = np.frombuffer(raw[:fs], np.uint8).astype(np.int16); b = np.frombuffer(raw[fs:2 * fs], np.uint8).astype(np.int16)
        if float((np.abs(a[:w * h] - b[:w * h]) > 25).mean()) < STILL_SHARE: quiet.append((float(np.abs(a - b).mean()), float(t)))
    if len(quiet) < 3: return None, FREEZE_TOL, f'{len(quiet)} of {k} sampled frame pairs moved nothing — too few to read a floor on'
    f, t = min(quiet); over = sorted(round(tt, 2) for ff, tt in quiet if ff > FREEZE_TOL)
    return f, FREEZE_TOL, (f"{len(quiet)} of {k} sampled frame pairs moved nothing; the quietest (at {t:.2f} s) reads {f:.2f} code values mean "
                           f"|difference| over the planes against freezedetect's {FREEZE_TOL:.2f} at -60 dB" + (f"; over it at {over} s" if over else ''))


def _fmt(rows, fps, kind):
    if kind == 'pops': return '; '.join(f"frame {n} ({n / fps:.3f} s) change {m} with the neighbours {sk} apart" for n, m, sk in rows)
    return '; '.join(f"frame {n} ({n / fps:.3f} s) change {dv} after/before {nb}" for n, dv, nb in rows)


def motion_cli(argv):
    ap = argparse.ArgumentParser(prog='decoded_checks.py motion', description='the motion read of a designed render: one-frame pops, one-frame steps, the WCAG flash rate; WARN lines, exit 0')
    ap.add_argument('render', help='an mp4, or a folder of PNG layers (composited over black)')
    ap.add_argument('--fps', type=float, default=None, help='the frame rate of a PNG folder (a video carries its own)')
    ap.add_argument('--accepted', default='', help="the element's own hard changes, its own seconds, comma-separated (a worded card's word lines)")
    ap.add_argument('--tiles', action='store_true', help='add the per-tile step read (4×4): a lead, never a verdict')
    a = ap.parse_args(argv)
    g, fps, (W, H) = motion_frames(a.render, a.fps)
    if len(g) < 3: print(f'MOTION-READ: fewer than 3 frames decoded from {a.render}'); return 2
    acc = {round(float(t) * fps) for t in a.accepted.split(',') if t.strip()}
    po, st = pops(g), steps(g, acc); held = [x for x in steps(g) if x[0] in acc]; fl, fat, ntr = flash_rate(g, fps)
    print(f"motion read {a.render}: {W}x{H}, {len(g)} frames at {fps:g} fps, proxy {g.shape[2]}x{g.shape[1]}")
    warn = 0
    print(f"{'WARN' if po else 'INFO'} pops: " + (_fmt(po, fps, 'pops') if po else 'none (floor: a ~2-level step in the frame mean)')); warn += bool(po)
    print(f"{'WARN' if st else 'INFO'} steps: " + (_fmt(st, fps, 'steps') if st else 'none off the declared changes') + (f" · declared (INFO): {[x[0] for x in held]}" if held else '')); warn += bool(st)
    print(f"{'WARN' if fl > 3 else 'INFO'} flash rate: {fl} general flash(es) in the busiest second" + (f" (from {fat} s)" if fat is not None else '') + f", {ntr} transition(s) — WCAG 2.3.1: at most 3"); warn += fl > 3
    if a.tiles:
        sx, sy = W / g.shape[2], H / g.shape[1]; hs, ws = g.shape[1] // 4, g.shape[2] // 4; ts = tile_steps(g, acc)
        print(f"{'WARN' if ts else 'INFO'} tile steps (a LEAD: designed slams, wipes, bar slashes and shakes fire it too — read each on its frames): " + (
            '; '.join(f"frame {f} ({f / fps:.3f} s) tile row {r} col {c} (x {round(c * ws * sx)}–{round((c + 1) * ws * sx)}, y {round(r * hs * sy)}–{round((r + 1) * hs * sy)}) change {dv} after/before {nb}" for f, r, c, dv, nb in ts) if ts else 'none'))
        warn += bool(ts)
    print(f"MOTION-READ {warn} warning row(s)"); return 0


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
        # ---- the motion rows ----
        def clip(fn, n=48): return np.stack([fn(k) for k in range(n)]).astype(np.float32)
        flash = clip(lambda k: np.full((128, 128), 40.0 + (80 if k == 24 else 0)))
        step = clip(lambda k: np.full((128, 128), 40.0 if k < 24 else 120.0))

        def small(k):
            a = np.full((128, 128), 40.0); a[10:22, 10:22] = 40.0 if k < 24 else 140.0; return a   # 0.9 % of the frame
        sm = clip(small)
        strobe = clip(lambda k: np.full((128, 128), 255.0 if 12 <= k < 36 and k % 2 else 0.0))
        chk.append(('a one-frame flash is a pop, not a step', [x[0] for x in pops(flash)] == [24] and not steps(flash)))
        chk.append(('a value that jumps and stays is a step, not a pop', [x[0] for x in steps(step)] == [24] and not pops(step)))
        chk.append(('a step on a declared frame is set aside', not steps(step, {24})))
        chk.append(('a 0.9 % box step: missed whole-frame, found by its tile', not steps(sm) and [(x[0], x[1], x[2]) for x in tile_steps(sm)] == [(24, 0, 0)]))
        chk.append(('a 24-transition second reads > 3 flashes; one flash reads 1', flash_rate(strobe, 24)[0] > 3 and flash_rate(flash, 24)[0] == 1))
        os.makedirs(os.path.join(r, 'caps'))
        json.dump([{'file': 'caps/c0.png', 'tl': [0.2, 0.6], 'text': 'A'}], open(os.path.join(r, 'caps', 'manifest.json'), 'w'))
        edl = {'events': [{'id': 'A', 'tl': [0.0, 1.0], 'in': 0}, {'id': 'B', 'tl': [1.0, 2.0], 'in': 0.5, 'accepted_cuts': [1.0]}],
               'post_layers': [{'id': 'L', 'at': 0.5, 'dur': 0.25}], 'audio': {'captions_dir': 'caps'}, 'qc': {'accepted_flashes': [1.75]}}
        chk.append(('declared edges: join 24, accepted cut 36, caption 5/15, flash 42 — a layer is not one', set(declared_edges(edl, 24, r)) == {24, 36, 5, 15, 42}))
        enc = ['-c:v', 'libx264', '-crf', '1', '-pix_fmt', 'yuv420p']
        fm = os.path.join(r, 'flash.mp4'); pp = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray', '-s', '128x128', '-r', '24', '-i', '-', *enc, fm], stdin=subprocess.PIPE)
        pp.stdin.write(flash.astype(np.uint8).tobytes()); pp.stdin.close(); pp.wait()
        g, f, _ = motion_frames(fm); chk.append(('an mp4 read through the proxy finds the pop at frame 24', len(g) == 48 and [x[0] for x in pops(g)] == [24]))
        pd = os.path.join(r, 'layer'); os.makedirs(pd)
        from PIL import Image
        for k in range(8):
            a = np.zeros((64, 64, 4), np.uint8); a[8:56, 8:56] = (255, 255, 255, 60 if k < 4 else 220); Image.fromarray(a).save(os.path.join(pd, f'f{k:03d}.png'))
        g, f, _ = motion_frames(pd, 24); chk.append(('a PNG layer folder, composited over black, steps at frame 4', [x[0] for x in steps(g)] == [4]))
        still = os.path.join(r, 'still.mp4'); grain = os.path.join(r, 'grain.mp4'); settle = os.path.join(r, 'settle.mp4'); rng = np.random.default_rng(5)

        def settling(k):   # a still frame with one small patch drifting a fraction of a level: motion in one place, no texture
            a = np.full((128, 128), 120.0); a[40:60, 40:60] = 120 + 6 * np.sin(k / 3.0); return a
        for path, fn in ((still, lambda k: np.full((128, 128), 120.0)), (grain, lambda k: 120 + rng.normal(0, 3.0, (128, 128))), (settle, settling)):
            pp = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray', '-s', '128x128', '-r', '24', '-i', '-', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', path], stdin=subprocess.PIPE)
            for k in range(48): pp.stdin.write(np.clip(fn(k), 0, 255).astype(np.uint8).tobytes())
            pp.stdin.close(); pp.wait()
        fs_, tol, _ = freeze_floor(still, 0, 2); fg, _, _ = freeze_floor(grain, 0, 2); fz, _, _ = freeze_floor(settle, 0, 2)
        chk.append(('the frozen-frame floor: grain over the whole picture reads over the tolerance (blind)', fg is not None and fg > tol))
        chk.append(('a clean held frame and a small patch settling read under it', fs_ is not None and fs_ <= tol and (fz is None or fz <= tol)))
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return 0 if ok else 1


if __name__ == '__main__':
    if '--selftest' in sys.argv: sys.exit(selftest())
    if len(sys.argv) > 1 and sys.argv[1] == 'motion': sys.exit(motion_cli(sys.argv[2:]))
    print(__doc__)
