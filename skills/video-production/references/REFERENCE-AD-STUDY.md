# Studying a reference ad — what a template may lend, and what it may not

A brief that arrives with "make it like this one" hands over a TEMPLATE: its hook, its pacing, its shot order, its
camera, its satisfaction point and the job its ending does. It never hands over its content. The study turns the
reference into two lists — what we borrow and what we must not carry — before a line of our script is written. The
client's text stays the SSOT (PREPRODUCTION-CORE § 1); the study feeds the beats, it never replaces the brief.

## 1. Watch it with evidence

- A video digest for the segments, the transcript, the on-screen text and the audio tags; frames at one
  per second, timestamped, denser where the cuts or the text flash faster than that. Summarise into 5-second windows.
- **Listen before you classify a presenter.** Frames cannot tell a voiceover from music: a moving mouth can be a voiced
  line, a lip-sync to the track, or silence. The transcript and the audio track decide which, never the pictures.

## 2. The template's profile decides what may become a hard constraint

| profile | what it is | borrow | never add unless the brief asks |
|---|---|---|---|
| texture | a product, food, drink or material shown changing state | shot order, camera pace, the state change, the texture moment, the mood, the music mood | a voiceover, a lip-sync, a person, captions |
| demo | a person using, trying or handling the product, no strong voice | the framing, the action order, the eye contact where it carries the trust, the product-to-person relation, the real room | a voiceover |
| voiceover | a presenter who speaks | the broad look and market context, the spoken language, the rhythm of the delivery, the gestures, the real room | the speaker's face or voice, their words, their handle |
| platform ending | an account, search or shop page at the end | only the job the ending does (the call to action) | the UI, the handle, a blank or black end |
| mixed | several of the above carry equal weight | name the active slots in the study before anyone writes | — |

Our routing follows from the profile: a voiceover template in a UGC spot is a UGC talking head (`video-gen-cost-gate`
§ 1 — Omni for a UGC talking head, Seedance 2.5 for every other shot); a texture template is b-roll and product; a
platform ending becomes a designed end card (`designed-elements`).

## 3. The window table

One row per 5-second window: material · shot and camera · action · product on screen · the selling point shown · the
satisfaction point · audio and text · **borrow** · **must not carry**.

**Never carried, whatever the profile:** the template's product, brand, packaging, claims, prices, captions and
subtitles, platform UI, watermark, account handle, and any real person's identity or voice.

## 4. The product side

From the client's product images and the brief: the identity anchors (shape, colours, the label as designed), the
selling points the brief confirms, and the points nobody confirmed — those never become a claim, however well the
template sold its own. Write down every conflict between the template and the product (the template pours a liquid; the
product is a powder) before the beats are set.

## 5. The hook, scored from frames

Score the first 3 seconds — the reference's, and later our own cut's against it — on five dimensions, 0–10 each:

| dimension | weight | read from |
|---|---|---|
| visual impact — does frame 0 stop a scroll | 30 % | the first frames: composition, colour, light, the subject |
| the spoken or written hook — tension, a pain, a question | 25 % | the transcript and the on-screen text beside the frames |
| emotion — does the picture itself trigger something | 15 % | faces, bodies, the mood of the frame |
| information — is the value clear in 3 s | 15 % | what a viewer knows at 3.0 s |
| rhythm — cut pace against the platform | 15 % | the cut list |

Every score cites a named frame and what is in it ("f0: the bottle fills two thirds of the frame"). With no speech and
no text, the spoken hook scores 0–3 and says why; a dimension the frames describe never scores 0. At least three
changes, each as *what → how → the expected effect*. **The scale ranks versions side by side; it predicts nothing** — it
is an LLM judge's rubric with no measured link to retention. The genre's own number stands beside it: a hook inside the
first 2 s (WHAT-VARIES).

## 6. From the study to the generation

- **The study is dense; the prompt is not.** A clip's prompt carries 4–5 natural beats in the template's order (hook →
  proof → use → the visual call to action), never the per-second analysis and never a string of 0.5–1 s micro-shots —
  ByteDance's own guidance for Seedance template rewrites, where many scene and action changes destabilise the
  product's identity. **The exception is ours, measured:** an audio-driven talking head carries the VO's speech windows
  as numeric beats, which fixes where the line ends (`video-gen-cost-gate` § 1).
- **Overlays are off in the generation**: captions, subtitles, prices, shopping UI, watermarks, lower thirds, platform
  text. Text on screen is designed in post (`designed-elements`), never generated.
- **The last second keeps the product on screen.** A platform ending becomes the visual call to action, never a blank,
  black or white end.
- **A voiceover template gets a new, non-specific person** in the template's broad context, speaking OUR words from the
  script, in the template's language unless the brief says otherwise.

## Provenance

- `bytedance/agentkit-samples` `skills/byted-bp-seedance-viral-creative-rewrite-skill` (`db8aaa9`, 2026-09-24): the
  profiles, the window columns, the never-carried list, the soft beats, overlays off, the product in the last second,
  the audio check before a presenter is classified. BytePlus wrote it for its own Seedance; it is vendor guidance, and
  the soft-beat rule is untested here against our numeric-beat measurement.
- The same repo, `python/02-use-cases/video_breakdown_agent` hook analyzer: the five dimensions and their weights.
