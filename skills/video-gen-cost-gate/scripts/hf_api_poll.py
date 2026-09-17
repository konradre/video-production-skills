#!/usr/bin/env python3
"""hf_api_poll.py — poll Higgsfield REST API requests listed in a jobs file
([{name, request_id, status_url, ...}]), download results to takes/<name>.<ext>, write
receipts/hfapi-<name>-<request_id>.json, and write the WALLET REFUND for any request the venue did
not charge for. Every log line starts with a timestamp: match " DONE | FAILED|HFAPI-POLL-END"
anywhere in the line, never ^DONE. Detach:

  python3 ~/.claude/skills/video-production/scripts/detach.py \
    --log <abs>/takes/hfapi-poll-<key>.log -- \
    python3 <abs>/hf_api_poll.py --root <abs> <abs>/receipts/hfapi-jobs-<key>.json

  hf_api_poll.py [--root <project>] [--timeout-min 30] [--every 15] <jobs.json>

FIVE facts, each one a trap that passes silently:

  1. SIX statuses, FOUR terminal: queued · in_progress · completed · failed · nsfw · canceled.
     A poller that waits only for completed/failed hangs on nsfw and canceled until its own timeout.
  2. 🔴 `failed`, `nsfw` and a successfully cancelled `queued` request are NOT CHARGED, and reserved
     credits auto-refund. The wallet has NO balance endpoint, so unless the refund is written back
     here the local ledger drifts LOW on every refusal and the balance stops being usable.
  3. `completed` is not success — only a result with a file is. The output shape is
     {video:{url}} · {images:[{url}]} · {audio:{url}, audios:[]}, and some operations add zip/mov.
     A parser written for one shape silently loses a paid take, so the walk below is tolerant.
  4. Output URLs are retained >= 7 days — better than kie's ~24 h and monid's ~24 h — but the
     download still happens at collection, never later.
  5. 🔴 `urllib` is Cloudflare-blocked on this host (403, error code 1010) and the refusal is
     indistinguishable from a bad key. Status reads go over curl; only the RESULT download, which is
     on a different host, uses urlretrieve.
"""
import argparse, importlib.util, json, os, subprocess, sys, time, urllib.request

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('hf_api', os.path.join(_here, 'hf_api.py'))
hf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hf)

TERMINAL = ('completed', 'failed', 'nsfw', 'canceled', 'cancelled')
FREE = ('failed', 'nsfw', 'canceled', 'cancelled')       # not charged; reserved credits auto-refund
EXT = {'video': 'mp4', 'audio': 'wav', 'image': 'png'}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def result_url(o):
    """{video:{url}} · {images:[{url}]} · {audio:{url}} and the zip/mov extras, then a tolerant walk.
    A shape-specific parser is how a paid take goes missing."""
    if not isinstance(o, dict):
        return None, None
    for k, kind in (('video', 'video'), ('audio', 'audio'), ('image', 'image')):
        v = o.get(k)
        if isinstance(v, dict) and isinstance(v.get('url'), str):
            return v['url'], kind
        if isinstance(v, str) and v.startswith('http'):
            return v, kind
    for k, kind in (('videos', 'video'), ('images', 'image'), ('audios', 'audio')):
        v = o.get(k)
        if isinstance(v, list) and v:
            it = v[0]
            if isinstance(it, dict) and isinstance(it.get('url'), str):
                return it['url'], kind
            if isinstance(it, str) and it.startswith('http'):
                return it, kind
    res = o.get('result') or o.get('output') or o.get('data')
    if isinstance(res, dict):
        u, kind = result_url(res)
        if u:
            return u, kind
    acc = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str) and v.startswith('http') and (
                        any(e in v.lower() for e in ('.mp4', '.mov', '.wav', '.png', '.jpg', '.webp'))
                        or k.lower() in ('url', 'video_url', 'output_url')):
                    acc.append(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(o)
    if not acc:
        return None, None
    u = acc[0]
    kind = ('video' if any(e in u.lower() for e in ('.mp4', '.mov'))
            else 'audio' if '.wav' in u.lower() else 'image')
    return u, kind


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('jobs')
    ap.add_argument('--root', default='.')
    ap.add_argument('--timeout-min', type=int, default=30)
    ap.add_argument('--every', type=int, default=15)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    os.makedirs(os.path.join(root, 'takes'), exist_ok=True)
    os.makedirs(os.path.join(root, 'receipts'), exist_ok=True)
    with open(a.jobs, encoding='utf-8') as f:
        jobs = json.load(f)
    done, t0 = {}, time.time()
    log('HFAPI-POLL-START', [j['name'] for j in jobs])

    while len(done) < len(jobs) and time.time() - t0 < 60 * a.timeout_min:
        for j in jobs:
            if j['name'] in done:
                continue
            # The RETURNED status_url, never a constructed one.
            code, o = hf.api('GET', j['status_url'], timeout=60)
            if not isinstance(o, dict):
                log('…', j['name'], f'HTTP {code}', str(o)[:140])
                continue
            st = str(o.get('status', '')).lower()
            if st not in TERMINAL:
                log('…', j['name'], st or json.dumps(o)[:120])
                continue

            if st in FREE:
                # NOT CHARGED. Write the refund back or the local ledger — the only copy of this
                # wallet that exists — drifts low by one estimate on every refusal.
                est = j.get('estimate_usd')
                if est:
                    hf.refund(est, j.get('estimate_credits'), take=j['name'],
                              request_id=j.get('request_id'), status=st, root=root,
                              note=f'{st} is NOT charged; reserved credits auto-refund')
                log('FAILED', j['name'], f'status={st}', 'FREE — not charged'
                    + (f", refunded ${est:.4f} to the local ledger" if est else ''),
                    json.dumps(o.get('error') or o.get('detail') or {})[:240])
                done[j['name']] = {'status': o, 'error': st, 'billed': False, 'refunded_usd': est}
                continue

            url, kind = result_url(o)
            if not url:
                log('completed but NO RESULT URL', j['name'], json.dumps(o)[:400])
                done[j['name']] = {'status': o, 'error': 'no url'}
                continue
            ext = os.path.splitext(url.split('?')[0])[1].lstrip('.') or EXT.get(kind, 'bin')
            out = os.path.join(root, 'takes', f"{j['name']}.{ext}")
            try:
                urllib.request.urlretrieve(url, out)   # a different host; >= 7 days, collected now
            except Exception as e:
                log('DOWNLOAD FAILED', j['name'], url[:80], str(e)[:120])
                continue                                # the paid URL survives a failed download
            rec = {'name': j['name'], 'request_id': j.get('request_id'), 'submit': j, 'status': o,
                   'url': url, 'kind': kind, 'bytes': os.path.getsize(out),
                   'estimate_usd': j.get('estimate_usd'), 'billed': True,
                   'elapsed_s': round(time.time() - t0)}
            try:
                p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                    'stream=width,height,nb_frames,r_frame_rate', '-of', 'csv=p=0', out],
                                   capture_output=True, text=True)
                rec['dims'] = p.stdout.strip()
            except Exception:
                pass
            with open(os.path.join(root, 'receipts',
                                   f"hfapi-{j['name']}-{j.get('request_id')}.json"), 'w',
                      encoding='utf-8') as f:
                json.dump(rec, f, indent=1)
            done[j['name']] = rec
            est = j.get('estimate_usd')
            log('DONE', j['name'], rec['bytes'], 'B',
                f"est ${est:.4f}" if isinstance(est, (int, float)) else '', rec.get('dims', ''),
                url[:60])
        if len(done) < len(jobs):
            time.sleep(a.every)

    got = len([d for d in done.values() if 'url' in d])
    billed = sum(d.get('estimate_usd') or 0 for d in done.values() if d.get('billed'))
    bal = hf.balance()
    log('HFAPI-POLL-END', got, 'of', len(jobs),
        f'downloaded · est billed ${billed:.4f} · wallet ${bal["usd"]:.2f} / {bal["credits"]:.1f} cr '
        f'(LOCAL LEDGER — no balance endpoint exists)')


if __name__ == '__main__':
    main()
