#!/usr/bin/env bash
# upscale_local.sh — the local reconstructive upscale (Topaz Rhea ×4 by default) on OPERATOR-APPROVED takes only, one after
# another, through the topaz_upscale tool; writes <out-dir>/<stem>__<model>x<scale>.mp4 and prints RHEA-OK/RHEA-FAILED per
# take and the sentinel UPSCALE-LOCAL-END. A log without the sentinel is a failure whatever the file sizes say.
# Run it DETACHED (video-production/scripts/detach.py) with every path absolute — a Bash-backgrounded run has a 10-minute cap and a
# truncated mezzanine silently shortens the deliverable. Poll the log on demand; never follow it.
#
#   upscale_local.sh --root <project> [--model rhea-1] [--scale 4] [--out-dir edit/upscale-out] [--tool <topaz_upscale.py>] takes/A.mp4 takes/B.mp4 …
# --tool defaults to $TOPAZ_UPSCALE_PY or the repository's tools/topaz-upscale/topaz_upscale.py (resolved from this script's real path)
set -u
ROOT="."; MODEL="rhea-1"; SCALE="4"; OUT="edit/upscale-out"; TOOL="${TOPAZ_UPSCALE_PY:-$(dirname "$(readlink -f "$0")")/../../../tools/topaz-upscale/topaz_upscale.py}"; TAKES=()
while [ $# -gt 0 ]; do case "$1" in
  --root) ROOT="$2"; shift 2;; --model) MODEL="$2"; shift 2;; --scale) SCALE="$2"; shift 2;; --out-dir) OUT="$2"; shift 2;; --tool) TOOL="$2"; shift 2;;
  -h|--help) sed -n '2,10p' "$0"; exit 0;; *) TAKES+=("$1"); shift;; esac; done
[ ${#TAKES[@]} -gt 0 ] || { echo "no takes given"; exit 2; }; [ -f "$TOOL" ] || { echo "upscale tool not found: $TOOL (set --tool or TOPAZ_UPSCALE_PY)"; exit 2; }
ROOT=$(cd "$ROOT" && pwd); mkdir -p "$ROOT/$OUT"
for T in "${TAKES[@]}"; do
  stem=$(basename "$T" .mp4); echo "[$(date +%H:%M:%S)] UPSCALE $stem ($MODEL x$SCALE)"
  python3 "$TOOL" --in "$ROOT/$T" --model "$MODEL" --scale "$SCALE" --out-dir "$ROOT/$OUT" 2>&1 | tail -3
  UP=$(ls -t "$ROOT/$OUT/${stem}__${MODEL}x${SCALE}".* 2>/dev/null | head -1)
  [ -z "$UP" ] && echo "[$(date +%H:%M:%S)] RHEA-FAILED $stem" || echo "[$(date +%H:%M:%S)] RHEA-OK $stem ← $(basename "$UP")"
done
echo "[$(date +%H:%M:%S)] UPSCALE-LOCAL-END"
