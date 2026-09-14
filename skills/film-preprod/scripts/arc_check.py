#!/usr/bin/env python3
"""arc_check.py — the character machinery, checked before a beat is written: Weiland's four-slot schema (lie · want · need ·
ghost) on every principal, an arc from the taxonomy with its canonical state chain, the 3-question classifier's answers
consistent with that arc, and the ARC-DELTA double-check — the same action at 0:00 and at the climax with the motive
inverted (she lights the lamp from ignorance; she lights it from choice). A short is a TWO-HANDER: the opponent doubles as
the Impact Character; a third principal is flagged. Exit 1 on any FAIL.

  arc_check.py --cast cast.json
cast.json = {"principals": [{"name","lie","want","need","ghost","arc","genre_answer","start_answer","end_answer",
             "action_open","motive_open","action_climax","motive_climax"}, …]}
arc ∈ positive | flat | disillusionment | fall | corruption
genre_answer ∈ positive | negative (Q1: does the genre want a positive or a negative change?)
start_answer ∈ good-place-truth | bad-place-lie (Q2: where does the hero start, and what do they believe?)
end_answer   ∈ better-truth | darker-truth-wiser | worse-lie (Q3: where do they end?)
"""
import argparse, json, sys

CHAINS = {
    'positive': 'BELIEVES LIE → ENCOUNTERS TRUTH → RESISTS → ACCEPTS → ACTS ON TRUTH → REJECTS LIE',
    'flat': 'BELIEVES TRUTH → TESTED → HOLDS → TRANSFORMS WORLD',
    'disillusionment': 'BELIEVES LIE → OVERCOMES LIE → NEW TRUTH IS TRAGIC   (structurally identical to positive, the Truth\'s polarity negative)',
    'fall': 'BELIEVES LIE → CLINGS → REJECTS TRUTH → BELIEVES WORSE LIE',
    'corruption': 'SEES TRUTH → REJECTS TRUTH → EMBRACES LIE',
}
CLASSIFY = {('positive', 'bad-place-lie', 'better-truth'): 'positive', ('negative', 'bad-place-lie', 'darker-truth-wiser'): 'disillusionment', ('positive', 'bad-place-lie', 'darker-truth-wiser'): 'disillusionment',
            ('negative', 'bad-place-lie', 'worse-lie'): 'fall', ('negative', 'good-place-truth', 'worse-lie'): 'corruption', ('positive', 'good-place-truth', 'better-truth'): 'flat', ('negative', 'good-place-truth', 'better-truth'): 'flat'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); ap.add_argument('--cast', required=True); a = ap.parse_args()
    C = json.load(open(a.cast, encoding='utf-8')); P = C['principals']; fails = []

    def fail(m): fails.append(m); print('FAIL', m)

    if len(P) > 2: fail(f'{len(P)} principals — a short is a two-hander (the opponent doubles as the Impact Character); four-corner opposition fragments attention under six minutes')
    for p in P:
        n = p.get('name', '?')
        for k in ('lie', 'want', 'need', 'ghost', 'arc'):
            if k not in p: fail(f'{n}: missing {k}' + (' (ghost may be null, but it must be stated)' if k == 'ghost' else ''))
        arc = p.get('arc')
        if arc not in CHAINS: fail(f'{n}: arc {arc!r} not in the taxonomy {list(CHAINS)}'); continue
        key = (p.get('genre_answer'), p.get('start_answer'), p.get('end_answer')); want = CLASSIFY.get(key)
        if want is None: print(f'WARN {n}: classifier answers {key} do not map to a canonical arc — state the reasoning in the beat sheet')
        elif want != arc: fail(f'{n}: the 3-question classifier says {want} ({key}) but arc is {arc}')
        if p.get('want') and p.get('need') and p['want'].strip().lower() == p['need'].strip().lower(): fail(f'{n}: want == need — the Want is external and salves the Lie; the Need is the internal antidote to it')
        ao, ac, mo, mc = (p.get(k, '') for k in ('action_open', 'action_climax', 'motive_open', 'motive_climax'))
        if not (ao and ac and mo and mc): fail(f'{n}: the arc-delta needs action_open/action_climax/motive_open/motive_climax')
        else:
            same = ao.strip().lower() == ac.strip().lower(); inv = mo.strip().lower() != mc.strip().lower()
            if not same: print(f'WARN {n}: the opening action ({ao!r}) and the climax action ({ac!r}) differ — the strongest arc-delta repeats ONE action with the motive inverted')
            if not inv: fail(f'{n}: the motive at the climax equals the motive at the open — no arc delta')
        print(f'{n}: {arc} — {CHAINS[arc]}')
    print('ARC-CHECK ' + ('FAIL' if fails else 'PASS')); sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
