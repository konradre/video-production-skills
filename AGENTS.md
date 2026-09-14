# AGENTS.md — video-production-skills

Orientation for an agent pointed at this repository. `README.md` is the long form, `METHOD.md` is the
method in the order it runs, `CHAIN.md` is the handoff contract.

## What this is

Fifteen agent skills, two host-side tools and a look library for producing video: short-form ad
campaigns, short films and music videos made from generated footage, and narrated motion-graphics
explainers drawn in code.

Each skill is a `SKILL.md` plus a `references/` directory (contracts and measurements) and a `scripts/`
directory (small Python and shell tools). Every script prints its usage on `--help` and changes nothing
when asked. Scripts that work inside a project take `--root <project>`.

These are plain `SKILL.md` files, so any agent that reads that format runs them. The scripts need no
agent at all.

⚠ `skills/` is generated from a separate source tree. Never hand-edit it here — see § Boundaries.

## Install

| agent | command |
|---|---|
| Claude Code | `./install.sh` |
| Codex | `./install.sh ~/.agents/skills` |

Both forms write the `~/.claude/skills/` link, because commands inside the skills call
`~/.claude/skills/<skill>/…` by absolute path. Codex needs its own folder as well, which the second form
adds; the installer accepts any number of extra folders. It is re-runnable and skips anything that
exists and is not a symlink.

Discovery: Codex scans `.agents/skills` and `$HOME/.agents/skills` and invokes with `$<skill-name>`.
Claude Code scans `~/.claude/skills`.

Base: Python 3.10 or newer with `numpy`, `Pillow`, `scipy`, `PyYAML`, plus `ffmpeg`. On Windows, run the
kit inside WSL2.

## Keys

```bash
cp .env.example .env                                             # fill in only the vendors you use
set -a; . ~/.claude/skills/video-production/../../.env; set +a   # load in the command that needs it
```

`.env.example` names every key and variable the kit reads and what each is for. Scripts read from the
process environment, never from the file. **A key never goes into a skill, a prompt, a receipt or a
command line.**

## Local GPU — settle this before installing anything heavy

Three steps want a GPU of your own. VRAM decides which of them run, not whether a GPU exists.

| your card | local generation | local finish (Topaz, Dehancer) |
|---|---|---|
| 24 GB NVIDIA | yes, and it holds the whole card | yes |
| ~11 GB NVIDIA | no | yes, near the edge |
| under ~11 GB | no | no |
| any AMD, Intel or APU | no — generation needs CUDA | Dehancer runs on AMD via OpenCL; Intel does not |

```
no local GPU, or under ~11 GB, or non-NVIDIA?
  → ignore README § ComfyUI, § MiniMax H3, § Topaz
  → leave every COMFY_*, TOPAZ_*, TVAI_* unset
  → five scripts cannot run — comfy_up.sh, comfy_ready.py, scene_blockout.py,
    upscale_local.sh, topaz_upscale.py. Nothing else calls them.
  → you keep all fifteen skills: every generation route is hosted anyway,
    the whole finish chain works, and a look applies as an ffmpeg lut3d filter
  → ONE METHOD CHANGES: without scene_blockout.py, read the geometry off the
    keeper frame at 2–4× zoom into the prompt verbatim, and say
    "no scene proxy for this shot" in the GO ask
```

On an APU the integrated GPU takes its VRAM from system RAM, so the carve-out and everything else draw
on one pool. The measured tiering, card by card, is **README § If you have no GPU, or a small one** —
that section owns it; this one is the routing decision only.

`tools/resolve-pass/` sits on a different axis: it needs Windows, DaVinci Resolve **Studio** and a
Dehancer licence whether or not you have a card, because external scripting is Studio-only. Without it a
look still applies as a LUT; what you lose is halation, bloom, grain and gate weave.

## Rules that bind every turn

Full table with enforcement points: `skills/video-production/references/STANDING-RULES.md`.

- 🔴 A cost line and the operator's explicit GO come before any billed call. The amount does not matter.
- 🔴 Nothing is upscaled before the operator has approved the take.
- 🔴 The refs gate runs in code before every generation call.
- 🔴 The client's text is the single source of truth. Additions are proposed as cost lines, never assumed.
- Continuity is the first acceptance test. The start image is the previous shot's last state.
- Never resubmit a billed job. `COMPLETED` is not success. Receipts keep the raw reply.
- Masters are 1080p only; at most 30 MiB in chat, otherwise the path.
- Decisions go to the operator as numbered plain questions, with the cost and the full path inline.
- Invoke a skill at the phase it governs. Never work from a recalled copy; re-read one whose revision moved.
- A number in a skill is a default until the project confirms it.
- Install the dependency or ask. Never a lazy workaround.
- Destructive ops: the operator names the exact target, one command per target, alone.
- One background waiter at a time. Poll, never follow. A missing sentinel is a failure.
- Capture a verdict on the same line as its command — `cmd | tail` returns tail's exit code.
- Verify a plan step immediately before it runs. A plan is a set of hypotheses, not instructions.

## How a production runs

`video-production` is the entry skill: give it the project root and the genre. It reads the project's
pause block, prints a status line, and hands off to the phase that owns the next step.

pre-production → references and continuity → the prompt → the gated generation call → the read → the cut
→ the sound → designed elements → the finish and QC → the client round

Handoffs are bounded: three automatic hops after the originating skill, a visited set, and stop
conditions that outrank the budget. `CHAIN.md` is the contract.

## Boundaries

- **Never hand-edit anything under `skills/` in this repository.** It is exported from a separate source
  tree through an overlay, so an edit here is silently overwritten by the next export. Open an issue
  describing the change instead.
- `README.md`, `METHOD.md`, `CHAIN.md`, `AGENTS.md`, `CLAUDE.md`, `install.sh` and `.env.example` are
  this repository's own files and are edited here.
- No credential goes into any file this repository tracks. `.env` is ignored by git.

## Where to look next

| you want | read |
|---|---|
| the long-form setup, tier by tier | `README.md` |
| the method in order, and why each rule exists | `METHOD.md` |
| the handoff budget and stop conditions | `CHAIN.md` |
| the two Windows tools and their variables | `tools/README.md` |
| the grading method and the look recipes | `look-library/GUIDE.md` |
| every key and variable, with what reads it | `.env.example` |
