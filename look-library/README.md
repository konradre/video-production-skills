# look-library — genre look pairs for the finish

Start with [`GUIDE.md`](GUIDE.md): the two tiers, the settings, Resolve + Dehancer setup, authoring and
exporting a look, baking the cubes, the hero-pass loop, the finishing recipes and the sources.

Each look is a **pair — two renderers of the same look, never stacked**:

| tier | file | renders on | carries |
|---|---|---|---|
| Colour | `cubes/<id>_33.cube` | anywhere — ffmpeg `lut3d` | WB, tone, split-tone, saturation, the film-stock transform |
| Spatial | `drx/<id>.drx` | the Resolve hero pass only (Resolve + Dehancer) | the full look incl. halation, bloom, grain |

Both ship. The cubes apply anywhere ffmpeg runs; the `.drx` grades need DaVinci Resolve with a licensed
Dehancer Pro **7.x** and its film profiles downloaded (they were authored on 7.4; a major version installs
as a separate plugin, so on 8.x re-author them from [`RECIPES.md`](RECIPES.md)). `index.json` carries the
sha256 of every file so a stale copy is caught. One entry, `ugc-phone`, ships a cube and no `.drx`; the
section below the table says why.

| id | genre | base | one-liner |
|---|---|---|---|
| `ads-clean` | ads | — | neutral crisp commercial, true blacks, grain/halation OFF |
| `ads-warm` | ads | — | golden lifestyle warmth held to ads discipline |
| `film-teal-orange` | film | Vision3 250D → 2383 | blockbuster split-tone, the restrained end of the range |
| `film-portra` | film | Portra 400 → Endura | creamy skin, people-first |
| `film-cinestill` | film | Vision3 500T → 2383 | tungsten night; the red halation lives in the `.drx` |
| `ugc-phone` | ads, creator-style | — | the colour tier of the phone-native finish; close to identity, no `.drx` by design |

## The phone-native tier (`ugc-phone`)

`ugc-phone` is the one entry without a `.drx`, and the gap is deliberate. It is not a look but the colour tier of
the phone-native finish (`skills/video-finish` § 5): a cube close to identity, with no film stock, no split-tone,
a gentle consumer tone map, a small black lift and skin left alone. Mid-grey 128 comes out at 131. A phone's
colour is nearly neutral, so there is little for a cube to do, and a Dehancer pass would work against the tier,
because halation, bloom and film grain read as film and a phone has none of them.

What makes the clip read as phone-shot happens after the cube. `skills/video-finish/scripts/phone_native.py`
runs at delivery resolution and adds the exposure drift, the stepped white balance, the exposure jump at each
cut, the handheld shake, a fine noise or a light denoise, and the phone-class H.264 encode at 2.5 to 12 Mbps.
`skills/video-finish-qc/scripts/phone_texture_probe.py` sets the dose by measuring the project's own real phone
clips and moving the candidate into their range. On the first calibration a raw 720p generated take carried
more fine texture than the real clips, so the dose that landed it in the band was a denoise and a 2.5 Mbps
encode, not added noise. The direction can reverse on another generator or another set of clips, so probe first.

Apply it like any other cube, through ffmpeg `lut3d` at mezzanine resolution, then hand the downscaled clip to
`phone_native.py`. The hero pass never runs on this tier. `GUIDE.md` § 3a carries the row beside the five looks,
and the root README's section on the phone-native finish has the calibration numbers.

## Editing a look

**Never hand-edit a `.cube`** — edit `looks/<id>.yaml` and rebake; the LUT and its parameter source never
drift. The film looks sample a spectral base cube first, fetched once:

```bash
./fetch_spectral_bases.sh          # the MIT base cubes → spectral_luts/ (only needed to rebake)
python3 build_cubes.py             # looks/*.yaml (+ base) → cubes/<id>_33.cube + index.json
python3 validate_cube.py cubes/*.cube
python3 preview.py --clip <an upscaled take>   # → preview/index.html, a human picks the look
```

Dependencies: Python 3, numpy, PyYAML, ffmpeg. Third-party notices: `../NOTICE.md`.
