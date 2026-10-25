# The mix, the loudness pass, and the read of the delivered file

The finisher (`video-finish`) renders the mix from the EDL; this file is the contract it implements and
the read that proves it on the DELIVERED file. Every number is measured per channel, never on a mono sum
(`-ac 1` sums to +6 dB and clips the measurement; average `(L+R)/2` when a mono read is needed).

## The stem

`build_vo_stem.py`: every placed line (each `audio.vo` entry with a file) on a silent 48 kHz stem at its
EDL time, gained to `target_lufs` (−18) with a `peak_cap_dbfs` (−3) ceiling per line, by sample
placement — no filtergraph timing drift. Rebuilt from the EDL on every master: a stale stem once shipped
a line at its previous version's time. Before a line is placed, its gap floor is read and its source printed
(`VO-PIPELINE.md` § Where a VO file came from).

## The master's mix graph

```
[vo stem] + [sfx: atrim src_in/dur, afade out 0.1 s, volume, adelay at]
         + [music: atrim to span, afade in/out, ducks as a per-frame volume expression, adelay tl[0]]
             (a duck of 3, 4 or 5 numbers — its own ramps; a duck whose own ramp is under 0.1 s runs on 48-sample frames,
              because a 1024-sample frame returned a suck-out 7–17 ms after its hit, measured 2026-10-25)
         + [native beds: -ss from -t (to−from) of the take, afade in 0.02 / out 0.03 when windowed, volume, adelay]
  → amix normalize=0 → atrim 0:runtime → PCM 24-bit master          a STATIC sum: no loudness processing here
```

A loudness pass in the master is a defect, not a convenience: a single-pass loudnorm is dynamic by definition, so it
rides the programme — the bed swells in every gap between lines and recedes under them — and every later stage
inherits a gain ride it cannot undo. A listener hears it as a second element washing in and out over the track.

## The delivery loudness pass — the order is the rule

1. **Measure the master** (`loudnorm … print_format=json`, read only): integrated `I` and true peak `TP`.
2. **One static gain**, `g = I_target − I_measured`. Never `loudnorm linear=true`: linear is a REQUEST — loudnorm
   falls back to DYNAMIC whenever the linear gain would push the true peak past its TP target, and says so only in
   its summary's `Normalization Type`.
3. **`aresample=192000`, `alimiter` at the EDL's TP, `aresample=48000`, `alimiter` again**: at 192 kHz a sample
   limiter sees the inter-sample peaks; AAC would keep 96 kHz without the resample. Measured on a real master
   (target −2.4, AAC 192k): a limiter only AFTER the resample delivered −1.0 dBTP, only before −2.0, both −2.1,
   none −1.9 — the after-only order is the worst of the four. (attack 5, release 60, `level=false`.)
4. **The limiting the target costs is printed before anything is heard.** After the gain the peak sits at
   `TP_measured + g`; everything above the TP target is limited. The loudest LIMITING-FREE target is
   `I_measured − TP_measured + TP_target`: a mix measuring I −21.1 / TP −5.25 against a −1 dBTP target is
   limiting-free up to −16.9 LUFS, and every louder target buys its loudness with limiting. **The total hides where it
   is spent:** the designed impacts are the loudest moments the mix was built around, so a limiter that takes several dB
   off exactly those windows undoes them. The finisher therefore renders the master twice (the gain alone, and the gain
   plus the limiter chain, both through the same resample) and writes each impact window's deepest cut to
   `edit/mezz/<deliverable>.limiter.json`, never into `deliver/`. An impact is the hit a suck-out releases on; with no
   suck-out in the EDL, the three loudest 400 ms windows stand in. `sound_table.py` prints the cut beside the loudest
   rows (makevoid/motion-graphics-music-video-skill `sfx_mix.py`). A failed read, or a record whose sha256 is another
   render's, reads as such and never as a cut.
5. **AAC overshoots the limited peaks by 0.4–1.0 dB, and the overshoot GROWS with how hard the limiter works**: the
   EDL's TP target sits under the platform's ceiling by at least that (−2.4 for a −1 dBTP delivery; a −1.5 target that
   delivered −0.9 on a quieter premix, where the earlier versions had overshot 0.2, is the measurement behind the range).
   The delivered bar is the platform ceiling — `loudnorm.TP_ceiling` in the EDL when it is not −1 dBTP — verified on the
   DELIVERED file every time, never inferred from the WAV target plus a fixed allowance; re-measure after any premix
   change.
6. Captions are overlaid after the downscale in the same pass; `-t <runtime>` caps the length (without it AAC
   priming and padding set the container duration); `-movflags +faststart`.

## Loudness steps and entries — the movement, not the number

A listener's notes are about movement ("avoid big changes in volume", "come in almost inaudibly and fade up over two
seconds"), never the integrated number (nicceasy/3d-product `references/sound-design.md` § 9, MIT). `sound_table.py`
reads it on the delivered file as INFO rows:
- **steps:** short-term loudness (BS.1770, 3 s windows CENTRED on their time, since a window stamped at its end lags its
  cause by half a window), LU/s over 1 s, placed at the power midpoint;
- **entries:** after a near-silence, the rise from 30 dB to 3 dB under the plateau on the 400 ms curve;
- **range:** the short-term range, reported and never gated.

Upstream gates a step at 3.5 LU/s and wants an entry to rise over ≥ 1.2 s, each on its own metric. Calibrated on synthetic
signals, this implementation reads:

| case | step (LU/s) | entry rise (s) |
|---|---|---|
| a hard 6 dB step | ~3.0 | — |
| a hard 10 dB step | ~6.0 | — |
| 6 dB over 3 s | ~1.9 | — |
| a hard entry | — | ~0.2 |
| a 1.5 s raised cosine | — | ~0.85 |
| a 2 s fade from −40 dB | — | ~1.35 |

A designed step is a named exception, read from the EDL and never counted: a suck-out and its impact, a cue declared
`fade_in: 0` (an absent `fade_in` is judged), and an entry on a line or an sfx. A quiet beat dips ≤ ~4 LU — "a gentle
dip, not a hole".

**Notes → numbers.** Change only the named layer, then null-test the rest against the previous version:

| note | change |
|---|---|
| "a bit" | −2 to −3 dB |
| "half" | −6 dB |
| "almost inaudibly" | ≤ −30 to −40 dB |

Its trap: lowering a bed raises the next step. A bed lowered 4 dB doubled the step into the next song (~3.1 → ~6.2 LU/s),
so re-read the steps after every level note.

## The loudness target

When the client supplied a reference, its measured integrated loudness is the target: the client approved that
level. Measure it with `ebur128=peak=true`, record I, LRA and peak with the file name, and hold the number in a
`derived` block (`video-edit-edl` EDL-CONTRACT.md § Derived constants) so it stays tied to the file it was read
from. The house −14 LUFS is the default when there is no reference. Either way, compare the target with the
finisher's printed limiting-free ceiling before choosing to limit.

## The bed against the voice — derived, never carried

When the client's split stems exist, the music-under-voice relationship and the duck are MEASURED from them: 50 ms
blocks; speech = blocks within 25 dB of the loudest VO block, gap = blocks more than 45 dB below it, the two sets
verified disjoint; the music under speech against the VO level is the relationship, the music under speech against
the music in the gaps is the duck. Size the bed's `vol` against the stem as BUILT and stamp both constants with their
inputs: a relationship carried for three rounds without re-measurement was 2.6 dB too loud, and a replaced VO set
had invalidated the `vol` sized against the old stem without a sound.

## "The music changes around the voice" — two reads before any fix

1. **The gain-ride read**: difference the 1 s short-term loudness of the rendered master (or the deliverable)
   against an EDL-exact static sum of the same stem, bed, ducks and fades. A static mix differences to a flat line,
   so any movement is processing. Self-test: the sum against itself reads 0.000 dB; a constant array 0.00 dB of swing.
2. **The source read**: every VO file's gap floor (`build_vo_stem.py` prints it). A file lifted from a finished cut
   carries that cut's bed inside every line — the music then appears exactly when the voice does, and muting the
   events' native audio changes nothing.

## The read of the delivered file (per metric, with its label — never a total score)

| metric | instrument | pass |
|---|---|---|
| duration vs `runtime_s` | ffprobe | < 50 ms |
| integrated LUFS · LRA · true peak | `ebur128=peak=true` on the delivered file | I within 0.5 LU of the target; TP ≤ the EDL's TP |
| VO placement | `qc_vo_placement.py` — 10 ms RMS envelopes, 300–4000 Hz, NCC vs the EDL `at` | every line < 15 ms |
| VO ↔ sfx clash | the sheet (`beat_sheet.py`) + a listen at the signature and every hit | no line under a hit or the signature |
| native artifacts | `audio_head_scan.py` on every take; the ear on the delivered file at each cut | no tone/drone the ear catches; no click at a cut |
| the sound table | `sound_table.py` — each music cue's presence at three points across its span, each suck-out's depth, the real silences before `qc.turn`, the loudest 400 ms moments and what sits there (with the limiter's cut there), the limiter's deepest cut per designed impact, 20–60 Hz against the band, the loudness steps, the entries after a near-silence and the range; both channels kept, their powers added | INFO only: 25–30 dB · ≥ 2 before the turn (films, music videos) · the designed impacts · about −15 dB — read, listened to, no verdict yet |
| the VO script | the `text` table quoted in the ask | matches the client script's lines verbatim |

A waveform cross-correlation is NOT the placement instrument: under loudnorm + AAC it read 0.08 where
the envelope read 0.65–0.91. The instrument self-tests (a take against itself at 0 ms, NCC ≥ 0.99) or
prints nothing.

**A presence or tonality instrument is gated by level.** On a clean render's −83 dBFS floor, codec noise reads as
perfectly tonal, so spectral flatness on the quietest blocks "found" music in a file that had none. The self-test
carries the floor case — silence and near-silence — not only the two full-scale extremes (white noise against a
tone), which pass while the instrument stays blind to the case that fooled it.

## Room tone

`roomtone_synth.py --ref <sibling take> --ss --t --dur --out`: the reference slice's smoothed
magnitude spectrum colours independent white noise in one FFT over the whole length — stationary, no
seams, no transients, RMS-matched, faded. Used under a muted window (`native_audio_from/to`) so a cut
does not fall into digital silence.

## The phone-mic register — a creator-style spot

The mix reads as a phone's when the sound carries the ROOM: a room-tone bed under every line (`roomtone_synth.py`), the
appliance hum and the handling noise the take earned kept rather than cleaned, a phone-mic band (a high-pass around
90 Hz, a soft roll-off above ~7.5 kHz), a light auto-gain feel (a slow compressor that lifts the gaps), no noise
reduction, no music under the open. The loudness pass does not move: the same measured master, one static gain to the
target (the house −14 LUFS without a client reference), the limiter chain above — a phone register is a spectrum and a
dynamic, never a level. Disfluencies are PLACED, not cleaned — 2–4 per 30 s with one in the first sentence
(`ad-spot-preprod` UGC-GRAMMAR.md § Delivery) — and a breath before a line stays. `video-finish/scripts/phone_native.py
--audio phone` applies the band and the compressor to a picture render; the stem, the placement and the loudness pass stay here.

**The register follows the capture device the frame shows** (house rule, 2026-09-25, from a practitioner's AI-UGC
workflow). A clip-on, wireless or headphone mic in the picture — most creators now wear one — earns a clean, close, dry
voice with the room kept low: no phone band and no auto-gain lift, so `phone_native.py --audio phone` is skipped. A bare
phone at arm's length earns the register above. A generator voices every line clean, so the device is chosen with the
persona and drawn into its still (`video-refs-continuity` REFERENCE-CONTRACT.md § Generating an identity reference);
the sound then agrees with a picture that explains it.

**A generator that speaks on its own clock is dubbed and RETIMED whenever a voice-over is locked.** Gemini Omni Flash 1.1
and MiniMax H3 voice the line themselves and take no audio input, so where a VO is locked the delivered voice is the VO
take; where none is, the model's own voice can ship (`video-prompt-dialects` PHONE-NATIVE.md § Dialogue), and because
every line is a fresh render of that voice, the lines are heard side by side for timbre, energy and pace before the cut.
To dub, whisper both at word level, fit
`native_t ≈ a × vo_t + b` on the matched words, then `atempo 1/a` + `adelay b` (pitch-preserving). Measured: H3's mouth
ran ≈ 1.09–1.13× slower and started ~0.75 s late against the same ElevenLabs take, and the fit left ~160–170 ms rms per
word with the placement at 0 ms (envelope NCC 0.99 on the delivered file) — fine at chest-up framing, loose for a close
read, which is why the words that must land exactly go to an audio-driven model (`video-gen-cost-gate` VENUES.md
§ Creator-style talking heads). "Every AI UGC has the same voice" is a community tell with a weak fix (a slightly
different room reverb per persona); the strong fix is a different voice per persona and a real room tone.
