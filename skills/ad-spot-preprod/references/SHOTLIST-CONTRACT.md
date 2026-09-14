# The shot list — the asset bible, the kit, the partitions, the rounds

## Pipeline order (dependencies run downhill — skip a step and you redo everything below it)

```
1. client assets in ........ packaging, pieces, flat art, the script verbatim; approved client images IMPORTED with provenance
2. venue selection ......... a Phase-0 test on the HARDEST shot (a reference call, a lipsync shot), costed — never on the easiest
3. the display plate ....... feeds every product beat and card (designed)
4. character sheets ........ prose-born in the first scene, or the client's approved photos; refs CUT FROM ACCEPTED TAKES; cast closed after the first keeper
5. "A" location plates ..... the before-state rooms, camera pinned
6. "B" plates .............. generated FROM the A keeper's frame 0 (image-to-image), the same camera
7. beats.json .............. the script as code (video-edit-edl § beats) — BEFORE the shot list, never from a prior cut
8. the generator's cap ..... the maximum single-generation duration, READ from the vendor, written in the shot list's header
9. the partitions .......... the script partitioned on continuity; each partition ONE generation within the cap; diffed against the script by code, both ways
10. generation ............. partition by partition, through the refs gate, the reference dress rehearsal and the cost line (video-refs-continuity → video-gen-cost-gate)
11. post ................... walls, drifts, card, VO, captions, grade (designed-elements · spot-audio-assembly · video-finish-qc)
12. pickups ................ short generations only where the long take left a gap or a defect, or where no accepted footage exists (the capper)
13. assembly ............... spots → capper → hero cut
```

The established method: the whole scene generated as one continuous clip on the chosen venue,
references for everything that is not a character (the room plate, the product sheets, the size crop)
plus character refs cut from accepted takes; the dialect decides how a line is written
(`video-prompt-dialects`). The per-shot img2vid model (one still → one clip, ≤ 4 s shots) is the
fallback shape, not the default.

## Partition first, count shots never

The shot list is DERIVED from continuity partitions of the script. A partition is a maximal run of beats that must hold
the same people, identity-bearing objects, setting and look, and it is ONE generation whenever it fits the generator's
read cap. Its reference set is exactly what recurs inside it — each person, each object that keeps its identity, the
setting, the look plate — never a standing kit carried across the spot and never a per-shot improvisation.

- **You buy a long generation for consistency, not for cutlessness.** The same faces, wardrobe, room, light and
  performance register are free inside one generation and a gamble between two; a cut the model composes inside a
  generation carries consistency by construction, where a cut an editor makes between generations gambles on it.
- **A short generation is a tool, not a failure** — after the long take exists (a gap, a defect), or wherever
  consistency across shots is not required at all: another room, another time, another scene.
- **A shot boundary is a claim that the action stops.** The script decides where it stops; the cap decides whether the
  list may stop there. `script_diff.py --shots` FAILS a sentence or a partition split across rows unless the row
  records `split: <why>`.
- **The cap is read, never inferred.** From the vendor's schema, estimator or error — never the longest take a production
  happened to run (`video-gen-cost-gate` § venues).
- **A prior cut is evidence about defects, never a source of structure.** Scene detection on a rejected deliverable
  reconstructs the previous producer's segmentation, mistakes included, with the authority of a measurement.

## Venue selection is a test, not an argument

The venue is settled by one costed test each on the hardest shots — a photoreal character sheet as a
reference (accepted or refused decides whether the sheet pipeline can run), a lipsync line, the most
filter-exposed premise — on identical inputs across the candidates, with the cost per keeper (not per
second) as the unit. The easiest spot passes on every model — passing it proves the chain runs, not
that the hard parts work. Record accepted/refused, the rewrite behaviour, the filter behaviour and the
cost at the campaign's shot count; a stale cost case is re-costed before it is quoted.

## The asset bible

| section | contract |
|---|---|
| characters | one entry per role with ID, the spots they appear in, the locked details (a hat, a sash, a garment state); a count check against the script |
| products | every SKU with its photos, its flat art, its fill colour, its spots |
| locations | A/B pairs named; the B generated from the A; single-state rooms |
| recurring elements | the wipe, the fills per SKU, the composited text pieces, the card, the audio signature — each with its owner (post layer / designed / audio) |

## The per-spot SHOTLIST.md (one file per spot, `shotlist_scaffold.py` writes the skeleton)

1. **Method line**: refs gate, cost gate, partition-first, the dialect.
2. **Script pointer**: the client text verbatim beside it; the derivation rule; **the generator's maximum duration
   with its source**.
3. **The kit table**: reused (from the accepted spots) vs to build — per SKU for a product spot (product sheet,
   exact-silhouette sheet, size crop, turntable, drift, wall, card + audio signature, cues, the B plate); for a spot with
   no product, card or wipe (`--spot-type ugc`) the people, the setting and the bed — plus, for every spot, the look plate
   per light context, the reference dress rehearsal per partition and the voices — with status.
4. **Room geometry** pinned for every partition (re-pinned from the first keeper's frame 0 after the pick).
5. **Characters** in prose (age, hair, wardrobe) or from the client's approved photos, refs cut from keepers, the cast CLOSED.
6. **Partitions** — `| partition | beats | events | duration | the script lines it serves | mode | refs (@Image order) |
   file | credits/seed | split |`; one row = one generation; the script lines quoted IN FULL; ids STABLE (the montage
   list and the pickups cite them; never renumber); action verbs and cast per row; a row that splits one action says
   why in `split`.
7. **Rounds and cost** by dependency level (`cost_plan.py`): what runs in parallel, what waits for a pick;
   the spot total clean and with one re-roll per partition; stills and VO as their own lines.
8. **The audio plan** against the gens: the VO lines TIMED before the partition durations are fixed (a sum that hits the
   runtime is not a timing); which line rides where; the explicit line in post audio; the wipe marker and the audio
   signature on the card (product spots).
9. **Acceptance** rows per take, row 0 = geometry/continuity, then consistency across every composed cut (`video-take-review`).
10. **Submission** commands per partition, with the ledger record before polling.

STATUS tick-boxes are not kept — the delivery table and the resume block carry status.

## Choosing the next spot and the capper

The next spot is the one that reuses the most accepted assets. The capper is a montage over the
CURRENT accepted spots' EDL events (copied, windowed on the disclaimer's word times), one new scene, a
product lineup; new generations only where no accepted footage exists; its runtime vs the client's
target is flagged once.
