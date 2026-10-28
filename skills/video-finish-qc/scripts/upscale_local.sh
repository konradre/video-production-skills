#!/usr/bin/env bash
# upscale_local.sh — the local reconstructive upscale (Topaz Rhea ×4 by default) on OPERATOR-APPROVED takes only, one after
# another, through the topaz_upscale tool; writes <out-dir>/<stem>__<model>x<scale>.mp4 and prints RHEA-OK/RHEA-FAILED per
# take and the sentinel UPSCALE-LOCAL-END. A log without the sentinel is a failure whatever the file sizes say.
# RHEA-OK needs the TOOL's verdict (exit 0 + TOPAZ-UPSCALE-OK) and the file; the line names the encoder and pixel format, and
# an 8-bit result (the ladder's h264 rung) is flagged — a file on disk once passed as OK after the tool had failed (2026-10-28).
# The tool's full output goes to <out-dir>/<stem>__<model>x<scale>.log; the script exits 1 when any take failed.
# Every take must trace to the operator's recorded pick (video-production/scripts/pick_gate.py) — else PICK-GATE-REFUSED, exit 3.
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
ROOT=$(cd "$ROOT" && pwd)
GATE="$(cd "$(dirname "$0")" && pwd)/../../video-production/scripts/pick_gate.py"   # the pick, checked in code before any work
python3 "$GATE" check --root "$ROOT" "${TAKES[@]}" || { echo "[$(date +%H:%M:%S)] PICK-GATE-REFUSED — record the operator's pick first (pick_gate.py record / derive)"; exit 3; }
mkdir -p "$ROOT/$OUT"; FAILS=0
for T in "${TAKES[@]}"; do
  stem=$(basename "$T" .mp4); echo "[$(date +%H:%M:%S)] UPSCALE $stem ($MODEL x$SCALE)"
  UP="$ROOT/$OUT/${stem}__${MODEL}x${SCALE}.mp4"; TLOG="${UP%.mp4}.log"
  python3 "$TOOL" --in "$ROOT/$T" --model "$MODEL" --scale "$SCALE" --out-dir "$ROOT/$OUT" > "$TLOG" 2>&1; RC=$?
  tail -3 "$TLOG"
  ENC=$(sed -n 's/.*"encoder": "\([^"]*\)".*/\1/p' "$TLOG" | tail -1)
  if [ $RC -eq 0 ] && [ "$(tail -1 "$TLOG")" = "TOPAZ-UPSCALE-OK" ] && [ -s "$UP" ]; then
    PIX=$(ffprobe -v error -select_streams v:0 -show_entries stream=pix_fmt -of csv=p=0 "$UP" 2>/dev/null)
    case "$PIX" in *10le|*10be|p010*) B="";; *) B=" ⚠ 8-BIT ($PIX) — the 10-bit rung failed; read $TLOG";; esac
    echo "[$(date +%H:%M:%S)] RHEA-OK $stem ← $(basename "$UP") (${ENC:-?}, ${PIX:-?})$B"
  else
    FAILS=$((FAILS + 1)); echo "[$(date +%H:%M:%S)] RHEA-FAILED $stem (tool exit $RC, $(tail -1 "$TLOG")) — read $TLOG"
  fi
done
echo "[$(date +%H:%M:%S)] UPSCALE-LOCAL-END"
[ $FAILS -eq 0 ]
