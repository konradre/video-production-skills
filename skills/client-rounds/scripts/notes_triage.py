#!/usr/bin/env python3
"""notes_triage.py — the client's notes as a CURATED, NUMBERED list with NO action taken. Each item carries the client's own words, the spot it refers to (client numbering =
DELIVERY order, mapped with --map), a suggested class from the client's own vocabulary — CUT (edit-only: "no regeneration
needed", "just cut", "trim", "shorten"), RECYCLE (an older version's shot: "keep the scene from the original", "recycle",
"the version we had"), REBUILD (a regen: "rebuild", "regenerate", "new", "needs another pass"), APPROVE (a quoted
approval — freezes that spot), GATE (a product-proportion or likeness note — a pre-production gate from now on) — and a
blank column for the operator's answer. A causality note ("reads as two separate clips", "one doesn't cause the other")
is marked CAUSALITY: the take's own footage first, one gen last.

  notes_triage.py --notes prompts/CLIENT-NOTES-<date>.txt [--map "#5=S01,#6=S02"] [--out prompts/CLIENT-ROUND-<date>.md]
"""
import argparse, re

CLASSES = [   # order matters: the client's explicit "no regeneration" outranks a stray "rebuild"; a first guess the operator corrects per item
    ('APPROVE', r"looks solid|gold exactly|no changes|100% agree|keep that version|i'?m good with|perfect|looking great|all clear"),
    ('CAUSALITY', r"two separate clips|doesn'?t cause|one continuous|flow between|connect everything"),
    ('CUT', r"no regeneration|just cut|trim|shorten|cut (the|to|it)|a few cuts|hold(s)? that|too long|too soon"),
    ('RECYCLE', r"recycle|keep the scene|the original (clip|version|scene)|older version|copy paste|we already have"),
    ('GATE', r"actual product|misrepresent|proportion|look(s)? suspiciously like|likeness|to be safe"),
    ('REBUILD', r"rebuild|regen|re-?generate|another pass|new (shot|scene|gen)|replace (him|her|the)|recast|tweak (his|her) appearance|unexpectedly|instinctively"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--notes', required=True); ap.add_argument('--map', default=''); ap.add_argument('--out')
    a = ap.parse_args(); text = open(a.notes, encoding='utf-8').read()
    m = dict(kv.split('=') for kv in a.map.split(',') if '=' in kv)
    paras = [p.strip() for p in re.split(r'\n\s*\n|\n(?=\s*\(?\d+\))|\n(?=\s*#\d)', text) if len(p.strip()) > 20]   # blank lines, "(1)" items, "#5" items
    rows = []; spot = None
    for p in paras:
        ref = re.search(r'#(\d+)', p); spot = m.get('#' + ref.group(1), spot) if ref else spot
        for sid in re.findall(r'\b(S\d{2}[A-Z]?)\b', p): spot = sid
        cls = next((c for c, rx in CLASSES if re.search(rx, p, re.I)), 'NOTE')
        quotes = re.findall(r'[“"]([^”"]{6,})[”"]', p); words = quotes[0] if quotes else p
        rows.append((spot or '?', cls, words.replace('\n', ' ')[:160]))
    out = [f'# Client round — {a.notes}', '', 'Curated, NO action taken. Operator answers per item (a number, a yes/no, or "best judgement").', '',
           '| # | spot | class | the client\'s words | operator\'s answer |', '|---|---|---|---|---|']
    out += [f'| {i} | {s} | {c} | {w} |  |' for i, (s, c, w) in enumerate(rows, 1)]
    out += ['', 'Classes: CUT = edit-only (video-edit-edl) · RECYCLE = a shot from an older version (a new EDL, the old one untouched) · REBUILD = a regen (video-refs-continuity → video-gen-cost-gate, cost line first) · CAUSALITY = one continuous joke, the take\'s own footage first, one gen last · APPROVE = quoted into the ledger, the spot FREEZES · GATE = a pre-production gate from now on (product proportion, likeness).']
    md = '\n'.join(out); print(md)
    if a.out: open(a.out, 'w', encoding='utf-8').write(md + '\n'); print(f'\nwrote {a.out}')


if __name__ == '__main__':
    main()
