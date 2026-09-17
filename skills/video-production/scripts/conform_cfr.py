#!/usr/bin/env python3
"""conform_cfr.py - supplied footage to ONE constant frame rate, as new masters, with the MOTION COST stated first.

A frame-rate conform is never free, and the two honest ways to do it cost different things:

  same-speed   nearest-frame selection (`fps=<target>`): real time is kept and the audio stays usable, but frames are
               DROPPED (source faster than target) or REPEATED (slower). 29.97 -> 24 drops one frame in five, so every
               4th output frame carries a double step: invisible on a slow move, a stutter on a fast pan.
  all-frames   every source frame kept and replayed at the target rate: motion stays perfectly even and every frame is
               a real one, but the clip runs slower or faster (29.97 -> 24 = 0.80x, 25 % longer) and its audio is dropped.

Frame blending and optical-flow interpolation are not offered: both manufacture frames the camera never shot.

`--plan` prints what each mode does to every source and converts nothing. A conversion needs `--mode`, so the choice is
always made on purpose - and made BEFORE anyone deletes an original: a same-speed master cannot give its dropped frames back.

Every output is verified before it counts: both rates equal the target, one packet duration (CFR), the frame count the mode
predicts, the source raster and pixel format, a clean full decode, and SSIM of the whole output against its own source
passed through the same frame mapping. Never overwrites. Byte-identical duplicate sources ("name(1).MP4" download copies)
are listed and skipped. `--receipt` writes the provenance (source sha256, probes, SSIM, checks). Sentinel: CONFORM-CFR-END.

  conform_cfr.py --dir <footage dir> --fps 24 --plan
  conform_cfr.py --dir <footage dir> --fps 24 --mode same-speed [--crf 14] [--preset medium] [--only <substr>] [--receipt <json>]
  conform_cfr.py --files a.mp4 b.mov --fps 24 --mode all-frames --receipt <json>
  conform_cfr.py --selftest
"""
import argparse, glob, hashlib, json, os, re, subprocess, sys, tempfile, time
from fractions import Fraction

VIDEO_RE = re.compile(r"\.(mp4|mov|m4v|mkv|mts)$", re.I)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(p):
    o = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,avg_frame_rate,nb_frames,nb_read_packets,"
                        "color_space,color_transfer,color_primaries,color_range:format=duration,size", "-of", "json", p]).stdout)
    s = o["streams"][0]
    s.update(o["format"])
    s["frames"] = int(s.get("nb_read_packets") or s.get("nb_frames") or 0)
    return s


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def cost(src_fps, tgt):
    """What each mode does to a source at src_fps, as plain sentences and numbers."""
    r = Fraction(src_fps) / Fraction(tgt)
    if r == 1:
        return {"same_speed": "already at the target rate", "all_frames": "already at the target rate", "ratio": 1.0}
    if r > 1:
        keep = Fraction(1) / r
        ss = (f"drops {float(1 - keep) * 100:.1f} % of the frames (keeps about {keep.limit_denominator(12)}): "
              f"a recurring DOUBLE step - invisible on a slow move, a stutter on a fast pan")
    else:
        ss = f"repeats {float(1 / r - 1) * 100:.1f} % of the frames: a recurring HELD frame - visible on any steady move"
    af = f"plays at {float(1 / r):.3f}x speed ({float(r - 1) * 100:+.1f} % length), every frame real, audio dropped"
    return {"same_speed": ss, "all_frames": af, "ratio": float(r)}


def colour_args(s):
    a = []
    for k, flag in (("color_primaries", "-color_primaries"), ("color_transfer", "-color_trc"), ("color_space", "-colorspace"), ("color_range", "-color_range")):
        v = s.get(k)
        if v and v not in ("unknown", "unspecified"):
            a += [flag, v]
    return a


def convert(p, out, s, tgt, mode, crf, preset):
    tmp = out + ".part.mp4"
    if mode == "same-speed":
        vf, amap, acodec = f"fps={tgt}", ["-map", "0:a:0?"], ["-c:a", "copy"]
    else:
        vf, amap, acodec = f"setpts=N/({tgt})/TB", [], ["-an"]
    cmd = (["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", p, "-map", "0:v:0"] + amap + ["-map_metadata", "0", "-vf", vf, "-r", str(tgt), "-fps_mode", "cfr",
           "-c:v", "libx265", "-preset", preset, "-crf", str(crf), "-pix_fmt", s["pix_fmt"], "-tag:v", "hvc1", "-x265-params", "log-level=error"]
           + colour_args(s) + acodec + ["-write_tmcd", "0", "-metadata:s:v:0", "timecode=", "-movflags", "+faststart", tmp])
    r = run(cmd)
    if r.returncode or not os.path.exists(tmp):
        return r.stderr[-400:]
    os.replace(tmp, out)      # tmp is this run's own file; `out` was checked absent by the caller
    return None


def verify(p, out, s, tgt, mode):
    o = probe(out)
    tf = Fraction(tgt)
    want = s["frames"] if mode == "all-frames" else round(float(s["duration"]) * tf)
    pk = set(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=duration_time", "-of", "csv=p=0", out]).stdout.split())
    dec = run(["ffmpeg", "-v", "error", "-nostdin", "-i", out, "-f", "null", "-"])
    ref = f"fps={tgt}" if mode == "same-speed" else f"setpts=N/({tgt})/TB"
    ss = run(["ffmpeg", "-v", "info", "-nostdin", "-i", out, "-i", p, "-lavfi", f"[0:v]setpts=N/({tgt})/TB[a];[1:v]{ref},setpts=N/({tgt})/TB[b];[a][b]ssim", "-f", "null", "-"]).stderr
    m = re.search(r"SSIM .*All:([0-9.]+)", ss)
    ssim = float(m.group(1)) if m else 0.0
    rate = f"{tf.numerator}/{tf.denominator}"
    checks = {"rate": o["r_frame_rate"] == rate and o["avg_frame_rate"] == rate, "cfr_one_packet_duration": len(pk) == 1,
              "frames": abs(o["frames"] - want) <= (0 if mode == "all-frames" else 1), "raster": (o["width"], o["height"]) == (s["width"], s["height"]),
              "pix_fmt": o["pix_fmt"] == s["pix_fmt"], "decodes_clean": dec.returncode == 0 and not dec.stderr.strip(), "ssim_ge_0.985": ssim >= 0.985}
    return o, want, ssim, checks


def selftest():
    """A synthetic 30000/1001 clip through both modes: same-speed must land on duration x target, all-frames must keep every frame."""
    d = tempfile.mkdtemp(prefix="conform-cfr-selftest-")
    src = os.path.join(d, "synthetic.mp4")
    r = run(["ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30000/1001:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", src])
    if r.returncode:
        print("SELFTEST FAIL: could not build the synthetic source:", r.stderr[-200:]); return 1
    s = probe(src); ok = True
    for mode in ("same-speed", "all-frames"):
        out = os.path.join(d, f"out-{mode}.mp4")
        err = convert(src, out, s, "24", mode, 8, "fast")
        if err:
            print(f"SELFTEST FAIL {mode}: {err}"); ok = False; continue
        o, want, ssim, checks = verify(src, out, s, "24", mode)
        good = all(checks.values())
        print(f"SELFTEST {mode}: source {s['frames']} f -> {o['frames']} f (want {want}), {float(o['duration']):.3f} s, SSIM {ssim:.4f} {'PASS' if good else 'FAIL ' + str(checks)}")
        ok &= good
    # negative control: the same-speed output read against the WRONG frame mapping must fail the SSIM check
    _, _, wrong, _ = verify(src, os.path.join(d, "out-same-speed.mp4"), s, "24", "all-frames")
    neg = wrong < 0.985
    print(f"SELFTEST wrong frame mapping is caught: SSIM {wrong:.4f} < 0.985 {'PASS' if neg else 'FAIL'}")
    ok &= neg
    c = cost(Fraction(30000, 1001), "24")
    known = abs(c["ratio"] - 1.24875) < 1e-4
    print(f"SELFTEST cost 29.97->24: ratio {c['ratio']:.5f} (want 1.24875) {'PASS' if known else 'FAIL'}")
    print("SELFTEST", "PASS" if ok and known else "FAIL", f"(scratch left in {d})")
    return 0 if ok and known else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir"); ap.add_argument("--files", nargs="+"); ap.add_argument("--fps", default="24", help="target rate: 24, 25, 30000/1001 ...")
    ap.add_argument("--mode", choices=["same-speed", "all-frames"]); ap.add_argument("--plan", action="store_true")
    ap.add_argument("--crf", type=int, default=14); ap.add_argument("--preset", default="medium"); ap.add_argument("--only"); ap.add_argument("--receipt")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not (a.dir or a.files):
        ap.error("--dir or --files")
    if not (a.plan or a.mode):
        ap.error("say --plan to read the motion cost, or --mode same-speed|all-frames to convert: the choice is never a default")
    if a.receipt and os.path.exists(a.receipt):
        sys.exit(f"refusing to overwrite the receipt {a.receipt}")
    tag = re.sub(r"[^0-9]", "p", str(a.fps))
    made = re.compile(rf"__{tag}fps(-allframes)?\.mp4$")
    src = a.files or [p for p in glob.glob(os.path.join(a.dir, "*")) if VIDEO_RE.search(p)]
    src = sorted((p for p in src if not made.search(p)), key=lambda p: (re.sub(r"\(\d+\)", "", p), len(p)))   # "name.MP4" sorts before its copy "name(1).MP4"
    if a.only:
        src = [p for p in src if a.only in p]
    if not src:
        sys.exit("no source files (a file named __<fps>fps.mp4 is this tool's own output and is never re-converted)")
    if a.plan:
        for p in src:
            s = probe(p); c = cost(Fraction(s["r_frame_rate"]), a.fps)
            print(f"{os.path.basename(p)}  {s['width']}x{s['height']} {s['pix_fmt']} {s['r_frame_rate']} fps {s['frames']} f {float(s['duration']):.2f} s\n    same-speed: {c['same_speed']}\n    all-frames: {c['all_frames']}")
        print("the double step on a pan = its speed in frame-widths per second x the delivery width / the target rate, in pixels; under ~5 px it does not read, near 30 px it stutters")
        print("CONFORM-CFR-END plan only, nothing converted")
        return
    hashes = {p: sha(p) for p in src}; seen = {}; ok_all = True
    rec = {"made": time.strftime("%Y-%m-%d %H:%M:%S"), "target_fps": a.fps, "mode": a.mode, "crf": a.crf, "preset": a.preset,
           "method": "fps filter, nearest frame, same speed, audio copied" if a.mode == "same-speed" else "every source frame replayed at the target rate, audio dropped", "files": []}
    for p in src:
        if hashes[p] in seen:
            print(f"DUPLICATE {os.path.basename(p)} == {os.path.basename(seen[hashes[p]])} (sha256) - skipped", flush=True)
            rec["files"].append({"source": p, "sha256": hashes[p], "duplicate_of": seen[hashes[p]]}); continue
        seen[hashes[p]] = p
        s = probe(p); c = cost(Fraction(s["r_frame_rate"]), a.fps)
        stem = re.sub(r"\(\d+\)(?=\.[^.]+$)", "", p)
        out = VIDEO_RE.sub(f"__{tag}fps{'-allframes' if a.mode == 'all-frames' else ''}.mp4", stem)
        print(f"{os.path.basename(p)}: {c['same_speed'] if a.mode == 'same-speed' else c['all_frames']}", flush=True)
        if os.path.exists(out):
            print(f"EXISTS {out} - not overwriting; verifying it", flush=True)
        else:
            t0 = time.time(); err = convert(p, out, s, a.fps, a.mode, a.crf, a.preset)
            if err:
                print(f"FAIL encode {p}: {err}", flush=True); ok_all = False; continue
            print(f"encoded {os.path.basename(out)} in {time.time() - t0:.0f} s", flush=True)
        o, want, ssim, checks = verify(p, out, s, a.fps, a.mode)
        good = all(checks.values()); ok_all &= good
        print(f"{'PASS' if good else 'FAIL ' + str([k for k, v in checks.items() if not v])} {os.path.basename(out)}  {o['width']}x{o['height']} {o['pix_fmt']} {o['frames']} f (want {want}) "
              f"{float(o['duration']):.3f} s  SSIM {ssim:.4f}  {int(o['size']) / 1048576:.1f} MB (source {int(s['size']) / 1048576:.1f} MB)", flush=True)
        rec["files"].append({"source": p, "sha256": hashes[p], "source_probe": s, "motion_cost": c, "output": out, "output_probe": o, "ssim_all": ssim, "checks": checks, "pass": good})
    if a.receipt:
        os.makedirs(os.path.dirname(os.path.abspath(a.receipt)), exist_ok=True)
        json.dump(rec, open(a.receipt, "w"), indent=1)
    n_ok = sum(1 for f in rec["files"] if f.get("pass")); n_dup = sum(1 for f in rec["files"] if "duplicate_of" in f)
    print(f"CONFORM-CFR-END {'ALL PASS' if ok_all else 'WITH FAILURES'} ({n_ok} converted and verified, {n_dup} duplicates skipped) - the originals stay until the cut is locked", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
