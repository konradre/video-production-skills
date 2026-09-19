#!/usr/bin/env python3
"""invented_sound.py — did a take that should be SILENT of speech invent some? The audio row of a quiet shot on a
joint audio-video model, which fills an empty audio lane with talk.

  invented_sound.py <take>... [--after 1.5] [--model small] [--band 300,3400] [--thr 0.005] [--json <out>]
                    [--selftest]

Two reads of the audio after --after seconds (the first-second flap is the mouth instrument's job):

  WORDS   faster-whisper with its VAD on, segments kept only below a 0.6 no-speech probability. Invented speech
          transcribes as fluent nonsense ("the sling I had done first again").
  BAND    the RMS of the 300-3400 Hz speech band. Measured on one H3 scene (2026-09-19, 36 takes): 0.051-0.053
          on every take with invented speech, 0.0001-0.0007 on every clean one, room tone with a named hum
          included — two orders of magnitude apart, so --thr 0.005 sits in the gap.

A take is INVENTED when either read fires. Calibrated against the same 30 takes an earlier by-ear count scored
(five arms, 2 / 0 / 1 / 1 / 0 takes with invented sound): this reproduced the counts take for take. A scripted
line, a scored bed or a sound effect in the band is not invented — read the words beside the number.

--selftest checks the band path on synthetic audio: room noise stays under --thr, a syllable-rate speech-band
burst clears it. The words path has no synthetic known answer; its calibration is the by-ear set above.
"""
import argparse, json, subprocess, sys
import numpy as np

SR = 16000


def band_rms(a, lo, hi):
    if a.size == 0: return 0.0
    sp = np.fft.rfft(a); fq = np.fft.rfftfreq(len(a), 1 / SR)
    sp[(fq < lo) | (fq > hi)] = 0
    return float(np.sqrt((np.fft.irfft(sp, len(a)) ** 2).mean()))


def audio_after(path, after):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(after), "-i", path, "-ac", "1", "-ar", str(SR),
                        "-f", "s16le", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768


def selftest(lo, hi, thr):
    rng = np.random.default_rng(0); t = np.arange(4 * SR) / SR
    room = 0.0015 * rng.standard_normal(t.size)                                   # a quiet room: broadband, low
    voice = np.sin(2 * np.pi * 600 * t) + 0.5 * np.sin(2 * np.pi * 1500 * t)              # two speech-band formants
    talk = room + 0.05 * voice * (np.sin(2 * np.pi * 4 * t) > 0)                           # at 4 syllables a second
    r0, r1 = band_rms(room, lo, hi), band_rms(talk, lo, hi)
    assert r0 < thr < r1, (r0, thr, r1)
    print(f"SELFTEST OK — room {r0:.4f} < thr {thr} < syllable burst {r1:.4f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("takes", nargs="*"); ap.add_argument("--after", type=float, default=1.5)
    ap.add_argument("--model", default="small"); ap.add_argument("--band", default="300,3400")
    ap.add_argument("--thr", type=float, default=0.005); ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(); lo, hi = [float(x) for x in a.band.split(",")]
    if a.selftest:
        selftest(lo, hi, a.thr); return
    if not a.takes: sys.exit("need at least one take")
    from faster_whisper import WhisperModel
    m = WhisperModel(a.model, device="cpu", compute_type="int8")
    out = []
    for p in a.takes:
        x = audio_after(p, a.after); b = band_rms(x, lo, hi)
        segs = [s for s in m.transcribe(x, language="en", vad_filter=True, beam_size=1,
                                        condition_on_previous_text=False)[0] if s.no_speech_prob < 0.6 and s.text.strip()]
        words = [f"{s.start + a.after:.1f}s:{s.text.strip()}" for s in segs]
        verdict = "INVENTED" if (words or b > a.thr) else "clean"
        out.append({"take": p, "band_rms": round(b, 5), "words": words, "verdict": verdict})
        print(f"{verdict:8s} {p.split('/')[-1]:48s} band {b:.4f}  words: {' | '.join(words) or '-'}", flush=True)
    if a.json: json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
