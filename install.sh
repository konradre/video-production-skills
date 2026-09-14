#!/usr/bin/env bash
# install.sh [<another agent's skills folder> ...] — link every skill into ~/.claude/skills, the path each command
# inside the skills calls, and into any folder named. Re-runnable; an existing file that is not a link is left alone.
set -eu
case "${1:-}" in -h|--help) sed -n '2,3p' "$0"; exit 0 ;; esac
REPO="$(cd "$(dirname "$0")" && pwd)"
for DEST in "$HOME/.claude/skills" "$@"; do
  mkdir -p "$DEST"
  for d in "$REPO"/skills/*/; do
    n="$(basename "$d")"
    if [ -e "$DEST/$n" ] && [ ! -L "$DEST/$n" ]; then echo "skip $DEST/$n: exists and is not a symlink"; continue; fi
    ln -sfn "$d" "$DEST/$n"; echo "linked $DEST/$n"
  done
done
cat <<'MSG'

Linked. The skills find the tools and the look library through these links, so the default layout needs no
environment variable; the optional overrides are listed in .env.example and tools/README.md.
Keys: copy .env.example to .env, fill in the vendors you use, and load it in the command that needs it:
  set -a; . ~/.claude/skills/video-production/../../.env; set +a
Start a production with the entry skill: /video-production
MSG
