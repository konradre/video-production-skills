#!/usr/bin/env python3
"""asset_edge_repaint.py — fix a residual defect IN THE SOURCE ASSET by measurement, never by layout gymnastics: where a
two-colour boundary (a ring's edge, a label's straight edge) was left with a notch or a speck by an earlier erase, the
boundary is re-fitted through the clean edge on both sides of the notch (a circle, since scallops and rings are arcs) and
the notch bbox is repainted colour A above the curve / colour B below it with a 1-px anti-aliased edge. Everything outside
the bboxes is byte-identical. Before/after 8× crops go to --review-dir so the fix is checked on the DELIVERED-scale artefact.

  asset_edge_repaint.py --src assets/wordmark-v4.png --dst assets/wordmark-v5.png --above ff2a2a --below 2a5cff
                        --job left:1178,1606:54,82,44,78:18-52,84-112 [--job right:…] [--review-dir review/asset] [--tol 80]
--job tag:ox,oy:x0,x1,y0,y1:fa0-fa1,fb0-fb1  — a 120-px window at (ox,oy); the notch bbox inside it; two column ranges either
side of the notch where the edge is clean (the fit columns). --above/--below are the two paint colours as hex (RGB); each is
re-measured as the median of the window's pixels within --tol of it.
"""
import argparse, os, sys
import numpy as np
from PIL import Image


def parse_job(s):
    tag, o, b, fc = s.split(':'); ox, oy = (int(v) for v in o.split(',')); x0, x1, y0, y1 = (int(v) for v in b.split(','))
    cols = [tuple(int(v) for v in r.split('-')) for r in fc.split(',')]; return tag, (ox, oy), (x0, x1, y0, y1), cols


def hexrgb(h): h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', required=True); ap.add_argument('--dst', required=True); ap.add_argument('--above', required=True); ap.add_argument('--below', required=True)
    ap.add_argument('--job', action='append', required=True); ap.add_argument('--review-dir', default='review/asset'); ap.add_argument('--tol', type=float, default=150, help='sum of |ΔR|+|ΔG|+|ΔB| within which a pixel counts as one of the two paints'); ap.add_argument('--win', type=int, default=120)
    a = ap.parse_args(); A = np.asarray(Image.open(a.src).convert('RGBA')).copy(); B = A.copy(); CA, CB = hexrgb(a.above), hexrgb(a.below); os.makedirs(a.review_dir, exist_ok=True)
    for js in a.job:
        tag, (ox, oy), (x0, x1, y0, y1), fitcols = parse_job(js); Wd = A[oy:oy + a.win, ox:ox + a.win, :3].astype(float); opaque = A[oy:oy + a.win, ox:ox + a.win, 3] >= 200
        near = lambda c: (np.abs(Wd - c).sum(axis=2) < a.tol) & opaque
        ma, mb = near(CA), near(CB)
        if not (ma.any() and mb.any()):
            q = (Wd[opaque] // 32 * 32).astype(int); vals, cnt = np.unique(q, axis=0, return_counts=True); top = vals[np.argsort(-cnt)[:4]]
            sys.exit(f"{tag}: a paint colour was not found in the window (above {ma.sum()} px, below {mb.sum()} px) — the window's dominant colours are " + ', '.join('#%02x%02x%02x' % tuple(int(v) + 16 for v in t) for t in top) + '; pass those as --above/--below or widen --tol')
        above, below = np.median(Wd[ma], axis=0), np.median(Wd[mb], axis=0)
        xs, ys = [], []
        for (p, q) in fitcols:
            for x in range(p, q):
                rows = np.nonzero(mb[:, x])[0]
                if len(rows): xs.append(x); ys.append(rows.min())      # the first "below" row from the top = the edge
        xs = np.array(xs, float); ys = np.array(ys, float) + 0.5; assert len(xs) >= 6, f'{tag}: too few edge columns to fit ({len(xs)})'
        M = np.c_[2 * xs, 2 * ys, np.ones_like(xs)]; cx, cy, c = np.linalg.lstsq(M, xs ** 2 + ys ** 2, rcond=None)[0]; r = np.sqrt(c + cx ** 2 + cy ** 2)
        upper = cy > ys.mean()   # the centre sits below the edge -> the edge is the circle's upper branch

        def f(x): d = max(r ** 2 - (x - cx) ** 2, 0.0); return cy - np.sqrt(d) if upper else cy + np.sqrt(d)

        resid = np.abs(ys - np.array([f(x) for x in xs])); n = 0
        for x in range(x0, x1):
            yb = f(x)
            for y in range(y0, y1):
                if A[oy + y, ox + x, 3] < 200: continue
                if y + 1 <= yb: col = above
                elif y >= yb: col = below
                else: t = y + 1 - yb; col = (1 - t) * above + t * below
                if np.abs(B[oy + y, ox + x, :3].astype(float) - col).max() > 2: n += 1
                B[oy + y, ox + x, :3] = np.round(col).astype(np.uint8)
        print(f'{tag}: circle r={r:.1f} centre=({cx:.1f},{cy:.1f}) on {len(xs)} cols, max resid {resid.max():.2f} px, mean {resid.mean():.2f}; repainted {n} px in x{ox + x0}-{ox + x1} y{oy + y0}-{oy + y1}')
        for name, img in (('before', A), ('after', B)):
            w = img[oy:oy + a.win, ox:ox + a.win]; rgb = (w[:, :, :3].astype(np.float32) * (w[:, :, 3:4] / 255.0)).astype(np.uint8)
            Image.fromarray(rgb).resize((a.win * 8, a.win * 8), Image.NEAREST).save(os.path.join(a.review_dir, f'{tag}-{name}-8x.png'))
    diff = np.abs(B.astype(int) - A.astype(int)).max(-1) > 0; ys_, xs_ = np.nonzero(diff)
    print(f'changed px total {int(diff.sum())}' + (f' bbox x{xs_.min()}-{xs_.max()} y{ys_.min()}-{ys_.max()}' if diff.any() else ''))
    Image.fromarray(B, 'RGBA').save(a.dst); print('wrote', a.dst, '— review crops in', a.review_dir)


if __name__ == '__main__':
    main()
