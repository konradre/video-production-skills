#!/usr/bin/env python3
"""audio_head_scan.py — a generated TONE at a take's audio head (a sustained note under a quiet cut doubles a quiet
bed — e.g. 520 Hz for 0.9 s — and is heard as a musical artifact). The first --secs seconds of each file are
scanned in 50 ms windows: spectral flatness over 100–8000 Hz below --flat (tonal) with a peak bin stable (±2 bins)
for at least --min-run seconds is reported as TONE <f> Hz <a>–<b> s. The fix is native_audio_from at <b> (or a mute
plus synthesized room tone — roomtone_synth.py), never a pasted ambience slice. Self-test first: a synthesized 520 Hz
note must be flagged and white noise must not, or nothing else is printed.

  audio_head_scan.py --root <project> (--edl edit/<SPOT>-EDL.json | --files takes/a.mp4 …) [--secs 1.5] [--flat 0.3] [--min-run 0.3]
"""
import argparse, json, os, subprocess, sys
import numpy as np

SR = 48000; WIN = 0.050


def pcm(f, t):
    return np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-t', f'{t:.3f}', '-i', f, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True, check=True).stdout, np.float32)


def tones(x, flat_thr, min_run):
    n = int(WIN * SR); w = np.hanning(n); fr = np.fft.rfftfreq(n, 1 / SR); band = (fr >= 100) & (fr <= 8000); runs = []; cur = None
    for i in range(len(x) // n):
        seg = x[i * n:(i + 1) * n]
        if np.sqrt(np.mean(seg ** 2)) < 10 ** (-60 / 20): flat, pk = 1.0, -1
        else:
            P = np.abs(np.fft.rfft(seg * w)) ** 2; Pb = P[band] + 1e-18; flat = float(np.exp(np.mean(np.log(Pb))) / np.mean(Pb)); pk = int(np.argmax(Pb))
        tonal = flat < flat_thr and pk >= 0
        if tonal and cur and abs(pk - cur[2]) <= 2: cur[1] = (i + 1) * WIN
        else:
            if cur and cur[1] - cur[0] >= min_run: runs.append(cur)
            cur = [i * WIN, (i + 1) * WIN, pk, float(fr[band][pk]) if pk >= 0 else 0.0] if tonal else None
    if cur and cur[1] - cur[0] >= min_run: runs.append(cur)
    return [(round(r[0], 2), round(r[1], 2), round(r[3])) for r in runs]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl'); ap.add_argument('--files', nargs='*', default=[]); ap.add_argument('--secs', type=float, default=1.5)
    ap.add_argument('--flat', type=float, default=0.3); ap.add_argument('--min-run', type=float, default=0.4)
    ap.add_argument('--drone-hz', type=float, default=250, help='a stable peak below this reads as DRONE (a generated low hum), above as TONE (a note)')
    a = ap.parse_args(); os.chdir(a.root)
    t = np.arange(int(1.0 * SR)) / SR; rng = np.random.default_rng(1)
    sine = (0.2 * np.sin(2 * np.pi * 520 * t) + 0.002 * rng.standard_normal(len(t))).astype(np.float32); noise = (0.1 * rng.standard_normal(len(t))).astype(np.float32)
    ts, tn = tones(sine, a.flat, a.min_run), tones(noise, a.flat, a.min_run)
    if not (ts and abs(ts[0][2] - 520) <= 40) or tn: sys.exit(f'SELF-TEST FAILED: sine -> {ts}, noise -> {tn}; the instrument is broken, no files scanned')
    print(f'self-test ok: a 520 Hz note reads as {ts[0]}, white noise reads clean')
    files = list(a.files)
    if a.edl: files += [x['take'] for x in json.load(open(a.edl, encoding='utf-8'))['events'] if x.get('take') and x.get('source') != 'designed']
    seen = set(); flagged = 0
    for f in files:
        if f in seen or not os.path.exists(f): continue
        seen.add(f); r = tones(pcm(f, a.secs), a.flat, a.min_run)
        if r: flagged += 1
        lab = 'TONE ' if any(hz >= a.drone_hz for _, _, hz in r) else 'DRONE' if r else 'clean'
        print(f"{lab} {f}" + ''.join(f"  {'tone' if hz >= a.drone_hz else 'drone'} {hz} Hz {s0}–{s1} s" for s0, s1, hz in r))
    print(f'{flagged} of {len(seen)} file(s) carry a stable tone or drone in the first {a.secs} s — the ear decides which are artifacts; the scan only locates them')


if __name__ == '__main__':
    main()
