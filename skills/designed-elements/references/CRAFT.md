# Craft — the taste rules, from a dozen rounds on one end card

An end card can go through a dozen rounds before it is right. Every rule below is the cost of one of them.

## Where taste comes from

- **From the client's own art and the design corpus, never from a web design system.** A UI-kit output
  is unusable for a poster; an accepted card is built from the brand world (the wordmark, the character,
  the product's pieces) to a professional ad-visual standard.
- **Taste encoded as numbers**: the shot-recipe cards (crash-zoom push 6 f, ">10 f reads as an ordinary
  push-in"; rebound 3–6 %, "larger reads as a spring toy"; shake `14px·e^(−t/1.8)`, ">20 px reads as a
  glitch") — a threshold that names what the failure looks like lets a reviewer label the defect and pick
  the lever. Use them for every motion beat: an entrance, a ding, a sting, a burst.
- Brand colour, one display face, the product's exact silhouette — the three things every element shares.

## Composition drivers — written as numbers beside the bans

A kit that lists only the bans passes on the discipline and loses the taste. Measured on a narrated explainer built
twice (an upstream kit's four-film ledger, 2026-09): the second film matched the first on motion per frame and glow
area and still looked worse; the whole gap was hero size (median 172 vs 219 px on a 521-px content band), time with
nothing big on screen (29 % vs 12 %), and whether light and set pieces were choreographed. Adding motion does not
close that gap. Write the drivers:

- **One hero per scene, at least a third of the content box's height** — a line of display type counts as one object,
  sized by the larger of its height and its width ÷ 2.5 (the width counted up to four heights). **Three size tiers**: the hero · supporting elements at
  about an eighth to a fifth of the box · labels at the legibility floor (22 px at a 720-px short side, scaled with
  the raster). No fourth size.
- **An empty frame** = nothing reaching a fifth of the box's height for more than 1.5 s.
- **Light follows the hero**: supporting elements carry no glow, one "current focus" highlight per frame at most, and
  a glow goes out before its element exits.
- **One or two set pieces per chapter** (a reveal, a big number, a symbol), choreographed as relative times written
  once — never improvised per scene.
- **Idle motion has a floor, not just a ceiling.** The still rule says nothing holds for more than 1.0 s; this says
  what "not still" has to amount to. Upstream measured a cut-out swaying **±10 px over 2 s** and called it static; the
  floor is **±22–28 px over 1.3–1.8 s** (an `inOut` sine, reversing), plus about **±1.5° of rotation** and a slow
  **1 → 1.06** scale across the scene, **each object on its own phase and duration** so nothing breathes in unison. A
  large object takes directional travel at a constant rate instead. Scaled: those numbers are a 1080-px stage, so
  multiply by the raster's short side ÷ 1080. `designed_frame_metrics.py` already measures the quantity that verifies
  it — a SMALL-MOTION hold at the limit is this rule unmet, not a still frame.
- A driver is found by measuring an ACCEPTED build against a rejected one (`video-take-review`
  `designed_frame_metrics.py`); the numbers above are where the upstream kit's own good and bad frames separate.

## Style comes from the subject, never from the last build

A kit that scaffolds from a starter and a previous project emits one house style and calls it taste. Measured
upstream, 2026-09-06: an opener for a second product shipped wearing the first product's skin — same palette, same
glow, same background, same face — because the style was taken from the starter rather than derived. The motion was
good and it failed anyway; a piece that fronts a subject cannot wear another subject's face.

- **Write the style down before any composition exists**, and get it approved with the scene plan: the subject and
  three adjectives for the feeling to leave behind · the palette, sourced from the subject's own artefacts, in hex ·
  the display face, chosen for character (not the first grotesk that renders) · one background language · one motion
  signature, the move that repeats as identity · one special moment where the most expensive effect is spent, once.
- **Two different subjects differ in at least three of four**: palette, display face, background language, motion
  signature. Two builds that share three of them are one build with the copy changed.
- **A starter's values are placeholders.** Its greys, its system font, its background: if any of them survives into
  the render, the style was never derived. Don't open the last project for "an example" either — what carries across
  builds is the rules in this file, not the look.
- **A reference gives rhythm, not skin.** Take the shot lengths, the order, the kinds of transition, the attention
  hierarchy, the energy. Never the palette, the face, the texture, the layout or the copy. "Make it like this" means
  "as alive as this" — say that in one sentence when the reference came from the operator, then build from the
  subject.

## Background motion and transitions — menus, because a rule phrased as a want gets answered the cheapest way

The instructive half of this is the failure. A rule reading "something must move every second" was answered by the
same streaking bars in two consecutive upstream builds under two different names, each justified backwards from the
subject. A want phrased without a menu gets met by whatever is cheapest to write, twice. So both axes are chosen
from a list, named in the style brief, and **different from the last build**.

**Background language — one per build** (two only when the background changes with a chapter): a still textured
ground with only the camera breathing · a large gradient drifting or rotating slowly · two to four blurred colour
blobs adrift · a living grain or paper texture offset from the timeline · one light sweep per chapter, not a
continuous one · a large geometric shape from the subject's own form turning over 20–40 s in two parallax layers ·
particles rising · a grid or pattern breathing 1.0 ↔ 1.04 · giant ghost type sliding behind at low contrast · a
themed image under a Ken Burns push with two parallax layers · horizontal flow — streaks, lanes, rain — **only when
the subject genuinely is speed or flow**, never as the default.

**Transitions — at least two kinds per build, at least one with real depth, and no more than two wipes.** The
hierarchy, in the order upstream arrived at it after two rejected generations (a whip-pan that revealed the stage
edge and read as a page turn, then a sudden spin-and-blur that read as an editor preset):

1. **The camera breathes** under everything — a slow drift of about ±4–5 %, easing in and out, direction
   alternating, chained with no jump. It never stops and it never jolts.
2. **Overlapping choreography** carries the change: the old scene's elements leave fast while the new one's are
   already arriving. The overlap is the transition; no camera effect is needed.
3. **An object wipe with thickness** — a card, an extruded form, a piece of the subject passing close to the lens and
   closing the frame at the cut. Never a flat rectangle sweeping across, which is what "object wipe" gets read as.
4. **A motivated push**, about one per film: diving into a screen, entering an aperture. A push with no reason in the
   story reads as a jolt.

A background change belongs behind 2–4, at the cut, never as a cross-fade mid-scene. One kind of transition at every
cut is a deck with an expensive skin — `slide_structure_audit.py` R4 reads that off the source.

## Assets

- **Cut from the highest-resolution source with a silhouette matte**; a keyed cut-out keys the figure's own
  blacks (hair, outlines) unless the matte is painted; hair must be opaque.
- **A label's straight edge bakes into every element made from it** — cut the asset clean at the source. The
  mechanism, measured: every card asset cut from the label raster carried the label's boundary as a straight run
  of opaque pixels (211 on the burst graphic's first column, 90 on the character cut-out); placed 10–210 px inside the frame it
  read as a contour with black beside it — the "black strip". Incomplete art has two honest fixes: complete it at
  the source, or make the crop line the FRAME edge (the asset bleeds off both sides). Never a border, never layout.
- **A hard border is an asset crop line**: fix it at the SOURCE, never with layout gymnastics.
- **Residual defects are fixed by measurement** (`asset_edge_repaint.py`: a circle fit through the clean
  edge, a repaint of the notch bbox, 8× before/after crops), then EVERY final re-renders with the fixed
  asset.
- **Alignment is measured, not eyeballed**: the tips of a burst are aligned to the same length; an outlier
  is measured against its neighbours.
- **Never reconstruct missing art by extrapolation.** Three rounds of extrapolated tips on a burst graphic — a midline fit, then
  a bisector axis with tangent sides, then capped lengths — were rejected on sight (the red
  covered the letters' drop shadow) and reverted to the original render. What the art does not contain is not
  drawn from a formula; it is fetched from a source that has it, or its cut edge bleeds off the frame.
- **A keyed cut-out's blacks are HOLES**: a character cut-out's hair and outlines and a wordmark's drop shadows read
  as black only because the card behind them is black; over any other layer they go translucent. Force alpha
  opaque inside a matte closed around the coloured body (a 71 px closing kept the rays' background keyed), and
  restore keyed shadows from the glyph mask shifted by the measured shadow offset.
- Reproduce a day-one key by fitting alpha, never by hand-painting.

## Rounds

1. **Check the DELIVERED frame at zoom before showing anything** — never the card render; a fix verified
   on the wrong artefact is a rejected round.
2. **One variable per round**; the operator decides layering on sight.
3. **After failed rounds, REVERT and ask what specifically is wrong**, candidates side by side.
4. **Every file shown is SAVED to the project and named by path.**
5. A designed event plays its full length; a new length is a new project.

## Legibility

A composited piece that cannot be identified is a defect: sprites above the readable floor (~40 px at a
2160-wide raster), clusters only in the far field, the product's silhouette exact (pieces that read as a
different shape are rejected; only random-angle placement reads as "landed").

**Type has a floor per ROLE, not one floor.** From an upstream rejection — a caption at 22 px and a name label at
26 px, "barely readable, let alone on a phone". On a 1080-px stage: body copy and captions **44 px** · name labels,
kickers and years **34 px** (a sub-label 32) · credits and sources **30 px** at no less than 60 % opacity ·
handwritten annotation **48 px** · a title **100 px** and up. **Nothing below 30 px, ever** — copy that does not fit
moves to another scene or goes, it does not shrink. Scale the whole table by the raster's short side ÷ 1080.

**A safe area multiplies every one of those floors by its reciprocal.** A vertical social cut wraps the content in
about `scale(0.78)`, which leaves roughly 190 px clear at the top and 230 at the bottom of a 1080×1920 stage — and
takes 22 % off every glyph. Size the type at **floor ÷ 0.78** before the wrap, not after. This is the group-scale
trap above with a fixed, known factor: the scale is the deliverable's, so the SOURCE size absorbs it.

## Readable time — computed from the composition's timeline, never judged on the render

- **Small print** (a source line, a legal line, a price condition) holds **≥ 2.5 s at ≥ 50 % opacity**. Put it on
  the scene's FIRST beats, never its last: 40–70 characters on a last beat held 0.97–1.7 s, and eight lines were
  reworked in one film.
- **The closing window**: (the end of the last scene − the ending fade) − the start of the last text ≥ **1.0 s**. A
  glitch entrance keeps text dark for over half its frames, so it halves the reading time — one conclusion was fully
  readable for 6 frames. Schedule the last action before the fade starts, too; the fade swallows it.
- **A group scale shrinks the type inside it**: 26 px × 0.72 = 18.7 px, under the floor. Multiply every font size by
  the scale and raise the SOURCE size, never the scale.

## Numbers on screen

- **A counter's intermediate values are on-screen claims.** A 1995 → 1998 roll left three unsourced years readable
  for 4–6 frames each; a 0 → 120 ms roll flashed "37 ms". Keep the whole roll unreadable (a blur ≥ 9 px at a 720-px
  short side for its full length, 0 on the landing frame — 6 → 1 px and 12 → 2 px both left values readable) or do
  not count. A rolling price or percentage in an ad is the same risk in a claims context.
- Every number, name and year that can appear traces to the approved copy or a sourced fact — `literal_audit.py`
  reads them from the composition's source, including the frames no sample shows.

## Glyphs

- **Check the display face's character map against every on-screen string** (fontTools) before a render round: ™, ®,
  currency, arrows, ≈ and ≠. A missing glyph falls back to another face mid-word.
- **Read isolated glyphs at size**: a slashed zero standing alone read as an icon; a face built for CJK set curly
  quotes and the ellipsis full-width inside Latin text — use straight quotes and three periods there.

## Joins — both sides of every cut are written

- "A holds its last 2 frames, hard cut" is read by each side as "I stay still, you enter on your beat" — 6–8 empty
  frames at five joins in one film. Write both halves: "A: the last 8 frames exit to zero · B: the first elements
  enter on its first frame".
- **An exit reaches zero** before a cut: opacity 1 − (n/N)^1.5. A linear 6.7 %-per-frame fade still stood at 40–57 %
  on the cut and popped.
- **A scene's first elements start on its first frame**: a scene that waits for its first beat stacks with the
  previous exit into 11–16 black frames. An entrance starts above zero opacity — `fadeIn(0) = 0` wastes a frame.
- A layer that straddles a join sits at `join − lead` (KIT). `video-finish-qc` catches a black run ≥ 0.1 s on the
  delivered file; the fix lives here, at the source.
- **In and out are not the same length.** An entrance is slow and firm — 0.7–1.3 s on a strong ease-out; an exit is
  quick — 0.35–0.55 s on an ease-in. Matched durations read mechanical, and the exit is the half that usually gets
  copied from the entrance.

## Sound sync

The composition carries the sync constant (the burst at `T0`), found by PSNR against the render and
verified by region brightness on the delivered frame; when the sound moves, the constant moves.
