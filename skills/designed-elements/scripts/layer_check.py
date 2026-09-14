#!/usr/bin/env python3
"""layer_check.py — is this PNG sequence a valid post layer, and when does it cover the frame? Checks a rendered layer
(frames/frame_%06d.png): contiguous numbering, one raster, RGBA with a real alpha channel, the count against the expected
duration, and the alpha coverage per frame — printing the first frame at which coverage reaches --opaque (the "opaque from
+0.29 s" figure the edit needs to place a piece wall so it straddles a join) and the last. Exit 1 on a structural FAIL.

  layer_check.py --frames hyper/<name>/frames [--fps 24] [--expect-dur 1.0] [--opaque 0.99]
"""
import argparse, glob, os, re, sys
import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--frames', required=True); ap.add_argument('--fps', type=float, default=24); ap.add_argument('--expect-dur', type=float); ap.add_argument('--opaque', type=float, default=0.99)
    a = ap.parse_args(); files = sorted(glob.glob(os.path.join(a.frames, '*.png'))); fails = []
    if not files: sys.exit(f'FAIL no PNG frames under {a.frames}')
    nums = [int(m.group(1)) for f in files for m in [re.search(r'(\d+)\.png$', f)] if m]
    if nums != list(range(nums[0], nums[0] + len(nums))): fails.append(f'numbering not contiguous ({nums[0]}..{nums[-1]}, {len(nums)} files)')
    sizes, cov = set(), []
    for f in files:
        im = Image.open(f); sizes.add((im.size, im.mode))
        if im.mode != 'RGBA': fails.append(f'{os.path.basename(f)} is {im.mode}, not RGBA'); cov.append(1.0); continue
        al = np.asarray(im.getchannel('A')); cov.append(float((al > 8).mean()))
    if len(sizes) > 1: fails.append(f'mixed rasters/modes: {sizes}')
    dur = len(files) / a.fps
    if a.expect_dur and abs(dur - a.expect_dur) > 0.5 / a.fps: fails.append(f'{len(files)} frames = {dur:.3f} s, expected {a.expect_dur} s')
    first = next((i for i, c in enumerate(cov) if c >= a.opaque), None); last = next((i for i in range(len(cov) - 1, -1, -1) if cov[i] >= a.opaque), None)
    print(f"{a.frames}: {len(files)} frames {dur:.3f} s @ {a.fps:g} fps, {sorted(sizes)[0] if sizes else '?'}; alpha coverage min {min(cov):.3f} max {max(cov):.3f}")
    print(f"  opaque (≥{a.opaque:.0%}) from frame {first} = +{first / a.fps:.3f} s to frame {last} = +{last / a.fps:.3f} s" if first is not None else '  never fully opaque (a drift/rain layer, not a wall)')
    print('  per-frame coverage: ' + ' '.join(f'{c:.2f}' for c in cov[:48]) + (' …' if len(cov) > 48 else ''))
    for m in fails: print('FAIL', m)
    print('LAYER-CHECK ' + ('FAIL' if fails else 'PASS')); sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
