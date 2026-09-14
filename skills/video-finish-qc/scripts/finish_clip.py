#!/usr/bin/env python3
"""finish_clip.py — a single-clip finish (a standalone asset, an alternate, a section excerpt — NOT the spot): a pre-graded
hero clip (carries head handles) + the take's own native audio → a 1080×1920 H.264 deliverable, mirroring the spot's deliver
stage: lanczos downscale, libx264 slow CRF 17 tune film, AAC 192k, faststart, TWO-PASS loudnorm (measure, then linear with
the measured values) to the given I/TP/LRA, aresample 48k. A fresh filename per render — an existing output is refused.

  finish_clip.py --root <project> --hero edit/hero/<clip>__<look>.mov --take takes/<take>.mp4 --in <take s> --out <take s>
                 --handle <head handle s inside the hero> --name <deliver basename> [--vol 1.0] [--fade-in 0] [--fade-out 0.2]
                 [--I -14 --TP -1 --LRA 9] [--match-tp <dBTP>] [--canvas 1080x1920]
--match-tp: a hit-and-silence clip has no meaningful programme loudness — match its true peak to the same beat in the
delivered spot with a plain gain, no loudnorm.
"""
import argparse, json, os, re, subprocess


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--hero', required=True); ap.add_argument('--take', required=True)
    ap.add_argument('--in', dest='tin', type=float, required=True); ap.add_argument('--out', dest='tout', type=float, required=True); ap.add_argument('--handle', type=float, default=0.0)
    ap.add_argument('--name', required=True); ap.add_argument('--vol', type=float, default=1.0); ap.add_argument('--fade-in', type=float, default=0.0); ap.add_argument('--fade-out', type=float, default=0.2)
    ap.add_argument('--I', type=float, default=-14); ap.add_argument('--TP', type=float, default=-1); ap.add_argument('--LRA', type=float, default=9); ap.add_argument('--match-tp', type=float)
    ap.add_argument('--canvas', default='1080x1920')
    a = ap.parse_args(); os.chdir(a.root); DUR = a.tout - a.tin; DELIV = f'deliver/{a.name}.mp4'; os.makedirs('deliver', exist_ok=True)
    assert DUR > 0 and a.handle >= 0 and not os.path.exists(DELIV), f'bad range or {DELIV} exists (fresh filename per render)'
    W, H = a.canvas.lower().split('x')

    def run(cmd): print('+', ' '.join(c if ' ' not in c else repr(c) for c in cmd)[:400]); subprocess.run(cmd, check=True)

    achain = f"aformat=sample_rates=48000:channel_layouts=stereo,volume={a.vol}"
    if a.fade_in > 0: achain += f",afade=t=in:st=0:d={a.fade_in}"
    if a.fade_out > 0: achain += f",afade=t=out:st={max(0, DUR - a.fade_out):.3f}:d={a.fade_out}"
    if a.match_tp is not None:
        meas = subprocess.run(['ffmpeg', '-v', 'info', '-ss', f'{a.tin:.4f}', '-t', f'{DUR:.4f}', '-i', a.take, '-af', achain + ',ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
        src = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', meas)[-1]); gain = a.match_tp - src
        print(f'match-tp: source true peak {src} dBTP -> target {a.match_tp} dBTP, gain {gain:+.2f} dB'); af = achain + f",volume={gain:.3f}dB,aresample=48000"
    else:
        meas = subprocess.run(['ffmpeg', '-v', 'info', '-ss', f'{a.tin:.4f}', '-t', f'{DUR:.4f}', '-i', a.take, '-af', achain + f",loudnorm=I={a.I}:TP={a.TP}:LRA={a.LRA}:print_format=json", '-f', 'null', '-'], capture_output=True, text=True).stderr
        m = json.loads(meas[meas.rfind('{'):meas.rfind('}') + 1]); print('loudnorm pass 1:', {k: m[k] for k in ('input_i', 'input_tp', 'input_lra')})
        af = achain + f",loudnorm=I={a.I}:TP={a.TP}:LRA={a.LRA}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=summary,aresample=48000"
    run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a.handle:.4f}', '-t', f'{DUR:.4f}', '-i', a.hero, '-ss', f'{a.tin:.4f}', '-t', f'{DUR:.4f}', '-i', a.take,
         '-map', '0:v:0', '-map', '1:a:0', '-dn', '-vf', f'scale={W}:{H}:flags=lanczos,format=yuv420p', '-af', af, '-ar', '48000', '-shortest',
         '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-tune', 'film', '-profile:v', 'high', '-level', '4.1', '-g', '48',
         '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-write_tmcd', '0', DELIV])   # -dn / -write_tmcd 0: the mov's timecode track would be re-muxed as a data track
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,width,height,pix_fmt,r_frame_rate,sample_rate', '-show_entries', 'format=duration,size', '-of', 'default=nw=1', DELIV], capture_output=True, text=True).stdout
    e = subprocess.run(['ffmpeg', '-v', 'info', '-i', DELIV, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    il = re.findall(r'I:\s+(-?[\d.]+) LUFS', e); tp = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', e)
    print(p.strip()); print('ebur128 integrated', il[-1] if il else '?', 'LUFS  true peak', tp[-1] if tp else '?', 'dBTP'); print('WROTE', DELIV)


if __name__ == '__main__':
    main()
