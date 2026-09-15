#!/usr/bin/env python3
"""music_loop.py — lengthen a music take on its own beat grid, by whole bars, keeping the take's own ending.

A bed shorter than its span is looped BEFORE a longer cue is priced: play the take to a beat A, jump back a whole
number of bars to a beat B on the same bar phase, play through to the take's own ending, with a short equal-power
crossfade across the join. The ending survives — its final hit lands at (take_hit + A − B) — so a card or a marker
placed on it moves by exactly the jump. Zero spend; a second billed generation on one spot was not needed once this
existed (a 38.8 s take under a 57.9 s spot, 2026-09-15).

The beat grid comes from `--bpm` (with `--first-beat` where the first downbeat sits; the grid is arithmetic from there)
or, when `librosa` is installed and no `--bpm` is given, from beat tracking on the take. The audition is the ear's:
listen across the join at 1× and at the bar level before the loop enters a build.

  music_loop.py --take audio/music/<take>.wav --bars 8 --a-target 26 [--bpm 108 --first-beat 0.12] [--beats-per-bar 4] [--xfade 0.04] [--out <file>]
  music_loop.py --selftest      # a synthetic click track: the output is longer by exactly the jump and the ending tone moves by it

Output: <take>-loop<bars>bar-<len>s.wav (float32 WAV at the take's rate) and one line with the tempo, A, B, the jump and
the new length. `--a-target` is the timeline second near which the jump-back happens (the loop point is the nearest
beat at or before it); `--bars` is the loop length in bars.
"""
import argparse, os, sys, warnings
import numpy as np
from scipy.io import wavfile

warnings.filterwarnings('ignore')


def read_wav(p):
    sr, y = wavfile.read(p)
    if y.dtype.kind == 'i': y = y.astype('float32') / float(2 ** (8 * y.dtype.itemsize - 1))
    elif y.dtype.kind == 'u': y = (y.astype('float32') - 128.0) / 128.0
    else: y = y.astype('float32')
    if y.ndim == 1: y = y[:, None]
    return sr, y


def beat_grid(y, sr, bpm=None, first_beat=0.0, tracked=None):
    """Beat times in seconds. Arithmetic from --bpm/--first-beat; otherwise librosa beat tracking."""
    n = len(y) / sr
    if bpm:
        period = 60.0 / bpm
        return float(bpm), np.arange(first_beat, n, period)
    try:
        import librosa
    except ImportError:
        sys.exit('no --bpm given and librosa is not installed: pass --bpm <tempo> [--first-beat <s>] (measure the tempo once, by ear against a metronome or with any beat tracker)')
    ym = y.mean(axis=1)
    on = librosa.onset.onset_strength(y=ym, sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=on, sr=sr, units='time')
    return float(np.atleast_1d(tempo)[0]), np.asarray(beats, dtype='float64')


def loop(y, sr, beats, bars, beats_per_bar, a_target, xfade):
    nb = bars * beats_per_bar
    cand = np.where(beats <= a_target + 1e-9)[0]
    i = int(cand[-1]) if len(cand) else int(np.argmin(np.abs(beats - a_target)))
    if i - nb < 0: sys.exit(f'--a-target {a_target} s is too early for a {bars}-bar loop: the first usable A is beat {nb} at {beats[nb]:.3f} s')
    A, B = float(beats[i]), float(beats[i - nb]); jump = A - B
    xf = max(1, int(xfade * sr)); sA, sB = int(round(A * sr)), int(round(B * sr))
    if sA + xf > len(y) or sB - xf < 0: sys.exit('the crossfade window runs past the take: shorten --xfade or move --a-target')
    head = y[:sA + xf].copy(); tail = y[sB - xf:].copy()
    w = np.linspace(0, 1, 2 * xf, dtype='float32')[:, None]          # equal-power crossfade across the join
    head[-2 * xf:] *= np.cos(w * np.pi / 2); tail[:2 * xf] *= np.sin(w * np.pi / 2)
    out = np.concatenate([head[:-2 * xf], head[-2 * xf:] + tail[:2 * xf], tail[2 * xf:]])
    return out, A, B, jump, i


def selftest():
    sr, bpm, bpb = 48000, 120.0, 4
    period = 60.0 / bpm; n = int(20.0 * sr); t = np.arange(n) / sr
    y = np.zeros((n, 1), dtype='float32')
    for k in range(int(20.0 / period)):                                  # a click on every beat
        s = int(k * period * sr); y[s:s + 240, 0] += np.hanning(240).astype('float32') * 0.5
    end = int(19.0 * sr); y[end:end + 4800, 0] += (0.3 * np.sin(2 * np.pi * 440 * t[:4800])).astype('float32')   # the "ending" tone at 19.0 s
    tempo, beats = beat_grid(y, sr, bpm=bpm, first_beat=0.0)
    out, A, B, jump, i = loop(y, sr, beats, bars=2, beats_per_bar=bpb, a_target=10.0, xfade=0.02)
    assert abs(jump - 2 * bpb * period) < 1e-6, jump
    assert abs(len(out) / sr - (20.0 + jump)) < 0.002, len(out) / sr
    env = np.abs(out[:, 0]); seg = env[int(18.0 * sr):]                   # the tone: a sustained region, unlike a 5 ms click
    win = int(0.05 * sr); rms = np.sqrt(np.convolve(seg ** 2, np.ones(win) / win, mode='valid'))   # 50 ms: a click reads ~0.10, the tone 0.21
    tone_at = 18.0 + int(np.argmax(rms > 0.17)) / sr
    assert abs(tone_at - (19.0 + jump)) < 0.06, (tone_at, 19.0 + jump)     # within the 50 ms detection window
    print(f'SELFTEST PASS — bpm {tempo:.0f}: A {A:.3f} B {B:.3f} jump {jump:.3f} s = 2 bars; length 20.000 → {len(out)/sr:.3f} s; the ending tone moved 19.000 → {tone_at:.3f} s')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--take'); ap.add_argument('--bars', type=int, default=8); ap.add_argument('--beats-per-bar', type=int, default=4)
    ap.add_argument('--a-target', type=float, help='the take second near which the loop jumps back (the nearest beat at or before it)')
    ap.add_argument('--bpm', type=float); ap.add_argument('--first-beat', type=float, default=0.0, help='where the first downbeat sits, with --bpm')
    ap.add_argument('--xfade', type=float, default=0.04); ap.add_argument('--out'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: return selftest()
    if not a.take or a.a_target is None: ap.error('--take and --a-target are required (or --selftest)')
    sr, y = read_wav(a.take)
    tempo, beats = beat_grid(y, sr, bpm=a.bpm, first_beat=a.first_beat)
    out, A, B, jump, i = loop(y, sr, beats, a.bars, a.beats_per_bar, a.a_target, a.xfade)
    L = len(out) / sr
    name = a.out or (os.path.splitext(a.take)[0] + f'-loop{a.bars}bar-{L:.2f}s.wav')
    if os.path.exists(name): sys.exit(f'{name} exists — a new loop is a new name, never an overwrite')
    wavfile.write(name, sr, np.clip(out, -1, 1).astype('float32'))
    print(f'tempo {tempo:.2f} bpm  period {60/tempo:.4f} s  A={A:.3f} (beat {i})  B={B:.3f}  jump {jump:.3f} s = {a.bars} bars  out {name}  len {L:.3f} s  the take\'s ending moved by +{jump:.3f} s')


if __name__ == '__main__':
    main()
