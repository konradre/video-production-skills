# The retrospective — the format that refines the corpus, not just the project

A project retrospective exists to change the skills, so its format is set by what a fold needs. Append at every audit,
stop and phase boundary; one file per project, kept where the project keeps its research. The retrospective that set this
format came from a documentary ad job (an equipment-auction spot, 2026-09-15).

## § 1–2 — the job and the arc, in a paragraph each

What was asked, by whom, with which constraints; what shipped, in which versions; where the operator's rulings live verbatim.

## § 3 — findings: one section per issue

```
### 3.N <one-line claim> [severity / LAYER]
**Evidence.** what happened, with the timecodes, versions, files and the operator's words.
**Lesson.** the rule, stated so it transfers to the next project.
**Lands.** the skill and section (or the instrument) the rule goes into, with its proposal number.
**Status.** applied / reverted / noted — and, for a positive finding, a RECIPE block (inputs, commands, acceptance).
```

**LAYER is one of five, and it decides the fold's priority:**

| layer | the description did not surface it | the body lacks the rule | the script is missing or wrong | the harness, the disk, the permissions | the operator's or the client's direction |
|---|---|---|---|---|---|
| tag | routing | body | instrument | lane | direction |

Count the tags before folding: instrument and body findings change the corpus; routing findings change descriptions and the
intake sweep; lane findings change the standing rules; direction findings are recorded, not folded.

## § 3b — the reimplementation ledger

Every project-local tool that stood in for a skill stage, one row each: the stage it replaced · what it did better · what it
lost (the gates that did not run). The "better" column is the fold-in list; the "lost" column is the cost of the shortcut.

## § 4 — proposals, each foldable alone

```
- **P<n> <skill> § <section>:** the change, in one sentence (§3.N). Proof: <the known-answer case that shows the fold works>.
```

A proposal that lands as a script names its selftest case; one that lands as a rule names the example the rule would have
caught. "Lands" without "proved by" is how a fold rots.

## § 5 — measurements, method stated

Credits and dollars by call; **rounds-to-converge per note class** (picture, audio, type, direction): the operator's time,
which credits do not show, and the strongest signal for where a reel-first or listen-gate step pays.

## § 6 — fold status

| P | lands in | status: folded / pending / rejected | landing commit |

Kept current across projects in the research tree's fold-status table, so a lesson that recurs on the next job is visible as
a proposal that never landed.
