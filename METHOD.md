# The method

This is the order we produce video with generated footage in, and why each step sits where it does.
The skills implement it; this document is the map. It is written for an operator and their coding
agent setting up on their own infrastructure, so it names no machine, path or client of ours.

## The shape of the whole thing

Generate small, approve, then reconstruct. Every clip is generated at a low resolution (480p on Seedance)
on a venue that accepts references, read by the agent and approved by the operator, and only then
upscaled with a
reconstructive model that invents detail. The upscaled mezzanine sits above delivery resolution; the
grade goes on there; grain, if any, goes on there; the deliver step downscales once per platform. The
order is the whole finishing argument and it does not commute: grade before the upscale and the
reconstructor rebuilds your halation as detail, grain at delivery resolution and the encoder throws it
away. `video-finish` carries the measurements.

Two things make this run without burning credits. The first is that nothing is bought without a cost
line and the operator's explicit yes, per batch, however small the amount. The second is that every
gate runs in code before the call, never from memory: the references are checked against a rules file,
the prompt is linted, the cut is checked against the script. An agent that "remembers" the rule forgets
it on the next context window. A script does not.

Many of the numbers in the skills are defaults. The order and the gates described here hold for every
production we make; a price, a clip cap, a pixel threshold or an instrument's tolerance does not. Each
of those was measured on one model, venue and version, and moves when any of them changes. Aspect
ratios, loudness targets, caption styles and edit timings belong to whichever genre, platform or client
asked for them, and the next brief sets its own. `skills/video-production/references/WHAT-VARIES.md`
sorts them by what moves them (genre, delivery platform, the generator and its native resolution, the
tools on hand, audio, client and budget) and says where to re-derive each one. It also marks the numbers
that came from a single job, so nobody treats them as a spec. The entry skill walks that list when a
project starts and writes the project's own values into its files.

## Pre-production

For an ad campaign the client's script is the single source of truth. It is saved verbatim beside the
plan, read end to end before the first prompt, and rewritten as a beat list in script order before any
shot list exists. The shot list is a derivation of the script: it may add framing, coverage and timing,
never a character, a beat or a line, and additions are proposed as numbered cost lines with "no" as the
default answer. It is built from continuity partitions rather than shots. A partition is a run of beats
that must hold the same people, objects, room and light, and it is one generation whenever it fits the
generator's maximum duration. That maximum is read from the vendor (its schema, its cost estimator or its
error message), never inferred from the longest take you happened to run. Consistency comes free inside
one generation and is a gamble between two, so every extra generation adds risk. A rejected cut from an
earlier round is evidence about its defects and never a source of structure; scene detection on it
rebuilds the previous producer's split, mistakes included. A small script diffs the beats against the
client's text, fails a quote that differs from it by a single word, and fails a scripted sentence split
across rows unless the row records why.
The rest of the plan is the brand kit (the audio signature, the fixed line, the variable line, the CTA),
the assets to ask for (flat artwork, the product's pieces on white, full-resolution originals), the
rulings to get from the client once (language risk, likeness), a global spec decided once (aspect, safe
zones, the true-size rule, the grade), a risk register whose mitigations are already in the shot list,
and a cost plan by dependency round, so the operator answers one GO per round and knows what waits
for a pick.

A short film inverts the order. The self-revelation is written first as one paragraph, every beat is
derived backward from it and it is held to 90 percent of the runtime. Characters carry four slots (a
lie, a want, a need, a ghost) and an arc with a state chain; a script refuses a beat sheet whose
answers and arc disagree. Premises are ranked twice, on story and on how likely they survive the
pipeline, and the two rankings are allowed to disagree; the disagreement is the operator's decision.
The shot the film is built around is storyboarded and generated first, because if it does not land the
film does not exist. A music video adds one rule on top: the track is measured before a beat is
written, and every second of it is allocated to a generation window before any prompt, so later beats
are placements paid for by trimming rather than appends.

## References and continuity

Every clip is generated from nothing, with no memory of the clip before it, so continuity has to be
built. Three ideas carry it. A keeper is a take the operator picked, and its frames are the only root a
scene can continue from. Backfill means every regeneration's references come from accepted assets: a
keeper frame, a crop of an accepted plate, an edit of an accepted still, and a fresh still only as the
last resort. Lineage means a start image chains back, by crop or image-to-image edit, to a keeper or
to the client's own photo; a still generated from prose starts a new world, and three seeds of it are a
round of continuity errors.

The practical rules follow from that. The start image is the previous shot's last state, never the
scene's opening wide. Before/after pairs come from one source. Inserts start on a crop of the accepted
plate at that framing. Character references are cut from the first accepted take. Product shape comes
from the client's own photo and product size from an in-world crop beside a known object, because a
magnified sheet pins shape and nothing else. A ledger records, per shot, what each element looked like
before and after, read off the keeper frames at zoom rather than remembered. The refs gate turns the
ledger into a rules file and refuses the generation call when a locked element's reference is missing
from that call, when a start image has no accepted record, or when a capitalised subject in the prompt
is neither ruled nor declared. It also opens the files. A reference whose file changed after it was
accepted fails, and so does light described in the prose when the call carries no look plate for that
light. Its table is pasted into the GO ask.

## The prompt

A prompt is compiled, not written. The shot document supplies the facts, the accepted references
supply every visible attribute, and the venue's dialect supplies the shape. The prompt says only what
neither a reference nor a parameter can carry: which reference is which subject, what happens in what
order, what the camera does, what is heard. The rule that cost us the most before we learned it is to
point at references and never describe them. Any adjective about a cited reference can only contradict
it, and on our runs the words won every time.

The dialects differ in ways that bite. Seedance addresses references ordinally and wants prohibitions
in a trailing region, not in the body; a negative in the body renders the thing it forbids. MiniMax H3
wants typed subject labels defined once and dialogue verbatim, the opposite polarity from Seedance,
where supplied-audio words must not appear at all. A web front end has a hard character cap the model
does not. Parameters never go in the prose. A linter checks the mechanical rows (slot ranges, the cap,
negations in the body, moderation words, a named off-frame object, beat density) before the gate;
the judgement rows are read by eye.

## The call

One gated path per venue. The submit script runs the refs gate first and refuses on a failure, prints
the cost, stops there without `--go`, and with it persists the venue's job handle the instant the job
is accepted, because billing happens at acceptance and not at fetch. The raw reply is kept, the ledger
gets one record per seed before polling starts, and the poller runs detached so a shell timeout cannot
take a paid job id with it. `COMPLETED` is not success; a file on disk is. A billed job is never
resubmitted; its result is re-fetched by id. Refusals are classified from the venue's own record before
they are called free. Seeds reach the operator as clips by path the moment they land, never as contact
sheets, and nothing moves on a seed before the operator's pick.

Before an expensive call that works from references alone, one still is generated from the same
reference set for a few cents, read for identity, wardrobe, room and light, and its path goes into the
cost line. With no start frame pinning the take, a wrong reference does not degrade the shot; it
produces a different one at full price, so the operator approves the spend against a picture of what
the references carry.

The venue decision is quality and prompt adherence first, permissiveness as the fallback criterion.
In practice that meant one venue for anything with people in the references, because the other refused
any photoreal person, and a second image model for surgical edits because the first ignores sheets when
composing. A new venue is proven on the hardest shot first. The easiest spot passes on every model and
proves nothing about the hard parts.

## The read

A landed seed is read the same day, with instruments, and the operator's verdict is the only pick.
Continuity comes first: the previous keeper's last state, the door, the seats, the counts, the cast,
the pose state, the named states, per cut, at zoom. A geometry break rejects the seed before its gag
is judged. A cut the model composed inside one generation is read for what survived it, the same faces,
wardrobe, room, light and performance on both sides; the cut itself fails nothing, because consistency
across it is what the long generation was bought for.
Then the acceptance matrix, row by row, never a score: the script beat, the technical read,
anatomy per person at 3x in a crop, faces at 1:1, the product's shape and size, composition and
eyelines, audio, named states on every frame after the event, dignity, realism. A keeper is a take plus
a usable window, and a void carries its reason into the ledger. Every instrument prints a known-answer
case beside its number or its number is not evidence; a scale metric once matched a frame to itself at
0.9, and it had already been used to make claims.

## The cut

The edit is a derived document. The keepers are the operator's picks, the script is the truth, and a
builder computes every timeline number from them, so re-running the same plan reproduces the same EDL
and an editorial note becomes a change to the plan rather than a hand edit of a time. Sound is placed
from picture markers that were measured on the keeper: the hit's RMS peak, a word onset from the
transcript, the frame a wall clears. The narrator chain derives backward from the hit. A script-fidelity
gate checks the EDL against the beat list before any finish and exits non-zero on a failure. Every new
version is a new file, the shipped file stands untouched, and the repair ladder runs cut, recycle, dub,
punch-in, and only then a regeneration.

## Sound

One voice and one model per role for the campaign's life, because a different model renders the same
voice id with a different timbre. An off-screen line is never the narrator. A line the venue refused is
dubbed in the character's own cloned voice, with the shot prompted on a similar mouth shape. Sound
effects come from the take first, a library second, generation last, and a pick from a reel is
confirmed as a syllable map before anything is cut. Music cues are cut to the marker they end on, and
a cue shorter than its span simply ends, which the checker fails. Native audio is scanned for generated
tones at every take's head; an artifact is muted and the hole filled with synthesized room tone rather
than a pasted slice. Every voice-over file records where it came from, and the stem builder refuses one
whose quiet stretches are not quiet, because a line lifted out of a finished cut carries that cut's music
bed between its words.

The master is a static mix. A single-pass loudness normaliser in the master rides the programme, lifting
the bed in every gap between lines, and every later stage inherits the ride. The finisher sets the level
once, at delivery. It measures the master, applies one gain to reach the target, and limits at 192 kHz
before the resample to 48 kHz and again after it. That order is one we measured rather than assumed. A
limiter placed only after the resample delivered a true peak a full decibel hotter than the target;
before, or before and after, held it. The finisher also prints how much limiting the target costs and the
loudest target the mix reaches with none, and when the client supplied a reference, its measured level is
the target. The verification runs on the delivered file, per metric with its label, and placement is
measured by envelope correlation because a waveform correlation reads near zero under loudnorm plus AAC.

## Designed elements

Anything that must be exact is designed, never generated: packaging, the wordmark and the card, the
product's pieces as sprites, a display with names, a wall that must straddle a cut at a known frame.
Anything that must be alive is generated. The two meet only where the operator has accepted a composite
on a plate, and never as a 2D overlay on generated motion. The compositions render deterministically
from local assets with a seeded random source, so a "fix one thing" round changes one thing. A defect is
fixed in the source asset by measurement, and every check is made on the delivered frame at zoom, not on
the element's own render. A dozen card variants can be rejected in a row when the fix is verified on the
wrong artefact.

## The explainer

A narrated explainer has no generated footage. Every frame is a HyperFrames scene drawn in code, so every
rule is arithmetic on a timeline and every fix is a re-render. The film that fails usually passes every
checklist item and is still small, empty or frozen, so the storyboard writes the drivers down as numbers:
one hero per scene sized to at least a third of the content box's height, light on the hero only, one or
two set pieces a chapter, and an action that keeps moving until the next beat. Scenes take their times from
the narration. Anchors are spoken phrases; a script resolves them against the voice's word timings and
writes each scene's beats, so after a re-recording, running that script again re-times the film. The facts
behind every number on screen get a source before anyone signs off the script, and the operator approves a
rendered first 20 to 30 seconds before the rest is built. Two instruments check the result. One reads the
delivered file for hero size, empty frames and holds; the other reads the composition's source and checks
every string it can put on screen against the approved copy.

## The finish and the QC

The upscale tier is decided per shot, from the framing. Local reconstructive upscaling is the default
because it is free and the cleanest arm for commercial work. A hosted diffusion upscaler is used from
the original take for any shot whose faces sit too small for the generator to have drawn them, roughly a
head under 50 pixels tall in a 480p vertical take, or whose text must read; it does not stack on the
local pass, and it goes through a cost line. The hero pass applies an authored Dehancer grade to each
upscaled clip in Resolve, one clip per call, over an in-app bridge the human starts, and writes a 10-bit
mezzanine that is probed rather than trusted. The spot then renders in three stages from the EDL, and
every intermediate is 10-bit 4:2:2; the deliverable is the only 8-bit 4:2:0 file.

The QC reads the delivered file, per metric: duration against the EDL, finite loudness within a
lufs of target, true peak under the platform ceiling, the delivered cut list against the EDL joins with
every extra detection named, take-cut leaks (a cut the operator kept inside a long generation is
declared on its event and reported rather than failed), the end card by correlation when the spot has
one, VO placement. Then the eye
and the ear at several timecodes. Anything found goes back to the EDL or the hero, never to a gain
nudge or a re-encode of the deliverable. Masters are 1080p only, and a variant always derives from the
graded mezzanine.

## Client rounds

The client's notes are the most expensive words in the project. Each note is saved verbatim, mapped
from the client's delivery-order numbering to spot ids, and located in the delivered file, the EDL
history and the script before anything moves, because the noun in a note often refers to a different
object than the one you assume. The notes become a numbered list classified in the client's own words
(cut, recycle, rebuild, causality, approve, gate) with no action taken, the operator answers per item,
and only then does the ladder run. An approved spot freezes. The delivery message names the file by
path with its size, what changed mapped to the client's items, the VO script as placed, the QC line,
residual doubts with frame times, and the decisions as numbered questions with the cost inline. Saving
is not sending: every round's files land in a standing deliver directory before the message is written.

## What it costs

These are our numbers, not a promise. A seven-spot vertical campaign, about forty takes at 480p, fit
inside one monthly plan of the video venue, with the hosted upscale spent only on two wides of one
spot, about $2.60. A music video's stills stayed near $5 across some forty paid images. The finishing
measurements (grain survival at 5 and 2.5 Mbps, the upscaler A/B, the Resolve codec facts, the hard-cap
budget arithmetic) are in `skills/video-finish/references/EVIDENCE.md`, and the grading method with its
sources is in `look-library/GUIDE.md`. Vendor prices move; the venue table in `video-gen-cost-gate`
says to re-read a rate page before quoting a number that matters, and to trust the receipt over the
arithmetic.
