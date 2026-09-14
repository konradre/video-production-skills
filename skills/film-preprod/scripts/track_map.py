#!/usr/bin/env python3
"""track_map.py — the TRACK MAP of a music video, measured not guessed, before the gen map: per-second features (dB, low
20–140 Hz, mid, hi > 4 kHz band energy, spectral centroid), the tempo by autocorrelation of the onset envelope, the bar and
the 8-bar phrase, and the section markers read off three independent signals — hats enter (hi jumps), a build-up (low
decays while mid/hi rise), an IMPACT (low snaps back), a near-SILENCE (dB collapses), the PEAK bass — so every later beat
is a placement on a hit, paid for by trimming, never an append. Writes features.json beside the map. Self-test first: a
synthesized click track at 120 BPM must read 120 ± 2 or nothing is printed.

  track_map.py --audio audio/track.wav [--out analysis/features.json] [--bpm-range 60,200]
"""
import argparse, json, subprocess, sys
import numpy as np

SR = 22050


def pcm(f):
    return np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True, check=True).stdout, np.float32)


def bpm_of(x, lo, hi):
    h = 128; n = len(x) // h; env = np.sqrt(np.mean(x[:n * h].reshape(n, h) ** 2, axis=1)); on = np.maximum(np.diff(env, prepend=env[0]), 0)
    on = on - on.mean(); fps = SR / h; ac = np.correlate(on, on, 'full')[len(on) - 1:]
    lag0, lag1 = int(fps * 60 / hi), int(fps * 60 / lo); k = lag0 + int(np.argmax(ac[lag0:lag1]))
    if 0 < k < len(ac) - 1:   # parabolic refinement of the peak lag (a 128-sample hop alone quantises to ±0.6 BPM at 120)
        y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]; d = (y0 - y2) / (2 * (y0 - 2 * y1 + y2)) if (y0 - 2 * y1 + y2) != 0 else 0.0; k = k + float(np.clip(d, -0.5, 0.5))
    return 60.0 * fps / k


def features(x):
    n = len(x) // SR; F = []
    for i in range(n):
        s = x[i * SR:(i + 1) * SR]; P = np.abs(np.fft.rfft(s * np.hanning(len(s)))) ** 2; fr = np.fft.rfftfreq(len(s), 1 / SR)
        band = lambda a, b: float(np.sqrt(P[(fr >= a) & (fr < b)].sum()) / len(s) * 1e3)
        cen = float((fr * P).sum() / (P.sum() + 1e-12)); db = float(20 * np.log10(np.sqrt(np.mean(s ** 2)) + 1e-9))
        F.append({'t': i, 'db': round(db, 1), 'low': round(band(20, 140), 1), 'mid': round(band(140, 4000), 1), 'hi': round(band(4000, SR / 2), 2), 'centroid': round(cen)})
    return F


def mmss(t): return f'{int(t) // 60}:{int(t) % 60:02d}'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); ap.add_argument('--audio', required=True); ap.add_argument('--out'); ap.add_argument('--bpm-range', default='60,200')
    a = ap.parse_args(); lo, hi = (float(v) for v in a.bpm_range.split(','))
    t = np.arange(int(8 * SR)) / SR; click = np.zeros_like(t, dtype=np.float32)
    for k in range(16): i0 = int(k * 0.5 * SR); click[i0:i0 + 300] = np.exp(-np.arange(300) / 60).astype(np.float32)
    b = bpm_of(click, lo, hi)
    if abs(b - 120) > 2: sys.exit(f'SELF-TEST FAILED: a 120 BPM click track read as {b:.1f} — the instrument is broken, nothing printed')
    print(f'self-test ok: a 120 BPM click reads {b:.1f}')
    x = pcm(a.audio); dur = len(x) / SR; bpm = bpm_of(x, lo, hi); bar = 4 * 60 / bpm; F = features(x)
    print(f'{a.audio}: {dur:.3f} s · {bpm:.1f} BPM · bar = {bar:.3f} s · 8-bar phrase = {8 * bar:.3f} s · 16-bar = {16 * bar:.2f} s')
    lows = np.array([f['low'] for f in F]); his = np.array([f['hi'] for f in F]); dbs = np.array([f['db'] for f in F]); ev = []
    med_db = float(np.median(dbs)); med_hi = float(np.median(his) + 1e-6)
    for i in range(1, len(F)):
        if dbs[i] < med_db - 8 and dbs[i - 1] >= med_db - 4: ev.append((i, 'SILENCE', f'dB {dbs[i-1]} → {dbs[i]}'))
        if his[i] > 2.5 * max(his[max(0, i - 3):i].mean(), 0.05) and his[i] > med_hi: ev.append((i, 'hats enter', f'hi {his[i-1]} → {his[i]}'))
        if i >= 4 and lows[i] > 4 * max(lows[i - 4:i].mean(), 0.5) and lows[i - 4:i].mean() < 0.5 * np.median(lows): ev.append((i, 'IMPACT (low snaps back)', f'low {lows[i-4:i].mean():.1f} → {lows[i]}'))
        if i >= 8 and lows[i - 8:i].mean() > 0.6 * np.median(lows) and lows[i] < 0.2 * np.median(lows) and his[i] >= his[i - 8]: ev.append((i, 'build-up starts (low decays, hi holds/rises)', f'low → {lows[i]}'))
    pk = int(np.argmax(lows)); ev.append((pk, 'PEAK bass', f'low = {lows[pk]}'))
    print('\n| time | event | signal |'); print('|---|---|---|')
    for i, name, sig in sorted(ev): print(f'| **{mmss(i)}** | {name} | {sig} |')
    print(f'\nallocate the whole {dur:.1f} s to phrases of {8 * bar:.2f} s first; every later beat is a placement on one of the hits above, paid for by trimming a looser stretch')
    if a.out:
        json.dump({'audio': a.audio, 'duration_s': round(dur, 3), 'bpm': round(bpm, 1), 'bar_s': round(bar, 3), 'phrase8_s': round(8 * bar, 3), 'features': F, 'events': [{'t': i, 'event': n, 'signal': s} for i, n, s in sorted(ev)]}, open(a.out, 'w'), indent=1); print('wrote', a.out)


if __name__ == '__main__':
    main()
