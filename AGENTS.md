# AGENTS.md — video-production-skills

Orientation for an agent that has just been pointed at this repository. `README.md` is the long form,
`METHOD.md` is the whole method in the order it runs, and `CHAIN.md` is the handoff contract. This file
is what you need before the first action.

## What this is

Fifteen agent skills, two host-side tools and a look library for producing video: short-form ad
campaigns, short films and music videos made from generated footage, and narrated motion-graphics
explainers drawn in code.

Each skill is a `SKILL.md` with its steps and completion criteria, a `references/` directory holding the
contracts and the measurements, and a `scripts/` directory of small Python and shell tools. **Every
script prints its usage on `--help` and changes nothing when asked.** Scripts that work inside a project
take its folder as `--root <project>`.

The skills are plain `SKILL.md` files and work in any agent that reads that format — Claude Code and
Codex both do. The scripts are plain Python and bash and need no agent at all.

## Install — do this first

```bash
./install.sh                      # links skills/* into ~/.claude/skills/
./install.sh ~/.agents/skills     # Codex: links into BOTH ~/.claude/skills/ and ~/.agents/skills/
```

**Both links are required, whichever agent you run.** 24 files inside the skills call
`~/.claude/skills/<skill>/…` by absolute path, so that link is load-bearing even when your agent loads
its skills from somewhere else. The installer always writes the `~/.claude/skills/` link and adds any
folder you name as an argument. It is re-runnable, and it leaves alone anything that exists and is not a
symlink.

Codex discovers skills under `.agents/skills` and `$HOME/.agents/skills`, and invokes one with
`$<skill-name>`. Claude Code discovers them under `~/.claude/skills`.

Base requirements: Python 3.10 or newer with `numpy`, `Pillow`, `scipy` and `PyYAML`, plus
[ffmpeg](https://ffmpeg.org/download.html). On Windows, run the kit inside WSL2.

## Keys

Copy `.env.example` to `.env` (git ignores it) and fill in only the vendors you use. That file names
every key and variable the kit reads and what each one is for — it is the single place for all of them.

Scripts read keys from the process environment, never from the file, so load it in the same command that
needs it:

```bash
set -a; . ~/.claude/skills/video-production/../../.env; set +a
```

**A key never goes into a skill, a prompt, a receipt or a command line.**

## The one decision that changes your setup plan

Three steps want a GPU of your own. Which ones you can run is decided by VRAM, not by whether a GPU
exists. Settle this before installing anything heavy — it determines which sections of `README.md` you
should ignore outright.

| what you have | what runs locally |
|---|---|
| **24 GB NVIDIA** | everything, but local generation holds the whole card |
| **~11 GB NVIDIA** | the local *finish* (Topaz, Dehancer) fits; local *generation* does not |
| **under ~11 GB**, or **any AMD/Intel card or APU** | treat as no-local-GPU: every generation route is hosted anyway |

On an APU the VRAM is carved out of system RAM, so 4 GB of it also costs you 4 GB of the RAM everything
else wants. On a 16 GB machine that is the binding constraint, not the GPU.

**In the no-local-GPU case**, ignore the README's ComfyUI, MiniMax H3 and Topaz sections, leave every
`COMFY_*`, `TOPAZ_*` and `TVAI_*` variable unset, and know that five scripts cannot run
(`comfy_up.sh`, `comfy_ready.py`, `scene_blockout.py`, `upscale_local.sh`, `topaz_upscale.py`). Nothing
else calls them. You keep all fifteen skills, every generation route, the whole finish chain and the
look library — applying a look is an ffmpeg `lut3d` filter.

One *method* changes, not just a tool: without `scene_blockout.py` you cannot compute a room from a
keeper frame, so the geometry for a new angle is read off that frame at 2–4× zoom and copied into the
prompt verbatim, and the GO ask says "no scene proxy for this shot".

`tools/resolve-pass/` is a separate axis: it needs Windows, DaVinci Resolve **Studio** and a Dehancer
licence whether or not you have a card. Resolve's free edition cannot drive it — external scripting is
Studio-only — and on free Resolve the export is CPU-only, so hardware encoding sits idle. Without the
pass a look still applies as a LUT; what you lose is halation, bloom, grain and gate weave.

## The rules that bind every turn

These hold whatever the phase. The full table with its enforcement points is
`skills/video-production/references/STANDING-RULES.md`.

- 🔴 **A cost line and the operator's explicit GO come before any billed call** — video, image, music,
  TTS, STT, clone, hosted upscale. The amount does not matter.
- 🔴 **Nothing is upscaled before the operator has approved the take.**
- 🔴 **The refs gate runs in code before every generation call.**
- 🔴 **The client's text is the single source of truth.** Additions are proposed as cost lines, never
  assumed.
- **Continuity is the first acceptance test**, before the gag. The start image is the previous shot's
  last state.
- **Never resubmit a billed job. `COMPLETED` is not success.** Receipts keep the raw reply.
- **Masters are 1080p only**; at most 30 MiB in chat, otherwise the path.
- **Decisions go to the operator as numbered plain questions** with the cost and the full path inline.
- **Invoke a skill at the phase it governs — never work from a recalled version of it.** Installed skills
  can move under a long task; re-read one whose revision moved.
- **A number in a skill is a default until the project confirms it.** A measurement holds for the model,
  venue, version and date it was taken on.
- **Install the dependency or ask — never a lazy workaround.**
- **Destructive ops: the operator names the exact target, one command per target, alone.** Project trees
  have no VCS, so write a `.bak` first.
- **One background waiter at a time.** Poll, never follow. A missing sentinel is a failure.
- **Capture a command's verdict on the same line as its invocation, never through a pipe** — `cmd | tail`
  returns tail's exit code.
- **A plan step earns a cheap verification immediately before it runs.** A written plan is a set of
  hypotheses, not instructions to execute on trust.

## How a production runs

Start with the `video-production` entry skill and name the project root and the genre. It reads the
project's pause block, prints a status line and hands off to the phase that owns the next step. The
phases run downhill, each with its own gate:

pre-production → references and continuity → the prompt → the gated generation call → the read → the cut
→ the sound → designed elements → the finish and QC → the client round.

Handoffs are bounded: three automatic hops after the originating skill, a visited set, and stop
conditions that outrank the budget. `CHAIN.md` is the contract.

## Where to look next

| you want | read |
|---|---|
| the long-form setup, tier by tier | `README.md` |
| the method in order, and why each rule exists | `METHOD.md` |
| the handoff budget and stop conditions | `CHAIN.md` |
| the two Windows tools and their variables | `tools/README.md` |
| the grading method and the look recipes | `look-library/GUIDE.md` |
| every key and variable, with what reads it | `.env.example` |
