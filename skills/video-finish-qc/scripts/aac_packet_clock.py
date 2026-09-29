#!/usr/bin/env python3
"""aac_packet_clock.py — scan a delivered file's AAC packets for a broken presentation clock, on the ENCODED stream.

An AAC-LC packet is 1024 samples (21.333 ms at 48 kHz). A presentation-timestamp jump that reaches the encoder is written
by the MP4 muxer as ONE overlong packet, and every packet after it plays late by the excess. loudnorm's 100 ms block
buffer flushing a partial final block is the measured case: one packet 101.3 ms long, 80 ms late, in 25 of 27 clips of
another pipeline (bridgeclip `docs/AV_SYNC_FOLLOWUP_2026-09-24.md`), and reproduced here on ffmpeg 6.1.1 — a single-pass
loudnorm → AAC with `-shortest` broke 5 of 6 fractional durations, 41.720 s at 38.805 s by +80.0 ms (measured 2026-09-29).
The stream start, the stream duration and a decode to raw PCM all miss it — raw PCM concatenates samples and drops the
timestamps — so the scan reads the packets themselves.

Rule: every packet ≤ one frame + one sample, and each packet starts one frame after the one before it (± one sample, or
± one time-base tick where the container rounds — Matroska's 1 ms). Accepted: encoder priming before zero, a short FINAL
packet, and a packet the container lists without a duration (the start continuity still checks it). A break prints its
position, its size, and the net offset it leaves on everything after it.

  aac_packet_clock.py <file> [--stream a:0] [--json]     # exit 1 on a break, 2 when the stream cannot be checked
  aac_packet_clock.py --selftest                          # a clean encode passes; an 80 ms PTS jump fails at the jump

A break is fixed upstream of the encoder, never with a constant shift — its size depends on the fractional edit duration.
bridgeclip's fix is a PAIR: materialise source gaps as silence on the input (`aresample=48000:async=1:first_pts=0:
min_hard_comp=0.001`), then rebuild the clock from the samples after the last loudness/resample filter (`asettb=1/48000,
asetpts=N`). The reset alone collapses a REAL gap in a take: a beep behind a 200 ms source gap landed 200 ms early with the
reset alone and on time with the pair, and this scan passes both — it sees the clock, not the content's timing.
"""
import argparse, json, os, subprocess, sys, tempfile
from fractions import Fraction


def scan(path, stream='a:0', timeout=300):
    """{'ok': True|False|None, 'reason', 'packets', 'breaks': [{'t', 'ms', 'kind'}], 'net_ms'} — ok None = the stream
    could not be checked (no audio, not AAC, unreadable); the caller decides whether that fails."""
    pr = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', stream, '-show_entries',
                         'stream=codec_name,profile,sample_rate,time_base', '-of', 'json', path],
                        capture_output=True, text=True, timeout=timeout)
    st = (json.loads(pr.stdout or '{}').get('streams') or [None])[0]
    out = {'ok': None, 'reason': '', 'packets': 0, 'breaks': [], 'net_ms': 0.0}
    if not st: out['reason'] = f'no {stream} stream'; return out
    if st.get('codec_name') != 'aac': out['reason'] = f"{st.get('codec_name')}: the scan knows AAC framing only"; return out
    sr = int(st['sample_rate']); tb = Fraction(st['time_base'])
    frame = 2048 if 'HE' in (st.get('profile') or '') else 1024      # HE-AAC: 2048 samples at the output (SBR) rate
    nominal = Fraction(frame, sr) / tb                                   # one packet, in time-base ticks
    tol = max(Fraction(1, sr) / tb, Fraction(1) if tb > Fraction(1, sr) else Fraction(0))   # a sample, or a coarser tick
    p = subprocess.Popen(['ffprobe', '-v', 'error', '-select_streams', stream, '-show_entries', 'packet=pts,duration',
                          '-of', 'csv=p=0', path], stdout=subprocess.PIPE, text=True)
    prev = None; net = Fraction(0)
    try:
        for line in p.stdout:                  # streamed: memory stays flat on a long file
            f = line.strip().split(',')
            if not f[0].lstrip('-').isdigit():
                out['breaks'].append({'t': None, 'ms': None, 'kind': f'a packet without a timestamp ({line.strip()!r})'}); continue
            pts = int(f[0]); dur = int(f[1]) if len(f) > 1 and f[1].isdigit() else None
            out['packets'] += 1
            if dur is not None and dur <= 0:
                out['breaks'].append({'t': float(pts * tb), 'ms': None, 'kind': 'zero-length packet'})
            if dur is not None and dur > nominal + tol:      # the MP4 form of a timestamp jump: one packet holds the gap
                out['breaks'].append({'t': float(pts * tb), 'ms': round(float((dur - nominal) * tb * 1000), 2), 'kind': 'overlong packet'})
            if prev is not None:
                step = pts - prev[0]
                if abs(step - nominal) > tol:  # a gap or an overlap between starts (Matroska/TS, or a short mid packet)
                    net += step - nominal
                    if not (prev[1] is not None and prev[1] > nominal + tol and step == prev[1]):   # not the overlong one again
                        out['breaks'].append({'t': float(pts * tb), 'ms': round(float((step - nominal) * tb * 1000), 2), 'kind': 'discontinuous start'})
            prev = (pts, dur)
        p.wait(timeout=timeout)
    finally:
        if p.poll() is None: p.kill()
    if p.returncode != 0 or not out['packets']:
        out['reason'] = 'ffprobe could not list the packets'; return out
    if prev[1] is not None and prev[1] > nominal + tol: net += prev[1] - nominal   # the last packet's overrun has no successor
    out['net_ms'] = round(float(net * tb * 1000), 2)
    out['ok'] = not out['breaks']
    if out['breaks']:
        b = out['breaks'][0]
        out['reason'] = (f"{len(out['breaks'])} break(s); first at {b['t']:.3f} s ({b['kind']}, {b['ms']:+} ms) — the audio after "
                         f"it plays {out['net_ms']:+} ms off its picture" if b['t'] is not None else f"{len(out['breaks'])} break(s); {b['kind']}")
    else:
        out['reason'] = f"{out['packets']} packets of {frame} samples at {sr} Hz, continuous"
    return out


def _fixture(d, name, af):
    path = os.path.join(d, name)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=6.37',
                    '-af', af, '-c:a', 'aac', '-b:a', '192k', path], check=True)
    return path


def selftest():
    with tempfile.TemporaryDirectory() as d:
        clean = scan(_fixture(d, 'clean.m4a', 'aformat=channel_layouts=stereo'))
        # an 80 ms presentation jump at 2 s — the shape the loudnorm flush leaves (3840 samples at 48 kHz)
        jump = scan(_fixture(d, 'jump.m4a', "aformat=channel_layouts=stereo,asetpts='if(gte(N,96000),N+3840,N)/SR/TB'"))
        mka = scan(_fixture(d, 'jump.mka', "aformat=channel_layouts=stereo,asetpts='if(gte(N,96000),N+3840,N)/SR/TB'"))
    ok = clean['ok'] is True and jump['ok'] is False and abs(jump['net_ms'] - 80) < 1 \
        and any(abs((b['t'] or 0) - 2.0) < 0.05 and abs((b['ms'] or 0) - 80) < 1 for b in jump['breaks']) \
        and mka['ok'] is False and abs(mka['net_ms'] - 80) < 2
    print(f"selftest clean:     {clean['reason']}\nselftest jump mp4:  {jump['reason']}\nselftest jump mka:  {mka['reason']}"
          f"\nSELFTEST {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file', nargs='?'); ap.add_argument('--stream', default='a:0'); ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: selftest()
    if not a.file: ap.error('a file, or --selftest')
    r = scan(a.file, a.stream)
    print(json.dumps(r) if a.json else f"{'PASS' if r['ok'] else 'FAIL' if r['ok'] is False else 'UNCHECKED'} aac packet clock: {r['reason']}")
    sys.exit(0 if r['ok'] else 1 if r['ok'] is False else 2)


if __name__ == '__main__':
    main()
