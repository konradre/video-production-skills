---
name: video-refs-continuity
description: >
  Continuity through consistency for generated video: builds the DERIVED reference set and start image
  every shot needs, keeps the continuity ledger between shots, and runs the refs gate in code before any
  generation call. Use when a shot must match the shot before it (room, cast, seats, wardrobe, held props,
  door swing, a named state), when a character, product or room reference is built or
  cut from a keeper, when a plate or start image is generated, or when seeds keep drifting between shots.
  Triggers — "continuity", "refs gate", "reference set", "start image", "continuity ledger", "backfill
  from accepted", "the door is on the wrong wall", "not the same guy", "the same shape in all videos".
  Not for the cost line, the GO and the submit itself — use video-gen-cost-gate. Not for the prompt's
  wording — use video-prompt-dialects. Not for upscale, film look, grain or the delivery encode — use
  video-finish.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3*), Bash(ffmpeg*), Bash(ffprobe*), Bash(ls*)
---

# Video Refs & Continuity

Every still and every clip is generated from nothing, with no memory of the shot before it. Continuity
is therefore **built**: a *ledger* of what each shot leaves behind, a reference set *derived* from what
the operator already accepted, and a *gate* that refuses the generation call until both are in place.
The ruling that binds this skill: spatial and geometric consistency between the shots of a scene is the
PRIORITY consideration for accepting or rejecting a generation — believability depends on it.

Three words carry the method. A **keeper** is a take the operator picked — its frames are the only root a
scene can continue from. **Backfill** means every regen's references come from accepted assets: a keeper
frame, a crop of an accepted plate, an edit of an accepted still; a fresh still is the last resort.
**Lineage** means every start image chains, by crop or image-to-image edit, back to a keeper or the
client's own photo — a still generated from prose starts a new world, and three seeds of it are a round
of continuity errors.

**What varies.** Which venue accepts a photoreal person, how many references a call carries, which mode holds a shot and
whether a local GPU builds the scene proxy are tool facts of the established chain — re-read them for another venue or
model. The ledger, the lineage and the gate do not move —
`video-production/references/WHAT-VARIES.md` § Generator, venue and native raster.

## 1. Fill the ledger from the keeper frames, at zoom

Before any reference for a scene, open the previous shot's keeper and read its LAST frame (and the
accepted plate, and the client's photos) at 2–4×. Record one row per element that appears in more than
one shot: element · fixed fact (read, never remembered) · state before · state after · tolerance
(locked / flexible / story-changing) · reference name. The axes — seating order, counts on shelves, what
is in whose hands, wardrobe, eyeline, door swing and distance, product size, named states — are the
checklist in [`references/CONTINUITY-AXES.md`](references/CONTINUITY-AXES.md); every one of them is a round lost when missed.

Two rules: **shot N's `after` is shot N+1's `before`** — diff them; and **every number in a prompt comes
from this table verbatim** (the count read on the zoom, never a number from memory).

**Where a keeper frame exists, compute the room instead of remembering it.** `scripts/scene_blockout.py
<keeper-frame.png>` returns the frame as a labelled grey-box scene (people, furniture, door, window, lamp,
floor; relative scale; ~20 s on a 24 GB GPU, $0; `scripts/comfy_ready.py` first — it says whether the server
and its two providers answer, and `scripts/comfy_up.sh` starts one from the env), and `scripts/scene_proxy.py <scene.json> <out> "<camera>"`
prints, for ANY camera you author, where every object sits — left/right %, depth rank, in frame, occluded,
out of frame — and renders a grey-box + depth frame of that angle. That table IS the *Room geometry per cut*
row and the source of every geometry sentence for a new angle; on the pilot it reproduced the accepted keepers'
order on every frame ([`references/SCENE-PROXY.md`](references/SCENE-PROXY.md)). Read the render before you write:
the grey frame is your own view of the angle, and the same scene supplies the still and the video references, so the
prompt, the stills and the refs cannot disagree (SCENE-PROXY.md § One geometry, three channels).

**Done when:** every multi-shot element has a row with both states and a reference name, the previous
keeper's last state is written as this shot's start state, and no number in the shot list lacks a row.

## 2. Build the reference set — derived, never fresh

Order of preference for any reference: an accepted keeper frame › a crop of an accepted plate › an edit
of an accepted still › a fresh still. Build in this order:

1. **Start image = the previous shot's LAST state**, never the scene's opening wide: who stands, what
   has fired, how much is still in the air. Make it an image-to-image edit of the keeper's own frame with
   ONLY the scripted change. A start image *dictates*; a reference image only *informs* — a reverse
   angle with no start image re-invents the room on every seed unless the scene proxy's grey frame of that
   camera rides as its layout-only reference (SCENE-PROXY.md). Which shots take a start image and which go
   refs-only is decided per shot by what it must hold (`video-gen-cost-gate` SKILL § Mode by what the shot
   must hold): an exact continuation or a defined Seedance move → a start image; a fresh angle → refs + the
   grey frame.
2. **Before/after pairs from ONE source** — the "after" still is an edit of the accepted "before". A kept
   post-state element (a transformed mantel) has its pre-state DERIVED from the kept frame with the
   change reversed. Pre-state refs ride only pre-transition gens, post-state refs only post-transition
   gens.
3. **Inserts and close-ups start on a CROP of the accepted plate at that framing** — references do not pin
   a close-up's background; a crop does.
4. **Character refs cut from the first accepted take** — a frame of its upscale, the subject isolated,
   occluders painted out (the model copies whatever else sits in the crop); one ref per recurring
   character, in every later gen.
5. **Product shape from the client's own photo** — single pieces cut out on grey, laid as the shot's own
   scatter (the model transfers the sheet's LAYOUT: a grid renders as rows). **Size from an
   in-world crop beside a known object** (a tie knot, a seated knee); a magnified sheet pins shape only
   and its role sentence says so. A held product is composited standing at true scale before the gen.
6. **Room ref = the establishing frame with the whole cast in it.** It EMBEDS them — adding a member from
   their single ref puts that person in twice. A recast replaces the old room ref everywhere.
7. **Text on a garment or prop is generated INTO the reference** (an image model with the string; the copy
   route with a lettered ref and no words in the prompt; the local knit composite last, verified in
   position at 4×) — never hand-placed on a whole figure, never left unstated on an item that carries text
   by convention (a uniform jacket).
8. **A look plate per light context** — an abstract full-frame field of colour and light, no subject,
   generated template-free (never through a prop leg) and cited by every shot in that light with a
   look-only role; the family is enumerated against the shot list before it is generated (three exterior
   plates covered ten shots and neither interior). Counts and accents stay in the prose; grain and bloom
   stay out of the plate. A prompt whose prose names a light cites that light's plate — the gate fails it
   otherwise once the rules list the plates.
9. **The scene proxy is one geometry for three channels.** Its render and table are read before any geometry
   word is written; its grey frame composes a start or end still (layout-only role) and stands as the r2v layout
   reference for a static new angle; its clip drives MiniMax H3's camera. On Seedance a move is a start image
   + an end still baked from the proxy — a clip beside a start image is inert (`SCENE-PROXY.md`, A/B
   2026-09-10). Renders ride only complete: the lamp a lamp-less proxy lacked vanished from the take.
10. **A client-supplied image is IMPORTED with its provenance** — `refs_gate.py --import NAME --file <path>
    --provenance "<who, when, how>"` — a lineage root of its own beside a keeper. Recording a client's approved
    photo as a generated take to satisfy the lineage rule writes a false record; the import is the honest path.

Point at references, never describe them — any adjective about a cited reference can only contradict
it. One subject per reference at native resolution, a preserve list and a conflict priority in the
prompt: [`references/REFERENCE-CONTRACT.md`](references/REFERENCE-CONTRACT.md).

The composite tools ship in `scripts/` (Python 3, numpy, Pillow, scipy): `plate_pieces.py` (exact product
sprites onto a plate — perspective-sized, locally tinted, kept off dark and bright pixels),
`sprinkle_pieces.py` (a band at a named piece length), `air_pieces.py` (the still-falling layer after a
burst, motion-blurred), `split_sheet.py` (a three-view sheet → single-subject crops), `knit_letters.py`
(intarsia lettering multiplied onto a knit's own luminance). Each takes `--in/--out` and a `--sheet`.

**Done when:** every locked element has one accepted reference or a before/after pair; every one traces by
crop or edit to a keeper or a client photo; the start image is the previous shot's last state; nothing in
the set is a montage, a schematic with labels or arrows, or a photoreal person bound for a venue that
refuses one.

## 3. Accept every generated still like a seed

A start image is a contract: any defect in it is in every seed built on it. Before it feeds anything,
run the scene's acceptance rows on it at zoom and record them: product pieces at 2× (shape, size,
haphazard angles), lettering (string and position against the accepted close-up), geometry against the
previous keeper (every person's position, the door leaf's swing, their distance from it), the cast
counted once each at 2× across the crowd, anatomy per person in a per-person crop at 3× (arms, hands,
legs, where each arm ends; one prop per hand), and the ledger (what has happened is visible; what the
script has not yet done is absent).

```
python3 scripts/refs_gate.py --root <project> --accept <NAME> --note "<every row checked>"
```

A defect is fixed at the source: a surgical edit (a count, a ghost, one limb) on the CLEAN plate with the
pieces composited afterwards — never a whole-plate regen when the rest is right; a mispositioned figure
is a copy-route regen from the pre-plate with an explicit placement sentence, never a sprite move.
Re-roll a still when its defect breaks something a later stage depends on (a continuity break, a wrong
object); accept it when the defect sits in a property every later prompt restates anyway — re-rolling a
defeated prior is a real risk, not a free retry.

**Every cited reference is accepted the same way, not only the start image.** In reference-driven generation the
references ARE the product: register each to its file (`--register NAME --file`) and accept it for the role it plays —
the note names that role's read (a face for an identity ref, no subject in a look plate, the named geometry in a
setting ref). The gate re-hashes the file on every run, so a reference edited after acceptance fails until it is
checked again.

**Done when:** the acceptance note names every row checked, and the gate shows the still `ACCEPTED` with a
`lineage → keeper` chain (or `--fresh-scene` for a scene with no predecessor, stated in the GO ask).

## 4. Run the gate before the GO — code, not memory

> In reference-driven generation the references are the product. Verify them with the cheap instrument before you
> spend on the expensive one: a still costs cents, a video seed tens of credits, a wrong reference the whole batch.
> (house rule, 2026-09-13 — the rehearsal still is `video-gen-cost-gate` COST-AND-GO § The reference dress rehearsal)

```
python3 scripts/refs_gate.py --root <project> --prompt prompts/<shot>.txt --refs A,B,C \
    --target hf|kie|monid [--start-image NAME] [--births ROLE,..] [--prose ROLE,..] [--record NAME]
python3 scripts/refs_gate.py --root <project> --register NAME --file references/<file>.png
python3 scripts/refs_gate.py --root <project> --import CLIENT-PHOTO --file assets/<file>.jpg --provenance "<client, date, channel>"
```

Each target has its own upload ledger, and the gate reads the one the call will use: `receipts/<NAME>-upload-id.txt`
for `hf`, `refs-urls.json` for `kie`, `monid-urls.json` for `monid`. A reference bound for monid is hosted on monid's own
`sfs` store by `video-gen-cost-gate/scripts/monid_upload.py` at **$0.00** — and because a lapsed sfs URL is re-issued by a
free `/cat` rather than re-uploaded, an expired link there costs nothing, unlike kie's ~24 h expiry. The same call also
carries a privacy consequence the other targets do not: an sfs URL is fetchable by anyone who holds it until its `ttl`
lapses, and `/rm` frees the quota without recalling a copy already served — so a client's own asset gets a short `ttl`,
not the default. **The gate checks that url's EXPIRY, not just its presence** — a lapsed signed url would pass a name
check and then cost the batch, because the model fetches it at generation time while the job bills at acceptance. Expiry is
read locally from the recorded `expiresAt` or the url's own `?e=<unix>` (zero API calls); an expired url FAILS, one lapsing
inside a generation's p95 WARNs, and the fix is free: `monid_upload.py --refresh <NAME> --go`.

Rules live in `<project>/prompts/refs-required.json`
([template](references/refs-required.example.json)): each element the prompt matches needs its reference
ROLES present AND uploaded for the target; every capitalised subject is ruled, born in this gen
(`--births`) or a conscious prose-only decision (`--prose`); a start image needs its own accepted record;
negated clauses are not elements. The gate opens the files, not only the names: every cited reference is
re-hashed against its registration (a file changed after acceptance FAILS), decoded and sized; light or grade
language in the prose with no look plate cited FAILS when the rules list `look_plates` (`--prose LOOK` keeps a
prose-only light on purpose); a cited reference nothing in the prompt depends on WARNs as COMPETING — an older room
plate beside an exact start frame competes with it. `require_ref_files` and `require_ref_acceptance` turn the
unregistered and unaccepted WARNs into FAILs, and a new project sets both. What an image SHOWS stays the acceptance
note's read: a detector that returns confident false positives would pass the wrong reference with a number beside
it. The gate's table is pasted into the cost/GO ask; `REFS-GATE FAIL` means
no submit. Add a rule the moment an element gets a locked reference — a sheet ruled for one scene and not the
next costs a round.

**Done when:** the table reads `REFS-GATE PASS` for the exact `--refs` and start image the submit will
use, and it is in the GO message.

## 5. Close the loop on the keeper

When the operator picks a seed: record its last frame as the next shot's start state (step 1), crop any
new keeper-derived references and record their derivation (`--record NAME --derived-from KEEPER`), and
write the handoff row in the ledger. On the seed itself continuity is the FIRST acceptance row — the
geometry across the take's own cuts and against the established shots — and a break rejects the seed
before its gag is judged; that read is the take review's, the ledger update is this skill's.

**Done when:** the keeper's `after` column is filled, every crop from it has a ledger record, and the next
shot's step 1 can start from the table alone.

## When continuity breaks — the repair ladder

Cheapest first; the full ladder with what did NOT work is
[`references/REPAIR-LADDER.md`](references/REPAIR-LADDER.md):

1. **Backfill** — rebuild the references from whatever is accepted; regen only the failing shot.
2. **Extension** — continue the keeper from its last frame (a video-extension mode on the keeper's own
   job): room, wardrobe, framing and props carry by construction.
3. **Insert** — a cutaway that explains the break (passage of time; where the prop came from).
4. **Start ON the establishing frame** — a punch-in on the same axis; never a reverse angle when
   continuity is the note.
5. **Punch-in or reframe at the finish** — a stale state that framing reveals leaves the frame for free.
6. **Drop or reframe the beat** — a state the model cannot render (one it overrides on seed after seed)
   gets a framing where it cannot appear, or the beat is cut.

**One continuous action is ONE generation.** A frame-perfect chain of separate gens still reads as a
stitch — each gen re-decides pace, drift and light — so size the gen to the whole action and cut only
where the script cuts. And a shot whose last state hides the face (a headstand, a face-down fall) cannot
be continued by a gen: write the face into the last frame, or continue from the take's own footage.

## ❌/✅

```
❌ "@ref2 the middle one, red-ginger, long face"          # the words beat the picture
✅ "@ref2 — take his complete appearance from his sheet and change nothing"

❌ A fresh still of "the same room" for shot N+1
✅ An edit of shot N's keeper frame with only the scripted change

❌ Prose geometry — "the door is on the far wall opposite the sofa"
✅ Upload the frame; copy the door sentence from the geometry record, never re-derive it

❌ A reverse angle's geometry written from memory of the wide
✅ `scene_proxy.py` through that camera; the row says door RIGHT, lamp beside it, sofa OCCLUDED — copy it

❌ A reverse angle to fix continuity
✅ A push-in starting ON the establishing frame

❌ Lettering pasted by hand on a figure
✅ Generated into the reference; copy route; knit composite last, checked at 4× in position

❌ The magnified silhouette sheet as the size reference
✅ An in-world crop beside a known object; the sheet's role is shape and colour only

❌ Room ref + the same character's single ref
✅ The room ref alone carries her; count every named character once at 2×

❌ Four gens chained frame-to-frame for one action
✅ One take sized to the whole action

❌ "The refs are probably in" → submit
✅ REFS-GATE PASS in the GO ask, for these refs and this start image

❌ A grade sentence in every prompt ("warm low sun, long shadows…")   # twelve prompts, twelve drifts
✅ One look plate per light context, look-only role; counts stay in prose

❌ A client's approved photo recorded as a keeper take to pass the lineage rule
✅ `--import` it with its provenance — a lineage root of its own

❌ "The refs are named and uploaded" → submit
✅ Registered, unchanged since acceptance, accepted for its role — and one still from the same set read first

❌ "Both boards are WRONG" — a note about an asset name
✅ The note names the hash-suffixed file; the re-roll that fixes it clears the note
```

## Failure behavior

- A still with no gate record, or not accepted, **fails** the gate: regenerate it through the gate, then
  accept it. A fresh upload is not a bypass.
- A start image whose lineage reaches neither a keeper nor a client-supplied import **fails** unless
  `--fresh-scene` is declared, and that declaration appears in the GO ask.
- A registered reference whose file changed since acceptance **fails** — re-check it for its role, re-register,
  re-accept. Unregistered or unaccepted references warn, and fail where the rules require files and acceptance.
- Light language in the prose with no look plate cited **fails** once the rules list `look_plates`.
- Every composite script prints a `check` crop; a composited piece that cannot be identified at 2× is a
  defect.
- When correction rounds on one element stop converging (three rounds), stop generating and ask the
  operator for the asset or the framing.
- `scene_blockout.py` fails closed — server down, node or checkpoint missing, job failed — with the route's
  own reason; the GO ask then says "no scene proxy for this shot" and the row is read off the frame. Never
  write geometry from memory and call it computed.

## Cross-references

- `video-finish` — the finishing chain; it starts only after a seed is APPROVED (no upscale before
  approval).
- [`references/ASSET-HYGIENE.md`](references/ASSET-HYGIENE.md) — citations vs assets both ways, two-SSOT
  sync, superseded assets, defect notes keyed to the file, counts derived never retyped, derived artefacts
  fingerprinted.
- [`references/SCENE-PROXY.md`](references/SCENE-PROXY.md) — the keeper frame as a labelled grey-box scene:
  build, read from any camera, the proxy clip, what to expect wrong, the hygiene.
- `~/.claude/skills/video-production/references/CHAIN.md` — handoff budget and stop conditions.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
