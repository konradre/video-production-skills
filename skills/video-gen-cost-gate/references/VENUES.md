# Venues — modes, prices, caps, moderation, upload conventions

Measured September 2026. Prices move; re-read the venue's own `cost` / rate page before quoting a
number that matters, and never quote a rate the receipts have not confirmed at least once.

## Video

| venue · model | modes | price | caps | moderation | notes |
|---|---|---|---|---|---|
| **Higgsfield CLI · `seedance_2_5`** (production route) | `t2v` · `omni_reference` (= r2v: start image + ≤30 image refs + video refs, ≤50 total) · `video_extension` (`--extension_mode forward --video-references <keeper job id>`) · `video_edit` | 480p **2.5 cr/s** (7 s = 17.5, 12 s = 30) · 720p 6.5/s · 1080p 9/s; Ultra plan 3000 cr/mo, no rollover (≈ $0.03–0.04/cr) | duration integer, 4–30 s single pass (READ from the estimator: `higgsfield generate cost seedance_2_5 --duration 40` errors "less than or equal to 30"; the model schema carries no bound, so never infer the cap from past takes); 9:16 ok; `generate_audio` on by default (the take's bangs and clangs ride in it); `bitrate_mode standard\|high` | **prompt WORDS**, not pictures: "penis", "dick", "thrusting" → status `nsfw` on the whole batch (refunded); a woman looking a man up and down → nsfw on 2/3; a waist-level frame of a bare torso, a headless torso start image → refused unbilled; ALL-CAPS script words trip the gate's own subject scan; person refs ACCEPTED (its reference mode exists for character consistency) | `generate create --json` returns a bare LIST of job ids; `generate get <id> --json`; `--wait` with a path hung; media flags take a path (auto-upload) or a UUID (upload id OR a previous job id); `workspace set <id>` once; OAuth tokens short-lived (`Session expired` → operator re-login); 8 jobs in parallel on Ultra; 2–5 min per take |
| **Higgsfield · `topaz_video`** (hosted upscale) | `--resolution 1080p\|2160p --enhancement '{"model":"rhea-1", …}'` | ≈ 1 cr/s at 2160×3840, 3-cr minimum | model ids: `rhea-1` (reconstructive, beat `prob-4` on crops) · `prob-4` default · `iris-3` · `slp-2.5` / `slf-1` (Starlight — **hang the CLI**, no job, no charge) · `ghq-5` · `thd-3` · `ahq-12` | — | reference the video by the generation's **JOB ID** (`--video-references <job id>` accepted in 3 s; a fresh video upload hung twice); an upload must settle ≥ 3 min before `generate create topaz_video`; `cost` unsupported — measure with a 1-s slice; hangs intermittently (4 in a row once) → one retry then the local route |
| **Higgsfield CLI · `minimax_h3`** (H3 WITH people — fal refuses photoreal people in refs) | refs only: `image_references` + `video_references` (a start image cannot mix with refs); no mode flag; `duration` integer (5 s = one take) | **2K only, 2 cr/s** (5 s = 10, 10 s = 20 — measured; ≈ 1.5× Seedance 480p) | 9:16 ok; ≈ 2 min per 5 s take; 1440×2560 out | took the photoreal family references fal had refused | the proxy clip as `<Video 1>` DROVE the camera and held the room; the text clause alone re-staged the shot (SCENE-PROXY.md § proxy clip) |
| **fal · `bytedance/seedance-2.5/*`** | `image-to-video` (start [+ end] frame, no refs; inherits the frame's ratio) · `reference-to-video` (≤30 image refs, no start frame) — never both on one call | 480p $0.2205/s · 720p $0.4730 · 1080p $1.164 (≈ 2× ByteDance-direct, ≈ 3× Higgsfield) | 4–30 s or `auto` (billed at ACTUAL output seconds: units ÷ 9.59) | `content_policy_violation — likenesses of real people` on ANY photoreal person in a reference or start frame, billed 0; fires on synthetic faces and even on photoreal bipeds of another species | queue rewrites the path — poll only the URLs the submit returns; the queue accepts ANY body (validation on the runner) → `COMPLETED` then a 422/504 on the RESULT fetch; `X-Fal-Billable-Units` arrives on a LATER re-fetch; result lookup went down 5+ h once → vendor switch |
| **fal · `minimax/h3/reference-to-video`** | refs (≤12 files incl. 2–15 s video refs) | 768P $0.06/s · 2K $0.13 · 4K $0.16 (480P exists at $0.05 but `gen_video_fal.py` enforces a **768P minimum** — a house rule) | 5–15 s hard; bills the REQUESTED integer duration; no bitrate parameter (encode density ≈ 0.4 bits/px/frame vs Seedance ≈ 0.6) | took the character sheets fal's Seedance refused | `prompt_expansion_mode` REWRITES the prompt and invents reference descriptions → always `fast`, persist and diff `expanded_prompt`; a different look — not for a spot built on Seedance |
| **Local H3 on your own GPU** (measured on a 24 GB Ampere card) — **OPEN as a route 2026-09-11** (the 09-10 decline was estimated, and every figure in it was wrong once measured) | the open weights through a local ComfyUI server — refs · fl2va · t2v; submit-and-poll over HTTP | **$0 marginal.** The real cost is the whole card for the duration + the bracket that stops resident GPU services and restores them after | **≈ 120 s for a 5 s take at 768×1344** (the decline estimated 4–6 min); ≈ 410 s for a 1088×1920 master via a ×2 tiled latent upscale. Peak 23.9 GB of 24 — the int8 trunks run fine, the decline's "Q4_K_M GGUF only" was wrong | runs unattended: a queue drains while other work continues, and the card is the only venue with no per-take charge, so seeds are free to burn | **choose this route at the outset** — recipe, config rules and the four measured traps: [LOCAL-H3.md](LOCAL-H3.md). Faster AND cheaper than hosted 2K here, so the volume argument that declined it has inverted; hosted stays the route when the card is busy or the operator is away |
| **Create a Meme** (web front-end to Seedance 2.5, operator pastes by hand) | `@ref1` addressing; start + end frame WITH refs | credits ≈ 3× the API price | **2000-char prompt cap** (the wrapper's, not the model's); 9 refs | took the sheets fal refused | "Do not press Enhance prompt"; a front-end's feature set is not the model's contract |
| **monid · `bytedance /v1/video/seedance-2.5`** — **THE ADOPTED SEEDANCE SHAPE: 2.5 @ 480p (house rule, 2026-09-14)**; PAYG, no subscription | `t2v` · `i2v` (`first_frame`) · first+last frame · `r2v` (≤30 image + ≤10 video + ≤10 audio refs, `@Image1`/`@Video1`/`@Audio1` ordinals) · video edit/extend — **say so explicitly in the prompt**, or the model reads it as a plain r2v, generates a NEW video, succeeds, and bills in full with no error to catch. 🔴 **The 30 / 10 / 10 reference counts are vendor PROSE in the schema's `role` descriptions, NOT `maxItems`** — re-read 2026-09-14: the `content` array carries no length bound, and neither does any of its four variants. They are a vendor CLAIM and are UNMEASURED here. Probing the real ceiling is **free when it fails** (an over-cap body the gateway refuses creates no run, $0.00; an upstream rejection arrives as `COMPLETED` + a non-2xx and is not charged) and costs one generation only if it SUCCEEDS — so `monid_submit.py` fails closed at 30 rather than spend to find out. Raise that number from a receipt, never from the description | **$10.7 / 1M tokens, FLAT at 480p and 720p** (no 1080p on this endpoint). 🔴 **`tokens = W × H × (duration × fps + 1) ÷ 1024` — MEASURED, exact.** The vendor's documented `× fps × seconds` is short by ONE FRAME: a 4 s clip returns **97** frames (`4.041667 s = 97/24`), which is why their own docs hedge it as "≈". 480p = 854×480 @ 24 fps ⇒ **4 s $0.4155 · 7 s $0.7239 · 12 s $1.2379 · 30 s $3.088**; effective **$0.1039/s at 4 s → $0.1029/s at 30 s** as the +1 frame amortises | duration **4–30 s** integer, or `auto` — ⚠ **`auto` HOLDS a full 30 s price up front**, releasing the remainder on settle: always pass an integer under a cost gate. **Prompt cap 6,000 chars** (vs Create a Meme's 2,000 — that one is the wrapper's). `ratio` accepted only for t2v/r2v; first/last-frame, edit and extend REQUIRE `adaptive` | real human faces rejected **UPSTREAM** (BytePlus ModelArk), and monid exposes none of the licensed-asset escapes ⇒ synthetic-sheet conversion mandatory. **Provider errors are not charged** (`COMPLETED` + `HTTP 404/500` = run finished, $0.00) — stated verbatim in monid's own API reference, not merely inferred from receipts | **MEASURED 2026-09-14** — t2v 4 s 480p 9:16: `COMPLETED` + provider `HTTP 200` in 3 m 03 s, `usage.completion_tokens` 38,830, **$0.415481**, wallet delta matched to six decimals ⇒ billing is exactly `billedUnits × rate`. ⚠ p50 **245 s**, p95 **603 s** → `--wait` (300 s default) TIMES OUT: **fire-and-poll**, never a bare `--wait`. ⚠ on an async fire **`-o` writes NOTHING** — the submit envelope is stdout only. ⚠ `output.content` is a **dict whose `video_url` is a plain STRING**, not a list and not `{url:…}`. `video_url` expires **~24 h** → download at collection. `monid inspect` is FREE: run it before every run. 🔴 **The terminal run statuses are FIVE — `COMPLETED` · `FAILED` · `BLOCKED` · `STOPPED` · `TIMED_OUT`** (monid API reference § Polling for Results). A poller that waits only for the first two HANGS on the other three. `BLOCKED` is a control gate refusing the run BEFORE execution (`200` + `reason` + `controls`, so free); `FAILED` is monid-side infrastructure; a provider-side `402` surfaces as `502`. ⚠ `billing` is ABSENT until the run settles — read `cost.value` |
| **treg · `reapi.video-gen.seedance-2-5.unrestricted`** — the real-likeness route; PAYG, no subscription, 0 % markup | one body does r2v and i2v: `prompt` carrying `@image1` / `@audio1` placeholders, `image_urls` (public URLs), `duration`, `size`, `resolution`, and **`content_filter: false`** — the only thing separating it from its sibling row `reapi.video-gen.seedance-2-5` (same `doubao-seedance-2.5-face` trunk, filter ON). A placeholder for media you did not attach is a 400 | **480p $0.1186/s · 720p $0.26683 · 1080p $0.462**, per second of OUTPUT, **refunded in full on a failed or moderated task**. Vendor catalog, treg-verified 2026-09-14, then confirmed by a settled receipt: a 4 s 480p take billed **$0.4744**, exactly 4 × $0.1186, and returned **97 frames at 24 fps** — the same duration × fps + 1 arithmetic the monid row documents. At 480p treg sits just above monid's measured **$0.1029–0.1039** | duration integer; 480p / 720p / 1080p; ≤30 image URLs of ≤30 MB each, every one answering the vendor's HEAD probe; prepaid balance, no plan, $1.00 free on a new team | the BytePlus **advanced creation rights** path, wrapped server-side: the image is registered as a digital character and generated from. That registration is why a real person's likeness is accepted on this row and refused on the others. **Clearance for the likeness is the caller's responsibility — the route handles the vendor's rights step, not the subject's consent** | **the CLI is mandatory for anything carrying a file** — the treg MCP exposes no host or upload tool, and its own `call` description says to shell out (`treg call <id> --upload name=@<path>`). `treg host <file>` mints a byte-exact public URL (7-day TTL); never a paste host (catbox, tmpfiles, uguu and a `replicate.delivery` URL each failed the vendor's probe — five dead submissions). Poll `treg call reapi.tasks.get --query id=<task>`: a catalog id takes `--query` / `--data`, **never a URL path**. No seed — every run is a fresh roll. Cap one call with the `X-Treg-Max-Cost` header; `X-Treg-Cost-Micro` comes back on the response. Output URLs last ~7 days |
| **monid · `bytedance /v1/video/seedance-2.0`** — **PRICED, NOT ADOPTED** | same content shape as 2.5 | **$7.0/1M** at 480p/720p · **$7.7** at 1080p · **$4.0 at 4K** — the only 4K Seedance here ⇒ 480p **$0.0673/s**, 30 s $2.02 | up to 4K; 4–30 s | as 2.5 (same upstream moderation) | p50 **127 s** / p95 189 s — ~2× faster than 2.5. Listed so the price is known, not so it is chosen: the dialects are calibrated on 2.5 |
| **monid · `bytedance /v1/video/seedance-2.0-fast`** — **PRICED, NOT ADOPTED** | as 2.0 | **$5.6/1M** ⇒ 480p **$0.0538/s**, 30 s $1.61 | 480p/720p | as 2.5 | p50 **185 s**. `video-prompt-dialects` already scopes 2.0-fast to the **draft** engine only |
| **monid · `bytedance /v1/video/seedance-2.0-mini`** — **PRICED, NOT ADOPTED** | as 2.0 | **$3.5/1M** ⇒ 480p **$0.0336/s**, 30 s $1.01 — **3× cheaper than 2.5** | 480p/720p | as 2.5 | p50 **124 s**. The cheapest Seedance here and therefore the strongest pull off the SOP — which is exactly why the marker is on it |
| **monid · `alibaba /v1/video/wan3.0`** — **PRICED, NOT ADOPTED** | text, frames, reference media, documents or links | **$0.05/s at 480P, FLAT per SECOND** (720P $0.10 · 1080P $0.20) — no token math, no `auto` hold | up to 30 s | unmeasured here | p50 **152 s**. `wan3.0-prime` is $0.068/s at 480P and ~2.4× faster (p50 63 s). **This corpus carries no prompt dialect for Wan** — adopting it is an extraction, not a table row |
| **monid · `sfs`** (Simple FS — the reference-hosting lane, and the reason no venue here is blocked on "needs a public URL") | FIVE endpoints, all free: `/put` → `curl -T <file> '<uploadUrl>'` → `/cat` → a signed URL any third party can fetch → `/rm`; `/ls` to browse; `/mv` to rename or move. **`/cat` returns `expiresAt` (ISO 8601) beside the url, and the url carries its own `?e=<unix>`** — so expiry is checkable LOCALLY at zero calls, and survives a lost ledger. **`/ls` takes `recursive` and returns `entries[]` of `{path, type, sizeBytes, lastModified}`** (cursor-paginated, limit ≤1000), so **ONE call verifies a whole 30-reference set** rather than one call per reference | **$0.00 PER_CALL on every endpoint**, 1 GB free per workspace | `sizeBytes` is REQUIRED on `/put` and is a cap **pinned into the signed URL** — an oversize upload is rejected MID-STREAM. `ttl` (`1h`/`1d`/`7d`/`30d`) bounds the **URL**, never the file's lifetime: an expired URL just needs a fresh `/cat`, which is free | — | **PROVEN end-to-end 2026-09-14 at $0.00** (put → upload HTTP 200 → cat → public fetch HTTP 200 → rm → NOT_FOUND). ⚠ **`/rm` revokes the LINK; it is NOT a recall of a copy already served.** Re-measured 2026-09-14 on two probes: a URL **never fetched** returned `404 link not found or expired` the instant it was removed, and `/ls` agreed `NOT_FOUND` (n=1); one **fetched before** the removal still returned 200 afterwards (n=1) — an edge cache, not a live file. Treat any sfs URL that has left the machine as public until its `ttl` lapses, and choose the `ttl` on that basis for a client's own assets. ⚠ **raw PUT (`curl -T`), never multipart `-F`**. Files **NEVER auto-delete** — `/rm` frees quota (`recursive` for a dir, `force` tolerates a missing path); `/put` also returns a `monid resources release -r <id>` hint. ⚠ **run-generated files are NOT listed by `/ls`** — a generation's output lives at the run's own ~24 h URL; `/put` it back if it must persist. **The lifecycle is neither Higgsfield's nor kie's:** the FILE persists forever, the URL lapses with its `ttl`, and re-issuing is a free `/cat` that moves no bytes — so `monid_upload.py` hosts idempotently (skipping on a matching sha256, re-uploading when the local file CHANGED) and `--refresh` re-issues, while `--verify` runs the one recursive `/ls`. A lapsed url FAILS the refs gate before the GO |

**Venue ranking — and the one thing it does NOT decide.**
Rank by **marginal cost**, and prefer **pay-as-you-go over plan lock-in** at equal cost. A plan's TRUE
rate is its price ÷ the credits **actually burned**, never the credits granted, and purchased credits that
expire are a cost the per-second rate hides. **NEVER rank a venue by its current balance** — a low wallet
is a funding question, never a priority signal.

**This picks the VENUE for a FIXED model and shape. It NEVER authorises a MODEL swap.** Seedance work is
**2.5 at 480p** (house rule). A cheaper trunk in the table above is DATA, not an option: the dialects are
calibrated on 2.5, and a new model is proven on the HARDEST shot first (`SKILL.md` § 1).

A subscription's true rate is what the month actually cost divided by the credits actually burned, so a
light month (credits expire) and a heavy month (top-up packs at retail, often on their own expiry clock)
both push it above the headline. Spiky, client-driven demand is what makes pay-as-you-go win on the same
model. Price your own two routes that way before choosing, and re-measure when either vendor moves.

**Real likeness routes to treg, not to Higgsfield.** A reference carrying a real person's
likeness is refused upstream on fal and on monid, and monid exposes none of BytePlus's licensed-asset
escapes; treg's `reapi.video-gen.seedance-2-5.unrestricted` row carries the rights path that makes it legal. At 480p it
is **$0.1186/s PAYG** with no plan behind it, so the ranking doctrine above reaches it without a tie-break.
Higgsfield keeps the shots treg has no row for: `video_extension` on a keeper's job id, `video_edit`,
`topaz_video`, and `minimax_h3` at 2K. **Measured once** — a single 4 s take, so the per-second rate is confirmed and nothing about drift past 4 s is.

**The 480p chain:** generate at 480p, approve, THEN reconstruct up (Rhea ×4 local, or Starlight from the
take for distant faces). Never propose 720p/1080p generation; the upscaler run once on the selected
footage is cheaper than prompts ×5–10 at 720p. Seedance re-renders frame 0 from a start image
(composition, blocking and light carry; pixel exactness does not); i2v output aspect = the frame's.

**Face gate per model version** (image → video start frames): 2.0-fast/480p landscape cleared at faces ≤
~60 px; 2.5/9:16 on fal refused at ≈ 27 % of frame width at every pixel size. Higgsfield's omni mode
accepts the same people. Photoreal portrait plates are the deepfake-reference shape: compose the figure
into a scene rather than passing a face plate.

### Creator-style talking heads — the September 2026 routing, and the venues the table above does not carry as rows

Measured here (a 30 s trust-series episode, 2026-09-15/16) and agency production data; the community signal on these
models is weak and affiliate-laden and is weighted as such — the evidence tier is stated on every row. Vendor figures stay vendor claims until a receipt confirms them.

| venue · model | modes · caps | price | what it holds / what breaks |
|---|---|---|---|
| **fal · `google/gemini-omni-flash/v1.1/{image-to-video,reference-to-video,text-to-video,edit}`**; monid `gemini /v1/video/omni-flash-*` | 3–10 s integer; 16:9 / 9:16; **720p NATIVE** (1080p and 4k are Google's own upscale ⇒ generate at 720p and reconstruct up); r2v ≤ 6 image refs + ≤ 3 video refs of ≤ 3 s; **NO audio input on any surface** — a reference clip's audio is ignored | fal **$0.03 / 0.10 / 0.15 / 0.30 per s** at 360p / 720p / 1080p / 4k (monid +$0.01); MEASURED: a 7 s 720p 9:16 i2v = 23.39 fal units, ~44 s wall; refusals bill nothing; fal result URLs expire, monid's keep 7 days | the simple talking head and the hook sweep (360p drafts at $0.03/s for remixes of one clip); MP4 with native audio + SynthID; ~15 % of takes stutter → regenerate; it INVENTS words (a client line came back with "dollars" on two numbers, and "say exactly these words" made it worse) ⇒ a script-exact mouth needs an audio-driven model (fal `fal-ai/bytedance/omnihuman/v1.5`, image + audio) or a lipsync pass over the take (`fal-ai/sync-lipsync/v3`, Kling lipsync, HeyGen v3 — their prices render client-side and are UNREADABLE in advance: the `x-fal-billable-units` header measures them); a negation BURNED captions onto the subject's shirt — positive-spec only |
| **Kling 3.0 Pro / Turbo** (fal, Higgsfield) | 3–15 s; talking clips **≤ 8 s** — past second 8 the lips and the audio part company (agency production data, community-corroborated); multi-shot tops at 15 s | ≈ $0.11–0.14 / s (Turbo; third-party figures) | handheld micro-motion, the phone feel; the mid-tier alternative for product-in-hand; NOT adopted here — unmeasured |
| **Sora 2** (OpenAI) | — | — | **RETIRED** — web and app off 2026-04-26, the API off 2026-09-24 with no replacement alias (OpenAI primary); every recipe that named it is dead |
| Veo 3.1 · Luma Ray3 · FLUX 3 (BFL, 2026-07-23, 20 s native audio) · Creatify Boreal (2026-09-15, "$0.01/s", "47× cheaper" — vendor) · Wan 3.0 (2026-08-24; **no open weights** — the last Apache release is Wan 2.2, and the April corpus's "Wan 2.7 Apache 2.0" was wrong) | — | vendor and community claims only | Veo 3.1's mouth realism fails on dialogue ⇒ non-talking b-roll and proof shots; the rest UNPROVEN here — a new model is proven on the hardest shot first (SKILL.md § 1), never adopted from a leaderboard, and Wan carries no dialect in this corpus |

Rules that arrived with the data. **Cost per USABLE take, never per second**: the keep ratio runs 3:1 to 6:1 across
models (agency data), so a 7 s Omni take at 720p is ≈ $0.83 per usable at a 15 % stutter rate and ≈ $4.20 at "six takes
for one", and a Seedance 2.5 720p 30 s pass is ≈ $8.85 BEFORE retries — the cost line quotes the usable figure with its
assumed keep rate. **Repair or regenerate by the take's price**: a cheap take is regenerated; an expensive one is
repaired (clean audio + a lipsync pass over the footage) — the rule comes from a vendor that sells the repair layer, and
is stated here with that incentive named. **Per shot type**: EVERY talking head — UGC or commercial —
→ **Omni Flash 1.1 + a fal lipsync pass** (§ The talking-head default); a hook sweep → Omni 1.1 at 360p;
product-in-hand or a 30 s story → Seedance 2.5 (the label is drawn, never read — keep it as an image reference and the
label shot short and front-on); a defined handheld move ≤ 8 s → Kling; the words that must land exactly → an
audio-driven model or a lipsync pass, never a prompt. Every take
carries SynthID or C2PA: the platform's auto-label is expected, never dodged (`ad-spot-preprod` RISKS.md § UGC compliance).

#### The talking-head default — Omni Flash 1.1 + fal lipsync

**Every talking head starts on Omni Flash 1.1 and gets a `fal-ai/sync-lipsync/v3` pass against the locked VO.** UGC and
commercial ads alike; Seedance 2.5 keeps product-in-hand, the 30 s story and — through treg's unrestricted row — a real
person's likeness. The call came from a two-version A/B on a 30 s trust-series episode: Seedance 2.5 480p + lipsync
against Omni Flash 1.1 720p + lipsync, two of the four lines swapped, judged by eye.

**Two things carry it beyond one judgement.** *Price parity at a higher native raster:* Omni is **$0.10/s at 720p**
against Seedance 2.5's **$0.1029/s at 480p** on monid — a 7 s take is $0.70 vs $0.72 — so the default generates at the
delivery-adjacent raster and asks less of the upscale, at the same money. *The mouth is the whole job:* both trunks
voice the line themselves and invent words, so the lipsync pass is mandatory either way, and it is the pass, not the
trunk, that pins the voice.

⚠ **The A/B behind this default is CONFOUNDED, and the default was adopted with that on the table.** The finish
retrospective's Finding 15 measured `sync-lipsync/v3` silence-mode padding **~1/3 of (video − audio) at the HEAD**, so the
Seedance version's mouths shipped late by +0.15/+0.32 s while the Omni version's takes were built with the pad measured
and compensated (+0.47/+0.31 s). A fair re-run needs one Seedance take rebuilt with the head-pad fix; it costs a lipsync
pass (0.117 units) plus a local Rhea upscale, so the settling test is ~$0. Until that runs, the default rests on the operator's read and on
the price/raster argument, not on a controlled comparison.

⚠ Omni's own traps stay in force: ~15 % of takes stutter (regenerate), **no audio input on any surface**, and a quoted
word in the prompt body can PRINT on a garment — a take was voided when the quoted gesture word "worn" appeared on a
polo's badge. Negations burn captions onto clothing; positive-spec only.

## Images (stills, plates, references)

| venue · model | use | price | moderation | notes |
|---|---|---|---|---|
| **kie.ai · `gpt-image-2-5-flare-image-to-image`** — **THE DEFAULT still model (house rule, 2026-09-10)**; `-sunburst-` = the precision tier | composing a scene from references; plates; start and end stills; the copy route for lettering | **$0.03 at 1K · $0.05 at 2K · $0.08 at 4K** (`input_urls` ≤ 16, `aspect_ratio`, `resolution 1K|2K|4K`; the 27:16-class ratios 1K only) | OpenAI-moderated like 2 (assume the same lettering refusals until measured) | **kie is the FIRST venue for stills** (house rule, 09-10); validated 09-10: a 2K still from a keeper + a face ref + a grey scene-proxy frame matched the proxy's end table (armchair 70 % vs table 66, lamp in view, no invented element, faces held) — 1536×2736 out; GPT Image 2 is superseded — Nano Banana Pro is the FALLBACK |
| **kie.ai · `gpt-image-2-image-to-image`** (SUPERSEDED by 2.5 on 2026-09-10 — the row stays for the evidence) | composing a scene from references (holds colour, size order and character on the first try); the copy route for lettering; repositioning a figure from the pre-plate | $0.09 at 1K/2K, $0.12 above | refuses the WORDS of some lettering ("may violate OpenAI's content policies", $0) — not the picture; anatomy-word density on the image leg (~2 body nouns; the preserve list counts) | ref 1 = the image being edited (the start image for the gate); references are public https URLs — data: URIs are rejected; uploads via `kieai.redpandaai.co/api/file-base64-upload` (not `api.kie.ai`), expire ~24 h; browser UA on upload and download; output resolution changed mid-session once — record dims in the receipt; ~30 % transient errors in tight loops (retry); 20 req/10 s |
| **kie.ai · `nano-banana-pro`** | surgical edits — exactly N figurines, remove a ghost, repair one limb ("change only this, count exactly that"); garment text via Google's moderator | $0.09 | "flagged as sensitive" when the input carries the product pieces at large scale (billed 0) → edit the CLEAN plate, composite after | IGNORES character sheets when composing a scene; cannot move a figure (~0.5 m + an invented prop) |
| **Higgsfield · `gpt_image_2_5`** (default; `--variant flare|sunburst`, `--quality low…max`, `--resolution 1k|2k|4k`) / `nano_banana_pro` (fallback) / `seedream_v5_pro` / `flux_2` | the SECOND still route — kie first (house rule, 09-10); credits, no upload step (`image_references` take upload or job UUIDs); refused lettering | gpt_image_2_5 with 3 refs: 1k/2k low 1.5/2 cr · medium 2/2.5 · high 3.5/5.5 · xhigh 5/8 · max 9/16.5; nano_banana_pro 2k 2 cr | — | `soul_location` = people-free scenes, prompt only; GPT Image 2 superseded |
| **Replicate** | took the sheets fal refused (venue-level partner validation differs) | — | — | fallback only; no script calls it — a call routed there by hand reads `REPLICATE_API_TOKEN` from the env file |

**Still frame sizing (2026-09-10).** A start or end still is generated at the CLIP's aspect (9:16 for a vertical
spot, 16:9 for film) at the venue's 2K preset; a video venue letterboxes or crops a frame that does not match. kie and
Higgsfield expose presets (`aspect_ratio` + `1K|2K|4K`), not pixel strings — measured: kie 2.5 2K 9:16 → 1536×2736,
Higgsfield Nano Banana Pro 2k 9:16 → 1536×2752, both multiples of 16 and within 1 % of 9:16. `gen_stills.py` checks every
landed still (aspect within 1 % of `--ratio`, both sides multiples of 16) and WARNs. If the OpenAI Images API is ever called
DIRECTLY (no script does; that call reads `OPENAI_API_KEY` from the env file) it takes a custom size: 16:9 → 1536×864 (recommended for image-to-video) or 2048×1152 (2K); 9:16 → 864×1536 or
1152×2048; both sides multiples of 16, long:short ≤ 3:1, 3840×2160 the cap and anything above 2560×1440 experimental
(OpenAI image-prompting guide + the images/generate reference, read 2026-09-10).

**Reference-adherence is per MODEL, not per prompt:** the same references and prompt on the same platform
held identity on gpt-image-2 and were ignored by nano-banana-pro. Reference-critical work defaults to the
model that honours it — since 2026-09-10 that is GPT Image 2.5 (a standing house rule: every OpenAI
image gen on 2.5, 2.5 the default still model, Nano Banana Pro the fallback); the 2.5 contract is assumed to
match 2's until a still measures otherwise.

## Music

| venue | modes | price | caps | moderation | conventions |
|---|---|---|---|---|---|
| **AceDataCloud Suno** — **THE DEFAULT music venue (house rule, 2026-09-12)**; a reseller of Suno, not Suno direct | `POST /suno/audios` — inspiration mode (`prompt`, `instrumental`) or custom mode (`custom: true` + `lyric`, `title`, `style`, `vocal_gender`) | **≈ 0.56 credits ≈ $0.08 per call, which returns TWO takes** (≈ $0.04 a take). Other ops: `stems` 0.56 · `concat` 0.04 · `create_voice` 0.10 · `replace_section` 0.80 · `all_stems` 1.60 (prefer `stems`) | `duration` 10–360 s, custom mode only, and a TARGET not a cap — an unguided call returned 5.5 min. Model `chirp-v5-5`; the vendor's own client ships an `.env.example` pinning `chirp-v4-5` | no content gate observed on instrumental beds | **always async** — task id, then `POST /suno/tasks` `{"id": "<task id>"}` every 3–5 s, ≈ 2 min 20 s. Downloads are **Opus inside `.m4a`** — Resolve rejects them; transcode to 48 kHz 24-bit WAV first. Bearer token `ACEDATACLOUD_API_TOKEN` from the env file that holds it. **No balance endpoint** — track spend from the receipts |

Every other music route — the operator's own candidates, a library bed — is a fallback that needs the
operator's permission first, named per cue. Cue, duck and licence rules live in `spot-audio-assembly`
§ Music.

## Balances and identity

`higgsfield account status` (credits) and `monid balance` (dollars) are both free reads; kie and AceData expose no
balance endpoint → track spend from the receipts and say "unreadable via API", never "0". A balance is REPORTED, never
ranked on — venue choice is by marginal cost (§ Venue ranking). Every status message to the operator carries the
balances (credits, dollars, TTS characters) and the free disk on the render drive.

## Secrets

Keys live in the kit's `.env`, copied from `.env.example`, and are loaded in the same command that needs them
(`set -a; . ~/.claude/skills/video-production/../../.env; set +a`; `KEY=value`, no `export`, no quotes). monid and
Higgsfield each keep their credential in their own CLI's store instead. A key pasted in
chat is rotated after use. Never printed, never in a receipt, never in a skill.
