#!/usr/bin/env python3
"""script_diff.py — the shot list (or the beat list) diffed against the CLIENT'S TEXT, by code, before the first prompt.
Three directions:
 (1) QUOTES — every quoted line in a beat ("…") must occur VERBATIM in the client's text (the script and every later client
     note, passed as --script), compared token by token after case, punctuation and whitespace are normalised. A quote that
     differs by ANY token — an added article, a dropped word, a changed contraction — FAILS and prints the difference; a beat
     that carries "ruled": "<the operator's ruling>" turns its deviation into a WARN (an approved spoken variant, a word the
     operator changed, an elided expletive, a column label the text extraction interleaved). A quote with no close match in
     the text is an INVENTED line (FAIL).
 (2) COVERAGE — every sentence of the covered text (--cover, default the FIRST --script file) must be covered by some beat's
     words. URL lines and table-of-contents lines are skipped; when the file is a whole brief, --cover-section START END
     scopes coverage to its script. An uncovered sentence is a beat the list forgot (WARN).
 (3) SEGMENTATION (--shots) — the inverse of coverage: a script sentence served by MORE THAN ONE row is a boundary the
     script never called for, and so is a continuity partition (beats sharing "partition" in the beat list) spread over
     more than one row. Either FAILS unless the row records why the action may split (`split: <why>` in the markdown row,
     "split_reason" in JSON — consistency across the split is not required: another room, another time; or the action
     outruns the generator's cap). --max-duration (READ from the vendor, never inferred from past takes) names whether the
     undeclared run fits one generation; without it a WARN says the cap is unknown.
Also: every beat that mentions the product's pieces must name its element id (--elements ELEM-FILL-<colour> …).
Exit 1 on any FAIL.

  script_diff.py --script prompts/<SPOT>-SCRIPT-client.txt [prompts/CLIENT-NOTES-*.txt …] --beats prompts/<SPOT>-beats.json
                 [--cover <file>] [--cover-section START_REGEX END_REGEX] [--elements ELEM-FILL-<colour>,…]
                 [--min-cover 0.6] [--shots prompts/r2v/<SPOT>-SHOTLIST.md|scenes.json] [--max-duration 30]
  script_diff.py --selftest
"""
import argparse, difflib, json, os, re, sys, tempfile

STOP = set('the a an and or of to in on at is are was were be been it its he she they them his her their this that with for as by from into out up down over under off then than so but not no yes we you i me my our your do does did have has had will would can could should just very really'.split())


def norm(s): return re.sub(r"[^a-z0-9' ]+", ' ', s.lower().replace('’', "'")).split()


def content(words): return [w for w in words if w not in STOP and len(w) > 2]


def num(v):
    try: return float(re.findall(r'\d+(?:\.\d+)?', str(v))[0])
    except Exception: return None


def best_window(q, t, index):
    """the span of text tokens t that best matches quote tokens q → (matched tokens, ratio, i0, i1): the most matched tokens
    first, then the ratio — so a changed contraction reads as a replacement, never as an insertion at the window's edge"""
    n = len(q); keys = content(q) or q; cands = set()
    for j, w in enumerate(q):
        if w in keys:
            for i in index.get(w, ()): cands.add(i - j)
    best = (0, 0.0, 0, 0)
    for s0 in cands:
        for d in range(-3, 4):
            i0 = max(0, s0 + d)
            for L in range(max(1, n - 3), n + 4):
                seg = t[i0:i0 + L]
                if not seg: continue
                sm = difflib.SequenceMatcher(None, q, seg, autojunk=False)
                key = (sum(b.size for b in sm.get_matching_blocks()), sm.ratio())
                if key > best[:2]: best = (key[0], key[1], i0, i0 + len(seg))
    return best


def describe(client, quote):
    out = []
    for tag, a0, a1, b0, b1 in difflib.SequenceMatcher(None, client, quote, autojunk=False).get_opcodes():
        if tag == 'insert': out.append('+' + ' '.join(quote[b0:b1]))
        elif tag == 'delete': out.append('-' + ' '.join(client[a0:a1]))
        elif tag == 'replace': out.append(' '.join(client[a0:a1]) + '→' + ' '.join(quote[b0:b1]))
    return ', '.join(out)


def script_text(text, section=None):
    text = text.replace('\f', '\n')   # a PDF's page break sits in front of the next page's first line; ^ never matches through it
    if section:
        m = re.search(section[0], text, re.I | re.M)
        if not m: sys.exit(f'--cover-section: START {section[0]!r} matches no line — nothing was scoped')
        e = re.search(section[1], text[m.end():], re.I | re.M)
        if not e: sys.exit(f'--cover-section: END {section[1]!r} matches no line after START — nothing was scoped')
        text = text[m.start():m.end() + e.start()]
    keep = [ln for ln in text.splitlines() if not re.search(r'https?://\S+', ln) and not re.search(r'\.{5,}\s*\d*\s*$', ln)]
    return '\n'.join(keep)


def sentences_of(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n{2,}', text) if len(content(norm(s))) >= 3]


def parse_shots(path, beat_ids):
    """rows = [{id, serves, duration, split, beats}] from a scenes/partitions JSON or the SHOTLIST.md table"""
    if path.endswith('.json'):
        S = json.load(open(path, encoding='utf-8')); S = S if isinstance(S, list) else (S.get('partitions') or S.get('shots') or S.get('scenes') or [])
        return [{'id': r.get('id'), 'serves': r.get('serves') or r.get('script') or '', 'duration': num(r.get('duration', r.get('seconds'))),
                 'split': r.get('split_reason', ''), 'beats': set(r.get('beats', []))} for r in S]
    rows, hdr = [], None
    for line in open(path, encoding='utf-8'):
        s = line.strip()
        if not s.startswith('|'): hdr = None; continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if hdr is None: hdr = [c.lower() for c in cells]; continue
        if set(''.join(cells)) <= set('-: '): continue

        def col(*names):
            for i, h in enumerate(hdr):
                if any(x in h for x in names): return cells[i] if i < len(cells) else ''
            return ''
        if not any('serves' in h or 'script line' in h for h in hdr): continue
        m = re.search(r'split:\s*([^|]+)', s)
        rows.append({'id': re.sub(r'[*`]', '', cells[0]), 'serves': col('line it serves', 'lines it serves', 'serves', 'script line'), 'duration': num(col('duration', 'seconds')),
                     'split': (m.group(1).strip() if m else col('split')).strip(), 'beats': {b for b in beat_ids if re.search(r'(?<![\w-])' + re.escape(b) + r'(?![\w-])', s)}})
    return rows


def run(a):
    text = '\n\n'.join(open(f, encoding='utf-8').read() for f in a.script); B = json.load(open(a.beats, encoding='utf-8')); fails = 0
    tnorm = ' '.join(norm(text)); tok = norm(text); index = {}
    for i, w in enumerate(tok): index.setdefault(w, []).append(i)
    cover = script_text(open(a.cover or a.script[0], encoding='utf-8').read(), a.cover_section); sentences = sentences_of(cover)
    beat_words = {b['beat']: set(content(norm(b.get('script', '') + ' ' + b.get('beat', '')))) for b in B['beats']}
    print(f"{a.beats}: {len(B['beats'])} beats vs {', '.join(a.script)}: {len(sentences)} covered sentences")
    # (1) quoted lines in beats must exist in the client's text, token for token
    for b in B['beats']:
        for q in re.findall(r'[“"]([^”"]{4,})[”"]', b.get('script', '')):
            qt = norm(q); qn = ' '.join(qt)
            if not qn or f' {qn} ' in f' {tnorm} ': continue
            _, r, i0, i1 = best_window(qt, tok, index)
            if r < 0.6: fails += 1; print(f"  FAIL {b['beat']}: INVENTED line — “{q}” is not in the client's text"); continue
            diff = describe(tok[i0:i1], qt); client = ' '.join(tok[i0:i1])
            if b.get('ruled'): print(f"  WARN {b['beat']}: not verbatim ({diff}) — ruled: {b['ruled']}")
            else: fails += 1; print(f"  FAIL {b['beat']}: NOT VERBATIM ({diff}) — the client wrote “{client}”; fix the quote, or record the operator's ruling as \"ruled\" on the beat")
    # (2) script sentences must be covered by a beat
    uncovered = 0
    for s in sentences:
        cw = set(content(norm(s)))
        if not cw: continue
        best = max(((len(cw & w) / len(cw), k) for k, w in beat_words.items()), default=(0, None))
        if best[0] < a.min_cover: uncovered += 1; print(f"  WARN no beat covers ({best[0]:.0%} best, {best[1]}): {s[:90]}")
    # (3) element ids on piece-bearing beats
    els = [e for e in a.elements.split(',') if e]
    if els:
        for b in B['beats']:
            sc = b.get('script', '').lower()
            if re.search(r'pieces?|blast|burst|drift|wall|fill', sc) and not any(e.lower() in sc for e in els):
                print(f"  WARN {b['beat']}: mentions the product's pieces but names no element id ({', '.join(els)})")
    # (4) segmentation — a boundary is a claim that the action stops; the script decides where, the cap whether it may
    splits = 0
    if a.shots:
        beat_ids = [b['beat'] for b in B['beats']]; part = {b['beat']: b.get('partition') for b in B['beats'] if b.get('partition')}
        rows = parse_shots(a.shots, beat_ids)
        if a.max_duration is None: print("  WARN the generator's maximum duration was not supplied (--max-duration) — read it from the vendor before any action is split")
        groups = {}
        for s in sentences:
            sn = ' '.join(norm(s)); scw = set(content(norm(s)))
            for i, r in enumerate(rows):
                for q in (re.findall(r'[“"]([^”"]{4,})[”"]', r['serves']) or [r['serves']]):
                    qn = ' '.join(norm(q)); qcw = set(content(norm(q)))
                    if qn and (qn in sn or (qcw and len(qcw & scw) / len(qcw) >= 0.8)): groups.setdefault(('sentence', s), set()).add(i); break
        for i, r in enumerate(rows):
            for bid in r['beats']:
                if part.get(bid): groups.setdefault(('partition', part[bid]), set()).add(i)
        for (kind, key), idx in groups.items():
            if len(idx) < 2: continue
            rs = [rows[i] for i in sorted(idx)]; ids = ', '.join(r['id'] for r in rs); what = f'the sentence “{key[:80]}”' if kind == 'sentence' else f'partition {key}'
            if all(r['split'] for r in rs[1:]):
                print(f"  INFO {what} is served by {ids} — split recorded: {'; '.join(r['split'] for r in rs[1:])}"); continue
            total = sum(r['duration'] or 0 for r in rs); known = all(r['duration'] for r in rs)
            if a.max_duration and known and total <= a.max_duration: why = f'{total:g} s together fits the {a.max_duration:g} s cap — it is ONE generation'
            elif a.max_duration and known: why = f'{total:g} s together outruns the {a.max_duration:g} s cap — record the split'
            else: why = 'record why the action may split, or make it one generation'
            splits += 1; print(f"  FAIL {what} is split across {ids}: {why}")
    fails += splits
    print(f"SCRIPT-DIFF {'FAIL' if fails else 'PASS'} — {fails - splits} quote failure(s), {uncovered} uncovered sentence(s), {splits} undeclared split(s)")
    return 1 if fails else 0


def selftest():
    script = 'If you are looking for meaningful connection, this is the place to find it.\n\nThe door opens: the visitor standing at the door, waiting.\n'
    beats = {'beats': [{'beat': 'B1', 'script': '“If you are looking for a meaningful connection”'}, {'beat': 'B2', 'script': '“The door opens: the visitor standing at the door”'}]}
    rows_split = ('## Partitions\n| id | beats | duration | the script lines it serves | mode |\n|---|---|---|---|---|\n'
                  '| S2 | B2 | 3 s | “The door opens” | refs |\n| S3 | B2 | 4 s | “the visitor standing at the door” | refs |\n')
    rows_ruled = rows_split.replace('“the visitor standing at the door” | refs |', '“the visitor standing at the door” | refs split: another room |')
    cases = []
    with tempfile.TemporaryDirectory() as d:
        sp, bp, tp = (os.path.join(d, n) for n in ('script.txt', 'beats.json', 'SHOTLIST.md'))
        open(sp, 'w').write(script); json.dump(beats, open(bp, 'w')); open(tp, 'w').write(rows_split)
        ns = lambda **k: argparse.Namespace(**{'script': [sp], 'beats': bp, 'cover': None, 'cover_section': None, 'elements': '', 'min_cover': 0.6, 'shots': None, 'max_duration': None, **k})
        cases.append(('an added article FAILS', run(ns()) == 1))
        tok = norm(script); index = {}
        for i, w in enumerate(tok): index.setdefault(w, []).append(i)
        q = norm("If you're looking for meaningful connection"); _, _, i0, i1 = best_window(q, tok, index)
        cases.append(('a changed contraction reads as a replacement', describe(tok[i0:i1], q) == "you are→you're"))
        beats['beats'][0]['ruled'] = 'the operator added the article'; json.dump(beats, open(bp, 'w'))
        cases.append(('the same deviation, ruled, PASSES with a WARN', run(ns()) == 0))
        cases.append(('one sentence served by two rows FAILS', run(ns(shots=tp, max_duration=30.0)) == 1))
        open(tp, 'w').write(rows_ruled)
        cases.append(('the same split, recorded, PASSES', run(ns(shots=tp, max_duration=30.0)) == 0))
    brief = 'About the app\nA business requirement.\n\fScript Scene one\nThe door opens.\n\fCharacter 1 Lead\nA role note.\n'
    scoped = script_text(brief, (r'^Script Scene one\s*$', r'^Character 1'))
    cases.append(('a section heading after a page break scopes coverage', 'business requirement' not in scoped.lower() and 'The door opens.' in scoped))
    try: script_text(brief, (r'^Script Scene two', r'^Character 1')); cases.append(('a START that matches nothing stops the run', False))
    except SystemExit: cases.append(('a START that matches nothing stops the run', True))
    for name, ok in cases: print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in cases); print(f"script_diff selftest {'PASS' if ok else 'FAIL'}"); return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--script', nargs='+'); ap.add_argument('--beats'); ap.add_argument('--elements', default=''); ap.add_argument('--min-cover', type=float, default=0.6)
    ap.add_argument('--cover', help='the file whose sentences must be covered (default: the first --script file)')
    ap.add_argument('--cover-section', nargs=2, metavar=('START', 'END'), help='regexes bounding the script inside a whole brief (page breaks read as line breaks; a regex that matches nothing stops the run)')
    ap.add_argument('--shots', help='the shot list (SHOTLIST.md) or a scenes/partitions JSON — enables the segmentation gate')
    ap.add_argument('--max-duration', type=float, help="the generator's maximum single-generation duration in seconds, READ from the vendor")
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    if not a.script or not a.beats: ap.error('--script and --beats are required')
    sys.exit(run(a))


if __name__ == '__main__':
    main()
