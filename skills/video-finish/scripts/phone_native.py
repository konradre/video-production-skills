#!/usr/bin/env python3
"""phone_native.py — the phone-native temporal layer and encode (`video-finish` § 5, the ugc-phone tier).

Runs AFTER the neutral grade and the downscale, at DELIVERY resolution, and inverts two film rules on purpose: the noise
is fine and per-pixel (a phone sensor's, not film grain) and the encode is the phone-class H.264 that flattens it into
the block statistics real phone footage shows. The dose is decided by MEASUREMENT, never by taste: probe the project's
real phone clips, probe this output, move the dose until the output sits inside the real band
(`video-finish-qc/scripts/phone_texture_probe.py`). A 720p generator take can read MORE fine texture than a phone clip
that arrived through a platform re-encode (measured 2026-09-16), so the layer carries a DENOISE arm beside the noise arm.

  phone_native.py --in <clip> --out <mp4> [--canvas 1080x1920] [--noise 6] [--denoise 0] [--drift 0.04] [--wb 150]
                  [--period 3.0] [--shake 2] [--cuts 3.2,7.8] [--ae-step 0.06] [--bitrate 12M] [--audio copy|phone|none]
                  [--seed 7] [--dry-run] [--probe] [--ref <real phone clip> …]
  phone_native.py --selftest      # a flat synthetic clip through two doses: the probe must read the higher dose higher

  --noise    ffmpeg `noise` strength (temporal + uniform), 0 = off — the probe reads the RESULT after the encode
  --denoise  hqdn3d luma-spatial strength, 0 = off — for a source that over-textures against the real band
  --drift    slow exposure drift, ± fraction of full scale (eq brightness), a sinusoid of --period seconds
  --wb       slow white-balance drift, ± kelvin around 6500, STEPPED every 0.5 s (a phone's AWB updates in steps)
  --shake    handheld micro-shake, ± px at delivery resolution (the frame is scaled 2× the value larger, then a crop wanders)
  --cuts     timeline seconds where an auto-exposure step lands (a cut in the edit); --ae-step its size, decaying over ~0.3 s
  --bitrate  the phone-class H.264 target: closed GOP, BT.709 tags, faststart, 4:2:0; the encode is part of the look
Every dial defaults to the tier's starting values; every render prints the filtergraph it ran. The look's colour lives in
the cube applied BEFORE this (`ugc-phone_33.cube`, near-identity); this script never grades.
"""
import argparse, json, math, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.normpath(os.path.join(HERE, '..', '..', 'video-finish-qc', 'scripts', 'phone_texture_probe.py'))


def probe_dims(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height,r_frame_rate:format=duration',
                        '-of', 'json', path], capture_output=True, text=True)
    js = json.loads(p.stdout or '{}')
    v = next((s for s in js.get('streams', []) if s.get('codec_type') == 'video'), {})
    has_audio = any(s.get('codec_type') == 'audio' for s in js.get('streams', []))
    return int(v.get('width', 0) or 0), int(v.get('height', 0) or 0), float((js.get('format') or {}).get('duration', 0) or 0), has_audio


def build(a, W, H, dur, cmdfile):
    """The filtergraph, in the tier's order: scale → denoise → WB drift → exposure drift + AE steps → shake → noise."""
    P = int(round(a.shake))
    chain = []
    if P > 0:
        Wp = W + 2 * P
        Hp = int(math.ceil(Wp * H / W))
        Hp += Hp % 2
        Hp = max(Hp, H + 2 * P)
        chain.append(f'scale={Wp}:{Hp}:flags=lanczos')
    else:
        chain.append(f'scale={W}:{H}:flags=lanczos')
    if a.denoise > 0:
        d = a.denoise
        chain.append(f'hqdn3d={d:g}:{d * 0.75:g}:{d * 1.5:g}:{d * 1.125:g}')
    if a.wb > 0:
        # stepped AWB: a new kelvin every 0.5 s along a slow sinusoid, sent to colortemperature by sendcmd
        lines = []
        t = 0.0
        while t < dur + 0.5:
            k = 6500 + a.wb * math.sin(2 * math.pi * t / (a.period * 1.7) + a.seed * 0.37)
            lines.append(f'{t:.2f} colortemperature temperature {k:.0f};')
            t += 0.5
        with open(cmdfile, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        chain.append(f"sendcmd=f='{cmdfile}'")
        chain.append('colortemperature=temperature=6500:mix=1')
    ph = a.seed * 0.61
    terms = [f'{a.drift:g}*sin(2*PI*t/{a.period:g}+{ph:.3f})'] if a.drift > 0 else []
    for i, c in enumerate(a.cut_list):
        sign = '+' if i % 2 == 0 else '-'
        terms.append(f'{sign}{a.ae_step:g}*gte(t,{c:g})*exp(-(t-{c:g})/0.3)')
    if terms:
        chain.append("eq=brightness='" + ''.join(terms) + "':eval=frame")
    if P > 0:
        chain.append(f"crop={W}:{H}:x='{P}+{P * 0.7:g}*sin(t*1.7+{ph:.2f})+{P * 0.3:g}*sin(t*4.3)':"
                     f"y='{P}+{P * 0.7:g}*cos(t*1.3+{ph:.2f})+{P * 0.3:g}*cos(t*3.1)'")
    if a.noise > 0:
        chain.append(f'noise=alls={a.noise:g}:allf=t+u:all_seed={a.seed}')
    chain.append('format=yuv420p')
    return ','.join(chain)


def encode_args(a, has_audio):
    br = a.bitrate.upper()
    n = float(br[:-1]) if br.endswith('M') else float(br) / 1e6
    args = ['-c:v', 'libx264', '-preset', 'medium', '-profile:v', 'high', '-level', '4.1', '-pix_fmt', 'yuv420p',
            '-b:v', f'{n:g}M', '-maxrate', f'{n * 1.15:g}M', '-bufsize', f'{n * 2:g}M',
            '-g', '48', '-keyint_min', '48', '-sc_threshold', '0', '-flags', '+cgop', '-x264-params', 'open-gop=0',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart']
    if a.audio == 'none' or not has_audio:
        args += ['-an']
    elif a.audio == 'copy':
        args += ['-c:a', 'copy']
    else:   # phone: a phone-mic band and a light auto-gain feel; the loudness pass stays spot-audio-assembly's
        args += ['-af', 'highpass=f=90,lowpass=f=7500,acompressor=threshold=-24dB:ratio=2.5:attack=5:release=120:makeup=2',
                 '-c:a', 'aac', '-b:a', '128k', '-ar', '48000']
    return args


def render(a):
    W, H = (int(x) for x in a.canvas.lower().split('x'))
    iw, ih, dur, has_audio = probe_dims(a.inp)
    if not iw or dur <= 0:
        sys.exit(f'PHONE-NATIVE FAIL — cannot probe {a.inp}')
    cmdfile = a.out + '.wbcmds.txt'
    vf = build(a, W, H, dur, cmdfile)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', a.inp, '-vf', vf] + encode_args(a, has_audio) + [a.out]
    print('filtergraph: ' + vf)
    if a.dry_run:
        print('ffmpeg: ' + ' '.join(cmd))
        if os.path.exists(cmdfile):
            os.remove(cmdfile)
        return
    r = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(cmdfile):
        os.remove(cmdfile)
    if r.returncode != 0 or not os.path.exists(a.out):
        sys.exit('PHONE-NATIVE FAIL — ffmpeg: ' + r.stderr.strip()[-800:])
    ow, oh, odur, _ = probe_dims(a.out)
    print(f'wrote {a.out}: {ow}x{oh} {odur:.2f} s ({os.path.getsize(a.out) / 1e6:.1f} MB)')
    if a.probe or a.ref:
        rows = probe_rows([a.out] + a.ref)
        for r_ in rows:
            print(f"  {os.path.basename(r_['file'])[-48:]:>48} | dead-flat {r_['dead_flat_pct']:5.1f} % | floor {r_['noise_floor']:5.2f} | median sd {r_['median_block_sd']:5.2f}")
        if a.ref and len(rows) == 1 + len(a.ref):
            # the real band is the RANGE over every sampled frame of every reference, never the mean of means:
            # one real clip read 6 % dead-flat on a textured frame and 34 % on a flat wall
            out, refs = rows[0], rows[1:]
            for k in ('dead_flat_pct', 'noise_floor', 'median_block_sd'):
                lo, hi = min(r_[k + '_min'] for r_ in refs), max(r_[k + '_max'] for r_ in refs)
                v = out[k]
                verdict = 'IN BAND' if lo <= v <= hi else ('BELOW — less texture than every reference frame: lower --denoise / raise --noise or --bitrate' if v < lo else 'ABOVE — more texture than every reference frame: raise --denoise / lower --noise or --bitrate')
                print(f'  {k}: output {v} (frames {out[k + "_min"]}–{out[k + "_max"]}) vs real band [{lo}, {hi}] → {verdict}')
    print('PHONE-NATIVE-END')


def probe_rows(files):
    r = subprocess.run([sys.executable, PROBE, '--json'] + files, capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        sys.exit('PHONE-NATIVE FAIL — the probe did not answer: ' + (r.stderr or r.stdout)[-400:])


def selftest():
    """A flat grey synthetic clip through two noise doses (no drift, no shake, no WB): the probe must read the higher dose
    as a higher noise floor and a lower dead-flat share than the flat source; a dry run must print a filtergraph."""
    d = tempfile.mkdtemp(prefix='phone-native-selftest-')
    src = os.path.join(d, 'flat.mp4')
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=0x808080:s=540x960:d=2:r=24',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', src], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit('selftest FAIL — could not write the flat source: ' + r.stderr[-300:])
    outs = []
    for dose in (4, 14):
        out = os.path.join(d, f'dose{dose}.mp4')
        args = argparse.Namespace(inp=src, out=out, canvas='540x960', noise=dose, denoise=0, drift=0.0, wb=0, period=3.0,
                                  shake=0, cut_list=[], ae_step=0.0, bitrate='6M', audio='none', seed=3, dry_run=False, probe=False, ref=[])
        W, H, dur = 540, 960, 2.0
        vf = build(args, W, H, dur, out + '.wbcmds.txt')
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', vf] + encode_args(args, False) + [out], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit('selftest FAIL — render: ' + r.stderr[-300:])
        outs.append(out)
    rows = probe_rows([src] + outs)
    flat, lo, hi = rows
    ok = lo['noise_floor'] > 0 and hi['noise_floor'] > lo['noise_floor'] and hi['dead_flat_pct'] < flat['dead_flat_pct'] and hi['median_block_sd'] > lo['median_block_sd']
    for r_ in rows:
        print(f"selftest {os.path.basename(r_['file']):>12}: dead-flat {r_['dead_flat_pct']:5.1f} % · floor {r_['noise_floor']:5.2f} · median sd {r_['median_block_sd']:5.2f}")
    dry = argparse.Namespace(inp=src, out=os.path.join(d, 'dry.mp4'), canvas='540x960', noise=6, denoise=1.5, drift=0.04, wb=150, period=3.0,
                             shake=2, cut_list=[0.8], ae_step=0.06, bitrate='6M', audio='none', seed=7, dry_run=True, probe=False, ref=[])
    vf = build(dry, 540, 960, 2.0, dry.out + '.wbcmds.txt')
    ok &= all(k in vf for k in ('hqdn3d', 'sendcmd', 'colortemperature', 'eq=brightness', 'crop=540:960', 'noise=alls=6'))
    if os.path.exists(dry.out + '.wbcmds.txt'):
        os.remove(dry.out + '.wbcmds.txt')
    print('selftest full filtergraph: ' + vf[:160] + ' …')
    print('PHONE-NATIVE SELFTEST ' + ('PASS' if ok else 'FAIL'))
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--in', dest='inp'); ap.add_argument('--out')
    ap.add_argument('--canvas', default='1080x1920')
    ap.add_argument('--noise', type=float, default=6.0); ap.add_argument('--denoise', type=float, default=0.0)
    ap.add_argument('--drift', type=float, default=0.04); ap.add_argument('--wb', type=float, default=150.0)
    ap.add_argument('--period', type=float, default=3.0); ap.add_argument('--shake', type=float, default=2.0)
    ap.add_argument('--cuts', default='', help='timeline seconds of the edit\'s cuts, comma-separated'); ap.add_argument('--ae-step', type=float, default=0.06)
    ap.add_argument('--bitrate', default='12M'); ap.add_argument('--audio', choices=['copy', 'phone', 'none'], default='copy')
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--probe', action='store_true')
    ap.add_argument('--ref', nargs='*', default=[], help='real phone clips whose band the output must land in (runs the probe)')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        selftest()
    if not a.inp or not a.out:
        ap.error('--in and --out are required (or --selftest)')
    a.cut_list = [float(x) for x in a.cuts.split(',') if x.strip()]
    render(a)


if __name__ == '__main__':
    main()
