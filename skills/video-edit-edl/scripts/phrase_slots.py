#!/usr/bin/env python3
"""phrase_slots.py - picture SLOTS for a voiced section, measured from the programme audio before any footage is assigned.

When a line is carried by cutaways (supplied footage, b-roll, stills), its picture is cut to the PHRASES of the voice: each
slot runs from just before one phrase's first word to just before the next one's, so a mention stays on its picture. Three
steps, each of which can be run alone:

  1  words     transcribe the WHOLE voice file with two model sizes and print where they disagree (a short excerpt
               transcribed alone loses that agreement). Free, local (faster-whisper).
  2  timeline  when the words were measured on the dry voice but the picture is cut to the MIX, prove the two share one
               timeline: envelope correlation, lag and score. A lag that is not 0 is added to every onset, never ignored.
  3  slots     phrases (in order, as written in the script) -> onset of each phrase's first word -> the cut, `--lead`
               frames before it (default 2: the cut lands 1.5-2.5 frames ahead of the word) -> slots in whole frames.

A slot shorter than --min-frames is flagged, not fixed: merge it into a neighbour (one continuous shot beats two cuts of one
subject) or keep it on purpose. Onsets where the two models differ by more than 0.10 s are flagged for an envelope check.

  phrase_slots.py words --audio <voice.wav> --out <words.json> [--models small.en,medium.en]
  phrase_slots.py timeline --mix <mix.wav> --dry <voice.wav>
  phrase_slots.py slots --words <words.json> --phrases "First phrase.|Second phrase|..." --fps 24 --out <slots.json>
                        [--lead 2] [--next-onset <s> | --end <s>] [--lag <s>] [--min-frames 30] [--prefix S] [--onset S1=4.94 ...]
  phrase_slots.py --selftest
"""
import argparse, json, os, re, sys


def norm(w):
    return re.sub(r"[^a-z0-9']+", "", w.lower().replace("’", "'"))


def cut_frame(onset_s, fps, lead):
    return int(round(onset_s * fps - lead))


def find_phrases(words, phrases):
    """words: [{'w','t0','t1'}] in order. Each phrase is matched token-wise from where the previous one ended."""
    toks = [norm(w["w"]) for w in words]; at = 0; found = []
    for ph in phrases:
        pt = [t for t in (norm(x) for x in ph.split()) if t]
        hit = next((i for i in range(at, len(toks) - len(pt) + 1) if toks[i:i + len(pt)] == pt), None)
        if hit is None:
            raise SystemExit(f"phrase not found in the transcript, in order, after word {at}: {ph!r}\n  transcript there: {' '.join(toks[at:at + 14])}")
        found.append((hit, hit + len(pt) - 1)); at = hit + len(pt)
    return found


def build_slots(models, phrases, fps, lead, next_onset, end, lag, min_frames, prefix, overrides=None):
    names = list(models); base = models[names[0]]; spans = find_phrases(base, phrases); slots = []
    for k, (ph, (i0, i1)) in enumerate(zip(phrases, spans)):
        ons = []
        for nm in names:
            try:
                j0, _ = find_phrases(models[nm], phrases)[k]; ons.append(models[nm][j0]["t0"])
            except SystemExit:
                pass
        onset = min(ons) + lag; spread = max(ons) - min(ons) if len(ons) > 1 else 0.0; sid = f"{prefix}{k + 1}"
        flags = [f"models differ {spread:.2f} s on this onset - check the envelope"] if spread > 0.10 else []
        if overrides and sid in overrides:
            onset = overrides[sid]; flags = [f"onset set by hand to {onset:.3f} s (an envelope read)"]
        slots.append({"id": sid, "phrase": ph, "onset_s": round(onset, 3), "phrase_end_s": round(base[i1]["t1"] + lag, 3), "cut_f": cut_frame(onset, fps, lead), "flags": flags})
    last = cut_frame(next_onset + lag, fps, lead) if next_onset is not None else int(round((end if end is not None else slots[-1]["phrase_end_s"]) * fps))
    for k, s in enumerate(slots):
        b = slots[k + 1]["cut_f"] if k + 1 < len(slots) else last
        s["tl_f"] = [s["cut_f"], b]; s["dur_f"] = b - s["cut_f"]; s["tl_s"] = [round(s["cut_f"] / fps, 6), round(b / fps, 6)]
        s["lead_frames"] = round(s["onset_s"] * fps - s["cut_f"], 2)
        if s["dur_f"] < min_frames:
            s["flags"].append(f"short ({s['dur_f']} f): merge into a neighbour or keep on purpose")
        if s["dur_f"] <= 0:
            raise SystemExit(f"slot {s['id']} has no length - phrases out of order, or --next-onset/--end too early")
    return slots


def envelope(path):
    import numpy as np, soundfile as sf
    from scipy.signal import butter, sosfiltfilt
    x, sr = sf.read(path, always_2d=True); x = x.mean(1)
    y = sosfiltfilt(butter(4, [300, 4000], btype="band", fs=sr, output="sos"), x); h = int(sr * 0.010); n = len(y) // h
    return np.sqrt((y[:n * h].reshape(n, h) ** 2).mean(1))


def best_lag(a, b, maxlag=200):
    """How many 10 ms bins `a` runs LATE against `b` (positive = a is delayed), and the normalised score there."""
    import numpy as np
    a = (a - a.mean()) / (a.std() or 1); b = (b - b.mean()) / (b.std() or 1); best = (-9.0, 0)
    for L in range(-maxlag, maxlag + 1):
        x, y = (a[L:], b[:len(a) - L]) if L >= 0 else (a[:L], b[-L:])
        n = min(len(x), len(y))
        if n < 50:
            continue
        c = float((x[:n] * y[:n]).mean())
        if c > best[0]:
            best = (c, L)
    return best[1], best[0]


def transcribe(audio, model_names):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("faster-whisper is not installed (pip install faster-whisper); it is the free local engine this step uses")
    out = {}
    for name in model_names:
        m = WhisperModel(name, device="cpu", compute_type="int8")
        segs, _ = m.transcribe(audio, word_timestamps=True, beam_size=5, condition_on_previous_text=False)
        out[name] = [{"w": w.word.strip(), "t0": round(w.start, 3), "t1": round(w.end, 3), "p": round(w.probability, 3)} for s in segs for w in s.words]
        print(f"{name}: {len(out[name])} words: {' '.join(w['w'] for w in out[name])}", flush=True)
    return out


def selftest():
    import numpy as np
    # neutral words on purpose: a self-test never carries anyone's script. Only the TIMES decide the known answers.
    words = [{"w": w, "t0": t, "t1": t + 0.2} for w, t in (("First", 4.94), ("phrase,", 5.22), ("here", 5.7), ("Second", 7.80), ("phrase", 8.2), ("runs", 8.3), ("longer", 8.5), ("third", 11.98), ("phrase.", 14.2))]
    late = [dict(w, t0=w["t0"] + (0.16 if w["w"] == "First" else 0.02)) for w in words]
    s = build_slots({"a": words, "b": late}, ["First phrase, here", "Second phrase runs longer", "third phrase"], 24, 2, 15.46, None, 0.0, 30, "S")
    got = [x["tl_f"] for x in s]; want = [[117, 185], [185, 286], [286, 369]]
    flagged = any("models differ" in f for f in s[0]["flags"]) and not s[1]["flags"]
    rng = np.random.default_rng(3); e = np.abs(rng.standard_normal(3000)); lag, score = best_lag(np.concatenate([np.zeros(30), e]), e)
    ok = got == want and flagged and lag == 30 and score > 0.9
    print(f"SELFTEST slots {got} (want {want}) | a 0.16 s model disagreement is flagged: {flagged} | a planted 30-bin delay reads {lag} bins, score {score:.2f} -> {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("words"); w.add_argument("--audio", required=True); w.add_argument("--out", required=True); w.add_argument("--models", default="small.en,medium.en")
    t = sub.add_parser("timeline"); t.add_argument("--mix", required=True); t.add_argument("--dry", required=True)
    s = sub.add_parser("slots"); s.add_argument("--words", required=True); s.add_argument("--phrases"); s.add_argument("--phrases-file"); s.add_argument("--fps", type=float, required=True); s.add_argument("--out", required=True)
    s.add_argument("--lead", type=float, default=2.0); s.add_argument("--next-onset", type=float); s.add_argument("--end", type=float); s.add_argument("--lag", type=float, default=0.0)
    s.add_argument("--min-frames", type=int, default=30); s.add_argument("--prefix", default="S")
    s.add_argument("--onset", action="append", default=[], metavar="ID=SECONDS", help="an onset read off the level envelope, where the models disagree (repeatable)")
    a = ap.parse_args()
    if not selftest():
        sys.exit(1)
    if a.cmd == "words":
        if os.path.exists(a.out):
            sys.exit(f"refusing to overwrite {a.out}")
        models = transcribe(a.audio, a.models.split(",")); names = list(models)
        if len(names) > 1 and len(models[names[0]]) == len(models[names[1]]):
            d = sorted(abs(x["t0"] - y["t0"]) for x, y in zip(models[names[0]], models[names[1]]))
            print(f"onset agreement: median {d[len(d) // 2]:.3f} s, max {d[-1]:.3f} s over {len(d)} words")
        elif len(names) > 1:
            print("the two models heard a different NUMBER of words - read both transcripts against the script before using either")
        json.dump({"source": a.audio, "engine": "faster-whisper int8 cpu; the whole file transcribed, windowed afterwards", "models": models}, open(a.out, "w"), indent=1); print("wrote", a.out)
    elif a.cmd == "timeline":
        lag, score = best_lag(envelope(a.mix), envelope(a.dry))
        print(f"the mix runs {lag * 10:+d} ms against the dry voice, envelope score {score:.3f} -> " + ("ONE timeline: the dry word times apply to the mix" if lag == 0 and score > 0.9 else f"pass --lag {lag / 100:.2f} to `slots`" if score > 0.9 else "NOT the same voice timeline - do not carry word times across"))
    else:
        if os.path.exists(a.out):
            sys.exit(f"refusing to overwrite {a.out}")
        phrases = [p.strip() for p in (open(a.phrases_file).read().split("\n") if a.phrases_file else a.phrases.split("|")) if p.strip()]
        models = json.load(open(a.words))["models"]
        slots = build_slots(models, phrases, a.fps, a.lead, a.next_onset, a.end, a.lag, a.min_frames, a.prefix, {k: float(v) for k, v in (o.split("=") for o in a.onset)})
        for x in slots:
            print(f"{x['id']:<4} f{x['tl_f'][0]:>5}-{x['tl_f'][1]:<5} {x['dur_f']:>4} f {x['dur_f'] / a.fps:5.2f} s  cut {x['lead_frames']:.2f} f before {x['onset_s']:.2f} s  \"{x['phrase']}\"  {' | '.join(x['flags'])}")
        json.dump({"fps": a.fps, "lead_frames": a.lead, "lag_s": a.lag, "words": a.words, "slots": slots}, open(a.out, "w"), indent=1); print("wrote", a.out)


if __name__ == "__main__":
    main()
