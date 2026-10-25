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
               [--downbeats [--drums <drums stem>] [--downbeat-at <s>] [--line-starts <s,s,…>]]
  beat_grid.py --selftest
--downbeats: the bar phase (4/4 only) from the backbeat — snare attacks on alternate beats (pdoom-video's detector: a
1.5–5 kHz attack with a noisy tail), read from --drums (the drums stem of a 4-stem Demucs split; a vocal-only separator
gives none) or from the mix, which the output then names. A backbeat fixes the bar only to HALF a bar — shifted two beats
the pattern is the same; the donor settled the half by its chord changes, by hand — so --downbeat-at (a downbeat heard by
ear, or a lyric known to land on one) chooses, and nothing else does — the kicks print beside each candidate as evidence
only, since a kick on 3 alone would read as beat 1; with no pin the verdict is AMBIGUOUS and both candidates print. Bars are counted by beat index, so a dropped or added beat (an interval far
from its neighbours', or the backbeat changing parity) splits the map: verdict PHASE-BREAK, each stretch solved on its own
(a pin settles only its own stretch), and `times` holds only the stretches that were labelled. --line-starts applies the section rule to each line's first-word onset:
a section starts on the downbeat of the bar its first line starts in; a pickup under 2 beats stays in the previous
section, a pickup of 2 beats or more starts the section at the pickup bar. Measured on synthetic drums and one generated
song (2026-10-25): its Demucs drums stem showed the backbeat over 2.6–234 s (AMBIGUOUS until pinned: four-on-the-floor
kicks); the mix read alone found it in one stretch at most and broke the map where the stem did not — read a drums stem,
and confirm the first downbeat by ear before a cut depends on it.
beat_data.json: verdict (grid | beat-map), bpm, t0, T, beats (the grid, or the map), tracked, kicks, residual_max_ms,
residual_mean_ms, drift_ms, first_beat_on_attack, candidates [{mult, bpm, kicks_on_beat, beats_with_onset}], chosen;
with --downbeats, downbeats {verdict (pinned | ambiguous | none | conflict | pin-off-grid | phase-break), source,
snare_on, candidates, phase, first, times, breaks, segments, why} and, with --line-starts, sections [{line_start, pickup_beats, section_start, why}].
Exit 0 = GRID accepted · 3 = BEAT-MAP (use the map; a loop or a cut on an arithmetic grid would drift) · 2 = unreadable.
The downbeat verdict never changes the exit code: it prints as its own DOWNBEATS line.
"""
import argparse, json, os, sys, warnings
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



def snares(x, sr):
    """snare attacks: 1.5–5 kHz attacks whose noisy 0.5–5 kHz tail 40–120 ms later sits within 8 dB of the loudest tail in
    ±2.5 s and within 25 dB of the track's loud tails — a hat or a kick's beater click carries almost no tail there.
    Pattern: pdoom-video `analysis/analyze.py` drum_onsets (read there on a Demucs drums stem)."""
    from scipy.signal import butter, sosfiltfilt
    st = attacks(x, sr, lo=1500, hi=5000)
    if len(st) == 0: return st
    xb = sosfiltfilt(butter(4, [500, 5000], 'bandpass', fs=sr, output='sos'), x.astype(np.float64))
    w = max(1, int(0.010 * sr)); e = np.sqrt(np.convolve(xb ** 2, np.ones(w) / w, mode='same'))
    def tail(t):
        a, b = int((t + 0.04) * sr), int((t + 0.12) * sr); seg = e[a:b]
        return 20 * np.log10((seg.mean() if len(seg) else 0) + 1e-9)
    tl = np.array([tail(t) for t in st]); rel = np.array([tl[i] - tl[np.abs(st - st[i]) < 2.5].max() for i in range(len(st))])
    return st[(rel > -8) & (tl > np.percentile(tl, 95) - 25)]


def on_beats(events, beats, frac=0.25):
    """per beat: does a hit BELONG to it — the nearest hit within frac of the local beat period. Which beat a hit belongs to,
    not whether it is exactly on it: a tracker's beat runs a frame or two late, and on a BEAT-MAP the tracked times are the
    grid (a real drums stem put its snares 0–56 ms ahead of the tracked beats, outside a fixed 30 ms)."""
    b = np.asarray(beats, float); out = np.zeros(len(b), bool)
    if len(events) == 0 or len(b) < 2: return out
    per = np.gradient(b); out[:] = nearest(b, np.sort(np.asarray(events, float))) <= frac * per; return out


def _solve(b, sn, kk, pin, i0=0):
    """one stretch with no phase break: the backbeat's parity, the two candidates, then the pin or the kicks; i0 = the
    stretch's first beat index in the whole map (phases are reported in whole-map indices)"""
    f = [float(sn[0::2].mean()), float(sn[1::2].mean())]; p = int(np.argmax(f)); out = {'from': round(float(b[0]), 3), 'to': round(float(b[-1]), 3), 'snare_on': {'even': round(f[(0 + i0) % 2], 3), 'odd': round(f[(1 + i0) % 2], 3)}}
    backbeat = sn.sum() >= 8 and f[p] >= 0.5 and f[p] - f[1 - p] >= 0.35
    ra = (p + 1) % 2; cands = []
    for r in (ra, ra + 2):
        idx = np.arange(r, len(b), 4)
        if len(idx): cands.append({'phase': (r + i0) % 4, 'first': round(float(b[r]), 6), 'kicks_on_downbeat': round(float(kk[idx].mean()), 3), '_r': r})
    out['candidates'] = [{k: v for k, v in c.items() if k != '_r'} for c in cands] if backbeat else []
    if pin is not None and b[0] - 0.06 <= pin <= b[-1] + 0.06:
        j = int(np.argmin(np.abs(b - pin)))
        if abs(b[j] - pin) > 0.06: return {**out, 'verdict': 'pin-off-grid', 'why': f'the pin {pin:.3f} s sits {abs(b[j] - pin) * 1000:.0f} ms from the nearest beat — pin a beat'}
        r = j % 4
        if backbeat and r not in (ra, ra + 2): return {**out, 'verdict': 'conflict', 'why': f'the pin {pin:.3f} s falls on a snare beat'}
        chosen, verdict = r, 'pinned'; why = 'the pin chose between the two backbeat candidates' if backbeat else 'pinned, UNCONFIRMED — no backbeat found to check the pin against'
    elif not backbeat:
        return {**out, 'verdict': 'none', 'why': f"no backbeat: snare on even beats {out['snare_on']['even']:.2f}, odd {out['snare_on']['odd']:.2f} (needs ≥ 8 snare beats, ≥ 0.50 on one parity, 0.35 apart)"}
    else:   # the kicks are evidence beside the candidates, never the choice: a kick on 3 alone would read as beat 1, half a bar wrong
        k = ' vs '.join(f"{c['kicks_on_downbeat']:.2f}" for c in cands)
        return {**out, 'verdict': 'ambiguous', 'why': f'the backbeat fixes the bar to half a bar (kicks on the two candidates {k}, evidence only) — pin a downbeat with --downbeat-at'}
    t = b[chosen::4]
    return {**out, 'verdict': verdict, 'phase': int((chosen + i0) % 4), 'first': round(float(t[0]), 6), 'times': [round(float(x), 6) for x in t], 'why': why}


def downbeats(beats, kicks, snare_t, pin=None, meter=4, source='mix'):
    """bar phase from the backbeat. A snare on 2 and 4 marks alternate beats, which fixes the bar only to HALF a bar:
    shifted two beats, the pattern is the same. The donor settled the half by its 2-bar chord changes, by hand — so here
    a PIN settles it (a downbeat heard by ear, or a lyric known to land on one) and nothing else does: the kicks print beside
    each candidate as evidence only (a kick on 3 alone would read as beat 1). No pin → AMBIGUOUS: both candidates print.
    The pin is trusted — a pin on a snare beat is refused, but one on beat 3 labels every bar half a bar off.
    Bars are counted by beat INDEX, so a dropped or added beat relabels every bar after it: the map is split at each such
    PHASE BREAK — an interval far from its neighbours' (a skipped or doubled beat), or the backbeat changing parity (located
    to the beat) — and every stretch is solved on its own; a pin settles only its own stretch. A break inside a drumless
    stretch shows neither sign and stays invisible here."""
    b = np.asarray(beats, float); out = {'meter': meter, 'source': source, 'n_snares': int(len(snare_t))}
    if meter != 4: return {**out, 'verdict': 'none', 'why': 'only 4/4 is measured'}
    if len(b) < 8: return {**out, 'verdict': 'none', 'why': f'only {len(b)} beats'}
    sn, kk = on_beats(snare_t, b), on_beats(kicks, b)
    dt = np.diff(b); med = np.array([np.median(dt[max(0, i - 4):i + 5]) for i in range(len(dt))])
    cuts = set(int(i) + 1 for i in np.nonzero((dt > 1.5 * med) | (dt < 0.6 * med))[0])
    par = []
    starts = list(range(0, len(b) - 15, 8)); starts += [len(b) - 16] if starts and starts[-1] != len(b) - 16 else []   # the last window reaches the end
    for w0 in starts:
        g = sn[w0:w0 + 16]; ix = np.arange(w0, w0 + 16); e_, o_ = g[ix % 2 == 0].mean(), g[ix % 2 == 1].mean()
        if g.sum() >= 4 and abs(e_ - o_) >= 0.5: par.append((w0, 0 if e_ > o_ else 1))
    for (w1, q1), (w2, q2) in zip(par[:-1], par[1:]):
        if q1 == q2: continue
        lo, hi = w1, min(len(b), w2 + 16); k = np.arange(lo, hi)   # the flip, located to the beat: the split that best fits q1 before, q2 after
        sc = np.array([sn[k][((k < j) & (k % 2 == q1)) | ((k >= j) & (k % 2 == q2))].sum() for j in range(lo + 1, hi)])
        js = np.nonzero(sc == sc.max())[0] + lo + 1; cuts.add(int(js[len(js) // 2]))   # beats with no snare tie the split: take the middle
    bounds = [0] + sorted(c for c in cuts if 0 < c < len(b)) + [len(b)]
    if len(bounds) == 2:
        r = _solve(b, sn, kk, pin); r.pop('from', None); r.pop('to', None); return {**out, **r}
    segs = []
    for s0, s1 in zip(bounds[:-1], bounds[1:]):
        if s1 - s0 < 8: segs.append({'from': round(float(b[s0]), 3), 'to': round(float(b[s1 - 1]), 3), 'verdict': 'none', 'why': f'only {s1 - s0} beats between breaks'}); continue
        segs.append(_solve(b[s0:s1], sn[s0:s1], kk[s0:s1], pin, s0))
    times = [t for sg in segs for t in sg.get('times', [])]; ok = [sg for sg in segs if sg.get('times')]
    breaks = [round(float(b[c]), 3) for c in bounds[1:-1]]
    return {**out, 'verdict': 'phase-break', 'breaks': breaks, 'segments': segs, 'times': times,
            'why': f"bars counted by beat index break at {', '.join(f'{t:.2f}' for t in breaks)} s; {len(ok)} of {len(segs)} stretches labelled"
                   + ('' if len(ok) == len(segs) else ' — pin a downbeat inside each unlabelled stretch, or a drums stem')}


def sections(starts, stretches, beats):
    """the section rule: a section starts on the downbeat of the bar its first line starts in; a pickup shorter than 2
    beats stays in the previous section (the section starts at the NEXT downbeat); a pickup of 2 beats or more starts the
    section at the pickup bar (pdoom's choruses open on a ~3-beat pickup, so each chorus starts at its pickup bar).
    stretches = [(from, to, downbeat times or None)]: a line in an unlabelled stretch, or one whose next downbeat lies past
    its stretch, stays unresolved. A pickup is counted in BEATS on the map itself, never seconds over a median period."""
    b = np.asarray(beats, float)
    def idx(t):   # fractional beat index of a time on the map (a tempo that moves keeps whole beats whole)
        j = int(np.clip(np.searchsorted(b, t, 'right') - 1, 0, len(b) - 2)); return j + (t - b[j]) / (b[j + 1] - b[j])
    rows = []
    for s in starts:
        sg = next((x for x in stretches if x[0] - 0.06 <= s <= x[1] + 0.06), None)
        if sg is None or not sg[2]:
            rows.append({'line_start': s, 'section_start': None, 'why': 'inside a stretch with no labelled bars' if sg else 'outside every measured stretch'}); continue
        d = np.asarray(sg[2], float); k = int(np.searchsorted(d, s + 0.02, 'right')) - 1
        if k < 0: rows.append({'line_start': s, 'section_start': None, 'why': "before the stretch's first downbeat"}); continue
        if s - d[k] <= 0.02: rows.append({'line_start': s, 'pickup_beats': 0.0, 'section_start': round(float(d[k]), 6), 'why': 'on the downbeat'}); continue
        if k + 1 >= len(d): rows.append({'line_start': s, 'section_start': None, 'why': "the next downbeat lies past this stretch's last bar"}); continue
        pk = idx(d[k + 1]) - idx(s)
        rows.append({'line_start': s, 'pickup_beats': round(float(pk), 2), 'section_start': round(float(d[k + 1] if pk < 2 - 1e-6 else d[k]), 6),
                     'why': 'a pickup under 2 beats stays in the previous section' if pk < 2 - 1e-6 else 'a pickup of 2 beats or more starts the section at the pickup bar'})
    return rows


def synth_drums(beat_times, dur, sr=22050, kick_idx=None, snare_par=None, hats=True):
    """kicks on beats whose index % 4 is in kick_idx (None = every beat), a snare on beats of index parity snare_par"""
    y = np.zeros(int(dur * sr), np.float32); rng = np.random.default_rng(1)
    n = np.arange(int(0.08 * sr)); kick = np.sin(2 * np.pi * 60 * n / sr) * np.exp(-n / (0.02 * sr))
    m = np.arange(int(0.15 * sr)); snare = 0.4 * np.sin(2 * np.pi * 190 * m / sr) * np.exp(-m / (0.03 * sr)) + 0.5 * rng.standard_normal(len(m)) * np.exp(-m / (0.045 * sr))
    h = np.arange(int(0.02 * sr)); hat = rng.standard_normal(len(h)) * np.exp(-h / (0.004 * sr)) * 0.3
    for k, t in enumerate(beat_times):
        s = int(t * sr)
        if (kick_idx is None or k % 4 in kick_idx) and s + len(kick) < len(y): y[s:s + len(kick)] += kick
        if snare_par is not None and k % 2 == snare_par and s + len(snare) < len(y): y[s:s + len(snare)] += snare
        if hats and k + 1 < len(beat_times):
            q = int((t + beat_times[k + 1]) / 2 * sr)
            if q + len(hat) < len(y): y[q:q + len(hat)] += hat
    return y, sr


def selftest_downbeats():
    """six cases on a steady 120 BPM grid from 0.25 s (beat k at 0.25 + 0.5k)"""
    dur = 20.0; bt = np.arange(0.25, dur - 0.3, 0.5); chk = []
    def run(kick_idx, snare_par, pin=None):
        y, sr = synth_drums(bt, dur, kick_idx=kick_idx, snare_par=snare_par); r = fit(y, sr)
        return downbeats(r['beats'], np.asarray(r['kicks']), snares(y, sr), pin=pin), r
    a, ra = run(None, 1)                    # four on the floor, snare on the odd beats (2 and 4 when beat 0 is a downbeat)
    chk.append(('four-on-the-floor + backbeat: AMBIGUOUS, candidates at phases 0 and 2', a['verdict'] == 'ambiguous' and sorted(c['phase'] for c in a['candidates']) == [0, 2]))
    b, _ = run(None, 1, pin=1.25)            # pin beat 2 (1.25 s)
    chk.append(('pinned at 1.25 s: verdict PINNED, phase 2, first downbeat 1.25', b['verdict'] == 'pinned' and b.get('phase') == 2 and abs(b['first'] - 1.25) < 0.02))
    c, _ = run({2}, 1)                       # a kick on 3 only: it must NOT be read as beat 1
    chk.append(('kick on 3 only: still AMBIGUOUS — the kicks are evidence, never the choice', c['verdict'] == 'ambiguous' and not c.get('times') and sorted(x['kicks_on_downbeat'] for x in c['candidates']) == [0.0, 1.0]))
    d, _ = run(None, 1, pin=0.75)            # pin on a snare beat
    chk.append(('a pin on a snare beat: CONFLICT', d['verdict'] == 'conflict'))
    e, _ = run(None, None)                   # no snare at all
    chk.append(('no snare: verdict NONE (no backbeat), nothing guessed', e['verdict'] == 'none' and not e.get('times')))
    rows = sections([1.85, 0.70, 2.26], [(bt[0], bt[-1], [0.25 + 2.0 * k for k in range(9)])], bt)
    chk.append(('pickup 0.8 beats stays in the previous section → 2.25', rows[0]['section_start'] == 2.25))
    chk.append(('pickup 3.1 beats starts the section at its pickup bar → 0.25', rows[1]['section_start'] == 0.25))
    chk.append(('a line on the downbeat → that downbeat, 2.25', rows[2]['section_start'] == 2.25))
    drop = np.delete(bt, 20); sn_t = bt[1::2]                                  # the tracker lost beat 20: indices after it shift by one
    f_ = downbeats(drop, bt, sn_t, pin=1.25); s0, s1 = (f_.get('segments') or [{}, {}])[:2]
    chk.append(('one beat dropped from the map: PHASE-BREAK at it, split into two stretches', f_['verdict'] == 'phase-break' and len(f_.get('segments', [])) == 2 and any(abs(t - bt[21]) < 0.01 for t in f_['breaks'])))
    chk.append(('  the pinned stretch labelled (from 1.25), the stretch after the break AMBIGUOUS, not mislabelled', s0.get('verdict') == 'pinned' and abs(s0.get('first', 0) - 1.25) < 0.02 and s1.get('verdict') == 'ambiguous' and all(t < bt[21] for t in f_['times'])))
    sl = np.concatenate([bt[:21], bt[21:] + 0.25])
    g_ = downbeats(sl, bt, np.concatenate([bt[1:21:2], bt[22::2] + 0.25]), pin=1.25)   # the tracker slips half a beat: the backbeat changes parity, every interval stays regular
    chk.append(('a parity slip with regular intervals: the break located within a beat of it', g_['verdict'] == 'phase-break' and any(abs(t - sl[21]) <= 0.51 for t in g_['breaks'])))
    vb = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.4, 2.9, 3.3, 3.8, 4.3, 4.8, 5.3])                 # a tempo that moves: 2.4 is two beats before 3.3
    vr = sections([2.4], [(0.0, 5.3, [1.5, 3.3])], vb)
    chk.append(('pickup on a moving tempo counted in beats: 2.4 → 3.3 is 2 beats, so the section starts at its pickup bar 1.5', vr[0]['section_start'] == 1.5 and vr[0]['pickup_beats'] == 2.0))
    ur = sections([12.0, 2.0], [(0.25, 10.0, [1.25, 3.25, 5.25, 7.25, 9.25]), (10.25, 19.25, None)], bt)
    chk.append(('a line in an unlabelled stretch stays unresolved — never carried from the stretch before', ur[0]['section_start'] is None and ur[1]['section_start'] == 1.25))
    import subprocess, tempfile                                                   # the CLI on an empty map: no beats, no crash, the JSON written, exit 3
    from scipy.io import wavfile
    td = tempfile.mkdtemp(prefix='bg-'); wavfile.write(os.path.join(td, 'silent.wav'), 22050, np.zeros(22050 * 5, np.int16))
    cp = subprocess.run([sys.executable, os.path.abspath(__file__), '--audio', os.path.join(td, 'silent.wav'), '--downbeats', '--line-starts', '1', '--out', os.path.join(td, 'o.json')], capture_output=True, text=True)
    chk.append(('the CLI on a silent clip with --downbeats --line-starts: exit 3, the JSON written, no traceback', cp.returncode == 3 and os.path.exists(os.path.join(td, 'o.json')) and 'Traceback' not in cp.stderr))
    print(f"downbeats: ambiguous {a['why']}; kick on 3: {c['why']}; snare_on {a.get('snare_on')}; dropped beat: {f_['why']}; slip: {g_['why']}")
    return chk


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
           ('the beat map is the tracked beats', b['beats'] == b['tracked'])] + selftest_downbeats()
    print(f"steady: {a['bpm']} bpm residual {a['residual_max_ms']} ms drift {a['drift_ms']} ms chosen x{a['chosen']['mult']}; "
          f"accelerando: {b['verdict']} ({b['why']})")
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--audio'); ap.add_argument('--out'); ap.add_argument('--residual-ms', type=float, default=15.0); ap.add_argument('--drift-ms', type=float, default=10.0)
    ap.add_argument('--hpss', action='store_true', help='track on the percussive part (a dense mix buries the drum attacks)')
    ap.add_argument('--start', type=float); ap.add_argument('--dur', type=float); ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--downbeats', action='store_true', help='the bar phase from the backbeat (4/4)'); ap.add_argument('--drums', help='the drums stem of a 4-stem split (else the mix)')
    ap.add_argument('--downbeat-at', type=float, help='a downbeat by ear or a lyric known to land on one: settles the half-bar ambiguity')
    ap.add_argument('--meter', type=int, default=4, help='beats per bar — only 4 is measured'); ap.add_argument('--line-starts', help="lines' first-word onsets, comma-separated: the section rule per line")
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
    if a.downbeats or a.downbeat_at is not None or a.line_starts:
        if a.drums:
            try: yd, _ = load(a.drums, a.start, a.dur)
            except Exception as ex: print(f'drums stem unreadable: {ex}'); sys.exit(2)
            kk, sn, src = attacks(yd, sr, hi=150), snares(yd, sr), 'drums stem'
        else:
            import librosa
            yp = librosa.effects.hpss(y)[1] if a.hpss else y
            kk, sn, src = np.asarray(r.get('kicks', []), float), snares(yp, sr), 'mix (percussive part)' if a.hpss else 'mix — no drums stem; a dense mix hides snares'
        db = downbeats(r['beats'], kk, sn, pin=a.downbeat_at, meter=a.meter, source=src); r['downbeats'] = db
        print(f"DOWNBEATS {db['verdict'].upper()} ({src}): " + (f"first {db['first']} s, every 4 beats — " if 'first' in db else '') + db['why']
              + (f"; snare on even beats {db['snare_on']['even']:.2f}, odd {db['snare_on']['odd']:.2f}" if 'snare_on' in db else ''))
        for c in db.get('candidates', []) if db['verdict'] == 'ambiguous' else []: print(f"  candidate: first downbeat {c['first']} s (phase {c['phase']}), kicks on its downbeats {c['kicks_on_downbeat']:.2f}")
        for sg in db.get('segments', []): print(f"  {sg['from']:8.2f}–{sg['to']:8.2f} s  {sg['verdict'].upper():12} " + (f"first {sg['first']} s  " if sg.get('times') else '') + sg['why'])
        if a.line_starts:
            if db.get('times'):   # stretches only from a map that has labelled bars (an empty or untracked map has none)
                st_ = [(sg['from'], sg['to'], sg.get('times')) for sg in db['segments']] if 'segments' in db else [(r['beats'][0], r['beats'][-1], db['times'])]
                r['sections'] = sections([float(v) for v in a.line_starts.split(',') if v.strip()], st_, r['beats'])
                for row in r['sections']: print(f"  line at {row['line_start']:.3f} s → section starts {row['section_start']} s ({row['why']}" + (f", pickup {row['pickup_beats']} beats)" if 'pickup_beats' in row else ')'))
            else: print(f"  sections: N/A — the downbeats are {db['verdict']}: a section ends on the first BEAT at or after the last word's end, and the plan says so")
    if a.out: json.dump(r, open(a.out, 'w'), indent=1); print('wrote', a.out)
    print('BEAT-GRID-END'); sys.exit(0 if r['verdict'] == 'grid' else 3)


if __name__ == '__main__':
    main()
