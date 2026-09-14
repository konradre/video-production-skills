# Dehancer `.drx` recipes — the spatial tier (authored in Resolve, once per look)

The `.drx` is the **hero-pass renderer** of each look: the full grade (colour + physics) in one Gallery
still. It is NOT stacked on the `.cube` — the `.cube` is the same look's colour-only approximation for
every non-Resolve path (ffmpeg `lut3d`, a render farm). Parallel renderers, one look. The method and the
consensus ranges: `GUIDE.md` §3–§4.

**Authoring cannot be scripted** — the Resolve API cannot write OFX params. The five shipped `drx/*.drx`
were dialled in once, by hand, from the recipes below on Dehancer Pro OFX 7.4 and Resolve Studio 18.5;
they apply unattended via `Timeline.ApplyGradeFromDRX` (`tools/resolve-pass/resolve_pass.py`; smoke:
`tools/resolve-pass/smoke_apply_drx_render.py`). A new look, or a rebuild on another Dehancer major
version, follows the same recipe.

## Common frame

- **Node 01** = corrections (wheels per look, below). **Node 02** = Dehancer, always last.
- Dehancer Input = **Rec.709 / no camera profile** (AI-gen video is display-referred, `GUIDE.md` §2).
- Export: Color page → grab Gallery still → right-click → *Export* → save as `<id>_<version>` into your
  looks export folder → copy the `.drx` here as `drx/<id>.drx` → rebake `index.json` hashes
  (`python3 build_cubes.py`).
- After each export: smoke it on a **fresh** clip (`smoke_apply_drx_render.py <path to the .drx>`), expect
  `SMOKE-OK` and `nodes_after` ≥ 2.
- ⚠ Dehancer wheels/curves stay INSIDE Dehancer; Resolve wheel values below are Node 01.

## Per-look dial-in

### ads-clean.drx  (Total Impact ~35)
| Dehancer | value |
|---|---|
| Film / Print | Kodak Vision3 250D / Kodak 2383 (the "clean" stock) |
| Halation | **OFF** |
| Bloom | OFF |
| Grain | **OFF** |
| Total Impact | **35** (ads restraint: 30–50) |

Node 01: Gain ≈ (1.02, 1.01, 1.01) · slight S-contrast (pivot 0.46) · Sat 1.04.

### ads-warm.drx  (Total Impact ~40)
| Dehancer | value |
|---|---|
| Film / Print | Kodak Vision3 250D / Kodak 2383 |
| Halation | OFF |
| Bloom | light (≤0.1) — the "glow" reads as warmth without grain cost |
| Grain | **OFF** |
| Total Impact | **40** |

Node 01: warm Offset (temp +0.18 equiv) · Gain ≈ (1.04, 1.00, 0.95) · Sat 1.06.

### film-teal-orange.drx  (Total Impact ~80)
Start from a first authored look on the same stock (Vision3 250D / 2383, Halation + Bloom 35 mm/Super 35,
Grain 16 mm ISO 250, TI 100). Changes only:

| change | value |
|---|---|
| Total Impact | 100 → **80** (film: 70–90) |
| Grain amount | pull LOW — the upscaler already re-injects shadow grain |
| Node 01 wheels | Lift RGB **−0.026 / +0.014 / +0.043** (±0-centred boxes) · Gain RGB **1.050 / 1.020 / 0.978** (⚠ Gain boxes are MULTIPLIERS around 1.00 — never type the delta) · Contrast 1.15, Pivot 0.440 · Sat 55 |

Export as `film-teal-orange_1.0`. (The first authored look stays untouched as the archive.)

### film-portra.drx  (Total Impact ~75)
| Dehancer | value |
|---|---|
| Film / Print | **Kodak Portra 400** / Kodak 2383 |
| Halation | 0.35 subtle, 35 mm |
| Bloom | light |
| Grain | 16 mm ISO 250, amount LOW (the skin look — portrait variant) |
| Total Impact | **75** |

Node 01: warm trims per `looks/film-portra.yaml` (temp +0.09 equiv, gentle).

### film-cinestill.drx  (Total Impact ~85)
| Dehancer | value |
|---|---|
| Film / Print | **CineStill 800T** if the profile list has it, else Kodak Vision3 500T / Kodak 2383 |
| Halation | **0.9** — the signature red ring is THE point (night: 0.75–1.1) |
| Bloom | moderate |
| Grain | 16 mm ISO 250, amount LOW |
| Total Impact | **85** |

Node 01: cool cast per `looks/film-cinestill.yaml` (temp −0.14 equiv, blue-lifted Lift).

## Verifying a `.drx` on real footage

The smoke proves `nodes_after ≥ 2` — that the grade landed — **not that halation, bloom or grain came
with it.** Verify by a 1:1 crop of graded against ungraded on a backlit highlight: halation reads as a
warm-red bleed around the highlight, grain as texture across flat areas. On the first live use of
`film-cinestill` both were present; the high-frequency energy on a smooth-gradient frame rose only ~26%
because the grain amount is deliberately LOW, so **the HF number alone is NOT sufficient evidence; the
1:1 visual is.**

⚠️ **Do not try to confirm a `.drx`'s contents by grepping it.** The file is XML, but OFX parameters
are stored encoded in long attribute values — `grain`, `halation`, `bloom`, `Dehancer` and `OFX` all
return **zero** matches on a `.drx` that demonstrably carries all of them. A string search here
produces a confident false negative.

**Downstream consequence:** because the `.drx` already lays down grain at mezzanine resolution, a finish
plan must NOT add a separate grain pass — that doubles it. See the `video-finish` skill §6.

⚠ Dehancer-generated `.cube` files (the LUT Generator export) are licence-restricted (Dehancer Ltd,
licensee-only) — never commit or publish them; cubes baked by `build_cubes.py` from MIT spectral bases
and your own parameters carry no such restriction.
