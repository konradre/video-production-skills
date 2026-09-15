# Phone-native — the genre dialect for a creator-style talking head

A GENRE dialect, layered on the model's own contract (Seedance, MiniMax H3, Gemini Omni Flash — DIALECTS.md): what the
prompt says so that a generated shot reads as phone-shot by a person, not lit and framed by a crew. It changes the
words of the style prefix, the camera clause, the light, the motion and the sound; it changes nothing about pointing at
references, the tail, the caps or the lint. Evidence: the community skills and vendor guides behind each rule were read in a research pass in September
2026; our own measurements are marked **M**.

## The formula — prompt the SHOT, not the adjective

`camera + person + environment + product action + expression + lighting + imperfection`, in that order, each as an
observable fact. "Authentic", "photorealistic", "UGC-style", "cinematic", "8K", "professional lighting", "volumetric"
steer nothing or steer the wrong way (DIALECTS.md G5); the words that carry a phone shot are the ones a viewer could check
against the frame.

## Attribute the camera — never name the device

- ✅ "shot on a front camera, handheld, at arm's length, a wide lens with everything in focus, slight edge distortion
  from the close distance, the frame drifting a little with her breathing"
- ❌ "a selfie", "an iPhone video", "holding her phone" — the noun summons the OBJECT: a phone appears in her hand, a
  second phone appears on the table, a camera UI is drawn on the frame. `video-take-review` fails a phone or a camera UI in
  frame (ACCEPTANCE-MATRIX row 10). Say what the camera IS and how it is held; never what it is called.

## Positive-spec law — a negation summons what it names (M)

"No subtitles, no captions, no on-screen text of any kind" BURNED captions onto the subject's shirt on Omni Flash 1.1;
"do not reproduce the grid or the markers" rendered a floor grid and cyan markers on H3; the Seedance A/Bs read the same.
Say what the frame IS: "the frame stays exactly as photographed from the first frame to the last", "a camera fixed on a
tripod" (both held, M). Prohibitions go to the tail, targeted (G6), and only where a reference makes the negation safe
(LINT L31).

## Short numbered beats, one action each

≈ 1 beat per 3 s; the model renders locomotion and physical state, not intent. "1. She looks up from the jar and starts
talking. 2. She turns it to show the label, then sets it down. 3. She leans in and laughs." A ~10 s talking head is ONE
generation, never two stitched (the seam and the voice shift are what the viewer reads as fake).

## Light — named practicals, uneven on purpose

Window daylight from camera-left with a soft shadow on the right; a warm overhead bulb; a slight blue cast from an
automatic white balance; apartment-scale unevenness; a small exposure shift when she moves. Never a two-point softbox, a
ring-light catchlight, a single hard even key, or "even, professional lighting" — each is a produced-ad tell the audience
reads in a frame. The look plate for the light context (`video-refs-continuity` § 2 item 8) is the plate of the ROOM's
light, never of a studio's.

## Motion — the video-call register

Weight shifts, a head tilt, blink asymmetry, lip and jaw micro-adjustments, eye contact that breaks and returns, a hand
that adjusts the frame once, the camera dipping with a gesture. A torso that holds still longer than ~6–7 s reads as a
render — our frozen-frame instrument read 82 % near-frozen frames on a rejected cut against ~21 % on accepted ones (M).
No "cinematic" presets, no slider moves, no orbit.

## Skin, face, body

Pores, fine lines, stray hairs, a real haircut; skin that is never "smooth", "flawless" or "airbrushed". The face floor is
~60 px of face height in the take's native pixels (M) — chest-up or tighter on every beat the face carries; a face that
is small AND under-rendered fails at equal size (`video-take-review` INSTRUMENTS.md — face detail at equal size). The
character is frozen after the first keeper and re-used by reference, never re-described (`video-refs-continuity` § 2
item 4); a real arm's-length reference photo, upscaled first, is a community heuristic for less morphing — UNVERIFIED here.

## Environment

Persona-matched clutter; a lived-in room where the product is actually used; the subject off-centre; concrete anchors
("an out-of-focus fridge with magnets behind her"); the product in her hands, in use. Consistency is INTER-shot: the same
room, the same light, the same product between shots — the saturation drift 79 → 130 across shots was the environment
failing, not a shot (M).

## Sound

Room tone, an appliance hum, handling noise, a fingernail on the jar, breathy laughter, an auto-gain lift after a pause,
no music under the open, no noise reduction. A model that takes no audio input (Omni Flash 1.1, H3) invents the voice
anyway; the line is then dubbed and retimed in post, and the words that must land exactly go to an audio-driven model
(`spot-audio-assembly` MIX-AND-QC.md § The phone-mic register; `video-gen-cost-gate` VENUES.md).

## An exemplar (Seedance 2.5 / Omni Flash shape — a sample of the dialect, not a template to paste)

> A woman in her thirties at her kitchen counter, filmed on a front camera held at arm's length, handheld, a wide lens
> with everything in focus, the frame drifting slightly as she talks. Window daylight from camera-left, a soft shadow on
> the right side of her face, a warm bulb over the counter. She holds a glass jar of the product in her right hand, label
> toward the camera. 1. She glances up mid-sentence and keeps talking to the camera, relaxed, a little tired. 2. She turns
> the jar once to show the label and sets it down out of the bottom of the frame. 3. She leans in and laughs, eyes off the
> lens for a moment, then back. Room tone, a fridge hum, the jar tapping the counter. Chest-up framing the whole time; the
> frame is exactly as photographed from the first frame to the last.

## Per-model rows (dated evidence in `video-gen-cost-gate/references/VENUES.md`)

| model | what the phone dialect must know |
|---|---|
| Gemini Omni Flash 1.1 | no audio input on any surface — the voice is always dubbed; 3–10 s, 720p native; ~15 % of takes stutter → regenerate; exact words cannot be prompted (it invented "dollars" twice, M) → OmniHuman or a lipsync pass; a negation burned captions (M) |
| Seedance 2.5 | the consistency model: ≤ 50 references (≤ 30 image refs on fal; on fal a start frame and refs are EXCLUSIVE); 30 s in one pass; word corruption on dialogue → repair with clean audio + a lipsync pass, never re-prompt; the label is drawn, never read — keep the jar as an image reference, the label shot short and front-on |
| Kling 3.0 Pro / Turbo | talking clips ≤ 8 s (lips and audio part company past second 8 — agency data + community); handheld micro-motion is its strength |
| MiniMax H3 | the dubbed tier: 768p minimum on fal; the mouth runs ~1.09–1.13× slow and starts ~0.75 s late against a VO take (M) → whisper-fit retime |
| Veo 3.1 | mouth-realism failure on dialogue — non-talking b-roll and proof shots only |

## Don'ts

Ask the model to read a label · name the device · "cinematic" · a generic negative list · "authentic / photorealistic /
UGC-style" · a text or logo shot through a reconstructive upscaler (Starlight sharpened garbled badge lettering into
confident fake text, M) · a second person, a second phone, a mirror.
