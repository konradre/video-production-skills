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
        — and when the capture already sits at the delivery raster and the deliverable carries no grain (§ 4, § 6):
          NO upscaler at all — a lanczos resample to the display shape; nothing is redrawn
```

**Real footage at the delivery raster is not upscaled.** A 1080p capture for a 1080p ad on the clean pair has no detail to
reconstruct and no grain for an above-delivery mezzanine to protect, so the faithful tier there is a mathematical resample
to the true display shape (the SAR honoured: an anamorphic 9:16 clip stored 1920×1080 becomes 1080×1920), never a model —
a model redraws. The operator's standing ask for real footage is that nothing is warped (2026-09-26): prove it, shot by
shot, with a (0, 0) phase correlation between the resampled flat and the graded hero (`video-finish-qc/scripts/
normalise_shots.py verify`) and on the finished spot against the pre-finish one (`qc_deliverable.py --prev`).

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

**A third tier exists for one genre.** A creator-style / UGC spot that must read as phone-shot takes the
**phone-native tier** (§ 5, `ugc-phone`): a faithful 1.5–2× enlargement when the source is 720p+ with a large face
(reconstruction only when the source is genuinely under-rendered), a near-identity cube, no Dehancer, and a temporal
layer plus a phone-class encode dosed against the project's own real phone clips. It is chosen at intake with the genre,
never as a rescue for a take that failed the reconstructive tier.

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

**The mezzanine is for grain.** With no grain on the deliverable — an ad on the clean pair, a 2.5–5 Mbps rendition (§ 6) —
an above-delivery mezzanine protects nothing, and a real source already at the delivery raster goes to the grade at that
raster (§ 1): normalised per shot, then the look.

**Done when:** the upscaled file is larger than the intended deliverable, and no downscale has
happened yet — or, for real footage at the delivery raster with no grain, no upscale ran at all and the graded input sits
at the display shape.

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

### The phone-native tier (`ugc-phone`) — a creator-style spot that must read as phone-shot

Phone-nativeness is not a colour transform. A `.cube` carries per-pixel colour only; what makes a phone clip read as a
phone clip is temporal texture, camera behaviour and the encode. So `ugc-phone` is a TIER, not a look: a near-identity
colour tier (`ugc-phone_33.cube` in the look library — no stock transform, no split-tone, a gentle consumer tone map, skin
untouched; mid-grey 128 → 131), **no Dehancer node** (halation, bloom and film grain read as film, and a phone has none),
and a temporal layer at DELIVERY resolution whose dose is decided by measurement. The order inverts two film rules on
purpose:

```
upscale — faithful 1.5–2× lanczos when the source is 720p+ with a large face; reconstructive only when under-rendered
→ the neutral cube at mezzanine resolution (chosen by rendering it, like every look — § 5)
→ the inter-shot consistency read BEFORE any global move (saturation / white-balance spread across shots — video-finish-qc QC.md)
→ downscale to delivery (1080×1920)
→ the temporal layer AT DELIVERY RESOLUTION: fine sensor-style noise OR a denoise (the probe decides the direction),
  a slow exposure drift (±3–5 %, a 2–4 s period), a stepped white-balance drift (±150 K), an auto-exposure step at each cut,
  a 1–3 px handheld micro-shake                                           — scripts/phone_native.py
→ captions and overlays in the native style; no watermark
→ the phone-class encode: H.264 4:2:0 1080×1920, closed GOP, BT.709 tags, at the bitrate the band asks for (2.5–12 Mbps)
→ audio: a room-tone bed, the phone-mic band, a light auto-gain feel, then the standing loudness pass (spot-audio-assembly)
```

Why fine noise at delivery resolution here, when § 6 says coarse grain above delivery: § 6 protects grain as an
aesthetic through the platform's re-encode; this tier wants the phone's OWN post-compression texture, which is fine noise
partly flattened by the encode. And why the dose is measured, never styled: the phone-texture probe
(`video-finish-qc/scripts/phone_texture_probe.py` — dead-flat 8×8 share, noise floor, median block sd, on native centre
crops at five points of the clip) read two real phone clips at a 0.1–0.7 noise floor and 0–10 % dead-flat, and three raw
720p Omni Flash takes at 1.8–2.0 and 0 % — **the generated take carried MORE fine texture than the phone clips, not less**,
so the dose that landed it inside the real band was a DENOISE (hqdn3d 6) and a 2.5 Mbps encode, and adding noise moved it
further out. On another generator, another raster or another set of real clips the direction can reverse; the retrospective's
"27.8 % dead-flat at a 0.00 floor" on a Seedance → Rhea → grade master was a matched-content comparison, not a universal
threshold. The numbers: [`references/EVIDENCE.md`](references/EVIDENCE.md) § The phone-native tier.

**The protocol.** (1) Probe the project's own real phone clips — as they arrived, by scene class (a flat wall, a textured
room, a dark frame); with none, a house reference set shot on the phones the audience uses and passed through the
platform's transcode. (2) Render the candidate through `phone_native.py --ref <real clips>`: it probes its own output
and says, per metric, IN BAND / ABOVE / BELOW against the RANGE over every reference frame (never a mean). (3) Move the
dose — `--denoise`, `--noise`, `--bitrate` — until all three read in band on matched content; the median block sd is
content-dominated and says nothing across scene classes. (4) Run the existing instruments too: face detail at equal
size, the frozen-frame fraction, the splice read, the inter-shot spread, the loudness. **Dose is an inverted U** —
medium won the one controlled test, heavy lost — and the proof shot's legibility is never degraded; the tier is a
candidate the operator renders and judges beside the clean finish, never a default.

```bash
python3 ~/.claude/skills/video-finish/scripts/phone_native.py --in <graded, downscaled clip> --out deliver/<name>-phone.mp4 \
  --denoise 6 --noise 0 --bitrate 2.5M --drift 0.04 --wb 150 --shake 2 --cuts 3.2,7.8 --audio phone \
  --ref assets/<real-phone-clip-1>.mp4 assets/<real-phone-clip-2>.mp4          # prints the band verdict per metric
python3 ~/.claude/skills/video-finish/scripts/phone_native.py --selftest
```

**Done when:** the real band is on record (which clips, which scene class, which frames), the candidate's three numbers
sit inside it, the existing instruments passed, and the operator has judged the phone render beside the clean one.

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

**The phone-native tier is the one exception** (§ 5): there the texture is fine sensor-style noise — or a denoise — applied
at DELIVERY resolution and flattened by a phone-class encode on purpose, dosed by the probe against real phone clips; the
rule above protects grain as an aesthetic, the tier wants a phone's own post-compression texture.

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

## Scripts

| script | does |
|---|---|
| `phone_native.py --in --out [--canvas] [--noise] [--denoise] [--drift] [--wb] [--period] [--shake] [--cuts] [--ae-step] [--bitrate] [--audio copy\|phone\|none] [--ref …] [--probe] [--dry-run]` · `--selftest` | the phone-native tier's temporal layer and encode at delivery resolution (§ 5): a denoise or fine sensor-style noise, a slow exposure drift, a stepped white-balance drift, an auto-exposure step at each cut, a handheld micro-shake, the phone-class H.264; `--ref` probes the output against real phone clips and says IN BAND / ABOVE / BELOW per metric; prints the filtergraph it ran |

## Cross-references

- [`references/EVIDENCE.md`](references/EVIDENCE.md) — the measured A/B numbers, grain-survival
  tables, hosted rates, Dehancer parameter split, the Topaz-on-Linux finding and the phone-native tier's
  calibration. Read it before choosing a model or arguing with any rule above.
- `video-finish-qc` `scripts/phone_texture_probe.py` — the instrument the phone-native tier is dosed by.
- `mastering-audio` — the audio half of a finish.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
