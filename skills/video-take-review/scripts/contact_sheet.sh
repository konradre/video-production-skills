#!/bin/bash
# contact_sheet.sh <take.mp4> [cols] [rows] [font file] → review/<take>-contact.jpg (evenly spaced frames, timecode burned in)
# A SURVEY image: JPEG, never a verdict read. Named -contact so it never overwrites qc_seed.py's continuity sheet (-sheet.jpg).
# The timecode font: the 4th argument, else DejaVu Sans Mono (Linux), Menlo (macOS), or fontconfig's monospace.
case "${1:-}" in -h|--help) sed -n '2,4p' "$0"; exit 0 ;; "") sed -n '2,4p' "$0" >&2; exit 2 ;; esac
font="${4:-}"
for c in /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf /System/Library/Fonts/Menlo.ttc "/System/Library/Fonts/Supplemental/Andale Mono.ttf"; do
  if [ -z "$font" ] && [ -f "$c" ]; then font="$c"; fi
done
if [ -z "$font" ] && command -v fc-match >/dev/null 2>&1; then font="$(fc-match -f '%{file}' monospace || true)"; fi
[ -f "$font" ] || { echo "no usable font (${font:-none found}): pass a .ttf or .ttc file as the 4th argument" >&2; exit 2; }
set -e; f="$1"; cols="${2:-4}"; rows="${3:-4}"; n=$((cols*rows)); mkdir -p review
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f"); fps=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$f")
frames=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$f")
step=$(( frames / n )); [ "$step" -lt 1 ] && step=1
out="review/$(basename "${f%.*}")-contact.jpg"
ffmpeg -v error -y -i "$f" -vf "select='not(mod(n\,$step))',drawtext=fontfile='$font':text='%{pts\:hms}':x=8:y=8:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5,scale=270:-1,tile=${cols}x${rows}" -frames:v 1 -q:v 3 "$out"
echo "$out ($dur s, $frames frames, $fps, every $step)"
