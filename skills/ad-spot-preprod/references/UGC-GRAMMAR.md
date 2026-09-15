# UGC grammar — the creator-style spot: where it wins, the hook, the structures, the beats, the delivery, the variants, the four artifacts

Applies to a UGC / creator-style spot (`--spot-type ugc`: a person talking to the camera, a real or generated presenter,
phone-shot or generated footage) on top of the ad grammar in `video-edit-edl` GENRE-GRAMMAR.md; a product spot with a card
and a wipe keeps its own rules. Every rule carries its tier: **M** measured on our own footage · **S** a community skill,
converged across two or more · **P** practitioner threads (weak, boundary conditions only) · **C** a vendor claim with no
named sample (never a number to plan on). The rules were distilled from a research pass over practitioner threads, community skills, vendor guides and the
peer-reviewed studies on origin perception (September 2026); the tier beside each rule is that pass's verdict.

## Where lo-fi wins, and where it does not — the intake axes

Walk these with the brief at intake (`video-production` § 1); each moves the build:

| axis | lo-fi / native creative | polished / product-forward | tier |
|---|---|---|---|
| price point (AOV) | impulse buys under ~$30–50 | a consideration phase at ~$100–150+ — a cheap aesthetic erodes trust there | P |
| funnel stage | prospecting (cold): pattern interrupts, a person, a room | retargeting (warm): structured, specific, product-forward — one 15-account practitioner read polished retargeting at 2–3× the ROAS of UGC on warm audiences | P |
| platform | Meta, TikTok | Google PMax / YouTube | P (single source; hold as the default until data exists) |
| category | low-involvement, consumer | B2B, high-intent, premium; the label-vs-origin effect is STRONGER in high-involvement categories | P + peer-reviewed |
| persona | a real person in a real room | a synthetic presenter — a demo, never a testimonial (below) | S + C |
| decay | ad-level fatigue in days; concept-level in months (a named case: three concepts run ~6 months, −38 % ROAS YoY at flat spend) | build the remix system before the first spot ships (§ The variant matrix) | P + named case |

**The dial is native-ness, not rawness.** "Produced content that looks native" — a real person, a real environment,
competent-but-not-studio light and sound — beats both gloss and chaos (P, S). Imperfection is an inverted U with a floor:
the one controlled test in the corpus (small, single-platform, vendor-run) found MEDIUM imperfection (handheld, uneven
light) won watch time while HEAVY (fumbled words, background noise) hurt completion (C, directional); the proof shot's
legibility is never degraded, because the proof IS the ad (S). Over-edited captions, emoji stacks and effects re-trigger ad
detection (P). A synthetic persona presents a demo; it never gives a personal testimonial, and street reactions are never
faked (S, high tier) — 100 % synthetic faces with no real-testimonial backbone failed more than 80 % of the time in one
vendor's own data (C). The magnitude of the UGC advantage is unsettled (1.3× to 6.7× by source) and part of it may be
variant VOLUME rather than format — attribute wins honestly.

## The hook

- **Layers** (single source): a visual disruption + a verbal promise + a rhythm.
- **The convergent core** (three or more sources): the curiosity gap · contrarian / skeptic ("I didn't believe this") · the
  pattern interrupt · the problem callout (a specific pain) · proof-first (the result before the claim). Single-source types,
  used with caution: reverse psychology, sensory / ASMR, confession, demonstration cold-open, price / value, app shortcut,
  persona mirror. No hook accuses or targets a protected trait (S).
- **Writing the visual hook**: open mid-action, already using the product, mid-sentence, in the real environment — never a
  static "hi guys"; the hook must be legible with the sound OFF (S). No brand-name opener; feature-first copy and a vague
  CTA are listed tells (P).
- **Timing**: a 0–3 s window (S); the finer platform-conditional claims (TikTok 1–2 s, Reels the first frame, Shorts 3–5 s)
  are unverified. The ad grammar's "hook inside 2 s" stands.
- **Never report a hook rate without hold and conversion beside it** (P): a hook that wins the first 3 s and loses the sale
  is the faux-GC failure, not a win.

## The structures

Convergent archetypes (two or more community skills): problem → solution · testimonial (a REAL person only) · unboxing ·
before / after · demo / proof. Single-source additions: objection handling, listicle, comparison ("I tested five…"),
founder transparency, street-style social proof, myth-bust, creator challenge, app walkthrough, try-on, reaction hook.
Founder-led lo-fi is conditional on the founder being genuine on camera (a named pair of spots: one read stiff and staged,
the other worked).

## The beats, by duration (S; the interior placements are community consensus)

| length | skeleton |
|---|---|
| 9–15 s | 0–1.5 hook with visual proof · 1.5–5 setup · 5–10 one proof or one objection · 10–15 CTA |
| 20–35 s | 0–2 hook · 2–6 problem · 6–16 demo with 2–3 concrete beats · 16–24 proof / objection · 24–35 offer, disclosure, CTA |
| 45–60 s | 0–3 hook · 3–10 stakes · 10–35 walkthrough · 35–50 objections and terms · 50–60 CTA |

Micro-placement inside a ~30 s spot: **composite REAL proof (product stills, b-roll of the product in use) at the demo beat,
~8–12 s**; cutaways at ~8 s and ~18 s; a static torso holds no longer than ~6–7 s; a ~10 s talking head is ONE continuous
generation (stitching produced seams and voice shifts — S, and our splice detector reads a hidden join at 60× the shot's
median frame change — M); one slightly abrupt jump cut reads phone-real (S). Duration is unresolved — under 15 s exposes
fewer tells (P), 30 s is the practitioner sweet spot, 45–60 s templates exist; longer formats need interleaved real
footage and the one-take discipline. The generator's cap is read before the beats are cut
(`video-production/references/PREPRODUCTION-CORE.md` § 2).

## Delivery — the script is the underrated lever

- **Disfluency is seasoning**: 2–4 per 30 s, one of them in the FIRST sentence ("honestly", "okay so", "wait", a restart);
  incomplete sentences and pauses read human; the single biggest threat is "sounds like they're reading" (P, S).
  2–4 words per second (S). The heavy arm — fumbled words, noise — lost (C).
- **Register**: a friend texting, never marketing language; specifics, not adjectives.
- **The CTA** sits in the last 3–5 s, specific ("the link is right there"); the least-evidenced part of the grammar — no
  source gives phrasing patterns or counts.
- A generated presenter that speaks on its own clock is dubbed and retimed (`spot-audio-assembly` MIX-AND-QC.md § The
  phone-mic register); the words that must land exactly go to an audio-driven model, never to a prompt.

## Captions

Burned in when autoplay is muted (most social viewing); made with the platform's own caption tool or a hand-typed look so
the text matches what real users post; short chunks aligned to speech; contrast ≥ 4.5:1; inside the platform's safe zones;
never over the product, a face, a price or a disclosure. Two defensible styles — speech-aligned native chunks, or a ≤ 6-word
overlay discipline reserving the bottom third for the hook and the CTA — pick ONE per platform and write it into the
campaign's `caption_style` (`spot-audio-assembly` CAPTIONS.md). The house ALL-CAPS brand-colour style is a product-spot
default, not a UGC one.

## The variant matrix — one variable at a time

The unit of testing is the VARIANT, and its cost advantage is the point: hook × persona × proof × length × CTA × caption
style × offer, one axis moved per cell, shipped into one dynamic-creative set and allocated by the platform. Add the dose
arms — polished / medium / heavy imperfection with CALIBRATED steps (`video-finish` § 5 the phone-native tier,
`video-finish-qc` `phone_texture_probe.py`) — and measure hold rate, not hook rate alone; this is the cheapest experiment
the corpus has not run. Plan the decay: a modular hook × body × CTA remix system, ~80 % baseline / ~20 % unconventional
cells (P).

## The four artifacts every UGC spot ships with

| artifact | what it is | where it lives |
|---|---|---|
| the creative | the spot, its alternates, per platform | `deliver/` |
| the evidence | the substantiation behind every claim a presenter makes — a consumer endorsement represents the product is effective for what is depicted, and the advertiser must hold the proof (16 CFR 255.2(a)); a result presented as typical needs the generally expected result disclosed (255.2(b)) | the decision log |
| the rights | the creator agreement (payment, usage window, whitelisting / partnership-ad permission, an AI-modification clause — most pre-2026 agreements say nothing about a tool regenerating a delivered face or voice), the likeness check on a generated cast, the music licence | the asset bible |
| the disclosure | the script's disclosure column: the material-connection disclosure (in the creative, visual AND audible where the endorsement is both), the platform's paid-partnership / commercial-content setting, the AI label where the creative is generated or significantly modified | RISKS.md § UGC compliance |

## Script columns

`time | spoken | on-screen text | shot | proof | disclosure | notes` — the disclosure column is never empty on a UGC spot;
the proof column names the real asset composited at the demo beat.
