# The QC of a finished spot — per metric, with its label

Nothing is graded by a total score: the number decides pass/fail and the label decides what to change.
`COMPLETED`, a big file, a passing per-shot check — none is success; the DELIVERED file is what is read.

## On every hero / mezzanine (before the cut)

| check | how | fail reads as |
|---|---|---|
| bit depth and raster | `ffprobe … stream=codec_name,pix_fmt,width,height` — `yuv422p10le`, the expected raster | 8-bit banding in mist and gradients; a padded width (CineForm ×16) needs a crop on the deliver leg |
| completion | the tool's sentinel in the log (`TOPAZ-UPSCALE-OK`, `RHEA-OK`, `HERO-PASS-END`) | a truncated mezzanine shortens the deliverable silently |
| distinctness | `hero_distinct.py a.mov b.mov …` — frame hashes, not byte sizes | a stale render served from a cached media-pool path |
| cut boundaries | 3–4 frames after every internal cut of the upscaled file at 1:1 (`video-take-review` `window_frames.py`) | temporal models smear across cuts; the thinnest-bitrate input comes back mushy first |
| Starlight shots | identity across cuts (a small face is reconstructed plausibly, not faithfully); invented small text (a door sign grew lettering) | a wrong face or fake text in a wide |
| the grade | a 1:1 crop of graded vs ungraded on a highlight (halation = a warm bleed) and a flat area (grain = texture); NEVER a grep of the `.drx` | a doubled grain pass; a look that crushed the subject |

## On the delivered file — `qc_deliverable.py` in one pass

| metric | pass | the failure it catches |
|---|---|---|
| duration vs `runtime_s` | < 50 ms | a truncated stage; a stale master under a new EDL |
| loudness I · LRA | within 1 LU of the EDL target and **finite** | an audio-STREAM check is not a SOUND check: a conforming AAC track at −inf ships silent |
| true peak | ≤ the platform ceiling (the EDL's `loudnorm.TP_ceiling`, else −1 dBTP); the EDL's TP is the master's limiter ceiling under it, exceeded by 0.4–1.0 dB of AAC overshoot that grows with how hard the limiter works | a hot transient past a static gain with no limiter; a limiter placed only AFTER the resample (measured −1.0 dBTP against −2.0 before / −2.1 both); a quieter premix pushed harder into the limiter (a −1.5 target delivered −0.9 where earlier versions overshot 0.2) |
| delivered cuts vs EDL joins | every extra detection named: a take's own cut, a declared accepted cut, motion, or a LEAK | rogue frames at a join the eye missed |
| take-cut leaks | no hero window crosses its take's own scene cut, except the cuts the event declares in `accepted_cuts` (printed as INFO) | the out-point past the take's internal cut. A cut the take COMPOSED inside one long generation and the operator kept is not a leak — declare it on the event: a row that fails a chosen keeper on every render teaches every reader to skip the verdict line |
| end card | NCC ≥ 0.9 of the final's last frame vs the card render's last frame | the wrong card version on a final |
| VO placement | every line < 15 ms by envelope NCC (`spot-audio-assembly`) | a stale stem; a shifted insert |
| per-event A/V sync | for every event with native audio and a hit: locate the hit's RMS peak in the delivered file and assert the picture event on the frames at that time; the cut stage's source seek explicit (`handle_head` = where `in` sits in the source; full-take heroes ⇒ `= in`) | an offset that lives INSIDE one event — a join tile cannot see it; the seek-convention defect shipped a wrong first render |
| **format rows** — frame, codec, colour tags, fps / CFR, faststart, audio format | the EDL canvas with 1080 on the short side · H.264 High `yuv420p` · BT.709 primaries + transfer + MATRIX · `r_frame_rate == avg_frame_rate` at the EDL fps · `moov` before `mdat` · AAC 48 kHz stereo | the standing "1080p masters only" rule had no instrument row; every shipped final carried an UNTAGGED matrix (`color_space=unknown`) until the deliver encode set `-colorspace bt709` (2026-09-10) — a metadata-only fix: `-c copy -bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1` |
| black / frozen frames | no black run ≥ 0.1 s except a trailing fade; no still run ≥ `qc.max_still_s` (0.5 s by default; the project sets it) inside the footage span, the longest run printed; a designed hold declares `accepted_still: "<why>"` on its event and prints as INFO (the card holds by design) | a hole from a missing layer or a truncated stage; a stalled overlay; a type beat that held one frame for 10 s while only the footage behind it moved |
| source geometry | INFO: every hero take whose display shape differs from its storage shape (SAR ≠ 1:1, a rotation tag), from the take's own probe; the eye check is a delivered frame beside the source's display frame at 1:1 — a circle stays a circle | 11 of 17 client clips stored anamorphically were read as square pixels and every render stretched them 3.16× wide; no row compared a delivered frame with its source (2026-09-15) |

**Every row has a kind.** `format` rows are mechanically fixable — the agent fixes them alone (a re-mux for tags or
faststart, a re-encode at the right frame) and re-runs; `judgement` rows change the content — duration, loudness, cuts,
leaks, black frames, the card, placement — and go to the operator with the number. The summary line names the failures
by kind (`ffmpeg-skill`'s `check.py` drew the same line: "format rows are safe to fix mechanically; judgement rows
change the content").

Then the eye and the ear, on the delivered file: the grade at zoom at several timecodes over light and
dark backgrounds (never the first frame alone); the mouth check on every wide; the audio at every cut and every hit (a click, a doubled tone, a clash under the signature);
the captions' text against the VO variant. Every comparison instrument carries a known-answer case in the
same invocation (a file against itself must return `inf` / NCC 1.0): `ffmpeg -v error` suppresses the
PSNR summary line and an empty result reads as "identical".

## On designed content — explainer scenes, kinetic titles, cards

A defect hunt passes a film that is small and dark: four QC rounds found nothing wrong with one (an upstream explainer
kit, 2026-09). Two judgement rows read what a defect list cannot:

| check | how | fail reads as |
|---|---|---|
| empty / small / still | `video-take-review` `designed_frame_metrics.py` on the DELIVERED file, the caption band cropped out (`--content`), the scene windows as `--shots` | a scene whose hero never reaches a third of the content box; nothing big on screen for more than 1.5 s; a narrated scene that enters and freezes (more than 40 % still samples, or a hold over 1.0 s). A card, a logo or a legal hold is still by design |
| on-screen text vs the approved copy | `designed-elements` `literal_audit.py <composition> --approved <copy>` on the SOURCE | a string no sampled frame showed — a counter's intermediate, a label on a transition, a stale kicker |

## Audio provenance

Every finish step earns a cheap verification immediately before it runs — a written plan is a set of
hypotheses. Two of five planned steps were wrong in ways the output would never show: "coarse grain, then
watermark" when the film-emulation `.drx` already lays grain, halation and bloom in the stock node (a 1:1
crop settles it), and "re-lay the real music track" when the edit's audio was not a clean slice of it (the
correlation below). Doubled grain looks like grain; a raw track looks like the music.

Never re-lay the raw music track over a processed mix — measure the correlation (0.146 against a 1.0
self-test); the graded intermediate's PCM audio is the best copy of a mix that was made in the grade.
Check what the grade pass emitted for audio before sourcing audio from anywhere else.

When the music seems to swell, or a second track seems to appear around the voice, read before re-mixing:
difference the short-term loudness against a static sum of the same parts (movement = processing), and read every
VO file's gap floor (a VO lifted from a finished cut carries its bed) — `spot-audio-assembly` MIX-AND-QC.md.

## Sending the result

The masters are 1080p only. A file ≤ 30 MiB may be sent in chat; a larger one is named by its full
path. Residual doubts go in the delivery note with their frame times, never as a re-roll question.
