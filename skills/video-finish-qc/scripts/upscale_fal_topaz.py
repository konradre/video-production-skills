#!/usr/bin/env python3
"""upscale_fal_topaz.py — the HOSTED reconstructive upscale (fal `topaz/upscale/video/generative`, Starlight Precise 2.6 by
default) for the shots the per-shot tier sends there: faces under ~50 px in the take, text that must read — from the
ORIGINAL take, never stacked on a local upscale. Flow: fal storage upload (initiate → PUT) → queue submit → poll →
download → receipt JSON with the billable units (re-fetched after 20 s: the billing header arrives late).
🔴 Billed per second of OUTPUT. The pre-flight (clips, seconds, model, factor) prints and the script EXITS unless
--confirmed is passed — that flag is the echo of the operator's GO on the cost line, never a default.

  upscale_fal_topaz.py --root <project> --clips S05-A,S05-B1 [--factor 4] [--model 'Starlight Precise 2.6'] [--in-dir edit/upscale-in]
                       [--out-dir edit/upscale-out] [--receipts receipts] [--confirmed] [--resume]
FAL_KEY in the environment (source the env file that holds it first; the key never appears on a command line).
--resume re-attaches to request ids recorded in <receipts>/fal-requests.log for the named clips (never resubmits).
"""
import argparse, json, os, subprocess, sys, time, urllib.error, urllib.request

ENDPOINT = 'topaz/upscale/video/generative'; BASE = 'topaz/upscale'; QUEUE = 'https://queue.fal.run'   # status/result/billing live under BASE (the full path → 405)


def log(*x): print(time.strftime('%H:%M:%S'), *x, flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--clips', required=True); ap.add_argument('--factor', type=float, default=4.0); ap.add_argument('--model', default='Starlight Precise 2.6')
    ap.add_argument('--in-dir', default='edit/upscale-in'); ap.add_argument('--out-dir', default='edit/upscale-out'); ap.add_argument('--receipts', default='receipts')
    ap.add_argument('--confirmed', action='store_true'); ap.add_argument('--resume', action='store_true'); ap.add_argument('--timeout-min', type=float, default=45)
    a = ap.parse_args(); os.chdir(a.root); clips = [c for c in a.clips.split(',') if c]; os.makedirs(a.out_dir, exist_ok=True); os.makedirs(a.receipts, exist_ok=True)
    secs = {}
    for c in clips:
        p = f'{a.in_dir}/{c}.mp4'; assert os.path.exists(p), f'missing {p}'
        secs[c] = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], capture_output=True, text=True).stdout or 0)
    print(f"PRE-FLIGHT {a.model} x{a.factor}: " + ', '.join(f'{c} {secs[c]:.2f} s' for c in clips) + f" — {sum(secs.values()):.2f} s of input, billed per second of output at the venue's rate for this factor")
    if not a.confirmed and not a.resume: print('not confirmed — pass --confirmed after the operator\'s GO on the cost line'); sys.exit(2)
    key = os.environ.get('FAL_KEY')
    if not key: sys.exit('no FAL_KEY in the environment — source the env file that holds it (set -a; . <file>; set +a) and re-run')
    H = {'Authorization': f'Key {key}'}

    def req(url, data=None, headers=None, method=None, raw=False, timeout=120, retries=40):
        h = dict(H); h.update(headers or {})
        for attempt in range(retries):
            r = urllib.request.Request(url, data=data, headers=h, method=method)
            try:
                with urllib.request.urlopen(r, timeout=timeout) as resp:
                    b = resp.read(); return (b if raw else json.loads(b or b'{}')), dict(resp.headers)
            except urllib.error.HTTPError as e:
                if e.code >= 500 and attempt < retries - 1: log('retry', e.code, url[-60:]); time.sleep(min(60, 8 * (attempt + 1))); continue
                raise
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < retries - 1: log('retry', type(e).__name__, url[-60:]); time.sleep(min(60, 8 * (attempt + 1))); continue
                raise

    reqlog = f'{a.receipts}/fal-requests.log'; jobs = {}
    if a.resume:
        for line in open(reqlog) if os.path.exists(reqlog) else []:
            f = line.rstrip('\n').split('\t')
            if len(f) >= 5 and f[1] == ENDPOINT and f[2] in clips: jobs[f[2]] = {'request_id': f[3], 'body': {'model': a.model, 'upscale_factor': a.factor, 'video_url': '(see the submit log)'}, 'submitted': time.time()}
        log('RESUME on', {c: j['request_id'] for c, j in jobs.items()}); assert jobs, 'nothing to resume for these clips'
    else:
        for c in clips:   # 1. upload  2. submit — one request per clip, recorded BEFORE polling so a crash never resubmits
            p = f'{a.in_dir}/{c}.mp4'; ct = 'video/mp4'
            init, _ = req('https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3', data=json.dumps({'content_type': ct, 'file_name': f'{c}.mp4'}).encode(), headers={'Content-Type': 'application/json'}, method='POST')
            data = open(p, 'rb').read(); r = urllib.request.Request(init['upload_url'], data=data, headers={'Content-Type': ct}, method='PUT')
            with urllib.request.urlopen(r, timeout=600) as resp: resp.read()
            log('uploaded', c, len(data), 'B'); body = {'video_url': init['file_url'], 'model': a.model, 'upscale_factor': a.factor}
            sub, _ = req(f'{QUEUE}/{ENDPOINT}', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'}, method='POST')
            jobs[c] = {'request_id': sub['request_id'], 'body': body, 'submitted': time.time()}; log('submitted', c, sub['request_id'])
            open(reqlog, 'a').write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{ENDPOINT}\t{c}\t{sub['request_id']}\t{a.model} x{a.factor}\n")
    t0 = time.time(); done = {}   # 3. poll — COMPLETED is not success until the file is on disk and probed
    while len(done) < len(jobs) and time.time() - t0 < a.timeout_min * 60:
        for c, j in jobs.items():
            if c in done: continue
            try: st, _ = req(f"{QUEUE}/{BASE}/requests/{j['request_id']}/status?logs=0")
            except urllib.error.HTTPError as e: log('status err', c, e.code); continue
            s = st.get('status')
            if s == 'COMPLETED':
                res, hdr = req(f"{QUEUE}/{BASE}/requests/{j['request_id']}"); out = f'{a.out_dir}/{c}.mp4'
                b, _ = req(res['video']['url'], raw=True, timeout=900); open(out, 'wb').write(b)
                dims = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,nb_frames', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout.strip()
                units = hdr.get('X-Fal-Billable-Units') or hdr.get('x-fal-billable-units')
                rec = {'clip': c, 'request_id': j['request_id'], 'endpoint': ENDPOINT, 'input': j['body'], 'response': res, 'billable_units_first_fetch': units, 'bytes': len(b), 'probe': dims, 'elapsed_s': round(time.time() - j['submitted'], 1)}
                json.dump(rec, open(f"{a.receipts}/fal-upscale-{c}-{j['request_id']}.json", 'w'), indent=1); done[c] = rec; log('DONE', c, len(b), 'B', dims, 'units', units, 'in', rec['elapsed_s'], 's')
            elif s in ('FAILED', 'CANCELLED'): log('FAILED', c, json.dumps(st)[:300]); done[c] = {'clip': c, 'failed': st}
            else: log('…', c, s, st.get('queue_position'))
        if len(done) < len(jobs): time.sleep(15)
    time.sleep(20)   # 4. billing re-fetch — the header is late
    for c, rec in done.items():
        if 'request_id' not in rec: continue
        try:
            _, hdr = req(f"{QUEUE}/{BASE}/requests/{rec['request_id']}"); rec['billable_units_refetch'] = hdr.get('X-Fal-Billable-Units') or hdr.get('x-fal-billable-units')
            json.dump(rec, open(f"{a.receipts}/fal-upscale-{c}-{rec['request_id']}.json", 'w'), indent=1); log('billing', c, 'units', rec['billable_units_refetch'])
        except Exception as e: log('billing refetch err', c, e)
    log('UPSCALE-FAL-END', 'completed', len([1 for r in done.values() if 'request_id' in r]), 'of', len(jobs))


if __name__ == '__main__':
    main()
