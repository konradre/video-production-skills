#!/usr/bin/env python3
"""window_frames.py — EVERY frame of a window of a take, cropped to a box, enlarged, gamma-lifted, tiled with
frame numbers: the named-state check (teeth after the drop, the hand, the pane, a limb count per person).
A sparse sample of the window passes defects that every frame shows; this shows every frame.

  window_frames.py --in <take.mp4> --from 2.9 --to 3.3 --out review/name.png [--box x0,y0,x1,y1] [--zoom 4]
                   [--gamma 1.6] [--cols 8]
  window_frames.py --selftest
--gamma > 1 lifts dark cavities (an open mouth) so the teeth read; --box in source pixels (default: the whole frame).
--out .png, or .jpg written at q95 4:4:4: this is a VERDICT image — cropped to what is judged, never downscaled, never at a
survey quality (INSTRUMENTS § review images).
Self-test cells, both from the source frame at --from with no gamma: cell 0 'SRC' is the whole frame with the box outlined,
fitted INTO the cell size (never enlarged), so the crop is placed in its frame; cell 1 'SRC 1:1' (with --box) is the box's own
pixels unscaled, so the enlargement and the gamma can be checked against them. Cell 0 used to be the full frame at full size,
which set every cell's size: a 240 × 180 box at zoom 1 on a 1920 × 1080 source tiled 120 crops in 1920 × 1080 cells, a sheet
15 408 px wide where each crop filled an eighth of its cell (2026-10-29).
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
    ap.add_argument('--selftest', action='store_true')
    if '--selftest' in sys.argv: sys.exit(selftest())
    a = ap.parse_args()
    fps, W, H = probe(a.src)
    fr = frames(a.src, a.t0, a.t1)
    if not fr: sys.exit('no frames decoded in the window')
    box = [int(v) for v in a.box.split(',')] if a.box else [0, 0, W, H]
    cw, ch = int((box[2] - box[0]) * a.zoom), int((box[3] - box[1]) * a.zoom)   # every crop cell's size
    ref = fr[0].copy(); ImageDraw.Draw(ref).rectangle(box, outline=(255, 40, 40), width=max(2, W // 480))
    sc = min(1.0, cw / W, ch / H)   # the whole frame fitted INTO a crop cell, never enlarged
    tiles = [ref.resize((max(1, int(W * sc)), max(1, int(H * sc))), Image.LANCZOS) if sc < 1 else ref]   # self-test cell 0
    labels = [f'SRC f{int(round(a.t0 * fps))}' + (f' (×{sc:.2f})' if sc < 1 else '')]
    if a.box:
        tiles.append(fr[0].crop(box)); labels.append('SRC 1:1')   # self-test cell 1: the box's own pixels, no zoom, no gamma
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
    print(f'{a.out}: {len(fr)} frames {a.t0:.3f}–{a.t1:.3f}s @ {fps:.3f} fps, box {box}, zoom {a.zoom}, gamma {a.gamma}, {sheet.width}×{sheet.height} '
          f'(cell 0 = the source frame fitted to the cell with the box outlined' + ('; cell 1 = the box at 1:1, no gamma)' if a.box else ')'))


def selftest():
    """a 1920 × 1080 clip with a known pattern: the sheet's cells take the CROP size (not the frame's), cell 0 fits inside one,
    and cell 1 holds the box's source pixels exactly"""
    import tempfile, os
    d = tempfile.mkdtemp(prefix='window_frames_selftest_'); clip = os.path.join(d, 'c.mkv'); out = os.path.join(d, 's.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=1920x1080:r=25:d=1', '-c:v', 'ffv1', '-pix_fmt', 'rgb24', clip], check=True)
    box = (880, 480, 1120, 660); bw, bh = box[2] - box[0], box[3] - box[1]
    subprocess.run([sys.executable, os.path.abspath(__file__), '--in', clip, '--from', '0', '--to', '0.2', '--box', ','.join(map(str, box)),
                    '--zoom', '1', '--gamma', '1.6', '--cols', '4', '--out', out], check=True, capture_output=True)
    sheet = Image.open(out).convert('RGB'); src = frames(clip, 0.0, 0.04)[0]
    bad = []
    if sheet.width != 4 * (bw + 6): bad.append(f'sheet width {sheet.width} (want {4 * (bw + 6)}: cells at the crop size)')
    got = sheet.crop(((bw + 6), 20, (bw + 6) + bw, 20 + bh))   # cell 1
    if np.abs(np.asarray(got, np.int16) - np.asarray(src.crop(box), np.int16)).max() > 0: bad.append('cell 1 is not the box at 1:1')
    if np.asarray(sheet.crop((0, 20, bw, 20 + bh))).std() < 1: bad.append('cell 0 is empty')
    for f in (clip, out): os.remove(f)
    os.rmdir(d)
    print('SELFTEST ' + ('PASS' if not bad else 'FAIL\n  ' + '\n  '.join(bad)) + f' — sheet {sheet.width}×{sheet.height} for a {bw}×{bh} box on 1920×1080')
    return 0 if not bad else 1


if __name__ == '__main__':
    main()
