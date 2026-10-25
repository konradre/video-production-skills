#!/usr/bin/env python3
"""style_brief_check.py — the style brief read before any composition exists (references/STYLE-BRIEF.md; CRAFT.md § Style
comes from the subject). A rule phrased as a want gets answered the cheapest way, so the brief's own rules are checked.

  style_brief_check.py <style-brief.md> [--prev <last build's style-brief.md>]
  style_brief_check.py --selftest

FAIL (exit 1):
  sections   the eleven `## N. <name>` sections, numbered 1–11 in order, each carrying content
  block      one ```style-brief block holding every key: subject, adjectives (three), not (≥ 2 neighbours), palette
             (≥ 1 colour, every token #RRGGBB), palette_source, display_face (not the scaffold's `Display`, not a CSS
             generic family or a generic(…) form), background (one or two menu ids), transitions (menu ids: ≥ 2 kinds, ≥ 1 of object-wipe /
             push), motion_signature, special_moment, render (canvas-2d | dom-svg | webgl-pass, or webgl-3d — WARN)
  --prev     the last build's brief, for another subject: the background repeats it, the transitions are its set, or the
             two share TWO or more of palette · display face · background · motion signature (CRAFT: two subjects differ
             in at least three of four). Palette shared = at least half this brief's colours within ΔE*ab 10 (CIE76) of
             a last-build colour; face = same family; background = an id in common; signature = Jaccard ≥ 0.5 on words of
             four letters or more — a word-overlap HEURISTIC, so both lines are always printed for the reader.
WARN: a palette colour equal to one hyper_new.py writes into its scaffold (pure white and black aside); an unknown key;
render webgl-3d (a three.js scene — no determinism proof of one in this lane yet).
Fences follow CommonMark (``` or ~~~, closed by the same character at least as long): headings and a style-brief block
inside another fence are text, an empty fence is not content, and an HTML comment block (a line BEGINNING with <!--,
through the first -->) is neither content nor a place for the block. Exit 0 passes; 2 is a usage error, an unreadable or undecodable file, or a --prev brief whose block fails the
same field validation (unusable data never counts as differentiation).
"""
import argparse, math, re, sys
from pathlib import Path

SECTIONS = ['Essence, and what it is not', 'Materials and rendering', 'Colour logic', 'Type and captions', 'Motion quality',
            'Camera grammar', 'Sound palette', 'Native moves', 'Pitfalls of the medium', 'Renderer', 'Variation space']
BACKGROUNDS = ['still-ground', 'gradient-drift', 'blob-drift', 'living-texture', 'light-sweep', 'form-turn',
               'particles-rising', 'pattern-breathing', 'ghost-type', 'image-push', 'flow']     # CRAFT's menu, in its order
TRANSITIONS = ['overlap', 'object-wipe', 'push']
DEPTH = {'object-wipe', 'push'}
RENDERS = ['canvas-2d', 'dom-svg', 'webgl-pass']
KEYS = ['subject', 'adjectives', 'not', 'palette', 'palette_source', 'display_face', 'background', 'transitions',
        'motion_signature', 'special_moment', 'render']
GENERIC_FACES = {'serif', 'sans-serif', 'cursive', 'fantasy', 'monospace', 'system-ui', 'emoji', 'math', 'fangsong',
                 'ui-serif', 'ui-sans-serif', 'ui-monospace', 'ui-rounded', '-apple-system'}   # CSS Fonts 4 generics
UNVALIDATED_RENDERS = {'webgl-3d'}
HERE = Path(__file__).resolve().parent
FENCE_OPEN = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
FENCE_CLOSE = re.compile(r'^ {0,3}(`{3,}|~{3,})\s*$')
HTML_COMMENT_OPEN = re.compile(r'^ {0,3}<!--')
HEX6 = re.compile(r'^#[0-9A-Fa-f]{6}$')


def norm(s):
    s = s.lower().replace('&', 'and').replace('color', 'colour')
    return ' '.join(re.sub(r'[^a-z0-9 ]+', ' ', s).split())


def items(v):
    return [x.strip() for x in v.split(',') if x.strip()]


def parse(text):
    """one CommonMark-style pass: [(level, heading, has_content)] for every top-level `#`/`##` heading, and the info and
    lines of every TOP-LEVEL fence (a fence inside another is its text). An empty fence is not content, and neither is an
    HTML comment block — a line BEGINNING with `<!--`, through the first line holding `-->` — whose lines are never
    headings or fences. A `<!--` anywhere else (inline code, prose) is text."""
    heads, fences, cur, open_f, in_comment = [], [], None, None, False
    for line in text.splitlines() + [None]:
        if open_f is not None:
            m = FENCE_CLOSE.match(line) if line is not None else None
            if line is None or (m and m.group(1)[0] == open_f[0] and len(m.group(1)) >= open_f[1]):
                fences.append((open_f[2], open_f[3]))
                if cur is not None and any(l.strip() for l in open_f[3]): cur[2] = True
                open_f = None
            else: open_f[3].append(line)
            continue
        if line is None: break
        if in_comment:                                   # an HTML comment block (CommonMark type 2) runs to the first `-->`
            if '-->' in line: in_comment = False
            continue
        c = HTML_COMMENT_OPEN.match(line)
        if c:                                            # only a line that BEGINS with `<!--` opens one; elsewhere it is text
            in_comment = '-->' not in line[c.end():]
            continue
        m = FENCE_OPEN.match(line)
        if m and not (m.group(1)[0] == '`' and '`' in m.group(2)):
            open_f = [m.group(1)[0], len(m.group(1)), (m.group(2).split() or [''])[0], []]; continue
        h = re.match(r'^(#{1,2}) (.*\S)\s*$', line)
        if h:
            cur = [len(h.group(1)), h.group(2), False]; heads.append(cur); continue
        if cur is not None and line.strip(): cur[2] = True
    return heads, fences


def block(text):
    """the top-level ```style-brief block as {key: value}; None when absent, plus a list of FAILs inside it"""
    m = [lines for info, lines in parse(text)[1] if info == 'style-brief']
    if not m: return None, ['no ```style-brief block']
    errs = [] if len(m) == 1 else [f'{len(m)} style-brief blocks — one only']
    kv = {}
    for line in m[0]:
        if not line.strip() or line.lstrip().startswith('#') and ':' not in line: continue
        if ':' not in line: errs.append(f'block line without a key: {line.strip()!r}'); continue
        k, v = line.split(':', 1); k = k.strip().lower()
        if k in kv: errs.append(f'block key {k!r} given twice')
        kv[k] = v.strip()
    return kv, errs


def sections(text):
    """[(number or None, name, has_content)] for every top-level `## ` heading"""
    out = []
    for lvl, name, content in parse(text)[0]:
        if lvl != 2: continue
        m = re.match(r'^(\d+)\.\s+(.*)$', name)
        out.append([int(m.group(1)), m.group(2), content] if m else [None, name, content])
    return out


def lab(h):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(int(h[i:i + 2], 16)) for i in (1, 3, 5))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047; y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a, b):
    return math.dist(lab(a), lab(b))


def words(s):
    return {w for w in re.findall(r'[a-z]+', s.lower()) if len(w) >= 4}


def starter_colours():
    """every colour hyper_new.py writes into a scaffold, pure white and black aside (None when the script is absent)"""
    p = HERE / 'hyper_new.py'
    if not p.exists(): return None
    src = p.read_text(encoding='utf-8'); out = set()
    for h in re.findall(r'#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?![0-9A-Fa-f])', src):
        h = (''.join(c * 2 for c in h) if len(h) == 3 else h).lower()
        if h not in ('ffffff', '000000'): out.add('#' + h)
    return out


def fields(kv, starter=None):
    """[(level, message)] for a parsed block's values — one validation, used for the brief AND for --prev's brief"""
    res = []; F = lambda m: res.append(('FAIL', m)); Wn = lambda m: res.append(('WARN', m))
    for k in kv:
        if k not in KEYS: Wn(f'unknown block key {k!r}')
    for k in KEYS:
        if not kv.get(k): F(f'block key {k!r} missing or empty')
    adj = items(kv.get('adjectives', ''))
    if len(adj) == 1: adj = adj[0].split()
    if kv.get('adjectives') and len(adj) != 3: F(f'adjectives: {len(adj)} given — three, for the feeling to leave behind')
    nb = items(kv.get('not', ''))
    if kv.get('not') and len({norm(x) for x in nb} - {''}) < 2: F(f'not: {len(nb)} neighbour(s) — at least two, the last build always one')
    pal = items(kv.get('palette', ''))
    bad = [p for p in pal if not HEX6.match(p)]
    if bad: F(f'palette: {", ".join(bad)} — every colour as #RRGGBB')
    good = [p.lower() for p in pal if HEX6.match(p)]
    if kv.get('palette') and not good: F('palette: no #RRGGBB colour')
    if len(set(good)) < len(good): Wn('palette: a colour listed twice')
    for p in sorted(set(good) & (starter or set())):
        Wn(f'palette: {p} is a colour hyper_new.py writes into its scaffold — confirm it was read on the subject')
    face = kv.get('display_face', '')
    if face and (norm(face) in {norm(g) for g in GENERIC_FACES} | {'display'} or re.match(r'^\s*generic\s*\(', face, re.I)):
        F(f'display_face: "{face}" is the scaffold placeholder or a generic family — choose a face for the subject')
    bg = items(kv.get('background', ''))
    if kv.get('background'):
        if [b for b in bg if b not in BACKGROUNDS]: F(f'background: {", ".join(b for b in bg if b not in BACKGROUNDS)} not on the menu ({", ".join(BACKGROUNDS)})')
        if not 1 <= len(bg) <= 2 or len(set(bg)) < len(bg): F(f'background: {len(bg)} given — one (two only when it changes with a chapter)')
    tr = items(kv.get('transitions', ''))
    if kv.get('transitions'):
        if [t for t in tr if t not in TRANSITIONS]: F(f'transitions: {", ".join(t for t in tr if t not in TRANSITIONS)} not on the menu ({", ".join(TRANSITIONS)})')
        if len(set(tr)) < 2: F(f'transitions: {len(set(tr))} kind(s) — at least two')
        if not set(tr) & DEPTH: F('transitions: none with real depth — object-wipe or push')
    rnd = kv.get('render', '')
    if rnd in UNVALIDATED_RENDERS:
        Wn(f'render: {rnd} — a three.js scene has no determinism proof in this lane yet: prove it (det_check.py prove) and get it ruled before the build')
    elif rnd and rnd not in RENDERS:
        F(f'render: "{rnd}" — the HyperFrames lane is {" | ".join(RENDERS)} (webgl-3d WARNs); an offline renderer is outside it')
    return res


def check(text, prev_text=None, starter=None):
    """[(level, message)] for a brief's text (and the last build's, for --prev)"""
    res = []; F = lambda m: res.append(('FAIL', m)); Wn = lambda m: res.append(('WARN', m)); I = lambda m: res.append(('INFO', m))
    found = sections(text); numbered = [s for s in found if s[0] is not None]
    for s in found:
        if s[0] is None: Wn(f'extra section "## {s[1]}" — the brief has eleven fixed sections')
    nums = [s[0] for s in numbered]
    if nums != list(range(1, 12)):
        F(f'sections numbered {nums or "none"} — expected 1–11 in order')
    for n, name, content in numbered:
        if 1 <= n <= 11 and norm(name) != norm(SECTIONS[n - 1]): F(f'§ {n} is "{name}" — expected "{SECTIONS[n - 1]}"')
        if not content: F(f'§ {n} {name} is empty — a section that does not apply says why in one line')
    kv, errs = block(text)
    for e in errs: F(e)
    if kv is None: return res
    res += fields(kv, starter)
    if prev_text is None: return res
    pkv, perrs = block(prev_text)
    why = list(perrs) if pkv is not None else (perrs or ['no block'])
    if pkv is not None: why += [m for l, m in fields(pkv) if l == 'FAIL']
    if why:
        res.append(('USAGE', f"--prev: the last build's brief does not validate ({'; '.join(why)}) — unusable data cannot count as differing")); return res
    good = sorted({p.lower() for p in items(kv.get('palette', '')) if HEX6.match(p)}); face = kv.get('display_face', '')
    bg = items(kv.get('background', '')); tr = items(kv.get('transitions', ''))
    ppal = [p.lower() for p in items(pkv['palette'])]; pbg = items(pkv['background']); ptr = items(pkv['transitions'])
    if set(bg) & set(pbg): F(f'background repeats the last build ({", ".join(sorted(set(bg) & set(pbg)))}) — CRAFT: different from the last build')
    if tr and set(tr) == set(ptr): F(f'transitions are the last build\'s set ({", ".join(sorted(set(tr)))}) — CRAFT: different from the last build')
    near = [p for p in good if min(delta_e(p, q) for q in ppal) < 10]
    shared = {'palette': bool(good) and len(near) * 2 >= len(good),
              'display face': norm(face) == norm(pkv['display_face']),
              'background': bool(set(bg) & set(pbg)),
              'motion signature': False}
    a, b = words(kv.get('motion_signature', '')), words(pkv['motion_signature'])
    jac = len(a & b) / len(a | b) if a | b else 0.0; shared['motion signature'] = jac >= 0.5
    for k, v in shared.items():
        I(f'--prev {k}: {"SHARED" if v else "differs"}' + (f' ({len(near)} of {len(good)} colours within ΔE 10)' if k == 'palette' else '')
          + (f' (word overlap {jac:.2f})' if k == 'motion signature' else ''))
    I(f'--prev signature, this : {kv.get("motion_signature", "")}'); I(f'--prev signature, last : {pkv["motion_signature"]}')
    n = sum(shared.values())
    if n >= 2: F(f'shares {n} of 4 with the last build ({", ".join(k for k, v in shared.items() if v)}) — two subjects differ in at least three')
    return res


def selftest():
    ok, notes = True, []
    def t(name, cond):
        nonlocal ok
        ok &= bool(cond); notes.append(('ok  ' if cond else 'FAIL') + ' ' + name)
    ex = HERE.parent / 'references' / 'STYLE-BRIEF-EXAMPLE.md'
    doc = HERE.parent / 'references' / 'STYLE-BRIEF.md'
    if not ex.exists() or not doc.exists():
        print(f'SELFTEST FAIL: {ex.name} or {doc.name} not beside the script'); return 1
    base = ex.read_text(encoding='utf-8'); st = starter_colours() or set()
    res = lambda txt, prev=None: check(txt, prev, st)
    fails = lambda txt, prev=None: [m for l, m in res(txt, prev) if l == 'FAIL']
    says = lambda txt, frag, prev=None: any(frag in m for m in fails(txt, prev))   # the SPECIFIC diagnostic, not any FAIL
    sub = lambda a, b, txt=None: (txt or base).replace(a, b, 1)
    line = lambda key, val, txt=None: re.sub(rf'^{key}: .*$', f'{key}: {val}', txt or base, count=1, flags=re.M)
    t('the worked example passes', not fails(base))
    menu = set(re.findall(r'^\| `([a-z0-9-]+)` \|', doc.read_text(encoding='utf-8'), re.M))
    t('the menus in STYLE-BRIEF.md match the script', menu == set(BACKGROUNDS) | set(TRANSITIONS))
    t('the scaffold colours are read from hyper_new.py', '#ff4fa3' in st and '#111111' in st and '#ffffff' not in st)
    t('a missing section fails', says(sub('## 7. Sound palette', '### Sound palette'), 'expected 1–11'))
    t('an empty section fails', says(re.sub(r'(## 9\. Pitfalls of the medium\n)(.*?)(\n## 10\.)', r'\1\n\3', base, flags=re.S), '§ 9 Pitfalls of the medium is empty'))
    t('a section holding only an empty fence fails', says(re.sub(r'(## 9\. Pitfalls of the medium\n)(.*?)(\n## 10\.)', r'\1\n```\n```\n\3', base, flags=re.S), '§ 9 Pitfalls of the medium is empty'))
    t('a section holding only an HTML comment fails', says(re.sub(r'(## 9\. Pitfalls of the medium\n)(.*?)(\n## 10\.)', r'\1\n<!--\nnothing here yet\n-->\n\3', base, flags=re.S), '§ 9 Pitfalls of the medium is empty'))
    t('an inline-code `<!--` in prose is text, not a comment', not fails(base.replace('## 10. Renderer', 'Do not emit an unclosed `<!--` in the generated HTML.\n\n## 10. Renderer', 1)))
    t('a comment prefixed to the block fence hides the block, as CommonMark does', says(base.replace('```style-brief', '<!-- draft -->```style-brief', 1), 'no ```style-brief block'))
    t('a style-brief block inside an HTML comment is not the block', says(re.sub(r'```style-brief.*?\n```\n', lambda m: '<!--\n' + m.group(0) + '-->\n', base, count=1, flags=re.S), 'no ```style-brief block'))
    nested = re.sub(r'(## 11\. Variation space\n)', r'\1\n````text\n```\n## 12. Inside a fence\n```\n````\n', base)
    t('a heading inside a longer fence is text, not a section', not fails(nested))
    quoted = re.sub(r'```style-brief.*?\n```\n', lambda m: '````text\n' + m.group(0) + '````\n', base, count=1, flags=re.S)
    t('a style-brief block quoted inside another fence is not the block', says(quoted, 'no ```style-brief block'))
    t('a misnamed section fails', says(sub('## 3. Colour logic', '## 3. Colours'), 'expected "Colour logic"'))
    t('a short hex fails', says(sub('#8A4B1F', '#8A4B1'), 'every colour as #RRGGBB'))
    t('one colour passes (a single-ink title is legal)', not fails(line('palette', '#E0662A')))
    t('one neighbour fails', says(line('not', 'Watercolour brush'), 'at least two'))
    t('a punctuation placeholder is not a neighbour', says(line('not', 'the last build, —'), 'at least two'))
    t('two adjectives fail', says(line('adjectives', 'warm, floury'), 'three'))
    t('the scaffold face fails', says(line('display_face', 'Display'), 'placeholder or a generic family'))
    t('generic families fail (ui-monospace, ui-rounded, sans-serif, generic(kai), generic(fangsong))',
      all(says(line('display_face', g), 'generic family') for g in ('ui-monospace', 'ui-rounded', 'sans-serif', 'generic(kai)', 'generic(fangsong)')))
    t('a background off the menu fails', says(line('background', 'starfield'), 'not on the menu'))
    t('one transition kind fails on the COUNT (a depth kind, alone)', says(line('transitions', 'object-wipe'), 'kind(s) — at least two'))
    t('two kinds without depth fail on DEPTH', says(line('transitions', 'overlap, overlap'), 'none with real depth'))
    t('an offline renderer fails', says(line('render', 'blender'), 'offline renderer is outside it'))
    w3 = res(line('render', 'webgl-3d'))
    t('webgl-3d WARNs, does not fail', any(l == 'WARN' and 'three.js' in m for l, m in w3) and not [m for l, m in w3 if l == 'FAIL'])
    t('no block fails', says(re.sub(r'```style-brief.*?```', '', base, flags=re.S), 'no ```style-brief block'))
    t('an empty key fails', says(line('special_moment', ''), "'special_moment' missing or empty"))
    t('a key given twice fails', says(sub('render: canvas-2d', 'render: canvas-2d\nrender: dom-svg'), 'given twice'))
    warn = res(line('palette', '#8A4B1F, #FF4FA3'))
    t('a scaffold colour WARNs and does not fail', any(l == 'WARN' and 'scaffold' in m for l, m in warn) and not [m for l, m in warn if l == 'FAIL'])
    other = line('palette', '#123A6B, #9CC3E6, #F2F2EC, #2E8B57')
    other = line('display_face', 'Space Grotesk', other); other = line('background', 'gradient-drift', other)
    other = line('transitions', 'overlap, push', other)
    other = line('motion_signature', 'a ticker slide — columns step left one module per beat, linear', other)
    t('a different last build passes', not fails(base, other))
    t('the same brief as the last build fails on all three counts', says(base, 'background repeats', base) and says(base, 'transitions are the last', base) and says(base, 'shares 4 of 4', base))
    near = line('palette', '#8C4D21, #EDE4D4, #3D3835, #DE6428, #C7A268', other); near = line('display_face', 'fraunces', near)
    t('a near palette + the same face (two shared) fails', says(base, 'shares 2 of 4', near))
    t('only the face shared passes', not fails(base, line('display_face', 'FRAUNCES', other)))
    rew = line('motion_signature', 'slow swell, each element settling three frames after the last element, sine', other)
    t('a reworded signature is counted shared by word overlap', any('signature: SHARED' in m for l, m in res(base, line('display_face', 'Fraunces', rew))))
    bad_prev = line('palette', 'red, blue', near)
    t('an invalid last-build palette is a usage error, not a pass', any(l == 'USAGE' and 'every colour as #RRGGBB' in m for l, m in res(base, bad_prev)))
    t('an empty last-build palette (", ,") is a usage error', any(l == 'USAGE' and 'palette: no #RRGGBB colour' in m for l, m in res(base, line('palette', ', ,', near))))
    t('a generic last-build face is a usage error', any(l == 'USAGE' and 'generic family' in m for l, m in res(base, line('display_face', 'sans-serif', other))))
    t('a last-build key given twice is a usage error', any(l == 'USAGE' and 'given twice' in m for l, m in res(base, sub('render: dom-svg', 'render: dom-svg\nrender: canvas-2d', other.replace('render: canvas-2d', 'render: dom-svg')))))
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile('wb', suffix='.md', delete=False) as f: f.write(b'\xff\xfe# not utf-8\n')
    r = subprocess.run([sys.executable, __file__, f.name], capture_output=True, text=True); Path(f.name).unlink()
    t('an undecodable file exits 2', r.returncode == 2 and 'UNREADABLE' in r.stdout)
    for n in notes: print(' ', n)
    print(f"SELFTEST {'PASS' if ok else 'FAIL'}: {sum(n.startswith('ok') for n in notes)}/{len(notes)}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('brief', nargs='?'); ap.add_argument('--prev'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    if not a.brief: ap.error('a style-brief.md, or --selftest')
    try:
        text = Path(a.brief).read_text(encoding='utf-8'); prev = Path(a.prev).read_text(encoding='utf-8') if a.prev else None
    except (OSError, UnicodeDecodeError) as e:
        print(f'STYLE-BRIEF UNREADABLE — {e}'); sys.exit(2)
    res = check(text, prev, starter_colours())
    for lvl, msg in res: print(f'  {lvl:5s} {msg}')
    if any(l == 'USAGE' for l, _ in res): sys.exit(2)
    nf = sum(l == 'FAIL' for l, _ in res); nw = sum(l == 'WARN' for l, _ in res)
    print(f"STYLE-BRIEF {'FAIL (' + str(nf) + ')' if nf else 'PASS'}{f' — {nw} WARN to answer' if nw else ''} — {a.brief}"
          + (f' against {a.prev}' if a.prev else ''))
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
