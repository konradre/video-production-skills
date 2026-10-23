#!/usr/bin/env python3
"""card_read_time.py — the readable-time check for a card whose rows reveal one at a time (a data card over footage),
read from the plan's own numbers, never from the render (CRAFT.md § Readable time).

A card is any JSON object carrying `rows` and `reveal` (the timeline second each row starts to reveal), with `from` and
`to` (when the card starts and when its exit starts) on the object or on its parent — so a project plan is read as it
stands. Optional on the card: `title`, `subtitle`, `foot`, `reveal_s`, `exit_s`. A row is a string, or [label, value]
read as one line.

  title     holds from full display (from + reveal_s) to the first row's reveal: ≥ its floor
  each row  holds from full display (its reveal + reveal_s) to the next row's reveal: ≥ its floor
  last row  holds from full display to the exit (to − exit_s): ≥ its floor + --take-in (2 s), and ≥ --last-min — the
            viewer takes in the whole card once its last row lands; a last row revealed 1.4 s before the exit read
            as the card leaving mid-thought (2026-10-23)
  foot      (the source line, small print) on screen ≥ 2.5 s
  floor     max(0.70 s, 0.25 s + characters ÷ 17) — FAIL under it; the no-voice target 0.5 s + characters ÷ 13 (nobody
            reads a data card aloud) is printed as WARN when a hold falls under it

  card_read_time.py <plan.json> [--reveal-s 0.4] [--exit-s 0.4] [--take-in 2.0] [--last-min 4.5]
  card_read_time.py --selftest
--last-min is the project's (video-production WHAT-VARIES: 4.5 s for a data card in a film or a compilation; 0 turns it
off). Exit 1 on any FAIL, 2 when the file holds no card.
"""
import argparse, json, sys


def chars(x):
    return len(' '.join(str(v) for v in x) if isinstance(x, (list, tuple)) else str(x))


def floor_s(n): return max(0.70, 0.25 + n / 17.0)


def target_s(n): return 0.5 + n / 13.0


def cards(o, parent=None, path=''):
    if isinstance(o, dict):
        if 'rows' in o and 'reveal' in o:
            src = o if 'from' in o and 'to' in o else (parent or {})
            if 'from' in src and 'to' in src: yield path, o, float(src['from']), float(src['to'])
        for k, v in o.items(): yield from cards(v, o, f'{path}/{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from cards(v, parent, f'{path}[{i}]')


def check(card, t0, t1, a):
    """[(level, text)] for one card"""
    rs, xs = float(card.get('reveal_s', a.reveal_s)), float(card.get('exit_s', a.exit_s))
    rows, rev = card['rows'], [float(t) for t in card['reveal']]; out = []
    if len(rev) != len(rows): return [('FAIL', f"{len(rows)} rows but {len(rev)} reveal times")]
    if rev != sorted(rev) or (rev and (rev[0] < t0 or rev[-1] > t1)): return [('FAIL', f"reveal times {rev} out of order or outside the card {t0}–{t1}")]
    lines = ([('title', card['title'], t0, rev[0] if rev else t1 - xs)] if card.get('title') else [])
    for i, r in enumerate(rows):
        last = i == len(rows) - 1
        lines.append((f"row {i + 1}" + (' (last)' if last else ''), r, rev[i], (t1 - xs) if last else rev[i + 1]))
    for name, txt, a0, b0 in lines:
        n = chars(txt); hold = b0 - (a0 + rs); need = floor_s(n); tgt = target_s(n)
        if name.endswith('(last)'): need = max(need + a.take_in, a.last_min); tgt = max(tgt + a.take_in, a.last_min)
        lvl = 'FAIL' if hold < need - 1e-6 else 'WARN' if hold < tgt - 1e-6 else 'ok'
        out.append((lvl, f"{name:12s} {n:3d} ch  holds {hold:5.2f} s  floor {need:5.2f}  target {tgt:5.2f}  «{(' | '.join(map(str, txt)) if isinstance(txt, (list, tuple)) else txt)[:60]}»"))
    if card.get('foot'):
        on = t1 - t0
        out.append(('FAIL' if on < 2.5 else 'ok', f"{'foot':12s} on screen {on:5.2f} s (small print ≥ 2.5 s)"))
    return out


def selftest():
    a = argparse.Namespace(reveal_s=0.4, exit_s=0.4, take_in=2.0, last_min=4.5)
    good = {'title': 'A sample statistic', 'rows': [['First year', '12.0%'], ['Second year', '3.5%']], 'reveal': [2.0, 5.0], 'foot': 'Source: a table'}
    bad = dict(good, reveal=[2.0, 9.0])   # the last row lands 1.0 s before the exit at 10.4
    g = check(good, 0.0, 10.4, a); b = check(bad, 0.0, 10.4, a)
    ok = all(l != 'FAIL' for l, _ in g) and any(l == 'FAIL' and '(last)' in t for l, t in b)
    plan = {'events': [{'cutaways': [{'from': 0.0, 'to': 10.4, 'stat': good}]}]}
    ok &= len(list(cards(plan))) == 1
    print(f"SELFTEST {'PASS' if ok else 'FAIL'}: a well-timed card passes, a last row shown 1.0 s fails, a plan's nested card is found")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plan', nargs='?'); ap.add_argument('--reveal-s', type=float, default=0.4); ap.add_argument('--exit-s', type=float, default=0.4)
    ap.add_argument('--take-in', type=float, default=2.0); ap.add_argument('--last-min', type=float, default=4.5); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    if not a.plan: ap.error('a plan file, or --selftest')
    found = list(cards(json.load(open(a.plan, encoding='utf-8')))); nf = 0
    if not found: print(f'CARD-READ-TIME NONE — no object with rows + reveal and from/to in {a.plan}'); sys.exit(2)
    for path, c, t0, t1 in found:
        print(f"{c.get('title', path)}  [{t0:g}–{t1:g} s]")
        for lvl, txt in check(c, t0, t1, a):
            nf += lvl == 'FAIL'; print(f"  {lvl:4s} {txt}")
    print(f"CARD-READ-TIME {'FAIL (' + str(nf) + ')' if nf else 'PASS'} — {len(found)} card(s) in {a.plan}")
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
