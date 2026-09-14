#!/usr/bin/env python3
"""sfx_onsets.py — the syllable map of an SFX file BEFORE it is cut: onsets (a rise of ≥ --rise dB over the preceding
60 ms floor) listed by ordinal with their times and peaks, so a reel pick given in the operator's words — "the four before
the last one", "the end one, not the bitten-off start", "the second last one that starts at 0:43" — maps to sample-exact
cut points. --cut a:b writes the excerpt with 5 ms fades. Self-test first: a synthesized
four-click file must yield exactly four onsets, or nothing else is printed.

  sfx_onsets.py <file> [--rise 12] [--hop-ms 10] [--cut 0.83:2.10 --out audio/sfx/<name>.wav]
"""
import argparse, subprocess, sys
import numpy as np

SR = 48000


def pcm(f):
    return np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True, check=True).stdout, np.float32)


def onsets(x, rise, hop_ms, min_db=-40.0, look_ms=100, refractory_ms=100):
    h = int(hop_ms / 1000 * SR); n = len(x) // h
    db = 20 * np.log10(np.sqrt(np.array([np.mean(x[i * h:(i + 1) * h] ** 2) for i in range(n)])) + 1e-9)
    out = []; look = max(1, int(look_ms / hop_ms)); ref = max(1, int(refractory_ms / hop_ms)); last = -ref
    for i in range(look, n):
        floor = db[i - look:i].min()
        if db[i] >= min_db and db[i] - floor >= rise and i - last > ref:
            pk = float(db[i:i + look].max()); out.append((round(i * hop_ms / 1000, 3), round(pk, 1))); last = i
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file'); ap.add_argument('--rise', type=float, default=12); ap.add_argument('--hop-ms', type=float, default=10); ap.add_argument('--cut'); ap.add_argument('--out')
    ap.add_argument('--min-db', type=float, default=-40, help='ignore rises that stay below this level (noise-floor flutter)')
    a = ap.parse_args()
    rng = np.random.default_rng(3); test = 0.001 * rng.standard_normal(int(1.2 * SR)).astype(np.float32)
    for k in range(4):
        i0 = int((0.2 + 0.25 * k) * SR); burst = rng.standard_normal(int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / (0.01 * SR)); test[i0:i0 + len(burst)] += 0.5 * burst.astype(np.float32)
    st = onsets(test, a.rise, a.hop_ms, a.min_db)
    if len(st) != 4: sys.exit(f'SELF-TEST FAILED: four clicks read as {len(st)} onsets {st}; the instrument is broken, nothing printed')
    print(f'self-test ok: four synthesized clicks read as four onsets at {[t for t, _ in st]}')
    x = pcm(a.file); on = onsets(x, a.rise, a.hop_ms, a.min_db)
    print(f'{a.file}: {len(x) / SR:.3f} s, {len(on)} onset(s)')
    for i, (t, d) in enumerate(on, 1): print(f'  {i:02d}  {t:7.3f} s  {d:6.1f} dBFS')
    if a.cut:
        assert a.out, '--cut needs --out'; s, e = (float(v) for v in a.cut.split(':')); assert 0 <= s < e <= len(x) / SR + 1e-6, 'cut outside the file'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{s:.4f}', '-t', f'{e - s:.4f}', '-i', a.file, '-af', f'afade=t=in:st=0:d=0.005,afade=t=out:st={max(0, e - s - 0.005):.4f}:d=0.005', '-ar', str(SR), '-c:a', 'pcm_s24le', a.out], check=True)
        print(f'wrote {a.out}: {e - s:.3f} s from {s:.3f}')


if __name__ == '__main__':
    main()
