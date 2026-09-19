# Dialects — the per-venue prompt contracts

Global rules bind every dialect; a dialect lifts one only by naming the exception. Sources: ByteDance's
own Seedance 2.5 optimizer spec (`sd25-pe`, the vendor's compiler spec, 92 KB), the ten-model dialect
library (`video-prompting-skill`), the BytePlus 2.0/2.5 guides, fal's 2.5 guide, and our measured runs.

## Global rules

- **G1 — parameters never in the prose**: model name, version, duration, aspect ratio, resolution, frame
  rate, the audio toggle, API field names. Exception: timing that a dialect's schema requires (H3 shot
  timestamps; Seedance cut budgets when the shot document pins beats).
- **G2 — one line by default**; structured layouts only where the schema is structured (H3 fields; the
  Seedance 【】 block; screenplay dialogue on LTX).
- **G3 — for image-to-video the image is the anchor**: write motion, camera, performance, sound and what
  must CHANGE; never re-describe the frame.
- **G4 — the shortest duration that fits the action**; never a model's maximum by default.
- **G5 — observable direction, not adjectives**: subject placement, camera height, light direction, motion
  speed, performance, sound. "cinematic / dynamic / epic" steer nothing.
- **G6 — negatives are targeted**: a specific likely failure, or nothing; on Seedance 2.5 the vendor
  sanctions only subtitles, BGM/audio, logos, watermarks (plus what the shot document asks for) — no
  quality packs, no generic blacklists.
- **Point, never describe**: a cited reference gets one narrow job and an exclusion, never adjectives
  (the most expensive lesson: the words beat the picture every time).
- **A genre dialect layers on the model's.** A creator-style / UGC spot swaps the style prefix, the camera clause, the
  light, the motion and the sound words for the phone-native dialect — the camera attributed, never named as a device;
  positive-spec only; the video-call register — and touches nothing about the addressing, the caps or the tail:
  [PHONE-NATIVE.md](PHONE-NATIVE.md).
- **A held vendor spec is indexed by FEATURE, not only by the rules you came for.** Six consensus rules
  were extracted from the vendor's prompt-optimizer spec; two whole features (the storyboard grid, ordered
  keyframes) sat unread beside them for a week because nobody had a question that named them. On
  adoption, enumerate every feature the spec documents into the dialect table, even those with no use yet.

## Seedance 2.5 (Higgsfield CLI `seedance_2_5`; Higgsfield API `bytedance/seedance-2.5/*`; fal `bytedance/seedance-2.5/*`; monid `bytedance /v1/video/seedance-2.5`; treg `reapi.video-gen.seedance-2-5.unrestricted` — five routes to one model; which shot goes where, each contract and each measured rate are `video-gen-cost-gate/references/VENUES.md`)

- **Modes**: `t2v` · `omni_reference` (r2v: start image + ≤30 image refs + ≤10 video refs + ≤10 audio, ≤50
  total — on the Higgsfield CLI; fal and the Higgsfield API split i2v and r2v into separate endpoints that
  cannot be mixed) · `video_edit` ·
  `video_extension` (`--extension_mode forward`, the keeper's job id as the video reference).
  On **fal** all three reference modes are the ONE `reference-to-video` endpoint selected by a `task` enum
  (`reference` / `editing` / `extension`); `editing` coerces `aspect_ratio` and `duration` to `auto`,
  `extension` coerces `aspect_ratio`. There is no separate edit or extend path there (VENUES.md § Video).
- **Addressing**: `@Image1 @Video1 @Audio1`, numbered per type in upload order — verify the order before
  citing; emit `@Image1` without a space. The start image is passed on its own flag and referred to as
  "the start frame".
- **Roles**: `@ImageN is used for <subject>'s <appearance, clothing, structure or material>; do not use
  <background, pose, lighting, text, camera angle>`. Never let an image and a video compete for one job.
  One line per subject — never a range ("A and B reference @Image1 and @Image2"). Multi-view refs of one
  subject: give each view a role and state the entity count ("all three images show one person; exactly
  one appears"). Unused uploads: `【Unused Assets】 @Image5 and @Image6 do not participate…`.
- **Layout (complex shot)**: `【Generation Goal】【Reference Asset Roles】【Subjects and Relationships】
  【Event Script】【Maintain Consistency】` + the sound line. The vendor's default event script is STAGES
  with end states (`At the start / Principal event / At the end`); numeric segments only when the author
  wrote them (they are event budgets, whole seconds, contiguous, no overlaps, no "nods three times in one
  second"). The house template uses `Cut N (t–t s)` because the shot document pins beats.
- **State inheritance is the core**: each beat starts from the prior beat's physical result (which hand
  holds what, doors open or closed, counts after transfers, screen direction); cause before reaction;
  occlusion restated ("what reappears"); the hidden interval is never a reset; handoffs state single-object
  ownership ("at the end it is only in her hands"); end deliberately (positions, composition, residual
  motion, hold).
- **Sound markup**: `( )` music · `< >` sound effects · `{ }` dialogue · `【 】` subtitles (ASCII `()`).
  Dialogue: `language + delivery + speaker + {line}` per speaker; "the other characters keep their mouths
  naturally closed"; for no-dialogue shots constrain speech, lips, sound sources and visible text together;
  vertical output produces spurious subtitles — "no subtitles on screen" is a sanctioned negative for every
  9:16 prompt.
- **Supplied-audio polarity**: when `@AudioN` carries the words they must NOT appear in the prompt at all —
  direct the lip-sync to the asset and forbid replacement speech. Text-authored lines are quoted. Written
  dialogue beats reference audio (the audio supplies timbre only) unless the user asks to reuse the words.
- **Edit / extend are phrasing, not flags — and on fal they are BOTH**: the `task` enum tells the gateway which
  mode to bill and which fields to coerce, and the prompt still has to tell the MODEL what to do. Setting the
  flag without the wording below still generates a NEW video. `Video edit: … @Video1 is the sole editing master … Except
  for the objects explicitly modified above, all other visible characters, props and background elements
  in @Video1 remain unchanged` (the scope-closure sentence is mandatory); `Extend @Video1 forward. The first
  frame of the extended segment directly continues from the final frame of @Video1 …` + the single-instance
  sentence ("the same subject remains one continuous object, without duplication or splitting"). Without
  such wording the model generates a NEW video — billed in full, no error. A target aspect/duration that
  differs from the reference video routes to generation with `Please note that this is not video editing.`
- **Keyframes**: `Use @ImageN as the first frame.` / `…as the last frame.` verbatim, standalone, never
  softened to "composition reference"; first and last frames share an aspect ratio.
- **Look plate**: an abstract full-frame field of light and colour cited by every shot in that light —
  `@ImageN is the look: take only its light, palette and contrast; never its content, framing or
  subject`; counts and accents stay in prose (`video-refs-continuity` § look plates). A prompt that also
  restates the plate in prose pays twice for one instruction (L23); dropping the grade prose for a bare
  "Grade exactly to @ImageN" is untested — keep the prose until the removal is measured.
- **Layout-only role (a grey proxy STILL)**: `@ImageN is the layout and camera reference only: take where each person and piece of furniture stands in the frame and how the frame is framed from it; never its grey boxes, black void or materials` — tested 2026-09-10 on Nano Banana Pro (an end still) and on Seedance r2v (frame 0 opened on the new angle; on H3 as `<Picture 3>` under the same sentence it was IGNORED — frame 0 = the picture the prompt calls the whole frame, 09-10, n=1 — so on H3 bake the angle into a real still first and cite that still as `<Picture 1>`); the layout sentence beside it is copied from the proxy's table (`video-refs-continuity` SCENE-PROXY.md § One geometry, three channels).
- **Storyboard grid** (vendor-documented, `sd25-pe`): ONE slot holding a grid of ≤ 15 panels for the whole
  clip, with a verbatim reading-order statement and the vendor's exclusion clause — sketch style, text
  annotations and placeholder characters are NOT content. Draw the figures as deliberate placeholders: at
  twelve panels each figure is ~200 px, exactly the scale at which a bad identity reference is worse than
  none, so identity stays with the character sheets and the grid supplies beats and staging only. Accuracy
  in the storyboard is the failure mode, not the goal. The ordered multi-keyframe form (`@Image1 … @ImageN`
  as staged states) is the high-fidelity counterpart. A board-vs-no-board A/B was generated and never read:
  the grid's beat-adherence gain is unmeasured.
- **Spatial relations anchored to stable objects** ("inside of the counter, facing outward"), never only
  screen-left/right. A clean blocking diagram may fix positions, but arrows, boxes and text in it are NOT
  content — and on our runs 2 of 3 takes rendered such labels into the scene; keep blocking in prose.
- **Camera**: `move + subject + start + direction + arrival`; one move per shot; a term with inconsistent
  meaning (rack focus, dolly zoom, shallow depth) expanded into its observable result. With a scene proxy
  (`video-refs-continuity` SCENE-PROXY.md) the clause is DERIVED from the authored move —
  `scripts/camera_clause.py` gives the move, its magnitude (orbit °, pan °), the lens class and the pace —
  and it is written per CUT: a single-camera sentence beside a reference video that cuts contradicts the video
  it ships with. A grey-box proxy clip in a `@VideoN` slot takes a motion-only role — `@VideoN is the camera and
  blocking reference: take only its camera motion, framing and timing; never its grey geometry, grid, markers or
  materials` — tested 2026-09-10 on Seedance 2.5: the line kept every grey material out; beside a start image
  the camera followed the clip ≈3° of 25°, with refs only ≈55 %, and an object the proxy lacked was removed
  from a take; the clause carries the arrival, the clip rides only complete and never beside a start image
  (L26; `video-refs-continuity` SCENE-PROXY.md § proxy clip).
- **Emotion**: trigger event → immediate observable reaction → the few clearest cues (eyes, brows, mouth,
  breathing, hands) → the target expressed outwardly; a causal reveal shows the trigger BEFORE the reaction
  and keeps both in frame or links them by an eyeline.
- **Wire limits**: 480p / 720p (/1080p on the Higgsfield CLI and on treg — never on the Higgsfield API);
  duration 4–30 s (integer on Higgsfield, or `auto` on fal); prompt ≤ 6000 chars (≈ 2.5–3.2 k worked; > 5 k
  warned; 7840 was trimmed); `ratio` adaptive by default; public https or asset ids on the wire (the
  Higgsfield CLI uploads by UUID); result URLs expire ~24 h.
- **The monid wire shape is NOT the @-flag shape — the DIALECT above is unchanged, the CALL is not.**
  One `content[]` array carries everything: a `{type:"text"}` item holding the whole prompt, then one
  `{type:"image_url", image_url:{url}, role}` per picture with `role` ∈ `first_frame` · `last_frame`
  (only alongside a first frame) · `reference_image` (≤30), plus `video_url` / `audio_url` items (≤10
  each, 2–30 s, ≤30 s total) under `reference_video` / `reference_audio`. **Ordinals are numbered per
  TYPE in ARRAY ORDER, and a first_frame is still an image** — so a start frame occupies `@Image1` and
  every reference shifts by one; `video-gen-cost-gate/scripts/monid_submit.py` prints the resolved map
  before the GO, because a prompt citing the wrong ordinal generates cleanly and bills in full. `ratio`
  is accepted ONLY for t2v and r2v: first/last-frame, video edit and extend inherit their source's
  aspect and REQUIRE `adaptive`. Pictures ride as public https URLs, which monid's own `sfs` store
  issues for $0.00 (`monid_upload.py`) — so nothing here is blocked on "it needs a public URL".
- **The Higgsfield API and treg wire shapes — the DIALECT above is unchanged here too.** The API has five
  dedicated endpoints and no `mode` flag (`hf_api_submit.py`): i2v takes `image_url` [+ `end_image_url`] and
  r2v takes `image_urls` ≤30 + `video_urls` ≤10 + `audio_urls` ≤10, at least one required, so a start image
  never rides beside references there; `video-edit` omits `duration` (the source decides). treg's `reapi`
  row does r2v and i2v in ONE body, with lowercase `@image1` / `@audio1` placeholders in the prompt, and a
  placeholder for media you did not attach is a 400 (references hosted by `treg_host.py`). Caps, prices and
  moderation per venue: `video-gen-cost-gate/references/VENUES.md`.
- **Moderation is on the prompt WORDS**: "penis", "dick", "thrusting" → `nsfw` on the whole batch
  (refunded); a woman looking a man up and down → nsfw on 2/3; a bare-torso waist frame or a headless
  start image → refused unbilled; ALL-CAPS script words trip the refs gate's subject scan. fal additionally
  refuses any photoreal person in a reference (venue-level). Slapstick passes when injury words are avoided
  ("sweeps him clean off his feet and out of the right edge of the frame"; not hit/strike/crush/knocked out).
- **Native audio** (2.5 on Higgsfield): the take's bangs, clangs and knocks ride in it — name them in `< >` and
  keep `generate_audio` on; 2.0-era runs returned silence on no-dialogue shots (per-version flag).

## Seedance 2.0 fast (draft engine; fal; monid `bytedance /v1/video/seedance-2.0-fast` — priced but **NOT adopted**, see `video-gen-cost-gate/references/VENUES.md`)

- Same contract as 2.5 except: `Shot 1:` storyboard line, **never numeric timestamps** ("does not respond
  to timestamps"); slots 9 img / 3 vid / 3 aud (identical to H3, so a refused job recompiles to H3 without
  re-selecting references); duration integer 4–15; no `output_format`; half the price per token;
  `Reference <Subject_N> in <Image_N>` phrasing; multi-view refs not recommended (read as twins); refuses
  real faces; audio cannot be the only input.

## MiniMax H3 (fal `minimax/h3/reference-to-video`, 768P minimum)

- Modes `t2va · i2va · fl2va · l2va · reference`; the schema branches on mode. Base: three fields in
  order, blank-line separated — `integrated_multimodal_description: [Shot 1] …` / `overall_soundscape:` /
  `non_diegetic_music:`. Full-reference: `subject_definitions · summary · retention_analysis ·
  detailed_description · overall_soundscape · non_diegetic_music`.
- Labels: `<Subject N>` (defined once, its source pictures cited INSIDE the definition — one subject per
  ASSET), `<Picture N>` (a concrete frame), `<Video N>` (camera motion is a Video relationship), `<Audio N>`;
  each label exactly one definition, one `retention_analysis` entry (`fully_preserved · partially_preserved
  · attribute_transfer · weak_reference`), at least one use. A look plate is `attribute_transfer`, never
  a subject — the expander classifies it so unprompted; by hand it took three attempts.
- **Describe an identity by BIOMETRIC traits, never by beauty adjectives.** A `<Subject N>` definition built
  from generic attractiveness language — "attractive Caucasian young woman", "soft oval face", "straight
  slender nose", "flawless skin" — is reported to activate the model's generalised beauty prior and OVERWRITE
  the face its own reference carries, so the take drifts toward a generic pretty face while the citation looks
  correct. Write what a passport would record instead: the actual nose shape, the jaw, the eye colour and
  spacing, the hairline, asymmetries, marks, age in the face. The reference supplies the likeness; the words
  must not compete with it (L33). ⚠ **Reported, not measured by us** — an upstream RefMod guide's claim
  (the RefMods-vs-reference-images guide in the `malcolmrey/various` HuggingFace dataset, § 7.4), adopted
  because the behaviour it asks for is better prompting whichever way the mechanism turns out. To settle it
  yourself: same seed, one take with biometric phrasing and one with beauty phrasing, both citing the same
  identity still; read the faces at 1:1, not downscaled.
- Dialogue VERBATIM: `(S1)` ids by first vocal event, `<d>[English] …</d>`, never invented; `<scenetrans>`,
  `<cutoff>`; visible text in double quotes. Silence is three-valued (`N/A` in both sound fields only on an
  explicit request).
- `[Shot 1]` untimed; later shots `At 00:03.500` strictly increasing inside the duration.
- A `<Video N>` motion reference gets the timecoded form — `[0.0-1.8s] The camera pushes in toward the
  subject. [1.8-3.6s] It arcs right.` — ONE sentence when the move is one continuous phase (inventing phases
  describes a shot nobody authored), and the role sentence `Use <Video N> only as the camera-motion and
  shot-timing reference; do not reproduce its proxy geometry, grid, markers, textures or colours`
  (`camera_clause.py --h3`). Tested 2026-09-10 (Higgsfield, 2K): with `<Video 1>` the camera ran ≈ the full
  authored arc and the room held, 2 of 2 seeds; the clause alone re-staged the shot from behind a sofa that was
  not in the reference, and a "static camera" with no `<Video N>` became an invented push-in — a move with a
  scene proxy ships the clip, always (L27) — a static shot too: a static clip (`scene_proxy.py --move "A -> A"`, clause
  "holds a locked, static frame") held the camera at 54–66 dB with frame 0 on the keeper (09-10, n=1).
  **The role sentence and the clip are ONE unit — ship both or neither (L31).** It is a negation, and H3 has no
  negative stream: with the clip dropped but the sentence left in, the model rendered the nouns it names — a
  floor/ceiling grid and cyan/red markers on every take (local weights, 2026-09-11). Delete the clip, delete the
  sentence. Conversely, a **small** clip is nearly free and beats no clip: a 384×672 ×56 f proxy cost +14 s on a
  170 s take (~8 %) and gave the best still-lock and camera hold measured, where a full-size 768×1344 ×124 f clip
  cost **2.7× per step** — reference tokens ride every sampling step (L27 refined).
- **Local venue (open weights through ComfyUI)** — the dialect is IDENTICAL (same schema, same labels: verified
  against a community shot built the same way), with three deltas the hosted venue hides. (a) No rewriter: text
  reaches the tokenizer verbatim, so every wording rule here applies at full strength and L31 becomes a FAIL
  rather than a nuance. (b) Dialogue must carry the trained envelope or the tag is spoken aloud —
  `(S1) says: <d>[English] We are <i>going</i> to do <i>incredible</i> things!</d>`, speaker id and `[English]`
  included (L32). (c) `retention_analysis` can RELEASE as well as lock: supplying a voice reference for timbre
  and then declaring cadence NOT preserved is how a good reference stops producing a monotone delivery.
  Two tag conventions are in circulation and **both work — they are equivalent, so pick one and be
  consistent**: parenthesised `(laughs) (sighs) (inhale) (clear-throat)` and angle-bracket `<sighs> <chuckle>
  <whisper>…</whisper>` each place a non-verbal vocal event at the same point with near frame-for-frame
  identical envelopes, and **neither tag is ever spoken aloud**. Measured against a no-tag control, which was
  digitally silent in that window — without that control "the two takes differ" is uninterpretable, because
  any prompt-token change reshuffles a generation. ⚠ One tag word, one config, one take per arm, and it
  establishes a non-verbal EVENT, not that the event sounds like the word. That needs an ear. Recipe, cost and config for this venue: `video-gen-cost-gate` references/LOCAL-H3.md.
- `prompt_expansion_mode` REWRITES the prompt (2295 → 3424 chars on `fast`) and invents reference
  descriptions; the rewriter re-derives definitions even on `fast` — persist and diff `expanded_prompt`.
- Wire: duration 5–15 s integer (bills the requested integer); ≤ 9 images (+$0.04 past five), ≤ 3 videos,
  ≤ 3 audio; data URIs accepted; no bitrate parameter (buy pixels: 768P floor).
- **Performance and staging** — upstream-verified on the OPEN-WEIGHT model through ComfyUI, where text enters
  the tokenizer verbatim (`h3-storyboard-skill` `SOURCES.md`, controlled comparisons 2026-08); hosted H3 sits
  behind a rewriter, so the wording rules carry that caveat and the model rules carry none; Seedance UNTESTED:
  - Count expression beats before writing. More than two or three in one shot average into a still face (nine
    beats in one 7 s close-up: 37–42 dB at the peak; the same beats as three 2–3 s shots, one each: 22–23 dB,
    every beat landed). A cut is itself a performance — split at 2–3 s, one main beat per shot (L28).
  - `<d>` does not move faces; it REALLOCATES screen time to the shot carrying the line (55 → 84 frames of a
    74-frame spec) and squeezes its neighbours (56 → 42 — a background character vanished). Dialogue shots and
    background-continuity shots go in separate clips, or both versions are run and cut. Beside a static
    `<Video 1>` the line still lands — verbatim by whisper, the mouth open on it, the camera at 50–60 dB (H3G, 09-10, n=1).
  - Never write "nothing changes / stays where it is" as a shot's state: the stillness leaks across the shot
    (L29). A pause is an edit — end shot A on the stop, open shot B on the reaction.
  - What a character looks at is in frame, or they look at the lens: move the CAMERA to the gaze target
    (`video-refs-continuity` CONTINUITY-AXES § Eyeline), never a head-turn against the story; then forbid the
    lens look in words.
  - An emotional turn written A→B crossfades into rubber-face. Hide the change behind an occlusion (eyes
    closed, head down, a hand, a cut) and open onto the new state; reverse-beat first (tighten before the
    release); the trigger sits in the same or the adjacent shot. A reference-pinned design change swaps the
    same way behind closed eyes.
  - Size and spacing by CROP relationship, never a fraction or a unit ("two thirds as tall" → 45–52 %; "ears a
    palm below the top edge, the base cut by the frame" → 69 %; "a hand's width" is ignored — an in-frame
    object is the ruler) (L30); never name an object that must not appear (it grows); a shape text cannot hold
    → a blank shaped reference image.
  - Dialogue is budgeted by SHOT: the mouth runs the whole shot and ignores the next timestamp, so a
    post-speech beat (a swallow, "finishes speaking") goes to the next shot, and a dubbed line's spoken length
    must fit the shot, not the gap to the next beat (H3G: a `[1.0-3.8s]` line ran 3.2–4.6 s).
  - `<Audio N>` is a mouth-and-breath scaffold, not a voice: timbre lands ~2 semitones high with a narrower
    range and accent drift — the delivered voice is dubbed.
  - A silent STANDING subject in a presenting pose mouths a silent syllable in the first second on H3 (4 of 6 static
    takes, 09-10). **The cause is the START STILL:** frame 0 copies the picture the prompt calls the whole frame, so a
    still that catches the subject mid-word opens the take on an open mouth the model then works. Local, 2026-09-19,
    six paired seeds per arm, first-1.5 s mouth-open ratio (inner-lip gap ÷ mouth width): both stills mid-word 0.31;
    the same room still with ONLY the mouth closed 0.19 — lower on 6 of 6 seeds, shut through 1.5 s on 5 of 6.
    Accept a silent subject's start still with the mouth closed (`video-refs-continuity` § 3). What did NOT fix it:
    "nobody speaks" and "keeps his mouth naturally closed" (09-10), anchoring digital silence as the soundtrack
    (0.32), deleting every speech word (0.27, a little). The seated people held shut under "keep their mouths
    naturally closed". With no closed-mouth still to hand, trim the first second in the edit, or write the line.
    ⚠ One scene, our own measurement; not yet corroborated upstream.
  - **A quiet shot gets a CONCRETE soundscape, never an absence.** "the room's natural quiet; no speech, no music"
    left invented sound in 2 of 6 takes; "soft living-room room tone with a low ventilation hum continues
    throughout" with `non_diegetic_music: N/A` left it in 0 of 6 and calmed the mouth later in the take (median
    ratio 0.112 → 0.066; local, 2026-09-19). It is the community's standing advice too (hivemind, 2026-09-18/19;
    r/StableDiffusion "How to make H3 stop talking gibberish?"): H3 fills an empty audio lane with talk, so give it
    something to hear (L35).
  - Two pictures of one person did NOT draw him twice on H3: a room still that holds him plus his identity still,
    0 doubles in 48 local takes, bound in the prompt or not (2026-09-19). The room-ref rule of `video-refs-continuity`
    § 2 item 6 was measured on stills and Seedance; on H3 the binding sentence ("exactly as he stands in
    <Picture 1>") stays the house form, not a fix for a failure seen here.
  - Tail: the local model degrades 1.2–1.7 s before the end; two hosted 5 s takes did not (H3A flat to the last
    frame, 2026-09-10). Read every take's last 1.5 s with `video-take-review/scripts/frame_psnr.py` regardless.
  - Verify a beat with PSNR, not the eye: > 45 dB frozen · 30–40 breathing only (a failed beat where one was
    written) · 18–28 an action · < 15 a cut. The local `17n+5` frame grid and `Duration` snapping do not apply
    hosted (integer seconds).

## Create a Meme (web front-end to Seedance 2.5, operator-pasted)

- `@ref1…@ref9` by upload order, `[Video1]` for a motion clip; start + end frame outside the slots and
  usable WITH refs (the front-end's affordance, not the model's).
- **2000 characters, hard** — re-measure after every edit; the 【】 layout written out is 2501.
- Never press "Enhance prompt": it de-brackets tags, reorders clauses, hedges audio.
- The end frame is authoritative — write the prompt to it; it also replaces references when it carries the
  cast.
- Took the sheets fal refused (venue-level partner validation differs).

## Image models (stills, plates, references)

- **kie gpt-image-2.5 image-to-image** (the default still model since 2026-09-10; `-flare-` by default, `-sunburst-` the precision tier; the contract below was measured on gpt-image-2; the first 2.5 still (09-10, three refs incl. a grey layout frame) followed it — roles, preserve list, anti-blend, conflict priority — with no invented element): ref 1 is the edited image; cite the others by role; phrase as a
  transformation; preserve list; anti-blend ("do not blend any two references, do not average their
  builds"); conflict priority ("in favour of @ref1, then @ref2"); 1–3 refs each with one clear job;
  single-subject crops at native resolution (a montage blends into an average). Refuses the WORDS of some
  lettering, not the picture → the copy route (a lettered reference and no lettering words). Composes people
  from references without complaint; draws a 2 cm product piece as a dot on a wide (composite it instead).
- **kie nano-banana-pro** (the fallback): "change only this, count exactly that" — ignores sheets when composing; cannot
  move a figure; flags inputs carrying product pieces at large scale as sensitive; Google's moderator writes
  garment text the OpenAI one refused.
- **Start frames are pre-action** (has-just / about-to, never mid-stride or with the projectile in flight)
  and a coherent MOMENT (where were the bodies a second ago, where next?); a `FIRST FRAME AND BLOCKING`
  section with facings and depth order; a stillness lock naming what has not happened yet; lint for lineups
  (n subjects, similar depth, evenly spaced, facing camera). Generate clean at 480p — no grain, halation or
  chromatic aberration baked into a start frame, because the video inherits it.
- **Anatomy-word density** on the image leg: ~2 body nouns (the preserve list counts); the video leg gates
  on the DEPICTED ACT (throwing at a moving vehicle), not vocabulary.
- **Character sheets** are image-model artefacts: sheet → scene still referencing the sheet → i2v from the
  still; photoreal identity sheets keep asymmetry, age cues and skin texture ("the same person photographed
  repeatedly, not a redesigned digital asset"); crop to single views before any video upload.

## Where the venues differ — the compiler's core diff

| axis | Seedance 2.5 | MiniMax H3 |
|---|---|---|
| addressing | ordinal `@Image1` | typed `<Subject N>` with a definition |
| reference semantics | inline "controls only X; do not copy Y" | closed-enum `retention_analysis` |
| structure | prose or the 【】 block | fixed named fields |
| timing | contiguous cut budgets or stages | `[Shot N] At …` strictly increasing |
| supplied-audio dialogue | words must NOT appear | words verbatim in `<d>` |
| slot budget | 30 / 10 / 10, ≤ 50 | 9 / 3 / 3 |
| negatives | sanctioned classes only | global negative rules layer |
