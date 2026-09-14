---
name: video-finish-qc
description: >
  Runs the FINISH of a whole spot from its EDL and the QC of the delivered master: the per-shot upscale tier
  (after approval and a cost line), the hero pass, the three-stage finish (graded cut, master, deliverable), the
  finals run, and the one-pass QC (duration, loudness, true peak, cuts, take-cut leaks, VO placement). Use when
  approved keepers must be upscaled, a hero pass is due, a spot must be rendered from its EDL, finals are
  requested, or a delivered file must be verified or sent. Triggers — "upscale the keepers", "run the hero pass",
  "render the spot", "finish it", "final renders", "QC the deliverable", "rogue frames", "is the loudness right",
  "send me the 1080p", "starlight on the wides". Not for the per-clip ordering doctrine — use video-finish. Not
  for the cut or the beat gate — use video-edit-edl. Not for voicing or sourcing the sound — use
  spot-audio-assembly. Not for LUFS mastering of a standalone mix — use mastering-audio.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3*), Bash(ffmpeg*), Bash(ffprobe*), Bash(bash*), Bash(ls*), Bash(df*), Bash(cp*)
---

# Video Finish QC — the spot pipeline

`video-finish` fixes the order for one clip; this skill runs that order over a whole spot from its EDL
and reads the result back. Three rules above the pipeline: **nothing is upscaled before the operator
approved the take**, **every hosted second is paid
for through a cost line and a GO** (`video-gen-cost-gate`'s form), and **the delivered file is the only
thing that is verified** — `COMPLETED`, a big file and a passing per-shot check are not success.

**What varies.** The tier arms (Rhea, Starlight, Iris), the Resolve and Dehancer hero pass, the 2160×3840 mezzanine and the
1080×1920 deliverable are the established chain for vertical spots: another upscaler, grading stack or platform keeps the
three rules and the stage order, and changes the arm, the pass and the EDL's `canvas`. The loudness and true-peak targets
come from the EDL — `video-production/references/WHAT-VARIES.md` § Delivery platform.

## 1. Tier every approved keeper

For each EDL event with a keeper, decide the upscale arm from the framing, not from the price:

```
head ≥ ~50 px tall in the 480×854 take (chest-up and closer), no text to read → local Rhea ×4 (free, ~6 min per 5 s)
head < ~50 px (any full-body wide) or text / fine graphics that must read      → hosted Starlight Precise 2.6 ×4 FROM THE
                                                                                  ORIGINAL TAKE (never stacked); cost line → GO
a punch-in (zoom) on a Rhea hero                                                 → Iris ×1 after Rhea (marginal); never Iris ×4 alone
generated above 480p native                                                      → upscale from the native version, not a flattened master
```

The ~50 px cut-off was measured on 480×854 takes (`video-finish` § 1); on another native raster, count the head in that
take's own pixels. Generate clean (no grain/halation/bloom in a prompt); never post-scale in the upscale pass — the deliver
leg downscales. Detail and budgets: [`references/PIPELINE.md`](references/PIPELINE.md) § tier.

**Done when:** every event carries its arm, the hosted list has a cost line with the operator's GO, and no
take on the list is unapproved.

## 2. Run the hero chain

```bash
python3 ~/.claude/skills/video-production/scripts/detach.py --log <abs log> -- bash ~/.claude/skills/video-finish-qc/scripts/upscale_local.sh --root <abs project> takes/<A>.mp4 takes/<B>.mp4
bash ~/.claude/skills/video-finish-qc/scripts/hero_pass.sh --root <project> --look <look> <A>__rhea-1x4.mp4     # Resolve open + bridge, ONE clip per call
python3 ~/.claude/skills/video-finish-qc/scripts/upscale_fal_topaz.py --root <project> --clips <ids> --factor 4        # pre-flight → GO → --confirmed
python3 ~/.claude/skills/video-finish-qc/scripts/hero_distinct.py edit/hero/<A>__<look>.mov edit/hero/<B>__<look>.mov
```

- The local upscale runs **detached**, every path absolute, a timeout above the job; poll the log, never
  follow it; **a missing sentinel is a failure whatever the file size**. Nothing else uses that GPU.
- The hero pass needs Resolve open with a PROJECT and the bridge started **by the operator**; one clip
  per call, one job at a time, fresh names ("external scripting refused" = bridge down → stop, ask,
  retry). Heroes of equal length have identical byte sizes — distinctness by frame hash.
- Hosted jobs log their request id before polling and re-attach with `--resume`; a billed job is never
  resubmitted; the receipt keeps both billing reads.
- Probe every mezzanine (`yuv422p10le`, the raster, the frame count) and look at 3–4 frames after each of
  its internal cuts at 1:1; on a Starlight shot check identity across cuts and invented small text.

**Done when:** every event's `src` exists, probes 10-bit at the expected raster, is distinct, and its
sentinel is in the log.

## 3. Finish the spot from the EDL

```bash
python3 ~/.claude/skills/video-finish-qc/scripts/finish_spot.py --root <project> --edl edit/<SPOT>-EDL.json --stage all --tag=-v3 > <log> 2>&1
```

The script-fidelity gate runs first (a FAIL = no finish); `cut` writes the graded footage mezzanine
(heroes pre-graded as look `none`, upscaled mezzanines through the look's cube, designed renders at native
raster); `master` rebuilds the VO stem, composites layers and the card (a spot whose beat list forbids a card
has none), and mixes sfx, cues with ducks and native beds into a STATIC sum — no loudness processing, because a
single-pass loudnorm rides the programme and every later stage inherits the ride; `deliver` measures the master,
applies ONE static gain to the EDL's target, limits at the EDL's TP at 192 kHz, resamples to 48 kHz, limits again,
downscales, overlays the captions and encodes with the length capped at the runtime. It prints the limiting the
target costs and the loudest limiting-free target for the mix — read both before the render is heard; when the
client supplied a reference, its measured level is the target. Every intermediate is 10-bit 4:2:2; the deliverable is the
only 8-bit 4:2:0 file. A new version is a new tag and a new EDL (`video-edit-edl`); the log ends with
`FINISH-END` or the stage failed. A standalone clip or an excerpt: `finish_clip.py` (a fresh name per
render). Free disk is part of every status — a ProRes pair per version fills a drive.

**Done when:** the deliverable exists under its tag, the log carries `FINISH-END all`, and `df` was read
before and after.

## 4. QC the delivered file — per metric, with its label

```bash
python3 ~/.claude/skills/video-finish-qc/scripts/qc_deliverable.py --root <project> --edl edit/<SPOT>-EDL.json --deliv deliver/<file>.mp4
```

Duration vs runtime · **finite** loudness within 1 LU and TP under the ceiling (an audio-STREAM check is not
a SOUND check) · the delivered cut list vs the EDL joins with every extra detection named · take-cut leaks
(rogue frames; a cut the take composed and the operator kept is declared on the event as `accepted_cuts` and
prints as INFO — a gate that fails a chosen keeper on every render teaches every reader to skip its verdict) ·
the end card by NCC of the last frame · VO placement by envelope NCC. Then the eye and the
ear on the delivered file: the grade at zoom at several timecodes, the mouth check on the wides, the audio
at every cut and hit, the captions against the VO. Every instrument carries its known-answer case.
Designed content (explainer scenes, kinetic titles, cards) adds two judgement rows: `designed_frame_metrics.py` on the
delivered file and `literal_audit.py` on the composition's source.
The table and what each failure means: [`references/QC.md`](references/QC.md).

**Done when:** `QC-DELIVERABLE PASS` and the listen/look found nothing; anything found goes back to the
EDL or the hero, never to a gain nudge or a re-encode of the deliverable.

## 5. Finals and delivery

```bash
bash ~/.claude/skills/video-finish-qc/scripts/final_renders.sh --root <project> S01 S02 S03 …     # finish → QC → deliver/final/, sequential, sentinel FINAL-END
```

- **1080p masters only**; ≤ 30 MiB may go in chat, larger files are named by their path; a section excerpt
  as a small clip is fine.
- Finals are named versions per spot on `-final` EDLs with the current card; a per-shot Starlight
  replacement goes INTO final and the previous version stays in `deliver/`.
- Never re-encode a deliverable for a variant — every variant comes from the graded mezzanine
  (`video-finish` §7–8); platform folklore is answered by a lookup before an encode changes.
- Residual doubts travel in the delivery note with frame times, never as a re-roll question.
- Post questions and the answers that held: [`references/FAQ.md`](references/FAQ.md).

**Done when:** every final is in `deliver/final/` with a QC PASS line in the log, and the ask names each
file by path with its size.

## Failure behavior

- Gate FAIL, a null keeper, a missing source → the finish stops with the event named; fix upstream.
- Bridge down → stop and ask the operator to reopen Resolve + bridge; never launch Resolve from the agent.
- A hosted job FAILED/CANCELLED → the receipt records it; a retry is a NEW cost line, never a resubmit.
- A missing sentinel, a truncated file, an 8-bit mezzanine, a −inf loudness → the stage is re-run, not patched.
- Under ~6 GB free on the target drive → stop rendering and report; prune old mezzanine pairs only when
  the operator names them.

## Scripts

| script | does |
|---|---|
| `upscale_local.sh --root [--model rhea-1 --scale 4] takes…` | local reconstructive upscale, sequential, sentinel |
| `upscale_fal_topaz.py --root --clips [--factor] [--confirmed] [--resume]` | hosted Starlight with pre-flight, receipts, resume |
| `hero_pass.sh --root --look files…` | the Resolve + Dehancer pass over the bridge, one clip per call |
| `hero_distinct.py files…` | frame-hash distinctness of same-size heroes |
| `finish_spot.py --root --edl [--stage] [--tag]` | gate → cut → master (a static mix; the card when the EDL has one) → deliver (one measured gain, the limiting printed, the length capped) from the EDL |
| `finish_clip.py --root --hero --take --in --out --name` | a standalone clip / excerpt deliverable |
| `qc_deliverable.py --root --edl --deliv` | the one-pass QC of the delivered file; declared `accepted_cuts` print as INFO, never as leaks |
| `final_renders.sh --root spots…` | finish → QC → `deliver/final/` for every approved spot |

## Cross-references

- [`references/PIPELINE.md`](references/PIPELINE.md) · [`references/QC.md`](references/QC.md) ·
  [`references/FAQ.md`](references/FAQ.md).
- `video-finish` — the per-clip doctrine and its measured evidence (tiers, grain survival, Resolve codecs,
  byte caps); `video-edit-edl` — the EDL and the gate; `spot-audio-assembly` — the stem, captions and the
  placement instrument; `video-take-review` — `window_frames.py` for cut-boundary frames.
- Handoffs follow `~/.claude/skills/video-production/references/CHAIN.md`.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
