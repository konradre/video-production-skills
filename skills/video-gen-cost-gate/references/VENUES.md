# Venues — modes, prices, caps, moderation, upload conventions

Measured September 2026. Prices move; re-read the venue's own `cost` / rate page before quoting a
number that matters, and never quote a rate the receipts have not confirmed at least once.

## 🔴 This table is A ROSTER, not a prescription — declare your own

**Every venue, price and default below is the one this kit's author measured, on the accounts they hold.**
You almost certainly hold different ones. Nothing here requires you to open an account anywhere, and no rule
in this kit refuses to run because a venue you do not have is "the" route (`SKILL.md` § 0 — constraints guide,
they never block).

**What actually travels is the ROUTING LOGIC, which is four rules and no vendor names:**

1. **Rank the venues YOU have by MARGINAL cost** — the price of the next second of output, not the headline
   rate and never the wallet balance. A subscription's true rate is what the month cost ÷ the credits actually
   burned.
2. **Prefer pay-as-you-go over plan lock-in at equal cost** — spiky, client-driven demand penalises a plan
   twice (a light month expires credits, a heavy month buys packs at retail).
3. **Let FUNDING decide which ranked venue is reachable.** Where the money sits is a hard constraint; being
   second or fourth on price is a premium to quote in the cost line, never a reason to refuse a batch.
4. **Route on CAPABILITY before price where a capability is the job** — a real person's likeness, an audio
   reference that drives the words, a raster a venue cannot reach. A venue that cannot do the shot is not
   cheap, it is absent.

**Declaring your roster:** keep the rows for venues you hold, delete or comment the rest, and replace the
prices with your own measured ones — a receipt, not a rate card. Then re-run the two things the rest of this
kit reads out of this file: **which venue is default for each shot type**, and **what the fallback chain is
when the default is unavailable, unfunded or refuses.** Where a rule below names a specific vendor, the vendor
is the EXAMPLE and the rule is the thing that ports.

⚠ **A price here is evidence with a date on it, not a constant.** Vendors reprice, add rasters and change
moderation without notice, and several rows below record a figure that was wrong until a receipt corrected it.
Re-measure before a decision rests on one.

## Video

| venue · model | modes | price | caps | moderation | notes |
|---|---|---|---|---|---|
| **Higgsfield CLI · `seedance_2_5`** — the subscription route; ⚠ price it against the vendor's own API row below before renewing | `t2v` · `omni_reference` (= r2v: start image + ≤30 image refs + video refs, ≤50 total) · `video_extension` (`--extension_mode forward --video-references <keeper job id>`) · `video_edit` | 480p **2.5 cr/s** (7 s = 17.5, 12 s = 30) · 720p 6.5/s · 1080p 9/s — **480p RECEIPT-CONFIRMED 2026-09-14**: across 392 transactions every spend is an exact multiple of 2.5 (−10 = 4 s, −12.5 = 5 s, −15 = 6 s, −20 = 8 s, −50 = 20 s), so the third-party "3.0 cr/s" figure is WRONG. Ultra 3000 cr/mo, **no rollover**, refill on the **1st**; monthly $129 / annual $99 (≈ $0.033–0.043/cr) — but top-up packs are **checkout-priced, never published**, and **expire after 90 days**, so the blended rate is what matters, not the plan rate (§ Venue ranking) | duration integer, 4–30 s single pass (READ from the estimator: `higgsfield generate cost seedance_2_5 --duration 40` errors "less than or equal to 30"; the model schema carries no bound, so never infer the cap from past takes); 9:16 ok; `generate_audio` on by default (the take's bangs and clangs ride in it); `bitrate_mode standard\|high` | **prompt WORDS**, not pictures: "penis", "dick", "thrusting" → status `nsfw` on the whole batch (refunded); a woman looking a man up and down → nsfw on 2/3; a waist-level frame of a bare torso, a headless torso start image → refused unbilled; ALL-CAPS script words trip the gate's own subject scan; person refs ACCEPTED (its reference mode exists for character consistency) | `generate create --json` returns a bare LIST of job ids; `generate get <id> --json`; `--wait` with a path hung; media flags take a path (auto-upload) or a UUID (upload id OR a previous job id); `workspace set <id>` once; OAuth tokens short-lived (`Session expired` → operator re-login); 8 jobs in parallel on Ultra; 2–5 min per take |
| **Higgsfield API · `bytedance/seedance-2.5/*`** — `https://api.higgsfield.ai`, PAYG, a separate wallet from the subscription above | five DEDICATED endpoints, no `mode` flag — `text-to-video` · `image-to-video` (`image_url` [+ `end_image_url`]) · `reference-to-video` (`image_urls` 1–30 + `video_urls` 1–10 + `audio_urls` 1–10, at least one required) · `video-edit` (`video_url`, OMIT `duration` — the source decides) · `video-extend`. 🔴 **`resolution` is `480p` or `720p` ONLY — there is NO 1080p on this API**, the single regression against the CLI, and the reason the talking-head default moved to 720p + an upscale (§ The talking-head default) | 🔴 **TOKEN-METERED, PROPORTIONAL TO PIXELS** — `tokens = ceil((input_video_s + generated_s) × W × H × 24 fps ÷ 1024)`, at **$0.0214 / 1K standard** or **$0.01284 / 1K (0.6×) when a VIDEO reference is present** — and that tier bills the INPUT seconds too. **Image and audio references are NOT video input.** ⇒ 9:16 list **$0.2056/s @480p · $0.4622/s @720p**; at the 30 % launch discount (**dated 2026-09-18, expiring**) **$0.144 · $0.324**. 🔴 **720p costs 2.25× 480p — the pixel ratio, and it is never free.** ⚠ **The pricing page's per-second figures are 480p figures**: *"up to 720p"* is the capability column, not the price point. Read against the vendor's own two rates, `$0.144/s` is 480p standard and `$0.0864/s` is 480p with-video-input (0.6× of it, to four figures) — no 720p price was ever printed there | duration integer **4–30** (default 5); automatic duration (`-1`) unsupported on r2v; `aspect_ratio` explicit and adds **`21:9`**; `output_format` `mp4\|mov`; outputs retained **≥ 7 days**. Uploads: `POST /files/generate-upload-url` → PUT with **every** returned header, **URL expires in 1 hour**; `asset://` unsupported (public URLs only). 🔴 **NO MP3 ON UPLOADS** — `image/jpeg\|jpg\|png\|webp\|gif`, `audio/wav\|x-wav`, `video/mp4` only, so our `voice_ref.mp3` needs a WAV convert for this lane | six statuses, four terminal: `queued` · `in_progress` · `completed` · `failed` · `nsfw` · `canceled`. **`failed` and `nsfw` are NOT charged** and reserved credits auto-refund; a successfully cancelled QUEUED request refunds (`202`; `400` once processing started). 🔴 **LIKENESS: THE SPLIT IS PUBLIC FIGURE vs ORDINARY PERSON, NOT VENUE vs VENUE — BOTH CELLS MEASURED 2026-09-18.** ✅ **AN ORDINARY PERSON'S FACE IS ACCEPTED HERE** — a photoreal head-and-shoulders portrait of a non-famous man as the sole `image_urls` reference, same 4 s 480p neutral non-speaking prompt, `generate_audio: false` → **`completed`, a 797 KB 480×854 file, $0.5757**. So this API DOES carry a real-likeness route and treg is no longer the only one; fal still refuses ANY photoreal person, which is the row that actually stands apart. ❌ **A PUBLIC FIGURE IS REFUSED, and the test cost $0.00.** The same prompt with a real, identifiable public figure as the sole `image_urls` reference, a neutral NON-SPEAKING 4 s 480p prompt, `generate_audio: false` → terminal status **`nsfw`**, empty error body, **not charged**, reserved credits auto-refunded (confirmed in the wallet ledger). 🔴 **AND SO DID treg, ON THE SAME IMAGE — so this is NOT a venue difference** (see the treg row; BytePlus `80006` *"rejected by the content safety system"*, task `failed`, credits 0, full refund). **A PUBLIC FIGURE IS REFUSED EVERYWHERE IN THIS TABLE, `content_filter: false` INCLUDED — while an ORDINARY face is accepted BOTH here and on treg.** ⇒ the likeness question has TWO answers and they must never be collapsed: *whose* face decides it, not *which* venue. 🔴 **THE OUTPUT CARRIES THE +1 FRAME.** The accepted take came back **97 frames at 24 fps, `duration=4.041667` (= 97/24 exactly)** on a 4 s request — the same off-by-one-frame signature monid's receipt measured on ByteDance, now visible in Higgsfield OUTPUT too. That is evidence for the ceiling arm of the cost line, **not proof of the billing basis**: 96 frames = 38,430 tok = $0.5757, 97 frames = 38,830 tok = $0.5817, and with no balance endpoint there is nothing to read back that says which was charged. Quote the ceiling; settle it only from a receipt. 🔴 **THE SUBMIT ACCEPTING IS NOT THE VERDICT** — moderation runs DURING processing, not at submit: the request returned a normal `{status:"queued", request_id, status_url}` and sat `in_progress` for ~65 s before landing `nsfw`. A caller that reads a clean submit as "the likeness passed" is reading the queue, not the gate | `Authorization: Key <KEY_ID>:<KEY_SECRET>` from the kit's `.env` (`HF_API_KEY_ID` / `HF_API_KEY_SECRET` / `HF_CREDENTIALS`, the vendor's own names so every docs snippet runs verbatim) — 🟢 **this kills the CLI's short-lived OAuth and its `Session expired → operator re-login` interruption.** Submit returns `{status, request_id, status_url, cancel_url}` — **use the returned URLs, never construct them.** 🔴 **Concurrency refuses with `400`, NOT 429** (*"Maximum number of concurrent requests (4) has been reached"*), with no `Retry-After` and no rate-limit headers, so a poller that reads 400 as a malformed body misdiagnoses it. 🔴 **`urllib` is Cloudflare-blocked with `403 {"error code: 1010"}` on EVERY endpoint — use `curl`.** That uniform refusal reads exactly like a bad key; an UNAUTHENTICATED `curl` returning a clean `401` is what separates an instrument failure from an auth failure. **`GET /models` is the authoritative catalog** (76 models, machine-readable) — `/docs/openapi.json` is explicitly NOT, and is stale enough to omit Seedance 2.5 entirely; `base_credits` in that catalog is a dead field, zero on everything. 🔴 **NO balance endpoint exists** (18 paths probed; only `GET /models` and `GET /requests/{id}/status` answer) ⇒ the API wallet is **UNREADABLE** and rides on our own ledger — never report it as 0, never guess it. Credits expire **one year** after they are added. Model access is per-account: `404`, `423` (`model_blocked`) or `503` can each mean "not available to you". 🟢 **BUILT 2026-09-18** — `hf_api.py` (computed cost line + the wallet's only ledger) · `hf_api_upload.py` (free; converts mp3 → WAV) · `hf_api_submit.py` · `hf_api_poll.py`; refs-gate target `hfapi`, ledger `hf-api-urls.json`. See § The lane as BUILT |
| **Higgsfield · `topaz_video`** (hosted upscale) | `--resolution 1080p\|2160p --enhancement '{"model":"rhea-1", …}'` | ≈ 1 cr/s at 2160×3840, 3-cr minimum | model ids: `rhea-1` (reconstructive, beat `prob-4` on crops) · `prob-4` default · `iris-3` · `slp-2.5` / `slf-1` (Starlight — **hang the CLI**, no job, no charge) · `ghq-5` · `thd-3` · `ahq-12` | — | reference the video by the generation's **JOB ID** (`--video-references <job id>` accepted in 3 s; a fresh video upload hung twice); an upload must settle ≥ 3 min before `generate create topaz_video`; `cost` unsupported — measure with a 1-s slice; hangs intermittently (4 in a row once) → one retry then the local route |
| **Higgsfield CLI · `minimax_h3`** (H3 WITH people — fal refuses photoreal people in refs) | refs only: `image_references` + `video_references` (a start image cannot mix with refs); no mode flag; `duration` integer (5 s = one take) | **2K only, 2 cr/s** (5 s = 10, 10 s = 20 — measured; ≈ 1.5× Seedance 480p) | 9:16 ok; ≈ 2 min per 5 s take; 1440×2560 out | took the photoreal family references fal had refused | the proxy clip as `<Video 1>` DROVE the camera and held the room; the text clause alone re-staged the shot (SCENE-PROXY.md § proxy clip) |
| **fal · `bytedance/seedance-2.5/*`** | `image-to-video` (start [+ end] frame, no refs; inherits the frame's ratio) · `reference-to-video` (no start frame) — never both on one call. 🔴 **r2v is ONE endpoint carrying THREE modes through a `task` enum — `reference` · `editing` · `extension`** (schema, 2026-09-17). There is no `/video-edit` or `/video-extend` path: both 404. `editing` coerces `aspect_ratio` AND `duration` to `auto`; `extension` coerces `aspect_ratio`. r2v carries **`image_urls` ≤30 (≤30 MB each) + `video_urls` ≤10 + `audio_urls` ≤10, and a HARD `total files across all modalities ≤ 50`** — the same 50 the Higgsfield row states, and the first source to give the 30/10/10 a stated global cap rather than prose. A video ref is 1.8–30.2 s, ≤200 MB, 300–6,000 px/side, AR 0.4–2.5, 24–60 fps; an audio ref is MP3/WAV, 1.8–30.2 s, ≤15 MB, **combined ≤30.2 s**, and **at least one image or video reference is REQUIRED beside it** — audio alone is not a valid call | 480p $0.2205/s · 720p $0.4730 · 1080p $1.164 (≈ 2× ByteDance-direct, ≈ 3× Higgsfield) | 4–30 s or `auto` (billed at ACTUAL output seconds: units ÷ 9.59) — ⚠ `duration` is a **STRING** enum (`"auto"`, `"4"`…`"30"`), not an integer, and `aspect_ratio` adds **`21:9`** and `auto`. `bitrate_mode standard\|high`. ⚠ **`generate_audio` is FREE** — *“the cost of video generation is the same regardless of whether audio is generated or not”* (vendor schema). 🔴 **`seed` EXISTS on this route** — the treg row's “no seed, every run is a fresh roll” is a treg fact, NOT a Seedance one; fal hedges it as *“results may still vary slightly even with the same seed”*, so it is a drift-reducer, never a reproducibility guarantee | `content_policy_violation — likenesses of real people` on ANY photoreal person in a reference or start frame, billed 0; fires on synthetic faces and even on photoreal bipeds of another species | queue rewrites the path — poll only the URLs the submit returns; the queue accepts ANY body (validation on the runner) → `COMPLETED` then a 422/504 on the RESULT fetch; `X-Fal-Billable-Units` arrives on a LATER re-fetch; result lookup went down 5+ h once → vendor switch |
| **fal · `minimax/h3/reference-to-video`** | refs (≤12 files incl. 2–15 s video refs) | 768P $0.06/s · 2K $0.13 · 4K $0.16 (480P exists at $0.05 but `gen_video_fal.py` enforces a **768P minimum** — a house rule) | 5–15 s hard; bills the REQUESTED integer duration; no bitrate parameter (encode density ≈ 0.4 bits/px/frame vs Seedance ≈ 0.6) | took the character sheets fal's Seedance refused | `prompt_expansion_mode` REWRITES the prompt and invents reference descriptions → always `fast`, persist and diff `expanded_prompt`; a different look — not for a spot built on Seedance |
| **Local H3 on your own GPU** (measured on a 24 GB Ampere card) — **OPEN as a route 2026-09-11** (the 09-10 decline was estimated, and every figure in it was wrong once measured) | the open weights through a local ComfyUI server — refs · fl2va · t2v; submit-and-poll over HTTP | **$0 marginal.** The real cost is the whole card for the duration + the bracket that stops resident GPU services and restores them after | **≈ 120 s for a 5 s take at 768×1344** (the decline estimated 4–6 min); ≈ 410 s for a 1088×1920 master via a ×2 tiled latent upscale. Peak 23.9 GB of 24 — the int8 trunks run fine, the decline's "Q4_K_M GGUF only" was wrong | runs unattended: a queue drains while other work continues, and the card is the only venue with no per-take charge, so seeds are free to burn | **choose this route at the outset** — recipe, config rules and the four measured traps: [LOCAL-H3.md](LOCAL-H3.md). Faster AND cheaper than hosted 2K here, so the volume argument that declined it has inverted; hosted stays the route when the card is busy or the operator is away |
| **Create a Meme** (web front-end to Seedance 2.5, operator pastes by hand) | `@ref1` addressing; start + end frame WITH refs | credits ≈ 3× the API price | **2000-char prompt cap** (the wrapper's, not the model's); 9 refs | took the sheets fal refused | "Do not press Enhance prompt"; a front-end's feature set is not the model's contract |
| **monid · `bytedance /v1/video/seedance-2.5`** — **THE ADOPTED SEEDANCE SHAPE: 2.5 @ 480p (house rule, 2026-09-14)**; PAYG, no subscription | `t2v` · `i2v` (`first_frame`) · first+last frame · `r2v` (≤30 image + ≤10 video + ≤10 audio refs, `@Image1`/`@Video1`/`@Audio1` ordinals) · video edit/extend — **say so explicitly in the prompt**, or the model reads it as a plain r2v, generates a NEW video, succeeds, and bills in full with no error to catch. 🔴 **The 30 / 10 / 10 reference counts are vendor PROSE in the schema's `role` descriptions, NOT `maxItems`** — re-read 2026-09-14: the `content` array carries no length bound, and neither does any of its four variants. They are a vendor CLAIM and are UNMEASURED here. Probing the real ceiling is **free when it fails** (an over-cap body the gateway refuses creates no run, $0.00; an upstream rejection arrives as `COMPLETED` + a non-2xx and is not charged) and costs one generation only if it SUCCEEDS — so `monid_submit.py` fails closed at 30 rather than spend to find out. Raise that number from a receipt, never from the description | **$10.7 / 1M tokens, FLAT at 480p and 720p** (no 1080p on this endpoint). 🔴 **`tokens = W × H × (duration × fps + 1) ÷ 1024` — MEASURED, exact.** The vendor's documented `× fps × seconds` is short by ONE FRAME: a 4 s clip returns **97** frames (`4.041667 s = 97/24`), which is why their own docs hedge it as "≈". 480p = 854×480 @ 24 fps ⇒ **4 s $0.4155 · 7 s $0.7239 · 12 s $1.2379 · 30 s $3.088**; effective **$0.1039/s at 4 s → $0.1029/s at 30 s** as the +1 frame amortises | duration **4–30 s** integer, or `auto` — ⚠ **`auto` HOLDS a full 30 s price up front**, releasing the remainder on settle: always pass an integer under a cost gate. **Prompt cap 6,000 chars** (vs Create a Meme's 2,000 — that one is the wrapper's). `ratio` accepted only for t2v/r2v; first/last-frame, edit and extend REQUIRE `adaptive` | real human faces rejected **UPSTREAM** (BytePlus ModelArk), and monid exposes none of the licensed-asset escapes ⇒ synthetic-sheet conversion mandatory. **Provider errors are not charged** (`COMPLETED` + `HTTP 404/500` = run finished, $0.00) — stated verbatim in monid's own API reference, not merely inferred from our receipts | **MEASURED 2026-09-14** — run `01M2F6HTEXF8TE7FS32TB448EN`, t2v 4 s 480p 9:16: `COMPLETED` + provider `HTTP 200` in 3 m 03 s, `usage.completion_tokens` 38,830, **$0.415481**, wallet delta matched to six decimals ⇒ billing is exactly `billedUnits × rate`. ⚠ p50 **245 s**, p95 **603 s** → `--wait` (300 s default) TIMES OUT: **fire-and-poll**, never a bare `--wait`. ⚠ on an async fire **`-o` writes NOTHING** — the submit envelope is stdout only. ⚠ `output.content` is a **dict whose `video_url` is a plain STRING**, not a list and not `{url:…}`. `video_url` expires **~24 h** → download at collection. `monid inspect` is FREE: run it before every run. 🔴 **The terminal run statuses are FIVE — `COMPLETED` · `FAILED` · `BLOCKED` · `STOPPED` · `TIMED_OUT`** (monid API reference § Polling for Results). A poller that waits only for the first two HANGS on the other three. `BLOCKED` is a control gate refusing the run BEFORE execution (`200` + `reason` + `controls`, so free); `FAILED` is monid-side infrastructure; a provider-side `402` surfaces as `502`. ⚠ `billing` is ABSENT until the run settles — read `cost.value` |
| **treg · `reapi.video-gen.seedance-2-5.unrestricted`** — the real-likeness route; PAYG, no subscription, 0 % markup | one body does r2v and i2v: `prompt` carrying `@image1` / `@audio1` placeholders, `image_urls` (public URLs), `duration`, `size`, `resolution`, and **`content_filter: false`** — the only thing separating it from its sibling row `reapi.video-gen.seedance-2-5` (same `doubao-seedance-2.5-face` trunk, filter ON). A placeholder for media you did not attach is a 400 | **480p $0.1186/s · 720p $0.26683 · 1080p $0.462**, per second of OUTPUT, **refunded in full on a failed or moderated task**. Vendor catalog, treg-verified 2026-09-14, then confirmed by a settled receipt: a 4 s 480p take billed **$0.4744**, exactly 4 × $0.1186, and returned **97 frames at 24 fps** — the same duration × fps + 1 arithmetic the monid row documents (task `task_01a0aaf2c1a3762cb0b54d27dd654484`, 2026-09-16). At 480p treg sits between monid's measured **$0.1029–0.1039** and Higgsfield's effective plan rate (§ Venue ranking) | duration integer; 480p / 720p / 1080p; ≤30 image URLs of ≤30 MB each, every one answering the vendor's HEAD probe; prepaid balance, no plan, $1.00 free on a new team | the BytePlus **advanced creation rights** path wrapped server-side — the image is registered as a digital character and generated from, which is the licensed-asset escape monid's row says it does not expose. An ORDINARY person's likeness is accepted here **and on the Higgsfield API** (measured 2026-09-18) — ⚠ **not "nowhere else", which this row claimed until that test**; fal is the row that refuses ANY photoreal person; clearance for that likeness is a client-side question, never a venue one. 🔴 **`content_filter: false` IS NOT A BLANKET BYPASS — MEASURED 2026-09-18, $0.00.** It relaxes the real-FACE rejection; a SEPARATE upstream content-safety layer sits behind it and still refuses a real, identifiable **PUBLIC FIGURE**: the same press photo that drew `nsfw` from the Higgsfield API came back here as **`status: failed`, `usage.credits: 0`, BytePlus error `80006` "Your prompt or input was rejected by the content safety system"** — the flag was set to `false` and the refusal fired anyway, so it is a DIFFERENT layer from the one the flag controls. Reserve then full release in the treg ledger, balance unchanged (task `task_01a0b11948be721f945c01a9cd5779a6`). ⇒ never quote this row as "takes any real likeness"; it takes an ordinary one, and so does the Higgsfield API. The whole matrix, measured 2026-09-18 for $0.5757 total: **public figure — refused on both; ordinary face — accepted on both; fal — refuses either** | **the CLI is mandatory for anything carrying a file** — the treg MCP exposes no host or upload tool, and its own `call` description says to shell out (`treg call <id> --upload name=@<path>`). `treg host <file>` mints a byte-exact public URL (7-day TTL); never a paste host (catbox, tmpfiles, uguu and a `replicate.delivery` URL each failed the vendor's probe — five dead submissions). Poll `treg call reapi.tasks.get --query id=<task>`: a catalog id takes `--query` / `--data`, **never a URL path**. ⚠ **Seed: the catalog schema DOES list a `seed` integer** (read 2026-09-18) while this row has long said there is none — one of the two is wrong and neither has been measured. Treat a run as a fresh roll until a receipt settles it. Cap one call with the `X-Treg-Max-Cost` header; `X-Treg-Cost-Micro` comes back on the response. Output URLs last ~7 days |
| **monid · `bytedance /v1/video/seedance-2.0`** — **PRICED, NOT ADOPTED** | same content shape as 2.5 on THIS gateway — 🔴 but **the 2.0 family's caps are NOT 2.5's, and the gateways disagree.** fal's schema (2026-09-17) enforces 2.0 at **`image_urls` ≤ 9 · `video_urls` ≤ 3 · `audio_urls` ≤ 3** as real `maxItems`, and **duration 4–15 s**, against 2.5's 30/10/10 and 4–30. monid documents 2.0 as 4–30. Read the cap off the GATEWAY you are calling, never off the model name — and note that fal states 2.0's caps STRUCTURALLY (`maxItems`) while stating 2.5's only in prose | **$7.0/1M** at 480p/720p · **$7.7** at 1080p · **$4.0 at 4K** — the only 4K Seedance here ⇒ 480p **$0.0673/s**, 30 s $2.02 | up to 4K; 4–30 s | as 2.5 (same upstream moderation) | p50 **127 s** / p95 189 s — ~2× faster than 2.5. Listed so the price is known, not so it is chosen: the dialects are calibrated on 2.5 |
| **monid · `bytedance /v1/video/seedance-2.0-fast`** — **PRICED, NOT ADOPTED** | as 2.0 | **$5.6/1M** ⇒ 480p **$0.0538/s**, 30 s $1.61 | 480p/720p | as 2.5 | p50 **185 s**. `video-prompt-dialects` already scopes 2.0-fast to the **draft** engine only |
| **monid · `bytedance /v1/video/seedance-2.0-mini`** — **PRICED, NOT ADOPTED** | as 2.0 | **$3.5/1M** ⇒ 480p **$0.0336/s**, 30 s $1.01 — **3× cheaper than 2.5** | 480p/720p | as 2.5 | p50 **124 s**. The cheapest Seedance here and therefore the strongest pull off the SOP — which is exactly why the marker is on it |
| **monid · `alibaba /v1/video/wan3.0`** — **PRICED, NOT ADOPTED** | text, frames, reference media, documents or links | **$0.05/s at 480P, FLAT per SECOND** (720P $0.10 · 1080P $0.20) — no token math, no `auto` hold | up to 30 s | unmeasured here | p50 **152 s**. `wan3.0-prime` is $0.068/s at 480P and ~2.4× faster (p50 63 s). **This corpus carries no prompt dialect for Wan** — adopting it is an extraction, not a table row |
| **monid · `sfs`** (Simple FS — the reference-hosting lane, and the reason no venue here is blocked on "needs a public URL") | FIVE endpoints, all free: `/put` → `curl -T <file> '<uploadUrl>'` → `/cat` → a signed URL any third party can fetch → `/rm`; `/ls` to browse; `/mv` to rename or move. **`/cat` returns `expiresAt` (ISO 8601) beside the url, and the url carries its own `?e=<unix>`** — so expiry is checkable LOCALLY at zero calls, and survives a lost ledger. **`/ls` takes `recursive` and returns `entries[]` of `{path, type, sizeBytes, lastModified}`** (cursor-paginated, limit ≤1000), so **ONE call verifies a whole 30-reference set** rather than one call per reference | **$0.00 PER_CALL on every endpoint**, 1 GB free per workspace | `sizeBytes` is REQUIRED on `/put` and is a cap **pinned into the signed URL** — an oversize upload is rejected MID-STREAM. `ttl` (`1h`/`1d`/`7d`/`30d`) bounds the **URL**, never the file's lifetime: an expired URL just needs a fresh `/cat`, which is free | — | **PROVEN end-to-end 2026-09-14 at $0.00** (put → upload HTTP 200 → cat → public fetch HTTP 200 → rm → NOT_FOUND). ⚠ **`/rm` revokes the LINK; it is NOT a recall of a copy already served.** Re-measured 2026-09-14 on two probes: a URL **never fetched** returned `404 link not found or expired` the instant it was removed, and `/ls` agreed `NOT_FOUND` (n=1); one **fetched before** the removal still returned 200 afterwards (n=1) — an edge cache, not a live file. Treat any sfs URL that has left the machine as public until its `ttl` lapses, and choose the `ttl` on that basis for a client's own assets. ⚠ **raw PUT (`curl -T`), never multipart `-F`**. Files **NEVER auto-delete** — `/rm` frees quota (`recursive` for a dir, `force` tolerates a missing path); `/put` also returns a `monid resources release -r <id>` hint. ⚠ **run-generated files are NOT listed by `/ls`** — a generation's output lives at the run's own ~24 h URL; `/put` it back if it must persist. **The lifecycle is neither Higgsfield's nor kie's:** the FILE persists forever, the URL lapses with its `ttl`, and re-issuing is a free `/cat` that moves no bytes — so `monid_upload.py` hosts idempotently (skipping on a matching sha256, re-uploading when the local file CHANGED) and `--refresh` re-issues, while `--verify` runs the one recursive `/ls`. A lapsed url FAILS the refs gate before the GO |

**Venue ranking (operator ruling 2026-09-14) — and the one thing it does NOT decide.**
Rank by **marginal cost**, and prefer **pay-as-you-go over plan lock-in** at equal cost. A plan's TRUE
rate is its price ÷ the credits **actually burned**, never the credits granted, and purchased credits that
expire are a cost the per-second rate hides. **NEVER rank a venue by its current balance** — a low wallet
is a funding question, never a priority signal.

**This ranks the VENUE for a fixed model and shape; a MODEL swap is a separate decision with a separate cost, and
it belongs to the operator** (`SKILL.md` § 0 — constraints guide, never block). Seedance work defaults to **2.5 at
480p**. A cheaper trunk in the table above is not off the table; it is **cheaper AND uncalibrated**, and the second
half is what has to reach the operator with the first. **Surface the swap with its real price: the saving per second
on one side, and on the other the dialect re-calibration** (`video-prompt-dialects` is tuned on 2.5) **plus a
proving run on the HARDEST shot** (`SKILL.md` § 1) — never the easiest. Recommend staying on 2.5 when the batch is
small enough that the saving cannot repay the proving run, recommend the swap when it can, and say which it is.

A subscription's true rate is what the month actually cost divided by the credits actually burned, so a
light month (credits expire) and a heavy month (top-up packs at retail, often on their own expiry clock)
both push it above the headline. Spiky, client-driven demand is what makes pay-as-you-go win on the same
model. Price your own two routes that way before choosing, and re-measure when either vendor moves.

**A plan and a PAYG API from the SAME vendor are two venues, not one — price them separately.** ⚠ Their
wallets are usually SEPARATE pools: topping up the API may not show in the CLI's `account status`, which
keeps reporting the plan. Moving off a plan onto the vendor's API is rarely justified on price alone; the
reasons that hold up are static-key auth in place of short-lived OAuth, credits that expire in a year
rather than a month, and endpoints the plan does not expose.

🔴 **The measured ladder, 9:16, per second of output — the API places FOURTH of five at BOTH rasters.**

| venue | 480p | 720p | real likeness | audio ref |
|---|---|---|---|---|
| **monid** `bytedance /v1/video/seedance-2.5` | **$0.1029–0.1039** | **$0.2311** | ❌ refused upstream | ✅ |
| **treg** `reapi…seedance-2-5.unrestricted` | $0.1186 | **$0.2668** | ✅ licensed-asset escape | ✅ |
| Higgsfield CLI (blended plan, now closed) | $0.1213 | $0.3153 | ✅ | ✅ |
| **Higgsfield API** (30 % launch discount applied) | $0.144 | $0.324 | ❓ untested | ✅ |
| fal `bytedance/seedance-2.5/*` | $0.2205 | $0.4730 | ❌ `content_policy_violation` | ✅ |

⚠ **Higgsfield's own "Compare prices with others" page benchmarks against fal ALONE, and fal is the dearest
Seedance venue in this table — 2.1× monid.** *"The best prices on the market"* is true against the market they
chose. 30 % under fal still lands above both working routes. **Read which baseline a discount is against before
quoting it:** on `/models-api-pricing` the struck price is Higgsfield's own list ($0.2057 → $0.144); on the compare
page it is **fal's** price ($0.2205 → $0.1544). Same product, two different "30 % off" numbers.

🟢 **Where the API DOES win: `video-edit` / `video-extend` at $0.0864/s** (480p, 0.6× tier) — under monid's
$0.1029/s, and treg has no row for either. **Bounded by the arithmetic of that tier**, which bills input seconds
too: `(in + gen) × 0.6` beats a fresh `gen × 1.0` only when **`gen > 1.5 × in`**. Extending a 5 s keeper by 5 s
bills 6 effective seconds against 5 for a fresh take — **dearer**. Extending a 4 s keeper to 30 s bills 20.4
against 30 — **much cheaper**. ⚠ The same arithmetic condemns the black-video VO-carrier trick on this API: a 7 s
generation against a 7 s video reference bills 8.4 effective seconds, **20 % over** passing the VO as an
`audio_url`, because audio references are not video input.

🟢 **MiniMax H3 on the API is $0.0715/s at 2K — HALF what Seedance costs at 480p on the same venue**, and it is a
fixed per-second rate, not token-metered (`/estimate` measured it linear: 6 s $0.429, 15 s $1.073; list $0.13/s,
45 % off). ⚠ Three gates before routing to it: **no audio input**, so it cannot serve the locked-VO talking head ·
5–15 s only · and `reference-to-video` charges **$0.08 per reference image past the first five**, so a 30-reference
set adds $2.00 before discount — **more than double the take itself**. Cheap for reference-light non-speaking
shots; the wrong shape for our 30-ref continuity sets.

**`POST /estimate/<endpoint-id>` returns TWO shapes — read `type`, never assume a number.** For a **fixed-price**
model it returns `{"type":"estimate","credits","usd","discount":{"percentage","credits","usd"}}`, where `usd` is
what the account actually pays, `discount.usd` is the saving, and list = the sum — **this is the authoritative
account-specific cost line, and the launch discount is already inside it** (verified against the compare page:
Kling 3.0 std list $0.126/s, ours $0.1071/s). For a **token-metered** model — every Seedance 2.5 and 2.0 endpoint,
at both rasters, on all four workflows — it returns `{"type":"description","pricing_description": "<the formula>"}`
with **no number at all**, so the cost gate must COMPUTE. Account conversion is **$0.0625/credit**, consistent
across four models. The call is free. ✅ The formula came back verbatim on 2026-09-18 and closes with *"Rates shown
are before any applicable customer discount"* — which is why every computed line here quotes **list beside net**.

#### The lane as BUILT (2026-09-18) — four scripts, and what each one exists to stop

`hf_api.py` (the formula, the wire, the wallet) · `hf_api_upload.py` · `hf_api_submit.py` · `hf_api_poll.py`.
The refs-gate target is **`hfapi`**, whose reference ledger is `<root>/hf-api-urls.json`.

- **The COMPUTED cost line.** `hf_api.py quote` evaluates `ceil((in_s + gen_s) × W × H × 24 ÷ 1024) × rate`,
  applies the dated discount, and prints three figures: the **net** (what it should cost), the **list** (what it
  costs if the launch discount has quietly lapsed), and the **+1-frame ceiling** — because ByteDance's published
  formula was measured short by exactly one frame on monid and **no Higgsfield receipt has settled which one bills
  here**. Verified against the vendor's own list price to four decimals: 480p $0.2056/s, 720p $0.4622/s.
- **The WALLET LEDGER, because there is nothing to read back.** `$HF_API_LEDGER`, default
  `~/.local/state/higgsfield-api/ledger.json`. `hf_api_submit.py` writes a **spend at acceptance** (billing happens
  there, not at fetch) and `hf_api_poll.py` writes the matching **refund** for a `failed` / `nsfw` / cancelled
  request, which are not charged — without that refund the only copy of the wallet drifts low on every refusal.
  ✅ **The refund arm is PROVEN, not theoretical**: the real-likeness probe of 2026-09-18 landed `nsfw`, and the
  ledger went spend $0.5757 → refund $0.5757 → wallet unchanged at its loaded figure.
  Record your own purchase with `hf_api.py load --usd <paid> --credits <received>`, which also sets the
  wallet's $/credit rate from it. Every line in that ledger is an ESTIMATE, never a receipt — Seedance
  returns no number, so nothing on the vendor's side can ever correct it.
- 🔴 **The presigned PUT signs `content-type;host;x-amz-tagging`** (measured). Add, drop or replace one of those
  headers and S3 answers **`403 SignatureDoesNotMatch`** — which reads exactly like a bad key and is actually your
  own header. Our `Content-Type: application/octet-stream` was the cause; `curl -T` with the vendor's returned
  headers verbatim is the fix. **Never send the Higgsfield credential to the presigned URL** — different host, and
  the signature is already in the query string.
- 🔴 **Uploads are tagged `x-amz-tagging: retention=temporary`** — so a hosted reference is **explicitly transient**
  and **no window is documented anywhere**. The gate therefore WARNs rather than passing, and names the free fix:
  `hf_api_upload.py --verify` is a HEAD per URL at zero cost, which is the only thing that turns "unknown" into a
  fact. (This is also why `hfapi` is `EXPIRING: True` in the gate despite carrying no `?e=` in the URL: a free
  remote check exists, where treg's opaque token has none.)
- **`GET /models` shape:** `{"total": 76, "items": [{slug, title, operation_type, output_type, base_credits}]}`.
  H3's slugs are `minimax/h3/{text,image,reference}-to-video`; Seedance 2.5 carries all five.
  `base_credits` is `"0.0000"` on every row — **never read a price out of that catalog, only the slug set.**

**Price ranks the venues; FUNDING decides which ranked venue is reachable today.**
Fourth on price is a premium to quote, never a prohibition. The two rules do not collide, and the difference is
worth stating because it is easy to blur: *"never rank a venue by its current balance"* forbids **demoting** a
venue for holding a low wallet — it does not oblige you to route work to a venue you cannot pay for. **Where the
money actually sits is a hard constraint on which venue is callable at all.** So the Higgsfield API is a legitimate
Seedance route, at any raster, whenever that is where the funds are allocated; it is simply not the route chosen on
price. **Quote the premium in the cost line and let the operator rule** — it is **1.40× monid** and **1.21× treg**,
so a fixed budget buys about **29 % fewer takes than monid** and **17 % fewer than treg**. Never silently reroute a
batch to a cheaper venue the operator has not funded, and never refuse a funded one for being fourth.

### What the Higgsfield API does that NO other row does — and what the move gave up

**Only here.** Route to the API for these on merit, not on price:

- 🟢 **`video-edit` and `video-extend` as STRUCTURALLY SEPARATE endpoints.** treg carries no row for either.
  monid reaches both, but **by prompt phrasing** — and that is the failure this table already documents: say it
  unclearly and the model reads it as a plain r2v, generates a NEW video, **succeeds, and bills in full with no
  error to catch**. fal reaches both through a `task` enum on one endpoint, so a wrong enum value has the same
  shape. **On the API a misread is impossible by construction** — different URL, different contract. Billed at the
  0.6× tier, bounded by `gen > 1.5 × in`. This is the strongest single reason the API exists in this table.
- 🟢 **The cheapest 2K MiniMax H3 in the stack — $0.0715/s against fal's $0.13** (45 % under). ⚠ fal refuses
  photoreal people on any reference while the Higgsfield CLI's `minimax_h3` **took the family references fal had
  refused**, so the API's H3 may inherit that tolerance — **untested, and a refusal is free to find out.**
- 🟡 **A 76-model catalog under ONE static key** (`GET /models`): Kling 3.0 std/pro/4k/turbo/motion-control,
  **Kling O3 and Kling Omni** (each with their own `video-edit` and `video-reference` routes), Wan 3.0 /
  3.0-prime / 2.6 / 2.7, LTX 2.5 fast+pro, Happy Horse 1.0/1.1, Qwen Image 3, Recraft 4.1, Ideogram 4, Grok
  Imagine, Marketing Studio, Soul / Soul 2 / **Soul ID** (a `character` operation type — the nearest thing in any
  catalog to the locked-JSON identity problem `video-refs-continuity` carries, and entirely unexplored here).
  **This is OPTIONALITY, not capability:** none of it is proven, and a new model is proven on the HARDEST shot
  first (`SKILL.md` § 1), never adopted from a catalog listing.

**Given up in the move — each one a thing the CLI or another venue still does better:**

- 🔴 **The job-id extend handle is GONE.** The CLI extended a keeper by its own **job id**, with nothing
  re-uploaded; the API's `video-extend` takes a `video_url`. ⚠ **Probably recoverable at $0:** API outputs stay at
  a public URL for **≥ 7 days**, so a keeper's own output URL should feed straight back in. **UNTESTED — one
  receipt settles it**, and until it does, plan an extension as an upload.
- 🔴 **No cost cap.** treg refuses a call above `X-Treg-Max-Cost`; the API has no equivalent. That bites hardest
  precisely here, because Seedance returns **no estimate number** — the gate's own arithmetic is the only bound
  between a typo in `duration` and a full charge.
- ⚠ **No balance endpoint** (the wallet is unreadable, § the row above) · **no 1080p Seedance** · **no Topaz, no
  GPT Image 2.5, no Nano Banana Pro, no lipsync** — all covered elsewhere, but not here.

**Real likeness routes to treg, not to Higgsfield.** A reference carrying a real person's
likeness is refused upstream on fal and on monid, and monid exposes none of BytePlus's licensed-asset
escapes; treg's `reapi.video-gen.seedance-2-5.unrestricted` row carries the rights path that makes it legal. At 480p it
is **$0.1186/s PAYG** with no plan behind it, so the ranking doctrine above reaches it without a tie-break.
Higgsfield keeps the shots neither treg nor fal has a row for: `topaz_video`, and `minimax_h3` at 2K — and it
keeps `video_extension` on a KEEPER'S JOB ID, which is a different thing from continuing an uploaded file.
⚠ **Corrected 2026-09-17 from fal's own schema: edit and extend are NOT Higgsfield-only.** fal reaches both on
`bytedance/seedance-2.5/reference-to-video` through its `task` enum (`editing` / `extension`), so the line that
read “Higgsfield keeps `video_extension` … `video_edit`” was wrong. What Higgsfield still keeps is the job-id
handle: fal continues a video you re-upload, not a take it already generated. **Measured once** — a single 4 s take, so the per-second rate is confirmed and nothing about drift past 4 s is.

🔴 **Before dropping a plan for its vendor's API, audit what the plan held ALONE — then name the cover for each
item.** Read the API's own catalog rather than assuming parity: Higgsfield's `GET /models` carries **no Topaz, no
GPT Image 2.5, no Nano Banana Pro and no lipsync/dubbing**, all of which the CLI reaches. Here each has a cover —
Topaz runs locally (the wrapper drives Topaz's own bundled `ffmpeg`, with local Rhea and fal's hosted Starlight
beside it), stills already route to kie first, lipsync is fal `sync-lipsync/v3` — and the one uncovered loss is
**Higgsfield-native 1080p Seedance**, which treg serves at $0.462/s. ⚠ Not everything moves the wrong way:
`minimax_h3` at 2K is **cheaper** on the API ($0.0715/s) than on the plan (2 cr/s). **Do the audit item by item;
a catalog listing is not parity and an absence is not a loss until you have looked for its cover.**

**The 480p chain — still the default for EVERY shot except the talking head:** generate at 480p, approve, THEN
reconstruct up (Rhea ×4 local, or Starlight from the take for distant faces). The upscaler run once on the selected
footage is cheaper than prompts ×5–10 at a higher raster, and that argument is about the SEARCH, not the take: you
pay the raster premium on every rejected seed as well as the keeper. 🔴 **The one carve-out: a talking head with a locked VO generates at 720p** (§ The talking-head default) — there the search is
short because the audio pins the performance, the face is the whole frame, and the delivery raster is 1080p, so a
1.5× resample beats a ×4 reconstruction. **Everywhere else 480p is what gets RECOMMENDED — not what gets enforced:
quote the 2.25× and what it moves downstream, then generate at whatever raster the operator rules** (`SKILL.md`
§ 0). Seedance
re-renders frame 0 from a start image (composition, blocking and light carry; pixel exactness does not); i2v output
aspect = the frame's. ⚠ **720p costs 2.25× 480p at every token-metered venue** — monid, treg and the Higgsfield API
alike, because all three meter on `W × H`. It is never a free upgrade, and the carve-out is priced, not waived.

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
→ **audio-driven Seedance 2.5 at 720p, delivered through a 1.5× scale** when a locked VO must land on the mouth,
else Omni Flash 1.1 (§ The talking-head default); a hook sweep → Omni 1.1 at 360p;
product-in-hand or a 30 s story → Seedance 2.5 (the label is drawn, never read — keep it as an image reference and the
label shot short and front-on); a defined handheld move ≤ 8 s → Kling; the words that must land exactly → an
audio-driven model or a lipsync pass, never a prompt. Every take
carries SynthID or C2PA: the platform's auto-label is expected, never dodged (`ad-spot-preprod` RISKS.md § UGC compliance).

#### The talking-head default — audio-driven Seedance 2.5 at 720p, upscaled 1.5× (SUPERSEDES the 1080p-native default below)

🔴 **Every talking head — UGC or commercial ad — generates at 720p on a venue that takes an audio reference, and is
delivered at 1080p through a 1.5× scale.** At the prices below, 720p plus a scale is worth more than 1080p native
on this chain — the saving is ~42 % a take and the delivered raster is the same. **Everything below the raster is
unchanged** — the audio reference still drives the WORDS, the
lipsync pass still disappears, the words still never appear in the prompt.

🔴 **On price the route is treg (real likeness) or monid (people-free); the Higgsfield API places fourth at this
raster** (§ Venue ranking). **treg $0.2668/s · monid $0.2311/s · Higgsfield API $0.324/s.** A 7 s take: **$1.87 on
treg against $3.23 at 1080p** — the ruling buys ~42 %, and the audio-driven route survives intact on all three.
1080p stays reachable on treg at $0.462/s for a shot that earns it; the API cannot serve 1080p at all.
⚠ **Fourth on price is not a prohibition — see § Price ranks the venues, funding decides which one is reachable.**
The API is a legitimate Seedance route when that is where the money is; the premium is 1.40× monid and 1.21× treg,
and it is quoted in the cost line rather than argued about.

🟢 **The upscale arm is already decided, already measured, and costs $0.** On a 720p take the operator judged the
**RAW better than the Starlight'd version**, and the delivered shape became a faithful **1.5× lanczos to 1080×1920
with the grade, no reconstruction** (2026-09-15/16, § Upscale tiers). That is exactly this job. **Reconstruct only
when the source is genuinely under-rendered** — small faces, 480p. 720p also cuts the risk the upscaler carries:
a head that is ~50 px at 480p is ~75 px at 720p, and the job drops from ×4 to ×1.5. ⚠ **Nobody benchmarks ×1.5**,
so a SeedVR2 / Rhea / Starlight A/B at that factor is ours to measure — free on the local card — and until it runs,
lanczos is the default, not a fallback.

**Which venues take an audio reference — read free from each vendor's own schema, 2026-09-17/18.** The default raster
is **720p** (the ruling above), so the **720p column is the one that picks the route**. The 1080p columns stay because
a shot occasionally earns 1080p — and because they are what show, at a glance, the one thing the API gave up.

| route | audio in | **720p price** | 1080p | 1080p price | notes |
|---|---|---|---|---|---|
| **monid `bytedance /v1/video/seedance-2.5`** — **the people-free 720p default** | `audio_url` role `reference_audio`, ≤ 10, each 2–30 s, ≤ 30 s total | **$0.2311/s** | ❌ | — | 480p/720p only. **Cheapest route at the new default raster**, and the token rate is flat across both rasters so the 2.25× is pure pixels. Real human faces are refused UPSTREAM (BytePlus ModelArk) and monid exposes no licensed-asset escape ⇒ a real likeness routes to treg |
| **treg `reapi.video-gen.seedance-2-5.unrestricted`** — **the real-likeness 720p default** | `audio_urls` ≤ 10 | **$0.2668/s** | ✅ | **$0.462/s** | model `doubao-seedance-2.5-face`; the ONLY row documenting *"a photo of a real person is accepted as the subject reference **and a voice clip as the speech reference**"*; 100 % over 244 observed calls; refunded on failure; `treg host <file>` mints a compliant URL free |
| **Higgsfield API `bytedance/seedance-2.5/reference-to-video`** | `audio_urls` 1–10 — ⚠ **WAV only on upload, no MP3** | $0.324/s | 🔴 ❌ | — | added 2026-09-18. **No 1080p at all** — the one regression that moved this default to 720p. Fourth of five on price at both rasters (§ Venue ranking). Real-likeness posture UNTESTED. `audio_urls` survives the move intact, which is why the audio-driven method below still runs here unchanged |
| **Higgsfield CLI `seedance_2_5`** — the subscription route | `audio_references` (array) | 6.5 cr/s ≈ $0.3153/s | ✅ | **9 cr/s ≈ $0.45/s** (480p 3) | the route the 09-17 ruling was proven on: two takes landed 1080×1920 in ~3 min each. `--audio-references` takes a UUID **or a local path the CLI auto-uploads**. Reachable only while plan credit remains; no further credit is going on it |
| treg `piapi.video-gen.seedance-2-5` | `audio_urls` ≤ 3, 15 s total | — (unread) | ✅ | $0.80/s | dearer, tighter cap |
| **fal `bytedance/seedance-2.5/reference-to-video`** | `audio_urls` ≤ 10, MP3/WAV, each 1.8–30.2 s and ≤15 MB, **combined ≤ 30.2 s** | $0.4730/s | ✅ | **$1.164/s** | added 2026-09-17 from fal's own schema — the table had no fal row and claimed to enumerate every audio-taking venue. **The DEAREST row here at every raster**, so it is completeness, not a route: take it only when fal is already the lane for other reasons. ⚠ **at least one image or video reference is required alongside the audio**, and fal refuses `likenesses of real people` on any reference — so this row CANNOT serve a real-likeness talking head at any price |
| treg `openrouter.video-gen.seedance-2-5` | none | — | ❌ | — | first/last frame only |

Providers disagree on the duration cap — one enforces ≤ 30 s **per clip** (probed at submit), another a 30 s **combined**
cap. Unresolved; a measured run settles it. Reference **images and audio do not move the price**; only a reference VIDEO
does (it shifts the upstream generation mode).

**The method, in the order it has to run:**
1. Cut the driving audio **from the programme VO itself**, frame-exact, so the take maps onto the timeline with no
   arithmetic left over. Silence the tail before the next line so it cannot leak in.
2. **The reference-carrying call, named per venue** — a text-to-video call refuses every reference, audio included:
   `omni_reference` on the Higgsfield CLI · `r2v` on monid · the r2v body carrying `@audio1` on treg ·
   `POST /bytedance/seedance-2.5/reference-to-video` on the Higgsfield API. A start image is legal beside the audio.
3. **The words never appear in the prompt.** Point the lip-sync at `@Audio1`, forbid replacement speech in the tail,
   and pin the VO's own speech windows as numeric beats.
4. **A 1.5× scale to 1080×1920 — NOT a reconstructive upscale.** The take lands at 720p and delivery is 1080p, so
   the finish is a faithful lanczos carrying the grade; the operator judged the raw better than the reconstructed
   version at this raster. Reconstruct only for a genuinely under-rendered source (small faces, 480p). Then the
   Dehancer hero. ⚠ `.drx` and `.cube` are PARALLEL renderers of one look, never stacked — `look-library/GUIDE.md`.
5. Accept the residual timing, or re-roll. **A post retime is judged by eye, never by its metric.**

**What the three defaults cost, 7 s, in the order they were ruled.** Omni 720p + a `sync-lipsync/v3` pass ≈ **$1.63**
(09-17 morning) → Higgsfield CLI 1080p native 63 cr ≈ **$3.15** (09-17 evening) → **treg 720p $1.87 + a $0 lanczos**
(09-18). The middle ruling bought a real quality step and is the reason the raster question is not a free one: at 1080p
native the skin keeps individual stubble hairs and pores where the lipsync chain returned a waxy chin and jaw with the
stubble rendered as a texture patch. **What 2026-09-18 changes is the raster, never the audio-driven method** — the
lipsync pass stays gone, so the waxy-chin failure does not come back with it; what returns is a 1.5× scale, which is a
resample, not a reconstruction. A shot that cannot afford even that goes to treg at 1080p for $3.23.

⚠ **Higgsfield's Lipsync Studio lists SYNC LIPSYNC 3** ("precise lip sync, up to 4K") — the model fal resells at
$8/min — **but it is WEB-UI ONLY**: absent from all 91 CLI job types and all 22 workflows (only `dubbing` and
`voice_change` are there). Not automatable today.

<details><summary>The superseded default — Omni Flash 1.1 + fal lipsync (same-day ruling, kept for the evidence)</summary>

**Every talking head starts on Omni Flash 1.1 and gets a `fal-ai/sync-lipsync/v3` pass against the locked VO.** UGC and
commercial ads alike; Seedance 2.5 keeps product-in-hand, the 30 s story and — through treg's unrestricted row — a real
person's likeness. The ruling is the operator's, from a two-version A/B on a 30 s trust-series episode (2026-09-17):
Seedance 2.5 480p + lipsync against Omni Flash 1.1 720p + lipsync, two of the four lines swapped, judged by eye.

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

</details>

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
