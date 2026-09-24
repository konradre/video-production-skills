#!/usr/bin/env python3
"""kie_poll.py — poll kie.ai tasks listed in a jobs file ([{name, task_id, ...}], written by gen_video_kie.py) on
the unified recordInfo endpoint, download each result to takes/<name>.mp4, and write
receipts/kie-<name>-<task_id>.json (the task record verbatim, url, bytes, dims, the estimate beside it).
Every log line starts with a timestamp: match " DONE | FAILED|KIE-POLL-END" anywhere in the line, never ^DONE.
gen_video_kie.py detaches it; restart one by hand with:
  python3 ~/.claude/skills/video-production/scripts/detach.py --log <abs>/takes/kie-poll-<key>.log \
    -- python3 <abs>/kie_poll.py --root <abs> <abs>/receipts/kie-batch-<key>-<stamp>.json

  kie_poll.py [--root <project>] [--timeout-min 30] [--every 15] <jobs.json>
  kie_poll.py --selftest

WIRE FACTS — the jobs API gen_stills.py has polled for stills since 2026-09-10; the VIDEO record's shape is
unproven until the first receipt, so the parser below is tolerant and the receipt keeps the record verbatim:

  1. data.state runs waiting → queuing → generating → success | fail. Only `success` WITH a result url is a take.
  2. data.resultJson is a JSON STRING, not an object: json.loads it, then resultUrls[0].
  3. A `fail` carries failCode and failMsg. Whether kie charges a failed video task is UNVERIFIED: the log says
     so and the receipt keeps the record, never "free". "Image fetch failed" is an expired reference upload.
  4. The result url sits in kie's temporary store: download at collection, never later.
"""
import argparse, json, os, subprocess, sys, time, urllib.request

STATUS = 'https://api.kie.ai/api/v1/jobs/recordInfo'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
MISS_BUDGET = 30


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def parse(rec):
    """(state, url, error) from one recordInfo reply. Tolerant on purpose: a shape-specific parser is how a paid
    take goes missing, and resultJson has arrived both as a string and (defensively) as an object."""
    d = (rec or {}).get('data') if isinstance(rec, dict) else None
    if not isinstance(d, dict):
        return 'unknown', None, f'no data in reply: {json.dumps(rec)[:160]}'
    st = str(d.get('state') or '').lower()
    if st == 'fail':
        return 'fail', None, f"{d.get('failCode')} {d.get('failMsg') or 'no failMsg'}"
    if st != 'success':
        return st or 'unknown', None, None
    rj = d.get('resultJson')
    if isinstance(rj, str):
        try:
            rj = json.loads(rj or '{}')
        except Exception:
            return 'success', None, f'resultJson does not parse: {rj[:160]}'
    urls = (rj or {}).get('resultUrls') if isinstance(rj, dict) else None
    if isinstance(urls, list) and urls and isinstance(urls[0], str) and urls[0].startswith('http'):
        return 'success', urls[0], None
    return 'success', None, f'success with no result url: {json.dumps(rj)[:160]}'


def selftest():
    cases = [
        ('success, resultJson a string', {'code': 200, 'data': {'state': 'success',
         'resultJson': '{"resultUrls":["https://example.invalid/v.mp4"]}'}}, ('success', 'https://example.invalid/v.mp4', None)),
        ('success, resultJson an object', {'data': {'state': 'success', 'resultJson': {'resultUrls': ['https://e.invalid/a.mp4']}}},
         ('success', 'https://e.invalid/a.mp4', None)),
        ('generating', {'data': {'state': 'generating'}}, ('generating', None, None)),
        ('queuing', {'data': {'state': 'queuing'}}, ('queuing', None, None)),
    ]
    fails = []
    for label, rec, want in cases:
        got = parse(rec)
        (print(f'ok   {label}') if got == want else (fails.append(label), print(f'FAIL {label}: {got} != {want}')))
    for label, rec, want_state, frag in [
        ('fail carries the message', {'data': {'state': 'fail', 'failCode': 501, 'failMsg': 'Image fetch failed'}},
         'fail', 'Image fetch failed'),
        ('success with no url', {'data': {'state': 'success', 'resultJson': '{}'}}, 'success', 'no result url'),
        ('no data at all', {'code': 404, 'msg': 'task not found'}, 'unknown', 'no data'),
    ]:
        st, url, err = parse(rec)
        if st == want_state and url is None and err and frag in err:
            print(f'ok   {label}  ({err})')
        else:
            fails.append(label); print(f'FAIL {label}: {(st, url, err)}')
    print('SELFTEST PASS' if not fails else f'SELFTEST FAIL: {", ".join(fails)}')
    return 0 if not fails else 1


def get(task, key):
    rq = urllib.request.Request(f'{STATUS}?taskId={task}', headers={'Authorization': f'Bearer {key}', 'User-Agent': UA})
    return json.loads(urllib.request.urlopen(rq, timeout=60).read())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('jobs', nargs='?')
    ap.add_argument('--root', default='.')
    ap.add_argument('--timeout-min', type=int, default=30)
    ap.add_argument('--every', type=int, default=15)
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.jobs:
        ap.error('the jobs file is required')
    key = os.environ.get('KIE_API_KEY', '').strip()
    if not key:
        sys.exit('KIE_API_KEY is not set: load the env file in the detached command')
    root = os.path.abspath(a.root)
    os.makedirs(os.path.join(root, 'takes'), exist_ok=True)
    os.makedirs(os.path.join(root, 'receipts'), exist_ok=True)
    jobs = json.load(open(a.jobs, encoding='utf-8'))
    done, misses, t0 = {}, 0, time.time()
    log('KIE-POLL-START', [j['name'] for j in jobs])
    while len(done) < len(jobs) and time.time() - t0 < 60 * a.timeout_min:
        for j in jobs:
            if j['name'] in done:
                continue
            try:
                rec = get(j['task_id'], key)
            except Exception as e:                    # broad on purpose: RemoteDisconnected is not a URLError
                misses += 1
                log('poll-miss', j['name'], str(e)[:120])
                if misses > MISS_BUDGET:
                    log('KIE-POLL-END', 'LOST — poll misses over budget; the task ids are in', a.jobs)
                    sys.exit(1)
                continue
            st, url, err = parse(rec)
            data = rec.get('data') if isinstance(rec, dict) else None
            if st == 'fail' or (st == 'success' and not url):
                log('FAILED', j['name'], j['task_id'], err,
                    '— whether kie charges a failed video task is UNVERIFIED; the receipt keeps the record')
                done[j['name']] = {'error': err, 'task': data}
                with open(os.path.join(root, 'receipts', f"kie-{j['name']}-{j['task_id']}.json"), 'w',
                          encoding='utf-8') as f:
                    json.dump({'name': j['name'], 'task_id': j['task_id'], 'submit': j, 'task': data,
                               'error': err}, f, indent=1)
                continue
            if st != 'success':
                log('…', j['name'], st)
                continue
            out = os.path.join(root, 'takes', f"{j['name']}.mp4")
            try:
                rq = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
                with urllib.request.urlopen(rq, timeout=300) as resp, open(out, 'wb') as f:
                    f.write(resp.read())
            except Exception as e:
                log('DOWNLOAD FAILED', j['name'], url[:80], str(e)[:120])
                continue                                   # the paid url survives a failed download
            r = {'name': j['name'], 'task_id': j['task_id'], 'submit': j, 'task': data, 'url': url,
                 'estimate_usd': j.get('estimate_usd'), 'bytes': os.path.getsize(out),
                 'elapsed_s': round(time.time() - t0)}
            try:
                p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                    'stream=width,height,nb_frames,r_frame_rate', '-of', 'csv=p=0', out],
                                   capture_output=True, text=True)
                r['dims'] = p.stdout.strip()               # a hosted model changed raster mid-session once
            except Exception:
                pass
            with open(os.path.join(root, 'receipts', f"kie-{j['name']}-{j['task_id']}.json"), 'w',
                      encoding='utf-8') as f:
                json.dump(r, f, indent=1)
            done[j['name']] = r
            log('DONE', j['name'], r['bytes'], 'B', f"est ${j.get('estimate_usd')}", r.get('dims', ''), url[:60])
        if len(done) < len(jobs):
            time.sleep(a.every)
    got = [d for d in done.values() if 'url' in d]
    est = sum(d.get('estimate_usd') or 0 for d in got)
    log('KIE-POLL-END', len(got), 'of', len(jobs), f'downloaded · est ${est:.3f} (kie reports no per-task price)')


if __name__ == '__main__':
    main()
