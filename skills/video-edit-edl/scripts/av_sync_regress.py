#!/usr/bin/env python3
"""av_sync_regress.py — the A/V-sync regression suite for the EDL cut path. Synthetic takes carry a white flash frame and a
1 kHz pulse on ONE clock; the REAL finisher (video-finish-qc `finish_spot.py`: cut → master → deliver, with the real
`build_vo_stem.py`) cuts them from a generated EDL, and the decoded output is read back — pixels and samples, the audio
decoded on its own presentation clock (`aresample=async=1:first_pts=0`), because a raw-PCM decode concatenates samples and
drops the timestamps a player honours. Pattern: bridgeclip's flash-and-pulse fixtures (`docs/AV_SYNC_REVIEW_2026-09-24.md`).

Fixtures — each a scratch project, nothing written outside a temp dir:
  offgrid  N events at off-grid in/out points, contiguous on the timeline (the cut stage): every flash within 1 frame of
           tl0 + (s - in), and the cut's frame count == round(runtime × fps) — per-segment frame rounding must not accumulate
  native   the same shape with the take's own audio as the bed: every flash has its pulse within 1 frame + 5 ms, in the
           master AND the AAC deliverable, and no pulse is lost
  late     the take's audio track starts 300 ms after its video (the container's start time; the content is aligned)
  gap      the take's audio misses packets from 3.0 to 3.5 s (Matroska keeps the gap on the clock)
  vo       VO lines placed at their EDL times by build_vo_stem.py; one line's file carries a 0.4 s timestamp gap
The tolerance is the measurement's, not a budget: one output frame for a flash (plus 5 ms for a pulse's 5 ms RMS bucket).

  av_sync_regress.py [--only offgrid,native,late,gap,vo] [--events 40] [--fps 24] [--seed 7] [--grid] [--keep <dir>]
Exit 0 = every fixture PASS · 1 = any FAIL. Sentinel: AV-SYNC-REGRESS-END.
"""
import argparse, json, os, random, shutil, subprocess, sys, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.abspath(os.path.join(HERE, '..', '..'))
FINISH = os.path.join(SK, 'video-finish-qc', 'scripts', 'finish_spot.py')
STEM = os.path.join(SK, 'spot-audio-assembly', 'scripts', 'build_vo_stem.py')
SR, TAKE_S, CANVAS = 48000, 12.0, (108, 192)


def ff(*a): subprocess.run(['ffmpeg', '-v', 'error', '-y', *a], check=True)


def take(path, fps, audio='aligned'):
    """flash frames every fps//2 frames (0.5 s at even fps); 20 ms 1 kHz pulses at the same presentation times"""
    k = fps // 2; per = k / fps
    vid = f"color=c=black:s=64x64:r={fps}:d={TAKE_S},drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='eq(mod(n\\,{k})\\,0)'"
    def aud(shift, d): return f"aevalsrc='if(lt(mod(t+{shift}\\,{per})\\,0.02)\\,0.5*sin(2*PI*1000*t)\\,0)':s={SR}:d={d}"
    enc = ['-c:v', 'libx264', '-pix_fmt', 'yuv420p'] + (['-g', '1', '-bf', '0', '-c:a', 'pcm_s16le'] if audio == 'gap' else ['-c:a', 'aac', '-b:a', '128k'])   # the gap take: PCM, so no untrimmed priming blurs it
    if audio == 'aligned': ff('-f', 'lavfi', '-i', vid, '-f', 'lavfi', '-i', aud(0, TAKE_S), '-map', '0:v', '-map', '1:a', *enc, path)
    elif audio == 'late':   # the track starts 0.3 s late; its content is shifted so presentation stays aligned
        ff('-f', 'lavfi', '-i', vid, '-itsoffset', '0.3', '-f', 'lavfi', '-i', aud(0.3, TAKE_S - 0.3), '-map', '0:v', '-map', '1:a', *enc, path)
    elif audio == 'gap':    # packets 3.0–3.5 s missing; the timestamps after the gap are kept
        ff('-f', 'lavfi', '-i', vid, '-f', 'lavfi', '-i', aud(0, TAKE_S), '-map', '0:v', '-map', '1:a', '-af',
           "asetnsamples=n=480,aselect='not(between(t\\,3.0\\,3.5))'", *enc, path)
    return per


def vo_file(path, pulses_at, gap=None, dur=1.6):
    af = f"aevalsrc='{'+'.join(f'if(between(t\\,{p}\\,{p + 0.02})\\,0.5*sin(2*PI*1000*t)\\,0)' for p in pulses_at)}':s={SR}:d={dur}"
    extra = ['-af', f"asetnsamples=n=480,aselect='not(between(t\\,{gap[0]}\\,{gap[1]}))'"] if gap else []
    ff('-f', 'lavfi', '-i', af, *extra, '-c:a', 'aac' if path.endswith('.m4a') else 'pcm_s16le', path)   # the gap file: PCM in Matroska, no priming


def flashes(path, fps):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-map', '0:v:0', '-vf', f'fps={fps},scale=8:8,format=gray', '-f', 'rawvideo', '-'],
                         capture_output=True, check=True).stdout
    m = np.frombuffer(raw, np.uint8).reshape(-1, 64).mean(1)
    return [i / fps for i in np.flatnonzero(m > 128)], len(m)


def pulses(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-map', '0:a:0', '-af', 'aresample=async=1:first_pts=0', '-ac', '1', '-ar', str(SR),
                          '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    x = np.abs(np.frombuffer(raw, np.float32)); w = SR // 200                                    # 5 ms RMS windows
    n = len(x) // w; r = np.sqrt((x[:n * w].reshape(n, w).astype(np.float64) ** 2).mean(1)) if n else np.zeros(0)
    on = [i for i in range(n) if r[i] > 0.02 and (i == 0 or r[i - 1] <= 0.02)]
    out = []
    for i in on:                                                                                  # refine to the first loud sample
        j = np.flatnonzero(x[i * w - w if i else 0:(i + 1) * w] > 0.05)
        out.append(((i * w - w if i else 0) + (j[0] if len(j) else w)) / SR)
    return out


def match(req, allowed, got, tol, bounds=(), guard=0.0, debug=None, slack=0.0):
    """(max |error| of each REQUIRED time to its nearest detection, required with none within tol, detections within tol of no
    ALLOWED time). Required = source events two frames clear of both cuts; allowed adds the ones nearer a cut and the edges of
    a packet gap. A detection within `guard` of a cut is ambiguous (a partial pulse, a flash the seek rounded in) and is skipped
    for the extra count only."""
    near = [min((abs(g - e) for g in got), default=float('inf')) for e in req]
    free = [g for g in got if not any(abs(g - b) < guard for b in bounds)]
    stray = [g for g in free if min((abs(g - e) for e in allowed), default=float('inf')) > max(tol, slack)]
    if debug is not None:
        debug += [f'required {e:.3f} → nearest detection {n * 1000:.1f} ms' for e, n in zip(req, near) if n > tol]
        debug += [f'detected {g:.3f} matches no source event' for g in stray]
    return (max(near) if near else 0.0), sum(1 for n in near if n > tol), len(stray)


def edl(d, take_rel, n, fps, seed, native, vo=None, grid=False):
    rng, t, ev = random.Random(seed), 0, []
    for i in range(n):
        dur = rng.randint(280, 1100); inn = rng.randint(50, int(TAKE_S * 1000) - dur - 50)   # milliseconds: off-grid at 24/25/30 fps
        if grid: dur, inn = (round(round(x * fps / 1000) * 1000 / fps) for x in (dur, inn))   # frame-aligned to the ms (--grid)
        e = {'id': f'E{i:02d}', 'take': take_rel, 'src': take_rel, 'in': inn / 1000, 'out': (inn + dur) / 1000,
             'tl': [t / 1000, (t + dur) / 1000], 'handle_head': inn / 1000, 'look': 'none'}
        if native: e['native_audio_vol'] = 1
        ev.append(e); t += dur
    E = {'spot': 'RG', 'deliver_base': 'RG', 'runtime_s': t / 1000, 'canvas': list(CANVAS), 'events': ev,
         'audio': {'vo': {'stem': 'edit/mix/RG-vo-stem.wav', 'peak_cap_dbfs': -1.0, 'target_lufs': -16.0, **(vo or {})},
                   'sfx': {}, 'music': {}, 'loudnorm': {'I': -16, 'TP': -1.5, 'LRA': 11}, 'captions_dir': 'edit/captions'}}
    os.makedirs(os.path.join(d, 'edit'), exist_ok=True); json.dump(E, open(os.path.join(d, 'edit', 'RG-EDL.json'), 'w'), indent=1)
    return E


def finish(d, fps, log):
    stub = os.path.join(d, 'no_captions.py'); open(stub, 'w').write("print('no captions in the fixture')\n")
    r = subprocess.run([sys.executable, FINISH, '--root', d, '--edl', 'edit/RG-EDL.json', '--stage', 'all', '--look', 'none', '--canvas',
                        f'{CANVAS[0]}x{CANVAS[1]}', '--fps', str(fps), '--no-gate', '--min-free-gb', '0', '--stem-builder', STEM,
                        '--captions-builder', stub], capture_output=True, text=True)
    open(log, 'w').write(r.stdout + r.stderr)
    if r.returncode != 0 or 'FINISH-END' not in r.stdout: raise RuntimeError(f'finish_spot.py failed — {log}:\n' + (r.stdout + r.stderr)[-800:])
    return {k: os.path.join(d, p) for k, p in (('cut', 'edit/mezz/RG-footage-graded.mov'), ('master', 'edit/mezz/RG-master-108x192.mov'),
                                                ('deliver', 'deliver/RG-v1.mp4'))}


def events(E, per, fps, absent=None):
    """(required, allowed) output times of the source's flash/pulse events. Required: two frames clear of both cuts and
    outside a packet gap. Allowed: every event inside [in, out) except those whose packets are missing, plus a 30 ms edge
    band at the gap's ends (an encoder smears a hard gap edge)."""
    req, allowed, m = [], [], 2.0 / fps + 1e-6
    for e in E['events']:
        for k in range(int(TAKE_S / per) + 1):
            s = k * per
            if not (e['in'] <= s < e['out']): continue
            t = e['tl'][0] + (s - e['in'])
            if absent and absent[0] - 0.03 <= s <= absent[1] + 0.03:
                if not (absent[0] + 0.03 < s < absent[1] - 0.03): allowed.append(t)   # the edge band: allowed, never required
                continue
            allowed.append(t)
            if e['in'] + m <= s <= e['out'] - m: req.append(t)
    return req, allowed


def run_fixture(name, root, a):
    d = os.path.join(root, name); os.makedirs(os.path.join(d, 'takes'), exist_ok=True); fps = a.fps; lines = []; ok = True
    tol_f, tol_p, tol_a = 1.0 / fps + 1e-6, 1.0 / fps + 0.005, 0.005   # a flash: one frame · flash→pulse: a frame + a bucket · audio→EDL: a bucket
    if name == 'vo':
        per = take(os.path.join(d, 'takes', 't.mp4'), fps)
        vo_file(os.path.join(d, 'takes', 'L1.wav'), [0.2]); vo_file(os.path.join(d, 'takes', 'L2.mkv'), [0.2, 1.2], gap=(0.5, 0.9))
        vo_file(os.path.join(d, 'takes', 'L3.m4a'), [0.2])                                         # AAC in MP4: the priming sits in an edit list
        E = edl(d, 'takes/t.mp4', 12, fps, a.seed, False, vo={'L1': {'file': 'takes/L1.wav', 'at': 0.5, 'lufs': -30.0, 'source': 'fixture'},
                                                              'L2': {'file': 'takes/L2.mkv', 'at': 2.25, 'lufs': -30.0, 'source': 'fixture'},
                                                              'L3': {'file': 'takes/L3.m4a', 'at': 4.0, 'lufs': -30.0, 'source': 'fixture'}})
        out = finish(d, fps, os.path.join(d, 'finish.log'))
        exp = [0.7, 2.45, 3.45, 4.2]; got = pulses(out['master']); err, miss, extra = match(exp, exp, got, 0.005)
        ok = err <= 0.005 and not miss and not extra
        lines.append(f"VO placement in the master: max error {err * 1000:.1f} ms over {len(exp)} pulses (tolerance 5 ms), missing {miss}, extra {extra}"
                     + ('' if ok else f" — detected {[round(g, 3) for g in got]}, expected {exp}"))
        return ok, lines
    mode = {'offgrid': 'aligned', 'native': 'aligned', 'late': 'late', 'gap': 'gap'}[name]
    ext = '.mkv' if mode == 'gap' else '.mp4'; tk = f'takes/t{ext}'
    per = take(os.path.join(d, tk), fps, mode)
    E = edl(d, tk, a.events, fps, a.seed, name != 'offgrid', grid=a.grid)
    out = finish(d, fps, os.path.join(d, 'finish.log'))
    exp_f, all_f = events(E, per, fps); got_f, nfr = flashes(out['cut'], fps); bounds = [e['tl'][0] for e in E['events']]
    dbg = [] if a.debug else None
    err, miss, extra = match(exp_f, all_f, got_f, tol_f, bounds, 1.0 / fps + 1e-6, dbg); want = round(E['runtime_s'] * fps)
    last = min((abs(g - exp_f[-1]) for g in got_f), default=float('inf')) * fps if exp_f else float('nan')   # drift shows at the END
    c_ok = err <= tol_f and not miss and not extra and nfr == want; ok &= c_ok
    lines.append(f"picture (cut): max flash error {err * fps:.2f} frames over {len(exp_f)} flashes (tolerance 1), missing {miss}, extra {extra};"
                 f" frames {nfr} vs round(runtime x fps) {want} ({nfr - want:+d}); last flash off by {last:.2f} frames")
    if dbg: lines += ['  cut: ' + x for x in dbg]
    if name == 'offgrid': return ok, lines
    absent = (3.0, 3.5) if mode == 'gap' else None
    exp_p, all_p = events(E, per, fps, absent)
    for stage in ('master', 'deliver'):
        gf, _ = flashes(out[stage], fps); gp = pulses(out[stage])
        dbg = [] if a.debug else None
        perr, pmiss, pextra = match(exp_p, all_p, gp, tol_a, bounds, 1.0 / fps, dbg, slack=1.0 / fps)   # an edge fragment sits up to a frame off its onset
        clear = [f for f in gf if not any(-1.0 / fps <= f - b <= 1.0 / fps for b in bounds)
                 and not (absent and any(e['tl'][0] + absent[0] - e['in'] - 0.05 <= f < e['tl'][0] + absent[1] - e['in'] for e in E['events']))]
        av = max((min((abs(p - f) for p in gp), default=float('inf')) for f in clear), default=0.0)   # every clear flash → its nearest pulse
        s_ok = perr <= tol_a and not pmiss and not pextra and av <= tol_p; ok &= s_ok
        lines.append(f"{stage}: pulses vs the EDL max {perr * 1000:.1f} ms (tolerance {tol_a * 1000:.0f}), missing {pmiss}, extra {pextra};"
                     f" flash→nearest pulse max {av * 1000:.1f} ms (tolerance {tol_p * 1000:.0f})")
        if dbg: lines += [f'  {stage}: ' + x for x in dbg]
    return ok, lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--only', default='offgrid,native,late,gap,vo'); ap.add_argument('--events', type=int, default=40)
    ap.add_argument('--fps', type=int, default=24); ap.add_argument('--seed', type=int, default=7); ap.add_argument('--keep')
    ap.add_argument('--debug', action='store_true', help='list every expected event with no detection, and every stray detection')
    ap.add_argument('--grid', action='store_true', help='frame-aligned in/out points (a diagnostic: off-grid is the default and the stress)')
    a = ap.parse_args()
    if a.fps % 2: ap.error('--fps must be even (the flash period is fps/2 frames = 0.5 s)')
    for p in (FINISH, STEM):
        if not os.path.isfile(p): sys.exit(f'missing sibling script {p} — run from a tree holding video-finish-qc and spot-audio-assembly')
    root = a.keep or tempfile.mkdtemp(prefix='av-sync-'); os.makedirs(root, exist_ok=True); allok = True
    try:
        for name in [x for x in a.only.split(',') if x]:
            try: ok, lines = run_fixture(name, root, a)
            except Exception as ex: ok, lines = False, [f'ERROR {ex}']
            allok &= ok; print(f"{'PASS' if ok else 'FAIL'} {name}"); [print('     ' + l) for l in lines]
    finally:
        if not a.keep: shutil.rmtree(root, ignore_errors=True)
    print(f"AV-SYNC-REGRESS {'PASS' if allok else 'FAIL'}"); print('AV-SYNC-REGRESS-END'); sys.exit(0 if allok else 1)


if __name__ == '__main__':
    main()
