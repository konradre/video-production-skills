#!/usr/bin/env python3
"""finish_clip.py — a single-clip finish (a standalone asset, an alternate, a section excerpt — NOT the spot): a pre-graded
hero clip (carries head handles) + the take's own native audio → a 1080×1920 H.264 deliverable, mirroring the spot's deliver
stage: lanczos downscale, libx264 slow CRF 17 tune film, AAC 192k, faststart, and the spot's loudness method — ONE measured
static gain to --I, then peak limiting at --TP oversampled (aresample 192k → alimiter → 48k → alimiter, latency compensated).
Until 2026-09-29 this was a two-pass loudnorm, whose linear=true falls back to DYNAMIC on peaky audio: lowering its TP target
RAISED a peaky take's delivered peak (-0.9 → -0.6 dBTP), so no TP setting could hold the ceiling. --LRA is accepted and unused.
A fresh filename per render — an existing output is refused.

  finish_clip.py --root <project> --hero edit/hero/<clip>__<look>.mov --take takes/<take>.mp4 --in <take s> --out <take s>
                 --handle <head handle s inside the hero> --name <deliver basename> [--vol 1.0] [--fade-in 0] [--fade-out 0.2]
                 [--I -14 --TP -2 --LRA 9] [--match-tp <dBTP>] [--canvas 1080x1920]
--match-tp: a hit-and-silence clip has no meaningful programme loudness — match its true peak to the same beat in the
delivered spot with a plain gain, no loudnorm.
After the encode, two AAC checks on the DELIVERED file; either FAIL exits 1 and keeps the file: the decoded true peak
against --tp-ceiling (default -1 dBTP; loudnorm's TP acts BEFORE the encode, and the AAC encode adds inter-sample peaks on
top), and the AAC packet clock (aac_packet_clock.py; loudnorm's flush of a partial block leaves one overlong packet).
The audio clock is rebuilt from the samples (bridgeclip's PAIR): source gaps become silence on the input
(aresample async, first_pts=0), and the timestamps are re-derived after the last loudness/resample filter
(asettb=1/48000,asetpts=N). The reset alone collapses a REAL gap in a take — a beep behind a 200 ms gap landed 200 ms
early; with the pair it landed on time (measured 2026-09-29). --TP defaults to -2: -1 is the platform ceiling itself
and left no headroom for the AAC overshoot (a peaky take delivered +0.10 dBTP at -1).
A true peak over the ceiling RETRIES ONCE: the attempt is kept as <name>__tp<TP>.mp4 and the clip is re-encoded with the
limiter ceiling lowered by the measured overshoot plus 0.3 dB (--match-tp lowers the same way); a second overshoot exits 1.
--no-retry keeps the single attempt.
"""
import argparse, json, os, re, subprocess, sys


HERE = os.path.dirname(os.path.abspath(__file__))   # resolved before main() changes directory


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--hero', required=True); ap.add_argument('--take', required=True)
    ap.add_argument('--in', dest='tin', type=float, required=True); ap.add_argument('--out', dest='tout', type=float, required=True); ap.add_argument('--handle', type=float, default=0.0)
    ap.add_argument('--name', required=True); ap.add_argument('--vol', type=float, default=1.0); ap.add_argument('--fade-in', type=float, default=0.0); ap.add_argument('--fade-out', type=float, default=0.2)
    ap.add_argument('--I', type=float, default=-14); ap.add_argument('--TP', type=float, default=-2); ap.add_argument('--LRA', type=float, default=9); ap.add_argument('--match-tp', type=float)
    ap.add_argument('--canvas', default='1080x1920'); ap.add_argument('--tp-ceiling', type=float, default=-1.0)
    ap.add_argument('--no-retry', action='store_true', help='keep the single attempt when the true peak lands over the ceiling')
    a = ap.parse_args(); os.chdir(a.root); DUR = a.tout - a.tin; DELIV = f'deliver/{a.name}.mp4'; os.makedirs('deliver', exist_ok=True)
    assert DUR > 0 and a.handle >= 0 and not os.path.exists(DELIV), f'bad range or {DELIV} exists (fresh filename per render)'
    W, H = a.canvas.lower().split('x')

    def run(cmd): print('+', ' '.join(c if ' ' not in c else repr(c) for c in cmd)[:400]); subprocess.run(cmd, check=True)

    achain = f"aresample=48000:async=1:first_pts=0:min_hard_comp=0.001,aformat=sample_rates=48000:channel_layouts=stereo,volume={a.vol}"   # source gaps -> silence
    if a.fade_in > 0: achain += f",afade=t=in:st=0:d={a.fade_in}"
    if a.fade_out > 0: achain += f",afade=t=out:st={max(0, DUR - a.fade_out):.3f}:d={a.fade_out}"

    def render(tp, match_tp):
        if match_tp is not None:
            meas = subprocess.run(['ffmpeg', '-v', 'info', '-ss', f'{a.tin:.4f}', '-t', f'{DUR:.4f}', '-i', a.take, '-af', achain + ',ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
            src = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', meas)[-1]); gain = match_tp - src
            print(f'match-tp: source true peak {src} dBTP -> target {match_tp} dBTP, gain {gain:+.2f} dB'); af = achain + f",volume={gain:.3f}dB,aresample=48000,asettb=1/48000,asetpts=N"
        else:   # the spot's deliver chain: one static gain, peaks limited at 192 kHz (where inter-sample peaks show), then at 48 kHz
            meas = subprocess.run(['ffmpeg', '-v', 'info', '-ss', f'{a.tin:.4f}', '-t', f'{DUR:.4f}', '-i', a.take, '-af', achain + ',ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
            mi = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', meas)[-1]); mtp_ = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', meas)[-1]); g = a.I - mi
            print(f"measured I {mi} LUFS / TP {mtp_} dBTP -> static gain {g:+.2f} dB -> " + (f"peak limiting {mtp_ + g - tp:.2f} dB to hold TP {tp:g}" if mtp_ + g > tp else f"no limiting, {tp - mtp_ - g:.2f} dB under TP {tp:g}"))
            lim = f"alimiter=limit={10 ** (tp / 20):.4f}:attack=5:release=60:level=false:latency=1"
            af = achain + f",volume={g:.3f}dB,aresample=192000,{lim},aresample=48000,{lim},asettb=1/48000,asetpts=N"   # the clock rebuilt from the samples after the last resample
        run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a.handle:.4f}', '-t', f'{DUR:.4f}', '-i', a.hero, '-ss', f'{a.tin:.4f}', '-t', f'{DUR:.4f}', '-i', a.take,
             '-map', '0:v:0', '-map', '1:a:0', '-dn', '-vf', f'scale={W}:{H}:flags=lanczos,format=yuv420p', '-af', af, '-ar', '48000', '-shortest',
             '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-tune', 'film', '-profile:v', 'high', '-level', '4.1', '-g', '48',
             '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-write_tmcd', '0', DELIV])   # -dn / -write_tmcd 0: the mov's timecode track would be re-muxed as a data track
        p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,width,height,pix_fmt,r_frame_rate,sample_rate', '-show_entries', 'format=duration,size', '-of', 'default=nw=1', DELIV], capture_output=True, text=True).stdout
        e = subprocess.run(['ffmpeg', '-v', 'info', '-i', DELIV, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
        il = re.findall(r'I:\s+(-?[\d.]+) LUFS', e); tp_ = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', e)
        print(p.strip()); print('ebur128 integrated', il[-1] if il else '?', 'LUFS  true peak', tp_[-1] if tp_ else '?', 'dBTP'); print('WROTE', DELIV)
        return float(tp_[-1]) if tp_ else float('-inf')

    tp, mtp = a.TP, a.match_tp
    tpv = render(tp, mtp)
    if tpv > a.tp_ceiling + 0.05 and not a.no_retry:
        over = tpv - a.tp_ceiling; kept = f"deliver/{a.name}__tp{(mtp if mtp is not None else tp):g}.mp4"
        assert not os.path.exists(kept), f'{kept} exists'
        os.rename(DELIV, kept)
        if mtp is not None: mtp = round(mtp - over - 0.3, 2)
        else: tp = round(tp - over - 0.3, 2)
        print(f"RETRY true peak {tpv} dBTP over the ceiling {a.tp_ceiling} by {over:.2f} dB — the attempt kept as {kept}; re-encoding once at "
              + (f"--match-tp {mtp}" if mtp is not None else f"TP {tp}"))
        tpv = render(tp, mtp)
    ck = json.loads(subprocess.run([sys.executable, os.path.join(HERE, 'aac_packet_clock.py'), '--json', DELIV], capture_output=True, text=True).stdout or '{"ok": false, "reason": "the scan did not run"}')
    fails = []
    for ok, label, detail in ((tpv <= a.tp_ceiling + 0.05, 'true peak', f'{tpv} dBTP decoded vs the platform ceiling {a.tp_ceiling} (the limiter ceiling {mtp if mtp is not None else tp} acts before the AAC encode)'),
                              (ck.get('ok') is not False, 'audio packet clock', ck.get('reason'))):
        print(f"{'PASS' if ok else 'FAIL'} {label}: {detail}"); ok or fails.append(label)
    if fails: sys.exit(f"FINISH-CLIP FAIL ({', '.join(fails)}) — {DELIV} kept for inspection")


if __name__ == '__main__':
    main()
