#!/usr/bin/env python3
"""Keeper frame -> labelled grey-box scene, headless, through the ComfyUI server that carries OmniCam.

    python3 scene_blockout.py <frame.png> [--out PREFIX] [--labels a,b,c] [--mode blockout|hybrid|depth_mesh]
                               [--threshold 0.55] [--no-walls] [--host URL]

Writes <PREFIX>.scene.json (the MotionScene + summary the route returned) and prints the object table.
Needs: a RUNNING ComfyUI server (the browser is not needed) with the OmniCam custom node, a MoGe checkpoint
under models/geometry_estimation and a sam3* checkpoint under models/checkpoints. The host comes from
--host or the COMFY_HOST env var; it is never written into this skill. Cost: $0, ~15-25 s per frame.
Fails closed: a server that does not answer, a missing checkpoint or a failed job stops with the reason.
"""
import argparse, json, mimetypes, os, sys, time, uuid, urllib.error, urllib.request
from pathlib import Path

DEFAULT_LABELS = ["person", "sofa", "armchair", "chair", "table", "coffee table", "bed", "door", "window",
                  "lamp", "television", "fireplace", "shelf", "plant", "car", "building", "tree"]
SUBFOLDER = "scene-proxy"


def call(host, path, body=None, files=None, timeout=90):
    if files:
        boundary = uuid.uuid4().hex
        chunks = []
        for name, value in (body or {}).items():
            chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
        for name, p in files.items():
            ctype = mimetypes.guess_type(p)[0] or "application/octet-stream"
            chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{Path(p).name}\"\r\n"
                          f"Content-Type: {ctype}\r\n\r\n".encode() + Path(p).read_bytes() + b"\r\n")
        chunks.append(f"--{boundary}--\r\n".encode())
        data, headers = b"".join(chunks), {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    else:
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(host + path, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on {path}: {e.read().decode(errors='replace')[:500]}")
    except urllib.error.URLError as e:
        sys.exit(f"ComfyUI server not reachable at {host} ({e.reason}). It must be RUNNING (no browser needed).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--out", help="output prefix (default: <image stem>-scene)")
    ap.add_argument("--labels", help="comma list of SAM3 labels; set it PER SCENE to kill phantoms")
    ap.add_argument("--mode", default="blockout", choices=["blockout", "hybrid", "depth_mesh"])
    ap.add_argument("--threshold", type=float, default=0.55, help="SAM3 score floor; raise to drop phantoms")
    ap.add_argument("--no-walls", action="store_true")
    ap.add_argument("--host", default=os.environ.get("COMFY_HOST", ""), help="ComfyUI URL (or COMFY_HOST)")
    a = ap.parse_args()
    if not a.host:
        sys.exit("set --host or COMFY_HOST to the ComfyUI server URL")
    host = a.host.rstrip("/")
    out = a.out or (Path(a.image).stem + "-scene")
    labels = [s.strip() for s in a.labels.split(",")] if a.labels else DEFAULT_LABELS

    caps = call(host, "/majoor/omnicam/reconstruction/capabilities")
    geo = {p["provider_id"]: p for p in caps.get("geometry", [])}
    seg = {p["provider_id"]: p for p in caps.get("segmentation", [])}
    for pid, table in (("comfy_moge", geo), ("comfy_sam3", seg)):
        if pid == "comfy_sam3" and a.mode == "depth_mesh":
            continue
        if not table.get(pid, {}).get("available"):
            sys.exit(f"provider {pid} unavailable: {table.get(pid, {}).get('reason', 'not registered')}")

    up = call(host, "/upload/image", {"subfolder": SUBFOLDER, "overwrite": "true"}, files={"image": a.image})
    ref = f"{up['subfolder']}/{up['name']} [input]" if up.get("subfolder") else f"{up['name']} [input]"
    body = {"node_id": f"scene-{Path(a.image).stem[:40]}", "client_id": "sceneproxy",
            "source": {"kind": "annotated_input", "value": ref},
            "settings": {"mode": a.mode, "quality": "balanced", "provider": "comfy_moge",
                         "segmentation_provider": "comfy_sam3", "sam3_threshold": a.threshold,
                         "semantic_labels": labels, "max_blockout_objects": 24, "detect_ground": True,
                         "detect_walls": not a.no_walls, "source_texture": False}}
    job = call(host, "/majoor/omnicam/reconstruction/jobs", body)
    jid, t0, last = job["job_id"], time.time(), ""
    while True:
        s = call(host, f"/majoor/omnicam/reconstruction/jobs/{jid}?client_id=sceneproxy")
        line = f"{s['state']} {s.get('stage', '')} {s.get('message', '')}"
        if line != last:
            print(f"  {time.time() - t0:5.1f}s {line}", file=sys.stderr); last = line
        if str(s["state"]).upper() in ("DONE", "FAILED", "STOPPED"):
            break
        if time.time() - t0 > 600:
            sys.exit("job timeout after 600 s")
        time.sleep(2)
    if str(s["state"]).upper() != "DONE":
        sys.exit(f"job {s['state']}: {json.dumps(s.get('error'))}")
    res = call(host, f"/majoor/omnicam/reconstruction/jobs/{jid}/result?client_id=sceneproxy")
    res["source_image"] = str(Path(a.image).resolve()); res["labels"] = labels
    Path(f"{out}.scene.json").write_text(json.dumps(res, indent=1))
    ms = res["motion_scene"]; cam = ms["cameras"][0]["track"]["keyframes"][0]["camera"]
    print(f"saved {out}.scene.json | {time.time() - t0:.0f} s | warnings {res.get('warnings')}")
    print(f"canvas {ms['canvas']['width']}x{ms['canvas']['height']} | source camera at {[round(v, 2) for v in cam['position']]} "
          f"fov {cam['fov']:.0f} | relative units, NOT metric")
    print(f"{'object':28} {'type':6} {'position x,y,z':26} {'size w,h,d':22} conf")
    for o in ms["objects"]:
        if o["type"] == "null":
            continue
        r = o.get("reconstruction", {})
        print(f"{o['id'][:28]:28} {o['type']:6} {str([round(v, 2) for v in o['position']]):26} "
              f"{str([round(v, 2) for v in o['size']]):22} {r.get('confidence', 0):.2f}")


if __name__ == "__main__":
    main()
