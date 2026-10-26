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
last frame of each shot, labelled) for the written read, which is the half no instrument does. With --dense <fps> (a
motion-design reference: 10-12) also a dense strip per shot — its frames at that rate between its cuts, 240 px tall, rows
no wider than 1920 px, pages no taller than 4000 px — because three frames a shot cannot show how a line draws on, how type moves or how a camera reveals.

Every source is read in its DISPLAY geometry (the sample aspect applied first) and at its average rate as constant frame
rate. Limits: a dissolve reads as a cut at its middle or as none; a whip pan can read as a cut; a profile or a small face
reads "none"; the motion class is the frame's dominant motion, camera or subject — the sheet is read before a number is
trusted.

  reference_teardown.py --refs <a.mp4> <b.mp4> … --out <dir> [--runtime 30] [--fps 24] [--asr small.en] [--card 3.0] [--dense 12]
  reference_teardown.py --selftest
Writes <dir>/teardown.json, <dir>/TEARDOWN.md, <dir>/<ref>-sheet.jpg and with --dense <dir>/<ref>-strip-<shot>-p<page>.jpg; never
overwrites an existing <dir>/teardown.json.
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


STRIP_H, STRIP_W, STRIP_PAGE_H, STRIP_GAP = 240, 1920, 4000, 3     # tile height, max page width and height, tile gap (px)


def strip_tile(dw, dh, height=STRIP_H, max_w=STRIP_W):
    """the tile size for a dw x dh display frame: `height` tall, unless that would be wider than a row allows"""
    w = max(2, int(round(height * dw / dh / 2)) * 2); room = max_w - 8 - STRIP_GAP          # one tile + its gap + the margin
    if w > room:
        w = room // 2 * 2; height = max(2, int(round(w * dh / dw / 2)) * 2)
    return w, height


def dense_rate(x):
    """a strip rate: a finite number of frames a second above zero (argparse type and strip_indices' guard)"""
    import math
    v = float(x)
    if not math.isfinite(v) or v <= 0: raise ValueError(f'--dense must be a finite rate above 0, got {x}')
    return v


def strip_indices(a, b, fa, rate):
    """the analysis frames a dense strip shows for the shot [a, b): one every fa/rate frames from a, never past b — j = 0
    is always frame a, so a shot shorter than one strip frame still shows its own first frame"""
    import math
    out, j, step = [], 0, max(fa / dense_rate(rate), 1.0)       # a rate above the analysis rate shows every frame once
    while True:
        k = a + int(math.floor(j * step + 1e-9))
        if k >= b: break
        out.append(k); j += 1
    return out


def analysis_frames(path, fa, tile):
    """(index, frame) over the SAME normalised stream the cuts were found on — the analysis filter chain at fa, in colour
    at `tile` size — so a strip frame is an analysis frame by index, and no timestamp is ever mapped: a fractional or a
    variable source rate cannot move a cut. Streamed: one decode, nothing held whole."""
    w, h = tile; n = w * h * 3
    vf = f"scale=trunc(iw*sar/2)*2:ih,setsar=1,fps={fa:.6f},scale={w}:{h}:flags=area,format=bgr24"
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', vf, '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
    i = 0
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield i, np.frombuffer(b, np.uint8).reshape(h, w, 3); i += 1
    p.stdout.close(); p.wait()


def shot_strips(path, fa, bounds, rate, tile):
    """one generator per shot over a single shared analysis stream: shot k's generator yields its strip frames and stops
    after its last analysis frame, so the shots must be consumed in order"""
    stream = analysis_frames(path, fa, tile)
    for a, b in zip(bounds[:-1], bounds[1:]):
        want = set(strip_indices(a, b, fa, rate))
        def take(want=want, b=b):
            for i, f in stream:
                if i in want: yield f
                if i >= b - 1: return
        yield take()


def write_strips(stem, name, s, frames, rate, max_w=STRIP_W, max_h=STRIP_PAGE_H):
    """one shot's dense strip as pages: frames left to right in time, rows no wider than max_w, pages no taller than
    max_h (a JPEG side stops at 65500 px), each page labelled. Returns (paths written, frame count)."""
    from PIL import Image, ImageDraw
    gap, head = STRIP_GAP, 26; paths, buf, count, per_row = [], [], 0, None

    def flush(final):
        nonlocal buf
        if not buf: return
        th, tw = buf[0].shape[:2]; rows = -(-len(buf) // per_row); page = len(paths) + 1
        img = Image.new('RGB', (min(len(buf), per_row) * (tw + gap) + 8, head + rows * (th + gap)), (18, 18, 18)); d = ImageDraw.Draw(img)
        first = count - len(buf)
        d.text((6, 7), f"{name} #{s['i']} {s['t0']:.2f}-{s['t1']:.2f}s ({s['len']:.2f}) frames {first + 1}-{count} at {rate} fps · page {page}", fill=(255, 220, 120))
        for k, f in enumerate(buf):
            img.paste(Image.fromarray(np.ascontiguousarray(f[..., ::-1])), (4 + (k % per_row) * (tw + gap), head + (k // per_row) * (th + gap)))
        out = f"{stem}-{s['i']:02d}-p{page}.jpg"; img.save(out, quality=85); paths.append(out); buf = []

    for f in frames:
        if per_row is None:
            th, tw = f.shape[:2]; per_row = max(1, (max_w - 8) // (tw + gap)); per_page = per_row * max(1, (max_h - head) // (th + gap))
        buf.append(f); count += 1
        if len(buf) == per_page: flush(False)
    flush(True)
    return paths, count


def teardown(path, fps_an, asr=None, sheet=None, dense=None, strip=None):
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
    if dense:
        for s, fr in zip(shots, shot_strips(path, fps, bounds, dense, strip_tile(m['w'], m['h']))):
            if strip: s['strips'], s['strip_frames'] = write_strips(strip, os.path.basename(path), s, fr, dense)
            else: s['strip_frames'] = sum(1 for _ in fr)
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


def selftest(dense=True):
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
    ok_d, rep_d = True, ''
    if dense: ok_d, rep_d = dense_selftest(d, src, fps, W, H)
    shutil.rmtree(d, ignore_errors=True)
    ok = ok_c and ok_m and ok_g and ok_d
    print(f"SELFTEST cuts {got} (want {[round(x, 3) for x in want]} ±1 f) · motion {mot} (want static pan static handheld), "
          f"pan speed {sp2:.2f} px/f (want 6) · grid first slot {g['slots'][0]['len']} s (want 1.5){rep_d} -> {'PASS' if ok else 'FAIL'}")
    return ok


def dense_selftest(d, src, fps, W, H):
    """the --dense checks, on the selftest's synthetic clip plus two more: counts, the SAVED pages read back (each shot's own
    frames, edges included, the pan in time order), a one-frame shot, a fractional and a variable source rate across a
    cut, a tile too wide for a row, a 90 s shot paged"""
    from PIL import Image
    tile = strip_tile(W, H); th, tw = tile[1], tile[0]
    def tiles(paths, n):                                   # read the SAVED pages back, tile by tile, in order, across pages
        g = STRIP_GAP; per = max(1, (STRIP_W - 8) // (tw + g)); page = per * max(1, (STRIP_PAGE_H - 26) // (th + g)); out = []
        for q in paths:
            im = np.asarray(Image.open(q).convert('L')).astype(np.float32)
            for k in range(min(page, n - len(out))):
                out.append(im[26 + (k // per) * (th + g):26 + (k // per) * (th + g) + th, 4 + (k % per) * (tw + g):4 + (k % per) * (tw + g) + tw])
        return out
    def encode(path, rate, levels):                      # flat gray frames, one level each
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray', '-s', '320x180', '-r', rate, '-i', '-',
                              '-c:v', 'libx264', '-crf', '10', '-pix_fmt', 'yuv420p', path], stdin=subprocess.PIPE)
        for v in levels: p.stdin.write(np.full((180, 320), v, np.uint8).tobytes())
        p.stdin.close(); p.wait()
    def held(path, stem):                                # teardown + readback: every tile of every shot, in order
        r = teardown(path, None, dense=12, strip=os.path.join(d, stem))
        fl = [[float(t.mean()) for t in tiles(sh['strips'], sh['strip_frames'])] for sh in r['shots'] if sh.get('strips')]
        ok = (len(fl) == 3 and [len(x) for x in fl] == [sh['strip_frames'] for sh in r['shots']]
              and all(v < 125 for v in fl[0] + fl[2]) and all(v > 125 for v in fl[1]))       # no tile leaks across a cut
        return ok, f"{[len(x) for x in fl]} {[(round(x[0]), round(x[-1])) for x in fl if x]}"

    rd = teardown(src, fps, dense=12, strip=os.path.join(d, 'synthetic-strip')); nd = [s.get('strip_frames', 0) for s in rd['shots']]
    want_d = [round(s['len'] * 12) for s in rd['shots']]; own = [s['luma'] for s in rd['shots']]
    saved = [tiles(s['strips'], s['strip_frames']) for s in rd['shots']] if all(s.get('strips') for s in rd['shots']) else []
    lv = [(float(t[0].mean()), float(t[-1].mean())) for t in saved]          # each SAVED row holds its own shot, edges included
    bd = [0] + [round(c * fps) for c in rd['cuts_s']]
    pan = ([f.mean(2) for i, f in analysis_frames(src, fps, tile) if i in set(strip_indices(bd[1], bd[2], fps, 12))]
           if len(bd) > 2 else [])
    order = len(saved) > 1 and len(pan) == len(saved[1]) and all(                 # the pan's tiles in time order
        np.abs(saved[1][k] - pan[k]).mean() < min(np.abs(saved[1][k] - pan[j]).mean() for j in (k - 2, k + 2) if 0 <= j < len(pan))
        for k in range(len(pan)))
    short = (strip_indices(10, 11, 30, 12) == [10] and strip_indices(0, 5, 30, 12) == [0, 2]      # a one-frame shot keeps its own
             and len(strip_indices(0, 36, 24, 12)) == 18 and all(0 <= k < 36 for k in strip_indices(0, 36, 24, 12))
             and strip_indices(0, 6, 24, 60) == [0, 1, 2, 3, 4, 5])                                # above fa: each frame once
    def refused(x):
        try: dense_rate(x); return False
        except ValueError: return True
    rate_ok = all(refused(x) for x in ('-12', '0', 'inf', 'nan')) and dense_rate('12') == 12.0      # never an endless index loop
    sfr = os.path.join(d, 'f2997.mp4'); encode(sfr, '30000/1001', [40] * 500 + [210] * 6 + [40] * 30)   # a fractional source rate
    frac, rep_f = held(sfr, 'f2997-strip')
    a30, b60, vfr, lst = (os.path.join(d, x) for x in ('a30.mp4', 'b60.mp4', 'vfr.mkv', 'list.txt'))   # a variable source rate
    encode(a30, '30', [40] * 496); encode(b60, '60', [210] * 12 + [40] * 30)
    open(lst, 'w').write(f"file '{a30}'\nfile '{b60}'\n")
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', vfr])
    vfr_ok, rep_v = held(vfr, 'vfr-strip')
    wt = strip_tile(2400 * 4, 240 * 4); wp, _ = write_strips(os.path.join(d, 'wide'), 'wide', dict(i=1, t0=0.0, t1=1.0, len=1.0),
                                                              iter([np.zeros((wt[1], wt[0], 3), np.uint8)]), 12)
    wide = Image.open(wp[0]).size[0] <= STRIP_W and all(Image.open(q).size[0] <= STRIP_W for sh in rd['shots'] for q in sh.get('strips', []))
    pg, n_pg = write_strips(os.path.join(d, 'long'), 'long', dict(i=1, t0=0.0, t1=90.0, len=90.0),
                            (np.zeros((240, 426, 3), np.uint8) for _ in range(1080)), 12)
    pages = n_pg == 1080 and len(pg) > 1 and all(Image.open(q).size[1] <= STRIP_PAGE_H for q in pg)
    ok = (len(nd) == 4 and all(abs(a - b) <= 1 for a, b in zip(nd, want_d)) and len(lv) == 4
          and all(min(range(4), key=lambda j: abs(v - own[j])) == k for k, pair in enumerate(lv) for v in pair)
          and order and short and rate_ok and wide and pages and frac and vfr_ok)
    return ok, (f" · dense strip frames {nd} (want {want_d} ±1 at 12 fps), saved first/last tile levels "
                f"{[(round(x), round(y)) for x, y in lv]} (each nearest its own shot's luma of {[round(x) for x in own]}), saved pan tiles in "
                f"order {order}, one-frame shot keeps its frame {short}, bad rates refused {rate_ok}, wide tile fits {wide}, 90 s shot paged {len(pg)} pages {pages}, "
                f"29.97 fps cuts hold {frac} {rep_f}, VFR cuts hold {vfr_ok} {rep_v}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--refs', nargs='+'); ap.add_argument('--out'); ap.add_argument('--runtime', type=float, default=30.0)
    ap.add_argument('--fps', type=int, default=24, help='the grid frame rate'); ap.add_argument('--asr', default=None, help='faster-whisper model, e.g. small.en')
    ap.add_argument('--card', type=float, default=0.0, help='seconds of end card at the end of the grid')
    ap.add_argument('--dense', type=dense_rate, default=None, help='also a dense strip per reference at this many frames a second between cuts (10-12 for a motion-design reference)')
    ap.add_argument('--selftest', action='store_true'); a = ap.parse_args()
    if not selftest(dense=bool(a.selftest or a.dense)): sys.exit(1)     # the --dense checks run when they matter
    if a.selftest: return
    if not a.refs or not a.out: ap.error('--refs and --out are required')
    os.makedirs(a.out, exist_ok=True); js = os.path.join(a.out, 'teardown.json')
    if os.path.exists(js): sys.exit(f'{js} exists - a teardown is a new directory')
    refs = []
    for p in a.refs:
        stem = re.sub(r'[^\w.-]+', '_', os.path.splitext(os.path.basename(p))[0])
        r = teardown(p, None, a.asr, os.path.join(a.out, f'{stem}-sheet.jpg'), a.dense, os.path.join(a.out, f'{stem}-strip') if a.dense else None); refs.append(r)
        st = r['stats']; print(f"{os.path.basename(p)}: {st['shots']} shots · median {st['median_len']} s · first cut {st['first_cut']} s · "
                               f"first word {st['first_word']} · {st['wpm']} wpm · sheet {stem}-sheet.jpg" + (f" · strips {stem}-strip-NN-pK.jpg" if a.dense else ''))
    agg = aggregate(refs); g = grid(refs, a.runtime, a.fps, a.card)
    json.dump(dict(references=refs, aggregate=agg, grid=g), open(js, 'w'), indent=1)
    write_md(os.path.join(a.out, 'TEARDOWN.md'), refs, agg, g)
    print(f"aggregate: {agg['shots']} shots · median {agg['median_len']} s (IQR {agg['iqr']}) · {agg['shots_per_10s']} shots/10 s · "
          f"framing {agg['framing_share']} · motion {agg['motion_share']}")
    print(f"grid: {len(g['slots'])} slots for {g['runtime']} s -> {a.out}/TEARDOWN.md"); print('TEARDOWN-END')


if __name__ == '__main__':
    main()
