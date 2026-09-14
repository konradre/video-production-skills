#!/usr/bin/env python3
"""knit_letters.py — composite INTARSIA-KNIT lettering onto a knitted garment in a still — the LAST fallback when no
image model will write the words (try the copy route first: a lettered reference and no lettering words in the prompt). Unlike a flat text overlay, the letters are quantised to a stitch grid (wales × courses),
each stitch carries a V-stitch shading tile, and the colour is MULTIPLIED onto the sweater's own luminance so the
folds, ribbing shadows and lamp light stay — the lettering reads as knitted into the fabric, not printed on it.
Usage: knit_letters.py --in <png> --out <png> --box x0,y0,x1,y1 --text "LINE ONE|LINE TWO" [--color 1c2140]
       [--stitch 9] [--course 0.78] [--leading 1.02] [--font <bold .ttf>]
       [--fill 0.45] [--blur 0.6] [--curve 0.0] [--seed 3]
--box    the chest area the lettering may occupy (the text is fitted to its width, centred in its height)
--stitch px per wale (stitch column); --course = course height as a fraction of --stitch (knit stitches are wider than tall)
--fill   a stitch cell is knitted when this fraction of it is covered by the glyph
--curve  gentle barrel warp of the lettering across the box width (0 = flat; 0.05 = a chest curve)
--font   a bold face; default DejaVu Sans Bold (Linux), Arial Bold (macOS), else fontconfig's bold sans
"""
import sys, math, random, os, shutil, subprocess
if '--help' in sys.argv or '-h' in sys.argv:
    print(__doc__); sys.exit(0)
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

A = {}; k = None
for a in sys.argv[1:]:
    if a.startswith('--'): k = a; A[k] = True
    elif k: A[k] = a; k = None
need = ('--in', '--out', '--box', '--text')
for n in need:
    if n not in A: sys.exit(f'missing {n}\n{__doc__}')
x0, y0, x1, y1 = [int(v) for v in A['--box'].split(',')]
lines = A['--text'].split('|')
col = A.get('--color', '1c2140'); color = np.array([int(col[i:i+2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0
stitch = float(A.get('--stitch', 9)); course = float(A.get('--course', 0.78)); leading = float(A.get('--leading', 1.02))
BOLD_FONTS = ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/Library/Fonts/Arial Bold.ttf')
font_path = A.get('--font') or next((p for p in BOLD_FONTS if os.path.isfile(p)), None)
if not font_path and shutil.which('fc-match'):
    font_path = subprocess.run(['fc-match', '-f', '%{file}', 'sans:bold'], capture_output=True, text=True).stdout.strip() or None
if not font_path or not os.path.isfile(font_path):
    sys.exit(f'no bold font found ({font_path or "none"}): pass --font <a .ttf file>')
fill = float(A.get('--fill', 0.45)); blur = float(A.get('--blur', 1.0)); curve = float(A.get('--curve', 0.0)); tex = float(A.get('--tex', 1.6))
random.seed(int(A.get('--seed', 3))); np.random.seed(int(A.get('--seed', 3)))

img = Image.open(A['--in']).convert('RGB'); W, H = img.size
bw, bh = x1 - x0, y1 - y0

# 1. glyph mask — one font size for every line, the widest line fitted to ~96 % of the box width
def render(size):
    f = ImageFont.truetype(font_path, size)
    widths = []; heights = []
    for ln in lines:
        l, t, r, b = f.getbbox(ln); widths.append(r - l); heights.append(b - t)
    return f, widths, heights
size = 8
while True:
    f, widths, heights = render(size + 1)
    total_h = sum(heights) + (len(lines) - 1) * heights[0] * (leading - 1) if len(lines) > 1 else heights[0]
    if max(widths) > bw * 0.96 or total_h > bh * 0.98: break
    size += 1
f, widths, heights = render(size)
glyph = Image.new('L', (bw, bh), 0); d = ImageDraw.Draw(glyph)
line_h = heights[0] * leading; block_h = heights[0] + (len(lines) - 1) * line_h
y = (bh - block_h) / 2
for ln, wdt in zip(lines, widths):
    l, t, r, b = f.getbbox(ln)
    d.text(((bw - wdt) / 2 - l, y - t), ln, font=f, fill=255)
    y += line_h
g = np.asarray(glyph, dtype=np.float32) / 255.0

# 2. stitch quantisation — the glyph becomes a set of knitted stitches on a wale × course grid
sw = stitch; sh = stitch * course
nx = int(math.ceil(bw / sw)); ny = int(math.ceil(bh / sh))
cells = np.zeros((ny, nx), dtype=np.float32)
for j in range(ny):
    for i in range(nx):
        ys, ye = int(j * sh), int(min(bh, (j + 1) * sh)); xs, xe = int(i * sw), int(min(bw, (i + 1) * sw))
        if ye > ys and xe > xs: cells[j, i] = 1.0 if g[ys:ye, xs:xe].mean() >= fill else 0.0
# a V-stitch shading tile: bright on the two arms of the V, darker in the trough and at the cell edges
ty, tx = int(round(sh)), int(round(sw))
tile = np.zeros((ty, tx), dtype=np.float32)
for yy in range(ty):
    for xx in range(tx):
        u = (xx + 0.5) / tx - 0.5; v = (yy + 0.5) / ty
        arm = abs(abs(u) * 1.6 - v)            # distance from the V's two arms
        tile[yy, xx] = 1.0 - 0.22 * min(1.0, arm * 3.2) - 0.10 * (1.0 - v) * (abs(u) > 0.42)
mask = np.zeros((bh, bw), dtype=np.float32); shade = np.ones((bh, bw), dtype=np.float32)
for j in range(ny):
    for i in range(nx):
        if cells[j, i] <= 0: continue
        ys, xs = int(j * sh), int(i * sw); ye, xe = min(bh, ys + ty), min(bw, xs + tx)
        mask[ys:ye, xs:xe] = 1.0
        shade[ys:ye, xs:xe] = tile[:ye - ys, :xe - xs] * (0.97 + 0.06 * random.random())
# soften the stitch edges a hair (yarn fuzz) and warp across the chest if asked
m = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur))
mask = np.asarray(m, dtype=np.float32) / 255.0
if curve > 0:
    src = Image.fromarray((np.stack([mask, shade], -1) * 255).astype(np.uint8).transpose(2, 0, 1)[0])
    xs_ = np.arange(bw, dtype=np.float32); cx = (xs_ - bw / 2) / (bw / 2)
    dy = (curve * bh) * (cx ** 2)  # edges of the chest fall away downward
    warped_m = np.zeros_like(mask); warped_s = np.ones_like(shade)
    for xx in range(bw):
        off = int(round(dy[xx]))
        if off > 0:
            warped_m[off:, xx] = mask[:bh - off, xx]; warped_s[off:, xx] = shade[:bh - off, xx]
        else:
            warped_m[:, xx] = mask[:, xx]; warped_s[:, xx] = shade[:, xx]
    mask, shade = warped_m, warped_s

# 3. colour multiplied onto the sweater's own luminance — folds and lamp light stay under the letters
arr = np.asarray(img, dtype=np.float32) / 255.0
box = arr[y0:y1, x0:x1]
lum = box @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
ref = float(np.percentile(lum[mask < 0.05], 70)) if (mask < 0.05).any() else float(lum.mean())
rel = np.clip(lum / max(ref, 1e-3), 0.35, 1.25)[..., None]
# the sweater's own fine knit texture (high-pass of its luminance), amplified, shows through the colour
lp = np.asarray(Image.fromarray((np.clip(lum, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5)), dtype=np.float32) / 255.0
detail = np.clip(1.0 + tex * (lum - lp) / max(ref, 1e-3), 0.6, 1.4)[..., None]
knit = color[None, None, :] * rel * shade[..., None] * detail
# a faint fibre halo: 1 px of half-strength colour just outside the letters, like yarn bleeding into the cream
halo = np.clip(np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), dtype=np.float32) / 255.0 - mask, 0, 1) * 0.35
mm = np.clip(mask + halo, 0, 1)[..., None]
out = box * (1 - mm) + knit * mm
arr[y0:y1, x0:x1] = out
Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).save(A['--out'])
print(f'KNIT-OK {A["--out"]} box={bw}x{bh} font={size}px stitches={int(cells.sum())} grid={nx}x{ny} stitch={sw:.1f}x{sh:.1f}px')
