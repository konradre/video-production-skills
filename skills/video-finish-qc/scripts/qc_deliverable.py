#!/usr/bin/env python3
"""qc_deliverable.py — the delivery QC in ONE pass on the DELIVERED file, per metric with its label (never a total score):
  duration     vs the EDL runtime (< 50 ms)
  loudness     integrated LUFS · LRA · true peak — and the loudness must be FINITE: an audio-STREAM check is not a SOUND check
               (a conforming AAC track at -inf passes a stream probe and ships silent); the true peak must sit under the platform
               ceiling (--tp-ceiling, -1 dBTP) — the EDL's TP is the encode-side target that AAC overshoots by up to ~1 dB
  cuts         the delivered scene-cut list vs the EDL joins: extras are a take's own cut, motion, or a LEAK — named
  leaks        every hero event's [in,out] against ITS TAKE's own scene cuts (a window crossing one = rogue frames) — except
               the cuts the event DECLARES in accepted_cuts (composed inside one generation and kept), printed as INFO
  card         the last frame of the deliverable vs the last frame of the card render (NCC ≥ 0.9): the right card shipped
  placement    every VO line by envelope NCC (spot-audio-assembly/qc_vo_placement.py), < 15 ms
  FORMAT rows  frame = the EDL canvas (1080 on the short side) · H.264 High yuv420p · BT.709 primaries + transfer + MATRIX
               (shipped finals carried an untagged matrix until 2026-09-10) · CFR at the EDL fps (r == avg) · faststart
               (moov before mdat) · AAC 48 kHz stereo
  black/frozen blackdetect ≥ 0.1 s anywhere but a trailing fade; freezedetect ≥ 0.5 s inside the footage span (the card is
               meant to hold)
Every row carries a KIND: `format` rows are mechanically fixable — the agent fixes them alone (a re-mux with
`-bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1`, a faststart re-mux, a re-encode
at the right frame); `judgement` rows change the content (duration, loudness, cuts, black frames) and go to the operator.
Exit 1 on any FAIL; the summary names the failures by kind.

  qc_deliverable.py --root <project> --edl edit/<SPOT>-EDL.json --deliv deliver/<file>.mp4 [--placement <qc_vo_placement.py>] [--no-card]
"""
import argparse, json, os, re, subprocess, sys
import numpy as np

SK = os.path.expanduser('~/.claude/skills')


def sh(c): return subprocess.run(c, capture_output=True, text=True)


def last_frame_thumb(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-sseof', '-0.2', '-i', p, '-frames:v', '1', '-vf', 'scale=96:170,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(raw[-96 * 170:], np.uint8).astype(np.float32) if len(raw) >= 96 * 170 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl', required=True); ap.add_argument('--deliv', required=True)
    ap.add_argument('--placement', default=f'{SK}/spot-audio-assembly/scripts/qc_vo_placement.py'); ap.add_argument('--no-card', action='store_true')
    ap.add_argument('--tp-ceiling', type=float, default=-1.0, help='the delivered true-peak bar (the platform ceiling); the EDL TP is the encode target under it')
    a = ap.parse_args(); os.chdir(a.root); e = json.load(open(a.edl, encoding='utf-8')); D = a.deliv; fails = []
    if not os.path.exists(D): sys.exit(f'QC-DELIVERABLE FAIL (missing) — no file at {D}')

    def verdict(ok, label, detail, kind='judgement'): (None if ok else fails.append((label, kind))); print(f"{'PASS' if ok else 'FAIL'} [{kind}] {label}: {detail}")

    # ---- format rows (mechanically fixable) ----
    pr = json.loads(sh(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,codec_name,profile,pix_fmt,width,height,r_frame_rate,avg_frame_rate,color_primaries,color_transfer,color_space,sample_rate,channels', '-of', 'json', D]).stdout or '{}').get('streams', [])
    vs = next((x for x in pr if x.get('codec_type') == 'video'), {}); au = next((x for x in pr if x.get('codec_type') == 'audio'), {})
    cw, ch = (e.get('canvas') or [1080, 1920])[:2]; efps = float(e.get('fps', 24))
    verdict((vs.get('width'), vs.get('height')) == (cw, ch) and min(cw, ch) == 1080, 'frame', f"{vs.get('width')}x{vs.get('height')} vs the EDL canvas {cw}x{ch} (1080 on the short side — 1080p masters only)", 'format')
    verdict(vs.get('codec_name') == 'h264' and vs.get('pix_fmt') == 'yuv420p', 'codec', f"{vs.get('codec_name')} {vs.get('profile')} {vs.get('pix_fmt')} (want h264 High yuv420p)", 'format')
    tags = (vs.get('color_primaries'), vs.get('color_transfer'), vs.get('color_space'))
    verdict(tags == ('bt709', 'bt709', 'bt709'), 'colour tags', f"primaries/transfer/matrix = {tags} (want bt709 ×3; fix without a re-encode: -c copy -bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1)", 'format')

    def fr(x):
        try: n, d_ = x.split('/'); return float(n) / float(d_)
        except Exception: return 0.0
    verdict(abs(fr(vs.get('r_frame_rate', '0/1')) - efps) < 0.01 and vs.get('r_frame_rate') == vs.get('avg_frame_rate'), 'fps / CFR', f"r {vs.get('r_frame_rate')} avg {vs.get('avg_frame_rate')} vs the EDL {efps:g} (r != avg = variable frame rate)", 'format')
    head = open(D, 'rb').read(2_000_000); mo, md = head.find(b'moov'), head.find(b'mdat')
    verdict(0 < mo < md if md >= 0 else mo > 0, 'faststart', f"moov at {mo}, mdat at {md} (moov must come first; fix: -c copy -movflags +faststart)", 'format')
    verdict(au.get('codec_name') == 'aac' and str(au.get('sample_rate')) == '48000' and au.get('channels') == 2, 'audio format', f"{au.get('codec_name')} {au.get('sample_rate')} Hz {au.get('channels')} ch (want aac 48000 2)", 'format')

    dur = float(sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', D]).stdout or 0)
    verdict(abs(dur - e['runtime_s']) < 0.05, 'duration', f"{dur:.3f} s vs EDL runtime {e['runtime_s']:.3f}")
    lo = sh(['ffmpeg', '-v', 'info', '-nostats', '-i', D, '-af', 'ebur128=peak=true', '-f', 'null', '-']).stderr
    I = re.findall(r'\n\s+I:\s+(-?[\d.]+|-inf) LUFS', lo); LRA = re.findall(r'LRA:\s+([\d.]+) LU', lo); TP = re.findall(r'Peak:\s+(-?[\d.]+|-inf) dBFS', lo)
    li = float(I[-1]) if I and I[-1] != '-inf' else float('-inf'); tp = float(TP[-1]) if TP and TP[-1] != '-inf' else float('-inf')
    ln = e.get('audio', {}).get('loudnorm', {'I': -14, 'TP': -1})
    verdict(np.isfinite(li) and abs(li - ln['I']) <= 1.0, 'loudness', f"I {li} LUFS (target {ln['I']}) · LRA {LRA[-1] if LRA else '?'}" + ('' if np.isfinite(li) else ' — SILENT TRACK'))
    over = tp - ln['TP']   # the EDL's TP is the encode-side target; AAC overshoots it by up to ~1 dB, so the delivered bar is the platform ceiling
    verdict(np.isfinite(tp) and tp <= a.tp_ceiling + 0.05, 'true peak', f"{tp} dBTP vs the platform ceiling {a.tp_ceiling} (EDL target {ln['TP']}, {over:+.1f} dB over it" + ('' if over <= 1.0 else ' — more than the AAC overshoot: check the limiter order') + ')')
    cuts = [round(float(x), 3) for x in re.findall(r'pts_time:([\d.]+)', sh(['ffmpeg', '-v', 'info', '-nostats', '-i', D, '-vf', "select='gt(scene,0.25)',showinfo", '-f', 'null', '-']).stderr)]
    joins = [round(x['tl'][0], 3) for x in e['events'][1:]]
    tol = max(0.05, 1.5 / efps)   # a scene-detector time against a declared take time: 1.5 frames
    acc_tl = [x['tl'][0] + float(c) - x['in'] for x in e['events'] for c in x.get('accepted_cuts', [])]
    extra = [c for c in cuts if not any(abs(c - j) < 0.03 for j in joins)]; missing = [j for j in joins if not any(abs(c - j) < 0.03 for c in cuts)]
    declared = [c for c in extra if any(abs(c - t) <= tol for t in acc_tl)]; extra = [c for c in extra if c not in declared]
    print(f"INFO cuts: delivered {cuts}\n      EDL joins {joins}\n      declared accepted cuts (composed inside a generation): {declared}\n      extra detections (a take's own cut, motion, or a LEAK — read each): {extra}\n      joins not detected (soft/jump joins are normal): {missing}")
    cache = {}

    def tcuts(t):
        if t not in cache: cache[t] = [round(float(x), 3) for x in re.findall(r'pts_time:([\d.]+)', sh(['ffmpeg', '-v', 'info', '-nostats', '-i', t, '-vf', "select='gt(scene,0.3)',showinfo", '-f', 'null', '-']).stderr)]
        return cache[t]

    leaks = []; kept = []
    for x in e['events']:
        if 'src' not in x or not os.path.exists(x['take']): continue
        acc = [float(c) for c in x.get('accepted_cuts', [])]
        inside = [c for c in tcuts(x['take']) if x['in'] + 0.03 < c < x['out'] - 0.03]
        kept += [f"{x['id']} {c}" for c in inside if any(abs(c - k) <= tol for k in acc)]
        bad = [c for c in inside if not any(abs(c - k) <= tol for k in acc)]
        if bad: leaks.append(f"{x['id']} {x['take']} in {x['in']:.3f} out {x['out']:.3f} crosses the take's cut at {bad}")
    if kept: print(f"INFO accepted cuts inside hero windows (declared on the event, not leaks): {kept}")
    verdict(not leaks, 'take-cut leaks', f"{len(leaks)} leak(s) over {sum(1 for x in e['events'] if 'src' in x)} hero events" + ''.join('\n      ' + l for l in leaks))
    card = [x for x in e['events'] if x.get('role') == 'endcard']
    # ---- black and frozen frames (judgement: a content defect the operator sees) ----
    foot_end = float(card[0]['tl'][0]) if card else dur
    bl = sh(['ffmpeg', '-v', 'info', '-nostats', '-i', D, '-vf', 'blackdetect=d=0.1:pic_th=0.98', '-f', 'null', '-']).stderr
    blacks = [(float(s0), float(e0)) for s0, e0 in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', bl)]
    bad_black = [b for b in blacks if b[1] < dur - 0.3]   # a trailing fade to black is a choice; a black run anywhere else is a hole
    verdict(not bad_black, 'black frames', f"{len(blacks)} black run(s) ≥ 0.1 s: {[(round(x, 2), round(y, 2)) for x, y in blacks]}" + (' — trailing fade only' if blacks and not bad_black else ''))
    fz = sh(['ffmpeg', '-v', 'info', '-nostats', '-i', D, '-vf', f"trim=0:{foot_end:.3f},freezedetect=n=-60dB:d=0.5", '-f', 'null', '-']).stderr
    frozen = re.findall(r'freeze_start: ([\d.]+)', fz)
    verdict(not frozen, 'frozen frames', f"{len(frozen)} frozen run(s) ≥ 0.5 s inside the footage span 0–{foot_end:.2f} s at {[round(float(x), 2) for x in frozen]} (the end card is allowed to hold)")
    if card and not a.no_card:
        A, B = last_frame_thumb(D), last_frame_thumb(card[0]['take'])
        if A is None or B is None: verdict(False, 'end card', 'could not read a last frame')
        else:
            A -= A.mean(); B -= B.mean(); ncc = float((A * B).sum() / (np.sqrt((A * A).sum() * (B * B).sum()) + 1e-9))
            verdict(ncc >= 0.9, 'end card', f"last frame vs {os.path.basename(card[0]['take'])} NCC {ncc:.3f}")
    r = sh([sys.executable, os.path.expanduser(a.placement), '--root', '.', '--edl', a.edl, '--deliv', D]); out = r.stdout.strip()
    print('      ' + out.replace('\n', '\n      ')[-900:]); verdict(r.returncode == 0 and 'PLACEMENT OK' in out, 'VO placement', 'see the lines above')
    by = {k: [l for l, kk in fails if kk == k] for k in ('format', 'judgement')}
    summary = '; '.join(f"{k}: {', '.join(v)}" for k, v in by.items() if v)
    print(f"QC-DELIVERABLE {'FAIL (' + summary + ')' if fails else 'PASS'} — {D}" + ("\n      format rows: fix mechanically and re-run; judgement rows: the operator decides" if fails else '')); sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
