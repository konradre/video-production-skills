#!/usr/bin/env python3
"""topaz_upscale.py — video in -> tvai_up -> video out, from WSL.

Drives the bundled ffmpeg (`tvai_up` filter) of Topaz Video, or of Topaz Video AI before the rename, on the
Windows host directly from WSL. Model dirs are passed via WSLENV (no system env vars exist). The install and its
model folders are detected; TOPAZ_FFMPEG, TVAI_MODEL_DIR, TVAI_MODEL_DATA_DIR and TOPAZ_OUT_DIR override them. Encoder ladder
(ComfyUI-TopazVideoAI pattern): hevc_nvenc 10-bit -> h264_nvenc -> libx264 10-bit.
Optional post-scale (e.g. Rhea x4 -> lanczos 1080p).

Usage (WSL):
  python3 topaz_upscale.py --in <clip> [--model prob-4] [--scale 2]
      [--tvai "k=v:k=v"] [--post-scale 1080x1920] [--out-dir DIR]
Outputs <stem>__<model>x<scale>.mp4 + JSON result + TOPAZ-UPSCALE-OK sentinel.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Topaz renamed Topaz Video AI to Topaz Video in 2025. The renamed app installs under "Topaz Video" and keeps its
# models in ...\Topaz Video\models\models (Topaz's troubleshooting page) or ...\Topaz Video\models. Topaz Video AI
# 3.x-6.x keeps descriptions and data in ...\Topaz Video AI\models, with more data one level up. We measured the
# pipeline on Topaz Video AI 6.0.2.
PROGRAM_FILES = "/mnt/c/Program Files/Topaz Labs LLC"
PROGRAM_DATA = "/mnt/c/ProgramData/Topaz Labs LLC"
DISTRO = os.environ.get("WSL_DISTRO_NAME", "Ubuntu")

ENCODERS = [  # ladder: first that works wins
    ["-c:v", "hevc_nvenc", "-preset", "p5", "-cq", "19", "-pix_fmt", "p010le", "-tag:v", "hvc1"],
    ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19", "-pix_fmt", "yuv420p"],
    ["-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p10le"],
]


def win_path(p):
    p = str(p)
    if p.startswith("/mnt/") and len(p) > 6:
        return f"{p[5].upper()}:{p[6:]}".replace("/", "\\")
    if p.startswith("/"):
        return rf"\\wsl.localhost\{DISTRO}" + p.replace("/", "\\")
    return p


def wsl_path(p):
    if len(p) > 2 and p[1] == ":":
        return f"/mnt/{p[0].lower()}" + p[2:].replace("\\", "/")
    return p


def is_model_dir(p):
    """True when p holds Topaz models: a .json description with a modelType beside .tz/.tz3 data files."""
    try:
        names = os.listdir(p)
    except OSError:
        return False
    if not any(n.endswith((".tz", ".tz3")) for n in names):
        return False
    for n in names:
        if n.endswith(".json"):
            try:
                with open(os.path.join(p, n), encoding="utf-8") as fh:
                    if "modelType" in json.load(fh):
                        return True
            except (OSError, ValueError, TypeError):
                continue
    return False


def detect_topaz(env=os.environ, pf=PROGRAM_FILES, pd=PROGRAM_DATA):
    """(ffmpeg, TVAI_MODEL_DIR, TVAI_MODEL_DATA_DIR): the install that exists, the renamed Topaz Video first, and the
    first of its model folders that holds models, falling back to the other install's folders. Env vars win."""
    new = (f"{pf}/Topaz Video/ffmpeg.exe", [(f"{pd}/Topaz Video/models/models",) * 2, (f"{pd}/Topaz Video/models",) * 2])
    old = (f"{pf}/Topaz Video AI/ffmpeg.exe", [(f"{pd}/Topaz Video AI/models", f"{pd}/Topaz Video AI")])
    first, second = (old, new) if os.path.isfile(old[0]) and not os.path.isfile(new[0]) else (new, old)
    models = first[1][0]
    for m, d in first[1] + second[1]:
        if is_model_dir(m):
            models = (m, d)
            break
    return (env.get("TOPAZ_FFMPEG") or first[0], env.get("TVAI_MODEL_DIR") or win_path(models[0]),
            env.get("TVAI_MODEL_DATA_DIR") or win_path(models[1]))


TOPAZ, MODEL_DIR, DATA_DIR = detect_topaz()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="clips", action="append", required=True)
    ap.add_argument("--model", default="prob-4", help="tvai_up model (prob-4=Proteus, rhea-1=Rhea, ahq-12, ...)")
    ap.add_argument("--scale", type=int, default=2, choices=[0, 1, 2, 3, 4])
    ap.add_argument("--tvai", default="", help="extra tvai_up params, colon-joined (e.g. 'compression=0.2:details=0.1')")
    ap.add_argument("--post-scale", default="", help="WxH lanczos downscale after tvai (e.g. 1080x1920)")
    ap.add_argument("--out-dir", default=os.environ.get("TOPAZ_OUT_DIR", "renders"), help="a Windows-reachable directory (TOPAZ_OUT_DIR); a C: path renders fastest")
    ap.add_argument("--timeout", type=int, default=3600)
    args = ap.parse_args()
    if not os.path.isfile(TOPAZ):
        sys.exit(f"Topaz's ffmpeg not found at {TOPAZ}: install Topaz Video, or set TOPAZ_FFMPEG")

    env = dict(os.environ, TVAI_MODEL_DIR=MODEL_DIR, TVAI_MODEL_DATA_DIR=DATA_DIR,
               WSLENV=(os.environ.get("WSLENV", "") + ":TVAI_MODEL_DIR/w:TVAI_MODEL_DATA_DIR/w").lstrip(":"))
    Path(wsl_path(args.out_dir)).mkdir(parents=True, exist_ok=True)

    vf = f"tvai_up=model={args.model}:scale={args.scale}"
    if args.tvai:
        vf += ":" + args.tvai
    if args.post_scale:
        w, h = args.post_scale.lower().split("x")
        vf += f",scale={w}:{h}:flags=lanczos"

    results = []
    args.out_dir = win_path(os.path.abspath(wsl_path(args.out_dir)))   # RELATIVE paths broke the success test once: the encode succeeded but wsl_path(out_win) missed -> every rung 'failed'
    for clip in args.clips:
        wp = win_path(os.path.abspath(clip))
        stem = Path(wp.replace("\\", "/")).stem
        out_name = f"{stem}__{args.model}x{args.scale}" + (f"_{args.post_scale}" if args.post_scale else "") + ".mp4"
        out_win = args.out_dir.rstrip("\\") + "\\" + out_name
        entry = {"in": wp, "out": out_win, "model": args.model, "scale": args.scale, "status": "?"}
        results.append(entry)
        for enc in ENCODERS:
            cmd = [TOPAZ, "-hide_banner", "-y", "-i", wp, "-vf", vf,
                   *enc, "-c:a", "copy", "-movflags", "+faststart", out_win]
            t0 = time.time()
            try:
                r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=args.timeout)
            except subprocess.TimeoutExpired:
                entry["status"] = "TIMEOUT"
                break
            if r.returncode == 0 and os.path.isfile(wsl_path(out_win)):
                entry["status"] = "Complete"
                entry["encoder"] = enc[1]
                entry["seconds"] = round(time.time() - t0, 1)
                break
            entry["status"] = "ENCODER-FAIL"
            entry["stderr_tail"] = (r.stderr or "")[-400:]
        print(f"{stem}: {entry['status']} ({entry.get('encoder', '-')}, {entry.get('seconds', '-')}s)",
              file=sys.stderr)

    ok = all(r["status"] == "Complete" for r in results)
    print(json.dumps({"ok": ok, "results": results}, indent=2))
    print("TOPAZ-UPSCALE-OK" if ok else "TOPAZ-UPSCALE-FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
