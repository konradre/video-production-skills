#!/usr/bin/env python3
"""pick_gate.py — the operator's pick as a RECORD the finish chain checks, not a sentence it is trusted to remember.

"Nothing is upscaled, hero-passed or cut on a clip before the operator's pick" was prose until 2026-09-29. The spend gate
already worked in code (`--go` echoes the operator's yes on a cost line); the pick gate did not. This is that gate: the pick
is recorded the moment the operator names the keeper by path, and every finish step refuses a clip it cannot trace back to
a recorded pick. Pattern from `dsh-narrate` (`src/flow/run.js`: a job file of the operator's yeses, a later stage refusing
with E_OUT_OF_ORDER until every earlier yes exists, and no yes accepted for a stop not yet reached).

  pick_gate.py record --root <project> [--window 1.2-4.8] [--note "…"] <clip>…     # the operator named these by path
  pick_gate.py derive --root <project> --from <picked clip> [--note "…"] <new file>…   # a trim/rename under a new name
  pick_gate.py check  --root <project> [--shots <shots.json>] <file>…               # exit 0 all traced · 3 any not
  pick_gate.py list   --root <project>
  pick_gate.py --selftest

The record is `<root>/receipts/picks.jsonl`, append-only: kind (pick|derive), path, sha256, bytes, window, from, note, at.
A file traces to a pick when, in order:
  1. its content (sha256) equals a recorded pick or derive — a copy or a rename of the keeper still counts;
  2. its own path is recorded but the content CHANGED since → REFUSED (a re-render at the keeper's path is not the keeper);
  3. its name carries a recorded stem: `<stem>` or `<stem>__<anything>` — the finish scripts' own naming
     (`<stem>__rhea-1x4.mp4` from upscale_local.sh, `<stem>__<look>.mov` from hero_pass.sh);
  4. with --shots: its name (before any `__`) is a shot id in shots.json, and that shot's `src` traces to a pick — the
     flats normalise_shots.py writes to edit/flat/<id>.mov.
A pick cannot be recorded for a clip that has not landed: a yes before the clip exists would bypass the pick.
Relative clip paths resolve against --root.
"""
import argparse, hashlib, json, os, sys, tempfile, time

REC = os.path.join('receipts', 'picks.jsonl')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def full(root, p): return p if os.path.isabs(p) else os.path.join(root, p)
def rel(root, p): return os.path.relpath(os.path.abspath(full(root, p)), os.path.abspath(root))
def stem(p): return os.path.splitext(os.path.basename(p))[0]


def load(root):
    f = os.path.join(root, REC)
    return [json.loads(l) for l in open(f) if l.strip()] if os.path.exists(f) else []


def append(root, row):
    os.makedirs(os.path.join(root, 'receipts'), exist_ok=True)
    with open(os.path.join(root, REC), 'a') as f: f.write(json.dumps(row) + '\n')


def trace(root, p, recs, shots=None):
    """(ok, why) — why names the record it traced to, or what is missing."""
    fp = full(root, p)
    if not os.path.isfile(fp): return False, 'no such file'
    s, r, st = sha(fp), rel(root, p), stem(p)
    for x in recs:
        if x['sha256'] == s: return True, f"{x['kind']} {x['path']} ({x['at']}{', window ' + x['window'] if x.get('window') else ''})"
    for x in recs:
        if x['path'] == r: return False, f"changed since it was recorded as a {x['kind']} ({x['at']}) — a re-render at the keeper's path is not the keeper"
    for x in recs:
        k = stem(x['path'])
        if st == k or st.startswith(k + '__'): return True, f"named from {x['kind']} {x['path']} ({x['at']})"
    if shots:
        sid = st.split('__')[0]
        for w in shots:
            if str(w.get('id')) == sid and w.get('src'):
                ok, why = trace(root, w['src'], recs)
                return ok, f"shot {sid} ← {w['src']}: {why}"
    return False, 'no recorded pick — the operator names the keeper by path, then `pick_gate.py record`'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', nargs='?', choices=['record', 'derive', 'check', 'list']); ap.add_argument('files', nargs='*')
    ap.add_argument('--root', default='.'); ap.add_argument('--window'); ap.add_argument('--note', default='')
    ap.add_argument('--from', dest='src'); ap.add_argument('--shots'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest: return selftest()
    if not a.cmd: ap.error('a command, or --selftest')
    root, recs, now = a.root, load(a.root), time.strftime('%Y-%m-%dT%H:%M:%S')
    if a.cmd == 'list':
        for x in recs: print(f"{x['at']}  {x['kind']:6} {x['path']}{'  window ' + x['window'] if x.get('window') else ''}"
                             f"{'  from ' + x['from'] if x.get('from') else ''}{'  — ' + x['note'] if x.get('note') else ''}")
        return 0
    if not a.files: ap.error('name the clip(s)')
    if a.cmd == 'record':
        bad = [p for p in a.files if not os.path.isfile(full(root, p))]
        if bad: print(f"PICK-REFUSED not landed: {', '.join(bad)} — a pick recorded before the clip exists would bypass the pick"); return 3
        for p in a.files:
            s = sha(full(root, p))
            if any(x['sha256'] == s and x['kind'] == 'pick' for x in recs): print(f'PICK-ALREADY {p}'); continue
            append(root, {'kind': 'pick', 'path': rel(root, p), 'sha256': s, 'bytes': os.path.getsize(full(root, p)),
                          'window': a.window, 'from': None, 'note': a.note, 'at': now}); print(f'PICK-RECORDED {p}')
        return 0
    if a.cmd == 'derive':
        if not a.src: ap.error('--from <picked clip>')
        ok, why = trace(root, a.src, recs)
        if not ok: print(f'PICK-REFUSED E_OUT_OF_ORDER {a.src}: {why}'); return 3
        bad = [p for p in a.files if not os.path.isfile(full(root, p))]
        if bad: print(f"PICK-REFUSED not written yet: {', '.join(bad)}"); return 3
        for p in a.files:
            append(root, {'kind': 'derive', 'path': rel(root, p), 'sha256': sha(full(root, p)), 'bytes': os.path.getsize(full(root, p)),
                          'window': a.window, 'from': rel(root, a.src), 'note': a.note, 'at': now}); print(f'PICK-DERIVED {p} ← {a.src}')
        return 0
    shots = json.load(open(full(root, a.shots))) if a.shots else None
    bad = 0
    for p in a.files:
        ok, why = trace(root, p, recs, shots)
        print(f"{'PICK-OK' if ok else 'PICK-MISSING E_OUT_OF_ORDER'} {p}: {why}"); bad += not ok
    return 3 if bad else 0


def selftest():
    with tempfile.TemporaryDirectory() as r:
        def w(p, b):
            os.makedirs(os.path.dirname(os.path.join(r, p)) or r, exist_ok=True); open(os.path.join(r, p), 'wb').write(b)
        q = lambda *x: main(['--root', r, *x])
        w('takes/S02-G4-s2.mp4', b'seed2'); w('takes/S02-G4-s3.mp4', b'seed3'); w('assets/C5325.mp4', b'footage')
        json.dump([{'id': 's03', 'src': 'assets/C5325.mp4', 'f0': 150, 'n': 99}], open(os.path.join(r, 'shots.json'), 'w'))
        t = []
        t.append(('record refuses a clip that has not landed', q('record', 'takes/S09.mp4') == 3))
        t.append(('an unpicked seed is refused', q('check', 'takes/S02-G4-s2.mp4') == 3))
        t.append(('record, then the seed traces', q('record', '--window', '1.2-4.8', 'takes/S02-G4-s2.mp4') == 0 and q('check', 'takes/S02-G4-s2.mp4') == 0))
        t.append(('a sibling seed stays refused', q('check', 'takes/S02-G4-s3.mp4') == 3))
        w('edit/upscale-out/S02-G4-s2__rhea-1x4.mp4', b'up'); w('edit/hero/S02-G4-s2__rhea-1x4__ads-clean.mov', b'hero')
        t.append(('the finish scripts\' <stem>__ names trace', q('check', 'edit/upscale-out/S02-G4-s2__rhea-1x4.mp4', 'edit/hero/S02-G4-s2__rhea-1x4__ads-clean.mov') == 0))
        w('edit/upscale-out/S02-G4-s20.mp4', b'other')
        t.append(('a longer stem is not a match', q('check', 'edit/upscale-out/S02-G4-s20.mp4') == 3))
        w('edit/copy/renamed.mp4', b'seed2')
        t.append(('a byte-identical copy traces by content', q('check', 'edit/copy/renamed.mp4') == 0))
        w('edit/upscale-in/S05-A.mp4', b'trim')
        t.append(('a trim under a new name is refused until derived', q('check', 'edit/upscale-in/S05-A.mp4') == 3))
        t.append(('derive refuses an unpicked parent', q('derive', '--from', 'takes/S02-G4-s3.mp4', 'edit/upscale-in/S05-A.mp4') == 3))
        t.append(('derive from the pick, then the trim traces', q('derive', '--from', 'takes/S02-G4-s2.mp4', 'edit/upscale-in/S05-A.mp4') == 0
                  and q('check', 'edit/upscale-in/S05-A.mp4') == 0))
        w('takes/S02-G4-s2.mp4', b'seed2-rerendered')
        t.append(('a re-render at the keeper\'s path is refused', q('check', 'takes/S02-G4-s2.mp4') == 3))
        w('edit/flat/s03.mov', b'flat'); w('edit/hero/s03__ads-clean.mov', b'flathero')
        t.append(('a flat is refused without --shots', q('check', 'edit/flat/s03.mov') == 3))
        t.append(('a flat whose source is unpicked is refused', q('check', '--shots', 'shots.json', 'edit/flat/s03.mov') == 3))
        t.append(('pick the footage, then the flat and its hero trace', q('record', 'assets/C5325.mp4') == 0
                  and q('check', '--shots', 'shots.json', 'edit/flat/s03.mov', 'edit/hero/s03__ads-clean.mov') == 0))
        t.append(('recording the same pick twice adds no row', q('record', 'assets/C5325.mp4') == 0
                  and sum(1 for x in load(r) if x['path'] == 'assets/C5325.mp4') == 1))
    for name, ok in t: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in t); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in t)}/{len(t)})"); return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
