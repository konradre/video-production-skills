#!/usr/bin/env python3
"""preview_cut.py - a REVIEW PROXY of a recommended cut, over the programme audio, before anything is conformed or graded.

A recommended cut is a table until it moves. This renders the plan's slots - each a window of a source clip, cropped to the
delivery aspect at the offset the plan names - small, fast and labelled, against the real programme mix, so the operator
picks on picture. What is not made yet (a presenter's shot, the end card) is a grey slate with its label, never a stand-in.
Burned-in labels mark every frame as a proxy: it is not a deliverable and never goes to a client.

Plan (JSON):  {"fps": 24,
               "slots": [{"id": "S1", "tl_f": [117, 185], "pick": {"file": "<rel path>", "src_frames": [204, 271], "crop_x": 0}}, ...],
               "gaps":  [{"tl_f": [0, 117], "label": "HEAD 1 TO COME"}, ...]}          # optional; any uncovered span is slated
`tl_f` is [first frame, first frame of the NEXT slot]; `src_frames` is inclusive and must be exactly as long as the slot.
`crop_x` is the crop's left edge in SOURCE pixels (omit = centred). Extra keys are ignored, so a plan can carry its reasons.

--alt swaps one slot's pick for a side-by-side version without touching the plan:  --alt S1=<rel path>:<first frame>:<crop x>
--check-sheet writes the frame either side of EVERY cut to one image: read it before the preview goes anywhere - it proves
the right clip sits in every slot and that no slot starts or ends on a wrong frame.

  preview_cut.py --root <project> --plan <plan.json> --mix <programme.wav> --out <preview.mp4> [--size 540x960] [--aspect 9:16]
                 [--alt S1=clip.mp4:239:1312 ...] [--check-sheet <jpg>]
  preview_cut.py --selftest
Never overwrites. Sentinel: PREVIEW-END ok | PREVIEW-FAILED.
"""
import argparse, json, math, os, re, subprocess, sys, tempfile

FONTS = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    o = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=width,height,nb_read_packets", "-of", "json", path]).stdout)["streams"][0]
    return int(o["width"]), int(o["height"]), int(o.get("nb_read_packets") or 0)


def safe(text):
    return re.sub(r"[^A-Za-z0-9 ._-]+", " ", text).strip()


def build(root, plan, mix, out, size, aspect, alts, check_sheet):
    if os.path.exists(out):
        sys.exit(f"refusing to overwrite {out}")
    fps = plan["fps"]; W, H = size; aw, ah = aspect
    font = next((f for f in FONTS if os.path.exists(f)), None); ff = f"fontfile={font}:" if font else ""
    dur = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mix]).stdout)
    total = math.ceil(dur * fps - 1e-6)
    slots = sorted(plan["slots"], key=lambda s: s["tl_f"][0]); gaps = {tuple(g["tl_f"]): g.get("label", "TO COME") for g in plan.get("gaps", [])}
    segs, t = [], 0
    for s in slots:
        a, b = s["tl_f"]
        if a < t:
            sys.exit(f"slot {s['id']} starts at f{a}, inside the slot before it (which ends at f{t})")
        if a > t:
            segs.append(("slate", t, a, gaps.get((t, a), "TO COME")))
        p = dict(s["pick"])
        if s["id"] in alts:
            f, f0, x = alts[s["id"]]; p.update(file=f, src_frames=[f0, f0 + (b - a) - 1], crop_x=x)
        n = p["src_frames"][1] - p["src_frames"][0] + 1
        if n != b - a:
            sys.exit(f"slot {s['id']}: the window is {n} f, the slot is {b - a} f")
        segs.append(("clip", a, b, p, s["id"])); t = b
    if t < total:
        rest = sorted((g for g in gaps if g[0] >= t), key=lambda g: g[0]) or [(t, total)]
        for g in rest:
            segs.append(("slate", max(g[0], t), min(g[1], total), gaps.get(g, "TO COME"))); t = min(g[1], total)
        if t < total:
            segs.append(("slate", t, total, "TO COME"))
    inputs, fc, labels = [], [], []
    for i, sg in enumerate(segs):
        n = sg[2] - sg[1]
        if n <= 0:
            continue
        if sg[0] == "slate":
            inputs += ["-f", "lavfi", "-i", f"color=c=0x2a2a2a:s={W}x{H}:r={fps}:d={n / fps + 1:.6f}"]
            fc.append(f"[{len(labels)}:v]drawtext={ff}text='{safe(sg[3])}':fontcolor=0xbbbbbb:fontsize={max(14, H // 38)}:x=(w-tw)/2:y=(h-th)/2,trim=end_frame={n},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v{len(labels)}]")
        else:
            p, sid = sg[3], sg[4]; path = os.path.join(root, p["file"]); sw, sh, nb = probe(path); f0 = p["src_frames"][0]
            if nb and p["src_frames"][1] >= nb:
                sys.exit(f"slot {sid}: the window ends at f{p['src_frames'][1]} but {p['file']} has {nb} frames")
            cw, ch = (round(sh * aw / ah), sh) if sw * ah >= sh * aw else (sw, round(sw * ah / aw))
            x = p.get("crop_x"); x = (sw - cw) // 2 if x is None else int(x); y = (sh - ch) // 2
            if not 0 <= x <= sw - cw:
                sys.exit(f"slot {sid}: crop_x {x} leaves the frame (0..{sw - cw})")
            inputs += ["-i", path]
            fc.append(f"[{len(labels)}:v]trim=start_frame={f0}:end_frame={f0 + n},setpts=PTS-STARTPTS,crop={cw}:{ch}:{x}:{y},scale={W}:{H}:flags=lanczos,setsar=1,"   # setsar: a rounded crop leaves a SAR of 399:400 and concat refuses mixed SARs
                      f"drawtext={ff}text='PROXY {safe(sid)} {safe(os.path.basename(p['file']))[:26]} f{f0}-{f0 + n - 1}':fontcolor=white:borderw=2:bordercolor=black:fontsize={max(12, H // 54)}:x=10:y=10,format=yuv420p[v{len(labels)}]")
        labels.append(f"[v{len(labels)}]")
    fc.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[v]")
    r = run(["ffmpeg", "-v", "error", "-nostdin"] + inputs + ["-i", mix, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", f"{len(labels)}:a", "-r", str(fps),
             "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    if r.returncode or not os.path.exists(out):
        print(r.stderr[-1200:]); print("PREVIEW-FAILED"); return False
    _, _, got = probe(out); cuts = [sg[1] for sg in segs[1:] if sg[2] > sg[1]]
    print(f"rendered {out}: {got} frames (want {total}), {len([s for s in segs if s[0] == 'clip'])} slot(s), {len([s for s in segs if s[0] == 'slate'])} slate(s)")
    ok = abs(got - total) <= 1
    if check_sheet and ok:
        if os.path.exists(check_sheet):
            sys.exit(f"refusing to overwrite {check_sheet}")
        want = sorted(set(f for c in cuts for f in (c - 1, c) if 0 <= f < got)); sel = "+".join(f"eq(n\\,{f})" for f in want); cols = min(8, len(want)); rows = -(-len(want) // cols)
        tw = 200; th = round(tw * H / W)      # the frame number is drawn BEFORE `select`, so the sheet shows timeline frames, not the ordinal of the pick
        r2 = run(["ffmpeg", "-v", "error", "-nostdin", "-i", out, "-vf", f"drawtext={ff}text='f%{{n}}':fontcolor=yellow:borderw=3:bordercolor=black:fontsize={max(24, H // 22)}:x=12:y=h-th-14,select='{sel}',scale={tw}:{th},tile={cols}x{rows}", "-frames:v", "1", "-q:v", "3", check_sheet])
        print(f"check sheet {check_sheet}: the frame either side of {len(cuts)} cut(s) - READ IT" if r2.returncode == 0 else f"check sheet failed: {r2.stderr[-300:]}")
        ok &= r2.returncode == 0
    print("PREVIEW-END ok" if ok else "PREVIEW-FAILED")
    return ok


def selftest():
    d = tempfile.mkdtemp(prefix="preview-cut-selftest-")
    for name, src in (("a.mp4", "testsrc2=size=640x360:rate=24:duration=3"), ("b.mp4", "smptebars=size=360x640:rate=24:duration=3")):
        run(["ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i", src, "-c:v", "libx264", "-pix_fmt", "yuv420p", os.path.join(d, name)])
    run(["ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i", "sine=frequency=440:duration=4", os.path.join(d, "mix.wav")])
    plan = {"fps": 24, "slots": [{"id": "S1", "tl_f": [24, 48], "pick": {"file": "a.mp4", "src_frames": [10, 33], "crop_x": 100}}, {"id": "S2", "tl_f": [48, 72], "pick": {"file": "b.mp4", "src_frames": [0, 23]}}],
            "gaps": [{"tl_f": [0, 24], "label": "HEAD TO COME"}]}
    ok = build(d, plan, os.path.join(d, "mix.wav"), os.path.join(d, "preview.mp4"), (270, 480), (9, 16), {}, os.path.join(d, "check.jpg"))
    _, _, got = probe(os.path.join(d, "preview.mp4")) if ok else (0, 0, 0)
    good = ok and got == 96 and os.path.exists(os.path.join(d, "check.jpg"))
    print(f"SELFTEST a 4 s mix at 24 fps -> {got} frames (want 96): head slate, a landscape slot cropped at x=100, a vertical slot, a tail slate, the check sheet -> {'PASS' if good else 'FAIL'} (scratch {d})")
    return good


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True); ap.add_argument("--plan", required=True); ap.add_argument("--mix", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="540x960"); ap.add_argument("--aspect", default="9:16"); ap.add_argument("--alt", nargs="*", default=[]); ap.add_argument("--check-sheet")
    a = ap.parse_args(); alts = {}
    for item in a.alt:
        sid, rest = item.split("=", 1); f, f0, x = rest.rsplit(":", 2); alts[sid] = (f, int(f0), None if x in ("", "c") else int(x))
    ok = build(a.root, json.load(open(a.plan)), a.mix, a.out, tuple(int(v) for v in a.size.split("x")), tuple(int(v) for v in a.aspect.split(":")), alts, a.check_sheet)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
