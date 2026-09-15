---
name: ad-spot-preprod
description: >
  Pre-production of an AD campaign from the client's brief: the format and tiers, the client's script saved
  verbatim as the SSOT, the brand kit and assets, the global spec and standing rules (designed product and text,
  the wipe, the fill SKU-locked), the asset bible and kit, the shared pre-production core (partitions on
  continuity, the script diff), the risk register and the cost plan. Use when a campaign or spot is briefed, a
  client script arrives or changes, the next spot must be chosen, or a shot list or cost plan is needed. Triggers
  — "the brief", "the client's script", "shot list", "which spot next", "what does the script call for", "cost
  plan", "kit for this SKU", "risk register", "the alternate spec", "a UGC spot", "creator-style ad". Not for a film or a music video — use
  film-preprod. Not for the reference set or the refs gate — use video-refs-continuity. Not for the cost line and
  the submit — use video-gen-cost-gate. Not for the beat gate or the EDL — use video-edit-edl.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3*), Bash(ls*)
---

# Ad Spot Pre-production

Nothing generates before the plan exists on paper: the client's words verbatim, the decisions with
their owners, the kit, the scenes, the cost. Every rule here is the price of a generation that was
made without one. The plan is a set of files in the project, not a memory.

**What varies.** The vertical format, the tiers, the sign-off structure, the wipe, the two-state grade and the product
rules are an ad campaign's defaults: a spot with no product on screen drops the product rules, the platform sets the
aspect and the safe zones, the vendor sets the clip cap, and the client's brand kit sets the sign-off. The client's text
as SSOT, the continuity partitions and the diff do not move — `video-production/references/WHAT-VARIES.md`.

## 1. Decide the format and the tiers

Standalone vertical spots, never scene bundles — compiles come free out of standalones and the reverse
is not true; three tiers from one build (the paid spots · the capper montage · the hero cut); an intro
scene that framed a long film is re-cut to stand alone; "we need more" goes to alternate hooks, not
runtime; "UGC" in a brief is checked against what is actually described.
[`references/INTAKE.md`](references/INTAKE.md) § format.

**Done when:** the tier table exists with runtimes, and the client has endorsed the format in their
own words.

## 2. Take in the script, the brand kit and the assets

- The client's text is the SSOT: read END TO END, saved verbatim beside the beats
  (`prompts/<SPOT>-SCRIPT-client.txt`); a pasted block is the SSOT; a full alternate spec is a NEW spot;
  a one-line note is a version bump. The derivation may add framing, coverage and timing — never a
  character, a beat or a line; additions are numbered cost lines with "no" as the default.
- The brand kit: the audio signature, the fixed line (locked), the variable line (a pile to cherry-pick
  by gag fit, never reused across spots), the CTA — the triad "what it is, what it does, where I get it".
  The outro is decided once.
- Assets: packaging photos, **FLAT artwork** (photos are wrapped and rounded), the pieces on white (the
  fill per SKU is read off them), full-resolution originals; a cast ref that resembles a public figure
  is re-rolled.
- Rulings from the client, once: language and platform risk (risqué first, fallbacks parked), any
  script question as ONE concise ask; rating, wardrobe and set where the script is silent are the
  operator's. Every decision logged with WHO and what would reopen it.

**Done when:** the script file, the brand-kit table, the asset checklist and the decision log exist,
and every open question is a single numbered ask.

## 3. Fix the global spec and the standing rules

9:16, safe zones, the two-state grade, the lens, the music arc (the before cue → the wipe → the after cue → the
closing bed), captions burned in, the venue's clip ceiling, the true-size framing rule. The seven
standing rules — the product and its pieces DESIGNED never generated; text never generated; the
explicit frame never framed; the wipe in every spot; B plates from the A keeper's frame 0; the fill
SKU-locked and named on every shot; the easiest spot first and knowing what it proves — and the sign-off
structure (the variable line's halves bracket the audio signature; the locked line; the CTA).
A spot with no product, card or wipe on screen (a UGC testimonial) carries only the rules its script invokes —
the scaffold's `--spot-type ugc` drops the rest. [`references/GLOBAL-SPEC.md`](references/GLOBAL-SPEC.md).

The grade is named here, once, and it starts from the look library's cube for the genre (`ads-clean` for an ad) — also when
the footage is the client's own: the operator picks it from a frame sheet of the project's frames
(`video-finish-qc/scripts/look_sheet.py`) before the first delivered version. A hand-written level chain is a deviation that
needs a reason; two of them stood for ten hours on a documentary spot before the operator asked (2026-09-15).

**Done when:** the global spec section is written once for the campaign, names the look the operator picked from the sheet,
and every later spot cites it.

## 4. Build the asset bible, the kit and the beats — then the shot list

```bash
python3 ~/.claude/skills/video-production/scripts/script_diff.py --script prompts/<SPOT>-SCRIPT-client.txt prompts/CLIENT-NOTES-*.txt --beats prompts/<SPOT>-beats.json --elements ELEM-FILL-<colour>
python3 ~/.claude/skills/ad-spot-preprod/scripts/shotlist_scaffold.py --beats prompts/<SPOT>-beats.json --out prompts/r2v/<SPOT>-SHOTLIST.md --spot-type product|ugc --max-duration <read from the vendor> --sku "<SKU>"
python3 ~/.claude/skills/video-production/scripts/script_diff.py --script prompts/<SPOT>-SCRIPT-client.txt --beats prompts/<SPOT>-beats.json --shots prompts/r2v/<SPOT>-SHOTLIST.md --max-duration <the same cap>
```

- The venue is chosen by a costed Phase-0 test on the HARDEST shots (a photoreal reference call, a
  lipsync line, the most exposed premise), cost per keeper as the unit — never by argument, never on the
  easiest spot.
- The asset bible: characters (one entry per role, locked details, a count check against the script),
  products, A/B locations, recurring elements with their owners.
- **The pre-production core runs here, in its order** (`video-production/references/PREPRODUCTION-CORE.md`):
  `beats.json` from the client's script FIRST, never from a prior cut; the generator's maximum duration READ before
  the shot list exists and written in its header; the script partitioned on CONTINUITY, never on shots — one
  generation per partition within the cap; with voice-over, the lines timed before any duration is fixed.
- Then the per-spot shot list from the scaffold (`--spot-type product` for a product spot, `ugc` for one with no
  product, card or wipe): the method line, the cap, the kit table, the room geometry pin, the cast (closed after
  the first keeper), the PARTITIONS with the script lines each serves in full, the audio plan, the acceptance
  rows, the submission commands. Ids are stable. The next spot is the one that reuses the most accepted assets;
  the capper draws from the CURRENT accepted spots.
- `script_diff.py` (core § 5) runs before the first prompt, both ways; in an ad campaign `--elements` also fails a
  piece-bearing beat without its element id — the one that changes later. [`references/SHOTLIST-CONTRACT.md`](references/SHOTLIST-CONTRACT.md).
- **Existing footage** (the client supplies the picture): the same core with the generation stages declared not applicable,
  with the reason — the sources probed for their DISPLAY shape and transcribed whole first, the beats from the client's text
  or the brief's message lines, the shot list as a keeper list with a microphone-position column, the scaffold as
  `--spot-type ugc` with the gens table, the refs gate and the fill marked N/A in the header:
  [`references/INTAKE.md`](references/INTAKE.md) § Existing footage.
- **A UGC / creator-style spot** (`--spot-type ugc`, phone-shot or generated — a person talking to the camera): the grammar
  is [`references/UGC-GRAMMAR.md`](references/UGC-GRAMMAR.md) — the intake axes (AOV band, funnel stage, platform, real or
  synthetic persona, phone-shot or generated), the hook core, the archetypes, the beats by duration with REAL proof
  composited at the demo beat, the delivery and caption rules, the variant matrix, the four artifacts; the script carries a
  disclosure column, and the compliance path is chosen at intake ([`references/RISKS.md`](references/RISKS.md) § UGC
  compliance). A synthetic persona presents a demo, never a testimonial.

**Done when:** `SCRIPT-DIFF PASS` on the beats AND on the shot list (`--shots`), the generator's cap is in the
header with its source, every section is filled, and every partition row quotes the script lines it serves.

## 5. Write the risk register and the fallbacks

Filters (route around, never rewrite the joke), moderation on a word (the dub), lipsync (decided per
line), transformation geometry, text in frame, packaging fidelity, likeness, platform copy risk (the
fallback register built with the originals and parked), fill continuity, venue cost at the campaign's
shot count. Open decisions numbered with an owner and a closing trigger.
[`references/RISKS.md`](references/RISKS.md).

**Done when:** every risk names the mitigation that is already in the shot list, and the fallback
register lists what each fallback costs.

## 6. Cost the rounds and hand over

```bash
python3 ~/.claude/skills/ad-spot-preprod/scripts/cost_plan.py --scenes prompts/r2v/<SPOT>-scenes.json --rate 2.5 --extra "stills:0.05" --extra "VO 954 chars:0.12"
```

Rounds by dependency (what runs in parallel, what waits for a pick), the spot total clean and with one
re-roll per scene, stills and VO as their own lines — as **numbered questions with the cost inline**,
one GO per round. The client-facing shot list ships as a designed PDF when asked. Then the hand-off:
`video-refs-continuity` builds the references the first scene needs; `video-gen-cost-gate` submits.

**A designed device gets a CREATIVE CHECKPOINT before the full build.** When the spot's idea rests on something designed —
type over footage, an animated opener, a card system — the first round is a short motion test of that device (a few
seconds, one raster, the real footage and the real words) plus the typeface as an operator PICK from rendered options (the
message line set in three to five candidates on the project's own frames), before polish, before the second raster, before
any cut-down. A written standard ("brand-appropriate, licensed") does not replace the pick: on one job the operator's first
look at the device in motion was the fourth full build, and every version to that point was rejected on the typeface and
the device together (2026-09-15). A campaign whose kit is already accepted skips this.

**Done when:** the cost lines are answered, the first round's references are listed by name, and the
plan is saved in the project with its path in the ask.

## Failure behavior

- A script line quoted in a beat that is not in the client's text → FAIL; the beat is rewritten from
  the text, never the text from the beat.
- A client note that contradicts the saved script → the newer client text wins; save it, diff, rebuild
  the beats, and say what changed.
- A venue test that refuses the reference or the premise → the method changes (references for
  everything but the character; the line in post audio), the creative rulings do not.
- A stale cost in a decision → re-cost before quoting; never cite an old figure as a reason.
- A sentence or a partition split across rows with no recorded reason → one generation, or the reason written in
  the row (consistency not required across the split, or the action outruns the read cap).
- A shot map taken from a prior cut's scene detection → discarded; the beats and partitions are rebuilt from the
  script.

## Scripts

| script | does |
|---|---|
| `video-production/scripts/script_diff.py --script --beats [--cover --cover-section] [--elements] [--shots --max-duration]` | quotes token-exact against the client's text (FAIL), uncovered sentences, unnamed fills, and the segmentation gate — a sentence or a partition split across rows (FAIL); `--selftest` |
| `shotlist_scaffold.py --beats --out [--spot-type product\|ugc] [--max-duration] [--sku]` | the per-spot shot list skeleton — the cap in its header, partition rows with the script lines in full |
| `cost_plan.py --scenes [--rate] [--extra]` | rounds by dependency, the numbered cost lines, clean and worst case |

## Cross-references

- [`references/INTAKE.md`](references/INTAKE.md) · [`references/GLOBAL-SPEC.md`](references/GLOBAL-SPEC.md) ·
  [`references/SHOTLIST-CONTRACT.md`](references/SHOTLIST-CONTRACT.md) · [`references/RISKS.md`](references/RISKS.md).
- `video-edit-edl` — the beats contract and the gate; `video-refs-continuity` — the reference set the plan
  names; `video-gen-cost-gate` — the cost line form; `designed-elements` — the kit's designed pieces;
  `client-rounds` — what happens when the client's notes come back.
- Handoffs follow `~/.claude/skills/video-production/references/CHAIN.md`.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
