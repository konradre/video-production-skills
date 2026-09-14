#!/usr/bin/env python3
"""frame_match.py — which take, and which time, does an operator's frame come from? Normalised cross-correlation
of the screenshot against every frame of each take (on 96×54 grey thumbs), best match per take with its NCC.
Run it BEFORE proposing a fix for an operator-named frame: a "zoom shift" chased through re-cuts and a regen can be
the take's own short low-angle piece, found in one minute this way.

  frame_match.py --take <take.mp4> [--take <other.mp4> ...] <frame.png> [--top 3]
Self-test: the script first matches a frame of the first take against that take and must report NCC ≥ 0.99 at
its own time; otherwise the instrument is broken and no other number is printed.
"""
import argparse, json, subprocess, sys
import numpy as np
from PIL import Image
from io import BytesIO

TW, TH = 96, 54


def probe_fps(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', path], capture_output=True, text=True)
    num, den = p.stdout.strip().split('/'); return float(num) / float(den)


def thumbs(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'scale={TW}:{TH},format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, TH, TW).astype(np.float32)


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def thumb_of(img):
    return np.asarray(img.convert('L').resize((TW, TH), Image.LANCZOS)).astype(np.float32)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('frame'); ap.add_argument('--take', action='append', required=True); ap.add_argument('--top', type=int, default=3)
    a = ap.parse_args()
    q = thumb_of(Image.open(a.frame))
    # self-test on the first take: its own frame 10 must match itself
    t0 = thumbs(a.take[0]); fps0 = probe_fps(a.take[0])
    k = min(10, len(t0) - 1); st = ncc(t0[k], t0[k]); st2 = max(ncc(t0[k], f) for f in t0)
    if st < 0.99 or st2 < 0.99: sys.exit(f'SELF-TEST FAILED: a frame matched itself at {st:.3f}/{st2:.3f} — the instrument is broken; no numbers printed')
    print(f'self-test ok: frame {k} of {a.take[0]} matches itself at {st2:.3f}')
    for path in a.take:
        th = t0 if path == a.take[0] else thumbs(path); fps = fps0 if path == a.take[0] else probe_fps(path)
        scores = np.array([ncc(q, f) for f in th])
        best = np.argsort(-scores)[:a.top]
        print(f'{path}: ' + ' · '.join(f'f{i} {i / fps:.3f}s NCC {scores[i]:.3f}' for i in best))


if __name__ == '__main__':
    main()
