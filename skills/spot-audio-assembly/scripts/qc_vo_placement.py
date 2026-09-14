#!/usr/bin/env python3
"""qc_vo_placement.py — where does each placed line actually SIT in the delivered file? Every VO take is matched against
the deliverable's audio around its EDL time by normalised cross-correlation of 10 ms RMS ENVELOPES in a 300–4000 Hz band
(a raw-waveform xcorr fails under loudnorm + AAC: 0.08 against 0.65–0.91 for the envelope), and the error against the
EDL is reported (|err| < --tol-ms = OK). Stereo is averaged, never summed (a unity sum reads +6 dB and clips the
measurement). Self-test first: the first take against ITSELF must land at 0 ms with NCC ≥ 0.99, or the instrument is
broken and no other number is printed.

  qc_vo_placement.py --root <project> --edl edit/<SPOT>-EDL.json --deliv deliver/<file>.mp4 [--lines L1,L2] [--tol-ms 15]
"""
import argparse, json, os, subprocess, sys
import numpy as np

SR = 48000; HOP = 0.010; WIN = 0.020


def pcm(f, ss=None, t=None):
    cmd = ['ffmpeg', '-v', 'error'] + (['-ss', f'{ss:.3f}'] if ss is not None else []) + (['-t', f'{t:.3f}'] if t else []) + ['-i', f, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-']
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)
    return x.reshape(-1, 2).mean(1)


def envelope(x):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < 300) | (f > 4000)] = 0; y = np.fft.irfft(X, n=len(x))
    h, w = int(HOP * SR), int(WIN * SR); n = max(1, (len(y) - w) // h + 1)
    return np.sqrt(np.array([np.mean(y[i * h:i * h + w] ** 2) for i in range(n)]) + 1e-12)


def ncc_lag(win, take):
    """best lag (frames) of take inside win by normalised cross-correlation; returns (lag, ncc)"""
    t = take - take.mean(); n = len(t); c = np.correlate(win, t, 'valid')
    cs = np.cumsum(np.insert(win, 0, 0.0)); cs2 = np.cumsum(np.insert(win ** 2, 0, 0.0))
    s = cs[n:] - cs[:-n]; s2 = cs2[n:] - cs2[:-n]; var = s2 - s ** 2 / n
    d = np.sqrt(np.maximum(var, 1e-12) * (t ** 2).sum()); r = c / d; k = int(np.argmax(r)); return k, float(r[k])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl', required=True); ap.add_argument('--deliv', required=True); ap.add_argument('--lines', default=''); ap.add_argument('--tol-ms', type=float, default=15)
    a = ap.parse_args(); os.chdir(a.root)
    vo = json.load(open(a.edl, encoding='utf-8'))['audio']['vo']
    lines = [x for x in a.lines.split(',') if x] or sorted(k for k in vo if isinstance(vo[k], dict) and 'file' in vo[k])
    # self-test: the first take inside a padded copy of itself
    t0 = pcm(vo[lines[0]]['file']); e0 = envelope(t0); pad = np.zeros(int(1.0 * SR), np.float32); k, r = ncc_lag(envelope(np.concatenate([pad, t0, pad])), e0)
    if abs(k * HOP - 1.0) > 0.011 or r < 0.99: sys.exit(f'SELF-TEST FAILED: a take matched itself at {k * HOP - 1.0:+.3f} s / NCC {r:.3f} — the instrument is broken; no numbers printed')
    print(f'self-test ok: {lines[0]} matches itself at {k * HOP - 1.0:+.3f} s, NCC {r:.3f}')
    ok = True
    for L in lines:
        at = float(vo[L]['at']); take = t0 if L == lines[0] else pcm(vo[L]['file']); n = len(take) / SR
        w0 = max(0.0, at - 1.0); win = pcm(a.deliv, ss=w0, t=n + 2.0)
        k, r = ncc_lag(envelope(win), envelope(take)); found = w0 + k * HOP; err = found - at
        flag = '' if abs(err) * 1000 < a.tol_ms else '  <-- OFF'; ok &= abs(err) * 1000 < a.tol_ms
        print(f"{L:6} {os.path.basename(vo[L]['file'])}: EDL at {at:.3f}  found {found:.3f}  err {err * 1000:+.0f} ms  ncc {r:.2f}{flag}")
    print('PLACEMENT OK' if ok else 'PLACEMENT ERROR'); sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
