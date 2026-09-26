---
name: video-finish-qc
description: >
  Runs the FINISH of a whole spot from its EDL — part of every video job; a builder's render before it is
  PRE-FINISH — and the QC of the delivered master: the per-shot upscale tier (after approval and a cost line),
  the per-shot normalise, the hero pass, the three-stage finish (graded cut, master, deliverable), the finals run,
  and the one-pass QC (duration, loudness, true peak, cuts, take-cut leaks, VO placement, the finish against the
  previous version). Use when approved keepers must be upscaled, shots normalised, a hero pass is due, a spot must
  be rendered from its EDL, finals are requested, or a delivered file must be verified or sent. Triggers —
  "upscale the keepers", "run the hero pass", "normalise the shots", "apply the ads look", "has it been finished",
  "render the spot", "finish it", "final renders", "QC the deliverable", "rogue frames", "is the loudness right",
  "send me the 1080p", "starlight on the wides". Not for the per-clip ordering doctrine — use video-finish. Not
  for the cut or the beat gate — use video-edit-edl. Not for voicing or sourcing the sound — use
  spot-audio-assembly. Not for LUFS mastering of a standalone mix — use mastering-audio.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3*), Bash(ffmpeg*), Bash(ffprobe*), Bash(bash*), Bash(ls*), Bash(df*), Bash(cp*)
---

# Video Finish QC — the spot pipeline

`video-finish` fixes the order for one clip; this skill runs that order over a whole spot from its EDL
and reads the result back. Four rules above the pipeline: **the finish is part of every video job** — a render a
project builder made before this chain ran is PRE-FINISH, the word goes in its name or note, in the delivery message and
in the pause block, and NEXT carries the finish until it has run on the version the operator reviews (since
2026-09-26: eleven versions of one spot had shipped pre-finish before anyone asked); **nothing is upscaled before the operator
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
generated AT the delivery raster (a 1080p native take for a 1080p master)        → NO upscale arm at all; straight to the hero
a real capture at or above the delivery raster (a 1080p clip, a 1080p master)    → NO upscaler: a lanczos resample to the display
                                                                                  shape inside the normalise (§ 2); nothing redrawn
```

🔴 **A take generated at the delivery raster gets NO reconstructive upscale.** The arm exists to reconstruct detail that
is not there; at the delivery raster there is nothing to reconstruct, and the tier table above does not apply. The finish
is the Dehancer hero alone. ⚠ `.drx` and `.cube` are PARALLEL renderers of one look and are NEVER stacked — the `.drx`
already holds everything the cube holds plus the spatial pass a 3D LUT cannot carry (`look-library/GUIDE.md`). A Resolve
host takes the `.drx` and `look: "none"` in the finisher; the cube is for a host with no Resolve.
⚠ The mezzanine canvas is then an upscale-then-downscale round trip for those events. Harmless, and not free to change
while designed cards and conformed footage still sit above the delivery raster — note it, do not silently re-canvas.

**Real footage at the delivery raster gets no upscaler either** (since 2026-09-26: 1080p deliverables only, and no
footage warped). The above-delivery mezzanine exists to carry grain
(`video-finish` § 4), and an ad on the clean pair carries none; the faithful tier at the delivery raster is a mathematical
resample to the true display shape — an anamorphic 9:16 clip stored 1920×1080 at SAR 81:256 becomes 1080×1920 — and
nothing is redrawn. `normalise_shots.py verify` proves it per shot (a (0, 0) phase correlation between flat and hero), and
`qc_deliverable.py --prev` proves it on the finished spot against the pre-finish one.

The ~50 px cut-off was measured on 480×854 takes (`video-finish` § 1); on another native raster, count the head in that
take's own pixels. Generate clean (no grain/halation/bloom in a prompt); never post-scale in the upscale pass — the deliver
leg downscales. Detail and budgets: [`references/PIPELINE.md`](references/PIPELINE.md) § tier.

**Done when:** every event carries its arm, the hosted list has a cost line with the operator's GO, and no
take on the list is unapproved.

## 2. Run the hero chain

```bash
python3 ~/.claude/skills/video-production/scripts/detach.py --log <abs log> -- bash ~/.claude/skills/video-finish-qc/scripts/upscale_local.sh --root <abs project> takes/<A>.mp4 takes/<B>.mp4
python3 ~/.claude/skills/video-finish-qc/scripts/normalise_shots.py measure --root <project> --shots edit/flat/shots.json --target-ref deliver/<approved>.mp4 --target-at <s,…>
python3 ~/.claude/skills/video-finish-qc/scripts/normalise_shots.py flatten --root <project> --shots edit/flat/shots.json --out-dir edit/flat
bash ~/.claude/skills/video-finish-qc/scripts/hero_pass.sh --root <project> --look <look> --in-dir edit/flat <id>.mov      # real footage: the flats
bash ~/.claude/skills/video-finish-qc/scripts/hero_pass.sh --root <project> --look <look> <A>__rhea-1x4.mp4     # Resolve open with a project, ONE clip per call
python3 ~/.claude/skills/video-finish-qc/scripts/normalise_shots.py verify --root <project> --shots edit/flat/shots.json --flat-dir edit/flat --hero-dir edit/hero --look <look>
python3 ~/.claude/skills/video-finish-qc/scripts/upscale_fal_topaz.py --root <project> --clips <ids> --factor 4        # pre-flight → GO → --confirmed
python3 ~/.claude/skills/video-finish-qc/scripts/hero_distinct.py edit/hero/<A>__<look>.mov edit/hero/<B>__<look>.mov
```

- The local upscale runs **detached**, every path absolute, a timeout above the job; poll the log, never
  follow it; **a missing sentinel is a failure whatever the file size**. Nothing else uses that GPU.
- **Normalise before the look.** A cube or a `.drx` is the GRADE step and assumes normalised input: the library look alone
  read pale on flat overcast footage beside a hand-normalised chain (2026-09-16). Per shot, in 16-bit RGB at the display
  shape: the 0.5/99.5 luma percentiles → 0.02/0.88 (mapping to 0/1 clipped 7–30 % of the brightest shots under the look's
  own gain) and a saturation factor to the chroma of footage the operator approved (`--target-ref … --target-at …`, or
  `--target-chroma`) — `--t-scale 0.91` for the Dehancer hero, which lands ~27 % less saturated than the cube's estimate,
  0.75 for a cube-only grade. The flat is 10-bit, BT.709, and starts at pts 0: a flat that started at 0.041 s made
  Resolve render one extra leading frame. `verify` reads every hero against its flat — 10-bit, frames, the look applied,
  NO geometric shift, the frame alignment. A builder that grades with the cube instead prepends
  `normalise_shots.py chain --id <id>`. A hero is cut into a plan at the frame NEAREST the in-time, seeking to that frame's
  OWN start: a seek between frames ahead of a builder's `fps` filter doubles the event's first frame whenever the next
  frame starts more than half a frame later — 14 of 22 events on a half-frame in-point, and 4 of 22 in the approved
  version itself (`normalise_shots.py --help`; `setpts=PTS-STARTPTS` before the `fps` filter closes it in a builder).
- The hero pass needs **Resolve 21** open with a PROJECT, and runs on **`--transport auto`**: Local
  external scripting first (the Studio-native path, no in-app script needed), the in-app bridge as the
  fallback. **Never pass `--transport local` — it calls `die()` instead of falling through**, which
  turns a recoverable transport miss into a hard stop. One clip per call, one job at a time, fresh
  names. A connection error is DIAGNOSED before anyone is asked to touch Resolve: a scripting probe
  answers "is it reachable" for free, the window title names the open project, and the bridge is a
  listening PORT, not a window. **Never ask anyone to open Resolve, a project or the bridge without
  checking first** — a scripting probe (the Resolve MCP's `runtime_mode` and `get_current`) and the bridge's
  listening port (49632 by default) answer all three for free. Local answered when a portable Resolve was
  started through its own launcher and refused a direct `Resolve.exe` start: a bridge that keeps being needed
  is a launcher fact to state once. Heroes of equal length have identical byte sizes — distinctness by
  frame hash.
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

The look is the library's cube for the genre — `--look ads-clean` on an ad, a film look on a film — on generated takes and
on existing footage alike, and always on NORMALISED input (§ 2: a cube is the grade step, never the normalise step); before
the FIRST delivered version the operator picks it from `scripts/look_sheet.py --normalise auto` (a few of the project's own
frames × the candidate cubes rendered on the normalised frame, the normalised-only column beside them, the builder's current
chain as a column when one exists) — or, when the pick is handed over, the agent
picks on that sheet and names the pick provisional until one spot has been watched in motion at full size. A hand-written
level chain is a deviation that needs a reason: two such chains stood for ten hours on a documentary spot before the
operator asked (2026-09-15). A new SOURCE TYPE — another codec, bit depth or pixel format: a png-codec still, a 10-bit
ProRes render — gets a one-event render check before a full build, over EVERY frame of the event and not its first; a
10-bit source once rendered black through the grade and every other QC row passed, and a doubled first frame passed a
first-frame check (2026-09-26). And the finisher reads the HOST drive first: under `--min-free-gb` (40 GB, or three times
the spot's mezzanine pair) it refuses to start, because a guest's `df` is not the host's free space and a mezzanine pair per
version fills a drive (`references/PIPELINE.md` § Disk).

**Done when:** the deliverable exists under its tag, the log carries `FINISH-END all`, the look came from the sheet and ran
on normalised input, and the host drive's free space was read before and after.

## 4. QC the delivered file — per metric, with its label

```bash
python3 ~/.claude/skills/video-finish-qc/scripts/qc_deliverable.py --root <project> --edl edit/<SPOT>-EDL.json --deliv deliver/<file>.mp4
```

Duration vs runtime · **finite** loudness within 1 LU and TP under the ceiling (an audio-STREAM check is not
a SOUND check) · the delivered cut list vs the EDL joins with every extra detection named · take-cut leaks
(rogue frames; a cut the take composed and the operator kept is declared on the event as `accepted_cuts` and
prints as INFO — a gate that fails a chosen keeper on every render teaches every reader to skip its verdict) ·
every event's window sampled at three points for NEAR-BLACK frames (all three under 16/255 = FAIL unless the event declares `accepted_black`; the row that catches a source type the grade turned black) · the end card by NCC of the last frame · VO placement by envelope NCC · the longest still run against the EDL's `qc.max_still_s` (a
designed hold is declared on its event) · the true peak against the platform ceiling the EDL names (`loudnorm.TP_ceiling`) ·
the source geometry of every hero take as INFO (a display shape unlike the storage shape is normalised before any crop —
`video-production/scripts/probe_sources.py`) · with `--prev <the previous version>`, every footage event's middle frame
against the previous version — regraded, moved (a crop, scale or warp) or retimed (a one-frame slip) — and
`--prev-expect finish` fails a finish that moved or retimed anything (it caught 14 of 22 shots one frame late that every
per-hero check had passed, 2026-09-26), `--prev-expect changed:<ids>` a re-cut whose changed crop never reached the picture
· the platform contract as INFO (the range tag, the keyframe spacing, the edit lists). Then the eye and the
ear on the delivered file: the grade at zoom at several timecodes, the mouth check on the wides, the audio
at every cut and hit, the captions against the VO, a delivered frame beside the source's display frame at 1:1 (a circle stays a
circle). Every instrument carries its known-answer case. With no operator reachable (a headless run) the eye and the ear are
PROVISIONAL: the instruments stand in, and a look/listen queue of timecodes rides the handoff — nothing is final until the
operator has done it.
Designed content (explainer scenes, kinetic titles, cards) adds two judgement rows: `designed_frame_metrics.py` on the
delivered file and `literal_audit.py` on the composition's source. A creator-style spot adds two INFO reads against the
project's own real phone clips — the phone-texture band (`--phone-ref <clips>`, `phone_texture_probe.py`) and the
inter-shot spread before any global move — and the UGC tells by eye (`references/QC.md` § On a creator-style spot).
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

🔴 **A repair is judged by OUTCOME, on the picture — never by the metric that motivated it.** Measured on a synthesised
talking head whose mouth ran ahead of the locked VO: a uniform `setpts` + `minterpolate` retime cut the drift spread from
0.26 s to ±0.055 s, and a 5-segment piecewise re-pace moved the phrase onsets from −0.13/−0.56/−0.38 to −0.02/−0.01/−0.06
and lifted the own-audio correlation from 0.513 to 0.799. **Both were rejected on sight as dropped frames**, and the
UNREPAIRED takes were accepted at ±0.13 s drift. Same failure class as ranking a resynthesised mouth by edge energy: an
instrument that improves while the image degrades. **An alignment metric is a SELECTION aid, never a repair verdict.**
Build the repair if you like; ship it only if it survives a look beside the unrepaired take, and put both in front of the
operator. Two sub-facts, true and now moot: a uniform stretch kills DRIFT but creates a constant OFFSET needing a
separate in-point shift, and `minterpolate` does not honour a `setpts` factor exactly — force the count with
`-frames:v N`.


- Gate FAIL, a null keeper, a missing source → the finish stops with the event named; fix upstream.
- A Resolve transport miss → DIAGNOSE first: a scripting probe (the Resolve MCP's `runtime_mode`: running, GUI or
  headless; `get_current`: a project open) and the bridge's listening port; ask only for what the diagnosis says is
  missing, never to start what is already running; never launch Resolve from the agent.
- A hosted job FAILED/CANCELLED → the receipt records it; a retry is a NEW cost line, never a resubmit.
- A missing sentinel, a truncated file, an 8-bit mezzanine, a −inf loudness → the stage is re-run, not patched.
- Under ~6 GB free on the target drive → stop rendering and report; prune old mezzanine pairs only when
  the operator names them.

## Scripts

| script | does |
|---|---|
| `upscale_local.sh --root [--model rhea-1 --scale 4] takes…` | local reconstructive upscale, sequential, sentinel |
| `upscale_fal_topaz.py --root --clips [--factor] [--confirmed] [--resume]` | hosted Starlight with pre-flight, receipts, resume |
| `normalise_shots.py measure\|flatten\|chain\|verify --root --shots <shots.json> […]` · `--selftest` | the per-shot normalise before the look (levels from the 0.5/99.5 luma percentiles, a saturation factor to an approved chroma target, the display shape by lanczos), the 10-bit flats at pts 0 the hero pass grades, the chain a cube-grading builder prepends, and each hero read back against its flat (10-bit, frames, look applied, no shift, the frame alignment); the selftest checks the levels and saturation on a synthetic ramp and that verify catches a 4 px shift, a one-frame offset and a missing look |
| `hero_pass.sh --root --look [--in-dir] [--transport auto\|bridge] files…` | the Resolve + Dehancer pass, one clip per call: Local scripting first, the bridge as the fallback (`local` is refused — it die()s instead of falling through) |
| `hero_distinct.py files…` | frame-hash distinctness of same-size heroes |
| `finish_spot.py --root --edl [--stage] [--tag] [--min-free-gb 40]` | gate → cut → master (a static mix; the card when the EDL has one) → deliver (one measured gain, the limiting printed, the length capped) from the EDL |
| `finish_clip.py --root --hero --take --in --out --name` | a standalone clip / excerpt deliverable |
| `qc_deliverable.py --root --edl --deliv [--black-luma 16] [--tp-ceiling] [--max-still-s] [--phone-ref <real clips>…] [--prev <file> [--prev-expect finish\|changed:<ids>]]` | the one-pass QC of the delivered file; declared `accepted_cuts` and `accepted_still` print as INFO, never as failures; near-black per event; the still threshold and the TP ceiling come from the EDL (`qc.max_still_s`, `loudnorm.TP_ceiling`) unless overridden; the source-geometry and platform-contract INFO rows; `--prev` reads every footage event against the previous version (regraded / moved / retimed), a verdict with `--prev-expect`; `--phone-ref` adds the phone-texture band as INFO on a creator-style spot; `--selftest` (near-black, and same / regraded / moved / retimed read back) |
| `phone_texture_probe.py <clips>… [--crop 640] [--at 0.1,0.3,0.5,0.7,0.9] [--json]` · `--selftest` | the phone-texture band of a clip: dead-flat 8×8 share, noise floor, median block sd on native centre crops at five points, the mean and the frame RANGE per metric; a matched-content comparison between the project's real phone clips and a candidate, never a threshold (`video-finish` § 5 the phone-native tier; the calibration in its EVIDENCE.md); the selftest injects sd 0.5 / 1 / 2 / 4 and must read back linearly |
| `look_sheet.py --out --cubes --looks ads-clean,ads-warm [--normalise auto [--target-chroma] \| "<chain>"] [--blend look:0.85] [--current "<vf>"] --frame <video@s|image> …` | the frame sheet the operator picks the look from, before the first delivery: with `--normalise` every cube renders on the normalised frame beside a normalised-only column; `--selftest` |
| `final_renders.sh --root spots…` | finish → QC → `deliver/final/` for every approved spot |

## Cross-references

- [`references/PIPELINE.md`](references/PIPELINE.md) · [`references/QC.md`](references/QC.md) ·
  [`references/FAQ.md`](references/FAQ.md).
- `video-finish` — the per-clip doctrine and its measured evidence (tiers, grain survival, Resolve codecs,
  byte caps); `video-edit-edl` — the EDL and the gate; `spot-audio-assembly` — the stem, captions and the
  placement instrument; `video-take-review` — `window_frames.py` for cut-boundary frames.
- Handoffs follow `~/.claude/skills/video-production/references/CHAIN.md`.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
