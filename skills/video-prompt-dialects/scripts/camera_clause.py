#!/usr/bin/env python3
"""Derive the camera clause from an authored move instead of writing it from memory.

    python3 camera_clause.py --from "px,py,pz,tx,ty,tz,fov" --to "px,py,pz,tx,ty,tz,fov" [--seconds 4] [--h3]
    python3 camera_clause.py --sidecar clip.mp4.json [--h3]          # the sidecar scene_proxy.py writes

Prints the observable move — dolly / truck / crane / pan / tilt / orbit around the target / zoom — with its
magnitude, the lens class and the pace, then the house sentence for Seedance (`move + subject + start +
direction + arrival`, with SUBJECT / START / ARRIVAL left for the shot document) and, with --h3, the
timecoded MiniMax form plus the motion-only role line for a proxy clip. Units are scene units (relative).
"""
import argparse, json, math, sys

EPS_T, EPS_R, EPS_F = 0.05, 2.0, 1.0        # units, degrees, degrees — below these an axis is "held"


def unit(v):
    n = math.sqrt(sum(x * x for x in v)); return [x / n for x in v] if n > 1e-9 else [0.0, 0.0, -1.0]


def basis(pos, tgt):
    fwd = unit([t - p for p, t in zip(pos, tgt)])
    up = [0.0, 1.0, 0.0]
    right = [fwd[1] * up[2] - fwd[2] * up[1], fwd[2] * up[0] - fwd[0] * up[2], fwd[0] * up[1] - fwd[1] * up[0]]
    right = unit(right); up = unit([right[1] * fwd[2] - right[2] * fwd[1], right[2] * fwd[0] - right[0] * fwd[2], right[0] * fwd[1] - right[1] * fwd[0]])
    return right, up, fwd


def parse(spec):
    v = [float(x) for x in spec.replace(" ", "").split(",")]
    if len(v) < 6:
        sys.exit("camera spec needs px,py,pz,tx,ty,tz[,fov]")
    return {"position": v[0:3], "target": v[3:6], "fov": v[6] if len(v) > 6 else 50.0}


def lens_class(fov_deg, sensor_mm=24.0):
    f = sensor_mm / (2 * math.tan(math.radians(max(1.0, fov_deg)) / 2))
    cls = "ultra-wide" if f < 20 else "wide-angle" if f < 30 else "standard" if f < 60 else "portrait" if f < 110 else "telephoto"
    return f, cls


def analyse(A, B, seconds):
    right, up, fwd = basis(A["position"], A["target"])
    d = [b - a for a, b in zip(A["position"], B["position"])]
    dolly, truck, crane = (sum(x * y for x, y in zip(d, ax)) for ax in (fwd, right, up))
    fa, fb = basis(A["position"], A["target"])[2], basis(B["position"], B["target"])[2]
    pan = math.degrees(math.atan2(fb[0], -fb[2]) - math.atan2(fa[0], -fa[2])); pan = (pan + 180) % 360 - 180
    tilt = math.degrees(math.asin(max(-1, min(1, fb[1]))) - math.asin(max(-1, min(1, fa[1]))))
    ta, tb = A["target"], B["target"]
    target_held = math.dist(ta, tb) < EPS_T
    az_a = math.atan2(A["position"][0] - ta[0], A["position"][2] - ta[2]); az_b = math.atan2(B["position"][0] - tb[0], B["position"][2] - tb[2])
    orbit = math.degrees((az_b - az_a + math.pi) % (2 * math.pi) - math.pi) if target_held else 0.0
    zoom = B["fov"] - A["fov"]
    path = math.sqrt(sum(x * x for x in d)); speed = path / max(seconds, 1e-6)
    pace = "slow and steady" if speed < 1.0 else "moderate" if speed < 3.0 else "fast, dynamic"
    # Each axis is scored against its own noise floor; the dominant axis names the move and a second axis
    # is reported only when it carries >= 35 % of the dominant score (a push-in with a little drift is a
    # push-in, not five moves). An orbit — position sweeping around a held target — outranks its parts.
    phrases = {"dolly": ("pushes in toward the subject" if dolly > 0 else "pulls back from the subject", abs(dolly) / EPS_T),
               "truck": (f"tracks laterally to camera-{'right' if truck > 0 else 'left'}", abs(truck) / EPS_T),
               "crane": ("cranes upward" if crane > 0 else "cranes downward", abs(crane) / EPS_T),
               "pan": (f"pans {'right' if pan > 0 else 'left'} {abs(round(pan))}°", abs(pan) / EPS_R),
               "tilt": (f"tilts {'up' if tilt > 0 else 'down'} {abs(round(tilt))}°", abs(tilt) / EPS_R),
               "zoom": ("zooms out optically" if zoom > 0 else "zooms in optically", abs(zoom) / EPS_F)}
    words, tags = [], []
    if target_held and abs(orbit) > 20 and path > EPS_T:
        words.append(f"arcs around the subject to camera-{'right' if truck > 0 else 'left'}, a {abs(round(orbit))}° orbit"); tags.append("orbit")
        if phrases["zoom"][1] > 1: words.append(phrases["zoom"][0]); tags.append("zoom")
    else:
        ranked = sorted(phrases.items(), key=lambda kv: -kv[1][1])
        top = ranked[0][1][1]
        for axis, (phrase, score) in ranked:
            if score > 1 and (axis == ranked[0][0] or score >= 0.35 * top):
                words.append(phrase); tags.append(axis)
    if not words: words.append("holds a locked, static frame"); tags.append("hold")
    f_mm, cls = lens_class(A["fov"])
    return {"words": words, "tags": tags, "dolly": round(dolly, 2), "truck": round(truck, 2), "crane": round(crane, 2),
            "pan_deg": round(pan, 1), "tilt_deg": round(tilt, 1), "orbit_deg": round(orbit, 1), "zoom_deg": round(zoom, 1),
            "path": round(path, 2), "speed": round(speed, 2), "pace": pace, "focal_mm": round(f_mm, 1), "lens": cls,
            "compound": len(tags) > 1}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="a"); ap.add_argument("--to", dest="b"); ap.add_argument("--seconds", type=float, default=4.0)
    ap.add_argument("--sidecar", help="clip.mp4.json from scene_proxy.py --move")
    ap.add_argument("--h3", action="store_true", help="also print the MiniMax timecoded form + the proxy-clip role line")
    ap.add_argument("--phone", action="store_true", help="also print the phone-native clause (a handheld iPhone shot at arm's length — references/PHONE-NATIVE.md)")
    argv, it = [], iter(sys.argv[1:])            # a camera that starts with a minus sign is a value, not a flag
    for tok in it:
        if tok in ("--from", "--to", "--seconds", "--sidecar"):
            argv.append(f"{tok}={next(it, '')}")
        else:
            argv.append(tok)
    a = ap.parse_args(argv)
    if a.sidecar:
        sc = json.load(open(a.sidecar)); A, B, seconds = sc["camera_a"], sc["camera_b"], float(sc.get("seconds", a.seconds))
    elif a.a and a.b:
        A, B, seconds = parse(a.a), parse(a.b), a.seconds
    else:
        sys.exit("give --from/--to or --sidecar")
    r = analyse(A, B, seconds)
    move = ", then ".join(r["words"]) if r["compound"] else r["words"][0]
    print(f"move: {move}")
    print(f"magnitudes: dolly {r['dolly']} · truck {r['truck']} · crane {r['crane']} · pan {r['pan_deg']}° · tilt {r['tilt_deg']}° · "
          f"orbit {r['orbit_deg']}° · zoom {r['zoom_deg']}° | path {r['path']} u in {seconds:g} s → {r['pace']} | "
          f"{r['focal_mm']} mm {r['lens']} lens")
    if r["compound"]:
        print("WARNING: compound move — the dialect wants ONE move per shot; split the cut or drop the weaker axis")
    print("\nSeedance clause (fill SUBJECT / START / ARRIVAL from the shot document):")
    print(f"  The camera {move} on SUBJECT, starting on START and arriving on ARRIVAL; {r['pace']}, one continuous move, no cut.")
    if a.phone:
        # The phone register has no dolly, crane or orbit words: the same measured move, said as a person holding a
        # front camera would make it. The device is named as the camera that shot it, never as a prop (PHONE-NATIVE.md, house
        # rule 2026-09-25).
        phone_words = {"hold": "stays on", "dolly": ("leans in toward" if r["dolly"] > 0 else "leans back from"),
                       "truck": "shifts sideways across", "crane": ("lifts up over" if r["crane"] > 0 else "lowers down on"),
                       "pan": "turns toward", "tilt": ("tips up toward" if r["tilt_deg"] > 0 else "tips down toward"),
                       "orbit": "walks around", "zoom": ("pinches in on" if r["zoom_deg"] < 0 else "pinches out from")}
        pm = phone_words.get(r["tags"][0], "stays on")
        print("\nPhone-native clause (a handheld iPhone shot — PHONE-NATIVE.md; fill SUBJECT / START / ARRIVAL):")
        print(f"  Handheld iPhone shot, the front camera held at arm's length; the frame {pm} SUBJECT, drifting slightly with the breath, "
              f"starting on START and settling on ARRIVAL; one continuous take, no cut.")
        if r["compound"]:
            print("  WARNING: a phone shot is ONE small move — a compound move is two shots, cut in the edit")
    if a.h3:
        print("\nH3 form:")
        print(f"  [0.0-{seconds:.1f}s] The camera {move}.")
        # This role line is a NEGATION. It is safe only while <Video 1> is actually passed on the call:
        # H3 has one positive stream, so with no referent it renders the nouns it names (a floor grid and
        # cyan/red markers, measured 2026-09-11). Drop the clip, drop this line. prompt_lint L31 gates it.
        print("  Use <Video 1> only as the camera-motion and shot-timing reference. Do not reproduce its proxy geometry, "
              "grid, markers, textures, colours or placeholder materials. Preserve the subject identity, scene appearance "
              "and visual styling described by the main prompt and the other references.")


if __name__ == "__main__":
    main()
