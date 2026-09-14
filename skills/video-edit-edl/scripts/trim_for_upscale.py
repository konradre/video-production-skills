#!/usr/bin/env python3
"""trim_for_upscale.py — cut the chosen keepers into <out-dir>/<id>.mp4 WITH HANDLES for a hosted or windowed upscale,
and write handle_head back into the EDL (the finisher seeks the upscaled source by it). Run AFTER the keepers are
picked (EDL events carry take + in + out). The head handle is limited by the in-point; a tail handle past the end of
the take is clamped by ffmpeg. The full-take chain (local Rhea on the whole take -> hero pass) needs no trim:
there handle_head == in, which the builder already wrote.

  trim_for_upscale.py --root <project> --edl edit/<SPOT>-EDL.json --ids S06-A S06-B [--handle-frames 4] [--fps 24]
                      [--out-dir edit/upscale-in] [--crf 8]
Writes <edl>.bak-<ts>-pre-trim first.
"""
import argparse, json, os, shutil, subprocess, time


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl', required=True); ap.add_argument('--ids', nargs='+', required=True)
    ap.add_argument('--handle-frames', type=int, default=4); ap.add_argument('--fps', type=float, default=24.0)
    ap.add_argument('--out-dir', default='edit/upscale-in'); ap.add_argument('--crf', default='8')
    a = ap.parse_args(); os.chdir(a.root)
    H = a.handle_frames / a.fps; edl = json.load(open(a.edl, encoding='utf-8')); os.makedirs(a.out_dir, exist_ok=True)
    known = {e['id'] for e in edl['events']}; missing = [i for i in a.ids if i not in known]; assert not missing, f'not in the EDL: {missing}'
    for e in edl['events']:
        if e['id'] not in a.ids: continue
        assert e.get('take'), f"{e['id']}: take is null — pick a keeper first"
        hh = min(e['in'], H); dur = (e['out'] - e['in']) + hh + H
        out = os.path.join(a.out_dir, f"{e['id']}.mp4")
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f"{e['in'] - hh:.6f}", '-t', f"{dur:.6f}", '-i', e['take'], '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', a.crf, '-pix_fmt', 'yuv420p', out], check=True)
        e['handle_head'] = round(hh, 6)
        print(e['id'], '->', out, 'head handle', round(hh, 4), 'dur', round(dur, 3))
    shutil.copy(a.edl, f"{a.edl}.bak-{time.strftime('%Y%m%d-%H%M%S')}-pre-trim")
    json.dump(edl, open(a.edl, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('EDL handle_head updated for', a.ids)


if __name__ == '__main__':
    main()
