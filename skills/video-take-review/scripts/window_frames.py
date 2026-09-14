#!/usr/bin/env python3
"""window_frames.py — EVERY frame of a window of a take, cropped to a box, enlarged, gamma-lifted, tiled with
frame numbers: the named-state check (teeth after the drop, the hand, the pane, a limb count per person).
A sparse sample of the window passes defects that every frame shows; this shows every frame.

  window_frames.py --in <take.mp4> --from 2.9 --to 3.3 --out review/name.png [--box x0,y0,x1,y1] [--zoom 4]
                   [--gamma 1.6] [--cols 8]
--gamma > 1 lifts dark cavities (an open mouth) so the teeth read; --box in source pixels (default: the whole frame).
--out .png, or .jpg written at q95 4:4:4: this is a VERDICT image — cropped to what is judged, never downscaled, never at a
survey quality (INSTRUMENTS § review images).
Self-test: the tile's first cell is the source frame at --from with no zoom/gamma, so the enlargement can be checked against it.
"""
import argparse, json, subprocess, sys
from io import BytesIO
import numpy as np
from PIL import Image, ImageDraw


def probe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate,width,height', '-of', 'json', path], capture_output=True, text=True)
    st = json.loads(p.stdout)['streams'][0]; num, den = st['r_frame_rate'].split('/')
    return float(num) / float(den), int(st['width']), int(st['height'])


def frames(path, t0, t1):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t0:.4f}', '-to', f'{t1:.4f}', '-i', path, '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    out, i = [], 0
    while True:
        j = raw.find(b'\x89PNG', i + 1)
        chunk = raw[i:] if j < 0 else raw[i:j]
        if chunk.strip(): out.append(Image.open(BytesIO(chunk)).convert('RGB'))
        if j < 0: break
        i = j
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--in', dest='src', required=True); ap.add_argument('--from', dest='t0', type=float, required=True); ap.add_argument('--to', dest='t1', type=float, required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--box'); ap.add_argument('--zoom', type=float, default=4.0); ap.add_argument('--gamma', type=float, default=1.6); ap.add_argument('--cols', type=int, default=8)
    a = ap.parse_args()
    fps, W, H = probe(a.src)
    fr = frames(a.src, a.t0, a.t1)
    if not fr: sys.exit('no frames decoded in the window')
    box = [int(v) for v in a.box.split(',')] if a.box else [0, 0, W, H]
    tiles = [fr[0].copy()]   # self-test cell: the untouched source frame
    labels = [f'SRC f{int(round(a.t0 * fps))}']
    for k, im in enumerate(fr):
        c = im.crop(box).resize((int((box[2] - box[0]) * a.zoom), int((box[3] - box[1]) * a.zoom)), Image.LANCZOS)
        arr = np.asarray(c).astype(np.float32) / 255.0
        arr = np.power(arr, 1.0 / a.gamma)
        tiles.append(Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)))
        n = int(round(a.t0 * fps)) + k
        labels.append(f'f{n} {n / fps:.3f}s')
    h = max(t.height for t in tiles); w = max(t.width for t in tiles)
    cols = a.cols; rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (w + 6), rows * (h + 22)), 'black'); dr = ImageDraw.Draw(sheet)
    for i, (t, l) in enumerate(zip(tiles, labels)):
        x, y = (i % cols) * (w + 6), (i // cols) * (h + 22)
        sheet.paste(t, (x, y + 20)); dr.text((x + 3, y + 3), l, fill='white')
    if a.out.lower().endswith(('.jpg', '.jpeg')): sheet.save(a.out, quality=95, subsampling=0)
    else: sheet.save(a.out)
    print(f'{a.out}: {len(fr)} frames {a.t0:.3f}–{a.t1:.3f}s @ {fps:.3f} fps, box {box}, zoom {a.zoom}, gamma {a.gamma} (cell 0 = untouched source frame)')


if __name__ == '__main__':
    main()
