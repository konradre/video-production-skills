#!/usr/bin/env python3
"""beat_grid.py — a beat grid that CHECKS ITSELF before anything is cut or looped on it.

A beat tracker's tempo number is not the tempo (one measured 129.2 against a true 131.97), but the beat TIMES it returns are
good; so the grid is a least-squares line t_i = t0 + i·T through them, and it is accepted only when it holds:
  residual  the tracked beats sit within ±--residual-ms (15, half a frame at 30 fps) of the line
  drift     the kicks' offset from their nearest grid beat, regressed on time, moves under --drift-ms (10) over the track
Either failing means the tempo DRIFTS (a live or generated track that speeds up or breathes): the verdict is BEAT-MAP and
the tracked beat times are the grid — an arithmetic grid would walk off the music by the end.
Half and double time: the tracker's tempo is kept unless the kicks say otherwise — 2× when most kicks fall between the 1×
beats, 0.5× when most 1× beats carry no onset at all. Every candidate's numbers print, so an ambiguity is visible.
Pattern: video-shotcraft `references/music-beat-sync.md` (the line fit, the 15 ms acceptance, the kick check on 0.5/1/2×).

  beat_grid.py --audio <music> [--out <beat_data.json>] [--residual-ms 15] [--drift-ms 10] [--hpss] [--start <s> --dur <s>]
  beat_grid.py --selftest
beat_data.json: verdict (grid | beat-map), bpm, t0, T, beats (the grid, or the map), tracked, kicks, residual_max_ms,
residual_mean_ms, drift_ms, first_beat_on_attack, candidates [{mult, bpm, kicks_on_beat, beats_with_onset}], chosen.
Exit 0 = GRID accepted · 3 = BEAT-MAP (use the map; a loop or a cut on an arithmetic grid would drift) · 2 = unreadable.
"""
import argparse, json, sys, warnings
import numpy as np

warnings.filterwarnings('ignore')
TOL = 0.030   # a kick or an onset "on" a beat: within 30 ms


def attacks(y, sr, lo=None, hi=None):
    """attack times from a band-limited, rectified, 5 ms-smoothed envelope's rising edges — within ~2 ms of the true onset,
    where an STFT flux peak sits half a window early and a tracker's beat a frame or two late (34 ms apart, measured)"""
    from scipy.signal import butter, sosfiltfilt, find_peaks
    x = y.astype(np.float64)
    if lo and hi: x = sosfiltfilt(butter(4, [lo, hi], 'bandpass', fs=sr, output='sos'), x)
    elif hi: x = sosfiltfilt(butter(4, hi, 'lowpass', fs=sr, output='sos'), x)
    elif lo: x = sosfiltfilt(butter(4, lo, 'highpass', fs=sr, output='sos'), x)
    w = max(1, int(0.005 * sr)); env = np.convolve(np.abs(x), np.ones(w) / w, mode='same'); d = np.maximum(0, np.diff(env, prepend=env[:1]))
    if not d.any(): return np.zeros(0)
    pk, _ = find_peaks(d, height=d.mean() + 3 * d.std(), distance=max(1, int(0.12 * sr)))
    return pk / sr


def nearest(t, grid):
    if len(grid) == 0 or len(t) == 0: return np.full(len(t), np.inf)
    if len(grid) == 1: return np.abs(t - grid[0])
    j = np.clip(np.searchsorted(grid, t), 1, len(grid) - 1); return np.minimum(np.abs(t - grid[j - 1]), np.abs(t - grid[j]))


def phase_of(times, period):
    """the grid phase that best fits a set of attack times: their circular mean modulo the period"""
    a = 2 * np.pi * (np.asarray(times) % period) / period; return (np.angle(np.exp(1j * a).mean()) % (2 * np.pi)) * period / (2 * np.pi)


def fit(y, sr, residual_ms=15.0, drift_ms=10.0, hpss=False):
    import librosa
    yp = librosa.effects.hpss(y)[1] if hpss else y
    _, tracked = librosa.beat.beat_track(y=yp, sr=sr, hop_length=128, tightness=400, units='time')   # hop 128: a 23 ms hop alone left 11.5 ms of residual
    tracked = np.asarray(tracked, float); dur = len(y) / sr
    if len(tracked) < 8: return {'verdict': 'beat-map', 'why': f'only {len(tracked)} beats tracked', 'tracked': tracked.tolist(), 'beats': tracked.tolist()}
    i = np.arange(len(tracked)); (T, t0), *_ = np.linalg.lstsq(np.vstack([i, np.ones_like(i)]).T, tracked, rcond=None)
    res = tracked - (t0 + i * T)
    kicks = attacks(yp, sr, hi=150); onsets = attacks(yp, sr, lo=30)
    ref = kicks if len(kicks) >= 8 else onsets if len(onsets) >= 8 else tracked   # the phase comes from the ATTACKS, not the tracker
    def grid(mult, sub=0):
        TT = T / mult; ph = phase_of(ref, TT if mult >= 1 else TT) + sub * TT / 2
        return np.arange(ph % TT, dur, TT)
    cands = []
    for mult in (1, 2, 0.5):
        g = grid(mult)
        kob = float((nearest(kicks, g) <= TOL).mean()) if len(kicks) else 0.0
        bwo = float((nearest(g, np.sort(onsets)) <= TOL).mean()) if len(onsets) else 0.0
        cands.append({'mult': mult, 'bpm': round(60.0 / (T / mult), 3), 'kicks_on_beat': round(kob, 3), 'beats_with_onset': round(bwo, 3)})
    c1, c2, ch = cands; chosen = c1
    if len(kicks) >= 8 and c1['kicks_on_beat'] < 0.8 and c2['kicks_on_beat'] >= 0.9: chosen = c2          # kicks between the 1x beats
    elif c1['beats_with_onset'] < 0.6 and ch['kicks_on_beat'] >= 0.9: chosen = ch                         # 1x beats in empty air
    g = grid(chosen['mult']); d = 0.0
    if len(kicks) >= 8:
        j = np.clip(np.searchsorted(g, kicks), 1, len(g) - 1); nb = np.where(np.abs(kicks - g[j - 1]) < np.abs(kicks - g[j]), g[j - 1], g[j])
        off = kicks - nb; m = np.abs(off) <= (T / chosen['mult']) / 4
        if m.sum() >= 8: d = abs(np.polyfit(kicks[m], off[m], 1)[0]) * (kicks[m].max() - kicks[m].min()) * 1000
    rmax, rmean = float(np.abs(res).max() * 1000), float(np.abs(res).mean() * 1000)
    ok = rmax <= residual_ms and d <= drift_ms
    first = bool(len(g) and len(onsets) and nearest(np.array([g[0]]), np.sort(onsets))[0] <= TOL)
    return {'verdict': 'grid' if ok else 'beat-map', 'bpm': chosen['bpm'], 't0': round(float(g[0]), 6), 'T': round(float(T / chosen['mult']), 6),
            'beats': [round(float(x), 6) for x in (g if ok else tracked)], 'tracked': [round(float(x), 6) for x in tracked],
            'kicks': [round(float(x), 6) for x in kicks], 'residual_max_ms': round(rmax, 2), 'residual_mean_ms': round(rmean, 2),
            'drift_ms': round(d, 2), 'first_beat_on_attack': first, 'phase_from': 'kicks' if ref is kicks else 'onsets' if ref is onsets else 'tracker',
            'candidates': cands, 'chosen': chosen,
            'why': 'residual and drift inside the limits' if ok else f"residual {rmax:.1f} ms (limit {residual_ms:g}) · drift {d:.1f} ms (limit {drift_ms:g}): the tempo moves"}


def load(path, start=None, dur=None):
    import librosa
    return librosa.load(path, sr=22050, mono=True, offset=start or 0.0, duration=dur)


def synth(beat_times, dur, sr=22050, hats=True, kick_every=1):
    y = np.zeros(int(dur * sr), np.float32); rng = np.random.default_rng(0)
    kick = np.sin(2 * np.pi * 60 * np.arange(int(0.08 * sr)) / sr) * np.exp(-np.arange(int(0.08 * sr)) / (0.02 * sr))
    hat = rng.standard_normal(int(0.02 * sr)) * np.exp(-np.arange(int(0.02 * sr)) / (0.004 * sr)) * 0.3
    for k, b in enumerate(beat_times):
        s = int(b * sr)
        if k % kick_every == 0 and s + len(kick) < len(y): y[s:s + len(kick)] += kick
        if hats and k + 1 < len(beat_times):
            h = int((b + beat_times[k + 1]) / 2 * sr)
            if h + len(hat) < len(y): y[h:h + len(hat)] += hat
    return y, sr


def selftest():
    dur = 20.0; steady = np.arange(0.25, dur - 0.3, 0.5)                                    # 120 BPM, a kick on every beat
    tt, acc = [0.3], 0.3                                                                   # 96 → 132 BPM across the track
    while acc < dur - 0.4:
        bpm = 96 + 36 * acc / dur; acc += 60.0 / bpm; tt.append(acc)
    a = fit(*synth(steady, dur)); b = fit(*synth(np.array(tt[:-1]), dur))
    chk = [('steady 120: verdict GRID', a['verdict'] == 'grid'),
           ('steady 120: bpm within 0.5 of 120', abs(a['bpm'] - 120) < 0.5),
           ('steady 120: residual under 15 ms, drift under 10 ms', a['residual_max_ms'] <= 15 and a['drift_ms'] <= 10),
           ('steady 120: 1x kept, and the kicks sit on its beats (the phase came from them)', a['chosen']['mult'] == 1 and a['chosen']['kicks_on_beat'] >= 0.95),
           ('steady 120: the grid sits on the kicks (0.25 s + k·0.5), not the off-beat hats', abs(((a['t0'] - 0.25) + 0.25) % 0.5 - 0.25) <= 0.01),
           ('steady 120: the grid\'s first beat sits on an attack', a['first_beat_on_attack']),
           ('96→132 accelerando: verdict BEAT-MAP (an arithmetic grid would walk off)', b['verdict'] == 'beat-map'),
           ('the beat map is the tracked beats', b['beats'] == b['tracked'])]
    print(f"steady: {a['bpm']} bpm residual {a['residual_max_ms']} ms drift {a['drift_ms']} ms chosen x{a['chosen']['mult']}; "
          f"accelerando: {b['verdict']} ({b['why']})")
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--audio'); ap.add_argument('--out'); ap.add_argument('--residual-ms', type=float, default=15.0); ap.add_argument('--drift-ms', type=float, default=10.0)
    ap.add_argument('--hpss', action='store_true', help='track on the percussive part (a dense mix buries the drum attacks)')
    ap.add_argument('--start', type=float); ap.add_argument('--dur', type=float); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    if not a.audio: ap.error('--audio, or --selftest')
    try: y, sr = load(a.audio, a.start, a.dur)
    except Exception as ex: print(f'unreadable: {ex}'); sys.exit(2)
    r = fit(y, sr, a.residual_ms, a.drift_ms, a.hpss); r['audio'] = a.audio
    for c in r.get('candidates', []):
        print(f"  x{c['mult']:<3} {c['bpm']:8.3f} bpm  kicks on a beat {c['kicks_on_beat']:.2f}  beats with an onset {c['beats_with_onset']:.2f}")
    print(f"{r['verdict'].upper()}: {r.get('bpm', '?')} bpm, t0 {r.get('t0', '?')} s — {r['why']}"
          + (f"; residual ±{r['residual_max_ms']} ms (mean {r['residual_mean_ms']}), drift {r['drift_ms']} ms, first beat on an attack: {r['first_beat_on_attack']}" if 'residual_max_ms' in r else ''))
    if a.out: json.dump(r, open(a.out, 'w'), indent=1); print('wrote', a.out)
    print('BEAT-GRID-END'); sys.exit(0 if r['verdict'] == 'grid' else 3)


if __name__ == '__main__':
    main()
