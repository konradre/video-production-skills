#!/usr/bin/env python3
"""speech_timing.py — the DELIVERY read of a talking take: did it rush, where did it hold, how fast did it
speak, and did it stutter. The matrix's `audio` row asks whether the words are the scripted words; this asks
whether the PERFORMANCE is usable, which is the other half and the one an agent cannot hear.

  speech_timing.py <take.mp4|audio.wav> [--duration D] [--gap 0.25] [--wpm 230,250] [--model base]
                   [--words <json>] [--json <out>] [--selftest]

Four numbers, each with the rule that reads it:

  SPAN     first word start -> last word end, against the take's own duration. A take that ends more than
           ~0.3 s early RUSHED: the model was given more seconds than the script fills, and the delivery
           goes flat or the last beat is thrown away. Head silence over ~0.3 s is the same defect at the
           other end and is cheap to trim; tail silence is not, because the performance already changed.
  GAPS     every silence >= --gap between consecutive words, with its time. Zero or one at a natural breath
           is good. A 0.7 s hold mid-line is a hold the operator will hear on the first play, and on a
           generated take it usually traces to a full stop in the prompt's script — the model reads a
           period as permission to stop.
  WPM      words / speech span, NOT words / duration: trailing silence would flatter the number. The band
           is a GENRE fact, never a universal — 230-250 is the creator/UGC band, and a 30 s brand read
           sits far below it. Pass the band the genre calls for.
  STUTTER  an adjacent repeated word, or a repeated bigram inside a short window ("job infinitely and make
           infinitely"). Generated speech produces these without any audio artefact, so they survive an
           intelligibility check and only a transcript read catches them. CANDIDATES, not a verdict: a
           scripted repetition is legitimate and only the script says which this is.

Words come from faster-whisper (the house instrument, local, free) unless --words supplies a JSON already
paid for: a list of [word, start, end], or {"words": [...]}, or faster-whisper's own dicts. A re-review of
the same take reuses the file rather than transcribing twice.

--selftest runs the analysis over a constructed word list whose answers are known, per the skill's rule that
every instrument prints a known-answer self-test beside its number.
"""
import argparse, json, os, re, subprocess, sys


def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def norm(w):
    return re.sub(r"[^\w']", '', str(w)).lower()


def load_words(path):
    d = json.load(open(path, encoding='utf-8'))
    if isinstance(d, dict):
        d = d.get('words') or d.get('segments') or []
    out = []
    for w in d:
        if isinstance(w, (list, tuple)) and len(w) >= 3:
            out.append((str(w[0]), float(w[1]), float(w[2])))
        elif isinstance(w, dict) and 'start' in w and 'end' in w:
            out.append((str(w.get('word') or w.get('text') or ''), float(w['start']), float(w['end'])))
    return out


def transcribe(path, model):
    from faster_whisper import WhisperModel                     # the house instrument: local, free
    mdl = WhisperModel(model, device='cpu', compute_type='int8')
    segs, _ = mdl.transcribe(path, word_timestamps=True)
    out = []
    for sg in segs:
        for w in (sg.words or []):
            out.append((w.word.strip(), float(w.start), float(w.end)))
    return out


def analyse(words, dur, gap, band):
    """Pure: words -> the four reads. Self-tested below; nothing here touches the filesystem."""
    r = {'n_words': len(words), 'duration_s': dur}
    if not words:
        r['verdict'] = ['NO WORDS — the take carries no transcribable speech, or whisper failed']
        return r
    t0, t1 = words[0][1], words[-1][2]
    span = t1 - t0
    r.update(span_s=round(span, 3), first_word_s=round(t0, 3), last_word_s=round(t1, 3))
    if dur:
        r.update(head_silence_s=round(t0, 3), tail_silence_s=round(dur - t1, 3))
    r['gaps'] = [{'after': words[i][0], 'at_s': round(words[i][2], 3), 'gap_s': round(words[i + 1][1] - words[i][2], 3)}
                 for i in range(len(words) - 1) if words[i + 1][1] - words[i][2] >= gap]
    r['wpm'] = round(len(words) / span * 60, 1) if span > 0 else None
    # stutters: an adjacent repeat, then a bigram repeated inside an 8-word window
    n = [norm(w[0]) for w in words]
    st = [{'kind': 'adjacent', 'at_s': round(words[i][1], 3), 'text': f'{words[i][0]} {words[i+1][0]}'}
          for i in range(len(n) - 1) if n[i] and n[i] == n[i + 1]]
    for i in range(len(n) - 1):
        for j in range(i + 2, min(i + 9, len(n) - 1)):
            if n[i] and n[i] == n[j] and n[i + 1] == n[j + 1]:
                st.append({'kind': 'repeated bigram', 'at_s': round(words[j][1], 3),
                           'text': ' '.join(w[0] for w in words[i:j + 2])})
                break
    r['stutters'] = st
    v = []
    lo, hi = band
    if dur and dur - t1 > 0.3:
        v.append(f'RUSHED — {dur - t1:.2f} s of the take is silent after the last word (> 0.30 s)')
    if dur and t0 > 0.3:
        v.append(f'LATE START — {t0:.2f} s of head silence (> 0.30 s); trim it or re-roll')
    for g in r['gaps']:
        v.append(f"HOLD — {g['gap_s']:.2f} s after \"{g['after']}\" at {g['at_s']:.2f} s")
    if r['wpm'] is not None and not (lo <= r['wpm'] <= hi):
        v.append(f"PACE — {r['wpm']:.0f} wpm is outside the {lo:g}-{hi:g} band asked for")
    for s in st:
        v.append(f"STUTTER CANDIDATE ({s['kind']}) at {s['at_s']:.2f} s: \"{s['text']}\"")
    r['verdict'] = v or ['clean — span, gaps, pace and repeats all inside the rules given']
    return r


def selftest():
    mk = lambda ws: [(w, s, e) for w, s, e in ws]
    cases = []
    clean = mk([('one', 0.10, 0.30), ('two', 0.32, 0.55), ('three', 0.57, 0.90)])
    r = analyse(clean, 1.0, 0.25, (150, 250))
    cases.append(('a clean 3-word run reports no gap and no stutter', not r['gaps'] and not r['stutters']))
    cases.append(('span is first start to last end', abs(r['span_s'] - 0.80) < 1e-6))
    cases.append(('wpm is words over the SPAN, not the duration', abs(r['wpm'] - 225.0) < 0.1))
    held = mk([('one', 0.10, 0.30), ('two', 1.10, 1.30)])
    r = analyse(held, 1.4, 0.25, (150, 250))
    cases.append(('a 0.80 s silence is reported as one gap', len(r['gaps']) == 1 and abs(r['gaps'][0]['gap_s'] - 0.80) < 1e-6))
    r = analyse(clean, 2.0, 0.25, (150, 250))
    cases.append(('1.10 s of tail silence reads as RUSHED', any('RUSHED' in v for v in r['verdict'])))
    r = analyse(mk([('and', 0.1, 0.2), ('and', 0.2, 0.3), ('go', 0.3, 0.4)]), 0.5, 0.25, (0, 1e9))
    cases.append(('an adjacent repeat is a stutter candidate', any(s['kind'] == 'adjacent' for s in r['stutters'])))
    ws = [('job', 0.1, 0.2), ('infinitely', 0.2, 0.4), ('and', 0.4, 0.5), ('make', 0.5, 0.6),
          ('job', 0.6, 0.7), ('infinitely', 0.7, 0.9)]
    r = analyse(mk(ws), 1.0, 0.25, (0, 1e9))
    cases.append(('a repeated bigram inside the window is a stutter candidate',
                  any(s['kind'] == 'repeated bigram' for s in r['stutters'])))
    r = analyse(clean, 1.0, 0.25, (240, 260))
    cases.append(('a wpm outside the band asked for is reported', any('PACE' in v for v in r['verdict'])))
    r = analyse([], 1.0, 0.25, (150, 250))
    cases.append(('no words fails closed rather than dividing by zero', 'NO WORDS' in r['verdict'][0]))
    for name, ok in cases:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in cases)
    print(f'speech_timing selftest {"PASS" if ok else "FAIL"}')
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('take', nargs='?')
    ap.add_argument('--duration', type=float, help='override the probed duration (seconds)')
    ap.add_argument('--gap', type=float, default=0.25, help='report a silence at or over this (default 0.25 s)')
    ap.add_argument('--wpm', default='230,250', help='the genre band, lo,hi (default 230,250 = creator/UGC)')
    ap.add_argument('--model', default='base', help='faster-whisper model (default base)')
    ap.add_argument('--words', help='a word-times JSON already paid for; skips transcription')
    ap.add_argument('--json', help='write the reads here')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.take:
        ap.error('give a take (or --selftest)')
    if not os.path.exists(a.take):
        sys.exit(f'speech_timing: no file at {a.take}')
    band = tuple(float(x) for x in a.wpm.split(','))
    words = load_words(a.words) if a.words else transcribe(a.take, a.model)
    dur = a.duration if a.duration is not None else duration(a.take)
    r = analyse(words, dur, a.gap, band)
    r['instrument'] = f'faster-whisper {a.model} int8' if not a.words else f'words from {a.words}'
    r['rule'] = f'gap >= {a.gap} s; wpm band {band[0]:g}-{band[1]:g}; rushed > 0.30 s of tail silence'
    print(f"{os.path.basename(a.take)}  {r['n_words']} words, span {r.get('span_s')} s of {dur} s, "
          f"{r.get('wpm')} wpm, {len(r.get('gaps', []))} gaps >= {a.gap} s, {len(r.get('stutters', []))} stutter candidates")
    for v in r['verdict']:
        print('  ' + v)
    print('  ---- known-answer self-test ----')
    selftest()
    if a.json:
        json.dump(r, open(a.json, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print('wrote', a.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
