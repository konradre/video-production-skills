#!/usr/bin/env python3
"""attach_proof.py — did the model RECEIVE every reference the take was gated on? A name in a prompt, or a path in a job
document, is not proof the model read the image. After the call, the gate's submission record (what was cited and
checked) is compared with the receipt's request record (what the call SENT, by name, with its url or upload id):

  ATTACHED  a gated name the request carried
  MISSING   a gated name the request did not carry → FAIL: the take was generated without it, whatever it looks like
  UNGATED   an input the gate never saw (an end image, an audio id) → WARN: nothing checked what it is
  UNPROVEN  the receipt predates the request record (no `inputs`), or the venue writes no gate record (fal) — confirm
            from the venue's own job record: kie recordInfo's `param`, monid's run input, the Higgsfield job detail

The other half of the proof is a read, not a computation: the product is VISIBLE in the take and matches its reference
(ACCEPTANCE-MATRIX row 5, at 2× beside the product photo) — a reference that was attached and ignored passes this script.

  attach_proof.py --root <project> --take S01-A1-s1 [--take …]     one or more takes
  attach_proof.py --root <project> --all                           every take the gate recorded at submission
  attach_proof.py --selftest

Exit 0 PASS · 1 FAIL (a gated reference was not attached) · 2 UNPROVEN only. Sentinel ATTACH-PROOF PASS|FAIL|UNPROVEN.
Receipts carry `inputs` from 2026-09-29 (hf_submit, hf_api_submit, monid_submit, gen_video_kie). Pattern:
1229119561Weike/ai-ugc-factory skills/ai-ugc-factory/SKILL.md (MODEL_INPUT_IMAGES_ACTUALLY_ATTACHED ·
PRODUCT_REFERENCE_WAS_IMAGE_INPUT · PRODUCT_VISIBLE_AND_MATCHES_REAL_ASSET).
"""
import argparse, glob, json, os, sys, tempfile


def gate_records(root):
    out = {}
    p = os.path.join(root, 'receipts', 'refs-gate.jsonl')
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if not line: continue
            try: j = json.loads(line)
            except ValueError: continue
            if j.get('asset') and 'prompt' in j and j.get('target') and isinstance(j.get('refs'), list):
                out[j['asset']] = j                                 # the last submission record wins
    return out


def receipt_records(root):
    out = {}
    for f in sorted(glob.glob(os.path.join(root, 'receipts', '*.json')), key=os.path.getmtime):
        try: d = json.load(open(f, encoding='utf-8'))
        except (OSError, ValueError): continue
        for r in d if isinstance(d, list) else []:
            if isinstance(r, dict) and r.get('name'):
                if r['name'] not in out or 'inputs' in r or 'inputs' not in out[r['name']][1]:
                    out[r['name']] = (os.path.relpath(f, root), r)
    return out


def prove(take, gates, receipts):
    rows, g = [], gates.get(take)
    src, rec = receipts.get(take, (None, None))
    if g is None:
        return 'UNPROVEN', [('gate', 'UNPROVEN', 'no submission record in receipts/refs-gate.jsonl (fal writes none) — '
                                                 'read the venue\'s own job record for its inputs')]
    if rec is None or 'inputs' not in rec:
        why = f'{src} predates the request record (no inputs)' if rec else 'no receipt names this take'
        return 'UNPROVEN', [('receipt', 'UNPROVEN', why + ' — confirm from the venue\'s job record: kie recordInfo param, '
                                                         'monid run input, the Higgsfield job detail')]
    sent = {}
    for x in rec['inputs']:
        if x.get('name'): sent.setdefault(x['name'], []).append(x)
    verdict = 'PASS'
    for name in g['refs']:
        if name in sent:
            x = sent[name][0]; where = x.get('url') or x.get('id') or ''
            rows.append((name, 'ATTACHED', f"{x.get('role', '?')} · {where[:70]}"))
        else:
            rows.append((name, 'MISSING', 'gated and cited, never sent — the take was generated without it')); verdict = 'FAIL'
    for name, xs in sent.items():
        if name not in g['refs']:
            rows.append((name, 'UNGATED', f"sent as {xs[0].get('role', '?')}, never through the gate — nothing checked what it shows"))
    for x in rec['inputs']:
        if not x.get('name'):
            rows.append((x.get('role', '?'), 'UNGATED', f"sent by id {str(x.get('id') or x.get('url'))[:60]} — no name, so no gate row"))
    return verdict, rows


def run(root, takes, out=print):
    gates, receipts = gate_records(root), receipt_records(root)
    takes = takes or sorted(gates)
    if not takes:
        out('ATTACH-PROOF UNPROVEN — no take recorded at submission in receipts/refs-gate.jsonl'); return 2
    worst = 'PASS'
    for t in takes:
        v, rows = prove(t, gates, receipts)
        out(f'{t}: {v}')
        for n, s, m in rows: out(f'  {s:<9} {n:<24} {m}')
        worst = 'FAIL' if 'FAIL' in (worst, v) else ('UNPROVEN' if 'UNPROVEN' in (worst, v) else 'PASS')
    out(f'ATTACH-PROOF {worst} — {len(takes)} take(s); the product-visible read stays yours (ACCEPTANCE-MATRIX row 5)')
    return {'PASS': 0, 'FAIL': 1, 'UNPROVEN': 2}[worst]


def selftest():
    cases = []
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, 'receipts'))
        with open(os.path.join(d, 'receipts', 'refs-gate.jsonl'), 'w') as f:
            for take, refs in (('S01-A-s1', ['PRODUCT-sheet', 'ROOM']), ('S01-B-s1', ['PRODUCT-sheet', 'ROOM']),
                               ('S01-C-s1', ['ROOM']), ('S01-D-s1', ['ROOM'])):
                f.write(json.dumps({'asset': take, 'target': 'monid', 'prompt': 'p.txt', 'refs': refs}) + '\n')
            f.write(json.dumps({'asset': 'ROOM', 'sha256': 'x', 'accepted': True}) + '\n')      # not a submission
        json.dump([{'name': 'S01-A-s1', 'inputs': [{'name': 'PRODUCT-sheet', 'role': 'reference_image', 'url': 'https://u/1'},
                                                   {'name': 'ROOM', 'role': 'reference_image', 'url': 'https://u/2'}]},
                   {'name': 'S01-B-s1', 'inputs': [{'name': 'ROOM', 'role': 'reference_image', 'url': 'https://u/2'}]},
                   {'name': 'S01-C-s1', 'inputs': [{'name': 'ROOM', 'role': 'reference_image', 'url': 'https://u/2'},
                                                   {'name': 'END', 'role': 'last_frame', 'url': 'https://u/3'}]},
                   {'name': 'S01-D-s1', 'run_id': 'r'}], open(os.path.join(d, 'receipts', 'monid-runs-s01.json'), 'w'))
        g, r = gate_records(d), receipt_records(d)
        cases.append(('every gated reference sent → PASS', prove('S01-A-s1', g, r)[0] == 'PASS'))
        v, rows = prove('S01-B-s1', g, r)
        cases.append(('the product sheet gated but never sent → FAIL MISSING', v == 'FAIL' and ('PRODUCT-sheet', 'MISSING') in [(a, b) for a, b, _ in rows]))
        v, rows = prove('S01-C-s1', g, r)
        cases.append(('an input the gate never saw → UNGATED, still PASS', v == 'PASS' and any(b == 'UNGATED' and a == 'END' for a, b, _ in rows)))
        cases.append(('a receipt without inputs → UNPROVEN', prove('S01-D-s1', g, r)[0] == 'UNPROVEN'))
        cases.append(('a take with no gate record (fal) → UNPROVEN', prove('S01-FAL-s1', g, r)[0] == 'UNPROVEN'))
        cases.append(('a registration record is not a submission', 'ROOM' not in g))
        cases.append(('--all: one FAIL makes the run FAIL (exit 1)', run(d, None, out=lambda *a: None) == 1))
        cases.append(('the PASS take alone exits 0', run(d, ['S01-A-s1'], out=lambda *a: None) == 0))
    for name, ok in cases: print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in cases); print(f"attach_proof selftest {'PASS' if ok else 'FAIL'}"); return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--take', action='append')
    ap.add_argument('--all', action='store_true'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    if not (a.take or a.all): ap.print_help(); sys.exit(2)
    sys.exit(run(os.path.abspath(a.root), a.take))


if __name__ == '__main__':
    main()
