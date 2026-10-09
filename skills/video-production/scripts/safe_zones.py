#!/usr/bin/env python3
"""safe_zones.py — a project's declared safe band as `hyperframes check --caption-zone` zones (fractions of the frame).

The project declares its target platforms in `delivery-targets.json` — the nearest one at or above the given directory —
and the band is the union of those targets' keep-outs in `references/SAFE-AREAS.md` (the table below mirrors it;
--selftest compares the two). With no declaration it prints the strict union of the vertical AD bands and says so: a
recommendation, never a verdict. render_hyper.sh reads these zones before every render, report-only.

  safe_zones.py --from <composition or project dir>            zones, one per line "<zone>\\t<label>"; the band on stderr
  safe_zones.py --from <dir> --seek                            the zone runs' seek list: one point per second, never under 11
  safe_zones.py --targets meta:ad,tiktok:ad [--conditions …]   the same from a target list, no declaration file read
  safe_zones.py … --drawbox 1080x1920                          an ffmpeg filter that paints the band on a frame that size
  safe_zones.py --selftest

delivery-targets.json   {"targets": ["meta:ad", "youtube:organic"], "conditions": ["meta-disclaimer"], "keep_out": []}
  targets      <platform>:<placement> — platform meta | youtube | tiktok | x · placement ad | organic; [] = no platform UI
  conditions   meta-disclaimer (Meta's bottom band 768 px) · youtube-1to1 (YouTube in-feed compressed to 1:1: 420 px top)
  keep_out     the project's own measured keep-outs ("x0=…;y0=…;x1=…;y1=…"), used INSTEAD of the table
The table holds 9:16 numbers: another canvas aspect gets no table zones (its own keep_out still applies). The zones are
the bottom and top bands, each rail, and the side margins as strips between the bands. A zone flags a TEXT element
whose CENTRE lies in it — an image in a band and text straddling a zone's edge pass, so the frame read with the band
painted on (--drawbox) still runs on the delivered frames.
"""
import argparse, json, math, os, re, sys, tempfile

W0, H0 = 1080, 1920
TABLE = {   # px at 1080x1920 — the rows of references/SAFE-AREAS.md § The keep-outs (read 2026-10-09)
    'meta': {'top': 269, 'bottom': 672, 'left': 65, 'right': 65, 'rails': [], 'organic': False},
    'youtube': {'top': 288, 'bottom': 672, 'left': 48, 'right': 192, 'rails': [], 'organic': True},   # Shorts and every vertical ad
    'tiktok': {'top': 240, 'bottom': 660, 'left': 120, 'right': 120, 'rails': [(780, 840, 1080, 1260)], 'organic': False},
    'x': None,   # none published
}
CONDITIONS = {'meta-disclaimer': ('meta', {'bottom': 768}), 'youtube-1to1': ('youtube', {'top': 420, 'bottom': 420})}
STRICT = ['meta:ad', 'youtube:ad', 'tiktok:ad', 'x:ad']
DECL = 'delivery-targets.json'
MARKERS = ('.claude/skill-gate.json', 'RESUME.md', '.git')   # a production root's marks (video-production § 1, § 5): the search stops there
ZONE_RE = re.compile(r'^x0=([0-9.]+);y0=([0-9.]+);x1=([0-9.]+);y1=([0-9.]+)$')


def search_dirs(start, levels=2):
    """the directories read for a declaration: from <start> up to the project root — the first holding
    .claude/skill-gate.json, RESUME.md or .git — never $HOME or above; with no root found, <start> and two parents only, so
    a file in a shared parent never sets the band of every project below it. A bare .claude/ is no mark: tool scaffolds
    ship their own."""
    d = os.path.abspath(start); home = os.path.abspath(os.path.expanduser('~')); chain = []
    while not (d == home or home.startswith(d.rstrip(os.sep) + os.sep)):
        chain.append(d)
        if any(os.path.exists(os.path.join(d, m)) for m in MARKERS): return chain
        up = os.path.dirname(d)
        if up == d: break
        d = up
    return chain[:levels + 1]


def find_decl(start):
    for d in search_dirs(start):
        if os.path.isfile(os.path.join(d, DECL)): return os.path.join(d, DECL)
    return None


def comp_facts(start):
    """(width, height, duration) from <start>/index.html's root attributes; None where absent."""
    p = os.path.join(start, 'index.html')
    if not os.path.isfile(p): return None, None, None
    html = open(p, encoding='utf-8', errors='replace').read()
    g = lambda k: (re.search(rf'data-{k}="([0-9.]+)"', html) or [None, None])[1]
    w, h, dur = g('width'), g('height'), g('duration')
    return (int(float(w)) if w else None), (int(float(h)) if h else None), (float(dur) if dur else None)


def band(targets, conditions):
    for c in conditions:
        if c not in CONDITIONS: raise SystemExit(f'unknown condition {c!r} — known: {", ".join(CONDITIONS)}')
    b = {'top': 0, 'bottom': 0, 'left': 0, 'right': 0, 'rails': []}; notes = []
    for t in targets:
        p, _, pl = str(t).partition(':')
        if p not in TABLE: raise SystemExit(f'unknown platform {p!r} in {t!r} — known: {", ".join(TABLE)}')
        if pl not in ('ad', 'organic'): raise SystemExit(f'placement must be ad or organic: {t!r}')
        row = TABLE[p]
        if row is None: notes.append(f'{p}: no keep-out published — read the frames'); continue
        row = dict(row)
        for c in conditions:
            cp, over = CONDITIONS[c]
            if cp == p: row.update({k: max(row[k], v) for k, v in over.items()})
        if pl == 'organic' and not row['organic']:
            notes.append(f'{p}:organic — no published overlay; its ad band stands in (measure a live post at 1:1 → keep_out)')
        for k in ('top', 'bottom', 'left', 'right'): b[k] = max(b[k], row[k])
        b['rails'] += [r for r in row['rails'] if r not in b['rails']]
    return b, notes


def _lo(px, size): return (px * 10000) // size            # keep-outs round OUTWARD, never shrink
def _hi(px, size): return -((-px * 10000) // size)
def _f(n): return f'{n / 10000:.4f}'.rstrip('0').rstrip('.') or '0'
def zone(x0, y0, x1, y1, W=W0, H=H0): return f'x0={_f(_lo(x0, W))};y0={_f(_lo(y0, H))};x1={_f(_hi(x1, W))};y1={_f(_hi(y1, H))}'


def zones(b):
    out = []
    if b['bottom']: out.append((zone(0, H0 - b['bottom'], W0, H0), f"bottom band {b['bottom']} px"))
    if b['top']: out.append((zone(0, 0, W0, b['top']), f"top band {b['top']} px"))
    for x0, y0, x1, y1 in b['rails']: out.append((zone(x0, y0, x1, y1), f'rail x ≥ {x0}, y {y0}–{y1} px'))
    if b['right']: out.append((zone(W0 - b['right'], b['top'], W0, H0 - b['bottom']), f"right margin {b['right']} px, between the bands"))
    if b['left']: out.append((zone(0, b['top'], b['left'], H0 - b['bottom']), f"left margin {b['left']} px, between the bands"))
    return out


def usable(b):
    """the share of a 1080x1920 frame left clear by the band, rails included."""
    x0, x1, y0, y1 = b['left'], W0 - b['right'], b['top'], H0 - b['bottom']
    if x1 <= x0 or y1 <= y0: return 0.0
    area = (x1 - x0) * (y1 - y0)
    for rx0, ry0, rx1, ry1 in b['rails']:
        area -= max(0, min(x1, rx1) - max(x0, rx0)) * max(0, min(y1, ry1) - max(y0, ry0))
    return area / (W0 * H0)


def resolve(start=None, targets=None, conditions=()):
    """(zone list, the SAFE BAND line). A declaration's keep_out replaces the table; [] targets = no platform UI."""
    src, keep = 'the --targets list', None
    if targets is None:
        p = find_decl(start) if start else None
        if p is None:
            targets, conditions, sd = STRICT, (), search_dirs(start or '.')
            src = (f'no {DECL} from {os.path.abspath(start or ".")} up to {sd[-1] if sd else "(nothing searched)"} — the strict union '
                   'of the vertical AD bands (a recommendation: declare the targets at the project root)')
        else:
            try: d = json.load(open(p, encoding='utf-8'))
            except ValueError as e: raise SystemExit(f'{p}: not JSON ({e})')
            targets, conditions, keep, src = d.get('targets'), d.get('conditions') or [], d.get('keep_out'), f'declared in {p}'
            if not isinstance(targets, list): raise SystemExit(f'{p}: "targets" must be a list ([] = no platform UI)')
    W, H, _ = comp_facts(start) if start else (None, None, None)
    if keep:
        for z in keep:
            m = ZONE_RE.match(str(z))
            if not m or not all(0 <= float(v) <= 1 for v in m.groups()) or float(m[1]) > float(m[3]) or float(m[2]) > float(m[4]):
                raise SystemExit(f'keep_out zone {z!r}: use "x0=…;y0=…;x1=…;y1=…" with fractions 0–1, x0 ≤ x1, y0 ≤ y1')
        return [(z, 'keep_out (the project’s own)') for z in keep], f'SAFE BAND: {src} — {len(keep)} keep_out zone(s), the table not used'
    if not targets: return [], f'SAFE BAND: {src} — no platform UI declared: no zone read'
    if W and H and abs(W / H - W0 / H0) > 0.01:
        return [], f'SAFE BAND: {src} — the canvas is {W}x{H}, not 9:16: the keep-out table does not apply; declare keep_out zones for this aspect'
    b, notes = band(targets, list(conditions))
    zs = zones(b)
    line = (f"SAFE BAND: {src} — {', '.join(map(str, targets))}" + (f" + {', '.join(conditions)}" if conditions else '') +
            f": top {b['top']} · bottom {b['bottom']} · left {b['left']} · right {b['right']} px"
            + (f" + {len(b['rails'])} rail(s)" if b['rails'] else '') + f"; {usable(b) * 100:.0f} % of the frame clear")
    if any(str(t).startswith('youtube') for t in targets) and 'youtube-1to1' not in conditions:
        b1, _ = band(targets, list(conditions) + ['youtube-1to1']); line += f" ({usable(b1) * 100:.0f} % under YouTube's 1:1 crop)"
    line += ''.join(f'; {n}' for n in notes)
    return zs, line


def seek(start):
    _, _, dur = comp_facts(start) if start else (None, None, None)
    n = max(11, math.ceil(dur) + 1) if dur else 11
    return 'seek=' + ','.join(f'{i / (n - 1):.4f}'.rstrip('0').rstrip('.') or '0' for i in range(n))


def drawbox(zs, size):
    W, H = (int(v) for v in size.lower().split('x'))
    out = []
    for z, _ in zs:
        x0, y0, x1, y1 = (float(v) for v in ZONE_RE.match(z).groups())
        out.append(f'drawbox=x={round(x0 * W)}:y={round(y0 * H)}:w={round((x1 - x0) * W)}:h={round((y1 - y0) * H)}:color=red@0.35:t=fill')
    return ','.join(out)


def selftest():
    chk = []
    def ok(name, cond): chk.append((name, bool(cond)))
    zs, line = resolve(targets=STRICT)
    ok('the strict union is the documented five zones',
       [z for z, _ in zs] == ['x0=0;y0=0.65;x1=1;y1=1', 'x0=0;y0=0;x1=1;y1=0.15', 'x0=0.7222;y0=0.4375;x1=1;y1=0.6563',
                              'x0=0.8222;y0=0.15;x1=1;y1=0.65', 'x0=0;y0=0.15;x1=0.1112;y1=0.65'])
    ok('the strict union leaves 33 % clear, 29 % under the 1:1 crop', '33 % of the frame clear' in line and '(29 % under' in line)
    zs, _ = resolve(targets=['meta:ad'])
    ok('Meta alone: its own top and margins, no rail', [z for z, _ in zs] == ['x0=0;y0=0.65;x1=1;y1=1', 'x0=0;y0=0;x1=1;y1=0.1402',
                                                                       'x0=0.9398;y0=0.1401;x1=1;y1=0.65', 'x0=0;y0=0.1401;x1=0.0602;y1=0.65'])
    zs, _ = resolve(targets=['meta:ad'], conditions=['meta-disclaimer'])
    ok("Meta's disclaimer takes 40 % at the bottom", zs[0][0] == 'x0=0;y0=0.6;x1=1;y1=1')
    zs, line = resolve(targets=['x:ad'])
    ok('X alone publishes nothing: no zone, said so', zs == [] and 'no keep-out published' in line)
    zs, line = resolve(targets=['tiktok:organic'])
    ok('an organic target without numbers falls back to its ad band, said so', len(zs) == 5 and 'its ad band stands in' in line)
    for bad in (['vimeo:ad'], ['meta:paid']):
        try: resolve(targets=bad); ok(f'{bad[0]} refused', False)
        except SystemExit: ok(f'{bad[0]} refused', True)
    with tempfile.TemporaryDirectory() as r:
        comp = os.path.join(r, 'hyper', 'card-2p5s'); os.makedirs(comp)
        open(os.path.join(comp, 'index.html'), 'w').write('<div id="root" data-composition-id="c" data-width="2160" data-height="3840" data-duration="2.5"></div>')
        zs, line = resolve(start=comp)
        ok('no declaration → the strict union, labelled a recommendation', len(zs) == 5 and 'a recommendation' in line)
        json.dump({'targets': ['youtube:organic']}, open(os.path.join(r, DECL), 'w'))
        zs, line = resolve(start=comp)
        ok('the declaration is found above the composition, YouTube read on its own numbers', 'declared in' in line and [z for z, _ in zs] ==
           ['x0=0;y0=0.65;x1=1;y1=1', 'x0=0;y0=0;x1=1;y1=0.15', 'x0=0.8222;y0=0.15;x1=1;y1=0.65', 'x0=0;y0=0.15;x1=0.0445;y1=0.65'])
        deep = os.path.join(r, 'a', 'b', 'c', 'card'); os.makedirs(deep)
        ok('with no project root, a declaration three levels up is not read', find_decl(deep) is None)
        os.makedirs(os.path.join(comp, '.claude'))
        ok("a composition's own .claude/ does not stop the search", find_decl(comp) == os.path.join(r, DECL))
        os.makedirs(os.path.join(r, 'hyper', '.claude')); open(os.path.join(r, 'hyper', '.claude', 'skill-gate.json'), 'w').write('{}')
        ok('a project root stops the search below a parent declaration', find_decl(comp) is None)
        os.remove(os.path.join(r, 'hyper', '.claude', 'skill-gate.json')); open(os.path.join(r, 'RESUME.md'), 'w').write('x')
        ok('the declaration at the project root is read', find_decl(deep) == os.path.join(r, DECL))
        os.remove(os.path.join(r, 'RESUME.md'))
        json.dump({'targets': []}, open(os.path.join(r, DECL), 'w'))
        ok('targets [] = no zone read', resolve(start=comp)[0] == [])
        json.dump({'targets': ['meta:ad'], 'keep_out': ['x0=0;y0=0.7;x1=1;y1=1']}, open(os.path.join(r, DECL), 'w'))
        ok("keep_out replaces the table", [z for z, _ in resolve(start=comp)[0]] == ['x0=0;y0=0.7;x1=1;y1=1'])
        json.dump({'targets': ['meta:ad'], 'keep_out': ['x0=0;y0=1.2;x1=1;y1=1']}, open(os.path.join(r, DECL), 'w'))
        try: resolve(start=comp); ok('a malformed keep_out is refused', False)
        except SystemExit: ok('a malformed keep_out is refused', True)
        open(os.path.join(comp, 'index.html'), 'w').write('<div id="root" data-width="3840" data-height="2160" data-duration="60"></div>')
        json.dump({'targets': ['youtube:ad']}, open(os.path.join(r, DECL), 'w'))
        zs, line = resolve(start=comp)
        ok('a 16:9 canvas gets no table zones, said so', zs == [] and 'not 9:16' in line)
        ok('a 60 s composition is sampled once a second', seek(comp).count(',') == 60)
        open(os.path.join(comp, 'index.html'), 'w').write('<div id="root" data-width="2160" data-height="3840" data-duration="2.5"></div>')
        ok('a 2.5 s card is sampled at 11 points', seek(comp) == 'seek=0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1')
    ok('the drawbox paints the bottom band at 1080x1920', drawbox([('x0=0;y0=0.65;x1=1;y1=1', '')], '1080x1920') == 'drawbox=x=0:y=1248:w=1080:h=672:color=red@0.35:t=fill')
    md = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'references', 'SAFE-AREAS.md')
    if os.path.isfile(md):
        rows = {}
        for l in open(md, encoding='utf-8'):
            for p, lead in (('meta', '| Meta'), ('youtube', '| YouTube'), ('tiktok', '| TikTok'), ('x', '| X')):
                if l.startswith(lead): rows[p] = [c.strip() for c in l.strip().strip('|').split('|')]
        same = len(rows) == 4 and rows['x'][1] == '—'
        for p in ('meta', 'youtube', 'tiktok'):
            if p not in rows: same = False; continue
            nums = [int((re.match(r'\d+', c) or [0])[0] or 0) for c in rows[p][1:5]]
            same = same and nums == [TABLE[p][k] for k in ('top', 'bottom', 'left', 'right')]
        same = same and '768' in rows.get('meta', [''] * 3)[2] and '780' in ' '.join(rows.get('tiktok', [])) and '840–1260' in ' '.join(rows.get('tiktok', [])) and '420' in ' '.join(rows.get('youtube', []))
        ok('the table matches SAFE-AREAS.md, row by row', same)
    else:
        print('skip the SAFE-AREAS.md comparison: not beside this script')
    for name, v in chk: print(f"{'ok  ' if v else 'FAIL'} {name}")
    good = all(v for _, v in chk); print(f"SELFTEST {'PASS' if good else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})")
    return 0 if good else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--from', dest='start'); ap.add_argument('--targets'); ap.add_argument('--conditions', default='')
    ap.add_argument('--seek', action='store_true'); ap.add_argument('--drawbox', metavar='WxH'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: return selftest()
    if a.seek: print(seek(a.start)); return 0
    if not a.start and not a.targets: ap.error('--from <dir> or --targets <list>')
    tg = [t for t in a.targets.split(',') if t] if a.targets else None
    zs, line = resolve(a.start, tg, [c for c in a.conditions.split(',') if c])
    print(line, file=sys.stderr)
    if a.drawbox: print(drawbox(zs, a.drawbox)); return 0
    for z, label in zs: print(f'{z}\t{label}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
