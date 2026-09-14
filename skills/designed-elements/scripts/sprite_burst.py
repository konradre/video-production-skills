#!/usr/bin/env python3
"""sprite_burst.py — the product's EXACT silhouettes as a particle burst composited over a hero clip, on top of the generated
burst (which supplies volume and motion under it). Sprites are the cells of the product's own silhouette sheet (grey background
masked), launched from the muzzle in a cone, tumbling under gravity and drag, resting where they land. The legibility
contract: a piece that cannot be identified is a defect — no single sprite is drawn below --min-readable-px.
⚠ Use ONLY where the operator has accepted a composited burst for that shot; a 2D overlay on generated MOTION is
rejected — the overlay must land on a static plate or
ride the generated burst's own motion, never replace it.

  sprite_burst.py --root <project> --in edit/hero/<hero>.mov --out edit/hero/<hero>-burst.mov --bang <s> --muzzle X,Y --dir dx,dy
                  [--dir2 -0.85,0.35] [--count 380] [--size 62] [--min-readable-px 40] [--floor 2500] [--floor-x 200,1500]
                  [--carpet 3200] [--sheet references/sheets/<sku>-sheet-exact.png] [--seed 7] [--g 2.4] [--drag 0.92] [--spawn 10]
Output: DNxHR HQX 10-bit, the input's audio copied.
"""
import argparse, math, os, random, re, subprocess, sys
import numpy as np
from PIL import Image, ImageFilter


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--in', dest='src', required=True); ap.add_argument('--out', required=True); ap.add_argument('--bang', type=float, required=True)
    ap.add_argument('--muzzle', required=True); ap.add_argument('--dir', required=True); ap.add_argument('--dir2', default='-0.85,0.35'); ap.add_argument('--count', type=int, default=380); ap.add_argument('--size', type=float, default=62)
    ap.add_argument('--min-readable-px', type=float, default=40); ap.add_argument('--floor', type=float, default=2500); ap.add_argument('--floor-x', default='200,1500'); ap.add_argument('--carpet', type=float, default=3200)
    ap.add_argument('--sheet', required=True); ap.add_argument('--seed', type=int, default=7); ap.add_argument('--g', type=float, default=2.4); ap.add_argument('--drag', type=float, default=0.92); ap.add_argument('--spawn', type=int, default=10); ap.add_argument('--fps', type=float, default=24)
    argv = list(sys.argv[1:]); i = 0
    while i < len(argv) - 1:   # --dir -0.7,-0.5 : a value that starts with '-' and a digit must be joined for argparse
        if argv[i].startswith('--') and re.match(r'^-\d', argv[i + 1]): argv[i:i + 2] = [f'{argv[i]}={argv[i + 1]}']
        i += 1
    a = ap.parse_args(argv); os.chdir(a.root); random.seed(a.seed); np.random.seed(a.seed)
    MX, MY = (float(v) for v in a.muzzle.split(',')); DX, DY = (float(v) for v in a.dir.split(',')); DX2, DY2 = (float(v) for v in a.dir2.split(',')); FX0, FX1 = (float(v) for v in a.floor_x.split(','))
    pr = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,nb_frames', '-of', 'csv=p=0', a.src], capture_output=True, text=True).stdout.strip().split(',')
    W, H, NF = int(pr[0]), int(pr[1]), int(pr[2] or 0)
    sh = Image.open(a.sheet).convert('RGB'); sa = np.asarray(sh).astype(int); bg = np.median(sa.reshape(-1, 3), axis=0); mask = np.abs(sa - bg).sum(axis=2) > 60; SH, SW = mask.shape; sprites = []
    for r in range(3):
        for c in range(3):
            m = mask[r * SH // 3:(r + 1) * SH // 3, c * SW // 3:(c + 1) * SW // 3]
            if m.sum() < 3000: continue
            ys, xs = np.where(m); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            rgb = sa[r * SH // 3:(r + 1) * SH // 3, c * SW // 3:(c + 1) * SW // 3][y0:y1, x0:x1]; al = (m[y0:y1, x0:x1] * 255).astype(np.uint8)
            im = Image.fromarray(np.dstack([rgb.astype(np.uint8), al]), 'RGBA'); im.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(1.2))); sprites.append(im)
    assert sprites, 'no sprite cells found on the sheet (3×3 cells over a flat background)'
    print(f'sprites {len(sprites)}  hero {W}x{H} {NF} f  bang frame {int(round(a.bang * a.fps))}', flush=True)
    n = math.hypot(DX, DY); DX, DY = DX / n, DY / n; n2 = math.hypot(DX2, DY2); DX2, DY2 = DX2 / n2, DY2 / n2; BF = int(round(a.bang * a.fps)); P = []; clamped = 0
    for i in range(a.count):
        if random.random() < 0.55: ang = math.atan2(DY, DX) + math.radians(random.uniform(-40, 40)); sp = random.uniform(25, 90)      # the plume
        else: ang = math.atan2(DY2, DX2) + math.radians(random.uniform(-22, 22)); sp = random.uniform(70, 115)                       # the spray at the target
        depth = random.uniform(0.6, 1.5); size = a.size * depth
        if size < a.min_readable_px: size = a.min_readable_px; clamped += 1
        P.append(dict(x=MX + random.uniform(-12, 12), y=MY + random.uniform(-12, 12), vx=math.cos(ang) * sp, vy=math.sin(ang) * sp, rot=random.uniform(0, 360), om=random.uniform(-14, 14), size=size,
                      spr=random.randrange(len(sprites)), born=BF + random.randrange(a.spawn), state=0, floor=(a.floor + random.gauss(0, 220)) if random.random() < 0.75 else a.carpet + random.gauss(0, 80), shade=random.uniform(0.72, 0.98)))
    if clamped: print(f'legibility: {clamped} sprites raised to the {a.min_readable_px:.0f} px floor', flush=True)

    def step(p):
        if p['state'] != 0: return
        p['vx'] *= a.drag; p['vy'] = p['vy'] * a.drag + a.g; p['x'] += p['vx']; p['y'] += p['vy']; p['rot'] += p['om']; p['om'] *= 0.985
        if p['vy'] > 0 and p['y'] >= p['floor'] and (FX0 <= p['x'] <= FX1 or p['floor'] > a.carpet - 300): p['state'] = 1
        if p['x'] < -150 or p['x'] > W + 150 or p['y'] > H + 150: p['state'] = 2

    cache = {}

    def sprite(p):
        key = (p['spr'], int(p['size']), int(p['rot']) % 360, round(p['shade'], 2))
        if key not in cache:
            s = sprites[p['spr']]; sc = p['size'] / max(s.size); im = s.resize((max(2, int(s.width * sc)), max(2, int(s.height * sc))), Image.LANCZOS)
            if p['shade'] < 1: arr = np.asarray(im).astype(float); arr[..., :3] *= p['shade']; im = Image.fromarray(arr.astype(np.uint8), 'RGBA')
            cache[key] = im.rotate(key[2], expand=True, resample=Image.BICUBIC)
        return cache[key]

    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', a.src, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(a.fps), '-i', '-', '-i', a.src, '-map', '0:v', '-map', '1:a?', '-c:v', 'dnxhd', '-profile:v', 'dnxhr_hqx', '-pix_fmt', 'yuv422p10le', '-c:a', 'copy', a.out], stdin=subprocess.PIPE)
    FB = W * H * 3; f = 0; drawn = 0
    while True:
        buf = dec.stdout.read(FB)
        if len(buf) < FB: break
        if f >= BF:
            fr = Image.frombuffer('RGB', (W, H), buf, 'raw', 'RGB', 0, 1).convert('RGBA'); layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            for p in P:
                if f < p['born'] or p['state'] == 2: continue
                if f > p['born']: step(p)
                if p['state'] == 2: continue
                im = sprite(p); x = int(p['x'] - im.width / 2); y = int(p['y'] - im.height / 2)
                if p['state'] == 0 and math.hypot(p['vx'], p['vy']) > 28:   # a cheap 2-tap smear on fast pieces
                    ghost = im.copy(); ghost.putalpha(ghost.getchannel('A').point(lambda v: v // 2)); layer.alpha_composite(ghost, (int(x - p['vx'] * 0.45), int(y - p['vy'] * 0.45)))
                layer.alpha_composite(im, (x, y)); drawn += 1
            fr.alpha_composite(layer); buf = fr.convert('RGB').tobytes()
        enc.stdin.write(buf); f += 1
        if f % 24 == 0: print(f'frame {f}/{NF}', flush=True)
    enc.stdin.close(); enc.wait(); dec.wait(); print(f'done {f} frames, {drawn} sprite draws -> {a.out}')


if __name__ == '__main__':
    main()
