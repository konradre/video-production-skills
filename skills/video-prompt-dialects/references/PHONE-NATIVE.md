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

## Name the camera that shot it — the device is the camera, never a prop (house rule, 2026-09-25)

Say how the camera moves first, even when it does not move — an unstated camera drifts — then name the device the
footage came from: the model matches the look to the equipment it is told shot it.

- ✅ "Handheld iPhone shot, the front camera held at arm's length, a wide lens with everything in focus, slight edge
  distortion from the close distance, the frame drifting a little with her breathing"
- ✅ "Static locked-off iPhone footage, the phone propped on the counter at chest height" — the phone set down: the camera
  does not move, and the prompt says so
- ✅ a produced register names the body that register implies ("a podcast set shot on a cinema camera") — the same rule,
  a different device
- ❌ "she holds up her phone", "her iPhone on the table beside the jar" — the device as an OBJECT in the scene gets drawn:
  a phone in her hand, a second phone on the table, a camera UI on the frame. `video-take-review` fails a phone or a
  camera UI in frame (ACCEPTANCE-MATRIX row 10), and the first take of a new prompt is read for exactly that — a
  community report has Omni Flash drawing a film strip when it was handed film-stock words.

This replaced "attribute the camera, never name the device", a rule from community skills that was never checked against
a control. Practitioners name the phone as the camera routinely, and the house adopted it without a test.

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
item 4). The presenter's first still is GENERATED (house rule, 2026-09-25): an authored persona, built in ONE image pass
and accepted against the persona checks in `video-refs-continuity` REFERENCE-CONTRACT.md § Generating an identity
reference — the framing committed, no clipped highlight on the skin, a background with a life in it, both hands natural,
no text over the face. Building the persona on a real person's photograph, edited until it is someone else, is the
practitioner route; the house does not use it.

## Environment

Persona-matched clutter; a lived-in room where the product is actually used; the subject off-centre; concrete anchors
("an out-of-focus fridge with magnets behind her"); the product in her hands, in use. Consistency is INTER-shot: the same
room, the same light, the same product between shots — the saturation drift 79 → 130 across shots was the environment
failing, not a shot (M).

## Sound

Room tone, an appliance hum, handling noise, a fingernail on the jar, breathy laughter, an auto-gain lift after a pause,
no music under the open, no noise reduction. **The sound follows the capture device the frame shows**: a clip-on or
wireless mic, or a headphone mic, in the still earns a clean, close voice; a bare phone at arm's length earns the phone-mic
register. A generator voices every line clean, so the device is chosen with the persona and drawn into the still (house
rule, 2026-09-25). A model that takes no audio input (Omni Flash 1.1, H3) invents the voice anyway: where a voice-over is
locked the line is dubbed and retimed in post, where none is the model's own voice can ship (§ Dialogue), and the words
that must land exactly go to an audio-driven model (`spot-audio-assembly` MIX-AND-QC.md § The phone-mic register;
`video-gen-cost-gate` VENUES.md).

## Dialogue on a model-voiced line — the stressed word, the line's length, the locked prompt

Where the model speaks the line itself (no locked voice-over), three rules (house rules, 2026-09-25, from a practitioner's
Gemini Omni workflow; the stress rule was demonstrated on camera there, and the community holds no signal on it either
way):

- **Stress a word by writing it in capitals** inside the quoted line — "so weak FOLLICLES wake back up" moves the stress
  onto that word. One or two words a line: a whole line in capitals reads as shouting, and `prompt_lint.py` L4 warns on
  it. The refs gate and the lint skip capitals inside a quoted or braced line, so a stressed word is never read as a
  subject. MiniMax H3 keeps its trained `<i>` inside the `<d>` envelope instead (DIALECTS.md, LINT L32).
- **Size the line to a duration the venue sells.** On a venue with fixed steps (Gemini Omni on kie takes 4, 6, 8 or
  10 s) a line whose natural length falls between two steps is rushed or clipped at the shorter one; at the longer one
  Omni slows it (the practitioner's report), while another route rushed it and left tail silence (our own delivery read).
  Either way the fix is the same: end the real line with a full stop, add a throwaway sentence after it, buy the next
  step up, and cut at the pause after the real line (`video-take-review` § 3, the delivery row). That the full stop gives
  the cut its pause is inferred from the delivery row's own observation; it is unmeasured.
- **Lock the prompt after the first line.** Generate the script's first line, read it harshly, and fold each correction
  into the prompt as a positive statement — the energy ("bright and fast, the delivery of someone filming their own
  video"), the pace, the smile, the confidence, "one continuous take from the first frame to the last". Then freeze
  everything but the quoted line for the rest of the script: `prompt_lint.py --locked <first-line prompt>` warns on any
  difference outside the quotes (L36), and a deliberate change re-locks. An audio-driven head is the exception: its
  voice file carries the performance, so its prompt directs the frame only (`video-gen-cost-gate` VENUES.md § The
  talking-head default).

## An exemplar (Seedance 2.5 / Omni Flash shape — a sample of the dialect, not a template to paste)

> Handheld iPhone shot, the front camera held at arm's length: a woman in her thirties at her kitchen counter, a wide
> lens with everything in focus, the frame drifting slightly as she talks. Window daylight from camera-left, a soft shadow on
> the right side of her face, a warm bulb over the counter. She holds a glass jar of the product in her right hand, label
> toward the camera. 1. She glances up mid-sentence and keeps talking to the camera, relaxed, a little tired. 2. She turns
> the jar once to show the label and sets it down out of the bottom of the frame. 3. She leans in and laughs, eyes off the
> lens for a moment, then back. Room tone, a fridge hum, the jar tapping the counter. Chest-up framing the whole time; the
> frame is exactly as photographed from the first frame to the last.

## Per-model rows (dated evidence in `video-gen-cost-gate/references/VENUES.md`)

| model | what the phone dialect must know |
|---|---|
| Gemini Omni Flash 1.1 (and kie's `gemini-omni-video`) | no audio input on any surface — the model voices the line: ship its voice where no voice-over is locked (§ Dialogue), dub where one is; 3–10 s on fal, 4 / 6 / 8 / 10 s on kie; 720p native; ~15 % of takes stutter → regenerate; exact words cannot be prompted (it invented "dollars" twice, M) → OmniHuman or a lipsync pass; a negation burned captions (M) |
| Seedance 2.5 | the consistency model: ≤ 50 references (≤ 30 image refs on fal; on fal a start frame and refs are EXCLUSIVE); 30 s in one pass; word corruption on dialogue → repair with clean audio + a lipsync pass, never re-prompt; the label is drawn, never read — keep the jar as an image reference, the label shot short and front-on |
| Kling 3.0 Pro / Turbo | talking clips ≤ 8 s (lips and audio part company past second 8 — agency data + community); handheld micro-motion is its strength |
| MiniMax H3 | the dubbed tier: 768p minimum on fal; the mouth runs ~1.09–1.13× slow and starts ~0.75 s late against a VO take (M) → whisper-fit retime |
| Veo 3.1 | mouth-realism failure on dialogue — non-talking b-roll and proof shots only |

## Don'ts

Ask the model to read a label · the device as a prop in the hand · "cinematic" · a generic negative list · "authentic / photorealistic /
UGC-style" · a text or logo shot through a reconstructive upscaler (Starlight sharpened garbled badge lettering into
confident fake text, M) · a second person, a second phone, a mirror.
