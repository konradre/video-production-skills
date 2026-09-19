#!/usr/bin/env python3
"""mouth_open.py — how far ONE face's mouth is open, frame by frame: the mouth-flap read of a silent subject, and
the articulation read of a speaking one. Numbers select; the sheet decides.

  mouth_open.py <take.mp4> --box x0,y0,x1,y1 [--ref-raster 768x1344] [--model face_landmarker.task]
                [--early 1.5] [--rest 2.0] [--sheet <out.jpg>] [--json <out>] [--selftest]

  RATIO   the inner-lip gap over the mouth width (MediaPipe FaceLandmarker points 13-14 over 78-308) on the box
          crop, upscaled to 480 px first — a face under ~100 px is not found reliably at native size. Closed lips
          read ~0.03-0.10, a parted mouth ~0.2, a syllable 0.3+.
  EARLY   the max ratio in the first --early seconds and when — the first-second flap. Calibrated on one H3 scene
          (2026-09-19, 36 takes): both start stills mid-word 0.31 (median of six), the still with only the mouth
          closed 0.19, that still plus a concrete soundscape 0.15; the eye-read montages agreed take by take.
  REST    the median and max after --rest seconds: how much the mouth works through the rest of the take.
  FOUND   frames where a face was found in the box. Under ~90 % the box is wrong or the face too small: fix the
          box, never read the ratio.

--box is in the pixels of --ref-raster and is scaled to the take's own raster, so one box reads a 768p pass and
its 1088p refine. --sheet writes the box crop at 0, 0.25 ... 1.5 s and 3 s, enlarged: a verdict image, read
before the number is believed.

Needs `pip install mediapipe` (the tasks API; 1.0+ has no mp.solutions) and the float16 landmarker model:
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
passed as --model or $FACE_LANDMARKER.

--selftest checks the ratio arithmetic on synthetic landmarks (a closed, a parted and an open mouth) and the box
scaling; detection itself has no synthetic known answer, which is why FOUND and the sheet ride beside every read.
"""
import argparse, json, os, sys
import numpy as np


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
    print("SELFTEST OK — ratio 0.00 / 0.20 / 0.35 on synthetic lips; box scales 768p -> 1088p")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("take", nargs="?"); ap.add_argument("--box"); ap.add_argument("--ref-raster", default="768x1344")
    ap.add_argument("--model", default=os.environ.get("FACE_LANDMARKER"))
    ap.add_argument("--early", type=float, default=1.5); ap.add_argument("--rest", type=float, default=2.0)
    ap.add_argument("--sheet"); ap.add_argument("--json"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); return
    if not (a.take and a.box and a.model):
        sys.exit("need <take> --box x0,y0,x1,y1 and --model (or $FACE_LANDMARKER)")
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
