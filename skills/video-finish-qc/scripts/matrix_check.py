#!/usr/bin/env python3
"""matrix_check.py — does a render path convert RGB → YUV with the matrix its file is tagged with?

ffmpeg converts RGB → YUV with BT.601 unless a filter names the matrix, and our files are tagged bt709. A frame born RGB
(a HyperFrames render, a PNG layer, a caption card, a shot graded through a cube) then plays back with its saturated
colours moved — pure green read back (0,215,0), pink #FF4FA3 read (255,99,163) — while grey, black and white stay exact,
so no grey or white-text check ever sees it (measured 2026-10-21 on ffmpeg 6.1.1, up to 40 levels).

The card is 16 flat patches: primaries, secondaries, white, black, mid grey, a skin tone, and six mid-saturated colours.
`measure` decodes ONE frame the way a player does — by the file's own colour tag — and compares each patch's mean to
the card's source RGB. Run the card through the path under test (render_hyper.sh, a finish with the card as a post_layer,
a caption, a cube), then measure what that path delivered.

  matrix_check.py card <out.png> [--size 1920x1080]                       # the 16-patch card as an RGB PNG
  matrix_check.py card --html <composition dir> [--size 1920x1080]        # the same card as a HyperFrames index.html
  matrix_check.py measure <video|png> [--at 1.0] [--as tag|bt709|bt601] [--max 6] [--size 1920x1080] [--json]
                                                                           # exit 1 over --max, 2 when it cannot decode
  matrix_check.py --selftest                                               # a 709 encode passes; ffmpeg's default FAILS;
                                                                           # finish_spot's three RGB steps pass
  matrix_check.py --finish-e2e [--keep <dir>]                              # the REAL finish_spot.py, one event per colour
                                                                           # branch, overlays over grey; exit 1 on any FAIL

`--as tag` (the default) reads the stream's `color_space`: bt709 → BT.709; smpte170m / bt470bg → BT.601; anything
else exits 2 rather than guess. A patch is read on its inner half, away from chroma-subsampled edges; a correct 8-bit
4:2:0 encode reads within 3.
"""
import argparse, importlib.util, json, os, struct, subprocess, sys, tempfile, zlib

COLS = ["FF0000", "00FF00", "0000FF", "FFFF00", "00FFFF", "FF00FF", "FFFFFF", "000000",
        "808080", "C89678", "BF0000", "FF4FA3", "B42828", "28A03C", "283CB4", "7F3FBF"]
SRC = [tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) for c in COLS]
TAGS = {'bt709': 'bt709', 'smpte170m': 'bt601', 'bt470bg': 'bt601'}


def size(s):
    w, h = (int(v) for v in s.lower().split('x')); return w, h


def cell(i, W, H):
    return (i % 4) * W // 4, (i // 4) * H // 4, W // 4, H // 4


def card_png(path, W, H, gutter=0):
    """the card as an RGB PNG; with gutter > 0 an RGBA PNG whose cells are opaque and whose gutters are transparent"""
    rows = []; cw, ch = W // 4, H // 4
    for y in range(H):
        r = bytearray(b'\x00')
        for x in range(W):
            px = bytes(SRC[(y * 4 // H) * 4 + x * 4 // W])
            if gutter: px += b'\x00' if (x % cw < gutter or x % cw >= cw - gutter or y % ch < gutter or y % ch >= ch - gutter) else b'\xff'
            r += px
        rows.append(bytes(r))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 6 if gutter else 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(b''.join(rows), 6)) + chunk(b'IEND', b''))


def card_html(d, W, H, dur=2.0, fps=24):
    os.makedirs(d, exist_ok=True); cid = os.path.basename(os.path.abspath(d))
    cells = '\n'.join(f'  <div class="p" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:#{c}"></div>'
                      for c, (x, y, w, h) in ((c, cell(i, W, H)) for i, c in enumerate(COLS)))
    html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{cid} — matrix_check patch card</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  html, body {{ margin:0; background:#000; }}
  #root {{ position:relative; width:{W}px; height:{H}px; overflow:hidden; background:#000; }}
  .clip {{ position:absolute; inset:0; }}
  .p {{ position:absolute; }}
</style>
</head>
<body>
<div id="root" data-composition-id="{cid}" data-start="0" data-width="{W}" data-height="{H}" data-duration="{dur}" data-fps="{fps}">
<section class="clip" data-start="0" data-duration="{dur}">
{cells}
</section>
</div>
<script>
(function(){{
  var ID='{cid}', st={{t:0}};
  var tl=gsap.timeline({{paused:true}});
  tl.to(st,{{t:{dur},duration:{dur},ease:'none'}},0);   // static card: nothing moves
  window.__timelines=window.__timelines||{{}}; window.__timelines[ID]=tl; if(window.__hfForceTimelineRebind) window.__hfForceTimelineRebind();
}})();
</script>
</body>
</html>
'''
    with open(os.path.join(d, 'index.html'), 'w') as f: f.write(html)


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                        'stream=codec_name,pix_fmt,color_space,color_range,width,height', '-of', 'json', path],
                       capture_output=True, text=True)
    s = json.loads(r.stdout or '{}').get('streams') or [{}]
    return s[0]


def measure(path, at=1.0, as_='tag', W=1920, H=1080):
    st = probe(path)
    if not st.get('codec_name'): return {'ok': None, 'reason': f'cannot read a video stream in {path}'}
    rgb_src = st.get('pix_fmt', '').startswith(('rgb', 'bgr', 'gbr', 'pal')) or st.get('codec_name') == 'png'
    if rgb_src: vf, used = f'scale={W}:{H}', 'rgb (no matrix)'
    else:
        m = TAGS.get(st.get('color_space') or '') if as_ == 'tag' else as_
        if not m: return {'ok': None, 'reason': f"untagged or unknown color_space {st.get('color_space')!r}: pass --as bt709|bt601"}
        rng = 'pc' if st.get('color_range') == 'pc' else 'tv'
        vf, used = f'scale={W}:{H}:in_color_matrix={m}:in_range={rng}', f'{m} {rng} ({"tag" if as_ == "tag" else "forced"})'
    seek = [] if rgb_src else ['-ss', str(at)]
    r = subprocess.run(['ffmpeg', '-v', 'error'] + seek + ['-i', path, '-vf', vf, '-frames:v', '1', '-f', 'rawvideo',
                        '-pix_fmt', 'rgb24', '-'], capture_output=True)
    buf = r.stdout
    if len(buf) < W * H * 3: return {'ok': None, 'reason': f'decode failed: {r.stderr.decode()[-200:]}'}
    out = []
    for i in range(16):
        x0, y0, w, h = cell(i, W, H); acc = [0, 0, 0]; n = 0
        for y in range(y0 + h // 4, y0 + 3 * h // 4, 4):
            for x in range(x0 + w // 4, x0 + 3 * w // 4, 4):
                p = (y * W + x) * 3; acc[0] += buf[p]; acc[1] += buf[p + 1]; acc[2] += buf[p + 2]; n += 1
        m = tuple(round(v / n) for v in acc)
        out.append({'patch': COLS[i], 'src': SRC[i], 'read': m, 'err': max(abs(a - b) for a, b in zip(SRC[i], m))})
    worst = max(out, key=lambda p: p['err'])
    return {'ok': True, 'decoded_as': used, 'tags': st, 'max_err': worst['err'], 'worst': worst, 'patches': out}


def report(res, mx):
    if res.get('ok') is None: print('MATRIX-CHECK CANNOT', res['reason']); return 2
    for p in res['patches']:
        print(f"  #{p['patch']}  src {str(p['src']):16s} read {str(p['read']):16s} err {p['err']:3d}{'  <-' if p['err'] > mx else ''}")
    v = 'PASS' if res['max_err'] <= mx else 'FAIL'
    print(f"MATRIX-CHECK {v} max err {res['max_err']} (limit {mx}) decoded as {res['decoded_as']}; worst #{res['worst']['patch']} read {res['worst']['read']}")
    return 0 if v == 'PASS' else 1


def selftest():
    W, H = 640, 360
    spec = importlib.util.spec_from_file_location('finish_spot', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'finish_spot.py'))
    fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs); TO709 = fs.TO709
    ok = True
    with tempfile.TemporaryDirectory() as d:
        png = os.path.join(d, 'card.png'); card_png(png, W, H)
        r = measure(png, W=W, H=H); ok &= r['max_err'] == 0; print(f"selftest card png:            max err {r['max_err']} (want 0)")
        def ff(args): subprocess.run(['ffmpeg', '-v', 'error', '-y'] + args, check=True)
        tag = ['-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709']
        cases = []
        good = os.path.join(d, 'good.mp4'); ff(['-loop', '1', '-t', '1', '-r', '24', '-i', png, '-vf', f'{TO709},format=yuv420p', '-c:v', 'libx264', '-crf', '12'] + tag + [good]); cases.append(('TO709 → yuv420p', good, True))
        bad = os.path.join(d, 'bad.mp4'); ff(['-loop', '1', '-t', '1', '-r', '24', '-i', png, '-vf', 'format=yuv420p', '-c:v', 'libx264', '-crf', '12'] + tag + [bad]); cases.append(("ffmpeg's default matrix", bad, False))
        base = os.path.join(d, 'base.mov'); ff(['-f', 'lavfi', '-i', f'color=black:s={W}x{H}:r=24:d=1', '-vf', 'format=yuv422p10le', '-c:v', 'prores_ks', '-profile:v', '3'] + tag + [base])
        lay = os.path.join(d, 'layer.mov'); ff(['-i', base, '-loop', '1', '-t', '1', '-r', '24', '-i', png, '-filter_complex',
             f'[0:v]format=yuv422p10le[b0];[1:v]scale={W}:{H}:flags=lanczos,{TO709},format=yuva422p10le[ov0];[b0][ov0]overlay=eof_action=pass:format=yuv422p10[out]',
             '-map', '[out]', '-c:v', 'prores_ks', '-profile:v', '3'] + tag + [lay]); cases.append(('finish_spot post_layer', lay, True))
        cap = os.path.join(d, 'caption.mp4'); ff(['-i', base, '-loop', '1', '-t', '1', '-r', '24', '-i', png, '-filter_complex',
             f"[0:v]format=yuv420p[v0];[1:v]{TO709},format=yuva420p[c0];[v0][c0]overlay=0:0:enable='gte(t,0)*lt(t,1)'[v1]",
             '-map', '[v1]', '-c:v', 'libx264', '-crf', '12'] + tag + [cap]); cases.append(('finish_spot caption overlay', cap, True))
        cube = os.path.join(d, 'id_33.cube')
        with open(cube, 'w') as f: f.write('LUT_3D_SIZE 33\n' + ''.join(f'{r / 32:.6f} {g / 32:.6f} {b / 32:.6f}\n' for b in range(33) for g in range(33) for r in range(33)))
        lut = os.path.join(d, 'lut.mov'); ff(['-i', good, '-vf', f'format=gbrp16le,lut3d=file={cube}:interp=tetrahedral,{TO709},format=yuv422p10le',
             '-c:v', 'prores_ks', '-profile:v', '3'] + tag + [lut]); cases.append(('finish_spot look (identity cube)', lut, True))
        for name, f, want in cases:
            r = measure(f, at=0.5, W=W, H=H); got = r['max_err'] <= 6; ok &= got == want
            print(f"selftest {name:32s} max err {r['max_err']:3d} → {'PASS' if got else 'FAIL'} (want {'PASS' if want else 'FAIL'})")
    print('SELFTEST', 'OK' if ok else 'FAILED'); return 0 if ok else 1


def finish_e2e(keep=None):
    """The REAL finish_spot.py on the card, all stages. Every branch that converts colour gets its own event: a cube on a
    tagged and an untagged source; look none on a BT.709, a BT.601-tagged and an RGB (png-codec) source; an RGBA post
    layer and an RGBA caption, each over FLAT GREY so an overlay that never composited reads grey and fails; an RGB end
    card. Each row is measured on the file the finisher wrote."""
    W, H, FPS = 1280, 720, 24   # 720p: an untagged source is BT.709 by the HD rule
    here = os.path.dirname(os.path.abspath(__file__)); SK = os.path.abspath(os.path.join(here, '..', '..'))
    d = keep or tempfile.mkdtemp(prefix='matrix-e2e-'); os.makedirs(d, exist_ok=True)
    def ff(args): subprocess.run(['ffmpeg', '-v', 'error', '-y'] + args, check=True, cwd=d)
    for p in ('edit/layers/card', 'edit/captions', 'takes', 'cubes'): os.makedirs(os.path.join(d, p), exist_ok=True)
    card_png(os.path.join(d, 'card.png'), W, H); card_png(os.path.join(d, 'card-rgba.png'), W, H, gutter=12)
    tag = ['-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709']
    still = ['-loop', '1', '-t', '4', '-r', str(FPS), '-i', 'card.png', '-f', 'lavfi', '-t', '4', '-i', 'anullsrc=r=48000:cl=stereo']
    enc = ['-c:v', 'libx264', '-crf', '10', '-c:a', 'aac', '-shortest']
    ff(still + ['-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p'] + enc + tag + ['takes/tagged.mp4'])
    ff(still + ['-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p'] + enc
       + ['-bsf:v', 'h264_metadata=matrix_coefficients=2:colour_primaries=2:transfer_characteristics=2', 'takes/untagged.mp4'])
    ff(still + ['-vf', 'scale=out_color_matrix=bt601:out_range=tv,format=yuv420p'] + enc
       + ['-colorspace', 'smpte170m', '-color_primaries', 'smpte170m', '-color_trc', 'smpte170m', 'takes/bt601.mp4'])
    ff(still + ['-c:v', 'png', '-c:a', 'pcm_s16le', '-shortest', 'takes/rgb.mov'])
    ff(['-f', 'lavfi', '-t', '4', '-i', f'color=0x808080:s={W}x{H}:r={FPS}', '-f', 'lavfi', '-t', '4', '-i', 'anullsrc=r=48000:cl=stereo',
        '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p'] + enc + tag + ['takes/grey.mp4'])
    for i in range(FPS): shutil_copy(os.path.join(d, 'card-rgba.png'), os.path.join(d, f'edit/layers/card/frame_{i:06d}.png'))
    shutil_copy(os.path.join(d, 'card-rgba.png'), os.path.join(d, 'edit/captions/cap-00.png'))
    with open(os.path.join(d, 'cubes', 'idtest_33.cube'), 'w') as f:
        f.write('LUT_3D_SIZE 33\n' + ''.join(f'{r / 32:.6f} {g / 32:.6f} {b / 32:.6f}\n' for b in range(33) for g in range(33) for r in range(33)))
    plan = [('tagged', 'idtest'), ('untagged', 'idtest'), ('tagged', 'none'), ('bt601', 'none'), ('rgb', 'none'), ('grey', 'none'), ('grey', 'none')]
    ev = []
    for k, (src, look) in enumerate(plan):
        f = f'takes/{src}.mp4' if src != 'rgb' else 'takes/rgb.mov'
        ev.append({'id': f'E{k:02d}', 'take': f, 'src': f, 'in': 0.5, 'out': 2.0, 'tl': [1.5 * k, 1.5 * k + 1.5], 'handle_head': 0.5, 'look': look})
    T = 1.5 * len(plan)
    ev.append({'id': 'EC', 'role': 'endcard', 'source': 'designed', 'take': 'takes/rgb.mov', 'in': 0.0, 'out': 1.5, 'tl': [T, T + 1.5]})
    E = {'spot': 'MX', 'deliver_base': 'MX', 'runtime_s': T + 1.5, 'canvas': [W, H], 'events': ev,
         'post_layers': [{'frames': 'edit/layers/card/frame_%06d.png', 'at': 7.75}],
         'audio': {'vo': {'stem': 'edit/mix/MX-vo-stem.wav', 'peak_cap_dbfs': -1.0, 'target_lufs': -16.0}, 'sfx': {}, 'music': {},
                   'loudnorm': {'I': -16, 'TP': -1.5, 'LRA': 11}, 'captions_dir': 'edit/captions'}}
    os.makedirs(os.path.join(d, 'edit'), exist_ok=True); json.dump(E, open(os.path.join(d, 'edit', 'MX-EDL.json'), 'w'), indent=1)
    stub = os.path.join(d, 'caps.py')
    with open(stub, 'w') as f:
        f.write("import json; json.dump([{'file': 'edit/captions/cap-00.png', 'tl': [9.25, 10.25]}], open('edit/captions/manifest.json', 'w'))\n")
    r = subprocess.run([sys.executable, os.path.join(SK, 'video-finish-qc', 'scripts', 'finish_spot.py'), '--root', d, '--edl', 'edit/MX-EDL.json',
                        '--stage', 'all', '--look', 'idtest', '--cubes', os.path.join(d, 'cubes'), '--canvas', f'{W}x{H}', '--fps', str(FPS), '--no-gate',
                        '--min-free-gb', '0', '--stem-builder', os.path.join(SK, 'spot-audio-assembly', 'scripts', 'build_vo_stem.py'),
                        '--captions-builder', stub], capture_output=True, text=True)
    if r.returncode != 0 or 'FINISH-END' not in r.stdout:
        print('FINISH-E2E CANNOT: finish_spot.py failed\n' + (r.stdout + r.stderr)[-1200:]); return 2
    M, Mm, Dv = 'edit/mezz/MX-footage-graded.mov', f'edit/mezz/MX-master-{W}x{H}.mov', 'deliver/MX-v1.mp4'
    rows = [('cube, tagged bt709 source', M, 0.75), ('cube, untagged HD source', M, 2.25), ('look none, bt709 source', M, 3.75),
            ('look none, bt601-tagged source', M, 5.25), ('look none, RGB (png) source', M, 6.75),
            ('RGBA post_layer over grey', Mm, 8.25), ('RGB end card', Mm, T + 0.75),
            ('RGBA caption over grey, delivered', Dv, 9.75), ('cube path, delivered', Dv, 0.75)]
    ok = True
    for name, f, at in rows:
        res = measure(os.path.join(d, f), at, 'tag', W, H)
        if res.get('ok') is None: print(f'e2e {name:34s} CANNOT {res["reason"]}'); ok = False; continue
        good = res['max_err'] <= 6; ok &= good
        print(f"e2e {name:34s} max err {res['max_err']:3d} {'PASS' if good else 'FAIL'} ({os.path.basename(f)} @ {at}s, as {res['decoded_as']})")
    print('FINISH-E2E', 'OK' if ok else 'FAILED', '' if keep else '(scratch removed)')
    if not keep: shutil_rmtree(d)
    return 0 if ok else 1


def shutil_copy(a, b):
    import shutil; shutil.copyfile(a, b)


def shutil_rmtree(d):
    import shutil; shutil.rmtree(d, ignore_errors=True)


def main():
    if '--selftest' in sys.argv: sys.exit(selftest())
    if '--finish-e2e' in sys.argv:
        k = sys.argv[sys.argv.index('--keep') + 1] if '--keep' in sys.argv else None; sys.exit(finish_e2e(k))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    c = sp.add_parser('card'); c.add_argument('out', nargs='?'); c.add_argument('--html'); c.add_argument('--size', default='1920x1080')
    m = sp.add_parser('measure'); m.add_argument('file'); m.add_argument('--at', type=float, default=1.0)
    m.add_argument('--as', dest='as_', default='tag', choices=['tag', 'bt709', 'bt601']); m.add_argument('--max', type=int, default=6)
    m.add_argument('--size', default='1920x1080'); m.add_argument('--json', action='store_true')
    a = ap.parse_args(); W, H = size(a.size)
    if a.cmd == 'card':
        if not (a.out or a.html): ap.error('card needs <out.png> or --html <dir>')
        if a.out: card_png(a.out, W, H); print('card', a.out, f'{W}x{H}')
        if a.html: card_html(a.html, W, H); print('card', os.path.join(a.html, 'index.html'), f'{W}x{H}')
        return
    res = measure(a.file, a.at, a.as_, W, H)
    if a.json: print(json.dumps(res)); sys.exit(2 if res.get('ok') is None else 0 if res['max_err'] <= a.max else 1)
    sys.exit(report(res, a.max))


if __name__ == '__main__':
    main()
