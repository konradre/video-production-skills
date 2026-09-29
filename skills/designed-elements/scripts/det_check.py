#!/usr/bin/env python3
"""det_check.py — prove a code-rendered composition is a pure function of time: the same frame whoever draws it, in
whatever order, on whichever run. HYPERFRAMES-CONTRACT.md states the rules (a seeded PRNG, no clock readers, a tweened
distance instead of an accumulation); this is the instrument that checks them.

  source   read the composition's own script (inline <script> in index.html and compositions/**/*.html, the project's
           own .js/.mjs — never node_modules, *.min.js or assets/) for the clock and random readers: Math.random,
           Date / Date.now, performance.now, crypto randomness, requestAnimationFrame, setTimeout / setInterval.
           Comments are ignored; a deliberate use carries `det-ok: <reason>` in a comment on its line. It CANNOT see
           an accumulation (`x += v` in an onUpdate) — only the render proof can.
  frames   compare two PNG sequences of one composition frame by frame on the decoded pixels, and say which scene
           (data-start / data-duration in index.html, with --project) each difference falls in, plus the status of
           each scene's first, middle and last frame.
  prove    source, then render the composition TWICE as a png-sequence on the render host with different --workers
           splits (default 1 and 3) and compare. Each worker is a fresh page that starts cold at its own frames, so a
           frame that depends on the frames drawn before it differs across the split, and a frame that reads a clock
           or an unseeded random differs everywhere. The frames stay where they were rendered — <remote-dir>/.det/<name>/
           <stamp>/w<N> on the host (a 2160x3840 proof is gigabytes), <project>/det/<stamp>/w<N> locally — the compare
           runs there, and only the report travels. Nothing is deleted; the operator removes the proof frames.

  det_check.py source <project>
  det_check.py frames <dirA> <dirB> [--fps 24] [--project <project>] [--tolerance 0]
  det_check.py prove <project> [--host <ssh host>] [--workers 1,3] [--fps 24] [--remote-dir ~/hyper] [--remote-python python3]
  det_check.py --selftest

--tolerance N accepts a per-channel difference up to N code values (a WebGL layer on a software rasteriser can differ by
one or two between runs; a 2D canvas or DOM composition holds 0). Exit 0 PASS, 1 FAIL, 2 unusable input. Sentinel
DET-CHECK PASS|FAIL.
"""
import argparse, datetime, glob, os, re, subprocess, sys, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.realpath(__file__))
RULES = [
    (r'\bMath\s*\.\s*random\b', 'unseeded random — draw from mulberry32(seed)'),
    (r'\bDate\s*\.\s*now\b|\bnew\s+Date\b|\bDate\s*\(', 'wall clock — pass the timeline time in'),
    (r'\bperformance\s*\.\s*now\b', 'wall clock — pass the timeline time in'),
    (r'\bcrypto\s*\.\s*(?:getRandomValues|randomUUID)\b', 'unseeded random — draw from mulberry32(seed)'),
    (r'\brequestAnimationFrame\b', 'a draw loop outside the timeline — draw from the tweened progress'),
    (r'\bset(?:Interval|Timeout)\b', 'a wall-clock timer — tween the value instead'),
    (r'''\bgetContext\s*\(\s*['"]2d['"]\s*\)''', "a 2D canvas without {willReadFrequently:true} — Chrome changes its raster path after the first presented frame, so each worker's first frame differs"),
]
SKIP_DIRS = {'node_modules', 'renders', 'frames', 'det', 'assets', '.git'}


def _strip_js(code):
    """Blank comments but keep line numbers; a `//` preceded by ':' (a URL) or inside a quote is not a comment."""
    code = re.sub(r'/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), code, flags=re.S)
    out = []
    for line in code.split('\n'):
        q, i, cut = None, 0, None
        while i < len(line):
            c = line[i]
            if q:
                if c == '\\': i += 1
                elif c == q: q = None
            elif c in '"\'`': q = c
            elif line.startswith('//', i) and (i == 0 or line[i - 1] != ':'): cut = i; break
            i += 1
        out.append(line if cut is None else line[:cut])
    return '\n'.join(out)


def _scripts(path):
    """(first line number, script text) for each inline <script> without a src; HTML comments blanked first."""
    html = open(path, encoding='utf-8', errors='replace').read()
    html = re.sub(r'<!--.*?-->', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), html, flags=re.S)
    for m in re.finditer(r'<script\b([^>]*)>(.*?)</script>', html, flags=re.S | re.I):
        if re.search(r'\bsrc\s*=', m.group(1), flags=re.I): continue
        yield html.count('\n', 0, m.start(2)) + 1, m.group(2)


def scan_source(project):
    """Return (files scanned, findings [(file, line, rule, text, allowed-reason)])."""
    units = []
    for root, dirs, files in os.walk(project):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            p = os.path.join(root, f)
            if f.endswith('.html'): units += [(p, ln, s) for ln, s in _scripts(p)]
            elif f.endswith(('.js', '.mjs')) and not f.endswith('.min.js'): units.append((p, 1, open(p, encoding='utf-8', errors='replace').read()))
    found, files = [], sorted({u[0] for u in units})
    for p, ln0, raw in units:
        rl = raw.split('\n'); code = _strip_js(raw).split('\n')
        for i, line in enumerate(code):
            for rx, why in RULES:
                for m in re.finditer(rx, line):
                    ok = re.search(r'det-ok:\s*(.+)', rl[i]); found.append((os.path.relpath(p, project), ln0 + i, why, m.group(0), ok.group(1).strip() if ok else None))
    return files, found


def scenes_of(project, fps):
    """[(name, first frame, last frame)] from the elements carrying data-start + data-duration (the root, audio and a
    whole-length captions track excluded)."""
    idx = os.path.join(project, 'index.html')
    if not os.path.exists(idx): return []
    html = open(idx, encoding='utf-8', errors='replace').read(); out = []
    for m in re.finditer(r'<(\w+)\b([^>]*\bdata-start="([\d.]+)"[^>]*)>', html):
        tag, attrs = m.group(1).lower(), m.group(2)
        d = re.search(r'\bdata-duration="([\d.]+)"', attrs)
        if not d or tag in ('audio', 'video') or 'data-width=' in attrs or 'captions' in attrs: continue
        name = (re.search(r'\bdata-composition-id="([^"]+)"', attrs) or re.search(r'\bid="([^"]+)"', attrs) or re.search(r'\bclass="([^"]+)"', attrs))
        s, e = float(m.group(3)), float(m.group(3)) + float(d.group(1))
        out.append((name.group(1) if name else tag, int(round(s * fps)), max(int(round(s * fps)), int(round(e * fps)) - 1)))
    return out


def _pngs(d):
    return sorted(glob.glob(os.path.join(d, '*.png')))


def compare(dir_a, dir_b, fps=24.0, project=None, tol=0):
    """Print the frame comparison; return (ok, mismatched frame indexes) or (None, msg) when the input is unusable."""
    A, B = _pngs(dir_a), _pngs(dir_b)
    if not A or not B: return None, f'no PNG frames in {dir_a if not A else dir_b}'
    if len(A) != len(B): print(f'FAIL frame count differs: {len(A)} in {dir_a} vs {len(B)} in {dir_b}'); return False, []
    bad = []
    for i, (fa, fb) in enumerate(zip(A, B)):
        a, b = np.asarray(Image.open(fa)), np.asarray(Image.open(fb))
        if a.shape != b.shape: bad.append((i, 255, 1.0, f'shape {a.shape} vs {b.shape}')); continue
        if np.array_equal(a, b): continue
        dif = np.abs(a.astype(np.int16) - b.astype(np.int16)); mx = int(dif.max())
        if mx > tol: bad.append((i, mx, float((dif.max(axis=-1) if dif.ndim == 3 else dif).astype(bool).mean()), ''))
    sc = scenes_of(project, fps) if project else []
    where = lambda i: next((n for n, f0, f1 in sc if f0 <= i <= f1), '-')
    print(f'{len(A)} frames @ {fps:g} fps compared on decoded pixels (tolerance {tol}): {len(bad)} differ')
    idx = {b[0] for b in bad}
    for n, f0, f1 in sc:
        fm = (f0 + f1) // 2; k = sum(1 for i in idx if f0 <= i <= f1)
        st = ' '.join(f"{lab} f{f}={'DIFF' if f in idx else 'same'}" for lab, f in (('first', f0), ('middle', fm), ('last', f1)))
        print(f'  scene {n}: frames {f0}-{f1}, {k} differ · {st}')
    for i, mx, frac, note in bad[:12]:
        print(f'  DIFF frame {i} (T={i / fps:.3f} s, scene {where(i)}): max {mx} code values, {frac:.1%} of pixels{" " + note if note else ""}')
    if len(bad) > 12: print(f'  … {len(bad) - 12} more')
    return not bad, sorted(idx)


def report_source(project):
    files, found = scan_source(project)
    live = [f for f in found if not f[4]]
    print(f'source: {len(files)} file(s) with script scanned under {project}')
    for rel, ln, why, txt, allowed in found:
        print(f"  {'ALLOWED' if allowed else 'FAIL'} {rel}:{ln} {txt} — {why}{' (det-ok: ' + allowed + ')' if allowed else ''}")
    if not files: print('  (no script found — nothing to read; the render proof still applies)')
    print('  accumulation (x += v in an onUpdate) is invisible to this scan — the render proof catches it')
    return not live


def prove(a):
    project = os.path.abspath(a.project); name = os.path.basename(project); parent = os.path.dirname(project)
    if not os.path.exists(os.path.join(project, 'index.html')): print(f'no composition at {project}/index.html'); return 2
    workers = [int(w) for w in a.workers.split(',')]
    if len(set(workers)) < 2: print('--workers needs two different counts (e.g. 1,3)'); return 2
    if not a.host and _pngs(os.path.join(project, 'frames')): print(f'{project}/frames holds PNGs and a local render overwrites them — move them first'); return 2
    src_ok = report_source(project)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S'); rsh = os.path.join(HERE, 'render_hyper.sh')
    # the proof frames live OUTSIDE the project on a host (render_hyper.sh --push mirrors the project with --delete) and
    # stay on the machine that rendered them: a 2160x3840 proof is gigabytes, so only the report travels
    base = f'{a.remote_dir}/.det/{name}/{stamp}' if a.host else os.path.join(project, 'det', stamp)
    sh = lambda c: subprocess.run(['ssh', '-o', 'BatchMode=yes', a.host, c], capture_output=True, text=True)
    if a.host:   # a png-sequence render empties <name>/frames first: never on a project whose frames are a deliverable
        f = sh(f'ls {a.remote_dir}/{name}/frames/ 2>/dev/null | grep -c "\\.png$"')
        if f.stdout.strip() not in ('', '0'): print(f'{a.host}:{a.remote_dir}/{name}/frames holds {f.stdout.strip()} PNGs and the render empties it — move them first, or prove a copy'); return 2
    for k, w in enumerate(workers):
        cmd = ['bash', rsh, '--dir', parent, '--name', name, '--format', 'png-sequence', '--fps', str(a.fps), '--workers', str(w), '--hf-version', a.hf_version]
        if a.host: cmd += ['--host', a.host, '--remote-dir', a.remote_dir] + (['--push'] if k == 0 and not a.no_push else [])
        print(f'render {k + 1}/{len(workers)}: --workers {w}', flush=True)
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or 'RENDER-END' not in r.stdout: print(r.stdout[-1500:], r.stderr[-800:]); print(f'render with --workers {w} failed — no proof'); return 2
        if a.host:
            m = sh(f'mkdir -p {base} && mv {a.remote_dir}/{name}/frames {base}/w{w} && ls {base}/w{w} | wc -l')
            if m.returncode != 0: print(m.stderr[-800:]); return 2
        else:
            os.makedirs(base, exist_ok=True); os.rename(os.path.join(project, 'frames'), os.path.join(base, f'w{w}'))
    dirs = [f'{base}/w{w}' for w in workers]; ok_all = src_ok
    if a.host:
        up = subprocess.run(['ssh', '-o', 'BatchMode=yes', a.host, f'cat > {a.remote_dir}/.det/det_check.py'], stdin=open(os.path.realpath(__file__), 'rb'), capture_output=True)
        if up.returncode != 0: print(up.stderr[-800:].decode(errors='replace')); return 2
    for other in dirs[1:]:
        print(f'compare {dirs[0]} vs {other}:', flush=True)
        if a.host:
            c = sh(f'{a.remote_python} {a.remote_dir}/.det/det_check.py frames {dirs[0]} {other} --fps {a.fps} --tolerance {a.tolerance} --project {a.remote_dir}/{name}')
            print(c.stdout.rstrip()); c.stderr.strip() and print(c.stderr[-800:])
            if c.returncode == 2 or 'DET-CHECK' not in c.stdout: return 2
            ok_all = ok_all and c.returncode == 0
        else:
            ok, _ = compare(dirs[0], other, a.fps, project, a.tolerance)
            if ok is None: return 2
            ok_all = ok_all and ok
    print(f'proof frames kept at {(a.host + ":") if a.host else ""}{base} — the operator removes them')
    print(f"DET-CHECK {'PASS' if ok_all else 'FAIL'} {name}"); return 0 if ok_all else 1


def selftest():
    ok = True
    def chk(label, cond):
        nonlocal ok; ok &= bool(cond); print(f"  {'ok ' if cond else 'BAD'} {label}")
    with tempfile.TemporaryDirectory() as T:
        def proj(name, index, extra=None):
            d = os.path.join(T, name); os.makedirs(os.path.join(d, 'assets'), exist_ok=True)
            open(os.path.join(d, 'index.html'), 'w').write(index)
            for rel, body in (extra or {}).items():
                os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True); open(os.path.join(d, rel), 'w').write(body)
            return d
        PRNG = 'function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);return((t^t>>>14)>>>0)/4294967296;}}'
        clean = proj('clean', f'''<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<!-- the old draft used Math.random() here -->
<div id="root" data-width="64" data-height="64" data-start="0" data-duration="0.5">
<section class="clip" data-composition-id="a" data-start="0" data-duration="0.25"></section>
<section class="clip" data-composition-id="b" data-start="0.25" data-duration="0.25"></section></div>
<script>
  var url = 'https://example.com/x'; // never Date.now() — the timeline time comes in
  {PRNG} /* performance.now() is banned */ var rnd = mulberry32(7);
</script>''', {'assets/gsap.min.js': 'var t=Date.now();', 'vendor/lib.min.js': 'Math.random()'})
        files, found = scan_source(clean)
        chk('clean project: no finding (comments, a URL, a CDN tag, assets/ and *.min.js ignored)', not found and len(files) == 1)
        bad = proj('bad', '<div id="root"></div>\n<script>\nvar a = Math.random();\n</script>', {'src/tick.js': 'var t0 = performance.now();\nsetInterval(f, 40);\nvar d = new Date();'})
        _, found = scan_source(bad)
        got = sorted((f[0], f[1], f[3]) for f in found)
        chk(f'Math.random in index.html:3, performance.now / setInterval / new Date in src/tick.js:1-3 → {got}', got == [('index.html', 3, 'Math.random'), ('src/tick.js', 1, 'performance.now'), ('src/tick.js', 2, 'setInterval'), ('src/tick.js', 3, 'new Date')])
        okd = proj('allowed', '<script>\nsetTimeout(build, 0); // det-ok: defer the build past the font load, before any frame\n</script>')
        _, found = scan_source(okd)
        chk('det-ok on the line → ALLOWED with its reason, not a FAIL', len(found) == 1 and found[0][4] and found[0][4].startswith('defer'))
        cv = proj('canvas', "<script>\nvar a = c.getContext('2d');\nvar b = d.getContext('2d', {willReadFrequently: true});\n</script>")
        _, found = scan_source(cv)
        chk("getContext('2d') bare → FAIL at line 2; with {willReadFrequently:true} → clean", [(f[1], f[4]) for f in found] == [(2, None)])
        chk('scenes from data-start/data-duration, the root excluded', scenes_of(clean, 24) == [('a', 0, 5), ('b', 6, 11)])
        def seq(name, n, alter=None, delta=1):
            d = os.path.join(T, name); os.makedirs(d)
            for i in range(n):
                a = np.full((8, 8, 4), (i * 20) % 256, np.uint8)
                if alter == i: a[2, 3, 0] = (int(a[2, 3, 0]) + delta) % 256
                Image.fromarray(a, 'RGBA').save(os.path.join(d, f'frame_{i:06d}.png'))
            return d
        A, B, C = seq('A', 12), seq('B', 12), seq('C', 12, alter=8)
        ok1, _ = compare(A, B, 24, clean); chk('identical sequences → PASS', ok1 is True)
        ok2, idx = compare(A, C, 24, clean); chk('one pixel +1 at frame 8 → FAIL at frame 8, scene b', ok2 is False and idx == [8])
        ok3, _ = compare(A, C, 24, clean, tol=1); chk('the same difference inside --tolerance 1 → PASS', ok3 is True)
        ok4, _ = compare(A, seq('D', 11), 24); chk('a different frame count → FAIL', ok4 is False)
        ok5, msg = compare(A, os.path.join(T, 'nothing'), 24); chk('an empty side → unusable (None), never a pass', ok5 is None)
    print(f"SELFTEST {'PASS' if ok else 'FAIL'}"); return 0 if ok else 1


def main():
    if '--selftest' in sys.argv: sys.exit(selftest())
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('source'); s.add_argument('project')
    f = sub.add_parser('frames'); f.add_argument('dir_a'); f.add_argument('dir_b'); f.add_argument('--fps', type=float, default=24); f.add_argument('--project'); f.add_argument('--tolerance', type=int, default=0)
    p = sub.add_parser('prove'); p.add_argument('project'); p.add_argument('--host', help='the render host (WSL2 cannot render; without --host the render runs here)'); p.add_argument('--workers', default='1,3'); p.add_argument('--fps', type=int, default=24)
    p.add_argument('--remote-dir', default='~/hyper'); p.add_argument('--remote-python', default='python3'); p.add_argument('--hf-version', default='0.8.18'); p.add_argument('--tolerance', type=int, default=0)
    p.add_argument('--no-push', action='store_true', help='render the copy already on the host (the push mirrors the local project with --delete: never push a partial copy)')
    a = ap.parse_args()
    if a.cmd == 'source':
        ok = report_source(a.project); print(f"DET-CHECK {'PASS' if ok else 'FAIL'} source"); sys.exit(0 if ok else 1)
    if a.cmd == 'frames':
        ok, _ = compare(a.dir_a, a.dir_b, a.fps, a.project, a.tolerance)
        if ok is None: print(f'unusable input: {_}'); sys.exit(2)
        print(f"DET-CHECK {'PASS' if ok else 'FAIL'} frames"); sys.exit(0 if ok else 1)
    sys.exit(prove(a))


if __name__ == '__main__':
    main()
