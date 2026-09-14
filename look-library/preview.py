#!/usr/bin/env python3
"""Preview grid for the look-library — ffmpeg-ops gen-luts.py chooser pattern.

Extracts a frame from a clip, applies every cube in cubes/ via ffmpeg lut3d
(tetrahedral), writes preview/<id>.png tiles + preview/index.html chooser
("human picks" — the operator eyeballs, the pipeline never auto-picks a look).

Usage: python3 preview.py --clip PATH [--t SECONDS]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-800:], file=sys.stderr)
        raise SystemExit(f"failed: {' '.join(cmd[:6])}…")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", required=True, help="a representative clip: an upscaled mezzanine of a generated take")
    ap.add_argument("--t", type=float, default=2.0)
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    prev = ROOT / "preview"
    prev.mkdir(exist_ok=True)
    base = prev / "_original.png"

    if not Path(args.clip).is_file():
        raise SystemExit(f"clip not found: {args.clip}")
    run(["ffmpeg", "-y", "-v", "error", "-ss", str(args.t), "-i", args.clip,
         "-frames:v", "1", "-vf", f"scale=-2:{args.height}", str(base)])

    tiles = [("_original", "ORIGINAL (draft, ungraded)")]
    for cube in sorted((ROOT / "cubes").glob("*.cube")):
        look_id = cube.stem.rsplit("_", 1)[0]
        out = prev / f"{look_id}.png"
        run(["ffmpeg", "-y", "-v", "error", "-i", str(base),
             "-vf", f"lut3d=file={cube}:interp=tetrahedral", str(out)])
        tiles.append((look_id, look_id))
        print(f"preview {out.name}")

    idx = json.loads((ROOT / "index.json").read_text()) if (ROOT / "index.json").exists() else {}
    meta = {l["id"]: l for l in idx.get("looks", [])}
    cells = []
    for fname, label in tiles:
        desc = meta.get(label, {}).get("description", "")
        genre = meta.get(label, {}).get("genre", "")
        tag = f" <span class='g'>[{genre}]</span>" if genre else ""
        cells.append(
            f"<figure><img src='{fname}.png' loading='lazy'>"
            f"<figcaption><b>{label}</b>{tag}<br><small>{desc}</small></figcaption></figure>")
    (prev / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>look-library chooser</title>"
        "<style>body{background:#111;color:#ddd;font:14px system-ui;margin:20px}"
        ".grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}"
        "img{width:100%;border-radius:6px}figcaption{margin-top:4px}"
        ".g{color:#8ac}</style>"
        f"<h2>look-library — preview @{args.t}s</h2><div class='grid'>"
        + "".join(cells) + "</div>\n")
    print(f"wrote {prev / 'index.html'} ({len(tiles)} tiles)")


if __name__ == "__main__":
    main()
