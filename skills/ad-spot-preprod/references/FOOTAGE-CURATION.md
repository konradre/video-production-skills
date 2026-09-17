# Footage curation — from a client's pack of clips to a picked cut

When the client supplies the picture, the work between "the files arrived" and "the operator picked the shots" is a
phase of its own. It has one output — a recommended cut the operator can judge on picture, with the reasons and the
runners-up on disk — and one rule above the rest: **a statement about a clip rests on evidence sized to the statement.**
A composition claim rests on a sheet dense enough that nothing between samples could change it; a detail claim rests on
a native-size crop; a steadiness, exposure or cut claim rests on a measurement that printed a known-answer self-test.
Nothing here spends money, and nothing here writes to a source file.

The order does not move. Each step's output is the next step's input, and every step writes to disk as it goes:

```
1 take the pack in        hashes · duplicates · display shape · frame rate
2 the frame-rate decision the motion cost stated BEFORE any conform; the originals stay until the cut is locked
3 break every clip down   measurements + three tiers of sheet + a written read per clip          (footage_intake.py)
4 group into ROUTES       the pack is camera routes, not files; "never the same shot twice" binds on route + subject
5 slots from the audio    the programme audio's phrases are the picture slots                     (phrase_slots.py)
6 candidate windows       each read at the DELIVERY shape, per metric                             (window_metrics.py)
7 assign                  relevance to the words, then looks, then no route + subject twice; a runner-up per slot
8 plan + proxy + pick     the plan file, a labelled preview over the mix, the cut-check sheet     (preview_cut.py)
9 after the pick          beats events, script diff, conform ONLY the picked windows, the EDL
```

## 1. Take the pack in

- Copy in; never edit in place. Hash every file: **download copies ("name(1).MP4") are byte-duplicates more often than
  not** — count the pack after de-duplication, never before.
- Probe the DISPLAY shape and the frame rate of every file (`video-production/scripts/probe_sources.py`): storage
  width × height alone reads a rotated or anamorphic clip as the wrong shape, and every crop after it inherits the error.
- Note what the camera recorded: one action camera or phone often records the SAME move in landscape, square and native
  vertical. That fact decides step 4.

**Done when:** the de-duplicated file list exists with a sha256, the display raster and the frame rate per file.

## 2. The frame-rate decision — before any conform, with its cost stated

The canvas frame rate is a series constant; the footage rarely matches it. There are two honest conforms and they cost
different things (`video-production/scripts/conform_cfr.py --plan` prints both, per file, and converts nothing):

| mode | keeps | costs |
|---|---|---|
| **same-speed** (nearest frame) | real time, usable audio | frames DROPPED (source faster) or REPEATED (source slower). 29.97 → 24 drops one frame in five: every 4th output frame carries a DOUBLE step |
| **all-frames** (every frame replayed at the target rate) | perfectly even motion, every frame real | the clip runs at source÷target speed (29.97 → 24 = 0.80×, 25 % longer); its audio is dropped |

Blending and optical-flow interpolation are not on the table where the client's rule is "real footage only": both
manufacture frames the camera never shot.

**The double step is what a viewer sees.** Its size at the delivery width is `pan speed (frame-widths/s) × delivery
width ÷ frame rate`, in pixels, and the dropped frame doubles it. Under ~5 px it does not read; near 30 px a pan
stutters. So a same-speed conform quietly removes every FAST move from the usable footage — the wide establishing pan
first — while slow tracks and a pan's settle survive untouched. Say that once, with the number, BEFORE converting, and
offer all-frames for the moves that need it.

🔴 **A same-speed master cannot give its dropped frames back. The originals stay on disk until the cut is locked.** When
the operator rules otherwise (disk, housekeeping), the conform becomes the master: verified per file — both rates, one
packet duration, the predicted frame count, the source raster and pixel format, a clean full decode, whole-file SSIM
against the source through the same frame mapping — with a receipt that carries every source's sha256.

**Done when:** the mode is the operator's choice made against the printed cost, every output passed its checks, and the
receipt is on disk.

## 3. Break every clip down

```bash
python3 ~/.claude/skills/video-take-review/scripts/footage_intake.py --src <footage dir> --out review/<pack>-intake --aspect 9:16 --delivery-width 1080 [--id-regex '_(\d{4})_']
```

Per clip it writes the record (sha256, probe, frames, display raster, the centred delivery crop, cut candidates by the
installed cut rule, motion, colour steps, its own self-tests), `per-frame.csv`, and three tiers of sheet — each tier is
allowed to carry one kind of claim and no other:

| sheet | carries | never carries |
|---|---|---|
| `overview.jpg` — 12 evenly spaced frames, one page | which clips are the same camera route; the rough arc of the move | anything about a window |
| `survey-NN.jpg` — every 4th frame | what is in frame across the WHOLE clip; what the delivery crop keeps and loses | detail, focus, a transient between samples |
| `allframes-NN.jpg` — every frame | a window's in and out; "nothing happens between these two samples" | detail |
| a native-size crop (`window_frames.py`) | whether units MATCH (as seen), what a sign or a number says, a recognisable face, focus | — |

Then the **written read, one file per clip** (the stub `visual-read.md` is created for it), filled from the sheets:
frame ranges → what is in frame → what the delivery crop keeps or loses and the crop x that keeps the subject; the
route it belongs to; candidate windows; what is SEEN, stated as seen; what is NOT claimed; what the clip does not
contain. Four disciplines, each the price of a wrong read:

- **Describe the whole clip, never its name, its raster or its first frame.**
- **"Matching" is what can be seen to match** — body, length, doors, windows, roof gear, livery, wheels. A year, a model
  or a configuration cannot be read off a picture: it goes to the client's fact-check list, never into the read.
- **A requested visual that is absent stays absent.** Name the nearest real candidate and what it lacks; never fill the
  gap with a generated shot, stock, or a clip from another episode. The operator decides whether to ask the client.
- **Findings go to disk as they are reached**, one clip at a time, and every read is labelled PROVISIONAL until the
  operator picks. An agent session reading many sheets dies on request bytes long before its context fills: survey
  images stay downscaled, verdict crops stay small in area and native in scale (`video-take-review` INSTRUMENTS.md §
  Review images), and a long pack is read in bounded groups with a handoff file between them.

What the motion numbers can and cannot say: speed is image displacement, not camera-versus-subject; the mean RGB step
moves with composition and only LOCATES an exposure step for the eye; an empty cut list is not proof of no cut.

**Done when:** every clip has its record, its sheets and a written read covering its whole length, and the instrument's
self-tests are in every record.

## 4. Group the pack into routes — it is routes, not files

A **route** is one subject seen by one camera move. A pack is usually far fewer routes than files: one camera often
walks the same move two or three times, in landscape, square and vertical. Read every overview, then write the route
table before ranking anything:

| route | files (mode) | subjects along the move |
|---|---|---|
| R3 row track | clip-A (landscape) · clip-B (vertical) · clip-C (square) | head: a single vehicle · body: the unbroken row |

- **Same subject + same move + timestamps minutes apart = one route**, whatever the file names say. Two passes of one
  subject in opposite directions are sub-routes (R4a, R4b).
- **What each mode gives a vertical deliverable:** native vertical and square crops keep the full sensor height (a
  1728 px-wide crop for a 1080 px delivery — 1.6× oversampled, and square leaves room to slide the crop); a landscape
  file gives a 1215 px crop and is, in effect, a TIGHTER lens on the same move — and its pan reads ~3× faster through
  the narrow crop. Prefer vertical or square on pixels; reach for landscape when the tighter view IS the shot.
- **"Never the same shot twice" binds on route + subject, not on the file.** Per-file uniqueness lets one row appear
  three times. A second use of a route needs a different SUBJECT along it and the operator's yes.

**Done when:** every file sits in a route row with its mode and its subjects, and the no-reuse rule is written against
routes.

## 5. Slots come from the programme audio

The picture under a voiced line is cut to the PHRASES of the voice, so a mention stays on its picture. Measure, in this
order (`video-edit-edl/scripts/phrase_slots.py`):

1. `words` — transcribe the WHOLE voice file with two model sizes and read where they disagree. An excerpt transcribed
   alone loses that agreement.
2. `timeline` — if the words were measured on the dry voice and the picture is cut to the mix, prove they share one
   timeline (envelope correlation: lag 0, score > 0.9) before carrying a single time across.
3. `slots` — the script's phrases, in order → the onset of each phrase's first word → the cut **2 frames before it**
   (it lands 1.5–2.5 frames ahead of the word) → slots in whole frames. Where the two models disagree by more than
   0.10 s, read the onset off the level envelope and pass it in (`--onset S1=4.94`).

The grammar the slots obey: a mention stays synced to its picture · **one continuous shot beats two cuts of one
subject**, so a phrase with no footage of its own rides on its neighbour's shot and the gap is REPORTED, not disguised ·
a slot under ~1.25 s is merged or kept on purpose · the client's visual list names KINDS of shot; which phrase each kind
sits under is the edit's call, and it is written down.

**Done when:** the slots file exists in frames, every flagged onset was read off the envelope, and each slot quotes its
phrase.

## 6. Candidate windows, read at the delivery shape

A clip does not ship; a window of it does, cropped to the delivery aspect and scaled to the delivery raster. For every
slot, list two to eight candidate windows exactly as long as the slot (file, first frame, crop x) and run:

```bash
python3 ~/.claude/skills/video-take-review/scripts/window_metrics.py --root <project> --candidates review/<round>.json --out review/<round> --intake review/<pack>-intake --stack
```

| metric | valid for | not valid for |
|---|---|---|
| sharpness (Laplacian variance at the delivery raster) | files of ONE route showing the same thing | anything across routes: gravel and foliage inflate it, a smooth subject filling the frame deflates it |
| luma, clipped highs and lows, colourfulness | flagging a hazy, clipped or dull window | ranking two well-exposed windows |
| speed (frame-widths/s) and **step px at the delivery width** | how a move will READ; the conform cadence (step × 2 at the dropped frame) | camera shake |
| shake (residual on the axis the move does NOT use) | handheld versus stabilised | — |

⚠ The obvious shake number — the smoothed residual ALONG the pan — reads the conform's cadence, not the hand: on a
dropped-frame conform it sits near 27 % of the pan speed on every pan while the other axis stays under 0.3 px. Read shake
on the axis the move does not use, and cadence on the one it does.

The strip is the verdict; the numbers only say where to look. A window that opens on the wrong thing (two subjects where
the phrase says "one") fails on the FIRST frame of the strip, whatever the rest shows.

**Done when:** every slot has its strips and its metrics on disk, and each metric in the write-up carries its validity.

## 7. Assign — relevance, then looks, then no repeat

1. **Relevance to the spoken phrase** — 3 the picture IS the phrase (a count word shows that count; a category word
   shows that category) · 2 related · 1 atmosphere. An abstract phrase — one that names no object — takes the shot with
   the most SCALE.
2. **Looks** at the delivery shape — cadence step first (a stutter outranks everything), then exposure, then the eye on
   the strip: subject size in frame, clutter, what the first and last frames hold.
3. **No route + subject twice** — and neighbours should differ in scale or direction; two static frontal shots back to
   back read as a jump.

Write a runner-up for every slot and say what it costs. When the best-looking option bends the no-repeat rule, it goes
in as the ALTERNATE with that said plainly — the operator may take it.

Then the coverage table against the client's own visual list (covered by which slot · weak · NOT IN THE PACK) and the
fact-check list (every claim the picture appears to make that nobody can verify from a frame).

**Done when:** the assignment uses each route + subject once, every slot names its runner-up, and the gaps and the
fact-check list are written.

## 8. The plan file, the proxy, the pick

The plan is one JSON the preview renders and the edit later reads: the programme audio, the word times, the cut rule,
the selection rule, the route table, the source facts (frame-rate history, what was deleted), and per slot the pick
(file, source frames, crop x, subject), its relevance and looks in words, its runner-up, everything else that was read,
and the coverage table. Reasons live IN the plan, so the next session does not re-derive them.

```bash
python3 ~/.claude/skills/video-edit-edl/scripts/preview_cut.py --root <project> --plan edit/<SPOT>-cut-recommendation-v1.json --mix <programme.wav> --out review/<round>/<SPOT>-cut-v1-PREVIEW.mp4 --check-sheet review/<round>/<SPOT>-cut-v1-check.jpg
# an alternate, without touching the plan:        … --alt S1=<clip>:<first frame>:<crop x> S4=…
```

What is not made yet — a presenter's shot, the end card — is a labelled grey slate, never a stand-in from another
episode. **Read the check sheet before the preview goes anywhere**: the frame either side of every cut proves the right
clip sits in every slot. The operator gets the preview paths, the slot table in words, the gap list, and numbered
questions; the beats file stays untouched until they pick.

**Done when:** the preview and its alternate render at the predicted frame count, the check sheet was read, and the ask
names paths.

## 9. After the pick

The pick goes into the plan ("picked, by whom, in their words") and into the beats file as events; `script_diff.py`
runs again. A visual the operator dropped is recorded as dropped by ruling, with the sentence. Only THEN are the picked
windows conformed to the mezzanine raster — the windows, with handles, at their crop x — and the EDL built
(`video-edit-edl` § 2). Nothing unpicked is conformed, graded or upscaled.

## ❌/✅

```
❌ Convert the pack to the canvas rate, delete the originals, then look at the pans
✅ --plan first: the double step in pixels per mode; the originals stay until the cut is locked

❌ "17 clips" → each clip once → the same row on screen three times
✅ The route table first; no route + subject twice

❌ Rank windows on the source frame                  ✅ Rank them through the delivery crop and raster
❌ Sharpness compared across routes                  ✅ Sharpness inside one route only; the strip decides
❌ "jitter 2.6 px — stabilise it"                     ✅ Residual along the pan = the conform cadence; shake is on the other axis
❌ A missing visual covered with stock or a generated shot
✅ "not in the pack" + the nearest real candidate; the operator decides whether to ask the client
❌ "the same year and model" read off similar fronts    ✅ "fronts that look alike, as seen" + the fact-check list
❌ Slots typed from the script's timing column       ✅ Slots measured from the programme audio's word onsets
❌ A table of picks sent for approval                ✅ A labelled proxy over the real mix, the check sheet read first
❌ A self-test that fails → loosen it                ✅ Work the known answer by hand first: the expectation may be what is wrong
```

## Failure behavior

- A self-test FAIL stops the instrument. Before touching the instrument, work the known answer by hand — a colourfulness
  test once expected "> 100" for pure red, whose true value is 85.53; the instrument was right and the test was wrong.
- A delegated read (another agent, another session) is watched by its LAST WRITTEN FILE or tool call, never by its pid:
  a session stuck in a usage-limit retry loop looks alive for as long as anyone lets it.
- A window that runs past its clip, a crop x that leaves the frame, a slot and a window of different lengths: each stops
  the tool with the slot named. None is patched by hand in the plan.
- Two models that hear a different NUMBER of words: read both transcripts against the script before using either.

## Dated evidence

- **2026-09-18, a supplied pack of vehicle-lot footage for a 9:16 spot.** 27 files → 17 after hashing (10 download copies) → 5 routes × up to
  3 camera modes. Sources 29.97 fps, conformed same-speed to 24 and the originals deleted before the
  cadence was read: every lot-wide pan then stepped ~30 px (double step ~60) at 1080 wide and was unusable,
  while the slow tracks stepped 2–4 px. Measured per-frame shift on a fast pan: 9.6 9.4 18.9 9.6 9.6 9.6 17.5 …
  (every 4th frame doubled); double-step fraction 0.235 against 0.25 predicted. The shake residual along the pan read
  1.5–2.6 px at 320 wide and tracked pan speed at ~27 %; the other axis read 0.02–0.3 px on every clip.
- Same job: five slots from a 14.2 s line (two whisper models on the whole 31 s stitch, median onset disagreement
  0.04 s, one 0.16 s disagreement settled by the envelope); mix versus dry timeline lag 0 ms, score 0.986; five routes
  assigned once each; one requested visual (a loading shot) not in the pack, reported, and dropped; the
  route-unique cut was picked over a prettier alternate that reused a route.
