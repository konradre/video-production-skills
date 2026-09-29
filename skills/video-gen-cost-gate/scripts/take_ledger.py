#!/usr/bin/env python3
"""take_ledger.py — what a kept take has actually cost here, and whether a shot has hit a stop rule.

The cost line quotes a price per USABLE take, and until now its keep rate was assumed (3:1–6:1 across models). This
measures it from the project's own record — the denominator is every take bought, kept or not:

  attempts  every gate record written at submission (`receipts/refs-gate.jsonl` rows that carry a target and a prompt:
            hf_submit, hf_api_submit, monid_submit, gen_video_kie and gen_stills record one per take BEFORE polling —
            billing happens at acceptance). A take is `<shot>-s<n>`; the shot is the name without `-s<n>`.
            gen_video_fal.py writes no gate record, so a fal take is invisible here and is reported as a pick with
            no attempt.
  kept      every `pick` in `receipts/picks.jsonl` (pick_gate.py record), matched by its file stem (`__<suffix>` and
            `-s<n>` stripped to the shot).

Per shot it prints attempts, picks and the stop-rule tripwire (SKILL § 2, the stop-rule ladder): no budget declared
and 3 paid attempts without a pick → STOP and name the options; a declared budget half spent without a pick → CHANGE
STRATEGY; the budget spent → BUDGET SPENT. Per venue it prints the keep rate over CLOSED shots (a shot with a pick);
open shots are listed apart, because their attempts are not finished. Under 5 picks the rate is low-n: quote the
assumed band beside it.

  take_ledger.py --root <project> [--budget <shot>=<n> ...] [--budgets budgets.json] [--types shot-types.json] [--json]
  take_ledger.py --selftest

Exit 0 (report), 1 when any shot has tripped a stop rule, 2 when the project has no gate records to read.
"""
import argparse, json, math, os, re, sys, tempfile
from collections import defaultdict

SEED = re.compile(r'-s\d+$')


def shot_of(name):
    return SEED.sub('', name)


def rows(path):
    out = []
    if not os.path.exists(path): return out
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if not line: continue
        try: out.append(json.loads(line))
        except ValueError: pass
    return out


def ledger(root, budgets=None, types=None):
    budgets, types = budgets or {}, types or {}
    gate = [r for r in rows(os.path.join(root, 'receipts', 'refs-gate.jsonl')) if r.get('target') and 'prompt' in r and r.get('asset')]
    picks = [r for r in rows(os.path.join(root, 'receipts', 'picks.jsonl')) if r.get('kind') == 'pick' and r.get('path')]
    S = defaultdict(lambda: {'attempts': 0, 'picks': 0, 'venues': set(), 'takes': []})
    for r in gate:
        s = S[shot_of(r['asset'])]; s['attempts'] += 1; s['venues'].add(r['target']); s['takes'].append(r['asset'])
    orphans = []
    for p in picks:
        take = os.path.splitext(os.path.basename(p['path']))[0].split('__')[0]
        sh = shot_of(take)
        if sh in S: S[sh]['picks'] += 1
        else: orphans.append(p['path'])
    out = []
    for sh in sorted(S):
        s = S[sh]; b = budgets.get(sh); trip = None
        if s['picks'] == 0:
            if b and s['attempts'] >= b: trip = f'BUDGET SPENT ({s["attempts"]} of {b}) — no pick'
            elif b and s['attempts'] >= math.ceil(b / 2): trip = f'CHANGE STRATEGY — half the declared budget ({s["attempts"]} of {b}) without a pick: a different mode, a split shot'
            elif not b and s['attempts'] >= 3: trip = f'STOP — {s["attempts"]} paid attempts, no budget declared: name the options (accept the best take, re-scope, defer, a placeholder)'
        out.append({'shot': sh, 'type': types.get(sh), 'venues': sorted(s['venues']), 'attempts': s['attempts'], 'picks': s['picks'], 'budget': b, 'trip': trip})
    by = defaultdict(lambda: {'closed_attempts': 0, 'picks': 0, 'closed_shots': 0, 'open_attempts': 0, 'open_shots': 0})
    for r in out:
        for key in ([f'venue {v}' for v in r['venues']] + ([f'type {r["type"]}'] if r['type'] else [])):
            g = by[key]
            if r['picks']: g['closed_attempts'] += r['attempts']; g['picks'] += r['picks']; g['closed_shots'] += 1
            else: g['open_attempts'] += r['attempts']; g['open_shots'] += 1
    return out, dict(by), orphans, len(gate)


def report(root, out, by, orphans, n):
    print(f'{root}: {n} take(s) bought across {len(out)} shot(s) (gate records) · {sum(r["picks"] for r in out)} pick(s)')
    for r in out:
        print(f"  {r['shot']:<24} {'/'.join(r['venues']):<10} attempts {r['attempts']:>2}  picks {r['picks']}"
              + (f'  budget {r["budget"]}' if r['budget'] else '') + (f'  ⚠ {r["trip"]}' if r['trip'] else ''))
    for k, g in sorted(by.items()):
        if g['picks']:
            rate = g['closed_attempts'] / g['picks']
            print(f"  KEEP RATE {k}: {g['closed_attempts']} attempts / {g['picks']} picks over {g['closed_shots']} closed shot(s) = {rate:.1f}:1"
                  + (' — low-n (under 5 picks): quote the assumed 3:1–6:1 beside it' if g['picks'] < 5 else ''))
        else:
            print(f"  KEEP RATE {k}: no pick yet — quote the assumed 3:1–6:1")
        if g['open_shots']: print(f"    open: {g['open_attempts']} attempts over {g['open_shots']} shot(s) with no pick — outside the rate")
    for p in orphans: print(f'  pick with no gate record (a fal take, or bought before the ledger): {p}')


def selftest():
    ok = True
    def chk(label, cond):
        nonlocal ok; ok &= bool(cond); print(f"  {'ok ' if cond else 'BAD'} {label}")
    with tempfile.TemporaryDirectory() as T:
        os.makedirs(os.path.join(T, 'receipts'))
        g = [{'asset': 'PLATE', 'file': 'references/PLATE.jpg', 'client_supplied': True}]            # a registration: no target
        g += [{'asset': f'S01-G1-s{i}', 'target': 'monid', 'prompt': 'p.txt'} for i in (1, 2, 3)]
        g += [{'asset': f'S02-G1-s{i}', 'target': 'hf', 'prompt': 'p.txt'} for i in (1, 2)] * 2      # two batches of 2
        g += [{'asset': f'S03-G1-s{i}', 'target': 'kie', 'prompt': 'p.txt'} for i in (1, 2)]
        g += [{'asset': 'STILL-A', 'target': 'kie', 'prompt': 'stills/a.txt'}]
        open(os.path.join(T, 'receipts', 'refs-gate.jsonl'), 'w').write('\n'.join(json.dumps(x) for x in g) + '\n')
        p = [{'kind': 'pick', 'path': 'takes/S01-G1-s2.mp4'}, {'kind': 'derive', 'path': 'takes/S01-G1-s2__hero.mp4'},
             {'kind': 'pick', 'path': 'refs/STILL-A__crop.png'}, {'kind': 'pick', 'path': 'takes/F9-s1.mp4'}]
        open(os.path.join(T, 'receipts', 'picks.jsonl'), 'w').write('\n'.join(json.dumps(x) for x in p) + '\n')
        out, by, orph, n = ledger(T, budgets={'S03-G1': 4}, types={'S01-G1': 'talking head'})
        R = {r['shot']: r for r in out}
        chk(f'{n} takes counted: registrations skipped, the repeat batch counted twice', n == 10)
        chk('S01-G1: 3 attempts, 1 pick, no trip', (R['S01-G1']['attempts'], R['S01-G1']['picks'], R['S01-G1']['trip']) == (3, 1, None))
        chk('S02-G1: 4 attempts, no pick, no budget → STOP', R['S02-G1']['trip'] and R['S02-G1']['trip'].startswith('STOP'))
        chk('S03-G1: budget 4, 2 attempts, no pick → CHANGE STRATEGY', R['S03-G1']['trip'] and R['S03-G1']['trip'].startswith('CHANGE'))
        chk('a still is a take: STILL-A picked through a __crop derivative name', R['STILL-A']['picks'] == 1)
        chk('the derive record is not a keep', R['S01-G1']['picks'] == 1)
        chk('a pick with no gate record is reported, not dropped', orph == ['takes/F9-s1.mp4'])
        m = by['venue monid']; chk('monid keep rate 3:1 over one closed shot', (m['closed_attempts'], m['picks']) == (3, 1))
        h = by['venue hf']; chk('hf: no pick → open attempts only', (h['picks'], h['open_attempts']) == (0, 4))
        chk('the type axis is carried', by['type talking head']['picks'] == 1)
        out2, by2, _, _ = ledger(T, budgets={'S02-G1': 4})
        chk('a declared budget of 4, all spent → BUDGET SPENT', [r for r in out2 if r['shot'] == 'S02-G1'][0]['trip'].startswith('BUDGET'))
        e, _, _, n0 = ledger(os.path.join(T, 'nothing'))
        chk('no gate records → nothing counted', (e, n0) == ([], 0))
    print(f"SELFTEST {'PASS' if ok else 'FAIL'}"); return 0 if ok else 1


def main():
    if '--selftest' in sys.argv: sys.exit(selftest())
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--budget', action='append', default=[], help='<shot>=<n> takes declared for that shot')
    ap.add_argument('--budgets', help='a JSON file {shot: n}'); ap.add_argument('--types', help='a JSON file {shot: type} — adds a per-type rate')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    budgets = json.load(open(a.budgets)) if a.budgets else {}
    for b in a.budget:
        k, _, v = b.partition('='); budgets[k] = int(v)
    types = json.load(open(a.types)) if a.types else {}
    out, by, orphans, n = ledger(a.root, budgets, types)
    if not n: print(f'no gate records under {a.root}/receipts/refs-gate.jsonl — nothing bought through the gate here'); sys.exit(2)
    if a.json: print(json.dumps({'shots': out, 'rates': by, 'orphan_picks': orphans}, indent=2))
    else: report(a.root, out, by, orphans, n)
    sys.exit(1 if any(r['trip'] for r in out) else 0)


if __name__ == '__main__':
    main()
