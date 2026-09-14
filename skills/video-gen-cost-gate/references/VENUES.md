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

**The 480p chain:** generate at 480p, approve, THEN reconstruct up (Rhea ×4 local, or Starlight from the
take for distant faces). Never propose 720p/1080p generation; the upscaler run once on the selected
footage is cheaper than prompts ×5–10 at 720p. Seedance re-renders frame 0 from a start image
(composition, blocking and light carry; pixel exactness does not); i2v output aspect = the frame's.

**Face gate per model version** (image → video start frames): 2.0-fast/480p landscape cleared at faces ≤
~60 px; 2.5/9:16 on fal refused at ≈ 27 % of frame width at every pixel size. Higgsfield's omni mode
accepts the same people. Photoreal portrait plates are the deepfake-reference shape: compose the figure
into a scene rather than passing a face plate.

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

`higgsfield account status` (credits); kie and AceData expose no balance endpoint → track spend from the
receipts and say "unreadable via API", never "0". Every status message to the operator carries the
balances (credits, dollars, TTS characters) and the free disk on the render drive.

## Secrets

Keys live in the kit's `.env`, copied from `.env.example`, and are loaded in the same command that needs them
(`set -a; . ~/.claude/skills/video-production/../../.env; set +a`; `KEY=value`, no `export`, no quotes). A key pasted in
chat is rotated after use. Never printed, never in a receipt, never in a skill.
