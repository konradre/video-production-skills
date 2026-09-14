---
name: video-finish
description: >
  Finishes generated or low-resolution video — upscale, film look, grain, watermark, delivery encode — in the
  order that survives platform recompression. Use when AI-generated footage (Seedance, Veo, Kling, Runway) needs
  to reach a deliverable; when choosing an upscaler or tier; when applying a Dehancer film look or a LUT; when
  deciding grain; or when a finished master looks mushy, bands, or loses its grain after upload. Triggers —
  "upscale this video", "which Topaz model", "Starlight or Rhea", "add the film look", "apply the LUT", "should I
  add grain", "where does the watermark go", "4K or 1080p", "why did my grain disappear after uploading", "too big
  to upload", "fit it under Discord's limit". Not for LUFS loudness mastering of the audio — use mastering-audio.
  Not for the EDL-driven spot finish, the hero chain or the deliverable QC — use video-finish-qc.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(ffmpeg*), Bash(ffprobe*), Bash(python3*), Bash(ls*), Bash(powershell.exe*)
---

# Video Finish

Taking generated video to a deliverable. **The order is the skill** — every rule below exists because
doing it in a different order destroys something you paid for.

```
upscale  →  grade (LUT + Dehancer)  →  grain  →  watermark  →  downscale  →  encode
```

Nothing in that chain commutes. Grade before the upscale and the reconstructor rebuilds your halation
as photographed detail. Grain at delivery resolution and the encoder discards it. Watermark before
the upscale and it gets sharpened into artefacts.

**Scope.** This skill is the per-clip technique and the order it must run in. A whole SPOT — its EDL, the
hero chain, the three-stage render, the finals and the deliverable QC — runs through `video-finish-qc`, which
applies the order below; come here for the tier, the grade, the grain, the watermark and the byte-cap decisions.

**What varies.** The tier names, rates and pixel thresholds are the Topaz and Dehancer versions measured in
[`references/EVIDENCE.md`](references/EVIDENCE.md); the delivery bitrate decides grain; the platform and the byte cap decide
the variant. The order is the one thing that does not move — `video-production/references/WHAT-VARIES.md`.

## 1. Classify the source, then pick the tier

**The decision that dominates every other: does this source need detail *reconstructed*, or only
*enlarged*?**

```
Source is AI-generated, heavily compressed, or below 720p?
  YES → RECONSTRUCTIVE tier — the model must invent detail
        Topaz Starlight (Fast 2 / Precise 2.6 / HQ / Mini / Sharp) · Topaz Astra · Topaz Rhea
  NO (clean capture, already ≥1080p) → FAITHFUL tier is fine and far cheaper
        Topaz Proteus · Topaz Gaia · ByteDance Video Upscaler
```

**A faithful upscaler applied to 480p produces enlarged 480p.** It does not deliver the softness that
makes reconstructed footage read as filmic rather than as a render — at any price. Picking Proteus
because it is cheaper is not a budget decision, it is choosing not to do the technique.

The softness is the *feature*. A reconstructive upscaler invents detail softer than capture, and that
is what separates upscaled 480p from a natively-rendered 1080p frame with its tell-tale hard edges.

**Within the reconstructive tier the pick is PER SHOT, not per pipeline.** Measured on a delivered
multi-spot campaign: local Rhea ×4 by default — free, and its output is the review copy —
and Starlight Precise 2.6 ×4 **from the original source** for any shot whose faces sit too small for
the generator to have drawn them (a head under ~50 px tall in a 480×854 take — at 480p, every full-body
wide; on another native raster, count the head in that take's own pixels) or whose text must read. On
those shots the faces' edge energy went up two to five times and glasses, hair and chart bars became
objects; chest-up and closer, Rhea held on every close
shot. Starlight does not stack on Rhea — both start from the source, so the free pass is triage, not a
step, and the framing predicts the need before anything runs: go straight to Starlight on a wide.
Two checks on every Starlight shot: identity across cuts (a small face is reconstructed plausibly,
not faithfully) and invented small text (a corridor door sign grew fake lettering). Numbers in
[`references/EVIDENCE.md`](references/EVIDENCE.md) § Starlight vs Rhea.

**Done when:** the tier is chosen from the source's nature, not from its price — and within the
reconstructive tier, per shot from the face size, not once for the pipeline.

## 2. Choose local or hosted

Both routes reach the same deliverable. The trade is money against wall-clock.

```
Is this a one-off, or is the GPU free tonight?
  YES → LOCAL (Topaz Video AI, unlimited local rendering under the subscription) — $0
        Cost is hours. Benchmark before committing (step 3)
  NO — latency matters, or the GPU is claimed?
       → HOSTED (fal `topaz/upscale/video/generative`) — see references/EVIDENCE.md for rates
```

**Output resolution is a bigger lever than model choice on a hosted bill** — 1080p costs half of 4K on
every Starlight variant. From a 480p source, 1080p is 2.25× and 4K is 4.5×; at 4.5× you are asking the
model to invent most of the frame. Buy 4K only when a 2K-or-larger deliverable is actually wanted.

**Hosted ingest:** fal takes a URL, not a file. Large masters go through the two-step storage API —
`POST /storage/upload/initiate` returns an `upload_url` and a `file_url`, then `PUT` the raw bytes.
Base64 data URIs are viable for reference stills, never for a master.

**Hosted credential:** `FAL_KEY` in the environment, sourced from the env file that holds it (`KEY=value`, no `export`, no
quotes — the same file is read by a shell and by a service's `EnvironmentFile`, which rejects `export`); sent as
`Authorization: Key <key>`, never on a command line. No `FAL_KEY` → stop and name the env file; never paste the key.

**Done when:** the route is chosen with the wall-clock cost named out loud, not discovered later.

## 3. Smoke-test one second before committing hours

Never launch a multi-hour upscale on an unmeasured assumption. A 1-second slice costs minutes and
answers four things a full run answers too late:

```bash
ffmpeg -v error -y -ss 30 -t 1 -i <master> -c copy /tmp/_smoke1s.mov
# then run the upscaler on _smoke1s.mov
```

- **Does the model exist in this install?** Check the model directory before trusting a name.
- **Does the container decode?** DNxHR, ProRes and HEVC are not equally supported everywhere.
- **Which encoder wins the ladder?** NVENC vs libx264 changes both speed and output bit depth.
- **Seconds per frame on *this* aspect ratio.** A benchmark from portrait footage does not predict
  landscape. Multiply by `duration × fps` for the real ETA.

⚠️ **Check the runner's timeout before the real run.** A per-clip timeout that defaults to one hour
kills a three-hour job at ~30% and reports `TIMEOUT`, not failure — the partial output looks like a
crash. Set it generously.

**Done when:** you have a measured seconds-per-frame from this footage and an ETA derived from it.

## 4. Upscale to a mezzanine ABOVE delivery resolution

**This is the rule that decides whether grain survives, and it is the one most often broken.**

Grain rendered at delivery resolution has energy right up to Nyquist, and a rate-limited encoder
discards that first. Grain rendered on a *larger* mezzanine and then downscaled is band-limited —
which is exactly what an encoder can afford to keep. Measured: **80% of the grain survives a 5 Mbps
rendition from an above-delivery mezzanine, versus 28% from a 1:1 one.**

So: **do not post-scale in the upscale pass.** Upscale to the mezzanine, grade there, and let the
deliver leg do the downscale. Never grade on a 1080 timeline when a larger mezzanine exists.

**Done when:** the upscaled file is larger than the intended deliverable, and no downscale has
happened yet.

## 5. Grade at mezzanine resolution

### Choose the look by RENDERING it, never by its name

A look's name and description do not predict what it does to *your* footage. Render every candidate
at full mezzanine resolution on one frame and compare them side by side.

**Pick the test frame for tonal range, not for prettiness** — the widest span the grade has to
survive: backlit haze, textured subject, a saturated colour, and a deep shadow in one frame. A frame
that is mostly midtones tells you nothing.

Measured on upscaled 480p creature footage: the look the project notes had recorded as the intended
choice (`film-teal-orange`) **crushed the foreground subject to near-silhouette**, discarding the fur
detail a 135-minute reconstructive upscale existed to create. That is invisible from the name and
obvious in one rendered frame. The chosen look was the one whose halation the footage had actually
earned.

⚠️ **Beware a look that buys contrast with shadow crush on reconstructed footage.** You paid for
invented detail; a heavy contrast curve throws it away, and cool shadow tints are exactly where 4:2:0
chroma blocks up. Prefer the look that keeps the detail, and add contrast as its own node.

Node order inside the grade:

```
shot balance  →  creative grade  →  LUT (.cube)  →  Dehancer (.drx)  →  light sharpen
```

🔴 **On AI-generated footage, set Dehancer's Input to Rec.709 — never a log profile.** Generated video
is display-referred Rec.709 already; there is no log encoding to undo. Choosing a log input applies an
inverse transform to footage that never had one, wrecking the black point and oversaturating
everything before the film emulation runs. This is the single most common mistake on this footage.

**Two tiers, and they must not overlap.** A `.cube` can only carry per-pixel colour — white balance,
tone curve, contrast, split-tone, saturation, black point, film-stock transform. Spatial and temporal
effects — halation, bloom, grain, gate weave — cannot be baked into a LUT and must run after it.
**Do not stack a film-stock LUT on top of Dehancer's own film profile**; one or the other owns the
stock transform, or you are emulating twice.

Halation is where backlit, misty or steam-filled footage wins — it is the physics a LUT cannot encode.
Starting values and the ads-versus-film parameter split are in
[`references/EVIDENCE.md`](references/EVIDENCE.md).

**Cap the sharpen.** The upscaler already invented micro-detail; sharpening on top gives over-crisp
edges plus compression ringing.

**Push contrast, not chroma.** 4:2:0 subsampling blocks up saturated reds and blues, so get colour
separation from luminance contrast and keep saturation restrained.

**Diagnose a look complaint per shot before any global move.** Measure black point, white point, luminance spread and
saturation shot by shot, and read skin tone as the content-controlled number: a spot called unreal measured healthy
contrast and black levels, with its defect in shot-to-shot INCONSISTENCY — and a global saturation lift would have
pushed the rejected shot, already the most saturated, further out.

**Done when:** the grade is applied at mezzanine resolution with a Rec.709 input and exactly one
source of the film-stock transform.

## 5b. Write the graded mezzanine at 10-bit — and VERIFY, do not assume

The grade's output is what grain and the downscale then run on. Written at 8-bit it bands on exactly
the content this footage is full of — mist, fog, sky, steam — and grain is being added to an already
quantised image.

🔴 **A codec's name does not tell you its bit depth. Probe the file:**

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,profile,pix_fmt,width,height \
  -of default=nw=1 <graded-file>
```

`yuv420p` / `yuv422p` = 8-bit. `yuv420p10le` / `yuv422p10le` = 10-bit. Measured: an H.265 render that
*should* have been Main10 came back `Main` / `yuv420p` because the encoder's bit-depth control was not
reachable from the scripting API — the request succeeded and silently gave 8 bits.

⚠️ **Check the geometry in the same probe.** Some intermediates pad to a macroblock multiple —
GoPro CineForm rounds width up to a multiple of 16, turning 3416 into 3424. Determine which edge the
pad sits on by PSNR against an unpadded render of the same grade, then carry the crop on the deliver
leg (`crop=3416:1920:0:0`) or the aspect ratio ships wrong.

Resolve-specific codec availability, and the API call that silently hides most of it, are in
[`references/EVIDENCE.md`](references/EVIDENCE.md) — read it before concluding a codec is unavailable.

**Done when:** the graded mezzanine probes as 10-bit, and its width and height are known and either
correct or scheduled for a crop.

## 6. Grain — coarse or not at all

Grain is a bitrate tax of **+50% to +120%** at the same CRF. Buy it deliberately.

```
Delivery is a 2.5 Mbps-class rendition (phone-tier social)?
  YES → skip grain entirely — it doubles the master and then does not exist
  NO (YouTube ladder, 5 Mbps+, or a local deliverable) ↓

Is the mezzanine above delivery resolution? (step 4)
  NO  → grain will mostly not survive; fix step 4 first
  YES → apply COARSE grain (≥2 px), never fine per-pixel
```

**Fine per-pixel grain is erased by a 2.5–5 Mbps re-encode** — it lands within 1–3% of having added
none, after costing the bitrate. Coarse grain keeps roughly a third of its energy. A constrained
encoder filters per-pixel noise out first; this reproduces Netflix's own film-grain-synthesis
observation.

**One pro-compression use survives all of that:** a whisper of grain dithers banding. Smooth
low-contrast gradients — fog, mist, skies, steam — band under 8-bit delivery, and grain is the cheapest
fix. Keep the mezzanine at 10-bit and dither on the final 8-bit encode as well.

**Also note the upscaler may already re-inject shadow grain.** You are adding to something, not
starting from clean.

🔴 **Check whether the GRADE already applied grain before you add any.** A film-emulation preset
(Dehancer and equivalents) typically carries grain, halation and bloom in the same node as the stock
transform — so a single grade pass can deliver colour + stock + halation + bloom + grain together,
and a "remaining grain step" then doubles it. Verify against the picture, not against the preset file:
plugin parameters are stored encoded inside the grade export, so grepping it for `grain` or
`halation` finds nothing whether or not they are enabled. Compare a 1:1 crop of graded against
ungraded on a highlight — halation shows as a warm bleed, grain as texture in flat areas.

**Done when:** grain is coarse and applied on the 4K/mezzanine, or deliberately omitted with the
delivery bitrate as the reason.

## 7. Watermark last, then deliver

**After the grade, after the grain, on the final master.** Two of those are hard rules:

- **Never before the upscale.** The reconstructor treats the mark as photographic content, sharpens
  its edges, reinterprets its semi-transparent pixels, and spends capacity rebuilding something you
  drew.
- **Never before the LUT or Dehancer.** The grade remaps its values, and halation bleeds light out of
  it as though it were a practical highlight in the scene — obviously wrong on a hard-edged graphic.

Against grain it is a choice: on top reads as a clean overlay (standard broadcast practice), underneath
integrates it into the image at some cost to legibility.

**Archive the graded, upscaled, grained master clean** and apply the watermark as the final layer per
deliverable. Repositioning it for another platform is then one node, not a re-grade.

Encode last, downscaling from the mezzanine in the same pass — and inside that pass:

⚠️ **Overlay the mark AFTER the downscale, not before.** Scaling the video first and compositing at
delivery resolution keeps the logo pixel-crisp; compositing at mezzanine resolution and then
downscaling resamples it, softening exactly the hard edges a graphic depends on. Both orders are one
encode pass, so this costs nothing.

⚠️ **Crop the logo to its opaque bounding box before sizing or positioning it.** Exported logos
routinely sit inside a larger transparent canvas, and margins are then measured from the *canvas* —
silently pushing the mark away from the corner. Measured: an 818×705 logo inside a 960×960 canvas
placed at a 64 px margin landed ~130 px in and ~90 px up.

```bash
# bbox of everything above alpha 8
python3 -c "from PIL import Image; import numpy as np; \
a=np.asarray(Image.open('logo.png').convert('RGBA'))[:,:,3]; y,x=np.where(a>8); \
print(f'crop={x.max()-x.min()+1}:{y.max()-y.min()+1}:{x.min()}:{y.min()}')"
```

**Verify the mark at several timecodes, never just the first frame** — a filtergraph error can put it
on frame 1 only, and head-frame checks pass. Sample early, middle and late, over light and dark
backgrounds both.

**Never build another deliverable by re-encoding a finished one.** Go back to the graded mezzanine;
re-encoding a delivery file puts the grain through compression twice.

**Done when:** an un-watermarked master exists alongside the watermarked deliverable.

## 8. Platform variants and hard size caps

A chat platform, a competition entry or an email attachment imposes a **byte ceiling, not a quality
target** — a different problem from step 7, and it needs a different tool.

🔴 **Two-pass at an explicit bitrate, never CRF.** CRF targets a quality level and produces whatever
size that costs, so hitting a cap with it means guess → encode → measure → guess again. Two-pass lets
the encoder see the whole file before allocating, and lands within a few percent on the first run.

**Derive the bitrate from the cap, do not pick one:**

```
video_kbps = (cap_bytes × 8 / duration_s / 1000) − audio_kbps − ~0.5% muxing overhead
```

⚠️ **Target below the stated cap.** "50 MB" may mean 50,000,000 or 52,428,800 bytes and the platform
rarely says which; container overhead is on top. Aim ~6% under and the ambiguity stops mattering.
Report the result in **both** decimal MB and MiB so the reader can check it against either.

**Always re-derive from the graded mezzanine.** The tempting input is the finished deliverable, which
is exactly the double-compression trap from step 7 — and it bites hardest here, because the second
encode is the heavily constrained one.

### Grain flips from asset to liability as the cap tightens

```
Is the resulting bitrate below ~2.5 Mbps?
  YES → the grain will be destroyed AND will have cost +50-120% of the bitrate getting there.
        DENOISE before encoding — spend those bits on the image instead
  NO  → keep the grain, and help it survive:
        x264 `-tune film` eases deblocking, which is what stops a constrained encoder
        smearing grain into mush. NOT `-tune grain`, which preserves grain by spending
        bitrate the cap does not have
```

### Scale the watermark proportionally, not by absolute pixels

A mark sized in pixels for one resolution reads oversized at a smaller one. Keep it a constant
fraction of frame width and scale the margins by the same factor, so every variant looks identical.
From a 2560-wide build at 240 px and 64/48 margins, the 1920-wide variant is 180 px at 48/36.

### Codec choice is a compatibility question here, not a quality one

H.265 and AV1 compress far better at a hard cap, and inline playback support for them is uneven
across chat clients and their mobile apps. **A file that looks worse and plays is better than one
that looks better and shows a download button** — ship H.264 unless the platform's support is known.

**Done when:** the file is under the cap on both readings of it, was built from the mezzanine, and
the grain decision matches the bitrate the cap actually allows.

## Verifying a long upscale is actually working

A live process proves nothing. Check that it is *progressing*:

```bash
ls -la <output-file>          # growing?
# GPU utilisation and VRAM, via nvidia-smi
```

Divide the output size by the bytes-per-frame measured in the smoke test to get frames completed, and
compare against elapsed time. A rate matching the smoke test means it is healthy.

**Watch VRAM headroom.** Reconstructive models at 4× can sit at >90% of an 11 GB card, and CUDA OOM on
these is documented as non-deterministic. Nothing else should touch that GPU while it runs. Launch
detached (`python3 ~/.claude/skills/video-production/scripts/detach.py --log <abs log> -- …`) so the job
outlives the shell, and poll on demand rather than holding a follower open.

**Failure behavior:** an upscale that dies leaves a truncated output and no completion sentinel. Treat
a missing sentinel as failure regardless of file size, and re-run rather than salvaging the partial —
a truncated mezzanine silently shortens the deliverable.

## Cross-references

- [`references/EVIDENCE.md`](references/EVIDENCE.md) — the measured A/B numbers, grain-survival
  tables, hosted rates, Dehancer parameter split, and the Topaz-on-Linux finding. Read it before
  choosing a model or arguing with any rule above.
- `mastering-audio` — the audio half of a finish.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
