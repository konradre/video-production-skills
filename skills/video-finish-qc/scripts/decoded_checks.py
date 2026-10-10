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

The motion rows read every frame on an area proxy (long side 320 px) — WARN lines here; the delivery QC (qc_deliverable.py)
keeps pops and steps as WARN lines and fails the flash rate and sustained flashes, judgement rows:
  pops        a one-frame flash: frame n unlike both neighbours while they match — min(d[n-1], d[n]) > 2.0 and
              mean|f[n+1] - f[n-1]| < 0.35 × that min (claude-motion-design's two-sided test; a cut cannot fire it).
              Measured floor: a step in the frame mean of ~2 levels — ~1.5 % of the frame at a 135-level flash in a
              quiet scene, worse with motion elsewhere; 0 fires on 39 designed renders and 7 shipped spots
  steps       a one-frame step: the change into frame n over 3 × both neighbouring changes and over 2.0 — what two
              tweens fighting over one property leave (HYPERFRAMES-CONTRACT § Silent traps). Every frame the EDL says
              changes on purpose is set aside on the EXACT frame (declared_edges: joins, accepted_cuts, captions on and
              off, qc.accepted_flashes); on three shipped spots that left only a worded card's own word lines, which
              the card's event declares as accepted_cuts
  flashes     WCAG 2.2 flashes paired at the SAME place, from the decoded RGB (flash_read): each place follows its relative
              luminance between extremes, and a rise or fall of ≥ 0.1 from the last extreme is a transition however many
              frames it takes (a smooth pulse counts), with its darker side under 0.8; the opposite transition at the same
              place within one second completes a flash there. A flash EVENT is a frame on which the places completing a
              flash cover ≥ 25 % of an area, so they happen at the same moment, as WCAG combines them. Red, WCAG 2.2: a
              move toward or away from a saturated red (R/(R+G+B) ≥ 0.8, linear) with the colours > 0.2 apart in u′v′.
              Areas: the WHOLE frame (the broadcast area) and a 10° field (flash_fields: the phone window, 0.94 × 0.53 of
              a 9:16 frame at 35 cm; the W3C window, 341 × 256 on a 1024 × 768 screen). Rows (flash_rows):
                flash rate         whole frame, more than 3 in any one second — a WARN here, a FAIL in the delivery QC
                sustained flashes  EA IRIS's extended failure counted in flashes on the same read (IRIS counts transitions, two
                                   to a flash): 2–3 a second held for 4 s of any 5 s — WARN here, FAIL there
                flash warning      IRIS's warning, 2 or more flashes in a second — WARN
                10° field          the phone window over 3 — WARN; the W3C window printed as INFO (per place it reads a
                                   fine texture's swings: 17 a second on falling gravel, measured)
                red flashes        the whole frame or the phone window over 3 — WARN; the W3C window INFO
              qc.accepted_flash_rate's time windows set flashes aside from the whole-frame rows (qc_deliverable.py); the
              10° and red rows read every flash
  floor       the frozen-frame row's blind spot (freeze_floor): freezedetect's statistic at sampled still frame pairs;
              over its −60 dB tolerance (0.26 code values) a frozen shot under that texture does not register

  decoded_checks.py motion <render.mp4 | frames-dir> [--fps 24] [--accepted s,s,… | <manifest.json> | <captions.html> | <timeline.json>]… [--tiles]
      a designed render's motion read: pops, steps and the flash rows; a frames-dir is read at the data-fps of the
      composition beside it unless --fps is given (24 when neither says); --accepted (repeatable) = the element's own hard
      changes: its own seconds (a worded card's word lines — the numbers its EDL event declares as accepted_cuts), a
      caption manifest, an explainer's compositions/captions.html (each caption's show and hide) or its timeline.json
      (each scene cut); --tiles adds the
      per-tile step read (4×4), a LEAD: it reaches a small element's snap, and designed slams, wipes, bar slashes and
      shakes fire it too (on one kit every tile hit was designed; on one shipped card it caught one of three real snaps,
      5 % over its threshold)
  decoded_checks.py --selftest
"""
import argparse, glob, json, math, os, re, subprocess, sys, tempfile
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


# ---- the flash rows: WCAG 2.2 general and red flashes, paired at the SAME place ----
RED_RATIO, RED_UV = 0.8, 0.2                  # WCAG 2.2 red: one state R/(R+G+B) >= 0.8 (linear sRGB), the states > 0.2 apart in u'v'
FLASH_FAIL, FLASH_WARN = 3, 2                 # over 3 flashes in any one second fails; 2 is EA IRIS's warning (WarningTransitions 4)
EXT_LO, EXT_HI, EXT_HOLD, EXT_WINDOW = 2, 3, 4.0, 5.0   # IRIS's extended failure: 2-3 flashes (4-6 transitions) a second for 4 s of any 5 s
_WP = (0.1978, 0.4683)                        # D65 in u'v': the colour given to a state too dark to have one


def _lin(c):
    c = c / 255.0; return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _flash_state(f):
    """an RGB frame (0-255) → relative luminance, red ratio, u', v' per place (linear sRGB). A state under 1 % luminance
    has no colour (ratio 0, the white point): colour is undefined at black, and decoded black is noisy — an assumption"""
    r, g, b = _lin(f[..., 0]), _lin(f[..., 1]), _lin(f[..., 2]); L = 0.2126 * r + 0.7152 * g + 0.0722 * b; blk = L < 0.01
    s = r + g + b; ratio = np.where(blk, 0.0, r / np.maximum(s, 1e-9))
    X = 0.4124 * r + 0.3576 * g + 0.1805 * b; Z = 0.0193 * r + 0.1192 * g + 0.9505 * b; d = np.maximum(X + 15 * L + 3 * Z, 1e-9)
    return L, ratio, np.where(blk, _WP[0], 4 * X / d), np.where(blk, _WP[1], 9 * L / d)


def _swing_general(z, L):
    """each place's luminance followed between its extremes: a rise or fall of FLASH_DELTA from the last extreme is a
    transition however many frames it takes, kept when its darker side is under FLASH_DARK → (up, down) masks"""
    T, P, lo, hi = z['T'], z['P'], z['lo'], z['hi']; u0 = T == 0      # before its first swing a place tracks its low and high
    np.minimum(lo, L, out=lo, where=u0); np.maximum(hi, L, out=hi, where=u0)
    ext = ((T == 1) & (L > P)) | ((T == -1) & (L < P)); P[ext] = L[ext]
    bu, bd = np.where(u0, lo, P), np.where(u0, hi, P)
    up, dn = ((T == -1) | u0) & (L - bu >= FLASH_DELTA), ((T == 1) | u0) & (bd - L >= FLASH_DELTA)
    cu, cd = np.minimum(bu, L) < FLASH_DARK, np.minimum(bd, L) < FLASH_DARK
    T[up], T[dn] = 1, -1; P[up | dn] = L[up | dn]; return up & cu, dn & cd


def _swing_red(z, r, u, v):
    """the same on the red ratio: a move toward red or away from it, the colours more than RED_UV apart in u'v' from the
    last extreme, kept when one of the two states is saturated red → (toward, away) masks"""
    T, P, U, V = z['T'], z['P'], z['U'], z['V']; u0 = T == 0
    lo_, hi_ = u0 & (r < z['rlo']), u0 & (r > z['rhi'])
    for k, x in (('rlo', r), ('ulo', u), ('vlo', v)): z[k][lo_] = x[lo_]
    for k, x in (('rhi', r), ('uhi', u), ('vhi', v)): z[k][hi_] = x[hi_]
    ext = ((T == 1) & (r > P)) | ((T == -1) & (r < P))
    for a, b in ((P, r), (U, u), (V, v)): a[ext] = b[ext]
    br, bu_, bv = np.where(u0, z['rlo'], P), np.where(u0, z['ulo'], U), np.where(u0, z['vlo'], V)      # toward red: from the low
    ar, au, av = np.where(u0, z['rhi'], P), np.where(u0, z['uhi'], U), np.where(u0, z['vhi'], V)      # away: from the high
    aw = ((T == 1) | u0) & (r < ar) & (np.hypot(u - au, v - av) > RED_UV)
    to = ((T == -1) | u0) & (r > br) & (np.hypot(u - bu_, v - bv) > RED_UV) & ~aw
    sat = r >= RED_RATIO; ct, ca = (br >= RED_RATIO) | sat, (ar >= RED_RATIO) | sat
    T[to], T[aw] = 1, -1; fl = to | aw
    for a, b in ((P, r), (U, u), (V, v)): a[fl] = b[fl]
    return to & ct, aw & ca


def _win_max(m, wh, ww):   # the largest share of True over every wh × ww window (an integral image)
    c = np.pad(m.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return float((c[wh:, ww:] - c[:-wh, ww:] - c[wh:, :-ww] + c[:-wh, :-ww]).max()) / (wh * ww)


def flash_fields(W, H):
    """WCAG 2.3.1's 10° field as (width, height) fractions of the frame. phone: 10° at 35 cm (phones are held at 32-37 cm)
    is 6.12 cm, 0.94 of a 6.5 cm-wide screen — 0.94 of the short side, 0.94 × short/long of the long side (0.94 × 0.53 of a
    9:16 frame). w3c: W3C's 341 × 256 on a 1024 × 768 screen, the frame fitted to that screen first (0.79 × 0.33 of 9:16)"""
    s_, l_ = min(W, H), max(W, H); k = 0.94 * s_ / l_; fit = min(1024 / W, 768 / H)
    return {'phone': (0.94, k) if W <= H else (k, 0.94), 'w3c': (min(1.0, 341 / (W * fit)), min(1.0, 256 / (H * fit)))}


def comp_fps(p):
    """a PNG folder's frame rate from its composition (<composition>/frames → <composition>/index.html data-fps), or None"""
    try: m = re.search(r'data-fps="([\d.]+)"', open(os.path.join(os.path.dirname(os.path.abspath(p.rstrip('/'))), 'index.html'), encoding='utf-8').read())
    except OSError: return None
    return float(m.group(1)) if m else None


def flash_frames(p, fps=None):
    """every frame as RGB (0-255, float32) on the area proxy, streamed — a video decoded with its tags honoured, or a folder
    of PNG layers premultiplied over black → (frames, fps, (W, H))"""
    if os.path.isdir(p):
        from PIL import Image
        fs = sorted(glob.glob(os.path.join(p, '*.png')))
        if not fs: return iter(()), float(fps or 24.0), (0, 0)
        W, H = Image.open(fs[0]).size; pw, ph = _proxy(W, H)

        def png():
            for f in fs:
                a = np.asarray(Image.open(f).convert('RGBA'), np.float32); rgb = np.clip(a[..., :3] * (a[..., 3:] / 255.0) + 0.5, 0, 255)
                yield np.asarray(Image.fromarray(rgb.astype(np.uint8)).resize((pw, ph), Image.BOX), np.float32)
        return png(), float(fps or 24.0), (W, H)
    st = json.loads(_run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', p]).stdout or b'{}').get('streams', [{}])[0]
    W, H = int(st.get('width') or 0), int(st.get('height') or 0)
    if not W: return iter(()), float(fps or 24.0), (0, 0)
    pw, ph = _proxy(W, H); size = pw * ph * 3

    def video():
        pr = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', p, '-vf', f'scale={pw}:{ph}:flags=area,format=rgb24', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
        try:
            while len(b := pr.stdout.read(size)) == size: yield np.frombuffer(b, np.uint8).reshape(ph, pw, 3).astype(np.float32)
        finally: pr.stdout.close(); pr.wait()
    return video(), float(fps or fps_of(p)), (W, H)


def flash_read(frames, fps, W, H):
    """WCAG 2.2 general and red flashes paired at the SAME place: a place's opposite transitions within one second are a
    flash there. A flash EVENT is a frame on which the places completing a flash cover >= FLASH_AREA of an area — the whole
    frame, or a 10° field anywhere in it — so the flashes happen at the same moment, as WCAG combines them →
    {'n', 'fps', 'fields', 'general': {area: [frame…]}, 'red': {area: [frame…]}}"""
    fields = flash_fields(W, H); win = max(1, int(round(fps))); z = None; n = 0
    out = {k: {a: [] for a in ('frame', *fields)} for k in ('general', 'red')}
    for i, f in enumerate(frames):
        n += 1; L, ratio, u, v = _flash_state(f); h, w = L.shape
        if z is None:
            zr = {'T': np.zeros(L.shape, np.int8), 'P': ratio.copy(), 'U': u.copy(), 'V': v.copy()}
            for e in ('lo', 'hi'): zr.update({'r' + e: ratio.copy(), 'u' + e: u.copy(), 'v' + e: v.copy()})
            z = {'general': {'T': np.zeros(L.shape, np.int8), 'P': L.copy(), 'lo': L.copy(), 'hi': L.copy()}, 'red': zr,
                 'd': {k: np.zeros(L.shape, np.int8) for k in out}, 't': {k: np.zeros(L.shape, np.int32) for k in out}}
            continue
        for k, (up, dn) in (('general', _swing_general(z['general'], L)), ('red', _swing_red(z['red'], ratio, u, v))):
            d, t = z['d'][k], z['t'][k]; live = (i - t) < win
            P = (up & (d == -1) & live) | (dn & (d == 1) & live)   # a place's pair completes: consumed, the next swing starts anew
            d[P] = 0; nu, nd = up & ~P, dn & ~P; d[nu] = 1; t[nu] = i; d[nd] = -1; t[nd] = i
            if not P.any(): continue
            if float(P.mean()) >= FLASH_AREA: out[k]['frame'].append(i)
            for a, (fw, fh) in fields.items():
                if _win_max(P, max(1, round(fh * h)), max(1, round(fw * w))) >= FLASH_AREA: out[k][a].append(i)
    return {'n': n, 'fps': float(fps), 'fields': fields, **out}


def busiest(ev, win):
    """(the most events inside any `win` frames, the frame that stretch starts at)"""
    best, at, j = 0, None, 0
    for k in range(len(ev)):
        while ev[k] - ev[j] >= win: j += 1
        if k - j + 1 > best: best, at = k - j + 1, ev[j]
    return best, at


def sustained(ev, n, fps):
    """EA IRIS's tracker (electronicarts/IRIS src/TransitionTracker.cpp with config/appsettings.json, read 2026-10-11) on one
    series of whole-frame flash events, counted in FLASHES — IRIS counts transitions, two to a flash, so its thresholds halve:
    F = the flashes in the trailing second at each frame; an EXTENDED failure where F is 2-3 and the trailing 5 s hold 4 s of
    frames with F at 2-3; a warning where F >= 2. On IRIS's own test clips this matches its fail and extended verdicts and
    warns on two that IRIS passes: at 1.5 flashes a second, two flashes can complete inside one second →
    {'max', 'extended', 'warn': the first frame of each or None, 'warn_s': the seconds with F >= 2}"""
    win = max(1, int(round(fps))); F = np.zeros(max(1, n), np.int32)
    for i in ev: F[i:min(len(F), i + win)] += 1
    band = (F >= EXT_LO) & (F <= EXT_HI); ew, eh = int(round(EXT_WINDOW * fps)), int(round(EXT_HOLD * fps))
    c = np.concatenate(([0], np.cumsum(band))); E = c[1:] - c[np.maximum(0, np.arange(1, len(F) + 1) - ew)]
    first = lambda m: int(np.argmax(m)) if m.any() else None
    return {'max': int(F.max()), 'extended': first(band & (E >= eh)), 'warn': first(F >= FLASH_WARN), 'warn_s': float((F >= FLASH_WARN).sum()) / fps}


def accepted_flash_windows(q):
    """the EDL's qc.accepted_flash_rate → ([(from s, to s, why)], [problem]): a list of {"from", "to", "note"} — one object
    reads as a one-item list. The spot-wide string of the first form sets nothing aside and is named a problem"""
    v = (q or {}).get('accepted_flash_rate')
    if not v: return [], []
    win, bad = [], []
    for x in (v if isinstance(v, list) else [v]):
        try: a, b, why = float(x['from']), float(x['to']), str(x.get('note') or '').strip()
        except (TypeError, KeyError, ValueError): bad.append(f"{x!r} is not a time window {{\"from\", \"to\", \"note\"}} — nothing set aside (EDL-CONTRACT § qc)"); continue
        if b > a and why: win.append((a, b, why))
        else: bad.append(f"{x!r} needs from < to and a note — nothing set aside")
    return win, bad


def flash_rows(res, accepted=()):
    """the flash rows of one flash_read(): [(level, label, detail)], level PASS/FAIL for the delivery QC's judgement rows
    (the flash rate, sustained flashes) and WARN/INFO for the rest. Whole-frame flash events inside an accepted (from, to,
    why) window are set aside from the whole-frame rows (the rate, sustained flashes, the warning) and each window prints
    what it set aside; the 10° and red rows are WARN lines and read every flash, the declared ones included"""
    fps, n = res['fps'], res['n']; win = max(1, int(round(fps))); rows = []
    within = lambda i: any(a - 1e-6 <= i / fps <= b + 1e-6 for a, b, _ in accepted)
    ev = {k: dict(res[k]) for k in ('general', 'red')}; ev['general']['frame'] = [i for i in res['general']['frame'] if not within(i)]
    at = lambda f: f" from {f / fps:.2f} s" if f is not None else ''
    for a, b, why in accepted:
        sel = [i for i in res['general']['frame'] if a - 1e-6 <= i / fps <= b + 1e-6]; c, f = busiest(sel, win)
        rows.append(('INFO', 'accepted flash rate', f"{a:g}–{b:g} s: {len(sel)} whole-frame flash(es) set aside, {c} in its busiest second{at(f)} — {why}"))
    g = ev['general']['frame']; nf, f0 = busiest(g, win); s = sustained(g, n, fps)
    rows.append(('PASS' if nf <= FLASH_FAIL else 'FAIL', 'flash rate', f"{nf} general flash(es) in the busiest second{at(f0)} — at most {FLASH_FAIL} in any one "
                 "second; a flash is a place brightening and darkening (or the reverse) by 0.1 relative luminance within a second, counted when the "
                 "places flashing on one frame cover 25 % of the WHOLE frame (the broadcast area)"))
    rows.append(('PASS' if s['extended'] is None else 'FAIL', 'sustained flashes', (f"{EXT_LO}–{EXT_HI} flashes a second held for {EXT_HOLD:g} s of {EXT_WINDOW:g}{at(s['extended'])}"
                 if s['extended'] is not None else f"no {EXT_HOLD:g} s of any {EXT_WINDOW:g} s at {EXT_LO}–{EXT_HI} flashes a second") + " — EA IRIS's extended failure, whole frame"))
    rows.append(('WARN' if s['warn'] is not None else 'INFO', 'flash warning', (f"{s['warn_s']:.2f} s with {FLASH_WARN} or more flashes in the trailing second{at(s['warn'])}"
                 if s['warn'] is not None else f"at most {s['max']} flash(es) in any second") + f" — EA IRIS warns at {FLASH_WARN}, whole frame"))
    (pw_, ph_), (ww_, wh_) = res['fields']['phone'], res['fields']['w3c']
    p, pf = busiest(ev['general']['phone'], win); w3, wf = busiest(ev['general']['w3c'], win)
    rows.append(('WARN' if p > FLASH_FAIL else 'INFO', 'flash rate in a 10° field', f"phone window {p}{at(pf)} — over {FLASH_FAIL} warns · W3C window {w3}{at(wf)} — INFO "
                 f"(WCAG 2.3.1: 25 % of any 10° field; phone {pw_:.2f} × {ph_:.2f} of the frame at 35 cm, W3C {ww_:.2f} × {wh_:.2f})"))
    rf, rff = busiest(ev['red']['frame'], win); rp, rpf = busiest(ev['red']['phone'], win); rw, rwf = busiest(ev['red']['w3c'], win)
    rows.append(('WARN' if max(rf, rp) > FLASH_FAIL else 'INFO', 'red flashes', f"whole frame {rf}{at(rff)} · phone window {rp}{at(rpf)} — over {FLASH_FAIL} in either warns · "
                 f"W3C window {rw}{at(rwf)} — INFO (WCAG 2.2: to or from a saturated red, R/(R+G+B) ≥ {RED_RATIO:g}, the colours more than {RED_UV:g} apart in u′v′)"))
    return rows


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


def accepted_frames(specs, fps):
    """{frame} an element changes on purpose, from each --accepted spec: seconds, comma-separated (at round(t·fps)), a
    caption manifest (.json, each card's tl), an explainer's compositions/captions.html ([block, show, hide] in
    seconds) — each caption's show and hide at the first frame at or after its time, as they are set — or an explainer's
    timeline.json (each scene's start after 0: a cut, at the first frame at or after it)"""
    out = set(); up = lambda t: math.ceil(float(t) * fps - 1e-6)
    for s in (x.strip() for x in specs or []):
        if not s: continue
        if os.path.isfile(s):
            if s.endswith('.json'):
                d = json.load(open(s, encoding='utf-8'))
                if isinstance(d, dict): out |= {up(sc['start']) for sc in d.get('scenes') or [] if float(sc.get('start', 0)) > 0}
                else:
                    for c in d: out |= {up(c['tl'][0]), up(c['tl'][1])}
            else:
                for a, b in re.findall(r'\[\d+, ([\d.]+), ([\d.]+)\]', open(s, encoding='utf-8').read()): out |= {up(a), up(b)}
            continue
        try: out |= {round(float(t) * fps) for t in s.split(',') if t.strip()}
        except ValueError: raise SystemExit(f'--accepted {s}: neither seconds nor a readable file')
    return out


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
    ap = argparse.ArgumentParser(prog='decoded_checks.py motion', description='the motion read of a designed render: one-frame pops, one-frame steps, the WCAG flash rows; WARN lines, exit 0')
    ap.add_argument('render', help='an mp4, or a folder of PNG layers (composited over black)')
    ap.add_argument('--fps', type=float, default=None, help="the frame rate of a PNG folder (a video carries its own); default: the data-fps of the composition beside the folder, else 24")
    ap.add_argument('--accepted', action='append', default=[], help="the element's own hard changes, repeatable: its own seconds, comma-separated "
                    "(a worded card's word lines), a caption manifest.json, an explainer's compositions/captions.html (each caption's show and hide), or its timeline.json (each scene cut)")
    ap.add_argument('--tiles', action='store_true', help='add the per-tile step read (4×4): a lead, never a verdict')
    a = ap.parse_args(argv)
    rate, src = a.fps, '--fps'
    if rate is None and os.path.isdir(a.render): rate = comp_fps(a.render); src = "the composition's data-fps" if rate else 'nothing declared it: 24 assumed, pass --fps'
    g, fps, (W, H) = motion_frames(a.render, rate)
    if len(g) < 3: print(f'MOTION-READ: fewer than 3 frames decoded from {a.render}'); return 2
    try: per = [(s, accepted_frames([s], fps)) for s in a.accepted]
    except SystemExit as e: print(f'MOTION-READ: {e}'); return 2
    acc = set().union(*(f for _, f in per)) if per else set()
    po, st = pops(g), steps(g, acc); held = [x for x in steps(g) if x[0] in acc]
    print(f"motion read {a.render}: {W}x{H}, {len(g)} frames at {fps:g} fps" + (f" ({src})" if os.path.isdir(a.render) else '') + f", proxy {g.shape[2]}x{g.shape[1]}")
    if os.path.isdir(a.render) and a.fps is None and rate is None: print(f"WARN fps: no --fps and no data-fps in {os.path.join(os.path.dirname(os.path.abspath(a.render.rstrip('/'))), 'index.html')} — read at 24 fps; times and the one-second windows are off unless that is right")
    for s, f in per: print(f"{'INFO' if f else 'WARN'} accepted {s}: {len(f)} frame(s) set aside" + ('' if f else ' — nothing read from it'))
    warn = 0
    print(f"{'WARN' if po else 'INFO'} pops: " + (_fmt(po, fps, 'pops') if po else 'none (floor: a ~2-level step in the frame mean)')); warn += bool(po)
    print(f"{'WARN' if st else 'INFO'} steps: " + (_fmt(st, fps, 'steps') if st else 'none off the declared changes') + (f" · declared (INFO): {[x[0] for x in held]}" if held else '')); warn += bool(st)
    for lvl, label, det in flash_rows(flash_read(*flash_frames(a.render, fps)[:2], W, H)):   # a FAIL of the delivery QC is a WARN line here
        bad = lvl in ('FAIL', 'WARN'); print(f"{'WARN' if bad else 'INFO'} {label}: {det}"); warn += bad
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
        chk.append(('a one-frame flash is a pop, not a step', [x[0] for x in pops(flash)] == [24] and not steps(flash)))
        chk.append(('a value that jumps and stays is a step, not a pop', [x[0] for x in steps(step)] == [24] and not pops(step)))
        chk.append(('a step on a declared frame is set aside', not steps(step, {24})))
        chk.append(('a 0.9 % box step: missed whole-frame, found by its tile', not steps(sm) and [(x[0], x[1], x[2]) for x in tile_steps(sm)] == [(24, 0, 0)]))
        # ---- the flash rows: known answers on a 9:16 proxy ----
        sz, Wf, Hf = (56, 32), 1080, 1920

        def rgb(c): return np.broadcast_to(np.array(c, np.float32), sz + (3,)).copy()

        def code(L): return 255 * (1.055 * L ** (1 / 2.4) - 0.055) if L > 0.0031308 else 255 * 12.92 * L   # the sRGB code of a relative luminance

        def rd(seq): return flash_read(iter(seq), 24.0, Wf, Hf)

        def nf(res, k='general', a='frame'): return busiest(res[k][a], 24)[0]
        r1 = rd([rgb((255,) * 3) if k % 2 else rgb((0,) * 3) for k in range(24)])
        chk.append(('flash: a full-frame grey strobe reads >= 11 a second in every area and no red', all(nf(r1, 'general', a) >= 11 for a in ('frame', 'phone', 'w3c')) and nf(r1, 'red') == 0))
        chk.append(('flash: one bright frame is one flash', nf(rd([rgb((40,) * 3)] * 5 + [rgb((120,) * 3)] + [rgb((40,) * 3)] * 5)) == 1))
        chk.append(('flash: a black-red strobe reads >= 11 red flashes a second', nf(rd([rgb((255, 0, 0)) if k % 2 else rgb((0, 0, 0)) for k in range(24)]), 'red') >= 11))
        r2 = rd([rgb((255, 0, 0)) if k % 2 else rgb((0, 148, 0)) for k in range(24)])
        chk.append(('flash: an iso-luminant red-green strobe is red only (>= 11 red, 0 general)', nf(r2, 'red') >= 11 and nf(r2) == 0))
        chk.append(('flash: a smooth 4 Hz pulse (no frame-to-frame step reaches 0.1) reads >= 4 a second', nf(rd([rgb((code(0.29 + 0.09 * np.sin(2 * np.pi * 4 * k / 24)),) * 3) for k in range(48)])) >= 4))

        def band(k):
            f = rgb((10,) * 3); x0 = int(k * 0.1 * sz[1]); f[:, x0:x0 + int(0.3 * sz[1])] = 255; return f
        r3 = rd([band(k) for k in range(8)])
        chk.append(('flash: a bright band moving across reads 0 in every area', all(nf(r3, 'general', a) == 0 for a in ('frame', 'phone', 'w3c'))))

        def part(k, rows_, cols_):   # a block of the frame strobes 0.2 <-> 0.5 relative luminance every 2 frames: 6 a second
            f = rgb((code(0.2),) * 3); f[:int(rows_ * sz[0]), :int(cols_ * sz[1])] = code(0.5 if (k // 2) % 2 else 0.2); return f
        r4 = rd([part(k, 0.55, 0.55) for k in range(48)])
        lv4 = {lb: lv for lv, lb, _ in flash_rows(r4)}; lv4a = {lb: lv for lv, lb, _ in flash_rows(r4, [(0.0, 2.0, 'the strobe the brief asks for')])}
        chk.append(('flash: a 6 Hz strobe on 30 % of the frame FAILS the flash rate; an accepted window over it passes and prints INFO',
                    nf(r4) >= 5 and lv4['flash rate'] == 'FAIL' and lv4a['flash rate'] == 'PASS' and lv4a.get('accepted flash rate') == 'INFO'))
        r5 = rd([part(k, 0.16, 1.0) for k in range(48)])
        lv5 = {lb: lv for lv, lb, _ in flash_rows(r5)}
        chk.append(('flash: a strobe on 16 % of the frame passes the whole frame and WARNs in the phone 10° field', nf(r5) == 0 and nf(r5, 'general', 'phone') >= 5
                    and lv5['flash rate'] == 'PASS' and lv5['flash rate in a 10° field'] == 'WARN'))
        rd_ = flash_rows(rd([rgb((255, 0, 0)) if k % 2 else rgb((0, 0, 0)) for k in range(24)]))
        chk.append(('flash: the red strobe WARNs the red row', {lb: lv for lv, lb, _ in rd_}['red flashes'] == 'WARN'))

        def slow(k): return rgb((255 if (k // 5) % 2 else 0,) * 3)   # a flash every 10 frames: 2.4 a second
        long_, short_ = {lb: lv for lv, lb, _ in flash_rows(rd([slow(k) for k in range(144)]))}, {lb: lv for lv, lb, _ in flash_rows(rd([slow(k) for k in range(72)]))}
        chk.append(('flash: 2.4 flashes a second for 6 s FAILS sustained (IRIS extended), for 3 s only warns; neither fails the rate',
                    long_['sustained flashes'] == 'FAIL' and short_['sustained flashes'] == 'PASS' and short_['flash warning'] == 'WARN' and long_['flash rate'] == short_['flash rate'] == 'PASS'))

        def slower(k): return rgb((255 if (k // 8) % 2 else 0,) * 3)   # a transition every 8 frames: 1.5 flashes a second
        sl = {lb: lv for lv, lb, _ in flash_rows(rd([slower(k) for k in range(144)]))}
        chk.append(('flash: 1.5 flashes a second for 6 s warns and never fails (IRIS passes it outright: counted in flashes, two can complete in one second)',
                    sl['flash warning'] == 'WARN' and sl['sustained flashes'] == 'PASS' and sl['flash rate'] == 'PASS'))
        w_ok, w_bad = accepted_flash_windows({'accepted_flash_rate': {'from': 1, 'to': 2.5, 'note': 'a gag'}}), accepted_flash_windows({'accepted_flash_rate': 'a strobe'})
        chk.append(('qc.accepted_flash_rate: a {from, to, note} window reads; the old spot-wide string sets nothing aside', w_ok == ([(1.0, 2.5, 'a gag')], []) and not w_bad[0] and len(w_bad[1]) == 1))
        cd = os.path.join(r, 'comp'); os.makedirs(os.path.join(cd, 'frames')); open(os.path.join(cd, 'index.html'), 'w').write('<div id="root" data-fps="29.97" data-duration="2">')
        chk.append(("a frames folder's rate comes from its composition's data-fps (29.97), and is None with no composition", comp_fps(os.path.join(cd, 'frames')) == 29.97 and comp_fps(os.path.join(r, 'caps')) is None))
        os.makedirs(os.path.join(r, 'caps'))
        json.dump([{'file': 'caps/c0.png', 'tl': [0.2, 0.6], 'text': 'A'}], open(os.path.join(r, 'caps', 'manifest.json'), 'w'))
        edl = {'events': [{'id': 'A', 'tl': [0.0, 1.0], 'in': 0}, {'id': 'B', 'tl': [1.0, 2.0], 'in': 0.5, 'accepted_cuts': [1.0]}],
               'post_layers': [{'id': 'L', 'at': 0.5, 'dur': 0.25}], 'audio': {'captions_dir': 'caps'}, 'qc': {'accepted_flashes': [1.75]}}
        chk.append(('declared edges: join 24, accepted cut 36, caption 5/15, flash 42 — a layer is not one', set(declared_edges(edl, 24, r)) == {24, 36, 5, 15, 42}))
        open(os.path.join(r, 'captions.html'), 'w').write('<script>\n  var C = [[0, 0.650, 1.100]];\n</script>')
        json.dump({'scenes': [{'id': 's01', 'start': 0.0}, {'id': 's02', 'start': 2.0}]}, open(os.path.join(r, 'timeline.json'), 'w'))
        acc = accepted_frames(['1.0,2.5', os.path.join(r, 'caps', 'manifest.json'), os.path.join(r, 'captions.html'), os.path.join(r, 'timeline.json')], 24)
        chk.append((f'--accepted: seconds 24/60, a manifest 5/15, a captions.html 16/27, a timeline.json scene cut 48 → {sorted(acc)}', acc == {24, 60, 5, 15, 16, 27, 48}))
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
