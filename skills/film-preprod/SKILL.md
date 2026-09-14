---
name: film-preprod
description: >
  Pre-production of a SHORT FILM or a MUSIC VIDEO: the veto map from whoever judges it, the story written
  end-first (the seven steps in seconds, a subworld per beat), premises ranked twice, the hero shot generated
  first, the track map measured before the gen map, the shared pre-production core (partitions on continuity, the
  script diff) and contest hygiene. Use when a film or a music video is briefed, a premise or format must be
  chosen, a beat sheet must be written or checked, a track must be mapped, or contest rules must become a
  checklist. Triggers — "story beats", "the seven steps", "the premise", "which format, live action or animation",
  "the hero shot", "self-revelation", "track map", "cut to the drop", "the jury", "the veto map", "the contest
  rules". Not for an ad campaign's brief or cost plan — use ad-spot-preprod. Not for the reference set — use
  video-refs-continuity. Not for the prompt itself — use video-prompt-dialects. Not for the cut — use
  video-edit-edl.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3*), Bash(ffmpeg*), Bash(ffprobe*), Bash(ls*)
---

# Film Pre-production

A short is not a small feature: the corpus that governs features assumes 120 pages and fails at
5 minutes. Four of its assets transfer once the unit is seconds; the rest is replaced by two rules
that generated video imposes — **the hero shot decides everything** and **premise selection is a
pipeline decision**. A music video adds a third: **the track is measured before a beat is written**.

## 1. Read the judges, write the veto map

Whoever decides the film's fate — a jury, an audience, a client — is researched first: their own
work, their stated taste, the archetype their choices converge on, and the one beat that resolves it.
Two tables before anything else: the **veto map** (asymmetric — one strong aversion outweighs three
mild positives; constraints, not preferences) and the **compliance table** against the rule set. The
convergence is your synthesis and is recorded as such; the vetoes are sourced and carry the weight.
[`references/JURY-AND-PREMISE.md`](references/JURY-AND-PREMISE.md) § 1.

**Done when:** both tables exist with a source per row and a ✅/⚠/⬜ per rule.

## 2. Write the end first, then the characters

The self-revelation is one paragraph written before any beat; every beat is derived backward from it
and it is held to 90 % (an early anagnorisis removes the moral jeopardy for the rest of the film).
Each principal carries the four slots (lie · want · need · ghost), an arc from the taxonomy with its
state chain, the 3-question classifier's answers, and the **arc-delta**: the same action at 0:00 and at
the climax with the motive inverted. A short is a two-hander. Sympathy before flaw in the first scene.

```bash
python3 ~/.claude/skills/film-preprod/scripts/arc_check.py --cast story/cast.json
```

[`references/STORY-METHOD.md`](references/STORY-METHOD.md).

**Done when:** the self-revelation paragraph exists, `ARC-CHECK PASS`, and the two principals'
chains are named.

## 3. The beat sheet on the Pratt axis, in seconds

```bash
python3 ~/.claude/skills/film-preprod/scripts/beat_calc.py 300 --ceiling <the cap, read from the vendor> --md story/beats.md
```

Seven steps (Weakness & Need · Desire · Opponent · Plan · Battle · SELF-REVELATION at 90 % · New
Equilibrium), each with what happens and its **subworld** (a per-beat environment brief — environments
are built before shots); the 22-step spine only as a checklist. A beat longer than the venue's clip
ceiling is designed as clips cut on a blink or a caught breath — checked BEFORE the beat is written. The ceiling is READ from the vendor's schema, estimator or error,
never from a take already run (`video-production/references/PREPRODUCTION-CORE.md` § 2).
For a music video the anchors are the track's hits (§ 6).

**Done when:** every beat has a time, a subworld and a clip count, and the self-revelation sits at
90 %.

## 4. Choose the premise twice

Blind competitor premises from a different model family, one assigned divergence axis per run, the
default metaphors banned, the laziest route capped at one — never fed your own idea. Then two
rankings: **story** (against the veto map and the archetype) and **execution** (does the world absorb
the tool's artifacts as diegetic behaviour, or fight them? night with one practical source, landscape,
paint: forgiving; kitchens, handwriting, water, machinery, scale, layered voices: exposed). The two
reads are allowed to disagree, and **the disagreement is the operator's decision**, with each premise's
objection recorded beside its rank.

```bash
python3 ~/.claude/skills/film-preprod/scripts/premise_rank.py --premises story/premises.json --ban "mirror,dream,clock"
```

**Done when:** the ranking table is in the project with the disagreement (if any) stated as a
numbered question to the operator.

## 5. The hero shot, the format, the look and the sound

Identify the shot the film is built around; storyboard it first, generate it first, build outward;
if it does not land the film does not exist. It decides the **format**: a photoreal face drifts over
a held close-up, a stylised one holds — painterly figuration with photographic camera language, never
the house style of the most animation-literate judge. Generate at 480p only and reconstruct as ONE
pass on the locked cut (an aesthetic decision: the softness reads as painted, not rendered). Light the
story's own source, under-lit, no strong backlight, restrained camera, composition over coverage; let
the mix crest with the push-in; never a voice-over that explains, never irony, never a sanitised
ending. Runtime is set by the story. [`references/HERO-SHOT-AND-FORMAT.md`](references/HERO-SHOT-AND-FORMAT.md).

**Done when:** the hero shot is storyboarded with its clip plan, the format is decided in writing
with the hero shot as the reason, and the look/sound rules are in the beat sheet's header.

## 6. Music video: the track map before the gen map

```bash
python3 ~/.claude/skills/film-preprod/scripts/track_map.py --audio audio/track.wav --out analysis/features.json
```

Duration, BPM, bar, 8-bar phrase, the section table and **the hits everything cuts to**, measured
from the audio; then the whole timeline allocated to generation windows in a gens table — later beats
are placements paid for by trimming the loosest stretch, never appends; generation order is
dependency-bound; the edit is locked before finishing. Characters told apart by colour, face and
outline only (no fine markers at 480p), human in manner never in movement; a species comes from
reference sheets, never from text; the reveal is never pre-loaded; a look plate per light context, mapped
to the shot list before it is generated; the pre-flight gate on every prompt.
[`references/MUSIC-VIDEO.md`](references/MUSIC-VIDEO.md).

**Done when:** the track map and the gens table cover every second, each beat sits on a hit, and the
generation order is written.

## 6b. The pre-production core — before the first reference or prompt

[`video-production/references/PREPRODUCTION-CORE.md`](../video-production/references/PREPRODUCTION-CORE.md) runs here for a
film and a music video exactly as for an ad: the beat sheet or the track map rewritten as `beats.json` first, the
generator's cap read from the vendor, the beats partitioned on CONTINUITY — one generation per run of beats that must
hold the same people, objects, setting and look, within the cap — dialogue or lyrics timed before any duration is fixed,
and `script_diff.py` both ways against the film's script or lyric sheet where one exists. Every split between
generations is a join that gambles on consistency.

**Done when:** `SCRIPT-DIFF PASS` on the beats and the shot list, the cap in the header with its source, and every
partition row quoting the lines it serves.

## 7. Contest hygiene (only when entering one)

Two clocks; lock before publishing; on-platform generation only (no external AI upscale, interpolation,
relight, or a NLE's neural tools); ALL audio generated, in every WIP cut too, with a manifest; no real
likeness or voice; no political or religious statement; retention; the submission checklist.
[`references/CONTEST-HYGIENE.md`](references/CONTEST-HYGIENE.md).

**Done when:** the disqualifier checklist is ticked in the project before the first WIP publish.

## Failure behavior

- `ARC-CHECK FAIL` → the character sheet is fixed before a beat is written; a beat sheet never
  compensates for a missing Lie.
- The two premise rankings disagree → a numbered question to the operator, never a tie-break by
  arithmetic.
- The hero shot fails at the venue's ceiling or in its first generation → the beat is redesigned as
  two clips, or the format changes; the film is not built around a shot that does not land.
- A contest rule turns out stricter than read (the audio asymmetry, the WIP reach) → the checklist is
  amended and every published cut re-verified.

## Scripts

| script | does |
|---|---|
| `beat_calc.py <seconds> [--ceiling] [--anchors] [--md]` | the 7-step sheet in seconds with subworlds and clip counts |
| `arc_check.py --cast` | four slots, arc chain, classifier consistency, the arc-delta, the two-hander |
| `premise_rank.py --premises [--ban]` | story vs execution rankings, hygiene of the blind set, the disagreement |
| `track_map.py --audio [--out]` | BPM, bar, phrase, section markers and the hits, from the audio |

## Cross-references

- [`references/STORY-METHOD.md`](references/STORY-METHOD.md) · [`references/JURY-AND-PREMISE.md`](references/JURY-AND-PREMISE.md) ·
  [`references/HERO-SHOT-AND-FORMAT.md`](references/HERO-SHOT-AND-FORMAT.md) · [`references/MUSIC-VIDEO.md`](references/MUSIC-VIDEO.md) ·
  [`references/CONTEST-HYGIENE.md`](references/CONTEST-HYGIENE.md).
- `ad-spot-preprod` — the ad-campaign sibling; `video-refs-continuity` — the reference kit the subworlds
  become; `video-prompt-dialects` — the pre-flight gate; `video-finish-qc` — the one-pass reconstruction
  of the locked cut.
- Handoffs follow `~/.claude/skills/video-production/references/CHAIN.md`.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
