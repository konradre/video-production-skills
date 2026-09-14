#!/usr/bin/env python3
"""split_sheet.py — split a 3-column character sheet (portrait | full front | full back) into single-view
crops. Why: an image model blends a montage into an average subject (a large and a small character averaged
is a dwarf) — one subject per reference, native resolution, never a montage.
Writes <out-dir>/<stem>-portrait.png, -front.png, -back.png (out-dir defaults to <sheet dir>/single).

  split_sheet.py <sheet.png> [<sheet2.png> ...] [--out-dir DIR] [--names portrait,front,back]
"""
import argparse
from pathlib import Path
from PIL import Image


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sheets', nargs='+')
    ap.add_argument('--out-dir')
    ap.add_argument('--names', default='portrait,front,back', help='one name per column, left to right')
    a = ap.parse_args()
    names = a.names.split(',')
    for src in map(Path, a.sheets):
        im = Image.open(src); w, h = im.size
        n = len(names)
        out_dir = Path(a.out_dir) if a.out_dir else src.parent / 'single'
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = src.stem.split('-sheet')[0]
        for i, name in enumerate(names):
            x0, x1 = i * w // n, (i + 1) * w // n
            dest = out_dir / f'{stem}-{name}.png'
            im.crop((x0, 0, x1, h)).save(dest)
            print(f'  {dest}  {x1 - x0}x{h}')


if __name__ == '__main__':
    main()
