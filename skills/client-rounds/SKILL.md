---
name: client-rounds
description: >
  Runs a CLIENT ROUND on delivered generated-video work: the notes saved verbatim and mapped to spot ids, every
  cited beat located in the delivered file, the EDL history and the script before anything moves, the notes
  curated into a numbered list (CUT, RECYCLE, REBUILD, CAUSALITY, APPROVE, GATE) the operator answers per item,
  the fixes executed by the ladder into a NEW version with approved spots frozen, and the ask as numbered
  questions with cost and path inline. Use when client feedback arrives, a delivered spot must be revised, a
  deliverable is about to be sent, or the operator must choose. Triggers — "client feedback", "the client's
  notes", "curate the list", "what did the client mean", "approved as is", "alternate ending", "send this to the
  client", "which option", "lock these in", "finals for the client". Not for the cut itself — use video-edit-edl.
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

**Done when:** the notes file exists, the mapping is written at its head, and each approval is a row
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

**Done when:** the list is saved with a class per item and an operator answer per item.

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

**Done when:** the new version exists under its own name, the previous version is byte-identical, and
every item's outcome (file, EDL, credits) is on its ledger row.

## 5. QC, then the ask

```bash
python3 ~/.claude/skills/client-rounds/scripts/delivery_ask.py --root <project> --edl edit/<SPOT>-EDL-v9.json --deliv deliver/<file>.mp4 --winroot '<project root as the operator opens it>' --qc logs/qc.txt --changed "…" --doubt "0:41 …" --q "… (37.5 cr) — yes or no?"
```

The delivered file is QC'd first (`video-finish-qc`); then the ask: the spot and version by its full
path as the operator opens it, runtime and size (≤ 30 MiB in chat, else the path), what changed mapped to the client's
items, the VO script as placed, the QC line and the beat sheet, **residual doubts with frame times in
the note — never a re-roll question**, what is frozen, and the decisions as **numbered plain questions
with the cost inline** and a default. Every round is saved to the standing deliver directory with its
provenance — sending is not saving. [`references/THE-ASK.md`](references/THE-ASK.md).

**Done when:** the ask has a path on every item, a cost on every question, and the files are in the
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

## Scripts

| script | does |
|---|---|
| `notes_triage.py --notes [--map] [--out]` | the curated numbered list with a class per item and a blank answer column |
| `delivery_ask.py --root --edl --deliv --winroot [--qc --changed --doubt --frozen --q --default]` | the delivery message: path, size, VO table, QC, doubts, frozen, numbered questions |

## Cross-references

- [`references/ROUND-PROTOCOL.md`](references/ROUND-PROTOCOL.md) · [`references/THE-ASK.md`](references/THE-ASK.md) ·
  [`references/ROUND-LEDGER.md`](references/ROUND-LEDGER.md).
- `video-edit-edl` — the cut and the new version; `video-take-review` — locating a posted frame;
  `spot-audio-assembly` — re-voicing; `video-finish-qc` — the QC and the finals; `ad-spot-preprod` — the
  gates a client note creates.
- Handoffs follow `~/.claude/skills/video-production/references/CHAIN.md`.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
