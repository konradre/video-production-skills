# The reusable kit — the element KINDS every campaign fills, dialled in once, customised per SKU

A campaign's kit is one row per element kind below, each with the number the edit uses. The kinds and their
edit rules are universal; the second table is ONE campaign's filled kit (a packaged snack, 2026-09), kept as
the worked example — a new campaign fills the same columns and nothing else changes downstream.

## The kinds (fill one row per element the campaign uses)

| kind | what it must carry | the number the edit takes from it |
|---|---|---|
| **the end card** | the brand world from the client's own art, SKU-neutral; a designed EVENT at its full length | `role: endcard` on one EDL event; its sync constant `T0` if a sound lands on it |
| **the closer bed + the audio signature** | the bed under the display and the card; the signature's hit | the hit's offset in the file → `spot-audio-assembly` places it |
| **the piece wall** | a LAYER of the SKU's silhouettes that covers the frame, holds, then leaves | its opaque window → placed at `join − lead` so it straddles a cut |
| **the drift** | a LAYER of pieces over a display event, at that event's length | `at = <event> tl[0]` |
| **the turntable / display** | the product on a designed display from the label texture — never generated | `look:` cube; the closer line's offset; the ding times |
| **the caption style** | the campaign's one font/style | `spot-audio-assembly` § captions |
| **a kinetic title** (optional) | wordmark or line as a designed EVENT | its length; where the cut places it |


The reusable end card and the reusable elements (the audio signature, the piece effects, the display) are
dialled in once; a new SKU customises some assets (the fill colour, the SKU on the rotator, the label).

## The worked example — one campaign's kit (a packaged snack, 2026-09; built once, accepted once, reused in every spot)

| element | what it is | the number the edit uses |
|---|---|---|
| **the end card** | the brand world from the client's own art: wordmark, character cut-out, the burst; 2.5 s FULL | `role: endcard`; the burst fires at `T0` on the audio signature's hit; the signature file starts at card + 0.02 s |
| **the closer bed + the signature** | the closing bed under the turntable and the card; the audio signature (its hit at +T0 in the file) | `spot-audio-assembly` |
| **the piece wall** | a jittered tile of the SKU's silhouettes that covers the frame, holds, then flies past the lens — 1.0 s layer | opaque from +0.29 s; placed at `join − 0.5` so it straddles a cut; the after cue slams in at the REVEAL |
| **the drift** | pieces raining over the turntable — 5.5 s layer at the turntable's length | `at = turntable tl[0]` |
| **the turntable** | the product on a studio display, names dinging in — CSS-3D cylinder from the label texture | `look: ads-clean`; the closer line 0.7 s in; the dings at 1.0/2.0/3.0 s (chimes OPT-IN, default off) |
| **the caption style** | the campaign's one font/style | `spot-audio-assembly` § captions |

## Per-SKU (the customisation set)

- **the label texture** for the cylinder (`assets/tex-<sku>.png`, the full wrap at the label's own aspect);
- **the exact-silhouette sheet** (3×3 cells of the SKU's pieces on a flat background) — the sprites of the
  wall, the drift and any composited burst are cut from THIS sheet, never drawn (`video-refs-continuity`
  § plate pieces);
- **the recolour** of sprites, drift and wall to the SKU's palette — a new project per recolour
  (`wall-a`, `wall-b`);
- **the SKU name** dinging in on the display.

## Building the brand world from the client's art

- **Rasterise the label PDFs at 600 dpi** into a vector directory; every brand asset (the wordmark, the
  character block, the scatter-top) is a black-keyed crop of that raster, never a re-drawing and never a
  crop of a delivered frame.
- **Erase the SKU name from the wordmark by component surgery**, so the card stays SKU-neutral and one
  card serves every SKU; the name returns as the ding on the display.
- **The cylinder texture is the full label wrap** (`assets/tex-<sku>.png`, 2048 px wide at the label's own
  aspect). The turntable is a CSS-3D cylinder — N strips at `rotateY(θ) translateZ(r)` with a shading
  overlay and a cap disc — which gives a true product turn with perfect print at every angle; a generated
  product shot invented its small print.
- **Author every legibility-critical comp natively at the mezzanine raster** (2160×3840 for a vertical
  spot), never rendered small and scaled: the sprite floor and the label's small print are measured on the
  native frame.

Generated shots never carry the product's packaging: the rotating SKU, the display, the card are designed.
A generated burst supplies volume and motion; the exact pieces, where the operator has accepted a
composite for that shot, come from the sheet through `sprite_burst.py` on a plate — **never a 2D overlay
on generated motion**.

## Where each element lands

```
turntable / display  → an EDL event (source designed, look cube), the closer over it, a layer of drift on top
end card             → the endcard event, full 2.5 s, the signature at +0.02, no captions over it
wall                 → a post layer straddling a join; its opaque window decides the REVEAL marker
drift                → a post layer over the turntable event
composited burst     → a new hero file (<hero>-burst.mov) that replaces the event's src
```
