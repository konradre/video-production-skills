#!/usr/bin/env python3
"""comfy_ready.py — is the ComfyUI server up, and does its OmniCam reconstruction route have its providers?

Reads COMFY_HOST (default http://127.0.0.1:8188). Exit 0 when the server answers /system_stats AND the
route lists an available geometry provider (MoGe) and segmentation provider (SAM3); exit 1 otherwise, with
the reason. --wait N polls for up to N seconds (a starting server); --server-only skips the provider check.

    python3 scripts/comfy_ready.py [--wait 120] [--server-only]
"""
import argparse, json, os, sys, time, urllib.error, urllib.request

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188").rstrip("/")
ROUTE = "/majoor/omnicam/reconstruction/capabilities"


def get(path, timeout=6):
    with urllib.request.urlopen(HOST + path, timeout=timeout) as r:
        return json.load(r)


def check(server_only):
    try:
        stats = get("/system_stats")
    except (urllib.error.URLError, OSError, ValueError) as e:
        return False, f"no server at {HOST}: {e}"
    ver = stats.get("system", {}).get("comfyui_version", "?")
    if server_only:
        return True, f"server up ({ver})"
    try:
        caps = get(ROUTE)
    except urllib.error.HTTPError as e:
        return False, f"server up ({ver}) but {ROUTE} → HTTP {e.code}: the OmniCam custom node is not installed or not loaded"
    except (urllib.error.URLError, OSError, ValueError) as e:
        return False, f"server up ({ver}) but {ROUTE} failed: {e}"
    def available(key):  # the route lists geometry and segmentation providers separately; "fake" is a test stub
        return [p.get("provider_id") for p in caps.get(key, []) if p.get("available") and p.get("provider_id") != "fake"]
    geo = next((k for k in available("geometry") or available("providers") if "moge" in k), None)
    seg = next((k for k in available("segmentation") if "sam3" in k), None)
    if not geo or not seg:
        missing = [n for n, v in (("MoGe checkpoint under models/geometry_estimation/", geo),
                                  ("SAM3 checkpoint under models/checkpoints/", seg)) if not v]
        return False, f"server up ({ver}), route present, providers missing: {'; '.join(missing)}"
    return True, f"server up ({ver}); providers {geo} + {seg} available"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--wait", type=float, default=0); ap.add_argument("--server-only", action="store_true")
    a = ap.parse_args(); t0 = time.time()
    while True:
        ok, why = check(a.server_only)
        if ok or time.time() - t0 >= a.wait:
            print(("READY: " if ok else "NOT READY: ") + why); sys.exit(0 if ok else 1)
        time.sleep(3)


if __name__ == "__main__":
    main()
