# Edit grammar by genre

The genre switch (ads · film · music video) decides what the beat list looks like and what a "good cut"
is; the builder, the gate and the finisher are the same. Presets from the edit-library are defaults the
operator corrects, never a taste of their own.

## Ads (a campaign of vertical spots)

- **Canvas** 1080×1920 at 24 fps; a spot is 15–60 s; a campaign shares its narrator, its card, its
  closer line, its caption style and its music cues — reuse a proven device from a sibling spot.
- **Shape**: hook inside the first 2 s (a knock, a line, a look) → setup → the reveal on a marker → the
  product beat (the product out, the hit) → the transformed state → the turntable with the closer 0.7 s
  in → the end card, 2.5 s FULL, the audio signature at +0.02. A capper spot copies the delivered spots' events
  into a montage windowed on the disclaimer's word times.
- **Cut-order checklist** (from the operator's reads of stitched cuts): cause before reaction; a
  sound-only event has its visual cause on screen; a reaction shot starts AFTER the turn; a line that sits "too late in the order" needs something
  between it and the previous line; a product quip only after the product is visible; a bridging shot
  where dialogue trails across a cut, with its eyeline motivation.
- **Length**: the hit shot plays almost to the end, a quarter second shaved off; the aftermath of a
  burst is cut short; a beat that cuts away too soon is lengthened; a shot that hangs a touch too long
  loses a second off the end.
- **Repair ladder before any regen**: drop a bad short shot; swap the shot from an
  older version; lengthen/shorten a window; a hybrid EDL mixing a new take's cuts with the existing
  keepers; a punch-in (`zoom`) to keep the wrong thing out of frame; a placed sfx for a lost sound.
  Four re-cuts in 1 h 45 cost zero credits.
- **Captions**: narrator only, campaign style, no punctuation.
- **Type over footage** (a spot whose words are designed type on real or generated footage — no narrator, a documentary
  spot): footage and the hook are on screen together from frame 1, because a card-only open spends the hook window on a
  card (a brief that asks for a card open overrides); frame use is stated as a footage SHARE per beat, measured from the
  layout, never as a layout — "a band with type above and below" seeded a strip at 0.56 scale with decorative fill around
  it; no beat is type-only except the card; a subject's head is checked per shot AND per raster, since the square crop of a
  vertical shot (or the reverse) cuts a head the other raster kept; every on-screen word has a named source — the client's
  text, a line heard in the footage, or the CTA — and an internal label or a concept name never prints; a hold on one frame
  is bounded by the EDL's `qc.max_still_s` and read back by `qc_deliverable.py` (a designed hold declares `accepted_still`).
- **Alternates** are their own EDLs and deliverables; finals are named versions per spot in
  `deliver/final/` with the current card.

### The UGC / creator-style spot (a sub-genre of ads; the grammar in `ad-spot-preprod` UGC-GRAMMAR.md)

- **Shape**: the hook on the FIRST frame, legible with the sound off (a person mid-action, mid-sentence, the product in
  hand) → the problem in her words → the demo with REAL proof composited at ~8–12 s of a 30 s spot (product stills, b-roll
  of the product in use) → a proof or an objection → the offer, the disclosure and the CTA in the last 3–5 s. Cutaways at
  ~8 s and ~18 s; a static torso holds ≤ ~6–7 s; the talking head is ONE continuous take (~10 s), and one slightly abrupt
  jump cut is allowed — a hidden join is not (`video-finish-qc`'s splice read finds it).
- **No music bed under the open**; room tone carries the first beat; a cue may enter under the demo. No card unless the
  brief asks, no wipe, no sign-off signature — the sub-genre drops the product-spot kit (`ad-spot-preprod` § 3).
- **Captions native**: speech-aligned short chunks, or a ≤ 6-word overlay discipline — one style per platform, never over
  the product, a face, a price or the disclosure; the house ALL-CAPS brand style is a product-spot default.
- **The disclosure is a beat**: the spoken line and the overlay sit in the open and are never cut, ducked or captioned
  over; a lipsync pass or a dub on a real creator's take is a compliance change (`ad-spot-preprod` RISKS.md § UGC
  compliance), declared on the event.
- **Alternates are the variant matrix**: one axis per EDL (hook, persona, proof, length, CTA, caption style, offer), each
  its own file and its own deliverable.

## Film (a short)

- **Canvas** 16:9 (or the festival's), 24 fps; no captions, no card, no narrator explaining the
  mystery (a jury veto); the beat list IS the beat sheet — the self-revelation at 90 % of the runtime,
  anchors 0/12/25/50/75/90/95 % (`film-preprod`), each beat a subworld.
- **Build outward from the hero shot**: the shot the film is built around is generated and cut in
  first; if it does not land the film does not exist. A 15 s beat that exceeds the venue's clip ceiling
  is designed as two clips cut on a blink or a caught breath.
- **Coverage → sequence**: composition over coverage; restrained camera; a held close-up cuts on the
  breath, not on the action; the reveal's asset appears in no earlier shot (never pre-load the reveal).
- **Sound leads**: motivated practical sources; the mix crests WITH the push-in, not before; no
  irony/knowingness; a dark ending stays dark when the brief is a dark fairy tale.
- **Markers** are story beats measured on the keeper (a breath, a door, a light change) rather than a hit.

## Music video

- **Track map before the gen map**: BPM, bar, 8-bar phrase, and the hits everything cuts to (near-
  silences, drops, peak bass) measured from the audio; the whole timeline allocated first — later beats
  are placements paid for by trimming, never appends.
- The operator cuts to the track; the EDIT is locked before finishing; the flattened master carries
  the cut's own processed audio (no VO stem, no captions).
- Generation order is dependency-bound: a shot that continues another waits for its last state.

## The edit-library (design pointer, not a load path)

An edit-library design (not shipped here) defines
`EditPreset {genre, measured{cut_length p10/p50/p90, pacing_curve, music_energy_map}, authored{hook,
captions, transitions, beat_sync{policy, tolerance_ms}, word_padding_ms}, inherited{generation_floor_s,
handles}, thresholds{…: {min, max, over: "<the failure, named>"}}, status}`. **Only a `validated`
preset loads**; a `provisional` one is vocabulary and a starting distribution to read, never a setting.
Until a preset is validated on your own spots (held-out, predeclared threshold), the grammar above is the
preset, and the operator's notes on the delivered cut are the only taste signal that counts.
