#!/usr/bin/env python3
"""Bake look-library colour-tier .cube LUTs (33^3) from looks/*.yaml.

Pattern provenance (GUIDE.md §9):
  - color-fx `bake_grade_to_lut`: bake FROM the named params so LUT and fallback never drift.
  - hyperframes `cube-build.mjs`: Rec.709 luma, smoothstep masks, clamp-to-unit, 33^3 default.
  - postfx theme YAML: the parameter vocabulary (white_balance/lift_gamma_gain/tone_curve/...).
  - ComfyUI-Darkroom bake rule: ONLY per-pixel colour ops bake; spatial FX -> the .drx tier.

Op order (deliberate, documented — GUIDE.md §4a):
  film_base LUT -> white_balance -> exposure -> lift_gamma_gain -> highlight_rolloff
  -> tone_curve -> split_toning -> black_point -> vibrance/saturation (skin-protected)
Rationale: stock transform first; printer-light trims; luma shaping; stylize; saturation last
so skin-protection sees the final hues. Input/output = display-referred Rec.709 in [0,1]
(AI-gen video is display-referred — GUIDE.md §2; no log conversion).

Usage: python3 build_cubes.py [--size 33] [--only <id>] [--bases spectral_luts]
Writes cubes/<id>_<size>.cube + index.json (hashed manifest, hyperframes pattern).
The film looks sample a spectral base cube first (looks/*.yaml `film_base`, a path relative to this
directory, or a file name found under --bases): fetch them with fetch_spectral_bases.sh.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent          # look-library/

LUMA = np.array([0.2126, 0.7152, 0.0722])       # Rec.709 (hyperframes convention)


# ---------------------------------------------------------------- cube I/O
def read_cube(path: Path):
    """Parse a .cube 3D LUT -> (arr[b,g,r,3], size). Red varies fastest (spec order)."""
    size = None
    rows = []
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        up = line.upper()
        if up.startswith("TITLE") or up.startswith("DOMAIN_"):
            continue
        if up.startswith("LUT_3D_SIZE"):
            size = int(line.split()[1])
            continue
        if up.startswith("LUT_"):
            continue
        parts = line.split()
        if len(parts) == 3:
            rows.append([float(p) for p in parts])
    if size is None or len(rows) != size ** 3:
        raise ValueError(f"{path}: bad cube (size={size}, rows={len(rows)})")
    return np.asarray(rows, dtype=np.float64).reshape(size, size, size, 3), size


def sample_lut(lut, size, rgb):
    """Vectorized trilinear sample. rgb: (M,3) in [0,1] -> (M,3)."""
    pos = np.clip(rgb, 0.0, 1.0) * (size - 1)
    i0 = np.floor(pos).astype(int)
    i0 = np.minimum(i0, size - 2)
    f = pos - i0
    r0, g0, b0 = i0[:, 0], i0[:, 1], i0[:, 2]
    fr, fg, fb = f[:, 0:1], f[:, 1:2], f[:, 2:3]

    def at(dr, dg, db):
        return lut[b0 + db, g0 + dg, r0 + dr]   # arr indexed [b,g,r]

    c00 = at(0, 0, 0) * (1 - fr) + at(1, 0, 0) * fr
    c10 = at(0, 1, 0) * (1 - fr) + at(1, 1, 0) * fr
    c01 = at(0, 0, 1) * (1 - fr) + at(1, 0, 1) * fr
    c11 = at(0, 1, 1) * (1 - fr) + at(1, 1, 1) * fr
    c0 = c00 * (1 - fg) + c10 * fg
    c1 = c01 * (1 - fg) + c11 * fg
    return c0 * (1 - fb) + c1 * fb


def write_cube(path: Path, data, size, title):
    lines = [
        f'TITLE "{title}"',
        "# look-library — baked by build_cubes.py from looks/<id>.yaml",
        "# method: GUIDE.md section 4a",
        f"LUT_3D_SIZE {size}",
    ]
    body = np.clip(data, 0.0, 1.0)
    lines += [f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in body]
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------- grade ops
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def op_white_balance(c, p):
    temp, tint = p.get("temp", 0.0), p.get("tint", 0.0)
    # hyperframes cube-build coefficients
    scale = np.array([
        1 + temp * 0.28 + tint * 0.08,
        1 - abs(tint) * 0.10 - tint * 0.08,
        1 - temp * 0.28 + tint * 0.08,
    ])
    return c * scale


def op_exposure(c, p):
    return c * (2.0 ** p.get("stops", 0.0))


def op_lift_gamma_gain(c, p):
    lift = np.asarray(p.get("lift", [0, 0, 0]), dtype=float)
    gamma = np.asarray(p.get("gamma", [1, 1, 1]), dtype=float)
    gain = np.asarray(p.get("gain", [1, 1, 1]), dtype=float)
    out = gain * (c + lift * (1.0 - c))
    out = np.clip(out, 0.0, None)
    return np.power(out, 1.0 / gamma)


def op_highlight_rolloff(c, p):
    knee, s = p.get("knee", 1.0), p.get("strength", 0.0)
    if s <= 0 or knee >= 1.0:
        return c
    t = np.clip((c - knee) / (1.0 - knee), 0.0, None)
    rolled = t * (1.0 + s) / (1.0 + s * t)      # g(0)=0, g(1)=1, slope at 1 = 1/(1+s)
    return np.where(c > knee, knee + (1.0 - knee) * rolled, c)


def op_tone_curve(c, p):
    s, pivot = p.get("strength", 0.0), p.get("pivot", 0.5)
    if s <= 0:
        return c
    lo = pivot * np.power(np.clip(c / pivot, 0, 1), 1.0 + s)
    hi = 1.0 - (1.0 - pivot) * np.power(np.clip((1.0 - c) / (1.0 - pivot), 0, 1), 1.0 + s)
    return np.where(c < pivot, lo, hi)


def op_split_toning(c, p):
    strength = p.get("strength", 0.0)
    if strength <= 0:
        return c
    balance = p.get("balance", 0.5)
    sh = np.asarray(p.get("shadow", [0, 0, 0]), dtype=float)
    hi = np.asarray(p.get("highlight", [0, 0, 0]), dtype=float)
    y = (c @ LUMA)[:, None]
    shadow_mask = 1.0 - smoothstep(balance - 0.25, balance + 0.20, y)
    highlight_mask = smoothstep(balance - 0.20, balance + 0.25, y)
    return c + strength * (sh * shadow_mask + hi * highlight_mask)


def op_black_point(c, p):
    lift = p.get("lift", 0.0)
    lift = np.asarray(lift if isinstance(lift, (list, tuple)) else [lift] * 3, dtype=float)
    return lift + (1.0 - lift) * c


def skin_weight(c, protect):
    """1 where free to saturate, dips toward (1-protect) on skin hues (~25 deg orange)."""
    if protect <= 0:
        return 1.0
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    mx, mn = c.max(axis=1), c.min(axis=1)
    delta = mx - mn
    hue = np.zeros_like(mx)
    m = delta > 1e-6
    rm = m & (mx == r)
    gm = m & (mx == g) & ~rm
    bm = m & ~rm & ~gm
    hue[rm] = (60 * ((g - b) / np.where(delta == 0, 1, delta)))[rm] % 360
    hue[gm] = (60 * ((b - r) / np.where(delta == 0, 1, delta)) + 120)[gm]
    hue[bm] = (60 * ((r - g) / np.where(delta == 0, 1, delta)) + 240)[bm]
    d = np.minimum(np.abs(hue - 25.0), 360.0 - np.abs(hue - 25.0))
    mask = np.exp(-((d / 22.0) ** 2)) * m       # grey pixels: no skin mask
    return (1.0 - protect * mask)[:, None]


def op_vibrance(c, p):
    sat = p.get("saturation", 1.0)
    vib = p.get("vibrance", 0.0)
    protect = p.get("skin_protect", 0.0)
    y = (c @ LUMA)[:, None]
    cur = np.abs(c - y).max(axis=1, keepdims=True)
    vib_w = 1.0 - np.clip(cur * 2.0, 0.0, 1.0)   # vibrance favours low-sat pixels
    factor = sat + vib * vib_w
    boost = factor - 1.0
    factor = 1.0 + np.where(boost > 0, boost * skin_weight(c, protect), boost)
    return y + (c - y) * factor


OPS = [
    ("white_balance", op_white_balance),
    ("exposure", op_exposure),
    ("lift_gamma_gain", op_lift_gamma_gain),
    ("highlight_rolloff", op_highlight_rolloff),
    ("tone_curve", op_tone_curve),
    ("split_toning", op_split_toning),
    ("black_point", op_black_point),
    ("vibrance", op_vibrance),
]


# ---------------------------------------------------------------- build
def bake_look(look: dict, size: int, bases: Path | None = None) -> np.ndarray:
    axis = np.linspace(0.0, 1.0, size)
    b, g, r = np.meshgrid(axis, axis, axis, indexing="ij")     # b slowest, r fastest
    c = np.stack([r.ravel(), g.ravel(), b.ravel()], axis=1)

    base = look.get("film_base")
    if base:
        path = ROOT / base
        if bases and (bases / Path(base).name).exists():
            path = bases / Path(base).name
        if not path.exists():
            raise SystemExit(f"film base not found: {path} — run fetch_spectral_bases.sh (or pass --bases)")
        lut, lsize = read_cube(path)
        c = sample_lut(lut, lsize, c)

    params = look.get("params", {})
    for name, fn in OPS:
        if name in params:
            c = np.clip(fn(c, params[name]), 0.0, 1.0)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=33)
    ap.add_argument("--only", help="bake a single look id")
    ap.add_argument("--bases", help="directory holding the spectral base cubes (default: looks/*.yaml film_base paths)")
    args = ap.parse_args()
    bases = Path(args.bases).resolve() if args.bases else None

    (ROOT / "cubes").mkdir(exist_ok=True)
    index = {"notes": "Colour tier of the look-library. Each look = .cube (this manifest, "
                      "apply via ffmpeg lut3d everywhere) + .drx (Dehancer hero pass in Resolve, "
                      "RECIPES.md). Params in looks/<id>.yaml are the deterministic "
                      "buildCube source — bake from them, never hand-edit a .cube.",
             "method": "GUIDE.md",
             "looks": []}

    for path in sorted((ROOT / "looks").glob("*.yaml")):
        look = yaml.safe_load(path.read_text())
        if args.only and look["id"] != args.only:
            continue
        data = bake_look(look, args.size, bases)
        out = ROOT / "cubes" / f"{look['id']}_{args.size}.cube"
        write_cube(out, data, args.size, f"look-library {look['id']} ({look['genre']})")
        sha = hashlib.sha256(out.read_bytes()).hexdigest()
        drx_entry = dict(look.get("drx", {}))
        drx_path = ROOT / "drx" / f"{look['id']}.drx"
        if drx_path.exists():
            drx_entry.update(file=f"drx/{look['id']}.drx", status="authored",
                             sha256=hashlib.sha256(drx_path.read_bytes()).hexdigest())
        index["looks"].append({
            "id": look["id"],
            "genre": look["genre"],
            "description": look["description"],
            "tags": look.get("tags", []),
            "intensity": look.get("intensity", 1.0),
            "yaml": f"looks/{path.name}",
            "film_base": look.get("film_base"),
            "cube": {"file": f"cubes/{out.name}", "size": args.size, "sha256": sha},
            "drx": drx_entry,
            "compression": look.get("compression", {}),
        })
        print(f"baked {out.name}  sha256={sha[:16]}…")

    if not args.only:
        (ROOT / "index.json").write_text(json.dumps(index, indent=2) + "\n")
        print(f"wrote index.json ({len(index['looks'])} looks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
