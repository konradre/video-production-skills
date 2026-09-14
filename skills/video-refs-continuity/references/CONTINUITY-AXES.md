# Continuity axes — the ledger's rows, and how each is pinned

One row per axis. *Read off* = where the fact comes from (a keeper frame at zoom, never memory or
prose). *Pinned by* = what carries it into the next gen. *Breaks as* = what the miss looks like on a seed —
each of these is a rejected round.

| axis | read off | pinned by | breaks as |
|---|---|---|---|
| **Position / seating order** — who is nearest the camera, who sits where | the previous keeper's last frame; the plate | the start image (an edit of that frame); "in front of the middle seat, one step forward of the sofa's front edge" | a character at the far end of the table who was directly opposite the lead; a character standing beside someone they were across the room from |
| **Pose state** — standing stays standing, fired stays fired | the last frame | start image = last state; the prompt opens on it ("already standing, the device already fired, NO bang") | a character seated again after standing in the previous shot; the device fires a second time |
| **Door: swing + distance + which side of the lens** | the accepted wide (leaf hinge side, swing direction, actor's distance) | one sentence copied from the geometry record into every prompt and still near a door ("the leaf swung INTO the room, hinged on the left, she two metres inside"); the reaction near a door = the OTS from the doorway | the door on the wrong wall; the door where the camera stands |
| **Eyeline** — per character, the line-deliverer first | the shot whose camera stands at the target ("directly opposite" = where the camera is) | a target in the prompt and in the start still ("eyes down on the carpet"; "looks to the right toward the friend at the mantel, never at the camera"); a group reaction frames left, centre AND right; a target NOT in frame turns the face to the lens (H3, three cases upstream) — move the CAMERA to where they look (table height beside the prop; the listener's place; beside the screen), never add a head-turn against the story, and forbid the lens look in words | eyes on the lens instead of the target; a whole group looking one way |
| **Facing** — who faces whom in every stand-up, turn and line beat | the plate's geometry | "turns to his right toward the friend at the mantelpiece and shouts at him" | the speaker turns to the camera instead of the addressee |
| **Counts** — objects on a shelf, pieces on a lap, guests in the room | the keeper at zoom, counted | the number in the prompt, verbatim; insert refs cropped from the plate's own shelf | a shelf of nine objects becomes six in three plates |
| **Cast** — closed, named, each once | the establishing frame | the room ref carries them; "the ONLY people in the shot are …, no other guests"; count each named character's wardrobe once at 2× across the crowd | a different audience (younger, more, fewer); the same character twice in one frame |
| **Wardrobe** — accessories, layers, no invented item | the keeper; the script | "nothing added to him" for every untransformed character; a pre/post pair from one source | a sash or a hat from nowhere; a different outfit in the next shot |
| **Held props + drink** — one prop per hand, the same object every shot | the keeper | the ledger row per character per shot in timeline order; fix at the cheapest shot | a cup when seated, a glass when standing |
| **Set dressing** — the same objects, the same picture, the same bricks | the accepted post-state frame | the pre-state DERIVED from it with only the change reversed; inserts = crops of the plate | the shelf's objects missing from every other shot |
| **Named state** — teeth out, a garment off, glass in the pane, a bag on the floor | the script's event + the frame it happens on | the state carried forward in every later prompt; verified on EVERY frame after the event at 4× (gamma lifted in dark cavities) | the state undone in a later shot (teeth back in; the window glazed again) |
| **Product shape + colour** — the same silhouette in every video | the client's single-piece photo | the exact-silhouette sheet (single pieces on grey, the shot's own scatter) in EVERY scene that shows the product — resting pieces on a table included | a different shape per video; pieces that read as a different object |
| **Product size** — true scale relative to the body | an accepted shot where it held | an in-world crop beside a known object (tie knot, seated knee) with the role "use the size relative to the tie knot only"; the held product composited standing at true scale | pieces 2–4× too big; a product wider than the real SKU |
| **Density and sound after a burst** — blanketed, still raining, no second bang | the keeper's last frame | `air_pieces.py` layer on the start image; "NO bang, the device already fired" | every continuation opens with a fresh bang |
| **Anatomy** — 2 arms, 2 legs, 1 head, each hand on an arm | every plate, crop and keeper frame, per person at 3× | a limb repair on the clean plate before any gen | a double arm from the elbow |
| **Room geometry per cut** — window, door, lamp as seen from THIS camera | the establishing frame · the scene proxy's table for THIS camera (`scene_proxy.py`, SCENE-PROXY.md) | "the white front door at the right of the frame with the floor lamp beside it… exactly as seen from the couch"; a room-side landmark "behind the camera, never in frame" | the couch turned the other way with the door behind it |
| **Dialogue continuity** — a trailing line needs its continuation | the keeper's audio | a bridging shot with "the obvious next thing"; the word remainder carried as an L-cut | a line trails off into frozen silence |

## The two checks that run on every seed

1. **The continuity sheet first** — the plate, the first frame of every cut, the last frame, side by side;
   every background element in every cut at zoom (one object checked is not all of them). A seed that
   breaks the ledger is rejected before its gag is judged.
2. **The handoff** — the keeper's last frame becomes the next shot's `before`; diff it against the ledger
   and write the row.

## Tolerance tags

Every Δ carries one: **Locked** (fails closed — product shape, door, cast, named states), **Flexible**
(may drift — background extras' exact poses), **Story-changing** (in force from its event onward — a
smashed windscreen, an object revealed on a table). The gate fails on Locked and in-force Story-changing rows only.
