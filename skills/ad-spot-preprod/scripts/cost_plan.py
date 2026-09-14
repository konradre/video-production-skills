#!/usr/bin/env python3
"""cost_plan.py — the rounds and the cost of a spot from its scenes table, as the numbered cost lines the operator answers
(expect "no" on any addition). Scenes carry a duration, a seed count, a mode and their dependency (the scene whose keeper
they need a reference from); rounds are the dependency levels, so the plan says what can run in parallel and what waits
for a pick. Credits at the venue rate (Seedance 2.5 at 480p: 2.5 credits per second of OUTPUT per seed); worst case = one
re-roll per scene; the designed events cost 0. Stills and VO are listed as their own lines.

  cost_plan.py --scenes scenes.json [--rate 2.5] [--usd-per-credit 0.035] [--extra "stills:0.09" --extra "VO 954 chars:0.12"]
scenes.json = [{"id":"S01-A","seconds":7,"seeds":3,"mode":"t2v","after":null,"gag":"…"}, {"id":"S01-B","seconds":8,"seeds":3,"mode":"omni_reference","after":"S01-A"}, {"id":"S01-13","designed":true,"seconds":4}, …]
"""
import argparse, json


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scenes', required=True); ap.add_argument('--rate', type=float, default=2.5); ap.add_argument('--usd-per-credit', type=float, default=0.035); ap.add_argument('--extra', action='append', default=[])
    a = ap.parse_args(); S = json.load(open(a.scenes, encoding='utf-8')); byid = {s['id']: s for s in S}
    level = {}

    def lv(s):
        if s['id'] in level: return level[s['id']]
        p = s.get('after'); level[s['id']] = 0 if not p else lv(byid[p]) + 1; return level[s['id']]

    for s in S: lv(s)
    gen = [s for s in S if not s.get('designed')]; rounds = sorted({level[s['id']] for s in gen})
    total = 0.0; n = 1
    for r in rounds:
        rows = [s for s in gen if level[s['id']] == r]; cr = sum(s['seconds'] * s.get('seeds', 3) * a.rate for s in rows); total += cr
        deps = sorted({s['after'] for s in rows if s.get('after')})
        print(f"{n}. Round {r + 1} = " + ' + '.join(f"{s['id']} × {s.get('seeds', 3)} ({s.get('mode', 't2v')}, {s['seconds']} s = {s['seconds'] * s.get('seeds', 3) * a.rate:g} cr)" for s in rows) + f" = {cr:g} cr ≈ ${cr * a.usd_per_credit:.2f}" + (f" — after the pick(s) on {', '.join(deps)}" if deps else ' — no dependency; runs first')); n += 1
    for s in [x for x in S if x.get('designed')]: print(f"{n}. {s['id']} designed, {s['seconds']} s — 0 cr"); n += 1
    for e in a.extra: name, usd = e.rsplit(':', 1); print(f"{n}. {name} ≈ ${float(usd):.2f}"); n += 1
    worst = total * 2
    print(f"\nSpot total ≈ {total:g} cr ≈ ${total * a.usd_per_credit:.2f} clean; one re-roll per scene ≈ {worst:g} cr ≈ ${worst * a.usd_per_credit:.2f} worst case; generated {sum(s['seconds'] for s in gen)} s + designed {sum(s['seconds'] for s in S if s.get('designed'))} s")
    print('GO needed per round — nothing submits before the operator answers the line for that round.')


if __name__ == '__main__':
    main()
