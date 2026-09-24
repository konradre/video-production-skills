---
name: video-take-review
description: >
  The per-seed READ of generated takes before the operator sees them: continuity across the take's own cuts and
  against the established shots FIRST, then the acceptance matrix (script beat, technical, anatomy, faces,
  product, eyelines, audio, named states at 4× on every frame, dignity), then voids and usable windows, then clips
  to the operator with residual doubts and frame times. Use when seeds land, a take must be judged against the
  ledger, the operator names a defect on a frame, a keeper's window must be set, or an instrument's number is
  about to be trusted. Triggers — "review the seeds", "which take", "continuity sheet", "is this seed usable",
  "cut before it breaks", "the same guy?", "frame 0:41", "check every frame", "break down the client's clips",
  "which window of this clip". Not for building the references the
  next shot needs — use video-refs-continuity. Not for the cost line or the submit — use video-gen-cost-gate. Not
  for placing the pick or applying a cut note — use video-edit-edl. Not for the delivered file's loudness or
  encode — use video-finish-qc.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3*), Bash(ffmpeg*), Bash(ffprobe*), Bash(bash*), Bash(ls*)
---

# Video Take Review

A landed seed is read the same day, by the agent, with instruments — and the operator's verdict is the
only pick. The read leads with **continuity** — the priority consideration for accepting or rejecting a gen —
never with the gag; a **void** carries its reason into the ledger; a **keeper**
carries its usable **window**; a residual doubt travels in the delivery note with its frame time, not in
a re-roll question. Three rules above the matrix: report what you SAW, not the win you hoped for (a take
that fixes one defect and introduces a worse one has the worse one as its headline); a whole-frame
downscale assesses composition only — identity, hands, teeth and product are read at 1:1 or larger; and
every instrument prints a known-answer self-test beside its number.

**What varies.** The pixel numbers here — the face floor, the instruments' blind spots, the composed-cut multiples —
were measured on 480p takes: count in the take's native pixels, and re-measure on a new generator's first takes. The
product rows exist only when a product is on screen, and the brand's standards and the genre's tone set the dignity row.
Continuity first, the matrix and the self-tests do not move — `video-production/references/WHAT-VARIES.md`.

## 1. Build the read for every seed

```
python3 scripts/qc_seed.py --out review --plate <accepted plate> takes/S02-G4-s1.mp4
bash    scripts/contact_sheet.sh takes/S02-G4-s1.mp4 4 4
python3 scripts/speech_timing.py takes/S02-G4-s1.mp4 --wpm 230,250   # a take that SPEAKS; see the delivery row
```

`qc_seed.py` gives the cut list (per-frame diff), the **continuity sheet** — the plate | the first frame
of every cut | the last frame — a 1 fps tile, the native-audio RMS peak (the hit's time) and a whisper
transcript. Read the sheet at 2–4×: every background element in every cut (one object checked is not
all of them). The transcript is of the WHOLE take, windowed afterwards to the excerpt in question — a short excerpt
transcribed alone loses the agreement between models that the full take keeps (`spot-audio-assembly` § 5). Client footage
is a take too: the same sheet, cut list and transcript per clip, and its display shape from
`video-production/scripts/probe_sources.py` before any crop. A whole PACK of supplied clips is broken down in one pass —
`scripts/footage_intake.py --src <dir> --out review/<pack>-intake` writes, per clip, the record (hash, display raster, the
delivery crop, cut candidates, motion with the conform's cadence read, colour steps), `per-frame.csv`, and three tiers of
sheet (overview → which clips are one camera ROUTE · survey → what is in frame across the whole clip · every frame → a
window's in and out), plus the stub for the written read. The procedure around it — routes, slots, windows, the pick —
is `ad-spot-preprod/references/FOOTAGE-CURATION.md`.

**Done when:** every seed has a sheet, a cut list, a transcript and a peak time in `review/`, and the
previous keeper's last frame (or the plate) sits beside them.

**Write the record, read the record.** `qc_seed.py --record` leaves `<take>.review.json` beside the take — the take's
sha256 and byte size, every measurement with the instrument and rule that produced it, the sheet path, and `notes[]` for
what the review decided (`qc_seed.py <take> --note "f69: the lamp exits right, correct"`). A resumed session reads the
record first (`--read`: a size check, then the hash) and re-views strips only for the claim it is about to act on — a
compaction re-derived one lamp read from image strips twice at image cost before this existed. A record whose bytes or
hash no longer match the take is STALE: `--read` refuses it, and it is re-measured, never hand-edited fresh.

**Write each image for what it is FOR.** A SURVEY image — the continuity sheet, the tile, a contact or cut sheet — is
JPEG q85 and may be downscaled; composition survives it. A VERDICT image — a face, a hand, a garment, a named state — is
a crop of the thing judged at native size or larger, JPEG q95 4:4:4, never downscaled. A GENERATOR INPUT — a start
image, a plate, a reference — stays PNG. An agent session can die on request BYTES long before its context fills
(lossless full frames, ~350 KB each, replayed every turn), so crop to what is judged; never cap a verdict image's
dimensions. [`references/INSTRUMENTS.md`](references/INSTRUMENTS.md) § Review images.

## 2. Continuity first — a break rejects the seed before its gag is judged

Against the previous keeper's last state and the established shots, per cut: the door (leaf, swing,
distance, which side of the lens), the seats and who is nearest the camera, counts on shelves, what is
in whose hands, wardrobe (accessories, layers), set dressing (the same objects), the
cast (each named character once, counted at 2× across the crowd; nobody invented), the pose state
(standing stays standing; fired stays fired; blanketed stays blanketed, no second bang), the product's
shape at every scale it appears and its size beside a known object, named states (teeth out, a garment off,
glass in the pane). A geometry break is not hideable; a missing beat is cheap to add. The axes:
`video-refs-continuity/references/CONTINUITY-AXES.md`.

**A cut the model composed inside ONE generation is a capability, never a defect.** Consistency is free inside one
generation and a gamble between two — it is what a long generation is bought for — so the read across a composed cut is
whether the world survived it: the same faces, wardrobe, room, light and performance register. Never fail a take for
containing a cut, and never grade the cut's motivation as a pass or a fail. A seam between two generations (an editor's
join, a splice hidden inside a shot) is a different object, judged at the edit.

```
python3 scripts/cut_consistency.py takes/S02-G4-s1.mp4 --cuts 5.5,9.25 --out review --box "5.5:150,200,330,420:150,200,330,420"
```

`cut_consistency.py` measures light, contrast, white balance and palette across every cut as multiples of the take's own
within-shot baseline, and writes the frames either side (a survey sheet) and the `--box` crops (verdict images) for the
identity and wardrobe read — a measurement beside the eye, never a verdict.

**Done when:** each seed carries a continuity verdict per cut with the failing axis named, or "holds".

## 3. The acceptance matrix — a table, never a score

Rows per seed, each answered PASS / FAIL / note; a FAIL is never overridden by a good-looking frame
([`references/ACCEPTANCE-MATRIX.md`](references/ACCEPTANCE-MATRIX.md)):

| row | the read |
|---|---|
| script beat | the scripted action IS the action (the verb the script wrote, not the one the model chose); the cause is on screen before the reaction; nothing invented |
| technical | dims, fps, CFR, duration; the take's internal cuts listed for the edit — DESCRIPTIVE, never a fail |
| consistency across cuts | per cut the model composed: the same faces, wardrobe, room, light and performance register either side — read on `cut_consistency.py`'s sheet and crops beside its multiples; a break on any axis FAILs, the cut's presence never does |
| anatomy | per person, in a per-person crop at 3×: 2 arms, 2 legs, 1 head, each hand on an arm, one prop per hand |
| faces | undistorted, ≥ ~60 px of face height in the take's native pixels (measured at 480p) for any beat the faces carry — a FLOOR, not a target: a face over it was rejected as under-rendered, and face detail compares only at equal resampled size; identity against the character's close shots (a reconstructed face is plausible, not faithful) |
| product | shape at 2× (the exact silhouette, haphazard angles, never aligned); proportion by a 4× crop beside the product photo (the pixel instrument is blind at 480p) |
| composition | nobody looks into the lens; the line-deliverer faces the camera, never back-to-camera; each gesture motivated in ITS framing; the reaction faces its cause with the matching emotion; no focus pull off the face; the camera holds its lock (NCC scale-match of the upper frame between frames) |
| audio | whisper: word-like events on an unscripted mouth = "shouting" (void); the scripted words intelligible (a near-homophone is a void); a generated tone at the head (spectral flatness < 0.3 with a stable peak); the hit's peak time |
| delivery | on a take that SPEAKS, the half the `audio` row does not cover — whether the performance is usable, which is the half an agent cannot hear. `speech_timing.py` reads four numbers off the word times: the SPAN against the duration (over ~0.3 s of tail silence = the model was given more seconds than the script fills and RUSHED; head silence is the same defect, and only that one is cheap to trim); every GAP at or over 0.25 s with its time (zero or one at a breath is good — a 0.7 s hold mid-line traces to a full stop in the prompt, which the model reads as permission to stop); the PACE as words over the SPAN, never over the duration, against the band the GENRE asks for (230–250 wpm is the creator/UGC band, and a brand read sits far below it — there is no universal band); and STUTTER CANDIDATES, an adjacent repeat or a bigram repeated inside a short window ("job infinitely and make infinitely"), which generated speech produces with no audio artefact at all, so they pass an intelligibility check and only a transcript read catches them. Candidates, never a verdict: the script says whether a repetition was written. A throwaway tail the prompt added after a full stop, to size a line to a venue's fixed duration step (`video-prompt-dialects` PHONE-NATIVE.md § Dialogue), is not the performance: the window ends at the pause after the real line, and the tail is never read as a stutter or a rush |
| named state | every frame of every window after the event, wides included, at 4× with the gamma lifted in dark cavities — a sparse sample passes defects that every frame at 4× shows |
| dignity | awake; nobody touched unless the script does it; nobody left lying under an effect; hands high, visible, held; no hand at the bottom edge of a chest-up two-shot — the brand's standards and the genre's tone set the bar |
| realism | poses natural; dance not jerky; no phantom extra; the runner seen from behind; the subject still in the last frame; on a creator-style take the tells pass — sound off first, hands on the product, a torso static > 6–7 s, consonant lip drift, the product morphing between shots, background warp, a phone or camera UI in frame (ACCEPTANCE-MATRIX.md row 10) |

**Done when:** the matrix is filled for every seed, the worst row is the headline of each seed's line,
and no row was inferred from a downscale.

## 4. Voids and windows

A seed that fails a hard row is **VOID** with its reason in the ledger (never reused). The same realism failure on
several seeds of ONE reference — waxy skin, a dead mouth, a face that reads fake — is a **reference void**: the reference is
rebuilt and re-accepted before the next seed (`video-refs-continuity` REPAIR-LADDER.md § Replace the reference, not the
seed), because re-rolling against it spends seeds on a picture the model cannot animate. A keeper is a take
plus a **window**: in/out set from the read — "only from 1/3 in, as they snap to", "cut before the teeth
show", "only the first 0.9 s", "cut on the frame the set leaves the lips", the out-point at least one
frame before the take's own internal cut. A window whose last state hides the face cannot be continued
by a gen; say so now.

```
python3 scripts/window_frames.py --in takes/S01B-CCU2-s2.mp4 --from 2.9 --to 3.3 --zoom 4 --gamma 1.6 --box 120,300,360,520 --out review/ccu2-mouth.png
python3 scripts/frame_match.py --take takes/S01B-F4-s1.mp4 review/operator-frame.png      # "which event is this?"
```

**A window of supplied footage is ranked at the DELIVERY shape, never on the source frame.**
`scripts/window_metrics.py --root --candidates <json> --out --intake <intake dir> --stack` decodes each candidate once
through its delivery crop and raster and prints, per metric with its validity: sharpness (comparable only inside one
camera route), luma and clipping, colourfulness, speed in frame-widths per second, the frame-to-frame **step in pixels at
the delivery width** — on a dropped-frame conform the recurring double step is twice it: under ~5 px it does not read,
near 30 px a pan stutters — and shake on the axis the move does not use. The 5-frame strip is the verdict; a window that
opens on the wrong thing fails on its first frame.

**Done when:** every seed is VOID (reason) or KEEPER (window, in/out, the state at the window's end).

## 5. Clips to the operator; the pick is theirs

Send the clips by path the moment they land (chat send only under the size cap, else the Windows path);
the sheets are the agent's notes, one line per seed: headline row, window, residual doubts with frame
times ("a wedding band 2.4–3.3 s"). The operator picks by path. When the operator names a defect:
locate it on THEIR frame (`frame_match.py` against the take windows and the gen heads), confirm the
person and the event back, and only then act — a defect acted on before it was located costs a wrong
fix or a wasted regen. When the operator says they see it in motion, they see it.

**Done when:** the pick is recorded by path with its window in the continuity ledger, voids carry
reasons, and the next skill (the ledger update in `video-refs-continuity`, then the finishing chain
after approval) can start from the record alone.

## ❌/✅

```
❌ "s2 plays the whole beat" as the headline                 ✅ "s2 breaks the door wall; s1 holds — s1"
❌ A contact sheet as the review                               ✅ The clips by path; the sheet as notes
❌ Identity judged on a 1000 px downscale                      ✅ A 1:1 crop of the face
❌ One figurine zoomed in one cut → "background clean"        ✅ Every element in every cut
❌ A 1.5× sample of the mouth window                           ✅ Every frame at 4×, gamma lifted
❌ "fixed the double arm" on a different person                ✅ Locate on the operator's frame, confirm back
❌ "Approve, or re-roll for the fleck?"                        ✅ The fleck in the delivery note with its time
❌ An instrument's number with no self-test                    ✅ A known-answer case printed beside it
❌ "the wide has no readable teeth"                            ✅ The named state read in the wide too, at hero size
❌ A take VOIDed because it contains a cut                     ✅ The cut listed; faces, wardrobe, room, light, register read across it
❌ A lossless full frame as a review image                     ✅ A crop of what is judged at q95; surveys at q85
❌ "the face clears 60 px" as a pass                           ✅ The floor cleared; detail compared at equal size
❌ "jitter 2.6 px - stabilise the pan"                         ✅ The residual ALONG a pan reads the conform cadence; shake is on the other axis
❌ 17 supplied files ranked as 17 shots                        ✅ The route table first: one subject + one move = one shot, whatever the file count
```

## Failure behavior

- An instrument that cannot detect the defect (a scale metric that matched a frame to itself at 0.90×;
  a hair-blob metric contaminated by loose pieces) is reported as broken, not as a number.
- No numeric tolerance is invented; the assets and the script define the target.
- Three non-converging rounds on one element → stop generating; the operator gets the alternatives as
  numbered questions.
- Nothing is upscaled, hero-passed or cut on a seed before the operator's pick.

## Cross-references

- `video-refs-continuity` — the axes, the ledger, the repair ladder when a read fails.
- `video-gen-cost-gate` — budget-final rules (a seed meeting every named constraint goes forward).
- [`references/INSTRUMENTS.md`](references/INSTRUMENTS.md) — every script, what it measures, its self-test.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
