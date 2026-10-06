# Realism — photoreal stills and photoreal footage

Read this file whole before writing any prompt for a live-action job: every reference still, start frame and look
plate (GPT Image 2.5), and every scene text for MiniMax H3 — written directly on fal or Higgsfield, or compiled by a
music-video front-end from one scene text. A governed project denies a prompt write until this skill is loaded (rule `prompts` in
`video-production/references/SKILL-GATE-TEMPLATE.json`); `scripts/prompt_lint.py` checks the mechanical part (L38–L41,
[`LINT.md`](LINT.md)).

The rule under every section: **describe the capture and the visible facts, never the quality.** A model left to fill
a gap fills it with its default render, and the default is the look that reads as generated.

## 1. Words

| ❌ never | ✅ instead |
|---|---|
| 8K, hyperrealistic, ultra-realistic, photorealistic, masterpiece, award-winning, stunning, highly detailed, best quality | the capture: "a real, unretouched photograph taken on a full-frame camera, 35 mm lens at f/2.8, ISO 3200, a 4-second exposure" |
| cinematic, epic — in a STILL prompt | the light and the lens they stand for; on H3 "cinematic" is an official style word and stays (§ 3.1) |
| moody, dramatic, beautiful light | where each source is, its colour, how far it reaches, what stays dark |
| a category ("a desert scene", "a campsite") | the visible facts: the ground, the plants, the distances, what is in the foreground |

- Fill every gap a viewer will look at; an element left undirected comes back as its generic version.
- State the light as physics: each source, its colour, its reach ("its warm glow dies within a couple of metres"), what
  falls to near-black. A night with no named source renders as a lit set.
- Name the real texture wherever the model's default is wrong: "rough, blackened, irregular fieldstones"; "fibrous,
  shaggy bark with dead leaves hanging"; "small, ragged, uneven flames". The default for many natural things is a
  smooth, rounded, evenly lit CG version.

## 2. Stills — GPT Image 2.5 (references, start frames, look plates)

### 2.1 The model and the route

- **Sunburst** for anything that must read as a photograph or survive an edit — a face, an approved composition;
  **Flare** for fast drafts. OpenAI rates Sunburst above GPT Image 2 and Flare level with it.
- **kie bills both the same** — USD 0.05 a 2K still, measured 2026-10-07 — so a photoreal reference is Sunburst:
  `gen_stills.py --model gpt25s`. kie has no `quality` parameter; the model and the words are the levers.
  Higgsfield `gpt_image_2_5 --variant sunburst --quality max` is the route with a quality setting (≈ 16.5 cr a 2K
  still; `video-gen-cost-gate` VENUES.md).
- kie's 2K lands 2736×1536 at 16:9, above OpenAI's 2560×1440 "experimental" line. A front-end that shrinks references
  (one caps them at 768 KiB) erases the difference; 2K is enough.

### 2.2 The prompt, in order

1. **The capture:** "A real, unretouched photograph taken on a full-frame camera, <lens> at <aperture>, ISO <n>,
   <exposure>."
2. **The subject and its visible facts** — an identity by biometric traits (face shape, nose, jaw, eye colour and
   spacing, hairline, marks, age), never beauty words (L33).
3. **The setting**, foreground to background, every element a viewer will look at.
4. **The light** (§ 1), then the night rules (§ 2.3) when it is dark.
5. **The frame** in words: "A 16:9 frame." The resolution rides on the call.
6. **The tail** — rendering faults and lettering only: "A clean, noise-free image. No HDR look, no glow or bloom, no
   over-sharpening, no oversaturated colour, no painterly or CGI rendering, no dramatic grading. No text, no
   watermark."

### 2.3 Night and low light

- Expose the way an eye sees the night, not the way an astrophotographer brightens it: ISO about 3200, a few seconds,
  "two stops darker than a typical astro photograph". ISO 6400 for 20–30 s is the photographer's recipe for making a
  night look bright.
- A Milky Way in frame: "visible but smooth, muted and low in contrast". A contrasty, saturated, sharpened galaxy is
  the processed-astro look that reads as fake.
- Keep the moon itself out of frame unless the shot is about it: say where the light comes from ("faint cold
  moonlight from high behind the camera").
- Darkness has a floor. Name what must stay readable ("the figure and the ground under it stay readable in the faint
  light"). Asking for darkness three ways at once — near-black shadows, true darkness, two stops under — buries the
  subject.

### 2.4 A clean image — grain is the video's job

No grain, sensor noise, halation, chromatic aberration or bloom in a reference, start frame or look plate: the video
copies it and then adds its own. Ask for "a clean, noise-free image" (L39). Grain belongs in the video prompt (§ 3.4).

### 2.5 Edits — make an accepted still real without losing it

- A still the operator already approved is EDITED, never re-rolled: "Turn this picture into a real photograph of the
  same place. Preserve the exact composition, camera position, layout and every object; change only how it is
  photographed and lit." Restate the keep-list; one change per pass.
- Measured (Sunburst, 2026-10-07): a whole-frame realism edit kept the layout and every approved detail and moved the
  exposure, colour, sky and textures toward a photograph — and an object the source drew as CG SURVIVED it (a
  campfire's smooth glowing stones and drawn flames; round, spiky "pom-pom" foliage). A CG object takes its own
  targeted edit: "Change only the <object>: <its real look>. Keep everything else exactly as it is."
- An identity reference edited for realism is a NEW file, and its stress lock lapses (`video-refs-continuity` § 3).
  Read the new face beside the approved one at 2–4× — face shape, eyes, nose, mouth, hairline, age cues, marks — before
  it replaces the old one anywhere.

### 2.6 Read a still for realism, at full size

The tells: smooth or glowing surfaces on things that are rough in life (stones, bark, skin); flames drawn as clean,
symmetric tongues; repeated, symmetric foliage; even, shadowless light in a night scene; a punchy sky; poreless skin;
hands. Each is fixed by a targeted edit (§ 2.5), never by re-rolling the whole frame.

## 3. Footage — MiniMax H3

### 3.1 The style first

- Open the first shot with the format, then the composition: "Live-action, cinematic, a medium close-up frames …"
  (MiniMax's own examples). The official style words: live-action, cinematic, 2D-animated, 3D CG, claymation,
  watercolor, vintage film. A style word alone does nothing — pair it with concrete light and lens (L41).
- Every sentence corresponds to something visible or audible; mood words and explanations do nothing.

### 3.2 The structure — H3's fields, or a front-end's one scene text

- Written directly (fal, Higgsfield): the fields in their fixed order (DIALECTS.md § MiniMax H3), 350–500 words a
  generation, the style before `[Shot 1]`'s composition.
- Compiled by a front-end (one scene text of at most 2,000 characters, about 300 words, plus a timed plan it turns
  into the `<d>` spans): the scene text carries, in order, the style sentence, the action in time order with its
  camera, the light, the realism line, the artifact tail. Over the cap, cut from the end — the tail first, the action
  and the camera last.
- Whether a front-end applies H3's prompt expansion is unknown until a take's own generation record shows the prompt
  actually sent: read it on the first take, and diff it against what was written.

### 3.3 Camera and cuts

- Camera = type + amplitude + speed, one natural sentence, from MiniMax's set: zoom in/out · push in / pull out · pan
  left/right · truck left/right · tilt up/down · pedestal up/down · arc shot · tracking shot · static shot · shake
  slightly/strongly · POV · roll. "The camera pushes in with small amplitude at slow speed toward his face." "The
  camera holds a static shot as …"
- One motivated move per shot, or a deliberately static one; never stacked moves.
- A cut must bring new information — subject, space, state, viewpoint or time. A small change of distance or angle is
  a camera move, not a cut.
- Fine hand work — fretting, writing, typing — garbles and drifts off the rhythm: frame it medium or wider unless the
  close-up is the point and has been tested.

### 3.4 The look of real footage

- "Natural documentary colour, restrained contrast, natural skin texture, fine natural film grain." Grain belongs HERE:
  real night footage carries it and MiniMax's examples use grain language. Drop it if the first take's grain boils.
- Lens and exposure behaviour read directly: "subtle handheld drift", "a wide-angle lens close to the ground",
  "exposure breathing as the light changes", "soft highlight halation". Natural exposure and slightly imperfect
  framing beat polished commercial light.
- A moving light source (a fire, a candle, passing headlights) is never the same twice: give each scene its own cause —
  "a soft gust makes the flames lean and gutter, then settle" — so repeated scenes do not loop one flicker.

### 3.5 Negatives — the safe form

- H3 has ONE positive stream and no negative prompt. A negation that names a concrete thing can DRAW it: a "do not
  reproduce" clause naming a grid and markers drew them when nothing else supplied them (DIALECTS § MiniMax H3, L31).
- In the body, state the wanted state: "the flames stay small and low, the air above them clear" — never "no sparks,
  no embers, no blaze"; "the light falls from high behind the camera" — never "the moon is never in frame".
- In the tail, only artifacts that are not objects in the scene — MiniMax's own form: "No subtitles, on-screen text,
  watermarks, animation styling or over-smoothed skin." L40 warns on a negation naming anything else.

### 3.6 References

- One job per reference, said in words ("Image 1 for the location and its light only"), and what it must not
  contribute. A look plate transfers attributes, never content.
- Identity apart from wardrobe, pose and setting. Only the characters the scene needs — an extra reference invites an
  extra person.
- Never re-describe a reference statically: state what stays and what moves.

### 3.7 Singing and speech

- Speakers keep stable ids `(S1)`; the words go VERBATIM inside `<d>[English] …</d>`; identity and delivery stay
  outside it.
- A voice heard while the person on screen is silent: "says in an off-screen voiceover: <d>…</d> while his lips remain
  completely closed" — on a front-end, lip-sync off for that scene.
- A line that crosses a cut: `<scenetrans>` on both sides and "continues seamlessly across the cut".
- The performance window (a front-end that lip-syncs to the song — its vendor's direction guide): from the first word
  to the last the singer is on screen, facing camera, medium close-up or closer, mouth unobstructed; entrances, reveals,
  time-lapses and pull-backs go before the first word or after the last, written in that order; loud described action
  stays out of the window; ask for clear, articulated delivery — never whisper, mumble or hushed.
- No silent closed-mouth lead-in: a sung scene opens a breath before the first word ("already drawing breath, his
  lips parting on the first word") or on something other than the mouth.

### 3.8 Sound

- `overall_soundscape`: one to four sentences naming the ambient and action sounds — wind, fire, fabric, footsteps. A
  quiet scene names its room tone, never an absence (L35).
- `non_diegetic_music`: instrumentation, tempo and dynamics, never mood words; `N/A` when there is none.

## 4. What the lint checks

| row | dialect | check |
|---|---|---|
| L38 | all | quality words; "cinematic" and "epic" in a still prompt |
| L39 | kie | grain or sensor noise asked of a still |
| L40 | minimax-h3 | a negation that names a scene object |
| L41 | minimax-h3 | the first shot does not open with a style word |

## Sources

OpenAI image-prompting guide (developers.openai.com/api/docs/guides/image-prompting) · hedra.com "make AI images look
like real photos" · kieran.build GPT Image 2.5 prompting guide · evolink.ai Flare vs Sunburst · docs.kie.ai GPT Image
2.5 Sunburst · National Parks at Night, "Keeping Our Galaxy Real" · MiniMax `VIDEO_PROMPT_WRITING_GUIDE_base_en.md`
and `…_ref_en.md` (huggingface.co/MiniMaxAI/MiniMax-H3, docs/) · fal.ai MiniMax H3 prompting guide · kapwing.com
"How to Prompt MiniMax H3" · a music-video front-end's published direction guide · Reddit r/StableDiffusion as
weak signal only. Read 2026-10-07; the measured rows are the kit's own.
