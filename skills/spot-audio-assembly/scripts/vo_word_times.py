#!/usr/bin/env python3
"""vo_word_times.py — word times for the word-synced captions, per VO file, written to audio.word_times (default
<captions_dir>/word-times.json) as {LINE: [[word, start, end], …]} in seconds relative to the file.
  --engine local   faster-whisper on this machine (free); hyphen fragments are joined, punctuation dropped (apostrophes kept),
                   and a hyphenated compound is split into two words with proportional times (the caption rule; --keep-hyphens to keep it)
  --engine scribe  ElevenLabs Scribe (BILLED per minute of audio; ELEVENLABS_API_KEY in the environment; --dry-run lists
                   the files and minutes first — the GO comes before the run)
--only L1,L2 re-times just those lines and splices them into the existing file, so HAND PATCHES on the other lines survive
(a full re-run once re-added a spurious 40 ms "The" and undid three patched splits). A swapped file also moves a LIP-SYNCED
line: its at is re-measured against the take, never carried (video-edit-edl AUDIO-PLACEMENT.md § Lines inside a shot).
Default lines = those the EDL's
captions reference (all placed lines when there are no captions). Whisper mis-times onsets in noisy sections — the
placement check (qc_vo_placement.py) is the authority for where a line SITS; word times are for the cards. A line that
returns no words, or fewer than its captions reference, exits non-zero and nothing is written.

  vo_word_times.py --root <project> --edl edit/<SPOT>-EDL.json [--engine local|scribe] [--only L1,L2] [--model small] [--split-hyphens] [--dry-run]
"""
import argparse, json, os, re, subprocess, sys, urllib.request, uuid


def dur(f):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], capture_output=True, text=True).stdout or 0)


def local(path, model, split):
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device='cpu', compute_type='int8')
    segs, _ = m.transcribe(path, word_timestamps=True, language='en')
    raw = [[w.word.strip(), round(w.start, 3), round(w.end, 3)] for s in segs for w in (s.words or []) if w.word.strip()]
    out = []
    for w in raw:   # whisper emits "one-" + "night" as fragments: join, then split on the hyphen below
        if out and (out[-1][0].endswith('-') or w[0].startswith('-')): out[-1] = [out[-1][0].rstrip('-') + '-' + w[0].lstrip('-'), out[-1][1], w[2]]
        else: out.append(w)
    out = [[re.sub(r"[^\w'\-]", '', w), s, e] for w, s, e in out if re.sub(r"[^\w'\-]", '', w)]   # Scribe's shape: no punctuation, apostrophes kept
    if split:
        sp = []
        for w, s, e in out:
            parts = [p for p in w.split('-') if p]
            if len(parts) < 2: sp.append([w, s, e]); continue
            n = sum(len(p) for p in parts); t = s
            for p in parts: d = (e - s) * len(p) / n; sp.append([p, round(t, 3), round(t + d, 3)]); t += d
        out = sp
    return out


def scribe(path, model, key):
    b = uuid.uuid4().hex; data = open(path, 'rb').read()
    body = (f'--{b}\r\nContent-Disposition: form-data; name="model_id"\r\n\r\n{model}\r\n'
            f'--{b}\r\nContent-Disposition: form-data; name="timestamps_granularity"\r\n\r\nword\r\n'
            f'--{b}\r\nContent-Disposition: form-data; name="language_code"\r\n\r\neng\r\n'
            f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{os.path.basename(path)}"\r\nContent-Type: audio/mpeg\r\n\r\n').encode() + data + f'\r\n--{b}--\r\n'.encode()
    req = urllib.request.Request('https://api.elevenlabs.io/v1/speech-to-text', data=body, headers={'xi-api-key': key, 'Content-Type': f'multipart/form-data; boundary={b}'})
    with urllib.request.urlopen(req, timeout=120) as r: o = json.load(r)
    return [[w['text'], round(w['start'], 3), round(w['end'], 3)] for w in o.get('words', []) if w.get('type', 'word') == 'word' and w['text'].strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl', required=True); ap.add_argument('--engine', choices=['local', 'scribe'], default='local')
    ap.add_argument('--only', default=''); ap.add_argument('--model'); ap.add_argument('--keep-hyphens', action='store_true', help='keep "under-dicked" as one word (default: hyphenated compounds split into two words, the caption rule)'); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--out', help='default: audio.word_times or <captions_dir>/word-times.json')
    a = ap.parse_args(); os.chdir(a.root)
    edl = json.load(open(a.edl, encoding='utf-8')); au = edl['audio']; vo = au['vo']; capd = au.get('captions_dir', 'edit/captions')
    out = a.out or au.get('word_times', f'{capd}/word-times.json'); model = a.model or ('small' if a.engine == 'local' else 'scribe_v1')
    only = [x for x in a.only.split(',') if x]
    lines = only or sorted({c['line'] for c in au.get('captions', [])}) or sorted(k for k in vo if isinstance(vo[k], dict) and 'file' in vo[k])
    res = json.load(open(out, encoding='utf-8')) if only and os.path.exists(out) else {}
    mins = sum(dur(vo[L]['file']) for L in lines) / 60
    print(f"{a.engine} {model}: {len(lines)} line(s) {lines}, {mins:.2f} min of audio" + (' — BILLED per minute' if a.engine == 'scribe' else ' — free, local') + ('; kept as is: ' + ','.join(k for k in res if k not in lines) if only else ''))
    if a.dry_run: print('DRY RUN — nothing transcribed'); return
    key = os.environ.get('ELEVENLABS_API_KEY')
    if a.engine == 'scribe' and not key: sys.exit('no ELEVENLABS_API_KEY in the environment — source the env file that holds it first')
    for L in lines:
        f = vo[L]['file']; res[L] = local(f, model, not a.keep_hyphens) if a.engine == 'local' else scribe(f, model, key)
        print(L, f, '->', ' '.join(f'{w}@{s:.2f}' for w, s, e in res[L]))
        need = max((c['words'][1] for c in au.get('captions', []) if c['line'] == L), default=0)
        if not res[L] or len(res[L]) < need:   # an empty or short timing result is never written, never interpolated
            sys.exit(f"{L}: {a.engine} returned {len(res[L])} word(s) for {f}; the captions reference {need} — nothing written")
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True); json.dump(res, open(out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False); print('wrote', out)


if __name__ == '__main__':
    main()
