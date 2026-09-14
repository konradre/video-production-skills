# Storyboard — the scene row, patterns by concept, the camera, set pieces, sustained action

The composition numbers (hero size, tiers, empty, light, joins, readable time) are `designed-elements` CRAFT; this
file turns them into a scene plan.

## The row (`storyboard.json`)

| column | holds | the rule |
|---|---|---|
| `anchor` | the first words spoken in the scene | unique in the whole narration — lengthen it until it is |
| `beats` | `{name: phrase}` spoken inside the scene | each element enters on its beat, within −0.2 … +0.1 s |
| `hero` | the one subject | at least a third of the content box; enters on the first or second beat |
| `size` | the three tiers | hero · supporting (≈ an eighth to a fifth of the box, four at most) · labels (six at most) |
| `light` | what glows | the hero only; one focus highlight per frame; the glow goes out before the exit |
| `action` | the verb that carries the line | keeps moving until the next beat (§ Sustained action) |
| `camera` | the move, if any | the budget below |
| `angle` | the point of view this scene is seen from | never three scenes running on the same one (checked) |
| `entities` | every person, company, place or product the narration NAMES here | each one appears in the scene (§ Named entities) |
| `join_in` · `join_out` | both sides of each cut | "the last 0.3 s exit to zero" · "the first elements enter on frame 1" |
| `set_piece` | reveal · big number · symbol · none | one or two per chapter (§ Set pieces) |
| `emphasis` | the one emphasis entrance (a glitch, a flash) | one per scene at most, on the scene's key term; the word appears only in this cell |
| `small_print` | `[{text, beat}]` | on the first beats; ≥ 2.5 s at ≥ 50 % opacity (checked) |
| `last_text` | the last scene's last text beat | a closing window ≥ 1.0 s before the fade (checked) |

## Patterns by concept type

| the concept | draw it as | the hero |
|---|---|---|
| a subject and its features | the subject on one side, numbered slots filling on the other | the subject, lit |
| an analogy | a concrete object and one large label | the object |
| a reveal (set piece) | clear the stage → light sweeps → a ghost outline → a flash and the hero word | the word at display size |
| a source | a paper or page card, the year counted in beside it | the card — the year never stands alone on an empty screen |
| a pipeline step | input → processor → output, arrows drawing on | the processor |
| a trade-off | a balance, or two columns with one verdict | the balance |
| many, scale | a matrix or a parallax wall, lit on the beat | the matrix — never scattered specks |
| a magnitude (set piece) | a big number counted in beside a comparison object | the number (intermediates unreadable or not counted — CRAFT § Numbers) |
| a timeline, an axis | the axis PLUS a hero: the big number or the magnified current tick | the big number |
| a formula | tokens in one by one; the RESULT at the hero tier | the result |
| a table, a ranking | the current row enlarged and lit, the rest grey | the current row |
| the close (set piece) | back to the metaphor: the symbol rises, a ring draws on, the conclusion lands | the symbol |

A naturally small subject — an axis, a formula, a table — is a defect without a hero beside it.

## The camera — a budget

- At least three moves per chapter and at most one per scene; a move lasts about 1.0–1.5 s, eases in and out, and
  ends before the beat it serves.
- The vocabulary: push in on the hero (to about 1.33) · pull back · **carry-over** (the previous hero shrinks and moves
  aside for the new one — never vanish and redraw) · group pan (the next idea sits beside this one) · parallax (two or
  three layers for "many") · accelerate out (a chapter's end).
- Captions and any HUD stay in screen space — they never move with the camera. No emphasis entrance and no staggered
  entrance during a move.
- Measured upstream: the style source ran 6.6 moves a minute; the kit's own films ran 2.2–2.5 with no push-in at all,
  because an earlier rule said "static shots mostly".
- When the subject IS geometry (perspective, focal length, a camera move), build the mechanism for real — a push faked
  with a scale is indistinguishable from a zoom.

**The order inside a scene, which the rate does not give you.** Two upstream rejections produced it: elements that
only enter and leave read as a deck however well the camera is budgeted, and a camera that pushes again after pulling
back cuts off what the viewer was reading.

- Born **close** on the scene's first element (about 1.4, settling to 1.3) → **travel** to the second as it enters →
  **pull back** to the scene's home framing as the title arrives → then **hold** at home until the transition. No
  second push once it has pulled back; what still needs to move is animated, not re-framed.
- **The pull-back finishes BEFORE any text appears** — at least 0.1 s of daylight between them. Text born with or
  during it reads as cut off. Keep it to 1.0–1.2 s so reading time survives; when it will not fit, **cut a sentence**
  rather than shortening the move, and the opening sentence the narration already carries is the first candidate.
- **A cut has a camera half, and both sides are written like the element joins.** About 0.9 s before the cut the old
  scene's elements are gone and the camera pushes toward where the NEXT scene's first element will be; at the cut the
  new scene is born already in that framing and settles. Its first element must be in **within 0.1 s** of the cut, or
  the close-up opens on nothing — the camera equivalent of CRAFT's "a scene's first elements start on its first
  frame".

## Point of view — the axis a camera budget does not have

Measured upstream: a film whose subject was seen from the same side throughout was called static **although** the
background flowed and the camera moved to budget. Rate and duration were right; the viewpoint never changed. So the
angle is a column, and the rule is mechanical: **no three consecutive scenes share an angle**
(`explainer_timeline.py` checks it), and a new fact ideally earns its own instrument rather than another label beside
the same view.

| the fact | the instrument that shows it |
|---|---|
| the opening and the close | the plain side view — the anchor the film returns to, and the only place the subject may simply be present |
| a rate or a speed | the operator's own position: a needle sweeping, the digits beside it, the ground streaming past the glass |
| a route, a distance, a set of stops | a drawn map: the path drawing on, a marker travelling it, stops popping as it passes them, the camera starting zoomed and loosening to the whole route |
| terrain, a climb, a bottleneck | a profile: the contour with the path cut through it, the worst segment highlighted and then enlarged |
| a comparison of time | a race on that map — the alternatives leaving together in their own lanes, one clock running, the winner arriving while the others are a quarter along. Never a split screen, which stops the world |
| a count or a capacity | the inside: a perspective run of seats or slots lighting in turn |
| nearness or scale | head-on: the subject growing from the vanishing point until it fills the frame |

**The cheapest single cure for monotony is the route map** — a styled vector map, the path as a dash offset, the
marker placed by arc length and rotated to the tangent, stops popping at their fractions, the map camera starting
about 2–2.5× at the origin and loosening to the whole route as progress completes, the totals landing after it
settles. One of these built once serves every film that has a journey in it.

A scene's own view must also breathe: a short keyframe list of `[time, zoom, centre]` with a slow ±0.6 % oscillation,
applied to the view's wrapper — never to the captions, which stay in screen space (above).

## Set pieces — relative times

The reveal, at least 3 s:

| time | action |
|---|---|
| T0 | the stage clear — only the ground |
| T0 + 0.13 · 0.73 · 1.33 s | three light sweeps |
| T0 + 0.6 s | a stage line widens |
| T0 + 1.23 s | the hero's outline appears at 10 % |
| T1 — the beat | a flash; the hero enters (the scene's one emphasis entrance) |
| T1 + 0.4 s | a pulse to about 1.1 |
| T1 + 0.53 s | the subtitle rises in |
| T1 + 0.8 s | the parts enter, staggered |

Variants: **the big number** (a 0.7 s count, its unit, a comparison object, the conclusion) and **the symbol** (it
rises by a sixth of the frame at most, a ring draws on beneath it, the conclusion lands). ⚠ A cleared stage with a
thin sweep reads EMPTY to the frame instrument: give the first beat a temporary hero — carry the previous title in, or
set the key word large and shrink it on the next beat.

## Named entities — anything the narration names is on the screen

From an upstream rejection: a company named with no picture of it, a person named with no face, "seventeen factories"
with no factory. The narration asserting a thing and the picture not showing it is the defect; the viewer hears a
name and looks for it.

1. From the script, list every entity — person, company, building or city, product or variant, event — into the
   scene's `entities` cell. One entity, one image, in the scene that names it.
2. Source it in this order: **a free-licence photograph** (an institutional or public-domain archive) → **the
   subject's own official page**, credited → **an image the operator supplies** → **a generated photoreal image
   labelled as an illustration**, and that last one **only for a generic place or object** — a factory floor, a
   production line. **Never a real person's face.**
3. If all four fail, ask before falling back to a silhouette or a placeholder. A named entity with nothing to show is
   a scripting decision, not a layout problem: cut the name or cut the claim.
4. Every image's provenance goes in `facts.md` beside the claim it supports, and a credit appears on screen where the
   licence asks for one.

## Sustained action

- Every beat's verb has an action that lasts until the next beat: data flowing, a pulse travelling an arrow, a line
  typing, cells lighting in turn, growth, a gate opening, a queue compressing.
- Nothing is fully still for more than 1.0 s after it enters (a breathing glow does not count); a slow push from 1.0 to
  1.05 is the floor of a scene with no other move, not its idea.
- The check is on the delivered frames: `designed_frame_metrics.py` STILL (> 40 % of samples) and HOLD (> 1.0 s). A
  TRUE-STILL hold needs an action; a SMALL-MOTION hold needs amplitude — bigger, brighter, denser motion, the hero
  breathing ±2 % — never more elements.
- The gap between a good and a weak explainer is not how much things move: two films matched on motion events per
  minute and differed on size and light.
