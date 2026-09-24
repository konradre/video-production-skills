#!/usr/bin/env python3
"""hf_api_submit.py — the ONLY way a job leaves a project on the Higgsfield REST API.
Runs the refs gate first; prints the COMPUTED cost line (Seedance returns no number, so the gate
computes one — hf_api.py); without --go it STOPS there. With --go: one submit per seed over curl,
the reply parsed shape-safely, raw replies in receipts/raw/, receipts/hfapi-jobs-<key>.json, a
gate-ledger record and a WALLET-ledger spend per seed BEFORE polling, then hf_api_poll.py detached
→ takes/<SCENE>-s<n>.mp4 (log takes/hfapi-poll-<key>.log).

  hf_api_submit.py --root <project> --scene S02-G4 --prompt prompts/r2v/S02-G4.txt
      --mode t2v|i2v|r2v|edit|extend --duration 8 [--refs NAME,NAME] [--audio NAME]
      [--video-refs NAME] [--start-image NAME] [--end-image NAME] [--source NAME|URL]
      [--input-seconds N] [--seeds 1] [--resolution 480p|720p] [--ratio 9:16] [--model seedance|h3]
      [--births R,R] [--prose X,Y] [--fresh-scene] [--despite-gate] [--go]
  hf_api_submit.py --root <project> --scene G1 --prompt prompts/v2v/G1.txt --model genjutsu
      --mode object-swap|motion-transfer --source <clip NAME> --refs NAME[,NAME…] [--resolution 480p]
      [--input-seconds N] [--seeds 1] [--go]

Reference NAMES resolve through <root>/hf-api-urls.json (hf_api_upload.py, free); a raw URL is
refused for a reference, because the gate must see a name.

WIRE FACTS (VENUES.md § Higgsfield API) — every one bills or misleads silently:

  1. 🔴 NO 1080p. `resolution` is 480p or 720p ONLY on this API's Seedance 2.5, while the (closed) CLI
     plan did 1080p. 720p costs 2.25× 480p — the pixel ratio exactly, because the meter is on W×H.
  2. 🔴 CONCURRENCY REFUSES WITH 400, NOT 429 — "Maximum number of concurrent requests (4) has been
     reached", with no Retry-After and no rate-limit headers. Read as a malformed body it looks fatal;
     it is a queue that clears. Handled below by the vendor's own string, never by the status code.
  3. `video-extend` takes a `video_url` — NOT a job id, which is what the CLI's --mode video_extension
     took. Feed the keeper's own output URL back (outputs are retained ≥ 7 days).
  4. Both durations bill on the 0.6× tier, so an EXTEND beats a fresh generation only when
     `gen > 1.5 × in`. The cost line prints both figures; the operator rules (SKILL.md § 0).
  5. `video-edit` takes NO duration — the source decides it. Sending one is an error, not a preference.
  6. `aspect_ratio` must be explicit on generation; automatic duration (-1) is unsupported on r2v.
  7. Billing happens at ACCEPTANCE. The receipt and the wallet-ledger line are written before the
     poller starts, because the wallet has no balance endpoint and an unrecorded spend is LOST.
  8. `failed` / `nsfw` / a cancelled `queued` request are NOT charged — hf_api_poll.py writes the
     matching REFUND into the wallet ledger, or the balance drifts low on every refusal.
  9. GENJUTSU (`higgsfiled/genjutsu/{object-swap,motion-transfer}/v1.0` — the vendor's own spelling, copied
     verbatim) re-casts an EXISTING clip. Its validator knows FOUR fields — `video_url`, `image_urls` (1-8),
     `prompt`, `resolution` — and ACCEPTS ANY OTHER FIELD SILENTLY, so a duration, a ratio or a typo would
     look sent and do nothing. Only those four are sent.
 10. Genjutsu bills per second of INPUT video, rounded up, and /estimate never returns the number — so the
     length is READ from the local file the upload ledger records for --source (ffprobe), never typed.
"""
import argparse, importlib.util, json, os, subprocess, sys, time

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('hf_api', os.path.join(_here, 'hf_api.py'))
hf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hf)

DEFAULT_GATE = os.path.expanduser('~/.claude/skills/video-refs-continuity/scripts/refs_gate.py')
TARGET = 'hfapi'                      # the refs-gate target: <root>/hf-api-urls.json
LEDGER_NAME = 'hf-api-urls.json'

# Slugs read from GET /models, 2026-09-18 — the authoritative catalog. /docs/openapi.json is NOT, and
# is stale enough to omit Seedance 2.5 entirely.
ENDPOINT = {
    ('seedance-2.5', 't2v'): 'bytedance/seedance-2.5/text-to-video',
    ('seedance-2.5', 'i2v'): 'bytedance/seedance-2.5/image-to-video',
    ('seedance-2.5', 'r2v'): 'bytedance/seedance-2.5/reference-to-video',
    ('seedance-2.5', 'edit'): 'bytedance/seedance-2.5/video-edit',
    ('seedance-2.5', 'extend'): 'bytedance/seedance-2.5/video-extend',
    ('minimax-h3', 't2v'): 'minimax/h3/text-to-video',
    ('minimax-h3', 'i2v'): 'minimax/h3/image-to-video',
    ('minimax-h3', 'r2v'): 'minimax/h3/reference-to-video',
    # Genjutsu, read from GET /models 2026-09-24 — `higgsfiled` IS the vendor's slug; copy it verbatim.
    ('genjutsu', 'object-swap'): 'higgsfiled/genjutsu/object-swap/v1.0',
    ('genjutsu', 'motion-transfer'): 'higgsfiled/genjutsu/motion-transfer/v1.0',
}
DUR_MIN, DUR_MAX = 4, 30
H3_DUR = (5, 15)
GENJUTSU_REFS = (1, 8)                # its validator, 2026-09-24: [] → "should be non-empty", 9 → "too long"
PROMPT_WARN = 5000                    # 6629 worked once; 7840 was trimmed. No hard cap is documented.
MAX_CONCURRENT_RETRIES = 40           # the limit is 4 in flight; a seed clears in minutes, not hours


def csv(s):
    return [x for x in (s or '').split(',') if x]


def load_gate(path):
    spec = importlib.util.spec_from_file_location('refs_gate', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def probe_source_seconds(root, urls, name):
    """Genjutsu bills per second of INPUT video and /estimate never returns the number, so the length is
    READ from the local file the upload ledger recorded for this NAME — never typed from memory."""
    meta = (urls.get('_meta') or {}).get(name) or {}
    src = meta.get('source')
    if not src:
        sys.exit(f'cannot price {name}: hf-api-urls.json records no local source for it — '
                 f'pass --input-seconds <the clip length>')
    p = src if os.path.isabs(src) else os.path.join(root, src)
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        sys.exit(f'ffprobe could not read the length of {p} — pass --input-seconds')


def submit_one(endpoint, body, label):
    """One submit, with the concurrency wait the 400-not-429 trap forces. Returns the parsed reply or
    None. A 400 that is NOT the concurrency string is a real rejection and is returned as such."""
    for attempt in range(MAX_CONCURRENT_RETRIES):
        code, out = hf.api('POST', '/' + endpoint.lstrip('/'), body, timeout=180)
        if hf.concurrency_hit(code, out):
            wait = min(15 + attempt * 5, 60)
            print(f'  {label}: concurrency limit reached (HTTP 400, the vendor\'s own wording — '
                  f'NOT a malformed body, NOT 429, no Retry-After). waiting {wait}s '
                  f'[{attempt + 1}/{MAX_CONCURRENT_RETRIES}]', flush=True)
            time.sleep(wait)
            continue
        return code, out
    return None, {'error': f'concurrency limit still held after {MAX_CONCURRENT_RETRIES} waits'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.')
    ap.add_argument('--scene', required=True)
    ap.add_argument('--prompt', required=True)
    ap.add_argument('--mode', required=True,
                    choices=['t2v', 'i2v', 'r2v', 'edit', 'extend', 'object-swap', 'motion-transfer'])
    ap.add_argument('--model', default='seedance', help='seedance (2.5), h3, or genjutsu')
    ap.add_argument('--duration', type=int, help='generated seconds; OMIT for --mode edit')
    ap.add_argument('--input-seconds', type=float, default=0,
                    help='source seconds for edit/extend or a video ref (0.6x tier), or a Genjutsu '
                         'source (probed from the upload ledger when omitted) — THEY BILL')
    ap.add_argument('--refs', default='', help='comma-separated image reference NAMES')
    ap.add_argument('--video-refs', default='', help='comma-separated video reference NAMES → 0.6x tier')
    ap.add_argument('--audio', default='', help='comma-separated audio reference NAMES (WAV; no mp3)')
    ap.add_argument('--start-image', help='i2v first frame')
    ap.add_argument('--end-image', help='i2v last frame (only with --start-image)')
    ap.add_argument('--source', help='edit/extend/genjutsu: a hosted NAME, or the keeper\'s own output URL')
    ap.add_argument('--seeds', type=int, default=1)
    ap.add_argument('--resolution', default='480p', choices=list(hf.RASTER),
                    help='NO 1080p exists on this API; 720p is 2.25x 480p')
    ap.add_argument('--ratio', default='9:16',
                    choices=['16:9', '4:3', '1:1', '3:4', '9:16', '21:9'])
    ap.add_argument('--output-format', default='mp4', choices=['mp4', 'mov'])
    ap.add_argument('--no-audio', action='store_true', help='generate_audio: false')
    ap.add_argument('--births', default='')
    ap.add_argument('--prose', default='')
    ap.add_argument('--fresh-scene', action='store_true')
    ap.add_argument('--gate', default=DEFAULT_GATE)
    ap.add_argument('--despite-gate', action='store_true',
                    help='submit although the refs gate FAILED — the override the cost line prices')
    ap.add_argument('--go', action='store_true')
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    key = a.scene.lower().replace('-', '')
    model = hf.MODEL_ALIAS.get(a.model.lower(), a.model.lower())
    refs, vrefs, auds = csv(a.refs), csv(a.video_refs), csv(a.audio)
    ep = ENDPOINT.get((model, a.mode))
    if not ep:
        sys.exit(f'no endpoint for model {model} mode {a.mode} — '
                 f'available: {", ".join(sorted(m + "/" + k for m, k in ENDPOINT))}\n'
                 f'  read the catalog yourself: hf_api.py models --grep {model.split("-")[0]}')

    # ── shape rules, each one a vendor fact rather than a preference ───────────────────────────────
    genjutsu = model == 'genjutsu'
    if genjutsu:
        if a.duration is not None:
            sys.exit('Genjutsu takes NO duration: the source clip decides it — and this endpoint ACCEPTS '
                     'unknown fields silently, so a duration would look sent and do nothing')
        if not a.source:
            sys.exit('--model genjutsu needs --source: the clip being re-cast (a hosted NAME, or a URL)')
        if not GENJUTSU_REFS[0] <= len(refs) <= GENJUTSU_REFS[1]:
            sys.exit(f'--refs must carry {GENJUTSU_REFS[0]}-{GENJUTSU_REFS[1]} images for Genjutsu (read '
                     f'from its own validator 2026-09-24); got {len(refs)}')
        if vrefs or auds or a.start_image or a.end_image:
            sys.exit('Genjutsu takes image references only — no --video-refs / --audio / --start-image / '
                     '--end-image: --source IS the video')
    elif a.mode == 'edit':
        if a.duration is not None:
            sys.exit('--mode edit takes NO duration: the SOURCE decides it, and sending one is an error')
        if not a.source:
            sys.exit('--mode edit needs --source (a hosted NAME or the keeper\'s own output URL)')
    else:
        if a.duration is None:
            sys.exit(f'--duration is required for --mode {a.mode}')
        lo, hi = H3_DUR if model == 'minimax-h3' else (DUR_MIN, DUR_MAX)
        if not lo <= a.duration <= hi:
            sys.exit(f'--duration must be {lo}-{hi} s for {model} (read from the endpoint schema); '
                     f'got {a.duration}')
    if a.mode == 'extend' and not a.source:
        sys.exit("--mode extend needs --source, and on this API it is a video_url — NOT a job id.\n"
                 "  Feed the keeper's own output URL back (outputs are retained >= 7 days).")
    if a.mode == 'i2v' and not a.start_image:
        sys.exit('--mode i2v needs --start-image')
    if a.end_image and not a.start_image:
        sys.exit('--end-image is only accepted WITH a --start-image')
    if a.mode == 'r2v' and not (refs or vrefs or auds):
        sys.exit('--mode r2v needs at least one reference: --refs / --video-refs / --audio')
    if len(refs) > 30 or len(vrefs) > 10 or len(auds) > 10:
        sys.exit(f'over the endpoint\'s own caps (image_urls 1-30, video_urls 1-10, audio_urls 1-10): '
                 f'{len(refs)}/{len(vrefs)}/{len(auds)}')

    # ── the refs gate ──────────────────────────────────────────────────────────────────────────────
    gate = load_gate(a.gate)
    g = gate.Gate(root)
    prompt_path = a.prompt if os.path.isabs(a.prompt) else os.path.join(root, a.prompt)
    text = open(prompt_path, encoding='utf-8').read()
    m = g.spot_re.search(os.path.basename(prompt_path))
    spot = m.group(1) if m else None
    gate_refs = refs + vrefs + auds
    # A Genjutsu source is the thing being EDITED — the gate's start image, exactly as ref 1 of an
    # image-to-image still is (gen_stills.py): its lineage must reach a keeper or a client import.
    gate_start = a.source if (genjutsu and not a.source.startswith('http')) else a.start_image
    ok, rows, roles = g.check(text, gate_refs, TARGET, gate_start, csv(a.births), csv(a.prose),
                              spot, fresh=a.fresh_scene)

    urls = {}
    lp = os.path.join(root, LEDGER_NAME)
    if os.path.exists(lp):
        with open(lp, encoding='utf-8') as f:
            urls = json.load(f)

    def url_of(name, allow_raw=False):
        if name.startswith('http'):
            if allow_raw:
                return name
            sys.exit(f'{name[:40]}… is a raw URL — the gate needs a NAME; host it free with '
                     f'hf_api_upload.py --root {root} <file> --name <NAME>')
        u = urls.get(name) if name != '_meta' else None
        if not isinstance(u, str):
            sys.exit(f'no hosted URL for {name} ({lp}) — '
                     f'hf_api_upload.py --root {root} <file> --name {name}')
        return u

    in_s = float(a.input_seconds or 0)
    if genjutsu and not in_s:
        in_s = probe_source_seconds(root, urls, a.source)

    # ── the cost line ──────────────────────────────────────────────────────────────────────────────
    print(f"REFS-GATE {a.prompt}  refs: {', '.join(gate_refs) or '-'}  start: {gate_start or '-'}")
    print(gate.fmt(rows))
    n_fail = sum(1 for r in rows if r[1] == 'FAIL')
    print('REFS-GATE PASS' if ok else f'REFS-GATE FAIL ({n_fail} row(s))')

    dur = a.duration if a.duration is not None else in_s
    has_video_ref = bool(vrefs) or a.mode in ('edit', 'extend')
    Q = hf.quote(model, a.resolution, dur, in_s, a.seeds, ep, has_video_ref, len(refs))
    bal = hf.balance()
    print(f'venue: Higgsfield API · {ep} · {a.resolution} · '
          + ("aspect: the source's own" if genjutsu else f'ratio {a.ratio}'))
    print(hf.cost_line(Q, bal if bal['entries'] else None))

    # The extend arithmetic, stated as a priced comparison rather than a rule (SKILL.md § 0).
    if a.mode == 'extend' and a.input_seconds and a.duration:
        fresh = hf.quote(model, a.resolution, a.duration, 0, a.seeds, 'text-to-video', False, 0)
        if a.duration <= 1.5 * a.input_seconds:
            print(f"  ⚠ EXTEND IS THE DEARER ROUTE HERE. Both durations bill at the 0.6× tier, so an "
                  f"extend beats a fresh generation only when gen > 1.5 × in "
                  f"({a.duration} s vs {1.5 * a.input_seconds:g} s). A fresh {a.duration} s take is "
                  f"${fresh['usd_total']:.4f} against ${Q['usd_total']:.4f} here — "
                  f"${Q['usd_total'] - fresh['usd_total']:.4f} cheaper. Extend still buys the exact "
                  f"continuation a fresh take cannot. Your call.")
        else:
            print(f"  extend is the cheaper route: a fresh {a.duration} s take would be "
                  f"${fresh['usd_total']:.4f} against ${Q['usd_total']:.4f}.")
    if len(text) > PROMPT_WARN:
        print(f'  ⚠ prompt is {len(text)} chars — 6629 worked once and 7840 was trimmed by the venue; '
              f'no hard cap is documented.')

    # ── the body ───────────────────────────────────────────────────────────────────────────────────
    body = {'prompt': text}
    if genjutsu:
        # ONLY the four fields its validator knows: it ACCEPTS anything else silently (measured
        # 2026-09-24), so a stray field would look sent and do nothing.
        body.update({'video_url': url_of(a.source, allow_raw=True),
                     'image_urls': [url_of(r) for r in refs], 'resolution': a.resolution})
    elif a.mode != 'edit':
        body['duration'] = a.duration
        body['aspect_ratio'] = a.ratio          # explicit or the venue picks for you
    if model not in ('minimax-h3', 'genjutsu'):
        body['resolution'] = a.resolution
        body['generate_audio'] = not a.no_audio
        body['output_format'] = a.output_format
    if a.mode == 'i2v':
        body['image_url'] = url_of(a.start_image)
        if a.end_image:
            body['end_image_url'] = url_of(a.end_image)
    if a.mode in ('edit', 'extend'):
        body['video_url'] = url_of(a.source, allow_raw=True)
    if a.mode == 'r2v':
        if refs:
            body['image_urls'] = [url_of(r) for r in refs]
        if vrefs:
            body['video_urls'] = [url_of(r) for r in vrefs]
        if auds:
            body['audio_urls'] = [url_of(r) for r in auds]

    if not a.go:
        shown = dict(body, prompt=text[:120] + ' …')
        print(json.dumps(shown, indent=2))
        print('DRY RUN — nothing submitted (paste the table + cost into the GO ask; re-run with --go).')
        if not ok:
            print(f'  the gate FAILED on {n_fail} row(s). That is a PRICED WARNING, not a veto: each '
                  f'FAIL above names its free fix, and proceeding anyway costs ${Q["usd_total"]:.4f} '
                  f'billed at acceptance whether or not the reference resolves. Override with '
                  f'--go --despite-gate.')
        sys.exit(0)
    if not ok and not a.despite_gate:
        sys.exit(f'REFS-GATE FAIL ({n_fail} row(s)) and no --despite-gate. Not a veto — the fixes above '
                 f'are free, and the override is one flag. Proceeding blind costs '
                 f'${Q["usd_total"]:.4f}, billed at acceptance even if a reference has lapsed.')

    # ── submit ─────────────────────────────────────────────────────────────────────────────────────
    os.makedirs(os.path.join(root, 'receipts', 'raw'), exist_ok=True)
    os.makedirs(os.path.join(root, 'takes'), exist_ok=True)
    rp = os.path.join(root, 'receipts', f'hfapi-jobs-{key}.json')
    R = []
    for s in range(1, a.seeds + 1):
        name = f'{a.scene}-s{s}'
        code, out = submit_one(ep, body, name)
        with open(os.path.join(root, 'receipts', 'raw', f'{key}-s{s}.json'), 'w', encoding='utf-8') as f:
            f.write(json.dumps({'http': code, 'reply': out}, indent=1))
        if not (code and str(code).startswith('2')) or not isinstance(out, dict):
            print(f'{name} REJECTED HTTP {code} — '
                  f'{(json.dumps(out) if not isinstance(out, str) else out)[:300]}')
            continue
        rid = out.get('request_id') or out.get('id')
        status_url = out.get('status_url')
        if not (rid and status_url):
            # Use the RETURNED urls; never construct them. Without one there is nothing to poll, and
            # the job may still be billing — so this is loud, and the raw reply is already on disk.
            print(f'{name} ACCEPTED but the reply carries no request_id/status_url — '
                  f'{json.dumps(out)[:300]}\n  raw reply: receipts/raw/{key}-s{s}.json')
            continue
        rec = {'name': name, 'request_id': rid, 'status_url': status_url,
               'cancel_url': out.get('cancel_url'), 'endpoint': ep, 'model': model, 'mode': a.mode,
               'resolution': a.resolution, 'duration': a.duration, 'input_seconds': in_s,
               'tier': Q.get('tier'), 'est_tokens': Q.get('tokens'),
               'estimate_usd': Q['usd_each'], 'estimate_usd_list': Q['usd_each_list'],
               'estimate_credits': round(Q['usd_each'] / hf.CREDIT_USD, 4),
               'submitted': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
        R.append(rec)
        # Receipt and WALLET line BEFORE polling: billing happens at acceptance, and the wallet has no
        # balance endpoint — an unrecorded spend is not merely untracked, it is unknowable.
        with open(rp, 'w', encoding='utf-8') as f:
            json.dump(R, f, indent=1)
        hf.spend(Q['usd_each'], rec['estimate_credits'], take=name, request_id=rid, endpoint=ep,
                 resolution=a.resolution, duration=(in_s if genjutsu else a.duration), root=root,
                 note=('ESTIMATE at acceptance — per INPUT second; /estimate returns no number' if genjutsu
                       else 'ESTIMATE at acceptance — Seedance returns no number'))
        g.record(name, TARGET, os.path.relpath(prompt_path, root),
                 gate_refs + ([gate_start] if gate_start else []), csv(a.births), roles)
        print(f'{name} request {rid}  (BILLED at acceptance, est ${Q["usd_each"]:.4f})', flush=True)

    with open(rp, 'w', encoding='utf-8') as f:
        json.dump(R, f, indent=1)
    bal = hf.balance()
    print(f'receipts {rp} ({len(R)} requests) · est ${Q["usd_each"] * len(R):.4f} · '
          f'wallet now ${bal["usd"]:.2f} / {bal["credits"]:.1f} cr (local ledger)')
    if R:
        log = open(os.path.join(root, 'takes', f'hfapi-poll-{key}.log'), 'ab')
        poller = os.path.join(_here, 'hf_api_poll.py')
        subprocess.Popen(['python3', poller, '--root', root, rp], stdout=log,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        print(f'poll detached → takes/hfapi-poll-{key}.log → takes/{a.scene}-s<n>.{a.output_format}  '
              f'(match " DONE | FAILED|HFAPI-POLL-END")')


if __name__ == '__main__':
    main()
