#!/usr/bin/env python3
"""monid_submit.py — the ONLY way a Seedance job leaves a project on monid (the pay-as-you-go route).
Runs the refs gate first and refuses on FAIL; prints the cost line from the MEASURED token formula;
without --go it STOPS there (paste the gate table + the cost into the GO ask). With --go: one
`monid run` per seed, the reply parsed shape-safely, raw replies in receipts/raw/<key>-s<n>.json,
receipts/monid-runs-<key>.json, a gate-ledger record per take, and monid_poll.py detached
→ takes/<SCENE>-s<n>.mp4 (log takes/monid-poll-<key>.log).

  monid_submit.py --root <project> --scene S02-G4 --prompt prompts/r2v/S02-G4.txt
                  --mode t2v|i2v|flf|r2v --duration 7 [--refs NAME,NAME] [--start-image NAME]
                  [--end-image NAME] [--seeds 1] [--resolution 480p] [--ratio 9:16]
                  [--births R,R] [--prose X,Y] [--fresh-scene] [--go]

Reference NAMES resolve through <root>/monid-urls.json (written by monid_upload.py, which hosts them
on sfs for $0.00); a raw URL is refused — the gate must see a name.

WIRE FACTS, measured 2026-09-14 (VENUES.md § monid) — every one is a silent-failure trap:

  1. BILLING IS EXACT AND THE VENDOR'S FORMULA IS WRONG. ByteDance documents
     `tokens = W × H × fps × seconds ÷ 1024`; a 4 s clip returns 97 frames, not 96, because
     4.041667 s = 97/24. The true form is `W × H × (duration × fps + 1) ÷ 1024`, floored. Measured:
     480p 9:16 4 s → 38,830 tokens → $0.415481, wallet delta matched to six decimals.
  2. `duration: "auto"` HOLDS the price of a full 30 s video up front and releases the remainder on
     settle. Under a cost gate the held amount is the amount asked for, so `auto` is REFUSED here.
  3. `ratio` is accepted ONLY for t2v and r2v. first/last-frame, video edit and extend inherit their
     source's aspect and REQUIRE `adaptive`. Passing 9:16 there is an error, not a preference.
  4. Ordinals are numbered PER TYPE IN ARRAY ORDER, and a first_frame is still an image — so a start
     image occupies @Image1 and the refs shift by one. The resolved map is printed in the dry run
     because a prompt citing the wrong ordinal generates cleanly and bills in full.
  5. An invalid body returns a bare {"error": …} with NO runId: no run, no charge. A missing runId is
     therefore a hard failure, never a pending run.
  6. NEVER `--wait` (p50 245 s, p95 603 s vs a 300 s default) and on an async fire `-o` writes NOTHING
     — the submit envelope is stdout only. Fire, persist the runId, poll detached.
  7. Real human faces are rejected UPSTREAM (BytePlus ModelArk) and monid exposes none of the
     licensed-asset escapes, so a photoreal person reference cannot be routed here at all.
"""
import argparse, importlib.util, json, os, shutil, subprocess, sys

DEFAULT_GATE = os.path.expanduser('~/.claude/skills/video-refs-continuity/scripts/refs_gate.py')

# Measured. The matrix cell is $ per 1M tokens and is FLAT across 480p and 720p on seedance-2.5.
RATE_USD_PER_MTOK = {'480p': 10.7, '720p': 10.7}
RASTER = {'480p': (854, 480), '720p': (1280, 720)}      # W×H; orientation does not change the product
FPS = 24
DUR_MIN, DUR_MAX = 4, 30
PROMPT_CAP = 6000                                        # the model's own cap, read from the schema
RATIO_MODES = {'t2v', 'r2v'}                             # every other mode REQUIRES adaptive


def tokens_for(resolution, duration):
    w, h = RASTER[resolution]
    return (w * h * (duration * FPS + 1)) // 1024        # the +1 frame is the correction, and it floors


def usd_for(resolution, duration):
    return tokens_for(resolution, duration) * RATE_USD_PER_MTOK[resolution] / 1e6


def load_gate(path):
    spec = importlib.util.spec_from_file_location('refs_gate', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def csv(s):
    return [x for x in (s or '').split(',') if x]


def find_key(o, key):
    if isinstance(o, dict):
        if key in o:
            return o[key]
        for v in o.values():
            f = find_key(v, key)
            if f is not None:
                return f
    elif isinstance(o, list):
        for v in o:
            f = find_key(v, key)
            if f is not None:
                return f
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.')
    ap.add_argument('--scene', required=True, help='scene key, e.g. S02-G4 (takes are <scene>-s<n>)')
    ap.add_argument('--prompt', required=True)
    ap.add_argument('--mode', required=True, choices=['t2v', 'i2v', 'flf', 'r2v'],
                    help='flf = first+last frame; i2v = first frame only')
    ap.add_argument('--duration', required=True,
                    help='integer seconds 4-30. "auto" is REFUSED: it holds a full 30 s price up front')
    ap.add_argument('--refs', default='', help='comma-separated NAMES, in prompt-citation order')
    ap.add_argument('--start-image', help='first_frame')
    ap.add_argument('--end-image', help='last_frame (only with --start-image)')
    ap.add_argument('--seeds', type=int, default=1)
    ap.add_argument('--resolution', default='480p', choices=list(RATE_USD_PER_MTOK))
    ap.add_argument('--ratio', default='9:16', help='t2v/r2v only; every other mode forces adaptive')
    ap.add_argument('--provider', default='bytedance')
    ap.add_argument('--endpoint', default='/v1/video/seedance-2.5')
    ap.add_argument('--no-audio', action='store_true')
    ap.add_argument('--births', default='')
    ap.add_argument('--prose', default='')
    ap.add_argument('--fresh-scene', action='store_true')
    ap.add_argument('--gate', default=DEFAULT_GATE)
    ap.add_argument('--go', action='store_true')
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    key = a.scene.lower().replace('-', '')
    refs = csv(a.refs)

    if str(a.duration).lower() == 'auto':
        sys.exit('--duration auto is REFUSED under a cost gate: it HOLDS the price of a full 30 s video\n'
                 '  up front and releases the remainder on settle, so the GO would be given against a\n'
                 '  number nobody asked for. Pass an integer 4-30.')
    try:
        dur = int(a.duration)
    except ValueError:
        sys.exit(f'--duration must be an integer 4-30; got {a.duration!r}')
    if not DUR_MIN <= dur <= DUR_MAX:
        sys.exit(f'--duration must be {DUR_MIN}-{DUR_MAX} s (read from the endpoint schema); got {dur}')
    if a.end_image and not a.start_image:
        sys.exit('--end-image (last_frame) is only accepted WITH a --start-image (first_frame)')
    if a.mode in ('i2v', 'flf') and not a.start_image:
        sys.exit(f'--mode {a.mode} needs --start-image')
    if a.mode == 'r2v' and not refs:
        sys.exit('--mode r2v needs --refs')
    if a.mode == 'flf' and not a.end_image:
        sys.exit('--mode flf needs --end-image')
    if len(refs) > 30:
        # 30 is vendor PROSE in the endpoint schema's `role` description, NOT `maxItems` — the content
        # array carries no length bound at all, nor does any variant (re-read 2026-09-14). This is a
        # fail-closed guard on an UNMEASURED claim, and fail-closed is the right direction: an over-cap
        # body the gateway or the provider rejects costs $0.00, while one that SUCCEEDS bills in full.
        # So the real ceiling is free to probe on failure and one generation on success — deliberately,
        # never by accident. Provenance: VENUES.md § monid.
        sys.exit(f'{len(refs)} reference images — refusing above 30, which is the VENDOR\'S STATED cap '
                 f'(prose in the endpoint schema, never measured here — VENUES.md § monid). '
                 f'Raise it from a receipt, not from this message.')

    # The ratio rule is a schema fact, not a preference: only t2v/r2v accept one.
    ratio = a.ratio if a.mode in RATIO_MODES else 'adaptive'
    if a.mode not in RATIO_MODES and a.ratio not in ('adaptive', '9:16'):
        print(f'note: --ratio {a.ratio} ignored — {a.mode} inherits its source aspect and REQUIRES adaptive')

    gate = load_gate(a.gate)
    g = gate.Gate(root)
    prompt_path = a.prompt if os.path.isabs(a.prompt) else os.path.join(root, a.prompt)
    text = open(prompt_path, encoding='utf-8').read()
    m = g.spot_re.search(os.path.basename(prompt_path))
    spot = m.group(1) if m else None
    ok, rows, roles = g.check(text, refs, 'monid', a.start_image, csv(a.births), csv(a.prose), spot,
                              fresh=a.fresh_scene)

    urls = {}
    p = os.path.join(root, 'monid-urls.json')
    if os.path.exists(p):
        urls = json.load(open(p, encoding='utf-8'))

    def url_of(name):
        if name.startswith('http'):
            sys.exit(f'{name[:40]}… is a raw URL — the gate needs a NAME; host it with '
                     f'monid_upload.py --root {root} <file> --name <NAME> (sfs, $0.00)')
        u = urls.get(name)
        if name == '_meta':
            u = None
        if not isinstance(u, str):
            sys.exit(f'no hosted URL for {name} ({p}) — monid_upload.py --root {root} <file> --name {name}')
        return u

    print(f"REFS-GATE {a.prompt}  refs: {', '.join(refs) or '-'}  start: {a.start_image or '-'}")
    print(gate.fmt(rows))
    est_each = usd_for(a.resolution, dur)
    toks = tokens_for(a.resolution, dur)
    total = est_each * a.seeds
    print(('REFS-GATE PASS' if ok else
           f"REFS-GATE FAIL ({sum(1 for r in rows if r[1] == 'FAIL')} missing) — REFUSED"))
    w, h = RASTER[a.resolution]
    print(f"cost: {a.seeds} × {dur} s × {a.resolution} = {toks:,} tok × ${RATE_USD_PER_MTOK[a.resolution]}/1M "
          f"= ${est_each:.4f} each → ${total:.4f}   ({w}×{h}, {dur * FPS + 1} frames, ${est_each / dur:.4f}/s)")
    if not ok:
        sys.exit(1)
    if len(text) > PROMPT_CAP:
        sys.exit(f'prompt is {len(text)} chars — the endpoint cap is {PROMPT_CAP}')

    # Ordinals are per TYPE in ARRAY ORDER, and a first_frame is an image. Print the map: a prompt that
    # cites the wrong ordinal generates cleanly and bills in full.
    content = [{'type': 'text', 'text': text}]
    imgs = []
    if a.start_image:
        imgs.append((a.start_image, 'first_frame'))
    if a.end_image:
        imgs.append((a.end_image, 'last_frame'))
    imgs += [(r, 'reference_image') for r in refs]
    for name, role in imgs:
        content.append({'type': 'image_url', 'image_url': {'url': url_of(name)}, 'role': role})
    print('  ordinals (cite these EXACTLY in the prompt):')
    for i, (name, role) in enumerate(imgs, 1):
        print(f'    @Image{i} = {name}  ({role})')

    body = {'content': content, 'resolution': a.resolution, 'duration': dur, 'ratio': ratio,
            'output_format': 'mp4', 'generate_audio': not a.no_audio}
    if not a.go:
        shown = dict(body)
        shown['content'] = [{'type': 'text', 'text': text[:120] + ' …'}] + \
                           [f'@Image{i} {n} ({r})' for i, (n, r) in enumerate(imgs, 1)]
        print(json.dumps(shown, indent=2))
        print('DRY RUN — nothing submitted (paste the table + cost into the GO ask; re-run with --go).')
        sys.exit(0)

    if not shutil.which('monid'):
        sys.exit('monid CLI not found — npm install -g @monid-ai/cli, then `monid keys add`')
    os.makedirs(os.path.join(root, 'receipts', 'raw'), exist_ok=True)
    os.makedirs(os.path.join(root, 'takes'), exist_ok=True)
    R = []
    for s in range(1, a.seeds + 1):
        # NEVER --wait: p50 245 s, p95 603 s against a 300 s default. Fire, persist, poll.
        out = subprocess.run(['monid', 'run', '-p', a.provider, '-e', a.endpoint,
                              '-i', json.dumps(body), '--json'], capture_output=True, text=True, cwd=root)
        open(os.path.join(root, 'receipts', 'raw', f'{key}-s{s}.json'), 'w', encoding='utf-8').write(
            out.stdout + '\n--stderr--\n' + out.stderr)
        try:
            j = json.loads(out.stdout)
        except Exception:
            print(f'{a.scene}-s{s} UNPARSED reply:', out.stdout[:200], out.stderr[:200]); continue
        rid = find_key(j, 'runId')
        if not rid:
            # no runId ⇒ the body was rejected before a run existed ⇒ nothing billed
            print(f'{a.scene}-s{s} REJECTED (no run created, $0.00): '
                  f'{json.dumps(j.get("error") or j)[:300]}')
            continue
        R.append({'name': f'{a.scene}-s{s}', 'run_id': rid, 'provider': a.provider,
                  'endpoint': a.endpoint, 'mode': a.mode, 'duration': dur,
                  'resolution': a.resolution, 'ratio': ratio, 'est_tokens': toks,
                  'estimate_usd': round(est_each, 6)})
        print(f'{a.scene}-s{s} run {rid}  (BILLED at acceptance, est ${est_each:.4f})', flush=True)
        # the ledger record BEFORE polling — a hard kill still leaves a recoverable id
        rp = os.path.join(root, 'receipts', f'monid-runs-{key}.json')
        json.dump(R, open(rp, 'w'), indent=1)
        g.record(f'{a.scene}-s{s}', 'monid', os.path.relpath(prompt_path, root),
                 refs + ([a.start_image] if a.start_image else []), csv(a.births), roles)
    rp = os.path.join(root, 'receipts', f'monid-runs-{key}.json')
    json.dump(R, open(rp, 'w'), indent=1)
    print(f'receipts {rp} ({len(R)} runs) · est ${est_each * len(R):.4f}')
    if R:
        log = open(os.path.join(root, 'takes', f'monid-poll-{key}.log'), 'ab')
        poller = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'monid_poll.py')
        subprocess.Popen(['python3', poller, '--root', root, rp], stdout=log, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
        print(f'poll detached → takes/monid-poll-{key}.log → takes/{a.scene}-s<n>.mp4  '
              f'(match " DONE | FAILED|MONID-POLL-END")')


if __name__ == '__main__':
    main()
