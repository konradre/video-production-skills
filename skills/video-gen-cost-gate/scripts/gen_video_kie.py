#!/usr/bin/env python3
"""gen_video_kie.py — the ONE way a Gemini Omni take leaves a project on kie.ai, the FIRST Omni venue (since
2026-09-25; fal is the fallback: gen_video_fal.py --engine omni). Runs the refs gate first; prints the
cost line from kie's step price beside fal's per-second price; without --go it STOPS there (paste the gate table
and the cost into the GO ask). With --go: one createTask per seed, the reply parsed shape-safely, the raw reply
in receipts/raw/kie-<key>-s<n>.json, receipts/kie-tasks-<key>.json written BEFORE polling, a gate-ledger record
per take, and kie_poll.py detached → takes/<SCENE>-s<n>.mp4 (log takes/kie-poll-<key>.log).

  gen_video_kie.py --root <project> --scene S01-H1 --prompt prompts/omni/S01-H1.txt
                   --mode t2v|i2v|flf|r2v --duration 4|6|8|10 [--refs NAME,NAME] [--start-image NAME]
                   [--end-image NAME] [--audio-ids ID,ID] [--character-ids ID,ID] [--seeds 1] [--seed N]
                   [--model flash11|omni] [--resolution 720p] [--ratio 9:16]
                   [--births R,R] [--prose X,Y] [--fresh-scene] [--despite-gate] [--go]
  gen_video_kie.py --selftest

Reference NAMES resolve through <root>/refs-urls.json (kie_upload.py, which MERGES). kie uploads lapse in about
24 h ("Image fetch failed" = expired, re-upload). A raw URL is refused: the gate must see a name.

WIRE FACTS, read from kie's own docs and pricing 2026-09-25 (VENUES.md § Creator-style talking heads). None is
receipt-proven yet: the first real take's receipt settles them.

  1. TWO models at one price. google/gemini-omni-flash-1-1 (--model flash11) is the DEFAULT: the newer release
     (27 Aug 2026) and the model the fal takes were measured on. gemini-omni-video (--model omni) is the original
     release: no 360p, no first or last frame.
  2. `duration` is a STRING and only "4" | "6" | "8" | "10". A line between two steps buys the next step and pads
     its tail (video-prompt-dialects PHONE-NATIVE.md § Dialogue). The price is per step and FLAT across 360p,
     720p and 1080p; 4k is its own row.
  3. The inputs share 7 UNITS: an image 1, a character id 1 (at most 3), the one video 2. The first frame
     (`first_frame_url`, 1.1 only) EXCLUDES image_urls, video_list, character_ids and audio_ids, so a start
     image and a pinned voice cannot ride together: put the start image in --refs and run r2v instead.
  4. `audio_ids` (at most 3) are DESIGNED voices from kie's gemini-omni-audio (a preset Gemini voice, a
     description, an example line); `character_ids` come from gemini-omni-character. Neither takes an uploaded
     recording, and this script only passes ids that already exist.
  5. A video input (`video_list`, 2 units, $0.84 flat, the model then sets the duration) is NOT wired here:
     kie_upload.py hosts images only.
  6. Billing is at task CREATION, the rule gen_stills.py has held on the same jobs API. A reply without code 200
     created no task and billed nothing.
  7. `resolution` is sent lowercase, as kie's enum lists it (360p | 720p | 1080p | 4k); its prose writes "720P".
"""
import argparse, importlib.util, json, os, subprocess, sys, time, urllib.error, urllib.request

CREATE = 'https://api.kie.ai/api/v1/jobs/createTask'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
DEFAULT_GATE = os.path.expanduser('~/.claude/skills/video-refs-continuity/scripts/refs_gate.py')

MODELS = {   # kie job model ids, read from kie's docs 2026-09-25
    'flash11': {'model': 'google/gemini-omni-flash-1-1', 'res': ('360p', '720p', '1080p', '4k'), 'frames': True},
    'omni': {'model': 'gemini-omni-video', 'res': ('720p', '1080p', '4k'), 'frames': False},
}
STEPS = (4, 6, 8, 10)
# USD per generation by duration step, kie's own pricing 2026-09-25 (1 credit = $0.005). FLAT across 360p, 720p
# and 1080p; 4k is its own row. A video input would bill $0.84 flat ($1.26 at 4k) and is not wired.
PRICE = {'std': {4: 0.315, 6: 0.42, 8: 0.525, 10: 0.63}, '4k': {4: 0.735, 6: 0.84, 8: 0.945, 10: 1.05}}
CREDIT_USD = 0.005
FAL_RATE = {'360p': 0.03, '720p': 0.10, '1080p': 0.15, '4k': 0.30}   # the fallback, $/s (VENUES.md, fal row)
UNITS_MAX, CHARACTERS_MAX, AUDIO_MAX, SEED_MAX = 7, 3, 3, 2147483647
RATIOS = ('16:9', '9:16')
MODES = ('t2v', 'i2v', 'flf', 'r2v')


def price(resolution, duration):
    return PRICE['4k' if resolution == '4k' else 'std'][duration]


def step_up(seconds):
    return next((s for s in STEPS if seconds <= s), None)


def build_input(mode, prompt, duration, resolution, ratio, model='flash11', image_urls=(), first=None,
                last=None, audio_ids=(), character_ids=(), seed=None):
    """The createTask `input` for one take. Pure, so --selftest covers it. Each rule is a kie documentation fact,
    and each raises BEFORE the billed call instead of letting a task fail after creation."""
    m = MODELS[model]
    if mode not in MODES:
        raise ValueError(f'mode must be one of {MODES}')
    if duration not in STEPS:
        up = step_up(duration)
        hint = f' — a {duration} s line buys the {up} s step and pads its tail' if up else ''
        raise ValueError(f'duration must be one of {STEPS} s, kie sells fixed steps{hint}')
    if resolution not in m['res']:
        raise ValueError(f'{m["model"]} renders {", ".join(m["res"])}; got {resolution}')
    if ratio not in RATIOS:
        raise ValueError(f'aspect ratio must be one of {RATIOS}; got {ratio}')
    if mode in ('i2v', 'flf') and not m['frames']:
        raise ValueError(f'{m["model"]} has no first or last frame: use --model flash11, or put the start image '
                         f'in --refs and run r2v')
    if mode in ('i2v', 'flf') and not first:
        raise ValueError(f'--mode {mode} needs --start-image')
    if mode == 'flf' and not last:
        raise ValueError('--mode flf needs --end-image')
    if last and mode != 'flf':
        raise ValueError('--end-image rides only with --mode flf')
    if first and mode not in ('i2v', 'flf'):
        raise ValueError(f'--start-image rides only with --mode i2v or flf; in {mode} put it in --refs')
    if mode in ('i2v', 'flf') and (image_urls or audio_ids or character_ids):
        raise ValueError('a first frame EXCLUDES image refs, audio ids and character ids on kie: drop them, '
                         'or put the start image in --refs and run r2v')
    if mode == 'r2v' and not (image_urls or character_ids):
        raise ValueError('--mode r2v needs --refs or --character-ids')
    if mode == 't2v' and image_urls:
        raise ValueError('--mode t2v takes no image refs; run r2v')
    if len(audio_ids) > AUDIO_MAX:
        raise ValueError(f'at most {AUDIO_MAX} audio ids; got {len(audio_ids)}')
    if len(character_ids) > CHARACTERS_MAX:
        raise ValueError(f'at most {CHARACTERS_MAX} character ids; got {len(character_ids)}')
    used = len(image_urls) + len(character_ids)
    if used > UNITS_MAX:
        raise ValueError(f'the inputs share {UNITS_MAX} units (an image 1, a character id 1); this take uses {used}')
    if seed is not None and not 0 <= int(seed) <= SEED_MAX:
        raise ValueError(f'seed must be 0-{SEED_MAX}; got {seed}')
    inp = {'prompt': prompt, 'duration': str(duration), 'resolution': resolution, 'aspect_ratio': ratio}
    if first:
        inp['first_frame_url'] = first
    if last:
        inp['last_frame_url'] = last
    if image_urls:
        inp['image_urls'] = list(image_urls)
    if audio_ids:
        inp['audio_ids'] = list(audio_ids)
    if character_ids:
        inp['character_ids'] = list(character_ids)
    if seed is not None:
        inp['seed'] = int(seed)
    return inp


def selftest():
    fails = []

    def expect(label, fn, err=None):
        try:
            r = fn()
        except ValueError as e:
            if err and err in str(e):
                print(f'ok   {label}  ({e})')
            else:
                fails.append(label); print(f'FAIL {label}: {e}')
            return None
        if err:
            fails.append(label); print(f'FAIL {label}: no error, expected one containing {err!r}')
        else:
            print(f'ok   {label}')
        return r

    U = ['https://example.invalid/a.jpg']
    r = expect('r2v body', lambda: build_input('r2v', 'p', 8, '720p', '9:16', image_urls=U, audio_ids=['a1'], seed=7))
    if r and not (r['duration'] == '8' and r['image_urls'] == U and r['audio_ids'] == ['a1'] and r['seed'] == 7
                  and 'first_frame_url' not in r):
        fails.append('r2v body shape'); print('FAIL r2v body shape', r)
    r = expect('i2v body', lambda: build_input('i2v', 'p', 4, '360p', '9:16', first=U[0]))
    if r and set(r) != {'prompt', 'duration', 'resolution', 'aspect_ratio', 'first_frame_url'}:
        fails.append('i2v body shape'); print('FAIL i2v body shape', r)
    expect('a line between steps', lambda: build_input('t2v', 'p', 7, '720p', '9:16'), 'buys the 8 s step')
    expect('past the top step', lambda: build_input('t2v', 'p', 12, '720p', '9:16'), 'fixed steps')
    expect('seven images fill the units', lambda: build_input('r2v', 'p', 6, '720p', '9:16', image_urls=U * 7))
    expect('eight images overflow', lambda: build_input('r2v', 'p', 6, '720p', '9:16', image_urls=U * 8), 'share 7')
    expect('six images + one character', lambda: build_input('r2v', 'p', 6, '720p', '9:16', image_urls=U * 6,
                                                               character_ids=['c1']))
    expect('five images + three characters', lambda: build_input('r2v', 'p', 6, '720p', '9:16', image_urls=U * 5,
                                                                  character_ids=['c1', 'c2', 'c3']), 'uses 8')
    expect('four characters', lambda: build_input('r2v', 'p', 6, '720p', '9:16', character_ids=list('abcd')),
           'at most 3 character')
    expect('four audio ids', lambda: build_input('t2v', 'p', 6, '720p', '9:16', audio_ids=list('abcd')),
           'at most 3 audio')
    expect('first frame excludes a voice', lambda: build_input('i2v', 'p', 6, '720p', '9:16', first=U[0],
                                                               audio_ids=['a1']), 'EXCLUDES')
    expect('omni has no first frame', lambda: build_input('i2v', 'p', 6, '720p', '9:16', model='omni', first=U[0]),
           'no first or last frame')
    expect('omni has no 360p', lambda: build_input('t2v', 'p', 6, '360p', '9:16', model='omni'), 'renders')
    expect('flf needs an end', lambda: build_input('flf', 'p', 6, '720p', '9:16', first=U[0]), 'needs --end-image')
    expect('a start image outside i2v', lambda: build_input('r2v', 'p', 6, '720p', '9:16', image_urls=U, first=U[0]),
           'rides only')
    expect('a bad ratio', lambda: build_input('t2v', 'p', 6, '720p', '1:1'), 'aspect ratio')
    for (res, dur), want in {('720p', 8): 0.525, ('1080p', 8): 0.525, ('360p', 4): 0.315, ('4k', 10): 1.05}.items():
        got = price(res, dur)
        if abs(got - want) > 1e-9:
            fails.append(f'price {res} {dur}'); print(f'FAIL price {res} {dur} s = {got}, want {want}')
        else:
            print(f'ok   price {res} {dur} s = ${got}')
    print('SELFTEST PASS' if not fails else f'SELFTEST FAIL: {", ".join(fails)}')
    return 0 if not fails else 1


def csv(s):
    return [x.strip() for x in (s or '').split(',') if x.strip()]


def load_gate(path):
    spec = importlib.util.spec_from_file_location('refs_gate', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.')
    ap.add_argument('--scene', help='scene key, e.g. S01-H1 (takes are <scene>-s<n>)')
    ap.add_argument('--prompt', help='the prompt file')
    ap.add_argument('--mode', choices=MODES, help='i2v = first frame only; flf = first + last frame (1.1 only)')
    ap.add_argument('--duration', type=int, help='4 | 6 | 8 | 10 — kie sells fixed steps')
    ap.add_argument('--model', default='flash11', choices=list(MODELS),
                    help='flash11 = google/gemini-omni-flash-1-1, the default and the newer release; '
                         'omni = gemini-omni-video, the original')
    ap.add_argument('--resolution', default='720p', help='720p is Omni native; 1080p costs the same here')
    ap.add_argument('--ratio', default='9:16', choices=RATIOS)
    ap.add_argument('--refs', default='', help='r2v: image NAMES, in the order the prompt cites them')
    ap.add_argument('--start-image', help='i2v / flf: the first-frame NAME (excludes every other input)')
    ap.add_argument('--end-image', help='flf: the last-frame NAME')
    ap.add_argument('--audio-ids', default='', help='designed voice ids from gemini-omni-audio, at most 3')
    ap.add_argument('--character-ids', default='', help='ids from gemini-omni-character, at most 3')
    ap.add_argument('--seeds', type=int, default=1)
    ap.add_argument('--seed', type=int, help='a base seed; take n uses base + n - 1')
    ap.add_argument('--births', default='')
    ap.add_argument('--prose', default='')
    ap.add_argument('--fresh-scene', action='store_true')
    ap.add_argument('--despite-gate', action='store_true',
                    help='submit although the refs gate FAILED: the override the cost line prices')
    ap.add_argument('--gate', default=DEFAULT_GATE)
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--go', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    for need in ('scene', 'prompt', 'mode', 'duration'):
        if getattr(a, need) is None:
            ap.error(f'--{need} is required')
    if a.seeds < 1:
        ap.error('--seeds must be at least 1')

    root = os.path.abspath(a.root)
    key = a.scene.lower().replace('-', '')
    refs = csv(a.refs)
    audio_ids, character_ids = csv(a.audio_ids), csv(a.character_ids)
    names = [n for n in refs + [a.start_image, a.end_image] if n]
    for n in names:
        if n.startswith('http'):
            sys.exit(f'{n[:40]}… is a raw URL: the gate needs a NAME. Upload it with kie_upload.py <file> '
                     f'--json-out {os.path.join(root, "refs-urls.json")} (uploads lapse in ~24 h)')

    gate = load_gate(a.gate)
    g = gate.Gate(root)
    prompt_path = a.prompt if os.path.isabs(a.prompt) else os.path.join(root, a.prompt)
    text = open(prompt_path, encoding='utf-8').read().strip()
    m = g.spot_re.search(os.path.basename(prompt_path))
    spot = m.group(1) if m else None
    gate_refs = refs + ([a.end_image] if a.end_image else [])
    ok, rows, roles = g.check(text, gate_refs, 'kie', a.start_image, csv(a.births), csv(a.prose), spot,
                              fresh=a.fresh_scene)
    n_fail = sum(1 for r in rows if r[1] == 'FAIL')
    print(f"REFS-GATE {a.prompt}  refs: {', '.join(gate_refs) or '-'}  start: {a.start_image or '-'}")
    print(gate.fmt(rows))
    print('REFS-GATE PASS' if ok else f'REFS-GATE FAIL ({n_fail} row(s))')

    ledger_p = os.path.join(root, 'refs-urls.json')
    urls = json.load(open(ledger_p, encoding='utf-8')) if os.path.exists(ledger_p) else {}

    def url_of(name):
        u = urls.get(name)
        if isinstance(u, str) and u.startswith('http'):
            return u
        if a.go:
            sys.exit(f'no kie url for {name} in {ledger_p}: kie_upload.py <file> --json-out {ledger_p}')
        return f'<{name}: not uploaded>'

    mdl = MODELS[a.model]['model']
    try:
        inputs = [build_input(a.mode, text, a.duration, a.resolution, a.ratio, a.model,
                              image_urls=[url_of(r) for r in refs],
                              first=url_of(a.start_image) if a.start_image else None,
                              last=url_of(a.end_image) if a.end_image else None,
                              audio_ids=audio_ids, character_ids=character_ids,
                              seed=(a.seed + s if a.seed is not None else None))
                  for s in range(a.seeds)]
    except ValueError as e:
        sys.exit(f'refused before any call: {e}')

    each = price(a.resolution, a.duration)
    fal_each = FAL_RATE.get(a.resolution, 0) * a.duration
    print(f'cost: {a.seeds} × {a.duration} s step × {a.resolution} on kie {mdl} = ${each:.3f} each '
          f'({round(each / CREDIT_USD)} credits) → ${each * a.seeds:.3f}   step price, flat across 360p/720p/1080p')
    print(f'      fal fallback (gen_video_fal.py --engine omni): ${FAL_RATE.get(a.resolution, 0):.2f}/s at '
          f'{a.resolution} = ${fal_each:.2f} for {a.duration} s, any whole second 3-10 there — quote both')
    if refs:
        print('  image order (reference media are read in list order, so cite them in this order):')
        for i, n in enumerate(refs, 1):
            print(f'    image {i} = {n}')
    body = {'model': mdl, 'input': inputs[0]}

    if not a.go:
        shown = dict(body, input=dict(inputs[0], prompt=text[:120] + ' …'))
        print(json.dumps(shown, indent=2, ensure_ascii=False))
        print('DRY RUN — nothing submitted (paste the table and the cost into the GO ask; re-run with --go).')
        if not ok:
            print(f'  the gate FAILED on {n_fail} row(s). That is a PRICED WARNING, not a veto: each FAIL above '
                  f'names its free fix, and proceeding anyway costs ${each * a.seeds:.3f}, billed at task creation '
                  f'whether or not a reference resolves. Override with --go --despite-gate.')
        sys.exit(0)
    if not ok and not a.despite_gate:
        sys.exit(f'REFS-GATE FAIL ({n_fail} row(s)) and no --despite-gate. Not a veto: the fixes above are free, '
                 f'and the override is one flag. Proceeding blind costs ${each * a.seeds:.3f}, billed at creation.')

    api_key = os.environ.get('KIE_API_KEY', '').strip()
    if not api_key:
        sys.exit('KIE_API_KEY is not set: load the env file in this command (set -a; . <file>; set +a)')
    os.makedirs(os.path.join(root, 'receipts', 'raw'), exist_ok=True)
    os.makedirs(os.path.join(root, 'takes'), exist_ok=True)
    rp = os.path.join(root, 'receipts', f'kie-tasks-{key}.json')
    R = json.load(open(rp, encoding='utf-8')) if os.path.exists(rp) else []
    known = {r['name'] for r in R}
    first_n = 1
    while f'{a.scene}-s{first_n}' in known:          # a later batch appends; it never overwrites a paid take
        first_n += 1
    for i, inp in enumerate(inputs):
        name = f'{a.scene}-s{first_n + i}'
        req = urllib.request.Request(CREATE, data=json.dumps({'model': mdl, 'input': inp}).encode(), method='POST',
                                     headers={'Authorization': f'Bearer {api_key}',
                                              'Content-Type': 'application/json', 'User-Agent': UA})
        try:
            raw = urllib.request.urlopen(req, timeout=120).read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            raw = f'HTTP {e.code} ' + e.read().decode('utf-8', 'replace')
        except Exception as e:                    # broad on purpose: RemoteDisconnected is not a URLError
            raw = f'NO REPLY {e}'
        with open(os.path.join(root, 'receipts', 'raw', f'kie-{key}-s{first_n + i}.json'), 'w', encoding='utf-8') as f:
            f.write(raw)
        try:
            d = json.loads(raw)
        except Exception:
            print(f'{name} UNPARSED reply: {raw[:200]} — no task id; read receipts/raw before any retry')
            continue
        task = (d.get('data') or {}).get('taskId') if isinstance(d, dict) else None
        if d.get('code') != 200 or not task:
            print(f'{name} REJECTED (no task created, $0.00): {d.get("code")} {d.get("msg")}')
            continue
        R.append({'name': name, 'task_id': task, 'model': mdl, 'mode': a.mode, 'duration': a.duration,
                  'resolution': a.resolution, 'ratio': a.ratio, 'seed': inp.get('seed'),
                  'estimate_usd': each, 'estimate_credits': round(each / CREDIT_USD),
                  'created': time.strftime('%Y-%m-%dT%H:%M:%S')})
        # the ledger record BEFORE polling: a hard kill still leaves a recoverable task id
        with open(rp, 'w', encoding='utf-8') as f:
            json.dump(R, f, indent=1)
        print(f'{name} task {task}  (BILLED at creation, est ${each:.3f})', flush=True)
        g.record(name, 'kie', os.path.relpath(prompt_path, root),
                 refs + [n for n in (a.start_image, a.end_image) if n], csv(a.births), roles)
    batch = [r for r in R if r['name'].startswith(f'{a.scene}-s') and r['name'] not in known]
    print(f'receipts {rp} ({len(batch)} new task(s)) · est ${each * len(batch):.3f}')
    if batch:
        jobs = os.path.join(root, 'receipts', f'kie-batch-{key}-{time.strftime("%Y%m%d-%H%M%S")}.json')
        with open(jobs, 'w', encoding='utf-8') as f:
            json.dump(batch, f, indent=1)
        poller = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kie_poll.py')
        log = open(os.path.join(root, 'takes', f'kie-poll-{key}.log'), 'ab')
        subprocess.Popen(['python3', poller, '--root', root, jobs], stdout=log, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
        print(f'poll detached → takes/kie-poll-{key}.log → takes/{a.scene}-s<n>.mp4  '
              f'(match " DONE | FAILED|KIE-POLL-END")')


if __name__ == '__main__':
    main()
