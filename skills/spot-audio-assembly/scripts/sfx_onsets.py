#!/usr/bin/env python3
"""sfx_onsets.py — the syllable map of an SFX file BEFORE it is cut: onsets (a rise of ≥ --rise dB over the preceding
60 ms floor) listed by ordinal with their times and peaks, so a reel pick given in the operator's words — "the four before
the last one", "the end one, not the bitten-off start", "the second last one that starts at 0:43" — maps to sample-exact
cut points. --cut a:b writes the excerpt with 5 ms fades. Self-test first: a synthesized
four-click file must yield exactly four onsets, a whoosh its pass-by peak and a riser its end, or nothing else is printed.

--sync names where a sound's SYNC POINT sits inside the sound as it will play (after --src-in), so the sound is placed by
the VISUAL event it belongs to, never by a guessed offset: `transient` (a one-shot or an impact: its onset; --ordinal picks
which), `peak` (a whoosh: its pass-by, the loudest moment), `end` (a riser, a reverse cymbal, a swell: the hit it drives
into — the last moment within 1 dB of its loudest). With --event T (the visual event's timeline second) it prints the
`at` that puts the sync point on T, and the EDL's `sync` block. Pattern: mg-styles-15 `lib/audio/README.md` § 1.

  sfx_onsets.py <file> [--rise 12] [--hop-ms 10] [--cut 0.83:2.10 --out audio/sfx/<name>.wav]
  sfx_onsets.py <file> --sync transient|peak|end [--ordinal 1] [--src-in <s> --dur <s>] [--event <timeline s>]
"""
import argparse, hashlib, json, subprocess, sys
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


def sync_point(x, kind, ordinal=1, rise=12.0, min_db=-40.0, hop_ms=5.0):
    """seconds into x of its sync point, or None. Levels from a 20 ms RMS on a 5 ms hop."""
    if kind == 'transient':   # 0.1 s of quiet ahead: a one-shot trimmed tight to its hit has no floor before it to rise from
        pad = 0.1; on = onsets(np.concatenate([np.zeros(int(pad * SR), np.float32), np.asarray(x, np.float32)]), rise, hop_ms, min_db)
        return round(on[ordinal - 1][0] - pad, 3) if 0 < ordinal <= len(on) else None
    h, w = int(hop_ms / 1000 * SR), int(0.020 * SR); n = max(1, (len(x) - w) // h + 1)
    db = 20 * np.log10(np.sqrt(np.array([np.mean(x[i * h:i * h + w] ** 2) for i in range(n)])) + 1e-9)
    if db.max() < min_db: return None
    if kind == 'peak': return round((int(np.argmax(db)) * h + w / 2) / SR, 3)          # the loudest window's centre
    return round((int(np.nonzero(db >= db.max() - 1.0)[0][-1]) * h + w) / SR, 3)       # the END of the last window within 1 dB of the loudest


def selftest(rise, hop_ms, min_db):
    rng = np.random.default_rng(3); test = 0.001 * rng.standard_normal(int(1.2 * SR)).astype(np.float32)
    for k in range(4):
        i0 = int((0.2 + 0.25 * k) * SR); burst = rng.standard_normal(int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / (0.01 * SR)); test[i0:i0 + len(burst)] += 0.5 * burst.astype(np.float32)
    st = onsets(test, rise, hop_ms, min_db)
    if len(st) != 4: return f'four clicks read as {len(st)} onsets {st}'
    t = np.arange(int(1.0 * SR)) / SR; noise = rng.standard_normal(len(t))
    whoosh = 0.4 * noise * np.sin(np.pi * t / 0.8) ** 4 * (t < 0.8)                         # passes by at 0.40 s
    riser = 0.4 * noise * (t / 0.8) ** 3 * (t < 0.8)                                         # drives into a hit at 0.80 s
    tight = test[int(0.2 * SR):]                                                              # a one-shot trimmed tight to its first hit
    got = {'transient': sync_point(test, 'transient', 2), 'tight': sync_point(tight, 'transient'), 'peak': sync_point(whoosh, 'peak'), 'end': sync_point(riser, 'end')}
    want = {'transient': 0.45, 'tight': 0.0, 'peak': 0.40, 'end': 0.80}
    bad = [f'{k} read {got[k]} (want {want[k]} ± 0.03)' for k in want if got[k] is None or abs(got[k] - want[k]) > 0.03]
    return '; '.join(bad) or None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file'); ap.add_argument('--rise', type=float, default=12); ap.add_argument('--hop-ms', type=float, default=10); ap.add_argument('--cut'); ap.add_argument('--out')
    ap.add_argument('--min-db', type=float, default=-40, help='ignore rises that stay below this level (noise-floor flutter)')
    ap.add_argument('--sync', choices=('transient', 'peak', 'end')); ap.add_argument('--ordinal', type=int, default=1)
    ap.add_argument('--src-in', type=float, default=0.0); ap.add_argument('--dur', type=float); ap.add_argument('--event', type=float)
    a = ap.parse_args()
    bad = selftest(a.rise, a.hop_ms, a.min_db)
    if bad: sys.exit(f'SELF-TEST FAILED: {bad}; the instrument is broken, nothing printed')
    print('self-test ok: four synthesized clicks read as four onsets; a whoosh peaks at 0.40 s, a riser ends at 0.80 s')
    x = pcm(a.file)
    if a.sync:
        i0 = int(a.src_in * SR); seg = x[i0:i0 + int(a.dur * SR)] if a.dur else x[i0:]
        s = sync_point(seg, a.sync, a.ordinal, a.rise, a.min_db)
        if s is None: sys.exit(f'{a.file}: no {a.sync} sync point found (too quiet, or fewer than {a.ordinal} onsets)')
        print(f'{a.file}: {a.sync} sync point {s:.3f} s into the sound as played (src_in {a.src_in:g})')
        if a.event is not None:
            at = round(a.event - s, 3); print(f'  at {at:.3f} puts it on the event at {a.event:.3f}')
            print('  EDL: ' + json.dumps({'at': at, 'sync': {'kind': a.sync, 's': s, 'event': a.event}}))
        print('  derived: ' + json.dumps({'from': [a.file], 'method': f'sfx_onsets.py --sync {a.sync} --ordinal {a.ordinal} --src-in {a.src_in:g}' + (f' --dur {a.dur:g}' if a.dur else ''),
                                         'sha256': {a.file: hashlib.sha256(open(a.file, 'rb').read()).hexdigest()}}) + "   (the plan entry's derived block: a swapped sound then FAILS the build until re-measured)")
        return
    on = onsets(x, a.rise, a.hop_ms, a.min_db)
    print(f'{a.file}: {len(x) / SR:.3f} s, {len(on)} onset(s)')
    for i, (t, d) in enumerate(on, 1): print(f'  {i:02d}  {t:7.3f} s  {d:6.1f} dBFS')
    if a.cut:
        assert a.out, '--cut needs --out'; s, e = (float(v) for v in a.cut.split(':')); assert 0 <= s < e <= len(x) / SR + 1e-6, 'cut outside the file'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{s:.4f}', '-t', f'{e - s:.4f}', '-i', a.file, '-af', f'afade=t=in:st=0:d=0.005,afade=t=out:st={max(0, e - s - 0.005):.4f}:d=0.005', '-ar', str(SR), '-c:a', 'pcm_s24le', a.out], check=True)
        print(f'wrote {a.out}: {e - s:.3f} s from {s:.3f}')


if __name__ == '__main__':
    main()
