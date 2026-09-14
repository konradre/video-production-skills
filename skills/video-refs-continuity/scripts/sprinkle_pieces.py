#!/usr/bin/env python3
"""sprinkle_pieces.py — lay the EXACT product silhouettes (cut from the sheet's own pieces) inside a band of
a still, at a given piece LENGTH in pixels (the scale of a known object in the frame). Sister of
plate_pieces.py for the cases its plate rules refuse (a white shelf, a cream cardigan): no colour masks —
you name the band, the count and the size.

  sprinkle_pieces.py --in <png> --out <png> --sheet <sheet.png> --band x0,y0,x1,y1 --count 14 --len 40
       [--len-jitter 0.25] [--seed 7] [--shadow 1]
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
for need in ('--in', '--out', '--band', '--sheet'):
    if not A.get(need) or A.get(need) is True: sys.exit(f'missing {need}\n{__doc__}')
SHEET = A['--sheet']; random.seed(int(A.get('--seed', 7)))
x0, y0, x1, y1 = [int(v) for v in A['--band'].split(',')]
N = int(A.get('--count', 14)); L = float(A.get('--len', 40)); J = float(A.get('--len-jitter', 0.25))
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
im = Image.open(A['--in']).convert('RGBA'); out = im.copy()
for i in range(N):
    sp = random.choice(sprites); ln = L * (1 + random.uniform(-J, J)); s = ln / max(sp.size)
    sp2 = sp.resize((max(2, int(sp.width * s)), max(2, int(sp.height * s))), Image.LANCZOS).rotate(random.uniform(0, 360), expand=True, resample=Image.BICUBIC)
    cx = random.randint(x0, x1); cy = random.randint(y0, y1)
    if A.get('--shadow', '1') != '0':
        shd = Image.new('RGBA', sp2.size, (0, 0, 0, 0)); shd.putalpha(sp2.getchannel('A').point(lambda v: int(v * 0.35)))
        shd = shd.filter(ImageFilter.GaussianBlur(1.2))
        out.alpha_composite(shd, (cx - sp2.width // 2 + 2, cy - sp2.height // 2 + 3))
    out.alpha_composite(sp2, (cx - sp2.width // 2, cy - sp2.height // 2))
out.convert('RGB').save(A['--out'])
print(f'{A["--out"]}: {N} pieces, len≈{L:.0f}px, band {x0},{y0}-{x1},{y1}, {len(sprites)} sprites')
