#!/usr/bin/env python3
"""edge_audit.py — no word bitten at a cut: every edge where a take's own sound plays is read from that SOUND.

A word cut off at a cut is heard at once and measured by nothing else in the chain. ASR word times end early (one
measured case: 0.19 s before the sound did), and a 200-4000 Hz speech band misses the sibilant tail ("-st", "-s")
that carries the end of a word. So each edge is read on a broadband envelope (--band, 120-7800 Hz by default) of the
take's own audio in 10 ms frames, relative to the event's own speech level (the 90th percentile over its window):

  takes mode (default) — every event whose native sound plays, at its AUDIBLE edges (native_audio_from/_to where set,
  else in/out):
    out  BITE   the 20 ms before the edge are at speech level (within --speech-db of the p90): a word is cut
         TIGHT  the 20 ms are above the quiet line (--quiet-db under the p90, or the take's bed + --bed-margin)
    in   BITE   the 30 ms before the edge AND the first 10 ms after it are at speech level: the edge splits a word
         TIGHT  the first 10 ms after the edge are above the quiet line: the word's onset is clipped
  Each flagged edge prints the measured fix: where the sounding word ends (or starts), the nearest gaps either side,
  and the take's own picture cuts near it (--cuts). Move the edge into a gap (in/out, or native_audio_from/_to), or
  carry the word's tail as an sfx over the next event (video-edit-edl § 3, carried sound) when the picture must
  change first.

  --deliv <file> — the DELIVERED file at every join where a take's sound plays on either side: the 20 ms before the
  join's last 10 ms, and the 10 ms after the join's first 10 ms, against the programme's level (the p90 over ±5 s;
  the 10 ms either side of the join are skipped — a hard cut's last sound rings that far through any band filter). This is what the viewer
  hears after the fades, the gain and the limiter. A join under a VO line, an sfx or a music cue is reported, not
  judged: that sound is meant to run across it, and the ear decides.

Whose sound plays: an event with native_audio_vol > 0 (the contract's default is muted). A builder whose takes ARE
the programme (a compilation of supplied clips, a person to camera) declares qc.native_programme: true in the EDL, or
pass --all-native. The read is of SOUND, not words: a knock or a burst an earned native bed is cut on by design reads
BITE too. finish_spot.py therefore stops the finish on a flag only under qc.native_programme, and only warns on an
earned bed; declare a meant cut in accepted_edges.

NOT READ (exit 2): an EDL that says nothing about whose sound plays — no qc.native_programme key, no event carrying a
native_audio_vol key — while a footage take carries an audio stream, or cannot be found (a short key in place of a path). Read as written it has no audible edge, so the gate
used to print PASS after reading nothing: one compilation's first cut read 0 edges and passed, where --all-native finds 6
BITE and 10 TIGHT, among them a word heard cut off at review (2026-10-22). Declare it either way: qc.native_programme
true (the takes ARE the programme) or false (every take's sound is muted), or native_audio_vol on the events. An EDL
from edl_build.py always carries native_audio_vol, so this fires only on a builder that never said.

A source that itself starts or ends mid-word (a supplied clip cut that way) cannot be repaired by a cut. Declare it on
the event as "accepted_edges": {"in": "<why>"}; it prints as INFO, and the operator hears about it once. A word's
tail carried as an sfx (the sfx file is the take, its src_in within a frame of the audible out) prints as INFO.

Word times (--transcripts <dir>: <take stem>.json, faster-whisper style segments[].words[] with start/end/word or
s/e/w) are printed beside each edge for orientation only. They never set a verdict.

The dB thresholds and read windows are leads from one job (video-production WHAT-VARIES § Leads from one job).
Re-measure them on the project's own takes when a verdict disagrees with the ear.

  edge_audit.py --root <project> --edl edit/<SPOT>-EDL.json [--cuts <cutlists.json>] [--transcripts <dir>] [--only ids] [--json <out>]
  edge_audit.py --root <project> --edl edit/<SPOT>-EDL.json --deliv deliver/<file>.mp4
  edge_audit.py --selftest
Exit 1 on any BITE or TIGHT, 2 on an unreadable input. Nothing is written except the --json report.
"""
import argparse, json, os, subprocess, sys, tempfile, wave
import numpy as np

SR = 16000; HOP = SR // 100          # 10 ms frames


def decode(path):
    r = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                       capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"cannot decode audio from {path}: {r.stderr.decode(errors='replace')[-200:]}")
    return np.frombuffer(r.stdout, np.float32).copy()


def envelope(x, band=(120.0, 7800.0)):
    """dB per 10 ms frame of the signal inside band: a zero-phase FFT band-pass with raised-cosine skirts (no ringing
    across an onset worth reading), then RMS per frame. Frame i covers [i/100, (i+1)/100) s."""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); lo, hi = band
    g = np.clip((f - (lo - 90)) / 120, 0, 1) * np.clip(((hi + 150) - f) / 300, 0, 1)   # wide skirts: a hard cut rings < 10 ms
    g = 0.5 - 0.5 * np.cos(np.pi * g)
    y = np.fft.irfft(X * g, len(x)); n = len(y) // HOP
    return 20 * np.log10(np.sqrt((y[:n * HOP].reshape(n, HOP).astype(np.float64) ** 2).mean(1)) + 1e-9)


def lvl(env, a, b):
    i0 = max(0, int(round(a * 100))); i1 = min(len(env), max(i0 + 1, int(round(b * 100))))
    return float(env[i0:i1].max()) if i1 > i0 else -120.0


def runs_below(env, thr, t0, t1, need=6):
    """the gaps (>= need frames under thr) inside [t0, t1) as [(start, end)] in seconds"""
    out = []; i0 = max(0, int(round(t0 * 100))); i1 = min(len(env), int(round(t1 * 100))); s = None
    for i in range(i0, i1):
        if env[i] < thr:
            s = i if s is None else s
        else:
            if s is not None and i - s >= need: out.append((s / 100, i / 100))
            s = None
    if s is not None and i1 - s >= need: out.append((s / 100, i1 / 100))
    return out


def words_for(tdir, take):
    if not tdir: return []
    p = os.path.join(tdir, os.path.splitext(os.path.basename(take))[0] + '.json')
    if not os.path.exists(p): return []
    out = []
    for s in json.load(open(p)).get('segments', []):
        for w in s.get('words', []):
            a, b = w.get('start', w.get('s')), w.get('end', w.get('e'))
            if a is not None and b is not None: out.append((float(a), float(b), str(w.get('word', w.get('w', ''))).strip()))
    return out


def declared(edl):
    """the EDL says whose sound plays: a qc.native_programme key (true or false), or a native_audio_vol key on an event"""
    return 'native_programme' in (edl.get('qc') or {}) or any('native_audio_vol' in x for x in edl.get('events') or [])


def has_audio(path):
    o = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', path],
                       capture_output=True, text=True).stdout
    return bool(o.strip())


def undeclared_sound(edl):
    """[event ids] whose take carries sound — or cannot be found, so nobody knows — in an EDL that never says whether any of
    it plays: the gate cannot judge. A take that is not a file (a project's short key in place of the path) counts."""
    if declared(edl): return []
    out = []; seen = {}
    for x in edl.get('events') or []:
        t = x.get('take')
        if not t or x.get('source') == 'designed' or x.get('role') == 'endcard': continue
        if not os.path.exists(t): out.append(f"{x['id']} (take not found: {t})"); continue
        if t not in seen: seen[t] = has_audio(t)
        if seen[t]: out.append(x['id'])
    return out


def plays(x, allnative):
    return bool(x.get('take')) and x.get('source') != 'designed' and (allnative or float(x.get('native_audio_vol', 0) or 0) > 0)


def read_edge(env, T, side, ref, quiet, speech):
    if side == 'out':
        e = lvl(env, T - 0.02, T)
        return e, None, ('BITE' if e > ref + speech else 'TIGHT' if e > quiet else 'ok')
    pre = lvl(env, T - 0.03, T) if T >= 0.03 else -120.0; e = lvl(env, T, T + 0.01)
    return e, pre, ('BITE' if pre > ref + speech and e > ref + speech else 'TIGHT' if e > quiet else 'ok')


def takes_mode(a, edl):
    allnative = a.all_native or bool((edl.get('qc') or {}).get('native_programme'))
    fps = float(edl.get('fps', 25)); cuts = json.load(open(a.cuts)) if a.cuts else {}
    sfx = (edl.get('audio') or {}).get('sfx') or []
    only = set(filter(None, a.only.split(','))); cache = {}; rows = []
    if not any(plays(x, allnative) for x in edl['events']):
        und = [] if a.all_native else undeclared_sound(edl); a.not_read = und
        if und:
            print(f"NOT READ {len(und)} footage event(s) whose take carries sound ({', '.join(und[:8])}{' …' if len(und) > 8 else ''}), and the EDL "
                  'never says whether it plays — declare qc.native_programme: true (the takes ARE the programme) or false (every take muted), '
                  'or native_audio_vol on the events; --all-native reads every edge now')
        else:
            print('INFO no event plays its take sound (native_audio_vol 0 everywhere, no qc.native_programme) — no edge to read; '
                  'a builder whose takes ARE the programme declares qc.native_programme: true')
    for x in edl['events']:
        if only and x['id'] not in only: continue
        if not plays(x, allnative): continue
        take = x['take']
        if not os.path.exists(take): print(f"FAIL {x['id']}: take missing {take}"); rows.append({'id': x['id'], 'verdict': 'MISSING'}); continue
        if take not in cache:
            env = envelope(decode(take), a.band); live = env[env > -100]
            cache[take] = (env, float(np.percentile(live, 10)) if len(live) else -100.0, words_for(a.transcripts, take))
        env, bed, words = cache[take]
        T_in = float(x.get('native_audio_from', x['in'])); T_out = float(x.get('native_audio_to', x['out']))
        w = env[int(round(T_in * 100)):int(round(T_out * 100))]
        ref = float(np.percentile(w, 90)) if len(w) else -60.0; quiet = max(ref + a.quiet_db, bed + a.bed_margin)
        for side, T in (('in', T_in), ('out', T_out)):
            e, pre, v = read_edge(env, T, side, ref, quiet, a.speech_db)
            r = {'id': x['id'], 'take': take, 'edge': side, 'T': round(T, 3), 'edge_db': round(e - ref, 1), 'verdict': v}
            if pre is not None: r['pre_db'] = round(pre - ref, 1)
            acc = (x.get('accepted_edges') or {}).get(side)
            car = side == 'out' and any(os.path.normpath(s.get('file', '')) == os.path.normpath(take) and s.get('src_in') is not None
                                        and abs(float(s['src_in']) - T) <= 1 / fps + 1e-6 for s in sfx)
            if v != 'ok' and car: r['verdict'] = 'CARRIED'
            elif v != 'ok' and acc: r['verdict'] = 'ACCEPT'; r['why'] = acc
            if r['verdict'] in ('BITE', 'TIGHT'):
                if side == 'out':
                    after = runs_below(env, quiet, T, T + 3.0); before = runs_below(env, quiet, max(0, T - 3.0), T)
                    r['sound_ends'] = after[0][0] if after else None; r['gap_before'] = before[-1] if before else None
                    r['fix'] = (f"the sound runs to {r['sound_ends']} s" + (f"; the last gap before the edge is {before[-1][0]:.2f}-{before[-1][1]:.2f} s" if before else '')
                                + " — move the edge into a gap, or carry the tail as an sfx over the next event")
                else:
                    before = runs_below(env, quiet, max(0, T - 3.0), T); after = runs_below(env, quiet, T, T + 3.0)
                    r['sound_starts'] = before[-1][1] if before else None; r['gap_after'] = after[0] if after else None
                    r['fix'] = (f"the sound starts at {r['sound_starts']} s" + (f"; the next gap after the edge is {after[0][0]:.2f}-{after[0][1]:.2f} s" if after else '')
                                + " — move the edge into a gap before the word (or after it), or fade over room tone, never over a word")
            near = [c for c in cuts.get(take, []) if abs(c - T) <= 1.5]
            ww = [f"{t}[{s:.2f}-{e_:.2f}]" for s, e_, t in words if s - 0.4 < T < e_ + 0.4]
            line = (f"{r['verdict']:7s} {x['id']:6s} {side:3s} {T:9.3f}  edge {r['edge_db']:+6.1f} dB" + (f" pre {r['pre_db']:+6.1f}" if 'pre_db' in r else '')
                    + (f"  cuts {near}" if near else '') + (f"  | words (orientation only): {' '.join(ww)}" if ww else ''))
            print(line, flush=True)
            if 'fix' in r: print(f"        fix: {r['fix']}", flush=True)
            if r['verdict'] == 'ACCEPT': print(f"        accepted: {acc}", flush=True)
            rows.append(r)
    return rows


def deliv_mode(a, edl):
    allnative = a.all_native or bool((edl.get('qc') or {}).get('native_programme'))
    env = envelope(decode(a.deliv), a.band); evs = edl['events']; au = edl.get('audio') or {}
    spans = [(f"vo {v.get('line', v.get('file', '?'))}", float(v['at']), float(v['at']) + float(v.get('dur', 0))) for v in au.get('vo', []) if isinstance(v, dict) and 'at' in v and v.get('dur')]
    spans += [(f"sfx {os.path.basename(s.get('file', '?'))}", float(s['at']), float(s['at']) + float(s.get('dur', 0))) for s in au.get('sfx', []) if 'at' in s and s.get('dur')]
    spans += [(f"music {os.path.basename(str(m.get('file', '?')))}", float(m['tl'][0]), float(m['tl'][1])) for m in au.get('music', []) if m.get('tl')]
    rows = []
    if not any(plays(x, allnative) for x in evs):
        und = [] if a.all_native else undeclared_sound(edl); a.not_read = und
        if und:
            print(f"NOT READ {len(und)} footage event(s) whose take carries sound ({', '.join(und[:8])}{' …' if len(und) > 8 else ''}), and the EDL "
                  'never says whether it plays — declare qc.native_programme: true (the takes ARE the programme) or false (every take muted), '
                  'or native_audio_vol on the events; --all-native reads every edge now')
        else:
            print('INFO no event plays its take sound (native_audio_vol 0 everywhere, no qc.native_programme) — no join to read; '
                  'a builder whose takes ARE the programme declares qc.native_programme: true')
    for e0, e1 in zip(evs, evs[1:]):
        J = float(e1['tl'][0]); sides = []
        if plays(e0, allnative) and float(e0.get('native_audio_to', e0['out'])) >= float(e0['out']) - 1e-6: sides.append(('out', e0))
        if plays(e1, allnative) and float(e1.get('native_audio_from', e1['in'])) <= float(e1['in']) + 1e-6: sides.append(('in', e1))
        if not sides: continue
        mm = f"{int(J // 60):02d}:{J % 60:05.2f}"
        cov = [n for n, s0, s1 in spans if s0 < J - 0.05 and s1 > J + 0.05]
        if cov: print(f"COVERED {mm}  {e0['id']}|{e1['id']}  under {', '.join(cov)} — listen"); rows.append({'J': J, 'verdict': 'COVERED', 'by': cov}); continue
        ref = float(np.percentile(env[max(0, int((J - 5) * 100)):int((J + 5) * 100)], 90)); out = []; flag = 'ok'
        for side, x in sides:
            d = (lvl(env, J - 0.03, J - 0.01) if side == 'out' else lvl(env, J + 0.01, J + 0.02)) - ref
            v = 'ok' if d <= a.quiet_db else ('BITE' if d > a.speech_db else 'TIGHT')
            if v != 'ok' and (x.get('accepted_edges') or {}).get(side): v = 'ACCEPT'
            out.append(f"{x['id']} {side} {d:+6.1f} dB {v}"); rows.append({'J': J, 'id': x['id'], 'edge': side, 'db': round(d, 1), 'verdict': v})
            flag = 'FAIL' if v in ('BITE', 'TIGHT') else ('ACCEPT' if v == 'ACCEPT' and flag == 'ok' else flag)
        print(f"{flag:7s} {mm}  {e0['id']:>6s}|{e1['id']:<6s}  " + '   '.join(out), flush=True)
    return rows


# ------------------------------------------------------------------ known answers
def _wav(path, x, sr):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())


def selftest():
    """a synthetic take of voiced 'words' (harmonic bursts) and one sibilant tail (4.5-7.5 kHz noise) on a -60 dB bed;
    every verdict below is known by construction"""
    sr = 48000; rng = np.random.default_rng(7); t = np.arange(int(4.0 * sr)) / sr
    x = rng.standard_normal(len(t)) * 0.001

    def voiced(a, b):
        m = (t >= a) & (t < b); tt = t[m] - a
        env = np.minimum(1, tt / 0.01) * np.minimum(1, (b - a - tt) / 0.02)
        x[m] += 0.35 * env * sum(np.sin(2 * np.pi * 150 * k * tt) / k for k in range(1, 21)) / 1.5

    def sibilant(a, b):
        n = rng.standard_normal(len(t)); X = np.fft.rfft(n); f = np.fft.rfftfreq(len(n), 1 / sr)
        X[(f < 4500) | (f > 7500)] = 0; s = np.fft.irfft(X, len(n)); s /= s.std() + 1e-12
        m = (t >= a) & (t < b); x[m] += 0.08 * s[m]
    voiced(0.30, 0.70); sibilant(0.70, 0.80)          # word A ends on its 'st'
    voiced(1.10, 1.50); voiced(1.80, 2.30); voiced(2.60, 3.00)
    d = tempfile.mkdtemp(prefix='edge_audit_selftest_'); take = os.path.join(d, 'take.wav'); _wav(take, x, sr)
    ev = lambda i, a_, b_, **k: dict({'id': i, 'take': take, 'in': a_, 'out': b_, 'native_audio_vol': 1.0}, **k)
    edl = {'fps': 25, 'events': [
        ev('S_TAIL', 0.30, 0.76), ev('GAP', 0.30, 0.95), ev('MIDWORD', 0.95, 1.30), ev('IN_MID', 1.30, 1.65),
        ev('IN_ONSET', 1.10, 1.65), ev('IN_GAP', 1.65, 2.45), ev('ACC', 0.95, 1.30, accepted_edges={'out': 'test'}),
        ev('CARRY', 1.65, 2.05), dict(ev('MUTED', 0.95, 1.30), native_audio_vol=0)],
        'audio': {'sfx': [{'file': take, 'at': 9.0, 'dur': 0.3, 'src_in': 2.05}]}}
    want = {('S_TAIL', 'out'): {'BITE', 'TIGHT'}, ('GAP', 'out'): {'ok'}, ('MIDWORD', 'out'): {'BITE'}, ('IN_MID', 'in'): {'BITE'},
            ('IN_ONSET', 'in'): {'TIGHT'}, ('IN_GAP', 'in'): {'ok'}, ('ACC', 'out'): {'ACCEPT'}, ('CARRY', 'out'): {'CARRIED'}}
    ns = argparse.Namespace(all_native=False, cuts='', only='', transcripts='', band=(120.0, 7800.0), speech_db=-15.0, quiet_db=-22.0, bed_margin=6.0)
    print('-- takes mode'); rows = takes_mode(ns, edl); got = {(r['id'], r['edge']): r['verdict'] for r in rows if 'edge' in r}
    bad = [f"{k}: {got.get(k)} (want {sorted(v)})" for k, v in want.items() if got.get(k) not in v]
    if any(r['id'] == 'MUTED' for r in rows): bad.append('MUTED: a muted take was read')
    ns_band = argparse.Namespace(**{**vars(ns), 'band': (200.0, 4000.0)})
    print('-- the same tail in a 200-4000 Hz band (must miss it: the reason the default band is wide)')
    rb = takes_mode(ns_band, {'fps': 25, 'events': [ev('S_TAIL', 0.30, 0.76)]})
    if [r['verdict'] for r in rb if r['edge'] == 'out'] != ['ok']: bad.append('the speech band read the sibilant tail — the band known answer moved')
    # the delivered file: e0 cut mid-word B (a bitten join), e1 opens and closes in gaps, e2 opens in a gap
    seg = lambda a_, b_: x[int(a_ * sr):int(b_ * sr)]
    dl = np.concatenate([seg(0.30, 1.30), seg(1.65, 2.45), seg(2.55, 3.20)]); deliv = os.path.join(d, 'deliv.wav'); _wav(deliv, dl, sr)
    dedl = {'fps': 25, 'events': [ev('D0', 0.30, 1.30, tl=[0.0, 1.0]), ev('D1', 1.65, 2.45, tl=[1.0, 1.8]), ev('D2', 2.55, 3.20, tl=[1.8, 2.45])]}
    print('-- deliv mode'); rd = deliv_mode(argparse.Namespace(**{**vars(ns), 'deliv': deliv}), dedl)
    dv = {(r['id'], r['edge']): r['verdict'] for r in rd if 'edge' in r}
    for k, v in {('D0', 'out'): 'BITE', ('D1', 'in'): 'ok', ('D1', 'out'): 'ok', ('D2', 'in'): 'ok'}.items():
        if dv.get(k) != v: bad.append(f"deliv {k}: {dv.get(k)} (want {v})")
    # 0 read: undeclared + a take with sound = NOT READ; declared muted = an honest 0; a take with no audio stream = an honest 0
    sil = os.path.join(d, 'silent.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=32x32:r=25:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', sil], check=True)
    und = {'fps': 25, 'events': [{'id': 'U', 'take': take, 'in': 0.3, 'out': 0.76, 'tl': [0, 0.46]}]}
    for label, e_, want_nr in (('undeclared, the take has sound', und, ['U']),
                               ('qc.native_programme false', {**und, 'qc': {'native_programme': False}}, []),
                               ('native_audio_vol 0 on the event', {'fps': 25, 'events': [{**und['events'][0], 'native_audio_vol': 0}]}, []),
                               ('undeclared, the take has no audio stream', {'fps': 25, 'events': [{**und['events'][0], 'take': sil}]}, []),
                               ('undeclared, the take is a short key, not a file', {'fps': 25, 'events': [{**und['events'][0], 'take': 'clip07'}]}, ['U (take not found: clip07)'])):
        n0 = argparse.Namespace(**vars(ns)); r0 = takes_mode(n0, e_)
        if r0 or getattr(n0, 'not_read', []) != want_nr: bad.append(f"0-read case '{label}': read {len(r0)}, not_read {getattr(n0, 'not_read', None)} (want {want_nr})")
    n0 = argparse.Namespace(**{**vars(ns), 'all_native': True}); takes_mode(n0, und)
    if getattr(n0, 'not_read', None): bad.append('--all-native must read, never NOT READ')
    os.remove(sil)
    for k in ('take.wav', 'deliv.wav'): os.remove(os.path.join(d, k))
    os.rmdir(d)
    print('SELFTEST ' + ('PASS' if not bad else 'FAIL\n  ' + '\n  '.join(bad)))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl', default='')
    ap.add_argument('--deliv', default='', help='read the delivered file at every join instead of the takes')
    ap.add_argument('--cuts', default='', help='{"<take path>": [cut seconds]} (video-take-review qc_seed.py) — printed beside a flagged edge')
    ap.add_argument('--transcripts', default='', help='dir of <take stem>.json word times — printed for orientation, never a verdict')
    ap.add_argument('--only', default=''); ap.add_argument('--json', default='')
    ap.add_argument('--all-native', action='store_true', help='every footage event plays its take sound (same as qc.native_programme in the EDL)')
    ap.add_argument('--band', default='120,7800', help='the envelope band in Hz (default 120,7800: the sibilant tail sits above 4 kHz)')
    ap.add_argument('--speech-db', type=float, default=-15.0, help='within this of the p90 = speech level (lead from one job)')
    ap.add_argument('--quiet-db', type=float, default=-22.0, help='under this re the p90 = quiet (lead from one job)')
    ap.add_argument('--bed-margin', type=float, default=6.0, help="or the take's own bed (p10) + this, whichever is higher")
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    if not a.edl: ap.error('--edl is required (or --selftest)')
    a.band = tuple(float(v) for v in a.band.split(','))
    os.chdir(a.root)
    try:
        edl = json.load(open(a.edl))
        rows = deliv_mode(a, edl) if a.deliv else takes_mode(a, edl)
    except (OSError, RuntimeError, ValueError) as ex:
        print(f'EDGE-AUDIT UNREADABLE — {ex}'); sys.exit(2)
    if a.json: json.dump(rows, open(a.json, 'w'), indent=1)
    what = f"{a.deliv} at every join" if a.deliv else f"{a.edl} takes"
    if getattr(a, 'not_read', None):
        print(f"EDGE-AUDIT NOT READ {what}: 0 read — {len(a.not_read)} footage event(s) carry sound the EDL never declares (above); a 0-read pass is no pass")
        sys.exit(2)
    n = {v: sum(1 for r in rows if r.get('verdict') == v) for v in ('BITE', 'TIGHT', 'ACCEPT', 'CARRIED', 'COVERED', 'MISSING')}
    print(f"EDGE-AUDIT {'FAIL' if n['BITE'] or n['TIGHT'] or n['MISSING'] else 'PASS'} {what}: {len(rows)} read · {n['BITE']} BITE · {n['TIGHT']} TIGHT · "
          f"{n['ACCEPT']} accepted · {n['CARRIED']} carried · {n['COVERED']} covered (listen)")
    sys.exit(1 if n['BITE'] or n['TIGHT'] or n['MISSING'] else 0)


if __name__ == '__main__':
    main()
