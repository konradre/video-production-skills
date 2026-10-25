#!/usr/bin/env python3
"""edl_insert.py — insert (or re-time) one event in an EDL and shift everything downstream by its duration: the
events after the anchor, post_layers.at, audio.vo.*.at, audio.sfx.*.at, audio.music.*.tl, runtime_s. A music cue that
SPANS the insertion point keeps playing under the insert (only its end moves). An sfx with a `sync` moves with its event,
wherever it starts (a riser starts before its hit); a suck-out duck ending on the insertion point moves whole with the hit
when its cue plays on past it, and stays with a cue that ENDS there (a WARN: re-cut that cue to the moved hit); an insert
that would leave a duck outside its cue writes nothing. A second run with --replace re-times an
existing insert (the previous shift is undone first). Writes <edl>.bak-<ts>-pre-insert beside the EDL first.

  edl_insert.py --root <project> --edl edit/<SPOT>-EDL.json --after <EVENT-ID> --id <NEW-ID> --take takes/<take>.mp4
                --in 0.4 --out 3.6 [--src edit/hero/<...>.mov] [--native-vol 0.8] [--note ...] [--replace] [--handle <s>]

handle_head defaults to IN: the finisher seeks a generated source by handle_head (where the in-point sits inside the
source), so a FULL-TAKE hero (take -> upscale -> hero pass, untrimmed) needs handle_head == in. Pass --handle only for a
source pre-trimmed to (in - handle). Writing 0.0 regardless of in shipped four versions of a spot 0.3 s late.
Times are rounded to 1/1000 s; tl spans stay == out - in.
"""
import argparse, json, os, shutil, sys, time


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl', required=True); ap.add_argument('--after', required=True)
    ap.add_argument('--id', required=True); ap.add_argument('--take', required=True)
    ap.add_argument('--in', dest='tin', type=float, required=True); ap.add_argument('--out', dest='tout', type=float, required=True)
    ap.add_argument('--src', help='pre-graded hero for the event; default: --src-pattern with {id}/{stem}')
    ap.add_argument('--src-pattern', default='edit/hero/{id}__rhea-1x4__ads-clean.mov')
    ap.add_argument('--native-vol', type=float, default=0.8); ap.add_argument('--note'); ap.add_argument('--replace', action='store_true')
    ap.add_argument('--handle', type=float, help='head handle inside a PRE-TRIMMED source; default = in (full-take hero)')
    a = ap.parse_args(); os.chdir(a.root)
    dur = round(a.tout - a.tin, 3); assert dur > 0, 'out must exceed in'
    e = json.load(open(a.edl, encoding='utf-8')); ev = e['events']; au = e['audio']
    r = lambda x: round(x, 3)

    def shift(t0, d):
        for x in ev:
            if x['tl'][0] >= t0 - 1e-6: x['tl'] = [r(x['tl'][0] + d), r(x['tl'][1] + d)]
        for L in e.get('post_layers', []):
            if L['at'] >= t0 - 1e-6: L['at'] = r(L['at'] + d)
        for v in au.get('vo', {}).values():
            if isinstance(v, dict) and 'at' in v and v['at'] >= t0 - 1e-6: v['at'] = r(v['at'] + d)
        mk = e.get('markers', {})
        for v in au.get('sfx', {}).values():
            if not (isinstance(v, dict) and v.get('at') is not None): continue
            sy = v.get('sync') or {}; ev_ = mk.get(sy.get('event')) if isinstance(sy.get('event'), str) else sy.get('event')
            if isinstance(ev_, (int, float)):   # a synced sound moves with the event it belongs to, wherever it starts (a riser starts before its hit)
                if ev_ >= t0 - 1e-6:
                    v['at'] = r(v['at'] + d)
                    if not isinstance(sy.get('event'), str): sy['event'] = r(ev_ + d)
            elif v['at'] >= t0 - 1e-6: v['at'] = r(v['at'] + d)
        for v in au.get('music', {}).values():
            if isinstance(v, dict) and 'tl' in v:
                s, t = v['tl']; v['tl'] = [r(s + d) if s >= t0 - 1e-6 else s, r(t + d) if t > t0 + 1e-6 else t]   # a spanning cue keeps playing
                if v.get('duck'):   # a ramp travels with its duck; a suck-out (gain <= 0.1, 0.2-0.7 s) ending on the insertion point moves whole
                    # with the hit it clears — when its cue plays on past that point. A cue that ENDS there (a before-cue cut to the hit) keeps
                    # its suck-out with it: that cue must be re-cut to the moved hit, and the WARN says so
                    so = lambda dk: float(dk[2]) <= 0.1 and 0.2 <= dk[1] - dk[0] <= 0.7 and abs(dk[1] - t0) <= 1e-6 and t > t0 + 1e-6
                    if any(float(dk[2]) <= 0.1 and 0.2 <= dk[1] - dk[0] <= 0.7 and abs(dk[1] - t0) <= 1e-6 for dk in v['duck']) and abs(t - t0) <= 1e-6:
                        print(f"WARN music cue ends on the insertion point {t0} with its suck-out: both stay; the hit moved {d:+.3f} s, so re-cut the cue (and its suck-out) to the new hit", flush=True)
                    v['duck'] = [[r(dk[0] + d), r(dk[1] + d), *dk[2:]] if so(dk) else
                                 [r(dk[0] + d) if dk[0] >= t0 - 1e-6 else dk[0], r(dk[1] + d) if dk[1] > t0 + 1e-6 else dk[1], *dk[2:]] for dk in v['duck']]
        for k, v in e.get('markers', {}).items():   # absolute markers move with the picture they sit on
            if isinstance(v, (int, float)) and v >= t0 - 1e-6: e['markers'][k] = r(v + d)
        e['runtime_s'] = r(float(e['runtime_s']) + d)

    anchor = [x for x in ev if x['id'] == a.after]; assert len(anchor) == 1, f'anchor {a.after} not found'
    existing = [x for x in ev if x['id'] == a.id]
    if existing:
        assert a.replace, f'{a.id} already in the EDL — pass --replace to re-time it'
        old = existing[0]; od = r(old['tl'][1] - old['tl'][0]); ev.remove(old); shift(old['tl'][0] + od, -od)   # undo the previous shift
    t0 = anchor[0]['tl'][1]; shift(t0, dur)
    stem = os.path.splitext(os.path.basename(a.take))[0]
    ins = {'id': a.id, 'take': a.take, 'in': a.tin, 'out': a.tout, 'tl': [r(t0), r(t0 + dur)], 'handle_head': a.handle if a.handle is not None else a.tin,
           'native_audio_vol': a.native_vol, 'look': 'none', 'src': a.src or a.src_pattern.format(id=a.id, stem=stem),
           'note': a.note or f'insert after {a.after}, trimmed {a.tin}->{a.tout} of the take'}
    ev.insert(ev.index(anchor[0]) + 1, ins)
    bad = [f"music {k}: duck {dk} now lies outside the cue {v['tl']}" for k, v in au.get('music', {}).items() if isinstance(v, dict) and 'tl' in v
           for dk in v.get('duck', []) if not (v['tl'][0] - 1e-6 <= dk[0] < dk[1] <= v['tl'][1] + 1e-6)]
    if bad: sys.exit('NOT WRITTEN — the insert would leave a duck outside its cue (a suck-out moved with its hit past the cue\'s end): '
                     + '; '.join(bad) + ' — extend that cue past the hit first (a longer excerpt), then insert')
    shutil.copy(a.edl, f"{a.edl}.bak-{time.strftime('%Y%m%d-%H%M%S')}-pre-insert")
    json.dump(e, open(a.edl, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(f"inserted {a.id} at tl {ins['tl']} ({dur} s); runtime {e['runtime_s']} s")
    for x in ev: print(f"  {x['id']:10s} tl {x['tl'][0]:7.3f}–{x['tl'][1]:7.3f}")
    print('  vo', {k: v['at'] for k, v in au.get('vo', {}).items() if isinstance(v, dict) and 'at' in v})
    print('  sfx', {k: v.get('at') for k, v in au.get('sfx', {}).items() if isinstance(v, dict)})
    print('  music', {k: v['tl'] for k, v in au.get('music', {}).items() if isinstance(v, dict) and 'tl' in v})


if __name__ == '__main__':
    main()
