#!/usr/bin/env python3
"""cut_consistency.py — consistency ACROSS the cuts inside one take. A cut the model composes inside one generation is a
capability, never a defect by itself: what breaks a take is a world that does not survive the cut — a face that changes,
wardrobe that shifts, a room that rearranges, light that jumps, a performance register that resets. This instrument measures
the axes a frame statistic CAN carry and hands the rest to the eye:
  light            mean L* (CIE Lab) of the half-second windows either side of every cut
  contrast         the L* spread of the same windows
  white balance    the shift of the mean a*/b*
  palette          the colour distribution's shift (a 16×16 a*b* histogram, Bhattacharyya distance)
each against the take's OWN within-shot baseline: the same metric between adjacent windows inside each shot, maximum over
the take. Every cut prints its value, its multiple of that maximum, and ABOVE when it exceeds it — a measurement, never a
verdict: a new angle can legitimately move light and palette past a quiet shot's baseline. Calibration 2026-09-13: a
client-accepted 20 s take's two composed cuts to new angles read ABOVE on light (1.4–1.6×) and palette (2.3×) and far under
on white balance (0.0–0.4×) and contrast (0.0–0.1×); four joins between separate generations (three seed swaps inside one
shot, one join of two shots) read ABOVE on all four rows. Raw values did NOT separate them across takes — a seed swap's light
step 1.35 against a composed cut's 9.39 — so compare multiples inside one take, never raw numbers between takes; a quiet
take's small baseline inflates every multiple. Two composed cuts from one take are a lead, not a threshold.
Identity and wardrobe are READ, never scored: the sheet writes the frames either side of every cut at native size, and
--box writes a face or a garment on each side at native size for the verdict read. The segment similarity matrix (grey
thumbnails, NCC) shows a camera setup the take returns to, where a changed room reads as a drop against its own frames.

  cut_consistency.py <take.mp4> [--cuts 5.5,9.25] [--gap 0.5] [--out review] [--box "5.5:x0,y0,x1,y1:x0,y0,x1,y1"] [--json]
  cut_consistency.py --selftest
Without --cuts the cut list comes from the take's own record (qc_seed.py --record), refused when stale or when it carries no
cut list (another reviewer's record format).
Images: the sheet is a SURVEY image (JPEG q85); a --box crop is a VERDICT image (JPEG q95, 4:4:4, never downscaled).
Self-test: a new angle of the same world and grade against a splice to another generation's grade — the splice must read
ABOVE on white balance at more than three times the composed cut.
"""
import argparse, hashlib, json, os, subprocess, sys
from io import BytesIO
import numpy as np
from PIL import Image

THUMB_W = 180
METRICS = ('light ΔL*', 'contrast ΔσL*', 'white balance Δa*b*', 'palette distance')


def srgb_to_lab(rgb):
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def stats(frames):
    """colour statistics of a window of frames (N×h×w×3 uint8)"""
    lab = srgb_to_lab(frames.reshape(-1, 3).astype(np.float64) / 255.0)
    h, _, _ = np.histogram2d(lab[:, 1], lab[:, 2], bins=16, range=[[-64, 64], [-64, 64]])
    return {'L': float(lab[:, 0].mean()), 'Lsd': float(lab[:, 0].std()), 'a': float(lab[:, 1].mean()), 'b': float(lab[:, 2].mean()), 'hist': h / max(h.sum(), 1.0)}


def metrics(s0, s1):
    return {METRICS[0]: abs(s0['L'] - s1['L']), METRICS[1]: abs(s0['Lsd'] - s1['Lsd']),
            METRICS[2]: float(np.hypot(s0['a'] - s1['a'], s0['b'] - s1['b'])),
            METRICS[3]: float(np.sqrt(max(0.0, 1.0 - float(np.sum(np.sqrt(s0['hist'] * s1['hist']))))))}


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))


def analyse(fr, cuts, fps, gap):
    """fr = N×h×w×3 frames; cuts = the first frame index of each new shot → (rows per cut, baseline max per metric, pairs, segments)"""
    n = len(fr); win = max(2, int(round(gap * fps))); bounds = [0] + sorted({c for c in cuts if 0 < c < n}) + [n]
    segs = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
    base = {m: 0.0 for m in METRICS}; pairs = 0
    for s, e in segs:
        for i in range(s + 1, e - 2 * win + 1, win):             # adjacent windows inside one shot
            m = metrics(stats(fr[i:i + win]), stats(fr[i + win:i + 2 * win])); pairs += 1
            for k, v in m.items(): base[k] = max(base[k], v)
    rows = []
    for j in range(1, len(segs)):
        (ps, pe), (ns, ne) = segs[j - 1], segs[j]
        m = metrics(stats(fr[max(ps, ns - win):ns]), stats(fr[ns:min(ne, ns + win)]))
        rows.append({'cut_frame': ns, 't': round(ns / fps, 3), **{k: round(v, 3) for k, v in m.items()},
                     'x_baseline': {k: (round(m[k] / base[k], 1) if pairs and base[k] > 0 else None) for k in METRICS},
                     'above': [k for k in METRICS if pairs and m[k] > base[k]]})
    return rows, base, pairs, segs


def probe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate,width,height', '-of', 'json', path], capture_output=True, text=True)
    st = json.loads(p.stdout)['streams'][0]; num, den = st['r_frame_rate'].split('/')
    return float(num) / float(den), int(st['width']), int(st['height'])


def decode(path, W, H):
    h = int(round(H * THUMB_W / W / 2) * 2)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'scale={THUMB_W}:{h}:flags=area', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, THUMB_W, 3)


def frame_at(path, idx):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'select=eq(n\\,{idx})', '-vframes', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    return Image.open(BytesIO(raw)).convert('RGB')


def record_cuts(take):
    rec = take + '.review.json'
    if not os.path.exists(rec): return None
    r = json.load(open(rec, encoding='utf-8'))
    times = (r.get('cuts') or {}).get('times_s')
    if times is None: sys.exit(f"{rec} carries no cut list (generator: {r.get('generator', 'not qc_seed.py')}) — pass --cuts")
    if os.path.getsize(take) != r.get('bytes'): sys.exit(f'STALE record {rec} (bytes) — re-run qc_seed.py --record, or pass --cuts')
    h = hashlib.sha256()
    with open(take, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    if h.hexdigest() != r.get('sha256'): sys.exit(f'STALE record {rec} (sha256) — re-run qc_seed.py --record, or pass --cuts')
    return times


def selftest():
    rng = np.random.default_rng(3); big = rng.random((360, 640, 3))
    for _ in range(4): big = (big + np.roll(big, 1, 0) + np.roll(big, 1, 1) + np.roll(big, -1, 0) + np.roll(big, -1, 1)) / 5
    lo, hi = big.min(), big.max(); warm = (big - lo) / (hi - lo) * 255 * np.array([1.0, 0.82, 0.62])
    view = lambda y, x: warm[y:y + 90, x:x + 160]
    A = np.stack([view(40, 40 + i) for i in range(48)]).astype(np.uint8)                                   # a slow pan
    B = np.stack([view(200, 300 + i) for i in range(48)]).astype(np.uint8)                                  # a NEW ANGLE, same world and grade
    C = np.stack([np.clip(view(200, 347 - i) * np.array([0.9, 0.95, 1.22]), 0, 255) for i in range(48)]).astype(np.uint8)   # another generation's grade
    rows, base, pairs, _ = analyse(np.concatenate([A, B, C]), [48, 96], 24.0, 0.5)
    wb = METRICS[2]; comp, join = rows[0], rows[1]
    ok = pairs > 0 and wb in join['above'] and join[wb] > 3 * comp[wb]
    print(f"selftest  composed cut (new angle, same grade): {wb} {comp[wb]:.2f} · spliced grade: {join[wb]:.2f} (within-shot max {base[wb]:.2f}) → {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('take', nargs='?'); ap.add_argument('--cuts', help='cut times in seconds, comma-separated (default: the take record)')
    ap.add_argument('--gap', type=float, default=0.5, help='window length in seconds either side of a cut, and between baseline windows')
    ap.add_argument('--out', default='review'); ap.add_argument('--box', action='append', default=[], help='"t:x0,y0,x1,y1:x0,y0,x1,y1" — a face or garment before and after the cut at t')
    ap.add_argument('--json', action='store_true'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    if not a.take: ap.error('a take is required')
    if selftest() != 0: sys.exit('the instrument failed its self-test — no number from it is used')
    fps, W, H = probe(a.take); fr = decode(a.take, W, H); name = os.path.splitext(os.path.basename(a.take))[0]
    times = [float(x) for x in a.cuts.split(',') if x] if a.cuts else record_cuts(a.take)
    if times is None: sys.exit('no --cuts and no take record — run qc_seed.py --record first, or pass the cut list')
    cuts = [int(round(t * fps)) for t in times]
    rows, base, pairs, segs = analyse(fr, cuts, fps, a.gap)
    print(f"{name}: {len(fr)} f @ {fps:g} fps · cuts at {times} s · baseline: {pairs} within-shot window pair(s), {a.gap:g} s windows · max " + ', '.join(f'{k} {base[k]:.2f}' for k in METRICS))
    if not pairs: print('  NO BASELINE — every shot is shorter than two windows; read the sheet only')
    for r in rows:
        print(f"  cut {r['t']:.3f} s  " + ' · '.join(f"{k} {r[k]:.2f}" + (f" ({r['x_baseline'][k]}×)" if r['x_baseline'][k] is not None else '') + (' ABOVE' if k in r['above'] else '') for k in METRICS))
    thumbs = [fr[(s + e) // 2].astype(np.float64).mean(-1) for s, e in segs]
    print('  segment similarity (NCC of mid-shot grey thumbnails): ' + ' | '.join(f"{i}:" + ' '.join(f"{ncc(thumbs[i], thumbs[j]):.2f}" for j in range(len(segs))) for i in range(len(segs))))
    os.makedirs(a.out, exist_ok=True)
    if rows:
        pairs_img = [(frame_at(a.take, r['cut_frame'] - 1), frame_at(a.take, r['cut_frame'])) for r in rows]
        w0, h0 = pairs_img[0][0].size; sheet = Image.new('RGB', (2 * w0 + 8, len(rows) * (h0 + 8)), 'black')
        for i, (b, c) in enumerate(pairs_img): sheet.paste(b, (0, i * (h0 + 8))); sheet.paste(c, (w0 + 8, i * (h0 + 8)))
        sp = f'{a.out}/{name}-cuts.jpg'; sheet.save(sp, quality=85); print(f'  sheet {sp} (survey: before | after at native size, one row per cut)')
    for spec in a.box:
        t, b0, b1 = spec.split(':'); k = int(round(float(t) * fps)); boxes = [tuple(int(v) for v in b.split(',')) for b in (b0, b1)]
        c0, c1 = frame_at(a.take, k - 1).crop(boxes[0]), frame_at(a.take, k).crop(boxes[1])
        im = Image.new('RGB', (c0.width + c1.width + 8, max(c0.height, c1.height)), 'black'); im.paste(c0, (0, 0)); im.paste(c1, (c0.width + 8, 0))
        bp = f'{a.out}/{name}-cut-{float(t):.3f}-box.jpg'; im.save(bp, quality=95, subsampling=0); print(f'  crop {bp} (verdict: native size, q95 4:4:4)')
    print('  identity and wardrobe are READ on the sheet and the crops — this instrument does not score them')
    if a.json: print(json.dumps({'take': a.take, 'fps': fps, 'gap_s': a.gap, 'baseline_max': base, 'baseline_pairs': pairs, 'cuts': rows}, ensure_ascii=False))


if __name__ == '__main__':
    main()
