---
name: video-edit-edl
description: >
  Builds the EDIT of a generated-video piece as a derived EDL: the script rewritten as a beat list FIRST, the
  picked keepers placed by derivation, the sound placed from picture markers, the script-fidelity gate before any
  finish, and every note applied as a parameter change to a NEW version file. Genre switch: ads, film, music
  video. Use when approved keepers need a cut, a cut note or a client round changes a cut, or an EDL must be
  checked against the script. Triggers — "build the EDL", "cut it", "move the line to", "the word should be at",
  "shave a bit off the end", "carry the sound into the next shot", "beat sheet", "does the cut follow the script",
  "new version", "make the alternate". Not for reading a seed or setting its window — use video-take-review. Not
  for the render, the upscale or the delivery encode — use video-finish-qc. Not for voicing or sourcing the sound
  — use spot-audio-assembly.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3*), Bash(ffmpeg*), Bash(ffprobe*), Bash(ls*), Bash(cp*)
---

# Video Edit — the EDL

The edit is a **derived document**: the client script is the single source of truth, the keepers are
the operator's picks, and every timeline number is computed from them by a builder. A typed time is a
defect waiting for the next re-version; a hand edit to a shipped EDL is a lost audit trail. The finisher
(`video-finish-qc`) reads nothing but this file, and the beat gate refuses a finish the script does not
sanction. Editorial notes are **cut notes first** — four re-cuts in an afternoon cost zero credits;
a regen is the last rung of the repair ladder, never the first.

**What varies.** The ad grammar's numbers — a hook inside 2 s, the closer 0.7 s into the turntable, the last line
0.5 s before the hit, the card's 2.5 s — and its captions and card belong to one genre: film and music video carry their
own ([`references/GENRE-GRAMMAR.md`](references/GENRE-GRAMMAR.md)), and a brand's own spec overrides either. The
derivation, the gate and the new-file rule do not move — `video-production/references/WHAT-VARIES.md`.

## 1. Write the beat list from the script — before the EDL

Rewrite the client script (or the film beat sheet, or the track map) as `prompts/<SPOT>-beats.json`:
one beat per script line or on-screen stage direction, in script order, each naming the EDL events that
will realise it, the VO and sfx that belong inside it, the order rules (sfx → O.S. line → the reaction word), the
marker a line must clear (`vo_ends_before`), the cue edges that sit on a marker, a layer's lead before
the next beat, a minimum duration, and the ids that must NOT appear (`forbidden_events`, with the
reason the operator gave). Markers are `{event, take}` — **measured** on the keeper: the hit's RMS peak
in 25 ms windows, a word onset from the take's transcript, the frame a wall clears. Nothing is guessed.

- A sound-only beat still needs its visual cause on screen; a reveal is its own beat and its asset
  appears in no earlier beat; a client-cited beat is located in the DELIVERED file and the EDL history
  before anything changes.
- Schema and every gate rule: [`references/BEATS-CONTRACT.md`](references/BEATS-CONTRACT.md).

**Done when:** every script line is a beat, every beat names its events, every marker carries the
measurement it came from, and the file exists before any EDL does.

## 2. Build the EDL by derivation

A **keeper** is `take + in + out + the state at out` (from `video-take-review`); the window's out-point
sits at least one frame before the take's own next internal cut. The builder — `scripts/edl_build.py`
on a plan, or a spot-specific `build-edl.py` whose every slot is an argparse flag — accumulates `tl`
from the ordered events, resolves every audio and layer time from a **reference** (a marker, an event
edge, another line's edge), writes the `.bak-<ts>` first, and rewrites the beats file's markers so the
gate follows the picks.

```
generated event → src = the pre-graded hero, look none, handle_head = in   (the seek convention)
designed event  → source designed, its own look, no src; the card = role endcard, 2.5 s FULL
native bed      → only when the keeper EARNED its sound; native_audio_from/to mute what it did not
punch-in        → zoom + anchor keeps the wrong thing out of frame without a regen
montage         → COPY delivered spots' events, window them on the disclaimer's word times
```

The genre decides the shape the beats take — ad spot (hook ≤ 2 s → reveal on a marker → product →
turntable + closer → card), film (the hero shot first, the self-revelation at 90 %, no captions, no
card), music video (the track map allocates the whole timeline first; later beats pay by trimming):
[`references/GENRE-GRAMMAR.md`](references/GENRE-GRAMMAR.md). The field contract the finisher reads,
and the plan's time-reference grammar: [`references/EDL-CONTRACT.md`](references/EDL-CONTRACT.md).

❌ A builder with no argparse — `--help` ran a default build and overwrote the live EDL.
✅ `argparse` on every CLI; `.bak` before every write; the same flags reproduce the same file.

A take's own cut inside a keeper's window is a rogue frame — unless the take COMPOSED it: a long generation's
internal shot change the operator kept is part of the keeper. Declare those on the event (`accepted_cuts` +
`accepted_cuts_note`); `edl_check --cuts` and the delivery QC then fail only an undeclared crossing. A number the
plan MEASURED from files (a bed `vol`, a duck, a lip-synced `at`, a loudness target) carries a `derived` block with
its inputs' hashes, and the build fails when an input changed (`EDL-CONTRACT.md` § Derived constants).

**Done when:** the builder prints the timeline, `scripts/edl_check.py` passes — with `--require-endcard` when the
beat list has a card (contiguous `tl`, spans = out − in, files present, windows inside their takes, no short cue) —
no derived constant is stale, and re-running the builder reproduces the EDL.

## 3. Place the sound from the picture

The operator gives placement as **word × time × event** (a word at a timeline second; a line during an event; a line ending just before the
sign-off sfx; a quip's halves on the setup and the payoff). Each becomes a reference, never a number:

- The **narrator chain derives backwards** from the hit: the last line ends ≥ 0.5 s before `HIT`
  (floored to the frame), earlier lines 0.1 s apart; the closer 0.7 s into the turntable; the
  disclaimer ends before the party or a montage window is lengthened. A product quip lands only after
  the product is visible; a quip's halves sit on setup and payoff.
- An **O.S. line** sits at its take time. A **dub** (a line the venue refused) sits on the take's mouth
  shape, native muted from the onset.
- **Carried sound**: when the picture cuts before the sound ends, cut the sound from the take at the cut
  frame and place it as an sfx at the next event (a word's tail carried over the next shot; a tear carried
  into the next cut; a knock a beat earlier with its raps muted).
- **Music** is cut to the marker it ends on; a cue slams in ON the reveal marker, not on the cut before
  it; a bed runs under the turntable and the card; ducks under lines; no bed under the hit; a cue
  shorter than its span just ENDS — cut a longer excerpt. Designed-sound extras (chimes) are opt-in.
- **Captions**: the narrator only, word ranges, no punctuation, never over the card, never two cards on
  one frame; a swapped VO take re-runs the word times for that line only.
- **A lip-synced line** (the picture was generated to that voice) sits where the take's own audio says —
  `{event, take}` by envelope NCC — and is RE-MEASURED whenever its file changes; a carried `at` dubs the shot.
- **Mix constants** (the bed under the voice, the duck) are measured from the client's reference stems when they
  exist and stamped with their inputs; a constant carried across rounds goes stale in silence.

The full grammar: [`references/AUDIO-PLACEMENT.md`](references/AUDIO-PLACEMENT.md).

**Done when:** every VO, sfx, music and layer entry's `note` names the event or marker it derives from,
and the beats file carries an `order`/`vo_ends_before`/`music_*_at` rule for each placement the
operator specified.

## 4. Gate before any finish

```bash
python3 ~/.claude/skills/video-edit-edl/scripts/beat_sheet.py --root <project> --edl edit/<SPOT>-EDL.json
python3 ~/.claude/skills/video-edit-edl/scripts/edl_check.py --root <project> --edl edit/<SPOT>-EDL.json [--require-endcard] --cuts <cutlists.json>
```

`beat_sheet.py` exits 1 on any FAIL — no finish runs on a FAIL, and its printed sheet rides in the
deliverable ask. `edl_check.py --cuts` takes the takes' own cut lists (from `video-take-review`'s
`qc_seed.py`) and fails any window that crosses one (the rogue frames a 1 fps tile could not see) —
except a cut the event declares in `accepted_cuts`, which prints as INFO; `--require-endcard` whenever the
beat list carries a card.
A finish script calls the gate itself before its first stage; a pipeline script per version runs
build → gate → finish → QC and ends on a sentinel line, so a silent partial run cannot be mistaken for a
render.

**Done when:** `BEAT-SHEET PASS` and `EDL-CHECK PASS` on the exact file the finisher will read.

## 5. Revise by parameter, into a new file

A note from the operator or the client is applied as a change to the plan or a builder flag, and the
result is a **new EDL file** (`-v9i`, `-final`); the previous version stands untouched, and an alternate
deliverable is its own EDL with its own audio map and captions.

```
operator-marked frames → they ARE the cut: match them to the take (video-take-review frame_match.py),
                         cut that clip at those frames; no re-derivation, no verification round, no substitute
a trim ("first 0.9 s", "without the first 1/3", "shave 1/4 s off the end") → the window, on the frame
"cut before the heads swivel" → the last STILL frame by motion energy; "just before she trips" → the onset
an insert / a re-order → scripts/edl_insert.py (shifts everything downstream; a spanning cue keeps playing;
                         --replace re-times an existing insert)
a bad short shot → drop it; a better shot in an older version → swap it; "cuts too soon" → lengthen
a new take among the keepers → a hybrid EDL, its cuts mixed in
a missing sound → a placed sfx; a lost word → a dub; the wrong thing in frame → a punch-in
only then → a regen (video-refs-continuity → video-gen-cost-gate), with the approved cut frozen
```

Locate first, then cut: the operator's frames identify the take's own piece in a minute, where
re-cuts and a regen chase a phantom.

**Done when:** the new version is a new file, the previous one is byte-identical, the pipeline ran
through the gate with its sentinel, and "lock these in" placements are unchanged.

## Failure behavior

- A `FAIL` from either gate stops the finish; fix the plan, rebuild, re-gate — never edit the EDL's
  numbers by hand and never run the finisher around the gate.
- A missing keeper (`take: null`) stops the build with the event named; the pick comes from the
  operator, not from the builder.
- A cue shorter than its span, a window past its take, a caption over the card: each is a FAIL with the
  fix named; none is a warning to ship through.
- `FAIL STALE` from the builder → an input of a derived constant changed since it was measured: re-measure the
  constant from the current inputs, then re-stamp (`--stamp-derived`). `--allow-stale-derived` builds anyway and
  prints every stale input — a layout to look at, never a version to finish.
- A window crossing its take's own cut → a rogue frame, unless the take composed that cut and the operator kept it:
  declare it on the event (`accepted_cuts` + `accepted_cuts_note`); never drop `--cuts` to reach a PASS.
- The project tree has no VCS: every writer drops a `.bak-<ts>-<why>` first, and a shipped EDL is never
  the file being edited.

## Scripts

| script | does |
|---|---|
| `edl_build.py --root --plan --out [--beats] [--stamp-derived] [--allow-stale-derived] [--no-lufs]` | the plan → EDL derivation; rewrites the beats markers; stamps and checks the input hashes of every derived constant (a stale one stops the build) |
| `beat_sheet.py --root --edl [--beats]` | the script-fidelity gate; exit 1 on FAIL; prints the sheet |
| `edl_check.py --root --edl [--require-endcard] [--cuts] [--fps]` | the structural read: continuity, files, windows, cues, the seek convention, rogue frames — a crossing the event declares in `accepted_cuts` prints INFO; a VO line with no `source` WARNs |
| `edl_insert.py --root --edl --after --id --take --in --out [--replace]` | insert or re-time an event, shifting everything downstream |
| `trim_for_upscale.py --root --edl --ids [--out-dir]` | cut keepers with handles for a hosted upscale; writes `handle_head` |

## Cross-references

- [`references/EDL-CONTRACT.md`](references/EDL-CONTRACT.md) · [`references/BEATS-CONTRACT.md`](references/BEATS-CONTRACT.md) ·
  [`references/AUDIO-PLACEMENT.md`](references/AUDIO-PLACEMENT.md) · [`references/GENRE-GRAMMAR.md`](references/GENRE-GRAMMAR.md).
- `video-take-review` — the keepers and their windows, the cut lists, `frame_match.py` for an operator's frame.
- `video-finish-qc` — consumes the EDL: upscale, look, master, deliver, and the QC that reads the delivered file back
  against it; `video-finish` — the per-clip order it applies.
- `video-refs-continuity` → `video-gen-cost-gate` — the regen rung, only after the ladder above.
- Handoffs follow `~/.claude/skills/video-production/references/CHAIN.md`.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
