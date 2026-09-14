#!/usr/bin/env python3
"""premise_rank.py — the premise decision as two rankings that are allowed to disagree: STORY quality (against the veto map
and the archetype) and EXECUTION risk (how likely the premise survives the pipeline — does its world absorb the tool's
artifacts as diegetic behaviour, or fight them?). The disagreement IS the decision and goes to the operator as such;
"most likely to be executed well is not the same as most likely to win". Also checks the competitor set's hygiene: one
assigned divergence AXIS per premise (a single prompt for five ideas returns five variations of one idea), the laziest
route (amnesia / simulation / false reality) capped at one, and the banned default metaphors absent.

  premise_rank.py --premises premises.json [--ban "mirror,dream,clock"]
premises.json = [{"id","axis","story":1-10,"execution":1-10 (10 = safest),"exposure":"…","objection":"…","hero_shot_fallback":true}, …]
"""
import argparse, json, sys

LAZY = ('amnesia', 'simulation', 'false reality', 'false-reality')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); ap.add_argument('--premises', required=True); ap.add_argument('--ban', default='')
    a = ap.parse_args(); P = json.load(open(a.premises, encoding='utf-8')); ban = [b.strip().lower() for b in a.ban.split(',') if b.strip()]; warn = []
    axes = [p.get('axis', '').lower() for p in P]
    if len(set(axes)) < len(axes): warn.append('two premises share a divergence axis — assign one binding axis per run')
    lazy = [p['id'] for p in P if any(k in (p.get('axis', '') + ' ' + p.get('exposure', '')).lower() for k in LAZY)]
    if len(lazy) > 1: warn.append(f'the amnesia/simulation route appears {len(lazy)} times ({lazy}) — cap it at one run')
    for p in P:
        hit = [b for b in ban if b in json.dumps(p).lower()]
        if hit: warn.append(f"{p['id']}: banned default metaphor(s) {hit}")
    by_story = sorted(P, key=lambda p: -p['story']); by_exec = sorted(P, key=lambda p: -p['execution'])
    print('| rank | by STORY | | by EXECUTION | exposure |'); print('|---|---|---|---|---|')
    for i, (s, e) in enumerate(zip(by_story, by_exec), 1): print(f"| {i} | {s['id']} ({s['story']}) | | {e['id']} ({e['execution']}) | {e.get('exposure', '')[:70]} |")
    top_s, top_e = by_story[0]['id'], by_exec[0]['id']
    if top_s != top_e: print(f"\nTHE DECISION: story favours {top_s}, execution favours {top_e} — the two reads disagree; that disagreement is the operator's call, not a tie to break by arithmetic.")
    else: print(f"\nBoth reads favour {top_s}; check its objection before locking: {by_story[0].get('objection', '(none recorded)')}")
    for p in P:
        if not p.get('hero_shot_fallback'): print(f"WARN {p['id']}: no fallback for the hero shot (two clips cut on a blink) — a 15 s held generation degrades")
        if p.get('objection'): print(f"NOTE {p['id']}: objection — {p['objection'][:120]}")
    for w in warn: print('WARN', w)
    print(f'PREMISE-RANK {len(P)} premises, {len(warn)} hygiene warning(s)'); sys.exit(0)


if __name__ == '__main__':
    main()
