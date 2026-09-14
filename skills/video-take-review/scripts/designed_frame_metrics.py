#!/usr/bin/env python3
"""designed_frame_metrics.py — composition and sustained-action metrics for DESIGNED motion (explainer scenes,
kinetic titles, cards): how big the hero is, how long the frame stays empty, how long it holds still. Every size
is a FRACTION of the content box and every duration is in seconds, so one set of thresholds reads any raster.

  designed_frame_metrics.py <clip.mp4 | frames-dir> [--fps 30] [--from 0 --to 60] [--content x0,y0,x1,y1]
        [--shots "SC01:0-4.2,SC02:4.2-9"] [--hero-floor 0.33] [--empty-floor 0.21] [--empty-max 1.5]
        [--still-thr 0.35] [--still-max 40] [--hold-max 1.0] [--ground auto|<0-255>] [--fg-delta 120] [--json out.json]
  designed_frame_metrics.py <images-dir> --each [--content …]     # every image is its own shot (hero only)
  designed_frame_metrics.py --selftest

hero    the largest foreground object in the content box after a 13×41 px dilation that merges one line of type,
        sized max(h, min(w, 4h) / 2.5), as a fraction of the box height. Foreground = luminance more than
        --fg-delta away from the ground (the median of the box's border ring, or a number you pass).
empty   the longest run of samples in which no hero reaches --empty-floor, in seconds.
still   samples 0.1 s apart whose mean absolute grey difference over the box (long side 320 px) is under
        --still-thr: the share of still samples and the longest still run. The longest run is classed by the
        share of box pixels that changed by more than 25 grey levels: under 0.12 % = TRUE-STILL (add an action),
        under 0.38 % = SMALL-MOTION (raise the moving element's amplitude, never add elements), above = ACTION.
Every frame is measured at a 720-px short side (downscaled with an area filter, never upscaled), the raster the
thresholds were calibrated on; frames stream, so memory stays flat on a long file. Flags are JUDGEMENT rows: read
the frames before acting on one. The still and empty rows bind narrated motion graphics — a slide walkthrough, a
card, a logo or a legal hold is still BY DESIGN. Needs numpy + Pillow and OpenCV or scipy; ffmpeg for a video.
"""
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None
if os.environ.get("DFM_NO_CV2"):
    cv2 = None

SHORT = 720                      # analysis raster: short side in px (never upscaled)
DILATE = (13, 41)                # merges glyphs up to ~40 px apart horizontally into one object
MIN_INK, MIN_FG = 30, 200        # object ink floor; a sample below MIN_FG foreground px has no hero
DT = 0.1                         # seconds between motion samples
CHANGE = 25                      # grey levels that count as a changed pixel
TRUE_STILL, SMALL_MOTION = 0.0012, 0.0038
KERNEL = np.ones(DILATE, np.uint8)


def analysis_size(w, h):
    s = SHORT / min(w, h)
    return (w, h) if s >= 1 else (max(1, round(w * s)), max(1, round(h * s)))


def probe(path):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate", "-of", "json", str(path)],
                                  capture_output=True, text=True, check=True).stdout)
    st = j["streams"][0]; num, den = (int(x) for x in st["r_frame_rate"].split("/"))
    return int(st["width"]), int(st["height"]), num / den


def video_frames(path, t0=0.0, t1=None):
    w, h, fps = probe(path)
    step = max(1, round(fps * DT)); aw, ah = analysis_size(w, h); dt = step / fps
    cmd = (["ffmpeg", "-v", "error"] + (["-ss", str(t0)] if t0 else []) + (["-to", str(t1)] if t1 else []) +
           ["-i", str(path), "-vf", f"select='not(mod(n\\,{step}))',scale={aw}:{ah}:flags=area",
            "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])

    def gen():
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE); size = aw * ah * 3; i = 0
        try:
            while True:
                buf = p.stdout.read(size)
                if len(buf) < size:
                    break
                yield t0 + i * dt, np.frombuffer(buf, np.uint8).reshape(ah, aw, 3); i += 1
        finally:
            p.stdout.close(); p.wait()
        if p.returncode:
            raise SystemExit(f"ffmpeg failed on {path} (exit {p.returncode})")
    return gen(), dt, f"{w}x{h}->{aw}x{ah} @ {fps:.3f} fps"


def image(path):
    im = Image.open(path).convert("RGB"); aw, ah = analysis_size(*im.size)
    return np.asarray(im if (aw, ah) == im.size else im.resize((aw, ah), Image.BOX)), im.size


def dir_frames(d, fps):
    files = sorted(f for f in Path(d).iterdir() if f.suffix.lower() in (".png", ".jpg", ".jpeg"))
    if not files:
        sys.exit(f"no frames in {d}")
    step = max(1, round(fps * DT))

    def gen():
        for i, f in enumerate(files[::step]):
            yield i * step / fps, image(f)[0]
    return gen(), step / fps, f"{Image.open(files[0]).size[0]}x{Image.open(files[0]).size[1]} frames @ {fps:g} fps"


def box_of(frame, box):
    H, W = frame.shape[:2]; x0, y0, x1, y1 = box
    return frame[round(y0 * H):round(y1 * H), round(x0 * W):round(x1 * W)]


def luminance(rgb):
    a = rgb.astype(np.int32)
    return (a[..., 0] * 299 + a[..., 1] * 587 + a[..., 2] * 114) // 1000


def ground_of(lum, spec):
    if spec != "auto":
        return float(spec)
    m = max(1, round(0.03 * min(lum.shape)))
    return float(np.median(np.concatenate([lum[:m].ravel(), lum[-m:].ravel(), lum[:, :m].ravel(), lum[:, -m:].ravel()])))


def hero_px(lum, ground, delta):
    fg = np.abs(lum - ground) > delta
    if int(fg.sum()) < MIN_FG:
        return 0.0
    if cv2 is not None:
        n, lab, stats, _ = cv2.connectedComponentsWithStats(cv2.dilate(fg.astype(np.uint8), KERNEL), connectivity=4)
        if n < 2:
            return 0.0
        ink = np.bincount(lab[fg], minlength=n)[1:]
        h = stats[1:, cv2.CC_STAT_HEIGHT].astype(float); w = stats[1:, cv2.CC_STAT_WIDTH].astype(float)
    else:
        from scipy import ndimage as ndi
        lab, n = ndi.label(ndi.binary_dilation(fg, structure=np.ones(DILATE, bool)))
        if not n:
            return 0.0
        ink = np.bincount(lab[fg], minlength=n + 1)[1:]
        sl = ndi.find_objects(lab)
        h = np.array([s[0].stop - s[0].start for s in sl], float); w = np.array([s[1].stop - s[1].start for s in sl], float)
    size = np.maximum(h, np.minimum(w, 4 * h) / 2.5)[ink >= MIN_INK]
    return float(size.max()) if size.size else 0.0


def grid(lum):
    h, w = lum.shape; s = 320 / max(h, w)
    im = Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8)).resize((max(1, round(w * s)), max(1, round(h * s))), Image.BICUBIC)
    return np.asarray(im, dtype=np.int32)


def measure(frames, box, ground, delta):
    out = []; prev_g = prev_l = None
    for t, fr in frames:
        lum = luminance(box_of(fr, box)); g = grid(lum)
        rec = {"t": t, "hero": hero_px(lum, ground_of(lum, ground), delta) / lum.shape[0]}
        if prev_g is not None and prev_g.shape == g.shape:
            rec["d"] = float(np.abs(g - prev_g).mean())
            rec["changed"] = float((np.abs(lum - prev_l) > CHANGE).mean())
        out.append(rec); prev_g, prev_l = g, lum
    return out


def summarize(recs, name, a, b, dt, o):
    S = [r for r in recs if a <= r["t"] < b]
    if not S:
        return {"shot": name, "span": [a, b], "error": "no samples"}
    heroes = [r["hero"] for r in S]; solid = [h for h in heroes if h > 0]
    run = best = 0
    for h in heroes:
        run = run + 1 if h < o.empty_floor else 0; best = max(best, run)
    res = {"shot": name, "span": [round(a, 3), round(b, 3)], "samples": len(S),
           "hero_median": round(float(np.median(solid)), 3) if solid else 0.0, "hero_min": round(min(heroes), 3),
           "empty_s": round(best * dt, 2)}
    D = [r for r in S if "d" in r]; flags = []
    if res["empty_s"] > o.empty_max:
        flags.append("EMPTY")
    elif res["hero_median"] < o.hero_floor:
        flags.append("SMALL")
    if len(D) >= 3:
        still = [r["d"] < o.still_thr for r in D]; run = best = end = 0
        for i, s in enumerate(still):
            run = run + 1 if s else 0
            if run > best:
                best, end = run, i
        res["still_pct"] = round(100 * sum(still) / len(still)); res["hold_s"] = round(best * dt, 2)
        if best:
            ch = float(np.median([r["changed"] for r in D[end - best + 1:end + 1]]))
            res["hold_class"] = "TRUE-STILL" if ch < TRUE_STILL else ("SMALL-MOTION" if ch < SMALL_MOTION else "ACTION")
            res["hold_changed_pct"] = round(100 * ch, 3)
        if res["still_pct"] > o.still_max:
            flags.append("STILL")
        if res["hold_s"] > o.hold_max:
            flags.append("HOLD")
    res["flags"] = flags
    return res


def parse_shots(spec, start, end):
    if not spec:
        return [("all", start, end)]
    out = []
    for tok in spec.split(","):
        name, rng = tok.rsplit(":", 1); a, b = rng.split("-"); out.append((name.strip(), float(a), float(b)))
    return out


def print_table(head, rows):
    print(head)
    print(f"{'shot':10} {'span s':>13} {'hero med/min':>13} {'empty':>6} {'still':>6} {'hold':>6}  {'class':13} flags")
    for r in rows:
        if "error" in r:
            print(f"{r['shot']:10} {r['error']}"); continue
        span = f"{r['span'][0]:g}-{r['span'][1]:g}"
        print(f"{r['shot']:10} {span:>13} {r['hero_median']:>6.2f}/{r['hero_min']:<6.2f} {r['empty_s']:>5.1f}s "
              f"{str(r.get('still_pct', '-')) + '%':>6} {str(r.get('hold_s', '-')) + 's':>6}  {r.get('hold_class', '-'):13} "
              f"{' '.join(r['flags']) or 'OK'}")


def run(o):
    box = tuple(float(v) for v in o.content.split(","))
    src = Path(o.input)
    if o.each:
        rows = []
        for f in sorted(p for p in src.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")):
            arr, size = image(f); lum = luminance(box_of(arr, box)); px = hero_px(lum, ground_of(lum, o.ground), o.fg_delta)
            rows.append({"image": f.name, "size": list(size), "hero_px": round(px, 1), "hero": round(px / lum.shape[0], 3),
                         "box_h_px": lum.shape[0]})
            print(f"{f.name:40} hero {px:6.1f} px of {lum.shape[0]} = {px / lum.shape[0]:.3f}")
    else:
        frames, dt, desc = video_frames(src, o.t_from, o.t_to) if src.is_file() else dir_frames(src, o.fps)
        recs = measure(frames, box, o.ground, o.fg_delta)
        if not recs:
            sys.exit(f"no frames decoded from {src}")
        rows = [summarize(recs, n, a, b, dt, o) for n, a, b in parse_shots(o.shots, recs[0]["t"], recs[-1]["t"] + dt)]
        print_table(f"designed_frame_metrics {src} | {desc} | box {box} | sample {dt:.3f} s | ground {o.ground} | "
                    f"{'opencv' if cv2 is not None else 'scipy'} | floors hero {o.hero_floor} empty {o.empty_floor}/{o.empty_max}s "
                    f"still {o.still_thr}/{o.still_max}% hold {o.hold_max}s", rows)
    if o.json:
        Path(o.json).write_text(json.dumps(rows, indent=1))
    return rows


def selftest(o):
    """Known-answer cases on synthetic frames: an empty canvas, a moving and a held hero, the type-line merge,
    small-area motion, and the video decode path."""
    W, H, F = 1280, 720, 30; ok = True

    def frames(draw, n=60):
        out = []
        for f in range(0, n, 3):
            a = np.zeros((H, W, 3), np.uint8); draw(a, f); out.append((f / F, a))
        return out

    def box(a, x, y, w, h, v=255):
        a[y:y + h, x:x + w] = v

    def check(name, cond, detail):
        nonlocal ok
        ok &= bool(cond); print(f"selftest {name:14} {'PASS' if cond else 'FAIL'}  {detail}")

    full = (0.0, 0.0, 1.0, 1.0)
    r = summarize(measure(frames(lambda a, f: None), full, "auto", 120), "empty", 0, 2, 0.1, o)
    check("empty-canvas", r["flags"] == ["EMPTY", "STILL", "HOLD"] and r["hold_class"] == "TRUE-STILL", r)
    r = summarize(measure(frames(lambda a, f: box(a, 100 + 8 * f, 210, 400, 300)), full, "auto", 120), "moving", 0, 2, 0.1, o)
    check("moving-hero", abs(r["hero_median"] - 312 / 720) < 0.01 and r["flags"] == [] and r["still_pct"] == 0, r)
    r = summarize(measure(frames(lambda a, f: box(a, 100, 210, 400, 300)), full, "auto", 120), "held", 0, 2, 0.1, o)
    check("held-hero", r["flags"] == ["STILL", "HOLD"] and r["hold_class"] == "TRUE-STILL" and abs(r["hero_median"] - 0.433) < 0.01, r)
    line = np.zeros((H, W), np.int32); sparse = np.zeros((H, W), np.int32)
    for i in range(8):
        line[300:360, 200 + i * 70:240 + i * 70] = 255; sparse[300:360, 100 + i * 100:140 + i * 100] = 255
    m, s = hero_px(line, 0, 120), hero_px(sparse, 0, 120)
    check("type-line", abs(m - 115.2) < 2 and abs(s - 72) < 1, f"merged {m:.1f} px (want 115.2) · spaced {s:.1f} px (want 72)")
    r = summarize(measure(frames(lambda a, f: (box(a, 700, 150, 400, 300), box(a, 60 + 8 * f, 600, 40, 40, 60))), full, "auto", 120),
                  "small-motion", 0, 2, 0.1, o)
    check("small-motion", "HOLD" in r["flags"] and r.get("hold_class") == "SMALL-MOTION", r)
    with tempfile.TemporaryDirectory() as td:
        mp4 = Path(td) / "moving.mp4"
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "640x360", "-r", "30",
                              "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(mp4)], stdin=subprocess.PIPE)
        for f in range(30):
            a = np.zeros((360, 640, 3), np.uint8); a[105:255, 60 + 4 * f:260 + 4 * f] = 255; p.stdin.write(a.tobytes())
        p.stdin.close(); p.wait()
        gen, dt, _ = video_frames(mp4); recs = measure(gen, full, "auto", 120)
        r = summarize(recs, "video", 0, 1, dt, o)
        check("video-decode", len(recs) == 10 and abs(r["hero_median"] - 162 / 360) < 0.02 and r["flags"] == [], r)
    print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({'opencv' if cv2 is not None else 'scipy'} path)")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?"); ap.add_argument("--fps", type=float, default=30.0, help="frame rate of a frames directory")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0, help="video input: start second")
    ap.add_argument("--to", dest="t_to", type=float, default=None, help="video input: end second")
    ap.add_argument("--content", default="0,0,1,1", help="content box as fractions x0,y0,x1,y1 (exclude captions, HUD, progress bar)")
    ap.add_argument("--shots", default="", help='"SC01:0-4.2,SC02:4.2-9" in seconds; default = one shot over the whole input')
    ap.add_argument("--hero-floor", type=float, default=0.33); ap.add_argument("--empty-floor", type=float, default=0.21)
    ap.add_argument("--empty-max", type=float, default=1.5); ap.add_argument("--still-thr", type=float, default=0.35)
    ap.add_argument("--still-max", type=float, default=40.0); ap.add_argument("--hold-max", type=float, default=1.0)
    ap.add_argument("--ground", default="auto"); ap.add_argument("--fg-delta", type=float, default=120.0)
    ap.add_argument("--each", action="store_true", help="every image in the directory is its own shot (hero only)")
    ap.add_argument("--json"); ap.add_argument("--selftest", action="store_true")
    o = ap.parse_args()
    if o.selftest:
        sys.exit(0 if selftest(o) else 1)
    if not o.input:
        ap.error("an input clip or frames directory is required (or --selftest)")
    run(o)


if __name__ == "__main__":
    main()
