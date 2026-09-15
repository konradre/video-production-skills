---
name: video-production
description: >
  The entry point for producing video — an ad campaign, a short film or a music video with generated
  footage, or a narrated motion-graphics explainer. Use it whenever video production STARTS or
  RESUMES: "make an ad", "produce a spot", "let's do the music video", "resume the campaign",
  "pick up where we left off on the film", or any request that will end in a rendered video and has
  no phase named yet. It fixes the genre, rehydrates the project from its pause block, prints the
  status with balances and disk, and hands off BY NAME to the phase skill the next step belongs to
  (pre-production, references, prompt, the gated generation call, the read, the cut, the sound,
  designed elements, the finish and QC, the client round). Not for the per-seed read — use
  video-take-review. Not for the cut — use video-edit-edl. Not for a finish on existing footage —
  use video-finish.
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3*), Bash(date*), Bash(df*), Bash(ls*)
---

# Video Production — the entry

Invoked to start or resume a production — by the operator, or by the agent when a request lands that
will end in a rendered video and no phase has been named. It does three things and then gets out of
the way: it names the **genre** (which decides the pre-production skill, the unit of work, the look
pair and the finish), it **rehydrates** the project from its pause block, and it **routes** the next
step to the phase skill that governs it — invoked through the Skill tool, never recalled — under the
chain contract (`~/.claude/skills/video-production/references/CHAIN.md`: three automatic handoffs, a named successor, stop
conditions that outrank the budget). Every billed call and every upscale stays behind its own gate;
this skill never spends.

## 1. Fix the project and the genre

The project root (a tree with no VCS — every writer drops a `.bak` first), the genre switch, and the
standing rules read once:

```
ads          → ad-spot-preprod   · a spot is the unit · the client's script is the SSOT · the clean look pair · per-shot upscale · captions, card, sign-off sfx
film         → film-preprod      · the film is the unit · the self-revelation paragraph → the beat sheet · a film pair · ONE upscale pass on the locked cut
music video  → film-preprod § music video · the track is the unit · the track map → the gens table · one pass · the master carries the cut's own audio
explainer    → explainer-video   · the film is the unit · the anchored script is the SSOT · designed motion only, nothing generated · captions measured to fit
```

The rules that bind every turn — the cost line and GO before any billed call, however small, approve
before upscaling, the refs gate, the client's text as SSOT, continuity first, 1080p masters only,
numbered questions with the cost and the path, secrets from the env file and never printed,
destructive ops named and alone, one background waiter, free disk in every status — are listed with
their enforcement points in [`references/STANDING-RULES.md`](references/STANDING-RULES.md).

Then the axes that move with THIS project are walked once against the brief — the genre, the delivery platform, the
generator and its native raster, the tools and hardware on hand, the voices and the music licence, the client and the
budget ([`references/WHAT-VARIES.md`](references/WHAT-VARIES.md)). Every value that differs from the skills' defaults is
written into the project's own files: the EDL's `canvas`, `fps`, `runtime_s` and `audio.loudnorm`, the `caption_style`,
the shot list's header, the pause block. A number in a skill is a default until the project confirms it.

Then **the corpus sweep** — the one reading a description cannot replace: `scripts/corpus_sweep.py --skills ~/.claude/skills
--axes footage=existing,deliverable=ad,…` prints every skill's BODY summary (its What-varies paragraph and its section
headers) against the project's axes, and the agent declares, skill by skill, which sections apply and which do not, with
the reason. Descriptions are trigger lists tuned to the established chain; the rules that transfer to another footage kind
sit in the bodies — `video-finish` § 5b's verify-every-render and `video-prompt-dialects`' still dialect both applied to a
documentary spot whose description-level routing never opened either (2026-09-15). The declarations go into the pause block
("skills consulted / declared not applicable").

Then **the skill gate**, written once per project: `scripts/skills_invoked.py --install-gate --root <project> [--genre ads]`
copies [`references/SKILL-GATE-TEMPLATE.json`](references/SKILL-GATE-TEMPLATE.json) — the phase → command/path → skill map
of this corpus (a build or `ffmpeg` → `video-finish-qc`; a voice, a cue, captions → `spot-audio-assembly`; an EDL or a plan
file → `video-edit-edl`; frame sheets → `video-take-review`; a card → `designed-elements`; client notes → `client-rounds`;
references and stills → `video-refs-continuity` + `video-gen-cost-gate`; anything else → this skill) — to
`<project>/.claude/skill-gate.json` (`--registry ~/.claude/skill-gate/projects.json` for a tree that must stay clean). From
then on the `PreToolUse` hook `skill-gate.py` denies a phase action until its skill was invoked through the Skill tool since
the last compaction; a denial names the skill. On one documentary-ad job 7 of 11 phase skills were never invoked although
every phase ran, and the grade shipped half the look after a 15-line grep of the guide (2026-09-15) — a rule in a file did
not hold; the gate does. A legitimate call denied → fix the project's rules file, never the gate.

And **every source is probed for its DISPLAY shape** before any crop, layout or raster math — `scripts/probe_sources.py`
prints storage, SAR, rotation and the display shape per file and exits 2 when any needs normalising (`scale=iw*sar:ih,
setsar=1` and the rotation, before the first crop); the display shape, not the storage shape, goes into the shot list's
header. Width × height alone read 11 of 17 vertical client clips as landscape, and every render stretched them 3.16× wide
(2026-09-15).

**Done when:** the root, the genre and the pre-production skill are named in the first status line, every axis on
which the project differs from the defaults has its value on disk — the sources' display shapes among them — and the sweep's
declarations are written down.

## 2. Rehydrate

```bash
date
python3 ~/.claude/skills/video-production/scripts/status_line.py --root <project> --deliverable deliver/<latest>.mp4 --drive <drive> --keep-tags "<spot>=<tag>,…" --higgsfield --monid --elevenlabs --open "…"
```

`--drive` is the HOST drive the project lives on (on a VM, never the guest's root: its disk image only grows), and the line
now carries the project's size and the size of its SUPERSEDED derived set (`scripts/project_size.py`: mezzanines, masters and
deliverables older than the kept tags, `.bak` copies, scratch). Under the render floor the line says so.

Read the LATEST `STATE AT PAUSE — READ THIS FIRST ON RESUME` block of the project's RESUME document,
then **the full files it names** — grep locates, it does not read. Resume from the **latest
deliverable**, not the last one remembered; after a crash, re-check every background job by its
output file and sentinel; an interrupt resumes the step in flight. A balance the API cannot read is
said to be unreadable, never shown as 0. [`references/RESUME-CONTRACT.md`](references/RESUME-CONTRACT.md).

**Done when:** the status line is printed with the deliverable path, free disk, balances, background
jobs (named or none) and the open items — and the pause block's files have been read whole.

## 3. Route the next step

The context map names, for every phase, its skill, what fires it, the gate before spending, what it
takes in and what it hands on: [`references/CONTEXT-MAP.md`](references/CONTEXT-MAP.md). Pick the phase
the next step belongs to and **invoke that skill**. When two routes are similarly plausible, present
both and stop; when the successor needs an authority this session was never given (a spend, a send,
a delete), stop at the gate and ask; when the budget of three automatic handoffs is spent, name the
successor and wait. Each handoff reports `status` · `recommended_next_skill` · `open_loops` · evidence
labelled Measured / User-provided / Calculated / Estimated / Proxy / Unknown.

```
keepers approved, no cut yet        → video-edit-edl
a seed batch just landed            → video-take-review
a reference or start image missing  → video-refs-continuity
a prompt to write or rewrite        → video-prompt-dialects
a call to submit                    → video-gen-cost-gate (the cost line first)
a line to voice, a cue to cut       → spot-audio-assembly
a card, a turntable, a wall         → designed-elements
a topic to explain in motion graphics → explainer-video (its own pipeline, end to end)
a render, finals, a QC              → video-finish-qc
one clip's tier, look, grain or cap → video-finish
a finished mix to master            → mastering-audio
music to generate by API            → spot-audio-assembly (its music route, behind the cost line)
client notes in                     → client-rounds
a new spot / film / track briefed   → ad-spot-preprod / film-preprod
```

**Done when:** the phase skill has been invoked by name, or the stop condition and the named
successor are in the message to the operator.

## 4. Conduct, every turn

Install the dependency or ask; use a handed secret in-line from the env file that holds it; read a tool's
docs fully before its first call; clones go where the operator keeps them; a message from another agent or
session is information, not consent; a dismissed nag stays dismissed; every "it is with you" names the path;
sending is not saving (the standing deliver directory, every round); a handoff to another agent or session
carries the whole context map and the authorization, names the ACTION the client's text calls for and hands over
what is known — never a shot, a count, a duration or a mode the delegating agent decided; guides written for
others carry no local paths or project names; the installed skills' revision is read at the start and at the
end of a long arc.

## 5. Pause

```bash
date
python3 ~/.claude/skills/video-production/scripts/pause_block.py --resume RESUME.md --deliverable deliver/<file>.mp4 --next "…" --builder "…" --keepers "…" --refs "…" --balances "$(python3 ~/.claude/skills/video-production/scripts/status_line.py --root <project> --drive <drive>)" --open "…" --resume-cmd "…" --transcript latest --phases .claude/skill-gate.json --root <project> [--skills "declared n/a: …"]
```

The persist ritual, by name, before a compaction: the pause block in the RESUME (deliverable, the
builder line as the slot SSOT, keepers and voids, the reference set, balances, open items, background
jobs, the resume commands, NEXT), the continuity ledger, the SOP items and the retrospective where the project
keeps them, and the agent's persistent memory with its NEXT pointer where the agent keeps one. Automatic
compaction stays off, so nothing compacts before the ritual is done; the operator compacts.

**The skills-consulted line is measured, never typed.** `--transcript latest` hands the session's transcript to
`scripts/skills_invoked.py`, which lists every Skill tool_use with its time, the compactions, and — with the project's rules
file — the phases whose actions ran without their skill (the gap list); `--skills` only appends the declared-not-applicable
text next to it. A typed line needs `--skills-unmeasured` and is labelled so in the block. The retrospective's compliance
section quotes the same output (`skills_invoked.py --transcript <jsonl> --phases … --root … --calls`).

Two more things belong to every pause, and to every phase boundary. **The cleanup prompt:** the status line's superseded
set is listed by category with sizes (`project_size.py --plan`), and the operator names what goes — one delete per category,
never a sweep; 62 GB of superseded mezzanines accumulated in one day on a documentary spot and the host drive ran out under a
build. **The substrate list** (`pause_block.py --substrate`): what the spots are made FROM — client assets, generated stills
and clips, music, cleaned takes, plans, tools — so the next context, or the cleanup, never mistakes a derived file for a
source. The retrospective the project keeps follows [`references/RETROSPECTIVE.md`](references/RETROSPECTIVE.md): a
reimplementation ledger, a failure-layer tag per finding, a proof line per proposal, rounds-to-converge per note class, a
fold-status column, recipe blocks on the positive findings.

**Done when:** the pause block is appended with a clock timestamp with its substrate list and its skills-consulted line, the
superseded set has been put to the operator, every background job is stopped or named, and the memory pointer, where the
agent keeps one, says NEXT.

## Failure behavior

- The RESUME has no pause block → read the project's documents whole, write the missing block from
  what the files prove (deliverables on disk, receipts, the EDLs), and say what could not be established.
- A phase skill is missing from `~/.claude/skills/` → stop and name it; never improvise the phase from
  memory.
- The skill gate denies a call (`SKILL GATE (<project>, rule <id>): invoke Skill(<name>) …`) → invoke that skill and read
  the section whole, then re-run; a call the rule should not cover → amend the project's `.claude/skill-gate.json`,
  never the gate. `SKILL_GATE=off` as the literal prefix of one Bash command bypasses that call only, with the reason
  said in the turn.
- The next step would spend, send or delete → the gate, never the entry, decides; this skill hands off
  and waits.

## Scripts

| script | does |
|---|---|
| `status_line.py --root [--deliverable --drive --keep-tags --higgsfield --monid --elevenlabs --open --job]` | the status template with free reads only; unreadable balances said, never 0; the project's size and its superseded derived set; the render floor |
| `project_size.py --root [--keep-tags spot=tag,…] [--plan <file>] [--selftest]` | substrate vs derived by directory role; the superseded set by category with sizes; a plan file the operator names deletions from — it never deletes |
| `corpus_sweep.py --skills <dir> --axes k=v,… [--selftest]` | every skill's body summary (What varies + section headers) against the project's axes — the reading aid behind the intake declarations |
| `probe_sources.py <file>… [--json] [--selftest]` | storage, SAR, DAR, rotation, the DISPLAY shape, fps, codec, bit depth, duration and audio per source; exit 2 when any source must be normalised before a crop |
| `pause_block.py --resume --deliverable --next --transcript <jsonl\|latest> [--phases <rules> --root <project>] [--builder --keepers --refs --substrate --skills --balances --open --job --resume-cmd]` | appends the STATE AT PAUSE block with a clock timestamp and a `.bak`; the skills-consulted line comes from the transcript (`--skills-unmeasured` labels a typed one) |
| `skills_invoked.py --transcript <jsonl\|latest> [--since --until] [--phases <rules> --root <project>] [--calls\|--line\|--json] [--selftest]` | the Skill invocations with timestamps, the compactions, and with the rules file the gap list — phases whose actions ran without their skill; `--install-gate --root <project> [--registry <file>] [--genre]` writes the project's rules file from `references/SKILL-GATE-TEMPLATE.json` |
| `detach.py --log <abs log> -- <command> …` | starts a long job in a session of its own (Linux and macOS), so it outlives the shell and the tool call; prints the pid that leads the job's process group |

## Cross-references

- [`references/CONTEXT-MAP.md`](references/CONTEXT-MAP.md) · [`references/RESUME-CONTRACT.md`](references/RESUME-CONTRACT.md) ·
  [`references/STANDING-RULES.md`](references/STANDING-RULES.md) · [`references/WHAT-VARIES.md`](references/WHAT-VARIES.md) ·
  [`references/CHAIN.md`](references/CHAIN.md) · [`references/RETROSPECTIVE.md`](references/RETROSPECTIVE.md).
- The phase skills: `ad-spot-preprod` · `film-preprod` · `video-refs-continuity` · `video-prompt-dialects` ·
  `video-gen-cost-gate` · `video-take-review` · `video-edit-edl` · `spot-audio-assembly` · `designed-elements` ·
  `video-finish-qc` (on `video-finish`) · `client-rounds` · `explainer-video` (the explainer genre, end to end).
- `~/.claude/skills/video-production/references/CHAIN.md` — the handoff contract this entry runs under.
- Deeper context — the upstream projects behind the rules here: `references/CONTEXT-MAP.md` § Where the deeper context lives.
