# Build — the project, the host and scene contract, captions, the pilot

The general composition contract (determinism, local assets, the render host, the render rules) is
`designed-elements` HYPERFRAMES-CONTRACT. An explainer adds one host and many scene sub-compositions.

## The project

```
<name>/
  explainer.json        name · canvas · fps · target_s · lead/tail/exit/ending-fade seconds · caption style · content_box
  script.md             the display text, one `## <scene-id> <title>` per scene
  storyboard.json       one row per scene (STORYBOARD.md)
  copy.md · facts.md    the approved on-screen strings · every claim with its source URL and date
  index.html            the host — slots and duration written by explainer_timeline.py
  compositions/scenes/<id>.html
  compositions/captions.html   generated
  assets/fonts/Display.ttf · assets/audio/vo.wav
  timeline.json         generated — scene windows, beats, caption blocks, the checks
  renders/<name>.mp4
```

## The host (`index.html`) — thin

One slot per scene (`data-composition-src="compositions/scenes/<id>.html"`, `data-composition-id="<id>"`), the captions
slot, the voice as `<audio id="<name>-vo">` at the root on a high track, a near-empty root timeline. The slots and the
root duration belong to `explainer_timeline.py`; an edit by hand is overwritten on the next run.

## A scene (`compositions/scenes/<id>.html`)

- **Everything inside `<template>`** — styles, markup, script. The file's head is dropped when the host mounts it.
- `@font-face` declared inside the template (lint reads each file on its own), its URL relative to the project root.
- The root styled by `#root`, never by a class on the root; every element id prefixed `<id>-`.
- **One paused GSAP timeline** registered as `window.__timelines['<id>']` after it is built. The host slot's
  composition id, the scene root's composition id and the timeline key are the same string — a mismatch renders
  frozen, silently.
- Entrances with `fromTo`. A beat entrance takes `immediateRender: false`, so it stays hidden until its beat; a
  continuation of the same property is a `to`.
- **Times come from `BEATS`** — scene-local seconds written from the narration; a literal time in a scene is a defect.
- **Every on-screen string lives in `COPY`**, whole (the source audit reads it); every random number from a seeded PRNG.
- The first element enters on frame 1 above zero opacity; the exit reaches zero before the cut, 1 − (n/N)^1.5.
- **A hero reads by luminance**: a light stroke or fill on a dark ground. The frame instrument sees luminance — a dark
  card on a dark ground read EMPTY (hero 0.12) and the same card with a light stroke read 0.42 (pilot, 2026-09-12).
- Content stays above the caption band (`explainer.json` `caption.top_frac`); `content_box` is the frame instrument's
  crop.

`explainer_new.py` writes every scene this way; start from its scene and keep the markers.

## Captions

`explainer_timeline.py` writes `compositions/captions.html`: blocks built from the display text, aligned to the spoken
words position by position, lines broken by the caption font's measured advance, each line `white-space: nowrap` (no
`<br>`), shown 0.05 s before the first word and held 0.5 s after the last, held through gaps under 0.6 s. The display
face at `assets/fonts/Display.ttf` is the one measured, so it is the one rendered.

## The shared layer, the probe, the pilot

- **Tokens and primitives go in the shared layer before the second scene.** A primitive every scene needs, left out of
  it, gets written once per scene and differently each time (upstream: one fade helper, four implementations, four
  formulas).
- **Probe** every state of a shared system in one render before scenes depend on it (upstream: eight camera states in
  ten minutes caught an empty frame and a subject too near the wall, before three scenes were built on them).
- **The pilot**: the first 20–30 s, styled, rendered and shown. Changes land in the shared layer and the pilot scene.

## Render

`render_hyper.sh --host <render host> --push --pull` (WSL2's headless Chromium hangs); `npx hyperframes lint` on the host
first, 0 errors. The script prints `RENDER-END` only when the output exists and `RENDER-FAILED` otherwise. A two-scene
1080×1920, 30 fps, 11 s pilot with captions and a voice track rendered in 11–13 s on the render host (2026-09-12).
