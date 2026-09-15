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
   limiting-free up to −16.9 LUFS, and every louder target buys its loudness with limiting.
5. **AAC overshoots the limited peaks by 0.4–1.0 dB, and the overshoot GROWS with how hard the limiter works**: the
   EDL's TP target sits under the platform's ceiling by at least that (−2.4 for a −1 dBTP delivery; a −1.5 target that
   delivered −0.9 on a quieter premix, where the earlier versions had overshot 0.2, is the measurement behind the range).
   The delivered bar is the platform ceiling — `loudnorm.TP_ceiling` in the EDL when it is not −1 dBTP — verified on the
   DELIVERED file every time, never inferred from the WAV target plus a fixed allowance; re-measure after any premix
   change.
6. Captions are overlaid after the downscale in the same pass; `-t <runtime>` caps the length (without it AAC
   priming and padding set the container duration); `-movflags +faststart`.

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
