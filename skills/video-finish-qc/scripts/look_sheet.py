#!/usr/bin/env python3
"""look_sheet.py — the frame sheet the operator picks the LOOK from, before the first delivered version: a few frames of the
project's own footage (and its generated stills) as columns raw · [the current chain] · each candidate cube at full strength ·
[one cube at a blend]. The grade starts from the look library's cube for the genre, also on existing footage; a hand-written
level chain is a deviation that needs a reason (two such chains stood for ten hours on a documentary spot, 2026-09-15).

  look_sheet.py --out review/looks/SHEET-looks.jpg --cubes <dir of <look>_33.cube> --looks ads-clean,ads-warm \\
                [--blend ads-clean:0.85] [--current "<ffmpeg filter chain>"] --frame takes/a.mp4@3.0 --frame stills/AER2.png …
  look_sheet.py --selftest
A frame is `<video>@<seconds>` or an image path; every frame is scaled to the tile height at true display shape (`setsar=1`).
The cube is applied on a 16-bit planar frame with tetrahedral interpolation (look-library GUIDE § 6b); a blend mixes the graded
and ungraded frames at the given weight.
"""
import argparse, os, subprocess, sys, tempfile


def sh(c): return subprocess.run(c, capture_output=True, text=True)


def grab(spec, out, H):
    if '@' in spec and not os.path.exists(spec):
        src, t = spec.rsplit('@', 1); r = sh(['ffmpeg', '-v', 'error', '-y', '-ss', t, '-i', src, '-frames:v', '1', '-vf', f'scale=-2:{H}:flags=lanczos,setsar=1', out])
    else: r = sh(['ffmpeg', '-v', 'error', '-y', '-i', spec, '-frames:v', '1', '-vf', f'scale=-2:{H}:flags=lanczos,setsar=1', out])
    if r.returncode or not os.path.exists(out): sys.exit(f'could not read a frame from {spec}: {r.stderr[-300:]}')


def render(raw, out, vf=None, cube=None, blend=None):
    if cube and blend is not None:
        fc = f"[0:v]format=gbrp16le,split[a][b];[b]lut3d=file={cube}:interp=tetrahedral[g];[a][g]mix=inputs=2:weights='{1 - blend:.3f} {blend:.3f}',format=rgb24"
        r = sh(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-filter_complex', fc, out])
    elif cube: r = sh(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-vf', f'format=gbrp16le,lut3d=file={cube}:interp=tetrahedral,format=rgb24', out])
    elif vf: r = sh(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-vf', vf, out])
    else: r = sh(['ffmpeg', '-v', 'error', '-y', '-i', raw, out])
    if r.returncode: sys.exit(f'render failed ({out}): {r.stderr[-300:]}')


def build(frames, cubes_dir, looks, blend, current, out, H=384):
    from PIL import Image, ImageDraw
    d = tempfile.mkdtemp(); cols = [('raw', None, None, None)]
    if current: cols.append(('current', current, None, None))
    for lk in looks: cols.append((lk, None, os.path.join(cubes_dir, f'{lk}_33.cube'), None))
    if blend: lk, w = blend.split(':'); cols.append((f'{lk} {float(w):.0%}', None, os.path.join(cubes_dir, f'{lk}_33.cube'), float(w)))
    for _, _, cube, _ in cols:
        if cube and not os.path.exists(cube): sys.exit(f'missing cube: {cube}')
    tiles = []
    for r, spec in enumerate(frames):
        raw = os.path.join(d, f'raw-{r}.png'); grab(spec, raw, H); row = []
        for c, (label, vf, cube, w) in enumerate(cols):
            o = os.path.join(d, f't-{r}-{c}.png')
            if c == 0: o = raw
            else: render(raw, o, vf=vf, cube=cube, blend=w)
            row.append(o)
        tiles.append(row)
    ims = [[Image.open(o).convert('RGB') for o in row] for row in tiles]
    W = max(im.width for row in ims for im in row); sheet = Image.new('RGB', (W * len(cols), H * len(frames) + 28), 'black'); dr = ImageDraw.Draw(sheet)
    for c, (label, *_ ) in enumerate(cols): dr.text((c * W + 6, 6), label, fill='yellow')
    for r, row in enumerate(ims):
        for c, im in enumerate(row): sheet.paste(im, (c * W + (W - im.width) // 2, 28 + r * H))
        dr.text((6, 28 + r * H + 6), os.path.basename(frames[r].rsplit('@', 1)[0]), fill='yellow')
    os.makedirs(os.path.dirname(os.path.abspath(out)) or '.', exist_ok=True); sheet.save(out, quality=88)
    return sheet.size, [c[0] for c in cols]


def selftest():
    d = tempfile.mkdtemp(); cube = os.path.join(d, 'ident_33.cube')
    with open(cube, 'w') as f:   # a 2-point identity cube: the instrument, not the look, is under test
        f.write('LUT_3D_SIZE 2\n'); [f.write(f'{r} {g} {b}\n') for b in (0.0, 1.0) for g in (0.0, 1.0) for r in (0.0, 1.0)]
    f1 = os.path.join(d, 'a.png'); f2 = os.path.join(d, 'b.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=160x284:d=1', '-frames:v', '1', f1], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=160x284:d=2:r=24', '-pix_fmt', 'yuv420p', f2], check=True)
    out = os.path.join(d, 'sheet.jpg'); size, cols = build([f1, f2 + '@1.0'], d, ['ident'], 'ident:0.5', 'eq=saturation=1.2', out, H=142)
    ok = cols == ['raw', 'current', 'ident', 'ident 50%'] and size[1] == 142 * 2 + 28 and size[0] == 4 * 80 and os.path.getsize(out) > 1000
    print(f"SELFTEST {'PASS' if ok else 'FAIL'}: columns {cols}, sheet {size}")
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--frame', action='append', default=[], help='<video>@<seconds> or an image; repeat')
    ap.add_argument('--cubes', default=os.environ.get('LOOK_LIBRARY_CUBES', os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'look-library', 'cubes')), help='the baked <look>_33.cube files (look-library/GUIDE.md: bake them first)')
    ap.add_argument('--looks', default='ads-clean'); ap.add_argument('--blend', default=None, help='<look>:<weight>, one extra column')
    ap.add_argument('--current', default=None, help='the chain currently in the builder, as an ffmpeg -vf string'); ap.add_argument('--out'); ap.add_argument('--tile-h', type=int, default=384)
    ap.add_argument('--selftest', action='store_true'); a = ap.parse_args()
    if a.selftest: selftest()
    if not a.frame or not a.out: ap.error('--frame (repeat) and --out are required')
    size, cols = build(a.frame, a.cubes, [x for x in a.looks.split(',') if x], a.blend, a.current, a.out, a.tile_h)
    print(f'sheet {a.out} {size[0]}x{size[1]} · columns: {", ".join(cols)} · the operator picks a column by name; the pick is the --look of every finish from now on')


if __name__ == '__main__':
    main()
