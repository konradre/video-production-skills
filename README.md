# video-production-skills

Fifteen Claude Code skills, two host-side tools and a look library for producing video: short-form
ad campaigns, short films and music videos made from generated footage, and narrated motion-graphics
explainers drawn in code. The measurements behind the finishing rules are in the references.

## What is in the box

| directory | what |
|---|---|
| `skills/video-production` | the entry skill. Fixes the genre, rehydrates a paused project, routes the next step to the phase skill that owns it |
| `skills/ad-spot-preprod` · `skills/film-preprod` | pre-production for an ad campaign, or for a film and a music video |
| `skills/video-refs-continuity` | the derived reference set, the start image, the continuity ledger and a refs gate that runs in code before any generation call |
| `skills/video-prompt-dialects` | the prompt compiled per venue dialect (Seedance 2.5 / 2.0, MiniMax H3, a web front end, two image models), with a linter |
| `skills/video-gen-cost-gate` | the venue table, the cost line and the operator's GO, the gated submit path, receipts at acceptance, detached polling. Two hosted routes buy the same Seedance 2.5 model — one by subscription, one pay-as-you-go — and the table ranks them by marginal cost |
| `skills/video-take-review` | the per-seed read: continuity first, then the acceptance matrix, voids and usable windows, instruments with self-tests |
| `skills/video-edit-edl` | the edit as a derived EDL: the beat list from the script, a builder that computes every time, a script-fidelity gate |
| `skills/spot-audio-assembly` | voice-over, dubs, off-screen voices, sfx and music cues, room tone, captions, the loudness pass and its verification |
| `skills/designed-elements` | end cards, turntables, piece walls and drifts as deterministic HyperFrames compositions |
| `skills/explainer-video` | a narrated motion-graphics explainer drawn in code: sourced facts, a script whose spoken anchors time every scene, the voice and its word times, HyperFrames scenes and captions, a frame instrument and an audit of every on-screen string |
| `skills/video-finish` · `skills/video-finish-qc` | the per-clip finishing order (upscale, grade, grain, watermark, downscale, encode) and the spot pipeline that runs it from the EDL, plus the QC of the delivered file |
| `skills/client-rounds` | client notes located before anything moves, classified, executed by a ladder, delivered with a numbered ask |
| `skills/mastering-audio` | a standalone loudness master for a finished mix |
| `tools/` | the local Topaz upscale wrapper and the unattended Resolve + Dehancer hero pass |
| `look-library/` | five looks, each as a baked `.cube` and an authored Dehancer `.drx`, their YAML recipes and baker, the dial-ins, and a guide to the whole grading method |
| `CHAIN.md` | the handoff contract every skill runs under: a budget of three automatic hops, a visited set, stop conditions |

Each skill is a `SKILL.md` with the steps and their completion criteria, a `references/` directory
with the contracts and measurements, and a `scripts/` directory of small Python and shell tools.
Every Python and shell script prints its usage on `--help` and changes nothing, and the scripts that
work inside a project take its folder as `--root <project>`.

## What you need

The base install is Claude Code, Python 3.10 or newer with numpy, Pillow, scipy and PyYAML
(`pip install numpy pillow scipy pyyaml`), and [ffmpeg](https://ffmpeg.org/download.html).
On Windows, run the kit inside WSL2. The skills give the agent bash commands, and WSL2 is where we built the kit.

The table follows a production in the order it runs. Each row names a step and its skill, what that step adds
on top of the base install, and the key or variable it reads from `.env`. Set up the rows you will use. The
entry skill (`video-production`), pre-production (`ad-spot-preprod`, `film-preprod`), the prompt
(`video-prompt-dialects`), the cut (`video-edit-edl`) and the client round (`client-rounds`) need nothing
more, and the status line reads the Higgsfield and ElevenLabs balances once those are set up. Three rows want a
GPU of your own, and how much VRAM it has decides which. [If you have no GPU, or a small one](#if-you-have-no-gpu-or-a-small-one) is the whole answer in one place.

| step · skill | what it does | install or sign up for | key or variable |
|---|---|---|---|
| references · `video-refs-continuity` | makes the stills: the reference set and the start image | a [kie.ai](https://kie.ai/api-key) key, the default still route; Higgsfield credits are the second | `KIE_API_KEY` |
| references · `video-refs-continuity` | the scene proxy, a room rebuilt as labelled boxes on your own GPU | ComfyUI with one node pack and two checkpoints, listed under [ComfyUI](#comfyui-only-for-work-on-your-own-gpu) | `COMFY_HOST`, plus `COMFY_DIR`, `COMFY_VENV`, `COMFY_ARGS`, `COMFY_LOG` and `COMFY_SSH` for `comfy_up.sh` |
| generation · `video-gen-cost-gate` | buys Seedance 2.5 and MiniMax H3 seeds, each behind a cost line and your go | a [Higgsfield](https://higgsfield.ai) account with credits and its CLI: `npm install -g @higgsfield/cli`, then `higgsfield auth login` and `higgsfield workspace set <workspace-id>`. A [fal.ai](https://fal.ai/dashboard/keys) key opens a second route, which refuses photoreal people in references | `FAL_KEY`; Higgsfield logs in through its CLI |
| generation · `video-gen-cost-gate` | buys the same Seedance 2.5 seeds pay-as-you-go — by the second rather than by the month — and hosts the reference images they cite, free | a [monid](https://monid.ai) account and its CLI: `npm install -g @monid-ai/cli`, then `monid keys add` to store the key and `monid balance` to confirm it. Credit is pay-as-you-go, so there is no plan to exhaust and no credits to expire. People-free shots only: real human faces are refused upstream by the model host | none — monid keeps the key in its own CLI store, not in `.env` |
| generation · `video-gen-cost-gate` | MiniMax H3 seeds on your own GPU, free per take | an NVIDIA card (we ran a 24 GB one), ComfyUI and the weights in [MiniMax H3 on your own GPU](#minimax-h3-on-your-own-gpu) | the `COMFY_*` variables |
| the read · `video-take-review` | a take's cut list, contact sheet and frame instruments | nothing more; [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (`pip install faster-whisper`) adds a transcript to the take's record | none |
| the sound · `spot-audio-assembly` | voice-over, dubs, voice clones and generated sfx | an [ElevenLabs](https://elevenlabs.io/app/settings/api-keys) key | `ELEVENLABS_API_KEY` |
| the sound · `spot-audio-assembly` | music cues | an [AceDataCloud](https://platform.acedata.cloud) token. It resells Suno and is the default music route, about $0.08 a call for two takes. The kit documents the call and ships no client of its own; the vendor publishes one. A cue the operator generates by hand, or a library bed, is the fallback | `ACEDATACLOUD_API_TOKEN` |
| the sound · `spot-audio-assembly` | word times for captions and sound placement | faster-whisper, free on the CPU, or ElevenLabs Scribe, billed per minute | `ELEVENLABS_API_KEY` for Scribe |
| the sound · `spot-audio-assembly` | burned-in captions | the caption fonts, which the kit does not ship; see [Caption fonts](#caption-fonts) | none |
| designed elements · `designed-elements`, `explainer-video` | end cards, turntables and piece walls, and narrated explainers drawn in code | [Node.js](https://nodejs.org/en/download) 22 or newer and `unzip` on the machine that renders, and your display font as a TTF. `npx` fetches HyperFrames, which draws in headless Chromium. Headless Chromium hangs under WSL2, so from WSL2 `render_hyper.sh --host` renders on another Linux machine over ssh and rsync. An explainer's voice and word times come from the sound rows | none |
| the finish · `video-finish`, `video-finish-qc` | a look's colour | nothing more; ffmpeg's `lut3d` filter applies the cubes | `LOOK_LIBRARY_CUBES`, optional |
| the finish · `video-finish-qc` | the hosted upscale, a billed 4× pass for wides where faces sit small and shots with text to read, and for every take if you skip Topaz | the fal key (Topaz Starlight) or Higgsfield credits (Rhea), behind a cost line and your go | `FAL_KEY` |
| the finish · `video-finish-qc` | the local upscale, a free 4× Rhea pass over approved takes framed chest-up or closer, before the grade | Topaz Video and a GPU with room for it, only if you upscale on your own card; see [Topaz](#topaz-only-for-upscaling-on-your-own-gpu) | `TOPAZ_FFMPEG`, `TVAI_MODEL_DIR` and `TVAI_MODEL_DATA_DIR`, all optional |
| the finish · `video-finish-qc` | a look's halation, bloom and grain, graded clip by clip in the hero pass | Windows with an NVIDIA GPU, [DaVinci Resolve Studio](https://www.blackmagicdesign.com/products/davinciresolve) (we verified 18.5), a [Dehancer Pro](https://www.dehancer.com/shop/davinci_resolve/pro) 7.x licence, and the in-app bridge from [davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp) | `RESOLVE_PY`, `DAVINCI_RESOLVE_MCP_DIR` and the rest in `tools/README.md` |
| any step, optional · your agent | lets the agent drive Resolve itself, to inspect a project, apply a grade or render outside the hero pass | the MCP server from [davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp), v4.1.3 or newer. `npx davinci-resolve-mcp setup` installs it and can register it with Claude Code and eleven other agents and editors. In Resolve Studio, set Preferences ▸ General ▸ External scripting using to Local | none |
| looks · `look-library/` | rebakes a look or ships a new one | the spectral base cubes from `look-library/fetch_spectral_bases.sh`, and an ffmpeg built with libvmaf for the VMAF gate | none |
| mastering · `mastering-audio` | a standalone loudness master for a finished mix | Node.js 18 or newer, then `npm install` once in `skills/mastering-audio` | none |

`tools/README.md` and `look-library/GUIDE.md` §5 walk through both Windows setups.

### ComfyUI, only for work on your own GPU

Install ComfyUI only if you want to run models on your own GPU, for MiniMax H3 seeds or the scene proxy.
Every hosted route works without it. [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) lists the ways
to install it: the desktop app for Windows and macOS, a portable build for Windows, `comfy-cli`, or a manual
install. `skills/video-refs-continuity/scripts/comfy_up.sh` starts a manual install headless from the
`COMFY_*` variables in `.env`, locally or over ssh. With any other install, start the server yourself and
point `COMFY_HOST` at it; `comfy_ready.py`, in the same folder, names anything missing.

The scene proxy needs ComfyUI 0.31 or newer,
[ComfyUI-Majoor-OmniCam](https://github.com/MajoorWaldi/ComfyUI-Majoor-OmniCam) in `custom_nodes/`, and two
checkpoints under `models/`: `geometry_estimation/moge_2_vitl_normal_fp16.safetensors` from `Comfy-Org/MoGe`
and `checkpoints/sam3.1_multiplex_fp16.safetensors` from `Comfy-Org/sam3.1`. The H3 recipe needs more, and
the next section lists it.

### MiniMax H3 on your own GPU

Local seeds cost nothing, but each run holds the whole card. On a 24 GB RTX 3090 in a box with about
64 GB of RAM, the recipe renders a 5-second take at 768×1344 in about two minutes, and VRAM peaks at
23.9 GB. We have not tried a smaller card.

The speed depends on a PyTorch build for CUDA 13.0 or newer. Put it in a virtualenv of its own, so the
tools that depend on your current PyTorch keep theirs:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
```

Those wheels run on RTX 20-series (Turing) cards and newer, with a driver that supports CUDA 13 (on
Linux, 580.65.06 or later). `nvidia-smi` prints the highest CUDA version your driver takes. On an older
build ComfyUI warns at startup that it needs cu130 for its optimized CUDA operations, and our take ran
2.1× slower.

ComfyUI provides the H3 nodes, the comfy-kitchen attention backend and the block-sparse attention node
the recipe uses, so you need no SageAttention build. We ran 0.35.0. Three custom node packs go into
`custom_nodes/`, each with its requirements installed into the same virtualenv:
[ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes),
[ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) and, for the ×2
master pass, [Comfyui_Minimax_h3_latent_Upscaler](https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler).

Every weight is public on Hugging Face, about 45 GB for the recipe; `hf` comes with
`pip install -U huggingface_hub`.

```bash
cd ComfyUI
hf download Comfy-Org/MiniMax-H3 text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors \
  vae/minimax_h3_video_vae_fp16.safetensors vae/minimax_h3_audio_vae_fp32.safetensors \
  loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors --local-dir models
hf download WarmBloodAban/Minimax-h3_Singularity \
  Minimax-h3_Singularity_ref2va_Pruned_v1.3_int8.safetensors --local-dir models/diffusion_models
# the ×2 master pass
hf download LBH-123-AI/Minimax_h3_latent_Upscaler \
  minimax_h3_latent_upscaler_3d_fp16.safetensors --local-dir models/latent_upscale_models
```

The sharpener pass adds `loras/minimax_h3_lms_v1.0_r64.safetensors` from `Alissonerdx/Minimax-H3-ComfyUI`
and the stock trunk that LoRA was trained on, `diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors`
from `Comfy-Org/MiniMax-H3`. Every model carries its own licence. The kit ships no graph. Build yours from
`skills/video-gen-cost-gate/references/LOCAL-H3.md`, which has the settings and the measurements behind
them.

### Caption fonts

The kit ships no fonts. `build_captions.py` loads a caption style's font from `hyper/fonts` in the project,
or from the folder `--fonts-dir` names, and stops if the file is missing. It knows three styles: `A` is
Bangers, saved as `Bangers-Regular.ttf`; `B` is Inter, saved as `Inter.ttf`; `C` is Nunito, saved as
`Nunito.ttf`. Style `B` sets the Black weight by name, so Inter has to be the variable font, and so does any
font you give a `weight`. All three are free on [Google Fonts](https://fonts.google.com) under the SIL Open
Font License, and Google Fonts is the place to look for more; each family's page shows its licence. To use
another face, put its TTF in the same folder and write the file name as `font` in the EDL's `caption_style`.

### Topaz, only for upscaling on your own GPU

Install Topaz only if you want the local upscale. It does one job in the kit: a Rhea ×4 pass over approved takes
framed chest-up or closer, plus at most an Iris ×1 pass over a punch-in, on the GPU of a Windows machine that WSL2
drives. Without a card to spare, skip it and use the hosted upscale, which covers the same takes with Rhea on
Higgsfield credits or Starlight on fal, each behind a cost line. Our 4× Rhea run held an 11 GB card at 92% VRAM.

[Topaz Video](https://www.topazlabs.com/topaz-video) was called Topaz Video AI before the rename. The wrapper in
`tools/topaz-upscale/` finds either one's install and model folders, and `tools/README.md` lists the variables that
override it. We measured it on Topaz Video AI 6.0.2 only. It drives Topaz's command line, which Topaz says it is
phasing out, so check a new release before a job depends on it.

### What still works when a dependency is missing

Most of the kit degrades rather than stops, and it is worth knowing where, because the substitutes are not
always worse.

| without | you lose | what still works |
|---|---|---|
| ffmpeg | the encode, the loudness read, the format checks, silence detection | everything up to the master; a hosted upscale returns a finished file |
| Node 22+ | designed elements and explainers — they render through headless Chromium | every generated-footage lane, and the mastering tool on Node 18 |
| a GPU with enough VRAM | local generation needs ~24 GB (ours peaked at 23.9); the local finish — Topaz and Dehancer — measured 92% of an 11 GB card, so below ~11 GB it goes too | the hosted lanes, all of them, and every finishing step — plus `scene_proxy.py`, which needs no GPU and still reads any `scene.json` you have. [Which tier is yours](#if-you-have-no-gpu-or-a-small-one) |
| faster-whisper | word times on your own machine | the billed transcription service, or hand-placed captions |
| Resolve Studio + Dehancer | halation, bloom, grain and gate weave as a graded pass | the colour itself, through a LUT in ffmpeg |
| Windows | Topaz and Resolve, which are Windows-only here | the Linux lanes; a hosted upscale replaces Topaz |
| an ElevenLabs key | generated voice-over and generated sfx | the take's own sound, a library sound, and every caption, loudness and mix step |
| a music vendor | generated cues | a cue the operator brings or a library bed — the cut, duck and licence rules are the same either way |
| the monid CLI | the pay-as-you-go generation route and its free reference hosting | the subscription route for the same model, and any other venue in the table |

The rule the kit holds to: **nothing you are asked to watch needs a build step.** A master plays in any
player; a designed element's source is one HTML file a browser opens.

### If you have no GPU, or a small one

"Do I have a GPU" is the wrong question — every local step has its own VRAM floor, and ours are measured,
not estimated. Find your row first.

| your card | what we measured on it | what it means |
|---|---|---|
| **24 GB** (RTX 3090) | local MiniMax H3 peaked at **23.9 GB of 24** | everything local runs, but generation holds the whole card — nothing else can share it |
| **~11 GB** (GTX 1080 Ti) | Resolve Studio 18.5 + Dehancer Pro 7.4 graded at **92% VRAM**; the Topaz Rhea ×4 pass also held **92%** | the local *finish* fits and local *generation* does not. Both jobs sit near the edge, so 11 GB is the floor, not the comfortable case |
| **under ~11 GB** (8 GB, 6 GB) | never tested — *"we have not tried a smaller card"* | those two jobs used about 10.1 GB, so they do not fit. Treat this as the no-local-GPU row below |
| **an AMD card or APU** (e.g. Radeon 780M) | — | local generation is out by construction — the wheels need CUDA 13 on an RTX 20-series card or newer. Dehancer is **not** out: it ships a separate **OpenCL** build for AMD, so the graded pass turns on VRAM, not on vendor. On an APU that VRAM is carved out of system RAM, so 4 GB of it also costs you 4 GB of the RAM everything else wants |
| **Intel integrated** (Iris, HD) | — | Dehancer does not support these at all, and local generation needs CUDA. Every hosted lane is unaffected |

Resolve's own floor is lower than ours — 2 GB VRAM and 16 GB system RAM — so it may well install on a modest card and
still be unable to carry the graded pass we measured, which held 92% of 11 GB. Treat "it launches" and "it can finish
a job" as separate questions.

**At ~11 GB**, ignore only [MiniMax H3 on your own GPU](#minimax-h3-on-your-own-gpu) and buy your seeds
hosted. Keep `tools/topaz-upscale/` and the Resolve chain — they are the two things that *do* fit. Expect
them to be slow rather than impossible: a Dehancer frame took 5.5 s at 3416×1920, and a full pass ran about
135 minutes.

**Everything below applies to the last two rows** — no card, one under about 11 GB, or a non-NVIDIA one.

Ignore three sections: [ComfyUI](#comfyui-only-for-work-on-your-own-gpu),
[MiniMax H3 on your own GPU](#minimax-h3-on-your-own-gpu), and
[Topaz](#topaz-only-for-upscaling-on-your-own-gpu).

Five scripts cannot run. Nothing else calls them, so nothing else breaks — but read the note under the list:

```
skills/video-refs-continuity/scripts/comfy_up.sh
skills/video-refs-continuity/scripts/comfy_ready.py
skills/video-refs-continuity/scripts/scene_blockout.py
skills/video-finish-qc/scripts/upscale_local.sh
tools/topaz-upscale/topaz_upscale.py
```

`tools/topaz-upscale/` is safe to delete **in these rows only** — at ~11 GB it is one of the few local things that still works. Leave every `COMFY_*`, `TOPAZ_*` and `TVAI_*` variable unset in `.env`.

One caveat on `scene_blockout.py`: it ran in ~15–25 s per frame on a 24 GB card, but that is the card it happened
to run on, **not a measured requirement** — its two checkpoints are small and nobody has tried it on a lesser card.
If you have some GPU, it is worth one attempt before you assume it is out.

You keep all fifteen skills and every generation route, because all four are hosted: Seedance 2.5 on
Higgsfield by subscription or on monid pay-as-you-go, fal for people-free shots, kie for stills. You keep the
whole finish chain, with the hosted upscale doing the job Topaz would have done. And you keep `look-library/`,
because applying a look is an ffmpeg `lut3d` filter — Resolve is only needed to author or rebake one.

One METHOD changes, not just a tool. Without `scene_blockout.py` you cannot compute a room from a keeper
frame, so the geometry for a new angle is read off that frame at 2–4× zoom and copied into the prompt
verbatim, and the GO ask says "no scene proxy for this shot"
(`skills/video-refs-continuity/SKILL.md` § Failure behavior). The reader, `scene_proxy.py`, needs no GPU and
still works on any `scene.json` you already have.

`tools/resolve-pass/` is a different axis, not this one. It needs Windows, DaVinci Resolve Studio and a
Dehancer licence whether or not you have a card. Without it a look still applies as a LUT; what you lose is
halation, bloom, grain and gate weave as a graded pass.

## Install

```bash
git clone https://github.com/konradre/video-production-skills
cd video-production-skills && ./install.sh
```

The installer symlinks `skills/*` into `~/.claude/skills/`. The skills find the tools and the look
library through those links, so the default layout needs no configuration. Every command inside the
skills calls `~/.claude/skills/<skill>/…`, so keep those links whichever agent runs the kit; if your agent
loads skills from another folder, `./install.sh <that folder>` links them there as well.

Vendor keys never live in the repo or in a skill. Copy `.env.example` to `.env`, which git ignores, and
fill in the keys for the parts you use. The file names every key and variable the kit reads and what each
one is for, including two fallback routes that no script calls. The scripts read keys from the
environment rather than from the file, so the agent loads it in the same command that needs it:

```bash
set -a; . ~/.claude/skills/video-production/../../.env; set +a
```

That path resolves through the installer's link to the root of your clone.

## How a production runs

Start with `/video-production` and name the project root and the genre. The entry skill reads the
project's pause block, prints a status line (deliverable, free disk, balances where a vendor lets you
read them, background jobs, open items) and hands off to the phase the next step belongs to. The
phases run downhill and each one carries its own gate:

pre-production → references and continuity → the prompt → the gated generation call → the read →
the cut → the sound → designed elements → the finish and QC → the client round.

`METHOD.md` walks the whole method in order and says why each rule exists. A few of them bind every
turn, whatever the phase. A cost line and the operator's explicit go come before any billed call, and
the amount does not matter. Nothing is upscaled before the operator has approved the take. The
client's text is the single source of truth and additions are proposed as cost lines. Continuity is
the first acceptance test, before the gag. Masters are 1080p only. Decisions go to the operator as
numbered questions with the cost and the file path inline.

## What is not here

Where a skill needs an example of a file shape, the example is a placeholder. The looks ship
complete, cubes and `.drx` grades both; the `.drx` files were authored on Dehancer Pro OFX 7.4 and
need a licensed Dehancer Pro 7.x with its film profiles downloaded, because a major version installs
as a separate plugin. The spectral base cubes the film looks were baked from are fetched, not
vendored; you only need them to rebake after editing a recipe. Third-party notices are in `NOTICE.md`.

## License

MIT. The film looks' cubes derive from spectral base cubes in
[ComfyUI-Darkroom](https://github.com/jeremieLouvaert/ComfyUI-Darkroom) (MIT, notices in `NOTICE.md`);
the designed elements render with [HyperFrames](https://github.com/heygen-com/hyperframes)
(Apache-2.0); the Resolve bridge comes from
[davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp) (MIT). The `.drx` grades hold
our own settings for the Dehancer plugin and none of its profile data. Cubes exported by Dehancer's own
LUT Generator are licensee-only and must never be published.
