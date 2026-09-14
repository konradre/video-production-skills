#!/usr/bin/env python3
"""hf_submit.py — the ONLY way a Seedance job leaves a project on the Higgsfield CLI. Runs the refs gate first
and refuses on FAIL; prints the cost; without --go it STOPS there (paste the gate table + the cost into the GO
ask). With --go: one `higgsfield generate create` per seed, the LIST reply parsed shape-safely, raw replies in
receipts/raw/<scenekey>-s<n>.json, receipts/hf-jobs-<scenekey>.json, a gate-ledger record per take, and
hf_poll.py detached → takes/<SCENE>-s<n>.mp4 (log takes/hf-poll-<scenekey>.log, appended). Never calls
`generate cost` (it hung with --mode); the price is --rate credits per second at --resolution.

  hf_submit.py --root <project> --scene S01-E --prompt prompts/r2v/S01-E.txt --mode omni_reference|t2v|video_extension
               --duration 4 [--refs NAME,NAME] [--start-image NAME] [--video-ref <keeper job id>] [--seeds 3]
               [--births R,R] [--prose X,Y] [--fresh-scene] [--rate 2.5] [--resolution 480p] [--aspect 9:16] [--go]

Reference NAMES resolve through <root>/receipts/<NAME>-upload-id.txt (written by hf_upload.py); a raw UUID is
refused — the gate must see a name. The gate is video-refs-continuity's refs_gate.py (--gate to override).
"""
import argparse, importlib.util, json, os, subprocess, sys

DEFAULT_GATE = os.path.expanduser('~/.claude/skills/video-refs-continuity/scripts/refs_gate.py')


def load_gate(path):
    spec = importlib.util.spec_from_file_location('refs_gate', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def csv(s):
    return [x for x in (s or '').split(',') if x]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.')
    ap.add_argument('--scene', required=True, help='scene key, e.g. S02-G4 (takes are <scene>-s<n>)')
    ap.add_argument('--prompt', required=True)
    ap.add_argument('--mode', required=True, choices=['omni_reference', 't2v', 'video_extension'])
    ap.add_argument('--duration', required=True, type=int)
    ap.add_argument('--refs', default='')
    ap.add_argument('--start-image')
    ap.add_argument('--video-ref', help='a previous job id (video_extension / voice+blocking reference)')
    ap.add_argument('--seeds', type=int, default=3)
    ap.add_argument('--births', default='')
    ap.add_argument('--prose', default='')
    ap.add_argument('--fresh-scene', action='store_true')
    ap.add_argument('--rate', type=float, default=2.5, help='credits per second at --resolution')
    ap.add_argument('--resolution', default='480p')
    ap.add_argument('--aspect', default='9:16')
    ap.add_argument('--model', default='seedance_2_5')
    ap.add_argument('--gate', default=DEFAULT_GATE, help='path to refs_gate.py')
    ap.add_argument('--go', action='store_true')
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    gate = load_gate(a.gate)
    g = gate.Gate(root)
    refs, start = csv(a.refs), a.start_image
    key = a.scene.lower().replace('-', '')

    def rid(name):
        if len(name) == 36 and name.count('-') == 4:
            sys.exit(f'{name} looks like a raw UUID — the gate needs a NAME; write receipts/{name}-upload-id.txt via hf_upload.py')
        p = os.path.join(root, 'receipts', f'{name}-upload-id.txt')
        if not os.path.exists(p):
            sys.exit(f'no upload id for {name} ({p}) — upload it first: hf_upload.py --root {root} <png> --name {name}')
        return open(p).read().strip()

    ids = [rid(n) for n in refs]
    start_id = rid(start) if start else None
    prompt_path = os.path.join(root, a.prompt) if not os.path.isabs(a.prompt) else a.prompt
    text = open(prompt_path, encoding='utf-8').read()
    m = g.spot_re.search(os.path.basename(prompt_path)); spot = m.group(1) if m else None
    ok, rows, roles = g.check(text, refs, 'hf', start, csv(a.births), csv(a.prose), spot, fresh=a.fresh_scene)
    print(f"REFS-GATE {a.prompt}  refs: {', '.join(refs) or '-'}  start: {start or '-'}")
    print(gate.fmt(rows))
    cost = a.rate * a.duration * a.seeds
    print(('REFS-GATE PASS' if ok else f"REFS-GATE FAIL ({sum(1 for r in rows if r[1] == 'FAIL')} missing) — REFUSED")
          + f"   cost: {a.seeds} × {a.duration} s × {a.rate:g} = {cost:g} cr")
    if not ok:
        sys.exit(1)
    if len(text) > 5000:
        print(f'⚠ prompt {len(text)} chars (6629 worked; 7840 was trimmed)')
    if not a.go:
        print('DRY RUN — nothing submitted (paste the table + cost into the GO ask; re-run with --go).'); sys.exit(0)

    cmd = ['higgsfield', 'generate', 'create', a.model, '--mode', a.mode]
    if start_id: cmd += ['--start-image', start_id]
    for i in ids: cmd += ['--image', i]
    if a.video_ref: cmd += ['--video-references', a.video_ref]
    if a.mode == 'video_extension': cmd += ['--extension_mode', 'forward']
    cmd += ['--prompt', text, '--resolution', a.resolution, '--duration', str(a.duration), '--aspect_ratio', a.aspect, '--json']
    os.makedirs(os.path.join(root, 'receipts', 'raw'), exist_ok=True)
    os.makedirs(os.path.join(root, 'takes'), exist_ok=True)
    R = []
    for s in range(1, a.seeds + 1):
        out = subprocess.run(cmd, capture_output=True, text=True, cwd=root)
        open(os.path.join(root, 'receipts', 'raw', f'{key}-s{s}.json'), 'w', encoding='utf-8').write(out.stdout + '\n--stderr--\n' + out.stderr)
        try:
            j = json.loads(out.stdout)
        except Exception:
            print(f'{a.scene}-s{s} UNPARSED reply:', out.stdout[:200], out.stderr[:200]); continue
        jid = j[0] if isinstance(j, list) else (j.get('id') or j.get('job_id'))
        if isinstance(jid, dict): jid = jid.get('id') or jid.get('job_id')
        R.append({'name': f'{a.scene}-s{s}', 'job_id': jid, 'mode': a.mode, 'duration': a.duration, 'resolution': a.resolution, 'rate': a.rate})
        print(f'{a.scene}-s{s} job {jid}  (BILLED at acceptance)', flush=True)
        # the ledger record BEFORE polling — a hard kill still leaves a recoverable id
        rp = os.path.join(root, 'receipts', f'hf-jobs-{key}.json'); json.dump(R, open(rp, 'w'), indent=1)
        g.record(f'{a.scene}-s{s}', 'hf', os.path.relpath(prompt_path, root), refs + ([start] if start else []), csv(a.births), roles)
    rp = os.path.join(root, 'receipts', f'hf-jobs-{key}.json'); json.dump(R, open(rp, 'w'), indent=1)
    print(f'receipts {rp} ({len(R)} jobs) · billed ≈ {a.rate * a.duration * len(R):g} cr')
    if R:
        log = open(os.path.join(root, 'takes', f'hf-poll-{key}.log'), 'ab')
        poller = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hf_poll.py')
        subprocess.Popen(['python3', poller, '--root', root, rp], stdout=log, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
        print(f'poll detached → takes/hf-poll-{key}.log → takes/{a.scene}-s<n>.mp4  (match " DONE | FAILED|HF-POLL-END")')


if __name__ == '__main__':
    main()
