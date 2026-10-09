# The composition contract — what a designed element must obey to render

Designed motion is code-rendered, deterministic and CPU-bound: an HTML composition rendered by HyperFrames
(heygen-com, Apache-2.0) through headless Chromium. It is the easy lane — infinitely revisable, byte-
reproducible — and it is fenced from generation: nothing here touches a diffusion model, a prompt
dialect or the GPU lease.

## The project

```
hyper/<name>/            one project per element AND per length: card-5p5s, drift-a-4s, wall-a
  index.html             the composition (one file; GSAP from the CDN, everything else local)
  hyperframes.json       paths (compositions, components, assets), media.autoProxy
  package.json           pinned: npx --yes hyperframes@<version> preview|check|render
  assets/                fonts/, the label texture, the cut-outs, the sprite cells — LOCAL files only
  renders/<name>.mp4     a designed EVENT (turntable, card): mp4 at the canvas raster, CRF 12
  frames/frame_%06d.png  a LAYER (wall, drift): a PNG sequence WITH ALPHA for the finisher's post_layers
```

**A new length is a NEW project** (`card-4s` → `card-5p5s`): the duration sits in `data-duration`, the
timeline and the name; an event in the EDL plays its render's FULL length.

**A new VERSION at the same length is a new RENDER FILE** (`renders/<name>-v6.mp4` beside `-v5`), never an overwrite
of the accepted render; each spot's EDL names the card it carries by path, so adoption is a re-finish of every
spot that should carry the new one — the round ledger lists which spots carry which version. A card fixed in one spot and not re-finished into the others ships two cards.

## index.html

```html
<div id="root" data-composition-id="<name>" data-start="0" data-width="2160" data-height="3840" data-duration="2.5" data-fps="24">
  <section class="clip" data-start="0" data-duration="2.5"> … </section>
</div>
<script>
  var tl = gsap.timeline({paused: true});               // ONE paused timeline drives everything
  tl.to(state, {p: 1, duration: 2.5, ease: 'none', onUpdate: draw}, 0);   // canvas work = a tweened progress object
  window.__timelines['<name>'] = tl; if (window.__hfForceTimelineRebind) window.__hfForceTimelineRebind();
</script>
```

- `data-composition-id` = the project name; `data-width/height` = the render raster (the mezzanine
  raster for an event that will be cut with heroes — 2160×3840 for a 1080×1920 spot; the delivery raster
  for a layer the finisher scales).
- Every random number comes from a **seeded PRNG** (`mulberry32(seed)`): a render is reproducible, and a
  "fix one thing" round changes one thing.
- Canvas elements draw from a tweened progress object inside the timeline, never from `requestAnimationFrame`
  or wall-clock time; images are loaded before the timeline is registered (`build()` after the last
  `onload`).
- **The timeline is built synchronously and registered last.** A build that must wait — images, or fonts when text is
  measured rather than computed — runs inside the wait (`document.fonts.ready`, the last `onload`), registers
  `window.__timelines[id]` at the END of that callback and then calls `__hfForceTimelineRebind()`. Registering first
  nests an empty timeline when the comp is a sub-composition (the engine's lint error
  `gsap_timeline_registered_before_async_build`). Fit computed from an advance table never needs the font wait.
- **Motion lives on the ONE timeline.** No CSS `transition`: it starts when its style changes, so a cold render worker
  starts it at its own first frame and every worker split shows a different frame (measured, § Silent traps). CSS
  `@keyframes` are seeked exactly in an mp4 render, but in a png-sequence LAYER an opacity keyframe animation renders at
  full opacity once it starts — so a layer tweens opacity on the timeline. `det_check.py source` fails a transition and
  warns on an opacity `@keyframes`.
- **Things move by transform.** `x`/`y`/`scale`/`rotation`, never `top`/`left`/`width`/`height`/`margin`/`padding`,
  `fontSize` or `letterSpacing`: layout values snap to whole pixels, so slow motion steps (the engine's lint error
  `gsap_non_transform_motion` — it reads tween vars only, so an `onUpdate` writing `style.left`/`style.top` snaps the same
  way and passes unflagged).
- **Anything that flows is a tweened DISTANCE, never an accumulation.** `pos += speed * dt` per frame is the
  determinism hole the seeded PRNG does not close: the value depends on how many frames happened, so a scrub lands
  somewhere else than a playthrough and two renders of one composition differ. Tween the distance (`flow` to
  `+=300`) and make each element's position a pure function of `(its seed, flow)`. The same rule retires the other
  three clock readers: no `Date.now()` or `performance.now()` — the timeline's time is passed in as a parameter; no
  `setInterval` for a typewriter or a counter — tween `{i: 0 → n}` and slice on update; a high-frequency sine
  (`sin(t * 137.2)`) where jitter is wanted, seeded once at load where randomness is.
- **A 2D canvas is opened with `getContext('2d', {willReadFrequently: true})`.** Chrome changes a large canvas's raster
  path after its first presented frame, so the first frame each render worker draws comes out different from the same
  frame drawn mid-sequence — fixed by this one option (§ The determinism proof).
- **Expose a seek, and capture through it.** `window.__hfSeek = t => { tl.pause(); tl.time(t); gsap.ticker.tick();
  draw(t); }`. Two traps, both silent, both producing a plausible WRONG frame: a screenshot taken straight after
  setting the time is **one tick stale**, because the library writes styles on the next tick and the canvas waits for
  a frame that a hidden tab throttles — so a capture seeks, waits two animation frames, seeks **again**, then shoots;
  and **pausing at a time suppresses the timeline's callbacks**, so an `onUpdate` that applies a camera or redraws a
  canvas never runs during a scrub — call it explicitly after the seek rather than relying on the tween to fire it.
  Every frame-level instrument in this kit reads frames produced this way.
- Display copy lives in the HTML or in one `COPY = { … }` object in the script, whole — never assembled from fragments
  in code, which `literal_audit.py` cannot read.
- No network at render for assets: fonts (`@font-face` from `assets/fonts/`), textures, cut-outs, sprites
  all local. Text in a display face is DESIGNED here — packaging text from a generator corrupts ("WARNIGY"). GSAP is the
  one exception: from the CDN at an EXACT version (`gsap@3.14.2`, as the scaffolds write it; never the engine docs'
  floating `gsap@3`). Its tag is parser-blocking, so the timeline is never built before it loads.
- **A PNG asset carries no colour chunk** (`gAMA`, `cHRM`, `iCCP`, `cICP`). Chromium colour-manages a PNG that has one,
  so the render departs from the file's own pixel values: a 128 grey with `gAMA` 1.0 rendered 188 (measured, png and
  mp4). Save the art as plain sRGB values; `det_check.py source` lists any PNG that still carries one.
- The composition's sound sync is a constant (`T0`, e.g. 0.83 s): the burst fires on the audio signature's hit,
  and it is the constant that moves when the sound is re-timed, never the sound (`spot-audio-assembly` § signature).

## Rendering

```bash
render_hyper.sh --dir hyper --name <name> --format mp4 --host <render host> --push --pull            # an event
render_hyper.sh --dir hyper --name <name> --format png-sequence --host <render host> --push --pull   # a layer
```

- **WSL2's headless Chromium hangs** — render on the GPU VM through a login shell with Node ≥ 22
  (`~/.local/bin` on the PATH), its own Chrome cache, `unzip` present. `--workers 2`, a timeout above the
  job, the sentinel `RENDER-END`; a log without it is a failure. `render_hyper.sh` prints it only once the mp4 or the
  frames exist, and `RENDER-FAILED` with exit 1 otherwise.
- `render_hyper.sh` runs `hyperframes check` (lint + runtime + layout + contrast; the motion audit runs only beside a
  `<comp>.motion.json` spec, so the summary reads `motion off`) before every render, REPORT-ONLY, once per zone of the
  project's declared safe band (`video-production` SAFE-AREAS.md, read from `delivery-targets.json` by `safe_zones.py`; the
  strict ad union when none is declared; `--keep-out` adds a zone): `renders/check.json` (the full report, run alone),
  a `renders/check-zone<N>.json` per further zone (run at once, contrast off), each under `--check-timeout`, and
  `check_summary.py`'s read. A zone hit is a WARNING, so `ok` stays true: read the ZONE lines. A LINT error stops the layout
  audit (duration 0, no samples) — such a comp was never laid out, so fix the lint first. Two lint errors recur on reused
  comps: a font stack naming a family with no `@font-face` (`'Bangers', Impact, sans-serif` → `font_family_without_font_face`)
  — a stack names `@font-face` families and one generic, nothing else; and a project copied to a new name with only one of
  `data-composition-id` and the `__timelines` key renamed (`timeline_id_mismatch` — the render still succeeds, which hides
  it). Audit artefacts, not defects: per-word masked reveals read as `text_occluded`/`content_overlap`; a png-sequence layer
  is checked with `--no-contrast`. A gate comes later, for comps made after this rule, with declared findings.
- **Headless Chromium fails slowly or silently, never loudly**: a blur with σ < 0.8 has no effect; `feConvolveMatrix`
  drops to a software path (0.13 fps measured upstream); an SVG filter carries `color-interpolation-filters="sRGB"`;
  keep a frame under ~600 DOM nodes and 6 SVG filter instances; render a 30-frame test at a 3 fps floor before a
  full render.
- **Fit text by computation, never by measuring the DOM at render time**: width from a per-face advance table measured
  once with fontTools (a humanist sans ran ≈ 0.57 em lowercase · 0.67 capitals · 0.59 digits — measure YOUR face);
  `letter-spacing` counted once per character, because Chromium adds it after every glyph and it does not scale with
  the font size. A fit that bottoms out below ~78 % of the design size means the copy changes, not the size. The fit
  is then deterministic whatever the font-load timing — the same guarantee as the seeded PRNG.
- A layer is verified with `layer_check.py` (contiguous frames, RGBA, the frame it becomes opaque); an
  event with `ffprobe` (raster, duration = `data-duration`, 24 fps).

## Silent traps — what the render host's engine does, measured

Measured 2026-10-10 on hyperframes 0.8.18 with GSAP 3.14.2, as png-sequence and mp4, at 1 and 3 workers. Every row
failed silently: a plausible frame and no error. Re-measure after an engine upgrade before trusting a row.

| trap | what the render shows | the rule | caught by |
|---|---|---|---|
| a CSS `transition` | a cold worker starts it at its own first frame, so each split shows another colour (191,0,64 against 234,0,21 at 1.5 s) | tween the change on the timeline | `det_check.py source`, FAIL |
| an opacity `@keyframes` in a png-sequence layer | full opacity from the moment it starts; an mp4 renders the same animation exactly | a layer tweens opacity on the timeline | `det_check.py source`, WARN |
| `will-change: transform` on text that scales up | drawn once at its first size, then stretched: 16 px text scaled 3× lost its stencil cuts (edge energy −22 %) | no `will-change` on anything that grows past its first size; translation and a scale down to rest are unaffected | `det_check.py source`, WARN |
| a PNG carrying `gAMA`, `cHRM`, `iCCP` or `cICP` | colour-managed: a 128 grey with `gAMA` 1.0 renders 188 | plain sRGB values with no colour chunk (§ index.html) | `det_check.py source`, WARN |
| a colour tween between hues, written in hex, `rgb()` or `hsl()` | interpolated in sRGB: blue → yellow passes through grey, 128,128,128 | write both ends as `oklch(L C H)`: GSAP tweens the three numbers (midpoint 0,207,189); the hue moves as a number, so write one end as H ± 360 to take the short way round | the eye |
| a blur across a worker split | 4 px off by 1 code value at the second worker's first frame | none: Chromium's antialiasing | `det_check.py frames` reports it as NOISE |

**The engine's own lint catches these.** `render_hyper.sh` runs `hyperframes check` before every render, and
`check_summary.py` prints every lint error and the warnings marked below by message:

- `gsap_cold_seek_hidden_fromto_missing_reveal` (error): an element the CSS starts hidden, made visible only in a
  `fromTo`'s from-vars, stays invisible on a cold worker. Put `opacity: 1` in the destination. A non-opacity property
  set only in the from-vars measured stable across splits.
- `gsap_timeline_registered_before_async_build` and `gsap_non_transform_motion` (errors), in § index.html.
- `gsap_animates_clip_element` (error): `autoAlpha`, `visibility` or `display` on a `.clip` fights the runtime's own
  visibility control. Animate a child instead.
- `gsap_css_transform_conflict` (error): GSAP overwrites a CSS `transform` on an element it transforms, a
  `translate(-50%, -50%)` centring included. Centre with flex or `inset`, and give the start values in the `fromTo`.
- `gsap_repeat_refresh_relative_value` and `gsap_relative_value_second_writer` (errors): a relative value accumulates
  differently on a cold seek.
- `html_dir_attribute_breaks_render` (error): `<html dir="…">` renders a blank video.
- `font_family_without_font_face` (error) and `system_font_will_alias` (warning, printed): fonts are local
  `@font-face` (§ Rendering).
- `gsap_callback_dom_measurement` (warning, printed): DOM measured inside a callback runs again on every seek, against
  that worker's own state. Measure once, at build; this contract computes text fit instead.
- `subcomposition_blanks_before_host` (warning, printed): a sub-composition slot that ends before its host leaves the
  frame blank.
- `overlapping_gsap_tweens` (warning, printed): two tweens write one property at the same time.
- `gsap_infinite_repeat` (warning): `repeat: -1` is clipped to a declared `data-duration` and renders deterministically.
  `gsap_repeat_floor_unclamped` and `gsap_repeat_ceil_overshoot` (warnings, printed): a computed repeat that turns into
  −1 or runs past the comp.

**Reported elsewhere, not reproduced here** (png and mp4). Keep these out of this contract unless a new measurement on
the render host's engine brings one back:
- `background-clip: text` rendering invisible;
- a font family named in an external stylesheet escaping its face (a local `@font-face` there renders the same as an
  inline one);
- a `mix-blend-mode` clip blending against nothing (over a clip and over a sub-composition, it blends);
- a sub-composition whose timeline ends before its slot being hidden (the authored `data-duration` governs: a 1 s
  timeline in a 4 s slot stays visible);
- a font face first requested mid-film losing the load race on a cold worker (a local face renders on its first frame);
- a `filter` tween from `none` jumping;
- CSS `@keyframes` drifting in an mp4;
- the render's audio coming out quieter. Integrated loudness is unchanged; true peak rose 1.1 dB on a test tone, which
  is inside `spot-audio-assembly`'s −2.4 dBTP master margin for a −1 dBTP delivery.

**CSS, SVG and GSAP behaviour every Chromium shares.** Each is silent and gives a plausible wrong frame:
- A blend mode composites only inside its own stacking context: an ancestor with a `filter`, `opacity` below 1, a
  `transform`, `isolation` or `will-change` cuts it off from what lies beneath. A blend inside a transparent LAYER has
  only transparency beneath it, and the finisher composites the layer with plain alpha, so the blend never meets the
  footage. A layer uses plain alpha.
- A `filter` flattens the 3D space inside its element (a grouping property forces `transform-style: flat`). Blur or
  warp each plane of a CSS-3D turntable, never the wrapper that holds the perspective.
- Changing `transformOrigin` while an element is scaled or rotated moves it. Set the origin at build, or while the
  transform is the identity.
- `em` spacing beside big type resolves against the PARENT's font size: a `gap` in `em` in a flex container around
  200 px type is relative to 16 px. Write px.
- A visibility gate on an eased value fires early when the ease is solved numerically, because bisection returns about
  1e-9 at 0. Gate on time or on tween progress, and make a hand-written ease return exactly 0 and 1 at its ends.
- From the `bang-motion` upstream (2026-09):
  - a more specific selector defeats an element's initial `opacity: 0`: keep the hidden state on the least specific
    selector, and `immediateRender: false` leaves the CSS holding it;
  - an SVG filter's default region (110 %) clips the tail of a blur: set x and y to −70 % and width and height to 240 %;
  - directional motion blur is `feGaussianBlur stdDeviation="x y"` (CSS `blur()` reads as out of focus), and the
    filter is detached when the tween ends;
  - text split before `document.fonts.ready` measures the wrong advances;
  - a running counter jitters its container unless it has `font-variant-numeric: tabular-nums` and a `min-width`;
  - a dashed stroke cannot be drawn with `stroke-dashoffset` (it walks): open a `clip-path: inset()` from one side;
  - a round linecap at dash length 0 shows a dot: hold opacity 0 until the draw starts;
  - a child SVG's own `visibility="visible"` beats a hidden parent: remove the attribute;
  - a blur tween writing `filter` overwrites a colour filter on the same element: colour filters go on the `<img>`;
  - a group scale shrinks the type inside it (CRAFT § Readable time).

## The determinism proof

A render is split across `--workers`: each worker is a fresh page that renders one contiguous run of frames, starting
cold (24 frames over 3 workers start at frames 0, 8 and 16). So a composition that is not a pure function of time does
not fail loudly — it renders a seam at every split, and a different one at a different worker count. `det_check.py`
checks it (pattern: `procedural-film`'s `check.cjs`, which hashes each shot's first, middle and last frame warm, reversed,
shuffled, cold and in sequence; ours renders through the real renderer instead of a harness):

```bash
python3 ~/.claude/skills/designed-elements/scripts/det_check.py source hyper/<name>                        # free, every round
python3 ~/.claude/skills/designed-elements/scripts/det_check.py prove hyper/<name> --host <render host>    # two renders, --workers 1 and 3
```

`source` reads the composition's own script (comments ignored) for `Math.random`, `Date`, `performance.now`, crypto
randomness, `requestAnimationFrame`, `setTimeout` / `setInterval` and a bare `getContext('2d')`; a deliberate use carries
`det-ok: <reason>` in a comment on its line. It reads the CSS too (`<style>`, `style=""`, the project's own `.css`): a
`transition` FAILs, while an opacity `@keyframes` and a `will-change: transform` WARN. Any PNG carrying a colour chunk
WARNs (§ Silent traps). It cannot see an accumulation, and a path with no `index.html` exits 2 rather than pass. `prove`
renders twice as a png-sequence,
compares every frame on the decoded pixels on the host, and reports each scene's first, middle and last frame and where
in the frame each difference lies. A frame off by at most 2 code values on at most 0.01 % of its pixels is reported as
NOISE and does not fail: Chromium's antialiasing at a worker's first frame after a blur (4 px off by 1 code value,
measured on 0.8.18). A large bare canvas's seam at a worker's first frame (§ index.html) is many times wider than the
band, and still fails. The where matters: a clip that spans the whole film is named as the scene of every differing frame. The proof
frames stay on the host under `<remote-dir>/.det/<name>/<stamp>/`; it refuses a project whose `frames/` holds PNGs, and
`--no-push` renders a copy already on the host (the push mirrors the local project with `--delete`).

The proof compares png-sequence frames because they are lossless: two mp4 encodes cannot isolate one cell, since a
cell that really differs spreads encoder noise across the frame. Without such a cell, two mp4s at different worker
counts decoded bit-identical. The mp4 capture path differs from the png one in one measured way (an opacity
`@keyframes`). So a passing proof speaks for the composition, and the delivered mp4 is still read on the delivered frame
(SKILL § 4).

Measured 2026-09-29 on the render host, hyperframes 0.8.18, `--workers 1` against `--workers 3`:

| composition | frames that differ | what it shows |
|---|---|---|
| a seeded 320×180 canvas | 0 of 24 | the pass case |
| the same with `Math.random` | every drawn frame | `source` catches it too |
| the same with `acc += 3` in the `onUpdate` | 8–11 (the second worker's run, while the canvas is on screen) | `source` sees nothing; only the render does |

The 320×180 canvas passed without the option, so a small canvas can stay on one raster path; a large one does not —
its first frame per worker differs from the same frame drawn mid-sequence. The option costs nothing, and `hyper_new.py`
writes it.

## What the EDL needs from an element

| element | EDL | notes |
|---|---|---|
| a designed event (turntable, display) | `{take: hyper/<name>/renders/<name>.mp4, in: 0, out: <dur>, source: designed, look: <cube>, handle_head: 0}` | plays its full length; graded by the cube (not pre-graded) |
| the end card | the same + `role: endcard` | exactly one; 2.5 s FULL; ungraded; the sting at `tl[0] + 0.02` |
| a layer (wall, drift) | `post_layers: [{id, frames: hyper/<name>/frames/frame_%06d.png, at, dur}]` | composited at the mezzanine over the footage; a wall is placed `join − lead` so it is opaque across the join |

The card's burst frame, the wall's opaque frame and the turntable's ding times are the numbers the edit
and the sound derive from — they live in the composition and are printed by its check.
