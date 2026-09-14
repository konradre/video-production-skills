---
name: designed-elements
description: >
  Builds the DESIGNED, code-rendered elements of a generated-video piece — end cards, turntables, layers that
  straddle a cut, bursts, kinetic titles — as HyperFrames compositions from the client's own art, fixed at the
  source by measurement and verified on the delivered frame. Use when a piece needs a card, a turntable or a
  layer, when a product must be designed instead of generated, when an asset has a defect, or when a designed
  event must be re-timed or re-rendered. Triggers — "end card", "the turntable", "a layer over the cut", "spruce
  up the card", "the edges need aligning", "new length", "render the hyper", "sync it to the sound". Not for
  generated motion, prompts or references — use video-refs-continuity. Not for placing the element on the timeline
  — use video-edit-edl. Not for the sting, the chimes or the bed — use spot-audio-assembly. Not for the grade or
  the encode — use video-finish. Not for a whole narrated explainer — use explainer-video.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3*), Bash(bash*), Bash(node*), Bash(npx*), Bash(ssh*), Bash(rsync*), Bash(ffmpeg*), Bash(ffprobe*), Bash(ls*)
---

# Designed Elements

Two families share nothing: generated motion (stochastic, GPU, expensive) and designed motion
(deterministic, CPU, code — infinitely revisable). This skill is the second, fenced from the first —
motion graphics never pollute the generation context. Its whole game is
**craft and design-system fidelity**, and its whole discipline is **fix at the source, check on the
delivered frame, one variable per round**.

**What varies.** The kit — card, turntable, wall, drift, burst — is an ad campaign's; a film or an explainer builds only
what its brief names. The 2160×3840 canvas, the legibility floor (~40 px at a 2160-wide raster) and the render host scale
with the delivery raster and the machine. Fixing at the source and reading the delivered frame do not move —
`video-production/references/WHAT-VARIES.md`.

## 1. Decide what is designed

Anything that must be exact is designed, never generated: packaging and product (a gen printed
"WARNIGY"), the wordmark and the card, the product's pieces as sprites, a display with names, a wall or
a drift that must straddle a cut at a known frame. Anything that must be alive is generated. The two
meet only where the operator has accepted a composite on a plate — **never a 2D overlay on generated
motion**.

**Done when:** every element in the shot list is labelled designed or generated, and each designed one
names its kit entry (card · turntable · wall · drift · burst · title) and its length.

## 2. Build from the kit, customised per SKU

```bash
python3 ~/.claude/skills/designed-elements/scripts/hyper_new.py --out hyper/<name>-<len> --kind card|turntable|layer --dur 2.5 --canvas 2160x3840 --seed 606
```

The campaign kit (card, wall, drift, turntable, signature slot) is dialled in once; a SKU changes the label
texture, the exact-silhouette sheet the sprites are cut from (`video-refs-continuity` plate pieces),
the palette and the name. Taste comes from the client's own art and the shot-recipe numbers, never a
web design system. Assets are cut from the highest-resolution source
with a silhouette matte; a hard border or a straight edge is fixed AT THE SOURCE. The contract every
composition obeys (`data-*`, `window.__timelines`, a seeded PRNG, local assets, a new length = a new
project): [`references/HYPERFRAMES-CONTRACT.md`](references/HYPERFRAMES-CONTRACT.md); the kit and where
each element lands in the EDL: [`references/KIT.md`](references/KIT.md).

**Done when:** the project renders its full length from local assets with a seed, and its sync constant
(the burst's `T0`, the wall's opaque frame, the ding times) is written in the composition.

## 3. Render, then read the render

```bash
bash ~/.claude/skills/designed-elements/scripts/render_hyper.sh --dir hyper --name <name> --format mp4 --host <render host> --push --pull
bash ~/.claude/skills/designed-elements/scripts/render_hyper.sh --dir hyper --name <name> --format png-sequence --host <render host> --push --pull
python3 ~/.claude/skills/designed-elements/scripts/layer_check.py --frames hyper/<name>/frames --expect-dur 1.0
```

Render on the GPU VM (WSL2's headless Chromium hangs), sentinel `RENDER-END`. An event is probed
(raster, duration = `data-duration`, fps); a layer is checked for contiguous RGBA frames and the frame at
which it goes opaque — the number the edit places the wall by. The card's burst frame is found by PSNR
against the render and verified by region brightness.

**Done when:** the render probes at its declared length and raster, the layer check passes, and the
sync numbers are handed to `video-edit-edl` and `spot-audio-assembly`.

## 4. Verify on the DELIVERED frame, at zoom

The render is not the artefact — the delivered frame is. After the finish, read the element in the
deliverable at 1:1 and 4× (`video-take-review` `window_frames.py`): the card's edges, the wordmark's
notches, the wall's coverage across the join, the pieces' legibility (no sprite below ~40 px at a
2160-wide raster; clusters only in the far field). A fix checked on the card render while the
delivered frame keeps the defect is a rejected round.

A composition that sets text is read at the source too: `literal_audit.py hyper/<name> --approved <approved copy>`
lists every string it can put on screen that the approved copy does not carry — a counter's intermediate or a label
on a transition shows between sampled frames and nowhere else. The readable-time, number, glyph and join rules are
arithmetic on the composition's own timeline: [`references/CRAFT.md`](references/CRAFT.md).

A composition with three or more scenes has its STRUCTURE read at the source as well:
`slide_structure_audit.py hyper/<name>`. Frames cannot tell you that a film is a slide deck — it can pass hero size,
empty runs and still share and still be one, because the defect is that scenes switch by opacity with nothing moving
the world, that a kicker/title/body stack sits in one container, that scale is the only thing animated, or that every
cut animates the same properties. Four judgement rows, read on the composition; it exits 2 rather than 0 when it
cannot segment the scenes, because a composition it could not read is not one it has cleared.

**Done when:** the defect list is written from the delivered frame, with frame times and crops saved to
the project and named by path, and — where the composition sets text — `literal_audit.py` reports no unapproved
literal, and — at three scenes or more — `slide_structure_audit.py` either passes or each flag has been read on the
composition and answered.

## 5. Fix at the source, one variable per round

```bash
python3 ~/.claude/skills/designed-elements/scripts/asset_edge_repaint.py --src assets/wordmark-v4.png --dst assets/wordmark-v5.png --above ff2a2a --below 2a5cff --job left:1178,1606:54,82,44,78:18-52,84-112
python3 ~/.claude/skills/designed-elements/scripts/sprite_burst.py --root <project> --in edit/hero/<hero>.mov --out edit/hero/<hero>-burst.mov --bang 4.3 --muzzle 1180,2300 --dir -0.7,-0.5 --sheet references/sheets/<sku>-sheet-exact.png
```

- A residual defect (a notch, a speck, a crop line) is repainted IN THE ASSET by measurement (a circle fit
  through the clean edge), never hidden by layout; missing art is completed at the source or bled off the
  frame, never extrapolated; the fixed asset then re-renders EVERY final.
- Alignment is measured; layering is the operator's call on
  sight; one variable changes per round; after failed rounds, revert to the accepted version and ask
  what specifically is wrong, candidates side by side.
- A new length or a new recolour is a NEW project (`drift-a-4s` → `drift-a-5p5s`, `wall-a` →
  `wall-b`); the accepted version is never edited in place, and a new version at the same length is a new
  render file that every EDL adopts by path (`references/HYPERFRAMES-CONTRACT.md`).
- The rules and the rounds that produced them: [`references/CRAFT.md`](references/CRAFT.md).

**Done when:** the fix is in the source asset, the before/after crops are saved, the element re-rendered,
and the delivered frame re-read.

## Failure behavior

- A render log without `RENDER-END`, a missing frame in a sequence, a raster off the declaration → the
  render is re-run, never patched around.
- A composition that needs the network for an asset, or an unseeded random → fixed before any round.
- `slide_structure_audit.py` exits 2 (it could not segment the scenes) → the composition does not mark them the way
  the contract does (`data-start` + `data-duration`); fix the markup, never read the 2 as a pass.
- A `slide_structure_audit.py` flag the composition confirms → the fix is structural (a world move at the cut, a text
  level removed, a second kind of transition), never a frame-level tweak.
- A fix that would need layout gymnastics → stop; find the asset defect and fix it there.
- The operator rejects a round → revert to the accepted version first, then ask what specifically is
  wrong.

## Scripts

| script | does |
|---|---|
| `hyper_new.py --out --kind card\|turntable\|layer [--dur --canvas --seed]` | scaffolds a composition that obeys the contract |
| `render_hyper.sh --dir --name --format mp4\|png-sequence [--host --push --pull]` | renders locally (Node ≥ 22) or on the render host; `RENDER-END` only once the output exists, `RENDER-FAILED` and exit 1 otherwise |
| `layer_check.py --frames [--expect-dur]` | validates a PNG-sequence layer; prints its opaque window |
| `asset_edge_repaint.py --src --dst --above --below --job …` | repaints a notch/speck at a fitted two-colour edge; 8× review crops |
| `sprite_burst.py --root --in --out --bang --muzzle --dir --sheet` | the exact-silhouette burst composited on a hero, legibility floor |
| `literal_audit.py <composition> --approved <copy> [--approved <script>] [--strict]` | every string the composition can put on screen, read from its SOURCE, against the approved copy (repeat `--approved` for each approved file); `--selftest` |
| `slide_structure_audit.py <composition> [--lead 0.6] [--json]` | the four structures that read as a slide deck, read from the SOURCE: scenes switched by opacity with no world move · a three-size text stack in one container · scale as the only geometric animation · one property set at every cut. Exit 1 on a flag, **2 when it cannot segment the scenes**; `--selftest` |

## Cross-references

- [`references/HYPERFRAMES-CONTRACT.md`](references/HYPERFRAMES-CONTRACT.md) · [`references/KIT.md`](references/KIT.md) ·
  [`references/CRAFT.md`](references/CRAFT.md).
- `video-refs-continuity` — the silhouette sheet and plate pieces the sprites are cut from; `video-edit-edl` —
  where events and layers sit; `spot-audio-assembly` — the sting, the chimes, the bed; `video-finish-qc` — the
  finish that composites layers and the QC that reads the card.
- Handoffs follow `~/.claude/skills/video-production/references/CHAIN.md`.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
