# Style brief — Ember Row Bakery, "First Loaf" (15 s, 9:16)

A worked example for an invented subject: a wood-fired neighbourhood bakery whose spot sells the first loaf out of the
oven at 6 a.m. The template and its rules: [`STYLE-BRIEF.md`](STYLE-BRIEF.md). `style_brief_check.py --selftest` runs on
this file, so it stays a passing brief.

```style-brief
subject: Ember Row Bakery, the 6 a.m. first loaf from a wood-fired oven
adjectives: warm, unhurried, floury
not: the last build (a teal fintech card system), Watercolour brush, Impasto palette knife
palette: #8A4B1F, #EFE6D6, #3B3633, #E0662A, #C9A46A
palette_source: crust (photo of the client's sourdough), flour bag paper, oven-door iron, ember glow through the oven mouth, the shop's oak counter
display_face: Fraunces
background: living-texture
transitions: overlap, object-wipe
motion_signature: the rise — a slow swell 1.00 → 1.04 over 0.6 s on sine.inOut, settling, each element 3 frames after the last
special_moment: the oven door opens at 9.5 s and ember light floods the frame once
render: canvas-2d
```

## 1. Essence, and what it is not

Ember Row Bakery, its first loaf of the day. Warm, unhurried, floury. A frame reads as this piece when it shows dark
iron and pale flour in the same shot, light that comes only from the oven, a little drifting flour dust, and type
that sits like a chalked price on a board. Not **the last build** (a teal fintech card system with glass panels): no
glass, no cool hues, nothing floats. Not **Watercolour brush**: no painted strokes, the photographs stay photographs.
Not **Impasto palette knife**: no paint texture on the bread; the crust's own texture is the texture.

## 2. Materials and rendering

The client's photographs of the loaf, the oven mouth and the counter, cut with a silhouette matte, on a warm-dark ground.
Background language: `living-texture` — a flour-dust grain offset from the timeline, drifting up slowly, anchored to the
world so it parallaxes with the camera. Type and the price tag live in screen space. Every asset is the client's own
photograph or set in the display face; nothing is drawn to look like bread.

## 3. Colour logic

Two neutrals carry everything: oven iron (dark) and flour (light). The ember orange is reserved for oven light and the
one price figure, nothing else. The crust brown and the oak only ever appear as the photographed objects themselves,
never as fills. Palette: iron `#3B3633`, flour `#EFE6D6`, crust `#8A4B1F`, oak `#C9A46A`, ember `#E0662A`, each read
from the artefact named in the block.

## 4. Type and captions

Display: Fraunces, soft wedge serifs at a heavy optical size, chosen because it reads as a hand-lettered bakery sign
without being a script. Text: the same family at a text optical size, so the piece has one voice. Roles, on the kit's
2160 × 3840 raster (CRAFT § Legibility, its 1080 table × 2): the line as a title at 200–240 px, the price at 260 px in
ember, the address as a label at ≥ 68 px, captions at ≥ 88 px on a flour-coloured strip with a 4 px iron rule, holding
the CRAFT readable times.

## 5. Motion quality

Motion signature: **the rise** — an element swells 1.00 → 1.04 over 0.6 s on `sine.inOut` and settles, each following
element 3 frames after the last, the way dough rises in a tray. Everything on ones; the flour dust drifts at 4 % of the
frame height per second. Never moves: the counter edge, the price once it lands.

## 6. Camera grammar

| Move | What it expresses | Can serve |
|---|---|---|
| slow push toward the oven mouth | heat, waiting | the open; a moment before something is ready |
| low lateral track along the counter | the morning's order of things | a list of loaves; a queue forming |
| locked close-up while the flour dust drifts | stillness, craft | the price; the line that must be read |
| pull back to the shop front | the place in its street | the address; the end |

## 7. Sound palette

Dry and close: a wooden peel on stone, a crust crackling as it cools, a bell on the shop door, a brushed snare at
most. One wet timbre for the special moment: the oven's breath as the door opens. A silence holds only the crackle.
Placement and silence counts: `spot-audio-assembly` § Sound direction.

## 8. Native moves

Special moment: **the oven door opens** at 9.5 s and the ember light floods the frame once, washing the iron to orange
for 0.8 s before it settles.

- **The rise.** A group of elements swells in turn, as dough does. *Fits content like:* loaves arriving on a rack;
  orders stacking up; a crowd filling a street.
- **The peel pass.** A wooden peel crosses close to the lens and carries the cut (the `object-wipe`). *Fits content
  like:* one loaf to the next; a tray swapped; a new day.
- **Light from one source.** Only the oven lights the scene; the frame darkens as the camera moves away from it. *Fits
  content like:* a night shift; a fireplace; a single lamp in a workshop.

## 9. Pitfalls of the medium

Flour dust as unseeded particles differs between render workers: seed it and draw it from the tweened progress
(HYPERFRAMES-CONTRACT § Silent traps). The ember flood at full strength clips the flour whites: cap it at the
photograph's own highlight. A large 2D canvas opened without `willReadFrequently` changes raster path mid-render.

## 10. Renderer

`canvas-2d` in HyperFrames: the dust and the light flood on one canvas under the DOM type. Nothing extra to install.

## 11. Variation space

Each spot decides its loaf, its line, its price, its opening shot and its length; the oven light, the rise, the peel
pass, the palette and the face are this brief's and do not change without the checkpoint's change steps
(`ad-spot-preprod` § 6).
