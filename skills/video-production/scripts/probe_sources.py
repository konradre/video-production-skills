#!/usr/bin/env python3
"""probe_sources.py — the DISPLAY shape of every source, before any crop, layout or raster math.

A container stores pixels; a display shape is what the viewer sees. The two differ whenever the stream carries a
sample aspect ratio (anamorphic storage — vertical phone video re-encoded into a 1920×1080 container with SAR 81:256
is one common shape) or a rotation tag (a phone clip stored landscape with `rotate=90`). A probe that records only
width × height reads such a clip as square-pixel landscape, and every crop built on that reading stretches the
subject; on one documentary spot 11 of 17 client clips were stored that way and every render stretched them 3.16×
wide before anyone compared a delivered frame with its source (2026-09-15).

For each file: storage w×h, SAR, DAR, rotation, the DISPLAY w×h (storage × SAR, rotated), fps, codec, pixel format,
bit depth, duration, audio channels and rate. A source whose display shape differs from its storage shape is flagged
NORMALISE — scale it to its display shape (`scale=iw*sar:ih,setsar=1`, then the rotation) BEFORE any crop, and write
the display shape, not the storage shape, into the shot list's header and the EDL's source notes.

  probe_sources.py <file>… [--json <out.json>]        # a table on stdout; the same rows as JSON when asked
  probe_sources.py --selftest                           # synthesises an anamorphic clip and a rotated clip; both must flag

Exit 0 on a clean set, 2 when any source needs normalising (so a builder can gate on it), 1 on a probe error.
"""
import argparse, json, os, subprocess, sys, tempfile
from fractions import Fraction


def _frac(s, default=Fraction(1)):
    try:
        a, b = s.replace('/', ':').split(':'); a, b = int(a), int(b)
        return Fraction(a, b) if a > 0 and b > 0 else default
    except Exception:
        return default


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path], capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(r.stderr.strip() or f'ffprobe failed on {path}')
    d = json.loads(r.stdout)
    v = next((s for s in d.get('streams', []) if s.get('codec_type') == 'video'), None)
    a = next((s for s in d.get('streams', []) if s.get('codec_type') == 'audio'), None)
    if v is None: raise RuntimeError(f'no video stream in {path}')
    w, h = int(v.get('width', 0)), int(v.get('height', 0))
    sar = _frac(str(v.get('sample_aspect_ratio', '1:1')))
    dar = _frac(str(v.get('display_aspect_ratio', '')), default=Fraction(w, h) * sar if h else Fraction(1))
    rot = 0
    for sd in v.get('side_data_list', []) or []:
        if 'rotation' in sd:
            try: rot = int(float(sd['rotation'])) % 360
            except Exception: pass
    if not rot:
        try: rot = int(float((v.get('tags') or {}).get('rotate', 0))) % 360
        except Exception: rot = 0
    dw, dh = int(round(w * sar)), h                      # storage × SAR = square-pixel display
    if rot in (90, 270): dw, dh = dh, dw
    fps = v.get('r_frame_rate', '0/1'); avg = v.get('avg_frame_rate', '0/1')
    try: fpsf = float(Fraction(fps))
    except Exception: fpsf = 0.0
    bits = v.get('bits_per_raw_sample') or ('10' if '10' in str(v.get('pix_fmt', '')) else '8')
    row = {
        'file': path, 'storage': f'{w}x{h}', 'sar': f'{sar.numerator}:{sar.denominator}', 'dar': f'{dar.numerator}:{dar.denominator}',
        'rotation': rot, 'display': f'{dw}x{dh}', 'display_aspect': round(dw / dh, 4) if dh else None,
        'fps': round(fpsf, 3), 'cfr': fps == avg, 'codec': v.get('codec_name'), 'pix_fmt': v.get('pix_fmt'), 'bit_depth': int(bits),
        'duration_s': round(float(d.get('format', {}).get('duration', 0) or 0), 3),
        'audio': (f"{a.get('channels')}ch {a.get('sample_rate')} Hz {a.get('codec_name')}" if a else 'none'),
        'normalise': (sar != 1) or (rot != 0),
    }
    return row


def render(rows):
    cols = ['file', 'storage', 'sar', 'rotation', 'display', 'fps', 'codec', 'pix_fmt', 'bit_depth', 'duration_s', 'audio', 'normalise']
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    for r in rows:
        out.append('| ' + ' | '.join(('NORMALISE' if r['normalise'] else 'ok') if c == 'normalise' else (os.path.basename(str(r[c])) if c == 'file' else str(r[c])) for c in cols) + ' |')
    return '\n'.join(out)


def selftest():
    with tempfile.TemporaryDirectory() as td:
        ana = os.path.join(td, 'anamorphic.mp4'); rot = os.path.join(td, 'rotated.mp4'); sq = os.path.join(td, 'square.mp4')
        base = ['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=640x360:rate=24', '-t', '0.5', '-pix_fmt', 'yuv420p']
        subprocess.run(base + ['-vf', 'setsar=81/256', ana], check=True)
        subprocess.run(base + [sq], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-display_rotation', '90', '-i', sq, '-c', 'copy', rot], check=True)   # a display-matrix rotation, as phones write
        A, R, S = probe(ana), probe(rot), probe(sq)
        sa = A['sar'].split(':'); dw = int(A['display'].split('x')[0])
        assert A['normalise'] and abs(int(sa[0]) / int(sa[1]) - 81 / 256) < 0.002 and abs(dw - 640 * 81 / 256) <= 1, A   # the encoder may store a near-equal SAR
        assert R['normalise'] and R['rotation'] in (90, 270) and R['display'] == '360x640', R
        assert not S['normalise'] and S['display'] == '640x360', S
        print(render([A, R, S])); print('SELFTEST PASS — the anamorphic and the rotated clip flag NORMALISE; the square-pixel clip does not')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='*'); ap.add_argument('--json'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: return selftest()
    if not a.files: ap.error('name at least one source file, or --selftest')
    rows = []
    for f in a.files:
        try: rows.append(probe(f))
        except Exception as ex: print(f'ERROR {f}: {ex}', file=sys.stderr); sys.exit(1)
    print(render(rows))
    if a.json: json.dump(rows, open(a.json, 'w'), indent=1); print(f'wrote {a.json}')
    n = [r for r in rows if r['normalise']]
    print(f"{len(n)} of {len(rows)} source(s) need NORMALISE to their display shape before any crop" if n else f'all {len(rows)} source(s) are square-pixel and unrotated')
    sys.exit(2 if n else 0)


if __name__ == '__main__':
    main()
