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
sha256 of every file so a stale copy is caught.

| id | genre | base | one-liner |
|---|---|---|---|
| `ads-clean` | ads | — | neutral crisp commercial, true blacks, grain/halation OFF |
| `ads-warm` | ads | — | golden lifestyle warmth held to ads discipline |
| `film-teal-orange` | film | Vision3 250D → 2383 | blockbuster split-tone, the restrained end of the range |
| `film-portra` | film | Portra 400 → Endura | creamy skin, people-first |
| `film-cinestill` | film | Vision3 500T → 2383 | tungsten night; the red halation lives in the `.drx` |

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
