#!/usr/bin/env python3
"""cast_stress.py — the STRESS-TEST LOCK for a new cast member: cheap stills under the conditions that break an identity,
read and scored, before the first video that shows them. The one-still dress rehearsal checks a reference SET for one
batch; this checks one MEMBER once — every angle, shot size and light the production will ask of them, and a two-shot
beside every co-star they share a frame with. A character locks at 10 of 10; one drift is a miss, never averaged away.
A location or a prop is presented as its matrix and locks on the operator's explicit pass.

Layout under --root (the matrix feeds gen_stills.py's own layout; it generates nothing itself):
  stress/<MEMBER>/descriptor.txt   the member's canonical descriptor — pasted VERBATIM into every prompt, never rewritten
  stress/<MEMBER>/matrix.json      the rows: angle · shot size · light · paired member · refs · result · verdict · note
  prompts/stills/<MEMBER>-Tnn.txt  one prompt per row, for gen_stills.py --only <ids> (dry run, then --go after the GO)
  prompts/stills/refs.json         {ID: [names]}, MERGED — an existing entry for another id is never touched
  receipts/refs-gate.jsonl         the lock: asset STRESS:<MEMBER> with each identity reference's sha256, read by
                                   refs_gate.py (rules `cast` + `require_cast_lock`); a reference changed later voids it

  cast_stress.py plan   --root P --cast NAME --refs A[,B] [--kind character|location|prop] [--costar NAME=REF[,REF]]...
                        [--light LABEL=PLATE]... [--min 10] [--ratio 9:16]      → matrix + prompts + the cost line
  cast_stress.py record --root P --cast NAME --row T03 --verdict pass|miss --note "<what was read>" [--result <png>]
  cast_stress.py status --root P --cast NAME
  cast_stress.py lock   --root P --cast NAME [--operator-pass "<who ruled, when>"]
  cast_stress.py --selftest

Exit 0 ok · 1 refused (a missing descriptor, a prompt that would be overwritten, a lock short of 10 of 10). Stills cost
(kie $0.05 each at 2K), so each member's matrix is its own cost line and GO. Pattern: machina-exm/film-studio-skills skills/stress-test/SKILL.md (the combat-test matrix, 10 of 10).
"""
import argparse, hashlib, json, os, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ANGLE = {'front': 'Front view, the face turned straight to the camera',
         'three-quarter': 'Three-quarter view, turned about 45 degrees from the camera',
         'profile': 'Profile view, side-on to the camera'}
SIZE = {'close-up': 'a close-up, head and shoulders', 'medium': 'a medium shot, from the waist up',
        'full-length': 'a full-length shot, head to feet'}
ORDER = [('front', 'close-up'), ('three-quarter', 'medium'), ('profile', 'close-up'), ('front', 'full-length'),
         ('three-quarter', 'close-up'), ('profile', 'medium'), ('three-quarter', 'full-length'), ('front', 'medium'),
         ('profile', 'full-length')]
KIE_2K = 0.05


def load_gate():
    sys.path.insert(0, HERE)
    import refs_gate
    return refs_gate


def csv(s):
    return [x.strip() for x in (s or '').split(',') if x.strip()]


def pairs(items, flag):
    out = []
    for it in items or []:
        if '=' not in it: sys.exit(f'{flag} takes NAME=VALUE, got {it!r}')
        k, v = it.split('=', 1); out.append((k.strip(), v.strip()))
    return out


def paths(root, member):
    d = os.path.join(root, 'stress', member)
    return d, os.path.join(d, 'descriptor.txt'), os.path.join(d, 'matrix.json')


def descriptor(root, member):
    p = paths(root, member)[1]
    return open(p, encoding='utf-8').read().strip() if os.path.exists(p) else None


def prompt_for(row, member, desc, costar_desc, ratio):
    who = f'{member}'
    lines = [desc, '']
    if row['paired']:
        lines += [costar_desc, '']
        frame = f"{ANGLE[row['angle']]}: {SIZE[row['size']]} of {who} standing beside {row['paired']}, both faces fully visible"
    else:
        frame = f"{ANGLE[row['angle']]}: {SIZE[row['size']]} of {who}"
    light = f"The light of the look-plate reference ({row['light']})." if row['plate'] else 'The light of the identity references.'
    lines.append(f"{frame}. {light} A simple static composition: standing still, a neutral expression, hands relaxed and "
                 f"visible, a plain background. No action. No text, no watermark, no caption, no logo. A vertical {ratio} frame."
                 if ratio in ('9:16', '4:5', '3:4', '2:3') else
                 f"{frame}. {light} A simple static composition: standing still, a neutral expression, hands relaxed and "
                 f"visible, a plain background. No action. No text, no watermark, no caption, no logo. A {ratio} frame.")
    return '\n'.join(lines) + '\n'


def plan(a):
    root = os.path.abspath(a.root); member = a.cast; refs = csv(a.refs)
    if not refs: sys.exit('plan: --refs names the member\'s identity references (registered and accepted in the gate)')
    costars = [(n, csv(v)) for n, v in pairs(a.costar, '--costar')]
    lights = pairs(a.light, '--light') or [('as referenced', None)]
    desc = a.descriptor and open(a.descriptor, encoding='utf-8').read().strip() or descriptor(root, member)
    missing = ([member] if not desc else []) + [n for n, _ in costars if not descriptor(root, n)]
    two = [(n, r, lab, pl) for n, r in costars for lab, pl in lights]
    n_solo = max(a.min - len(two), 3 * len(lights))
    rows, i = [], 0
    for k in range(n_solo):
        ang, size = ORDER[k % len(ORDER)]
        lab, pl = lights[k % len(lights)]
        i += 1; rows.append({'id': f'T{i:02d}', 'angle': ang, 'size': size, 'light': lab, 'plate': pl, 'paired': None,
                             'refs': refs + ([pl] if pl else []), 'result': None, 'verdict': 'pending', 'note': ''})
    for n, r, lab, pl in two:
        i += 1; rows.append({'id': f'T{i:02d}', 'angle': 'three-quarter', 'size': 'medium', 'light': lab, 'plate': pl,
                             'paired': n, 'refs': refs + r + ([pl] if pl else []), 'result': None, 'verdict': 'pending', 'note': ''})
    print(f'STRESS PLAN {member} ({a.kind}) — {len(rows)} rows: {n_solo} solo across {len(lights)} light(s), {len(two)} two-shot(s)')
    for r in rows:
        print(f"  {r['id']}  {r['angle']:<13} {r['size']:<11} {r['light']:<16} {('beside ' + r['paired']) if r['paired'] else '':<18} refs {','.join(r['refs'])}")
    if missing:
        print(f"REFUSED — no canonical descriptor for {', '.join(missing)}: write stress/<NAME>/descriptor.txt (pasted verbatim into "
              f"every prompt, never rewritten), then plan again. Nothing written."); return 1
    d, _, mp = paths(root, member)
    sd = os.path.join(root, 'prompts', 'stills'); os.makedirs(sd, exist_ok=True); os.makedirs(d, exist_ok=True)
    texts = {f"{member}-{r['id']}": prompt_for(r, member, desc, descriptor(root, r['paired']) if r['paired'] else '', a.ratio) for r in rows}
    clash = [k for k, t in texts.items() if os.path.exists(os.path.join(sd, k + '.txt'))
             and open(os.path.join(sd, k + '.txt'), encoding='utf-8').read() != t]
    if clash:
        print(f"REFUSED — {len(clash)} prompt file(s) already hold different text ({', '.join(clash[:4])}): a re-plan never "
              f"overwrites a prompt a still may have been generated from. Move them aside first. Nothing written."); return 1
    for k, t in texts.items():
        open(os.path.join(sd, k + '.txt'), 'w', encoding='utf-8').write(t)
    rp = os.path.join(sd, 'refs.json')
    cur = json.load(open(rp, encoding='utf-8')) if os.path.exists(rp) else {}
    cur.update({f"{member}-{r['id']}": r['refs'] for r in rows})
    json.dump(cur, open(rp, 'w', encoding='utf-8'), indent=1)
    old = json.load(open(mp, encoding='utf-8')) if os.path.exists(mp) else None
    kept = {r['id']: r for r in (old or {}).get('rows', []) if r.get('verdict') != 'pending'}
    for r in rows:
        if r['id'] in kept and kept[r['id']]['refs'] == r['refs']:
            r.update({k: kept[r['id']][k] for k in ('result', 'verdict', 'note')})
    json.dump({'member': member, 'kind': a.kind, 'refs': refs, 'ratio': a.ratio, 'planned': time.strftime('%Y-%m-%d %H:%M'),
               'rows': rows}, open(mp, 'w', encoding='utf-8'), indent=1)
    ids = ','.join(texts)
    print(f"wrote {os.path.relpath(mp, root)} · {len(texts)} prompt(s) in prompts/stills/ · refs.json merged")
    print(f"cost: {len(rows)} still(s) × ${KIE_2K:.2f} on kie (2K) → ${KIE_2K * len(rows):.2f}   GO?")
    print(f"then: gen_stills.py --root {root} --only {ids} --ratio {a.ratio}   (dry run; --go after the GO; "
          f"--fresh-scene when the identity is an authored root with no keeper behind it)")
    return 0


def load(root, member):
    mp = paths(root, member)[2]
    if not os.path.exists(mp): sys.exit(f'no matrix for {member} — cast_stress.py plan first')
    return mp, json.load(open(mp, encoding='utf-8'))


def record(a):
    root = os.path.abspath(a.root); mp, m = load(root, a.cast)
    row = next((r for r in m['rows'] if r['id'] == a.row), None)
    if row is None: sys.exit(f"no row {a.row} in {a.cast}'s matrix ({', '.join(r['id'] for r in m['rows'])})")
    res = a.result or os.path.join('startframes', f'{a.cast}-{a.row}.png')
    ap = res if os.path.isabs(res) else os.path.join(root, res)
    if not os.path.exists(ap): sys.exit(f'no still at {res} — record the file the read was made on')
    if not a.note.strip(): sys.exit('record needs --note: what was read (face, hair, age cues, build, wardrobe, marks; BOTH identities on a two-shot)')
    row.update({'result': os.path.relpath(ap, root), 'sha256': hashlib.sha256(open(ap, 'rb').read()).hexdigest(),
                'verdict': a.verdict, 'note': a.note.strip(), 'read': time.strftime('%Y-%m-%d %H:%M')})
    json.dump(m, open(mp, 'w', encoding='utf-8'), indent=1)
    print(f"STRESS {a.cast} {a.row} {a.verdict.upper()} — {row['note']}")
    return 0


def score(m):
    v = [r['verdict'] for r in m['rows']]
    return v.count('pass'), v.count('miss'), v.count('pending'), len(v)


def status(a):
    root = os.path.abspath(a.root); _, m = load(root, a.cast)
    p, x, q, n = score(m)
    for r in m['rows']:
        print(f"  {r['id']}  {r['verdict']:<7} {r['angle']:<13} {r['size']:<11} {r['light']:<16} "
              f"{('beside ' + r['paired']) if r['paired'] else '':<18} {r.get('result') or '-'}  {r.get('note', '')}")
    print(f"STRESS {a.cast} ({m['kind']}): {p} pass · {x} miss · {q} pending of {n}")
    return 0


def lock(a):
    root = os.path.abspath(a.root); mp, m = load(root, a.cast)
    p, x, q, n = score(m)
    if x or q:
        print(f"REFUSED — {p} of {n}: {x} miss, {q} pending. The member stays draft: revise the reference set (a new identity "
              f"still, a dedicated headshot) and rerun the affected rows, or move the scene to a later block."); return 1
    if m['kind'] == 'character' and n < 10:
        print(f'REFUSED — a character locks on 10 of 10; this matrix has {n} rows — plan again with --min 10'); return 1
    if m['kind'] != 'character' and not a.operator_pass:
        print(f"REFUSED — a {m['kind']} locks on the operator's explicit pass: show the matrix (status), then "
              f"lock --operator-pass \"<who ruled, when>\""); return 1
    gate = load_gate(); g = gate.Gate(root)
    shas = {}
    for name in m['refs']:
        rec = g.latest_record(name) or {}
        if not rec.get('sha256'): sys.exit(f'{name} has no registered file in the gate — register it: the lock pins its bytes')
        shas[name] = rec['sha256']
    g.append({'asset': 'STRESS:' + a.cast, 'stress_locked': True, 'score': f'{p}/{n}', 'kind': m['kind'],
              'matrix': os.path.relpath(mp, root), 'matrix_sha256': hashlib.sha256(open(mp, 'rb').read()).hexdigest(),
              'refs': shas, 'operator_pass': a.operator_pass, 'ts': time.strftime('%Y-%m-%d %H:%M')})
    print(f"STRESS {a.cast} LOCKED {p}/{n} — the gate now reads STRESS:{a.cast}; a change to "
          f"{', '.join(shas)} voids it")
    return 0


def selftest():
    from PIL import Image
    cases = []
    with tempfile.TemporaryDirectory() as d:
        for sub in ('prompts', 'receipts', 'refs', 'startframes', 'stress/VISITOR', 'stress/HOST'): os.makedirs(os.path.join(d, sub))
        json.dump({'rules': [], 'caps_stoplist': []}, open(os.path.join(d, 'prompts', 'refs-required.json'), 'w'))
        g = load_gate().Gate(d)
        for n in ('VISITOR-ref', 'HOST-ref', 'LOOK-warm'):
            Image.new('RGB', (512, 768), (120, 90, 60)).save(os.path.join(d, 'refs', f'{n}.png'))
            g.append({'asset': n, **g.file_facts(f'refs/{n}.png'), 'accepted': True, 'note': 'selftest'})
        os.makedirs(os.path.join(d, 'prompts', 'stills'))
        json.dump({'OTHER-01': ['X']}, open(os.path.join(d, 'prompts', 'stills', 'refs.json'), 'w'))
        A = lambda **k: argparse.Namespace(**{'root': d, 'cast': 'VISITOR', 'refs': 'VISITOR-ref', 'kind': 'character',
                                              'costar': ['HOST=HOST-ref'], 'light': ['warm lamp=LOOK-warm'], 'min': 10,
                                              'ratio': '9:16', 'descriptor': None, 'row': None, 'verdict': None, 'note': '',
                                              'result': None, 'operator_pass': None, **k})
        cases.append(('no descriptor → plan REFUSED, nothing written', plan(A()) == 1 and not os.path.exists(os.path.join(d, 'stress', 'VISITOR', 'matrix.json'))))
        open(os.path.join(d, 'stress', 'VISITOR', 'descriptor.txt'), 'w').write('VISITOR: a woman of 40, short grey hair, a green wool coat.')
        open(os.path.join(d, 'stress', 'HOST', 'descriptor.txt'), 'w').write('HOST: a man of 60, a white beard, a brown cardigan.')
        cases.append(('plan writes the matrix', plan(A()) == 0))
        m = json.load(open(os.path.join(d, 'stress', 'VISITOR', 'matrix.json')))
        cases.append(('10 rows, one of them the two-shot beside the co-star', len(m['rows']) == 10 and sum(1 for r in m['rows'] if r['paired'] == 'HOST') == 1))
        t = open(os.path.join(d, 'prompts', 'stills', 'VISITOR-T10.txt')).read()
        cases.append(('the two-shot prompt carries BOTH descriptors verbatim', 'a green wool coat' in t and 'a white beard' in t))
        rj = json.load(open(os.path.join(d, 'prompts', 'stills', 'refs.json')))
        cases.append(('refs.json is merged, the other id kept', rj.get('OTHER-01') == ['X'] and rj['VISITOR-T10'] == ['VISITOR-ref', 'HOST-ref', 'LOOK-warm']))
        cases.append(('a re-plan with the same text is idempotent', plan(A()) == 0))
        open(os.path.join(d, 'stress', 'VISITOR', 'descriptor.txt'), 'w').write('VISITOR: a woman of 40, long red hair.')
        cases.append(('a re-plan that would rewrite a prompt is REFUSED', plan(A()) == 1))
        open(os.path.join(d, 'stress', 'VISITOR', 'descriptor.txt'), 'w').write('VISITOR: a woman of 40, short grey hair, a green wool coat.')
        for r in m['rows']:
            Image.new('RGB', (576, 1024), (100, 100, 100)).save(os.path.join(d, 'startframes', f"VISITOR-{r['id']}.png"))
        for r in m['rows'][:9]:
            record(A(row=r['id'], verdict='pass', note='face, hair, coat match'))
        cases.append(('9 of 10 read → lock REFUSED (one pending)', lock(A()) == 1))
        record(A(row='T10', verdict='miss', note='HOST reads 20 years younger'))
        cases.append(('a miss → lock REFUSED, never averaged away', lock(A()) == 1))
        record(A(row='T10', verdict='pass', note='both identities match after the headshot was added'))
        cases.append(('10 of 10 → LOCKED', lock(A()) == 0))
        rec = g.latest_record('STRESS:VISITOR')
        cases.append(('the lock pins the identity reference bytes', rec and rec['stress_locked'] and rec['refs'].get('VISITOR-ref') == g.latest_record('VISITOR-ref')['sha256']))
        mp = os.path.join(d, 'stress', 'VISITOR', 'matrix.json'); m = json.load(open(mp)); m['kind'] = 'location'; json.dump(m, open(mp, 'w'))
        cases.append(('a location needs the operator\'s explicit pass', lock(A()) == 1 and lock(A(operator_pass='operator, selftest')) == 0))
    for name, ok in cases: print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in cases); print(f"cast_stress selftest {'PASS' if ok else 'FAIL'}"); return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', nargs='?', choices=['plan', 'record', 'status', 'lock'])
    ap.add_argument('--root', default='.')
    ap.add_argument('--cast', help='the member (the name the rules\' cast map uses)')
    ap.add_argument('--refs', help='plan: the member\'s identity reference names, registered in the gate')
    ap.add_argument('--kind', default='character', choices=['character', 'location', 'prop'])
    ap.add_argument('--costar', action='append', help='plan: NAME=REF[,REF] — every member sharing a frame with this one')
    ap.add_argument('--light', action='append', help='plan: LABEL=PLATE — every light context the member appears in')
    ap.add_argument('--min', type=int, default=10, help='plan: the least number of rows (10 for a character)')
    ap.add_argument('--ratio', default='9:16')
    ap.add_argument('--descriptor', help='plan: a descriptor file other than stress/<NAME>/descriptor.txt')
    ap.add_argument('--row'); ap.add_argument('--verdict', choices=['pass', 'miss']); ap.add_argument('--note', default='')
    ap.add_argument('--result', help='record: the still read (default startframes/<NAME>-<row>.png)')
    ap.add_argument('--operator-pass', help='lock: a location or prop locks on the operator\'s explicit pass')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    if not a.cmd or not a.cast: ap.print_help(); sys.exit(2)
    if a.cmd == 'record' and not (a.row and a.verdict): sys.exit('record needs --row and --verdict')
    sys.exit({'plan': plan, 'record': record, 'status': status, 'lock': lock}[a.cmd](a))


if __name__ == '__main__':
    main()
