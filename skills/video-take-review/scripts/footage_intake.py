#!/usr/bin/env python3
"""footage_intake.py - break a pack of SUPPLIED clips down before anyone picks from it: per clip, the measurements and the
three tiers of sheet a read is allowed to rest on. Sources are read, never written; every output is a new file.

Per clip, under <out>/<clip id>/:
  measurements.json   sha256 + bytes (so a later pass can prove the masters are untouched), the probe, frames, fps, the
                      DISPLAY raster, the centred delivery-aspect crop, cut candidates (the installed qc_seed rule), motion,
                      colour steps, the sheet list, and the instrument's self-tests
  per-frame.csv       frame, timecode, dx/dy (phase correlation at 320 wide), response, cut diff, mean RGB step
  overview.jpg        N evenly spaced frames on ONE page          -> groups clips into camera ROUTES; composition only
  survey-NN.jpg       every k-th frame                            -> what is in frame over the WHOLE clip; composition only
  allframes-NN.jpg    every frame                                 -> window boundaries, a transient between survey samples
  visual-read.md      a stub for the written read (created once, never overwritten)
A claim about DETAIL (do units match, what a sign says, is a face recognisable, does focus hold) rests on none of these:
it needs a native-size crop (`window_frames.py`). The delivery-aspect crop is drawn on every tile that is wider than it.

What the motion numbers can and cannot say. `speed` is image displacement, not camera-versus-subject. On a clip whose frame
rate was conformed by dropping frames, a pan carries a recurring DOUBLE step: `double_step_fraction` reads that cadence, and
the smoothed residual along the pan axis reads it too - which is why SHAKE is read on the axis the move does not use.
Mean RGB steps move with composition; they locate an exposure or white-balance step for the eye, they do not prove one.

  footage_intake.py --src <dir | files...> --out <review dir> [--aspect 9:16] [--delivery-width 1080] [--id-regex '_(\\d{4})_']
                    [--overview 12] [--survey-every 4] [--no-allframes] [--no-hash] [--only <substr>]
  footage_intake.py --selftest
Sentinel: FOOTAGE-INTAKE-END.
"""
import argparse, ast, csv, glob, hashlib, json, os, re, subprocess, sys
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

cv2.setNumThreads(1)
HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO_RE = re.compile(r"\.(mp4|mov|m4v|mkv|mts)$", re.I)


def load_cut_rule():
    """The cut rule is single-sourced in qc_seed.py, which is not import-safe: lift the one function out of its source."""
    src = open(os.path.join(HERE, "qc_seed.py")).read()
    node = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "cut_frames")
    ns = {"np": np}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "qc_seed.cut_frames", "exec"), ns)
    return ns["cut_frames"]


def font(size=13):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def motion(a, b):
    (dx, dy), resp = cv2.phaseCorrelate(a.astype(np.float32), b.astype(np.float32))
    return dx, dy, resp


def cadence(shifts, min_speed=0.5):
    """Dropped or repeated frames from a frame-rate conform, read on the DOMINANT axis of the move.
    A frame is a double step when it moves >= 1.7x the median of its six neighbours, a held frame when <= 0.25x, counted
    only where the move is fast enough to tell (neighbour median >= min_speed px at 320 wide)."""
    s = np.abs(np.asarray(shifts, float)); n = len(s); dbl = held = told = 0
    for i in range(n):
        nb = np.concatenate([s[max(0, i - 3):i], s[i + 1:i + 4]])
        if len(nb) < 4:
            continue
        med = float(np.median(nb))
        if med < min_speed:
            continue
        told += 1; dbl += s[i] >= 1.7 * med; held += s[i] <= 0.25 * med
    if told < 12:
        return {"frames_fast_enough_to_tell": int(told), "verdict": "the clip never moves fast enough to show a conform cadence"}
    fd, fh = dbl / told, held / told
    verdict = ("DROPPED-FRAME cadence: a same-speed conform from a faster source - fast pans will stutter" if 0.10 <= fd <= 0.40 else
               "HELD-FRAME cadence: a same-speed conform from a slower source, or duplicated frames" if 0.10 <= fh <= 0.40 else
               "UNCLEAR: some double or held steps, but the move is too slow to read a cadence - judge by the step size at the delivery width" if max(fd, fh) >= 0.04 else "even motion")
    return {"frames_fast_enough_to_tell": int(told), "double_step_fraction": round(fd, 3), "held_frame_fraction": round(fh, 3), "verdict": verdict}


def selftests(cut_frames):
    rng = np.random.default_rng(7); a = rng.random((180, 320)).astype(np.float32) * 100
    zero = motion(a, a); shift = motion(a, np.roll(np.roll(a, 3, 1), -2, 0))
    flat = np.full((20, 20, 3), 80., np.float32); warm = flat.copy(); warm[:, :, 0] += 15
    bright = float((flat + 20).mean() - flat.mean()); wb = (warm.mean((0, 1)) - flat.mean((0, 1))).tolist()
    drop = cadence(np.tile([2.0, 2.0, 2.0, 4.0], 30)); even = cadence(np.full(120, 2.0)); hold = cadence(np.tile([2.0, 2.0, 2.0, 2.0, 0.0], 24)); still = cadence(np.full(120, 0.05))
    d = np.full(80, 0.01); d[39] = 0.5; hard = cut_frames(d, .12, 3.); pan = cut_frames(np.full(80, 0.33), .12, 3.)
    r = {"phase_static_want_0_0": [round(zero[0], 3), round(zero[1], 3)], "phase_shift_want_3_-2": [round(shift[0], 3), round(shift[1], 3)],
         "brightness_step_want_20": bright, "rgb_step_want_15_0_0": wb, "cadence_1112_pattern_want_DROPPED": drop["verdict"][:7], "cadence_even_want_even": even["verdict"],
         "cadence_every_5th_held_want_HELD": hold["verdict"][:4], "cadence_static_want_never": still["verdict"][:14], "cut_hard_want_[40]": hard, "cut_sustained_motion_want_[]": pan}
    ok = (abs(zero[0]) < .02 and abs(zero[1]) < .02 and abs(shift[0] - 3) < .02 and abs(shift[1] + 2) < .02 and bright == 20 and wb == [15, 0, 0]
          and drop["verdict"].startswith("DROPPED") and even["verdict"] == "even motion" and hold["verdict"].startswith("HELD") and "never" in still["verdict"] and hard == [40] and pan == [])
    r["PASS"] = bool(ok)
    return r


def display_probe(p):
    o = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_streams", "-show_format", "-of", "json", p], capture_output=True, text=True).stdout)
    st = o["streams"][0]; w, h = st["width"], st["height"]
    sar = st.get("sample_aspect_ratio", "1:1")
    if sar and sar not in ("1:1", "0:1", "N/A"):
        a, b = (int(v) for v in sar.split(":")); w = round(w * a / b)
    rot = 0
    for sd in st.get("side_data_list", []):
        rot = int(sd.get("rotation", rot) or rot)
    rot = int(st.get("tags", {}).get("rotate", rot) or rot)
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, den = (int(v) for v in st["r_frame_rate"].split("/"))
    return o, st, w, h, num / den, int(st.get("nb_read_packets") or st.get("nb_frames") or 0)


class Pages:
    """Tiles flushed page by page, so a long clip never sits in memory."""
    def __init__(self, out, stem, title, tile_w, cols, per_page, crop_frac, fnt):
        self.out, self.stem, self.title, self.w, self.cols, self.per, self.crop, self.f = out, stem, title, tile_w, cols, per_page, crop_frac, fnt
        self.tiles, self.page, self.paths = [], 0, []

    def add(self, rgb, label):
        h = round(rgb.shape[0] * self.w / rgb.shape[1]); t = Image.fromarray(rgb).resize((self.w, h), Image.LANCZOS)
        if self.crop is not None:
            cw = self.w * self.crop; x = (self.w - cw) / 2
            ImageDraw.Draw(t).rectangle((x, 0, x + cw, h - 1), outline="#00ffff", width=2)
        self.tiles.append((t, label))
        if len(self.tiles) == self.per:
            self.flush()

    def flush(self):
        if not self.tiles:
            return
        self.page += 1; h = self.tiles[0][0].height; rows = -(-len(self.tiles) // self.cols)
        im = Image.new("RGB", (self.cols * self.w, rows * (h + 21) + 28), "#151515"); d = ImageDraw.Draw(im); d.text((5, 5), self.title, font=self.f, fill="white")
        for k, (t, label) in enumerate(self.tiles):
            x, y = k % self.cols * self.w, k // self.cols * (h + 21) + 28
            im.paste(t, (x, y + 21)); d.text((x + 3, y + 2), label, font=self.f, fill="#ffe678")
        name = f"{self.stem}.jpg" if self.per >= 10 ** 6 else f"{self.stem}-{self.page:02}.jpg"
        path = os.path.join(self.out, name)
        if not os.path.exists(path):
            im.save(path, quality=85)
        self.paths.append(path); self.tiles = []


def intake(p, ordinal, out_root, clip_id, a, cut_frames, tests, fnt):
    out = os.path.join(out_root, clip_id)
    if os.path.exists(os.path.join(out, "measurements.json")):
        print(f"{ordinal:02} {clip_id} already measured - skipped (new files only)", flush=True); return
    os.makedirs(out, exist_ok=True)
    probe, st, w, h, fps, n_expect = display_probe(p)
    aw, ah = (int(v) for v in a.aspect.split(":")); crop_w = min(w, h * aw / ah); crop_frac = None if crop_w >= w - 1 else crop_w / w
    ifps = max(1, round(fps)); tc = lambda i: f"{i // (ifps * 3600):02}:{i // (ifps * 60) % 60:02}:{i // ifps % 60:02}:{i % ifps:02}"
    sw = 640; sh = round(h * sw / w); sh += sh % 2
    over_idx = set(round(i * (max(n_expect, 1) - 1) / (a.overview - 1)) for i in range(a.overview)) if n_expect else set()
    crop_note = f"cyan = centred {a.aspect}" if crop_frac else f"source already {a.aspect} or narrower"
    pages_all = None if a.no_allframes else Pages(out, "allframes", f"{clip_id} EVERY frame / {crop_note}", 240, 8, 48, crop_frac, fnt)
    pages_sur = Pages(out, "survey", f"{clip_id} every {a.survey_every}th frame / {crop_note}", 320, 6, 36, crop_frac, fnt)
    pages_ovr = Pages(out, "overview", f"{clip_id}  {w}x{h}  {n_expect} f  {fps:.3f} fps  / {crop_note}", 346 if w >= h else 260, 3 if w >= h else 4, 10 ** 6, crop_frac, fnt)
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-nostdin", "-threads", "2", "-i", p, "-vf", f"scale={sw}:{sh}", "-an", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    rows, shifts, tiny_prev, tinies_diff, prev_g, prev_rgbmean, n = [], [], None, [], None, None, 0
    while True:
        raw = proc.stdout.read(sw * sh * 3)
        if not raw:
            break
        if len(raw) != sw * sh * 3:
            sys.exit(f"short frame from the decoder on {p}")
        f = np.frombuffer(raw, np.uint8).reshape(sh, sw, 3)
        g = cv2.cvtColor(cv2.resize(f, (320, round(sh / 2))), cv2.COLOR_RGB2GRAY); tiny = cv2.resize(g, (48, 27)).astype(float) / 255; m = f.reshape(-1, 3).mean(0)
        if prev_g is not None:
            dx, dy, resp = motion(prev_g, g); diff = float(np.abs(tiny - tiny_prev).mean()); step = m - prev_rgbmean
            shifts.append((dx, dy)); tinies_diff.append(diff); rows.append([n, tc(n), dx, dy, resp, diff, float(step.mean()), *step.tolist()])
        prev_g, tiny_prev, prev_rgbmean = g, tiny, m
        label = f"f{n} {tc(n)}"
        if pages_all:
            pages_all.add(f, label)
        if n % a.survey_every == 0:
            pages_sur.add(f, label)
        if n in over_idx:
            pages_ovr.add(f, f"f{n}  {n / fps:.2f}s")
        n += 1
    if proc.wait() != 0 or n == 0:
        sys.exit(f"decode failed on {p}")
    for pg in (pages_all, pages_sur, pages_ovr):
        if pg:
            pg.flush()
    sh_arr = np.array(shifts) if shifts else np.zeros((0, 2)); cuts = cut_frames(np.array(tinies_diff), .12, 3.) if tinies_diff else []
    with open(os.path.join(out, "per-frame.csv"), "x", newline="") as fh:
        wr = csv.writer(fh); wr.writerow(["frame", "tc", "dx_at320", "dy_at320", "phase_response", "cut_diff", "mean_rgb_step", "R_step", "G_step", "B_step"]); wr.writerows(rows)
    mot = {}
    if len(sh_arr) > 24:
        axis = int(np.median(np.abs(sh_arr[:, 1])) > np.median(np.abs(sh_arr[:, 0]))); other = 1 - axis; k = 12
        res = lambda v: np.abs(v - np.convolve(v, np.ones(k) / k, mode="same"))[k // 2:-(k // 2)]
        speed = np.abs(sh_arr[:, axis]); to_delivery = (w / 320) * (a.delivery_width / crop_w)
        mot = {"instrument": "phase correlation at 320 wide, consecutive frames; image displacement, not camera-versus-subject",
               "move_axis": "xy"[axis], "speed_px320_mean": round(float(speed.mean()), 3), "speed_px320_p90": round(float(np.percentile(speed, 90)), 3),
               "speed_frame_widths_per_s_in_delivery_crop_mean": round(float(speed.mean()) / 320 * (w / crop_w) * fps, 3),
               "step_px_at_delivery_width_mean": round(float(speed.mean()) * to_delivery, 1), "step_px_at_delivery_width_p90": round(float(np.percentile(speed, 90)) * to_delivery, 1),
               "cadence": cadence(sh_arr[:, axis]),
               "shake_px320_on_the_axis_the_move_does_not_use": {"mean": round(float(res(sh_arr[:, other]).mean()), 3), "p90": round(float(np.percentile(res(sh_arr[:, other]), 90)), 3)},
               "residual_px320_on_the_move_axis_READS_CADENCE_NOT_SHAKE": {"mean": round(float(res(sh_arr[:, axis]).mean()), 3), "p90": round(float(np.percentile(res(sh_arr[:, axis]), 90)), 3)},
               "fastest_frames": [int(i) + 1 for i in np.argsort(-speed)[:8]]}
    big = sorted(rows, key=lambda r: -abs(r[6]))[:6]
    rec = {"ordinal": ordinal, "clip": clip_id, "source": p, "bytes": os.path.getsize(p), "frames": n, "fps": round(fps, 5), "duration_s": round(n / fps, 4), "last_frame": n - 1,
           "display": [w, h], "delivery_aspect": a.aspect, "delivery_width": a.delivery_width, "centre_crop_xywh": [round((w - crop_w) / 2, 1), 0, round(crop_w, 1), h],
           "crop_width_vs_delivery": round(crop_w / a.delivery_width, 3), "cut_candidates": cuts, "cut_rule": "qc_seed.cut_frames: diff > 0.12 and > 3x the median of the +/-12 neighbours; an empty list is not proof of no cut",
           "motion": mot, "colour": {"instrument": "whole-frame mean RGB step; moves with composition - it locates a step for the eye, it does not prove one", "largest_steps": [[r[0], r[1], round(r[6], 3)] for r in big]},
           "sheets": {"overview": pages_ovr.paths, "survey": pages_sur.paths, "allframes": pages_all.paths if pages_all else []}, "selftests": tests,
           "probe": {"codec": st.get("codec_name"), "profile": st.get("profile"), "pix_fmt": st.get("pix_fmt"), "coded": [st["width"], st["height"]], "r_frame_rate": st["r_frame_rate"],
                     "avg_frame_rate": st.get("avg_frame_rate"), "colour": [st.get("color_primaries"), st.get("color_transfer"), st.get("color_space"), st.get("color_range")], "format_duration": probe["format"].get("duration")}}
    if not a.no_hash:
        hsh = hashlib.sha256()
        with open(p, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 22), b""):
                hsh.update(b)
        rec["sha256"] = hsh.hexdigest()
    with open(os.path.join(out, "measurements.json"), "x") as fh:
        json.dump(rec, fh, indent=1)
    stub = os.path.join(out, "visual-read.md")
    if not os.path.exists(stub):
        open(stub, "w").write(f"# {clip_id} - whole-clip read (PROVISIONAL until the operator picks)\n\nSource `{os.path.basename(p)}` - {n} f at {fps:.3f} fps - display {w}x{h} - sheets read: <list them>\n\n"
                              "| frames | what is in frame | what the delivery crop keeps / loses (and the crop x that keeps the subject) |\n|---|---|---|\n| f0- |  |  |\n\n"
                              "**Route:** <same subject + same move as which other clips; which aspect mode this file is>\n\n**Candidate windows:** <frames, crop x, which line or visual each could serve>\n\n"
                              "**Seen, stated as seen:** <readable text, unit numbers, faces, anything a viewer could recognise - only from native crops>\n\n"
                              "**NOT claimed:** <year, model, configuration, anything the picture cannot prove -> the fact-check list>\n\n**Not in this clip:** <a requested visual that is absent>\n")
    c = mot.get("cadence", {}).get("verdict", "too short to read motion")
    print(f"{ordinal:02} {clip_id} {n} f {w}x{h} cuts={cuts} step@delivery mean {mot.get('step_px_at_delivery_width_mean', '-')} px | {c}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", nargs="+"); ap.add_argument("--out"); ap.add_argument("--aspect", default="9:16"); ap.add_argument("--delivery-width", type=int, default=1080)
    ap.add_argument("--id-regex", help="one capture group that names the clip, e.g. '_(\\d{4})_'; default: the file stem"); ap.add_argument("--overview", type=int, default=12)
    ap.add_argument("--survey-every", type=int, default=4); ap.add_argument("--no-allframes", action="store_true"); ap.add_argument("--no-hash", action="store_true")
    ap.add_argument("--only"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    cut_frames = load_cut_rule(); tests = selftests(cut_frames)
    print("SELF-TEST", "PASS" if tests["PASS"] else "FAIL", json.dumps(tests), flush=True)
    if not tests["PASS"]:
        sys.exit(1)
    if a.selftest:
        return
    if not (a.src and a.out):
        ap.error("--src and --out")
    files = []
    for s in a.src:
        files += sorted(f for f in glob.glob(os.path.join(s, "*")) if VIDEO_RE.search(f)) if os.path.isdir(s) else [s]
    if a.only:
        files = [f for f in files if a.only in f]
    if not files:
        sys.exit("no clips")
    os.makedirs(a.out, exist_ok=True); fnt = font(); ids = {}
    for k, p in enumerate(files, 1):
        m = re.search(a.id_regex, os.path.basename(p)) if a.id_regex else None
        cid = re.sub(r"[^A-Za-z0-9._-]+", "_", m.group(1) if m else os.path.splitext(os.path.basename(p))[0])
        if cid in ids:
            sys.exit(f"two clips share the id {cid}: {ids[cid]} and {p} - widen --id-regex")
        ids[cid] = p
        intake(p, k, a.out, cid, a, cut_frames, tests, fnt)
    print(f"FOOTAGE-INTAKE-END {len(files)} clip(s) under {a.out}", flush=True)


if __name__ == "__main__":
    main()
