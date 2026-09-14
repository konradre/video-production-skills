# Cost and GO — the protocol

## The standing rule

*Show a cost breakdown and get explicit operator confirmation before any generation call; every leg
dry-run by default; `--go` is what spends.* It holds a music video near $5 across ~40 paid images
despite wasted attempts, and it holds a multi-spot campaign inside one monthly plan. The amount does not
matter — a still of a few cents is asked for like a thirty-credit seed.

**One price table.** Every rate lives in [`VENUES.md`](VENUES.md). A price written anywhere else — here, in a
SKILL body, in a cost plan — is a pointer to it; when two figures disagree the table wins, and the other figure
is fixed the same day.

## The ask

```
1. S02-G4 (the reaction beat): omni_reference · 480p · 8 s · 3 seeds = 60 cr (480 → 420). GO?
2. The bridge still first ($0.05), then 2 seeds × 5 s = 25 cr. GO on both, or the still only?
REFS-GATE PASS  … (the table, verbatim)
refs @Image1 = S02-ROOM-post · @Image2 = S02-FRIEND-ref · @Image3 = PRODUCT-sheet · start = S02-G4-start
rehearsal still: startframes/S02-G4-rehearsal.png — identity, wardrobe, room and light read against the set
```

- Numbered plain questions, one decision each, the cost and the balance inline, the full path of any
  file the operator must look at — in the asking message, every time.
- The cost line the operator echoes back is the arithmetic: `1 × A1 + 2 × F2 = 40 cr`.
- What is FREE is named as free (a keeper frame as a reference; an edit-only rebuild; whispering the
  takes; the local upscale after approval).
- A refunded or refused batch is resubmitted inside the original GO; anything else is a new ask.

## The pre-GO table — one row per correction that cost credits

| row | why it is a row |
|---|---|
| refs present AND uploaded for this target; a start image with its own accepted record | a plate generated without the product sheet buys a round of wrong-shaped pieces |
| every cited reference registered to its file, unchanged since acceptance, and accepted for the role it plays | a correctly named, uploaded reference showing the wrong person, garment or room passes a name check and burns the batch |
| the reference dress rehearsal read — one still from the SAME set, its path in the ask (refs-only calls; batches over ~30 cr) | in reference-driven generation an absent or wrong reference does not degrade the shot, it invents a different one at full price |
| the generation is a whole continuity partition within the vendor's READ cap; its negatives scoped to its length | one continuous action split into separate generations paid three times and shipped two seams |
| every noun and action traces to the script or the ledger; nothing invented | an invented character or beat costs several gens before it is caught |
| the state at frame 0 = the previous shot's last state (nothing raining before the burst; no second bang after it) | a continuation that restarts the event is a rejected batch |
| cast closed in words; the room ref carries them; each named character once | a different audience, or the same person twice, on the next seed |
| the reaction faces its cause; the line-deliverer faces the camera, never the lens; every eyeline a target | a line delivered facing away from its cause is a rejected batch at full price |
| the door sentence copied from the geometry record | the cast swivels to the wrong wall |
| anatomy per person at 3× on the start image | a double arm in the still is a double arm in every seed |
| faces clear ~60 px of face height in the generator's native raster (measured at 480p) — a FLOOR, never a target; a face that carries the beat is framed well above it (`video-prompt-dialects` HOUSE-TEMPLATE § The pre-GO read) | faces the generator cannot draw come back distorted; a face just over the floor came back under-rendered and was rejected |
| light named in the prose has its look plate cited under a look-only role | one grade sentence in ten prompts and no plate behind any of them; the client rejected the light first |
| product size pinned by an in-world crop; shape by the sheet, in EVERY scene that shows it | pieces 2–4× too big, twice |
| garment text pinned with the string or pinned blank | garbled lettering on an item that conventionally carries text |
| dignity: hands high and visible, nobody left unconscious under an effect, no hand cropped at the waist by the frame's lower edge — the brand's standards and the genre's tone set the bar | a seed the client cannot be shown |
| a named state that keeps failing gets a framing where it cannot appear | seven seeds of the same defect |

The checks are a TABLE in the ask, not lessons in a document, because the question after a wasted gen is
always the same: what in the workflow failed to communicate the need to check this first?

## The reference dress rehearsal — cents before credits

In reference-driven video the references carry every claim the prompt makes about who these people are, what they
wear, what room this is and how it is lit; with no start frame pinning the take, an absent or wrong reference does not
degrade the shot — it invents another one at full price. So before any refs-only call, and before any batch over
~30 cr on any mode, ONE still is generated from the SAME reference set with a condensed prompt at the clip's aspect
(`gen_stills.py`, the model's rate in `VENUES.md`) and read for identity, wardrobe, setting and look — and for
COMPETING references, an older plate or a stray look the shot does not depend on. Its path rides in the cost line: the
operator approves a spend against a seen still, not against a description. A rehearsal still is read and set aside;
it becomes a start image only by passing the gate's acceptance for that role. The asymmetry behind the rule, from
one rebuild: its stills cost $0.15 in all and its video 357.5 cr, one 20 s seed alone 50 cr.

## Budget-final rules

- Once the budget is final, a seed that meets every named constraint goes forward; the free steps never
  wait for a GO; a residual doubt (a fleck in the mouth, a ring on one hand) goes into the delivery note
  with its frame time. A re-roll is offered only if the operator raises it or the seed fails a NAMED
  constraint.
- Tight budget ⇒ regen one seed at a time, checked before the next.
- Attempts per keeper is the real cost — instrument it (the ledger counts seeds per accepted take);
  estimators are pinned to the last real invoice, never to a published rate alone (estimators under-shoot
  their first invoices).

## Free before billed — the order of spend

disk (existing takes: whisper them for the words, RMS-scan for the onset; keeper frames as refs; an
edit-only rebuild ≈ 6 min and zero credits) → a still (cents — `VENUES.md`) → a seed (12.5–75 cr). Before ANY
billed regeneration, search what is already on disk: a word the client wants spoken is often already in most of
the existing takes.

## What is never bought

- A test at video resolution; a 1-s upscale smoke slice is the one exception, measured once per route.
- A second submission of a billed job.
- A gen against an unaccepted still, a still without the sheet, a prompt with an unruled subject.
- A long refs-only generation on a reference set no rehearsal still has read.
- A re-roll to chase a defect the operator has not named.
