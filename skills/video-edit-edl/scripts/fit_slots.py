#!/usr/bin/env python3
"""fit_slots.py — PICTURE FOLLOWS AUDIO: fit each voiced slot's assigned clip to the slot, never the voice to the clip. The
slots come from `phrase_slots.py` (whole frames, from the voice's phrase onsets); the voice keeps its pace. Per slot, with
`needed` = the slot's frames and `available` = the assigned window (`in` to `out`, or to the end of the take):
  CUT      available ≥ needed               → the event uses the first `needed` seconds of the window (no new file)
  SLOW     short by ≤ --slow-limit (20 %)   → the window stretched by setpts to exactly `needed` frames (frames HELD, none
                                              invented — at 24 fps a 20 % stretch repeats about one frame in five)
  LOOP     shorter than that                → the window extracted, then looped from its start to exactly `needed` frames
  MISSING  no clip, no such take, nothing after `in`, or the take has no recorded pick → REPORTED, never filled: the event
           keeps take null and the finish refuses it (a frozen or black slot is a defect a viewer sees)
Pattern: dsh-narrate ADR 0005 (a voice sped up or padded to fit the picture is the defect a listener hears) and its
render/segment.js (SLOW_LIMIT 0.2; the loop runs over the extracted window, because -stream_loop loops a whole input).

SLOW and LOOP write <fit-dir>/<slot id>.mp4 (H.264 CRF 8, no audio, the frame count checked) and record it as DERIVED from
the take (`video-production/scripts/pick_gate.py derive`), so the upscale and hero scripts accept it. The fitted file is an
ordinary event source afterwards: trim_for_upscale.py, the upscale and finish_spot.py treat it like any take.
The input EDL is never touched; --out gets the fitted copy. An event whose id is a slot id is updated, a slot with no event is
added; tl comes from the slot's frames.

  fit_slots.py --root <project> --slots <slots.json> --assign <assign.json> --edl <EDL.json> --out <fitted EDL.json>
               [--slow-limit 0.2] [--fit-dir edit/fit] [--plan]
  fit_slots.py --selftest
assign.json: {"S1": {"take": "takes/a.mp4", "in": 1.2, "out": 3.4}, "S2": {"take": "footage/C1.mp4", "in": 0.5}, "S3": null}
--plan prints the decisions and writes nothing. Exit 3 when any slot is MISSING (the EDL is still written, the gaps named);
0 otherwise. Sentinel FIT-SLOTS-END.
"""
import argparse, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, '..', '..', 'video-production', 'scripts', 'pick_gate.py')


def dur_of(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return None


def frames_of(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', p],
                       capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


def gate(root, *args):
    return subprocess.run([sys.executable, GATE, *args[:1], '--root', root, *args[1:]], capture_output=True, text=True)


def decide(root, slot, a, fps, slow_limit):
    n = slot['tl_f'][1] - slot['tl_f'][0]; needed = n / fps
    if not a: return {'mode': 'missing', 'why': 'no clip assigned', 'n': n, 'needed': needed}
    tk = a['take']; fp = tk if os.path.isabs(tk) else os.path.join(root, tk)
    if not os.path.isfile(fp): return {'mode': 'missing', 'why': f'no such take {tk}', 'n': n, 'needed': needed}
    d = dur_of(fp); t0 = float(a.get('in', 0.0)); t1 = min(float(a.get('out', d)), d) if d else float(a.get('out', 0))
    avail = t1 - t0
    if avail <= 0: return {'mode': 'missing', 'why': f'nothing left after in={t0} in {tk}', 'n': n, 'needed': needed}
    g = gate(root, 'check', tk)
    if g.returncode != 0: return {'mode': 'missing', 'why': f'{tk} has no recorded pick — nothing is cut on an unpicked clip', 'n': n, 'needed': needed}
    base = {'take': tk, 'in': t0, 'end': t1, 'available': avail, 'n': n, 'needed': needed}
    if avail >= needed - 0.5 / fps: return {**base, 'mode': 'cut'}
    gap = (needed - avail) / needed
    return {**base, 'mode': 'slow' if gap <= slow_limit + 1e-9 else 'loop', 'gap': gap}


def render(root, sid, f, fps, fit_dir):
    out_rel = os.path.join(fit_dir, f'{sid}.mp4'); out = os.path.join(root, out_rel); os.makedirs(os.path.dirname(out), exist_ok=True)
    src = f['take'] if os.path.isabs(f['take']) else os.path.join(root, f['take']); n = f['n']
    enc = ['-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '8', '-pix_fmt', 'yuv420p', '-r', str(fps)]
    if f['mode'] == 'slow':
        k = f['needed'] / f['available']
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f"{f['in']:.6f}", '-t', f"{f['available']:.6f}", '-i', src, '-vf',
                        f'setpts=(PTS-STARTPTS)*{k:.6f},fps={fps},tpad=stop_mode=clone:stop=2,trim=end_frame={n}', *enc, out], check=True)
    else:
        with tempfile.TemporaryDirectory() as td:
            win = os.path.join(td, 'window.mkv')   # -stream_loop loops a WHOLE input, so the window becomes one first
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f"{f['in']:.6f}", '-t', f"{f['available']:.6f}", '-i', src, '-an', '-c:v', 'ffv1', win], check=True)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-stream_loop', '-1', '-i', win, '-vf',
                            f'fps={fps},tpad=stop_mode=clone:stop=2,trim=end_frame={n}', *enc, out], check=True)
    got = frames_of(out)
    if got != n: raise SystemExit(f'{sid}: the fitted file has {got} frames, the slot needs {n} — nothing written to the EDL')
    return out_rel


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--slots'); ap.add_argument('--assign'); ap.add_argument('--edl'); ap.add_argument('--out')
    ap.add_argument('--slow-limit', type=float, default=0.2); ap.add_argument('--fit-dir', default='edit/fit'); ap.add_argument('--plan', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest: return selftest()
    if not (a.slots and a.assign and a.edl and (a.out or a.plan)): ap.error('--slots --assign --edl and --out (or --plan)')
    root = a.root; J = lambda p: json.load(open(p if os.path.isabs(p) else os.path.join(root, p), encoding='utf-8'))
    S, A = J(a.slots), J(a.assign); fps = int(S['fps']); plan = []
    for s in S['slots']:
        f = decide(root, s, A.get(s['id']), fps, a.slow_limit); plan.append((s, f))
        w = f"{f['take']} {f['in']:.3f}–{f['end']:.3f} ({f['available']:.3f} s)" if 'take' in f else ''
        print(f"{s['id']:5} {f['mode'].upper():7} needed {f['needed']:.3f} s ({f['n']} f) {w}"
              + (f" — short by {f['gap'] * 100:.0f} %" if 'gap' in f else '') + (f" — {f['why']}" if 'why' in f else ''))
    missing = [s['id'] for s, f in plan if f['mode'] == 'missing']
    if a.plan:
        print(f"plan only: {len(plan) - len(missing)} fit, {len(missing)} missing{' (' + ', '.join(missing) + ')' if missing else ''}"); print('FIT-SLOTS-END')
        return 3 if missing else 0
    E = J(a.edl); byid = {e['id']: e for e in E['events']}
    for s, f in plan:
        e = byid.get(s['id'])
        if e is None: e = {'id': s['id']}; E['events'].append(e); byid[s['id']] = e
        e['tl'] = [round(s['tl_f'][0] / fps, 6), round(s['tl_f'][1] / fps, 6)]
        for k in ('src', 'handle_head'): e.pop(k, None)
        if f['mode'] == 'missing':
            e.update(take=None, fit={'mode': 'missing', 'why': f['why']}); continue
        if f['mode'] == 'cut':
            e.update(take=f['take'], **{'in': round(f['in'], 6), 'out': round(f['in'] + f['needed'], 6)}, fit={'mode': 'cut'}); continue
        rel = render(root, s['id'], f, fps, a.fit_dir)
        d = gate(root, 'derive', '--from', f['take'], '--note', f"fit_slots {f['mode']} for slot {s['id']}", rel)
        if d.returncode != 0: raise SystemExit(f"{s['id']}: the lineage was refused — {d.stdout.strip()}")
        e.update(take=rel, **{'in': 0.0, 'out': round(f['needed'], 6)},
                 fit={'mode': f['mode'], 'from': f['take'], 'window': [round(f['in'], 6), round(f['end'], 6)],
                      **({'factor': round(f['needed'] / f['available'], 6)} if f['mode'] == 'slow' else {})})
        print(f"  {s['id']} → {rel} ({f['n']} frames, derived from {f['take']})")
    E['events'].sort(key=lambda e: e['tl'][0])
    out = a.out if os.path.isabs(a.out) else os.path.join(root, a.out)
    if os.path.exists(out): raise SystemExit(f'{a.out} exists — fit into a NEW file (revise by parameter, into a new file)')
    json.dump(E, open(out, 'w', encoding='utf-8'), indent=1)
    print(f"wrote {a.out}: {len(plan) - len(missing)} fitted, {len(missing)} missing{' (' + ', '.join(missing) + ') — the finish refuses them' if missing else ''}")
    print('FIT-SLOTS-END'); return 3 if missing else 0


def selftest():
    import numpy as np
    with tempfile.TemporaryDirectory() as r:
        os.makedirs(os.path.join(r, 'takes')); t = os.path.join(r, 'takes', 't.mp4'); u = os.path.join(r, 'takes', 'u.mp4')
        for p, d in ((t, 5), (u, 4)):   # u differs in content: a byte-identical copy would trace to t's pick by its hash
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f"color=c=black:s=64x64:r=24:d={d},drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='eq(mod(n\\,12)\\,0)'",
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', p], check=True)
        subprocess.run([sys.executable, GATE, 'record', '--root', r, 'takes/t.mp4'], check=True, capture_output=True)
        slots = {'fps': 24, 'slots': [{'id': f'S{i}', 'tl_f': [24 * (i - 1), 24 * i]} for i in range(1, 6)]}
        assign = {'S1': {'take': 'takes/t.mp4', 'in': 1.0}, 'S2': {'take': 'takes/t.mp4', 'in': 1.0, 'out': 1.9},
                  'S3': {'take': 'takes/t.mp4', 'in': 2.0, 'out': 2.4}, 'S4': None, 'S5': {'take': 'takes/u.mp4', 'in': 0.0}}
        for n, o in (('slots.json', slots), ('assign.json', assign), ('edl.json', {'events': []})): json.dump(o, open(os.path.join(r, n), 'w'))
        q = lambda *x: main(['--root', r, '--slots', 'slots.json', '--assign', 'assign.json', '--edl', 'edl.json', *x])
        rc_plan = q('--plan'); plan_clean = not os.path.exists(os.path.join(r, 'edit')); rc = q('--out', 'fit.json')
        E = {e['id']: e for e in json.load(open(os.path.join(r, 'fit.json')))['events']}
        def fl(p):
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(r, p), '-vf', 'scale=8:8,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
            return list(np.flatnonzero(np.frombuffer(raw, np.uint8).reshape(-1, 64).mean(1) > 128))
        s2, s3 = fl(E['S2']['take']), fl(E['S3']['take'])
        chk = [('--plan writes nothing and exits 3 on a missing slot', rc_plan == 3 and plan_clean),
               ('the fitted EDL is written and the run exits 3', rc == 3 and set(E) == {f'S{i}' for i in range(1, 6)}),
               ('S1 long enough → CUT, no new file', E['S1']['fit']['mode'] == 'cut' and E['S1']['take'] == 'takes/t.mp4' and abs(E['S1']['out'] - 2.0) < 1e-6),
               ('S2 short by 10 % → SLOW, factor 1.111', E['S2']['fit']['mode'] == 'slow' and abs(E['S2']['fit']['factor'] - 1 / 0.9) < 1e-4),
               ('S3 short by 60 % → LOOP', E['S3']['fit']['mode'] == 'loop'),
               ('S4 unassigned → MISSING, take null', E['S4']['take'] is None and E['S4']['fit']['mode'] == 'missing'),
               ('S5 unpicked take → MISSING, never cut', E['S5']['take'] is None and 'pick' in E['S5']['fit']['why']),
               ('every fitted file holds exactly the slot\'s 24 frames', frames_of(os.path.join(r, E['S2']['take'])) == 24 == frames_of(os.path.join(r, E['S3']['take']))),
               ('SLOW: the window-start flash at frame 0, the 1.5 s flash at (1.5-1.0)x1.111 s = frame 13 ±1', len(s2) == 2 and s2[0] == 0 and abs(s2[1] - 13) <= 1),
               ('LOOP: the window start repeats every 0.4 s (9.6 frames)', len(s3) >= 2 and s3[0] == 0 and all(9 <= b - a <= 10 for a, b in zip(s3, s3[1:]))),
               ('the fitted files trace to the pick (derived)', gate(r, 'check', E['S2']['take'], E['S3']['take']).returncode == 0),
               ('the tl follows the slots', E['S3']['tl'] == [2.0, 3.0]),
               ('a second run refuses to overwrite its --out', subprocess.run([sys.executable, __file__, '--root', r, '--slots', 'slots.json', '--assign',
                                                                                'assign.json', '--edl', 'edl.json', '--out', 'fit.json'], capture_output=True).returncode != 0)]
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
