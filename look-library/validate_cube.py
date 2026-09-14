#!/usr/bin/env python3
"""Validate .cube LUTs — port of hyperframes cube-validate.mjs checks.

Checks: LUT_3D_SIZE present and 2..64, row count == size^3, every row = 3 finite
numbers, DOMAIN_MAX > DOMAIN_MIN, no unsupported LUT_ keywords, no 1D/3D mix.
Extra (ours): warn if any value falls outside [0,1] (ffmpeg lut3d clamps; Resolve
may not) — warn, not fail.

Usage: python3 validate_cube.py <file.cube> [more...]   exit 0 = all ok
"""
import sys


def validate(path):
    size = None
    lut1d = None
    rows = 0
    out_of_range = 0
    dom_min, dom_max = [0.0] * 3, [1.0] * 3
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        return False, f"unreadable: {e}"
    for n, raw in enumerate(text.replace("﻿", "").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        kw = parts[0].upper()
        rest = parts[1:]
        if kw == "TITLE":
            continue
        if kw in ("DOMAIN_MIN", "DOMAIN_MAX"):
            if len(rest) != 3:
                return False, f"line {n}: {kw} expects three numbers"
            vals = [float(v) for v in rest]
            if kw == "DOMAIN_MIN":
                dom_min = vals
            else:
                dom_max = vals
            continue
        if kw == "LUT_1D_SIZE":
            lut1d = int(rest[0])
            continue
        if kw == "LUT_3D_SIZE":
            size = int(rest[0])
            if size < 2 or size > 64:
                return False, f"line {n}: LUT_3D_SIZE {size} out of 2..64"
            continue
        if kw.startswith("LUT_") and kw != "LUT_3D_INPUT_RANGE":
            return False, f"line {n}: unsupported keyword {kw}"
        if kw == "LUT_3D_INPUT_RANGE":
            continue
        # data row
        if size is None:
            if lut1d:
                return False, "1D cube LUTs are not supported"
            return False, f"line {n}: LUT data before LUT_3D_SIZE"
        if len(parts) != 3:
            return False, f"line {n}: data row must contain three numbers"
        try:
            vals = [float(v) for v in parts]
        except ValueError:
            return False, f"line {n}: invalid number"
        if any(v != v or v in (float("inf"), float("-inf")) for v in vals):
            return False, f"line {n}: non-finite value"
        if any(v < 0.0 or v > 1.0 for v in vals):
            out_of_range += 1
        rows += 1
    if lut1d and size:
        return False, "mixed 1D and 3D LUT"
    if size is None:
        return False, "missing LUT_3D_SIZE"
    if any(mx <= mn for mn, mx in zip(dom_min, dom_max)):
        return False, "DOMAIN_MAX must exceed DOMAIN_MIN"
    if rows != size ** 3:
        return False, f"expected {size ** 3} rows for size {size}, found {rows}"
    note = f" (warn: {out_of_range} rows outside [0,1])" if out_of_range else ""
    return True, f"ok: LUT_3D_SIZE {size}, {rows} rows{note}"


def main(argv):
    if len(argv) > 1 and argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if len(argv) < 2:
        print("usage: validate_cube.py <file.cube> [more...]", file=sys.stderr)
        return 2
    bad = 0
    for path in argv[1:]:
        ok, msg = validate(path)
        print(f"{'OK ' if ok else 'ERR'} {path}: {msg}")
        bad += 0 if ok else 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
