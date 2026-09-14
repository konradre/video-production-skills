#!/usr/bin/env python3
"""gen_stills.py — per-shot STILLS on kie.ai (gpt-image-2.5 image-to-image by default — flare, or sunburst for the precision
tier; nano-banana-pro as the fallback for surgical edits; gpt-image-2 kept for the record, superseded 2026-09-10):
plates, start images, reference crops re-imagined from references, and the reference DRESS REHEARSAL (one still from the
same reference set as an expensive video call, read before the call). Dry-run by default; --go spends
($0.05/image at 2K on 2.5; $0.09 on the older models). The refs gate runs INSIDE (ref 1 = the image being edited = the start image for the
gate); a still with a locked element in it is that element's scene, so it needs that element's reference.

Layout under --root: prompts/stills/<ID>.txt (one prompt per file) · prompts/stills/refs.json ({ID: [names]}) ·
prompts/stills/_tail.txt (common tail; _<ID>-tail.txt overrides) · refs-urls.json ({name: https url}, written
by kie_upload.py — expires ~24 h, re-upload per session) · startframes/<ID>.png · receipts/.
Why gpt-image-2 for composing: nano IGNORES character sheets when composing a scene. Why single-view crops:
gpt-image-2 blends a montage. Why 9:16: a video start image's aspect IS the clip's — every landed still is checked: aspect within 1 % of --ratio and both
sides multiples of 16, else a WARN (a video venue letterboxes or crops a frame that does not match).
A landed still is recorded in the gate's ledger WITH its file (sha256, size) — the gate re-checks that file on every later use.

  gen_stills.py --root <project> [--only S06-01,S06-02] [--model gpt25|gpt25s|nano|gpt2] [--ratio 9:16] [--resolution 2K]
                [--births R,R] [--prose X,Y] [--fresh-scene] [--go]
--fresh-scene: a scene with no predecessor keeper (the gate's own flag, passed through) — said in the GO ask. A still built from
the client's approved images needs no flag: import those images with refs_gate.py --import and their lineage is rooted.
KIE_API_KEY comes from the environment (source the env file: set -a; . <file>; set +a).
"""
import argparse, importlib.util, json, os, shutil, sys, time, urllib.request
from pathlib import Path

CREATE = "https://api.kie.ai/api/v1/jobs/createTask"
STATUS = "https://api.kie.ai/api/v1/jobs/recordInfo"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
MODELS = {   # kie.ai job model ids; rate = USD per image by resolution (kie pricing 2026-09-10)
    "gpt25": {"model": "gpt-image-2-5-flare-image-to-image", "refs": "input_urls", "extra": lambda r, s: {"aspect_ratio": r, "resolution": s.upper()},
              "rate": lambda s: {"1K": 0.03, "2K": 0.05}.get(s.upper(), 0.08)},
    "gpt25s": {"model": "gpt-image-2-5-sunburst-image-to-image", "refs": "input_urls", "extra": lambda r, s: {"aspect_ratio": r, "resolution": s.upper()},
               "rate": lambda s: {"1K": 0.03, "2K": 0.05}.get(s.upper(), 0.08)},
    "gpt2": {"model": "gpt-image-2-image-to-image", "refs": "input_urls", "extra": lambda r, s: {"aspect_ratio": r}, "rate": lambda s: 0.09 if s.upper() in ("1K", "2K") else 0.12},
    "nano": {"model": "nano-banana-pro", "refs": "image_input", "extra": lambda r, s: {"aspect_ratio": r, "resolution": s, "output_format": "png"}, "rate": lambda s: 0.09},
}
DEFAULT_GATE = os.path.expanduser('~/.claude/skills/video-refs-continuity/scripts/refs_gate.py')


def run(prompt, refs, key, ratio, resolution, model, on_task=None):
    m = MODELS[model]
    body = {"model": m["model"], "input": {"prompt": prompt, m["refs"]: refs, **m["extra"](ratio, resolution)}}
    req = urllib.request.Request(CREATE, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": UA})
    d = json.loads(urllib.request.urlopen(req, timeout=120).read())
    if d.get("code") != 200:
        return {"ok": False, "err": f"create {d.get('code')}: {d.get('msg')}"}
    task = d["data"]["taskId"]
    print(f"  task created (BILLED): {task}", flush=True)   # billing is at creation, not at fetch
    if on_task: on_task(task)
    misses = 0
    for _ in range(120):
        time.sleep(5)
        rq = urllib.request.Request(f"{STATUS}?taskId={task}", headers={"Authorization": f"Bearer {key}", "User-Agent": UA})
        try:
            s = json.loads(urllib.request.urlopen(rq, timeout=60).read())
        except Exception as e:                       # broad on purpose — RemoteDisconnected is not URLError
            misses += 1
            if misses > 20: return {"ok": False, "task": task, "err": f"polling failed {misses}x, last: {e}"}
            continue
        misses = 0
        st = (s.get("data") or {}).get("state")
        if st == "success":
            u = (json.loads(s["data"].get("resultJson") or "{}").get("resultUrls") or [None])[0]
            return {"ok": True, "task": task, "url": u}
        if st == "fail":
            return {"ok": False, "task": task, "err": s["data"].get("failMsg") or "unknown"}
    return {"ok": False, "task": task, "err": "timed out"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--only", default="", help="comma-separated shot ids")
    ap.add_argument("--ratio", default="9:16")
    ap.add_argument("--resolution", default="2K")
    ap.add_argument("--model", default="gpt25", choices=list(MODELS), help="gpt25 = GPT Image 2.5 flare (default) · gpt25s = sunburst · nano = the fallback · gpt2 = superseded")
    ap.add_argument("--gate", default=DEFAULT_GATE)
    ap.add_argument("--births", default="", help="roles / subjects BORN in this still")
    ap.add_argument("--prose", default="", help="subjects deliberately prose-only")
    ap.add_argument("--fresh-scene", action="store_true", help="a scene with no predecessor keeper — passed to the refs gate; say it in the GO ask")
    ap.add_argument("--go", action="store_true")
    a = ap.parse_args()
    ROOT = Path(a.root).resolve(); PDIR = ROOT / "prompts" / "stills"; URLS = ROOT / "refs-urls.json"
    OUT = ROOT / "startframes"; RECEIPTS = ROOT / "receipts"

    spec = importlib.util.spec_from_file_location('refs_gate', a.gate); gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
    g = gate.Gate(str(ROOT))

    def ledger(item, task):
        RECEIPTS.mkdir(exist_ok=True)
        with open(RECEIPTS / "tasks-created.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{item}\t{task}\n")

    tail = (PDIR / "_tail.txt").read_text(encoding="utf-8").strip() if (PDIR / "_tail.txt").exists() else ""
    mapping = json.loads((PDIR / "refs.json").read_text(encoding="utf-8")) if (PDIR / "refs.json").exists() else {}
    urls = json.loads(URLS.read_text()) if URLS.exists() else {}
    ids = sorted(p.stem for p in PDIR.glob("*.txt") if not p.name.startswith("_"))
    want = {x.strip() for x in a.only.split(",")} if a.only else set(ids)
    sel = [i for i in ids if i in want]
    rate = MODELS[a.model]["rate"](a.resolution)
    print(f"kie.ai {MODELS[a.model]['model']} · {a.ratio} · ${rate:.2f}/image (estimate)\n")
    jobs = []
    for k in sel:
        shot_tail_p = PDIR / f"_{k}-tail.txt"
        shot_tail = shot_tail_p.read_text(encoding="utf-8").strip() if shot_tail_p.exists() else tail
        full = (PDIR / f"{k}.txt").read_text(encoding="utf-8").strip() + (" " + shot_tail if shot_tail else "")
        names = mapping.get(k, [])
        missing = [n for n in names if n not in urls]
        if missing: sys.exit(f"{k}: refs not uploaded yet — run kie_upload.py --json-out refs-urls.json: {missing}")
        refs = [urls[n] for n in names]
        jobs.append((k, full, refs, names))
        print(f"  {k:<10} {len(full):>4} chars · {len(refs)} refs · {', '.join(names)}{'   [OVERWRITES]' if (OUT / f'{k}.png').exists() else ''}")
        for i, n in enumerate(names, 1): print(f"              @ref{i} = {n}")
    births = [x for x in a.births.split(",") if x]; prose = [x for x in a.prose.split(",") if x]; gate_roles = {}; gate_fail = False
    for k, full, refs, names in jobs:
        start = names[0] if names else None   # i2i: ref 1 is the edited image for gpt2 AND nano
        m = g.spot_re.search(k); spot = m.group(1) if m else None
        ok, rows, roles = g.check(full, names, "kie", start, births, prose, spot, fresh=a.fresh_scene)
        print(f"\nREFS-GATE {k}  refs: {', '.join(names) or '-'}  start: {start or '-'}" + ("  (--fresh-scene declared)" if a.fresh_scene else "") + "\n" + gate.fmt(rows))
        print("REFS-GATE PASS" if ok else f"REFS-GATE FAIL ({sum(1 for r in rows if r[1] == 'FAIL')} missing) — REFUSED")
        gate_roles[k] = roles; gate_fail |= (not ok)
    print(f"\nTOTAL: {len(jobs)} images = ${len(jobs) * rate:.2f}")
    if gate_fail: sys.exit("REFS-GATE FAIL — nothing submitted. Fix the reference set (upload / cut / import / declare --births, --prose or --fresh-scene) and re-run.")
    if not a.go:
        print("\nDRY RUN — nothing submitted. Re-run with --go to spend."); return
    key = os.environ.get("KIE_API_KEY", "").strip()
    if not key: sys.exit("KIE_API_KEY is not set.")
    OUT.mkdir(exist_ok=True); RECEIPTS.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S"); rec = []; spent = 0.0
    for k, full, refs, names in jobs:
        print(f"\n→ {k}", flush=True)
        r = run(full, refs, key, a.ratio, a.resolution, a.model, on_task=lambda t, k=k: ledger(k, t))
        if not r["ok"]:
            print(f"  FAILED: {r['err']}", flush=True); rec.append({"shot": k, "ok": False, "err": r["err"]})
        else:
            spent += rate; dest = OUT / f"{k}.png"
            print(f"  billed. url: {r['url']}", flush=True)
            row = {"shot": k, "ok": True, "task": r["task"], "url": r["url"], "usd": rate, "refs": refs, "downloaded": False}
            try:
                rq = urllib.request.Request(r["url"], headers={"User-Agent": UA, "Accept": "*/*"})
                with urllib.request.urlopen(rq, timeout=180) as resp, open(dest, "wb") as f: shutil.copyfileobj(resp, f)
                row["downloaded"] = True
                try:
                    from PIL import Image; row["size"] = list(Image.open(dest).size)   # record dims — a hosted model changed resolution mid-session
                except Exception: pass
                if row.get("size"):   # the still must be the clip's own frame: its aspect within 1 % of --ratio, both sides multiples of 16
                    w, h = row["size"]; issues = []
                    if ":" in a.ratio and a.ratio.replace(":", "").isdigit():
                        tw, th = (int(x) for x in a.ratio.split(":")); off = abs(w / h - tw / th) / (tw / th)
                        row["aspect_off_pct"] = round(off * 100, 2)
                        if off > 0.01: issues.append(f"aspect {w}:{h} is {off * 100:.1f} % off {a.ratio}")
                    row["mult16"] = (w % 16 == 0 and h % 16 == 0)
                    if not row["mult16"]: issues.append(f"{w}x{h} is not a multiple of 16 on both sides")
                    if issues: print(f"  WARN {'; '.join(issues)} — a video venue letterboxes or crops what does not match its frame; regenerate at the clip's aspect", flush=True)
                print(f"  OK  {dest.name}  {dest.stat().st_size // 1024} KB  {row.get('size')}", flush=True)
            except Exception as e:
                row["downloadErr"] = str(e); print(f"  DOWNLOAD FAILED ({e}) — url kept in receipt", flush=True)
            try:   # the landed file is registered with its sha256 so the gate re-checks it on every later use
                g.record(k, "kie", f"prompts/stills/{k}.txt", names, births, gate_roles.get(k, []), file=str(dest) if row["downloaded"] else None)
            except SystemExit as ex:
                g.record(k, "kie", f"prompts/stills/{k}.txt", names, births, gate_roles.get(k, []))
                print(f"  WARN the landed file did not register ({ex}) — recorded without its content hash", flush=True)
            rec.append(row)
        (RECEIPTS / f"stills-{stamp}.json").write_text(json.dumps({"spentUsd": round(spent, 2), "items": rec}, indent=2))
    print(f"\n{sum(1 for x in rec if x.get('ok'))}/{len(jobs)} landed · ${spent:.2f} · receipt receipts/stills-{stamp}.json")
    print("Next: zoom-check each still and record it: refs_gate.py --root <project> --accept <ID> --note '<rows checked>'")


if __name__ == "__main__":
    main()
