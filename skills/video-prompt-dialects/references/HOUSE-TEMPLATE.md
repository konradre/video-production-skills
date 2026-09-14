# The house template — Seedance 2.5 ads, section by section

The prefix is glued to every prompt of a campaign; the 【】 sections follow the vendor's layout; the cut
budgets are used because the shot document pins beats. Below: the prefix, the skeleton of each section
with the shape every sentence takes, and the three situations the template has to cover. Placeholders sit
in angle brackets; the SHAPE of every sentence is the template.

## Prefix (one per campaign)

```
Photoreal live-action commercial, vertical 9:16, <the light: overcast soft daylight from the camera side>,
clean bright exposure, natural colour, no film grain, no on-screen text; the camera is already moving on
frame one.
```

The light clause changes per set ("warm domestic lamp light in a <room>"; "flat cool corporate light from
ceiling panels with cold daylight from the corridor beyond the glass").

**Two deliberate exceptions live in the prefix, and only there.** The aspect is a parameter, and "parameters never in
the prose" still holds everywhere else: the vendor's own layout carries the aspect in its style line, while resolution,
duration and the face-size checks stay in the shot's metadata and every other prohibition goes to the tail. The light
clause names the light CONTEXT, and the look plate for that context rides in the same prompt under a look-only role —
light described in words drifts prompt by prompt where a plate holds (`video-refs-continuity` § look plates; the refs
gate fails light prose with no plate once the project lists its plates).

## The skeleton

```
【Generation Goal】<the script's own sentences, quoted. A continuation opens: "The shot begins on the start
frame and continues from it without any cut: …">
【Reference Asset Roles】The start frame is <the wide / the first frame of this shot>: keep its room, camera
height, furniture, light, the <N> people, their places, their poses and their clothes exactly. @Image1 is
<the product>: <the exact product, its artwork and colours>; it is <where it sits in the start frame>.
@Image2 is <the product's SHAPE>, shown magnified: use the silhouette and those colours only, never the
size shown. @Image3 shows the SIZE of one piece against <a real object>; every piece is that size.
@Image4 is <a set element> exactly as it stands <where> in the start frame: <what never changes, moves,
recolours or multiplies>. @Image5 is <CHARACTER>'s face and clothes. … @Video1 is <the same character>
speaking in the previous shot: use the VOICE only — <they stay off-camera, to the left>, and nothing of
that shot's framing or room is used. 【Unused Assets】<@ImageN does not participate>.
【Subjects and Relationships】<N> people, only these <N>, exactly as in the start frame. <NAME>: <age,
build, hair, clothes; seat or position as THIS camera sees it; hands; state>. … <the room as THIS camera
sees it: the door in which wall, at which edge of the frame, facing which way; the furniture by side; the
light>. Nobody holds anything but <what the ledger says>. Nothing <transformed> before <the event>.
【Event Script】Cut 1 (0–2.0 s): <the framing on its own clause>: <what happens — cause before reaction;
the start = the previous shot's last state>. Cut 2 (2.0–3.5 s): <framing>: <t–t s: action; t–t s: action;
the hit named with its sound in < >; every eyeline a target; every hand placed>. … <the last frame keeps
the subject in it, small>.
【Audio】<Room tone; the named sounds; {line} per speaker in sentence case — "no other words from anyone";
"no music" unless scored>.
【Camera and Light】<N> shots with hard cuts at <t, t, t> seconds; slow push-ins on a steady gimbal; the
same <light> throughout; <camera height>.
【Maintain Consistency】<the door sentence copied verbatim from the geometry record>; <seats, wardrobe,
counts>; <the pose state carried: "after which X stays standing">; the product is only ever @Image1; <the
lock line for a fixed frame>; no <the campaign's exclusions>; no other people; no text anywhere.
```

## The negative tail — scoped by what the generation is

The tail's exclusions come in two blocks, decided per generation and never inherited from the last prompt:

- **Always on** — plastic or waxy skin, beauty retouching, added grain, on-screen text, subtitles, logos, watermarks,
  and whatever the shot document forbids.
- **One continuous shot of ≤ ~6 s only** — a hidden splice, an unmotivated cut, an abrupt push-in. A generation whose
  event script composes cuts, or that runs longer, omits this block: a long generation is bought for the coverage it
  composes, and a cut inside one generation carries consistency by construction, so forbidding cuts forbids the reason
  it was generated long (`prompt_lint.py` L34). Consistency across a composed cut is judged at review
  (`video-take-review`), never cut presence.

## The three situations

### A scene's opening — `t2v`, no references

The keepers of this shot become the references for every later shot, so the prompt carries what a
reference would: the cast closed and seated by name; the room described as THIS camera sees it with the
door named relative to the frame; the framing first in each cut; the cause (a knock) before the reaction
(every head turns); the reveal at the last frame; the tail carrying the exclusions.

### A one-gen scene state with internal cuts — `omni_reference`, a start image and several refs

The script is quoted as the goal; the start frame's authority is stated; every reference gets a role AND
an exclusion (the shape ref: "never the size shown"; the size ref: "every piece is that size"); every
count is written from the ledger ("six", "the same six"); the pose state is carried ("after which X stays
standing"); the line-deliverer's addressee is named. The lesson this shape carries: the wide and the
stand-up hold across seeds, but a close-up inside the same gen re-imagines background detail at that
scale — inserts get their own cropped start image (see `video-refs-continuity`). A long refs-only generation of
a whole continuity partition composes its own coverage: the cuts it makes inside the take are the consistency the
long take was bought for, so its tail omits the single-shot block.

### A bridging shot continuing a scene mid-line — a start image, one image ref, one video ref

The start image carries the SET; the video reference carries the VOICE ("use the VOICE only — he stays
off-camera in this shot, to the left, and nothing of that shot's framing or room is used"); the
off-camera speaker is written as heard-only; the one motivated movement is a target ("to his right toward
the glass wall"); the lock line in the tail ("no cut and no change of camera angle anywhere in the shot —
it is the start frame's viewpoint from first frame to last"). Seeds continue the voice and the room; only
the first ~1 s is used as the bridge.

## The ledger → subjects block

The 【Subjects and Relationships】 block is copied from the continuity ledger, per person: age · build ·
hair · clothes · seat/position as THIS camera sees it · hands · state; then "only these N people"; then
the geometry per cut. A colour scheme, a prop count, an accessory or a reaction the script does not state
is an invention.

## The pre-GO read of a prompt

Two questions per cut before any submit: does the camera see the FACE while the character sees the
CAUSE? does every face that carries a beat sit WELL ABOVE ~60 px of face height in the generator's native raster? ~60 px
is the FLOOR below which the generator cannot draw a face at all (measured at 480p, where clearing it well meant chest-up
or tighter; a take generated above 480p gets the same pixels in a wider framing), never a target: a face just over it
comes back under-rendered, and under-rendered reads as generated. The direction is community-consistent across current
video models — small and distant faces degrade, and face pixel count is the lever; the band client-accepted faces measured
in (97–121 px at 480p, against a rejected 68.5 px) is our own lead from one job, not a spec — on another generator or
native raster, the first takes' faces are measured before either number is trusted. Then: is every
noun traced, every eyeline a target, every hand placed, the door sentence copied, the framing on its own
clause, the first frame the previous keeper's last state, the negatives scoped to the generation's length, and the
light's plate cited?
