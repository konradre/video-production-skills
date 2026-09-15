# The zoom-out chain — a generated open that lands on real footage

A jump-zoom or drone-style open (far → near) over a place the footage already shows, made from stills, that cuts into the
first live shot without the seam showing. Measured once (an equipment-auction spot, 2026-09-15): four stills, one still
per altitude, $0.20 at the image venue, every still accepted first try, both rasters, the operator's "try it on the
cut-down too" the same evening. The rules below are what made it land; each is the cheap version of a failure the
generated-footage skills already know.

## The rule that decides everything: derive outward from the real frame

The last generated picture must be the first live frame's neighbour, or the cut shows. So the chain starts at the footage,
not at the prompt:

1. **Pick the landing frame** — the first frame of the live shot the open lands on (cut at true display shape, ungraded).
   Both rasters land on the SAME frame; a raster-specific opener (a different wide for the square) is dropped, or the chain
   is generated twice.
2. **Import it into the refs gate as a client-supplied lineage root** (`refs_gate.py --import R-<name> --file … --provenance
   "<clip>, frame at <t>"`), with two or three real wides of the place for the layout (`--import W1…`). Accept each after a
   look (`--accept`).
3. **Generate closest-first.** The first still is the landing frame seen from a little higher and further back (the same
   subjects, the same screen position). Its output becomes reference 1 of the next, wider still; the real frame and the
   wides ride along as references 2–4 so the layout holds. Four steps cover ~7 m → ~30 m → ~100 m → ~300 m.
4. **Keep the subject at one screen position** in every prompt ("the booth truck just above the centre of the frame") so
   the played-back dive reads as one camera; ask for the venue's plain, flat, ungraded colour "exactly like the references"
   so the builder's grade applies to the stills and the footage alike.
5. **Accept each still through the gate before it feeds the next** — the gate records the file's hash, so a re-rolled still
   cannot silently replace an accepted one.

## Cut and sound

- Play the chain far → near as rapid cuts with a small push-in baked on each (a 6–8 % zoom over the hold), accelerating:
  15 / 13 / 12 / 11 frames at 24 fps is 2.125 s. The landing cut IS the first live frame; nothing dissolves.
- Render the stills as 8-bit RGB clips (png codec in a .mov), never 10-bit ProRes: a 10-bit source turned black through an
  ffmpeg `colorlevels` grade and the spot's QC passed it (`video-finish-qc` § near-black).
- The prefix shifts every absolute time in the plan (type cards, the logo, cue edges): derive them from events. A music bed
  that is now too short is re-looped by whole bars so its ending still lands on the card (`video-edit-edl` § 2).
- The voice can enter on the landing cut — the open is music only, the cut lands with the first word.

## Prompt shape (image-to-image, one still per step)

"Zoom out from the first reference photo. The same <subject> and the same <people> now photographed from a drone about
<altitude> up and <distance> behind, tilted down <angle>. <What is visible at that altitude: the rows, the building, the
surroundings.> Keep every element of the first reference in the same place, only seen from higher and further back." plus
a common tail: photorealistic, vertical 9:16, same day and light as the references, flat ungraded colour exactly like the
references, no text, no lettering, no logos, no watermark, nothing invented that does not belong to the place.

The wider the step, the more the venue invents (the surroundings at 300 m are the model's idea of the region); say so in
the delivery note — the client knows what their yard's neighbours look like.

## Failure behavior

- A still that moves the subject or changes the light → re-roll that step only; the accepted steps stay.
- The landing cut visibly jumps → the last still is too far from the real frame: add a closer step, never a dissolve.
- Black or flat frames in the delivered open → the source clip's bit depth against the grade; QC per event (§ near-black).
