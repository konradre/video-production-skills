# Evidence — the measurements behind every rule in SKILL.md

Consulted when choosing a model, setting a Dehancer parameter, or arguing with an ordering rule.
Every table here is measured, not vendor copy. Provenance at the bottom.

## Upscaler tiers and hosted rates

Rates are **4K output, per second of video**, gathered in late August 2026. 1080p output is roughly half.
Billing is per second of **output** on fal and Topaz's own API; some vendors bill **input** seconds
instead, which diverges the moment frame interpolation enters.

### Reconstructive — the tier the technique requires

| Provider | Model | 4K $/s | Note |
|---|---|---|---|
| fal | **Starlight Fast 2** | **0.130** | cheapest model that does the thing |
| fal | Starlight Precise 2.6 / HQ / Mini / Sharp | 0.260 | "diffusion realism pass built for AI-generated video" |
| fal | Topaz Astra 2 | 0.500 | invents detail never in the source; picks its own output resolution |
| local | Topaz Rhea | **0** | 4×-only; unlimited local render under the subscription |

fal endpoint: `topaz/upscale/video/generative`. Params: `video_url` (required), `model`,
`upscale_factor` (1–4, default 2), `target_fps`, `softness` (1–5, Precise 2.6 only), `H264_output`.
Output defaults to HEVC.

### Faithful — cheaper, **and not a substitute**

| Provider | Model | 4K $/s |
|---|---|---|
| fal | ByteDance Video Upscaler | 0.0288 |
| fal | Topaz Gaia 2 | 0.030 |
| fal | Topaz Proteus | 0.050–0.060 |

## Starlight vs Rhea — the A/B on a real keeper

Both arms ended as the same deliverable, frame-matched. Local arm on an 11 GB Pascal card.

| arm | wall time (97 frames) | $ | master bitrate |
|---|---|---|---|
| Starlight Precise 2.6 ×3 → Lanczos down | ≥5 min queue | 1.10 | 4.96 Mbps |
| Rhea v1 ×4 → Lanczos 1080p, one pass | **705.8 s** | 0 | 4.09 Mbps |

Starlight ×3 carried **7–16% more fine texture and up to 28% more edge energy**. Rhea was softer and
cleaner — smoother reflections, no re-injected specks — and 17% smaller at the same CRF. Neither
showed artefacts.

**The ×2 arm wins nothing but price.** It matched ×3 on fine texture and lost 16–22% of edge energy;
a 1.09× *up*-scale from a 992-px mezzanine cannot sharpen the way a down-scale from 2K does.

### The per-shot verdict from a delivered campaign

The A/B above had texture and edges but no faces, so it read as taste. On the finals of a seven-spot
campaign (~40 Seedance takes at 480×854, all on local Rhea ×4 heroes) Starlight was run on the two
wides of one spot only. Laplacian edge energy on the delivered 1080p frames,
Rhea → Starlight Precise 2.6 ×4 (both from the take, 1920×3416, the same Resolve grade):

| shot | crop | Rhea → Starlight |
|---|---|---|
| wide, exec at the chart | exec face | 103 → 227 |
| | chart bars | 219 → 339 |
| | CEO face | 62 → 137 |
| wide, worker in the corridor | exec face | 73 → 232 |
| | worker | 14 → 51 |
| | CEO face | 35 → 176 |

The delivered file grew 31.1 → 36.8 MB at the same CRF 17 — there was now detail to encode. Cost
2 × 121 frames at ×4 = 260 fal units ≈ $2.60 (≈ $0.27 per output second at the 4K-class tier),
~5 min of queue each. A face of ~30 px in the take was never drawn by the generator: Rhea enlarges
the smear faithfully, Starlight draws a face.

**Rule (per shot):** Rhea ×4 local by default; Starlight ×4 from the source where a head is under
~50 px tall in the 480×854 take (≈ 1/15 of frame height — any full-body wide) or text must read;
chest-up and closer, Rhea holds. Starlight does not stack on Rhea. Checks: identity across cuts,
invented small text. Budget shape for a seven-spot campaign: all-Starlight ≈ $55, wides only ≈ $13,
Rhea everywhere $0 plus ~4 h of local GPU.

## After the grade — which arm survives compression

The decisive comparison, because it measures the deliverable rather than the mezzanine. Two
independent graders (ffmpeg `lut3d` and Resolve + Dehancer) ranked the arms **identically**, so the
ranking is a property of the upscales, not of the look.

### Dehancer grain survival (film look minus clean look, flat tiles)

| arm | master | @5 Mbps | @2.5 Mbps |
|---|---|---|---|
| ×3 (mezzanine **above** delivery, downscaled) | 0.934 | **0.744 (80%)** | 0.164 (18%) |
| ×2 (mezzanine below, upscaled 1.09×) | 1.082 | 0.493 (46%) | 0.146 (13%) |
| Rhea ×4 → 1080 **native**, grain 1:1 | 1.417 | 0.401 (28%) | 0.164 (12%) |

**At 2.5 Mbps every arm collapses to ≈0.15 — the no-grain level — while still having doubled the
master bitrate.** The mechanism, not the brand, is the lesson: the arm that carries grain best is the
one whose mezzanine sits *above* delivery resolution. This is why SKILL.md step 4 forbids post-scaling
in the upscale pass.

### Cleanliness

Rhea ×4 wins both tiers: **18% less flat-area noise than ×3, 24% less than ×2**, flicker **2.07 vs
2.63 / 2.77**, and its own texture survives a 2.5 Mbps proxy best (95% / 91% retained). ×3 is the
sharpest at +23% flat noise.

**Verdict:** film/grain deliverables → an above-delivery mezzanine. Clean/ads deliverables → Rhea, at
$0. Skip grain looks entirely for 2.5 Mbps-class placements.

## Grain and delivery encode — local measurements

Metric is high-pass energy (mean |Y − gaussian-blur σ1.5|); higher = more fine texture. Recompressed
at fixed bitrates to simulate a platform rendition.

| clip | as encoded | after 2.5 Mbps | after 5 Mbps |
|---|---|---|---|
| no grain | 2.18 | 2.04 | 2.13 |
| fine per-pixel grain | 3.17 | **2.09** | **2.16** |
| **coarse 2-px grain** | 3.46 | **2.46** | **2.64** |

Fine grain returns to within 1–3% of the no-grain baseline — every bit spent on it is wasted after
upload. Coarse keeps a third to 40%.

**Grain is a bitrate tax:** +50% (fine, low strength) to +120% (fine, higher strength) at the same
CRF. A VBV cap is mandatory anywhere a platform enforces a ceiling.

Other measured facts: `-tune grain` preserves grain better but costs bitrate — pair it with a cap.
Blue-noise dither is on by default in `libplacebo`, which also does deband + `deband_grain` in one
pass and runs on CPU Vulkan inside WSL2.

## Dehancer and LUT parameters

**Input = Rec.709 for AI-generated footage.** It is display-referred already; there is no log to undo.

**Two tiers.** `.cube` carries per-pixel colour only — WB, tone curve, contrast, split-tone,
saturation, black point, film-stock transform. `.drx` carries the spatial physics a LUT cannot encode
— halation, bloom, grain, gate weave, film breath. Halation runs *before* the negative transform;
grain is independent of stock and sized by frame.

| Parameter | ads / clean | film / cinematic |
|---|---|---|
| Film profile | Vision3 250D, or none | **Vision3 250D** day · **500T** night |
| Print stock | Kodak 2383 (light) | **Kodak 2383** |
| Halation | off, or ≤0.1 | **0.35–0.5** day · **0.75–1.1** night/neon |
| Bloom | off | light |
| Grain | off / minimal | low, capped — see the survival table |
| Tone curve | ~0.28, gentle S | ~0.5 |
| Split-tone | ~0.25 | 0.62–0.85 |
| Saturation | 1.02–1.08, skin protect 0.7 | 1.08–1.2, skin protect 0.55 |
| Black point | 0 lift | +0.008 |
| Vignette | none / 0.1 | ~0.34 |
| Total Impact | 30–50 | 70–90, grain pulled independently |
| LUT size | 33³ | 33³ |

Skin variant: **Portra 400**. Night/neon variant: **CineStill 800T** (teal cast, red halation).

⚠️ **Skin-tone gate.** Shadow-deepening looks — bleach, noir, heavy teal-orange — crush the
darkest-skinned subject in frame. QA every film look against the darkest subject, and keep skin
protection high on clean looks.

⚠️ **Never publish Dehancer-generated `.cube` files** — they are licensee-only.

## Topaz on Linux

**No official Linux release.** Linux existed only as a beta track (`TopazVideoAIBeta_*_amd64.deb`),
and community reports say it is no longer actively maintained.

The working route is **`jojje/vai-docker`** — a turn-key headless container running Topaz's own ffmpeg
with the `tvai_up` filter, `--gpus all`. Blockers, in order:

1. **Version entitlement.** The published Linux deb list tops out around 5.0.3.1.b. Models introduced
   in v6 may simply not exist on the Linux build — verify the model before planning around it.
2. **`auth.tpz` is hostname-bound and time-limited.** A new host needs its own mint; a mismatch
   silently produces a watermark rather than an error.
3. Documented non-deterministic CUDA OOM on Linux, reportedly fixed at 3.5.1.0.b+.

**The speed case:** a modern 24 GB card is roughly 2.5–3.5× an 11 GB Pascal on this workload. For a
one-off overnight job that saves a few hours once — usually less than the setup costs. Worth building
when upscaling becomes routine, not for a single deliverable.

## Wall-clock reference

Measured at 4× to a ~6.5 Mpx mezzanine on an 11 GB Pascal card:

| footage | seconds per frame |
|---|---|
| portrait (~1984×3456 out) | 7.28 |
| landscape (~3416×1920 out) | **5.48** |

Aspect ratio matters — **do not carry a benchmark across it.** Multiply by `duration × fps`:
a 90-second 24 fps cut is ~2,150 frames, so roughly 3.3 hours at the landscape rate. VRAM sat at
**92%** of 11 GB throughout.

## DaVinci Resolve — render codecs, and the call that hides them (measured on Studio 18.5; carries forward to 21)

🔴 **`Project.GetRenderCodecs()` takes the format's EXTENSION — the dict VALUE from
`GetRenderFormats()` — never the display KEY.** Addressed by key it returns an empty dict for most
formats, with no error. Measured on the same project, same connection, same call:

| format | `GetRenderCodecs(key)` | `GetRenderCodecs(ext)` | what the ext list actually holds |
|---|---|---|---|
| `QuickTime` → `mov` | **0** | **60** | Apple ProRes 422 / 422 HQ / 422 LT / 4444 / 4444 XQ, DNxHD/DNxHR |
| `MXF OP1A` → `mxf_op1a` | **0** | **75** | AVC Intra, DNxHD/DNxHR |
| `MXF OP-Atom` → `mxf` | **0** | **47** | Avid codecs |
| `MP4` → `mp4` | 4 | 4 | H.264/H.265 (± NVIDIA) |
| `AVI` → `avi` | 13 | 13 | GoPro CineForm YUV 10-bit, Grass Valley HQ, uncompressed |

**MP4 and AVI work either way only because their key case-insensitively equals their extension** —
which is what hides the bug. `QuickTime` does not equal `mov`, so every ProRes and DNxHR option
vanishes, and the remaining list (H.264, H.265, CineForm) looks exactly like a licence-gated free
edition. It is not. **Do not diagnose a missing codec as an edition limit without querying by
extension first.**

**Adjacent facts established at the same time, so they are not re-litigated:**

- The edition is confirmed by `Resolve.GetProductName()` → `"DaVinci Resolve Studio"`. Ask the API,
  never infer the edition from which codecs appear.
- **External scripting being refused is not an edition signal either.** On this Studio install
  `scriptapp("Resolve")` returns `None` while the in-app bridge connects fine. It is unrelated to
  licensing — and the cause is **not** simply an agent-launched instance; see § DaVinci Resolve 21
  below, where a human-launched Studio 21 refused it too.
- The bridge transport is **not** lossy for this call: bridge-by-extension returns all 60/75 codecs.

**Practical consequence:** on Studio, prefer **ProRes 422 HQ in `mov`** for a graded mezzanine — 10-bit
4:2:2, no macroblock padding, universally decodable. GoPro CineForm in `avi` is a valid fallback and is
genuinely 10-bit (`cfhd` / `yuv422p10le`), but **pads width to a multiple of 16**.

### CineForm padding, measured

3416×1920 in → 3424×1920 out. The pad is on the **right**: cropping at `x=0` scored **26.42 dB** PSNR
against an unpadded render of the same grade, versus **22.34 dB** at `x=8`. Carry
`crop=3416:1920:0:0` on the deliver leg.

### Render wall-clock

89.39 s / 2145 frames at 3416×1920, one Dehancer `.drx` grade (2 nodes), to CineForm 10-bit:
**227.6 s (3.8 min), 6.91 GB.** A 1-second smoke of the same chain took 3.7 s — so the smoke
over-predicted the full run by ~45%, which is the right direction to be wrong in.

## DaVinci Resolve 21 — the default baseline, and how to choose a transport

**Resolve 21 is the version this kit targets.** A look library authored on 18.5 needs **no rework**:

- **`.drx` authored on 18.5 apply unchanged** — the files carry an 18.5 `DbAppVer` and
  `ApplyGradeFromDRX` succeeds on 21 with no migration step.
- **Dehancer Pro 7.4 instantiates and renders clean.** Prove it from the node graph, not the eye:
  `GetToolsInNode(2)` naming the OFX entry is the proof. 21 sits inside the 7.4 Setup Guide's
  "19 and later", where 18.5 was only its "may work on earlier".
- **The Graph object is reachable** (it arrives in 19): `GetNumNodes`, `GetToolsInNode`,
  `GetLUT`/`SetLUT`, `ApplyGradeFromDRX`. Replacement-only — there is no append mode on any version.

🔴 **`fusionscript.dll` and the running Resolve may differ by major version.** An 18.5
`RESOLVE_SCRIPT_LIB` has driven a 21 instance with no error, so a version mismatch is not the first
thing to chase when a connection fails.

🔴 **Do not predict which transport will work — use a ladder.** A reading that scoped the
external-scripting refusal to *who launched Resolve* was refuted: a human-launched Studio 21 with a
project open returned `None` from `scriptapp("Resolve")` under both an 18.5 and the portable 21's own
`RESOLVE_SCRIPT_LIB`, while the in-app bridge answered and `--transport auto` rendered normally.

**What actually varies is the LAUNCHER.** A portable Resolve started through its own launcher installs
sandbox junctions that redirect `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve` at the portable's
tree; started directly from the inner `Resolve.exe` those junctions are absent and the scripting paths
resolve to whatever major version is *installed*. The `External scripting using` preference is not
stored as plain text, so it cannot be read off disk either.

**Doctrine.** Drive the hero pass on **`--transport auto`**: Local external scripting first, the in-app
bridge as the fallback. **`--transport local` calls `die()` instead of falling through**, so it must
never be the house flag — pinning it once turned an available bridge into a reported blocker. And
**diagnose before escalating**: a scripting probe answers "is it reachable, and on what project" for
free, the window title names the open project, and the bridge is a listening port rather than a window.
Process memory size is not evidence about whether a project is open.

🔴 **The API has no call that ADDS an OFX to a node.** The graph surface is `GetNumNodes`,
`GetLUT`/`SetLUT`, `GetNodeLabel`, `GetToolsInNode`, `SetNodeEnabled`, `ApplyGradeFromDRX`,
`ApplyArriCdlLut`, `ResetAllGrades` — none instantiates a plugin. An OFX reaches a node only by a UI
click or inside a `.drx`. A plugin listed in `OFXPluginCacheV2.xml` with `status="0"` was **scanned**,
which is not the same as loaded; the node-graph read-back is the only proof it instantiated.

🔴 **Never grep a `.drx` for a plugin name — it false-negatives.** `<Body>` is hex-encoded ASCII;
decoded it starts `0x81` then the zstd magic `28 b5 2f fd`. Every library look carries
`com.dehancer.film_pro.v7`, and `grep dehancer` matches none of them.

## Hard-cap variant — the worked budget (Discord 50 MB)

Same 89.387 s piece, same graded CineForm mezzanine, re-derived rather than re-encoded from the
1440p deliverable.

| step | value |
|---|---|
| stated cap | 50 MB |
| target (≈6% under, covers MB-vs-MiB and muxing) | **47 MB** |
| total budget | 47 000 000 × 8 / 89.387 = **4206 kbps** |
| audio | AAC **128 kbps** = 1.43 MB |
| muxing overhead allowance | ~0.5% ≈ 0.24 MB |
| **video bitrate set** | **4000 kbps** |
| predicted | ≈46.4 MB |
| **measured** | **46 187 526 B = 46.2 MB decimal / 44.0 MiB** — 2145 frames, H.264 High, 4134 kbps |

✅ **Field outcome:** uploaded and viewed on Discord — reads well, **grain visibly
survived**. Qualitative operator report, not a measurement, but it confirms the decision branch: at
**4.1 Mbps 1080p, downscaled 1.78× from the graded mezzanine, with `-tune film`**, grain is still
present in the delivered file. Consistent with the ~2.5 Mbps floor below which grain is destroyed —
this ran comfortably above it.

⚠️ **Scope this correctly: that is OUR encode surviving, not a platform transcode.** A chat platform
serves an under-limit upload essentially as-is, so the result validates the bitrate, tune and
downscale choices — it says nothing about surviving a transcode ladder. The ladder claim rests on the
separate 5 Mbps proxy measurement above, and on the YouTube arm, which is untested as of this writing.

**The budget arithmetic landed within 0.4% of prediction**, which is the argument for two-pass in one
number: the cap was hit on the first run with no guess-and-check, and with 7.6% headroom against the
decimal reading of the limit (12% against MiB).

```
crop=3416:1920:0:0 → scale=1920:1080:lanczos → overlay wm(180×155 @ 48/36) → format=yuv420p
libx264 -preset slow -tune film -b:v 4000k -pass 1|2   ·   aac 128k @48k   ·   +faststart
```

**Why `-tune film` and not `-tune grain`:** `film` lowers deblocking strength, which is what keeps a
constrained encoder from smearing grain into mush. `grain` preserves grain by *spending bitrate* —
the one thing a hard cap does not have. At 4 Mbps `grain` starves the image to protect the noise.

**Why two-pass:** CRF targets quality and yields whatever size that costs, so hitting a byte ceiling
with it is guess-encode-measure-repeat. Two-pass sees the whole file before allocating.

**Why H.264 rather than H.265/AV1**, which would look better at this bitrate: inline playback support
for the newer codecs is uneven across chat clients and their mobile apps, and a file that looks
slightly worse but *plays inline* beats one that looks better behind a download button.

**Watermark scaled proportionally**, not re-specified: 240 px at 2560 wide → 180 px at 1920 wide,
margins 64/48 → 48/36. Constant fraction of frame width, so every variant reads identically.

### The variant ladder this produces

| file | res | size | purpose |
|---|---|---|---|
| `…__rhea-1x4__film-cinestill.avi` | 3416×1920 10-bit | 6.91 GB | **graded mezzanine — every variant derives from HERE** |
| `…__1440p_clean.mp4` | 2560×1440 | 367.6 MB | un-watermarked archive |
| `…__1440p_watermarked.mp4` | 2560×1440 | 364.6 MB | YouTube upload |
| `…__1080p_discord50.mp4` | 1920×1080 | 46.2 MB | hard-cap chat/competition |

**None of the deliverables is an input to another.** Four encodes, four single-compression paths.

## Instrument discipline — two ways a measurement lies

**`ffmpeg -v error` suppresses the PSNR filter's own result line.** The `[Parsed_psnr_0] … average:`
summary is logged at INFO, so a comparison run at `-v error` prints nothing and reads as a failed
command rather than a suppressed result. Use `-v info` and grep the summary, or write `stats_file`.

**Every comparison carries a known-answer case in the same invocation.** Comparing the reference
against *itself* must return `inf`; anything else means the instrument is broken and its verdicts are
void. That self-test is what caught the `-v error` suppression above — the real comparisons returned
empty, and without the self-test the empty result would have been read as "the crops are identical".

## Deliver leg — the encode that shipped

89.39 s / 2145 frames, graded CineForm 10-bit mezzanine 3416×1920 → YouTube 1440p.

```
crop=3416:1920:0:0 → scale=2560:1440:flags=lanczos → [overlay wm] → format=yuv420p
libx264 preset medium, crf 16, maxrate 40M, bufsize 80M, high@5.1
bt709 primaries/trc/colorspace, sws_dither=ed, aac 320k @48k, +faststart
```

Result **~33 Mbps, 365–368 MB**, 2145 frames out (exact match in), ~4.5 min per encode at ~8 fps.

**Why 1440p rather than 1080p:** uploading above 1080 puts YouTube in its VP9/AV1 tier with a higher
bitrate ladder, so grain and halation survive even for viewers watching at 1080. This is the
mezzanine-above-delivery rule (step 4) applied one level further out, to the platform's own
transcode. 3416 → 2560 is still 1.33× above delivery.

**Aspect note:** 3416×1920 is 1.7792, not exactly 16:9 (1.7778) — it inherits from an 854×480 source.
Scaling straight to 2560×1440 imposes a 0.078% horizontal squeeze, which is below perception and
preferable to cropping content or shipping a non-standard resolution.

## Audio — when NOT to re-lay the original track

A finish plan that says "re-lay the lossless music" is only correct if the edit's audio is an
unprocessed slice of that file. Test it before trusting it:

| method | offset found | peak correlation |
|---|---|---|
| envelope correlation @4 kHz | 34.415 s | 0.553, runner-up ratio **1.0002** |
| sample-accurate waveform @48 kHz | 34.4167 s | **0.146** (self-test 1.0000) |

Both agree on *where*, and both refuse the match. Same music, carrying processing applied in the NLE
— re-laying would have replaced the mixed audio with the raw track. **A repeating musical structure
makes envelope correlation nearly useless for offset-finding** (the runner-up ratio of 1.0002 says
dozens of offsets score alike); only the waveform correlation is diagnostic, and here it disproved
the plan rather than confirming it.

Resolve had already written the audio out as **PCM 16/48** in the graded render, so the best available
copy was in hand with no extra generation. **Check what the grade pass emitted before sourcing audio
from anywhere else.**

## The phone-native tier — the texture probe's calibration (2026-09-16)

`video-finish-qc/scripts/phone_texture_probe.py` on native 640×640 centre crops, grey plane, five frames at 10 / 30 / 50 /
70 / 90 % of the duration: the share of dead-flat 8×8 blocks, the noise floor (the median sd of the flattest 20 % of
blocks) and the median block sd, each as the mean over the frames with the frame range beside it. The selftest's injected
Gaussian noise of sd 0.5 / 1 / 2 / 4 read back 0.49 / 0.92 / 1.77 / 3.51 — linear. The layer is
`scripts/phone_native.py` (`--ref` runs this comparison on its own output).

| clip | raster · encode | dead-flat % | noise floor | median block sd |
|---|---|---|---|---|
| real phone clip A, as it arrived from a client | 1920×1080 H.264 ~2.5 Mbps | 2.1 [0.4–4.1] | 0.52 [0.36–0.74] | 2.99 [1.54–5.02] |
| real phone clip B, same source | same | 2.6 [0.0–9.6] | 0.48 [0.12–0.71] | 2.24 [1.05–3.28] |
| Gemini Omni Flash 1.1, three raw takes of one shot | 720×1280 H.264 ~2.2 Mbps | 0.0 | 1.75–1.96 | 7.06–7.18 |
| the same take delivered: faithful 1.5× lanczos + the ads-clean cube | 1080×1920 H.264 ~5 Mbps | 0.0 | 1.10 [1.03–1.19] | 5.33 [5.17–5.52] |
| the same take through Starlight ×2, then delivered | 1080×1920 | 0.0 | 2.37 | 7.16 |
| `phone_native.py` a — no noise, no denoise, 12 Mbps | 1080×1920 | 0.0 | 1.16 | 4.75 |
| b — hqdn3d 2, 12 Mbps | | 0.4 | 0.85 | 4.63 |
| c — hqdn3d 3, 4 Mbps | | 0.7 | 0.83 | 4.46 |
| d — noise 6, 12 Mbps | | 0.0 | 1.41 | 4.91 |
| **e — hqdn3d 6, 2.5 Mbps** | | **1.5 [0.9–1.8]** | **0.69 [0.61–0.78]** | **4.09 [3.81–4.26]** — IN BAND on all three |
| f — hqdn3d 8 + noise 2, 2.5 Mbps | | 0.4 [0.1–1.5] | 0.74 [0.62–0.87] | 3.95 [3.67–4.11] — in band |

What the table says. (1) A generated take is NOT under-textured by default: the 720p Omni output carried three to four
times the fine texture of two phone clips that had arrived through a ~2.5 Mbps re-encode, so the earlier "27.8 % dead-flat
at a 0.00 noise floor" finding on a Seedance → Rhea → grade master is a matched-content result, never a universal AI
tell. (2) The direction of the dose is decided per pair — here it was DOWN (a denoise and a lower bitrate); adding noise
(d) moved the take further out. (3) The band of one clip is a RANGE across its frames — two frames of one real clip read
6 % and 34 % dead-flat on an earlier three-frame read — so the acceptance compares against the range over every reference
frame, never a mean of means. (4) The median block sd is content-dominated (an outdoor lot against a living room): matched
scene class, or the number says nothing. (5) The encode is the largest lever: 12 → 2.5 Mbps moved more than hqdn3d 0 → 3.
The two real clips are the only references measured so far; a house reference set by scene class (a flat wall, a
textured room, a dark frame), shot on the phones the audience uses and passed through the platform's own transcode, is
the open item — and the platform re-encodes both the real and the generated upload, so the band that matters is the one
AFTER that transcode.

## Provenance

Local A/B evidence, the grain/encode measurements and the look-library parameter consensus come from
evidence runs on two productions in August–September 2026 (a seven-spot 9:16 ad campaign and an
89-second 16:9 music video); hosted rates were gathered from vendor pricing pages in the same weeks.
Re-measure before trusting a rate older than a vendor pricing change.
