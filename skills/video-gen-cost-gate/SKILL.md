---
name: video-gen-cost-gate
description: >
  The generation call and its GO: picks the venue (Higgsfield Seedance 2.5, fal Seedance/H3, kie
  image models) for a video seed or a still, prints the cost line with the refs-gate table and waits for
  the operator's explicit go, submits through the one gated path, persists the receipt at the moment the
  venue accepts the job, polls detached, and hands the landed seeds to the operator as clips. Use when a
  seed, still, extension or upscale is about to be bought, when credits or dollars are being estimated,
  when a job hangs, refuses (nsfw, content policy), 503s or is refunded, or when a poller must be armed.
  Triggers — "cost line", "GO", "how many credits", "submit the seeds", "poll the takes", "refunded",
  "nsfw refusal", "which venue", "fal or Higgsfield", "kie still". Not for building the reference set
  or the start image the call needs — use video-refs-continuity. Not for the prompt's wording — use
  video-prompt-dialects. Not for upscale or grade — use video-finish.
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3*), Bash(higgsfield*), Bash(ffprobe*), Bash(ls*), Bash(df*)
---

# Video Gen & Cost Gate

Every generation call is production: nothing is bought on a test, and nothing is bought without the
operator's explicit **GO** on a cost line — however small the amount. The
call itself goes through ONE gated path per venue, so the refs gate, the cost, the receipt and the
poller cannot be skipped by hand. Three words carry the method: **GO** (the operator's yes to a named
cost, per batch, never standing), **receipt** (the venue's job handle persisted the instant it accepts
the job — billing happens at acceptance, not at fetch), **clip** (a landed seed reaches the operator as
a file path; the pick is theirs).

**What varies.** The venues, prices, modes, caps and the stills model are the established chain's, dated in
[`references/VENUES.md`](references/VENUES.md); the balance sets the batch size (a venue with no balance endpoint records it
as *unreadable* — never 0, never a guess — and the GO's cap is that batch's limit). The GO, the receipt, the one gated path
and the clip handover do not move — `video-production/references/WHAT-VARIES.md` § Generator, venue and native raster.

## 0. Constraints GUIDE, they never BLOCK — this governs every rule below

🔴 **Every house rule, default, ranking and "never" in this skill is CONTEXT THAT SHAPES A SUGGESTION, not a
refusal.** Read one as a veto and you have converted the operator's own accumulated evidence into a cage around
the operator. A rule here exists to make the recommendation *better informed* and to make its cost *visible at the
moment of choosing* — never to remove an option from the table.

**The shape every constraint takes:** state what the rule says · state what departing from it costs, as a number
where a number exists · recommend · **then do what the operator rules.** A constraint that cannot produce a
number still produces a sentence; it never produces a stop.

```
❌ "480p is the house rule — I can't generate at 720p"
✅ "480p is the chain; 720p is 2.25× the tokens (+$0.41 on this batch) and moves the face floor,
    the upscale tier and the review limits. I'd stay at 480p. 720p if you want it?"
❌ "That venue is fourth on price, so we use monid"
✅ "monid is cheapest; the funded venue is 1.40× that, +$0.41 here. Which?"
❌ Silently narrow a batch, a venue or a raster to the rule and report only the narrowed result
✅ Run what was asked; put the cheaper or safer alternative beside it with its number
```

**THREE things are not constraints in this sense, and they stay** — none of them blocks the operator:

| what | why it stays |
|---|---|
| **The cost line and the GO** | It blocks *the agent* from spending the operator's money unasked. It is the operator's decision point, not a limit on them — removing it would mean spending without consent, the opposite of guiding. |
| **A pre-submit refusal that protects a BILLED call** (the refs gate on a lapsed URL, `monid_submit.py` on `--duration auto`) | These convert rather than vanish: the refusal becomes a **priced warning inside the cost line**, and the GO overrides it. Never a silent stop; never an unoverridable one. |
| **A VENDOR's own refusal** (`nsfw`, `content_policy_violation`, a `423 model_blocked`) | Not ours to relax. Report it, name what it cost (usually nothing), route around it. |

**Portability — this is why the roster is a parameter, not a constant.** The venue table below is *our* roster and
*our* measured prices. Another operator adopting this skill has a different roster, a different fallback chain and
different funding. So the routing logic is **"rank the venues YOU have by marginal cost, prefer PAYG at equal cost,
then let funding decide which ranked venue is reachable"** — never "use monid". Where a rule names a specific venue,
read the venue as an example of the rule and the rule as the thing that travels.

## 1. Pick the venue from the table

Rule for images and video alike: **quality and prompt-adherence first, permissiveness as the fallback
criterion.** The table — modes, prices, caps, moderation classes, upload conventions — is
[`references/VENUES.md`](references/VENUES.md). The decisions it settles:

- 🔴 **Seedance 2.5 is the video model for every shot; Gemini Omni Flash 1.1 is the default ONLY for a UGC
  talking-head clip** (since 2026-09-26). B-roll, product, equipment, a scene, an image-to-video from an accepted still
  and a commercial talking head all route to Seedance 2.5 on the venues below; Omni's lower step price does not make it
  the default for any of them.
- Video with people in the references → **treg `reapi.video-gen.seedance-2-5.unrestricted`**, the PAYG
  people-capable route ($0.1186/s at 480p · $0.2668 at 720p · $0.462 at 1080p, PAYG, no plan behind it): `content_filter: false`
  carries the BytePlus licensed-asset escape, so it takes a **real person's likeness**, which every other
  row refuses. Its references are hosted by `treg host` and the call is **CLI-only** — the treg MCP exposes
  no upload tool. ⚠ **Higgsfield's subscription and its PAYG API are two venues with separate wallets** — price
  them apart (`references/VENUES.md` § Venue ranking). `seedance_2_5 --mode omni_reference` is the subscription
  route; the **API** carries **no 1080p, no Topaz, no GPT Image 2.5 and no lipsync**, so a move onto it has to name
  the cover for each. `minimax_h3` at 2K runs the other way — **cheaper on the API at $0.0715/s** than on the plan. fal's Seedance refuses any
  photoreal person in a reference (`content_policy_violation`, billed 0) — fal only for people-free
  shots. MiniMax H3 is 768p minimum and a different look.
- **People-free Seedance with no plan to feed → monid `bytedance /v1/video/seedance-2.5`, the
  pay-as-you-go route.** Same model, same 480p house shape as the Higgsfield route, bought by the
  second instead of by the month: **$10.7/1M tokens ⇒ $0.1039/s at 4 s → $0.1029/s at 30 s**, measured.
  Rank by MARGINAL cost and prefer pay-as-you-go over plan lock-in at equal cost — a plan's true rate is
  its price ÷ the credits actually burned, and **a venue is NEVER ranked by its current balance** (a low
  wallet is a funding question; `references/VENUES.md` § Venue ranking). References ride free on monid's
  own `sfs` store (`scripts/monid_upload.py`, $0.00), so "it needs a public URL" never routes work off
  it. **The partition is the same one fal already forces, for a different reason:** real human faces are
  rejected UPSTREAM (BytePlus ModelArk) and monid exposes none of the licensed-asset escapes, so a
  photoreal person in a reference routes to treg's unrestricted row — the escape monid lacks — or to
  Higgsfield when the shot also needs one of its extra modes.
- **A talking head that must carry a LOCKED voice-over → Seedance 2.5 generated at 720p with the VO as an audio
  reference, delivered through a 1.5× scale**, on a venue that accepts one — never a post-generation lipsync pass,
  and never a prompt-voiced mouth (`references/VENUES.md` § The talking-head default, which supersedes both the
  earlier 1080p-native default and the Omni Flash 1.1 + `sync-lipsync/v3` default before it).
  **On price the venue is treg for a real likeness ($0.2668/s) or monid for people-free ($0.2311/s); the
  Higgsfield API places fourth and carries no 1080p at all** — ⚠ **fourth is a premium to quote, not
  a prohibition: where the funds are allocated decides which venue is reachable** (`references/VENUES.md` § Price
  ranks the venues, funding decides which one is reachable). The audio drives the WORDS, not just the
  timbre: both proof takes spoke the script line verbatim. 🔴 **The words must be ABSENT from the prompt** — written
  dialogue beats reference audio and demotes it to timbre (`video-prompt-dialects` DIALECTS.md § Supplied-audio
  polarity). **The lipsync pass stays gone** — that is what the audio reference bought, and it survives the raster
  change; what returns at 720p is a 1.5× lanczos to 1080×1920, a resample rather than a reconstruction, at $0 and no
  face-shaped softening tax. 1080p stays reachable on treg at $0.462/s for a shot that earns it. Omni Flash 1.1 keeps
  only the UGC talking heads with NO locked VO (it takes no audio input on any surface); a commercial talking head with
  no locked VO stays on Seedance 2.5 (since 2026-09-26).
- **An EDIT or an EXTEND, and 2K MiniMax H3 → the Higgsfield API, on merit rather than price.** `video-edit` and
  `video-extend` are **structurally separate endpoints** there: treg has no row for either, monid reaches both only
  by prompt phrasing — which misreads into a fresh r2v that succeeds and **bills in full with no error to catch** —
  and fal routes both through a `task` enum with the same failure shape. A wrong URL is a 404; a wrong phrasing is a
  silent full charge. Billed at the 0.6× tier, worth it only when `gen > 1.5 × in` (both durations bill). H3 at 2K
  is $0.0715/s there, 45 % under fal. ⚠ The API has **no cost cap** (treg takes `X-Treg-Max-Cost`), returns **no
  estimate number** for Seedance, and its `video-extend` takes a `video_url`, **not the CLI's job id** — feed the
  keeper's own output URL back (outputs live ≥ 7 days; untested, one receipt settles it).
- **A person or object swapped into an EXISTING clip → the Higgsfield API's Genjutsu** (`--model genjutsu --mode
  object-swap`, or `motion-transfer` to drive a reference with the clip's motion) — the one route that re-casts
  footage we already hold. Priced per second of INPUT, rounded up ($0.318 @480p, list); the source is the gate's
  start image and its length is probed, never typed (`references/VENUES.md` § Video).
- **A prompt for an audio-driven take carries the VO's own speech windows as numeric beats** — it fixes the ENDPOINT
  (end-of-line error 0.83 s → 0.06 s, measured) but not the interior: the model buys the ending by elongating one word.
  🔴 **Do NOT repair the residue by retiming in post on the strength of a metric** — two repairs measured better and were
  rejected on sight as dropped frames. Judge a repair by eye against the unrepaired take, or re-roll.
- A continuation of a keeper → `--mode video_extension` on the keeper's own job id (same price as a
  fresh gen). On monid the edit and extend modes are **phrasing, not flags** — say so explicitly in the
  prompt or the model reads it as a plain r2v, generates a NEW video, succeeds, and bills in full with
  no error to catch (`video-prompt-dialects` DIALECTS.md § Seedance 2.5).
- Stills → **GPT Image 2.5 is the default image model for every still, plate and reference, and kie is the
  FIRST venue for image gens (house rule, 2026-09-10)**: kie `gpt-image-2-5-flare-image-to-image` ($0.05 at
  2K; validated 09-10 — one still matched the scene proxy's end table with no invented element), Higgsfield
  `gpt_image_2_5` second (2–2.5 cr at 2k; `--variant sunburst` for the precision tier); **Nano Banana Pro is
  the fallback** —
  surgical edits (a count, a ghost, one limb) and garment text the OpenAI-moderated model refuses (kie
  `nano-banana-pro` / Higgsfield `nano_banana_pro`), or the copy route (`video-refs-continuity`). GPT Image 2
  is superseded; never start a new still on it.
- Generation resolution is **480p on the 480p chain — every shot except one**; MiniMax H3 generates at its 768p
  minimum on fal (a house rule) or at 2K, its only tier, on Higgsfield; approval, then a reconstructive upscale
  (`video-finish`). 🔴 **The carve-out: a talking head with a locked VO generates at
  720p** and finishes with a 1.5× scale. A take generated above 480p moves every pixel number downstream — the face
  floor, the upscale tier, the review instruments' limits — so the carve-out is per-shot and stated, never inferred.
  ⚠ **720p costs 2.25× 480p at every token-metered venue** (monid, treg, the Higgsfield API all meter on `W × H`):
  it is priced, never free — so outside the carve-out 480p is the RECOMMENDATION, with the 2.25× and the downstream
  moves quoted beside it, and the operator rules the raster (§ 0).
- A new venue or model is proven on the HARDEST shot first (a lipsync line, the product close-up),
  never the easiest — passing the easy spot proves the chain runs, not that the hard parts work.
- **A creator-style talking head** (a UGC spot) routes by SHOT TYPE: a simple talking head or a hook sweep → Gemini Omni
  Flash 1.1, **kie first, fal the fallback** (since 2026-09-25: kie `google/gemini-omni-flash-1-1` is $0.525 per
  8 s at 720p or 1080p against fal's $0.80 / $1.20, sold in fixed 4 / 6 / 8 / 10 s steps — fal takes any whole second
  3–10 s, and a 360p draft or a 3 s take is cheaper there, so the cost line quotes both; 720p native, no uploaded audio,
  ~15 % of takes stutter → regenerate); every other shot in the spot — product-in-hand, b-roll, a 30 s story, a pinned
  voice, a defined handheld move — → Seedance 2.5 (since 2026-09-26, Omni is the default for the UGC
  talking-head clip only; Kling 3.0 ≤ 8 s stays an unmeasured alternative, never the default); the words that must
  land exactly → an audio-driven model or a lipsync pass, never a prompt. The cost line quotes the price per USABLE take with its assumed
  keep rate (3:1–6:1 across models), and a cheap take is regenerated where an expensive one is repaired
  (`references/VENUES.md` § Creator-style talking heads). Sora 2 is retired; Veo 3.1, Ray3, FLUX 3, Boreal and Wan 3.0 are
  unproven here.
- **A vendor limit is READ, never inferred.** A cap not read from the vendor's own schema, estimator or error is
  UNKNOWN — never the largest value you happen to have used: a multi-call extension workaround was once designed
  around an 8 s "ceiling" taken from a production's own receipts, for a model whose estimator names the real cap in one
  free call (`higgsfield generate cost <model> --duration 40` → the error states the maximum; never with `--mode`).
  On **monid** the free read is `monid inspect -p <provider> -e <endpoint>`, whose `input` schema carries every
  cap verbatim — run it before EVERY run, because the schemas change. Its `notes` also carry the vendor's
  billing formula, and **a formula is a vendor CLAIM until a receipt confirms it**: ByteDance's published
  `W × H × fps × seconds ÷ 1024` was short by exactly one frame, and only a measured run found it
  (`references/VENUES.md` § monid).
  The cap is read before a shot list splits any action (`video-production/references/PREPRODUCTION-CORE.md` § 2).

### Mode by what the shot must hold

Higgsfield's `omni_reference` takes image refs, a start image, an end image and video refs together, so the
mode is a per-SHOT choice, never a house default. Refs-only is not the consistency optimum by itself and
neither is a start image — each holds different things (measured 2026-09-10, one family-room scene, 72 cr):

| the shot must hold | set-up | why |
|---|---|---|
| a whole CONTINUITY PARTITION — several beats that must hold the same people, objects, setting and look — as ONE long generation within the read cap | refs only (r2v): the reference set carries identity, wardrobe, room and look (a look plate per light context); no start or end frame pinning what the model composes; the negatives scoped to a long take (`video-prompt-dialects` HOUSE-TEMPLATE § The negative tail) | consistency is free inside one generation and a gamble between generations; a long refs-only take composes its own coverage, and a start image re-renders the frame it was given — where separate gens were joined, two seams measured above the take's own maximum (house rule, 2026-09-13) |
| a NEW angle; cast and room carried by references; static or a small move | on Seedance: refs only — the keeper as the appearance ref + the scene proxy's grey frame of the new camera under the layout-only role; no start image, no still to buy. On H3: with the keeper in the reference set the model frames on the KEEPER in either position (n=2) — a grey still as `<Picture N>` is ignored, a baked still beside the keeper is too, and a static clip carries no angle — so a NEW static angle on H3 = bake the still (GPT Image 2.5 from the keeper + cast + the grey frame), ACCEPT it as a room ref (the rule list + `refs_gate.py --accept`), cite it as the ONLY room picture `<Picture 1>` with the keeper OUT of the set, and ship a static proxy clip at that camera as `<Video 1>` (frame 0 on the still, held, 3 of 3 — a spoken line beside it lands too, 1 of 1); a new angle WITH a move stays the orbit clip (2 of 2). A static shot at the keeper's angle ships a static proxy clip as `<Video 1>` — it pins the camera, and a spoken line lands beside it | Seedance r2v: frame 0 opened on the authored angle first try; H3: frame 0 stayed on the keeper and the camera invented a push-in (09-10, n=1); a static clip as `<Video 1>` then held it at 54–66 dB (n=1); the kie still as `<Picture 1>` + the keeper as `<Picture 3>` + a static clip at the new camera → frame 0 on the keeper again (n=1); the still as the ONLY room picture + the static clip → frame 0 on the still, held (3 of 3; with a `<d>` line 1 of 1); without the grey frame a new angle is re-invented from prose |
| a defined camera MOVE with an arrival, on Seedance | a start image (the keeper, or an accepted still) + an END still baked from the proxy's arrival frame; the clause states the arrival; no clip | a smooth, true-parallax arc arriving on the still; a clip beside a start image moved ≈3° of 25°, without one ≈55 % |
| a defined move on MiniMax H3 | refs + the proxy clip as `<Video 1>` with the timecoded clause and the role sentence | ≈ the full arc with the room held; the clause alone re-staged the room |
| an EXACT continuation — a named state, a held prop, the last pose | start image = the keeper's LAST frame (the standing rule), refs for identity | a start image carries the state pixel-exact; refs-only re-imagines it |
| a face at medium framing, a spoken line | whichever row above fits; the FACE at the right size — in the start image or a tight ref — decides, not the mode | an unreferenced element is invented (the 08-30 r2v evidence) |

Refs-only skips the still (≈2 cr or $0.05) but also skips the one reviewable frame before a 10 cr take: when
the angle is risky, buy the still and start from it. The scene is complete first (`video-refs-continuity`
SCENE-PROXY.md § Build it) and every render rides under its role line (`video-prompt-dialects` LINT L26).

**Done when:** venue, mode (per shot, by the table), resolution, duration and rate are named for the batch, and every reference
the call carries is legal on that venue.

## 2. The cost line and the GO

```
REFS-GATE PASS  (table pasted)          ← video-refs-continuity, for THESE refs and THIS start image
S02-G4 · omni_reference · 480p · 8 s · 3 seeds × 8 s × 2.5 = 60 cr  (balance 480 → 420)   GO?
```

One line per batch: seeds × seconds × rate, the balance before and after, dollars for stills at the model's
rate in [`references/VENUES.md`](references/VENUES.md) — the ONE price table; a price written anywhere else is a
pointer to it, and when two figures disagree the table wins — and the free steps named as free. Then wait. The
rules the operator set on this line, in their words, are in [`references/COST-AND-GO.md`](references/COST-AND-GO.md);
the ones that bind every ask:

- **The reference dress rehearsal before an expensive video call.** In reference-driven generation the reference
  set IS the product: before any refs-only call, and before any batch over ~30 cr on any mode, ONE still is
  generated from the SAME reference set with a condensed prompt at the clip's aspect (`gen_stills.py`, cents) and
  read for identity, wardrobe, setting and look; its path rides in the cost line, so the GO is given against a
  seen preview, never a description. A still costs cents; a wrong reference costs the whole batch (operator
  ruling 2026-09-13; COST-AND-GO.md § The reference dress rehearsal).

- **Free before billed.** Whisper the existing takes for the words, RMS-scan for the onset, cut a
  keeper frame as a reference, re-run an edit — search the disk before a regen. Order of spend: disk →
  still → seed.
- **The pre-GO checks are one table, not prose**: refs present and uploaded · cast closed · every noun
  and action traced to the script or the ledger · the start image accepted · anatomy counted · the
  eyeline written per character · the door sentence copied · text legible · product size pinned. Each
  row is a correction that cost credits once.
- **Budget final ⇒ a seed that meets every named constraint goes forward**; free checks (upscale after
  approval, hero pass, frame sheets, the build) never wait for a GO; a residual doubt goes in the
  delivery note with its frame time — never as a re-roll question. Tight budget ⇒ one seed at a time,
  checked before the next.
- **A venue chosen for FUNDING rather than price quotes the PREMIUM on the same line.** Where the money sits
  decides which venue is callable; the ranking decides what it costs. So a batch
  routed to a funded-but-dearer venue reads `… · Higgsfield API (funded) · 1.40× monid, +$0.41 this batch`, and the
  operator rules with the number in front of them. **Never silently reroute a batch to a cheaper venue the operator
  has not funded, and never refuse a funded venue for placing fourth.**
- Decisions go to the operator as **numbered plain questions** with the cost and the file path inline.
- Never `higgsfield generate cost` with `--mode` (it hung); the price is known per resolution.

**Done when:** the GO ask carries the gate table, the resolved reference names in slot order, the cost
line with balances, and the operator's explicit yes is in hand for exactly that batch.

## 3. Submit through the one path

```
python3 scripts/hf_submit.py --root <project> --scene S02-G4 --prompt prompts/r2v/S02-G4.txt \
    --mode omni_reference --duration 8 --refs ROOM,W1,PRODUCT-sheet --start-image S02-G4-start --seeds 3 [--go]
python3 scripts/gen_stills.py --root <project> --only S02-G4-start [--model gpt25|gpt25s|nano|gpt2] [--fresh-scene] [--go]
python3 scripts/gen_video_fal.py --root <project> --prompt-file … --engine seedance|h3 --mode r2v --refs … [--go]
python3 scripts/gen_video_kie.py --root <project> --scene S01-H1 --prompt prompts/omni/S01-H1.txt \
    --mode t2v|i2v|flf|r2v --duration 4|6|8|10 [--refs A,B] [--start-image NAME] [--audio-ids ID] [--go]  # Omni, kie first
python3 scripts/gen_video_fal.py --root <project> --prompt-file … --engine omni --mode i2v|r2v|t2v \
    --image … --duration 7 --resolution 720p --aspect-ratio 9:16 [--go]                                 # Omni, the fallback
python3 scripts/monid_upload.py --root <project> --batch 'references/*.png' --go   # sfs, $0.00, idempotent
python3 scripts/monid_upload.py --root <project> --verify        # ONE recursive /ls for the whole set
python3 scripts/monid_upload.py --root <project> --refresh --go  # re-issue lapsed urls, moves no bytes
python3 scripts/treg_host.py --root <project> --batch 'references/*.png' --go     # treg.to, $0.00, idempotent
python3 scripts/treg_host.py --root <project> --verify           # every recorded expiry, zero API calls
python3 scripts/treg_host.py --root <project> --refresh --go     # RE-UPLOADS: a new url, and it spends quota
python3 scripts/monid_submit.py --root <project> --scene S02-G4 --prompt prompts/r2v/S02-G4.txt \
    --mode t2v|i2v|flf|r2v --duration 7 --refs ROOM,W1 --resolution 480p --ratio 9:16 [--go]
python3 scripts/hf_api.py quote --resolution 720p --duration 8 --seeds 3   # COMPUTED, free, no network
python3 scripts/hf_api.py balance                                # the wallet — its ONLY copy, see below
python3 scripts/hf_api_upload.py --root <project> --batch 'references/*.png'   # free; mp3 → WAV here
python3 scripts/hf_api_upload.py --root <project> --verify       # free HEAD per url; the lifetime check
python3 scripts/hf_api_submit.py --root <project> --scene S02-G4 --prompt prompts/r2v/S02-G4.txt \
    --mode t2v|i2v|r2v|edit|extend --duration 8 --refs ROOM,W1 [--audio VO] [--video-refs ORBIT] \
    [--source <keeper URL>] [--input-seconds N] --resolution 480p|720p [--model h3] [--go]
python3 scripts/hf_api_submit.py --root <project> --scene G1 --prompt prompts/v2v/G1.txt \
    --model genjutsu --mode object-swap|motion-transfer --source <clip NAME> --refs A,B [--go]
```

**The Higgsfield API is the one venue that hands back NO price, so the gate computes one.** `/estimate`
answers a token-metered model with `{"type":"description","pricing_description":"<formula>"}` and no
number at all — so `hf_api.py` carries the formula (`ceil((in_s + gen_s) × W × H × 24 ÷ 1024) × rate`),
quotes LIST beside NET because the launch discount is dated and expiring, and prints the `+1 frame`
ceiling because ByteDance's published formula was measured short by exactly one frame on monid and no
Higgsfield receipt has settled which one bills here. **It is also the one venue with NO balance
endpoint** (`higgsfield account status` reports the frozen PLAN wallet, a different account), so
`hf_api.py`'s ledger — `$HF_API_LEDGER`, default `~/.local/state/higgsfield-api/ledger.json` — is the
only copy of that wallet that exists: `hf_api_submit.py` writes a spend at acceptance and
`hf_api_poll.py` writes the matching refund for a `failed` / `nsfw` / cancelled request, which are not
charged. An unrecorded spend there is not untracked but **unknowable**.

Dry run by default; `--go` spends. Each path runs the refs gate first and holds on FAIL — a priced warning an
explicit GO overrides, never a silent or unoverridable stop (§ 0) — prints the
cost, parses the venue's reply shape-safely (Higgsfield `generate create --json` returns a bare LIST of
job ids), writes the raw reply to `receipts/raw/`, appends a ledger record per seed BEFORE polling,
and detaches the poller. Reference names resolve through `receipts/<NAME>-upload-id.txt`
(`scripts/hf_upload.py`), `refs-urls.json` (`scripts/kie_upload.py`, which MERGES — an overwrite once
dropped eleven live URLs), `monid-urls.json` (`scripts/monid_upload.py`, which merges the same way) or
`treg-urls.json` (`scripts/treg_host.py`, which merges and re-hosts); a
raw UUID or a raw URL is refused because the gate must see a name. kie URLs expire in
about 24 h ("Image fetch failed" = expired, billed 0 → re-upload). A prompt over 5000 chars is warned
(6629 worked; 7840 was trimmed); on monid 6000 is the endpoint's own cap and `monid_submit.py` refuses
above it rather than letting the venue trim.

**A monid reference has a lifecycle the other venues do not, and the gate enforces it.** The FILE persists
forever but its signed url lapses with its `ttl`, and the model fetches that url at generation time — while
the job bills at **acceptance**. So a lapsed url would pass a name check and cost the batch. `--batch` hosts
a whole set idempotently (skipping anything whose sha256 still matches, re-uploading anything whose local
file CHANGED), `--verify` answers "do all 30 still exist?" in one free recursive `/ls`, `--refresh` re-issues
a lapsed url by a free `/cat` that moves no bytes, and the refs gate FAILS a reference whose url has expired —
checked locally from the recorded `expiresAt` or the url's own `?e=<unix>`, at zero API calls.

`monid_submit.py` holds three things back by default, because each one bills in full while looking correct — each
is a **priced warning an explicit GO overrides** (§ 0), never an unoverridable stop:
**`--duration auto`** (it HOLDS a full 30 s price up front and releases the remainder on settle, so the
GO would be given against a number nobody asked for — always an integer 4–30); **a `ratio` on a mode
that cannot take one** (only t2v and r2v accept a ratio; first/last-frame, edit and extend inherit their
source's aspect and REQUIRE `adaptive`); and **a raw URL in place of a reference name**. It prints the
resolved `@Image1…@ImageN` map before the GO, because ordinals are numbered **per type in array order**
and a start image is itself an image — so a first frame takes `@Image1` and every ref shifts by one, and
a prompt citing the wrong ordinal generates cleanly at full price.

**Done when:** `receipts/hf-jobs-<scene>.json` (or the fal/kie receipt) holds every job id and the
ledger has one record per seed, before any result is read.

## 4. Poll detached, one waiter, sentinel-checked

The poller is detached (`hf_submit.py` starts it in its own session; restart one by hand with
`video-production/scripts/detach.py`, absolute paths) and logs to
`takes/hf-poll-<scenekey>.log`; every line starts with a timestamp, so a monitor matches
`" DONE | FAILED|HF-POLL-END"` anywhere in the line, never `^DONE`. One background waiter at a time;
never `tail -f | grep`. Mechanics in [`references/RECEIPTS-AND-POLLING.md`](references/RECEIPTS-AND-POLLING.md):

- `COMPLETED` is not success — only a result with a file is. Refusals (`nsfw`, `ip_detected`, a 422)
  are free; check `higgsfield account transactions` for the refund, then resubmit a refunded batch
  **inside the original GO**. A 503 on one seed is resubmitted under a NEW scene key, never the same
  (it would clobber the batch receipts). A billed job is never resubmitted — its result persists;
  re-fetch it.
- **monid is fire-and-poll, never `--wait`** (p50 **245 s**, p95 **603 s** against a 300 s default — the
  wait returns a timeout on a run that is still billing), and on an async fire `-o` writes nothing: the
  submit envelope is stdout only, so the `runId` is persisted from it before anything else happens.
  `COMPLETED` carries a second question there that no other venue has — **a provider error arrives as
  `COMPLETED` with `providerResponse.httpStatus` 404/500 and is NOT charged**, so `monid_poll.py` reads
  the http status and the run's own `cost.value` before calling a take failed or a failure billed. A
  reply with **no `runId` at all** is a body the gateway rejected: no run exists and nothing was billed.
- **kie video is create-then-poll** (`gen_video_kie.py` detaches `kie_poll.py`; match `" DONE | FAILED|KIE-POLL-END"`).
  Billing is at task creation; a create reply without code 200 made no task and billed nothing; `resultJson` is a JSON
  STRING holding `resultUrls`. Whether kie charges a FAILED video task is unverified: the receipt keeps the task record
  verbatim, and nothing calls a failure free until kie's own record does.
- Two 504s in a row is an outage: stop paying to find out; switch venue on the next GO.
- The billing header on fal is late, not absent: re-fetch the result URL until it appears; never record
  a missing header as zero. Seedance bills actual output seconds; H3 bills the requested integer.
- A hanging Higgsfield Topaz or Starlight submission (no job, no charge) is retried once, then the
  route switches (local Rhea) — never loop on a hanging route.

**Done when:** the log ends `HF-POLL-END N of N downloaded`, every take is on disk with a receipt naming
its job id, URL, bytes and dimensions, and any refusal is classified free or billed from the venue's
own record.

## 5. Hand over clips; then nothing moves until the pick

Seeds go to the operator as clips — the full path (chat send only under ~20–30 MiB) — the moment
each lands; contact sheets and audio envelopes are the agent's notes, one line each. A sheet cannot
show the timing of a gag. The pick is the operator's, named by path. No upscale, hero pass or edit
starts on a seed before that pick.

**Done when:** the operator has named the keeper(s) by path and the pick is recorded (continuity
ledger, receipts), or every seed is voided with the reason.

## ❌/✅

```
❌ "Generating 3 seeds now" → submit                       ✅ cost line + gate table → wait for the GO
❌ higgsfield generate create … by hand                    ✅ hf_submit.py --go (gate, receipt, poller)
❌ Receipt written after the download                      ✅ ledger line at task creation, before polling
❌ `except URLError` on the poll                           ✅ `except Exception` with a miss budget
❌ COMPLETED → "done"                                      ✅ a file on disk + a 2xx result = done
❌ Resubmit a billed job that "went missing"               ✅ re-fetch the result by job id
❌ 503 on seed 2 → resubmit under the same scene key       ✅ a NEW scene key for the resubmission
❌ "Approve, or re-roll for the fleck?" after a final top-up ✅ the seed meets the constraints → forward
❌ Contact sheets to the operator for a gag                ✅ the clips, by path
❌ Rhea started on a seed before the pick                  ✅ the chain begins at the pick
❌ `cmd | tail -3; echo $?`                                ✅ `rc=$?` on the invocation line
```

## Failure behavior

- Gate FAIL → nothing is submitted **on that pass**, and the ask names what is missing (upload / cut / declare)
  **plus what it costs to proceed anyway** — a lapsed reference URL bills the whole batch at acceptance and returns
  nothing, so that number is the argument. **It is a priced warning, not a veto: an explicit GO against a named FAIL
  submits** (§ 0). What must never happen is a silent stop, or a FAIL the operator cannot overrule.
- A venue error that reads as a refusal is confirmed from the venue's own record (job status,
  transactions) before it is called free.
- Three rounds on one shot without convergence → stop generating; put the alternatives (extension,
  insert, reframe, drop) to the operator as numbered questions with costs.
- Disk is a production resource: check the drive's free space before a batch and before every finish
  (a full drive took the whole environment down).

## Cross-references

- `video-refs-continuity` — the reference set, the start image and the refs gate the call depends on.
- `video-finish` — the reconstructive upscale and grade, after approval only.
- `~/.claude/skills/video-production/references/CHAIN.md` — handoff budget and stop conditions.
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
