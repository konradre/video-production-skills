#!/usr/bin/env python3
"""window_metrics.py - candidate WINDOWS of supplied clips, read at the DELIVERY shape, before one is picked for a slot.

A clip is not what ships: a window of it, cropped to the delivery aspect and scaled to the delivery raster, is. So every
candidate is decoded once through exactly that crop and scale, and read there. Per candidate: a 5-frame strip (a SURVEY
image - composition, never detail) and per-metric numbers. A table, never a total score; the eye on the strip is the verdict.

  sharp      Laplacian variance of luma at the delivery raster. Comparable ONLY between files of one camera route showing
             the same thing: texture (gravel, foliage) inflates it, a smooth subject filling the frame deflates it.
  luma, clip_hi, clip_lo   mean Y (0-255), % of pixels at or above 250, % at or below 5
  colour     Hasler-Susstrunk colourfulness
  speed      mean image speed through the delivery crop, in frame-widths per second   } from the intake's per-frame.csv
  step_px    mean and p90 frame-to-frame step at the delivery width, in pixels        } (footage_intake.py)
  cadence    the intake's dropped/held-frame read, on this window only
  shake      smoothed residual on the axis the move does NOT use, px at 320 wide

On a clip whose frame rate was conformed by dropping frames, `step_px` is the number that matters for looks: the recurring
double step is twice it. Under ~5 px it does not read; near 30 px a pan stutters.

Candidates file (JSON list): {"id", "slot", "clip", "file", "f0", "n", "x" (crop offset in source px, omit = centred),
"route" and "note" optional}. `file` is relative to --root. `clip` names the intake folder that holds per-frame.csv.

  window_metrics.py --root <project> --candidates <json> --out <dir> [--intake <intake dir>] [--aspect 9:16] [--raster 1080x1920] [--stack]
  window_metrics.py --selftest
Sentinel: WINDOW-METRICS-END.
"""
import argparse, csv, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def lap_var(y):
    y = y.astype(np.float64)
    return float((-4 * y[1:-1, 1:-1] + y[:-2, 1:-1] + y[2:, 1:-1] + y[1:-1, :-2] + y[1:-1, 2:]).var())


def colourfulness(rgb):
    r, g, b = (rgb[..., i].astype(np.float64) for i in range(3)); rg, yb = r - g, 0.5 * (r + g) - b
    return float(np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))


def selftest():
    flat = np.full((64, 64), 128, np.uint8); chk = (np.indices((64, 64)).sum(0) % 2 * 255).astype(np.uint8)
    grey = np.dstack([flat] * 3); red = np.zeros((64, 64, 3), np.uint8); red[..., 0] = 255
    # uniform red: rg = 255, yb = 127.5, both with zero spread -> 0.3 * sqrt(255^2 + 127.5^2) = 85.53
    st = {"lap_flat_want_0": lap_var(flat), "lap_checker_over_1e5": lap_var(chk) > 1e5, "colour_grey_want_0": colourfulness(grey), "colour_red_want_85.53": round(colourfulness(red), 2)}
    ok = st["lap_flat_want_0"] == 0 and st["lap_checker_over_1e5"] and st["colour_grey_want_0"] == 0 and abs(st["colour_red_want_85.53"] - 85.53) < 0.01
    print("SELF-TEST", "PASS" if ok else "FAIL", st, flush=True)
    return ok


def probe(path):
    o = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "json", path], capture_output=True, text=True).stdout)["streams"][0]
    num, den = (int(v) for v in o["r_frame_rate"].split("/"))
    return o["width"], o["height"], num / den


def stream_window(path, f0, n, crop, size, wanted):
    """One decode at the delivery raster; only the frames in `wanted` (offsets into the window) are kept."""
    w, h = size
    vf = f"trim=start_frame={f0}:end_frame={f0 + n},setpts=PTS-STARTPTS," + (f"crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]}," if crop else "") + f"scale={w}:{h}:flags=lanczos,format=rgb24"
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-vf", vf, "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    kept, k = {}, 0
    while True:
        raw = proc.stdout.read(w * h * 3)
        if len(raw) < w * h * 3:
            break
        if k in wanted:
            kept[k] = np.frombuffer(raw, np.uint8).reshape(h, w, 3).copy()
        k += 1
    proc.wait()
    return kept, k


def motion_of_window(intake, clip, f0, n, src_w, crop_w, fps, delivery_w):
    p = os.path.join(intake, clip, "per-frame.csv") if intake else None
    if not p or not os.path.exists(p):
        return {"note": "no per-frame.csv for this clip - run footage_intake.py first"}
    dx, dy = [], []
    for r in csv.DictReader(open(p)):
        if f0 < int(r["frame"]) < f0 + n:
            dx.append(float(r["dx_at320"])); dy.append(float(r["dy_at320"]))
    if len(dx) < 8:
        return {"note": "window too short to read motion"}
    sh = np.array([dx, dy]).T; axis = int(np.median(np.abs(sh[:, 1])) > np.median(np.abs(sh[:, 0]))); s = np.abs(sh[:, axis]); o = sh[:, 1 - axis]
    k = min(12, len(o) // 2 * 2 or 2); res = np.abs(o - np.convolve(o, np.ones(k) / k, mode="same"))[k // 2:-(k // 2) or None]
    from footage_intake import cadence      # the same rule the intake printed, on this window only
    to_px = (src_w / 320) * (delivery_w / crop_w)
    return {"speed_frame_widths_per_s": round(float(s.mean()) / 320 * (src_w / crop_w) * fps, 3), "step_px_mean": round(float(s.mean()) * to_px, 1), "step_px_p90": round(float(np.percentile(s, 90)) * to_px, 1),
            "cadence": cadence(s)["verdict"].split(":")[0], "shake_px320": round(float(res.mean()), 3) if len(res) else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root"); ap.add_argument("--candidates"); ap.add_argument("--out"); ap.add_argument("--intake"); ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--raster", default="1080x1920"); ap.add_argument("--stack", action="store_true", help="also stack the strips into one sheet per slot"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if not selftest():
        sys.exit(1)
    if a.selftest:
        return
    if not (a.root and a.candidates and a.out):
        ap.error("--root, --candidates and --out")
    W, H = (int(v) for v in a.raster.split("x")); aw, ah = (int(v) for v in a.aspect.split(":"))
    os.makedirs(a.out, exist_ok=True)
    try:
        fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
    except OSError:
        fnt = ImageFont.load_default()
    rows, strips = [], {}
    for c in json.load(open(a.candidates)):
        path = os.path.join(a.root, c["file"]); sw, sh, fps = probe(path); cw = round(sh * aw / ah)
        crop = None if cw >= sw else [int(c["x"]) if c.get("x") is not None else (sw - cw) // 2, 0, cw, sh]
        if crop and not 0 <= crop[0] <= sw - cw:
            sys.exit(f"{c['id']}: crop x {crop[0]} leaves the frame (0..{sw - cw})")
        f0, n = int(c["f0"]), int(c["n"]); idx = [0, n // 4, n // 2, 3 * n // 4, n - 1]
        kept, got = stream_window(path, f0, n, crop, (W, H), set(idx))
        if got < n:
            print(f"WARN {c['id']}: the window runs past the clip ({got} of {n} frames decoded)", flush=True)
        if not kept:
            sys.exit(f"{c['id']}: nothing decoded")
        frames = [kept[min(i, max(kept))] if i not in kept else kept[i] for i in idx]
        sharp, luma, hi, lo, col = [], [], [], [], []
        for fr in frames:
            y = 0.2126 * fr[..., 0] + 0.7152 * fr[..., 1] + 0.0722 * fr[..., 2]
            sharp.append(lap_var(y)); luma.append(float(y.mean())); hi.append(float((y >= 250).mean() * 100)); lo.append(float((y <= 5).mean() * 100)); col.append(colourfulness(fr))
        m = {"id": c["id"], "slot": c.get("slot"), "clip": c["clip"], "route": c.get("route"), "f0": f0, "n": n, "x": crop[0] if crop else 0, "crop_w_src": min(cw, sw), "crop_w_vs_delivery": round(min(cw, sw) / W, 3),
             "sharp": round(float(np.median(sharp)), 1), "luma": round(float(np.mean(luma)), 1), "clip_hi_pct": round(float(np.mean(hi)), 2), "clip_lo_pct": round(float(np.mean(lo)), 2), "colour": round(float(np.mean(col)), 1),
             "motion": motion_of_window(a.intake, c["clip"], f0, n, sw, min(cw, sw), fps, W), "note": c.get("note", "")}
        rows.append(m)
        tw, th = 270, round(270 * H / W); strip = Image.new("RGB", (5 * tw + 8, th + 26), (16, 16, 16)); d = ImageDraw.Draw(strip); mo = m["motion"]
        d.text((4, 3), f"{c['id']}  {c['clip']} f{f0}-{f0 + n - 1} x{m['x']}  sharp {m['sharp']:.0f}  luma {m['luma']:.0f}  hi {m['clip_hi_pct']}%  col {m['colour']:.0f}  step {mo.get('step_px_mean', '-')} px  {mo.get('cadence', '')}", fill=(255, 230, 120), font=fnt)
        for j, fr in enumerate(frames):
            strip.paste(Image.fromarray(fr).resize((tw, th), Image.LANCZOS), (4 + j * tw, 26))
        dst = os.path.join(a.out, f"strip-{c['id']}.jpg")
        if not os.path.exists(dst):
            strip.save(dst, quality=85)
        strips.setdefault(str(c.get("slot")), []).append(dst)
        print(json.dumps(m), flush=True)
    base = os.path.splitext(os.path.basename(a.candidates))[0]; mp = os.path.join(a.out, base + ".metrics.json")
    if os.path.exists(mp):
        sys.exit(f"refusing to overwrite {mp} - give the candidates file a new name for a new round")
    json.dump(rows, open(mp, "w"), indent=1)
    if a.stack:
        for slot, paths in strips.items():
            ims = [Image.open(p) for p in paths]; sheet = Image.new("RGB", (max(i.width for i in ims), sum(i.height for i in ims))); y = 0
            for i in ims:
                sheet.paste(i, (0, y)); y += i.height
            dst = os.path.join(a.out, f"{base}-slot-{slot}.jpg")
            if not os.path.exists(dst):
                sheet.save(dst, quality=85)
    print(f"WINDOW-METRICS-END {len(rows)} window(s) -> {mp}", flush=True)


if __name__ == "__main__":
    main()
