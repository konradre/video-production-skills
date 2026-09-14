#!/usr/bin/env python3
"""frame_psnr.py — the motion curve of a take as adjacent-frame PSNR (dB) on a 240 px grey downscale.

Reads: > 45 dB frozen · 30–40 breathing only (a FAILED beat where one was written) · 18–28 an action · < 15 a
cut. A written beat must be a DIP at its time; a tail whose mean leaves the take's band while the body holds
is a tail anomaly. Prints the curve at --step intervals, the minimum and when, and the last --tail seconds
against the take mean. Exit 0; exit 2 when ffmpeg/ffprobe fail. --selftest proves the direction on synthetic
frames without a file.

    python3 scripts/frame_psnr.py takes/S02-H3A-s1.mp4 [--step 0.25] [--tail 1.5]
    python3 scripts/frame_psnr.py --selftest
"""
import argparse, json, subprocess, sys
import numpy as np

W = 240


def psnr_curve(frames):
    f = frames.astype(np.float32)
    mse = ((f[1:] - f[:-1]) ** 2).mean(axis=(1, 2))
    return np.where(mse > 0, 10 * np.log10(255.0 ** 2 / np.maximum(mse, 1e-9)), 99.0)


def decode(src):
    try:
        probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                                    "stream=width,height,r_frame_rate", "-of", "json", src]))["streams"][0]
        h = max(2, round(W * probe["height"] / probe["width"] / 2) * 2)
        num, den = (int(x) for x in probe["r_frame_rate"].split("/")); fps = num / den
        raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", src, "-vf", f"scale={W}:{h}", "-f", "rawvideo",
                                       "-pix_fmt", "gray", "-"])
    except (subprocess.CalledProcessError, FileNotFoundError, KeyError, IndexError) as e:
        sys.exit(f"ffmpeg/ffprobe failed on {src}: {e}")
    return np.frombuffer(raw, np.uint8).reshape(-1, h, W), fps


def selftest():
    rng = np.random.default_rng(0)
    base = rng.integers(0, 256, (1, 120, W), np.uint8)
    frozen = np.repeat(base, 3, axis=0)
    small = np.concatenate([base, np.clip(base.astype(int) + rng.integers(-2, 3, base.shape), 0, 255).astype(np.uint8)])
    cut = np.concatenate([base, rng.integers(0, 256, (1, 120, W), np.uint8)])
    a, b, c = psnr_curve(frozen).min(), psnr_curve(small).mean(), psnr_curve(cut).mean()
    ok = a >= 99 and 35 < b < 60 and c < 15
    print(f"selftest  frozen {a:.1f} dB (≥ 99)  ±2-level jitter {b:.1f} dB (35–60)  random cut {c:.1f} dB (< 15)  → {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("take", nargs="?"); ap.add_argument("--step", type=float, default=0.25)
    ap.add_argument("--tail", type=float, default=1.5); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest: selftest()
    if not a.take: ap.error("a take is required (or --selftest)")
    frames, fps = decode(a.take); p = psnr_curve(frames); n = len(frames)
    print(f"{a.take.split('/')[-1]}  {n} frames @ {fps:.0f} fps  adjacent-frame PSNR (dB): mean {p.mean():.1f}  "
          f"min {p.min():.1f} @ {p.argmin() / fps:.2f} s  max {p.max():.1f}")
    k = max(1, round(a.step * fps)); cells = [f"{i / fps:5.2f}s:{p[i:i + k].mean():4.1f}" for i in range(0, len(p), k)]
    for j in range(0, len(cells), 8): print("  " + "  ".join(cells[j:j + 8]))
    t = p[-max(1, round(a.tail * fps)):]; body = p[:-len(t)] if len(p) > len(t) else p
    flag = ""
    if len(body) and (t.mean() > 45 > body.mean() or t.mean() < 15 < body.mean()): flag = "  ← TAIL ANOMALY: read the last frames"
    print(f"  last {a.tail:.1f} s: mean {t.mean():.1f}  min {t.min():.1f}   (body mean {body.mean():.1f}){flag}")


if __name__ == "__main__":
    main()
