#!/usr/bin/env bash
# final_renders.sh — the FINAL renders of the approved spots, sequentially: finish (all stages, tag -final) → QC → copy into
# deliver/final/. One EDL per spot at edit/<SPOT>-EDL-final.json (the approved cut with the current card swapped in). Free
# disk is printed before every spot (a mezzanine pair per version fills a drive). Sentinel FINAL-END; a log without it, or
# a FINISH-FAILED / QC FAIL line, is not a delivery.
#
#   final_renders.sh --root <project> [--edl-pattern 'edit/{spot}-EDL-final.json'] [--tag -final] S01B S02 S03 …
set -u
ROOT="."; PAT="edit/{spot}-EDL-final.json"; TAG="-final"; SPOTS=(); SK="$HOME/.claude/skills/video-finish-qc/scripts"
while [ $# -gt 0 ]; do case "$1" in
  --root) ROOT="$2"; shift 2;; --edl-pattern) PAT="$2"; shift 2;; --tag) TAG="$2"; shift 2;; -h|--help) sed -n '2,8p' "$0"; exit 0;; *) SPOTS+=("$1"); shift;; esac; done
[ ${#SPOTS[@]} -gt 0 ] || { echo "no spots given"; exit 2; }
ROOT=$(cd "$ROOT" && pwd); cd "$ROOT" || exit 1; mkdir -p deliver/final logs
for SPOT in "${SPOTS[@]}"; do
  EDL="${PAT//\{spot\}/$SPOT}"; [ -f "$EDL" ] || { echo "FINISH-FAILED $SPOT: no EDL at $EDL"; continue; }
  BASE=$(python3 -c "import json;print(json.load(open('$EDL'))['deliver_base'])")
  echo "[$(date +%T)] FINISH $SPOT ($BASE)"; df -h "$ROOT" | tail -1
  python3 "$SK/finish_spot.py" --root "$ROOT" --edl "$EDL" --stage all --tag="$TAG" > "logs/finish-$SPOT$TAG.log" 2>&1; tail -2 "logs/finish-$SPOT$TAG.log"
  /usr/bin/grep -q '^FINISH-END' "logs/finish-$SPOT$TAG.log" && [ -f "deliver/$BASE$TAG.mp4" ] || { echo "FINISH-FAILED $SPOT (no sentinel or no file)"; continue; }
  echo "[$(date +%T)] QC $SPOT"; python3 "$SK/qc_deliverable.py" --root "$ROOT" --edl "$EDL" --deliv "deliver/$BASE$TAG.mp4" 2>&1 | /usr/bin/grep -E '^(PASS|FAIL|QC-DELIVERABLE)' | cut -c1-160
  cp "deliver/$BASE$TAG.mp4" "deliver/final/$BASE$TAG.mp4" && ls -la "deliver/final/$BASE$TAG.mp4"
done
echo "[$(date +%T)] FINAL-END"
