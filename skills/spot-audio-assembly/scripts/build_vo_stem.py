#!/usr/bin/env python3
"""build_vo_stem.py — place EVERY VO line the EDL carries (each audio.vo entry with a file — the O.S. line, the dubs,
the narrator) on a silent stem at its EDL time, gained to target_lufs with a peak cap, by numpy sample placement (no
filtergraph timing drift). The finisher rebuilds this stem on every master — a stale stem once shipped a line at its
previous version's time. A `startswith('L')` filter once dropped a spot's O.S. line: every entry with a file is placed.
SOURCE HYGIENE first: every line's GAP FLOOR — the 10th percentile of its 50 ms block levels, L/R averaged — must sit at or
below --floor-max (default -40 dBFS, a lead measured on one job; a recorded voice after its repair chain, or another TTS
vendor's clean files, set the project's value). A VO file whose quietest tenth is louder carries sound between its words: an excerpt of a
finished mix brings that mix's music bed and the scene's audio into every line, and every placement instrument then
validates the contamination against itself. A line that legitimately carries sound under it (a room recording, a treated
O.S. line) declares floor_ok: "<why>". The floor and the line's source (a TTS job id, a clone id, or extracted_from:
<path> @ <s>) print for every line; the floor instrument self-tests (synthetic speech with clean gaps, then under a
-30 dBFS bed) before any file is read. A DIRTY line stops the build before the stem is written.

  build_vo_stem.py --root <project> --edl edit/<SPOT>-EDL.json [--out edit/mix/<SPOT>-vo-stem.wav] [--floor-max -40]
"""
import argparse, json, os, subprocess, sys
import numpy as np

SR = 48000
BLOCK = SR // 20   # 50 ms


def decode(f, ch):
    return np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-f', 'f32le', '-ac', str(ch), '-ar', str(SR), '-'], capture_output=True, check=True).stdout, np.float32)


def gap_floor(x):
    """the 10th percentile of 50 ms block RMS in dBFS; None when the file is too short to read (< 0.5 s)"""
    n = len(x) // BLOCK
    if n < 10: return None
    r = np.sqrt((x[:n * BLOCK].reshape(n, BLOCK).astype(np.float64) ** 2).mean(1)) + 1e-12
    return float(np.percentile(20 * np.log10(r), 10))


def self_test():
    t = np.arange(SR * 3) / SR
    speech = 0.3 * np.sin(2 * np.pi * 180 * t) * (np.sin(2 * np.pi * 2.5 * t) > 0)   # 200 ms words, 200 ms gaps of true silence
    speech[int(SR * 1.2):int(SR * 1.8)] = 0                                           # a phrase pause
    bed = 10 ** (-30 / 20) * np.sqrt(2) * np.sin(2 * np.pi * 110 * t)                 # a bed at -30 dBFS RMS
    clean, dirty = gap_floor(speech), gap_floor(speech + bed)
    ok = clean < -80 and abs(dirty + 30) < 3
    print(f"gap-floor self-test: clean gaps {clean:.1f} dBFS (want < -80) · under a -30 dBFS bed {dirty:.1f} (want -30 ± 3) -> {'OK' if ok else 'BROKEN'}")
    if not ok: sys.exit('the gap-floor instrument failed its self-test — no floor from it is used')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl', required=True); ap.add_argument('--out', help='default: audio.vo.stem from the EDL')
    ap.add_argument('--floor-max', type=float, default=-40.0, help='the loudest gap floor a clean VO file may carry, dBFS (the default is a lead from one job; set it from the clean files of this project)')
    a = ap.parse_args(); os.chdir(a.root)
    self_test()
    edl = json.load(open(a.edl, encoding='utf-8')); vo = edl['audio']['vo']; RUN = float(edl['runtime_s']); out = a.out or vo['stem']
    buf = np.zeros(int(RUN * SR), np.float32); PEAK = 10 ** (vo['peak_cap_dbfs'] / 20); T = vo['target_lufs']; dirty = []
    for k in sorted(x for x in vo if isinstance(vo[x], dict) and 'file' in vo[x]):
        t = vo[k]
        x = decode(t['file'], 1)
        assert t.get('lufs') is not None, f'{k}: no lufs in the EDL (the builder measures it; run it with the ebur128 read on)'
        fl = gap_floor(decode(t['file'], 2).reshape(-1, 2).mean(1))
        if fl is None: hyg = 'too short to read'
        elif fl <= a.floor_max: hyg = 'clean'
        elif t.get('floor_ok'): hyg = f"floor_ok: {t['floor_ok']}"
        else: hyg = 'DIRTY'; dirty.append(f"{k}: gap floor {fl:.1f} dBFS above {a.floor_max:g} — {t['file']}")
        g = 10 ** ((T - t['lufs']) / 20); pk = abs(x).max() * g
        if pk > PEAK: g *= PEAK / pk
        i0 = int(round(t['at'] * SR)); n = min(len(x), len(buf) - i0); assert n > 0, f'{k}: placed past the runtime'
        buf[i0:i0 + n] += x[:n] * g
        print(f"{k:6} at {t['at']:.3f}–{t['at'] + len(x) / SR:.3f} s  gain {20 * np.log10(g):+.1f} dB  peak {20 * np.log10(abs(x).max() * g):.1f} dBFS" + ('  TRUNCATED at the runtime' if n < len(x) else '')
              + f"  floor {'-' if fl is None else format(fl, '.1f')} dBFS ({hyg})  source {t.get('source') or 'NOT RECORDED'}")
    if dirty: sys.exit('VO SOURCE HYGIENE FAIL — sound between the words (an excerpt of a finished mix carries its bed); nothing written:\n  ' + '\n  '.join(dirty)
                       + '\n  get the clean render, or declare floor_ok: "<why>" on the entry')
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', '-c:a', 'pcm_s24le', out], input=buf.tobytes(), check=True)
    print('wrote', out, RUN, 's')


if __name__ == '__main__':
    main()
