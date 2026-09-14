#!/usr/bin/env python3
"""air_pieces.py — a MID-AIR layer of the EXACT product silhouettes still falling through a still, for a
start image that sits a second after a burst (the room is still raining). Pieces are cut from the sheet's
own cells, sized by perspective (--near px at the bottom edge → --far px at --far-y and above), tumbled
(random rotation), and given a vertical MOTION BLUR (falling) so they read as moving, not as stickers; no
drop shadow (they are in the air). Optional --avoid boxes (faces) keep the pieces off those areas.

  air_pieces.py --in <png> --out <png> --sheet <sheet.png> [--count 300] [--near 34] [--far 10] [--far-y 0.25]
       [--blur 0.35] [--avoid "x0,y0,x1,y1;x0,y0,x1,y1"] [--seed 7]
--blur   motion-blur length as a fraction of the piece length (0 = crisp)
"""
import sys, random
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

if '--help' in sys.argv or '-h' in sys.argv:
    print(__doc__); sys.exit(0)
A = {}; k = None
for a in sys.argv[1:]:
    if a.startswith('--'): k = a; A[k] = True
    elif k: A[k] = a; k = None
for need in ('--in', '--out', '--sheet'):
    if not A.get(need) or A.get(need) is True: sys.exit(f'missing {need}\n{__doc__}')
SHEET = A['--sheet']; random.seed(int(A.get('--seed', 7)))
N = int(A.get('--count', 300)); NEAR = float(A.get('--near', 34)); FAR = float(A.get('--far', 10)); FARY = float(A.get('--far-y', 0.25))
BL = float(A.get('--blur', 0.35))
avoid = []
if A.get('--avoid') and A.get('--avoid') is not True:
    for b in A['--avoid'].split(';'):
        if b.strip(): avoid.append([int(v) for v in b.split(',')])
sh = Image.open(SHEET).convert('RGB'); sa = np.asarray(sh).astype(int)
bg = np.median(sa.reshape(-1, 3), axis=0); mask = np.abs(sa - bg).sum(axis=2) > 60
lab, n = ndimage.label(ndimage.binary_dilation(mask, iterations=2)); sprites = []
for i in range(1, n + 1):
    m = (lab == i) & mask
    if m.sum() < 500: continue
    ys, xs = np.where(m); yy0, yy1, xx0, xx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgba = np.zeros((yy1 - yy0, xx1 - xx0, 4), np.uint8)
    rgba[..., :3] = sa[yy0:yy1, xx0:xx1]; rgba[..., 3] = (m[yy0:yy1, xx0:xx1] * 255).astype(np.uint8)
    sprites.append(Image.fromarray(rgba, 'RGBA'))
if not sprites:
    sys.exit(f'no sprites found in {SHEET} — single pieces on a flat grey background')
im = Image.open(A['--in']).convert('RGBA'); W, H = im.size; out = im.copy()


def motion_blur(sp, px):
    """vertical smear of a sprite by px pixels (stack shifted copies, average) — a falling piece"""
    if px < 1: return sp
    steps = int(px) + 1; canvas = Image.new('RGBA', (sp.width, sp.height + steps), (0, 0, 0, 0))
    acc = np.zeros((canvas.height, canvas.width, 4), np.float32)
    for s in range(steps):
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0)); layer.alpha_composite(sp, (0, s)); acc += np.asarray(layer, np.float32)
    acc /= steps
    return Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8), 'RGBA')


placed = 0; tries = 0
while placed < N and tries < N * 20:
    tries += 1
    cx = random.randint(0, W - 1); cy = random.randint(0, H - 1)
    if any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1 in avoid): continue
    t = min(1.0, max(0.0, (cy / H - FARY) / (1.0 - FARY)))   # 0 at/above far-y, 1 at the bottom edge
    ln = FAR + (NEAR - FAR) * t; ln *= random.uniform(0.8, 1.2)
    sp = random.choice(sprites); s = ln / max(sp.size)
    sp2 = sp.resize((max(2, int(sp.width * s)), max(2, int(sp.height * s))), Image.LANCZOS).rotate(random.uniform(0, 360), expand=True, resample=Image.BICUBIC)
    sp2 = motion_blur(sp2, BL * ln * random.uniform(0.5, 1.5))
    if t > 0.75: sp2 = sp2.filter(ImageFilter.GaussianBlur(0.6))   # nearer pieces sit out of the plane of focus
    out.alpha_composite(sp2, (cx - sp2.width // 2, cy - sp2.height // 2)); placed += 1
out.convert('RGB').save(A['--out'])
print(f'{A["--out"]}: {placed} air pieces (near {NEAR:.0f}px → far {FAR:.0f}px above y={FARY}), blur {BL}, {len(sprites)} sprites')
