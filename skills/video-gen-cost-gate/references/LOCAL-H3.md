# Local MiniMax H3 — the recipe, once this venue is chosen

Read this only after `VENUES.md` puts the shot on the local lane. Everything here is measured on one
24 GB Ampere box; the numbers are what that class of card does, not a vendor claim.

## The recipe

```
trunk    a Ref2VA pruned int8 FINETUNE (not the stock pruned trunk — see "trunk choice")
LoRA     the 4-step ref2v turbo distill @ 1.0
sampling 4 steps · euler · simple · CFG 1 · SigmaShift 12/3 (video:audio ≈ 4:1 — move both or neither)
attention  the framework's fast attention backend  +  block-sparse (sol) τ 1.3, start_percent 0.2
refs     the angle still + the identity still; a SMALL proxy clip if the shot has a move
prompt   the H3 schema, with every clause about an input the graph does not carry deleted (L31)
```

→ **≈ 120 s for a 5 s take at 768×1344 ×124 f**, still-lock 0.996 against the plate, camera hold
inside 3 on every edge. Peak VRAM 23.9 GB of 24 — this recipe fills the card, so nothing else may hold
VRAM while it runs.

**For a higher-resolution master:** a ×2 tiled latent-upscale second pass on the *light* refine
schedule → 1088×1920, lock intact, ≈ 410 s all in. Never the strong schedule: measured worse on every
axis — temporal stability 47.9 vs 51.8 dB with a 26 dB single-frame jump, edges 14 vs 3, and it ends
up *softer* (detail 298 vs 319) despite doing more denoising work. A no-turbo 20-step base under the same light
refine gives a sharper master (face detail +9.5–13 %) at 1.9× the time (§ "Why posted H3 looks better").

**The ×2 pass keeps the audio bit-identical and RE-ANIMATES the mouth** (2026-09-19). On a speaking take its
mouth motion was uncorrelated with pass 1's (−0.03); on a silent take a barely parted mouth came back open
(mouth-open ratio 0.21 → 0.67). The 544→768 refine closed one instead (0.23 → 0.08); the LMS pass kept it
(0.21 → 0.23). By eye the ×2 lip sync read BETTER than pass 1's, because the mouth is legible at 1088 — but it
is the refine's articulation over pass 1's audio, so review lip sync on the ×2 master itself, never infer it
from pass 1 (n = 1 speaking take). Hivemind: pushing the denoise "can and will hurt lip sync". The shift pair
in the recipe stays near 4:1 for the same joint-stream reason: an upstream long-video node documents that the
audio breaks otherwise (not measured here), and no frame instrument would see it.

**Pinning the soundtrack to digital silence** — a `MiniMaxH3AddGuide` carrying only an audio input of silence
at frame 0 — returns a silent track (invented sound 2 of 6 → 0 of 6) and a calmer mouth later in the take
(median ratio 0.112 → 0.069), for −0.01 of frame-0 plate match on 6 of 6 seeds (2026-09-19). It does NOT stop
the first-second mouth flap; the start still does (`video-prompt-dialects` DIALECTS § MiniMax H3). Reach for it
where the native audio is discarded and a still mouth matters; for the audio alone, a concrete soundscape does
the same job at no cost.

**For more fine texture, change the TRUNK before you reach for a second pass.** The two trunks differ by
27 % in fine detail on an otherwise identical take, at identical cost. There is also a sharpener LoRA, but
it is a RESTORATION pass — it earns its keep on degraded or external footage and does nothing for a clean
native take: see § "Whether a second pass earns its place".

## Why posted H3 looks better than this recipe — the recipe is tuned for SPEED

The recipe above was tuned for time per take (14× end to end, § "The four config rules"); quality was held only
where it was measured. The H3 people post that looks far better is bought differently. Community corpus,
2026-09-19 — r/StableDiffusion and the Banodoco Discord, several independent posters per lever. Two of the levers are
measured here (below the table); the rest are the community's claim:

| lever | posted quality work | this recipe |
|---|---|---|
| steps and distill | the reference sampler is 50 flow-matching steps on full weights (AMD's day-0 H3 serving article: Euler-ancestral, `flow_shift` 12 / audio 3). Local quality runs use 16–50 steps with no turbo LoRA, or an 8-step DMD turbo LoRA; the top-voted local showcase dropped turbo LoRAs because they lost detail. 10–65 min per clip | 4 steps on a 4-step turbo LoRA, ~2 min |
| resolution | ~0.98 MP is the trained native, but heavy users call anything under ~2 MP "token-starved": a SECOND pass re-samples at 1.8–2 MP for 3–12 real steps (8 DMD steps at 0.9 MP + 3 at 1.8 MP; 16 at 1 MP + a 6-step de-rope at 2 MP) | 0.98 MP, then the 2-step light refine to 2.09 MP over the 4-step base |
| face size | far and small faces are H3's best-known weakness; showcase work frames medium or close, and a wide gets a Topaz or crop-regenerate-blend face pass | S02's face is ~56 px at 768p — under the review floor (`video-take-review` § 3, faces) |
| sparse window | sol attention kept to 40–90 % of the schedule, "really better" (one report) | sol from 20 % to the end |
| motion | "de-rope", a targeted temporal re-sample, for fast-motion smear | none; S02 barely moves |
| curation | cheap previews per seed, re-renders, the best of many posted | every seed is read |

The operator's eye on the ×2 master (2026-09-19): both passes read low-res, and the ×2 reads better because more
of the mouth is legible — the face-size row, not a sampler setting. **Measured the same day on S02** (local, three
seeds each, the closed-mouth start still and the concrete soundscape):

- **Framing is the big lever.** A 2× punch-in start still cut from the 2K plate (native pixels, the face ~2×) under
  the shipped recipe: face detail at equal size 1.41–1.55× the wide on every seed, at the same compute; the camera
  held the tighter frame, the mouth stayed shut, no invented sound. A silent take — lip sync at the bigger face is
  not measured yet.
- **Compute is a modest lever, and only through the ×2.** No turbo, euler 20 steps, sol on 0.4–0.9, then the same
  ×2 turbo refine: the master gains 9.5–13 % face detail and up to 14 % whole-frame detail, holds the still and the
  camera better and runs steadier, 3 of 3 seeds, for 1.9× the time (~11.5 min a master against ~6). The 768 base
  alone is steadier but SOFTER (face detail lower on 3 of 3) — never judge this lever on pass 1. 50 steps bought
  nothing over 20 at 3.6× the time. The audio stayed clean at 20 and 50 steps without turbo.
- The two are independent (stacking them is not tested yet). When the face carries the beat, frame it large first; add the no-turbo base when the master's
  detail matters and the time is there. Every arm here still got an audio read — the step arm below is why.

## The four config rules, each measured

**1. The CUDA build is the single biggest lever, and it is silent when wrong.** The fast attention
kernels need a current CUDA build of the tensor library; on an older one the framework logs a warning
at startup and everything still runs — 2.1× slower. Build a second virtualenv rather than upgrading
the one other tools depend on, and pin the server to it. Ladder measured on one graph:
220 s/step (stock attention) → 147 (fast backend) → 55 (drop the full-size reference clip) → 25.7
(current CUDA build) → **15.5** (block-sparse on top). **14× end to end.**

⚠ **Before rule 2 — which sparse SELECTION you may use is decided by your WEIGHTS, not by taste.** The
framework offers three block-sparse selections behind one node, and they are not interchangeable:

| selection | what it needs | verdict here |
|---|---|---|
| **`sol-attn`** — adaptive per-head threshold (the one in the recipe) | **nothing; it is training-free** | **use this.** 1.69× with the take unchanged within noise, and our best-locking, only artifact-free run has it on |
| **`sla`** — fixed top-k | weights **distilled against that sparsity pattern**; without one the keep-percent must rise until it converges toward dense and the speed-up disappears | ❌ **MEASURED INERT on our weights.** Same plate-match, same detail to the unit, same audio and the same time as the adaptive selection — a no-op, exactly as the tooltip predicts. **There is no selection decision to make here** |
| **`vsa`** — learned coarse branch, 3D cube tiling | a checkpoint carrying the extra gate layers, which the loader **detects from the state dict** | **not available to us.** Both our trunks carry ZERO such layers, so it runs without its coarse branch — the part worth having |

**This RESOLVES a disagreement this section used to record as open.** The wider community reports a quality
cost for block sparsity while we measure none, and the reason is now legible: the complaint attaches to the
**training-free** selection, while the people reporting sparsity as free are running **top-k with weights
distilled for it**. Both reports are correct about different configurations. The speed figures never
disagreed (1.60× on their hardware against our 1.69×). **There is no like-for-like swap to try** — changing
selection means changing weights.

⚠ **Two layers get conflated constantly, including by experienced users.** The dense attention backend (the
fast quantized one) and the sparse selection are different things, stacked: the selection runs *on top of*
whichever dense backend is active. "Use the fast backend instead of sparse attention" compares across two
layers. Best practice is both at once, which is what the recipe above ships.

**Operationally unchanged:** if a delivered shot looks degraded and sparse attention is on, turn it off and
re-run before looking anywhere else — and never assume the speed-up is free on content unlike ours. One
caveat measured elsewhere and worth carrying: **the saving grows with resolution and token count**, so on a
small grid there may be little to win. Check before you count on it.

**2. Sparse attention must never act from the first evaluation.** Keep the first full denoiser
evaluation dense — `start_percent 0.2` or equivalent. With sparsity from the first sigma-1.0
evaluation an independent controlled same-seed test saw the opening motion take an abrupt
pose/orientation change with heavy smearing before settling into the opposite heading; that project
reverted its own default because of it. Never drop the guard chasing speed.

**3. A guide-latent LoRA runs on the trunk it was trained against, and denoise 1.0 is its regime.**
Both failures are silent. Trained on the stock trunk and applied across a finetune, a sharpener LoRA
drifted identity — the subject's face changed and he gained a tie present in neither the first pass
nor the plate (still-lock 0.983 → 0.928). On its own training trunk, re-measured under one fixed
prompt, **identity held completely**: face, clothing and room intact at 1:1 across both arms, the only
residue a slight framing push-in (0.992 → 0.944). And its card states the target "is noised normally"
in training, so **denoise 1.0 IS the trained setting**: lowering it to 0.5 gave total collapse, frame-0
correlation −0.003, output unrelated to the plate. The obvious fix is the wrong fix.
⚠ **The sting in this rule:** the training trunk is where the pass is SAFE and also where it adds no
detail at all. The detail gain only appears on the finetune — the trunk it drifts on. That is why the
pass is narrow rather than recommended.

**4. Generating at low resolution and upscaling AFTERWARDS loses the plate's grade — but handing off
DURING sampling does not.** A 544×960 base then latent-upscaled to 768 was cheaper than a native take
(161 s vs 170) and the upscaler tracked its input faithfully — but the low-res base rendered its first
≈2.5 s in a cold blue-grey wash before converging on the plate's warm light (still-lock **0.584**).
Framing and cast were locked throughout; only the colour failed. **That sequential route stays disqualified
for any shot that must match a plate.** The failure is the SHAPE, not low resolution itself: a flow-aligned
handoff that rescales mid-sampling holds the grade from frame 0 — § "Starting small and handing off".

## How many steps — 4 stays, and the reason is the AUDIO

**Keep the 4 steps the recipe ships.** A lower count measures better on every video instrument we own and
is still the wrong call, and the way that was caught is the point of this section. More steps without the turbo
LoRA — the community's quality route — measured 2026-09-19: sharper only through the ×2 refine, by ~10 %, at 1.9× the
time, with clean audio (§ "Why posted H3 looks better").

Measured on one box, one prompt, one trunk, a locked static shot, two seeds, everything else identical:

| steps | plate-match | fine detail (whole frame) | face-region detail | worst edge | time | **audio artifact** |
|---|---|---|---|---|---|---|
| **4 (shipped)** | 0.992 | 284 flat | 862 | 2.3 | ~105 s | **0.029 → 0.137** |
| 3 | 0.992 | 292 flat | 886 | 2.6 | 89 s | 0.104 → 0.164, **peak 0.999 with clipping** |
| 2 | 0.988 | 309 flat | 907 | 3.0 | 73 s | 0.109 → 0.204 |

Fewer steps give **more** fine detail — whole-frame and in the face box alike, flat across every sampled
frame, on both seeds. On the second seed the low-step arm also won on plate-match. On video alone it looks
like a free 30 % speed-up with a detail bonus, and it was written up as one.

🔴 **It is not free. The audio stream degrades, and monotonically.** The take's prompt specifies *"the room's
natural quiet; no speech, no music"*, so every number in that last column is artifact energy in a clip that
should be near-silent — **3.6× at three steps, and the three-step arm peaks at 0.999 and clips.** The model
generates audio and video jointly, and the step-distilled LoRAs are distilled on VIDEO. Audio is the stream
that pays for a low step count, and no instrument that reads frames can see it.

⚠ **Measuring a face at all is a trap worth naming.** A stock frontal-face detector returned a confident
false positive on this shot — the subject's trousers and a fireplace tool-set — and returned the SAME wrong
box on every arm, so reusing "the detected box" across arms reproduced the error and looked like agreement.
An earlier version of the face column here carried those wrong-region numbers. **Reject any face found
outside the upper third of a standing-subject frame, and confirm the box by eye once before citing anything
measured in it** — a detector that fails consistently is indistinguishable from one that works.

**The generalisable rule: a video-only measurement cannot clear a joint audio-video model.** Any change to
steps, sampler, schedule or sparsity gets an audio arm — per-second RMS against what the prompt actually
asked for, plus peak and clipping — before it is called an improvement.

⚠ **The community says the same thing from the other side, and it is worth more than our two seeds.** Users
report going UP rather than down ("increasing to 10 or 12 steps helps quality"), one reports three steps
costing face detail on a character LoRA and reverting to four, and the early steps are held to carry the
structure — *"if the initial 3 steps are dumb, everything will just be dumb."* Every two- and three-step
usage found in either corpus is a **second pass after a longer first pass**, never the primary pass, and one
of those reports names the same failure we measured: at a low second-pass step count *"the audio will be
rather bad."*

**So the low-step arms are a measured LEAD for video-only work — a silent shot, a plate, a proxy for
timing — and not the recipe.** If you take one, listen to the result.

⚠ **A community recommendation that did NOT survive contact here, recorded so it is not retried:** several
independent reports prefer a different sampler (`res_multistep`) over the plain one. At our step count it
cost **13 % of the detail (284 → 247)** and pushed the camera hold past the threshold, for no speed or
plate-match gain. Those reports run a different reference lineage at 8–20 steps with different turbo LoRAs,
and **a step-distilled LoRA and a sampler trajectory are calibrated against each other** — one of those
posters says exactly that. At 2 steps the two samplers produce an identical take, because a linear multistep
method has no history to use on its first step. **The sampler was never the variable.**

**And when a detail gain looks too good, test whether it is texture at all.** Laplacian variance cannot
separate fine texture from a lifted noise floor, and flat-across-frames does not separate them either (noise
is flat too). High-pass each frame and correlate adjacent frames: real texture sits in the same places frame
after frame, sampling noise reshuffles. Here persistence was identical across every arm (0.980–0.981) while
the low-step arm carried 6 % more high-frequency energy — so that gain WAS real structure. It still lost, on
the axis nobody had measured.

⏱ **Discard the first job of a session when timing.** The same configuration ran 121.7 s cold and 104.6 s
warm — a 14 % difference, briefly mis-read as a sampler speed-up.

## Trunk choice

A finetune and the stock pruned trunk cost the same per step, so choose on behaviour. Measured on one
shot: the finetune held the plate slightly better (0.996 vs 0.986) and — the larger difference — drew
a prompt-induced artifact far more weakly, where the stock trunk escalated the same artifact into
full wireframe outlines over the cast — but that artifact was 100 % the prompt, and once the offending
clause goes, both trunks render clean. **On clean prompts the stock trunk carries 27 % more fine detail
(284 vs 223, flat across the take) for 0.004 of plate-match, at the same price** — which makes the trunk,
not any second pass, the fine-detail lever. The stock trunk is also the one community LoRAs are trained
against, so any guide-latent LoRA pass belongs on it (rule 3).

### A third trunk: the distill BAKED IN — 1.4-1.8× the detail, and an audio gate

The same reference lineage is also published with the 4-step distill **merged into the weights** instead of
loaded as a LoRA. Community report: *"a model that has turbo pre-merged works better for me than the base
with external turbo lora."* Measured against our own base + LoRA on four seeds, everything else identical:

| | plate-match | whole-frame detail | face detail | face adherence to the reference | camera hold | time |
|---|---|---|---|---|---|---|
| base + LoRA | 0.992 · 0.976 · 0.971 · 0.975 | 284 · 274 · 276 · 269 | 862-925 | — | held on 4/4 | ~105 s |
| **baked** | 0.968 · 0.976 · 0.966 · 0.979 | **528 · 412 · 435 · 470** | **1137-1379** | **−0.013 mean** | held on **3/4** | ~106 s |

**+50 % to +86 % fine detail on every seed and 1.42× on the face, at the same price**, flat across frames and
confirmed as texture rather than noise by the persistence test. Visibly better eyes, hair and collar at 1:1,
and the same person.

🔴 **The cost is the AUDIO, and it is why this is not the default.** On a take whose prompt asks for quiet,
the baked trunk put spurious audio in **2 of 4 seeds** against the LoRA route's 1 of 4 — one of them **225×**
its own baseline, another **clipping at full scale**. One seed in four also broke the camera hold outright.
Both failures cluster on the same hard seed, so the bake reads as an amplifier of what a seed is already
doing rather than a defect of its own.

**So: an OPTION with a per-take gate, not a trunk swap.** Take it wherever the **native audio is discarded
anyway** — a shot getting voice-over, designed sfx and a music bed over muted native sound — where the only
measured cost does not exist and the detail is free. Everywhere else, check the audio and the camera hold on
the take before it goes forward.

⚠ A baked distill has **no strength dial**. We run it at full strength, so nothing is lost today; it removes
headroom rather than capability.

⚠ **The community's stated objection did NOT reproduce.** Experienced reference users warn that merged trunks
*"don't follow references as closely as the originals"* — measured against the reference still, face adherence
moved −0.050, −0.016, **+0.002, +0.011** across four seeds: noise around zero. Their warning is most likely
about fused HYBRIDS of several different models; a pure bake of one lineage is a different object. **The audio
cost, conversely, has no community footprint at all — it is ours, and it decided the verdict.**

### A second detail option: the SLA-distilled turbo LoRA — and a warning about swapping turbo LoRAs at all

**The turbo LoRA is a far bigger lever than the sparse selection**, and one distilled cut of it buys detail:
**+29 % to +47 % fine detail on four seeds out of four**, plate-match **neutral** (−0.014, +0.018, +0.004,
+0.002 → mean **+0.003**) with one arm reading **0.994**, the best figure recorded on this shot. Same time.

**It carries the same kind of cost as the baked trunk, and it is again the audio.** On a take prompted for
quiet, 2 of 4 seeds elevated speech-band energy and **1 of 4 crossed into speech-like** — against a baseline
that produced speech-like audio on **none** of the four. One seed in four also degraded the camera hold past
the ≤ 3 line, and face adherence to the reference fell 0.037 on the seed measured for it.

🔴 **A turbo LoRA is NOT a drop-in part — verify one before you trust it.** A different turbo LoRA of the same
lineage, tried as a control, produced **plate-match 0.373** with an edge drifting at 9.8: reframed camera,
cast rearranged, take unusable. **The lineage was not the cause — the working one shares it.** Swap a turbo
LoRA only with a plate-match check on its first take. The failure is total rather than subtle, so the check
is cheap and decisive.

**Ordering, for a shot whose native audio is discarded anyway** (voice-over, designed sfx and a bed over muted
native sound): **baked trunk > SLA-distilled LoRA > the shipped LoRA** on detail, and the only measured cost
of either does not exist there. Everywhere else both stay behind the per-take gate.

## Starting small and handing off — faster AND sharper than a native take

Generate at a small grid, then rescale the model to the target grid PART-WAY THROUGH sampling under
flow-aligned guidance, instead of finishing small and upscaling afterwards. Measured on one box, same
trunk, prompt, attention and 4-step turbo schedule, every output 768×1344×124:

| route | plate-match | fine detail | time |
|---|---|---|---|
| native at the target grid | **0.992** | 284 flat | ~145 s |
| small grid → upscale AFTER sampling (rule 4) | 0.584 | — | 161 s |
| **small grid → handoff DURING sampling** | **0.974** · 0.964 | **350** · 337 flat | **93 s** |

**Three wins at once: the grade collapse is gone (0.584 → 0.974), it is 36 % faster than a native take, and
it carries 19–23 % MORE fine detail** — flat across every sampled frame, the signature of real texture
rather than the artifact spike the sequential route produced. Cost is ≈ 0.02 of plate-match, a quarter of
what the sharpener charges for less detail. Two seeds, including the seed that FAILED on the sequential
route.

**The recipe:** build the conditioning and the starting latent at the SOURCE grid (544×960 → 768×1344, a
1.41× step), wrap the model in the progressive-handoff node with the target given in pixels, hand off at
**0.35** of the schedule with direction guidance at weight 0.25, and **keep the 4-step turbo schedule** —
the reference workflow drops turbo for a 19-step multistep sampler and that is not necessary. The handoff
nodes wrap `MODEL` generically, so they need no trunk of their own: ours ran on the same reference trunk and
conditioning as every other route here.

⚠ **Provenance, stated plainly: this is OUR measurement, not a community practice.** A recency-floored sweep
of the largest open video-model community found **zero** discussion of flow-aligned handoff, and neither the
technique nor its author's pack appears among the repos being adopted. What that community uses for low→high
is sequential: latent upscaling (its own favourite), a fast no-resample enhancer, or pixel upscaling. Treat
this as a measured lead worth taking on a box you control, not a settled default, and re-measure before
relying on it for anything delivered.

⚠ Needs a third-party node pack (the flow-trajectory / progressive-handoff pair). The parameters above are
the only ones measured, and the handoff coordinate is untuned.

## Whether a second pass earns its place

**Two different passes, two different answers.** Take the tiled latent upscale by default; take the
sharpener LoRA only for the shots named below.

**The tiled latent upscale — default yes.** ≈3.5× a plain take, keeps the plate-match, and the *light*
refine schedule beats the strong one on every measure. This is the pass you reach for when you want a
bigger master.

**The sharpener LoRA is a RESTORATION pass. Its gain is a function of how degraded the GUIDE is, not of
anything else you can set.** Its author calls it "a little more sharpness" and says it "sharpens a source
video"; the demo clips are compressed, soft footage. Measured on one seed, one prompt, one trunk:

| what you hand it as the guide | detail before → after | plate-match | verdict |
|---|---|---|---|
| a clean native take | 284 → **282** (with refs) / 301 (caption-only) | 0.992 → 0.944 | **No.** Nothing to restore. ~4.8× the time for noise |
| a **degraded or external clip** | **36 → 110** | 0.992 → 0.936 | **Yes.** 3.1×, and visibly the difference between unusable and usable |

The degraded row is the pass doing its job: face structure, a collar edge, shirt buttons, fine pattern
strokes and small painted objects all come back out of mush. **It reconstructs rather than recovers** — it
reached 110 where the undamaged original measured 284, so do not expect the source quality back.

**And do not reach for it to sharpen your own good take.** On the trunk it was trained against, a clean
native first pass goes 284 → 282. An earlier version of this section claimed +50 %; that figure was the
FINETUNE climbing out of its own soft first pass (223 → 338) compared against a different trunk on a
different prompt, and it does not survive holding either constant. The trunk, not this pass, is the
fine-detail lever for material you generated yourself.

**The cost is the same in every arm and it is not identity.** Plate-match falls ≈ 0.05 (0.992 →
0.936–0.944) as a slight framing PUSH-IN, on a clean guide and a degraded one alike. That is what rules the
pass out for a shot which must match a plate — not identity drift, which was a finetune-only failure.

**Four rules if you use it**, the first two straight from the model card:
1. **The guide must match the output's resolution and land on a valid clip length** — `17k + 5` frames
   (… 107, 124, …), and never shorter than the target. A different resolution or length breaks the
   alignment silently. Resize the source before it reaches the guide input.
2. **Guide latents alone.** The reference-image node passes a block with its own clock instead of an
   aligned guide; the card calls mixing the two "optional/experimental … not necessarily better", and
   measured here it was worse — 0.944 lock and 282 detail against caption-only's 0.942 and 301.
3. **Never lower the denoise.** 0.5 produced output unrelated to the plate — frame-0 correlation −0.003 —
   twice. The LoRA is trained with the target fully noised, so full denoise is its regime, and the obvious
   fix is the wrong fix.
4. **Run it only on an artifact-free guide.** It sharpens whatever is there, defects included — it made a
   wireframe artifact brighter and better defined rather than removing it. Compression softness is the
   defect it FIXES; a structural artifact is one it amplifies.

⚠ **The identity references are finetune-only.** On the finetune they lifted still-lock 0.928 → 0.946 and
are worth passing. On the stock trunk they are worth nothing measurable (0.942 → 0.944) and they COST
detail (301 → 282) — so if you run the pass there at all, run it caption-only, which is also its trained
regime.

⚠ **Two numbers this section used to carry are withdrawn.** The +50 % detail gain, and the 0.963 still-lock
for the pass on its training trunk: both were measured on a prompt whose artifact clause was still present.
Under the fixed prompt the same configuration reads 0.942.

## Operating the box

Local generation is $0 marginal but it is not free: it takes the whole card for the duration. Open a
bracket that stops resident GPU services, records exactly what it stopped, and restores only that on
close — with a lock and a state file so a crashed run does not strand the services. Close it when the
queue drains. Submit-and-poll over the HTTP API rather than holding a session open; a detached remote
job outlives the local shell. Server and bracket mechanics: `video-refs-continuity` SCENE-PROXY.md
§ headless.

## Failure behavior

A partially-valid API graph returns **HTTP 200 with a prompt id** and a `node_errors` map — the valid
outputs are queued anyway. Treat any non-empty `node_errors` as a failure and delete the queued
prompt by its FULL id; a short id silently does nothing. Never read a 200 as success.
