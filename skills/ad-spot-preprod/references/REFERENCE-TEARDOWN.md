# Reference teardown — the structure of real references, measured, becomes the beat grid

A spot that must read like a known format (a phone vlog, a street interview, a product demo, a talking-head explainer)
borrows that format's STRUCTURE — how long the shots run, when the first cut comes, what size the face is at each point,
how the camera moves, where the words start and how fast they run — and never its pixels: our cast, our places, our
client's words. The structure is measured on 3–5 real references, the content of every shot is read and written down,
and what is kept and what is swapped is a table, not an impression. The result is a timestamped grid our own beats are
written into.

**When.** A generated or creator-style spot in a format the team has not measured; a reference the client or the
operator supplies ("like this one"); before the shot list of a NEW format. A campaign whose format is already measured
reuses its teardown. **Not for:** choosing among the client's own footage (`FOOTAGE-CURATION.md`), the hook's wording
(`SKILL.md` § 2, mining the hook pattern), or a reference video fed to the generator as a motion input
(`video-prompt-dialects`).

## 1. Pick 3–5 references

- REAL footage of the target format — not generated examples of it — on the deliverable's platform and aspect, recent;
  the client's own reference is always in the set.
- One line per reference beside the local copies: the source URL, the date it was read, why it is in the set, its length.
  The copies are for analysis only, never a frame in a deliverable, and they sit outside the deliverable tree.
- **Three is the floor.** One reference is a copy, not a pattern; two that disagree cannot be told apart from noise.

**Done when:** 3–5 references are on disk with their source lines, each chosen for a stated reason.

## 2. Measure — the instrument's half

```bash
python3 ~/.claude/skills/ad-spot-preprod/scripts/reference_teardown.py --refs <a> <b> <c> --out review/teardown-<format> \
    --runtime <our length> [--card <seconds of end card>] [--asr small.en]
```

Per reference, in its DISPLAY geometry: every shot with its start, end and length; its framing (the largest frontal face,
found at the same place in two of three sampled frames, skin-toned, with an eye when it is big enough — ECU / CU / MCU /
MS / WS, or none); its motion (the frame's dominant motion by phase correlation — static · drift · pan · handheld — with
the speed in frame widths per second); luma and saturation; the loudness; with `--asr` (local, free) the first spoken
word, the speech rate over the speech span and the words per shot. Across the references: shots per 10 s, the median shot
and its spread, the first cut, the framing and motion mix by screen time. It writes `TEARDOWN.md`, `teardown.json` and one
contact sheet per reference (first · middle · last frame of every shot, labelled).

**Its limits, read before its numbers:** a dissolve reads as one cut or none; a whip pan can read as a cut; a profile or
a very small face reads "none"; "motion" is the frame's dominant motion, camera or subject. The sheet is read before a
number is trusted.

**Done when:** the self-test printed PASS, every reference has its table and its sheet, and the sheets have been read
against the shot lists.

## 3. The written read — the half no instrument does

Per shot, one cell in the CONTENT column of `TEARDOWN.md`: what is on screen, the ONE action, the camera's move, the audio
event (a spoken line, ambient, a music hit), any on-screen text — and what makes the shot read as the format (for phone
footage: the lens, the stabilisation, exposure pumping, framing that misses; they feed the phone-native finish tier and
`UGC-GRAMMAR.md`).

The agent writes it from the sheets and the transcript; for many references a multimodal lane can draft it, given the
clips, the sheets and the measured table and asked to fill THESE columns only. **The measured columns are never replaced
by a model's estimate** — a written breakdown misreports durations and cut counts, and the grid is built on them.

**Done when:** every CONTENT cell is written and every shot's action is one verb.

## 4. Keep the bones, swap the world

A two-column table under `TEARDOWN.md` § Bones kept / world swapped:

| kept (structure) | swapped (content) |
|---|---|
| the shot-length pattern, the first cut, the hook's length · the framing sequence · the camera grammar · the order of kinds of beat · where speech starts and how fast it runs · where the card sits | the people · the places · the props and wardrobe · every word · the jokes · any set piece that identifies its creator |

- **The client's script stays the SSOT.** A reference supplies timing, framing and coverage — the derivation's own
  latitude (`SKILL.md` § 2) — never a character, a beat or a line. A structural element the script cannot carry is
  dropped, not forced.
- A sequence too close to one creator's signature (the same scenes in the same order at the same sizes) is changed until
  it is ours, and the exposure is stated to the operator once (`RISKS.md`).
- Cast inspiration taken from real people's photos gets the likeness check (`RISKS.md` § likeness,
  `video-refs-continuity` REFERENCE-CONTRACT.md).

**Done when:** the table exists and names, for each kept element, the measured value it keeps.

## 5. The beat grid

The instrument's grid is timestamped slots at the references' rhythm — the hook at the references' median first-shot
length, then their median shot — each carrying the framing and motion the references use at that point of their running
time. **Each slot takes ONE action from our beats (`prompts/<SPOT>-beats.json`), in the script's order.**

- **Beat density inside one generation stays at ~1 beat per 3 s or fewer** (`video-prompt-dialects` LINT L12). A reference
  that cuts every 1.5–2 s is realised by CUTS — a long generation's composed cuts, or the edit — never by more actions in
  one shot.
- **With a voice-over the VO's phrases set the cut points** (`video-edit-edl/scripts/phrase_slots.py`), and the grid becomes
  the CHECK on the plan's rhythm (shots per 10 s, the first cut, the framing mix) rather than a mould.
- The grid's durations go into the shot list's partitions (`SHOTLIST-CONTRACT.md`) and its order into the prompt
  (`video-prompt-dialects`). ⚠ **UNDER TEST since 2026-09-18:** a timestamped beat script as the PROMPT of a long
  generation (`[0.0–3.0 s] …` per beat) and an identity block at the prompt's end. Until a costed A/B lands, the house
  template's event script stays the default and neither is written as a rule.

**Done when:** every slot carries one of our beats (or, with a VO, the rhythm check is recorded against the phrase slots),
the grid's source references are named, and the durations sit in the shot list.

## ❌/✅

```
❌ "make it feel like a real vlog" → adjectives in the prompt        ✅ 3–5 real vlogs measured → lengths, sizes, moves → the grid
❌ Durations taken from a model's written breakdown                   ✅ durations from the cut detector; the model writes content only
❌ The reference's scenes, props or people copied                     ✅ its timing, framing and grammar kept; the world swapped
❌ Five actions in a 10 s generation because the reference cuts fast  ✅ its cuts become composed cuts or edit cuts, one action each
❌ One reference "as the template"                                    ✅ three or more; one is a copy study, and it is labelled so
❌ The grid forced over a locked voice-over                           ✅ the VO's phrases cut; the grid checks the rhythm
```

## Failure behavior

- The instrument's self-test fails → fix it before any number from it is used.
- The detector misreads a reference (a dissolve-heavy edit, whip pans) → correct that shot list from its sheet by hand and
  say so in `TEARDOWN.md`; never retune the thresholds on one reference.
- References that disagree (a median shot of 1.2 s against 4 s) → they are two formats: split the set or ask the operator
  which one is meant; never average two formats into one grid.
- Fewer than three references → the teardown is labelled a copy study, and the operator is told.

## Evidence (dated)

- **2026-09-18 — the instrument, validated.** On three aspect versions of one delivered spot with known cut lists (12
  joins each): 36 of 36 joins found within one frame, 0 false cuts; framing read the two presenter shots MCU (face 0.17–0.18
  of the frame height) and every footage shot "none". Two defects were found and fixed on the way: a decorrelation-only
  detector cut a fast underside sweep and a leg entering the frame (fixed by the coarse-layout + histogram rule: at the
  joins coarse 47.9–90.6 and histogram 0.36–1.93, inside shots coarse p99 30–31 and the false candidates' histogram
  0.05–0.12); window-frame corners seen through a window passed a single-frame face hit and a skin test (beige outside)
  and were removed by the two-of-three-frames and eye tests. Self-test: four synthetic scenes, cuts to the frame, the pan
  read at 5.99 px/frame of 6.
- **2026-09-17 — why the step exists.** A creator's published workflow (a paid partnership of a video platform; one
  example, no measurements) put "the reference's structure is the asset" first. Its other steps — stills before video,
  one long generation for consistency, one action per beat, fixing one scene at a time — were already in this corpus with
  measured limits; the measured structure of real references was the missing step.
