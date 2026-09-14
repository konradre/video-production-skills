#!/usr/bin/env python3
"""roomtone_synth.py — CLEAN, stationary room tone matched to a reference slice's spectral colour and level. A pasted
ambience slice carries the take's artifacts (it must be clean and consistent); a hard mute reads as a hole (the drop
from room fuzz to total silence is audible). This takes a short clean stretch of
a sibling take (the same room), averages its magnitude spectrum, smooths it in log-frequency (drops narrow tonal peaks
and hum, keeps the broad colour), colours independent white noise per channel with that envelope in ONE FFT over the
whole length (exactly stationary — no loop seams, no transients), matches RMS, applies fades, writes a WAV.

  roomtone_synth.py --ref takes/<take>.mp4 --ss 3.2 --t 0.6 --dur 2.5 --out audio/sfx/<SPOT>-roomtone-synth.wav
                    [--fade-in 0.01] [--fade-out 0.25] [--gain-db 0] [--seed 7]
"""
import argparse, subprocess
import numpy as np

SR = 48000


def pcm(f, ss, t):
    return np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(ss), '-t', str(t), '-i', f, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout, np.float32).reshape(-1, 2).astype(np.float64)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ref', required=True); ap.add_argument('--ss', type=float, required=True); ap.add_argument('--t', type=float, required=True)
    ap.add_argument('--dur', type=float, required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--fade-in', type=float, default=0.01); ap.add_argument('--fade-out', type=float, default=0.25); ap.add_argument('--gain-db', type=float, default=0.0); ap.add_argument('--seed', type=int, default=7)
    a = ap.parse_args()
    ref = pcm(a.ref, a.ss, a.t); L = int(a.dur * SR); rng = np.random.default_rng(a.seed)
    N = 2048; Hh = 512; w = np.hanning(N); freqs = np.fft.rfftfreq(N, 1 / SR)

    def mean_mag(x):
        return np.mean([np.abs(np.fft.rfft(x[i:i + N] * w)) for i in range(0, len(x) - N, Hh)], axis=0)

    def smooth_log(mag):   # 1/6-octave moving average in log-frequency
        out = mag.copy()
        for k in range(1, len(mag)):
            f = freqs[k]; i0 = max(1, int(np.searchsorted(freqs, f * 2 ** (-1 / 12)))); i1 = max(i0 + 1, int(np.searchsorted(freqs, f * 2 ** (1 / 12)))); out[k] = mag[i0:i1].mean()
        out[0] = 0; return out

    gain = 10 ** (a.gain_db / 20); out = np.zeros((L, 2), np.float32)
    for ch in range(2):
        env = smooth_log(mean_mag(ref[:, ch])); grid = np.fft.rfftfreq(L, 1 / SR); envL = np.interp(grid, freqs, env)
        y = np.fft.irfft(np.fft.rfft(rng.standard_normal(L)) * envL, n=L)
        y *= np.sqrt(np.mean(ref[:, ch] ** 2)) / np.sqrt(np.mean(y ** 2)) * gain; out[:, ch] = y
    fi = int(a.fade_in * SR); fo = int(a.fade_out * SR)
    if fi: out[:fi] *= np.linspace(0, 1, fi)[:, None]
    if fo: out[-fo:] *= np.linspace(1, 0, fo)[:, None]
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'pcm_s16le', a.out], input=out.astype(np.float32).tobytes(), check=True)
    r = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
    print(f"ref RMS {r(ref):.1f} dBFS (peak {20 * np.log10(np.abs(ref).max() + 1e-12):.1f}) -> bed RMS {r(out):.1f} dBFS (peak {20 * np.log10(np.abs(out).max() + 1e-12):.1f}), {a.dur} s, stationary, wrote {a.out}")


if __name__ == '__main__':
    main()
