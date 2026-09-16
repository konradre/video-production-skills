# The reference contract — how a reference is built, and how it is pointed at

## Pointing, never describing

| goes in the prompt | comes from the reference |
|---|---|
| which ref is which character / element (`@Image2 the product`) | coat, face, hair, build, colour — every visible attribute |
| the relationship BETWEEN refs (size order; who is nearest) | — |
| what the subject DOES — action, staging, blocking | — |
| the role and the exclusion ("use its shape, size, materials and colours only, never its background") | — |

Any adjective describing a cited reference can only contradict it. A wrong colour word beside the correct sheet
wins on every generation; deleting the description and citing the sheet fixes it in one roll. Diff prose against the asset,
never against other prose — consistency between documents is not evidence.

## Building a reference

- **One subject per reference, native resolution.** A montage is blended into an average subject (a
  large and a small character averaged is a dwarf). Split a three-view sheet with `split_sheet.py`; never
  downscale on upload.
- **Each reference gets one narrow job**, named with an exclusion. Practical cap 1–3 image refs per gen
  for image models; video venues take more (a start image + image refs + video refs together) — the start
  image carries the SET, a video reference carries the VOICE and blocking of the take before.
- **A style anchor and a layout anchor are never the same image** unless the role line names which
  properties come from it. A sibling's sheet passed for its three-panel LAYOUT transferred its whole design
  (hair, bare chest, gaunt face) and converged three characters into one design. The role line is the only
  thing that separates a layout from a design.
- **Colour identity is stated relative, and bounded on both sides, whenever the frame is dark.** An
  absolute coat name held in a bright frame and failed in a shaded one (grey-silver came back dark brown,
  and the character who threw could no longer be the one who caught). Write the coat as a contrast against
  its own background AND against the other characters in the same sentence — "clearly lighter than the
  forest behind it, and still clearly darker than the pale one" — because a one-sided relative instruction
  is a direction with no stopping point: it overshot to a shade the operator had already ruled out. After
  any correction, the risk is the corrected direction.
- **Preserve list, anti-blend, conflict priority, transformation phrasing:** "face, brow, hair length and
  texture, coat colour, build must appear 100 % identical to its own reference; only the pose, the lighting
  and the setting change; do not blend any two references; resolve any conflict in favour of @ref1, then
  @ref2".
- **Never a schematic map with labels or arrows** — the labels render into the scene.
  Blocking goes in prose with metres; geometry goes in FRAMES (upload the keeper frame; prose geometry
  does not hold).
- **Sheets transfer their LAYOUT.** A sheet of pieces laid out as a grid produces upright rows; a
  scatter sheet (random angles, one overlap, uneven gaps) produces haphazard pieces. Build the
  sheet as the shot's own scatter.
- **Shape reads only above a size.** At 480p a product silhouette reads at ≳ 40 px per piece; below that
  every piece is a dot. Design the product shot at the framing the product needs (close enough that the actual shape of
  the pieces reads at their actual size), then anchor size to a body part in the prompt
  for each new framing — a tighter frame scaled the pieces up with it.
- **A magnified sheet pins shape and colour only.** Size comes from an in-world crop beside a known object,
  with the sheet's role demoted to "magnified — shape and colours only, never the size". A size ref's
  pieces also set the BURST's colour — every SKU needs its own scale ref in its own colours.
- **A held product**: the product sheet from the REAL product photo (never an image model's drawing — it
  invents proportions), a real in-world size photo, the proportions in words ("thinner than his wrist,
  six times taller than wide, never thickens"), the real product composited into the START image standing
  at true scale (a seated knee ≈ 50 cm ⇒ a 30 cm product = 0.6 × the knee height in px), and acceptance by
  a 4× crop of the take beside the product photo — pixel instruments are blind at 480p.
- **The room ref carries the cast.** The establishing frame with everyone in it is the ROOM/CAST image for
  every later shot ("the room and its people, every seat, face, hair and outfit exactly as placed"). Adding a member from their single ref doubles them. When the cast is recast, the new plate
  becomes the room ref, the gate rules get the new names, and the old ref is struck from every prompt.
- **Character refs are cut from the first accepted take** — a frame of its upscale, head-and-shoulders,
  isolated against a flat fill per row, occluders painted out. Passed in every later gen.
- **A shot whose start frame hides the set needs the set's plate in the refs** (a frame where bodies
  block the furniture → different furniture on every seed until the room plate rides along). Ask of every gen: what
  does the start frame NOT show that the shot will?
- **An element that drifts in motion gets an approved frame of it IN MOTION** as a reference, and the prompt
  names density beside shape ("a few hundred separate pieces, never glitter, snow, spray or petals").
- **Pre/post partition.** Lettered or transformed refs ride only post-transition gens; pre-state
  refs only pre-transition gens. The pre-state of a kept post-state element is derived from the kept frame
  with the scripted change reversed.
- **Garment / prop text, in order:** (a) an image model that will write the words (a Google-moderated
  route accepted what an OpenAI-moderated one refused); (b) the copy route — the LETTERED still as an
  image reference with NO lettering words in the prompt (the model refuses the words, not the picture);
  (c) another venue's image model with image references; (d) the local knit composite (`knit_letters.py`),
  checked at 4× against the accepted close-up, same place, same size. A garment that conventionally
  carries text is pinned with the exact string or pinned blank on that item — "no lettering anywhere"
  leaves it unspecified and it garbles.
- **Surgical edits vs re-imagining.** A count, a ghost, one prop, one limb: an editing image model on the
  CLEAN plate (pieces composited after — a plate carrying product pieces at large scale can be flagged as
  sensitive). A new wall, a new person, a moved figure: the copy route from the pre-plate with an explicit
  placement sentence. An editing model cannot move a figure (~0.5 m and an invented prop); a whole
  standing figure is not a sprite.
- **Photoreal people as references:** fine on a venue whose reference mode exists for character consistency;
  refused outright ("likenesses of real people", billed 0) on another. Check the venue table before the
  set is built, and never pass a real person's photo — crops of OUR keepers only.
- **A likeness check on cast refs:** a character who resembles a public figure is re-rolled before it ships.

## Generating an identity reference — the locked JSON is the seed these routes do not have

The order of preference above puts a fresh still LAST, and this section is for that last resort: a
character the campaign will reuse who has no keeper and no client photo behind them. Everything else
derives; this one has to be *authored*, and an authored identity is a lineage ROOT — so it must be
re-generable after the output URL has lapsed and the frame is the only copy left. None of the image
routes carry a seed, so the prompt IS the seed, and the only thing that makes it one is how little
freedom it leaves. **Write it as JSON, save it beside the frame it produced, and register the frame with
the JSON as its provenance.** A frame whose prompt was prose cannot be regenerated; it can only be
re-rolled, which is a new character.

**Lock every variable, because an unlocked one is a variable the model chooses.** One concrete value per
attribute — never "or", never a range ("20–30"), never "natural-looking" without the specifics. Quantify
what can be quantified: degrees for head turn and tilt, cm for distances, mm for small detail (liner
flick, nail length, chain thickness), % for framing and headroom, counts for countable things, **a hex for
every colour**. Left and right are the subject's; frame positions are "frame left". Small items sit at an
anatomical landmark ("2 cm below the collarbones"), never "on the chest".

**Lock ABSENCE, twice.** Anything a model might add that the reference does not contain is stated as
`"none"` *and* listed in the negative prompt: glasses, hat, earrings, bag, a second person, text, logos,
props, tattoos elsewhere. An absence stated once, positively, is not locked.

**One anchor image sets pose, framing, lighting, camera and aspect; every other image refines identity
only.** On a conflict, trust the sharpest, most frontal, least compressed evidence — motion blur,
compression and lens distortion are properties of the capture, not traits of the person.

**Counter the model's default prior explicitly, or the deviation is ignored.** Image models pull every
person toward a default attractive face, and any trait that differs from it is quietly discarded unless
it is escalated in all three places at once: described geometrically in its own field, restated as a
one-line imperative constraint, and its default-prior version added to the negative list. The axes worth
walking every time are eye shape and lid, face shape and symmetry, build, clothing COVERAGE, hair volume
and gloss, skin texture, stance, overall "look", background saturation, and unrequested additions.
Counter-steer toward the reference's own features, never toward plainness: a glamorous reference is
described faithfully, not flattened.

**De-slop in the same pass, always.** Quality boosters ("8K", "ultra-detailed", "masterpiece", "sharp
focus", "flawless") belong in the NEGATIVE list, never the positive fields. A capture pipeline — body,
lens, aperture, ISO, codec or film stock — replaces every adjective about quality. Imperfections are
present and LOCATED (skin micro-texture, facial asymmetry, hair clumps, fabric creases, sensor noise),
because an imperfection that is not located is random. Grading stays flat, sharpening stays off, and the
constraint list ends by naming the medium the image must read as — an unretouched real capture, never a
render.

**Iterating is a variable audit, not a patch.** When a generated frame misses, diff it against the
reference across the WHOLE list, not only the trait that was named: every difference means some variable
was under-locked, and the fix is to split that field into finer sub-fields with more geometry, strengthen
its constraint line, and add the drifted appearance to the negatives. Output the complete JSON with its
version bumped, even for a one-field change — a patch that lives only in the conversation is lost the
moment the session ends, and the frame it produced then has no provenance.

**Two boundaries.** Never put a real person's name, a celebrity comparison or "looks like X" in the JSON —
appearance descriptors only, and never an inferred nationality or religion. And an authored JSON locks a
consistent ORIGINAL character, never a verified identity: a real person's likeness is a routing fact with
its own rights path (SKILL.md § 2), not something a prompt can assert.

Method adapted from `portrait-clone` (superdesigndev/treg, Apache-2.0), read 2026-09-16; its full field
schema is the floor, and the corpus rules above — one subject per reference, the role line, the preserve
list — still govern how the resulting frame is CITED.

## Look plates — light and palette as a reference

A **look plate** is an abstract full-frame field of colour and light with no subject — a golden hour, a
dusk, a canopy, a night road — cited by every shot in that light so the shots agree on palette and contrast
without a grade sentence in every prompt. It is a reference kind of its own, beside the character sheet, the
room plate and the product sheet, and it carries the look at GENERATION time; grain, halation and bloom
still belong to the finish (generate clean — `video-finish`).

- **One plate per light context, enumerated against the real shot list.** Three plausible-sounding
  variants (golden / dusk / canopy) covered ten exteriors and neither interior, so an interior shot cited a
  cool blue-hour woodland plate for a warm tungsten room — a reference in direct contradiction of its own
  grade line — and had to drop the slot. Write the shot → plate map before the plates are generated; the
  shot list, not taste, decides how many there are.
- **Asset kind selects the template.** A plate is not a prop: routed through a prop leg it inherits the
  three-view product framing (and ghosted duplicates behind each view). Generate it template-free, as a
  direct text-to-image of the field itself — three plates came back as clean full-frame colour fields that
  way.
- **Its role line is look-only.** `@ImageN is the look: take only its light, palette and contrast; never
  its content, framing or subject`. (An H3 expander classifies such a plate `attribute_transfer`, not a
  subject — the right reading, which took three hand-written attempts.) Counts, heights and subject accents
  ("two red points", "the taillights the only warm accent") stay in the prompt's prose: a look plate cannot
  carry them, and every prompt restating its own count is what lets the plate's own count defect stand.
- **Fix what the asset is for; ignore what it is not for.** An eyeshine plate that returned three specular
  points where two were asked was accepted, because every prompt that cites it states its own count, and
  re-rolling it risked re-summoning the prior (a whole animal around two points of light) that had just been
  defeated. Re-roll a still when the defect breaks something a later stage depends on; accept when the
  defect sits in a property a later stage restates anyway.
- **When the plate lands after the prompts that cite it, reclaim the prose — carefully.** Every prompt
  written before the plate existed carries a prose stand-in for the plate's job; ten of twelve did. Replace
  only sentences that merely re-describe the plate, keep the subject-specific accents, and only where the
  character budget is tight (a prompt at 1999 of 2000 gains; one with 531 spare gains nothing). Swapping
  the prose for a bare `Grade exactly to @refN` was planned as an A/B and never read — the plate in a slot
  with a look-only role is proven on every delivered gen; the prose-free form is not. Keep the grade prose
  until its removal has been measured.

The upstream hygiene — a cited plate that never existed as an asset, a superseded plate cited by name, a
defect note that outlived its fix — is in [`ASSET-HYGIENE.md`](ASSET-HYGIENE.md).

## Start images

- The start image is the previous shot's LAST state — an edit of the keeper's frame with only the
  scripted change — never the scene's opening wide.
- Composite the exact product pieces after the edit: `plate_pieces.py` on the floor polygon (perspective
  size near → far, local tint, off dark / saturated / near-white pixels), `sprinkle_pieces.py` bands on
  laps, shoulders and shelves at a named piece length, `air_pieces.py` for the still-falling layer with
  face boxes avoided.
- The venue re-renders frame 0: composition, blocking, light and palette carry; pixel-exactness does not.
  Spend the effort on blocking and light, not fine detail.
- A start frame is PRE-action — "has just / is about to", never mid-stride or with the projectile in the
  air — and a coherent MOMENT, not a lineup (where were these bodies a second ago, where next?).
- A "product already in hand at frame 0" still is not a shortcut: an editing model distorts the product
  and invents props, and a pasted product in a clasped hand reads as a sticker. Start it standing at true
  scale and pin the hold with refs and wording.
- A headless or bare-torso start image is refused by the venue's filter (unbilled): frame chest-up or
  knees-down, never the waist.

## Client-supplied references

A client's own approved image — a character photo, a product shot, a location — enters the set by IMPORT, with its
provenance (who supplied it, when, through which channel) and its content hash: `refs_gate.py --import`. It is a
lineage root in its own right: a start image cut or edited from it is rooted without `--fresh-scene`, and nothing has
to be recorded as a generated take to pass the gate. It still meets the venue's rules (a venue that refuses real-person
references refuses it), and anything re-rolled from it still gets the likeness check.

## The reference pre-flight — cents before credits

Before an expensive reference-driven call, one still from the SAME reference set (`video-gen-cost-gate` COST-AND-GO §
The reference dress rehearsal) shows what the set actually carries — identity, wardrobe, setting and look resolve at
still cost. Read it for COMPETING references as well: an older room plate beside an exact start frame, a look plate
from another light. Drop what the shot does not depend on before the video call, not after it.
