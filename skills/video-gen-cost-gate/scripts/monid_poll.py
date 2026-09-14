#!/usr/bin/env python3
"""monid_poll.py — poll monid runs listed in a jobs file ([{name, run_id, ...}]), download results to
takes/<name>.mp4, write receipts/monid-<name>-<run_id>.json (run, url, cost, billedUnits, bytes, dims).
Every log line starts with a timestamp: match " DONE | FAILED|MONID-POLL-END" anywhere in the line,
never ^DONE. Detach:
  python3 ~/.claude/skills/video-production/scripts/detach.py --log <abs>/takes/monid-poll-<key>.log \
    -- python3 <abs>/monid_poll.py --root <abs> <abs>/receipts/monid-runs-<key>.json

  monid_poll.py [--root <project>] [--timeout-min 30] [--every 20] <runs.json>

WIRE FACTS, measured 2026-09-14 (VENUES.md § monid) — each one is a trap that passes silently:

  1. NEVER `monid run --wait`. p50 is 245 s and p95 is 603 s against a 300 s default, so the wait
     times out on a run that is still billing. Fire, then poll — which is what this script is.
  2. `COMPLETED` means the RUN finished, never that the generation succeeded. A provider error is
     `status: COMPLETED` + `providerResponse.httpStatus` 404/500 — and it is NOT CHARGED ($0.00).
     Classifying that as a success would download nothing and report a take; classifying it as a
     billed failure would over-report spend. Both are checked below.
  3. `output.content` is a DICT whose `video_url` is a plain STRING — not a list, not {"url": …}.
     A parser written for the fal shape returns None here and the take is silently lost.
  4. The result URL expires in ~24 h, so the download happens at collection, not later.
  5. Cost is a RECEIPT, never arithmetic: `cost.value` and `billedUnits` come back on the run record
     and are stored verbatim. The estimate is kept beside them so drift is visible.
"""
import argparse, json, os, subprocess, sys, time, urllib.request


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def get_run(run_id):
    r = subprocess.run(['monid', 'runs', 'get', '-r', run_id, '--json'], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {'_unparsed': (r.stdout or '')[:300] + ' | ' + (r.stderr or '')[:300]}


def video_url_of(o):
    """`output.content.video_url` is a dict holding a plain STRING. Kept tolerant: the content key has
    already moved once, and a shape-specific parser is how a paid take goes missing."""
    out = o.get('output') if isinstance(o, dict) else None
    if isinstance(out, dict):
        c = out.get('content')
        if isinstance(c, dict):
            v = c.get('video_url')
            if isinstance(v, str) and v.startswith('http'):
                return v
            if isinstance(v, dict) and isinstance(v.get('url'), str):
                return v['url']
        if isinstance(c, list):
            for it in c:
                if isinstance(it, dict):
                    v = it.get('video_url')
                    if isinstance(v, str) and v.startswith('http'):
                        return v
                    if isinstance(v, dict) and isinstance(v.get('url'), str):
                        return v['url']
    acc = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str) and v.startswith('http') and ('video' in k.lower() or '.mp4' in v):
                    acc.append(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(o)
    return acc[0] if acc else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('runs')
    ap.add_argument('--root', default='.')
    ap.add_argument('--timeout-min', type=int, default=30, help='p95 is 603 s; 30 min covers a long tail')
    ap.add_argument('--every', type=int, default=20)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    os.makedirs(os.path.join(root, 'takes'), exist_ok=True)
    os.makedirs(os.path.join(root, 'receipts'), exist_ok=True)
    jobs = json.load(open(a.runs))
    done, t0 = {}, time.time()
    log('MONID-POLL-START', [j['name'] for j in jobs])

    while len(done) < len(jobs) and time.time() - t0 < 60 * a.timeout_min:
        for j in jobs:
            if j['name'] in done:
                continue
            o = get_run(j['run_id'])
            st = str(o.get('status', '')).upper()
            if st not in ('COMPLETED', 'FAILED', 'CANCELLED', 'CANCELED', 'ERROR'):
                log('…', j['name'], st or json.dumps(o)[:120])
                continue
            http = ((o.get('providerResponse') or {}).get('httpStatus'))
            cost = (o.get('cost') or {}).get('value')
            # COMPLETED is "the run finished". A provider error is COMPLETED + a non-2xx, and is free.
            if st != 'COMPLETED' or (isinstance(http, int) and not 200 <= http < 300):
                err = json.dumps((o.get('providerResponse') or {}).get('error') or o.get('error') or {})[:300]
                free = (cost in (0, 0.0, None))
                log('FAILED', j['name'], f'status={st} provider_http={http}',
                    f'cost=${cost} ({"FREE — provider errors are not charged" if free else "BILLED"})', err)
                done[j['name']] = {'run': o, 'error': f'{st}/{http}', 'cost_usd': cost, 'billed': not free}
                continue
            url = video_url_of(o)
            if not url:
                log('completed but no video_url', j['name'], json.dumps(o.get('output'))[:400])
                done[j['name']] = {'run': o, 'error': 'no url', 'cost_usd': cost}
                continue
            out = os.path.join(root, 'takes', f"{j['name']}.mp4")
            try:
                urllib.request.urlretrieve(url, out)       # ~24 h expiry — collect now
            except Exception as e:
                log('DOWNLOAD FAILED', j['name'], url[:80], str(e)[:120])
                continue                                    # the paid URL survives a failed download
            rec = {'name': j['name'], 'run_id': j['run_id'], 'submit': j, 'run': o, 'url': url,
                   'cost_usd': cost, 'billed_units': o.get('billedUnits'),
                   'estimate_usd': j.get('estimate_usd'), 'bytes': os.path.getsize(out),
                   'elapsed_s': round(time.time() - t0)}
            try:
                p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                    'stream=width,height,nb_frames,r_frame_rate', '-of', 'csv=p=0', out],
                                   capture_output=True, text=True)
                rec['dims'] = p.stdout.strip()              # a hosted model changed raster mid-session once
            except Exception:
                pass
            json.dump(rec, open(os.path.join(root, 'receipts', f"monid-{j['name']}-{j['run_id']}.json"), 'w'), indent=1)
            done[j['name']] = rec
            est = j.get('estimate_usd')
            drift = f" (est ${est:.4f})" if isinstance(est, (int, float)) else ''
            log('DONE', j['name'], rec['bytes'], 'B', f"${cost}{drift}", rec.get('dims', ''), url[:60])
        if len(done) < len(jobs):
            time.sleep(a.every)

    billed = sum(d.get('cost_usd') or 0 for d in done.values())
    log('MONID-POLL-END', len([d for d in done.values() if 'url' in d]), 'of', len(jobs),
        f'downloaded · billed ${billed:.6f}')


if __name__ == '__main__':
    main()
