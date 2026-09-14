#!/usr/bin/env python3
"""hero_distinct.py — are these hero renders actually different clips? DNxHR/ProRes intermediates of equal frame count
have IDENTICAL byte sizes, so a size listing cannot tell a fresh render from a stale one served from a cached media-pool
path. Each file's first, middle and last frames are hashed (raw grey pixels) and identical frame-hash triples are
reported as duplicates; frame counts and rasters are printed beside them. Self-test: a file against itself must read as
identical, or nothing else is printed.

  hero_distinct.py edit/hero/a.mov edit/hero/b.mov …
"""
import argparse, hashlib, json, subprocess, sys


def info(p):
    o = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries', 'stream=nb_read_frames,width,height,pix_fmt', '-of', 'json', p], capture_output=True, text=True).stdout)['streams'][0]
    return int(o.get('nb_read_frames') or 0), o.get('width'), o.get('height'), o.get('pix_fmt')


def fhash(p, idx):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-vf', f"select='eq(n\\,{idx})',scale=64:64,format=gray", '-frames:v', '1', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return hashlib.md5(raw).hexdigest()[:10]


def triple(p, n): return tuple(fhash(p, i) for i in (0, n // 2, max(0, n - 1)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); ap.add_argument('files', nargs='+'); a = ap.parse_args()
    n0 = info(a.files[0])[0]
    if triple(a.files[0], n0) != triple(a.files[0], n0): sys.exit('SELF-TEST FAILED: a file did not match itself; the instrument is broken')
    print(f'self-test ok: {a.files[0]} matches itself')
    seen = {}; dup = 0
    for p in a.files:
        n, w, h, pf = info(p); t = triple(p, n); key = (n, t)
        flag = f'  DUPLICATE of {seen[key]}' if key in seen else ''; dup += bool(flag); seen.setdefault(key, p)
        print(f'{p}: {n} frames {w}x{h} {pf} hashes {"/".join(t)}{flag}')
    print(f'{dup} duplicate(s) among {len(a.files)} file(s)'); sys.exit(1 if dup else 0)


if __name__ == '__main__':
    main()
