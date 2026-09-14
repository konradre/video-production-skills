#!/usr/bin/env python3
"""Read a scene proxy from any camera: the per-object table, a graybox frame, a depth pass, a proxy clip.

    python3 scene_proxy.py <scene.json> <out-prefix> [VIEW] [--size 480] [--table table.json]
    python3 scene_proxy.py <scene.json> <out-prefix> --move "A -> B" --seconds 4 --fps 24 --mp4 clip.mp4
    python3 scene_proxy.py <scene.json> <out-prefix> --move "A -> B" --extremes [--band 0.1] [--rise 0.15] [--samples 9]
    python3 scene_proxy.py --selftest

VIEW is `source` (the keeper's own camera, default), `top` (floor plan), `reverse` (mirrored through the
scene centre, kept inside the room), or an explicit camera `px,py,pz,tx,ty,tz[,fov]` in scene units.
`--move` takes two such cameras; the clip eases from A to B and writes <mp4>.json beside it with the
scene's sha256 — the fingerprint the gate diffs (ASSET-HYGIENE.md). Needs numpy + Pillow; ffmpeg for --mp4.
`--extremes` renders the move at --samples points instead of a clip and measures VOID (pixels that hit no
geometry) in a --band of each frame edge, against the keeper's own camera: an edge whose void rises more than
--rise above the source camera's is a shell that does not cover the move — the generator invents what the proxy
leaves black. A measurement exits 0; with --strict it exits 1 when any edge reads SHELL SHORT (for a channel where
the proxy is the only room picture — SCENE-PROXY.md § Check the shell at the move's extremes).
No ComfyUI, no browser. Scene units are relative (a seated person ≈ 0.9), never metric.
"""
import argparse, hashlib, json, math, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

SOLID = {"cube", "human", "card", "sphere", "glb", "model"}


def basis(position, target, roll=0.0):
    fwd = np.asarray(target, float) - np.asarray(position, float)
    n = np.linalg.norm(fwd); fwd = fwd / n if n > 1e-9 else np.array([0.0, 0.0, -1.0])
    up = np.array([0.0, 1.0, 0.0])
    right = np.cross(fwd, up)
    if np.linalg.norm(right) < 1e-9:
        up = np.array([0.0, 0.0, -1.0 if fwd[1] > 0 else 1.0]); right = np.cross(fwd, up)
    right /= np.linalg.norm(right); up = np.cross(right, fwd); up /= np.linalg.norm(up)
    a = math.radians(roll); c, s = math.cos(a), math.sin(a)
    return right * c + up * s, up * c - right * s, fwd


def euler_xyz(deg):
    x, y, z = (math.radians(float(v)) for v in deg)
    rx = np.array([[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]])
    ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    rz = np.array([[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]])
    return rx @ ry @ rz


def world_transform(objects, obj):
    """(centre, rotation matrix, size) through the parent chain (nulls carry position/rotation only)."""
    by_id = {o["id"]: o for o in objects}
    pos = np.asarray(obj.get("position", [0, 0, 0]), float)
    rot = euler_xyz(obj.get("rotation", [0, 0, 0]))
    size = np.asarray(obj.get("size", [1, 1, 1]), float)
    if obj.get("type") == "card" and len(size) >= 2:
        size = np.array([size[0], size[1], size[2] if len(size) > 2 and size[2] > 0.02 else 0.02])
    parent = by_id.get(obj.get("parent_id") or "")
    depth = 0
    while parent is not None and depth < 16:
        prot = euler_xyz(parent.get("rotation", [0, 0, 0])); ppos = np.asarray(parent.get("position", [0, 0, 0]), float)
        pos = prot @ pos + ppos; rot = prot @ rot
        parent = by_id.get(parent.get("parent_id") or ""); depth += 1
    return pos, rot, np.maximum(size, 0.01)


def render(cam, W, H, objects):
    right, up, fwd = basis(cam["position"], cam["target"], cam.get("roll", 0.0))
    f = 0.5 * H / math.tan(math.radians(cam["fov"]) * 0.5)
    ys, xs = np.mgrid[0:H, 0:W]
    dirs = (xs - W / 2)[..., None] * right + (H / 2 - ys)[..., None] * up + f * fwd
    dirs /= np.linalg.norm(dirs, axis=-1, keepdims=True)
    o = np.asarray(cam["position"], float)
    depth = np.full((H, W), np.inf); shade = np.zeros((H, W)); ids = np.zeros((H, W), int)
    for k, obj in enumerate(objects, 1):
        if obj.get("type") not in SOLID | {"ground"} or not obj.get("enabled", True):
            continue
        c, rot, size = world_transform(objects, obj)
        axes = rot.T                                   # rows = the box's local axes in world space
        half = size / 2
        ol = axes @ (o - c); dl = np.einsum("ij,hwj->hwi", axes, dirs)
        with np.errstate(divide="ignore", invalid="ignore"):
            t1 = (-half - ol) / dl; t2 = (half - ol) / dl
            tmin = np.max(np.minimum(t1, t2), axis=-1); tmax = np.min(np.maximum(t1, t2), axis=-1)
            hit = tmax >= np.maximum(tmin, 1e-4)
            t = np.where(hit, tmin, np.inf); closer = t < depth
            p = ol[None, None, :] + dl * np.where(np.isfinite(t), t, 0.0)[..., None]
        face = np.argmax(np.abs(p) / half, axis=-1)
        lum = np.select([face == 0, face == 1, face == 2], [0.55, 0.85, 0.7], 0.5)
        if obj.get("type") == "human":
            lum = lum * 0.75
        depth = np.where(closer, t, depth); shade = np.where(closer, lum, shade); ids = np.where(closer, k, ids)
    return depth, shade, ids


def project(point, cam, W, H):
    right, up, fwd = basis(cam["position"], cam["target"], cam.get("roll", 0.0))
    rel = np.asarray(point, float) - np.asarray(cam["position"], float)
    z = float(rel @ fwd)
    if z <= 1e-4:
        return None
    f = 0.5 * H / math.tan(math.radians(cam["fov"]) * 0.5)
    return W * 0.5 + float(rel @ right) * f / z, H * 0.5 - float(rel @ up) * f / z, z


def parse_cam(spec, base):
    v = [float(x) for x in spec.replace(" ", "").split(",")]
    if len(v) < 6:
        sys.exit("camera spec needs px,py,pz,tx,ty,tz[,fov]")
    return {"position": v[0:3], "target": v[3:6], "fov": v[6] if len(v) > 6 else base["fov"], "roll": 0.0}


def solids(objects):
    return [o for o in objects if o.get("type") in SOLID and o.get("enabled", True)]


def table(cam, W, H, objects, ids):
    rows = []
    for k, obj in enumerate(objects, 1):
        if obj.get("type") not in SOLID or not obj.get("enabled", True):
            continue
        c, _, _ = world_transform(objects, obj)
        pr = project(c, cam, W, H); px = int((ids == k).sum())
        label = obj.get("name") or obj["id"]
        if pr is None:
            rows.append({"object": obj["id"], "label": label, "read": "behind the camera", "px": px}); continue
        x, y, z = pr; xf, yf = x / W, y / H
        lr = "left" if xf < 0.4 else ("right" if xf > 0.6 else "centre")
        inside = 0 <= xf <= 1 and 0 <= yf <= 1
        vis = "in frame" if inside and px else ("occluded" if inside else "out of frame")
        rows.append({"object": obj["id"], "label": label, "x_pct": round(xf * 100), "y_pct": round(yf * 100),
                     "depth": round(z, 2), "px": px, "read": f"{lr}, {vis}"})
    rows.sort(key=lambda r: (r.get("depth") is None, r.get("depth", 0)))
    return rows


def save_view(cam, W, H, objects, out, name):
    depth, shade, ids = render(cam, W, H, objects)
    finite = np.isfinite(depth); d = np.where(finite, depth, 0.0); dn = np.zeros_like(d)
    if finite.any():
        lo, hi = d[finite].min(), d[finite].max(); dn[finite] = 1 - (d[finite] - lo) / max(hi - lo, 1e-6)
    Image.fromarray((dn * 255).astype(np.uint8)).save(f"{out}-{name}-depth.png")
    gray = Image.fromarray((np.where(finite, shade, 0.12) * 255).astype(np.uint8)).convert("RGB")
    draw = ImageDraw.Draw(gray)
    rows = table(cam, W, H, objects, ids)
    for r in rows:
        if r.get("px") and "in frame" in r["read"]:
            draw.text((r["x_pct"] / 100 * W + 2, r["y_pct"] / 100 * H - 6), r["object"].split("_")[0], fill=(255, 220, 0))
    gray.save(f"{out}-{name}-gray.png")
    return rows


def ease(t):
    return t * t * (3 - 2 * t)


EDGES = ("left", "right", "top", "bottom")


def edge_voids(cam, W, H, objects, band):
    """Share of each edge band's pixels whose ray hits no geometry."""
    depth, _, _ = render(cam, W, H, objects)
    hole = ~np.isfinite(depth); bw = max(1, round(W * band)); bh = max(1, round(H * band))
    return {"left": float(hole[:, :bw].mean()), "right": float(hole[:, -bw:].mean()),
            "top": float(hole[:bh].mean()), "bottom": float(hole[-bh:].mean())}


def lerp_cam(A, B, u):
    return {"position": [(1 - u) * x + u * y for x, y in zip(A["position"], B["position"])],
            "target": [(1 - u) * x + u * y for x, y in zip(A["target"], B["target"])],
            "fov": (1 - u) * A["fov"] + u * B["fov"], "roll": 0.0}


def extremes(objects, src, A, B, W, H, samples=9, band=0.1, rise=0.15, seconds=4.0):
    """The eased move sampled edge by edge against the keeper's camera -> (source voids, rows, short edges)."""
    k = max(2, samples); base = edge_voids(src, W, H, objects, band); rows = []
    for i in range(k):
        u = i / (k - 1); rows.append((round(u * seconds, 2), edge_voids(lerp_cam(A, B, ease(u)), W, H, objects, band)))
    short = []
    for e in EDGES:
        t, v = max(rows, key=lambda r: r[1][e])
        if v[e] - base[e] > rise:
            short.append((e, t, v[e], base[e]))
    return base, rows, short


def selftest():
    """Known answer: a back wall alone leaves the leading edge of a 35° yaw black; two side walls cover it."""
    ground = {"id": "ground", "type": "ground", "position": [0, -0.01, -1], "size": [12, 0.02, 12]}
    back = {"id": "back_wall", "type": "cube", "position": [0, 1.5, -4], "size": [4, 3, 0.2]}
    sides = [{"id": "left_wall", "type": "cube", "position": [-2, 1.5, -1.5], "size": [0.2, 3, 5]},
             {"id": "right_wall", "type": "cube", "position": [2, 1.5, -1.5], "size": [0.2, 3, 5]}]
    A = {"position": [0, 1.2, 2], "target": [0, 1.2, -4], "fov": 60.0, "roll": 0.0}
    B = {"position": [0, 1.2, 2], "target": [4.2, 1.2, -4], "fov": 60.0, "roll": 0.0}
    ok = True
    for name, objs, want in (("open", [ground, back], lambda s: "right" in s), ("closed", [ground, back] + sides, lambda s: not s)):
        base, rows, short = extremes(objs, A, A, B, 216, 384)
        got = sorted(e for e, *_ in short); passed = want(got); ok &= passed
        print(f"selftest {name:6} short edges {got} · right band: source {base['right']:.0%}, worst {max(r[1]['right'] for r in rows):.0%}"
              f"  {'PASS' if passed else 'FAIL'}")
    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scene", nargs="?"); ap.add_argument("out", nargs="?"); ap.add_argument("view", nargs="?", default="source")
    ap.add_argument("--size", type=int, default=480, help="render width in px (height follows the canvas)")
    ap.add_argument("--table", help="also write the per-object table as JSON")
    ap.add_argument("--move", help='"px,py,pz,tx,ty,tz,fov -> px,py,pz,tx,ty,tz,fov" for a proxy clip')
    ap.add_argument("--seconds", type=float, default=4.0); ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--mp4", help="write the proxy clip here (needs ffmpeg)")
    ap.add_argument("--extremes", action="store_true", help="with --move: measure edge void along the move instead of rendering a clip")
    ap.add_argument("--band", type=float, default=0.1, help="edge band width as a share of the frame (default 0.1)")
    ap.add_argument("--rise", type=float, default=0.15, help="void rise over the keeper's camera that reads as SHELL SHORT (default 0.15)")
    ap.add_argument("--samples", type=int, default=9, help="points sampled along the move, ends included (default 9)")
    ap.add_argument("--strict", action="store_true", help="with --extremes: exit 1 when any edge reads SHELL SHORT")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not a.scene or not a.out:
        ap.error("scene and out-prefix are required (or --selftest)")
    raw = Path(a.scene).read_bytes(); res = json.loads(raw)
    ms = res["motion_scene"] if "motion_scene" in res else res
    objects = ms["objects"]
    src = dict(ms["cameras"][0]["track"]["keyframes"][0]["camera"]); src.setdefault("roll", 0.0)
    W = a.size; H = round(W * ms["canvas"]["height"] / ms["canvas"]["width"])
    sol = solids(objects)
    centres = np.array([world_transform(objects, o)[0] for o in sol]) if sol else np.array([src["target"]])
    centre = centres.mean(axis=0)

    if a.move:
        specs = [s.strip() for s in a.move.split("->")]
        if len(specs) != 2:
            sys.exit('--move needs "A -> B"')
        A, B = parse_cam(specs[0], src), parse_cam(specs[1], src)
        if a.extremes:
            base, rows, short = extremes(objects, src, A, B, W, H, a.samples, a.band, a.rise, a.seconds)
            print(f"edge void = share of a {a.band:.0%} edge band whose rays hit no geometry | {W}x{H} | SHELL SHORT above +{a.rise:.0%}")
            print(f"{'t s':>7} " + " ".join(f"{e:>7}" for e in EDGES))
            print(f"{'keeper':>7} " + " ".join(f"{base[e]:>7.0%}" for e in EDGES))
            for t, v in rows:
                print(f"{t:>7} " + " ".join(f"{v[e]:>7.0%}" for e in EDGES))
            for e, t, v, b in short:
                print(f"SHELL SHORT {e}: {v:.0%} void at {t} s against {b:.0%} at the keeper's camera — add the missing wall or "
                      f"box by hand (SCENE-PROXY § Build it) or shorten the move")
            if not short:
                print("COVERED: no edge's void rises more than the limit above the keeper's camera")
            sys.exit(1 if short and a.strict else 0)
        n = max(2, round(a.seconds * a.fps)); tmp = Path(tempfile.mkdtemp(prefix="scene-proxy-"))
        for i in range(n):                                    # frame times [0, (n-1)/fps]
            u = ease(i / (n - 1)); cam = {"position": [(1 - u) * x + u * y for x, y in zip(A["position"], B["position"])],
                                          "target": [(1 - u) * x + u * y for x, y in zip(A["target"], B["target"])],
                                          "fov": (1 - u) * A["fov"] + u * B["fov"], "roll": 0.0}
            _, shade, _ = render(cam, W, H, objects)
            Image.fromarray((np.where(np.isfinite(_), shade, 0.12) * 255).astype(np.uint8)).save(tmp / f"f{i:05d}.png")
        rows_a = table(A, W, H, objects, render(A, W, H, objects)[2]); rows_b = table(B, W, H, objects, render(B, W, H, objects)[2])
        if a.mp4:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps), "-i", str(tmp / "f%05d.png"),
                            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "18", a.mp4], check=True)
            Path(a.mp4 + ".json").write_text(json.dumps({"scene": str(Path(a.scene).resolve()),
                "scene_sha256": hashlib.sha256(raw).hexdigest(), "camera_a": A, "camera_b": B,
                "seconds": a.seconds, "fps": a.fps, "frames": n, "size": [W, H],
                "table_a": rows_a, "table_b": rows_b}, indent=1))
            print(f"wrote {a.mp4} ({n} frames, {W}x{H}) + {a.mp4}.json (scene fingerprint + tables)")
        else:
            print(f"rendered {n} frames under {tmp}")
        for tag, rows in (("A", rows_a), ("B", rows_b)):
            print(f"-- camera {tag}");
            for r in rows: print(f"   {r['object']:26} {r.get('x_pct', ''):>4} {r.get('depth', ''):>6}  {r['read']}")
        return

    if a.view == "source":
        cam = src
    elif a.view == "top":
        span = float(np.ptp(centres, axis=0).max()) if len(centres) > 1 else 4.0
        cam = {"position": (centre + [0.0, span * 1.6 + 2.0, 0.001]).tolist(), "target": centre.tolist(), "fov": 70.0, "roll": 0.0}
    elif a.view == "reverse":
        p = np.asarray(src["position"], float); d = (p - centre) * np.array([1, 0, 1])
        lo, hi = centres.min(axis=0) - 0.5, centres.max(axis=0) + 0.5
        pos = np.clip(centre - d, lo, hi); pos[1] = p[1]
        cam = {"position": pos.tolist(), "target": centre.tolist(), "fov": src["fov"], "roll": 0.0}
    else:
        cam = parse_cam(a.view, src)
    name = a.view if "," not in a.view else "custom"
    rows = save_view(cam, W, H, objects, a.out, name)
    print(f"camera {[round(v, 2) for v in cam['position']]} -> {[round(v, 2) for v in cam['target']]} fov {cam['fov']:.0f} | {W}x{H} | "
          f"{a.out}-{name}-gray.png + -depth.png")
    print(f"{'object':26} {'x%':>4} {'y%':>4} {'depth':>6} {'px':>6}  read")
    for r in rows:
        print(f"{r['object']:26} {r.get('x_pct', ''):>4} {r.get('y_pct', ''):>4} {r.get('depth', ''):>6} {r['px']:>6}  {r['read']}")
    if a.table:
        Path(a.table).write_text(json.dumps({"camera": cam, "size": [W, H], "rows": rows,
                                             "scene_sha256": hashlib.sha256(raw).hexdigest()}, indent=1))


if __name__ == "__main__":
    main()
