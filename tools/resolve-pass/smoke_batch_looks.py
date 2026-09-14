"""Batch smoke: apply each look-library .drx to the open timeline, render one clip each.

Run from WSL via Windows Python 3.10 (Resolve must be open, project+timeline loaded,
External scripting = Local):
  /mnt/c/.../Python310/python.exe smoke_batch_looks.py
Renders <RESOLVE_PASS_OUT>\\smoke\\smoke_<id>.mp4 per look. Prints BATCH-OK on full pass.
"""
import os, sys, time, glob

if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
    print(__doc__)
    sys.exit(0)

os.environ.setdefault("RESOLVE_SCRIPT_API", r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting")
os.environ.setdefault("RESOLVE_SCRIPT_LIB", r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll")
sys.path.append(os.path.join(os.environ["RESOLVE_SCRIPT_API"], "Modules"))

LOOKS_DIR = os.environ.get("LOOK_LIBRARY_DRX", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "look-library", "drx"))
FALLBACK_DIR = os.environ.get("RESOLVE_LOOKS_EXPORT_DIR", r"C:\looks")          # <id>_1.0_*.drx exports
OUT = os.path.join(os.environ.get("RESOLVE_PASS_OUT", r"C:\hero-pass\renders"), "smoke")
IDS = ["ads-clean", "ads-warm", "film-teal-orange", "film-portra", "film-cinestill"]


def die(msg):
    print("FAIL:", msg)
    sys.exit(2)


def find_drx(look_id):
    p = os.path.join(LOOKS_DIR, look_id + ".drx")
    if os.path.isfile(p):
        return p
    hits = sorted(glob.glob(os.path.join(FALLBACK_DIR, look_id + "_1.0_*.drx")))
    return hits[-1] if hits else None


try:
    import DaVinciResolveScript as dvr
except Exception as e:
    die(f"import DaVinciResolveScript: {e!r}")
resolve = dvr.scriptapp("Resolve")
if resolve is None:
    die("Resolve not running or External scripting != Local")
print("connected:", resolve.GetProductName(), resolve.GetVersionString())
proj = resolve.GetProjectManager().GetCurrentProject()
tl = proj and proj.GetCurrentTimeline()
if not tl:
    die("no current project/timeline")
items = tl.GetItemListInTrack("video", 1) or []
if not items:
    die("no items on video track 1")
print("timeline:", tl.GetName(), "| items:", len(items))

fmts = proj.GetRenderFormats() or {}
fmt = next((k for k, v in fmts.items() if str(v).lower() == "mp4"), None)
codecs = proj.GetRenderCodecs(fmt) or {}
codec = next((v for k, v in codecs.items() if "264" in k), None) or next(iter(codecs.values()))
proj.SetCurrentRenderFormatAndCodec(fmt, codec)
os.makedirs(OUT, exist_ok=True)

results = {}
for look_id in IDS:
    drx = find_drx(look_id)
    if not drx:
        results[look_id] = "DRX-MISSING"
        continue
    ok = tl.ApplyGradeFromDRX(drx, 0, items)
    print(f"\n{look_id}: ApplyGradeFromDRX -> {ok}  nodes={items[0].GetNumNodes()}  ({drx})")
    if not ok:
        results[look_id] = "APPLY-FAIL"
        continue
    proj.SetRenderSettings({"SelectAllFrames": True, "TargetDir": OUT,
                            "CustomName": f"smoke_{look_id}", "ExportVideo": True, "ExportAudio": False})
    job = proj.AddRenderJob()
    if not job:
        results[look_id] = "JOB-FAIL"
        continue
    proj.StartRendering([job])
    t0 = time.time()
    while proj.IsRenderingInProgress():
        if time.time() - t0 > 300:
            break
        time.sleep(3)
    st = proj.GetRenderJobStatus(job) or {}
    outs = glob.glob(os.path.join(OUT, f"smoke_{look_id}*"))
    results[look_id] = st.get("JobStatus", "?") if outs else "NO-OUTPUT"
    print(f"{look_id}: {st.get('JobStatus')} in {st.get('TimeTakenToRenderInMs', 0)}ms -> {outs}")

print("\n==== results ====")
for k, v in results.items():
    print(f"  {k}: {v}")
print("BATCH-OK" if all(v == "Complete" for v in results.values()) else "BATCH-INCOMPLETE")
