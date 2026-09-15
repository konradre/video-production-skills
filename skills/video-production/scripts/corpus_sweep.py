#!/usr/bin/env python3
"""corpus_sweep.py — the reading aid behind the intake declarations: for every skill under --skills it prints what a
description hides — the skill's "What varies" paragraph and its section headers — and marks, per project axis, whether the
axis VALUE appears in the description only, in the body only, or in both. A "body-only" mark is the case this exists for: a
skill whose trigger list says "generated video" while its body carries rules that apply to any footage (verify every render,
variants from the mezzanine, the grade from the library). The agent still reads and declares; the sweep only makes sure every
body is opened once.

  corpus_sweep.py --skills ~/.claude/skills --axes footage=existing,deliverable=ad,venue=none [--only video-,spot-,ad-spot,film-,designed,client-rounds,explainer,mastering]
  corpus_sweep.py --selftest
Axis values match as whole words, case-insensitive; --synonyms footage=existing:documentary|real|client adds terms per value.
"""
import argparse, os, re, sys, tempfile

DEFAULT_PREFIXES = ['video-', 'spot-audio', 'ad-spot', 'film-preprod', 'designed-elements', 'client-rounds', 'explainer-video', 'mastering-audio']
DEFAULT_SYN = {'existing': ['documentary', 'real footage', 'client clips', 'existing footage', 'another stack', 'any source'],
               'generated': ['seedance', 'take', 'seed', 'keeper'], 'ad': ['spot', 'campaign', 'sign-off', 'cta'], 'film': ['beat sheet', 'self-revelation']}


def parse_skill(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    desc = ''
    m = re.search(r'^description:\s*>?\s*\n?((?:.|\n)*?)(?=^\w[\w-]*:|^---)', s, re.M)
    if m: desc = ' '.join(l.strip() for l in m.group(1).splitlines())
    body = s.split('---', 2)[-1] if s.startswith('---') else s
    wv = re.search(r'\*\*What varies\.\*\*\s*((?:.|\n)*?)(?=\n\n)', body)
    heads = [h.strip() for h in re.findall(r'^#{2,3} (.+)$', body, re.M)]
    return desc, (wv.group(1).replace('\n', ' ').strip() if wv else ''), heads, body


def hit(text, terms): return [t for t in terms if re.search(r'\b' + re.escape(t) + r'\b', text, re.I)]


def sweep(skills_dir, axes, syn, prefixes):
    rows = []
    for name in sorted(os.listdir(skills_dir)):
        if prefixes and not any(name.startswith(p) for p in prefixes): continue
        sk = os.path.join(skills_dir, name, 'SKILL.md')
        if not os.path.exists(sk): continue
        desc, wv, heads, body = parse_skill(sk); marks = {}
        for ax, val in axes.items():
            terms = [val] + syn.get(val, [])
            d, b = hit(desc, terms), hit(body, terms)
            marks[ax] = 'both' if d and b else 'description-only' if d else 'BODY-ONLY' if b else 'neither'
        rows.append((name, marks, wv, heads))
    return rows


def render(rows, axes):
    out = []
    for name, marks, wv, heads in rows:
        out.append(f'## {name}   ' + ' · '.join(f'{ax}={axes[ax]}: {m}' for ax, m in marks.items()))
        if wv: out.append('   what varies: ' + wv[:400] + ('…' if len(wv) > 400 else ''))
        out.append('   sections: ' + ' | '.join(heads[:14]) + (' | …' if len(heads) > 14 else ''))
    out.append('\nDeclare per skill: applies (which sections) / not applicable (why). BODY-ONLY marks are the ones a description would have hidden.')
    return '\n'.join(out)


def selftest():
    d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, 'video-x'))
    open(os.path.join(d, 'video-x', 'SKILL.md'), 'w').write('---\nname: video-x\ndescription: >\n  Finishes generated video. Use when AI-generated footage needs a deliverable.\n---\n\n# X\n\n**What varies.** The tiers move; another stack keeps the order.\n\n## 1. Tier\n\n## 5b. Verify the mezzanine on any source, documentary footage included\n')
    rows = sweep(d, {'footage': 'existing'}, DEFAULT_SYN, ['video-'])
    ok = len(rows) == 1 and rows[0][1]['footage'] == 'BODY-ONLY' and rows[0][2].startswith('The tiers move') and len(rows[0][3]) == 2
    print(f"SELFTEST {'PASS' if ok else 'FAIL'}: {rows[0][1] if rows else rows}, what-varies parsed={bool(rows and rows[0][2])}, headers={len(rows[0][3]) if rows else 0}")
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--skills', default=os.path.expanduser('~/.claude/skills')); ap.add_argument('--axes', default='footage=existing')
    ap.add_argument('--only', default=','.join(DEFAULT_PREFIXES), help='skill-name prefixes; empty = every skill')
    ap.add_argument('--synonyms', action='append', default=[], help='value:term|term'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: selftest()
    axes = {kv.split('=')[0]: kv.split('=')[1] for kv in a.axes.split(',') if '=' in kv}
    syn = dict(DEFAULT_SYN)
    for sy in a.synonyms:
        v, terms = sy.split(':', 1); syn[v] = syn.get(v, []) + terms.split('|')
    print(render(sweep(a.skills, axes, syn, [p for p in a.only.split(',') if p]), axes))


if __name__ == '__main__':
    main()
