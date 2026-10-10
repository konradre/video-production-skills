---
name: client-rounds
description: >
  Runs a CLIENT ROUND on delivered generated-video work: the notes saved verbatim and mapped to spot ids, every
  cited beat located in the delivered file, the EDL history and the script before anything moves, the notes
  curated into a numbered list (CUT, RECYCLE, REBUILD, CAUSALITY, APPROVE, GATE; each an ERROR or TASTE, anchored,
  and every uncaught ERROR given its check) the operator answers per item, the fixes executed by the ladder into a
  NEW version with approved spots frozen, a compare page of the new version against the last lined up by event,
  and the ask — every note answered by its number, the checks read from the run log — as numbered questions with
  cost and path inline. Use when client feedback arrives, a delivered spot must be revised, a deliverable is about
  to be sent, or the operator must choose. Triggers — "client feedback", "the client's notes", "curate the list",
  "what did the client mean", "approved as is", "alternate ending", "send this to the client", "which option",
  "lock these in", "finals for the client". Not for the cut itself — use video-edit-edl.
  Not for the render or the QC instruments — use video-finish-qc. Not for a new brief or a new spot — use
  ad-spot-preprod.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3*), Bash(ffprobe*), Bash(ls*)
---

# Client Rounds

The client's notes are the most expensive words in the project: a note acted on before it was
located cost a wrong fix, a note answered with a paragraph cost a re-ask, a note "fixed" by a
regeneration cost forty credits that an edit would have saved. The round is a protocol with the
operator's answer in the middle of it, and the operator — never the agent — talks to the client.

**What varies.** The classes carry one client's words as examples — another client's vocabulary maps onto the same six;
the Windows paths, the chat cap and the deliver directory in the ask are the operator's environment. Locating first, the
numbered list and the new-version rule do not move — `video-production/references/WHAT-VARIES.md`.

## 1. Receive and record

Save the notes verbatim, dated (`prompts/CLIENT-NOTES-<date>.txt`); map the client's numbering to spot
ids (**client numbering = delivery order**); quote every approval into the ledger in the client's
words — an approved spot **freezes**, and a later idea for it becomes an alternate asset. The
client's domain expertise decides what lands; their wording is exact; the operator sets the diction.

**Done when:** the notes file exists, the mapping is written at its head (`#5=S01, #6=S02` — `notes_triage.py` reads it as the
map), and each approval is a row
in the ledger with its quote ([`references/ROUND-LEDGER.md`](references/ROUND-LEDGER.md)).

## 2. Locate every cited beat before anything moves

**Read the client's script end to end before any audit measurement** — it can reframe a finding: a held beat the
script asks for reads as a frozen body until the script is read. Then for each note: the frame time in the DELIVERED
file, the version that introduced it in the EDL history, and what the SCRIPT says — the client may be pointing back at
the script's original idea. A note that
names a version is checked against that file (`video-take-review` `frame_match.py` for a posted frame). A note about a
SOUND at a timecode is located by transcribing the DELIVERED file at that timecode (± 3 s) and quoting back what is heard
before anything changes — "a bit of VO at the very start" was the subject's own spoken filler between two runs, and the
first fix, made from word times, trimmed a number instead (2026-09-15).

**Done when:** every note carries a frame time, an EDL version and a script line beside it — and a sound note the
transcript of the delivered audio at its timecode.

## 3. Curate the numbered list — no action

```bash
python3 ~/.claude/skills/client-rounds/scripts/notes_triage.py --notes prompts/CLIENT-NOTES-<date>.txt --map "#5=S01,#6=S02" --out prompts/CLIENT-ROUND-<date>.md
```

Classify in the client's own words — **CUT** ("no regeneration needed, just cut it"),
**RECYCLE** ("keep the scene from the original clip"), **REBUILD** ("rebuild the flow"), **CAUSALITY** ("both shots work individually, but one doesn't cause the other" =
a rejection of the method: one continuous joke, the take's own footage first, one connecting gen
last), **APPROVE**, **GATE** (product proportion, likeness — pre-production gates from now on). Then
the operator answers per item (a number, a yes/no, or "best judgement"). Nothing executes before the answers. [`references/ROUND-PROTOCOL.md`](references/ROUND-PROTOCOL.md).

**Sort every note ERROR or TASTE** beside its class. An ERROR is wrong whatever anyone likes — a word cut off or touching
the frame edge, a misspelled name, a wrong number or price, a pop or a click, a black or frozen frame, sound out of sync,
the wrong size; TASTE is colour, pace, music, wording, feel. Both get fixed. **Every ERROR reached the client past our
checks, so it gets its check row now, at the round:** the check that ran and missed it, with why, or a proposed check —
what it measures, the skill that would own it, this note as its example. At the round's close each proposal becomes a
`pending` row of the project's fold table and reaches that skill only through a reviewed change, never as an edit to an
installed copy.

**Anchor every note** on the spot § 2 located: a moment (`at`, seconds in the delivered file), a stretch (`from`, `to`), a
spot on the frame (`x`, `y` as fractions from the top left, beside its `at` — read off a frame, it is an `estimate` and is
said as one when the notes are read back), a paragraph of the script, or the whole version. `notes_triage.py` writes the
round record beside the list (`prompts/CLIENT-ROUND-<date>.json`, never overwritten): each note's number, spot, class,
suggested kind, the client's words, and an anchor wherever the words carry a timecode; the rest is filled in as the round
goes (ROUND-PROTOCOL.md § The round record). A round about one video passes `--spot <id>`, the spot every note gets until
one names another; a project whose ids are not `S01`-style passes its own pattern (`--ids 'EP\d+'`). With `--map`, a `#N`
the map lacks reads spot `?` until it is mapped. Every paragraph with a word in it is an item, a short note included —
the file's head (the mapping, a date line) and a sign-off's signature block aside. A paragraph that is no note — a greeting, a thank-you, a sign-off — is
`CHAT`: no spot, no answer, and the ask and the compare page skip it; `notes_triage.py` suggests it only for a paragraph
made wholly of a greeting, thanks or a sign-off, with no question, request word, spot, timecode or note word — "Hi, this
one looks great!" stays a note to sort — and the list still shows it.

**Done when:** the list is saved with a class, a kind and an anchor per note, a check row on every ERROR, and an operator
answer per item.

## 4. Execute by the ladder, into a new version

Cut (frame-exact, zero credits) → re-voice the same words when a line "lands flat" AND build the
client's alternative in the same slots → recycle the older version's shot → regen last, through the
cost line, with the approved cut frozen. A rebuild takes its STRUCTURE from the script — one generation per
continuity partition — never from the rejected cut's scene boundaries (`video-production/references/PREPRODUCTION-CORE.md` § 1): scene detection on a
rejected file reconstructs the previous producer's split, mistakes included. Every version is a **new EDL file and a new deliverable name**
(`video-edit-edl`); shipped files are never edited; "lock these in" placements are kept; alternates
are their own EDLs. A GATE item changes the pre-production rules (`ad-spot-preprod`), not just this spot. The note set
names what to KEEP: beside each fix, a guard for what the previous version got right (the brand system, each spot's hook,
the concept's device) — five fixes that each constrained one defect all landed, and the piece lost its design (2026-09-15).

**Every note is answered by its number** in the round record once the new version settles: `done` with exactly what
changed and where — never "addressed" —, `partly` or `not_done` with why, or `frozen` (an approved spot stays as it is; a
new idea for it becomes an alternate).

**Done when:** the new version exists under its own name, the previous version is byte-identical, and
every item's outcome (file, EDL, credits) is on its ledger row and its answer in the round record.

## 5. QC, then the ask

```bash
python3 ~/.claude/skills/client-rounds/scripts/delivery_ask.py --root <project> --edl edit/<SPOT>-EDL-v9.json --deliv deliver/<file>.mp4 --winroot '<project root as the operator opens it>' --log logs/<SPOT>-v9-run.txt --round prompts/CLIENT-ROUND-<date>.json --compare review/<SPOT>-v8-v9.html --changed "…" --doubt "0:41 …" --q "… (37.5 cr) — yes or no?"
```

The delivered file is QC'd first (`video-finish-qc`); then the ask: the spot and version by its full
path as the operator opens it, runtime and size (≤ 30 MiB in chat, else the path), what changed mapped to the client's
items, the VO script as placed, the QC line and the beat sheet, **residual doubts with frame times in
the note — never a re-roll question**, what is frozen, and the decisions as **numbered plain questions
with the cost inline** and a default. Every round is saved to the standing deliver directory with its
provenance — sending is not saving. [`references/THE-ASK.md`](references/THE-ASK.md).

**A round's ask answers every note by its number** (`--round prompts/CLIENT-ROUND-<date>.json`) and lists the checks
proposed for its errors. **Its checks are read, never retyped:** `--log` names the run log (`--qc` counts as one), and the
ask carries the last `EDL-CHECK` and `BEAT-SHEET` line printed for this EDL and the last `QC-DELIVERABLE` line for this
file. The finish runs only the beat gate, so run `edl_check.py` and `beat_sheet.py` into the version's run log before the
ask (`video-edit-edl` § 4; seconds, no render). A check with no line refuses the ask — re-run it, or `--na "BEAT-SHEET: <why>"` for one that does not apply. A FAIL
is shown, never withheld: QC's judgement rows are the operator's call. Every paragraph read as `CHAT` is listed under
"read as no note — check each", so a note misread as a greeting is seen, never skipped unseen.

**A revision goes with its compare page** — the operator's review, never the client's:

```bash
python3 ~/.claude/skills/client-rounds/scripts/compare_versions.py --root <project> --a deliver/<SPOT>-v8.mp4 --b deliver/<SPOT>-v9.mp4 --edl-a edit/<SPOT>-EDL-v8.json --edl-b edit/<SPOT>-EDL-v9.json --round prompts/CLIENT-ROUND-<date>.json --out review/<SPOT>-v8-v9.html
```

The two versions side by side, stacked or as a wipe, lined up by EDL event — a moment of the new version shows the same
take time of the same event in the old one, however the cut moved — with every inserted, removed, re-timed or replaced
event labelled and the round's notes as marks to jump to. Its path rides in the ask (`--compare`); `qc_deliverable.py
--prev` is its measured twin.

**Done when:** the ask has a path on every item, a cost on every question, every note of the round answered by its
number, the three checks read from the run log (or `--na` with why), and the files are in the
deliver directory before the message is written.

## 6. Send → wait; finals

The operator sends; the agent waits and does not generate speculatively. When the client names finals,
each is a ledger row naming the exact version, rendered by the finals run with the current card
(`video-finish-qc`), and the campaign's frozen set is complete.

**Done when:** the ledger shows every spot frozen or in a named round, and `deliver/final/` holds
one file per final.

## Failure behavior

- A note that cannot be located in the delivered file → ask the operator ONE concise question with
  the two candidate readings and their frame times; never act on a guess.
- The operator's answer names an older version → that version's EDL is the source; the current EDL
  is not edited in place.
- A regen answer → the cost line first (`video-gen-cost-gate`); a "no" leaves the item open on the
  ledger, not silently dropped.
- A residual doubt after a final → the note, not a re-roll ask.
- `delivery_ask.py` refuses (exit 2, no message written) while a note of the round has no spot (a `CHAT` paragraph is no note), no anchor, a kind still `?`, an
  ERROR with no check row or no answer, or while a check has no line in the run log — each refusal names its item. Each
  has a truthful way through: `not_done` with why is an answer, and `--na` with why covers a check that does not apply.
  A run log from before the gates named their EDL reads as missing: re-run `edl_check.py` and `beat_sheet.py` (seconds,
  no render).

## Scripts

| script | does |
|---|---|
| `notes_triage.py --notes [--map] [--spot] [--ids] [--out]` · `--selftest` | the curated numbered list with a class, a suggested kind (ERROR · TASTE) and an anchor per item and a blank answer column; with `--out`, the round record beside it (`.json`, never overwritten) |
| `delivery_ask.py --root --edl --deliv --winroot [--log --qc --na --round --compare --changed --doubt --frozen --q --default]` · `--selftest` | the delivery message: path, size, VO table, the checks read from the run log, every round note answered by its number and the checks proposed, the compare page, doubts, frozen, numbered questions; refuses (exit 2) while a note or a check is missing |
| `compare_versions.py --root --a --b [--edl-a --edl-b] [--round] --out` · `--selftest` | one offline page: version N against N−1 side by side, stacked or as a wipe, lined up by EDL event (inserted, removed, re-timed and replaced events labelled), the round's notes as marks; never overwrites |

## Cross-references

- [`references/ROUND-PROTOCOL.md`](references/ROUND-PROTOCOL.md) · [`references/THE-ASK.md`](references/THE-ASK.md) ·
  [`references/ROUND-LEDGER.md`](references/ROUND-LEDGER.md).
- `video-edit-edl` — the cut and the new version; `video-take-review` — locating a posted frame;
  `spot-audio-assembly` — re-voicing; `video-finish-qc` — the QC and the finals; `ad-spot-preprod` — the
  gates a client note creates.
- Handoffs follow `~/.claude/skills/video-production/references/CHAIN.md`.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
