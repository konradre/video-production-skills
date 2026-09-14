"""resolve_pass.py — the unattended hero-pass batch on the Resolve host.

Per input clip: import to media pool -> own timeline -> ApplyGradeFromDRX(look) ->
mezzanine render (--format/--codec, default MP4/H264 8-bit, bt709) -> JSON result.
⚠️ H.264/H.265 here are 8-bit; for a 10-bit graded mezzanine pass --format mov --codec ProRes422HQ
(or --format avi --codec GoProYUV10, which pads width to a multiple of 16). --list-codecs prints
what this install actually offers.
Hand-off: the ffmpeg deliver leg takes the mezzanine.

Corpus patterns: samuelgursky granular bare-apply + busy-guard; mhadifilms idempotent
project open; chaiwithjai render loop; one render job at a time.
Look library: look-library/drx/<id>.drx (LOOK_LIBRARY_DRX or --drx-dir; hashed in look-library/index.json).

Run from WSL (Resolve open with a project):
  cd tools/resolve-pass && <win-python> resolve_pass.py --look film-portra \
      --in "C:\\...\\clip.mp4" [--in ...] [--out-dir "C:\\hero-pass\\renders"] [--wait 60] [--transport auto|local|bridge]
Accepts /mnt/<d>/... and /home/... input paths (auto-translated for Resolve).

Transports (the samuelgursky/davinci-resolve-mcp ladder, `resolve_connection.py`):
  1. Studio external scripting — `scriptapp("Resolve")` (Local), or `scriptapp("Resolve", host, timeout)`
     when RESOLVE_SCRIPT_HOST is set (Network);
  2. the in-app bridge — a script started from Workspace ▸ Scripts ▸ resolve_bridge re-exports the live
     `resolve` object over an HMAC loopback socket (the repository at DAVINCI_RESOLVE_MCP_DIR). It does
     not care about the licence gate or who launched Resolve — every agent-launched instance we tried
     refused external scripting while the bridge path stayed open.
`--wait N` polls both for up to N seconds (Resolve takes ~40 s to boot; the API answers only once a project
manager is up). Diagnostics name the four causes external scripting refuses for.
"""
import argparse
import glob
import json
import os
import sys
import time

os.environ.setdefault("RESOLVE_SCRIPT_API", r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting")
os.environ.setdefault("RESOLVE_SCRIPT_LIB", r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll")
sys.path.append(os.path.join(os.environ["RESOLVE_SCRIPT_API"], "Modules"))

PROJ_NAME = os.environ.get("RESOLVE_PASS_PROJECT", "hero-pass")
BRIDGE_REPO = os.environ.get("DAVINCI_RESOLVE_MCP_DIR", r"C:\tools\davinci-resolve-mcp")
DISTRO = os.environ.get("RESOLVE_PASS_DISTRO", "Ubuntu")
DRX_DIR = os.environ.get("LOOK_LIBRARY_DRX", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "look-library", "drx"))


def win_path(p):
    """Translate WSL paths to Windows for Resolve; pass Windows paths through."""
    if p.startswith("/mnt/") and len(p) > 6:
        return f"{p[5].upper()}:{p[6:]}".replace("/", "\\")
    if p.startswith("/"):
        return rf"\\wsl.localhost\{DISTRO}" + p.replace("/", "\\")
    return p


def die(msg):
    print(json.dumps({"ok": False, "error": msg}))
    print("RESOLVE-PASS-FAIL")
    sys.exit(2)


def _external(dvr):
    """Transport 1 — Studio external scripting (Local, or Network when RESOLVE_SCRIPT_HOST is set)."""
    host = os.environ.get("RESOLVE_SCRIPT_HOST")
    try:
        return dvr.scriptapp("Resolve", host, float(os.environ.get("RESOLVE_SCRIPT_TIMEOUT", "5"))) if host else dvr.scriptapp("Resolve")
    except Exception:
        return None


def _bridge():
    """Transport 2 — the in-app bridge (Workspace ▸ Scripts ▸ resolve_bridge). None when not running."""
    if not os.path.isdir(BRIDGE_REPO):
        return None
    if BRIDGE_REPO not in sys.path:
        sys.path.insert(0, BRIDGE_REPO)
    try:
        from src.utils import resolve_bridge_client as bc
        return bc.connect(require_enabled=False)
    except Exception:
        return None


def connect_resolve(transport="auto", wait=0):
    """Try the ladder until one answers or `wait` seconds pass. Returns (resolve, transport_name)."""
    dvr = None
    if transport in ("auto", "local"):
        try:
            import DaVinciResolveScript as dvr  # noqa: N813 — Blackmagic's module name
        except Exception as e:
            if transport == "local":
                die(f"import DaVinciResolveScript: {e!r}")
    deadline = time.time() + wait
    while True:
        if dvr is not None and transport in ("auto", "local"):
            r = _external(dvr)
            if r is not None:
                return r, "external"
        if transport in ("auto", "bridge"):
            r = _bridge()
            if r is not None:
                return r, "bridge"
        if time.time() >= deadline:
            return None, None
        time.sleep(3)


def find_pool_item(folder, wp):
    """Reuse an already-imported clip. AddItemListToMediaPool returns [] (not the item) for a path the
    pool already holds, so a second pass over the same sources read as IMPORT-FAIL."""
    want = os.path.normcase(os.path.normpath(wp))
    for it in folder.GetClipList() or []:
        try:
            fp = it.GetClipProperty("File Path") or ""
        except Exception:
            fp = ""
        if fp and os.path.normcase(os.path.normpath(fp)) == want:
            return it
    for sub in folder.GetSubFolderList() or []:
        hit = find_pool_item(sub, wp)
        if hit is not None:
            return hit
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--look", help="look id from look-library (e.g. film-teal-orange)")
    ap.add_argument("--in", dest="clips", action="append", help="input clip (repeatable)")
    ap.add_argument("--out-dir", default=os.environ.get("RESOLVE_PASS_OUT", r"C:\hero-pass\renders"))
    ap.add_argument("--drx-dir", default=DRX_DIR, help="directory holding <look>.drx (LOOK_LIBRARY_DRX)")
    ap.add_argument("--timeout", type=int, default=600, help="seconds per render")
    ap.add_argument("--wait", type=int, default=0, help="seconds to keep polling for a Resolve connection")
    ap.add_argument("--transport", choices=["auto", "local", "bridge"], default="auto")
    ap.add_argument("--format", help="render container (default mp4). e.g. mov")
    ap.add_argument("--codec", help="render codec (default H.264, 8-bit). e.g. DNxHR_HQX for 10-bit")
    ap.add_argument("--list-codecs", action="store_true", help="print Resolve's formats/codecs and exit")
    args = ap.parse_args()

    if not args.list_codecs:                       # --list-codecs is a standalone query
        if not args.look:
            ap.error("--look is required (or use --list-codecs)")
        if not args.clips:
            ap.error("--in is required (or use --list-codecs)")

    drx = None
    if args.look:
        drx = os.path.join(args.drx_dir, args.look + ".drx")
        if not os.path.isfile(drx):
            die(f"look not found: {drx}")

    resolve, transport = connect_resolve(args.transport, args.wait)
    if resolve is None:
        die("no Resolve connection: external scripting refused (Resolve not running / no project open yet / "
            "Preferences > System > General > External scripting != Local / free edition or an instance the "
            "agent launched) AND no in-app bridge answering (start Workspace > Scripts > resolve_bridge)")
    print(f"connected via {transport}: {resolve.GetVersionString()}", file=sys.stderr)
    pm = resolve.GetProjectManager()
    try:
        pm.SaveProject()                       # don't lose the operator's current project state
    except Exception:
        pass
    proj = pm.LoadProject(PROJ_NAME) or pm.CreateProject(PROJ_NAME)   # idempotent open
    if proj is None:
        die(f"cannot open/create project {PROJ_NAME}")
    if args.list_codecs:
        # Codecs are addressed by EXTENSION, never the display key -- see the comment below.
        fmts = proj.GetRenderFormats() or {}
        out = {}
        for k, v in sorted(fmts.items()):
            cs = proj.GetRenderCodecs(v) or proj.GetRenderCodecs(k) or {}
            out[k] = {"ext": v, "codecs": {ck: cv for ck, cv in sorted(cs.items())}}
        print(json.dumps({"ok": True, "transport": transport,
                          "product": resolve.GetProductName(), "formats": out}, indent=2))
        print("RESOLVE-PASS-OK")
        return

    mp = proj.GetMediaPool()
    ms = resolve.GetMediaStorage()

    fmts = proj.GetRenderFormats() or {}
    # --format/--codec default to MP4/H.264 (8-bit). Grading a 10-bit mezzanine to 8-bit here
    # bands smooth gradients (mist, sky, steam) and throws away depth BEFORE grain is added —
    # pass a 10-bit intermediate (e.g. --format mov --codec DNxHR_HQX) for a mezzanine that
    # still has to survive grain and a downscale. See the video-finish skill, steps 5-6.
    want_fmt = (args.format or "mp4").lower()
    fmt = next((k for k, v in fmts.items() if str(v).lower() == want_fmt), None) \
        or next((k for k, v in fmts.items() if want_fmt in str(v).lower()), None)
    if fmt is None:
        die(f"format {args.format!r} not offered by Resolve; available: {sorted(set(map(str, fmts.values())))}")
    # 🔴 GetRenderCodecs takes the format's EXTENSION (the dict VALUE), never the display KEY.
    # Measured on Studio 18.5: GetRenderCodecs("QuickTime") -> 0 codecs, while
    # GetRenderCodecs("mov") -> 60 (all ProRes). MXF OP1A: 0 by key, 75 by ext. MP4 and AVI work
    # either way ONLY because their key case-insensitively equals their ext -- which is what hid
    # this bug, and made a full ProRes/DNxHR codec list look like a licence gate.
    codecs = proj.GetRenderCodecs(fmts.get(fmt) or fmt) or proj.GetRenderCodecs(fmt) or {}
    if args.codec:
        want = args.codec.lower().replace("_", "").replace("-", "").replace(" ", "")
        codec = next((v for k, v in codecs.items()
                      if want in str(k).lower().replace("_", "").replace("-", "").replace(" ", "")
                      or want in str(v).lower().replace("_", "").replace("-", "").replace(" ", "")), None)
        if codec is None:
            die(f"codec {args.codec!r} not offered for format {fmt!r}; available: {sorted(codecs.items(), key=str)}")
    else:
        codec = next((v for k, v in codecs.items() if k == "H.264"), None) \
            or next((v for k, v in codecs.items() if "264" in k), None)
    # 🔴 SetCurrentRenderFormatAndCodec ALSO takes the EXTENSION, not the display key (measured:
    # ("QuickTime","ProRes422HQ") refused, ("mov","ProRes422HQ") accepted). Try ext first, key as fallback.
    fmt_ext = str(fmts.get(fmt) or fmt)
    if not (proj.SetCurrentRenderFormatAndCodec(fmt_ext, codec) or proj.SetCurrentRenderFormatAndCodec(fmt, codec)):
        die(f"Resolve refused format/codec {fmt_ext!r}|{fmt!r}/{codec!r}")
    os.makedirs(args.out_dir, exist_ok=True)

    results = []
    for clip in args.clips:
        wp = win_path(clip)
        stem = os.path.splitext(os.path.basename(wp))[0]
        entry = {"in": wp, "look": args.look, "status": "?", "out": None}
        results.append(entry)
        if not os.path.isfile(wp):
            entry["status"] = "INPUT-MISSING"
            continue
        item = find_pool_item(mp.GetRootFolder(), wp)       # 2nd run: pool already holds it -> import returns []
        if item is None:
            items = ms.AddItemListToMediaPool([wp]) or []
            item = items[0] if items else None
        if item is None:
            entry["status"] = "IMPORT-FAIL"
            continue
        # match timeline to clip geometry/rate before creating it
        res = (item.GetClipProperty("Resolution") or "").split("x")
        fps = item.GetClipProperty("FPS")
        if len(res) == 2:
            proj.SetSetting("timelineResolutionWidth", res[0])
            proj.SetSetting("timelineResolutionHeight", res[1])
        if fps:
            proj.SetSetting("timelineFrameRate", str(fps))
        tname = f"{stem}__{args.look}_{int(time.time())}"
        tl = mp.CreateTimelineFromClips(tname, [item])
        if tl is None:
            entry["status"] = "TIMELINE-FAIL"
            continue
        titems = tl.GetItemListInTrack("video", 1) or []
        if not titems or not tl.ApplyGradeFromDRX(drx, 0, titems):
            entry["status"] = "APPLY-FAIL"
            continue
        entry["nodes"] = titems[0].GetNumNodes()
        while proj.IsRenderingInProgress():        # busy-guard: one job at a time
            time.sleep(2)
        custom = f"{stem}__{args.look}"
        proj.SetRenderSettings({"SelectAllFrames": True, "TargetDir": args.out_dir,
                                "CustomName": custom, "ExportVideo": True, "ExportAudio": True})
        job = proj.AddRenderJob()
        if not job:
            entry["status"] = "JOB-FAIL"
            continue
        # 🔴 StartRendering RETURNS A BOOLEAN and Resolve refuses the FIRST render of a
        # freshly opened/created project until it has been saved (measured 2026-09-13: a
        # queued job sat at JobStatus 'Ready' through three StartRendering calls, all False;
        # the same job rendered once the project had been saved). Ignoring the return value
        # reported the refusal as NO-OUTPUT, which reads as a render crash.
        started = proj.StartRendering([job])
        if not started:
            pm.SaveProject()
            started = proj.StartRendering([job])
        if not started:
            resolve.OpenPage("deliver")
            started = proj.StartRendering([job])
        if not started:
            entry["status"] = "START-REFUSED"
            continue
        t0 = time.time()
        while proj.IsRenderingInProgress():
            if time.time() - t0 > args.timeout:
                entry["status"] = "TIMEOUT"
                break
            time.sleep(3)
        st = proj.GetRenderJobStatus(job) or {}
        outs = sorted(glob.glob(os.path.join(args.out_dir, custom + "*")))
        if entry["status"] != "TIMEOUT":
            entry["status"] = st.get("JobStatus", "?") if outs else "NO-OUTPUT"
        entry["ms"] = st.get("TimeTakenToRenderInMs")
        entry["out"] = outs[-1] if outs else None
        print(f"{stem} + {args.look}: {entry['status']} nodes={entry.get('nodes')} -> {entry['out']}",
              file=sys.stderr)

    ok = all(r["status"] == "Complete" for r in results)
    print(json.dumps({"ok": ok, "project": PROJ_NAME, "transport": transport, "results": results}, indent=2))
    print("RESOLVE-PASS-OK" if ok else "RESOLVE-PASS-FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
