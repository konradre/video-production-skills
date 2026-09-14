# The pre-production core — what every genre runs before the first reference or prompt

Each pre-production skill owns its genre's front half: `ad-spot-preprod` the format, the brand kit and the global spec;
`film-preprod` the veto map, the end-first story, the premise, the hero shot and the track map. What follows holds for
every genre and runs, in this order, before the first reference, still or prompt. Each step is the price of a
generation that was made without it.

## 1. The beats come from the SSOT — never from a prior cut

The SSOT is the client's script (ads), the film's script or beat sheet (film), the track map and its lyric sheet (music
video). It is rewritten as `prompts/<SPOT>-beats.json` (`video-edit-edl` § 1) before any shot list exists. A rejected
deliverable is evidence about DEFECTS, never a source of STRUCTURE: scene detection on it reconstructs the previous
producer's segmentation, mistakes included, with the authority of a measurement.

## 2. The generator's cap is read before anything is split

The maximum single-generation duration is read from the vendor's own schema, estimator or error — never from the longest
take already run — and written in the shot list's header with its source (`video-gen-cost-gate` § 1). Unread, the cap is
UNKNOWN and no action may be split.

## 3. Partition on continuity, never on shots

A continuity partition is a maximal run of beats that must hold the same people, objects, setting and look. It is ONE
generation when it fits the cap, with its reference set derived from what recurs inside it: each person, each
identity-bearing object, the setting, the look plate for its light. Shorter generations come after — to cover a gap or
fix a defect in the long take — and wherever consistency across the split is not required (another room, another
time). A shot boundary claims the action stops; the SSOT decides where it stops, the cap decides whether it may.
Consistency is free inside one generation and a gamble between generations, and it is what an audience reads as
believability (house rule, 2026-09-13). A film's clip plan and a music video's gens table are partitioned the same
way before either is generated.

## 4. Spoken lines are timed before durations are fixed

With voice-over, dialogue or lyrics, the lines are timed first (`spot-audio-assembly` `vo_word_times.py`, or the track
map's measured hits); durations that sum to a runtime target are a target hit, not a timing.

## 5. The SSOT diff — by code, both ways

```bash
python3 ~/.claude/skills/video-production/scripts/script_diff.py --script <the SSOT text> [<later notes> …] --beats prompts/<SPOT>-beats.json [--cover-section START END]
python3 ~/.claude/skills/video-production/scripts/script_diff.py --script <the SSOT text> --beats prompts/<SPOT>-beats.json --shots <SHOTLIST.md or scenes.json> --max-duration <the cap as read>
```

A quoted line that differs from the SSOT by ANY token FAILS (an added article once passed a 60 %-overlap rule); a beat
carrying the operator's `ruled` note turns an approved variant into a WARN. A sentence of the SSOT that no beat covers
is a beat the list forgot. A sentence or a partition split across rows FAILS unless the row records why — consistency
not required across the split, or the action outruns the cap. `--elements` adds the product check an ad campaign needs.

**Done when:** `SCRIPT-DIFF PASS` on the beats and on the shot list, the cap in the header with its source, and every
partition row quoting the SSOT lines it serves in full.

## 6. Then the references

The reference set is built per partition (`video-refs-continuity`), one still from that set is read before any
expensive call (`video-gen-cost-gate` COST-AND-GO.md § The reference dress rehearsal), and the project's values for
every axis that differs from the defaults are on disk ([`WHAT-VARIES.md`](WHAT-VARIES.md)).
