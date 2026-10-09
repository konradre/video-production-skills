#!/usr/bin/env python3
"""check_summary.py — read `hyperframes check --json` reports and print what a reviewer must see. REPORT-ONLY: it always
exits 0 on findings (render_hyper.sh runs it before every render and never changes the render's exit code).

  check_summary.py renders/check.json [renders/check-zone1.json …]
  check_summary.py --selftest

Per report: one line of errors/warnings per section (lint, runtime, layout, motion, contrast) with layout's sample count;
every LINT error by code and message; every lint WARNING that is a render trap (HYPERFRAMES-CONTRACT § Silent traps: a
slot left blank, DOM measured in a callback, a substituted font, a repeat that overshoots or turns infinite, two tweens
writing one property) by code and message, and every lint warning counted by code; LAYOUT NOT SAMPLED when a lint error
stopped the layout audit (duration 0, no samples — the comp was never laid out); every caption_zone_collision as a ZONE line, because a zone hit is a WARNING
and the report's `ok` stays true; the other codes as counts; a section the run switched off (render_hyper.sh's zone
runs after the first: contrast) reads `off`, never 0E/0W. Known audit artefacts, not defects: per-word masked reveals
read as text_occluded / content_overlap; white text on a transparent layer reads as a contrast failure.
"""
import collections, json, os, sys, tempfile

SECTIONS = ('lint', 'runtime', 'layout', 'motion', 'contrast')
TRAP_WARNINGS = ('subcomposition_blanks_before_host', 'gsap_callback_dom_measurement', 'system_font_will_alias',
                 'gsap_repeat_floor_unclamped', 'gsap_repeat_ceil_overshoot', 'overlapping_gsap_tweens')   # hyperframes 0.8.18 lint codes


def summarise(path):
    out = []
    try:
        d = json.load(open(path))
    except (OSError, ValueError) as e:
        return [f"CHECK {os.path.basename(path)}: unreadable ({e}) — read check.err beside it"]
    head = []
    for s in SECTIONS:
        sec = d.get(s) or {}
        head.append(f"{s} off" if sec.get('enabled') is False else f"{s} {sec.get('errorCount', 0)}E/{sec.get('warningCount', 0)}W")
    lay = d.get('layout') or {}
    out.append(f"CHECK {os.path.basename(path)}: ok={d.get('ok')} · " + ' · '.join(head) + f" · layout samples {len(lay.get('samples') or [])}")
    lint = d.get('lint') or {}
    seen, warn = set(), collections.Counter()
    for f in lint.get('findings') or []:
        c = f.get('code')
        if f.get('severity') == 'error' and c not in seen:
            seen.add(c); out.append(f"  LINT ERROR {c}: {(f.get('message') or '')[:200]}")
        elif f.get('severity') == 'warning':
            warn[c] += 1
            if c in TRAP_WARNINGS and c not in seen:
                seen.add(c); out.append(f"  LINT WARN {c}: {(f.get('message') or '')[:200]}")
    if warn:
        out.append('  lint warnings: ' + ', '.join(f"{k}×{v}" for k, v in warn.most_common()))
    if lint.get('errorCount') and not (lay.get('samples') or []):
        out.append("  LAYOUT NOT SAMPLED — a lint error stopped the layout audit; fix the lint, then re-check")
    other = collections.Counter()
    for s in SECTIONS[1:]:
        for f in (d.get(s) or {}).get('findings') or []:
            if f.get('code') == 'caption_zone_collision':
                out.append(f"  ZONE t={f.get('time')}: {(f.get('message') or '')[:200]}")
            else:
                other[f"{f.get('code')}/{f.get('severity')}"] += 1
    if other:
        out.append('  other: ' + ', '.join(f"{k}×{v}" for k, v in other.most_common()))
    return out


def selftest():
    def sec(e=0, w=0, findings=(), **kw): return dict(errorCount=e, warningCount=w, findings=list(findings), **kw)
    lint_fail = {'ok': False, 'lint': sec(1, 2, [{'code': 'timeline_id_mismatch', 'severity': 'error', 'message': 'Timeline registered as "a" but no element has data-composition-id="a".'},
                                                {'code': 'subcomposition_blanks_before_host', 'severity': 'warning', 'message': '<div id="el-s01"> sub-composition ends at 3s but the composition runs to 5s'},
                                                {'code': 'gsap_infinite_repeat', 'severity': 'warning', 'message': 'GSAP tween uses `repeat: -1` (infinite)'}]),
                 'runtime': sec(), 'layout': sec(samples=[], duration=0), 'motion': sec(), 'contrast': sec()}
    zone_hit = {'ok': True, 'lint': sec(), 'runtime': sec(), 'motion': sec(), 'contrast': sec(enabled=False),
                'layout': sec(0, 2, [{'code': 'caption_zone_collision', 'severity': 'warning', 'time': 1.25, 'message': '<div> "Shop now" is centred in the reserved caption band.'},
                                     {'code': 'text_occluded', 'severity': 'error', 'time': 0.1, 'message': 'x'}], samples=[0, 1])}
    chk = []
    with tempfile.TemporaryDirectory() as r:
        a, b, c = (os.path.join(r, n) for n in ('lint.json', 'zone.json', 'bad.json'))
        json.dump(lint_fail, open(a, 'w')); json.dump(zone_hit, open(b, 'w')); open(c, 'w').write('{not json')
        la, lb, lc = summarise(a), summarise(b), summarise(c)
        chk.append(('a lint error is named', any('LINT ERROR timeline_id_mismatch' in l for l in la)))
        chk.append(('an unsampled layout is called out', any('LAYOUT NOT SAMPLED' in l for l in la)))
        chk.append(('a trap warning prints whole; every warning is counted; a non-trap warning is counted only',
                    any(l.startswith('  LINT WARN subcomposition_blanks_before_host') for l in la)
                    and any('gsap_infinite_repeat×1' in l and 'subcomposition_blanks_before_host×1' in l for l in la)
                    and not any(l.startswith('  LINT WARN gsap_infinite_repeat') for l in la)))
        chk.append(('a zone hit prints even though ok is true', any(l.startswith('  ZONE') and 'Shop now' in l for l in lb)))
        chk.append(('a sampled layout is not called unsampled', not any('LAYOUT NOT SAMPLED' in l for l in lb)))
        chk.append(('other codes are counted', any('text_occluded/error×1' in l for l in lb)))
        chk.append(('a switched-off section reads off, an active one its counts', 'contrast off' in lb[0] and 'contrast 0E/0W' in la[0]))
        chk.append(('an unreadable report is named, not fatal', any('unreadable' in l for l in lc)))
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return 0 if ok else 1


if __name__ == '__main__':
    if '--selftest' in sys.argv: sys.exit(selftest())
    if len(sys.argv) < 2: print(__doc__); sys.exit(0)
    for p in sys.argv[1:]:
        print('\n'.join(summarise(p)))
    sys.exit(0)
