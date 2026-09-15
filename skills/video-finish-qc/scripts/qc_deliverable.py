#!/usr/bin/env python3
"""qc_deliverable.py — the delivery QC in ONE pass on the DELIVERED file, per metric with its label (never a total score):
  duration     vs the EDL runtime (< 50 ms)
  loudness     integrated LUFS · LRA · true peak — and the loudness must be FINITE: an audio-STREAM check is not a SOUND check
               (a conforming AAC track at -inf passes a stream probe and ships silent); the true peak must sit under the platform
               ceiling (--tp-ceiling; default = the EDL's loudnorm.TP_ceiling, else -1 dBTP) — the EDL's TP is the master's
               limiter ceiling under it, and the AAC overshoot on limited peaks measured 0.4–1.0 dB, growing with the limiting
  cuts         the delivered scene-cut list vs the EDL joins: extras are a take's own cut, motion, or a LEAK — named
  leaks        every hero event's [in,out] against ITS TAKE's own scene cuts (a window crossing one = rogue frames) — except
               the cuts the event DECLARES in accepted_cuts (composed inside one generation and kept), printed as INFO
  card         the last frame of the deliverable vs the last frame of the card render (NCC ≥ 0.9): the right card shipped
  placement    every VO line by envelope NCC (spot-audio-assembly/qc_vo_placement.py), < 15 ms
  FORMAT rows  frame = the EDL canvas (1080 on the short side) · H.264 High yuv420p · BT.709 primaries + transfer + MATRIX
               (shipped finals carried an untagged matrix until 2026-09-10) · CFR at the EDL fps (r == avg) · faststart
               (moov before mdat) · AAC 48 kHz stereo
  black/frozen blackdetect ≥ 0.1 s anywhere but a trailing fade; freezedetect ≥ qc.max_still_s (--max-still-s; 0.5 s by
               default) inside the footage span, the longest run printed — the card holds by design, and a designed hold
               inside the footage is declared on its event as accepted_still: "<why>" and prints as INFO
  geometry     INFO: every hero take probed for SAR and rotation — a source whose display shape differs from its storage
               shape is listed (normalise before any crop: video-production/scripts/probe_sources.py); the eye check is a
               delivered frame beside the source's display frame at 1:1
  near-black   EVERY event's window sampled at three points (10 / 50 / 90 %): a window whose samples all read under
               --black-luma (16/255) FAILS unless the event declares `accepted_black: true` — a 10-bit source once rendered
               black through a grade while every other row passed (2026-09-15)
  phone band   INFO, with --phone-ref <real phone clips>: the delivered file's phone-texture band (phone_texture_probe.py —
               dead-flat 8×8 share, noise floor, median block sd) against the RANGE over every reference frame; a
               creator-style spot's read, never a failure — the operator judges the phone render beside the clean one
Every row carries a KIND: `format` rows are mechanically fixable — the agent fixes them alone (a re-mux with
`-bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1`, a faststart re-mux, a re-encode
at the right frame); `judgement` rows change the content (duration, loudness, cuts, black frames) and go to the operator.
Exit 1 on any FAIL; the summary names the failures by kind.

  qc_deliverable.py --root <project> --edl edit/<SPOT>-EDL.json --deliv deliver/<file>.mp4 [--placement <qc_vo_placement.py>] [--no-card] [--tp-ceiling] [--max-still-s]
  qc_deliverable.py --selftest        # the near-black instrument against a synthetic clip: a black event FAILS, a declared one passes
"""
import argparse, json, os, re, subprocess, sys
import numpy as np

SK = os.path.expanduser('~/.claude/skills')


def sh(c): return subprocess.run(c, capture_output=True, text=True)


def mean_luma(p, t):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', p, '-frames:v', '1', '-vf', 'scale=32:32,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return float(np.frombuffer(raw[-1024:], np.uint8).mean()) if len(raw) >= 1024 else None


def near_black_events(D, events, thr=16.0):
    """Every event's window sampled at 10 / 50 / 90 %: returns [(id, [lumas])] for windows whose samples ALL read under thr and
    that do not declare accepted_black. Three probes per event keep it cheap; a real black hole never passes three."""
    bad = []
    for x in events:
        t0 = float(x['tl'][0]); t1 = float(x['tl'][1]) if len(x.get('tl', [])) > 1 else t0 + float(x.get('out', 0)) - float(x.get('in', 0))
        if t1 - t0 <= 0: continue
        ls = [mean_luma(D, t0 + (t1 - t0) * f) for f in (0.1, 0.5, 0.9)]; ls = [l for l in ls if l is not None]
        if ls and max(ls) < thr and not x.get('accepted_black'): bad.append((x.get('id', '?'), [round(l, 1) for l in ls]))
    return bad


def selftest():
    import tempfile
    d = tempfile.mkdtemp(); clip = os.path.join(d, 'clip.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=gray:s=64x64:d=2:r=24', '-f', 'lavfi', '-i', 'color=c=black:s=64x64:d=2:r=24',
                    '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]', '-pix_fmt', 'yuv420p', clip], check=True)
    ev = [{'id': 'a', 'tl': [0.0, 2.0]}, {'id': 'b', 'tl': [2.0, 4.0]}]
    bad = near_black_events(clip, ev); ok1 = [b[0] for b in bad] == ['b']
    ev[1]['accepted_black'] = True; ok2 = near_black_events(clip, ev) == []
    print(f"SELFTEST {'PASS' if ok1 and ok2 else 'FAIL'}: black event flagged={ok1} (found {bad}), declared event passes={ok2}")
    sys.exit(0 if ok1 and ok2 else 1)


def last_frame_thumb(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-sseof', '-0.2', '-i', p, '-frames:v', '1', '-vf', 'scale=96:170,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(raw[-96 * 170:], np.uint8).astype(np.float32) if len(raw) >= 96 * 170 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl'); ap.add_argument('--deliv')
    ap.add_argument('--placement', default=f'{SK}/spot-audio-assembly/scripts/qc_vo_placement.py'); ap.add_argument('--no-card', action='store_true')
    ap.add_argument('--tp-ceiling', type=float, default=None, help='the delivered true-peak bar (the platform ceiling); default = the EDL loudnorm.TP_ceiling, else -1.0 — the EDL TP is the master target under it')
    ap.add_argument('--max-still-s', type=float, default=None, help='the longest still run allowed inside the footage span; default = the EDL qc.max_still_s, else 0.5')
    ap.add_argument('--black-luma', type=float, default=16.0, help='an event whose three sampled frames all read under this mean luma (0–255) fails unless it declares accepted_black')
    ap.add_argument('--phone-ref', nargs='*', default=[], help="the project's real phone clips: prints the delivered file's phone-texture band against theirs as INFO (a creator-style spot)")
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: selftest()
    if not a.edl or not a.deliv: ap.error('--edl and --deliv are required (or --selftest)')
    os.chdir(a.root); e = json.load(open(a.edl, encoding='utf-8')); D = a.deliv; fails = []
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
    tpc = a.tp_ceiling if a.tp_ceiling is not None else float(ln.get('TP_ceiling', -1.0))   # the platform's bar for the DELIVERED file
    over = tp - ln['TP']   # the EDL's TP is the master's limiter ceiling; AAC overshoots the limited peaks by 0.4–1.0 dB, so the delivered bar is the platform ceiling
    verdict(np.isfinite(tp) and tp <= tpc + 0.05, 'true peak', f"{tp} dBTP vs the platform ceiling {tpc} ({'EDL loudnorm.TP_ceiling' if a.tp_ceiling is None and 'TP_ceiling' in ln else '--tp-ceiling' if a.tp_ceiling is not None else 'the default'}; EDL master target {ln['TP']}, {over:+.1f} dB over it" + ('' if over <= 1.0 else ' — more than the AAC overshoot: check the limiter order') + ')')
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
    # ---- source geometry (INFO: the QC cannot know the crop, but it can say which sources are not what their storage says) ----
    geo = []
    for t in sorted({x['take'] for x in e['events'] if 'src' in x and os.path.exists(x.get('take', ''))}):
        pr = sh(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=sample_aspect_ratio:stream_tags=rotate:stream_side_data=rotation', '-of', 'default=nw=1', t]).stdout
        sm = re.search(r'sample_aspect_ratio=(\S+)', pr); sar = sm.group(1) if sm else '1:1'
        rm = re.search(r'(?:rotation|TAG:rotate)=(-?[\d.]+)', pr); rot = (float(rm.group(1)) % 360) if rm else 0.0
        if sar not in ('1:1', 'N/A', '0:1') or rot: geo.append(f"{os.path.basename(t)} SAR {sar}" + (f" rotation {rot:g}" if rot else ''))
    print(f"INFO source geometry: {len(geo)} hero take(s) whose display shape differs from their storage shape" + (f" — normalise before any crop (video-production/scripts/probe_sources.py); check a delivered frame beside the source's display frame at 1:1: {geo}" if geo else ''))
    card = [x for x in e['events'] if x.get('role') == 'endcard']
    # ---- black and frozen frames (judgement: a content defect the operator sees) ----
    foot_end = float(card[0]['tl'][0]) if card else dur
    bl = sh(['ffmpeg', '-v', 'info', '-nostats', '-i', D, '-vf', 'blackdetect=d=0.1:pic_th=0.98', '-f', 'null', '-']).stderr
    blacks = [(float(s0), float(e0)) for s0, e0 in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', bl)]
    bad_black = [b for b in blacks if b[1] < dur - 0.3]   # a trailing fade to black is a choice; a black run anywhere else is a hole
    verdict(not bad_black, 'black frames', f"{len(blacks)} black run(s) ≥ 0.1 s: {[(round(x, 2), round(y, 2)) for x, y in blacks]}" + (' — trailing fade only' if blacks and not bad_black else ''))
    mst = a.max_still_s if a.max_still_s is not None else float(e.get('qc', {}).get('max_still_s', 0.5))   # the project's threshold, from the EDL
    fz = sh(['ffmpeg', '-v', 'info', '-nostats', '-i', D, '-vf', f"trim=0:{foot_end:.3f},freezedetect=n=-60dB:d={mst:g}", '-f', 'null', '-']).stderr
    runs = []
    for m in re.finditer(r'freeze_(start|duration): ([\d.]+)', fz):   # start … duration pairs; a run still open at the trim end gets the remainder
        if m.group(1) == 'start': runs.append([float(m.group(2)), None])
        elif runs and runs[-1][1] is None: runs[-1][1] = float(m.group(2))
    runs = [(s0, d0 if d0 is not None else max(0.0, foot_end - s0)) for s0, d0 in runs]
    holds = [(float(x['tl'][0]), float(x['tl'][1]), x['id']) for x in e['events'] if x.get('accepted_still')]
    declared_runs = [r for r in runs if any(h0 - 0.05 <= r[0] <= h1 for h0, h1, _ in holds)]
    frozen = [r for r in runs if r not in declared_runs]; longest = max((d for _, d in runs), default=0.0)
    if declared_runs: print(f"INFO still runs inside declared holds (accepted_still on the event): {[(round(s0, 2), round(d0, 2)) for s0, d0 in declared_runs]}")
    nb = near_black_events(D, e['events'], a.black_luma)
    verdict(not nb, 'near-black events', f"{len(nb)} event window(s) read black at all three samples (< {a.black_luma:g}/255): {nb}" + (' — a source type the grade turns black? declare accepted_black only for a shot meant to be black' if nb else ''))
    src = '--max-still-s' if a.max_still_s is not None else ('the EDL qc.max_still_s' if 'max_still_s' in e.get('qc', {}) else 'the default')
    verdict(not frozen, 'frozen frames', f"{len(frozen)} still run(s) ≥ {mst:g} s inside the footage span 0–{foot_end:.2f} s at {[(round(s0, 2), round(d0, 2)) for s0, d0 in frozen]}; longest run {longest:.2f} s (threshold {mst:g} s from {src}; the end card is allowed to hold)")
    if card and not a.no_card:
        A, B = last_frame_thumb(D), last_frame_thumb(card[0]['take'])
        if A is None or B is None: verdict(False, 'end card', 'could not read a last frame')
        else:
            A -= A.mean(); B -= B.mean(); ncc = float((A * B).sum() / (np.sqrt((A * A).sum() * (B * B).sum()) + 1e-9))
            verdict(ncc >= 0.9, 'end card', f"last frame vs {os.path.basename(card[0]['take'])} NCC {ncc:.3f}")
    r = sh([sys.executable, os.path.expanduser(a.placement), '--root', '.', '--edl', a.edl, '--deliv', D]); out = r.stdout.strip()
    print('      ' + out.replace('\n', '\n      ')[-900:]); verdict(r.returncode == 0 and 'PLACEMENT OK' in out, 'VO placement', 'see the lines above')
    # ---- the phone-texture band (INFO, a creator-style spot: a comparison against the project's real phone clips, never a threshold) ----
    if a.phone_ref:
        pr_ = sh([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phone_texture_probe.py'), '--json', D] + a.phone_ref)
        try: rows = json.loads(pr_.stdout)
        except Exception: rows = []
        if len(rows) == 1 + len(a.phone_ref):
            dv, refs = rows[0], rows[1:]
            for k in ('dead_flat_pct', 'noise_floor', 'median_block_sd'):
                lo, hi = min(x[k + '_min'] for x in refs), max(x[k + '_max'] for x in refs)
                where = 'IN BAND' if lo <= dv[k] <= hi else ('BELOW (less texture than every reference frame)' if dv[k] < lo else 'ABOVE (more texture than every reference frame)')
                print(f"INFO phone band {k}: delivered {dv[k]} (frames {dv[k + '_min']}–{dv[k + '_max']}) vs real [{lo}, {hi}] → {where}")
            print("      the band is a matched-content comparison (video-finish § 5 the phone-native tier); the operator judges the phone render beside the clean one")
        else:
            print('INFO phone band: the probe could not read every clip — ' + (pr_.stderr or pr_.stdout).strip()[-300:])
    by = {k: [l for l, kk in fails if kk == k] for k in ('format', 'judgement')}
    summary = '; '.join(f"{k}: {', '.join(v)}" for k, v in by.items() if v)
    print(f"QC-DELIVERABLE {'FAIL (' + summary + ')' if fails else 'PASS'} — {D}" + ("\n      format rows: fix mechanically and re-run; judgement rows: the operator decides" if fails else '')); sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
