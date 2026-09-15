#!/usr/bin/env python3
"""phone_texture_probe.py — the texture band of a clip, for the MATCHED-CONTENT comparison behind the phone-native tier.

Per file, on native centre crops (never a resample — a downscale suppresses exactly the noise being read), grey plane,
frames at 20 / 50 / 80 % of the duration (fractions, so a 7 s take and a 30 s spot sample alike):
  dead-flat %      the share of 8×8 blocks with ZERO variance (the encoder flattened them)
  noise floor      the median block sd of the flattest 20 % of blocks (content-light; what fine noise survives the encode)
  median block sd  the median block sd over the whole crop (content + noise; compare only on matched content)

The numbers are a COMPARISON, never a threshold. Measured 2026-09-16: two real phone clips as they arrived from a
client (H.264 1080p, ~2.5 Mbps) read 34.3 % / 0.06 / 0.69 and 2.6 % / 0.43 / 2.24; three Omni Flash 1.1 takes at native
720p read 0.0 % / 1.75–1.96 / 7.1 — MORE fine texture than the phone clips, not less — and the same take delivered at
1080×1920 ~5 Mbps read 0.0 % / 1.09 / 5.29. A generated take is therefore not under-textured by default; the encode the
real clips arrived through decides the band. Protocol: probe the project's own real clips first, by scene class (a flat
wall, a textured room, a dark frame); probe the candidate on matched content; the tier's dose (noise OR denoise, and the
encode bitrate) moves the candidate INTO the real band — `video-finish` § 5 (the phone-native tier).

  phone_texture_probe.py <clip>… [--crop 640] [--at 0.2,0.5,0.8] [--json]
  phone_texture_probe.py --selftest      # a flat frame + injected Gaussian noise sd 0.5/1/2/4 must read back linearly

Exit 0 when every file was probed; 1 on a file that yielded no frame; the selftest exits 1 on a failed assertion.
"""
import argparse, json, subprocess, sys
import numpy as np


def sh(cmd):
    return subprocess.run(cmd, capture_output=True)


def probe_dims(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                        'stream=width,height:format=duration', '-of', 'json', path], capture_output=True, text=True)
    js = json.loads(p.stdout or '{}')
    st = (js.get('streams') or [{}])[0]
    W, H = int(st.get('width', 0) or 0), int(st.get('height', 0) or 0)
    dur = float((js.get('format') or {}).get('duration', 0) or 0)
    return W, H, dur


def frames(path, crop=640, at=(0.2, 0.5, 0.8)):
    """Native centre crops (grey, uint8→float32) at the given fractions of the duration."""
    W, H, dur = probe_dims(path)
    if not W or not H or dur <= 0:
        return [], (W, H, dur)
    w = min(crop, W, H)
    w -= w % 2
    out = []
    for f in at:
        t = max(0.0, min(dur * f, dur - 0.05))
        p = sh(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', path, '-frames:v', '1',
                '-vf', f'crop={w}:{w}:(iw-{w})/2:(ih-{w})/2,format=gray', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'])
        a = np.frombuffer(p.stdout, dtype=np.uint8)
        if a.size == w * w:
            out.append(a.reshape(w, w).astype(np.float32))
    return out, (W, H, dur)


def stats(f):
    """dead-flat % · noise floor (median sd of the flattest 20 % of 8×8 blocks) · median block sd."""
    h, w = f.shape
    h8, w8 = h // 8 * 8, w // 8 * 8
    b = f[:h8, :w8].reshape(h8 // 8, 8, w8 // 8, 8).transpose(0, 2, 1, 3).reshape(-1, 64)
    sd = b.std(axis=1)
    dead = float((sd == 0).mean() * 100)
    flat = np.sort(sd)[:max(1, int(len(sd) * 0.2))]
    return dead, float(np.median(flat)), float(np.median(sd))


def measure(path, crop=640, at=(0.1, 0.3, 0.5, 0.7, 0.9)):
    """The mean over the sampled frames, and the per-file RANGE across them — the band of one clip is a range, not a
    point: two frames of one real clip read 6 % and 34 % dead-flat (a textured room and a flat wall)."""
    fs, (W, H, dur) = frames(path, crop, at)
    if not fs:
        return None
    d = [stats(f) for f in fs]
    cols = ('dead_flat_pct', 'noise_floor', 'median_block_sd')
    r = {'file': path, 'width': W, 'height': H, 'duration_s': round(dur, 3), 'frames': len(fs), 'crop': int(fs[0].shape[0])}
    for i, k in enumerate(cols):
        v = [x[i] for x in d]
        r[k] = round(float(np.mean(v)), 3)
        r[k + '_min'] = round(float(min(v)), 3)
        r[k + '_max'] = round(float(max(v)), 3)
    return r


def selftest():
    """Known-answer case: a flat 640×640 frame reads 100 % dead-flat at a 0.00 floor; injected Gaussian noise of sd
    0.5 / 1 / 2 / 4 reads back monotonically and within the uint8 quantisation of its sd (the retrospective's positive
    control read 0.45 / 0.90 / 1.78 / 3.50 for the same injection)."""
    rng = np.random.default_rng(7)
    flat = np.full((640, 640), 128, np.float32)
    dead, floor, med = stats(flat)
    ok = dead == 100.0 and floor == 0.0 and med == 0.0
    print(f"selftest flat frame: dead-flat {dead:.1f} % · floor {floor:.2f} · median {med:.2f} → {'OK' if ok else 'FAIL'}")
    prev = 0.0
    for s in (0.5, 1.0, 2.0, 4.0):
        f = np.clip(np.round(flat + rng.normal(0, s, flat.shape)), 0, 255).astype(np.uint8).astype(np.float32)
        dead, floor, med = stats(f)
        good = 0.78 * s <= floor <= 1.05 * s and med > prev and dead == 0.0
        ok &= good
        prev = med
        print(f"selftest sd {s:.1f} injected: dead-flat {dead:.1f} % · floor {floor:.2f} · median {med:.2f} → {'OK' if good else 'FAIL'}")
    print('PHONE-TEXTURE-PROBE SELFTEST ' + ('PASS' if ok else 'FAIL'))
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('clips', nargs='*')
    ap.add_argument('--crop', type=int, default=640, help='centre-crop side in NATIVE pixels (clamped to the frame)')
    ap.add_argument('--at', default='0.1,0.3,0.5,0.7,0.9', help='fractions of the duration to sample')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        selftest()
    if not a.clips:
        ap.error('give at least one clip, or --selftest')
    at = tuple(float(x) for x in a.at.split(','))
    rows, bad = [], 0
    for c in a.clips:
        r = measure(c, a.crop, at)
        if r is None:
            bad += 1
            print(f"{c}: no frame could be read", file=sys.stderr)
            continue
        rows.append(r)
        if not a.json:
            print(f"{c[-56:]:>56} | {r['width']}x{r['height']} n={r['frames']} crop {r['crop']} | "
                  f"dead-flat 8x8 % {r['dead_flat_pct']:5.1f} [{r['dead_flat_pct_min']:.1f}–{r['dead_flat_pct_max']:.1f}] | "
                  f"noise floor {r['noise_floor']:5.2f} [{r['noise_floor_min']:.2f}–{r['noise_floor_max']:.2f}] | "
                  f"median block sd {r['median_block_sd']:5.2f} [{r['median_block_sd_min']:.2f}–{r['median_block_sd_max']:.2f}]")
    if a.json:
        print(json.dumps(rows, indent=1))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
