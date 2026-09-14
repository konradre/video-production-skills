#!/usr/bin/env python3
"""edl_check.py — the structural read of an EDL before the beat gate and before any finish: the timeline is contiguous
and every tl span equals out - in; every take exists and [in, out] lies inside it; every src (hero) resolves by the
finisher's file rule ('a|b' alternatives, each a glob, the first that exists wins); a generated event with in > 0 and
handle_head == 0 is flagged (the seek convention that shipped four versions 0.3 s late); exactly one endcard when
--require-endcard (a spot whose beat list forbids a card has none); every VO / music / sfx file exists; a music cue at
least as long as its span (a short cue just ENDS mid-span — no loop, no fade); every VO line ends inside the runtime and
records where its file came from (a WARN when `source` is absent); every EDL out-point sits at least one frame before the
take's own next internal cut (rogue frames) when --cuts is given — except a cut the event DECLARES part of the keeper
(`accepted_cuts` + `accepted_cuts_note`: a long generation composed it and the operator kept it), printed as INFO.
Exit 1 on any FAIL.

  edl_check.py --root <project> --edl edit/<SPOT>-EDL.json [--require-endcard] [--cuts cutlists.json] [--fps 24]
--cuts: {"<take path>": [cut times in take seconds]} — the cut lists video-take-review's qc_seed.py prints.
"""
import argparse, glob, json, os, re, subprocess, sys


def probe(p):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], capture_output=True, text=True).stdout or 0)


def first(pat):
    """the finisher's file rule: 'a|b' alternatives, each a glob; the first that exists wins"""
    for p in (pat or '').split('|'):
        g = sorted(glob.glob(p))
        if g: return g[0]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl', required=True); ap.add_argument('--require-endcard', action='store_true')
    ap.add_argument('--cuts'); ap.add_argument('--fps', type=float, default=24.0)
    a = ap.parse_args(); os.chdir(a.root)
    e = json.load(open(a.edl, encoding='utf-8')); ev = e['events']; au = e.get('audio', {}); fails = []; warns = []
    cuts = json.load(open(a.cuts)) if a.cuts else {}

    def fail(m): fails.append(m); print('FAIL', m)

    def warn(m): warns.append(m); print('WARN', m)

    t = 0.0; dd = {}
    for x in ev:
        if abs(x['tl'][0] - t) > 1e-3: fail(f"{x['id']}: tl starts {x['tl'][0]} but the previous event ends {t} (gap/overlap)")
        if abs((x['tl'][1] - x['tl'][0]) - (x['out'] - x['in'])) > 1e-3: fail(f"{x['id']}: tl span {x['tl'][1] - x['tl'][0]:.3f} != out-in {x['out'] - x['in']:.3f}")
        t = x['tl'][1]
        if not x.get('take'): fail(f"{x['id']}: take is null — pick a keeper"); continue
        if not os.path.exists(x['take']): fail(f"{x['id']}: take missing {x['take']}"); continue
        d = dd.setdefault(x['take'], probe(x['take']))
        if not (0 <= x['in'] < x['out'] <= d + 1 / a.fps + 1e-6): fail(f"{x['id']}: [{x['in']}, {x['out']}] outside the take ({d:.3f} s)")
        if x.get('src') and not first(x['src']): fail(f"{x['id']}: src missing {x['src']} (no alternative exists)")
        if x.get('source') != 'designed' and x['in'] > 0 and float(x.get('handle_head', 0)) == 0:
            warn(f"{x['id']}: in={x['in']} but handle_head=0 — a full-take hero needs handle_head=in (the source is assumed to START at the in-point)")
        acc = [float(c) for c in x.get('accepted_cuts', [])]   # cuts the take COMPOSED and the operator kept: presence is descriptive, consistency is the verdict
        if acc and not x.get('accepted_cuts_note'): warn(f"{x['id']}: accepted_cuts without accepted_cuts_note — record why each cut is part of the keeper")
        for c in acc:
            if not (x['in'] < c < x['out']): warn(f"{x['id']}: accepted cut {c} lies outside the window [{x['in']}, {x['out']}] — a stale declaration")
        for c in cuts.get(x['take'], []):
            if not (x['in'] + 1 / a.fps - 1e-6 < c < x['out'] - 1e-6): continue
            if any(abs(c - k) <= 1 / a.fps + 1e-6 for k in acc): print(f"INFO {x['id']}: the take's cut at {c} is a declared accepted cut")
            else: fail(f"{x['id']}: window [{x['in']}, {x['out']}] crosses the take's own cut at {c} (rogue frames — a cut the take composed and the operator kept goes in accepted_cuts)")
    if abs(t - float(e.get('runtime_s', t))) > 1e-3: fail(f"runtime_s {e.get('runtime_s')} != last tl end {t}")
    ecs = [x for x in ev if x.get('role') == 'endcard']
    if a.require_endcard and len(ecs) != 1: fail(f"{len(ecs)} endcard events (need exactly one, role: endcard)")
    for k, v in au.get('vo', {}).items():
        if not isinstance(v, dict) or 'file' not in v: continue
        if not os.path.exists(v['file']): fail(f"VO {k}: file missing {v['file']}"); continue
        if not v.get('source'): warn(f"VO {k}: no source recorded — a TTS job id, a clone id, or extracted_from: <path> @ <s> (an excerpt of a finished mix carries its bed)")
        d = v.get('dur') or probe(v['file'])
        if v['at'] + d > t + 1e-3: fail(f"VO {k}: ends {v['at'] + d:.3f} past the runtime {t:.3f}")
    for k, m in au.get('music', {}).items():
        if not isinstance(m, dict): continue
        f = first(m.get('file'))
        if not f: fail(f"music {k}: file missing {m.get('file')}"); continue
        span = m['tl'][1] - m['tl'][0]; d = probe(f)
        if d + 1e-3 < span: fail(f"music {k}: {f} is {d:.2f} s but its span is {span:.2f} s — the cue just ENDS at {m['tl'][0] + d:.2f}; cut a longer excerpt")
        for da, db, g in m.get('duck', []):
            if not (m['tl'][0] - 1e-6 <= da < db <= m['tl'][1] + 1e-6): fail(f"music {k}: duck [{da},{db}] outside the cue span {m['tl']}")
    for k, s in au.get('sfx', {}).items():
        if isinstance(s, dict) and s.get('file') and not first(s['file']): fail(f"sfx {k}: file missing {s['file']}")
    for L in e.get('post_layers', []):
        if not glob.glob(re.sub(r'%0?\d*d', '*', L['frames'])): fail(f"layer {L['id']}: no frames at {L['frames']}")
        if L['at'] + L['dur'] > t + 1e-3: warn(f"layer {L['id']}: ends {L['at'] + L['dur']:.3f} past the runtime {t:.3f}")
    print(f"EDL-CHECK {'FAIL (' + str(len(fails)) + ')' if fails else 'PASS'} — {len(ev)} events, runtime {t:.3f} s, {len(warns)} warning(s)")
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
