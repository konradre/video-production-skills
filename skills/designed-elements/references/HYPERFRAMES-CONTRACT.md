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
- **Anything that flows is a tweened DISTANCE, never an accumulation.** `pos += speed * dt` per frame is the
  determinism hole the seeded PRNG does not close: the value depends on how many frames happened, so a scrub lands
  somewhere else than a playthrough and two renders of one composition differ. Tween the distance (`flow` to
  `+=300`) and make each element's position a pure function of `(its seed, flow)`. The same rule retires the other
  three clock readers: no `Date.now()` or `performance.now()` — the timeline's time is passed in as a parameter; no
  `setInterval` for a typewriter or a counter — tween `{i: 0 → n}` and slice on update; a high-frequency sine
  (`sin(t * 137.2)`) where jitter is wanted, seeded once at load where randomness is.
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
  all local. Text in a display face is DESIGNED here — packaging text from a generator corrupts ("WARNIGY").
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
- `npm run check` (lint + runtime + layout + motion + contrast) before a render round.
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

## What the EDL needs from an element

| element | EDL | notes |
|---|---|---|
| a designed event (turntable, display) | `{take: hyper/<name>/renders/<name>.mp4, in: 0, out: <dur>, source: designed, look: <cube>, handle_head: 0}` | plays its full length; graded by the cube (not pre-graded) |
| the end card | the same + `role: endcard` | exactly one; 2.5 s FULL; ungraded; the sting at `tl[0] + 0.02` |
| a layer (wall, drift) | `post_layers: [{id, frames: hyper/<name>/frames/frame_%06d.png, at, dur}]` | composited at the mezzanine over the footage; a wall is placed `join − lead` so it is opaque across the join |

The card's burst frame, the wall's opaque frame and the turntable's ding times are the numbers the edit
and the sound derive from — they live in the composition and are printed by its check.
