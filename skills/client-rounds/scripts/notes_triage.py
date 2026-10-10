#!/usr/bin/env python3
"""notes_triage.py — the client's notes as a CURATED, NUMBERED list with NO action taken. Each item carries the client's own words, the spot it refers to (client numbering =
DELIVERY order, mapped with --map), a suggested class from the client's own vocabulary — CUT (edit-only: "no regeneration
needed", "just cut", "trim", "shorten"), RECYCLE (an older version's shot: "keep the scene from the original", "recycle",
"the version we had"), REBUILD (a regen: "rebuild", "regenerate", "new", "needs another pass"), APPROVE (a quoted
approval — freezes that spot), GATE (a product-proportion or likeness note — a pre-production gate from now on) — and a
blank column for the operator's answer. A causality note ("reads as two separate clips", "one doesn't cause the other")
is marked CAUSALITY: the take's own footage first, one gen last.

Each item also carries a suggested KIND — ERROR (objectively wrong: cut off, misspelled, a wrong number, a pop, a black
frame, out of sync) or TASTE (colour, pace, music, wording), `?` where the words decide neither — and an ANCHOR wherever
the words carry a timecode: "0:41" → a moment, "0:12-0:20" → a stretch; an aspect ratio such as 9:16 is never a time.
Every suggestion is a first guess the agent confirms against the delivered file (references/ROUND-PROTOCOL.md).
A paragraph that is no note — every part of it a greeting, a thank-you or a sign-off ("Hi team, thanks for the quick
turnaround!", "Cheers, talk soon — the team"), with no question, no request word, no spot, no timecode and no note word —
is CHAT: no spot (it neither takes nor passes one on), no kind, no answer; the ask and the compare page skip it. Anything
else that a greeting opens ("Hi, this one looks great!", "Hi, can you swap the voice?") stays a note to sort. The list
still shows a CHAT paragraph, so a misread is corrected per item.

With --out, the ROUND RECORD is written beside the list (<out stem>.json) and never overwritten — it collects the round's
answers: per note n, spot, class, kind, words, anchor, check (an ERROR's row), decision, answer (ROUND-PROTOCOL.md § The
round record). An approval starts anchored to the whole version and answered frozen.
Pattern for the kind and the check row: mortiflix-oss harness/GATES.md § Reading the owner's response.

  notes_triage.py --notes prompts/CLIENT-NOTES-<date>.txt [--map "#5=S01,#6=S02"] [--spot EP1] [--ids 'EP[0-9]+'] [--out prompts/CLIENT-ROUND-<date>.md]
--spot is the spot a note gets when no earlier note named one (a round about one video); --ids is the project's own
spot-id pattern (default: S, two digits, an optional letter), so a note naming EP2 maps there.
  notes_triage.py --selftest
"""
import argparse, json, os, re, subprocess, sys, tempfile

CLASSES = [   # order matters: the client's explicit "no regeneration" outranks a stray "rebuild"; a first guess the operator corrects per item
    ('APPROVE', r"looks solid|gold exactly|no changes|100% agree|keep that version|i'?m good with|perfect|looking great|all clear"),
    ('CAUSALITY', r"two separate clips|doesn'?t cause|one continuous|flow between|connect everything"),
    ('CUT', r"no regeneration|just cut|trim|shorten|cut (the|to|it)|a few cuts|hold(s)? that|too long|too soon"),
    ('RECYCLE', r"recycle|keep the scene|the original (clip|version|scene)|older version|copy paste|we already have"),
    ('GATE', r"actual product|misrepresent|proportion|look(s)? suspiciously like|likeness|to be safe"),
    ('REBUILD', r"rebuild|regen|re-?generate|another pass|new (shot|scene|gen)|replace (him|her|the)|recast|tweak (his|her) appearance|unexpectedly|instinctively"),
]
KINDS = [     # ERROR first: a note that names a defect is an error even when it also uses a taste word
    ('ERROR', r"cut off|cropped|touch(es|ing)? the edge|off.?screen|overlap|misalign|misspel|typo|spelled wrong|\bwrong\b|incorrect|\bmistake|"
              r"\bpops?\b|popping|\bclicks?\b|clipp(ed|ing)|distort|black (frame|flash|screen)|\bflash(es)?\b|frozen|freez|stutter|glitch|"
              r"out of sync|not in sync|lip.?sync|garbled|pixelat|artifact|watermark|blurr?y"),
    ('TASTE', r"colou?r|warm|cool|\bdark|bright|\bpac(e|ing)\b|\bdrags?\b|\bslow|\bfast|music|\bsong\b|wording|\btone\b|\bfeel|\bvibe|"
              r"prefer|rather|punch|energy|\bfont\b|\bstyle\b|bigger|smaller|too busy"),
]
TC = re.compile(r'(?<![\d:.])(\d{1,2}):([0-5]\d)(?:\.(\d{1,3}))?(?![\d:])')   # m:ss(.fff); h:mm:ss is not matched at all
NOT_TIME = {'9:16'}                                                             # the one aspect ratio that reads as m:ss
RANGE_SEP = re.compile(r'\s*(?:-|–|—|to|until|through|thru)\s*', re.I)
REQUEST = re.compile(r"\?|\b(can|could|would|please|swap|change|add|remove|replace|instead|but)\b", re.I)
GREETING = re.compile(r"(?i:hi|hello|hey|dear|good (?:morning|afternoon|evening))(?: (?:(?i:there|team|all|everyone|guys|folks|both)|[A-Z][\w'-]*)){0,2}")
THANKS = re.compile(r"(?i:thanks|thank you|many thanks)(?i: (?:so|very) much| a lot)?(?i: again)?(?: for (?P<what>.+))?")
OPENER = re.compile(r"(?i:(?:i )?hope (?:you(?:'re| are)(?: all)?|you all are|all is|everyone(?:'s| is)) (?:well|good|doing well)|(?:i )?hope you(?:'re| are) (?:having|doing) (?:a )?(?:great|good|nice) (?:day|week|weekend)|(?:i )?hope you had a (?:great|good|nice) (?:day|week|weekend)|happy (?:monday|tuesday|wednesday|thursday|friday)|good to hear from you)")
SIGN_OFF = re.compile(r"(?i:(?:talk|speak) soon|cheers|best|best regards|kind regards|regards|all the best|have a (?:great|good|nice) (?:day|weekend|week))")
SIGNATURE = re.compile(r"\s[—–-]\s*((?:the )?(?:team|crew)|[A-Z][\w'-]*(?: [A-Z][\w'-]*){0,2})\s*$")   # a name, or the team, after a dash
EVALUATIVE = {'great', 'love', 'loved', 'perfect', 'good', 'solid', 'nice', 'awesome', 'amazing', 'fine', 'approved', 'approve', 'ok', 'okay',
              'happy', 'like', 'liked', 'prefer', 'best', 'better', 'worse', 'fantastic', 'excellent', 'brilliant', 'beautiful', 'wonderful', 'exactly'}


def pleasantry(part):
    if GREETING.fullmatch(part) or OPENER.fullmatch(part) or SIGN_OFF.fullmatch(part): return True
    m = THANKS.fullmatch(part)
    if not m: return False
    what = (m.group('what') or '').lower().split()     # "thanks for the quick turnaround" — never "thanks for the cut, it looks great"
    return len(what) <= 6 and not EVALUATIVE & {w.strip(".,!'") for w in what}


IDS = r'S\d{2}[A-Z]?'   # the default spot id; a project with its own ids passes --ids


def is_chat(p, ids=IDS):
    """a paragraph that is no note: every part of it a greeting, a thank-you or a sign-off (a name after a dash), and it asks
    nothing, requests nothing and names no spot, timecode or note word — anything else stays a note to sort"""
    p = p.replace('’', "'")
    if REQUEST.search(p) or re.search(rf'#\d|\b(?:{ids})\b', p) or anchor_from(p) is not None \
            or any(re.search(rx, p, re.I) for _, rx in CLASSES + KINDS):
        return False
    body = SIGNATURE.sub('', ' '.join(p.split()))
    parts = [x.strip() for x in re.split(r"[.!,;:]|\s[—–-]\s", body) if x.strip()]
    return bool(parts) and all(pleasantry(x) for x in parts)


def anchor_from(text):
    """the first anchor the words carry: a stretch between two adjacent timecodes, else the first moment; None without one"""
    tcs = [(m.start(), m.end(), int(m.group(1)) * 60 + int(m.group(2)) + float('0.' + (m.group(3) or '0')))
           for m in TC.finditer(text) if m.group(0) not in NOT_TIME]
    for (s0, e0, t0), (s1, e1, t1) in zip(tcs, tcs[1:]):
        if RANGE_SEP.fullmatch(text[e0:s1]) and t1 > t0: return {'from': t0, 'to': t1, 'from_text': True}
    if not tcs: return None
    a = {'at': tcs[0][2], 'from_text': True}
    if len(tcs) > 1: a['also'] = [t for _, _, t in tcs[1:]]   # several moments named: the agent decides which one the note is about
    return a


def mmss(t):
    return f"{int(t // 60)}:{t % 60:05.2f}".rstrip('0').rstrip('.') if t % 1 else f"{int(t // 60)}:{int(t % 60):02d}"


def show(a):
    if not a: return '— (locate it)'
    if a.get('whole'): return 'whole version'
    if 'from' in a: return f"{mmss(a['from'])}–{mmss(a['to'])}"
    if 'paragraph' in a: return f"¶{a['paragraph']}"
    return mmss(a['at']) + (' (+ ' + ', '.join(mmss(t) for t in a['also']) + ')' if a.get('also') else '')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--notes'); ap.add_argument('--map', default=''); ap.add_argument('--out'); ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--spot', help='the spot a note gets when no earlier note named one (a round about one video)')
    ap.add_argument('--ids', default=IDS, help=f"the project's spot-id pattern (default {IDS}); a note naming one maps there")
    a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    if not a.notes: ap.error('--notes is required (or --selftest)')
    try: re.compile(a.ids)
    except re.error as ex: ap.error(f'--ids is not a regular expression: {ex}')
    ids = a.ids
    rec_path = os.path.splitext(a.out)[0] + '.json' if a.out else None
    if rec_path and os.path.exists(rec_path):
        sys.exit(f"{rec_path} exists — the round record collects this round's answers and is never overwritten; a new triage is a new round (another --out)")
    text = open(a.notes, encoding='utf-8').read()
    m = dict(kv.split('=') for kv in a.map.split(',') if '=' in kv)
    paras = [p.strip() for p in re.split(r'\n\s*\n|\n(?=\s*\(?\d+\))|\n(?=\s*#\d)', text) if len(p.strip()) > 20]   # blank lines, "(1)" items, "#5" items
    rows = []; spot = a.spot
    for p in paras:
        quotes = re.findall(r'[“"]([^”"]{6,})[”"]', p); short = (quotes[0] if quotes else p).replace('\n', ' ')[:160]
        if is_chat(p, ids):   # a greeting, a thank-you, a sign-off: no note — it neither takes nor passes on a spot
            rows.append({'spot': None, 'class': 'CHAT', 'kind': None, 'short': short, 'words': p, 'anchor': None}); continue
        ref = re.search(r'#(\d+)', p); spot = m.get('#' + ref.group(1), spot) if ref else spot
        for mm in re.finditer(rf'\b(?:{ids})\b', p): spot = mm.group(0)
        cls = next((c for c, rx in CLASSES if re.search(rx, p, re.I)), 'NOTE')
        kind = None if cls == 'APPROVE' else next((k for k, rx in KINDS if re.search(rx, p, re.I)), '?')
        anc = {'whole': True} if cls == 'APPROVE' else anchor_from(p)
        rows.append({'spot': spot or '?', 'class': cls, 'kind': kind, 'short': short, 'words': p, 'anchor': anc})
    out = [f'# Client round — {a.notes}', '', 'Curated, NO action taken. Operator answers per item (a number, a yes/no, or "best judgement").', '',
           '| # | spot | class | kind | anchor | the client\'s words | operator\'s answer |', '|---|---|---|---|---|---|---|']
    out += [f"| {i} | {r['spot'] or '—'} | {r['class']} | {r['kind'] or '—'} | {'—' if r['class'] == 'CHAT' else show(r['anchor'])} | {r['short']} |  |" for i, r in enumerate(rows, 1)]
    out += ['', 'Classes: CUT = edit-only (video-edit-edl) · RECYCLE = a shot from an older version (a new EDL, the old one untouched) · REBUILD = a regen (video-refs-continuity → video-gen-cost-gate, cost line first) · CAUSALITY = one continuous joke, the take\'s own footage first, one gen last · APPROVE = quoted into the ledger, the spot FREEZES · GATE = a pre-production gate from now on (product proportion, likeness) · CHAT = a greeting, a thank-you or a sign-off: no note, no spot, no answer — the ask skips it (correct it if it says something).',
            'Kind (a first guess — confirm each): ERROR = objectively wrong; it gets its check row (the check that missed it, or a proposed one) · TASTE = colour, pace, music, wording · ? = sort it. An anchor read from the words is confirmed against the delivered file; "— (locate it)" is still to find.']
    md = '\n'.join(out); print(md)
    if a.out:
        open(a.out, 'w', encoding='utf-8').write(md + '\n'); print(f'\nwrote {a.out}')
        items = [{'n': i, 'spot': r['spot'], 'class': r['class'], 'kind': r['kind'], 'words': r['words'], 'anchor': r['anchor'], 'check': None, 'decision': None,
                  'answer': {'status': 'frozen', 'why': f"approved: \"{r['short']}\""} if r['class'] == 'APPROVE' else None} for i, r in enumerate(rows, 1)]
        json.dump({'record': 'client-round/v1', 'notes': a.notes, 'list': a.out, 'map': m, 'spot_default': a.spot, 'ids': ids, 'items': items},
                  open(rec_path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print(f'wrote {rec_path} — the round record: fill each anchor, kind, ERROR check row and answer as the round goes')


def selftest():
    notes = ('Hi team, thanks so much for the quick turnaround on these!\n\n'
             '#5 — the price at 0:41 is wrong, it says $1,200 instead of $1,250\n\n'
             '#6 — the middle drags from 0:12 to 0:20, maybe a bit faster\n\n'
             '#7 — "looks solid", keep that version exactly as is\n\n'
             '#8 — the 9:16 version feels a little dark overall\n\n'
             '#9 — the logo pops in at 0:03 and again at 0:27.5, please fix\n\n'
             'Thanks again, talk soon — the team\n')
    with tempfile.TemporaryDirectory() as d:
        n = os.path.join(d, 'notes.txt'); open(n, 'w', encoding='utf-8').write(notes); out = os.path.join(d, 'round.md')
        args = [sys.executable, os.path.abspath(__file__), '--notes', n, '--map', '#5=S01,#6=S02,#7=S03,#8=S04,#9=S05', '--out', out]
        first = subprocess.run(args, capture_output=True, text=True)
        rec = json.load(open(os.path.join(d, 'round.json'), encoding='utf-8')) if first.returncode == 0 else {'items': []}
        again = subprocess.run(args, capture_output=True, text=True)
        n2 = os.path.join(d, 'notes2.txt'); open(n2, 'w', encoding='utf-8').write('Hi team, hope you\'re all well!\n\nthe voice is too quiet at 0:12, please lift it\n\n'
                                                                              'EP2 — the logo is cut off at the end\n\nmore on that one: the end card drags a little\n')
        r2 = subprocess.run([sys.executable, os.path.abspath(__file__), '--notes', n2, '--spot', 'EP1', '--ids', r'EP\d+', '--out', os.path.join(d, 'r2.md')], capture_output=True, text=True)
        rec2 = json.load(open(os.path.join(d, 'r2.json'), encoding='utf-8')) if r2.returncode == 0 else {}
    chat = [x for x in rec['items'] if x['class'] == 'CHAT']; it = {i: x for i, x in enumerate((x for x in rec['items'] if x['class'] != 'CHAT'), 1)}
    get = lambda n, k: (it.get(n) or {}).get(k)
    chk = [('the greeting and the sign-off are CHAT: no spot, no kind, no answer; the sign-off takes no spot from #9',
            [x['n'] for x in chat] == [1, 7] and all(x['spot'] is None and x['kind'] is None and x['answer'] is None for x in chat)),
           ('a note that opens with thanks or a greeting but names a time, a spot or a defect stays a note',
            not is_chat('Thanks! The logo pops at 0:03') and not is_chat('Hi — #5 looks solid') and not is_chat('Thanks, but the price is wrong')
            and is_chat('Cheers, talk soon')),
           ('a greeting-led request or approval stays a note; only a whole greeting, thank-you or sign-off is CHAT',
            not is_chat('Hi, can you swap the voice?') and not is_chat('Hi, this one looks great!') and not is_chat('Best version yet')
            and not is_chat('Thanks for the new version which looks great') and not is_chat('Hi love it') and is_chat('Best regards')
            and is_chat('Hello Sam,') and is_chat('Thanks so much for the quick turnaround on these!')),
           ("an email opener is CHAT: 'Hi team, hope you're well!', 'Hope all is well'", is_chat("Hi team, hope you’re well!") and is_chat('Hope all is well')
            and not is_chat("Hope you're well — the logo is cut off")),
           ('--spot gives unnumbered notes the one video; --ids reads the project\'s own ids', [x['spot'] for x in rec2.get('items', [])] == [None, 'EP1', 'EP2', 'EP2']),
           ('five notes, each mapped to its spot', [x['spot'] for x in it.values()] == ['S01', 'S02', 'S03', 'S04', 'S05']),
           ('#5: an ERROR, anchored at the moment 0:41', get(1, 'kind') == 'ERROR' and get(1, 'anchor') == {'at': 41.0, 'from_text': True}),
           ('#6: TASTE, a stretch 0:12–0:20', get(2, 'kind') == 'TASTE' and (get(2, 'anchor') or {}).get('from') == 12.0 and (get(2, 'anchor') or {}).get('to') == 20.0),
           ('#7: an approval, the whole version, answered frozen', get(3, 'class') == 'APPROVE' and get(3, 'kind') is None and get(3, 'anchor') == {'whole': True}
            and (get(3, 'answer') or {}).get('status') == 'frozen'),
           ('#8: 9:16 is an aspect ratio, not a time — no anchor', get(4, 'anchor') is None and get(4, 'kind') == 'TASTE'),
           ('#9: two moments named — the first anchors, the other is listed', get(5, 'kind') == 'ERROR' and get(5, 'anchor') == {'at': 3.0, 'from_text': True, 'also': [27.5]}),
           ('every note starts with no check row and no answer, the approval aside', all(x['check'] is None for x in rec['items']) and sum(x['answer'] is None for x in it.values()) == 4),
           ('the words are kept verbatim in the record', get(1, 'words', ) == '#5 — the price at 0:41 is wrong, it says $1,200 instead of $1,250'),
           ('a second run refuses to overwrite the round record', again.returncode != 0 and 'never overwritten' in again.stderr)]
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return 0 if ok else 1


if __name__ == '__main__':
    main()
