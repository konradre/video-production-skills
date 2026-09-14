# QC — the classes, in priority order

Read the DELIVERED render (a reduced preview reads motion loose). Every scene gets a line, "OK" included. Record each
finding as it is found, in the file, with the instrument's number beside the frame time — a pass that writes at the
end loses everything to a crash.

| # | class | how | severity |
|---|---|---|---|
| 1 | readability and occlusion | text under the caption band or off the frame; type under the floor (22 px at a 720-px short side, scaled); light text on a light element | frames at every beat | high when unreadable |
| 2 | beats | an element's entrance against its beat (−0.2 … +0.1 s); a sentence with no visible change | frames at beat −0.2, 0, +0.1, +0.3 s | medium; high for a sentence with no change |
| 3 | facts and copy | every on-screen string against `copy.md` and `facts.md` | `literal_audit.py` | high |
| 4 | style | a colour outside the palette, a second display face, uneven stroke weights | frames | medium |
| 5 | joins | an element vanishing or jumping at a cut, black frames, a half-visible element popping at the cut | frames at each scene boundary ± 2 frames | medium; high for a black run |
| 6 | animation | jitter, a reversed direction, a large linear move, an element already at its end state on its first frame, a tween starting mid-state | three consecutive frames at entrance, middle and exit | medium |
| 7 | render traces | banding in glows, grey haze, jagged text edges | 1:1 crops | low to medium |
| 8 | empty · small | `designed_frame_metrics.py` EMPTY and SMALL | the flagged frames | high for nothing big over 1.5 s; low for a hero under a third |
| 9 | sustained action | `designed_frame_metrics.py` STILL and HOLD with the class | the flagged frames | medium for TRUE-STILL (add an action); low for SMALL-MOTION (raise amplitude) |
| 10 | camera | the budget per chapter, the ease, captions moving with the camera | first, middle and last frames of each move | high when captions move |

**Severity words.** High: unreadable, occluded, a fact wrong, a planned element missing, captions moved, empty.
Medium: a beat off, style, a join, a stiff move. Low: spacing, alignment, brightness.

- A measurement over a fixed box misses a moving element — follow the element's box, or read the frames
  (`video-take-review` INSTRUMENTS).
- A number without its frame is a hypothesis; a frame without its number is an impression. Report both.
- A finding that is a defect in the scaffold or the shared layer is fixed there in the same step, then every scene
  that carries it is re-rendered.
