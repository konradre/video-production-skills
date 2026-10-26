#!/usr/bin/env python3
"""mouth_open.py — how far ONE face's mouth is open, frame by frame: the mouth-flap read of a silent subject, and
the articulation read of a speaking one. Numbers select; the sheet decides.

  mouth_open.py <take.mp4> --box x0,y0,x1,y1 [--ref-raster 768x1344] [--model face_landmarker.task]
                [--early 1.5] [--rest 2.0] [--voice <stem> [--at 0] [--lag 6] [--pauses a-b,c-d]]
                [--sheet <out.jpg>] [--json <out>] [--selftest]

  RATIO   the inner-lip gap over the mouth width (MediaPipe FaceLandmarker points 13-14 over 78-308) on the box
          crop, upscaled to 480 px first — a face under ~100 px is not found reliably at native size. Closed lips
          read ~0.03-0.10, a parted mouth ~0.2, a syllable 0.3+.
  EARLY   the max ratio in the first --early seconds and when — the first-second flap. Calibrated on one H3 scene
          (2026-09-19, 36 takes): both start stills mid-word 0.31 (median of six), the still with only the mouth
          closed 0.19, that still plus a concrete soundscape 0.15; the eye-read montages agreed take by take.
  REST    the median and max after --rest seconds: how much the mouth works through the rest of the take.
  FOUND   frames where a face was found in the box. Under ~90 % the box is wrong or the face too small: fix the
          box, never read the ratio.
  LAG     with --voice (a vocal stem, or the take itself for its own sound; --at = the voice file's time at the
          take's frame 0): the ratio against the voice's level per frame (RMS dBFS, floored at -60), correlated at
          lags -6…+6 frames — at lag k the mouth's frame i + k against the voice's frame i, so a positive best lag
          means the mouth comes late. Pattern: `.claude/skills/motion-graphics-music-video/scripts/tools/python/
          mouth_sync.py` in the `motion-graphics-music-video-skill` project, `video-production` CONTEXT-MAP; rebuilt
          on this ratio (its dark-pixel openness did not separate the arms here). The zero is UNCALIBRATED: no take
          with a known offset has been read, and a real mouth may open before its sound — read a take known to be
          in sync first and judge the others against it. The number says which scenes to look at first; the sheet
          decides.
  PAUSE   with --pauses (voice-file seconds, the gaps in the line): the ratio's median, max and range inside each
          pause beside the median over the voiced frames (level above -36 dBFS) — a mouth that keeps working
          through a rest.

--box is in the pixels of --ref-raster and is scaled to the take's own raster, so one box reads a 768p pass and
its 1088p refine. --sheet writes the box crop at 0, 0.25 ... 1.5 s and 3 s, enlarged: a verdict image, read
before the number is believed.

Needs `pip install mediapipe` (the tasks API; 1.0+ has no mp.solutions) and the float16 landmarker model:
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
passed as --model or $FACE_LANDMARKER.

--selftest checks the ratio arithmetic on synthetic landmarks (a closed, a parted and an open mouth), the box
scaling, the lag scan on a known shift (the mouth 3 frames late, 2 early, with lost frames), the voice level's
framing through --at (a burst in a written WAV, decoded by ffmpeg) and the pause read; detection itself has no
synthetic known answer, which is why FOUND and the sheet ride beside every read.
"""
import argparse, json, os, subprocess, sys
import numpy as np


def voice_db(path, at, n, fps, sr=16000):
    """the voice's RMS level (dBFS) per take frame: frame i covers [at + i/fps, at + (i+1)/fps) of the voice file;
    a frame outside the file reads as digital silence (-180)"""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).astype(np.float64); out = np.full(n, -180.0)
    for i in range(n):
        a, b = int(round((at + i / fps) * sr)), int(round((at + (i + 1) / fps) * sr))
        seg = x[max(a, 0):max(b, 0)]
        if seg.size: out[i] = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)
    return out


def lag_scan(mouth, vdb, max_lag=6, floor=-60.0):
    """r of the mouth ratio against the voice level at lags -max_lag…+max_lag: at lag k, mouth[i + k] against
    voice[i] — a positive best lag means the mouth comes late. Lost frames (NaN) drop out pairwise."""
    m = np.asarray(mouth, float); v = np.clip(np.asarray(vdb, float), floor, 0.0); n = min(len(m), len(v)); out = {}
    for k in range(-max_lag, max_lag + 1):
        if abs(k) >= n: out[k] = None; continue            # no overlap at this lag (a short clip, a wide window)
        a = m[max(0, k):n + min(0, k)]; b = v[max(0, -k):n - max(0, k)]; ok = np.isfinite(a) & np.isfinite(b)
        out[k] = (float(np.corrcoef(a[ok], b[ok])[0, 1])
                  if ok.sum() >= 3 and np.std(a[ok]) > 1e-9 and np.std(b[ok]) > 1e-9 else None)
    return out


def pause_read(mouth, vdb, at, fps, pauses, voiced_db=-36.0):
    """the ratio inside each named pause (voice-file seconds) beside its median over the voiced frames"""
    m = np.asarray(mouth, float)
    idx = lambda x: int(np.ceil(round((x - at) * fps, 6)))   # the first frame starting at or after x, on the frame grid
    vm = m[(np.asarray(vdb) > voiced_db) & np.isfinite(m)]
    rows = []
    for a, b in pauses:
        seg = m[max(idx(a), 0):max(idx(b), 0)]; seg = seg[np.isfinite(seg)]
        rows.append({"pause": [a, b], "frames": int(seg.size),
                     "median": round(float(np.median(seg)), 3) if seg.size else None,
                     "max": round(float(seg.max()), 3) if seg.size else None,
                     "range": round(float(seg.max() - seg.min()), 3) if seg.size else None})
    return rows, (round(float(np.median(vm)), 3) if vm.size else None)


def ratio(pts):
    up, lo, l, r = pts[13], pts[14], pts[78], pts[308]
    return float(np.hypot(up.x - lo.x, up.y - lo.y) / (np.hypot(l.x - r.x, l.y - r.y) + 1e-9))


def scale_box(box, ref, w, h):
    sx, sy = w / ref[0], h / ref[1]
    return int(box[0] * sx), int(box[1] * sy), int(box[2] * sx), int(box[3] * sy)


def selftest():
    class P:
        def __init__(s, x, y): s.x, s.y = x, y
    def lips(gap, width=0.4):
        pts = [P(0.5, 0.5) for _ in range(468)]
        pts[13], pts[14] = P(0.5, 0.6 - gap / 2), P(0.5, 0.6 + gap / 2)
        pts[78], pts[308] = P(0.5 - width / 2, 0.6), P(0.5 + width / 2, 0.6)
        return pts
    for gap, want in ((0.0, 0.0), (0.08, 0.2), (0.14, 0.35)):
        got = ratio(lips(gap)); assert abs(got - want) < 1e-6, (gap, got, want)
    assert scale_box((300, 210, 460, 370), (768, 1344), 1088, 1920) == (425, 300, 651, 528)
    # the lag scan: a syllable train of voice levels, the mouth tracking it with a known shift
    rng = np.random.default_rng(7); n = 240
    v = np.full(n, -60.0)
    for s in range(6, n - 12, 11):
        v[s:s + rng.integers(4, 8)] = rng.uniform(-24, -8)
    def mouth_from(shift):           # the mouth's frame i + shift shows the voice's frame i
        mo = np.full(n, 0.06)
        for i in range(n):
            j = i - shift
            if 0 <= j < n: mo[i] = 0.06 + 0.3 * (np.clip(v[j], -60, 0) + 60) / 60
        return mo + rng.normal(0, 0.01, n)
    for shift in (3, -2, 0):
        sc = lag_scan(mouth_from(shift), v); best = max((k for k in sc if sc[k] is not None), key=lambda k: sc[k])
        assert best == shift, (shift, best, sc[best])
    lost = mouth_from(3); lost[40:52] = np.nan
    sc = lag_scan(lost, v); assert max((k for k in sc if sc[k] is not None), key=lambda k: sc[k]) == 3
    # the voice level's framing: a 0.5 s burst at 1.0 s of a written WAV, read with --at 0.5 at 24 fps → frames 12-23
    import tempfile, wave
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "v.wav"); sr = 16000; x = np.zeros(int(2.5 * sr))
        x[sr:int(1.5 * sr)] = 0.8 * np.sin(2 * np.pi * 220 * np.arange(int(0.5 * sr)) / sr)
        with wave.open(p, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x * 32767).astype("<i2").tobytes())
        db = voice_db(p, 0.5, 60, 24.0)          # frames 48-59 run past the file's 2.5 s
    loud = [i for i in range(60) if db[i] > -10]
    assert loud == list(range(12, 24)), loud
    assert db[11] < -60 and db[24] < -60 and db[59] == -180.0, (db[11], db[24], db[59])
    db = db[:48]
    # the pause read: a mouth that keeps working through a rest
    mo = np.full(48, 0.05); mo[12:24] = 0.3; mo[30:34] = [0.05, 0.2, 0.25, 0.05]
    rows, vmed = pause_read(mo, db, 0.5, 24.0, [(0.5 + 30 / 24, 0.5 + 34 / 24)])   # frames 30-33; 34 sits on its end
    assert vmed == 0.3 and rows[0]["frames"] == 4 and rows[0]["max"] == 0.25 and rows[0]["range"] == 0.2, (vmed, rows)
    rows, _ = pause_read(np.zeros(30), np.full(30, -60.0), 0.7, 30.0, [(0.7, 0.9)])   # 0.2 s at 30 fps = 6 frames, not 7
    assert rows[0]["frames"] == 6, rows
    sc = lag_scan(np.linspace(0, 1, 24), np.linspace(-60, 0, 24), 30)   # a window wider than the clip: no crash
    assert sc[30] is None and sc[-30] is None and sc[0] is not None, sc
    sc = lag_scan([0.1, 0.2, 0.3], [-40.0, -20.0, -10.0])               # three frames at the default lag
    assert sc[6] is None and sc[0] is not None, sc
    print("SELFTEST OK — ratio 0.00 / 0.20 / 0.35 on synthetic lips; box scales 768p -> 1088p; lag scan finds +3, "
          "-2 and 0 frames (and +3 with 12 frames lost); the voice framing puts a 1.0-1.5 s burst at --at 0.5 on "
          "frames 12-23; the pause read reports a 0.2 range inside a rest beside a voiced median of 0.3, and 6 frames for 0.2 s at 30 fps; a lag window wider than the clip reads None")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("take", nargs="?"); ap.add_argument("--box"); ap.add_argument("--ref-raster", default="768x1344")
    ap.add_argument("--model", default=os.environ.get("FACE_LANDMARKER"))
    ap.add_argument("--early", type=float, default=1.5); ap.add_argument("--rest", type=float, default=2.0)
    ap.add_argument("--voice"); ap.add_argument("--at", type=float, default=0.0); ap.add_argument("--lag", type=int, default=6)
    ap.add_argument("--pauses", help="a-b,c-d in the voice file's seconds")
    ap.add_argument("--sheet"); ap.add_argument("--json"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); return
    if not (a.take and a.box and a.model):
        sys.exit("need <take> --box x0,y0,x1,y1 and --model (or $FACE_LANDMARKER)")
    if a.pauses and not a.voice:
        sys.exit("--pauses reads against the voice: pass --voice too")
    pauses = [tuple(float(x) for x in p.split("-")) for p in a.pauses.split(",")] if a.pauses else []
    import cv2, mediapipe as mp
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision
    lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=a.model), num_faces=1, running_mode=vision.RunningMode.IMAGE))
    box = [int(v) for v in a.box.split(",")]; ref = [int(v) for v in a.ref_raster.split("x")]
    cap = cv2.VideoCapture(a.take); fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    vals, crops = [], {}
    want = {round(t * fps): t for t in (0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 3.0)}
    i = 0
    while True:
        ok, f = cap.read()
        if not ok: break
        h, w = f.shape[:2]; x0, y0, x1, y1 = scale_box(box, ref, w, h)
        c = cv2.resize(f[y0:y1, x0:x1], (480, 480), interpolation=cv2.INTER_CUBIC)
        r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(c, cv2.COLOR_BGR2RGB)))
        vals.append(ratio(r.face_landmarks[0]) if r.face_landmarks else float("nan"))
        if i in want: crops[want[i]] = cv2.resize(c, (240, 240), interpolation=cv2.INTER_AREA)
        i += 1
    lm.close()                     # close before interpreter teardown, or MediaPipe's __del__ raises on exit
    v = np.array(vals); n = len(v); e, s = v[: int(round(a.early * fps)) + 1], v[int(round(a.rest * fps)):]
    fin = lambda x: x[np.isfinite(x)]
    rec = {"take": os.path.basename(a.take), "frames": n, "found": int(np.isfinite(v).sum()),
           "early_max": round(float(fin(e).max()), 3) if fin(e).size else None,
           "early_max_s": round(float(np.nanargmax(e)) / fps, 2) if fin(e).size else None,
           "rest_median": round(float(np.median(fin(s))), 3) if fin(s).size else None,
           "rest_max": round(float(fin(s).max()), 3) if fin(s).size else None,
           "trace": [None if not np.isfinite(x) else round(float(x), 3) for x in v]}
    warn = "" if rec["found"] >= 0.9 * n else "  ⚠ FOUND under 90 % — fix the box before reading the ratio"
    print(f"{rec['take']}  found {rec['found']}/{n}  early max {rec['early_max']}@{rec['early_max_s']}s  "
          f"rest median {rec['rest_median']}  rest max {rec['rest_max']}{warn}")
    if a.voice:
        vdb = voice_db(a.voice, a.at, n, fps); sc = lag_scan(v, vdb, a.lag); got = {k: r for k, r in sc.items() if r is not None}
        best = max(got, key=got.get) if got else None
        rec["lag"] = {"voice": a.voice, "at": a.at, "scan": {str(k): None if r is None else round(r, 3) for k, r in sc.items()},
                      "best": best, "r": round(got[best], 3) if got else None}
        print("lag (frames, + = mouth late):  " + "  ".join(f"{k:+d}:{'—' if r is None else f'{r:+.2f}'}" for k, r in sc.items()))
        print(f"best lag {best:+d} frames (r {got[best]:+.2f}) — the zero is uncalibrated: read a take known to be in sync, "
              f"then the sheet" if got else "no lag read: too few frames with both a face and a level")
        if pauses:
            rows, vmed = pause_read(v, vdb, a.at, fps, pauses); rec["pauses"] = rows; rec["voiced_median"] = vmed
            for r_ in rows:
                print(f"pause {r_['pause'][0]:.2f}-{r_['pause'][1]:.2f}: {r_['frames']} frames, median {r_['median']}, "
                      f"max {r_['max']}, range {r_['range']} (voiced median {vmed})")
    if a.sheet and crops:
        row = []
        for t in sorted(crops):
            c = crops[t].copy(); cv2.putText(c, f"{t:.2f}s", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            row.append(c)
        cv2.imwrite(a.sheet, np.hstack(row), [cv2.IMWRITE_JPEG_QUALITY, 95, cv2.IMWRITE_JPEG_SAMPLING_FACTOR, 0x111111])
    if a.json:
        json.dump(rec, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
