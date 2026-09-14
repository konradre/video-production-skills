#!/usr/bin/env python3
"""edl_build.py — build an EDL by DERIVATION from a plan: an ordered event list (keeper = take + in + out) plus audio
and layer entries whose times are written as REFERENCES (a marker, an event edge, another line's edge), never as typed
numbers. Every timeline position is computed here, so re-running the same plan reproduces the EDL and an editorial note
becomes a change to the plan, not a hand edit of a time.

  edl_build.py --root <project> --plan edit/<SPOT>-plan.json --out edit/<SPOT>-EDL.json [--beats prompts/<SPOT>-beats.json]
               [--stamp-derived] [--allow-stale-derived]

Plan (full field list: references/EDL-CONTRACT.md § The plan):
  events[]    {id, take, in, out, src?, look?, source?, role?, vol?, native_from?, native_to?, zoom?, anchor?,
               accepted_cuts?, accepted_cuts_note?, note}
              a generated event without src gets hero_pattern.format(stem=<take stem>, id=<id>) and look "none"
              (pre-graded hero); a "designed" event keeps its own look and never gets a src; the card is role "endcard".
              accepted_cuts = take seconds of cuts inside the window that the take COMPOSED and the operator kept.
  markers     {NAME: {event, take}} — MEASURED on the keeper (an RMS peak, a word onset), never guessed.
  vo / sfx    at = a time ref;  music tl = [ref, ref];  post_layers at = ref.
              a vo line may carry source (a TTS job id, a clone id, extracted_from: <path> @ <s>), lip_synced, floor_ok.
  time ref    number | "start" | "end" | "<MARKER>" | "<EVENT-ID>" (its tl start) | "<EVENT-ID>.end"
              | {"marker": M, "offset": s} | {"event": E, "take": s} (a take time inside E)
              | {"event_start"|"event_end": E, "offset": s}
              | {"before_vo": L, "gap": s}  this entry ENDS gap s before line L starts
              | {"after_vo": L, "gap": s}   this entry starts gap s after line L ends
              | {"vo_ends_before": M, "gap": s}  this entry ENDS gap s before marker M (floored to the frame)
  derived     any entry may carry {"derived": {"from": [files], "method": "...", "sha256": {file: hash}}} beside a number
              MEASURED from files (a bed vol, a duck gain, a lip-synced at, a loudness target). Every input is re-hashed
              on every build and a changed input FAILS it (--allow-stale-derived builds anyway, loudly). --stamp-derived
              records the hash of each input that has none — right after measuring, never to silence a FAIL.
Writes <out>.bak-<ts>-pre-build first when <out> exists. With --beats, that file's markers are rewritten to the plan's
so the gate stays in step with the picks (a marker moves with the take it was measured on).
"""
import argparse, glob, hashlib, json, math, os, shutil, subprocess, sys, time


def probe(p):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], capture_output=True, text=True).stdout or 0)


def first(pat):
    """the finisher's file rule: 'a|b' alternatives, each a glob; the first that exists wins"""
    for p in (pat or '').split('|'):
        g = sorted(glob.glob(p))
        if g: return g[0]
    return None


def lufs(p):
    out = subprocess.run(['ffmpeg', '-v', 'info', '-nostats', '-i', p, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    for line in out.splitlines()[::-1]:
        if line.strip().startswith('I:'): return float(line.split()[1])
    return None


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def derived_blocks(node, where='plan'):
    """every {"derived": {...}} block in the plan, with the path of the entry that carries it"""
    if isinstance(node, dict):
        if isinstance(node.get('derived'), dict): yield where, node['derived']
        for k, v in node.items():
            if k != 'derived': yield from derived_blocks(v, f'{where}.{k}')
    elif isinstance(node, list):
        for i, v in enumerate(node): yield from derived_blocks(v, f'{where}[{i}]')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--plan', required=True); ap.add_argument('--out', required=True); ap.add_argument('--beats')
    ap.add_argument('--no-lufs', action='store_true', help='skip the ebur128 read of each VO file (the stem builder needs lufs; skip only for a dry layout)')
    ap.add_argument('--stamp-derived', action='store_true', help='record the sha256 of every derived input that has none (right after measuring)')
    ap.add_argument('--allow-stale-derived', action='store_true', help="build even when a derived constant's input changed (every stale input is printed)")
    a = ap.parse_args(); os.chdir(a.root)
    P = json.load(open(a.plan, encoding='utf-8')); fps = float(P.get('fps', 24)); F = 1 / fps
    # ---- derived constants: a number measured from files is only as current as those files ----
    stale, unstamped, stamped = [], [], 0
    for where, d in derived_blocks(P):
        hs = d.setdefault('sha256', {}) if a.stamp_derived else d.get('sha256', {})
        for f in d.get('from', []):
            if not os.path.exists(f): stale.append(f'{where}: input missing {f}'); continue
            cur = sha256(f)
            if f not in hs:
                if a.stamp_derived: hs[f] = cur; stamped += 1
                else: unstamped.append(f'{where}: {f}')
            elif hs[f] != cur: stale.append(f"{where}: {f} changed since the constant was derived ({d.get('method', 'no method recorded')})")
    if stamped:
        shutil.copy(a.plan, f"{a.plan}.bak-{time.strftime('%Y%m%d-%H%M%S')}-pre-stamp"); json.dump(P, open(a.plan, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print(f'stamped {stamped} derived input hash(es) into {a.plan}', flush=True)
    for u in unstamped: print(f'WARN derived constant not stamped: {u} — --stamp-derived records the inputs as they are NOW', flush=True)
    for s in stale: print(f"{'WARN' if a.allow_stale_derived else 'FAIL'} STALE {s}", flush=True)
    if stale and not a.allow_stale_derived: sys.exit('derived constants are STALE — re-measure them from the current inputs, then re-stamp; nothing was built')
    fr = lambda x: round(round(x / F) * F, 6); fl = lambda x: round(math.floor(x / F + 1e-6) * F, 6)
    hero = P.get('hero_pattern', 'edit/hero/{stem}__rhea-1x4__ads-clean.mov'); dlook = P.get('default_look', 'ads-clean')
    # ---- events: tl accumulates; nothing is typed ----
    t = 0.0; events = []; tl = {}; EIN = {}
    for ev in P['events']:
        i0, o0 = fr(float(ev['in'])), fr(float(ev['out'])); assert o0 > i0, (ev['id'], 'out must exceed in')
        x = {'id': ev['id'], 'take': ev['take'], 'in': i0, 'out': o0, 'handle_head': fr(float(ev.get('handle_head', i0))), 'note': ev.get('note', '')}
        if ev.get('source') == 'designed':
            x['source'] = 'designed'; x['look'] = ev.get('look', dlook)
            if ev.get('role'): x['role'] = ev['role']
        else:
            stem = os.path.splitext(os.path.basename(ev['take']))[0]
            x['src'] = ev.get('src') or hero.format(stem=stem, id=ev['id']); x['look'] = ev.get('look', 'none'); x['native_audio_vol'] = float(ev.get('vol', 1.0))
            for k in ('native_from', 'native_to'):
                if ev.get(k) is not None: x['native_audio_' + k.split('_')[1]] = float(ev[k])
            if ev.get('zoom'): x['zoom'] = float(ev['zoom']); x['anchor'] = ev.get('anchor', [0.5, 0.5])
            if ev.get('accepted_cuts'): x['accepted_cuts'] = [round(float(c), 3) for c in ev['accepted_cuts']]; x['accepted_cuts_note'] = ev.get('accepted_cuts_note', '')
        d = o0 - i0; t1 = round(t + d, 6); x['tl'] = [t, t1]; tl[ev['id']] = x['tl']; EIN[ev['id']] = i0; t = t1; events.append(x)
    RUN = t
    markers = {}
    for name, m in P.get('markers', {}).items():
        assert m['event'] in tl, (name, 'marker on an event not in the plan'); markers[name] = round(tl[m['event']][0] + float(m['take']) - EIN[m['event']], 6)
    vo_out = {}; vo_dur = {}

    def resolve(ref, self_dur=None, who=''):
        if isinstance(ref, (int, float)): return float(ref)
        if isinstance(ref, str):
            if ref == 'start': return 0.0
            if ref == 'end': return RUN
            if ref in markers: return markers[ref]
            if ref in tl: return tl[ref][0]
            if ref.endswith('.end') and ref[:-4] in tl: return tl[ref[:-4]][1]
            sys.exit(f'{who}: unknown time ref {ref!r} (not a marker, not an event id)')
        off = float(ref.get('offset', 0)); gap = float(ref.get('gap', 0))
        if 'marker' in ref: return markers[ref['marker']] + off
        if 'event' in ref and 'take' in ref: return tl[ref['event']][0] + float(ref['take']) - EIN[ref['event']] + off
        if 'event_start' in ref: return tl[ref['event_start']][0] + off
        if 'event_end' in ref: return tl[ref['event_end']][1] + off
        if 'before_vo' in ref:
            L = ref['before_vo']; assert L in vo_out, ('PENDING', L); assert self_dur is not None, f'{who}: before_vo needs a duration'
            return vo_out[L]['at'] - gap - self_dur
        if 'after_vo' in ref:
            L = ref['after_vo']; assert L in vo_out, ('PENDING', L); return vo_out[L]['at'] + vo_dur[L] + gap
        if 'vo_ends_before' in ref:
            assert self_dur is not None, f'{who}: vo_ends_before needs a duration'; return fl(markers[ref['vo_ends_before']] - gap - self_dur)
        sys.exit(f'{who}: unreadable time ref {ref}')

    # ---- VO: resolve in dependency order (a line placed before/after another line waits for it) ----
    V = P.get('vo', {}); lines = {k: v for k, v in V.items() if isinstance(v, dict) and 'file' in v}; scal = {k: v for k, v in V.items() if k not in lines}
    for k, v in lines.items(): vo_dur[k] = round(probe(v['file']), 3)
    for k, v in lines.items():   # a lip-synced line sits where its take's own audio says, and moves when its file changes
        if v.get('lip_synced') and not (isinstance(v['at'], dict) and 'event' in v['at'] and 'take' in v['at']):
            print(f"WARN vo {k}: lip_synced but its at is not an {{event, take}} ref — a lip-synced line sits at its take's time", flush=True)
        if v.get('lip_synced') and v['file'] not in (v.get('derived') or {}).get('from', []):
            print(f"WARN vo {k}: lip_synced with no derived stamp on its file — swapping the file will not invalidate the measured at", flush=True)
    pending = dict(lines)
    for _ in range(len(lines) + 1):
        for k, v in list(pending.items()):
            try: at = resolve(v['at'], vo_dur[k], f'vo {k}')
            except AssertionError as ex:
                if ex.args and ex.args[0] == 'PENDING': continue
                raise
            vo_out[k] = {'file': v['file'], 'at': fr(at) if not (isinstance(v['at'], dict) and 'vo_ends_before' in v['at']) else at, 'text': v.get('text', ''),
                         'lufs': None if a.no_lufs else lufs(v['file']), 'dur': vo_dur[k], 'note': v.get('note', ''),
                         **{q: v[q] for q in ('source', 'lip_synced', 'floor_ok', 'derived') if q in v}}
            del pending[k]
        if not pending: break
    assert not pending, f'VO lines never resolved (a cycle or a missing line): {sorted(pending)}'
    vo = {**scal, **vo_out}
    # ---- music / sfx / layers ----
    music = {}
    for k, m in P.get('music', {}).items():
        s, e2 = resolve(m['tl'][0], who=f'music {k}'), resolve(m['tl'][1], who=f'music {k}'); assert e2 > s, (k, 'empty cue span')
        music[k] = {'file': m['file'], 'tl': [round(s, 6), round(e2, 6)], 'vol': m.get('vol', 0.7), **{q: m[q] for q in ('fade_in', 'fade_out', 'duck', 'duck_ramp', 'derived') if q in m}, 'note': m.get('note', '')}
        if m.get('duck'): music[k]['duck'] = [[round(resolve(da, who=k), 6), round(resolve(db, who=k), 6), g] for da, db, g in m['duck']]
        f = first(m['file'])
        if f and probe(f) + 1e-3 < e2 - s: print(f'WARN music {k}: {f} is {probe(f):.2f} s < span {e2 - s:.2f} s — the cue just ENDS; cut a longer excerpt', flush=True)
    sfx = {}
    for k, s in P.get('sfx', {}).items():
        f = first(s['file'])
        sfx[k] = {'file': s['file'], 'at': round(resolve(s['at'], who=f'sfx {k}'), 6), 'dur': s.get('dur') if s.get('dur') is not None else (round(probe(f), 3) if f else None),
                  'vol': s.get('vol', 1.0), **{q: s[q] for q in ('src_in', 'alt') if q in s}, 'note': s.get('note', '')}
    layers = [{'id': L['id'], 'frames': L['frames'], 'at': round(resolve(L['at'], who=L['id']), 6), 'dur': float(L['dur']), 'note': L.get('note', '')} for L in P.get('post_layers', [])]
    au = {'vo': vo, 'music': music, 'sfx': sfx, 'captions': P.get('captions', []), 'loudnorm': P.get('loudnorm', {'I': -14, 'TP': -1, 'LRA': 9})}
    for q in ('captions_dir', 'word_times', 'caption_style', 'silence'):
        if q in P: au[q] = P[q]
    edl = {'spot': P['spot'], 'deliver_base': P.get('deliver_base', P['spot']), 'version': P.get('version', '1.0'), 'fps': fps, 'canvas': P.get('canvas', [1080, 1920]),
           'runtime_s': RUN, 'source': P.get('source', f'built by edl_build.py from {a.plan}'), 'events': events, 'post_layers': layers, 'audio': au,
           'grade_note': P.get('grade_note', ''), 'source_script': P.get('source_script', ''), 'markers': markers}
    if a.beats:
        B = json.load(open(a.beats, encoding='utf-8'))
        B['markers'] = {n: {'event': m['event'], 'take': float(m['take']), '_note': m.get('_note', 'rewritten by edl_build.py from the plan')} for n, m in P.get('markers', {}).items()}
        shutil.copy(a.beats, f"{a.beats}.bak-{time.strftime('%Y%m%d-%H%M%S')}-pre-build"); json.dump(B, open(a.beats, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    if os.path.exists(a.out): shutil.copy(a.out, f"{a.out}.bak-{time.strftime('%Y%m%d-%H%M%S')}-pre-build")
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True); json.dump(edl, open(a.out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(f'{a.out} v{edl["version"]} runtime {RUN}')
    for x in events: print(f"  {x['tl'][0]:7.3f}–{x['tl'][1]:7.3f} {x['id']:10} {os.path.basename(x['take']):30} take {x['in']:.3f}–{x['out']:.3f}")
    print('  markers', markers); print('  vo', {k: v['at'] for k, v in vo_out.items()}); print('  music', {k: v['tl'] for k, v in music.items()})
    print('  sfx', {k: v['at'] for k, v in sfx.items()}); print('  layers', {L['id']: L['at'] for L in layers})


if __name__ == '__main__':
    main()
