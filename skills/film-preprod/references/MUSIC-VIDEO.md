# The music-video variant — the track map before the gen map

## 1. Measure the track, never guess it

`track_map.py --audio audio/track.wav --out analysis/features.json`: duration, BPM, the bar, the
8-bar phrase, per-second band energies and centroid, and the events read off three independent
signals — hats entering (hi > 4 kHz jumps: the cleanest section marker), a build-up (low band decays
to near zero while mid/hi rise, the centroid climbs), an IMPACT (low snaps back), a near-SILENCE (dB
collapses: the held breath), the PEAK bass (the loudest bar). Write the section table (intro / verse /
gap / groove / build / impact / drop / breakdown / re-build / drop 2 / outro) with the acoustic
signature of each, and **the hits everything cuts to** — typically five.

Get the source audio first, and treat an extractor failure as a version problem before a flag problem:
the installed downloader was two months stale against a hostile-to-automation target, and the plain
command with no flags at all was the one that worked after the update. Update, run plain, then theorise.

## 2. Allocate the whole timeline first

Every second of the track is assigned to a generation window BEFORE any prompt: a gens table with
`| gen | window | duration | start frame | end frame | motion ref | refs | prompt chars | beat |`.
Later beats are **placements paid for by trimming** the loosest stretch, never appends — the track
does not get longer. A beat lands ON a hit (the action on the impact; the set-piece on the loudest bar).

## 3. Generation order is dependency-bound

A gen that continues another consumes its predecessor's last state (`video-refs-continuity` § start
image) or its output as a motion reference, so it waits for that keeper: write the order explicitly
(`G1→G2→G3→…`, a later gen pulled forward when an earlier one depends on it). The edit is LOCKED before finishing; the flattened master carries the
cut's own processed audio (no VO stem, no captions); the reconstruction is one pass on the locked cut.

## 4. Character design for 480p

Told apart by **colour family, face and outline only** — size, coat colour, face shape, silhouette
(a crown of hair, a bare chest, a longer coat). **No fine markers**: stripes, notches and small
markings are pixels at 480p and each is a sentence competing with the species word. **Human in
manner, never in movement** (the same locomotion clause in every prompt: hunched shoulders, no neck,
arms near the knees, a knee-bent stride with no head bounce) — the comedy is human behaviour on a body
that does not move like one. A genre convention the reference corpus lacks is the operator's ruling; keep it.

## 5. Species from a reference, never from text

Text-to-image cannot render a species with no photoreal training referent — it snaps to the nearest
real animal. The species comes from operator-authored reference sheets; the image leg (where photoreal
figures are legal) composes start frames from them; the video leg takes frames — and sheets only at a
venue that still accepts them (`video-gen-cost-gate` § venues). An asset leg refuses a text-only
generation for such a subject and demands a source image: negatives never beat a training-data attractor
(six paid rolls returned the same real animal against every negative), and shortening the prompt does not
either — every content word pointed at the attractor.

## 6. The reveal is not pre-loaded

An asset that belongs to a reveal is cited by no earlier shot; the space stays ordinary and the
reveal's objects live in their own plate. The fake-out works because the audience's own
suspicion is dangled and then eaten — nothing earlier may tip it.

## 7. The pre-flight gate on every prompt

Before any prompt is pasted: the character cap, the slot ceiling, no slot gaps, **one slot doing one
job** (a slot that carried two references produced a two-meaning defect), no appearance adjectives
describing a cited reference, the pre-action lock on every start frame, every start frame on disk
(`video-prompt-dialects` § lint). Four iterations reached zero false positives — replay the recorded
defect cases before "simplifying" it. And the backward geometry check: a camera path that needs a feature
the plate lacks (the camera leaving through a SECOND window when the cabin plates had one) is a blocking
edit to the asset spec, raised before the gen — never a silent mismatch. With a scene proxy of the plate
(`video-refs-continuity` SCENE-PROXY.md) the check is computed: run the authored move through
`scene_proxy.py --move` and read the framing tables — a subject that leaves the frame or a wall the move
passes through fails the plan before a credit is spent. Count the expression beats per shot in the same pass:
more than two or three in one shot average into a still face on H3 (`video-prompt-dialects` DIALECTS § MiniMax
H3, L28) — split the shot before the prompt, not after the take.

## 8. The look-plate family, enumerated against the shot list

One abstract plate of light and colour per light context the shot list actually contains — golden, dusk,
canopy, night road — each cited by every shot in that light with a look-only role, so the film's palette
holds across venues and days without a grade sentence in every prompt. Write the shot → plate map first:
three exterior plates covered ten shots and neither interior, and the interior that cited a woodland dusk
for a tungsten room had to drop its slot. Plates are generated template-free (a prop leg's three-view
framing is destructive for a field), and grain, halation and bloom stay out of them — texture is the
finish's job (`video-refs-continuity` § look plates).

## 9. Lyric timing — a ladder, then the cut rule and the karaoke rules

**Every word of the known lyrics on a visible sung line gets a measured onset before a cut, a scene window or a lyric
caption is placed.** Take the first rung that times every such word; a rung that misses one hands the song to the next
rung, never to a guess. Vocals outside the lyric sheet — ad-libs, stutters, backing and outro chants — are recorded as
labelled estimates (an interval and what is heard there), never as measured onsets, and never block the ladder. A piece
with no sung line skips it: instrumental passages take the track map's silences and hits, spoken lines take rung 2's
timestamps checked by ear.

1. **The venue's hosted analysis** where the venue offers one (read its readiness flag and its size cap: the cap is on
   the uploaded master, which is never recompressed to fit). Only cues it marks as exact
   are vocal onsets; adjusted, estimated or unknown cues go to the ear check like rung 2's.
2. **Local word timestamps** from a Whisper-class transcriber (`faster-whisper` large-v3-turbo on a CUDA host, in an
   activated venv; the first run downloads its CTranslate2 weights, ~1.6 GB, unless a cached Hugging Face
   `openai/whisper-large-v3-turbo` snapshot is converted with `ct2-transformers-converter`, which needs `transformers`; `mlx-whisper` runs on Apple silicon only), every visible line
   checked by ear against the track at its timestamp. A sung word the transcriber drops, splits or slides across a held note is a miss.
3. **Forced alignment of the KNOWN lyrics to a separated vocal stem** — only when rungs 1 and 2 both miss sung words, and
   on a GPU host with room for the models (~4 GB of weights):
   - Separate the lead vocal (Demucs `htdemucs_ft`; where a lead sits under a pad, a karaoke-lead mel-band-roformer stem).
   - **Measure the stem's offset against the master** by cross-correlation before anything is timed on it, and shift it.
     The donor's stem sat 23 ms late (an MP3 decode that kept the encoder delay); measure every new stem, never copy that number.
   - Frame-wise CTC log-probabilities from **two** acoustic models (`torchaudio` MMS_FA and wav2vec2 LV60K), fused across
     mono, left and right — choruses are often double-tracked L/R — and decoded as **one** constrained Viterbi pass over
     the whole song with a garbage token between lines. The garbage token absorbs vocals the sheet does not list; it does
     not prove a word was placed on the right occurrence. A repeated line or an ambiguous boundary is pinned with a time
     window or an anchor, and checked by ear.
   - **Refine each word's start and end from the signal**, not the CTC path alone, in this order: when a rest of ≥ 50 ms
     precedes the word, the start moves to where the voice re-enters if that is more than 40 ms before the CTC start,
     else it stays; only when no such rest precedes it does the start snap to the strongest spectral-flux peak in a
     window from up to 0.25 s before the CTC start (a vowel-initial word; 0.12 s otherwise) to 40 ms after it, the peak
     weighted down with distance and skipped when frication follows it (that is the previous word's final consonants); a
     fricative-initial word then moves back to where its 4–10 kHz noise begins. An end is the next word's start when the
     voice carries on, else where the voice drops 15 dB below the word for ≥ 60 ms.
   - **Confidence per word combines three readings**: agreement of the alternative fusion sets with the primary path, the
     CTC posterior, and agreement with the transcriber's word timestamps (rung 2) — the cross-check, never the answer. A
     manual fix carries its own confidence.
   - **Plot every line** (spectrogram, pitch, vocal onsets, the word marks) and check each plot before its timings count
     as measured.
   - Every manual correction goes into a fix table **with the evidence that justifies it**. The four failure classes to
     expect: a pickup smeared over the backing vocals; a long legato vowel that misplaces a word's start; a rest-onset
     rule firing on a reverb tail or a breath; a lead buried under a pad (place it from the karaoke-lead stem plus the
     rhythm the same line has in the other choruses).
   Method from `mexicat/pdoom-video` `analysis/align.py` (MIT code; its song and lyrics are not licensed). Not yet run
   here: the first song aligned this way records its stem offset, per-word confidence, uncertain words and fix table
   beside the track map.

**The cut rule — the edit is derived from the lyrics, never typed.** A cut that introduces a line lands on the **last
beat at or before the line's first-word onset plus a tolerance of 20 ms**, so a word that starts just ahead of its beat
cuts on that beat, a few ms into the word, rather than on the beat before. Then check the cut against the word timings:
a cut inside the previous word widens that line's tolerance to the next beat when that beat falls within ~50 ms after
the onset (the donor widened one line to 50 ms because the beat before fell inside the previous word), otherwise it
moves to the boundary between the two words — the previous word's end, which on a legato line is the new word's onset —
off the beat. A section ends on a measured song analysis's section start when that start falls at or after its last
word's end, otherwise on the first downbeat **at or after** that end — never inside the last word (the donor's analysed
outro starts inside the held last note; here the cut waits for the note to end). `beat_grid.py` gives beat times and
beat phase, not bar phase: until downbeats are measured, that is the first beat at or after the last word's end, and the
plan says so. Find lines by their **content** ("the line that starts 'sudden drop'"), never by a typed time, so a
re-timed lyric moves every cut with it — the spoken-phrase anchors of `explainer-video`, snapped to the beat grid
(`spot-audio-assembly/scripts/beat_grid.py`). A generation boundary — a venue's scene window — is not a picture cut:
it sits in silence or a phrase gap, never through a word, and takes a beat only when the beat falls in that gap.

**The karaoke rules — any on-screen lyric that follows the voice:**
- A word appears or highlights at its onset and completes by its end; the line may show dim up to ~0.4 s early, and the
  highlight **never runs ahead of the voice**.
- Sung text in the signal colour, unsung at 30–40 %; no outlined or haloed type.
- A word drawn in pieces (sung / unsung) places each piece at the glyph's own x position, never at the measured width of
  the text before it — measuring the prefix drops the kern between the pieces and the word visibly jumps.
- Lyric text inside the title-safe area — at least 96 px from every edge on a 1080-line raster — and clear of any
  on-screen HUD (and of the platform's UI zones on a vertical deliverable — `video-production/scripts/safe_zones.py`).
