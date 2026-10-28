#!/usr/bin/env python3
"""qc_deliverable.py — the delivery QC in ONE pass on the DELIVERED file, per metric with its label (never a total score):
  duration     vs the EDL runtime (< 50 ms)
  loudness     integrated LUFS · LRA · true peak — and the loudness must be FINITE: an audio-STREAM check is not a SOUND check
               (a conforming AAC track at -inf passes a stream probe and ships silent); the true peak must sit under the platform
               ceiling (--tp-ceiling; default = the EDL's loudnorm.TP_ceiling, else -1 dBTP) — the EDL's TP is the master's
               limiter ceiling under it, and the AAC overshoot on limited peaks measured 0.4–1.0 dB, growing with the limiting
  packets      the AAC packet clock (aac_packet_clock.py): no packet over 1024 samples, no gap between packet starts — a
               timestamp jump before the encoder (loudnorm's flush of a partial block) becomes ONE overlong packet and every
               later packet plays late; the stream start, the duration and a raw-PCM decode all miss it
  cuts         the delivered scene-cut list vs the EDL joins: extras are a take's own cut, motion, or a LEAK — named
  leaks        every hero event's [in,out] against ITS TAKE's own scene cuts (a window crossing one = rogue frames) — except
               the cuts the event DECLARES in accepted_cuts (composed inside one generation and kept), printed as INFO
  card         the last frame of the deliverable vs the last frame of the card render (NCC ≥ 0.9): the right card shipped
  placement    every VO line by envelope NCC (spot-audio-assembly/qc_vo_placement.py), < 15 ms
  FORMAT rows  frame = the EDL canvas (1080 on the short side) · H.264 High yuv420p · BT.709 primaries + transfer + MATRIX
               (shipped finals carried an untagged matrix until 2026-09-10) · CFR at the EDL fps (r == avg) · faststart
               (moov before mdat) · AAC 48 kHz stereo
  black/frozen blackdetect ≥ 0.1 s anywhere but a trailing fade or inside what an event's accepted_black declares (INFO —
               "<why>" for the whole event: a title, a kinetic-type VO, an end card on black; {"why": …, "src": [[a, b], …]}
               or "tl" windows for a source's own dip inside a moving event, so the rest of it stays checked); freezedetect ≥ qc.max_still_s (--max-still-s; 0.5 s by
               default) inside the footage span, the longest run printed — the card holds by design, and a designed hold
               inside the footage is declared on its event as accepted_still: "<why>" (the whole event) or
               {"why": …, "src": [[a, b], …]} in the take's own seconds / "tl": [[a, b], …] on the timeline (only those
               windows — a source's own still shot, while the rest of the event stays checked) and prints as INFO. Its floor is
               printed beside it: freezedetect's −60 dB tolerance is 0.26 code values, and on grain from a decoded σ of
               0.66 a frozen shot never got under it — over the floor the row is BLIND (a WARN line; read held shots by eye).
               The floor is the quietest still frame pair, so it misses two cases: a duplicate frame after the grain reads 0
               and hides the grain, and grain on some shots only is listed, not flagged. qc.grain_after: true (the finish
               lays grain over the picture) prints the row BLIND outright, without the floor read
  geometry     INFO: every hero take probed for SAR and rotation — a source whose display shape differs from its storage
               shape is listed (normalise before any crop: video-production/scripts/probe_sources.py); the eye check is a
               delivered frame beside the source's display frame at 1:1
  near-black   EVERY event's window sampled at three points (10 / 50 / 90 %): a window whose samples all read under
               --black-luma (16/255) FAILS unless the event declares `accepted_black: true` — a 10-bit source once rendered
               black through a grade while every other row passed (2026-09-15)
  vs previous  with --prev <the previous version's deliverable>: every footage event's middle frame against the same frame of
               the previous version — mean |dY| (regraded or not), phase correlation of the luma (moved: a crop, scale or warp),
               and the frame alignment m-1/m/m+1 (retimed) — as INFO per event; --prev-expect turns it into a verdict:
               `finish` = every footage event regraded, none moved, none retimed (a finish changes the look and nothing else —
               it caught four aerial shots one frame late, 2026-09-26); `changed:<id,…>` = each named event differs from the
               previous version (a changed crop reached the picture — a builder cache keyed by event id once shipped the stale
               render and every other row passed); an event whose middle frame reads `same` is read again
               at four frames near its two edges, because a change confined to a hold, a fade or a trim at an edge never
               reaches the middle (a tail hold over a source dissolve read 'unchanged — a stale cache?')
  contract     INFO: the colour range tag, the keyframe spacing and the edit lists — the platform-contract encode wants `tv`, a
               closed 2 s GOP and no edit lists (look-library GUIDE § 7)
  decoded      (decoded_checks.py) frame 0's median RGB within 2 code values of qc.frame0_bg (a limited-range master read as full
               lifts black to 16) · the Y code values against the range tag (WARN) · with qc.loop the last→first seam · frame 0
               as the platform thumbnail: not near-black, or the poster_at frame baked in (qc.poster: "none" declares it) · every
               audio.sfx cue found in the mix at its time by correlation · with qc.beat_data every on_beat cut within 3 frames
  motion       WARN lines (decoded_checks.py): one-frame pops (qc.accepted_flashes set aside) · one-frame steps off every
               frame the EDL changes on purpose (the joins, accepted_cuts, every caption's on and off, qc.accepted_flashes —
               a worded card declares its own word lines in accepted_cuts) · and the flash rows (decoded_checks.flash_rows:
               WCAG 2.2 flashes paired at the SAME place, a flash counted when the places flashing on one frame cover 25 % of
               the area) — two judgement rows on the WHOLE frame: over 3 flashes in any one second FAILS, and 2–3 a second
               held for 4 s of any 5 s FAILS (EA IRIS's extended failure, counted in flashes); WARN lines: IRIS's warning
               at 2 a second, the phone 10° field over 3 (the W3C window printed as INFO), red flashes over 3 in the whole
               frame or the phone field. qc.accepted_flash_rate: [{"from": s, "to": s, "note": "<why>"}] declares a
               deliberate strobe — its flashes are set aside from the whole-frame rows and print as INFO with the reason on
               every run
  edge frames  (decoded_checks.edge_frames, on the same frames): a change inside the first or last 7 frames of a footage event
               — the join itself and every declared edge set aside — over 10 levels, 4 × the event's median and 3 × the change
               beside it (an isolated spike; a pan is a run): a neighbouring shot, a card or a black frame at the cut. A judgement row under qc.native_programme (supplied clips cut by the
               builder, where it was measured), a WARN line elsewhere; accepted_edge_frames {head|tail: why} on the event
               declares a meant change (printed, never failed)
  phone band   INFO, with --phone-ref <real phone clips>: the delivered file's phone-texture band (phone_texture_probe.py —
               dead-flat 8×8 share, noise floor, median block sd) against the RANGE over every reference frame; a
               creator-style spot's read, never a failure — the operator judges the phone render beside the clean one
Every row carries a KIND: `format` rows are mechanically fixable — the agent fixes them alone (a re-mux with
`-bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1`, a faststart re-mux, a re-encode
at the right frame); `judgement` rows change the content (duration, loudness, cuts, black frames) and go to the operator.
Exit 1 on any FAIL; the summary names the failures by kind.

  qc_deliverable.py --root <project> --edl edit/<SPOT>-EDL.json --deliv deliver/<file>.mp4 [--placement <qc_vo_placement.py>] [--no-card] [--tp-ceiling] [--max-still-s]
                    [--prev deliver/<previous version>.mp4 [--prev-expect finish|changed:<id,…>]]
  qc_deliverable.py --selftest        # near-black: a black event FAILS, a declared one passes · vs previous: regraded / moved / retimed read back
"""
import argparse, glob, json, os, re, subprocess, sys
import numpy as np

SK = os.path.expanduser('~/.claude/skills')


def sh(c): return subprocess.run(c, capture_output=True, text=True)


def mean_luma(p, t):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', p, '-frames:v', '1', '-vf', 'scale=32:32,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return float(np.frombuffer(raw[-1024:], np.uint8).mean()) if len(raw) >= 1024 else None


def near_black_events(D, events, thr=16.0):
    """Every event's window sampled at 10 / 50 / 90 %: returns [(id, [lumas])] for windows whose samples ALL read under thr and
    that do not declare accepted_black. Three probes per event keep it cheap; a real black hole never passes three."""
    bad = []
    for x in events:
        t0 = float(x['tl'][0]); t1 = float(x['tl'][1]) if len(x.get('tl', [])) > 1 else t0 + float(x.get('out', 0)) - float(x.get('in', 0))
        if t1 - t0 <= 0: continue
        ls = [mean_luma(D, t0 + (t1 - t0) * f) for f in (0.1, 0.5, 0.9)]; ls = [l for l in ls if l is not None]
        whole = x.get('accepted_black') and not isinstance(x.get('accepted_black'), dict)   # a window form never excuses a whole black event
        if ls and max(ls) < thr and not whole: bad.append((x.get('id', '?'), [round(l, 1) for l in ls]))
    return bad


def luma_at(p, t, W=None, H=None):
    vf = (f'scale={W}:{H},' if W else '') + 'format=gray16le'
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.4f}', '-i', p, '-frames:v', '1', '-vf', vf, '-f', 'rawvideo', '-'], capture_output=True).stdout
    if not W:
        pr = json.loads(sh(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', p]).stdout)['streams'][0]; W, H = pr['width'], pr['height']
    return np.frombuffer(raw, np.uint16).reshape(H, W).astype(np.float64) / 65535 if len(raw) == W * H * 2 else None



def _covered(a0, a1, wins, tol=0.05):
    """True when [a0, a1] lies inside the union of the windows (each widened by tol): a run that crosses two adjacent declared
    events is still declared."""
    t = a0
    for w0, w1 in sorted(wins):
        if w0 - tol <= t <= w1 + tol: t = max(t, w1 + tol)
        if t >= a1: return True
    return t >= a1


def still_windows(x, key='accepted_still'):
    """The timeline windows an event's accepted_still (or accepted_black) declares: a string or True = the whole event; a
    dict = only its "src" windows (the take's own seconds, mapped through the event's in-point) and its "tl" windows."""
    v = x.get(key); tl = x.get('tl', [])
    if not v or len(tl) < 2: return []
    t0, t1 = float(tl[0]), float(tl[1])
    if not isinstance(v, dict): return [(t0, t1)]
    i0 = float(x.get('in', 0.0))
    out = [(max(t0, t0 + float(s0) - i0), min(t1, t0 + float(s1) - i0)) for s0, s1 in v.get('src', [])]
    out += [(max(t0, float(a_)), min(t1, float(b_))) for a_, b_ in v.get('tl', [])]
    return [(a_, b_) for a_, b_ in out if b_ > a_]


def edge_dy(D, P, x, fps):
    """The largest mean |dY| (0–255) between D and P over two frames in from each edge of the event (1 and 3 after its first
    frame, 4 and 2 before its last): a change confined to an edge — a tail hold, a fade, a trim — that the middle frame never
    sees. None when nothing could be read."""
    k0, k1 = round(float(x['tl'][0]) * fps), round(float(x['tl'][1]) * fps); best = None
    for k in sorted({k0 + 1, k0 + 3, k1 - 4, k1 - 2}):
        if not k0 <= k < k1: continue
        a = luma_at(D, (k + 0.5) / fps)
        if a is None: continue
        b = luma_at(P, (k + 0.5) / fps, a.shape[1], a.shape[0])
        if b is None: continue
        dy = float(np.mean(np.abs(a - b)) * 255); best = dy if best is None else max(best, dy)
    return best


def _shift(x, y):
    F = np.fft.fft2(x - x.mean()) * np.conj(np.fft.fft2(y - y.mean())); F /= np.abs(F) + 1e-9
    c = np.abs(np.fft.ifft2(F)); iy, ix = np.unravel_index(np.argmax(c), c.shape)
    return (int(iy if iy < c.shape[0] // 2 else iy - c.shape[0]), int(ix if ix < c.shape[1] // 2 else ix - c.shape[1]))


def prev_compare(D, P, events, fps):
    """Each footage event's middle frame of D against the same timeline frame of P and its two neighbours: (id, mean |dY| /255,
    the phase shift at the same frame, the frame offset or None). A grade changes dY and nothing else; a one-frame slip matches a
    NEIGHBOUR best in structure (gradient NCC, blind to a grade) and at a (0, 0) phase shift; a crop, scale or warp moves the
    phase peak at every one of the three."""
    rows = []
    g = lambda z: np.hypot(*np.gradient(z))
    ncc = lambda x, y: float(((x - x.mean()) * (y - y.mean())).sum() / (np.sqrt(((x - x.mean()) ** 2).sum() * ((y - y.mean()) ** 2).sum()) + 1e-12))
    for x in events:
        if x.get('role') == 'endcard' or x.get('source') == 'designed' or len(x.get('tl', [])) < 2: continue
        k0, k1 = round(float(x['tl'][0]) * fps), round(float(x['tl'][1]) * fps); m = (k0 + k1) // 2
        a = luma_at(D, (m + 0.5) / fps)
        if a is None: continue
        H, W = a.shape; b = {d: luma_at(P, (m + d + 0.5) / fps, W, H) for d in (-1, 0, 1)}
        if b[0] is None: rows.append((x.get('id', '?'), None, None, None)); continue
        ga = g(a); best = max((d for d in (-1, 0, 1) if b[d] is not None), key=lambda d: ncc(ga, g(b[d])))
        sh0 = _shift(a, b[0]); off = best if best and _shift(a, b[best]) == (0, 0) else (0 if sh0 == (0, 0) else None)
        rows.append((x.get('id', '?'), float(np.mean(np.abs(a - b[0])) * 255), sh0, off))
    return rows


def _box(z, r=2):
    c = np.cumsum(np.cumsum(np.pad(z, r + 1, mode='edge'), 0), 1); k = 2 * r + 1
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k])[:z.shape[0], :z.shape[1]] / k / k


def frames_at(p, t, n, W, H):
    """n consecutive luma frames from t, at W×H (lanczos), 0–255 floats; None when the file gave fewer than two."""
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.4f}', '-i', p, '-frames:v', str(n), '-vf', f'scale={W}:{H}:flags=lanczos,format=gray16le',
                          '-f', 'rawvideo', '-'], capture_output=True).stdout
    k = len(raw) // (W * H * 2)
    return np.frombuffer(raw[:k * W * H * 2], np.uint16).reshape(k, H, W).astype(np.float64) / 257 if k >= 2 else None


def _tex(f):
    """(plain, high-pass) moving texture: the mean |change| between consecutive frames, and the same after a 5×5 box blur of
    each change is subtracted — grain lives in the second; a moving edge or a pan inflates the first."""
    d = np.diff(f, axis=0)
    return float(np.mean(np.abs(d))), float(np.mean([np.mean(np.abs(x - _box(x))) for x in d]))


def grain_read(D, M, events, fps, W, H, n=7, motion=2.5, floor=0.1):
    """Per footage event, the moving texture the DELIVERED file keeps against the master it was encoded from, at the same n
    frames from the event's middle, both at the delivered raster: (id, master high-pass, plain/high-pass, kept or None).
    kept is None when the event is motion-dominated (plain/high-pass over `motion`: a moving picture hides the grain in the
    read) or has no texture to keep (master high-pass under `floor`). Measured on one film (a Dehancer 16 mm
    grain): CRF 17 -tune film kept 47–100 % per event, CRF 12 -tune grain 74–107 %; the grain-free flats of the same shots
    through CRF 17 film kept 100–106 %."""
    rows = []
    for x in events:
        if x.get('role') == 'endcard' or x.get('source') == 'designed' or len(x.get('tl', [])) < 2: continue
        k0, k1 = round(float(x['tl'][0]) * fps), round(float(x['tl'][1]) * fps)
        if k1 - k0 < n: continue
        t = ((k0 + k1) // 2 - n // 2 + 0.25) / fps
        a, b = frames_at(M, t, n, W, H), frames_at(D, t, n, W, H)
        if a is None or b is None or len(a) != len(b): rows.append((x.get('id', '?'), None, None, None)); continue
        mp, mh = _tex(a); dh = _tex(b)[1]
        ratio = mp / mh if mh > 0 else None
        kept = dh / mh if mh >= floor and ratio is not None and ratio <= motion else None
        rows.append((x.get('id', '?'), mh, ratio, kept))
    return rows


def find_master(D, e, mezz='edit/mezz'):
    """The master finish_spot.py encoded D from: edit/mezz/<spot>-master-<W>x<H><tag>.mov, the tag read off the deliverable's
    name (deliver/<deliver_base><tag>.mp4). None when the name does not carry it (a renamed file) or no single master matches."""
    spot = e.get('spot', 'SPOT'); base = os.path.splitext(os.path.basename(D))[0]; db = e.get('deliver_base', spot)
    if not base.startswith(db): return None
    tag = base[len(db):]; pat = re.compile(rf'{re.escape(spot)}-master-\d+x\d+{re.escape(tag)}\.mov$')
    hits = [p for p in glob.glob(os.path.join(mezz, f'{spot}-master-*.mov')) if pat.search(os.path.basename(p))]
    return hits[0] if len(hits) == 1 else None


def classify(row):
    id_, dy, sh_, off = row
    if dy is None: return 'unreadable'
    return 'moved' if off is None else 'retimed' if off else 'regraded' if dy > 1.0 else 'same'


def matrix_provenance(D, e, mezz='edit/mezz'):
    """(finished, detail) for the colour-matrix row: a deliverable finish_spot.py wrote has a record in edit/mezz/*.finish.json
    naming its sha256 — its conversions are the ones matrix_check.py --finish-e2e covers. Any other render (a project's own
    builder) owes one matrix_check card run through its exact decode and encode before its first delivery, recorded in the EDL
    as qc.matrix_check (measured 2026-10-23: a builder's BT.601 conversion under a bt709 tag passed every other row)."""
    import hashlib
    h = hashlib.sha256()
    with open(D, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    sha = h.hexdigest()
    for p in sorted(glob.glob(os.path.join(mezz, '*.finish.json'))):
        try: r = json.load(open(p))
        except (OSError, ValueError): continue
        if isinstance(r, dict) and r.get('sha256') == sha: return True, f"finished by {r.get('tool', 'finish_spot.py')} ({p})"
    rec = (e.get('qc') or {}).get('matrix_check')
    if rec: return True, f"not a finish_spot.py render; card run recorded in qc.matrix_check: {rec}"
    return False, ("not a finish_spot.py render (no edit/mezz/*.finish.json names this file) — a matrix_check card run through "
                   "this render's exact decode and encode is OWED before its first delivery (QC.md § builder renders); "
                   "record its result as qc.matrix_check in the EDL; a finish_spot.py delivery made before 2026-10-25, or delivered "
                   "from a master that carries no record, has none — re-run the finish from its cut stage (--stage all)")


def selftest():
    import tempfile
    d = tempfile.mkdtemp(); clip = os.path.join(d, 'clip.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=gray:s=64x64:d=2:r=24', '-f', 'lavfi', '-i', 'color=c=black:s=64x64:d=2:r=24',
                    '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]', '-pix_fmt', 'yuv420p', clip], check=True)
    ev = [{'id': 'a', 'tl': [0.0, 2.0]}, {'id': 'b', 'tl': [2.0, 4.0]}]
    bad = near_black_events(clip, ev); ok1 = [b[0] for b in bad] == ['b']
    ev[1]['accepted_black'] = True; ok2 = near_black_events(clip, ev) == []
    print(f"SELFTEST {'PASS' if ok1 and ok2 else 'FAIL'}: black event flagged={ok1} (found {bad}), declared event passes={ok2}")
    base = os.path.join(d, 'prev.mp4')   # a moving picture; four "new versions" of it, one per verdict
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=192x320:d=2:r=24', '-pix_fmt', 'yuv420p', '-crf', '12', base], check=True)
    vfs = {'same': 'null', 'regraded': 'eq=contrast=1.2:brightness=0.04', 'moved': 'crop=192:316:0:4,pad=192:320:0:0',
           'retimed': 'trim=start_frame=1,setpts=PTS-STARTPTS,tpad=stop=1:stop_mode=clone'}
    got = {}
    for k, vf in vfs.items():
        o = os.path.join(d, f'{k}.mp4'); subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', base, '-vf', vf, '-pix_fmt', 'yuv420p', '-crf', '12', o], check=True)
        got[k] = classify(prev_compare(o, base, [{'id': k, 'tl': [0.0, 2.0]}], 24)[0])
    ok3 = all(got[k] == k for k in vfs)
    print(f"SELFTEST {'PASS' if ok3 else 'FAIL'}: vs previous — {got} (each must read as its own name)")
    tail = os.path.join(d, 'tail.mp4')   # the last 6 frames held: the middle reads same, the edge read must see it
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', base, '-vf', 'trim=end_frame=42,setpts=PTS-STARTPTS,tpad=stop=6:stop_mode=clone', '-pix_fmt', 'yuv420p', '-crf', '12', tail], check=True)
    ev2 = {'id': 't', 'tl': [0.0, 2.0]}; mid = classify(prev_compare(tail, base, [ev2], 24)[0]); edy = edge_dy(tail, base, ev2, 24)
    ok4 = mid == 'same' and edy is not None and edy > 1.0
    print(f"SELFTEST {'PASS' if ok4 else 'FAIL'}: an edge-only change — middle reads {mid}, edge dY {edy if edy is None else round(edy, 1)} (want same and > 1)")
    w = still_windows({'tl': [10.0, 20.0], 'in': 100.0, 'accepted_still': {'why': 'x', 'src': [[102.0, 104.0]]}})
    ok5 = (w == [(12.0, 14.0)] and still_windows({'tl': [1.0, 2.0], 'accepted_still': 'card'}) == [(1.0, 2.0)]
           and _covered(1.0, 3.0, [(0.5, 2.0), (2.0, 3.5)]) and not _covered(1.0, 3.0, [(0.5, 1.5), (2.5, 3.5)]))
    print(f"SELFTEST {'PASS' if ok5 else 'FAIL'}: accepted_still windows {w} (want [(12.0, 14.0)]) and the black-run coverage of adjacent declared events")
    wb = still_windows({'tl': [10.0, 20.0], 'in': 100.0, 'accepted_black': {'why': 'dip', 'src': [[103.0, 103.2]]}}, 'accepted_black')
    ev[1]['accepted_black'] = {'why': 'a window only', 'tl': [[2.0, 2.1]]}; nb6 = [b[0] for b in near_black_events(clip, ev)]
    ok6 = [(round(x, 6), round(y, 6)) for x, y in wb] == [(13.0, 13.2)] and nb6 == ['b'] and not _covered(12.5, 13.1, wb)
    print(f"SELFTEST {'PASS' if ok6 else 'FAIL'}: accepted_black windows {wb} (want [(13.0, 13.2)]); a window form still fails a whole black event ({nb6})")
    mz = os.path.join(d, 'mezz'); os.makedirs(mz)
    r1 = matrix_provenance(clip, {}, mz)                                                          # no record, no declaration: owed
    r2 = matrix_provenance(clip, {'qc': {'matrix_check': 'card max err 1 (2026-10-25)'}}, mz)   # a builder render, card run recorded
    import hashlib; json.dump({'tool': 'finish_spot.py', 'sha256': hashlib.sha256(open(clip, 'rb').read()).hexdigest()}, open(os.path.join(mz, 'clip.mp4.finish.json'), 'w'))
    open(os.path.join(mz, 'broken.finish.json'), 'w').write('{')
    r3 = matrix_provenance(clip, {}, mz); r4 = matrix_provenance(base, {}, mz)                 # the record names clip, not base
    ok7 = not r1[0] and 'OWED' in r1[1] and r2[0] and 'qc.matrix_check' in r2[1] and r3[0] and 'finish_spot' in r3[1] and not r4[0]
    print(f"SELFTEST {'PASS' if ok7 else 'FAIL'}: colour-matrix provenance — owed {not r1[0]}, declared {r2[0]}, finish_spot record {r3[0]}, another file {not r4[0]}")
    gm = os.path.join(d, 'grain-master.mov')   # a static gradient under moving noise (the grain); two deliverables at half size
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'gradients=s=384x640:d=1:r=24:speed=0.00001', '-vf', 'noise=alls=14:allf=t,format=yuv422p10le',
                    '-c:v', 'prores_ks', '-profile:v', '3', gm], check=True)
    kd = {}
    for k, vf in (('kept', 'scale=192:320:flags=lanczos'), ('erased', 'scale=192:320:flags=lanczos,hqdn3d=12:12:24:24')):
        o = os.path.join(d, f'grain-{k}.mp4'); subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', gm, '-vf', vf + ',format=yuv420p', '-c:v', 'libx264', '-crf', '0', o], check=True)
        kd[k] = grain_read(o, gm, [{'id': k, 'tl': [0.0, 1.0]}], 24, 192, 320)[0][3]
    clean = os.path.join(d, 'grain-clean.mov')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'gradients=s=384x640:d=1:r=24:speed=0.00001', '-vf', 'format=yuv422p10le', '-c:v', 'prores_ks', '-profile:v', '3', clean], check=True)
    kc = grain_read(clean, clean, [{'id': 'c', 'tl': [0.0, 1.0]}], 24, 192, 320)[0][3]
    mz2 = os.path.join(d, 'mz2'); os.makedirs(mz2); open(os.path.join(mz2, 'SP-master-2160x3840-v0.2g.mov'), 'w').close(); open(os.path.join(mz2, 'SP-master-2160x3840-v0.2.mov'), 'w').close()
    fm = (find_master('deliver/sp-v0.2g.mp4', {'spot': 'SP', 'deliver_base': 'sp'}, mz2), find_master('deliver/renamed.mp4', {'spot': 'SP', 'deliver_base': 'sp'}, mz2))
    ok8 = (kd['kept'] is not None and kd['kept'] > 0.9 and kd['erased'] is not None and kd['erased'] < 0.5 and kc is None
           and fm[0] and fm[0].endswith('SP-master-2160x3840-v0.2g.mov') and fm[1] is None)
    print(f"SELFTEST {'PASS' if ok8 else 'FAIL'}: grain kept — a lossless encode {kd['kept'] if kd['kept'] is None else round(kd['kept'], 2)} (want > 0.9), "
          f"a denoised one {kd['erased'] if kd['erased'] is None else round(kd['erased'], 2)} (want < 0.5), a clean master {kc} (want None: no texture); "
          f"the master found by tag {fm[0] is not None and fm[0].endswith('v0.2g.mov')}, none for a renamed file {fm[1] is None}")
    sys.exit(0 if ok1 and ok2 and ok3 and ok4 and ok5 and ok6 and ok7 and ok8 else 1)


def last_frame_thumb(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-sseof', '-0.2', '-i', p, '-frames:v', '1', '-vf', 'scale=96:170,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(raw[-96 * 170:], np.uint8).astype(np.float32) if len(raw) >= 96 * 170 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl'); ap.add_argument('--deliv')
    ap.add_argument('--placement', default=f'{SK}/spot-audio-assembly/scripts/qc_vo_placement.py'); ap.add_argument('--no-card', action='store_true')
    ap.add_argument('--edge-audit', default=f'{SK}/video-edit-edl/scripts/edge_audit.py', help='the cut-edge read of the delivered joins (no word bitten)')
    ap.add_argument('--tp-ceiling', type=float, default=None, help='the delivered true-peak bar (the platform ceiling); default = the EDL loudnorm.TP_ceiling, else -1.0 — the EDL TP is the master target under it')
    ap.add_argument('--max-still-s', type=float, default=None, help='the longest still run allowed inside the footage span; default = the EDL qc.max_still_s, else 0.5')
    ap.add_argument('--black-luma', type=float, default=16.0, help='an event whose three sampled frames all read under this mean luma (0–255) fails unless it declares accepted_black')
    ap.add_argument('--phone-ref', nargs='*', default=[], help="the project's real phone clips: prints the delivered file's phone-texture band against theirs as INFO (a creator-style spot)")
    ap.add_argument('--prev', default=None, help="the previous version's deliverable: every footage event's middle frame compared (regraded / moved / retimed), INFO")
    ap.add_argument('--prev-expect', default=None, help="finish = every footage event regraded, none moved or retimed; changed:<id,…> = those events differ from --prev")
    ap.add_argument('--master', default=None, help="the master this file was encoded from (default: finish_spot.py's edit/mezz/<spot>-master-<W>x<H><tag>.mov, the tag read off the deliverable's name): the grain-kept read per footage event")
    ap.add_argument('--grain-warn', type=float, default=0.70, help='a WARN line when a readable event keeps less than this share of the master\'s moving texture (a lead from one film)')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: selftest()
    if not a.edl or not a.deliv: ap.error('--edl and --deliv are required (or --selftest)')
    os.chdir(a.root); e = json.load(open(a.edl, encoding='utf-8')); D = a.deliv; fails = []
    if not os.path.exists(D): sys.exit(f'QC-DELIVERABLE FAIL (missing) — no file at {D}')

    def verdict(ok, label, detail, kind='judgement'): (None if ok else fails.append((label, kind))); print(f"{'PASS' if ok else 'FAIL'} [{kind}] {label}: {detail}")

    # ---- format rows (mechanically fixable) ----
    pr = json.loads(sh(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,codec_name,profile,pix_fmt,width,height,r_frame_rate,avg_frame_rate,color_primaries,color_transfer,color_space,sample_rate,channels', '-of', 'json', D]).stdout or '{}').get('streams', [])
    vs = next((x for x in pr if x.get('codec_type') == 'video'), {}); au = next((x for x in pr if x.get('codec_type') == 'audio'), {})
    cw, ch = (e.get('canvas') or [1080, 1920])[:2]; efps = float(e.get('fps', 24))
    verdict((vs.get('width'), vs.get('height')) == (cw, ch) and min(cw, ch) == 1080, 'frame', f"{vs.get('width')}x{vs.get('height')} vs the EDL canvas {cw}x{ch} (1080 on the short side — 1080p masters only)", 'format')
    verdict(vs.get('codec_name') == 'h264' and vs.get('pix_fmt') == 'yuv420p', 'codec', f"{vs.get('codec_name')} {vs.get('profile')} {vs.get('pix_fmt')} (want h264 High yuv420p)", 'format')
    tags = (vs.get('color_primaries'), vs.get('color_transfer'), vs.get('color_space'))
    verdict(tags == ('bt709', 'bt709', 'bt709'), 'colour tags', f"primaries/transfer/matrix = {tags} (want bt709 ×3; fix without a re-encode: -c copy -bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1)", 'format')

    def fr(x):
        try: n, d_ = x.split('/'); return float(n) / float(d_)
        except Exception: return 0.0
    verdict(abs(fr(vs.get('r_frame_rate', '0/1')) - efps) < 0.01 and vs.get('r_frame_rate') == vs.get('avg_frame_rate'), 'fps / CFR', f"r {vs.get('r_frame_rate')} avg {vs.get('avg_frame_rate')} vs the EDL {efps:g} (r != avg = variable frame rate)", 'format')
    head = open(D, 'rb').read(2_000_000); mo, md = head.find(b'moov'), head.find(b'mdat')
    verdict(0 < mo < md if md >= 0 else mo > 0, 'faststart', f"moov at {mo}, mdat at {md} (moov must come first; fix: -c copy -movflags +faststart)", 'format')
    verdict(au.get('codec_name') == 'aac' and str(au.get('sample_rate')) == '48000' and au.get('channels') == 2, 'audio format', f"{au.get('codec_name')} {au.get('sample_rate')} Hz {au.get('channels')} ch (want aac 48000 2)", 'format')

    dur = float(sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', D]).stdout or 0)
    verdict(abs(dur - e['runtime_s']) < 0.05, 'duration', f"{dur:.3f} s vs EDL runtime {e['runtime_s']:.3f}")
    lo = sh(['ffmpeg', '-v', 'info', '-nostats', '-i', D, '-af', 'ebur128=peak=true', '-f', 'null', '-']).stderr
    I = re.findall(r'\n\s+I:\s+(-?[\d.]+|-inf) LUFS', lo); LRA = re.findall(r'LRA:\s+([\d.]+) LU', lo); TP = re.findall(r'Peak:\s+(-?[\d.]+|-inf) dBFS', lo)
    li = float(I[-1]) if I and I[-1] != '-inf' else float('-inf'); tp = float(TP[-1]) if TP and TP[-1] != '-inf' else float('-inf')
    ln = e.get('audio', {}).get('loudnorm', {'I': -14, 'TP': -1})
    verdict(np.isfinite(li) and abs(li - ln['I']) <= 1.0, 'loudness', f"I {li} LUFS (target {ln['I']}) · LRA {LRA[-1] if LRA else '?'}" + ('' if np.isfinite(li) else ' — SILENT TRACK'))
    tpc = a.tp_ceiling if a.tp_ceiling is not None else float(ln.get('TP_ceiling', -1.0))   # the platform's bar for the DELIVERED file
    over = tp - ln['TP']   # the EDL's TP is the master's limiter ceiling; AAC overshoots the limited peaks by 0.4–1.0 dB, so the delivered bar is the platform ceiling
    verdict(np.isfinite(tp) and tp <= tpc + 0.05, 'true peak', f"{tp} dBTP vs the platform ceiling {tpc} ({'EDL loudnorm.TP_ceiling' if a.tp_ceiling is None and 'TP_ceiling' in ln else '--tp-ceiling' if a.tp_ceiling is not None else 'the default'}; EDL master target {ln['TP']}, {over:+.1f} dB over it" + ('' if over <= 1.0 else ' — more than the AAC overshoot: check the limiter order') + ')')
    ck = json.loads(sh([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aac_packet_clock.py'), '--json', D]).stdout or '{"ok": false, "reason": "the scan did not run"}')   # fail closed
    if ck.get('ok') is None: print(f"INFO audio packet clock: not checked — {ck.get('reason')} (the audio format row carries the verdict)")
    else: verdict(ck['ok'], 'audio packet clock', ck['reason'] + ('' if ck['ok'] else ' — fix upstream of the encoder, never with a constant shift: the pair in aac_packet_clock.py\'s header'))
    cuts = [round(float(x), 3) for x in re.findall(r'pts_time:([\d.]+)', sh(['ffmpeg', '-v', 'info', '-nostats', '-i', D, '-vf', "select='gt(scene,0.25)',showinfo", '-f', 'null', '-']).stderr)]
    joins = [round(x['tl'][0], 3) for x in e['events'][1:]]
    tol = max(0.05, 1.5 / efps)   # a scene-detector time against a declared take time: 1.5 frames
    acc_tl = [x['tl'][0] + float(c) - x['in'] for x in e['events'] for c in x.get('accepted_cuts', [])]
    extra = [c for c in cuts if not any(abs(c - j) < 0.03 for j in joins)]; missing = [j for j in joins if not any(abs(c - j) < 0.03 for c in cuts)]
    declared = [c for c in extra if any(abs(c - t) <= tol for t in acc_tl)]; extra = [c for c in extra if c not in declared]
    print(f"INFO cuts: delivered {cuts}\n      EDL joins {joins}\n      declared accepted cuts (composed inside a generation): {declared}\n      extra detections (a take's own cut, motion, or a LEAK — read each): {extra}\n      joins not detected (soft/jump joins are normal): {missing}")
    cache = {}

    def tcuts(t):
        if t not in cache: cache[t] = [round(float(x), 3) for x in re.findall(r'pts_time:([\d.]+)', sh(['ffmpeg', '-v', 'info', '-nostats', '-i', t, '-vf', "select='gt(scene,0.3)',showinfo", '-f', 'null', '-']).stderr)]
        return cache[t]

    leaks = []; kept = []
    for x in e['events']:
        if 'src' not in x or not os.path.exists(x['take']): continue
        acc = [float(c) for c in x.get('accepted_cuts', [])]
        inside = [c for c in tcuts(x['take']) if x['in'] + 0.03 < c < x['out'] - 0.03]
        kept += [f"{x['id']} {c}" for c in inside if any(abs(c - k) <= tol for k in acc)]
        bad = [c for c in inside if not any(abs(c - k) <= tol for k in acc)]
        if bad: leaks.append(f"{x['id']} {x['take']} in {x['in']:.3f} out {x['out']:.3f} crosses the take's cut at {bad}")
    if kept: print(f"INFO accepted cuts inside hero windows (declared on the event, not leaks): {kept}")
    verdict(not leaks, 'take-cut leaks', f"{len(leaks)} leak(s) over {sum(1 for x in e['events'] if 'src' in x)} hero events" + ''.join('\n      ' + l for l in leaks))
    # ---- source geometry (INFO: the QC cannot know the crop, but it can say which sources are not what their storage says) ----
    geo = []
    for t in sorted({x['take'] for x in e['events'] if 'src' in x and os.path.exists(x.get('take', ''))}):
        pr = sh(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=sample_aspect_ratio:stream_tags=rotate:stream_side_data=rotation', '-of', 'default=nw=1', t]).stdout
        sm = re.search(r'sample_aspect_ratio=(\S+)', pr); sar = sm.group(1) if sm else '1:1'
        rm = re.search(r'(?:rotation|TAG:rotate)=(-?[\d.]+)', pr); rot = (float(rm.group(1)) % 360) if rm else 0.0
        if sar not in ('1:1', 'N/A', '0:1') or rot: geo.append(f"{os.path.basename(t)} SAR {sar}" + (f" rotation {rot:g}" if rot else ''))
    print(f"INFO source geometry: {len(geo)} hero take(s) whose display shape differs from their storage shape" + (f" — normalise before any crop (video-production/scripts/probe_sources.py); check a delivered frame beside the source's display frame at 1:1: {geo}" if geo else ''))
    card = [x for x in e['events'] if x.get('role') == 'endcard']
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import decoded_checks as dc
    # ---- black and frozen frames (judgement: a content defect the operator sees) ----
    foot_end = float(card[0]['tl'][0]) if card else dur
    bl = sh(['ffmpeg', '-v', 'info', '-nostats', '-i', D, '-vf', 'blackdetect=d=0.1:pic_th=0.98', '-f', 'null', '-']).stderr
    blacks = [(float(s0), float(e0)) for s0, e0 in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', bl)]
    bwin = [w for x in e['events'] for w in still_windows(x, 'accepted_black')]   # whole events, or only their declared windows
    declared_black = [b for b in blacks if _covered(b[0], b[1], bwin)]   # a title, a kinetic-type VO, a card on black: declared on its event
    bad_black = [b for b in blacks if b[1] < dur - 0.3 and b not in declared_black]   # a trailing fade to black is a choice; a black run anywhere else is a hole
    if declared_black: print(f"INFO black runs inside events that declare accepted_black: {[(round(x, 2), round(y, 2)) for x, y in declared_black]}")
    verdict(not bad_black, 'black frames', f"{len(blacks)} black run(s) ≥ 0.1 s, {len(bad_black)} undeclared: {[(round(x, 2), round(y, 2)) for x, y in bad_black]}" + (' — trailing fade / declared runs only' if blacks and not bad_black else ''))
    mst = a.max_still_s if a.max_still_s is not None else float(e.get('qc', {}).get('max_still_s', 0.5))   # the project's threshold, from the EDL
    fz = sh(['ffmpeg', '-v', 'info', '-nostats', '-i', D, '-vf', f"trim=0:{foot_end:.3f},freezedetect=n=-60dB:d={mst:g}", '-f', 'null', '-']).stderr
    runs = []
    for m in re.finditer(r'freeze_(start|duration): ([\d.]+)', fz):   # start … duration pairs; a run still open at the trim end gets the remainder
        if m.group(1) == 'start': runs.append([float(m.group(2)), None])
        elif runs and runs[-1][1] is None: runs[-1][1] = float(m.group(2))
    runs = [(s0, d0 if d0 is not None else max(0.0, foot_end - s0)) for s0, d0 in runs]
    holds = [(h0, h1, isinstance(x.get('accepted_still'), dict)) for x in e['events'] for h0, h1 in still_windows(x)]
    # a whole-event hold declares the runs that START inside it; a window declares only the runs it covers
    declared_runs = [r for r in runs if any((_covered(r[0], r[0] + r[1], [(h0, h1)]) if win else h0 - 0.05 <= r[0] <= h1) for h0, h1, win in holds)]
    frozen = [r for r in runs if r not in declared_runs]; longest = max((d for _, d in runs), default=0.0)
    if declared_runs: print(f"INFO still runs inside declared holds (accepted_still on the event): {[(round(s0, 2), round(d0, 2)) for s0, d0 in declared_runs]}")
    nb = near_black_events(D, e['events'], a.black_luma)
    verdict(not nb, 'near-black events', f"{len(nb)} event window(s) read black at all three samples (< {a.black_luma:g}/255): {nb}" + (' — a source type the grade turns black? declare accepted_black only for a shot meant to be black' if nb else ''))
    src = '--max-still-s' if a.max_still_s is not None else ('the EDL qc.max_still_s' if 'max_still_s' in e.get('qc', {}) else 'the default')
    verdict(not frozen, 'frozen frames', f"{len(frozen)} still run(s) ≥ {mst:g} s inside the footage span 0–{foot_end:.2f} s at {[(round(s0, 2), round(d0, 2)) for s0, d0 in frozen]}; longest run {longest:.2f} s (threshold {mst:g} s from {src}; the end card is allowed to hold)")
    if (e.get('qc') or {}).get('grain_after'): fl_, tol_, det_ = None, dc.FREEZE_TOL, None   # the finish lays grain over every frame
    else: fl_, tol_, det_ = dc.freeze_floor(D, 0.0, foot_end)
    if det_ is None: print(f"WARN frozen frames BLIND: the EDL declares qc.grain_after (the finish lays grain over the picture), so a frozen shot never gets under freezedetect's {tol_:.2f} — read the held shots by eye")
    elif fl_ is None: print(f"INFO frozen-frame floor: not read — {det_}")
    elif fl_ > tol_: print(f"WARN frozen frames BLIND: {det_} — a frozen shot under this texture does not register; read the held shots by eye")
    else: print(f"INFO frozen-frame floor: {det_} — a frozen run registers")
    if card and not a.no_card:
        A, B = last_frame_thumb(D), last_frame_thumb(card[0]['take'])
        if A is None or B is None: verdict(False, 'end card', 'could not read a last frame')
        else:
            A -= A.mean(); B -= B.mean(); ncc = float((A * B).sum() / (np.sqrt((A * A).sum() * (B * B).sum()) + 1e-9))
            verdict(ncc >= 0.9, 'end card', f"last frame vs {os.path.basename(card[0]['take'])} NCC {ncc:.3f}")
    r = sh([sys.executable, os.path.expanduser(a.placement), '--root', '.', '--edl', a.edl, '--deliv', D]); out = r.stdout.strip()
    print('      ' + out.replace('\n', '\n      ')[-900:])
    if r.returncode == 0 and 'PLACEMENT N/A' in out: print('INFO VO placement: no placed VO lines in the EDL — nothing to place')
    else: verdict(r.returncode == 0 and 'PLACEMENT OK' in out, 'VO placement', 'see the lines above' if out else (r.stderr or '').strip()[-300:] or 'the placement script printed nothing')
    if os.path.exists(os.path.expanduser(a.edge_audit)):   # every join where a take's own sound plays: no word bitten after the fades, the gain and the limiter
        r = sh([sys.executable, os.path.expanduser(a.edge_audit), '--root', '.', '--edl', a.edl, '--deliv', D]); out = r.stdout.strip()
        shown = [l for l in out.splitlines() if not l.startswith('ok ')]
        print('      ' + '\n      '.join(shown)[-1500:])
        last = (out.splitlines() or ['no output'])[-1]
        if (e.get('qc') or {}).get('native_programme') or r.returncode == 0 or 'NOT READ' in last:   # the takes' own speech IS the programme, or the EDL never said whose sound plays: a judgement row
            verdict(r.returncode == 0, 'cut edges (no word bitten)', last + ('' if r.returncode == 0 else ' — declare qc.native_programme (true or false) or native_audio_vol in the EDL' if 'NOT READ' in last
                                                                            else ' — the take-edge gate (edge_audit.py on the EDL) names each fix'))
        else: print(f'WARN cut edges: {last} — earned native beds only: the read is of SOUND, not words; listen at each flagged join, declare a meant cut (a knock on its hit) in accepted_edges')
    else: print(f'INFO cut edges: not read — {a.edge_audit} not found')
    # ---- the platform contract (INFO): range tag, keyframe spacing, edit lists (look-library GUIDE § 7) ----
    rng = sh(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=color_range', '-of', 'csv=p=0', D]).stdout.strip()
    kf = [i for i, l in enumerate(sh(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'packet=flags', '-of', 'csv=p=0', D]).stdout.split()) if 'K' in l]
    gaps = sorted({b - a_ for a_, b in zip(kf, kf[1:])}); mv = open(D, 'rb').read(); mi = mv.find(b'moov'); elst = mv.count(b'elst', max(mi, 0))
    print(f"INFO contract: colour range {rng or 'untagged'} (want tv) · keyframes every {gaps[:4]}{'…' if len(gaps) > 4 else ''} frames (a closed 2 s GOP = [{2 * int(efps)}]) · edit lists {elst} (want 0)")
    # ---- the decoded picture and sound (decoded_checks.py): frame 0, range, loop seam, poster, sfx, beat cuts, motion ----
    q = e.get('qc', {}) or {}
    if q.get('frame0_bg'): ok, det = dc.frame0_bg(D, q['frame0_bg']); verdict(ok, 'frame 0 vs the background', det)
    ok, det = dc.range_read(D, rng); print(f"{'INFO' if ok else 'WARN'} range read: {det}")
    ok, det = matrix_provenance(D, e); print(f"INFO colour matrix: {det}")   # INFO either way: owed is a step to take, not a verdict on the file
    if q.get('loop'): ok, det = dc.loop_seam(D); verdict(ok, 'loop seam', det)
    ok, det = dc.poster(D, e.get('poster_at'), q.get('poster'), a.black_luma); verdict(ok, 'poster (frame 0)', det)
    if e.get('poster_at') is not None: ok, det = dc.poster_flash(D); print(f"{'INFO' if ok else 'WARN'} poster flash: {det}")   # WARN only: the chosen thumbnail is kept
    for name, ok, det in dc.sfx(D, '.', e.get('audio', {}).get('sfx', {})): verdict(ok, f'sfx {name} in the mix', det)
    if q.get('beat_data'): ok, det = dc.beat_cuts(e['events'], q['beat_data'], efps, '.'); verdict(ok, 'beat cuts', det)
    g, _, _ = dc.motion_frames(D, efps)   # pops and steps are WARN lines, the frames decide (HYPERFRAMES-CONTRACT § Silent traps); the flash rate is a judgement row
    if len(g) >= 3:
        edges = dc.declared_edges(e, efps, '.'); fl = {round(float(t) * efps) for t in q.get('accepted_flashes') or []}
        po, st = dc.pops(g, fl), dc.steps(g, set(edges)); on = [x for x in dc.steps(g) if x[0] in edges]
        print(f"{'WARN' if po else 'INFO'} pops: " + (dc._fmt(po, efps, 'pops') + ' — read each frame and its neighbours; a designed one goes in qc.accepted_flashes' if po else 'none'))
        print(f"{'WARN' if st else 'INFO'} steps: " + (dc._fmt(st, efps, 'steps') + ' — read each; a worded card declares its word lines in its event\'s accepted_cuts' if st else 'none off the declared edges')
              + f" · on declared edges (INFO): {len(on)} — {sorted({w.split(' ')[0] for x in on for w in edges[x[0]]})}")
        ef = dc.edge_frames(g, e, efps, edges); bad_ef = [x for x in ef if not x[5]]   # a stray frame INSIDE an event's first/last 7 frames
        for i, side, k, c, med, why in ef:
            print(f"      {'accepted' if why else 'STRAY   '} {i} {side} at {k / efps:.2f} s (frame {k}): change {c} vs the event median {med}" + (f' — {why}' if why else ''))
        det = f"{len(bad_ef)} undeclared at the first/last 7 frames of the footage events, {len(ef) - len(bad_ef)} declared (accepted_edge_frames)" + (
            ' — read each frame and its neighbours: a neighbouring shot, a card or a black frame at the cut is moved out by the in/out; a change the take makes on purpose is declared' if bad_ef else '')
        if q.get('native_programme') or not bad_ef: verdict(not bad_ef, 'stray frames at event edges', det)   # supplied footage cut by the builder: a judgement row
        else: print(f'WARN stray frames at event edges: {det} (a judgement row under qc.native_programme; the 10 / 4 × / 3 × thresholds are leads from one compilation)')
        wins, bad = dc.accepted_flash_windows(q)   # a deliberate strobe: time windows whose flashes the whole-frame rows set aside
        for b in bad: print(f"WARN qc.accepted_flash_rate: {b}")
        it, ffps, (fw, fh) = dc.flash_frames(D, efps)
        for lvl, label, det in dc.flash_rows(dc.flash_read(it, ffps, fw, fh), wins):   # PASS/FAIL = judgement rows; WARN/INFO lines
            if lvl in ('PASS', 'FAIL'): verdict(lvl == 'PASS', label, det)
            else: print(f"{lvl} {label}: {det}")
    # ---- against the previous version (INFO; a verdict with --prev-expect) ----
    if a.prev:
        rows = prev_compare(D, a.prev, e['events'], efps); cls = {r[0]: classify(r) for r in rows}
        print(f"INFO vs previous ({a.prev}): " + ' · '.join(f"{r[0]} {cls[r[0]]}" + (f" dY {r[1]:.1f}" if r[1] is not None else '') + (f" shift {r[2]}" if r[2] not in (None, (0, 0)) else '') + (f" off {r[3]:+d} frame" if r[3] else '') for r in rows))
        if a.prev_expect == 'finish':
            off = [f"{i} {c}" for i, c in cls.items() if c != 'regraded']
            verdict(not off, 'finish vs previous', f"{len(rows) - len(off)}/{len(rows)} footage events regraded with no move and no retime" + (f"; not: {off}" if off else ''))
        elif a.prev_expect and a.prev_expect.startswith('changed:'):
            want = [i for i in a.prev_expect.split(':', 1)[1].split(',') if i]; same = [i for i in want if cls.get(i, 'missing') in ('same', 'missing', 'unreadable')]
            byid = {x.get('id'): x for x in e['events'] if len(x.get('tl', [])) >= 2}; at_edge = []
            for i in list(same):   # the middle frame missed it: read the edges (a tail hold, a fade, a trim) — and a designed event, which the middle read skips
                edy = edge_dy(D, a.prev, byid[i], efps) if i in byid else None
                if edy is not None and edy > 1.0: same.remove(i); at_edge.append(f"{i} dY {edy:.1f}")
            if at_edge: print(f"INFO changed at an edge only (the middle frame reads the same): {at_edge}")
            verdict(not same, 'changes reached the picture', f"{len(want) - len(same)}/{len(want)} named events differ from the previous version" + (f"; unchanged at the middle and at both edges: {same} — a stale cache?" if same else ''))
    # ---- grain kept by the deliver encode (INFO rows; a WARN line under --grain-warn — a lead, calibrated on one film) ----
    M = a.master or find_master(D, e)
    if M and os.path.exists(M):
        gr = grain_read(D, M, e['events'], efps, int(vs.get('width') or cw), int(vs.get('height') or ch))
        fmt = lambda r: (f"{r[0]} {r[3]:.0%}" if r[3] is not None else f"{r[0]} " + ('unreadable' if r[1] is None else 'no texture' if r[1] < 0.1 else f"motion (plain/hp {r[2]:.1f}, not read)"))
        print(f"INFO grain kept vs the master ({M}; the moving texture at the same frames): " + ' · '.join(fmt(r) for r in gr))
        low = [f"{r[0]} {r[3]:.0%}" for r in gr if r[3] is not None and r[3] < a.grain_warn]
        if low: print(f"WARN grain: {low} kept under {a.grain_warn:.0%} of the master's moving texture — the deliver encode erased it; a look that carries grain "
                      "buys it in the EDL's deliver_encode (CRF 12 -tune grain kept 74–107 % where CRF 17 film kept 47–100 %, one film, 3.2x the bytes; EDL-CONTRACT.md); "
                      "the threshold is a lead from that film — compare the two encodes by eye before re-encoding")
    else: print(f"INFO grain kept: not read — {'no file at ' + M if M else 'no master found for this name (pass --master)'}")
    # ---- the phone-texture band (INFO, a creator-style spot: a comparison against the project's real phone clips, never a threshold) ----
    if a.phone_ref:
        pr_ = sh([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phone_texture_probe.py'), '--json', D] + a.phone_ref)
        try: rows = json.loads(pr_.stdout)
        except Exception: rows = []
        if len(rows) == 1 + len(a.phone_ref):
            dv, refs = rows[0], rows[1:]
            for k in ('dead_flat_pct', 'noise_floor', 'median_block_sd'):
                lo, hi = min(x[k + '_min'] for x in refs), max(x[k + '_max'] for x in refs)
                where = 'IN BAND' if lo <= dv[k] <= hi else ('BELOW (less texture than every reference frame)' if dv[k] < lo else 'ABOVE (more texture than every reference frame)')
                print(f"INFO phone band {k}: delivered {dv[k]} (frames {dv[k + '_min']}–{dv[k + '_max']}) vs real [{lo}, {hi}] → {where}")
            print("      the band is a matched-content comparison (video-finish § 5 the phone-native tier); the operator judges the phone render beside the clean one")
        else:
            print('INFO phone band: the probe could not read every clip — ' + (pr_.stderr or pr_.stdout).strip()[-300:])
    by = {k: [l for l, kk in fails if kk == k] for k in ('format', 'judgement')}
    summary = '; '.join(f"{k}: {', '.join(v)}" for k, v in by.items() if v)
    print(f"QC-DELIVERABLE {'FAIL (' + summary + ')' if fails else 'PASS'} — {D}" + ("\n      format rows: fix mechanically and re-run; judgement rows: the operator decides" if fails else ''))
    print('      visual: PENDING — these rows are measurements; say "container valid · measured rows pass · visual pending" until the frames themselves were read (STANDING-RULES: evidence is not looking)'); sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
