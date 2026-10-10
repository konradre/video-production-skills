#!/usr/bin/env python3
"""delivery_ask.py — the message that goes with a deliverable, in the form the operator reads on a phone between clips:
the file by its full path (a chat attachment only when ≤ 30 MiB — otherwise the path IS the delivery), its runtime and
size, the VO script table from the EDL (every placed line, verbatim), the CHECKS read from the run log, what changed
since the previous version — in a round, every note answered by its number —, the compare page, the residual doubts
WITH frame times (never a re-roll question), what is frozen, and the decisions as NUMBERED plain questions with the cost
inline. Rationale goes in the notes beside the clips, never inside the questions.

The checks are read, never retyped: from the run logs (--log, repeatable; --qc counts as one) the last EDL-CHECK and
BEAT-SHEET verdict line that names THIS EDL and the last QC-DELIVERABLE line that names THIS file. A check with no such
line REFUSES the ask — re-run it, or --na "BEAT-SHEET: <why>" for a check that does not apply. A FAIL is printed, never
withheld: QC's judgement rows are the operator's call.
--round prints this spot's notes (the round record's notes whose spot is the EDL's spot, or --spot, and every note on
"*" — all spots, answered once) by their numbers
with their answers, and the checks proposed for its errors. It REFUSES while one of them has no anchor, a kind still "?",
an ERROR with no check row, or no answer (done needs exactly what changed — never "addressed"; partly, not_done and
frozen need why), and while any note of the round has no spot — a CHAT paragraph (a greeting, a thank-you, a sign-off)
is no note and is skipped. A spot the round holds no note for gets a line saying so, never a refusal. A refusal exits 2
and writes no message.
Pattern for the notes answered by number and the refused missing check: mortiflix-oss harness/GATES.md § The loop.

  delivery_ask.py --root <project> --edl edit/<SPOT>-EDL-v9.json --deliv deliver/<file>.mp4 --winroot 'C:\\path\\to\\project'
                  --log logs/<SPOT>-v9-run.txt [--qc logs/qc.txt] [--na "BEAT-SHEET: <why>"] [--round prompts/CLIENT-ROUND-<date>.json]
                  [--spot S01] [--compare review/<SPOT>-v8-v9.html] [--changed "..."] [--doubt "0:41 a stray fleck on the lamp"]
                  [--frozen "S02 v4 (client: looks solid)"] [--q "Redo scene C by extending B (3 seeds, 37.5 cr) — yes or no?"] [--default "say defaults"]
  delivery_ask.py --selftest
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

CHECKS = ('EDL-CHECK', 'BEAT-SHEET', 'QC-DELIVERABLE')
VAGUE = {'addressed', 'fixed', 'done', 'changed', 'updated', 'handled', 'sorted', 'resolved', 'actioned'}


def read_checks(logs, edl, deliv):
    """{check: (verdict, log)} — the LAST verdict line each check printed for this EDL (EDL-CHECK, BEAT-SHEET) or this file
    (QC-DELIVERABLE); a line naming another version's file is not this one's"""
    got = {}
    for lg in logs:
        for line in open(lg, encoding='utf-8', errors='replace').read().splitlines():
            m = re.match(r'(EDL-CHECK|BEAT-SHEET|QC-DELIVERABLE) (PASS|FAIL\b.*?) — (.+)$', line.strip())
            if not m: continue
            name, parts = m.group(1), line.strip().split(' — ')
            path = (parts[1] if name == 'EDL-CHECK' else parts[-1]).strip()   # EDL-CHECK: verdict — <edl> — counts
            target = deliv if name == 'QC-DELIVERABLE' else edl
            if os.path.realpath(path) == os.path.realpath(target): got[name] = (parts[0][len(name) + 1:], lg)
    return got


def mmss(t):
    return f"{int(t // 60)}:{t % 60:05.2f}".rstrip('0').rstrip('.') if t % 1 else f"{int(t // 60)}:{int(t % 60):02d}"


def anchor_ok(a):
    return isinstance(a, dict) and (a.get('whole') is True or 'paragraph' in a or 'at' in a or ('from' in a and 'to' in a))


def show(a):
    if a.get('whole'): return 'whole'
    if 'from' in a and 'to' in a: return f"{mmss(a['from'])}–{mmss(a['to'])}"
    if 'paragraph' in a: return f"¶{a['paragraph']}"
    s = mmss(a['at'])
    if 'x' in a and 'y' in a: s += f" @{a['x']:.2f},{a['y']:.2f}" + (' (estimate)' if a.get('estimate') else '')
    return s


def check_ok(c):
    return isinstance(c, dict) and ((c.get('existing') and c.get('missed')) or (c.get('propose') and c.get('how') and c.get('owner')))


def round_problems(items):
    probs = []
    for it in items:
        n, cls, kind, an = it.get('n'), it.get('class'), it.get('kind'), it.get('answer') or {}
        if not anchor_ok(it.get('anchor')): probs.append(f"note {n}: no anchor — the moment, stretch, spot, paragraph or whole version it is about")
        if cls != 'APPROVE' and kind not in ('ERROR', 'TASTE'): probs.append(f"note {n}: kind {kind!r} — sort it ERROR or TASTE, or set its class to \"CHAT\" if it is no note (a greeting, a sign-off)")
        if kind == 'ERROR' and not check_ok(it.get('check')):
            probs.append(f"note {n}: an ERROR with no check row — {{existing, missed}} for the check that passed it, or {{propose, how, owner}}")
        st, change, why = an.get('status'), (an.get('change') or '').strip(), (an.get('why') or '').strip()
        if st not in ('done', 'partly', 'not_done', 'frozen'): probs.append(f"note {n}: no answer — done, partly, not_done or frozen"); continue
        if st == 'done' and (not change or change.lower().rstrip('.!') in VAGUE): probs.append(f"note {n}: done needs exactly what changed and where, never {change or 'nothing'!r}")
        if st != 'done' and not why: probs.append(f"note {n}: {st} needs why")
    return probs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl'); ap.add_argument('--deliv'); ap.add_argument('--winroot')
    ap.add_argument('--log', action='append', default=[]); ap.add_argument('--qc'); ap.add_argument('--na', action='append', default=[])
    ap.add_argument('--round'); ap.add_argument('--spot'); ap.add_argument('--compare')
    ap.add_argument('--changed', action='append', default=[]); ap.add_argument('--doubt', action='append', default=[]); ap.add_argument('--frozen', action='append', default=[])
    ap.add_argument('--q', action='append', default=[]); ap.add_argument('--default'); ap.add_argument('--chat-limit-mib', type=float, default=30)
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    if not (a.edl and a.deliv and a.winroot): ap.error('--edl, --deliv and --winroot are required (or --selftest)')
    os.chdir(a.root); e = json.load(open(a.edl, encoding='utf-8')); refuse = []
    # ---- the checks, read from the run log ----
    na = {}
    for item in a.na:
        name, _, why = item.partition(':'); name = name.strip().upper()
        if name not in CHECKS or not why.strip(): ap.error(f'--na takes "<{"|".join(CHECKS)}>: <why>", got {item!r}')
        na[name] = why.strip()
    logs = a.log + ([a.qc] if a.qc else [])
    for lg in logs:
        if not os.path.exists(lg): refuse.append(f'no run log at {lg}')
    got = read_checks([lg for lg in logs if os.path.exists(lg)], a.edl, a.deliv)
    for c in CHECKS:
        if c not in got and c not in na:
            refuse.append(f"{c}: no line in the run log names {a.deliv if c == 'QC-DELIVERABLE' else a.edl} — re-run it (a log from before the gates named their EDL reads as missing), or --na \"{c}: <why>\"")
    # ---- this spot's notes, answered by number ----
    notes = []; spot = a.spot or e.get('spot')
    if a.round:
        R = json.load(open(a.round, encoding='utf-8')); items = [it for it in R.get('items', []) if it.get('class') != 'CHAT']   # a greeting or a sign-off is no note
        unmapped = [it.get('n') for it in items if it.get('spot') in (None, '', '?')]
        if unmapped: refuse.append(f"notes {unmapped} have no spot — map the client's numbering (delivery order) before any ask of this round;"
                                   ' a greeting or a sign-off misread as a note: set its class to "CHAT"')
        notes = [it for it in items if it.get('spot') in (spot, '*')]
        refuse += round_problems(notes)
    if refuse:
        print(f'DELIVERY-ASK REFUSED — {len(refuse)} item(s), no message written:', file=sys.stderr)
        for r in refuse: print(f'  - {r}', file=sys.stderr)
        sys.exit(2)
    # ---- the message ----
    win = lambda p: a.winroot.rstrip('\\') + '\\' + p.replace('/', '\\')
    size = os.path.getsize(a.deliv); mib = size / 2 ** 20
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a.deliv], capture_output=True, text=True).stdout or 0)
    lines = [f"**{e.get('spot', '?')} v{e.get('version', '?')}** — `{win(a.deliv)}`", f"{dur:.1f} s · {mib:.1f} MiB ({size / 1e6:.1f} MB) · " + ('attached below' if mib <= a.chat_limit_mib else f'over {a.chat_limit_mib:.0f} MiB — open it at the path'), '']
    if a.changed: lines += ['**Changed since the previous version**'] + [f'- {c}' for c in a.changed] + ['']
    chat = [it for it in R.get('items', []) if it.get('class') == 'CHAT'] if a.round else []
    if chat: lines += [f"**Read as no note — check each** (`{a.round}`; a misread one: set its class back and sort it)"] + [f"- {it.get('n')} · «{' '.join((it.get('words') or '').split())[:110]}»" for it in chat] + ['']
    if a.round and not notes: lines += [f"**The client's notes** — none of this round's notes names {spot!r} (`{a.round}`)", '']
    if notes:
        lines += [f"**The client's notes, answered by number** (`{a.round}`)"]
        for it in notes:
            an = it['answer']; w = ' '.join(it.get('words', '').split()); w = w if len(w) <= 110 else w[:107] + '…'
            said = an['status'].replace('_', ' ') + (f": {an['change']}" if an.get('change') else '') + (f" — {an['why']}" if an.get('why') else '')
            lines.append(f"- **{it['n']}** · {show(it['anchor'])} · {it.get('kind') or it.get('class')} · «{w}» → {said}")
        props = [it for it in notes if it.get('kind') == 'ERROR']
        if props:
            lines += ['', '**Checks for this round\'s errors** (a proposal reaches its skill only through a reviewed change)']
            for it in props:
                c = it['check']
                lines.append(f"- note {it['n']} → {c['owner']}: {c['propose']} — {c['how']}" if c.get('propose') else f"- note {it['n']}: `{c['existing']}` ran and passed it — {c['missed']}")
        lines.append('')
    vo = e.get('audio', {}).get('vo', {}); placed = [(k, v) for k, v in vo.items() if isinstance(v, dict) and 'file' in v]
    if placed:
        lines += ['**VO script (as placed)**', '', '| line | at | text |', '|---|---|---|'] + [f"| {k} | {v['at']:.2f} | {v.get('text', '')} |" for k, v in sorted(placed, key=lambda kv: kv[1]['at'])] + ['']
    lines += ['**Checks** (read from the run log)']
    for c in CHECKS:
        if c in got: verdict, lg = got[c]; lines.append(f"- {c} {verdict} — `{lg}`" + (' ← a FAIL: the operator decides' if verdict.startswith('FAIL') else ''))
        else: lines.append(f'- {c} n/a — {na[c]}')
    lines.append('')
    if a.compare: lines += [f"**Compare** `{win(a.compare)}` — this version against the last, lined up by event", '']
    if a.doubt: lines += ['**Residual doubts (in the note, not a re-roll ask)**'] + [f'- {d}' for d in a.doubt] + ['']
    if a.frozen: lines += ['**Frozen (approved, untouched)**'] + [f'- {f}' for f in a.frozen] + ['']
    if a.q: lines += ['**Decisions**'] + [f'{i}. {q}' for i, q in enumerate(a.q, 1)] + ([f'({a.default})'] if a.default else []) + ['']
    print('\n'.join(lines))


def selftest():
    d = tempfile.mkdtemp(prefix='delivery-ask-selftest-')
    try:
        for sub in ('edit', 'deliver', 'logs', 'prompts'): os.makedirs(os.path.join(d, sub))
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-f', 'lavfi', '-i', 'color=c=black:s=64x112:r=24:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        os.path.join(d, 'deliver', 'S01-v9.mp4')], check=True)
        json.dump({'spot': 'S01', 'version': 'v9', 'events': [], 'audio': {'vo': {}}}, open(os.path.join(d, 'edit', 'S01-EDL-v9.json'), 'w'))
        open(os.path.join(d, 'logs', 'run.txt'), 'w').write(
            'EDL-CHECK PASS — edit/S01-EDL-v8.json — 9 events, runtime 30.000 s, 0 warning(s)\n'      # another version's: never this one's
            'EDL-CHECK FAIL (1) — edit/S01-EDL-v9.json — 9 events, runtime 30.000 s, 0 warning(s)\n'
            'EDL-CHECK PASS — edit/S01-EDL-v9.json — 9 events, runtime 30.000 s, 0 warning(s)\n'       # the LAST line for this EDL counts
            'BEAT-SHEET PASS — edit/S01-EDL-v8.json\n'
            'QC-DELIVERABLE FAIL (judgement: duration) — deliver/S01-v9.mp4\n')
        open(os.path.join(d, 'logs', 'old.txt'), 'w').write('EDL-CHECK PASS — 9 events, runtime 30.000 s, 0 warning(s)\nBEAT-SHEET PASS\n')
        good = [{'n': 1, 'spot': 'S01', 'class': 'NOTE', 'kind': 'ERROR', 'words': 'the price at 0:41 is wrong', 'anchor': {'at': 41.0},
                 'check': {'propose': 'a price on screen read back against the brief', 'how': 'OCR of the frames where a price shows', 'owner': 'video-finish-qc'},
                 'answer': {'status': 'done', 'change': 'the price corrected to $1,250, 0:39–0:44'}},
                {'n': 2, 'spot': 'S01', 'class': 'NOTE', 'kind': 'TASTE', 'words': 'drags from 0:12 to 0:20', 'anchor': {'from': 12.0, 'to': 20.0},
                 'check': None, 'answer': {'status': 'partly', 'change': 'the middle shot 1.2 s shorter', 'why': 'the hook stays: the client approved it'}},
                {'n': 3, 'spot': 'S02', 'class': 'APPROVE', 'kind': None, 'words': 'looks solid', 'anchor': {'whole': True}, 'check': None,
                 'answer': {'status': 'frozen', 'why': 'approved: "looks solid"'}},
                {'n': 5, 'spot': '*', 'class': 'NOTE', 'kind': 'TASTE', 'words': 'the music is too loud in all of them', 'anchor': {'whole': True}, 'check': None,
                 'answer': {'status': 'done', 'change': 'the bed 3 dB lower under every line, all spots'}},
                {'n': 6, 'spot': None, 'class': 'CHAT', 'kind': None, 'words': 'Hi team, thanks for the quick turnaround!', 'anchor': None, 'check': None, 'answer': None}]

        def rec(name, items):
            p = os.path.join(d, 'prompts', name); json.dump({'record': 'client-round/v1', 'items': items}, open(p, 'w')); return 'prompts/' + name

        def run(*extra):
            return subprocess.run([sys.executable, os.path.abspath(__file__), '--root', d, '--edl', 'edit/S01-EDL-v9.json', '--deliv', 'deliver/S01-v9.mp4',
                                   '--winroot', 'C:\\p', *extra], capture_output=True, text=True)
        bad_check = [dict(good[0], check=None)] + good[1:]
        vague = [dict(good[0], answer={'status': 'done', 'change': 'Addressed.'})] + good[1:]
        no_why = [good[0], dict(good[1], answer={'status': 'not_done'})] + good[2:]
        unmapped = good + [{'n': 4, 'spot': '?', 'class': 'NOTE', 'kind': 'TASTE', 'words': 'x', 'anchor': {'whole': True}, 'check': None, 'answer': None}]
        r_missing = run('--log', 'logs/run.txt')
        r_ok = run('--log', 'logs/run.txt', '--na', 'BEAT-SHEET: no beat list for this spot', '--round', rec('good.json', good), '--compare', 'review/S01-v8-v9.html')
        cases = [('a check with no line for THIS EDL refuses (BEAT-SHEET named only v8)', r_missing.returncode == 2 and 'BEAT-SHEET' in r_missing.stderr and not r_missing.stdout),
                 ('--na with why covers it; the ask is written', r_ok.returncode == 0 and 'BEAT-SHEET n/a — no beat list' in r_ok.stdout),
                 ('the LAST line for this EDL counts, a FAIL is shown', 'EDL-CHECK PASS — `logs/run.txt`' in r_ok.stdout and 'QC-DELIVERABLE FAIL (judgement: duration)' in r_ok.stdout
                  and 'the operator decides' in r_ok.stdout),
                 ("only this spot's notes and the all-spots one, by number, with their answers — the CHAT paragraph skipped", '- **1** · 0:41 · ERROR' in r_ok.stdout and '- **2** · 0:12–0:20 · TASTE' in r_ok.stdout
                  and '**3**' not in r_ok.stdout and '- **5** · whole · TASTE' in r_ok.stdout and '**6**' not in r_ok.stdout and 'Read as no note' in r_ok.stdout and '- 6 · «Hi team, thanks for the quick turnaround!»' in r_ok.stdout),
                 ('the proposed check is listed', 'note 1 → video-finish-qc: a price on screen' in r_ok.stdout),
                 ('the compare page by its operator path', 'C:\\p\\review\\S01-v8-v9.html' in r_ok.stdout)]
        for label, items, needle in (('an ERROR with no check row refuses', bad_check, 'note 1: an ERROR with no check row'),
                                     ('done "Addressed." refuses', vague, 'note 1: done needs exactly what changed'),
                                     ('not_done with no why refuses', no_why, 'note 2: not_done needs why'),
                                     ('an unmapped note in the round refuses, naming the CHAT fix', unmapped, 'misread as a note: set its class to "CHAT"'),
                                     ('a kind still ? names the CHAT fix', [dict(good[0], kind='?')] + good[1:], 'or set its class to "CHAT"')):
            r = run('--log', 'logs/run.txt', '--na', 'BEAT-SHEET: x', '--round', rec('t.json', items)); cases.append((label, r.returncode == 2 and needle in r.stderr))
        r_none = run('--log', 'logs/run.txt', '--na', 'BEAT-SHEET: x', '--round', rec('s02.json', [good[2]]))
        cases.append(('a spot the round holds no note for gets a line, never a refusal', r_none.returncode == 0 and "none of this round's notes names 'S01'" in r_none.stdout))
        r_old = run('--log', 'logs/old.txt', '--na', 'QC-DELIVERABLE: x')
        cases.append(('a log from before the gates named their EDL reads as missing', r_old.returncode == 2 and 'EDL-CHECK: no line' in r_old.stderr))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    for name, ok in cases: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in cases); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in cases)}/{len(cases)})"); return 0 if ok else 1


if __name__ == '__main__':
    main()
