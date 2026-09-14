#!/usr/bin/env python3
"""plate_pieces.py — scatter the EXACT product silhouette (pieces cut from the reference sheet's own cells)
onto a plate / start image, deterministically. Why: image models draw small product pieces as dots, clovers
or glitter dust; the sheet is the truth, so the pieces on a start image are CUT from it, never drawn.
Sprites = the sheet's own pieces (a 3×3 grid of cells, the grey background masked). Size follows perspective
(--near px at the bottom edge → --far px at --far-y). Colour = the sprite's own, tinted by the plate's local
light. Placement = inside --poly (normalised x,y pairs) minus dark pixels (trousers, bags), bright saturated
pixels (dresses) and near-white (a white dress).

  plate_pieces.py --in <plate.png> --out <out.png> --sheet <sheet.png> [--count 450] [--seed 7]
       [--poly "0.0,1.0;1.0,1.0;0.98,0.66;0.02,0.66"] [--near 34] [--far 11] [--far-y 0.60] [--check <png>]
--check writes a 2× crop of the near band so the pieces can be identified before the plate feeds a gen.
"""
import sys, random
import numpy as np
from PIL import Image, ImageFilter

if '--help' in sys.argv or '-h' in sys.argv:
    print(__doc__); sys.exit(0)
A = {}; k = None
for a in sys.argv[1:]:
    if a.startswith('--'): k = a; A[k] = True
    elif k: A[k] = a; k = None
if not A.get('--in') or not A.get('--out') or not A.get('--sheet') or A.get('--sheet') is True:
    sys.exit(__doc__)
SHEET = A['--sheet']
COUNT = int(A.get('--count', 450)); SEED = int(A.get('--seed', 7))
NEAR = float(A.get('--near', 34)); FAR = float(A.get('--far', 11)); FARY = float(A.get('--far-y', 0.60))
poly = [tuple(map(float, p.split(','))) for p in A.get('--poly', '0.0,1.0;1.0,1.0;0.98,0.66;0.02,0.66').split(';')]
random.seed(SEED); np.random.seed(SEED)

# --- sprites from the sheet
sh = Image.open(SHEET).convert('RGB'); sa = np.asarray(sh).astype(int)
bg = np.median(sa.reshape(-1, 3), axis=0); mask = np.abs(sa - bg).sum(axis=2) > 60
H, W = mask.shape; sprites = []
for r in range(3):
    for c in range(3):
        m = mask[r*H//3:(r+1)*H//3, c*W//3:(c+1)*W//3]
        if m.sum() < 3000: continue
        ys, xs = np.where(m); y0, y1, x0, x1 = ys.min(), ys.max()+1, xs.min(), xs.max()+1
        rgb = sa[r*H//3:(r+1)*H//3, c*W//3:(c+1)*W//3][y0:y1, x0:x1]
        al = (m[y0:y1, x0:x1] * 255).astype(np.uint8)
        im = Image.fromarray(np.dstack([rgb.astype(np.uint8), al]), 'RGBA')
        im.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(1.2)))
        sprites.append(im)
if not sprites:
    sys.exit(f'no sprites found in {SHEET} — the sheet must be single pieces on a flat grey background, 3×3 cells')
print(f'sprites: {len(sprites)} from {SHEET}')

# --- plate + exclusion mask
pl = Image.open(A['--in']).convert('RGB'); P = np.asarray(pl).astype(float) / 255
h, w, _ = P.shape
mx = P.max(axis=2); mn = P.min(axis=2); v = mx; s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
bad = (v < 0.14) | ((s > 0.6) & (v > 0.45)) | (v > 0.85)

def inside(x, y):
    n = len(poly); ins = False; j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi): ins = not ins
        j = i
    return ins

out = pl.convert('RGBA'); placed = 0; tries = 0
while placed < COUNT and tries < COUNT * 40:
    tries += 1
    x, y = random.random(), random.random()
    if y < FARY or not inside(x, y): continue
    px, py = int(x * w), int(y * h)
    if bad[max(0, py-2):py+3, max(0, px-2):px+3].mean() > 0.2: continue
    hh = FAR + (NEAR - FAR) * (y - FARY) / (1 - FARY)
    sp = random.choice(sprites)
    sc = hh / sp.height; sp = sp.resize((max(2, int(sp.width * sc)), max(3, int(sp.height * sc))), Image.LANCZOS)
    sp = sp.rotate(random.uniform(0, 360), expand=True, resample=Image.BICUBIC)
    # squash slightly with distance (a flat piece seen at a low angle)
    sq = 0.55 + 0.45 * (y - FARY) / (1 - FARY)
    sp = sp.resize((sp.width, max(2, int(sp.height * sq))), Image.LANCZOS)
    # local light
    r0 = max(4, int(hh)); win = P[max(0, py-r0):py+r0, max(0, px-r0):px+r0]
    loc = win.reshape(-1, 3).mean(axis=0); lum = 0.299*loc[0] + 0.587*loc[1] + 0.114*loc[2]
    arr = np.asarray(sp).astype(float); rgb = arr[..., :3] / 255
    gain = float(np.clip(lum / 0.50, 0.40, 1.15))
    tint = loc / max(lum, 1e-3) * (0.299*rgb[..., 0:1] + 0.587*rgb[..., 1:2] + 0.114*rgb[..., 2:3])
    rgb = np.clip((0.70 * rgb + 0.30 * tint) * gain, 0, 1)
    arr[..., :3] = rgb * 255
    sp = Image.fromarray(arr.astype(np.uint8), 'RGBA')
    out.alpha_composite(sp, (px - sp.width // 2, py - sp.height // 2))
    placed += 1
out.convert('RGB').save(A['--out']); print(f'placed {placed} pieces ({tries} tries) → {A["--out"]}')
if A.get('--check') and A.get('--check') is not True:
    chk = out.convert('RGB').crop((int(0.25*w), int(0.80*h), int(0.75*w), int(0.96*h))).resize((int(0.5*w)*2, int(0.16*h)*2), Image.LANCZOS)
    chk.save(A['--check']); print('check →', A['--check'])
