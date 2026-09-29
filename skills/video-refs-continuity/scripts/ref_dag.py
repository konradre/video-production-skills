#!/usr/bin/env python3
"""ref_dag.py — the ORDER a reference set is built in: a still is generated only after every still it is built FROM.

Portraits and locations have nothing upstream; a prop is built with its owner in the frame (a hand, a wrist, a pocket) so
it comes after the owner's portrait; an anchor frame composes accepted references, so it comes after all of them. Build
out of order and the prop is generated against a face nobody has accepted yet, then re-rolled when the face changes.
Pattern: ReCA (`videorlm/framework/pipeline.py`: one image DAG for portrait / location / prop / anchor, then validate →
repair → re-validate — video-refs-continuity SKILL.md § 3 carries the repair by reason).

refs.json: [{"name": "MOM", "kind": "portrait"}, {"name": "KITCHEN", "kind": "location"},
            {"name": "APRON", "kind": "prop", "owner": "MOM"},
            {"name": "S01-START", "kind": "anchor", "refs": ["MOM", "KITCHEN", "APRON"]}, …]   (+ optional "depends_on": [...])
kinds: portrait · location · look · prop · anchor.

  ref_dag.py --refs <refs.json> [--accepted A,B,…]     # the waves; with --accepted, what may be built NEXT
  ref_dag.py --selftest
Exit 1 on an unknown name, a cycle, a prop with no owner or an anchor with no refs; 0 otherwise.
"""
import argparse, json, sys, tempfile, os

ROOTS = {'portrait', 'location', 'look'}


def deps_of(r):
    return list(dict.fromkeys(([r['owner']] if r.get('owner') else []) + list(r.get('refs', [])) + list(r.get('depends_on', []))))


def plan(refs):
    names = {r['name']: r for r in refs}; errs, warns = [], []
    for r in refs:
        k = r.get('kind')
        if k == 'prop' and not r.get('owner'): errs.append(f"{r['name']}: a prop with no owner — name whose hand, pocket or table it is built with")
        if k == 'anchor' and not r.get('refs'): errs.append(f"{r['name']}: an anchor with no refs — an anchor composes accepted references")
        if k in ROOTS and deps_of(r): warns.append(f"{r['name']}: a {k} built from {deps_of(r)} — a {k} is normally a root")
        for d in deps_of(r):
            if d not in names: errs.append(f"{r['name']}: depends on {d}, which is not in the set")
    if errs: return None, errs, warns
    left, done, waves = dict(names), set(), []
    while left:
        wave = sorted(n for n, r in left.items() if all(d in done for d in deps_of(r)))
        if not wave: return None, [f"a cycle among {sorted(left)}"], warns
        waves.append(wave); done |= set(wave); [left.pop(n) for n in wave]
    return waves, [], warns


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--refs'); ap.add_argument('--accepted', default=''); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest: return selftest()
    if not a.refs: ap.error('--refs, or --selftest')
    refs = json.load(open(a.refs)); waves, errs, warns = plan(refs)
    for w in warns: print('WARN', w)
    if errs:
        for e in errs: print('FAIL', e)
        return 1
    kind = {r['name']: r.get('kind') for r in refs}
    for i, w in enumerate(waves, 1): print(f"wave {i}: " + ', '.join(f'{n} ({kind[n]})' for n in w))
    acc = {x for x in a.accepted.split(',') if x}
    if acc:
        by = {r['name']: r for r in refs}
        nxt = [n for w in waves for n in w if n not in acc and all(d in acc for d in deps_of(by[n]))]
        wait = [n for w in waves for n in w if n not in acc and n not in nxt]
        print(f"NEXT (every upstream accepted): {', '.join(nxt) or 'nothing — the set is complete'}"
              + (f" · waiting: {', '.join(f'{n} on ' + ','.join(d for d in deps_of(by[n]) if d not in acc) for n in wait)}" if wait else ''))
    return 0


def selftest():
    good = [{'name': 'MOM', 'kind': 'portrait'}, {'name': 'KITCHEN', 'kind': 'location'}, {'name': 'APRON', 'kind': 'prop', 'owner': 'MOM'},
            {'name': 'S01', 'kind': 'anchor', 'refs': ['MOM', 'KITCHEN', 'APRON']}]
    w, e, _ = plan(good)
    chk = [('portraits and locations first, the prop after its owner, the anchor last', w == [['KITCHEN', 'MOM'], ['APRON'], ['S01']] and not e),
           ('a prop with no owner fails', bool(plan([{'name': 'CUP', 'kind': 'prop'}])[1])),
           ('an anchor with no refs fails', bool(plan([{'name': 'A', 'kind': 'anchor'}])[1])),
           ('an unknown dependency fails', bool(plan([{'name': 'CUP', 'kind': 'prop', 'owner': 'DAD'}])[1])),
           ('a cycle fails', bool(plan([{'name': 'X', 'kind': 'prop', 'owner': 'Y'}, {'name': 'Y', 'kind': 'prop', 'owner': 'X'}])[1]))]
    with tempfile.TemporaryDirectory() as r:
        p = os.path.join(r, 'refs.json'); json.dump(good, open(p, 'w'))
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): main(['--refs', p, '--accepted', 'MOM,KITCHEN'])
        chk.append(('with MOM and KITCHEN accepted, the next buildable is APRON alone', 'NEXT (every upstream accepted): APRON ·' in buf.getvalue()))
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
