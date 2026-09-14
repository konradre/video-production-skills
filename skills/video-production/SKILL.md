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

**Done when:** the root, the genre and the pre-production skill are named in the first status line, and every axis on
which the project differs from the defaults has its value on disk.

## 2. Rehydrate

```bash
date
python3 ~/.claude/skills/video-production/scripts/status_line.py --root <project> --deliverable deliver/<latest>.mp4 --drive <drive> --higgsfield --monid --elevenlabs --open "…"
```

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
python3 ~/.claude/skills/video-production/scripts/pause_block.py --resume RESUME.md --deliverable deliver/<file>.mp4 --next "…" --builder "…" --keepers "…" --refs "…" --balances "$(python3 ~/.claude/skills/video-production/scripts/status_line.py --root <project> --drive <drive>)" --open "…" --resume-cmd "…"
```

The persist ritual, by name, before a compaction: the pause block in the RESUME (deliverable, the
builder line as the slot SSOT, keepers and voids, the reference set, balances, open items, background
jobs, the resume commands, NEXT), the continuity ledger, the SOP items and the retrospective where the project
keeps them, and the agent's persistent memory with its NEXT pointer where the agent keeps one. Automatic
compaction stays off, so nothing compacts before the ritual is done; the operator compacts.

**Done when:** the pause block is appended with a clock timestamp, every background job is stopped or
named, and the memory pointer, where the agent keeps one, says NEXT.

## Failure behavior

- The RESUME has no pause block → read the project's documents whole, write the missing block from
  what the files prove (deliverables on disk, receipts, the EDLs), and say what could not be established.
- A phase skill is missing from `~/.claude/skills/` → stop and name it; never improvise the phase from
  memory.
- The next step would spend, send or delete → the gate, never the entry, decides; this skill hands off
  and waits.

## Scripts

| script | does |
|---|---|
| `status_line.py --root [--deliverable --drive --higgsfield --elevenlabs --open --job]` | the status template with free reads only; unreadable balances said, never 0 |
| `pause_block.py --resume --deliverable --next [--builder --keepers --refs --balances --open --job --resume-cmd]` | appends the STATE AT PAUSE block with a clock timestamp and a `.bak` |
| `detach.py --log <abs log> -- <command> …` | starts a long job in a session of its own (Linux and macOS), so it outlives the shell and the tool call; prints the pid that leads the job's process group |

## Cross-references

- [`references/CONTEXT-MAP.md`](references/CONTEXT-MAP.md) · [`references/RESUME-CONTRACT.md`](references/RESUME-CONTRACT.md) ·
  [`references/STANDING-RULES.md`](references/STANDING-RULES.md) · [`references/WHAT-VARIES.md`](references/WHAT-VARIES.md) ·
  [`references/CHAIN.md`](references/CHAIN.md).
- The phase skills: `ad-spot-preprod` · `film-preprod` · `video-refs-continuity` · `video-prompt-dialects` ·
  `video-gen-cost-gate` · `video-take-review` · `video-edit-edl` · `spot-audio-assembly` · `designed-elements` ·
  `video-finish-qc` (on `video-finish`) · `client-rounds` · `explainer-video` (the explainer genre, end to end).
- `~/.claude/skills/video-production/references/CHAIN.md` — the handoff contract this entry runs under.
- Deeper context — the upstream projects behind the rules here: `references/CONTEXT-MAP.md` § Where the deeper context lives.
