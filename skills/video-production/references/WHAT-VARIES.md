# What varies — the defaults that move with the project

The skills carry three kinds of statement, and only one of them holds for every production:

| kind | what it is | when it moves |
|---|---|---|
| **method** | the order, the gates, the reads and the records — the cost line and GO before a billed call, the refs gate, continuity first, the delivered file as the only thing verified, a new version as a new file | never; a project that seems to need an exception is a question for the operator |
| **tool fact** | a number or a behaviour measured on one model, venue, tool version or encode chain — a price, a cap, a mode that held, a pixel threshold, an instrument's tolerance | when the model, venue, version or chain changes, or the measurement is old: re-read the vendor, re-measure on the first takes |
| **brief setting** | what one genre, platform or client asked for — the aspect, the loudness target, the caption style, the card, the edit grammar's timings | every project: re-derived from this project's brief, platform spec and client reference |

This file lists the second and third kinds by the axis that moves them. Everything it does not list is method.

**At intake** (`video-production` § 1), walk the axes below against the brief and write every value that differs into the
project's own files — the EDL's `canvas`, `fps`, `runtime_s` and `audio.loudnorm`, the campaign's `caption_style`, the
shot list's header, the pause block. A skill's default applies only where the project holds no value of its own. A
default carried into a project it does not fit raises no error; it ships wrong.

**A lead** is a number measured on one production: the starting point for the first takes of the next, re-measured
there, never a pass/fail threshold on a different generator, raster or genre. The leads are listed last.

## Genre and format

| what moves | the skills' default | re-derive from | where it lives |
|---|---|---|---|
| the unit of work and its SSOT | ads: the spot and the client's script · film: the film and its beat sheet · music video: the track and its map · explainer: the anchored script | the genre switch | `video-production` § 1 |
| the edit grammar's timings | ads: a hook inside the first 2 s, the closer 0.7 s into the turntable, the last narrator line ≥ 0.5 s before the hit, the end card 2.5 s full | the genre's own grammar (film: no card, no captions, the self-revelation at 90 %; music video: the track map first); a brand's spec and the operator's reads of this project's cuts override | `video-edit-edl` § 2–3, GENRE-GRAMMAR.md |
| the ad campaign's structures | vertical standalone spots in tiers; the sign-off (the variable line around the audio signature, the locked line, the CTA); a wipe in every spot; a two-state grade for a before/after joke; the product and its fill designed and SKU-locked | the campaign's brand kit and joke; a spot with no product, card or wipe on screen drops the product rules (`--spot-type ugc`); film and music video carry none of them | `ad-spot-preprod` § 1–3, GLOBAL-SPEC.md |
| captions | burned in, the narrator only, no punctuation; the house style ALL CAPS with the spoken word in the brand colour | sound-off social viewing wants them; a client reference sets a measured variant in `caption_style`; film and music video carry none; punctuation returns only when the operator lifts the ban | `spot-audio-assembly` § 5, CAPTIONS.md |
| the acceptance rows | the product's shape and size, the product's fall, dignity | the product rows exist only with a product on screen; the brand's standards and the genre's tone set what reads as abuse | `video-take-review` ACCEPTANCE-MATRIX.md rows 5, 9, 11 |
| the designed kit | card, turntable, piece wall, drift, burst | the brief names which designed elements exist; a film or an explainer builds only those | `designed-elements` § 1–2 |
| the look and the upscale pass | ads: the clean look pair and an upscale per shot · film and music video: a film pair and one pass on the locked cut | the genre switch; the look is chosen by rendering it on this footage, never by its name | `video-production` § 1, `video-finish` § 5 |
| the prompt's style prefix | a photoreal live-action commercial, 9:16, clean exposure, no grain, no on-screen text | this project's genre, aspect and look; a creator-style spot swaps it for the phone-native dialect (a front camera held at arm's length, window light, room tone — never "cinematic", never the device named) | `video-prompt-dialects` § 2, PHONE-NATIVE.md |
| the UGC / creator-style sub-genre of ads | native-ness at MEDIUM: a real person in a real room, competent-but-not-studio light and sound, handheld; the hook legible without sound; a synthetic persona presents a demo, never a testimonial; the phone-native dialect, the phone-native finish tier, the two compliance paths | the intake axes, walked with the brief: the AOV band (raw lo-fi for impulse buys, product-forward at ~$100–150+), the funnel stage (native for prospecting, structured and specific for retargeting), the platform (Meta / TikTok native; PMax / YouTube polished — weakly evidenced, the default until data exists), a real vs a synthetic persona, phone-shot vs generated footage; every value into the shot list's header and the decision log | `ad-spot-preprod` UGC-GRAMMAR.md, `video-prompt-dialects` PHONE-NATIVE.md, `video-finish` § 5, `ad-spot-preprod` RISKS.md § UGC compliance |

## Delivery platform

| what moves | the skills' default | re-derive from | where it lives |
|---|---|---|---|
| aspect, delivered raster, frame rate | 9:16, 1080×1920 delivered, 24 fps CFR (the EDL's `canvas` and `fps`); a 2160×3840 mezzanine and design canvas | the platform's or festival's spec; a landscape piece changes the canvas, the mezzanine and the design canvas together (`finish_spot.py --canvas`, `hyper_new.py --canvas`) | `video-finish-qc` PIPELINE.md, `video-edit-edl` EDL-CONTRACT.md |
| safe zones | gags, faces and text clear of the vertical platform UI — GLOBAL-SPEC.md and PIPELINE.md carry different figures, each from the spec it was read from | the target platform's current overlay, read before the shot list | `ad-spot-preprod` GLOBAL-SPEC.md |
| loudness target and true-peak ceiling | the client reference's measured integrated level; with no reference, the house −14 LUFS; the true peak under the platform's ceiling, with the EDL's TP target ≈ 1 dB below it for AAC | the client's reference first, then the platform's or broadcaster's published target and ceiling | `spot-audio-assembly` MIX-AND-QC.md, `video-finish-qc` § 3 |
| the delivery encode | H.264 High, CRF 17, AAC 192 kbps, 8-bit 4:2:0; for paid social progressive, CFR, Rec.709, no HDR | the platform's ingest spec; a broadcaster or a festival names its own codec, container and mezzanine | `video-finish-qc` PIPELINE.md |
| grain | off for phone-tier social; coarse, on a mezzanine above delivery, from ~5 Mbps up — the phone-native tier INVERTS this: fine sensor-style noise or a denoise at delivery resolution, and a phone-class encode, dosed until the texture probe reads inside the project's real phone clips' band | the delivery bitrate — a decision tree, not a setting; on a creator-style spot the real clips' band | `video-finish` § 5 (the phone-native tier) and § 6 |
| the master raster | 1080p masters (a standing rule) | a brief that requires 2K or 4K is the operator's decision, never the agent's; the resolution is bought only when the deliverable wants it | STANDING-RULES.md, `video-finish` § 2 |
| a byte cap | ≤ 30 MiB in the operator's chat | the channel's own cap; the bitrate is derived from it, two-pass | `video-finish` § 8, `client-rounds` § 5 |

## Generator, venue and native raster

| what moves | the skills' default | re-derive from | where it lives |
|---|---|---|---|
| venue, model, mode, price, moderation | the established chain, dated in VENUES.md: Seedance 2.5 on Higgsfield for shots with people, monid the pay-as-you-go route for the same model on people-free shots (rank by marginal cost, prefer PAYG over plan lock-in, NEVER by current balance), fal only for people-free shots, GPT Image 2.5 on kie for stills | the vendor's own docs and cost page, read in full before the first call; a new model is proven on the hardest shot first | `video-gen-cost-gate` § 1, VENUES.md |
| generation resolution | 480p on the 480p chain (Seedance) — 720p or 1080p generation is never proposed; MiniMax H3 at its 768p minimum on fal (a house rule) or at 2K, its only tier, on Higgsfield | a new model's tier is the operator's call; any take above 480p moves every pixel number in the rows below | `video-gen-cost-gate` § 1, VENUES.md |
| the clip cap and minimum | read from the vendor; a 4 s minimum on the established chain | the vendor's schema, estimator or error — never the longest take already run | PREPRODUCTION-CORE.md § 2, `video-gen-cost-gate` § 1 |
| the dialect | one contract per model version — layout, addressing, caps, the words a moderator refuses, ≈ 1 beat per 3 s | the model's own docs; a version bump re-reads its row | `video-prompt-dialects` § 1, DIALECTS.md |
| the mode table | refs-only for a whole continuity partition, a start image for an exact continuation, an end still for a Seedance move, a proxy clip on H3 — each row measured at n = 1–3 | the cheapest same-seed A/B on a new model before a shot list relies on a row | `video-gen-cost-gate` § 1 |
| native audio | the take's own sound: the first sfx source and the lip-sync reference | a model that generates no audio moves every sound to post | `spot-audio-assembly` § 3–4, `video-edit-edl` § 3 |
| face size | ~60 px of face height as the floor, measured at 480p; the accepted faces sat well above it (a lead) | count the face in the take's native pixels; above 480p the same pixels arrive in a wider framing; re-measure on the first takes | `video-take-review` § 3, `video-prompt-dialects` HOUSE-TEMPLATE.md |
| the upscale tier | reconstructive for a generated source; per shot, local Rhea at a head ≥ ~50 px in a 480×854 take, hosted Starlight below it or where text must read | the source's nature and native raster; another upscaler or version is benchmarked on one shot through both arms | `video-finish` § 1, `video-finish-qc` § 1 |
| instrument limits | a pixel instrument blind to product proportion at 480p; placement and consistency tolerances from the measured chain | the instrument's known-answer case, re-run at the new raster or encode chain before its number is trusted | `video-take-review` INSTRUMENTS.md |

## Tools, hardware and environment

| what moves | the skills' default | re-derive from | where it lives |
|---|---|---|---|
| the finishing stack | Topaz (local Rhea, hosted Starlight), then Resolve 21 + Dehancer on the `auto` transport (Local first, in-app bridge as the fallback) | another upscaler or grading stack keeps the ORDER and replaces the arm (`upscale_local.sh`, `hero_pass.sh`) | `video-finish`, `video-finish-qc` § 2 |
| a local GPU | the scene proxy's server, local H3, the local upscale | without one: the proxy fails closed ("no scene proxy for this shot"), local H3 is off, the upscale goes hosted through a cost line | `video-refs-continuity` § 1, VENUES.md, `video-finish` § 2 |
| the render host for designed elements | a GPU VM (headless Chromium hangs under WSL2) | any host where the composition renders headless at its declared raster (Node ≥ 22) | `designed-elements` § 3 |
| transcription | local faster-whisper, free; Scribe billed per minute | the machine and the language; a billed engine goes through the cost line | `spot-audio-assembly` § 5 |
| vendor accounts | Higgsfield, fal, kie, ElevenLabs, AceData Suno — each keyed script or documented call reads its key from the environment (`FAL_KEY`, `KIE_API_KEY`, `ELEVENLABS_API_KEY`, `ACEDATACLOUD_API_TOKEN`); Higgsfield and monid each log in through their own CLI and keep the credential in that CLI's own store, so neither has an env var to set | a different vendor needs its own script arm and its own docs read; the cost line does not move | every billed script |
| the operator's environment | Windows paths in the delivery ask, a standing deliver directory, a chat cap | the operator's machine and channels | `client-rounds` § 5 |
| the agent | any agent that invokes these skills through the Skill tool and runs their scripts — nothing here depends on one model or session | a phase handed to another agent carries the handoff rule; a harness with a smaller request budget carries fewer review images per turn | STANDING-RULES.md, `video-take-review` § 1 |

## Audio and voice

| what moves | the skills' default | re-derive from | where it lives |
|---|---|---|---|
| voices and models | a narrator voice id rendered by one model for the campaign's life; a distinct voice per role; the off-screen voice never the narrator | the brief's casting, language and accent; a model version change is re-auditioned by ear | `spot-audio-assembly` § 1 |
| the music route | AceData Suno by default; the operator's candidates and a library bed as fallbacks | the client's licence terms — broadcast, paid media or a label can require a library, a composer or cleared stems | `spot-audio-assembly` § 3, SFX-AND-MUSIC.md |
| mix constants | the bed and the duck measured from the client's reference stems | each client's reference; with none, the operator's ear | `video-edit-edl` § 3, `spot-audio-assembly` MIX-AND-QC.md |
| the audio signature | on the end card, its hit on the card's burst | a brand that has a sound; a brand without one has no signature slot | `ad-spot-preprod` § 2, `spot-audio-assembly` § 3 |
| the VO hygiene floor | a line's gap floor at or under −40 dBFS (a lead from one job) | generated VO sits far under it; a recorded voice after its repair chain, or another TTS vendor's clean files, set `--floor-max` | `spot-audio-assembly` § 5, VO-PIPELINE.md |
| placement tolerance | envelope NCC, every line within 15 ms, measured on the house encode chain | the instrument's self-test on the new encode chain | `spot-audio-assembly` § 6 |

## Client and budget

| what moves | the skills' default | re-derive from | where it lives |
|---|---|---|---|
| rulings | language, platform risk, rating, wardrobe and set, logged once | each client; the operator decides where the script is silent | `ad-spot-preprod` § 2 |
| the round's classes | CUT, RECYCLE, REBUILD, CAUSALITY, APPROVE, GATE — one client's words as the examples | another client's vocabulary maps onto the same classes | `client-rounds` § 3 |
| the tiers | paid spots, a capper montage, a hero cut | the media plan | `ad-spot-preprod` § 1 |
| spend per batch | seeds per batch at the venue's rate; one seed at a time on a tight budget; a reference dress rehearsal before a refs-only call or a batch over ~30 cr | the balance and the venue's price; the ~30 cr threshold is in Higgsfield credits — convert it at another venue's rate | `video-gen-cost-gate` § 2 |

## Leads from one job — re-measure before relying on them

Each number lives, with its sample size, where its rule lives; this list says where, so none is mistaken for a spec.

| lead | where its number and sample live | re-measure by |
|---|---|---|
| the accepted face band above the ~60 px floor | `video-prompt-dialects` HOUSE-TEMPLATE.md § The pre-GO read | the first takes' faces, detail compared at equal resampled size |
| composed-cut consistency multiples | `video-take-review` `cut_consistency.py`, its calibration note | the project's accepted takes, multiples compared inside one take |
| the VO gap floor | `spot-audio-assembly` VO-PIPELINE.md § provenance | the project's clean files, after any repair chain |
| the upscale tier's head size | `video-finish` § 1 and its EVIDENCE.md | one shot through both arms at the new raster |
| the mode table's rows | `video-gen-cost-gate` § 1 | a same-seed A/B on the new model |
| the ad grammar's timings | `video-edit-edl` GENRE-GRAMMAR.md | the operator's reads of this project's first cut |
