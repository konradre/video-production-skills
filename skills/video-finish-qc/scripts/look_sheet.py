#!/usr/bin/env python3
"""look_sheet.py — the frame sheet the operator picks the LOOK from, before the first delivered version: a few frames of the
project's own footage (and its generated stills) as columns raw · [the current chain] · each candidate cube at full strength ·
[one cube at a blend]. The grade starts from the look library's cube for the genre, also on existing footage; a hand-written
level chain is a deviation that needs a reason (two such chains stood for ten hours on a documentary spot, 2026-09-15).
A cube is the GRADE step, never the normalise step: on flat footage (overcast, full-range phone clips, a re-encode) every cube
column read pale beside a hand-normalised chain, because the sheet compared "normalised, no look" with "look, no normalisation"
(2026-09-16). `--normalise auto` levels each frame (0.5/99.5 luma percentiles -> 0.02/0.88) and, with --target-chroma, lands its
saturation on the target — the per-shot normalise of normalise_shots.py on the tile — then renders every cube ON the normalised
frame beside a normalised-only column; `--normalise "<chain>"` takes a chain of your own (run `colorlevels` on `format=gbrp16le`:
ffmpeg 6.1 segfaults on it over packed rgb24). A sheet pick is provisional until one
delivered spot has been watched in motion at full size.

  look_sheet.py --out review/looks/SHEET-looks.jpg --cubes <dir of <look>_33.cube> --looks ads-clean,ads-warm \\
                [--normalise auto [--target-chroma 0.0275] | --normalise "<chain>"] [--blend ads-clean:0.85] \\
                [--current "<ffmpeg filter chain>"] --frame takes/a.mp4@3.0 --frame stills/AER2.png …
  look_sheet.py --selftest
A frame is `<video>@<seconds>` or an image path; every frame is scaled to the tile height at true display shape (`setsar=1`).
The cube is applied on a 16-bit planar frame with tetrahedral interpolation (look-library GUIDE § 6b); a blend mixes the graded
and ungraded frames at the given weight.
"""
import argparse, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))


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


def auto_chain(png, target_chroma):   # the per-shot normalise measured on the tile itself (normalise_shots.py)
    import numpy as np; from PIL import Image; import normalise_shots as ns
    f = np.asarray(Image.open(png).convert('RGB'), np.float32) / 255; lo, hi = ns.levels(ns.luma(f).ravel())
    lev = ns.B_OUT + (ns.W_OUT - ns.B_OUT) * np.clip((f - lo) / (hi - lo), 0, 1)
    sat = float(np.clip(target_chroma / max(ns.chroma(lev), 1e-4), *ns.SAT_RANGE)) if target_chroma else 1.0
    return ns.chain({'lo': round(lo, 4), 'hi': round(hi, 4), 'sat': round(sat, 3)})


def build(frames, cubes_dir, looks, blend, current, out, H=384, normalise=None, target_chroma=None):
    from PIL import Image, ImageDraw
    d = tempfile.mkdtemp(); cols = [('raw', None, None, None)]
    if current: cols.append(('current', current, None, None))
    if normalise: cols.append(('normalised', 'NORM', None, None))
    on = 'normalised + ' if normalise else ''
    for lk in looks: cols.append((on + lk, None, os.path.join(cubes_dir, f'{lk}_33.cube'), None))
    if blend: lk, w = blend.split(':'); cols.append((f'{on}{lk} {float(w):.0%}', None, os.path.join(cubes_dir, f'{lk}_33.cube'), float(w)))
    for _, _, cube, _ in cols:
        if cube and not os.path.exists(cube): sys.exit(f'missing cube: {cube}')
    tiles = []
    for r, spec in enumerate(frames):
        raw = os.path.join(d, f'raw-{r}.png'); grab(spec, raw, H); row = []; base = raw
        if normalise:
            base = os.path.join(d, f'norm-{r}.png')
            render(raw, base, vf=(auto_chain(raw, target_chroma) if normalise == 'auto' else normalise) + ',format=rgb24')
        for c, (label, vf, cube, w) in enumerate(cols):
            o = os.path.join(d, f't-{r}-{c}.png')
            if c == 0: o = raw
            elif vf == 'NORM': o = base
            elif vf: render(raw, o, vf=vf)                        # the current chain works on the raw frame, as in the builder
            else: render(base, o, cube=cube, blend=w)             # every cube on the normalised frame when --normalise is set
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
    flat = os.path.join(d, 'flat.png')   # a flat frame (luma ~0.35-0.62): the normalised column must stretch it
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f1, '-vf', 'format=gbrp16le,colorlevels=romin=0.35:gomin=0.35:bomin=0.35:romax=0.62:gomax=0.62:bomax=0.62,format=rgb24', flat], check=True)
    out2 = os.path.join(d, 'sheet2.jpg'); size2, cols2 = build([flat], d, ['ident'], None, None, out2, H=142, normalise='auto', target_chroma=0.03)
    from PIL import Image
    import numpy as np
    nt = np.asarray(Image.open(out2).convert('L'), np.float32)[28:, 80:160] / 255; rt = np.asarray(Image.open(out2).convert('L'), np.float32)[28:, 0:80] / 255
    spread = (np.percentile(nt, 99) - np.percentile(nt, 1)) / max(np.percentile(rt, 99) - np.percentile(rt, 1), 1e-3)
    ok2 = cols2 == ['raw', 'normalised', 'normalised + ident'] and spread > 1.3   # the guards cap the stretch at x1.8
    print(f"SELFTEST {'PASS' if ok and ok2 else 'FAIL'}: columns {cols}, sheet {size}; with --normalise auto {cols2}, luma spread x{spread:.2f} over raw")
    ok = ok and ok2
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--frame', action='append', default=[], help='<video>@<seconds> or an image; repeat')
    ap.add_argument('--cubes', default=os.environ.get('LOOK_LIBRARY_CUBES', os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'look-library', 'cubes')), help='the baked <look>_33.cube files (look-library/GUIDE.md: bake them first)')
    ap.add_argument('--looks', default='ads-clean'); ap.add_argument('--blend', default=None, help='<look>:<weight>, one extra column')
    ap.add_argument('--current', default=None, help='the chain currently in the builder, as an ffmpeg -vf string'); ap.add_argument('--out'); ap.add_argument('--tile-h', type=int, default=384)
    ap.add_argument('--normalise', default=None, help='auto (per-frame levels, + saturation with --target-chroma) or an ffmpeg chain; cubes render on the normalised frame')
    ap.add_argument('--target-chroma', type=float, default=None, help='with --normalise auto: the chroma target (normalise_shots.py measure prints it)')
    ap.add_argument('--selftest', action='store_true'); a = ap.parse_args()
    if a.selftest: selftest()
    if not a.frame or not a.out: ap.error('--frame (repeat) and --out are required')
    size, cols = build(a.frame, a.cubes, [x for x in a.looks.split(',') if x], a.blend, a.current, a.out, a.tile_h, a.normalise, a.target_chroma)
    print(f'sheet {a.out} {size[0]}x{size[1]} · columns: {", ".join(cols)} · the operator picks a column by name; the pick is the --look of every finish from now on')


if __name__ == '__main__':
    main()
