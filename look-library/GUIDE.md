---
title: Film looks, LUTs and Dehancer in DaVinci Resolve for AI-generated video — a method another team can implement
date: 2026-09-09
audience: an operator and their coding agent setting up the same grading method on their own infrastructure. Nothing here depends on our machines, paths or projects; the public repositories and vendor documents it draws on are named so the sources can be read directly.
provenance: everything labelled "measured" or "shipped" comes from two productions finished with this method in August–September 2026 — a seven-spot 9:16 social ad campaign and an 89-second 16:9 music video — and from A/B runs on their footage; everything labelled "consensus" comes from a survey of eleven open-source colour and Resolve-automation repositories; the vendor facts come from Dehancer's own Setup Guide and Quick Guide and from Blackmagic's scripting README.
---

# Film looks, LUTs and Dehancer in DaVinci Resolve — the method

> What ships beside this guide: the five looks as baked `.cube` files (`cubes/`) and authored Dehancer
> `.drx` grades (`drx/`, Dehancer Pro OFX 7.4), the phone tier's cube with no `.drx` beside them, their
> recipes (`looks/*.yaml`, `RECIPES.md`), the cube
> baker, the validator and the preview chooser. The spectral base cubes are fetched with
> `fetch_spectral_bases.sh` only when a recipe is edited and rebaked.

## 1. What the method is, in one paragraph

Generate video at 480p, keep it clean (no grain, halation or bloom in any prompt), let a
**reconstructive** upscaler invent the detail — its output is softer at the edges than a native 1080p
render, which is the tell of AI video — and then grade the upscaled mezzanine in DaVinci Resolve with a
Dehancer film emulation that adds the halation, bloom and grain a LUT cannot. Deliver from that mezzanine
with a single encode per platform. Every look exists as two files that render the same look on different
machines: a `.cube` LUT for any ffmpeg host and a `.drx` Resolve grade for the Dehancer hero pass. The
grade is authored once by hand in Resolve and applied forever by script.

## 2. Three facts about the source that shape every setting

1. **AI-generated video is display-referred Rec.709.** There is no log curve to undo. Dehancer's Input
   is set to Rec.709 with no camera profile; a log input applies an inverse transform that never existed
   and wrecks the black point. This is the single most common mistake.
2. **Grade after the upscale, on the mezzanine, never before.** A reconstructive upscaler treats grain
   and halation in its input as detail to rebuild; graded 480p turns into smeared noise. And never grade
   on a 1080 timeline when a larger mezzanine exists — grade at mezzanine resolution and let the deliver
   step downscale.
3. **The upscaler already re-injects faint shadow grain.** Anything you add is added to that. Clean
   commercial work runs grain off; film work runs it low.

Two consequences that were measured rather than argued: grain only survives platform compression when it
was rendered on a mezzanine **above** delivery resolution (80% of it survives a 5 Mbps rendition from an
above-delivery mezzanine, 28% from a 1:1 one; at 2.5 Mbps every arm collapses to the no-grain level while
still having doubled the master bitrate), and fine per-pixel grain added in ffmpeg is erased by a 2.5–5
Mbps re-encode while costing +50% to +120% bitrate, so if grain must be added outside Dehancer it is coarse
(≥ 2 px), late (after the resize) and capped.

## 3. Every look is two files, never stacked

| tier | file | renders where | carries |
|---|---|---|---|
| colour | `<look>_33.cube` | anywhere — ffmpeg `lut3d`, a render farm, CI, designed graphics | white balance, exposure, lift/gamma/gain, highlight roll-off, tone curve, split-tone, black point, saturation with skin protection, the film-stock transform |
| spatial | `<look>.drx` | the Resolve hero pass only | the whole grade — the primaries plus the Dehancer node with its stock, halation, bloom, grain and Total Impact |

They are parallel renderers of one look, chosen by which machine is rendering; the `.drx` is not applied
on top of the `.cube`. The split is forced by physics and confirmed by the vendor: **only per-pixel colour
operations can be baked into a 3D LUT.** Dehancer's own LUT Generator says of its `.cube` export that it
excludes Grain, Halation, Bloom, Vignette, Film Breath and Gate Weave and "cannot be used as a grading
preset" (Quick Guide pp. 53–54). Inside a film emulation, halation runs before the negative transform and
grain is independent of the stock and sized by frame (JanLohse's `spectral_film_lut`); the `.drx` holds
that order for you.

### 3a. The five looks and the phone tier the library defines, and what each did on real footage

| look | genre | colour-tier base (cube) | Dehancer node (drx) | verdict from use |
|---|---|---|---|---|
| `ads-clean` | ads | none | Kodak Vision3 250D / Kodak 2383, halation OFF, bloom OFF, grain OFF, Total Impact 35 | the campaign look for all seven ads — true blacks, neutral overcast daylight, deadpan office and living-room scenes stay clean |
| `ads-warm` | ads | none | 250D / 2383, bloom light (≤ 0.1), grain OFF, TI 40 | rejected on an overcast construction-site spot (yellowed the sky and the mud); on the music video it was warm and punchy with the best detail retention per unit of contrast but read commercial rather than filmic — use only on scenes that are warm already |
| `film-teal-orange` | film | spectral Vision3 250D → 2383 | started from the first authored look (250D / 2383, halation + bloom at 35 mm / Super 35, grain 16 mm ISO 250), TI 80 | rejected on the music video: its contrast curve crushed the foreground subject to near-silhouette, throwing away the fur detail a 135-minute upscale had just reconstructed; its cool shadow tint is also where 4:2:0 delivery blocks up worst |
| `film-portra` | film | spectral Portra 400 → Endura Premier | Kodak Portra 400 / 2383, halation 0.35 (35 mm), bloom light, grain 16 mm ISO 250 low, TI 75 | the most natural of the film set, full skin and fur texture, but flat against a hard electronic track; unshipped so far — the people-first look |
| `film-cinestill` | film | spectral Vision3 500T → 2383 (the CineStill 800T colour identity) | CineStill 800T if the profile list has it, else Vision3 500T / 2383; halation **0.9**, bloom moderate, grain 16 mm ISO 250 low, TI 85 | shipped on the music video (1440p YouTube master and a 1080p 50 MB chat cut): real halation on the god-rays and practicals that backlit misty footage had earned; costs some black density, recoverable with a contrast node; grain visibly survived the chat-platform encode |
| `ugc-phone` | ads — the UGC / creator-style sub-genre | none — near-identity: WB 0, exposure +0.02, no split-tone, tone curve 0.12, black lift 0.004, saturation 1.02 with skin protected (mid-grey 128 → 131 through the cube) | **none by design** — halation, bloom and film grain read as film, and a phone has none of them | not a look but the colour tier of the phone-native FINISH TIER (`video-finish` § 5): the phone-ness is the temporal layer and the phone-class encode in `phone_native.py` (fine sensor noise OR a denoise, exposure and white-balance drift, micro-shake, ~2.5–12 Mbps H.264), dosed by `phone_texture_probe.py` against the project's own real phone clips — a 720p Omni take needed a DENOISE and a 2.5 Mbps encode to land inside two real clips' band (September 2026); unshipped so far |

**Choose a look by rendering it, never by its name.** Render every candidate at full mezzanine resolution
on one frame that spans the tonal range — a backlit highlight, a textured subject, a saturated colour, a
deep shadow — and compare side by side. The look our project notes had recorded as the intended choice
was the one that crushed the subject; that is invisible from a recipe and obvious in one rendered frame.

## 4. The settings

### 4a. Colour tier — the YAML that bakes the cube

Each look is a YAML file; a baker turns it into a 33³ `.cube`. Parameters are normalised the way the
`postfx` repository normalises them (temperature and tint ±1, strengths 0–1); the film base is a spectral
negative×print cube sampled first. Operation order in the baker, deliberate: **film-base LUT → white
balance → exposure → lift/gamma/gain → highlight roll-off → tone curve → split-tone → black point →
vibrance/saturation with skin protection last**, so skin protection sees the final hues.

```yaml
id: film-cinestill
genre: film                    # film | ads
intensity: 0.85                # recommended blend at the deliver step (1.0 = full)
film_base: spectral_luts/vision3_500t_2383.cube     # from ComfyUI-Darkroom's data/spectral_luts (MIT)
params:
  white_balance: { temp: -0.14, tint: 0.03 }
  exposure: { stops: 0.04 }
  lift_gamma_gain: { lift: [0, 0, 0.005], gamma: [1, 1, 1], gain: [1.0, 0.995, 1.05] }
  highlight_rolloff: { knee: 0.62, strength: 0.45 }
  tone_curve: { strength: 0.24, pivot: 0.44 }
  split_toning: { shadow: [-0.02, 0.006, 0.03], highlight: [0.02, 0, 0.01], strength: 0.55, balance: 0.5 }
  black_point: { lift: [0.016, 0.014, 0.024] }
  vibrance: { vibrance: 0.14, saturation: 1.08, skin_protect: 0.5 }
compression: { grain: low-capped, mezzanine: yuv420p10le, sharpen: light }
```

The shipped values for the five looks that carry a `.drx`, with the consensus range they were tuned against
(the phone tier's values, close to identity, are in its § 3a row and in `looks/ugc-phone.yaml`):

| parameter | `ads-clean` | `ads-warm` | `film-teal-orange` | `film-portra` | `film-cinestill` | consensus ads / film |
|---|---|---|---|---|---|---|
| film base | none | none | vision3_250d_2383 | portra_400_endura_premier | vision3_500t_2383 | none / Vision3 250D day, 500T night |
| white balance temp / tint | +0.03 / 0 | +0.18 / +0.03 | +0.05 / 0 | +0.09 / +0.015 | −0.14 / +0.03 | near-neutral / +0.08 or scene-warm |
| exposure (stops) | +0.04 | +0.06 | 0 | +0.04 | +0.04 | — |
| lift (R,G,B) | 0 | .004/.002/0 | 0/0/.004 | .004/.002/.001 | 0/0/.005 | 0 / +0.008 |
| gamma | 1 | 1.01/1/0.99 | 0.995/1/1 | 1.015/1.005/0.995 | 1 | — |
| gain | 1.02/1.01/1.01 | 1.04/1.00/0.95 | 1.03/1.00/0.99 | 1.015/1.00/0.98 | 1.00/0.995/1.05 | — |
| highlight roll-off knee / strength | 0.76 / 0.35 | 0.68 / 0.5 | 0.72 / 0.4 | 0.66 / 0.4 | 0.62 / 0.45 | — |
| tone curve strength / pivot | 0.28 / 0.46 | 0.24 / 0.46 | **0.32** / 0.44 | 0.14 / 0.46 | 0.24 / 0.44 | ~0.28 gentle S / ~0.5 |
| split-tone strength | 0.25 | 0.4 | 0.72 | 0.4 | 0.55 | ~0.25 / 0.62–0.85 |
| black point lift | 0 | 0.008 | 0.006 | 0.008 | .016/.014/.024 | 0 / +0.008 |
| saturation / vibrance / skin protect | 1.04 / .18 / 0.7 | 1.06 / .16 / 0.7 | 1.10 / .14 / 0.6 | 1.04 / .14 / 0.75 | 1.08 / .14 / 0.5 | 1.02–1.08, 0.7 / 1.08–1.2, 0.55 |
| recommended blend | 1.0 | 1.0 | 0.85 | 0.9 | 0.85 | — |

Why the shipped numbers sit below the consensus in places: `film-teal-orange` uses tone-curve 0.32 rather
than the standalone 0.5 because the 2383 print base already supplies S-curve contrast (0.5 on top would
double it), blends the `postfx` "blockbuster" split-tone (0.85) with `hyperframes`' restrained one (0.62)
at 0.72, and caps saturation at 1.10 because 4:2:0 delivery degrades saturated reds and blues — get
separation from luminance contrast, not chroma. `ads-warm` is `postfx`'s golden-warm look pulled toward the
ads column (temperature +0.4 → +0.18, split 0.6 → 0.4, saturation capped at 1.06). `film-portra` halves
the `postfx` Portra trims wherever the Endura Premier print base already supplies them. `film-cinestill`
keeps the blue-lifted blacks and drops the white-balance shift from −0.28 to −0.14 because the tungsten
cast is already in the 500T base. Clarity, vignette and chromatic aberration appear in the consensus and
are deliberately not baked: they are not per-pixel operations.

**The baker's operations, so an agent can rebuild it** (RGB in [0,1], Rec.709 luma 0.2126/0.7152/0.0722):
white balance scales RGB by `(1 + 0.28·temp + 0.08·tint, 1 − 0.10·|tint| − 0.08·tint, 1 − 0.28·temp + 0.08·tint)`;
exposure multiplies by `2^stops`; lift/gamma/gain is `(gain·(c + lift·(1−c)))^(1/gamma)`; highlight roll-off
above the knee is `knee + (1−knee)·t·(1+s)/(1+s·t)` with `t = (c−knee)/(1−knee)`; the tone curve is a power
S around the pivot (`pivot·(c/pivot)^(1+s)` below, its mirror above); split-tone adds
`strength·(shadow·mask_lo + highlight·mask_hi)` with smoothstep masks on luma around `balance`; black point
is `lift + (1−lift)·c`; saturation scales chroma about luma with vibrance favouring low-saturation pixels,
and the boost is attenuated on skin hues (a Gaussian around hue 25°, width 22°) by `skin_protect`. Clamp
after every step; write 33³ with red varying fastest; validate size 2–64, row count = size³, finite triples,
DOMAIN_MAX > DOMAIN_MIN, no 1D/3D mix (the `hyperframes` cube-validate checks); warn on values outside
[0,1]. Never hand-edit a cube — edit the YAML and rebake, so the LUT and its parameter fallback never
drift (the `color-fx` rule). Keep a hashed manifest (id, genre, cube sha256, drx sha256, compression notes)
and a preview page that renders every cube on one frame for a human to choose from; the pipeline never
auto-picks a look.

### 4b. Spatial tier — the Dehancer dial-in per look

Two nodes on the clip, always in this order: **Node 01 = Resolve primaries**, **Node 02 = Dehancer, last**
— the vendor's own order too (Quick Guide p.4: corrections / masks / colour-space transform → Dehancer
last → sharpen). Dehancer's own wheels and curves stay inside Dehancer. Input = Rec.709, no camera profile.

| look | film / print | halation | bloom | grain | Total Impact | Node 01 primaries |
|---|---|---|---|---|---|---|
| `ads-clean` | Vision3 250D / Kodak 2383 | OFF | OFF | OFF | **35** | gain ≈ 1.02/1.01/1.01, a slight S (pivot 0.46), sat 1.04 |
| `ads-warm` | 250D / 2383 | OFF | light (≤ 0.1) — the glow reads as warmth without a grain cost | OFF | **40** | warm offset (≈ +0.18 temperature), gain 1.04/1.00/0.95, sat 1.06 |
| `film-teal-orange` | 250D / 2383 | on, 35 mm / Super 35 | on | 16 mm ISO 250, amount LOW | **80** | lift −0.026/+0.014/+0.043, gain 1.050/1.020/0.978, contrast 1.15 pivot 0.440, sat 55 |
| `film-portra` | Portra 400 / 2383 | 0.35, 35 mm | light | 16 mm ISO 250, LOW | **75** | gentle warm trims (≈ +0.09 temperature) |
| `film-cinestill` | CineStill 800T if listed, else Vision3 500T / 2383 | **0.9** — the red ring is the point | moderate | 16 mm ISO 250, LOW | **85** | cool cast (≈ −0.14 temperature), blue-lifted lift |

Consensus ranges behind those: halation off or ≤ 0.1 for ads, 0.35–0.5 daylight film, 0.75–1.1 night and
neon; grain off for ads, low and capped for film; Total Impact 30–50 ads, 70–90 film with the grain amount
pulled down independently. **Total Impact is Dehancer's global strength and it includes the geometric
effects** (Quick Guide p.52), which is why the film recipes set grain amount separately.

What the controls are, from Dehancer's manual: grain has an **Analogue** mode (slow, lifelike) and a
**Noise** mode (fast, dithering-like), it lowers contrast so re-expand after it, and its profiles are
8/16/35/65 mm × ISO 50/250/500 (we use 16 mm ISO 250 everywhere); halation has eight profiles (rem-jet and
no-rem-jet stocks), is tuned by the Amplify-max method and works in tandem with Bloom, whose "Save Lights"
control stops highlights clipping. **A major Dehancer version installs as a separate plugin with
incompatible node settings** — pin every `.drx` to the major version it was authored on and never update
the plugin mid-project.

Two UI traps: the **Gain boxes are multipliers around 1.00** (type 1.050, never the delta) and the Lift
boxes are zero-centred; and a `.drx` cannot be inspected by searching it — the OFX parameters are stored
encoded, so a search for `grain` returns nothing on a file that demonstrably carries grain. Verify a look
by rendering it.

## 5. Setting up the grading machine

**Topology.** One Windows workstation with an NVIDIA GPU runs DaVinci Resolve, the Dehancer OFX plugin
and (optionally) Topaz Video AI for the local upscale; the pipeline lives wherever you like — ours is on a
Linux side that reaches the Windows box over a loopback socket — and hands clips across a shared path.
Versions this was verified on: **Resolve Studio 18.5** (the scripting API and `fusionscript.dll` present)
and **Dehancer Pro OFX 7.4** (plugin id `com.dehancer.film_pro.v7`) on an 11 GB GTX 1080 Ti with driver
581.15. Dehancer's Windows requirement is "Resolve 18 and newer" on its website and "19 and later, may work
on earlier" in the 7.4 Setup Guide; it works on 18.5. On 18.5 there is no Graph object in the API
(`GetNodeGraph` arrives in 19); the per-clip grade is applied with `Timeline.ApplyGradeFromDRX(path,
gradeMode, [items])`, gradeMode 0 = no keyframes, and that is the only call the method needs.

### 5a. Installing and configuring Dehancer (from its Setup Guide and Quick Guide)

1. Run the installer with Resolve closed; restart Resolve.
2. Preferences → System → Memory and GPU → GPU processing mode **CUDA**. If the plugin does not appear:
   Preferences → System → Video Plugins → re-enable it → restart. NVIDIA drivers 461, 516 and 522 are
   documented to crash it.
3. **Film and camera profiles are not bundled.** In the plugin, Options → Check Profiles downloads them
   (Internet required once); they cache under `%LOCALAPPDATA%\Dehancer\<plugin id>\LUTs` (about 1,140
   files, 172 MB).
4. Apply a film profile to any clip and render one frame; a render with no watermark means the plugin is
   live.
5. Dehancer has **no API, no CLI and no batch renderer**, and its web app is photo-only. The only
   programmatic path is Resolve's scripting API applying an authored grade — which is the whole method.
   The Resolve plugin sits in the vendor's Photo & Video subscription tier; the LUT Generator needs the
   Pro activation. Cubes exported by the LUT Generator are licensee-only: never commit or publish them.

### 5b. Two ways into Resolve from a script — only one is reliable

1. **External scripting** — `scriptapp("Resolve")` through `fusionscript.dll`, with Preferences → System →
   General → External scripting = Local. A Studio feature. It works for a Resolve the human launched; on
   our box it **refused every instance a script or agent had launched** (headless or GUI, Studio title
   correct, scripting mode on, the TCP port accepting, the handshake returning nothing). Do not read a
   refusal as a licence problem — `Resolve.GetProductName()` answers that question.
2. **The in-app bridge** from `samuelgursky/davinci-resolve-mcp` (MIT) — a script started inside Resolve
   (`Workspace ▸ Scripts ▸ resolve_bridge`) re-exports the live `resolve` object over an HMAC-signed
   loopback socket (default `127.0.0.1:49632`). It does not care who launched Resolve or which edition it
   is (it is how the free edition is driven too). It is **silent by design** — no window, no toast, no
   console line; the only proof it is up is the listener:
   `powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 49632"` → `Listen`, owned by a child
   process rather than `Resolve.exe`. The scripts appear twice in the menu (user and ProgramData copies).

Install the bridge once: clone the repository on the Windows box, create its Python venv, run its
`scripts/install_resolve_bridge.py` (it drops `resolve_bridge.py` into `%APPDATA%\Blackmagic Design\DaVinci
Resolve\Support\Fusion\Scripts\Utility` and the `%PROGRAMDATA%` twin, a runtime under `Fusion\`, and a
config with the port, the HMAC token, the media roots your clips live under and the output roots). The
same repository is an MCP server, useful for ad-hoc control from an agent. **Every session:** the human
launches Resolve, opens a project, clicks the bridge script; the pass then connects deterministically
(three 5-second renders in 32 s cold, 13 s warm, measured). Never have a script launch Resolve for a job
that needs the GUI project open. The pass should try external scripting first and fall through to the
bridge, polling for up to a minute (Resolve takes ~40 s to boot and answers only once a project manager is
up).

### 5c. Authoring a look and exporting the `.drx` — once per look, by hand

Authoring cannot be scripted: the Resolve API cannot write OFX parameters, and it cannot even list the
installed OFX plugins. So each look is a one-time manual dial-in, and the exported grade is applied
unattended forever.

1. Open a project on a clip representative of the footage class — an upscaled mezzanine of an
   AI-generated take, never a camera plate. Color page.
2. Node 01: the primaries from §4b. Node 02: **Dehancer**; Input Rec.709, no camera profile; film and
   print stock; halation, bloom, grain and Total Impact from the table.
3. Judge on the full-resolution frame **and** on 1:1 crops of a backlit highlight (halation reads as a
   warm-red bleed around it) and of a flat area (grain reads as texture).
4. **Export.** Gallery → grab a still of the graded clip → right-click the still → Export → name it
   `<look>_<version>` → choose a folder. Resolve writes **two files**: `<name>.dpx` — the still itself, a
   preview picture — and **`<name>.drx`**, which is the grade. The `.drx` is a `Gallery::GyStill` XML of
   about 44 KB whose clip-level `<Body>` is a zstd-compressed blob holding the node graph, the primaries
   and the Dehancer node with its parameters (decompressed, ours carries the plugin id, a grain profile
   selector such as `16mm250`, the bloom and grain amounts and so on); a second, empty `<Body>` is the
   timeline-level grade; the thumbnail buffers are preview data. The DPX is for the eye; the `.drx` is
   what the pipeline consumes. Keep the versioned master where you exported it and copy the `.drx` into
   the look library; rehash the manifest.
5. **Smoke it on a fresh clip** — one that never carried the authored graph, so the node count goes
   1 → 2 — with the script below, and require the apply call to return true and the item's `GetNumNodes()`
   to be ≥ 2. That proves the grade landed, **not** that the physics came with it: repeat step 3's 1:1
   crops on the rendered output. Our first live use of `film-cinestill` verified halation (warm-red bleed
   on a backlit highlight) and grain (texture across flat mist and a dark truck body) that way; the
   high-frequency energy number rose only 26% because the grain is deliberately low, so the number alone
   is not evidence.
6. An instrument beside the eye, if you want one: ffmpeg `signalstats` on the same frame before and
   after the first look showed YMIN 11 → 22 (lifted blacks), YMAX 241 → 224 (rolled highlights), average
   saturation 13.4 → 9.6, and Laplacian high-frequency energy 1.2 → 5.3 (the 16 mm grain).

`ApplyGradeFromDRX` **replaces** the target node graph; it never appends. Author the whole look in the
still. The OFX node survives export and apply byte-faithfully because the grade body is carried as an
opaque blob — documented in `samuelgursky/davinci-resolve-mcp`'s grade-transfer code and in the
Blackmagic forum workaround for un-scriptable OFX (a Gallery still's `.drx` stores the full node graph
including the OFX node).

## 6. Applying the looks unattended

### 6a. The hero pass — Resolve + Dehancer, per clip

The loop, in the public scripting API (Python; the shipped implementation, `tools/resolve-pass/resolve_pass.py`, adds path
translation, a transport ladder and JSON results):

```python
resolve = connect()                                   # scriptapp("Resolve") or the bridge client, whichever answers
pm = resolve.GetProjectManager(); pm.SaveProject()   # never lose the human's open project
proj = pm.LoadProject("hero-pass") or pm.CreateProject("hero-pass")      # idempotent open
mp, ms = proj.GetMediaPool(), resolve.GetMediaStorage()

fmts = proj.GetRenderFormats()                        # {"QuickTime": "mov", "MP4": "mp4", ...}
codecs = proj.GetRenderCodecs("mov")                  # by EXTENSION — by display key it returns {} for most formats
codec = next(v for k, v in codecs.items() if "DNxHR HQX" in k)
assert proj.SetCurrentRenderFormatAndCodec("mov", codec)      # also takes the extension

for clip in clips:
    item = find_in_pool(mp.GetRootFolder(), clip)     # AddItemListToMediaPool returns [] for a path the pool already holds
    if item is None:
        item = (ms.AddItemListToMediaPool([clip]) or [None])[0]
    w, h = item.GetClipProperty("Resolution").split("x")
    proj.SetSetting("timelineResolutionWidth", w); proj.SetSetting("timelineResolutionHeight", h)
    proj.SetSetting("timelineFrameRate", str(item.GetClipProperty("FPS")))
    tl = mp.CreateTimelineFromClips(f"{stem(clip)}__{look}_{int(time.time())}", [item])   # fresh name every time
    items = tl.GetItemListInTrack("video", 1)
    assert tl.ApplyGradeFromDRX(drx_path, 0, items)   # 0 = no keyframes; REPLACES the node graph
    nodes = items[0].GetNumNodes()                    # expect 2 (primaries + Dehancer)
    while proj.IsRenderingInProgress(): time.sleep(2) # one job at a time
    proj.SetRenderSettings({"SelectAllFrames": True, "TargetDir": out_dir,
                            "CustomName": f"{stem(clip)}__{look}", "ExportVideo": True, "ExportAudio": True})
    job = proj.AddRenderJob(); proj.StartRendering([job])
    while proj.IsRenderingInProgress(): time.sleep(3)
    status = proj.GetRenderJobStatus(job)             # "Complete", plus TimeTakenToRenderInMs
```

Output: `<clip>__<look>.mov`, DNxHR HQX 10-bit 4:2:2, at the mezzanine's own resolution and rate; about
7 s of render per 7-second 2160×3840 clip, 228 s for an 89-second 3416×1920 piece.

Codec facts that are not what the UI suggests (measured on Studio 18.5):
- `GetRenderCodecs()` and `SetCurrentRenderFormatAndCodec()` take the format's **extension** (`mov`),
  never its display key (`QuickTime`). Asked by key they return nothing for most formats — which looks
  exactly like a licence-gated free edition and is not.
- The default render is MP4 H.264 **8-bit**. A graded mezzanine that still has to survive a downscale
  must be 10-bit 4:2:2. **Preference order: ProRes 422 HQ in `mov`** (10-bit 4:2:2, no macroblock
  padding, decodable everywhere) **→ DNxHR HQX in `mov`** (the same class; use it when the install lists
  ProRes but refuses to set it, which ours did) **→ GoPro CineForm 10-bit in `avi` only as a last resort**,
  because it **pads the width to a multiple of 16** — 3416 → 3424, on the right — and the deliver step
  then has to crop (`crop=3416:1920:0:0`; the pad side was measured by PSNR against an unpadded render,
  26.4 dB cropping at x=0 vs 22.3 dB at x=8).
- **Probe every mezzanine for `yuv422p10le`.** A request for 10 bits can succeed and quietly give 8.
- Fresh timeline names per render; one render job at a time.

### 6b. The colour tier everywhere else — ffmpeg

```
# full strength, on a 16-bit planar frame with tetrahedral interpolation
-vf "format=gbrp16le,lut3d=file=looks/film-cinestill_33.cube:interp=tetrahedral"
# at a blend (here 0.85): mix the graded and ungraded frames
-filter_complex "[0:v]split[a][b];[b]lut3d=file=looks/film-cinestill_33.cube:interp=tetrahedral[g];[a][g]mix=inputs=2:weights='0.15 0.85'"
```

Write the graded mezzanine at 10 bits (`-pix_fmt yuv420p10le` or a 4:2:2 intermediate) — smooth AI
gradients (mist, sky, walls) band at 8 bits, and grain would then be added to an already-quantised image.
In an edit that mixes hero-pass shots with designed graphics, the hero shots arrive pre-graded (mark them
"no look") and the graphics take the cube.

### 6c. The upscale in front of the grade — chosen per shot

- **Local Topaz Rhea ×4 by default.** Topaz Video AI (6.x on our box) exposes its models through its
  bundled ffmpeg (`tvai_up`) after `login`; Rhea is a reconstructive model that runs on a Pascal card.
  Free, slow (5.5 s per 3416×1920 frame, 7.3 s per portrait frame on an 11 GB card, VRAM at 92%), and
  the cleanest arm for commercial work (18–24% less flat-area noise than Starlight, least flicker). Run
  it detached with a timeout longer than the job; a truncated mezzanine silently shortens the deliverable,
  so treat a missing completion sentinel as failure.
- **Starlight Precise 2.6 ×4 (hosted, per second of output)** from the **original take**, for any shot
  whose faces sit too small for the generator to have drawn them (a head under ~50 px tall in a 480×854
  take, i.e. any full-body wide) or whose text must read. Measured on two wides of one ad: the faces'
  edge energy rose two to five times over Rhea, glasses and hair became objects, and the file grew 18% at
  the same CRF because there was now something to encode; about $2.60 for 2 × 5 s at ×4. Starlight does
  not stack on Rhea; both start from the take. Check identity across cuts (a small face is reconstructed
  plausibly, not faithfully) and invented small text (a door sign grew fake lettering). Chest-up and
  closer, Rhea holds.
- Whichever arm, **do not post-scale in the upscale pass**: upscale to the mezzanine, grade there, and
  let the deliver step downscale — that is what keeps the grain.

### 6d. Which codec at each stage — the ladder to follow

Every stage before delivery is written at **10-bit 4:2:2 or better**; 4:2:0 and 8 bits appear only in
the deliverable. The reason is the same at every rung: the next stage (an upscaler, a grade, a downscale,
a grain pass) works on what the previous one kept, and chroma and bit depth lost early cannot be recovered
by anything downstream. Saturation pushes, skin secondaries and smooth AI gradients show the loss first.

| stage | write it as | why | acceptable fallback |
|---|---|---|---|
| the locked edit, flattened before the upscale | ProRes 422 HQ or DNxHR HQX (10/12-bit 4:2:2) at the edit's native resolution; audio as PCM | the upscaler rebuilds from this; a lossy or 8-bit flatten hands it banding and chroma blocks to "enhance" | ProRes 4444 / DNxHR 444 if any layer carries alpha or the material is very saturated |
| the upscale output (mezzanine) | ProRes 422 HQ (`-c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le`) — Topaz's bundled ffmpeg has `prores_ks` and `dnxhd` | keeps 4:2:2 through the grade; the encode is trivial next to the upscale itself | 10-bit HEVC through NVENC (`p010le`) is 4:2:0 and about a fifth the size — take it only when disk is the constraint; that is what our first music video shipped with, and it is the one compromise recorded against the local route |
| the graded mezzanine (the Resolve render) | ProRes 422 HQ in `mov`; DNxHR HQX in `mov` where ProRes is refused | 10-bit 4:2:2, no padding, universal | CineForm 10-bit in `avi`, with the width crop |
| the master (composite, mixed audio) | ProRes 422 HQ at the mezzanine raster, PCM audio | one lossless-class generation between the grade and every deliverable | — |
| deliverables | H.264 High 4:2:0 8-bit from the master, one encode each | what the platforms accept; 10-bit H.264 breaks playback on some clients | H.265/AV1 only where inline playback is known to work |

Two edit-side rules that belong with the ladder: **flatten at the highest native resolution any take
carries, or upscale the takes individually and conform afterwards** — flattening a 1344×768 take into an
854×480 timeline threw its native detail away before the upscaler ever saw it; and **check three or four
frames after every cut in the upscaled file**, because temporal upscalers smear across cut boundaries and a
cut-dense edit gives them many chances.

## 7. The two finishing recipes that shipped

### Commercial — seven 9:16 social ads, 1080×1920

- upscale: local Rhea ×4 on every take; Starlight ×4 on two wides of one spot
- grade: `ads-clean.drx` hero pass → 10-bit 4:2:2 heroes (ProRes 422 HQ where the install writes it,
  DNxHR HQX where it does not — ours) → cut → ProRes 422 HQ 2160×3840 master (probe it for `yuv422p10le`)
- grain: none — social-class delivery; the platform re-encode discards it anyway
- deliver: `scale=1080:1920`, captions overlaid **after** the downscale, libx264 preset slow, CRF 17,
  `-tune film`, High 4.1, GOP 48, AAC 192 k, faststart; audio two-pass `loudnorm` to −14 LUFS with a
  −2.4 dBTP target, then `aresample=48000`, **then** a limiter — a limiter placed before the resample
  re-grows the peaks it just capped (measured −0.2 dBTP on a hard transient, −2.2 after the reorder)
- result: 8–10 Mbps, inside every platform's limits (X accepts up to 25 Mbps and advises under 30 MB;
  YouTube's reference is 8 Mbps at 1080p; TikTok's reservation floor is 2.5 Mbps; Meta wants a fixed frame
  rate and a closed GOP of 2–5 s; all want H.264 4:2:0 with BT.709 tags, AAC ≥ 128 kbps at 48 kHz, the
  moov atom first and no edit lists)

The stricter platform-contract encode, if the deliverable must clear every ad platform's validator:
CRF 19 with a 12 M/24 M VBV cap, closed 2 s GOP (48 frames at 24 fps), 2 B-frames, `-color_primaries
bt709 -color_trc bt709 -colorspace bt709 -color_range tv`, AAC 48 kHz, `-movflags
+faststart+negative_cts_offsets -use_editlist 0` (ffmpeg writes one edit list per track by default),
with the AAC encoder priming pre-trimmed by exactly 1024 samples (`aresample=48000,atrim=start_sample=1024,
asetpts=PTS-STARTPTS`) so the file is sample-accurate without an edit list; remux the draft's original
audio if a hosted upscaler re-encoded it (fal's Topaz leg degrades audio to 128 kbps). Measured: 4.96
Mbps at 1080p, 8.35 at 1440p.

### Film — an 89-second 16:9 music video

- source: flatten the locked edit to a 10/12-bit 4:2:2 intermediate at its native resolution with PCM
  audio (ours: DNxHR HQX 854×480, `yuv422p12le`); never an H.264 export, and never below the highest
  native resolution any take carries (§6d)
- upscale: local Rhea ×4 to 3416×1920. Write it as ProRes 422 HQ to keep the 4:2:2 chroma; we shipped
  HEVC 10-bit 4:2:0 through NVENC for size (216 MB for 89 s) and that is the one place the chain lost
  something — 135 minutes on an 11 GB card either way
- look: chosen from four rendered candidates on the widest-tonal-range frame → `film-cinestill`
- grade: the hero pass. Render it as ProRes 422 HQ in `mov` (or DNxHR HQX where ProRes is refused); we
  shipped CineForm 10-bit `avi`, which pads and had to be cropped on delivery, before the codec-by-extension
  fact was found. 227.6 s for 2145 frames. One Resolve pass delivered colour + stock + halation 0.9 + bloom
  + grain together, so **no separate grain pass** (adding one would have doubled it). Resolve wrote the
  audio out as PCM 16/48 and that copy rode through — re-laying the raw music would have replaced a mix the
  NLE had processed (sample-accurate correlation 0.146 against a self-test of 1.0)
- deliver, every variant from the mezzanine and never from another deliverable:
  `crop=3416:1920:0:0 → scale=2560:1440:flags=lanczos → overlay watermark → format=yuv420p`, libx264 medium
  CRF 16, maxrate 40 M, bufsize 80 M, High 5.1, BT.709 tags, `sws_dither=ed`, AAC 320 k → ~33 Mbps. 1440p
  rather than 1080p so YouTube's VP9/AV1 tier carries the grain even for viewers watching at 1080. The
  watermark is cropped to its opaque bounding box first (exported logos sit inside a larger transparent
  canvas, which pushes the mark away from the corner) and overlaid after the downscale, scaled as a
  constant fraction of frame width per variant
- the hard-cap chat cut: derive the bitrate from the cap (`video_kbps = cap_bytes × 8 / duration_s /
  1000 − audio_kbps − ~0.5%`, targeted ~6% under the stated cap because "50 MB" may mean 50,000,000 or
  52,428,800 bytes), two-pass at that explicit bitrate — never CRF — with `-tune film` (lowers deblocking
  so a capped encoder does not smear grain; `-tune grain` spends bitrate the cap does not have), H.264 for
  inline playback, AAC 128 k. Landed within 0.4% of prediction on the first run; grain visibly survived.

## 8. Gates before a look ships

1. **Darkest-skin check** on every film look: shadow-deepening looks (bleach, noir, heavy teal-orange)
   crush the darkest-skinned subject in frame; keep skin protection high on clean looks.
2. **Grain A/B through the real social encode** — the grain decision is bitrate-dependent, not aesthetic.
3. **VMAF ≥ 93 at 1080p**, graded-compressed against graded-master (needs an ffmpeg built with libvmaf).
4. Sharpen light and only after the grade; the upscaler already invented micro-detail.
5. Probe the mezzanine for 10 bits; verify the true peak and the grade on the **delivered** file, at
   zoom, at several timecodes, over light and dark backgrounds — never the first frame alone. Every
   comparison carries a known-answer case in the same invocation (a file against itself must return
   `inf`): `ffmpeg -v error` suppresses the PSNR summary line, and an empty result reads as "identical".

## 9. Sources — the repositories and documents each part came from

Eleven open-source repositories were read in full for the look library (none is vendored; each was a
pattern source), plus the Resolve and Topaz automation donors and the vendor documents.

| source | what the method takes from it |
|---|---|
| [0xBeycan/postfx](https://github.com/0xBeycan/postfx) (MIT) | the primary colour consensus: 15 signature looks with full per-parameter values, genre-explicit (`13_clean_commercial` → `ads-clean`, `09_cinematic_teal_orange`, `14_golden_warm` → `ads-warm`, `01_portra_400`, `05_cinestill_800t`); the YAML parameter vocabulary |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) (Apache-2.0) | the manifest schema (`skills/media-use/luts/index.json`: a looks[] list, hashed cubes, a deterministic `buildCube(params)` fallback, `cube-validate`); the Rec.709 luma and smoothstep masks in the baker; 17 preset ids |
| [jeremieLouvaert/ComfyUI-Darkroom](https://github.com/jeremieLouvaert/ComfyUI-Darkroom) (MIT) | the two-tier bake rule (only per-pixel colour bakes into a LUT), the halation / grain / bloom physics defaults (`nodes/halation.py` red-orange TIR ring; `film_grain.py` ISO 400 / 0.5 / colour 0.3), and the 35 pre-baked spectral negative×print cubes (`data/spectral_luts/`) the film looks start from |
| [JanLohse/spectral_film_lut](https://github.com/JanLohse/spectral_film_lut) (MIT) | the datasheet-to-cube film-emulation baker Darkroom vendors; the internal order (halation before the negative LUT, grain independent of stock and sized by frame) |
| [tomastimelock/color-fx](https://github.com/tomastimelock/color-fx) (MIT) | `bake_grade_to_lut`: bake from named parameters so the LUT and the fallback never drift; skin-tone protection; tetrahedral interpolation |
| [0xdarkmatter/claude-mods](https://github.com/0xdarkmatter/claude-mods) — the `ffmpeg-ops` skill | the compression discipline: the 33³ sweet spot, the grade order (denoise → normalise → grade → sharpen → encode), a 10-bit mezzanine for banding-prone gradients, the VMAF gate, the skin-tone warning on shadow-deepening looks, a variant-and-chooser preview |
| [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) (AGPL-3.0; reference only) | seven ffmpeg-native colour profiles with `lut3d` last — the deliver-step form of a look |
| [nobphotographr/davinci-resolve-automation](https://github.com/nobphotographr/davinci-resolve-automation) (MIT) | eight CDL looks with genre labels (documentary, music video, commercial, arri, kodak5219, …) — the ads-versus-film split in numbers; DRX-template and `SetLUT` patterns |
| [0xsline/OpenChatCut](https://github.com/0xsline/OpenChatCut) (AGPL-3.0; reference only) | a WebGL look registry with intensity / contrast / grain defaults per look |
| [praey54/resolve-cli](https://github.com/praey54/resolve-cli) (MIT) | the Resolve CLI contract (JSON results, exit codes, headless `-nogui`) |
| [mhadifilms/dvr](https://github.com/mhadifilms/dvr) (MIT) | idempotent Resolve-API robustness (`ensure()`, decoded errors, reconcile) — the project-open pattern |
| [samuelgursky/davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp) (MIT) | **adopted as-is**: the in-app bridge and the transport ladder, the MCP server, the granular apply and busy-guard patterns, the delivery-target projection idea, and the documented semantics — OFX parameters cannot be written but a grade carrying an OFX node transfers byte-faithfully; `ApplyGradeFromDRX` replaces the graph |
| `sh570655308/ComfyUI-TopazVideoAI`, `topyaz`, calesthio's `topaz-video-enhancement` skill | the `tvai_up` ffmpeg invocation, model discovery, the licence probe and encoder ladder behind a local Topaz wrapper; a model-selection rubric |
| Dehancer Ltd — *DaVinci OFX Setup Guide* (17 pp, 2025-01) and *Quick Guide* (55 pp, 2024-04), the system-requirements page, the ToS | node order, Clip / Timeline / Adjustment-clip application modes, Input Rec.709 for display-referred sources, the LUT Generator's exclusions, the grain Analogue/Noise modes and the mm×ISO profiles, the halation profiles and Bloom "Save Lights", Total Impact, the major-version pinning rule, the profile download, the no-API fact |
| Blackmagic — the Resolve 18.5 scripting README; Blackmagic forum thread t=84645 | the `Timeline.ApplyGradeFromDRX(path, gradeMode, items)` form on 18.5 and the workaround that a Gallery still's `.drx` stores the full node graph including OFX |
| the Banodoco community (Aug 2026) and an X thread by @godswayfoundinc (2026-08-27) | the 480p → reconstruct → Dehancer thesis; the field verdicts that put Starlight Precise 2.6 above HQ, Mini and Fast 2; the shadow-grain observation; the "detailer composite" idea (Starlight at the same size, 90% over the original, background masked) as an optional manual refinement |

## 10. The short list of things that bite

- Dehancer Input must be Rec.709 on AI footage; a log input is the commonest mistake.
- The `.drx` replaces the node graph on apply; author the whole look in the still.
- Node 01 primaries live in Resolve; Dehancer's wheels stay inside Dehancer. Gain boxes are multipliers,
  Lift boxes are zero-centred.
- A `.drx` cannot be inspected by text search. Render it and look, at 1:1, on a fresh clip.
- A `.drx` is pinned to its Dehancer major version; a major update installs as a different plugin and the
  presets stop matching.
- Resolve may refuse external scripting from any instance a script launched; the human launches it and
  clicks the bridge, which is silent — check the port.
- Render codecs are addressed by extension, not display name; ProRes may be listed and refused; CineForm
  pads width; probe for 10-bit rather than trusting a codec name.
- One render job at a time; fresh timeline names; a re-imported path returns an empty list.
- Grade after the upscale; grain only from a mezzanine above delivery resolution; never a second grain
  pass on top of a film `.drx`.
- The upscale tier is per shot: Rhea by default, Starlight from the take for distant faces and text.
- Check what the grade pass emitted for audio before sourcing audio from anywhere else.
- Never publish a Dehancer-generated `.cube`; cubes baked from MIT spectral bases and your own parameters
  are yours.
- Every intermediate is 10-bit 4:2:2 or better — ProRes 422 HQ first, DNxHR HQX second; 4:2:0 and
  8 bits only in the deliverable; flatten at the highest native resolution any take carries.
- Verify on the delivered file, at zoom, at several timecodes, with a known-answer check in the same
  invocation.
