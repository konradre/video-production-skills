#!/usr/bin/env python3
"""hf_poll.py — poll Higgsfield jobs listed in a jobs file ([{name, job_id, ...}]), download results to
takes/<name>.mp4, write receipts/hf-<name>-<job_id>.json (job, url, bytes, elapsed). Every log line starts with
a timestamp: match " DONE | FAILED|HF-POLL-END" anywhere in the line, never ^DONE. Refusals (nsfw, ip_detected)
log as FAILED with the status — they are free; a billed job is never resubmitted (re-fetch by id instead).
Detach: python3 ~/.claude/skills/video-production/scripts/detach.py --log <abs>/takes/hf-poll-<key>.log -- python3 <abs>/hf_poll.py --root <abs> <abs>/receipts/hf-jobs-<key>.json

  hf_poll.py [--root <project>] [--timeout-min 60] [--every 20] <jobs.json>
"""
import argparse, json, os, sys, time, subprocess, urllib.request


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def urls_in(o, acc):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and v.startswith('http') and ('.mp4' in v or 'video' in k.lower() or 'result' in k.lower()):
                acc.append(v)
            else:
                urls_in(v, acc)
    elif isinstance(o, list):
        for v in o:
            urls_in(v, acc)
    return acc


def status_of(o):
    if isinstance(o, list) and o: o = o[0]
    return (o.get('status') or o.get('state') or '').lower() if isinstance(o, dict) else ''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('jobs')
    ap.add_argument('--root', default='.')
    ap.add_argument('--timeout-min', type=int, default=60)
    ap.add_argument('--every', type=int, default=20, help='seconds between polls')
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    os.makedirs(os.path.join(root, 'takes'), exist_ok=True); os.makedirs(os.path.join(root, 'receipts'), exist_ok=True)
    jobs = json.load(open(a.jobs)); done = {}; t0 = time.time()
    log('HF-POLL-START', [j['name'] for j in jobs])
    while len(done) < len(jobs) and time.time() - t0 < 60 * a.timeout_min:
        for j in jobs:
            if j['name'] in done: continue
            r = subprocess.run(['higgsfield', 'generate', 'get', j['job_id'], '--json'], capture_output=True, text=True)
            try:
                o = json.loads(r.stdout)
            except Exception:
                log('get failed', j['name'], r.stdout[:200], r.stderr[:200]); continue
            st = status_of(o)
            if st in ('completed', 'complete', 'succeeded', 'success'):
                top = o[0] if isinstance(o, list) and o else o
                ru = top.get('result_url') if isinstance(top, dict) else None   # prefer result_url — the input url was grabbed once
                us = [ru] if ru else urls_in(o, [])
                mp4 = [u for u in us if '.mp4' in u] or us
                if not mp4:
                    log('completed but no url', j['name'], json.dumps(o)[:400]); done[j['name']] = {'job': o, 'error': 'no url'}; continue
                out = os.path.join(root, 'takes', f"{j['name']}.mp4")
                try:
                    urllib.request.urlretrieve(mp4[0], out)
                except Exception as e:                       # the paid URL survives a failed download
                    log('DOWNLOAD FAILED', j['name'], mp4[0][:80], str(e)[:120]); continue
                rec = {'name': j['name'], 'job_id': j['job_id'], 'submit': j, 'job': o, 'url': mp4[0],
                       'bytes': os.path.getsize(out), 'elapsed_s': round(time.time() - t0)}
                try:
                    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,nb_frames,r_frame_rate',
                                        '-of', 'csv=p=0', out], capture_output=True, text=True)
                    rec['dims'] = p.stdout.strip()
                except Exception:
                    pass
                json.dump(rec, open(os.path.join(root, 'receipts', f"hf-{j['name']}-{j['job_id']}.json"), 'w'), indent=1)
                done[j['name']] = rec; log('DONE', j['name'], rec['bytes'], 'B', mp4[0][:80])
            elif st in ('failed', 'cancelled', 'canceled', 'error', 'nsfw', 'ip_detected'):
                log('FAILED', j['name'], st, json.dumps(o)[:300]); done[j['name']] = {'job': o, 'error': st}
            else:
                log('…', j['name'], st or json.dumps(o)[:120])
        if len(done) < len(jobs): time.sleep(a.every)
    log('HF-POLL-END', len([d for d in done.values() if 'url' in d]), 'of', len(jobs), 'downloaded')


if __name__ == '__main__':
    main()
