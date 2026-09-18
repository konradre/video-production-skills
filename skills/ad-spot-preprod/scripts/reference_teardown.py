#!/usr/bin/env python3
"""reference_teardown.py — the measured STRUCTURE of real reference videos (keep the bones, swap the world).

Per reference: every shot with its start, end and length (a cut = the frame's COARSE layout jumps against its neighbours
AND its histogram jumps or it decorrelates hard — motion moves detail, not the coarse layout), its FRAMING (the largest frontal face, found at the same place in two of three sampled frames, as a share
of the frame height, its centre skin-toned — ECU/CU/MCU/MS/WS, or none), its MOTION (global phase correlation between frames: static · drift · pan · handheld, with the numbers), its
luma and saturation; the audio's loudness; with --asr the words (faster-whisper, local, free) → the first spoken word, the
speech rate over the speech span, the words per shot. Across the references: shots per 10 s, the median and IQR shot
length, the first cut, the first word, the framing and motion mix. Then a BEAT GRID for --runtime: timestamped slots at
the references' rhythm, each with the framing and motion the references use at that point of their running time — the
skeleton our own beats are written into (one action per slot). Also one contact sheet per reference (first · middle ·
last frame of each shot, labelled) for the written read, which is the half no instrument does.

Every source is read in its DISPLAY geometry (the sample aspect applied first) and at its average rate as constant frame
rate. Limits: a dissolve reads as a cut at its middle or as none; a whip pan can read as a cut; a profile or a small face
reads "none"; the motion class is the frame's dominant motion, camera or subject — the sheet is read before a number is
trusted.

  reference_teardown.py --refs <a.mp4> <b.mp4> … --out <dir> [--runtime 30] [--fps 24] [--asr small.en] [--card 3.0]
  reference_teardown.py --selftest
Writes <dir>/teardown.json, <dir>/TEARDOWN.md and <dir>/<ref>-sheet.jpg; never overwrites an existing <dir>/teardown.json.
Sentinel TEARDOWN-END.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
import numpy as np

AN_W = 320                                                   # analysis width (display geometry)
FRAMING = [(0.40, 'ECU'), (0.25, 'CU'), (0.15, 'MCU'), (0.08, 'MS'), (0.0, 'WS')]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, check=True, **kw)


def probe(path):
    j = json.loads(run(['ffprobe', '-v', 'error', '-show_entries',
                        'stream=codec_type,width,height,sample_aspect_ratio,avg_frame_rate,r_frame_rate:format=duration',
                        '-of', 'json', path]).stdout)
    v = next(s for s in j['streams'] if s['codec_type'] == 'video')
    sar = v.get('sample_aspect_ratio', '1:1')
    sn, sd = (1, 1) if sar in ('0:1', 'N/A', None) else map(int, sar.split(':'))
    fr = v.get('avg_frame_rate') or v.get('r_frame_rate'); a, b = map(int, fr.split('/'))
    fps = a / b if b else 24.0
    if not 5 <= fps <= 120: a, b = map(int, v['r_frame_rate'].split('/')); fps = a / b
    dw, dh = round(int(v['width']) * sn / sd), int(v['height'])
    return dict(w=dw, h=dh, fps=fps, dur=float(j['format'].get('duration', 0)),
                audio=any(s['codec_type'] == 'audio' for s in j['streams']))


def frames(path, fps, h):
    """generator of gray analysis frames (display geometry, constant rate)"""
    vf = f"scale=trunc(iw*sar/2)*2:ih,setsar=1,fps={fps:.6f},scale={AN_W}:{h}:flags=area,format=gray"
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', vf, '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
    n = AN_W * h
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(h, AN_W)
    p.wait()


def measure(path, fps):
    import cv2
    m = probe(path); h = int(round(AN_W * m['h'] / m['w'] / 2)) * 2
    win = cv2.createHanningWindow((AN_W, h), cv2.CV_32F); prev = prevf = prevh = prevc = None
    mad, hl1, dx, dy, luma, resp, crs = [], [], [], [], [], [], []
    ch = max(2, int(round(32 * h / AN_W)))
    for f in frames(path, fps, h):
        ff = f.astype(np.float32); hist = np.histogram(f, bins=32, range=(0, 256))[0] / f.size
        co = cv2.resize(ff, (32, ch), interpolation=cv2.INTER_AREA)                # the frame's coarse layout
        if prev is None:
            mad.append(0.0); hl1.append(0.0); dx.append(0.0); dy.append(0.0); resp.append(1.0); crs.append(0.0)
        else:
            crs.append(float(np.abs(co - prevc).mean()))
            mad.append(float(np.abs(ff - prevf).mean())); hl1.append(float(np.abs(hist - prevh).sum()))
            (sx, sy), rp = cv2.phaseCorrelate(prevf.copy(), ff.copy(), win)     # copies: the window is applied in place
            dx.append(sx); dy.append(sy); resp.append(float(rp))
        luma.append(float(f.mean())); prev, prevf, prevh, prevc = f, ff, hist, co
    return m, h, np.array(mad), np.array(hl1), np.array(dx), np.array(dy), np.array(luma), np.array(resp), np.array(crs)


def detect_cuts(crs, hl1, resp, fps, ratio=2.5, crs_min=12.0, hist_min=0.25, resp_max=0.15, crs_strong=55.0):
    """a cut = the COARSE layout (a 32-px-wide thumbnail) jumps against its own neighbourhood AND either the luma histogram
    jumps or the picture decorrelates hard. Measured on two delivered spots with 24 known joins: at the joins coarse
    47.9-90.6 and histogram 0.36-1.93; inside shots coarse p99 30-31 and the false candidates' histogram 0.05-0.12 (a fast
    underside sweep, a leg entering the frame). Motion moves detail, not the coarse layout; a whip pan still can."""
    n = len(crs); w = max(3, int(round(0.5 * fps))); cuts = []
    for i in range(1, n):
        lo, hi = max(1, i - w), min(n, i + w + 1)
        nb = np.concatenate([crs[lo:i], crs[i + 1:hi]]); med = float(np.median(nb)) if len(nb) else 0.0
        hit = crs[i] >= max(crs_min, ratio * med) and (hl1[i] >= hist_min or (resp[i] < resp_max and crs[i] >= crs_strong))
        if hit and (not cuts or i - cuts[-1] >= max(3, int(round(0.12 * fps)))): cuts.append(i)
        elif hit and crs[i] > crs[cuts[-1]]: cuts[-1] = i                     # keep the stronger of two near hits
    return cuts


def motion_class(dx, dy, fps, width):
    v = np.stack([dx, dy], 1); sp = np.hypot(v[:, 0], v[:, 1])
    if len(v) < 2: return 'static', 0.0, 0.0, 0.0
    mean = v.mean(0); cons = float(np.hypot(*mean) / (sp.mean() + 1e-9)); wps = float(np.median(sp) * fps / width)
    jit = float(np.std(sp) * fps / width)
    if wps < 0.02: cls = 'static'
    elif cons >= 0.6: cls = 'pan' if wps >= 0.06 else 'drift'
    else: cls = 'handheld'
    return cls, round(wps, 3), round(cons, 2), round(jit, 3)


def grab(path, t, height):
    raw = run(['ffmpeg', '-v', 'error', '-ss', f'{max(t, 0):.3f}', '-i', path, '-frames:v', '1', '-vf',
               f'scale=trunc(iw*sar/2)*2:ih,setsar=1,scale=-2:{height}', '-f', 'image2pipe', '-vcodec', 'png', '-']).stdout
    import cv2
    return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)


def faces(img):
    """Haar frontal faces whose centre is skin-toned (YCrCb Cr 133-173, Cb 77-127 on >= 25 % of the box's middle) and, when
    the box is >= 60 px tall (of the 720-px sample: MS and closer), with an eye in its upper part; on a near-grey frame (median saturation < 25) the skin test is
    skipped rather than failing every face. Measured on a delivered spot: window-frame corners seen through a window passed the 2-of-3
    and skin tests (beige outside) and failed the eye test; the presenter's face passed all three."""
    import cv2
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); H = g.shape[0]
    cc = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml'))
    fs = [tuple(map(int, f)) for f in cc.detectMultiScale(g, scaleFactor=1.1, minNeighbors=6, minSize=(max(12, H // 25),) * 2)]
    if float(np.median(cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[..., 1])) < 25: return fs, H
    ycc = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb); keep = []
    for x, y, w, h in fs:
        c = ycc[y + h // 4:y + 3 * h // 4, x + w // 4:x + 3 * w // 4].reshape(-1, 3)
        if not len(c) or float(((c[:, 1] >= 133) & (c[:, 1] <= 173) & (c[:, 2] >= 77) & (c[:, 2] <= 127)).mean()) < 0.25: continue
        if h >= 60:                   # >= 60 px of 720 (MS and closer): big enough to show eyes; none = a texture (a window frame)
            ec = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, 'haarcascade_eye.xml'))
            if len(ec.detectMultiScale(g[y:y + int(0.6 * h), x:x + w], scaleFactor=1.1, minNeighbors=4, minSize=(max(6, w // 10),) * 2)) == 0: continue
        keep.append((x, y, w, h))
    return keep, H


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1]); x1, y1 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    i = max(0, x1 - x0) * max(0, y1 - y0); return i / float(a[2] * a[3] + b[2] * b[3] - i)


def framing(imgs):
    """the largest frontal face that is found in at least two of the shot's three sampled frames at the same place
    (a single-frame hit on an engine bay or an underbody is a texture, not a face) -> (class, faces, face height share)"""
    dets = [faces(im) for im in imgs]; H = dets[0][1]; kept = []
    for k, (fs, _) in enumerate(dets):
        for f in fs:
            if sum(any(iou(f, g) > 0.3 for g in other) for j, (other, _) in enumerate(dets) if j != k) >= 1: kept.append(f)
    if not kept: return 'none', 0, 0.0
    fh = float(np.median([f[3] for f in kept])) / H; n = max(len([f for f in fs if f in kept]) for fs, _ in dets)
    return next(lbl for thr, lbl in FRAMING if fh >= thr), n, round(fh, 3)


def loudness(path):
    e = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    r = re.findall(r'I:\s+(-?[0-9.]+) LUFS', e); return float(r[-1]) if r else None


def asr_words(path, model):
    from faster_whisper import WhisperModel
    segs, _ = WhisperModel(model, device='cpu', compute_type='int8').transcribe(path, word_timestamps=True, vad_filter=True)
    return [(w.word.strip(), round(w.start, 3), round(w.end, 3)) for s in segs for w in (s.words or [])]


def teardown(path, fps_an, asr=None, sheet=None):
    import cv2
    m = probe(path); fps = fps_an or round(m['fps'])
    _, h, mad, hl1, dx, dy, luma, resp, crs = measure(path, fps)
    n = len(mad); cuts = detect_cuts(crs, hl1, resp, fps); bounds = [0] + cuts + [n]
    words = asr_words(path, asr) if asr and m['audio'] else []
    shots, thumbs = [], []
    for k in range(len(bounds) - 1):
        a, b = bounds[k], bounds[k + 1]; t0, t1 = a / fps, b / fps
        cls, wps, cons, jit = motion_class(dx[a + 1:b], dy[a + 1:b], fps, AN_W)
        smp = [grab(path, t0 + q * (t1 - t0), 720) for q in (0.25, 0.5, 0.75)]; mid = smp[1]; fr, nf, fh = framing(smp)
        hsv = cv2.cvtColor(mid, cv2.COLOR_BGR2HSV)
        ws = [w for w in words if t0 <= w[1] < t1]
        shots.append(dict(i=k + 1, t0=round(t0, 3), t1=round(t1, 3), len=round(t1 - t0, 3), framing=fr, faces=nf, face_h=fh,
                          motion=cls, speed_wps=wps, consistency=cons, jitter=jit, luma=round(float(luma[a:b].mean()), 1),
                          sat=round(float(hsv[..., 1].mean()), 1), words=len(ws), text=' '.join(w[0] for w in ws)))
        if sheet: thumbs.append([grab(path, t, 180) for t in (t0 + 0.5 / fps, (t0 + t1) / 2, max(t0, t1 - 1.5 / fps))])
    lens = np.array([s['len'] for s in shots]); dur = n / fps
    sp = (words[-1][2] - words[0][1]) if words else 0.0
    stats = dict(shots=len(shots), shots_per_10s=round(10 * len(shots) / dur, 2) if dur else 0, median_len=round(float(np.median(lens)), 3),
                 iqr=[round(float(np.percentile(lens, 25)), 3), round(float(np.percentile(lens, 75)), 3)],
                 first_cut=round(cuts[0] / fps, 3) if cuts else None, first_word=words[0][1] if words else None,
                 wpm=round(60 * len(words) / sp, 1) if sp > 0 else None, speech_coverage=round(sum(w[2] - w[1] for w in words) / dur, 2) if dur and words else None)
    meta = dict(path=path, display=[m['w'], m['h']], fps_source=round(m['fps'], 3), fps_analysis=fps, duration=round(dur, 3),
                audio=m['audio'], loudness_I=loudness(path) if m['audio'] else None)
    if sheet: write_sheet(sheet, os.path.basename(path), shots, thumbs)
    return dict(meta=meta, shots=shots, stats=stats, cuts_s=[round(c / fps, 3) for c in cuts])


def write_sheet(out, name, shots, thumbs):
    from PIL import Image, ImageDraw
    tw = max(t.shape[1] for row in thumbs for t in row); rowh = 180 + 26; W = 3 * tw + 8
    img = Image.new('RGB', (W, rowh * len(shots) + 30), (18, 18, 18)); d = ImageDraw.Draw(img)
    d.text((6, 8), name, fill=(255, 220, 120))
    for r, (s, row) in enumerate(zip(shots, thumbs)):
        y = 30 + r * rowh
        d.text((6, y + 4), f"#{s['i']} {s['t0']:.2f}-{s['t1']:.2f}s ({s['len']:.2f}) {s['framing']} {s['motion']} {s['speed_wps']} w/s  {s['text'][:60]}", fill=(230, 230, 230))
        for c, t in enumerate(row):
            img.paste(Image.fromarray(t[..., ::-1]), (c * (tw + 4), y + 24))
    img.save(out, quality=85)


def grid(refs, runtime, fps, card=0.0):
    """slots at the references' rhythm; each slot takes the framing and motion the references show at that point of
    their running time (majority over references, by normalised position)."""
    firsts = [r['shots'][0]['len'] for r in refs]; meds = [r['stats']['median_len'] for r in refs]
    first, med = float(np.median(firsts)), float(np.median(meds)); body = runtime - card
    fr = lambda s: round(s * fps) / fps
    t, slots = 0.0, []
    while t < body - 1e-6:
        L = first if not slots else med
        L = min(L, body - t)
        if body - (t + L) < 0.5 * med: L = body - t                          # no stub slot at the end
        slots.append([fr(t), fr(t + L)]); t += L
    out = []
    for k, (a, b) in enumerate(slots):
        pos = ((a + b) / 2) / runtime; fvote, mvote = {}, {}
        for r in refs:
            T = r['meta']['duration']; s = next((s for s in r['shots'] if s['t0'] <= pos * T < s['t1']), r['shots'][-1])
            fvote[s['framing']] = fvote.get(s['framing'], 0) + 1; mvote[s['motion']] = mvote.get(s['motion'], 0) + 1
        out.append(dict(slot=k + 1, t0=a, t1=b, len=round(b - a, 3), framing=max(fvote, key=fvote.get),
                        motion=max(mvote, key=mvote.get), action=''))
    if card: out.append(dict(slot=len(out) + 1, t0=fr(body), t1=fr(runtime), len=round(card, 3), framing='card', motion='static', action='end card / CTA'))
    return dict(runtime=runtime, fps=fps, first_len=round(first, 3), median_len=round(med, 3), slots=out)


def aggregate(refs):
    lens = np.concatenate([[s['len'] for s in r['shots']] for r in refs]); mix = lambda k: {}
    fm, mm = {}, {}
    for r in refs:
        for s in r['shots']:
            fm[s['framing']] = fm.get(s['framing'], 0) + s['len']; mm[s['motion']] = mm.get(s['motion'], 0) + s['len']
    tot = sum(fm.values()) or 1.0
    vals = lambda key: [r['stats'][key] for r in refs if r['stats'][key] is not None]
    return dict(references=len(refs), shots=int(len(lens)), median_len=round(float(np.median(lens)), 3),
                iqr=[round(float(np.percentile(lens, 25)), 3), round(float(np.percentile(lens, 75)), 3)],
                shots_per_10s=round(float(np.median(vals('shots_per_10s'))), 2), first_cut=round(float(np.median(vals('first_cut'))), 3) if vals('first_cut') else None,
                first_word=round(float(np.median(vals('first_word'))), 3) if vals('first_word') else None,
                wpm=round(float(np.median(vals('wpm'))), 1) if vals('wpm') else None,
                framing_share={k: round(v / tot, 2) for k, v in sorted(fm.items(), key=lambda x: -x[1])},
                motion_share={k: round(v / tot, 2) for k, v in sorted(mm.items(), key=lambda x: -x[1])})


def na(v, unit=''):
    return '—' if v is None else f'{v}{unit}'


def write_md(out, refs, agg, g):
    L = ['# Reference teardown', '', 'MEASURED by `ad-spot-preprod/scripts/reference_teardown.py`. The CONTENT column of every table is the written read '
         '(`references/REFERENCE-TEARDOWN.md` step 3) — the agent or a multimodal lane fills it from the sheets; the measured columns stay as measured.', '']
    L += ['## Aggregate', '', '| references | shots | median shot | IQR | shots / 10 s | first cut | first word | wpm |', '|---|---|---|---|---|---|---|---|',
          f"| {agg['references']} | {agg['shots']} | {agg['median_len']} s | {agg['iqr'][0]}–{agg['iqr'][1]} s | {agg['shots_per_10s']} | {na(agg['first_cut'], ' s')} | {na(agg['first_word'], ' s')} | {na(agg['wpm'])} |", '',
          f"Framing by screen time: {agg['framing_share']} · motion: {agg['motion_share']}", '']
    for r in refs:
        m, st = r['meta'], r['stats']
        L += [f"## {os.path.basename(m['path'])}", '', f"{m['display'][0]}x{m['display'][1]} · {m['duration']} s · {st['shots']} shots · median {st['median_len']} s · "
              f"first cut {na(st['first_cut'], ' s')} · first word {na(st['first_word'], ' s')} · {na(st['wpm'], ' wpm')} · I {na(m['loudness_I'], ' LUFS')}", '',
              '| # | t0–t1 | len | framing | motion (w/s) | words | CONTENT — one action, camera, audio, on-screen text (written read) |', '|---|---|---|---|---|---|---|']
        L += [f"| {s['i']} | {s['t0']:.2f}–{s['t1']:.2f} | {s['len']:.2f} | {s['framing']} | {s['motion']} ({s['speed_wps']}) | {s['words']} | {s['text'][:80]} |" for s in r['shots']]
        L += ['']
    L += [f"## Beat grid — {g['runtime']} s at {g['fps']} fps (first slot {g['first_len']} s, then {g['median_len']} s)", '',
          'Structure KEPT (timing, framing, motion); content SWAPPED — each slot takes ONE action from `prompts/<SPOT>-beats.json`. '
          'With a voice-over the VO\'s phrases set the cut points (`video-edit-edl/scripts/phrase_slots.py`) and this grid is the check on '
          'the plan\'s rhythm, not a mould to force.', '',
          '| slot | t0–t1 | len | framing | motion | ONE action (our beat) |', '|---|---|---|---|---|---|']
    L += [f"| {s['slot']} | {s['t0']:.3f}–{s['t1']:.3f} | {s['len']:.3f} | {s['framing']} | {s['motion']} | {s['action']} |" for s in g['slots']]
    L += ['', '## Bones kept / world swapped', '', '| kept (structure) | swapped (content) |', '|---|---|', '| | |', '']
    open(out, 'w', encoding='utf-8').write('\n'.join(L))


def selftest():
    """Known answer: four scenes of known length (1.50 · 2.25 · 3.00 · 1.25 s at 24 fps; each its own coarse layout, level
    and detail), shot 2 panning 6 px/frame, shot 4 jittering ±3 px, shots 1 and 3 static. Cuts must come back within one frame, the pan must read pan at ~6 px/frame, the
    static shots static, the jitter handheld; the pan itself must raise NO cut. The beat grid for 9 s: the first slot 1.50 s."""
    import cv2
    d = tempfile.mkdtemp(prefix='teardown_'); rng = np.random.default_rng(11); W, H, fps = AN_W, 180, 24
    lens = [36, 54, 72, 30]; levels = [70, 150, 105, 185]; tex = []
    for k, lv in enumerate(levels):                                           # a scene: its own coarse layout + level + detail
        lay = cv2.resize(rng.normal(0, 40, (3, 5)).astype(np.float32), (W + 400, H + 40), interpolation=cv2.INTER_CUBIC)
        det = cv2.GaussianBlur(rng.normal(0, 30, (H + 40, W + 400)).astype(np.float32), (0, 0), 1.5)
        tex.append(np.clip(lv + lay + det, 0, 255).astype(np.uint8))
    fr = []
    for k, n in enumerate(lens):
        for i in range(n):
            if k == 1: x, y = 20 + 6 * i, 20
            elif k == 3: x, y = 200 + int(rng.integers(-3, 4)), 20 + int(rng.integers(-3, 4))
            else: x, y = 200, 20
            fr.append(tex[k][y:y + H, x:x + W])
    src = os.path.join(d, 'synthetic.mp4')
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                          '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', src], stdin=subprocess.PIPE)
    for f in fr: p.stdin.write(np.ascontiguousarray(f).tobytes())
    p.stdin.close(); p.wait()
    r = teardown(src, fps); want = [36 / 24, 90 / 24, 162 / 24]
    got = r['cuts_s']; ok_c = len(got) == 3 and all(abs(a - b) <= 1 / fps + 1e-6 for a, b in zip(got, want))
    mot = [s['motion'] for s in r['shots']]; sp2 = r['shots'][1]['speed_wps'] * W / fps if len(r['shots']) > 1 else 0
    ok_m = len(mot) == 4 and mot[0] == 'static' and mot[1] == 'pan' and abs(sp2 - 6) <= 0.5 and mot[2] == 'static' and mot[3] == 'handheld'
    g = grid([r], 9.0, 24); ok_g = abs(g['slots'][0]['len'] - 1.5) < 1e-6
    shutil.rmtree(d, ignore_errors=True)
    ok = ok_c and ok_m and ok_g
    print(f"SELFTEST cuts {got} (want {[round(x, 3) for x in want]} ±1 f) · motion {mot} (want static pan static handheld), "
          f"pan speed {sp2:.2f} px/f (want 6) · grid first slot {g['slots'][0]['len']} s (want 1.5) -> {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--refs', nargs='+'); ap.add_argument('--out'); ap.add_argument('--runtime', type=float, default=30.0)
    ap.add_argument('--fps', type=int, default=24, help='the grid frame rate'); ap.add_argument('--asr', default=None, help='faster-whisper model, e.g. small.en')
    ap.add_argument('--card', type=float, default=0.0, help='seconds of end card at the end of the grid')
    ap.add_argument('--selftest', action='store_true'); a = ap.parse_args()
    if not selftest(): sys.exit(1)
    if a.selftest: return
    if not a.refs or not a.out: ap.error('--refs and --out are required')
    os.makedirs(a.out, exist_ok=True); js = os.path.join(a.out, 'teardown.json')
    if os.path.exists(js): sys.exit(f'{js} exists - a teardown is a new directory')
    refs = []
    for p in a.refs:
        stem = re.sub(r'[^\w.-]+', '_', os.path.splitext(os.path.basename(p))[0])
        r = teardown(p, None, a.asr, os.path.join(a.out, f'{stem}-sheet.jpg')); refs.append(r)
        st = r['stats']; print(f"{os.path.basename(p)}: {st['shots']} shots · median {st['median_len']} s · first cut {st['first_cut']} s · "
                               f"first word {st['first_word']} · {st['wpm']} wpm · sheet {stem}-sheet.jpg")
    agg = aggregate(refs); g = grid(refs, a.runtime, a.fps, a.card)
    json.dump(dict(references=refs, aggregate=agg, grid=g), open(js, 'w'), indent=1)
    write_md(os.path.join(a.out, 'TEARDOWN.md'), refs, agg, g)
    print(f"aggregate: {agg['shots']} shots · median {agg['median_len']} s (IQR {agg['iqr']}) · {agg['shots_per_10s']} shots/10 s · "
          f"framing {agg['framing_share']} · motion {agg['motion_share']}")
    print(f"grid: {len(g['slots'])} slots for {g['runtime']} s -> {a.out}/TEARDOWN.md"); print('TEARDOWN-END')


if __name__ == '__main__':
    main()
