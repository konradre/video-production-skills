#!/usr/bin/env bash
# render_hyper.sh — render one HyperFrames composition project to an mp4 (a designed EVENT: turntable, card) or a PNG sequence
# with alpha (a LAYER for the finisher's post_layers), locally or on the render host. WSL2's headless Chromium hangs — render on
# the GPU VM through a login shell with Node ≥ 22 (--host). Sentinel RENDER-END; a log without it is a failure.
#
#   render_hyper.sh --dir <projects root> --name <comp> --format mp4|png-sequence [--fps 24] [--crf 12] [--workers 2]
#                   [--host <ssh host>] [--remote-dir ~/hyper] [--push] [--pull] [--hf-version 0.8.18] [--timeout 1800]
#                   [--keep-out "<zone>"]… [--check-only] [--no-check] [--check-timeout 600]
# --push rsyncs <dir>/<name> to <host>:<remote-dir>/<name> first (renders/ and frames/ excluded); --pull brings renders/ and
# frames/ back. Output: <name>/renders/<name>.mp4 or <name>/frames/frame_%06d.png. A new length is a NEW project name.
# Before the render: `hyperframes check` REPORT-ONLY, one run per zone of the project's safe band — read from the nearest
# delivery-targets.json at or above the composition by video-production/scripts/safe_zones.py (the strict ad union when
# none is declared: SAFE-AREAS.md); --keep-out adds a zone. The first run carries the full report (renders/check.json) and
# runs alone; the further zones then run at once, each into renders/check-zone<N>.json with contrast off. Zones are sampled
# once a second, never at fewer than 11 points; every run stops at --check-timeout. Then check_summary.py's read; the
# check never changes the exit code. A png-sequence layer is checked with --no-contrast. --check-only stops after the
# read; --no-check skips it.
set -u
DIR="."; NAME=""; FMT=""; FPS=24; CRF=12; WORKERS=2; HOST=""; RDIR="~/hyper"; PUSH=0; PULL=0; HFV="0.8.18"; TMO=1800; KO=(); CHKONLY=0; NOCHECK=0; SD=$(cd "$(dirname "$0")" && pwd)
CTMO=600; KD=(); KL=(); SEEK="seek=0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1"
while [ $# -gt 0 ]; do case "$1" in
  --dir) DIR="$2"; shift 2;; --name) NAME="$2"; shift 2;; --format) FMT="$2"; shift 2;; --fps) FPS="$2"; shift 2;; --crf) CRF="$2"; shift 2;; --workers) WORKERS="$2"; shift 2;;
  --host) HOST="$2"; shift 2;; --remote-dir) RDIR="$2"; shift 2;; --push) PUSH=1; shift;; --pull) PULL=1; shift;; --hf-version) HFV="$2"; shift 2;; --timeout) TMO="$2"; shift 2;;
  --keep-out) KO+=("$2"); shift 2;; --check-only) CHKONLY=1; shift;; --no-check) NOCHECK=1; shift;; --check-timeout) CTMO="$2"; shift 2;;
  -h|--help) sed -n '2,17p' "$0"; exit 0;; *) echo "unknown arg $1"; exit 2;; esac; done
[ -n "$NAME" ] && [ -n "$FMT" ] || { echo "--name and --format are required"; exit 2; }; [ -f "$DIR/$NAME/index.html" ] || { echo "no composition at $DIR/$NAME/index.html"; exit 2; }
if [ "$FMT" = mp4 ]; then OUT="renders/$NAME.mp4"; ARGS="--format mp4 --fps $FPS --output $OUT --crf $CRF"; else OUT="frames"; ARGS="--format png-sequence --fps $FPS --output frames"; fi
[ -n "$HOST" ] || RDIR="$DIR"   # a local render works in place; CMD below is built from RDIR
CMD="export PATH=\$HOME/.local/bin:\$PATH; cd $RDIR/$NAME || exit 1; mkdir -p renders frames; [ $FMT = png-sequence ] && rm -f frames/*.png; echo \"===== RENDER $NAME \$(date +%H:%M:%S) =====\"; T=\$(command -v timeout || command -v gtimeout); [ -n \"\$T\" ] || echo \"no timeout or gtimeout on this host: the render runs without its $TMO s limit\"; \${T:+\$T $TMO} npx -y hyperframes@$HFV render $ARGS --workers $WORKERS > render.log 2>&1; rc=\$?; echo \"exit=\$rc \$(date +%H:%M:%S)\"; grep -vE 'npm warn|^\s*\$' render.log | grep -E 'Failed|✓|✗|Rendered|rendered in|error' | cut -c1-160 | tail -3; ls -la renders 2>/dev/null | tail -3; ls frames 2>/dev/null | wc -l; exit \$rc"
# the render's output must EXIST — the sentinel prints only then (a mis-quoted remote command once ran nothing and still ended in RENDER-END)
if [ "$FMT" = mp4 ]; then CHECK="test -s $RDIR/$NAME/$OUT"; else CHECK="ls $RDIR/$NAME/frames/*.png > /dev/null 2>&1"; fi
VP="$SD/../../video-production/scripts/safe_zones.py"   # the project's declared band, read here from the local composition
if [ "$NOCHECK" = 0 ]; then
  if [ -f "$VP" ]; then
    ZS=$(python3 "$VP" --from "$DIR/$NAME") || echo "SAFE BAND unreadable (above): no zone read until delivery-targets.json is fixed"
    while IFS=$'\t' read -r z l; do [ -n "$z" ] && { KD+=("$z"); KL+=("$l"); }; done <<< "$ZS"
    SEEK=$(python3 "$VP" --from "$DIR/$NAME" --seek) || SEEK="seek=0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1"
  else echo "no video-production/scripts/safe_zones.py beside this skill: only --keep-out zones are read"; fi
  for z in ${KO[@]+"${KO[@]}"}; do d=0; for y in ${KD[@]+"${KD[@]}"}; do [ "$y" = "$z" ] && d=1; done; [ "$d" = 1 ] || { KD+=("$z"); KL+=("--keep-out"); }; done
fi
hf_check() {   # REPORT-ONLY: the full check (+ zone 1) alone, then the other zones at once → renders/check*.json → check_summary.py
  [ "$NOCHECK" = 1 ] && return 0
  local ca="--json --timeout 15000" f="renders/check.json" i=1 z o c cz=""; [ "$FMT" = png-sequence ] && ca="$ca --no-contrast"
  [ -n "${KD[0]+x}" ] && cz="--caption-zone '${KD[0]};severity=warning;$SEEK'"   # --timeout: the render-ready wait, raised for parallel runs
  c="export PATH=\$HOME/.local/bin:\$PATH; cd $RDIR/$NAME || exit 0; mkdir -p renders; exec 3>&1; : > renders/check.err; T=\$(command -v timeout || command -v gtimeout); [ -n \"\$T\" ] || echo \"no timeout or gtimeout on this host: the checks run without their $CTMO s limit\"; ck() { o=\$1; shift; \${T:+\$T $CTMO} npx -y hyperframes@$HFV check \"\$@\" . > renders/\$o 2>> renders/check.err; [ \$? = 124 ] && echo \"CHECK TIMED OUT after $CTMO s: renders/\$o\" >&3; return 0; }; ck check.json $ca $cz;"   # alone first: it warms the npx cache and the browser before the zone runs fan out
  for z in ${KD[@]+"${KD[@]:1}"}; do i=$((i + 1)); f="$f renders/check-zone$i.json"
    c="$c ck check-zone$i.json --json --timeout 15000 --no-contrast --caption-zone '$z;severity=warning;$SEEK' &"; done
  c="$c wait"
  echo "===== CHECK $NAME (report-only) ====="
  i=0; for z in ${KD[@]+"${KD[@]}"}; do i=$((i + 1)); [ "$i" = 1 ] && o=check.json || o="check-zone$i.json"; echo "zone $i → renders/$o: $z (${KL[$((i - 1))]})"; done
  if [ -n "$HOST" ]; then ssh "$HOST" "bash -lc $(printf '%q' "$c")"; ssh "$HOST" "cd $RDIR/$NAME && python3 - $f" < "$SD/check_summary.py"
  else bash -c "$c"; (cd "$RDIR/$NAME" && python3 "$SD/check_summary.py" $f); fi
  return 0
}
if [ -n "$HOST" ]; then
  [ "$PUSH" = 1 ] && ssh "$HOST" "mkdir -p $RDIR"   # rsync creates the last directory only: a fresh --remote-dir failed the push
  [ "$PUSH" = 1 ] && rsync -a --delete --exclude renders --exclude frames --exclude node_modules "$DIR/$NAME/" "$HOST:$RDIR/$NAME/"
  hf_check; [ "$CHKONLY" = 1 ] && { echo "CHECK-ONLY $NAME"; exit 0; }
  ssh "$HOST" "bash -lc $(printf '%q' "$CMD")"; RC=$?   # %q, never '$CMD': the command carries its own single quotes
  ssh "$HOST" "bash -lc $(printf '%q' "$CHECK")" || RC=1
  [ "$PULL" = 1 ] && rsync -a "$HOST:$RDIR/$NAME/renders/" "$DIR/$NAME/renders/" 2>/dev/null; [ "$PULL" = 1 ] && [ "$FMT" = png-sequence ] && rsync -a "$HOST:$RDIR/$NAME/frames/" "$DIR/$NAME/frames/"
else
  NV=$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1); [ -n "$NV" ] && [ "$NV" -ge 22 ] || { echo "local render needs Node >= 22 (found ${NV:-none}); use --host"; exit 2; }
  hf_check; [ "$CHKONLY" = 1 ] && { echo "CHECK-ONLY $NAME"; exit 0; }
  bash -c "$CMD"; RC=$?
  if [ "$FMT" = mp4 ]; then test -s "$DIR/$NAME/$OUT" || RC=1; else ls "$DIR/$NAME"/frames/*.png > /dev/null 2>&1 || RC=1; fi
fi
[ "$RC" = 0 ] || { echo "RENDER-FAILED $NAME $FMT (exit $RC) — no sentinel; read render.log"; exit 1; }
echo "RENDER-END $NAME $FMT"
