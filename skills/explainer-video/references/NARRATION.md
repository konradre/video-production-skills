# Narration — the budget, the script, the voice

## The budget comes from the voice, measured

- Measure the chosen voice on one sample sentence of the real script: words per second of speech. Voices differ more
  than defaults admit — one local English voice ran 2.3 words/s where a cloud voice ran 2.96 (an upstream explainer
  kit, 2026-09), and a script budgeted at the cloud rate ran 6 min 17 s against a 5-minute target.
- Words for a length ≈ seconds × the measured rate × 0.9 (the pauses between sentences and scenes). At 2.3 words/s:
  60 s ≈ 125 words ≈ 12 sentences · 3 min ≈ 370 words · 5 min ≈ 620 words.
- One sentence ≈ one scene; a scene is one idea with one hero. Chapters follow the content, not the length — one
  chapter that explains one thing fully, or several that survey.
- A measured runtime more than 15 % off the target → add or cut sentences. Never change the voice's speed to fit.

## script.md

- `## <scene-id> <title>`, then the lines spoken in that scene, in order. One sentence per beat, 20 words at most; a
  long sentence splits into beats at its commas.
- **Structure**: the first chapter answers *why* (the problem, the metaphor, the hero's entrance, the source); the
  middle answers *how*, step by step ("step N" and its action); the last evaluates, names the limits, and returns to
  the metaphor to close.
- **One running example** — the same case, names and numbers in every scene — and **one metaphor**, returned to at
  the end.
- **Every sentence is drawable.** Name what the scene shows while writing the line; a line with no picture is
  rewritten or cut.
- A term appears first in full with its abbreviation, then as the abbreviation.
- A number comes only from `facts.md`, with the organisation and the year said; a number that ages carries "as of".
- Example data (a model, a score, a price) is marked illustrative in the delivery note.

## Display text and spoken text are different files

- `script.md` holds the DISPLAY text. The voice's input may respell (a course code read as words, a phonetic name, a
  spelled-out abbreviation) — keep that respelled copy as the voice's own input file.
- `explainer_timeline.py` aligns the display words to the spoken words position by position (never by
  find-and-replace: "one → 1" is right in "question one" and wrong in "one small function") and refuses a capitalised
  or numeric display word the audio never says.
- A pronunciation override changes only the voice's input, never the captions.

## The voice

- Through `spot-audio-assembly` (a cost line and GO before every TTS call) or a voice-clone lane that emits a joins
  sidecar; one voice and one model for the whole film.
- Loudness-normalised before it goes into the composition; the delivered file is read again (SKILL § 7).
- An engine that returns no word events stops the timing — a timing gap is never interpolated.

## Checkpoint 1 — the script sign-off

The whole script, the scene split, the word count, the measured rate and the estimated runtime, before any voice is
generated. The script is the cheapest place to change the film.
