#!/usr/bin/env python3
"""music_take_read.py — a generated music take MEASURED before it is trusted: its key, its tuning, its tempo drift and its
tail. Generators ignore the requested key and tempo, and the commonest fault sits in the decay, so a sweetener is never
tuned to a key the take does not hold and a crunchy ending is caught before the cue is cut. Pattern: nicceasy/3d-product
references/sound-design.md §§ 5, 8, 10 (MIT). Upstream's numbers: r > 0.7, a spread ≤ ~3–5 c, a drift ≤ ~2–3 %, the tail's
direction. Ours, uncalibrated: the near-tie 0.05, the drift gate r 0.3, the body correlation 0.8, the level wobble 3 dB, the
pitch wobble 8 c. All are defaults until measured on our takes.

  key     a chroma (55 Hz–5 kHz, corrected by the measured tuning) against the Krumhansl–Kessler major and minor profiles,
          all 24 keys; the correlation is the confidence (> 0.7 solid) and the runner-up prints beside it
  tuning  the strongest spectral peaks' offset from A440 equal temperament, in cents: the circular mean, and the spread of
          the 2 s segments' offsets (≤ ~3–5 c reads as one tuning)
  tempo   an onset envelope's autocorrelation tempo in the first and the last third, its octave chosen by a comb and a
          120 BPM prior (octave_pick), the other octave named when the onsets fit it as well; the drift is their
          difference (≤ ~2–3 %), the same in either octave
  tail    the last --tail s of AUDIBLE signal (trailing blocks under -60 dBFS trimmed) against the body before it: energy
          above 6 kHz re the full band, the 100–500 Hz correlation between the channels, and the 500 Hz–4 kHz spectral
          flatness, its level wobble around the decay's trend and its pitch wobble frame to frame. A decay that gains
          hiss, loses its stereo image, turns to noise or wobbles is the fault (upstream measured −50 → −26 dB and
          0.97 → 0.5). Every spectrum adds the channels' powers, so opposite polarity never cancels a read
A read is gated by level: a take under -50 dBFS reads "too quiet to read", never a key. A surprising number is checked
with a second method before it is acted on (the tempo: beat_grid.py). The fix ladder, cheapest first, is in
references/SFX-AND-MUSIC.md § Music.

  music_take_read.py <take> [--tail 3] [--start <s> --dur <s>] [--json <out.json>]
  music_take_read.py --selftest
Self-test first, on synthetic takes with known answers, or nothing is printed. Exit 0 = read (WARN lines are information)
· 2 = self-test failed, or the file is unreadable.
"""
import argparse, json, subprocess, sys
import numpy as np

SR = 44100
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
QUIET_DB, SILENT_DB = -50.0, -60.0


def load(path, start=None, dur=None):
    cmd = ['ffmpeg', '-v', 'error'] + (['-ss', f'{start:.3f}'] if start is not None else []) + (['-t', f'{dur:.3f}'] if dur else []) \
        + ['-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).reshape(-1, 2).astype(np.float64)


def dbfs(x): return 10 * np.log10(np.mean(np.asarray(x) ** 2) + 1e-18)


def frames(mono, n, hop):
    m = 1 + (len(mono) - n) // hop if len(mono) >= n else 0
    return np.lib.stride_tricks.as_strided(mono, (m, n), (mono.strides[0] * hop, mono.strides[0]), writeable=False)


def mags(x, n, hop):
    """per frame, the two channels' magnitudes combined by POWER — a take in opposite polarity is never cancelled, as a
    downmix would cancel it"""
    w = np.hanning(n); FL = frames(np.ascontiguousarray(x[:, 0]), n, hop); FR = frames(np.ascontiguousarray(x[:, 1]), n, hop)
    for k in range(len(FL)):
        yield k, np.sqrt(np.abs(np.fft.rfft(FL[k] * w)) ** 2 + np.abs(np.fft.rfft(FR[k] * w)) ** 2)


def peaks_cents(x, n=16384, hop=4096):
    """per frame, up to 8 spectral peaks in 80–2000 Hz within 30 dB of the frame's strongest; returns (dev cents, weight, t)"""
    f = np.fft.rfftfreq(n, 1 / SR); band = (f >= 80) & (f <= 2000); idx = np.nonzero(band)[0]
    devs, wts, ts = [], [], []
    for k, mag in mags(x, n, hop):
        lm = 20 * np.log10(mag + 1e-12); b = lm[idx]
        loc = idx[1:-1][(b[1:-1] > b[:-2]) & (b[1:-1] >= b[2:]) & (b[1:-1] > lm[idx].max() - 30)]
        for i in loc[np.argsort(-lm[loc])][:8]:
            a, c, d = lm[i - 1], lm[i], lm[i + 1]; den = a - 2 * c + d
            p = 0.5 * (a - d) / den if den else 0.0                                   # parabolic interpolation, in bins
            fr = (i + p) * SR / n; cents = 1200 * np.log2(fr / 440.0)
            devs.append(((cents + 50) % 100) - 50); wts.append(mag[i]); ts.append((k * hop + n / 2) / SR)
    return np.array(devs), np.array(wts), np.array(ts)


def circ_mean_c(d, w=None):
    ang = 2 * np.pi * np.asarray(d) / 100; w = np.ones_like(ang) if w is None else np.asarray(w)
    return float(np.angle(np.sum(w * np.exp(1j * ang))) * 100 / (2 * np.pi))


def tuning(x, seg_s=2.0):
    d, w, t = peaks_cents(x)
    if not len(d): return None, None
    off = circ_mean_c(d, w); segs = []
    for s0 in np.arange(0, t.max() + 1e-9, seg_s):
        m = (t >= s0) & (t < s0 + seg_s)
        if m.sum() >= 4: segs.append(circ_mean_c(d[m], w[m]))
    spread = float(np.std([((s - off + 50) % 100) - 50 for s in segs])) if len(segs) >= 2 else 0.0
    return round(off, 1), round(spread, 1)


def chroma(x, off_c, n=16384, hop=4096):
    f = np.fft.rfftfreq(n, 1 / SR); band = (f >= 55) & (f <= 5000)
    pc = (np.round(12 * np.log2(f[band] / 440.0) + 69 - off_c / 100).astype(int)) % 12
    ch = np.zeros(12)
    for _, mag in mags(x, n, hop): ch += np.bincount(pc, weights=mag[band], minlength=12)
    return ch


def key_of(ch):
    if not np.isfinite(ch).all() or ch.std() == 0: return (float('nan'), 'unmeasurable'), (float('nan'), '—')
    rows = []
    for k in range(12):
        for name, prof in (('major', MAJOR), ('minor', MINOR)):
            rows.append((float(np.corrcoef(ch, np.roll(prof, k))[0, 1]), f'{NAMES[k]} {name}'))
    rows.sort(reverse=True); return rows[0], rows[1]


def onset_env(x, n=1024, hop=256):
    w = np.hanning(n); FL = frames(np.ascontiguousarray(x[:, 0]), n, hop); FR = frames(np.ascontiguousarray(x[:, 1]), n, hop)
    if len(FL) < 3: return np.zeros(0), hop / SR
    S = np.log1p(np.sqrt(np.abs(np.fft.rfft(FL * w, axis=1)) ** 2 + np.abs(np.fft.rfft(FR * w, axis=1)) ** 2) * 100)
    flux = np.maximum(np.diff(S, axis=0), 0).sum(axis=1)
    if len(flux) < 32: return np.zeros(0), hop / SR                           # under ~0.2 s: no envelope to read (the 16-tap mean would outgrow it)
    return flux - np.convolve(flux, np.ones(16) / 16, 'same'), hop / SR


def acf_tempo(env, dt, lo_bpm=60, hi_bpm=200):
    e = env - env.mean(); ac = np.correlate(e, e, 'full')[len(e) - 1:]
    l0, l1 = int(60 / hi_bpm / dt), int(60 / lo_bpm / dt) + 1
    if l1 >= len(ac) - 1 or l0 < 2: return None
    i = l0 + int(np.argmax(ac[l0:l1])); a, b, c = ac[i - 1], ac[i], ac[i + 1]; den = a - 2 * b + c
    lag = i + (0.5 * (a - c) / den if den else 0.0)
    return 60.0 / (lag * dt), float(b / ac[0]) if ac[0] > 0 else 0.0   # the tempo, and how periodic the onsets are (0–1)


def octave_pick(env, dt, bpm, lo_bpm=40, hi_bpm=240):
    """(tempo, the other octave or None). The autocorrelation's strongest period names a pulse, not its octave: a clap on
    2 and 4 makes the two-beat lag the strongest, so four on the floor at 124 read 62. Of the half, the same and the double
    tempo, keep the one whose comb — the mean autocorrelation at 1, 2, 3 and 4 periods — times a log-normal tempo prior
    (120 BPM, one octave: librosa's beat-tracking default) is largest. The onsets alone cannot settle the octave: the same
    prior lifts a 70 BPM kick with quiet offbeat hats to 140. So when the comb without the prior picks another octave,
    that octave is returned beside the tempo and the read says the octave is a call. Where the prior is even (85
    against 170) the pattern decides, unflagged: a clap on 2 and 4 at 170 reads 85"""
    e = env - env.mean(); ac = np.correlate(e, e, 'full')[len(e) - 1:]
    if ac[0] <= 0: return bpm, None
    ac = ac / ac[0]; raw, pri = None, None
    def peak(lag):
        i0, i1 = max(1, int(lag * 0.96)), min(len(ac) - 1, int(np.ceil(lag * 1.04)) + 1)
        return max(0.0, float(ac[i0:i1].max())) if i0 < i1 else 0.0
    for c in (bpm / 2, bpm, bpm * 2):
        if not lo_bpm <= c <= hi_bpm: continue
        comb = float(np.mean([peak(k * 60.0 / c / dt) for k in range(1, 5)])); s = comb * np.exp(-0.5 * np.log2(c / 120.0) ** 2)
        if raw is None or comb > raw[0]: raw = (comb, c)
        if pri is None or s > pri[0]: pri = (s, c)
    if pri is None: return bpm, None
    return pri[1], (raw[1] if raw[1] != pri[1] else None)


CONF_MIN = 0.3   # synthetic beats read >= 0.5; two real piano takes 0.05-0.22, where the tracker's beats held steady


def tempo_drift(x):
    """(first, last, drift %, confidence, the other octave or None): each third's tempo within ±15 % of the whole take's,
    so both read one octave; no drift verdict when either third's onset periodicity is under CONF_MIN (a sparse or rubato
    take). The drift is a ratio, so it holds whichever octave the label names"""
    env, dt = onset_env(x); m = len(env) // 3
    if m < int(4 / dt): return None, None, None, None, None
    g = acf_tempo(env, dt, 40, 240)                                            # wide, so a two-beat lag under 60 is seen as one
    if g is None: return None, None, None, None, None
    g0, alt = octave_pick(env, dt, g[0])
    a = acf_tempo(env[:m], dt, g0 / 1.15, g0 * 1.15); b = acf_tempo(env[-m:], dt, g0 / 1.15, g0 * 1.15)
    alt = round(alt, 1) if alt else None
    if a is None or b is None: return round(g0, 1), None, None, None, alt
    conf = round(min(a[1], b[1]), 3)
    return round(a[0], 1), round(b[0], 1), (round(100 * (b[0] - a[0]) / a[0], 2) if conf >= CONF_MIN else None), conf, alt


def band_power(x, lo, hi, n=4096):
    """per-channel power in [lo, hi) Hz, frames averaged"""
    w = np.hanning(n); f = np.fft.rfftfreq(n, 1 / SR); m = (f >= lo) & (f < hi); out = []
    for c in range(x.shape[1]):
        F = frames(np.ascontiguousarray(x[:, c]), n, n // 2)
        out.append(float((np.abs(np.fft.rfft(F * w, axis=1)) ** 2)[:, m].sum(axis=1).mean()) if len(F) else 0.0)
    return np.array(out)


def lowmid_corr(x, lo=100, hi=500):
    X = np.fft.rfft(x, axis=0); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f >= hi)] = 0
    y = np.fft.irfft(X, n=len(x), axis=0); den = np.sqrt((y[:, 0] ** 2).sum() * (y[:, 1] ** 2).sum())
    return float((y[:, 0] * y[:, 1]).sum() / den) if den > 0 else None


def flatness(x, lo=500, hi=4000, n=4096):
    f = np.fft.rfftfreq(n, 1 / SR); m = (f >= lo) & (f < hi)
    P = np.array([mag[m] ** 2 for _, mag in mags(x, n, n // 2)]) + 1e-20     # channel powers added: no polarity cancels
    if not len(P): return None
    return float(np.mean(np.exp(np.mean(np.log(P), axis=1)) / np.mean(P, axis=1)))


def level_wobble(s, blk=0.02):
    """the std (dB) of 20 ms block levels around their straight-line trend: a decay is a trend, a tremolo is not"""
    b = int(blk * SR); m = len(s) // b
    if m < 10: return None
    lv = 10 * np.log10((s[:m * b] ** 2).reshape(m, b, s.shape[1]).mean(axis=1).sum(axis=1) + 1e-18); tt = np.arange(m)
    return float(np.std(lv - np.polyval(np.polyfit(tt, lv, 1), tt)))


def pitch_wobble(s):
    """the std (cents) of the per-frame tuning offset on 93 ms frames — a vibrato or a drifting pitch in the decay"""
    d, w, t = peaks_cents(s, n=4096, hop=1024)
    if len(d) < 12: return None
    per = [circ_mean_c(d[t == u], w[t == u]) for u in np.unique(t)]; c = circ_mean_c(per)
    return float(np.std([((v - c + 50) % 100) - 50 for v in per]))


def tail_read(x, tail_s=3.0):
    blk = int(0.05 * SR); nb = len(x) // blk
    lv = np.array([dbfs(x[i * blk:(i + 1) * blk]) for i in range(nb)])
    aud = np.nonzero(lv > SILENT_DB)[0]
    if not len(aud): return None
    end = (aud[-1] + 1) * blk; t0 = max(0, end - int(tail_s * SR))
    body, tail = x[:t0], x[t0:end]
    if len(body) < SR * 2 or len(tail) < SR * 0.5: return None
    def hf(s):
        p = band_power(s, 6000, SR / 2).sum(); full = band_power(s, 20, SR / 2).sum()
        return 10 * np.log10(p / full + 1e-18) if full > 0 else None
    r = {'tail_from_s': round(t0 / SR, 2), 'tail_to_s': round(end / SR, 2), 'tail_dbfs': round(dbfs(tail), 1),
         'hf_body_db': hf(body), 'hf_tail_db': hf(tail), 'corr_body': lowmid_corr(body), 'corr_tail': lowmid_corr(tail),
         'flat_body': flatness(body), 'flat_tail': flatness(tail), 'lvl_wob_body': level_wobble(body[-len(tail):]),
         'lvl_wob_tail': level_wobble(tail)}
    ft = flatness(tail); r['pitch_wob_tail'] = pitch_wobble(tail) if ft is not None and ft < 0.2 else None   # a pitch only in a TONAL tail
    r = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}
    warn = []
    if r['hf_tail_db'] is not None and r['hf_body_db'] is not None and r['hf_tail_db'] - r['hf_body_db'] >= 10 and r['hf_tail_db'] > -40:
        warn.append(f"energy above 6 kHz rises {r['hf_tail_db'] - r['hf_body_db']:+.1f} dB in the tail ({r['hf_body_db']:.1f} → {r['hf_tail_db']:.1f} dB re full)")
    if r['corr_tail'] is not None and r['corr_body'] is not None and r['corr_body'] >= 0.8 and r['corr_tail'] < 0.7:   # low mids near mono in the body; a wide body reports only
        warn.append(f"100–500 Hz channel correlation falls {r['corr_body']:.2f} → {r['corr_tail']:.2f}")
    if r['corr_tail'] is not None and r['corr_tail'] < 0:                     # whatever the body: anti-phase low mids cancel in mono
        warn.append(f"100–500 Hz channel correlation in the tail is negative ({r['corr_tail']:.2f}): the low mids cancel on a mono speaker — listen")
    if r['flat_tail'] is not None and r['flat_body'] is not None and r['flat_tail'] >= max(0.2, 2 * r['flat_body']):
        warn.append(f"500 Hz–4 kHz flatness rises {r['flat_body']:.2f} → {r['flat_tail']:.2f} (towards noise)")
    if r['lvl_wob_tail'] is not None and r['lvl_wob_tail'] >= 3.0:            # a clean synthetic decay reads ~1.6; the body (beats) is reference only
        warn.append(f"the tail's level wobbles {r['lvl_wob_tail']:.1f} dB around its decay (≥ 3; the body {r['lvl_wob_body']} dB)")
    if r['pitch_wob_tail'] is not None and r['pitch_wob_tail'] >= 8:
        warn.append(f"the tail's pitch wobbles {r['pitch_wob_tail']:.1f} c frame to frame (≥ 8)")
    r['warn'] = warn
    return r


def read(x, tail_s=3.0):
    lvl = dbfs(x); out = {'dbfs': round(lvl, 1), 'dur_s': round(len(x) / SR, 2)}
    if lvl < QUIET_DB:
        out['verdict'] = f'too quiet to read ({lvl:.1f} dBFS < {QUIET_DB:g})'; return out
    off, spread = tuning(x); out['tuning_c'], out['tuning_spread_c'] = off, spread
    (c1, k1), (c2, k2) = key_of(chroma(x, off or 0.0))
    fin = lambda v: round(v, 2) if np.isfinite(v) else None                    # JSON carries null, never NaN
    out['key'], out['key_r'], out['runner_up'], out['runner_up_r'] = k1, fin(c1), k2, fin(c2)
    out['tempo_first'], out['tempo_last'], out['drift_pct'], out['tempo_conf'], out['tempo_octave_alt'] = tempo_drift(x)
    out['tail'] = tail_read(x, tail_s)
    warn = []
    if not np.isfinite(c1): warn.append('no key: the chroma is flat or empty — read it by ear')
    elif c1 <= 0.7: warn.append(f'key {k1} at r {c1:.2f} — not solid (> 0.7); read it by ear before tuning a sweetener')
    elif np.isfinite(c2) and c1 - c2 < 0.05: warn.append(f'key {k1} r {c1:.2f} against {k2} r {c2:.2f} — a near-tie (< 0.05): the notes are clear, the tonic is a listening call')
    if off is None: warn.append('no tuning: no stable spectral peak in 80–2000 Hz')
    if spread is not None and spread > 5: warn.append(f'tuning spread {spread:.1f} c across segments (> ~3–5 c): pitch wobble')
    if out['drift_pct'] is not None and abs(out['drift_pct']) > 3: warn.append(f"tempo drifts {out['drift_pct']:+.2f} % first third → last (> ~2–3 %): cross-check with beat_grid.py")
    elif out['tempo_conf'] is not None and out['tempo_conf'] < CONF_MIN: warn.append(f"no drift verdict: the onsets are weakly periodic (r {out['tempo_conf']:.2f} < {CONF_MIN}) — read the beats with beat_grid.py")
    if out['tail']: warn += out['tail']['warn']
    out['warn'] = warn; return out


# ------------------------------------------------------------------------------------------------------------ self-test
def synth(chords, bpm=120.0, bpm_end=None, detune_c=0.0, beats_per_chord=8, tail_fault=None, drums=True, seed=3, offbeat_hats=0.0):
    rng = np.random.default_rng(seed); nbeats = beats_per_chord * len(chords)
    b1 = bpm_end or bpm; per = [60.0 / (bpm + (b1 - bpm) * i / max(1, nbeats - 1)) for i in range(nbeats)]
    bt = np.concatenate([[0.0], np.cumsum(per)]); dur = bt[-1] + 3.0; n = int(dur * SR); x = np.zeros((n, 2))
    hz = lambda midi: 440.0 * 2 ** ((midi - 69 + detune_c / 100) / 12)
    for ci, notes in enumerate(chords):
        a, b = bt[ci * beats_per_chord], bt[(ci + 1) * beats_per_chord] if ci < len(chords) - 1 else dur - 0.5
        i0, i1 = int(a * SR), int(b * SR); t = np.arange(i1 - i0) / SR; env = np.minimum(1, t / 0.02) * np.exp(-t / 3.0)
        s = sum(sum((0.5 ** h) * np.sin(2 * np.pi * hz(m) * (h + 1) * t) for h in range(4)) for m in notes)
        x[i0:i1] += 0.08 * (s * env)[:, None]
    for tb in (bt[:-1] if drums else []):
        i = int(tb * SR); k = np.arange(int(0.12 * SR)); kick = 0.5 * np.sin(2 * np.pi * 55 * k / SR) * np.exp(-k / (0.03 * SR))
        hat = 0.05 * rng.standard_normal(int(0.03 * SR)) * np.exp(-np.arange(int(0.03 * SR)) / (0.005 * SR))
        x[i:i + len(kick)] += kick[:len(x) - i, None]; x[i:i + len(hat)] += hat[:len(x) - i, None]
    if offbeat_hats:                                  # quiet 30 ms noise ticks halfway between the beats
        hrng = np.random.default_rng(71); hl = int(0.03 * SR)
        for t0, t1 in zip(bt[:-1], bt[1:]):
            j = int((t0 + t1) / 2 * SR); x[j:j + hl] += (offbeat_hats * hrng.standard_normal(hl) * np.exp(-np.arange(hl) / (0.005 * SR)))[:len(x) - j, None]
    if tail_fault in ('hiss', 'decorr'):              # 'hiss': the decay turns to hiss · 'decorr': and its low mids lose the image too
        i = n - int(3.5 * SR); x[i:] += 0.05 * rng.standard_normal((n - i, 2))
    if tail_fault == 'antimid':                       # mid-band noise in opposite polarity: a downmix would cancel it
        i = n - int(3.5 * SR); Z = np.fft.rfft(rng.standard_normal(n - i)); f = np.fft.rfftfreq(n - i, 1 / SR); Z[(f < 500) | (f >= 4000)] = 0
        nz = np.fft.irfft(Z, n=n - i); nz = 0.1 * nz / nz.std(); x[i:, 0] += nz; x[i:, 1] -= nz
    if tail_fault == 'tremolo':                       # 8 Hz, 85 % on the decay
        i = n - int(3.5 * SR); tt = np.arange(n - i) / SR; x[i:] *= (1 - 0.85 * (0.5 + 0.5 * np.sin(2 * np.pi * 8 * tt)))[:, None]
    if tail_fault == 'vibrato':                       # the decay re-rendered with a 5 Hz, ±30 c vibrato
        i = n - int(3.5 * SR); tt = np.arange(n - i) / SR; env = np.exp(-tt / 3.0); s = np.zeros(n - i)
        for mm in chords[-1]:
            f0 = hz(mm); ph = 2 * np.pi * f0 * tt + (f0 * (2 ** (30 / 1200) - 1) / 5) * (-np.cos(2 * np.pi * 5 * tt))
            s += sum((0.5 ** h) * np.sin((h + 1) * ph) for h in range(4))
        x[i:] = 0.08 * (s * env)[:, None]
    if tail_fault == 'antiphase':                     # the decay's low mids flip polarity on one channel
        i = n - int(3.5 * SR); Z = np.fft.rfft(x[i:, 1]); f = np.fft.rfftfreq(n - i, 1 / SR); band = (f >= 100) & (f < 500)
        Z[band] *= -1; x[i:, 1] = np.fft.irfft(Z, n=n - i)
    if tail_fault == 'decorr':
        Z = np.fft.rfft(rng.standard_normal((n - i, 2)), axis=0); f = np.fft.rfftfreq(n - i, 1 / SR); Z[(f < 100) | (f >= 500)] = 0
        lm = np.fft.irfft(Z, n=n - i, axis=0); x[i:] += 0.15 * lm / lm.std()
    return x


def house(bpm=124.0, bars=24, seed=5):
    """four on the floor: a kick on every beat, a clap on 2 and 4, a quiet closed hat on the offbeats — the clap makes the
    two-beat lag the strongest autocorrelation peak, the octave a plain argmax lands on (two real house takes read 62.5/63)"""
    rng = np.random.default_rng(seed); per = 60.0 / bpm; nb = 4 * bars; n = int((nb * per + 2.0) * SR); x = np.zeros((n, 2))
    k = np.arange(int(0.15 * SR)); kick = 0.6 * np.sin(2 * np.pi * 50 * k / SR * (1 + 2 * np.exp(-k / (0.01 * SR)))) * np.exp(-k / (0.06 * SR))
    hl, cl = int(0.04 * SR), int(0.12 * SR)
    for b in range(nb):
        i = int(b * per * SR); x[i:i + len(kick)] += kick[:, None]
        j = int((b + 0.5) * per * SR); x[j:j + hl] += (0.02 * rng.standard_normal(hl) * np.exp(-np.arange(hl) / (0.008 * SR)))[:, None]
        if b % 4 in (1, 3): x[i:i + cl] += (0.35 * rng.standard_normal(cl) * np.exp(-np.arange(cl) / (0.03 * SR)))[:, None]
    return x


def selftest():
    C, F, G, Am, Dm, E = [60, 64, 67, 48], [65, 69, 72, 53], [67, 71, 74, 55], [57, 60, 64, 45], [62, 65, 69, 50], [64, 68, 71, 52]
    prog_c, prog_a = [C, F, G, C], [Am, Dm, E, Am]
    r1 = read(synth(prog_c)); r2 = read(synth(prog_a)); r3 = read(synth(prog_c, detune_c=20))
    r4 = read(synth(prog_c, bpm=120, bpm_end=132)); r5 = read(synth(prog_c, tail_fault='decorr')); r6 = read(synth(prog_c, tail_fault='hiss'))
    r7 = read(synth(prog_c, drums=False)); r8 = read(synth(prog_c, tail_fault='antiphase'))
    r9 = read(synth(prog_c, tail_fault='antimid')); r10 = read(synth(prog_c, tail_fault='tremolo')); r11 = read(synth(prog_c, tail_fault='vibrato'))
    op = synth(prog_c); op[:, 1] = -op[:, 0]; r12 = read(op)
    rq = read(np.zeros((SR * 5, 2))); rf = read(1e-4 * np.random.default_rng(1).standard_normal((SR * 5, 2)))
    rh = read(house()); rh100 = read(house(bpm=100.0)); r70 = read(synth([C] * 4, bpm=70)); r70h = read(synth([C] * 4, bpm=70, offbeat_hats=0.005))
    tw = lambda r: (r.get('tail') or {}).get('warn', [])
    chk = [('key: a I–IV–V–I in C reads C major, solid (r > 0.7)', r1.get('key') == 'C major' and r1['key_r'] > 0.7),
           ('key: a i–iv–V–i in A reads A minor', r2.get('key') == 'A minor'),
           ('key: a clear I–IV–V–I raises no near-tie WARN', not any('near-tie' in w for w in r1['warn'])),
           ('tuning: an in-tune take reads within ±3 c of A440', r1['tuning_c'] is not None and abs(r1['tuning_c']) <= 3),
           ('tuning: a take 20 c sharp reads +20 ± 3 c, and still C major', r3['tuning_c'] is not None and abs(r3['tuning_c'] - 20) <= 3 and r3.get('key') == 'C major'),
           ('tuning: one tuning reads a spread ≤ 3 c', r1['tuning_spread_c'] is not None and r1['tuning_spread_c'] <= 3),
           ('tempo: a steady 120 reads 120 ± 1.5 at both ends and drifts < 1 %', r1['tempo_first'] and abs(r1['tempo_first'] - 120) <= 1.5 and abs(r1['drift_pct']) < 1),
           ('tempo: 120 → 132 across the take drifts > 3 % and WARNs', r4['drift_pct'] is not None and r4['drift_pct'] > 3 and any('tempo drifts' in w for w in r4['warn'])),
           ('tempo: four on the floor at 124 with the clap on 2 and 4 reads 124 ± 1.5, not the half-time 62',
            rh['tempo_first'] and abs(rh['tempo_first'] - 124) <= 1.5 and abs(rh['tempo_last'] - 124) <= 1.5 and rh['drift_pct'] is not None),
           ('tempo: the same at 100 reads 100 ± 1.5, not the 1.5-beat lag 66.7 (its two-beat lag sits under 60)',
            rh100['tempo_first'] and abs(rh100['tempo_first'] - 100) <= 1.5),
           ('tempo: a kick on every beat at 70 still reads 70 ± 1.5, not the double 140, and the octave is not flagged',
            r70['tempo_first'] and abs(r70['tempo_first'] - 70) <= 1.5 and not r70['tempo_octave_alt']),
           ('tempo: four on the floor at 124 names 62 as the other octave (the onsets cannot settle it)', rh['tempo_octave_alt'] and abs(rh['tempo_octave_alt'] - 62) <= 1.5),
           ('tempo: 70 with quiet offbeat hats never reads 140 unqualified — 70, or 140 with 70 named as the other octave',
            r70h['tempo_first'] and (abs(r70h['tempo_first'] - 70) <= 1.5 or (r70h['tempo_octave_alt'] and abs(r70h['tempo_octave_alt'] - 70) <= 1.5))),
           ('tail: a clean decay raises no tail WARN', r1['tail'] is not None and not tw(r1)),
           ('tail: hiss alone WARNs on >6 kHz and flatness, never on the low-mid correlation (hiss leaves tonal low mids correlated)',
            len(tw(r6)) == 2 and not any('correlation' in w for w in tw(r6))),
           ('tail: hiss plus low mids that lose their stereo image WARNs on all three reads', len(tw(r5)) == 3),
           ('tail: low mids flipped in polarity on one channel WARN as negative correlation', any('negative' in w for w in tw(r8))),
           ('tail: mid-band noise in opposite polarity still WARNs on flatness (the channels\' powers add)', any('flatness' in w for w in tw(r9))),
           ('tail: an 8 Hz, 85 % tremolo on the decay WARNs on level wobble', any('level wobbles' in w for w in tw(r10))),
           ('tail: a 5 Hz, ±30 c vibrato on the decay WARNs on pitch wobble', any('pitch wobbles' in w for w in tw(r11))),
           ('tail: a clean decay WARNs on neither wobble', not any('wobbles' in w for w in tw(r1))),
           ('stereo: a take in opposite polarity still reads C major and its tuning, and the tail WARNs negative',
            r12.get('key') == 'C major' and r12['tuning_c'] is not None and abs(r12['tuning_c']) <= 3 and any('negative' in w for w in tw(r12))),
           ('tempo: chords with no beat give no drift verdict, and say so', r7['drift_pct'] is None and any('no drift verdict' in w for w in r7['warn'])),
           ('level gate: digital silence is too quiet to read — no key', 'key' not in rq and 'too quiet' in rq.get('verdict', '')),
           ('level gate: a -80 dBFS noise floor is too quiet to read — no key', 'key' not in rf and 'too quiet' in rf.get('verdict', ''))]
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('take', nargs='?'); ap.add_argument('--tail', type=float, default=3.0); ap.add_argument('--start', type=float)
    ap.add_argument('--dur', type=float); ap.add_argument('--json'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if not selftest(): print('SELF-TEST FAILED — the instrument is broken; nothing read'); sys.exit(2)
    if a.selftest: sys.exit(0)
    if not a.take: ap.error('a take, or --selftest')
    try: x = load(a.take, a.start, a.dur)
    except Exception as ex: print(f'unreadable: {ex}'); sys.exit(2)
    r = read(x, a.tail); print(f"{a.take}: {r['dur_s']} s, {r['dbfs']} dBFS")
    if 'verdict' in r: print(r['verdict'])
    else:
        print(f"key     {r['key']} (r {r['key_r']}; runner-up {r['runner_up']} {r['runner_up_r']})" if r['key_r'] is not None else 'key     unmeasurable')
        print(f"tuning  {r['tuning_c']:+.1f} c from A440, spread {r['tuning_spread_c']} c" if r['tuning_c'] is not None else 'tuning  unmeasurable')
        dr = f"drift {r['drift_pct']:+.2f} %" if r['drift_pct'] is not None else f"no drift verdict (onset periodicity r {r['tempo_conf']})"
        oc = f" (or {r['tempo_octave_alt']} — the octave is a call: beat_grid.py's x0.5/x1/x2 rows or the ear)" if r.get('tempo_octave_alt') else ''
        print(f"tempo   {r['tempo_first']} → {r['tempo_last']} BPM{oc}, {dr}" if r['tempo_first'] else 'tempo   too short to read')
        t = r['tail']
        print(f"tail    {t['tail_from_s']}–{t['tail_to_s']} s at {t['tail_dbfs']} dBFS: >6 kHz {t['hf_body_db']} → {t['hf_tail_db']} dB re full · "
              f"100–500 Hz corr {t['corr_body']} → {t['corr_tail']} · flatness {t['flat_body']} → {t['flat_tail']} · level wobble "
              f"{t['lvl_wob_body']} → {t['lvl_wob_tail']} dB · pitch wobble {t['pitch_wob_tail']} c" if t else 'tail    nothing audible to read')
        for w in r['warn']: print(f'WARN {w}')
    clean = lambda v: {k: clean(u) for k, u in v.items()} if isinstance(v, dict) else [clean(u) for u in v] if isinstance(v, list) \
        else (None if isinstance(v, float) and not np.isfinite(v) else v)
    if a.json: json.dump(clean(r), open(a.json, 'w'), indent=1, allow_nan=False)
    print('MUSIC-TAKE-END'); sys.exit(0)


if __name__ == '__main__':
    main()
