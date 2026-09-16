# Captions — the campaign standard

One style for every clip of a campaign, fixed in the EDL's `caption_style` and rendered by
`build_captions.py` as RGBA cards at DELIVERY resolution, which the finisher overlays AFTER the downscale
so the type stays crisp.

## The house default

| rule | value |
|---|---|
| font | one display face (style `A`), white, black stroke, soft shadow, centred at 70 % height, max 86 % width |
| case | ALL CAPS |
| punctuation | **NEVER** — no periods, commas, question marks, ellipses; contractions keep the apostrophe; hyphenated compounds split into two words |
| highlight | the spoken word in the brand colour (a colour taken from the wordmark) |
| whose lines | the narrator only; never a character's dialogue, never an O.S. line |
| cards | word ranges per line; three-word cards for a fast disclaimer; a quip's card follows its VO variant exactly |
| timing | show 0.05 s before the first word, hold 0.5 s after the last; a card ends **one frame before the next card's lead**; nothing over the end card |

A card's line breaks come from the font's measured advance — `build_captions.py` lays each line out with the TTF's
own `textlength` against the card width — never from a character count, which mixed scripts and wide capitals defeat.

## A campaign's own style — set by measurement

When the client's reference carries captions, measure them on a frame at the reference's own width — cap height,
line pitch, block centre, stroke, shadow, case, emphasis — and set the style from those numbers, never from an
adjective ("subdued", "UGC-like"). Punctuation stays banned unless the operator lifts it; a reference that shows a
comma does not lift the rule.

| key | reads | default |
|---|---|---|
| `font` | `A` Bangers · `B` Inter (variable) · `C` Nunito (variable) · or a font file name, under the fonts dir | `A` |
| `weight` | a variable font's named instance (`Black`, `SemiBold`) | `Black` on `B` |
| `size_h` · `stroke_h` · `shadow_h` | fractions of the canvas height | 0.058 · 0.0055 · 0.004 |
| `shadow_alpha` | 0–255 | 150 |
| `line_h` | line pitch as a multiple of the size | 1.12 |
| `y` · `max_w` | block centre (fraction of height) · card width (fraction of width) | 0.70 · 0.86 |
| `highlight` | `#rrggbb`, or `none` — one plain layer per card, no per-word emphasis | `#ffe01b` |
| `upper` | ALL CAPS | `true` |
| `lead` · `hold` | seconds before the first word · after the last | 0.05 · 0.5 |

**An unknown key stops the build.** A style block whose key names matched nothing the builder read once rendered the
defaults for a whole job and looked deliberate. Keys starting with `_` are notes.

**Placement is checked against OUR frames, never copied from the reference.** A block centre measured on a client's
reference sat across the faces of a two-shot whose subjects sit higher in frame than the reference's: read the caption
band against every event's frames at the cards' display times before the render ships.

## The words

The display text is the script's (`audio.vo[line].text`); the transcript supplies timing only. A transcript's
capitalisation is not the client's copy — a mid-sentence word came back capitalised, invisible under ALL CAPS and
wrong the moment the case changed — so script word *i* pairs with time *i* only when the two counts agree, and the
builder stops otherwise (re-run that line's word times with `--only`).

## Word times

`vo_word_times.py` writes `{LINE: [[word, start, end]…]}` relative to each VO file; timeline time is
`vo[line].at + word time`. Local faster-whisper is free and merges hyphen fragments; Scribe bills per
minute. A swapped take re-runs that line ONLY (`--only`) so hand patches on the others survive. Whisper
mis-times onsets in noisy sections — patch by ear against the placement check, never by re-running.

## Card boundaries — half-open, never `between()`

The cards are PNG layers composited by `video-finish-qc/scripts/finish_spot.py`, and the expression that
switches them is load-bearing. **`enable='between(t,a,b)'` is inclusive at BOTH ends**, so two layers that
share a boundary are both enabled on the frame that lands exactly on it. Every word-highlight layer inside a
card shares one by construction: `build_captions.py` hands layer *k* the `t1` that is layer *k+1*'s `t0`.
Card-to-card the builder already leaves a frame of air (`nxt - LEAD - 1/24`), so a card-to-card collision
cannot arise; the exposure is the highlight layers alone. No delivered spot is known to have carried the
defect — what follows is the mechanism reproduced in a scratch render, not an incident.

Measured 2026-09-17 in a scratch render, 24 fps, boundary at t = 1.0: with `between()` one frame composited
both layers; with `enable='gte(t,a)*lt(t,b)'` zero frames showed both **and** zero showed neither. The
half-open form is the fix. **An epsilon trim is not** — subtracting 2 ms from the earlier layer trades a
collision that needs exact equality for an uncovered window 2 ms wide, and at 24 fps a frame lands in that
window about one time in twenty. A doubled frame is a smudge; a blank frame is a missing caption.

A designed card that carries a **colour emoji** is rendered by PIL with `embedded_color=True`; ffmpeg's
`drawtext` cannot draw one at all, which is the reason these are PNG overlays rather than a text filter.

## Alternates

An alternate quip or an alternate cut is its own EDL with its own captions; a caption never carries a
line the deliverable does not voice.
