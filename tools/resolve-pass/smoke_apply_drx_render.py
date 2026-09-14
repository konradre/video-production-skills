"""smoke_apply_drx_render.py <path to a .drx> — apply one grade to the open timeline's clips and render a smoke.
Resolve must be open with a project and a timeline loaded; run it with the Windows Python that can import
DaVinciResolveScript. Output: <RESOLVE_PASS_OUT>\\smoke\\smoke_look.*; prints SMOKE-OK on success."""
import os, sys, time, glob
if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
    print(__doc__); sys.exit(0)
os.environ.setdefault("RESOLVE_SCRIPT_API", r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting")
os.environ.setdefault("RESOLVE_SCRIPT_LIB", r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll")
sys.path.append(os.path.join(os.environ["RESOLVE_SCRIPT_API"], "Modules"))
DRX = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SMOKE_DRX", "")
OUT = os.path.join(os.environ.get("RESOLVE_PASS_OUT", r"C:\hero-pass\renders"), "smoke")
def die(msg): print("FAIL:", msg); sys.exit(2)
try:
    import DaVinciResolveScript as dvr
except Exception as e:
    die(f"import DaVinciResolveScript: {e!r}  (python {sys.version.split()[0]})")
resolve = dvr.scriptapp("Resolve")
if resolve is None: die("scriptapp('Resolve') returned None -> Resolve not running, or External scripting != Local")
print("connected:", resolve.GetProductName(), resolve.GetVersionString(), "| page:", resolve.GetCurrentPage())
pm = resolve.GetProjectManager(); proj = pm.GetCurrentProject()
if proj is None: die("no current project")
tl = proj.GetCurrentTimeline()
if tl is None: die("no current timeline")
print("project:", proj.GetName(), "| timeline:", tl.GetName(), "| tracks:", tl.GetTrackCount("video"))
items = tl.GetItemListInTrack("video", 1) or []
if not items: die("no items on video track 1")
for it in items:
    mpi = it.GetMediaPoolItem()
    print(f"  item: {it.GetName()!r} start={it.GetStart()} dur={it.GetDuration()} nodes_before={it.GetNumNodes()} src={mpi.GetClipProperty('File Path') if mpi else '?'}")
if not os.path.isfile(DRX): die(f"DRX missing: {DRX}")
ok = tl.ApplyGradeFromDRX(DRX, 0, items)
print("ApplyGradeFromDRX ->", ok)
for it in items:
    print(f"  item: {it.GetName()!r} nodes_after={it.GetNumNodes()} lut1={it.GetLUT(1)!r}")
if not ok: die("ApplyGradeFromDRX returned False")
# --- render
fmts = proj.GetRenderFormats() or {}
fmt = next((k for k,v in fmts.items() if str(v).lower()=="mp4"), None) or next((k for k,v in fmts.items() if str(v).lower()=="mov"), None)
codecs = proj.GetRenderCodecs(fmt) or {}
codec = next((v for k,v in codecs.items() if "264" in k), None) or next(iter(codecs.values()), None)
print("format/codec:", fmt, codec, "| available:", list(codecs.keys())[:8])
print("SetCurrentRenderFormatAndCodec ->", proj.SetCurrentRenderFormatAndCodec(fmt, codec))
os.makedirs(OUT, exist_ok=True)
settings = {"SelectAllFrames": True, "TargetDir": OUT, "CustomName": "smoke_look", "ExportVideo": True, "ExportAudio": True}
print("SetRenderSettings ->", proj.SetRenderSettings(settings))
job = proj.AddRenderJob(); print("AddRenderJob ->", job)
if not job: die("AddRenderJob failed")
print("StartRendering ->", proj.StartRendering([job]))
t0=time.time()
while proj.IsRenderingInProgress():
    st = proj.GetRenderJobStatus(job) or {}
    print(f"  {int(time.time()-t0):4d}s  {st.get('JobStatus')}  {st.get('CompletionPercentage')}%", flush=True)
    if time.time()-t0 > 480: print("timeout; leaving the job running"); break
    time.sleep(5)
st = proj.GetRenderJobStatus(job) or {}
print("final:", st)
outs = sorted(glob.glob(os.path.join(OUT, "smoke_look*")))
print("outputs:", [(os.path.basename(p), os.path.getsize(p)) for p in outs])
print("SMOKE-OK" if outs and st.get("JobStatus")=="Complete" else "SMOKE-INCOMPLETE")
