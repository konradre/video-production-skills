#!/usr/bin/env bash
# render_hyper.sh — render one HyperFrames composition project to an mp4 (a designed EVENT: turntable, card) or a PNG sequence
# with alpha (a LAYER for the finisher's post_layers), locally or on the render host. WSL2's headless Chromium hangs — render on
# the GPU VM through a login shell with Node ≥ 22 (--host). Sentinel RENDER-END; a log without it is a failure.
#
#   render_hyper.sh --dir <projects root> --name <comp> --format mp4|png-sequence [--fps 24] [--crf 12] [--workers 2]
#                   [--host <ssh host>] [--remote-dir ~/hyper] [--push] [--pull] [--hf-version 0.8.18] [--timeout 1800]
# --push rsyncs <dir>/<name> to <host>:<remote-dir>/<name> first (renders/ and frames/ excluded); --pull brings renders/ and
# frames/ back. Output: <name>/renders/<name>.mp4 or <name>/frames/frame_%06d.png. A new length is a NEW project name.
set -u
DIR="."; NAME=""; FMT=""; FPS=24; CRF=12; WORKERS=2; HOST=""; RDIR="~/hyper"; PUSH=0; PULL=0; HFV="0.8.18"; TMO=1800
while [ $# -gt 0 ]; do case "$1" in
  --dir) DIR="$2"; shift 2;; --name) NAME="$2"; shift 2;; --format) FMT="$2"; shift 2;; --fps) FPS="$2"; shift 2;; --crf) CRF="$2"; shift 2;; --workers) WORKERS="$2"; shift 2;;
  --host) HOST="$2"; shift 2;; --remote-dir) RDIR="$2"; shift 2;; --push) PUSH=1; shift;; --pull) PULL=1; shift;; --hf-version) HFV="$2"; shift 2;; --timeout) TMO="$2"; shift 2;;
  -h|--help) sed -n '2,10p' "$0"; exit 0;; *) echo "unknown arg $1"; exit 2;; esac; done
[ -n "$NAME" ] && [ -n "$FMT" ] || { echo "--name and --format are required"; exit 2; }; [ -f "$DIR/$NAME/index.html" ] || { echo "no composition at $DIR/$NAME/index.html"; exit 2; }
if [ "$FMT" = mp4 ]; then OUT="renders/$NAME.mp4"; ARGS="--format mp4 --fps $FPS --output $OUT --crf $CRF"; else OUT="frames"; ARGS="--format png-sequence --fps $FPS --output frames"; fi
[ -n "$HOST" ] || RDIR="$DIR"   # a local render works in place; CMD below is built from RDIR
CMD="export PATH=\$HOME/.local/bin:\$PATH; cd $RDIR/$NAME || exit 1; mkdir -p renders frames; [ $FMT = png-sequence ] && rm -f frames/*.png; echo \"===== RENDER $NAME \$(date +%H:%M:%S) =====\"; T=\$(command -v timeout || command -v gtimeout); [ -n \"\$T\" ] || echo \"no timeout or gtimeout on this host: the render runs without its $TMO s limit\"; \${T:+\$T $TMO} npx -y hyperframes@$HFV render $ARGS --workers $WORKERS > render.log 2>&1; rc=\$?; echo \"exit=\$rc \$(date +%H:%M:%S)\"; grep -vE 'npm warn|^\s*\$' render.log | grep -E 'Failed|✓|✗|Rendered|rendered in|error' | cut -c1-160 | tail -3; ls -la renders 2>/dev/null | tail -3; ls frames 2>/dev/null | wc -l; exit \$rc"
# the render's output must EXIST — the sentinel prints only then (a mis-quoted remote command once ran nothing and still ended in RENDER-END)
if [ "$FMT" = mp4 ]; then CHECK="test -s $RDIR/$NAME/$OUT"; else CHECK="ls $RDIR/$NAME/frames/*.png > /dev/null 2>&1"; fi
if [ -n "$HOST" ]; then
  [ "$PUSH" = 1 ] && rsync -a --delete --exclude renders --exclude frames --exclude node_modules "$DIR/$NAME/" "$HOST:$RDIR/$NAME/"
  ssh "$HOST" "bash -lc $(printf '%q' "$CMD")"; RC=$?   # %q, never '$CMD': the command carries its own single quotes
  ssh "$HOST" "bash -lc $(printf '%q' "$CHECK")" || RC=1
  [ "$PULL" = 1 ] && rsync -a "$HOST:$RDIR/$NAME/renders/" "$DIR/$NAME/renders/" 2>/dev/null; [ "$PULL" = 1 ] && [ "$FMT" = png-sequence ] && rsync -a "$HOST:$RDIR/$NAME/frames/" "$DIR/$NAME/frames/"
else
  NV=$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1); [ -n "$NV" ] && [ "$NV" -ge 22 ] || { echo "local render needs Node >= 22 (found ${NV:-none}); use --host"; exit 2; }
  bash -c "$CMD"; RC=$?
  if [ "$FMT" = mp4 ]; then test -s "$DIR/$NAME/$OUT" || RC=1; else ls "$DIR/$NAME"/frames/*.png > /dev/null 2>&1 || RC=1; fi
fi
[ "$RC" = 0 ] || { echo "RENDER-FAILED $NAME $FMT (exit $RC) — no sentinel; read render.log"; exit 1; }
echo "RENDER-END $NAME $FMT"
