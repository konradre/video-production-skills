#!/usr/bin/env bash
# comfy_up.sh — start ComfyUI as a detached headless server, locally or over ssh, from the env.
#   COMFY_DIR   the ComfyUI checkout (required)          COMFY_VENV  its virtualenv (optional)
#   COMFY_ARGS  default: --listen 0.0.0.0 --port 8188 --disable-auto-launch
#   COMFY_LOG   default: /tmp/comfyui.log               COMFY_SSH   user@host — run the same command there
#   COMFY_HOST  the URL comfy_ready.py probes; a server already answering is left alone.
# Then: python3 scripts/comfy_ready.py --wait 120
#   It takes no arguments: -h or --help prints this header and starts nothing.
set -u
if [ "$#" -gt 0 ]; then sed -n '2,8p' "$0"; case "$1" in -h|--help) exit 0 ;; *) exit 2 ;; esac; fi
: "${COMFY_DIR:?set COMFY_DIR to the ComfyUI checkout}"
ARGS="${COMFY_ARGS:---listen 0.0.0.0 --port 8188 --disable-auto-launch}"
LOG="${COMFY_LOG:-/tmp/comfyui.log}"
HOST="${COMFY_HOST:-http://127.0.0.1:8188}"
if curl -fsS -m 4 "${HOST%/}/system_stats" >/dev/null 2>&1; then
  echo "already up at $HOST — nothing started"; exit 0
fi
ACT=""; [ -n "${COMFY_VENV:-}" ] && ACT=". '${COMFY_VENV}/bin/activate' && "
# Python's start_new_session gives the server a session of its own (setsid exists only on Linux), so it outlives this shell
CMD="cd '${COMFY_DIR}' && ${ACT}python3 -c 'import subprocess as s, sys; s.Popen([sys.executable, \"main.py\"] + sys.argv[2:], stdin=s.DEVNULL, stdout=open(sys.argv[1], \"wb\"), stderr=s.STDOUT, start_new_session=True)' '${LOG}' ${ARGS} && echo started"
if [ -n "${COMFY_SSH:-}" ]; then
  ssh -o BatchMode=yes -o ConnectTimeout=10 "${COMFY_SSH}" "${CMD}" || { echo "ssh to ${COMFY_SSH} failed" >&2; exit 1; }
  echo "ComfyUI launched on ${COMFY_SSH} (log ${LOG} there); probe: python3 scripts/comfy_ready.py --wait 120"
else
  bash -c "${CMD}" || exit 1
  echo "ComfyUI launched (log ${LOG}); probe: python3 scripts/comfy_ready.py --wait 120"
fi
