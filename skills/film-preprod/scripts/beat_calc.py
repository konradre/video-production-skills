#!/usr/bin/env python3
"""beat_calc.py — the Pratt beat calculator retargeted from pages to seconds. The feature convention is 1 page ≈ 1 minute,
so the calculator was always measuring TIME: beat_second = ceil(total_seconds × pct / 100). The anchors are Truby's 7-step
DNA (the minimal organic form — the right granularity for a short; the 22-step is a checklist only) on Pratt's shared
percentage axis with Weiland's arc roles; the SELF-REVELATION is held to 90 % (the "Verdict" anti-pattern: a
self-revelation at 25 % removes the hero's moral jeopardy for the rest of the film). Each row carries a SUBWORLD column
(Truby's Visual Seven Steps — a per-beat environment brief, the artefact a generation project needs) and is checked
against the venue's clip ceiling: a beat longer than the ceiling is designed as N clips cut on a blink or a caught breath.

  beat_calc.py <total seconds> [<more totals>…] [--ceiling 15] [--anchors anchors.json] [--md out.md]
anchors.json = [[pct, "step", "role", "subworld"], …] to override the seven defaults (e.g. a music video's hits as anchors).
"""
import argparse, json, math, sys

SEVEN = [
    (0, 'Weakness & Need', 'Characteristic Moment — Lie visible, sympathy FIRST, then the flaw', 'the enslaving world — small, warm, familiar'),
    (12, 'Desire', 'Inciting Event — the wish is made', 'a boundary crossed for the first time'),
    (25, 'Opponent', 'First Plot Point — the world stops enabling the Lie', "the opponent's world of power"),
    (50, 'Plan', 'Midpoint Moment of Truth — reaction flips to action', 'multiple locations — the road out'),
    (75, 'Battle', 'Third Plot Point — the ultimate Want-vs-Need choice', 'the smallest space — one light source, two people, an edge'),
    (90, 'SELF-REVELATION', 'Climax — the anagnorisis. THE HELD CLOSE-UP, the push-in dictated by the performance', 'the new world — the same street, unchanged, and now unbearable'),
    (95, 'New Equilibrium', 'Resolution — what the choice costs; the final image', '—'),
]


def beat_time(total, pct): return math.ceil(total * pct / 100.0)


def mmss(s): return f'{s // 60}:{s % 60:02d}'


def sheet(total, anchors, ceiling):
    rows = []
    for i, (pct, step, role, sub) in enumerate(anchors):
        start = beat_time(total, pct); end = beat_time(total, anchors[i + 1][0]) if i + 1 < len(anchors) else total
        rows.append((pct, start, end - start, step, role, sub))
    lines = [f'### {mmss(total)} ({total} s) — beat_second = ceil({total} × pct/100); clip ceiling {ceiling} s', '', '| % | in | dur | step | role | subworld | clips |', '|---|---|---|---|---|---|---|']
    for pct, start, dur, step, role, sub in rows:
        clips = math.ceil(dur / ceiling) if ceiling else 1
        note = f'{clips} (cut on a blink / a caught breath)' if clips > 1 else '1'
        lines.append(f'| {pct} | {mmss(start)} | {dur} s | **{step}** | {role} | {sub} | {note} |')
    sr = [r for r in rows if 'SELF' in r[3].upper()]
    if sr and sr[0][0] < 85: lines.append(f'\n⚠ the self-revelation sits at {sr[0][0]} % — Truby: hold it as late as possible (90 %); an early anagnorisis removes the moral jeopardy for everything after it')
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('totals', nargs='*', type=int); ap.add_argument('--ceiling', type=float, default=15, help="the venue's max clip length in seconds (0 = no check)"); ap.add_argument('--anchors'); ap.add_argument('--md')
    a = ap.parse_args(); anchors = [tuple(x) for x in json.load(open(a.anchors))] if a.anchors else SEVEN
    assert anchors == sorted(anchors, key=lambda r: r[0]) and anchors[0][0] == 0, 'anchors must start at 0 % and ascend'
    out = '\n\n'.join(sheet(t, anchors, a.ceiling) for t in (a.totals or [240, 300, 360]))
    print(out)
    if a.md: open(a.md, 'w', encoding='utf-8').write(out + '\n'); print(f'\nwrote {a.md}', file=sys.stderr)


if __name__ == '__main__':
    main()
