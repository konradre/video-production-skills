# QC — the classes, in priority order

Read the DELIVERED render (a reduced preview reads motion loose). Every scene gets a line, "OK" included. Record each
finding as it is found, in the file, with the instrument's number beside the frame time — a pass that writes at the
end loses everything to a crash.

| # | class | how | severity |
|---|---|---|---|
| 1 | readability and occlusion | text under the caption band or off the frame; type under the floor (22 px at a 720-px short side, scaled); light text on a light element | frames at every beat | high when unreadable |
| 2 | beats | an element's entrance against its beat (−0.2 … +0.1 s); a sentence with no visible change | frames at beat −0.2, 0, +0.1, +0.3 s; a tile on every beat first: `video-take-review` `contact_sheet.sh <render> 6 1 --beats <p>/timeline.json` | medium; high for a sentence with no change |
| 3 | facts and copy | every on-screen string against `copy.md` and `facts.md`; every claim, on screen and in any copy written for the film's platforms (a title, a description, a post, a cut-down's captions), keeps its status's qualifier — "reportedly", "proposed", "a prototype", "illustrative" | `literal_audit.py` for the strings — it matches text and reads no status, so its PASS says nothing about a qualifier; every claim, on screen and in the platform copy, read against `facts.md`'s status column by eye | high; a lost qualifier is high |
| 4 | style | a colour outside the palette, a second display face, uneven stroke weights | frames | medium |
| 5 | joins | an element vanishing or jumping at a cut, black frames, a half-visible element popping at the cut | frames at each scene boundary ± 2 frames | medium; high for a black run |
| 6 | animation | jitter, a reversed direction, a large linear move, an element already at its end state on its first frame, a tween starting mid-state, a one-frame pop or step (two tweens on one property, a 3D object fading in — `designed-elements` HYPERFRAMES-CONTRACT § Silent traps) | three consecutive frames at entrance, middle and exit; `video-finish-qc` `decoded_checks.py motion <render> --accepted <p>/compositions/captions.html --accepted <p>/timeline.json` names the frames that pop, step or flash, every caption's show and hide and every scene cut set aside (a large element only; `--tiles` is a lead for a small one) | medium |
| 7 | render traces | banding in glows, grey haze, jagged text edges | 1:1 crops | low to medium |
| 8 | empty · small | `designed_frame_metrics.py` EMPTY and SMALL | the flagged frames | high for nothing big over 1.5 s; low for a hero under a third |
| 9 | sustained action | `designed_frame_metrics.py` STILL and HOLD with the class — BLIND on a shot whose grain or living ground lifts its floor over the still threshold: there it cannot see a hold | the flagged frames; on a BLIND shot, every hold read by eye | medium for TRUE-STILL (add an action); low for SMALL-MOTION (raise amplitude) |
| 10 | camera | the budget per chapter, the ease, captions moving with the camera | first, middle and last frames of each move | high when captions move |
| 11 | comprehension, cold | once per approved cut, never per draft: an observer that has not seen the script says what the film is about and what changes in it, compared with the opening question (NARRATION.md). A topic or a change it misses, misnames or gets wrong is a LEAD, not yet a defect — a summary leaves out things it understood — so read that stretch of the film (its frames and the line under it) and, still in doubt, re-watch it as one question | a video model's digest of the delivered render that is given no script and no question, so no answer is cued — its summary and segments are the cold read (a re-watch is one question over one short span, paid again, the expected answer never in the question). It is a paid call: a cost line from the service's own estimate and the operator's GO before it; a render that shows a client's confidential material is uploaded only after the operator confirms | graded once the frames or the re-watch confirm it: high when the film does not carry its topic or its change; medium for a step that does not land |

**Severity words.** High: unreadable, occluded, a fact wrong, a planned element missing, captions moved, empty.
Medium: a beat off, style, a join, a stiff move. Low: spacing, alignment, brightness.

- A measurement over a fixed box misses a moving element — follow the element's box, or read the frames
  (`video-take-review` INSTRUMENTS).
- A number without its frame is a hypothesis; a frame without its number is an impression. Report both.
- Captions are read at phone size once, on the whole film: `contact_sheet.sh <render> 6 1 --phone` (one frame a second,
  360 px tiles) — every caption must read at that size.
- A finding that is a defect in the scaffold or the shared layer is fixed there in the same step, then every scene
  that carries it is re-rendered.
