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
