# The repair ladder — when continuity breaks

Cheapest first. Each rung names the case it fixed and what it costs; the section at the end is what was
tried and did NOT work, so it is not tried again.

## 1. Backfill from accepted assets (free apart from the regen itself)

When the operator keeps two clips from
different rounds, THEIR frames become the SSOT of the room: a kept insert's frame → the character's ref;
a kept pan → the set's post-state ref; the pre-state derived from it with the change reversed; the room
plate EDITED to carry both; the close-up fix gens started on crops of that plate. Every regen chained back
to something already approved — that is what makes a round land.

## 2. Extension from the keeper (same price as a fresh gen)

A video-extension mode on the keeper's own job id (`--extension_mode forward` on Seedance 2.5 at the time
of writing) yields new footage continuing the keeper's last frame. Room, coat state, framing and props
carry by construction; the join frames were near-identical. Use it for every aftermath / hold beat that
follows a keeper — the route that holds a door on its wall when cut references have not.

## 3. An insert that explains the break (one short gen)

A keeper whose door is closed when the previous shot left it open: a short POV insert (the character
reaches back and shuts it, turns, produces the prop, starts the next action) fixes the door AND "where did
it come from", and action-matches into the next shot. Keep the insert's native audio. The
same device bridges a trailing line: a bridging shot built from the NEXT scene's own first frame as the
start image, the previous take as a video reference for voice and pose, the prompt = the obvious next
line + the one small reaction the cut needs; then only its first ~1 s is used.

## 4. Start ON the establishing frame — never a reverse angle

A reverse angle re-invents the set (a "looking in" from the far side rebuilds the room as a different room on
every seed, even with the establishing frame among the refs). When continuity is the note: crop the
establishing keeper's frame to the intended framing (a 9:16 push-in on the same axis), upload it as the
start image, keep the identity refs, and write "no cut, no change of angle; the start frame's viewpoint
from first frame to last". The cut from the wide to the push-in reads as a punch-in on the same axis. An
over-the-shoulder from the wrong end of a table MOVES the character — frame a match ON the established
axis, or as an explicit reverse with left and right named for that side.

## 5. Punch-in or reframe at the finish (zero cost)

A stale state that framing reveals (a garment back on in a close-up after it came off; a generated label at the
frame edge) leaves the frame with a per-event zoom/anchor punch-in on the existing hero at mezzanine
resolution; verify on two frames. Prepare the regen as the gated fallback, not bought.

## 6. Drop, reframe, or cut the beat

A state the model cannot render — one it overrides on seed after seed across two prompts — is not
prompted against again: choose a framing where the element cannot be in the frame
(knees-down, chest-up, hands cupped over the mouth for the shout; never the waist of a bare torso — the
filter refuses it; never the back of the head), cut on the frame the state
changes, or drop the shot.

## The two structural rules above the ladder

- **One continuous action is ONE generation.** Four gens chained frame-to-frame held geometry at every join
  and the scene-change detector found no cut, yet the cut reads as disjointed, stitched
  together: each gen re-decides pace, camera drift, light and micro-blocking. Size the gen to the whole
  action (a 12 s take at 30 cr replaced four 5–6 s gens at ~52 cr and deleted three joins) and cut only
  where the script cuts. The start-image chain stays the tool for a REAL cut that must match. Even inside
  one long gen the internal cuts are diffed (a seed can show a character seated, then emerging from
  elsewhere with a stranger in their place).
- **A shot whose last state hides the face cannot be continued by a gen.** A headless torso start image is
  refused unbilled; the next frames with a head are blur. Decide before generating how the NEXT shot
  starts: write the face into the last frame, continue from the take's own footage (the tumble, the
  landing, the low angle), or budget a new angle still.

## What did NOT work — do not retry

| tried | result |
|---|---|
| an editing image model asked to "move him" | ~0.5 m shift and an invented prop in his hand |
| a local sprite move of a whole standing figure | ghosting — a figure is not a paste job |
| a reverse angle to restore geometry | a different room on every seed |
| more words for size ("small", "thumb-length") | 2–4× real on two rounds; only a size-forcing framing and an in-world crop fixed it |
| negatives against a dominant prior ("not a <the wrong animal>") | nothing, twice; only removing the scene the prior completes works |
| describing what the reference shows | the words beat the picture, every time |
| a "no lettering anywhere" clause on a jacket that carries text | garbled lettering — pin the string or pin the blank on that item |
| a room description in the Subjects block to hold geometry across an in-gen cut | held on 1 of 3 seeds; pinning the geometry PER CUT as the camera sees it held on 3 of 3 |
| a 2D overlay to repair a burst that keeps drifting | ruled out — fix the start frame, add refs, re-roll, or accept |
| a fresh still of "the same room" | a new world; three seeds of it = a rejected round |
