#!/usr/bin/env python3
"""seed_montage.py — every seed of one shot on ONE sheet, compared at once, and the near-duplicates named.

Read one at a time, seeds cannot be told apart from each other: a near-duplicate of a seed already read looks like a new
angle, and the fourth take of a move reads better than the first only because it came fourth. One montage — the seeds as
COLUMNS, the same sample points as ROWS — puts every candidate beside every other, and a similarity table says which pairs
are the same take twice (keep one, read the other's window only if it differs where it matters). Pattern: OrbitSheets'
Frame Select (`nodes.py`: "scoring frames in isolation cannot tell a near-duplicate from a genuinely new angle").
The sheet is the agent's note for the read, never the pick: the clips still go to the operator by path.

  seed_montage.py --out <sheet.jpg> [--at 0.1,0.3,0.5,0.7,0.9] [--width 270] [--dup 0.97] <seed>…
  seed_montage.py --selftest
--at   sample points as FRACTIONS of each seed's own duration (seeds of one shot share a length; a fraction keeps the rows
       aligned when one runs a few frames longer)
--dup  mean normalised cross-correlation (64×64 luma, over the rows) at or above which a pair is called a near-duplicate
"""
import argparse, os, subprocess, sys, tempfile
import numpy as np


def dur(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def grab(p, t, w):
    from PIL import Image
    import io
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.4f}', '-i', p, '-frames:v', '1', '-vf', f'scale={w}:-2', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                         capture_output=True).stdout
    return Image.open(io.BytesIO(raw)).convert('RGB') if raw else None


def luma64(im):
    return np.asarray(im.convert('L').resize((64, 64)), float)


def ncc(a, b):
    a, b = a - a.mean(), b - b.mean(); d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d else (1.0 if abs(a).sum() == abs(b).sum() == 0 else 0.0)


def montage(seeds, at, w, out):
    from PIL import Image, ImageDraw
    cells = [[grab(s, f * dur(s), w) for f in at] for s in seeds]
    h = max((c.height for col in cells for c in col if c), default=w)
    lab, pad = 22, 6; W = len(seeds) * (w + pad) + pad + 60; H = len(at) * (h + pad) + pad + lab
    sheet = Image.new('RGB', (W, H), (18, 18, 18)); d = ImageDraw.Draw(sheet)
    for j, s in enumerate(seeds):
        d.text((60 + pad + j * (w + pad), 4), f'{j + 1}  {os.path.basename(s)[:28]}', fill=(230, 230, 230))
    for i, f in enumerate(at):
        d.text((6, lab + pad + i * (h + pad) + h // 2 - 6), f'{f:.0%}', fill=(230, 230, 230))
        for j in range(len(seeds)):
            c = cells[j][i]
            if c: sheet.paste(c, (60 + pad + j * (w + pad), lab + pad + i * (h + pad)))
    sheet.save(out, quality=88)
    lum = [[luma64(c) if c else None for c in col] for col in cells]
    sim = np.full((len(seeds), len(seeds)), np.nan)
    for a in range(len(seeds)):
        for b in range(len(seeds)):
            v = [ncc(x, y) for x, y in zip(lum[a], lum[b]) if x is not None and y is not None]
            sim[a, b] = np.mean(v) if v else np.nan
    return sheet.size, sim


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('seeds', nargs='*'); ap.add_argument('--out'); ap.add_argument('--at', default='0.1,0.3,0.5,0.7,0.9')
    ap.add_argument('--width', type=int, default=270); ap.add_argument('--dup', type=float, default=0.97); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest: return selftest()
    if len(a.seeds) < 2 or not a.out: ap.error('two or more seeds and --out')
    at = [float(x) for x in a.at.split(',')]; size, sim = montage(a.seeds, at, a.width, a.out)
    print(f'wrote {a.out} ({size[0]}x{size[1]}): {len(a.seeds)} seeds × {len(at)} points')
    print('similarity (mean NCC over the rows):'); print('      ' + ''.join(f'{j + 1:>7}' for j in range(len(a.seeds))))
    for i in range(len(a.seeds)): print(f'  {i + 1:>3} ' + ''.join(f'{sim[i, j]:7.3f}' for j in range(len(a.seeds))))
    dups = [(i + 1, j + 1, sim[i, j]) for i in range(len(a.seeds)) for j in range(i + 1, len(a.seeds)) if sim[i, j] >= a.dup]
    for i, j, v in dups: print(f'NEAR-DUPLICATE {i} ≈ {j} ({v:.3f}): the same take twice — read one, keep the other only where it differs')
    if not dups: print(f'no pair at or above {a.dup}: every seed is its own take')
    return 0


def selftest():
    with tempfile.TemporaryDirectory() as r:
        mk = lambda n, vf: subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'testsrc2=size=160x284:rate=24:duration=3', '-vf', vf, '-pix_fmt', 'yuv420p', os.path.join(r, n)], check=True)
        mk('a.mp4', 'null'); mk('a2.mp4', 'noise=alls=6:allf=t'); mk('b.mp4', 'hflip,hue=h=90')
        out = os.path.join(r, 'sheet.jpg'); size, sim = montage([os.path.join(r, x) for x in ('a.mp4', 'a2.mp4', 'b.mp4')], [0.2, 0.5, 0.8], 120, out)
        chk = [('the sheet is written, 3 columns × 3 rows', os.path.exists(out) and size[0] > 3 * 120 and size[1] > 3 * 100),
               ('a and its noisy twin read as near-duplicates', sim[0, 1] >= 0.97),
               ('a and a flipped, re-hued take do not', sim[0, 2] < 0.97),
               ('the table is symmetric with 1.0 on the diagonal', abs(sim[0, 1] - sim[1, 0]) < 1e-9 and abs(sim[2, 2] - 1) < 1e-9)]
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
