#!/usr/bin/env python3
"""voice_ab_reel.py — the A/B reel of voice treatments: each variant once, a gap of silence between, an index printed and
written beside the reel (ordinal · name · start time), so the operator picks by ordinal and the pick goes into the EDL by
name. Processed voice enters a build only after this reel has been heard (spot-audio-assembly § 4).

  voice_ab_reel.py --out audio/reels/REEL-line-3.wav raw=takes/line.wav afftdn9=audio/clean/line_light9.wav model=audio/clean/line_dfn.wav [--gap 0.3]
  voice_ab_reel.py --selftest
Variants are `name=path` (the name is what the operator will say); the reel is 48 kHz stereo WAV; every variant keeps its own
level (the reel is for hearing the treatment, not the mix).
"""
import argparse, os, subprocess, sys, tempfile


def build(out, variants, gap):
    inputs = []; parts = []
    for i, (name, path) in enumerate(variants):
        if not os.path.exists(path): sys.exit(f'missing variant file: {name}={path}')
        inputs += ['-i', path]
        pad = f',apad=pad_dur={gap}' if i < len(variants) - 1 else ''
        parts.append(f'[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo{pad}[a{i}]')
    graph = ';'.join(parts) + ';' + ''.join(f'[a{i}]' for i in range(len(variants))) + f'concat=n={len(variants)}:v=0:a=1[o]'
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', graph, '-map', '[o]', '-c:a', 'pcm_s24le', out], capture_output=True, text=True)
    if r.returncode: sys.exit(f'ffmpeg failed: {r.stderr[-800:]}')
    t = 0.0; rows = []
    for i, (name, path) in enumerate(variants):
        d = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], capture_output=True, text=True).stdout or 0)
        rows.append((i + 1, name, t, d)); t += d + (gap if i < len(variants) - 1 else 0)
    idx = out + '.index.txt'
    with open(idx, 'w', encoding='utf-8') as f:
        for n, name, start, d in rows: f.write(f'{n}\t{name}\t{start:.2f}s\t{d:.2f}s\n')
    return rows, t, idx


def selftest():
    d = tempfile.mkdtemp(); vs = []
    for i, sec in enumerate((1.0, 1.5, 2.0)):
        p = os.path.join(d, f'v{i}.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'sine=frequency={220 * (i + 1)}:duration={sec}', '-ar', '48000', p], check=True)
        vs.append((f'v{i}', p))
    out = os.path.join(d, 'reel.wav'); rows, total, idx = build(out, vs, 0.3)
    got = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout)
    want = 1.0 + 1.5 + 2.0 + 2 * 0.3
    ok = abs(got - want) < 0.05 and len(rows) == 3 and rows[2][2] > rows[1][2] > rows[0][2] == 0.0 and os.path.exists(idx)
    print(f'SELFTEST {"PASS" if ok else "FAIL"}: reel {got:.2f} s (want {want:.2f}), {len(rows)} rows, index {os.path.basename(idx)}')
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('variants', nargs='*', help='name=path, in the order the operator will hear them')
    ap.add_argument('--out'); ap.add_argument('--gap', type=float, default=0.3); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: selftest()
    if not a.out or not a.variants: ap.error('--out and at least one name=path are required')
    vs = [(v.split('=', 1)[0], v.split('=', 1)[1]) for v in a.variants if '=' in v]
    if len(vs) != len(a.variants): ap.error('every variant is name=path')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    rows, total, idx = build(a.out, vs, a.gap)
    for n, name, start, d in rows: print(f'{n:2d}  {name:<24s} at {start:6.2f} s  ({d:.2f} s)')
    print(f'reel {a.out} ({total:.2f} s) · index {idx} · the pick goes into the EDL by NAME')


if __name__ == '__main__':
    main()
