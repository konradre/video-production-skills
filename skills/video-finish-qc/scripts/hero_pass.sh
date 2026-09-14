#!/usr/bin/env bash
# hero_pass.sh — the Resolve + Dehancer hero pass on already-upscaled mezzanines, ONE clip per call, through the resolve-pass
# tool over the in-app bridge. Resolve must be open with a PROJECT loaded and Workspace › Scripts › resolve_bridge started
# by the operator (an agent-launched Resolve refuses external scripting; "external scripting refused" = the bridge is down —
# stop and ask the operator to reopen it, then retry). Never parallelise render jobs. Output: <out-dir>/<stem>__<look>.mov
# (DNxHR HQX 10-bit 4:2:2 by default). Sentinel HERO-PASS-END.
#
#   hero_pass.sh --root <project> --look ads-clean [--in-dir edit/upscale-out] [--out-dir edit/hero] [--codec DNxHR_HQX] [--format mov]
#                [--python <windows venv python>] [--tool-dir <resolve-pass dir>] <file-in-in-dir> …
# --python defaults to $RESOLVE_PY (the Windows venv interpreter that can reach Resolve's scripting API); --tool-dir to
# $RESOLVE_PASS_DIR or the repository's tools/resolve-pass (resolved from this script's real path). The tool translates /mnt/<d>/ paths itself.
set -u
ROOT="."; LOOK=""; IN="edit/upscale-out"; OUT="edit/hero"; CODEC="DNxHR_HQX"; FMT="mov"; PY="${RESOLVE_PY:-}"; TD="${RESOLVE_PASS_DIR:-$(cd "$(dirname "$(readlink -f "$0")")/../../../tools/resolve-pass" 2>/dev/null && pwd)}"; FILES=()
while [ $# -gt 0 ]; do case "$1" in
  --root) ROOT="$2"; shift 2;; --look) LOOK="$2"; shift 2;; --in-dir) IN="$2"; shift 2;; --out-dir) OUT="$2"; shift 2;; --codec) CODEC="$2"; shift 2;; --format) FMT="$2"; shift 2;;
  --python) PY="$2"; shift 2;; --tool-dir) TD="$2"; shift 2;; -h|--help) sed -n '2,12p' "$0"; exit 0;; *) FILES+=("$1"); shift;; esac; done
[ -n "$LOOK" ] || { echo "--look is required"; exit 2; }; [ ${#FILES[@]} -gt 0 ] || { echo "no files given"; exit 2; }
[ -n "$PY" ] && [ -x "$PY" ] || { echo "no Resolve-capable python: pass --python or set RESOLVE_PY"; exit 2; }; [ -f "$TD/resolve_pass.py" ] || { echo "resolve_pass.py not in $TD"; exit 2; }
ROOT=$(cd "$ROOT" && pwd); mkdir -p "$ROOT/$OUT"; cd "$TD" || exit 1
for F in "${FILES[@]}"; do
  echo "[$(date +%H:%M:%S)] HERO $F ($LOOK)"
  "$PY" resolve_pass.py --look "$LOOK" --in "$ROOT/$IN/$F" --out-dir "$ROOT/$OUT" --format "$FMT" --codec "$CODEC" --transport bridge --wait 60 --timeout 300 2>&1 | tail -3
done
echo "[$(date +%H:%M:%S)] HERO-PASS-END"
