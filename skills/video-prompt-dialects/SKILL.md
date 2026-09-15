---
name: video-prompt-dialects
description: >
  Writes the prompt for a video or still generation in the DIALECT the venue speaks — Seedance 2.5 /
  2.0 (the 【】 template, @ImageN roles with exclusions, cause-before-reaction event script), MiniMax H3
  (typed Subject labels, verbatim dialogue), the Create-a-Meme front-end (@refN, 2000-char cap),
  kie gpt-image-2.5 / nano-banana-pro stills — from a shot document and its accepted references, then
  lints it before the gate. Use when a prompt is being authored or rewritten, when a venue refuses or
  misreads one, when "cinematic" or a negative list is about to be written, when a shot must continue
  a keeper or match a start image, or when the same shot moves to another venue. Triggers — "write the
  prompt", "prompt for this shot", "rewrite for Higgsfield", "the model widened the shot", "it rendered
  what I forbade", "nsfw on the prompt words", "lint the prompt". Not for the reference set or the
  start image the prompt cites — use video-refs-continuity. Not for the cost line and the submit — use
  video-gen-cost-gate.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3*), Bash(ls*)
---

# Video Prompt Dialects

A prompt is compiled, not written: the shot document supplies the facts, the accepted references supply
every visible attribute, the venue's **dialect** supplies the shape, and the prompt says only what neither
a reference nor a parameter can carry — who is which reference, what happens in what order, what the
camera does, what is heard. Three words carry the method: **dialect** (one venue, one schema — a
front-end's feature set is not the model's contract), **contract** (what the prompt may say: the
relationship between references, the action, the exclusions; never a description of a cited reference,
never a parameter), **tail** (the trailing exclusion region — the only place a prohibition steers instead
of injecting).

**What varies.** Each dialect is one model's contract at one version: its layout, its caps, the words its moderator
refuses and the beat density it renders were measured there, and a new model or version is read from its own docs before
its first prompt. The style prefix belongs to the campaign — its genre, aspect and look; a creator-style spot replaces it
with the phone-native genre dialect ([`references/PHONE-NATIVE.md`](references/PHONE-NATIVE.md): the camera attributed,
never named; positive-spec only; the video-call register), layered on the model's own contract. Pointing at references,
affirmatives in the body and the lint do not move — `video-production/references/WHAT-VARIES.md`.

## 1. Resolve the venue, mode and layout

| venue · mode | addressing | layout | cap | the divergences that bite |
|---|---|---|---|---|
| Seedance 2.5 (Higgsfield `omni_reference` / `t2v` / `video_extension`; fal r2v / i2v) | `@Image1…` per type, in upload order; a start image is passed separately | style prefix + the 【】 sections (below); numeric cut budgets when the shot document pins beats, stage form otherwise | ≈ 2.5–3.2 k chars works; 6 k wire; > 5 k warned | dialogue in `{ }` per speaker, or quoted in sentence case; supplied-audio words must NOT appear; edit/extend are inferred from wording (a plain reference request bills a whole new video); parameters never in the prose |
| Seedance 2.5 on monid (`bytedance /v1/video/seedance-2.5`, the pay-as-you-go route) | the same `@Image1…` dialect in the PROSE, but the call is a `content[]` array with a `role` per picture; ordinals count per type in array order, so a `first_frame` takes `@Image1` and the refs shift | as 2.5 above | **6000 chars, the model's own** | `ratio` only on t2v/r2v — first/last-frame, edit and extend REQUIRE `adaptive`; edit and extend are phrasing, and a plain reference request bills a whole new video |
| Seedance 2.0 fast | as 2.5 | `Shot 1:` storyboard line, never numeric timestamps | 9 img / 3 vid / 3 aud | half the price; refuses real faces |
| MiniMax H3 (fal, 768p min) | `<Subject N>` / `<Picture N>` defined once, cited in the definition; `Image 1` in prose | named fields in fixed order, blank-line separated; `[Shot N] At 00:MM.mmm` strictly increasing | 7 k | dialogue VERBATIM in `<d>[English] …</d>` — the opposite polarity; `prompt_expansion_mode` rewrites and invents — `fast`, persist and diff `expanded_prompt` |
| Create a Meme (web front-end) | `@ref1…@ref9` by upload order; `[Video1]` motion clip; start + end frame outside the slots | one paragraph | **2000 chars, hard** | never press "Enhance prompt"; the 【】 layout written out does not fit |
| kie gpt-image-2.5 (i2i, flare / sunburst — the default) · nano-banana-pro (the fallback) | ref 1 = the image being edited; "@ref2 the product" | prose: a transformation ("must appear 100 % identical to its own reference; only the pose, light and setting change"), the preserve list, the conflict priority, the exclusion per ref | — | gpt2 composes and copies; nano edits surgically and IGNORES sheets when composing; the words a moderator refuses go through the copy route |

The full contracts, wire limits and moderation classes: [`references/DIALECTS.md`](references/DIALECTS.md).
Parameters — resolution, duration, aspect, audio toggle — never appear in the prompt; they ride on the call.

**Done when:** the dialect is named, the reference slots are listed in upload order with their names, and
the layout (cut budgets vs stage form vs single line) is chosen from the shot document.

## 2. Compile the house template from the shot document

Seedance 2.5 ads shape, section by section — the worked examples are in
[`references/HOUSE-TEMPLATE.md`](references/HOUSE-TEMPLATE.md):

1. **Style prefix**, glued to every prompt of the campaign (photoreal live-action commercial, 9:16, the
   light, clean exposure, no grain, no on-screen text, "the camera is already moving on frame one").
2. **【Generation Goal】** — the script's own sentences, quoted; a continuation opens "The shot begins on the
   start frame and continues from it without any cut".
3. **【Reference Asset Roles】** — one line per reference: `@ImageN is X: use only its A, B, C; never its
   D` (a shape sheet: "the silhouette and colours only, never the size shown"; a size ref: "the
   size relative to the tie knot only"; a room ref: "its ground, furniture and daylight only"); the
   start frame sentence fixes the camera, the people, their places and clothes "exactly"; a video ref
   carries "his VOICE only — he stays off-camera"; a look plate's line is look-only ("take only its
   light, palette and contrast; never its content"). Unused uploads are listed as unused.
4. **【Subjects and Relationships】** — the ledger, per person: age, build, hair, clothes, seat, hands;
   "only these N people"; who faces whom; the geometry as THIS camera sees it ("the white front door in
   the far wall at the centre of the frame, directly facing the camera"); "nothing added to him" for every
   untransformed character. At most ONE anchor coordinate; everyone else by relationship.
5. **【Event Script】** — `Cut N (t–t s):` the framing FIRST on its own clause, then the action: cause
   before reaction (contact → motion → sound → response); the start = the previous shot's last state
   (standing stays standing; after a burst "blanketed and still raining, NO bang — the device already
   fired"); every eyeline a target ("eyes locked on the doorway at the right edge, never at the lens");
   hands placed ("the free hand up beside the head, held there"); the hit named with its sound in `< >`;
   a runner described from behind; the last frame keeps the subject in it, small.
6. **【Audio】** — room tone, the named sounds, the lines: `{line}` per speaker in sentence case (ALL-CAPS
   trips the gate; profanity trips the filter → a mouth-shape twin, dubbed later), "no words, nobody
   shouts" for everyone else, "no music" unless scored.
7. **【Maintain Consistency】** — the locked facts: the door sentence copied verbatim from the geometry
   record; seats, wardrobe, counts, the product "only ever @Image1"; the lock line for a fixed frame ("the
   camera never pulls back, tilts or widens; no object of any kind appears in the frame").

Rules that hold in every section:

- **Point, never describe.** A cited reference gets a role and an exclusion; any adjective about what it
  shows can only contradict it.
- **Referent + result, never mechanics.** One familiar, filmed motion ("moves like a cross-country skier")
  and the visible outcome; a category ("big wild animals") resolves to the wrong animal; joint-level gait
  words compose into a hop.
- **Affirmatives in the body; the tail carries the prohibitions.** `no head bounce` in the body rendered a
  bounce; `THEY DO NOT MOVE IN UNISON` rendered unison. Sanctioned tail negatives on Seedance 2.5:
  subtitles, music, logos, watermarks, and what the shot document explicitly forbids.
- **Negatives are scoped to the generation's length.** "No hidden splice, no unmotivated cut, no abrupt push-in"
  belongs to one continuous shot of a few seconds. A long generation — a whole continuity partition — composes its
  own coverage, and a cut inside it carries consistency by construction; those words forbid the reason it was
  generated long (HOUSE-TEMPLATE § The negative tail; LINT L34).
- **Never NAME an off-frame object** — the model widens to show it and invents it; write the look
  ("jabs a finger down, out of the bottom edge"); the name may appear only inside a quoted line.
- **Bind the camera to one subject or one fixed geometry**; a move that cannot hold its named subjects
  (a push-in while three diverge) is resolved by the model discarding the part you cared about. When a scene
  proxy exists, the clause is derived from the authored move (`scripts/camera_clause.py`) and written per
  cut — never one camera sentence for a clip that cuts.
- **Blocking in metres, on named floor and furniture sides** ("two metres in front of the cab glass",
  "along the left side of the table, on the carpet") — a step "toward camera along the table" walked on it.
- **Beat density ≤ ~1 beat per 3 s**; the model renders locomotion and physical state, not intent — plan
  comedy around situation, and shrink the beat count before shrinking the seconds.
- **The verb must be the scripted action** ("he drinks from the bottle", not "the others hold him") and the
  reaction's emotion matches its cause (shock, not joy, at a collapse).

**Done when:** every noun and action in the prompt traces to a script sentence, the ledger or a
reference role; every reference in the slot list has exactly one role line; the start state equals the
previous keeper's last state; and the lines are quoted in sentence case.

## 3. Lint before the gate

```
python3 scripts/prompt_lint.py --dialect seedance-2.5 --refs ROOM,W1,PRODUCT-sheet prompts/r2v/S02-G4.txt
```

Mechanical checks, each from an incident ([`references/LINT.md`](references/LINT.md)): slot ranges
expand with no double assignment, no gap, within the venue cap; negations in the body; ALL-CAPS tokens
outside the stoplist; the venue's moderation words; parameters in the prose; a named off-frame object;
category referents and gait mechanics; "aerial view"; camera move vs diverging subjects; a framing that
is not on its own clause; beat density; the char cap; a prompt that repeats a reference's description;
single-shot negatives on a long generation (`--duration`); and by eye, a look plate restated in prose and a
citation that resolves to no asset.
The lint is advisory except the slot and cap rows — but a warning row is answered in the prompt or in the
GO ask, never ignored.

**Done when:** `PROMPT-LINT OK` (warnings named) and the prompt file is the one the gate and the submit
will read.

## 4. When the venue answers wrongly

| symptom | cause | rewrite |
|---|---|---|
| `nsfw` within a minute | a prompt WORD, not the picture (an anatomical noun, "thrusting", a suggestive look described) | paraphrase the shape ("the exact @Image silhouette"); the profane line becomes a mouth-shape twin and is dubbed in the character's own cloned voice later; frame chest-up or knees-down, never the waist of a bare torso |
| a fresh bang at frame 1 | the prompt said "a few last pieces drift down" | "the room is blanketed, still raining, NO bang — the device already fired" |
| the shot widened / pulled back | an off-frame object named; a camera move that cannot hold the subjects | write the look, not the thing; bind the camera; lock line in the tail |
| the line-deliverer faces the lens | the default | write the addressee: "turns to his right toward the friend at the mantel and shouts at him" |
| the first word of a line dropped (2/2 under one layout) | layout-sensitive | put the line in `{ }` on the audio line; A/B a layout change same-seed before adopting it; whisper the takes |
| a label or arrow rendered in the scene | a schematic map as a reference | blocking in prose; geometry from frames |
| the model invented a description of the reference (H3 expansion) | `prompt_expansion_mode` | `fast`; diff `expanded_prompt`; roles with exclusions |

**Done when:** the rewrite names the cause row, the changed words are the only change, and the GO ask
says which row it answers.

## 5. Record and hand off

The prompt file lives beside the shot document (`prompts/r2v/<SHOT>.txt`, `prompts/stills/<ID>.txt`)
with its reference names in slot order in the shot list; the gate and the submit read the file, never a
pasted string. Hand to `video-gen-cost-gate` with the refs and the start image named.

**Done when:** the prompt file, the slot list and the shot-list row agree, and the cost-gate ask cites
the file path.

## ❌/✅

```
❌ "@ref2 the middle one, red-ginger, long face"          ✅ "@ref2 — take his complete appearance from his sheet and change nothing"
❌ "cinematic, dynamic, epic"                              ✅ "a slow push-in on a steady gimbal from seated eye level"
❌ "no head bounce" in the body                            ✅ "the head travels level"; prohibitions in the tail
❌ "moves like big wild animals"                            ✅ "moves like a cross-country skier: long strides, slow cadence, level head"
❌ "x 20 %, x 52 %, x 63 %, staggered in depth"            ✅ one anchor; "bunched, overlapping, one hand up on the red one's arm"
❌ "has just spotted his bag on the carpet (below the frame)" ✅ "looks down at the floor below the frame; nothing else enters the frame"
❌ "an aerial view of the ridge"                            ✅ "a wide landscape photograph from a high ridge top"
❌ "the camera pushes in as the three run apart"            ✅ "the camera stays on the largest one and makes ONE slow push"
❌ {WHO'S READY FOR SOME <profanity>?} (caps, the word)    ✅ {Who's ready for some… company?} → the real line dubbed in post
❌ "packed with dancing guests and the other women"         ✅ "the ONLY people in the shot are …; no other guests, no men"
❌ "medium shot, waist up" buried in the event sentence     ✅ "Cut 2 (4–7 s): medium on the lead from the front at eye level: …"
❌ "a selfie video, she holds up her iPhone"                ✅ "shot on a front camera, handheld, at arm's length" — the device named puts a phone in her hand
❌ "authentic UGC style, no studio lighting"                ✅ "window daylight from camera-left, a warm bulb over the counter, the frame drifting as she talks"
```

## Failure behavior

- A lint FAIL on slots or the cap blocks the gate; a warning row is answered explicitly.
- A refusal is diagnosed by listing what PASSED first and diffing against what failed — never by three
  hypotheses in a row.
- Three rewrites of one prompt without convergence → stop; the operator gets the alternatives as
  numbered questions (a different framing, an extension, an insert).

## Cross-references

- `video-refs-continuity` — the references and start image the prompt points at; the ledger the
  subjects block is copied from.
- `video-gen-cost-gate` — the venue table, the cost line and the submit.
- The vendor's own optimizer spec (`sd25-pe`) and the ten-model dialect library are cited in
  `references/DIALECTS.md`; read them when a venue not listed here appears.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
