# The round ledger — one table per campaign, one row per client item

| round | date | client # → spot | version delivered | item | class | operator's answer | outcome (file / EDL / cost) | status |
|---|---|---|---|---|---|---|---|---|
| | | | | | CUT · RECYCLE · REBUILD · CAUSALITY · APPROVE · GATE | | | shipped · frozen · open |

## Rules of the ledger

- **Client numbering = delivery order**, mapped once per round; the spot id is what the build uses.
- **Approvals are quoted** and the spot's status becomes `frozen`; anything later for that spot is an
  alternate asset with its own row.
- **Every version is a new EDL file and a new deliverable name** (`-v9b`, `-final`); the ledger names
  both, plus the credits the round cost.
- **Locked placements** ("lock these in for now") are recorded so the next version keeps them.
- **Finals** are a row per spot naming the exact version the client chose and the file in `deliver/final/`.
- **The round record** (`prompts/CLIENT-ROUND-<date>.json`, written by `notes_triage.py`) holds each note's anchor, kind,
  check row and answer by number; the ledger row carries its class, the operator's answer and the outcome, and the round
  column names the record.
- The ledger and the resume block carry status; STATUS tick-boxes in the shot script do not.
