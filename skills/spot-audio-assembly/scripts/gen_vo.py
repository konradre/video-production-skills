#!/usr/bin/env python3
"""gen_vo.py — VO takes from ElevenLabs by raw REST: the campaign narrator, a cloned character voice (a dub), or a
shared-library voice for an off-screen line (added to the account first — free). One MP3 per job; an existing output is
SKIPPED (a take is billed per call — never regenerate a landed one by accident); the plan's character count is read
before and after (free) so the billed delta is on the record. --dry-run prints the characters each job would spend and
touches nothing: the operator's GO comes between the dry run and the run, and this script never asks for it.

  gen_vo.py --root <project> --jobs audio/vo/jobs-<SPOT>-<line>.json [--voice <voice_id>] [--dry-run]
            [--preview audio/vo/PREVIEW-<name>.mp3] [--door] [--out-dir audio/vo]

jobs = [{name, text, voice_id?, owner_id?, label?, prev?, next?, stability?, similarity?, style?, seed?, model?}, …]
  voice_id   overrides --voice for that job; with owner_id it is a shared-library voice, added to the account if missing
  prev/next  previous_text / next_text — English context that steers prosody and language WITHOUT being spoken
             (multilingual v2 reads slang as another language without it)
  seed       pins a take across regens; voice id + model + settings decide identity — never mix models on one voice
--door     writes <name>-door.mp3 beside each take: band-limited + a short boxy room (an O.S. line behind a closed door)
--preview  the run's takes concatenated with 0.7 s gaps + an index (ordinal, start, file) — picks are by ordinal from a NAMED reel
Key: ELEVENLABS_API_KEY in the environment (source the env file that holds it first; the key never appears on a command line).
"""
import argparse, json, os, subprocess, sys, time, urllib.error, urllib.request

API = 'https://api.elevenlabs.io/v1'
DOOR = 'highpass=f=110,lowpass=f=1400,lowpass=f=1800,aecho=0.75:0.45:16|31:0.24|0.11,volume=1.25'


def dur(f):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], capture_output=True, text=True).stdout.strip() or 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--jobs', required=True); ap.add_argument('--voice', help='default voice id for jobs without voice_id')
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--preview'); ap.add_argument('--door', action='store_true'); ap.add_argument('--out-dir', default='audio/vo')
    a = ap.parse_args(); os.chdir(a.root); jobs = json.load(open(a.jobs, encoding='utf-8')); os.makedirs(a.out_dir, exist_ok=True)
    key = os.environ.get('ELEVENLABS_API_KEY'); H = {'xi-api-key': key or '', 'Content-Type': 'application/json'}

    def get(url): return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30))

    def used():
        o = get(f'{API}/user/subscription'); return o['character_count'], o['character_limit'], o.get('tier', '?')

    todo = [j for j in jobs if not os.path.exists(os.path.join(a.out_dir, j['name'] + '.mp3'))]
    for j in jobs: print(f"{'SKIP (exists)' if j not in todo else 'RENDER'} {j['name']:28} {len(j['text']):4d} chars  voice {j.get('voice_id') or a.voice or '?'}  {j['text'][:60]!r}")
    print(f"characters to bill this run: {sum(len(j['text']) for j in todo)} over {len(todo)} take(s)")
    if a.dry_run: print('DRY RUN — nothing sent'); return
    if not key: sys.exit('no ELEVENLABS_API_KEY in the environment — source the env file that holds it (set -a; . <file>; set +a) and re-run')
    if not todo: print('nothing to render'); return
    c0, lim, tier = used(); print(f'plan {tier}: {c0}/{lim} characters used before')
    mine = None; out = []
    for j in todo:
        vid = j.get('voice_id') or a.voice; assert vid, f"{j['name']}: no voice id (job voice_id or --voice)"
        if j.get('owner_id'):
            mine = mine if mine is not None else {v['voice_id'] for v in get(f'{API}/voices')['voices']}
            if vid not in mine:
                req = urllib.request.Request(f"{API}/voices/add/{j['owner_id']}/{vid}", data=json.dumps({'new_name': j.get('label', j['name'])}).encode(), headers=H, method='POST')
                try: print('added shared voice', j.get('label'), json.load(urllib.request.urlopen(req, timeout=30)).get('voice_id')); mine.add(vid)
                except urllib.error.HTTPError as ex: print('ADD FAILED', j.get('label'), ex.code, ex.read()[:200]); continue
        fn = os.path.join(a.out_dir, j['name'] + '.mp3')
        body = {'text': j['text'], 'model_id': j.get('model', 'eleven_multilingual_v2'),
                'voice_settings': {'stability': j.get('stability', 0.5), 'similarity_boost': j.get('similarity', 0.75), 'style': j.get('style', 0.0), 'use_speaker_boost': True}}
        if j.get('seed') is not None: body['seed'] = int(j['seed'])
        if j.get('prev'): body['previous_text'] = j['prev']
        if j.get('next'): body['next_text'] = j['next']
        req = urllib.request.Request(f'{API}/text-to-speech/{vid}?output_format=mp3_44100_128', data=json.dumps(body).encode(), headers={**H, 'Accept': 'audio/mpeg'})
        data = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=90) as r: data = r.read()
                break
            except urllib.error.HTTPError as ex:
                print('HTTP', ex.code, fn, ex.read()[:300])
                if ex.code in (429, 500, 502, 503) and attempt < 2: time.sleep(3 * (attempt + 1)); continue
                break
        if not data: continue
        open(fn, 'wb').write(data); out.append(fn)
        print(f"ok {fn}  {dur(fn):.2f} s  stab={j.get('stability', 0.5)} style={j.get('style', 0.0)} seed={j.get('seed')}")
        if a.door:
            door = fn[:-4] + '-door.mp3'; subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', fn, '-af', DOOR, '-c:a', 'libmp3lame', '-b:a', '128k', door], check=True); out.append(door); print('   door', door)
    c1, _, _ = used(); print(f'plan: {c1}/{lim} used after  (billed this run: {c1 - c0} characters)')
    if a.preview and out:
        gap = os.path.join(a.out_dir, '_gap.mp3'); lst = os.path.join(a.out_dir, '_preview.txt')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', '0.7', '-c:a', 'libmp3lame', '-b:a', '128k', gap], check=True)
        with open(lst, 'w') as f:
            for fn in out: f.write(f"file '{os.path.abspath(fn)}'\nfile '{os.path.abspath(gap)}'\n")
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-af', 'aformat=channel_layouts=mono', '-c:a', 'libmp3lame', '-b:a', '128k', a.preview], check=True)
        idx = a.preview.rsplit('.', 1)[0] + '-index.txt'; t = 0.0
        with open(idx, 'w') as f:
            for i, fn in enumerate(out, 1): f.write(f"{i:02d} {t:6.2f}s  {fn}\n"); t += dur(fn) + 0.7
        print('preview', a.preview, 'index', idx)


if __name__ == '__main__':
    main()
