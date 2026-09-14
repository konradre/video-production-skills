#!/usr/bin/env bash
# fetch_spectral_bases.sh — fetch the three spectral negative×print base cubes the film looks sample first,
# from jeremieLouvaert/ComfyUI-Darkroom (MIT), into spectral_luts/. Run once, then `python3 build_cubes.py`.
set -eu
case "${1:-}" in -h|--help) sed -n '2,3p' "$0"; exit 0 ;; esac
HERE="$(cd "$(dirname "$0")" && pwd)"; DEST="$HERE/spectral_luts"; mkdir -p "$DEST"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git clone --depth 1 --filter=blob:none --sparse https://github.com/jeremieLouvaert/ComfyUI-Darkroom "$TMP/darkroom" >/dev/null 2>&1
git -C "$TMP/darkroom" sparse-checkout set data/spectral_luts >/dev/null 2>&1
for f in vision3_250d_2383 vision3_500t_2383 portra_400_endura_premier; do
  cp "$TMP/darkroom/data/spectral_luts/$f.cube" "$DEST/$f.cube"; echo "fetched $f.cube"
done
python3 "$HERE/validate_cube.py" "$DEST"/*.cube
