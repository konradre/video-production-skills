#!/bin/bash
# contact_sheet.sh <take.mp4> [cols] [rows] [font file] [--at s,s,…] [--beats <json>] [--phone] → review/<take>-contact[-at|-beats][-phone].jpg
# A SURVEY image: JPEG, never a verdict read. Named -contact so it never overwrites qc_seed.py's continuity sheet (-sheet.jpg).
# Evenly spaced frames by default; --at the frames ON SCREEN at those seconds; --beats a tile on every beat — a beat_grid.py JSON ("beats": [s, …]) or an explainer timeline.json (each scene's start + its named beats, scene-local seconds).
# Each tile is 270 px wide. --phone = the phone sheet (animate's review.mjs): 360 px tiles, and with no --at/--beats one frame a second over the whole film — read every caption at this size; the label is drawn AFTER the scale, so it reads at tile size.
# The label font: the 4th argument, else DejaVu Sans Mono (Linux), Menlo (macOS), or fontconfig's monospace. --selftest builds a clip and checks every mode.
set -u
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"   # the selftest runs it again from a scratch dir
pos=(); at=""; beats=""; phone=0; selftest=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    --at) at="${2:-}"; shift 2 ;;
    --beats) beats="${2:-}"; shift 2 ;;
    --phone) phone=1; shift ;;
    --selftest) selftest=1; shift ;;
    *) pos+=("$1"); shift ;;
  esac
done
if [ "$selftest" = 1 ]; then
  d="$(mktemp -d)"; trap 'rm -rf "$d"' EXIT; cd "$d" || exit 1
  ffmpeg -v error -y -f lavfi -i "color=c=black:s=1080x1920:r=24:d=4,geq=lum='20+50*T':cb=128:cr=128" -pix_fmt yuv420p t.mp4 || exit 1   # luma = 20 + 50 t: a tile's level names its time
  printf '{"beats": [0.5, 1.0, 1.5, 2.25]}' > grid.json
  printf '{"scenes": [{"id": "s01", "start": 0.0, "beats": {"start": 0.0, "hero": 0.4, "end": 2.0}}, {"id": "s02", "start": 2.0, "beats": {"start": 0.0, "b1": 1.25, "end": 2.0}}]}' > timeline.json
  ok=1
  chk() { local f="$1" want="$2"; local got; got=$(ffprobe -v error -show_entries stream=width,height -of csv=p=0 "$f" 2>/dev/null)
    if [ "$got" = "$want" ]; then echo "ok   $f $got"; else echo "FAIL $f $got (want $want)"; ok=0; fi; }
  bash "$SELF" t.mp4 4 2 >/dev/null && chk review/t-contact.jpg 1080,960
  bash "$SELF" t.mp4 3 1 --at 0.5,1.25,3.9 >/dev/null && chk review/t-contact-at.jpg 810,480
  bash "$SELF" t.mp4 4 1 --beats grid.json >/dev/null && chk review/t-contact-beats.jpg 1080,480
  bash "$SELF" t.mp4 2 1 --beats timeline.json --phone >/dev/null && chk review/t-contact-beats-phone.jpg 720,1280   # 4 beats (each scene's start + its named beat), 2 a row, 360 x 640 tiles
  bash "$SELF" t.mp4 4 1 --phone >/dev/null && chk review/t-contact-phone.jpg 1440,640                             # 4 s at one frame a second, 4 a row
  # timeline.json beats are SCENE-LOCAL: s02's b1 is 2.0 + 1.25 = 3.25 s — its tile must be the frame at 3.25, not at 1.25
  bash "$SELF" t.mp4 1 1 --beats timeline.json >/dev/null; mv review/t-contact-beats.jpg tl.jpg
  bash "$SELF" t.mp4 1 1 --at 3.25 >/dev/null; mv review/t-contact-at.jpg a325.jpg
  bash "$SELF" t.mp4 1 1 --at 1.25 >/dev/null; mv review/t-contact-at.jpg a125.jpg
  python3 - <<'EOF' || ok=0
import subprocess, numpy as np
def gray(p):
    w, h = (int(x) for x in subprocess.run(['ffprobe','-v','error','-show_entries','stream=width,height','-of','csv=p=0',p],capture_output=True,text=True).stdout.split(','))
    return np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',p,'-f','rawvideo','-pix_fmt','gray','-'],capture_output=True).stdout,np.uint8).reshape(h,w).astype(float)
tl, a, b = gray('tl.jpg'), gray('a325.jpg'), gray('a125.jpg'); th = a.shape[0]
tile = tl[3 * th + 60:4 * th, :].mean(); want, wrong = a[60:, :].mean(), b[60:, :].mean()
ok = abs(tile - want) < 3 and abs(tile - wrong) > 30
print(('ok  ' if ok else 'FAIL') + f" a scene-local beat lands on scene start + its time: tile luma {tile:.0f}, the frame at 3.25 s {want:.0f}, at 1.25 s {wrong:.0f}")
raise SystemExit(0 if ok else 1)
EOF
  [ "$ok" = 1 ] && echo "SELFTEST PASS" || { echo "SELFTEST FAIL"; exit 1; }
  exit 0
fi
f="${pos[0]:-}"; [ -z "$f" ] && { sed -n '2,6p' "$0" >&2; exit 2; }
font="${pos[3]:-}"
for c in /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf /System/Library/Fonts/Menlo.ttc "/System/Library/Fonts/Supplemental/Andale Mono.ttf"; do
  if [ -z "$font" ] && [ -f "$c" ]; then font="$c"; fi
done
if [ -z "$font" ] && command -v fc-match >/dev/null 2>&1; then font="$(fc-match -f '%{file}' monospace || true)"; fi
[ -f "$font" ] || { echo "no usable font (${font:-none found}): pass a .ttf or .ttc file as the 4th argument" >&2; exit 2; }
set -e; cols="${pos[1]:-4}"; rows="${pos[2]:-4}"; mkdir -p review
tw=270; [ "$phone" = 1 ] && tw=360; fsz=$(( tw / 14 ))
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f"); fps=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$f")
sfx=""; [ "$phone" = 1 ] && sfx="-phone"
lab="drawtext=fontfile='$font':fontsize=$fsz:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=4:x=6:y=6"
if [ -z "$at" ] && [ -z "$beats" ]; then
  frames=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$f")
  n=$((cols*rows)); step=$(( frames / n )); [ "$step" -lt 1 ] && step=1
  if [ "$phone" = 1 ]; then step=$(awk -F/ '{r = ($2 ? $1 / $2 : $1); printf "%d", (r < 1 ? 1 : r + 0.5)}' <<< "$fps"); rows=$(( (frames / step + cols - 1) / cols )); fi   # one frame a second, every second
  out="review/$(basename "${f%.*}")-contact$sfx.jpg"
  ffmpeg -v error -y -i "$f" -vf "select='not(mod(n\,$step))',scale=$tw:-2,$lab:text='%{pts\:hms}',tile=${cols}x${rows}" -frames:v 1 -q:v 3 "$out"
  echo "$out ($dur s, $frames frames, $fps, every $step, tiles $tw px)"; exit 0
fi
# --at / --beats: one tile per named time, labelled with its name and seconds
list="$(mktemp)"; tmp="$(mktemp -d)"; trap 'rm -rf "$tmp" "$list"' EXIT
if [ -n "$at" ]; then mode=at; tr ',' '\n' <<< "$at" | awk 'NF {printf "%s\t%.3f s\n", $1, $1}' > "$list"
else mode=beats; python3 - "$beats" > "$list" <<'EOF'
import json, sys
j = json.load(open(sys.argv[1]))
if 'scenes' in j:      # an explainer timeline.json: beats are SCENE-LOCAL seconds, so each is scene start + its own time
    for s in j['scenes']:
        for k, v in (s.get('beats') or {}).items():
            if k != 'end': t = float(s['start']) + float(v); print(f"{t:.3f}\t{s['id']}.{k} {t:.2f} s")
else:                  # a beat_grid.py JSON: the grid or the beat map, film seconds
    for i, t in enumerate(j.get('beats') or []): print(f"{float(t):.3f}\tbeat {i} {float(t):.2f} s")
EOF
fi
n=$(wc -l < "$list"); [ "$n" -gt 0 ] || { echo "no times to sample" >&2; exit 2; }
rows=$(( (n + cols - 1) / cols )); k=0; fr=$(awk -F/ '{printf "%.6f", ($2 ? $1 / $2 : $1)}' <<< "$fps")
while IFS=$'\t' read -r t label; do
  ss=$(awk -v t="$t" -v r="$fr" 'BEGIN {s = int(t * r + 1e-6) / r - 0.25 / r; printf "%.4f", (s < 0 ? 0 : s)}')   # the frame ON SCREEN at t
  printf '%s' "$label" > "$tmp/l$k.txt"
  ffmpeg -nostdin -v error -y -ss "$ss" -i "$f" -frames:v 1 -vf "scale=$tw:-2,$lab:textfile='$tmp/l$k.txt'" "$tmp/$(printf %04d $k).png"   # -nostdin: ffmpeg would eat the loop's list
  [ -f "$tmp/$(printf %04d $k).png" ] || { echo "no frame at $t s ($label)" >&2; exit 1; }
  k=$((k + 1))
done < "$list"
[ "$k" -eq "$n" ] || { echo "made $k of $n tiles" >&2; exit 1; }
out="review/$(basename "${f%.*}")-contact-$mode$sfx.jpg"
ffmpeg -v error -y -framerate 1 -i "$tmp/%04d.png" -vf "tile=${cols}x${rows}" -frames:v 1 -q:v 3 "$out"
echo "$out ($n tiles from --$mode, ${cols}x$rows, tiles $tw px)"
