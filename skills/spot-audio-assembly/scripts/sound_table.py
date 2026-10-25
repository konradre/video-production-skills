#!/usr/bin/env python3
"""sound_table.py — the sound table read on the DELIVERED file: every designed sound the EDL places, measured where it
landed, so "every row of the sound table is in the mix" is a reading, not a belief. INFO rows only, no verdict, until
the reads have been measured on two real deliverables.

  (each sfx's presence at its `at` — around its sync point when it has one — is qc_deliverable's sfx row; its sync point
   on its event is edl_check's sum — neither is repeated here)
  music     each music cue found in the delivered mix: per-channel correlation of the cue (at its vol, ducks avoided) with
            the mix over ±20 ms at three points across its span, and its level against the mix
  suck-out  each music duck with gain ≤ 0.1 lasting 0.2–0.7 s: how far the whole mix fell inside it against the 0.5 s
            before its ramp (the rule: 25–30 dB; a line or a riser playing inside it shows as a shallow depth)
  silences  with --turn or qc.turn (a marker name): the runs of ≥ 0.25 s at least 20 dB under the programme's level before
            the turn; a run inside the union of the suck-outs is tagged and never counted (films and music videos: at least
            two); after each, the FIRST audible sound's level, and the loudest in the half-second after it
  loudest   the three loudest 400 ms moments and what the EDL places there (the designed impacts should be these)
  low end   20–60 Hz power against the 20 Hz–20 kHz band (the rule: about 15 dB under)
Levels and spectra keep both channels — a level is the mean of the channels' powers, so stereo content in opposite
polarity is measured, never cancelled by a downmix, and a dBFS reads as it does per channel. Self-test first on synthetic mixes with known answers, or nothing is printed (exit 2).

  sound_table.py --root <project> --edl edit/<SPOT>-EDL.json --deliv deliver/<file>.mp4 [--turn <marker>] [--json <out.json>]
  sound_table.py --selftest
Exit 0 (the rows are information) · 2 = self-test failed or the file is unreadable.
"""
import argparse, glob, json, os, subprocess, sys
import numpy as np

SR = 48000; BLK = 0.050


def pcm(f, ss=None, t=None):
    """(n, 2) float64 — both channels kept"""
    cmd = ['ffmpeg', '-v', 'error'] + (['-ss', f'{ss:.4f}'] if ss is not None else []) + (['-t', f'{t:.4f}'] if t else []) + ['-i', f, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).reshape(-1, 2).astype(np.float64)


def st(x):
    x = np.asarray(x, np.float64); return x[:, None] if x.ndim == 1 else x


def power(x):
    """the mean power of a stretch: the MEAN of the channels' powers — opposite polarity is never cancelled, as a downmix would,
    and a dBFS reads as it does per channel (a stereo 0.1 sine: -23.0)"""
    x = st(x); return float(np.mean(x ** 2, axis=0).mean()) if len(x) else 0.0


def db_of(x): return 10 * np.log10(power(x) + 1e-18)


def block_db(x, blk=BLK):
    x = st(x); n = int(blk * SR); m = len(x) // n
    return 10 * np.log10(np.mean(x[:m * n].reshape(m, n, x.shape[1]) ** 2, axis=1).mean(axis=1) + 1e-18)


def programme_level(db):
    """the active programme's level: the median of the blocks within 30 dB of the loudest"""
    return float(np.median(db[db > db.max() - 30]))


def runs_under(db, thr, min_s=0.25, blk=BLK):
    q = db <= thr; out = []; i = 0
    while i < len(q):
        if q[i]:
            j = i
            while j < len(q) and q[j]: j += 1
            if (j - i) * blk >= min_s - 1e-9: out.append((round(i * blk, 3), round(j * blk, 3)))
            i = j
        else: i += 1
    return out


def duck_parts(dk, cue_ramp=0.25):
    """[from, to, gain] · [from, to, gain, ramp] · [from, to, gain, ramp_in, ramp_out] (EDL-CONTRACT.md § audio)"""
    if not isinstance(dk, (list, tuple)) or len(dk) not in (3, 4, 5): raise ValueError(f'a duck is 3, 4 or 5 numbers: {dk!r}')
    a, b, g = (float(v) for v in dk[:3]); ri = float(dk[3]) if len(dk) > 3 else float(cue_ramp); ro = float(dk[4]) if len(dk) > 4 else ri
    return a, b, g, ri, ro


def suckouts(edl):
    out = []
    for name, m in ((edl.get('audio') or {}).get('music') or {}).items():
        if not isinstance(m, dict): continue
        for dk in m.get('duck', []):
            a, b, g, ri, ro = duck_parts(dk, m.get('duck_ramp', 0.25))
            if g <= 0.1 and 0.2 <= b - a <= 0.7: out.append({'cue': name, 'from': a, 'to': b, 'gain': g, 'ramp_in': ri})
    return out


def union(spans, pad=0.1):
    """merged [a - pad, b + pad] intervals: adjacent or overlapping suck-outs make one quiet stretch"""
    out = []
    for a, b in sorted((a - pad, b + pad) for a, b in spans):
        if out and a <= out[-1][1]: out[-1][1] = max(out[-1][1], b)
        else: out.append([a, b])
    return out


def depth(x, a, b, ri):
    """the mix level before the ramp against inside the window (the window's last 80 %: the ramp is settling at its start)"""
    def lv(s, e):
        i, j = int(max(0, s) * SR), int(max(0, e) * SR); seg = st(x)[i:j]
        return db_of(seg) if len(seg) > SR * 0.02 else None
    pre = lv(a - ri - 0.5, a - ri); ins = lv(a + 0.2 * (b - a), b)
    return (round(pre - ins, 1) if pre is not None and ins is not None else None), pre, ins


def loudest(x, k=3, win=0.4, hop=0.1, sep=1.0):
    x = st(x); w, h = int(win * SR), int(hop * SR); n = max(1, (len(x) - w) // h + 1)
    lv = np.array([db_of(x[i * h:i * h + w]) for i in range(n)]); picks = []
    for i in np.argsort(-lv):
        t = i * hop
        if all(abs(t - p[0]) >= sep for p in picks): picks.append((round(t, 2), round(float(lv[i]), 1)))
        if len(picks) == k: break
    return picks


def low_end(x, seg=1.0):
    x = st(x); n = int(seg * SR); m = len(x) // n
    if m == 0: return None
    win = np.hanning(n)
    P = sum(np.mean([np.abs(np.fft.rfft(x[i * n:(i + 1) * n, c] * win)) ** 2 for i in range(m)], axis=0) for c in range(x.shape[1]))   # channel powers added
    f = np.fft.rfftfreq(n, 1 / SR); lo = P[(f >= 20) & (f <= 60)].sum(); full = P[(f >= 20) & (f <= 20000)].sum()
    return round(10 * np.log10(lo / full + 1e-12), 1) if full > 0 else None


def first(pat, root='.'):
    for p in str(pat or '').split('|'):
        g = sorted(glob.glob(os.path.join(root, p)))
        if g: return g[0]
    return None


def music_points(m, n=3, L=0.6):
    """three timeline points across the cue's span, each window clear of the cue's ducks, its fades and its edges"""
    t0, t1 = float(m['tl'][0]), float(m['tl'][1]); fi, fo = float(m.get('fade_in') or 0), float(m.get('fade_out', 0.15) or 0)
    lo, hi = t0 + fi + 0.05, t1 - fo - L - 0.05; ducks = [duck_parts(dk, m.get('duck_ramp', 0.25)) for dk in m.get('duck', [])]
    if hi <= lo: return []
    clear = lambda t: all(t + L <= a - ri - 0.02 or t >= b + ro + 0.02 for a, b, g, ri, ro in ducks)
    cand = [t for t in np.arange(lo, hi + 1e-9, 0.05) if clear(t)]
    if not cand: return []
    return sorted({round(float(cand[int(round(q * (len(cand) - 1)))]), 3) for q in np.linspace(0.15, 0.85, n)})


def correlate(cue, mix):
    """the best normalised correlation of cue inside mix over EVERY sample lag, per channel then averaged — a noise bed
    decorrelates within a sample, so a stride (0.5 ms) missed a cue starting on a frame (1/24 s, the finisher's ms-rounded delay)"""
    cue, mix = st(cue), st(mix); L = len(cue); n = len(mix) - L + 1
    if n < 1: return 0.0
    tot, k = np.zeros(n), 0
    for c in range(min(cue.shape[1], mix.shape[1])):
        a, w = cue[:, c], mix[:, c]; na = np.linalg.norm(a)
        if not na: continue
        nw = np.sqrt(np.convolve(w ** 2, np.ones(L), 'valid'))   # each window summed directly: cumulative sums cancel after a loud prefix
        tot += np.where(nw > 0, np.correlate(w, a, 'valid') / np.where(nw > 0, na * nw, 1.0), 0.0); k += 1
    return float((tot / k).max()) if k else 0.0


def music_rows(edl, x, cue_pcm):
    """[(what, reading)] — every cue's presence at points across its span"""
    rows = []
    for name, m in ((edl.get('audio') or {}).get('music') or {}).items():
        if not isinstance(m, dict) or 'tl' not in m: continue
        try: pts = music_points(m)
        except ValueError as ex: rows.append((name, f'unreadable ducks: {ex}')); continue
        if not pts: rows.append((name, 'no stretch of the cue lies clear of its ducks and fades — read it by ear')); continue
        rs, rel = [], []
        for t in pts:
            try: c = cue_pcm(m, t - float(m['tl'][0]), 0.6)
            except Exception as ex: rows.append((name, f'unreadable: {ex}')); rs = None; break
            c = st(c) * float(m.get('vol', 0.7)); i0 = int(max(0.0, t - 0.02) * SR); w = st(x)[i0:i0 + len(c) + int(0.04 * SR)]
            if len(w) <= len(c): rs.append(0.0); continue
            rs.append(correlate(c, w)); rel.append(db_of(c) - db_of(w[int(0.02 * SR):int(0.02 * SR) + len(c)]))
        if rs is None: continue
        rows.append((f"{name} {float(m['tl'][0]):.2f}–{float(m['tl'][1]):.2f}", f"correlation {', '.join(f'{r:.2f}' for r in rs)} at {', '.join(f'{t:.2f}' for t in pts)} s"
                     + (f"; its level {np.median(rel):+.1f} dB against the mix" if rel else '') + ('' if min(rs) >= 0.2 else '  — weak or missing there: listen')))
    return rows


def placed_at(edl, t):
    au = edl.get('audio') or {}; names = []
    for k, s in (au.get('sfx') or {}).items():
        if isinstance(s, dict) and 'at' in s and s['at'] - 0.1 <= t <= s['at'] + float(s.get('dur') or 0.5) + 0.1: names.append(f'sfx {k}')
    for k, v in (au.get('vo') or {}).items():
        if isinstance(v, dict) and 'at' in v and v['at'] <= t <= v['at'] + float(v.get('dur') or 0): names.append(f'VO {k}')
    return ', '.join(names) or 'no sfx or line — music or a native bed'


def read(edl, x, turn_name=None, cue_pcm=None):
    """every row, from the delivered mix x ((n, 2) or mono, SR) and a loader cue_pcm(music entry, offset s, dur s)"""
    rows = []; db = block_db(x); ref = programme_level(db); mk = edl.get('markers') or {}
    if cue_pcm is not None:
        for what, val in music_rows(edl, x, cue_pcm): rows.append(('music', what, val))
    so = suckouts(edl); U = union([(d['from'], d['to']) for d in so])
    for d in so:
        dep, pre, ins = depth(x, d['from'], d['to'], d['ramp_in'])
        rows.append(('suck-out', f"{d['cue']} {d['from']:.2f}–{d['to']:.2f}", f"the mix fell {dep} dB (rule 25–30)" if dep is not None else 'too short to read'))
    if turn_name:
        tt = mk.get(turn_name)
        if not isinstance(tt, (int, float)): rows.append(('silences', turn_name, f'qc.turn names {turn_name!r}, which is no marker'))
        else:
            thr = ref - 20; sil = [(a, b) for a, b in runs_under(db, thr) if b <= tt + 1e-6]; real = 0
            for a, b in sil:
                so_ = any(u0 <= a and b <= u1 for u0, u1 in U); real += not so_   # a suck-out, or several back to back, is its own rule
                j0 = int(round(b / BLK)); nxt = db[j0:j0 + int(1.0 / BLK)]; on = np.nonzero(nxt > thr)[0]
                if len(on):
                    fa = on[0]; mx = nxt[fa:fa + int(0.5 / BLK)]
                    after = f'then the first sound at {b + fa * BLK:.2f} s, {float(nxt[fa]) - ref:+.1f} dB on the programme (the loudest in its next 0.5 s {float(mx.max()) - ref:+.1f})'
                else: after = 'then nothing audible for 1 s'
                rows.append(('silence', f"{a:.2f}–{b:.2f}{' (a suck-out, not counted)' if so_ else ''}", after))
            rows.append(('silences', turn_name, f'{real} before the turn at {tt:.2f} s, suck-outs not counted (films and music videos: at least 2)'))
    else: rows.append(('silences', '—', 'N/A — no turn named (--turn or qc.turn: a film or a music video names its turn)'))
    for t, lv in loudest(x): rows.append(('loudest', f'{t:.2f} s', f'{lv:.1f} dBFS (400 ms) — {placed_at(edl, t + 0.2)}'))
    le = low_end(x); rows.append(('low end', '20–60 Hz', f'{le} dB against the full band (rule: about -15)' if le is not None else 'too short to read'))
    return rows, ref


def _raises(f):
    try: f()
    except ValueError: return True
    return False


def selftest():
    rng = np.random.default_rng(7); dur = 6.0; n = int(dur * SR); t = np.arange(n) / SR
    bed = 0.05 * rng.standard_normal(n) + 0.02 * np.sin(2 * np.pi * 45 * t)
    for a, b in ((1.0, 1.4), (2.6, 3.0)): bed[int(a * SR):int(b * SR)] = 0.0
    bed[int(3.6 * SR):int(4.0 * SR)] *= 0.03                                            # the suck-out before the impact
    click = 0.3 * np.sin(2 * np.pi * 2000 * np.arange(int(0.03 * SR)) / SR) * np.hanning(int(0.03 * SR))
    hit = 0.5 * rng.standard_normal(int(0.4 * SR)) * np.exp(-np.arange(int(0.4 * SR)) / (0.15 * SR))
    x = bed.copy(); x[int(2.0 * SR):int(2.0 * SR) + len(click)] += click; x[int(4.0 * SR):int(4.0 * SR) + len(hit)] += hit
    edl = {'markers': {'TURN': 4.0}, 'audio': {'sfx': {'click': {'file': 'x', 'at': 2.0, 'dur': 0.03}, 'hit': {'file': 'y', 'at': 4.0, 'dur': 0.4}},
                                              'music': {'bed': {'tl': [0, 6], 'duck': [[3.6, 4.0, 0.03, 0.06, 0]]}}}}
    rows, ref = read(edl, x, 'TURN'); get = lambda kind: [r for r in rows if r[0] == kind]
    so = get('suck-out'); si = get('silence'); lo = get('loudest')
    pair = np.sin(2 * np.pi * 40 * t) + np.sin(2 * np.pi * 1000 * t)                  # equal power at 40 Hz and 1 kHz
    ms = np.stack([np.sin(2 * np.pi * 40 * t) + np.sin(2 * np.pi * 1000 * t), np.sin(2 * np.pi * 40 * t) - np.sin(2 * np.pi * 1000 * t)], 1)   # 40 Hz mid, 1 kHz side
    tone = 0.3 * np.sin(2 * np.pi * 300 * t); anti = np.stack([tone, -tone], 1)
    adj = 0.05 * rng.standard_normal(n); adj[int(1.0 * SR):int(1.7 * SR)] *= 0.03                                # two suck-outs back to back
    rows2, _ = read({'markers': {'T': 2.5}, 'audio': {'music': {'m': {'tl': [0, 6], 'duck': [[1.0, 1.35, 0.03, 0.06, 0], [1.35, 1.7, 0.03, 0.06, 0]]}}}}, adj, 'T')
    fs = 0.05 * rng.standard_normal(n); fs[int(1.0 * SR):int(1.5 * SR)] = 0.0
    fs[int(1.5 * SR):int(1.6 * SR)] = 0.01 * rng.standard_normal(int(0.1 * SR)); fs[int(1.75 * SR):int(1.85 * SR)] = 0.25 * rng.standard_normal(int(0.1 * SR))
    rows3, ref3 = read({'markers': {'T': 3.0}, 'audio': {}}, fs, 'T'); sil3 = [r for r in rows3 if r[0] == 'silence']
    bedm = 0.1 * rng.standard_normal((n, 2)); voice = 0.1 * rng.standard_normal((n, 2))
    mix_with, mix_without = 0.7 * bedm + voice, voice
    E4 = {'audio': {'music': {'bed': {'file': 'z', 'tl': [0, 6], 'vol': 0.7}}}}
    loader = lambda m, off, d: bedm[int(off * SR):int((off + d) * SR)]
    with_ = music_rows(E4, mix_with, loader); without_ = music_rows(E4, mix_without, loader)
    sh = int(round(1 / 24 * 1000)) * SR // 1000; mix_fr = voice.copy(); mix_fr[sh:] += 0.7 * bedm[:n - sh]   # the finisher's adelay, rounded to the ms
    fr_ = music_rows({'audio': {'music': {'bed': {'file': 'z', 'tl': [1 / 24, 6], 'vol': 0.7}}}}, mix_fr, loader)
    pf = rng.integers(-1, 2, (n, 2)) / 2 ** 23; tt = np.arange(int(0.02 * SR)) / SR
    for t0 in (1.0, 2.6, 4.2): pf[int((t0 - 0.02) * SR):int(t0 * SR)] = 0.8 * np.sin(2 * np.pi * 1000 * tt)[:, None]   # a loud 20 ms just before each read point
    pf_ = music_rows({'audio': {'music': {'bed': {'file': 'z', 'tl': [0, 6], 'vol': 0.7}}}}, pf, loader)
    chk = [('suck-out: the mix fell at least 25 dB', len(so) == 1 and float(so[0][2].split('fell ')[1].split(' dB')[0]) >= 25),
           ('silences: three runs before the turn, the last one the suck-out', len(si) == 3 and '(a suck-out' in si[2][1] and '(a suck-out' not in si[0][1]),
           ('silences: the count is 2 — the suck-out is not one of them', any(r[0] == 'silences' and r[2].startswith('2 before') for r in rows)),
           ('silences: two suck-outs back to back are one quiet stretch, not a real silence', any(r[0] == 'silences' and r[2].startswith('0 before') for r in rows2)),
           ('first sound: the first audible block after the silence, not the louder one 0.25 s later', len(sil3) == 1 and f'first sound at 1.50 s, {block_db(fs)[30] - ref3:+.1f} dB' in sil3[0][2] and block_db(fs)[30] - ref3 < -10 and f'next 0.5 s {block_db(fs)[30:40].max() - ref3:+.1f}' in sil3[0][2]),
           ('loudest: the impact at 4.0 s first', len(lo) == 3 and abs(float(lo[0][1].split(' ')[0]) - 4.0) <= 0.2),
           ('loudest: the impact is named by what the EDL places there', len(lo) == 3 and 'sfx hit' in lo[0][2]),
           ('low end: equal power at 40 Hz and 1 kHz reads -3.0 dB', abs(low_end(pair) - (-3.0)) <= 0.3),
           ('low end, stereo: a 40 Hz mid with a 1 kHz side still reads -3.0 dB (no downmix cancels the side)', abs(low_end(ms) - (-3.0)) <= 0.3),
           ('level, stereo: a tone in opposite polarity on the two channels reads its power, not silence', abs(db_of(anti) - 10 * np.log10(0.045)) <= 0.1),
           ('level, stereo: a 0.1 sine on both channels reads -23.0 dBFS, as ffmpeg reads it per channel', abs(db_of(np.stack([0.1 * np.sin(2 * np.pi * 1000 * t)] * 2, 1)) - (-23.01)) <= 0.05),
           ('music: a bed starting on a frame (1/24 s, placed by the ms) is found at every point — every sample lag searched', len(fr_) == 1 and 'weak' not in fr_[0][1]),
           ('music: a bed in the mix under a louder voice is found at all three points', len(with_) == 1 and 'weak' not in with_[0][1] and with_[0][1].count(',') >= 2),
           ('music: a bed missing from the mix reads weak', len(without_) == 1 and 'weak or missing' in without_[0][1]),
           ('music: a bed missing after loud prefixes and a one-LSB floor reads weak (no cumulative-sum cancellation)', len(pf_) == 1 and 'weak or missing' in pf_[0][1] and all(float(v) <= 1.0 for v in pf_[0][1].split('correlation ')[1].split(' at')[0].split(', '))),
           ('duck forms: 3, 4 and 5 numbers parse; 2 raises', duck_parts([1, 2, .5])[3] == 0.25 and duck_parts([1, 2, .5, .1])[4] == 0.1 and duck_parts([1, 2, .5, .1, 0])[4] == 0.0 and _raises(lambda: duck_parts([1, 2])))]
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl'); ap.add_argument('--deliv'); ap.add_argument('--json'); ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--turn', help="the turn's marker name (else the EDL's qc.turn, entered by hand like every qc key)")
    a = ap.parse_args()
    if not selftest(): print('SELF-TEST FAILED — the instrument is broken; no rows printed'); sys.exit(2)
    if a.selftest: sys.exit(0)
    if not (a.edl and a.deliv): ap.error('--edl and --deliv, or --selftest')
    os.chdir(a.root); edl = json.load(open(a.edl, encoding='utf-8'))
    try: x = pcm(a.deliv)
    except Exception as ex: print(f'unreadable: {ex}'); sys.exit(2)
    def cue_pcm(m, off, d):
        f = first(m.get('file'))
        if not f: raise FileNotFoundError(f"no file for {m.get('file')}")
        return pcm(f, ss=off, t=d)
    rows, ref = read(edl, x, a.turn or (edl.get('qc') or {}).get('turn'), cue_pcm)
    print(f'{a.deliv}: {len(x) / SR:.3f} s, programme level {ref:.1f} dBFS (50 ms blocks, the mean of the channels\' powers)')
    for kind, what, val in rows: print(f'INFO {kind:9} {what}: {val}')
    if a.json: json.dump([{'row': k, 'what': w, 'reading': v} for k, w, v in rows], open(a.json, 'w'), indent=1)
    print('SOUND-TABLE-END'); sys.exit(0)


if __name__ == '__main__':
    main()
