#!/usr/bin/env python3
"""
gen_video_fal.py — fal video runner: Seedance 2.5 (i2v | r2v) and MiniMax H3 (r2v). fal REFUSES any photoreal person
in a reference or start frame (content_policy_violation, billed 0) — use it for people-free shots only; the
production route for people is Higgsfield (hf_submit.py). FAL_KEY comes from the environment.

Dry by default: prints the compiled body and the estimate, then stops. `--go` spends.

THREE ENGINES, THREE PROMPT DIALECTS. They are not interchangeable:
    Create a Meme (Seedance)  @ref1        start+end frames AND refs together
    fal Seedance 2.5          @Image1      i2v OR r2v — never both
    fal MiniMax H3            Image 1      refs + video refs, 5-15s only

Wire facts learned live — do not rediscover them:

  1. The queue REWRITES the path. Poll only the URLs the submit response returns;
     building them from the full endpoint returns 405.
  2. The queue ACCEPTS ANY BODY. Validation runs on the runner, so a bad request
     reaches COMPLETED and the *result* fetch returns 422. COMPLETED IS NOT SUCCESS.
  3. X-Fal-Billable-Units on the result is the ACTUAL charge, and it is LATE, not
     absent: unset on the first fetch after COMPLETED, populated seconds later on a
     re-fetch of the same URL. Seedance bills ACTUAL output duration (units / 9.59 =
     seconds at 480p); H3 bills the REQUESTED integer duration at $0.05/unit. A refused
     request returns billable='0' and is genuinely free.

And one learned here the expensive way: a paid handle is persisted at COMMIT time
(the moment the queue accepts), never at collection. `RemoteDisconnected` is a
ConnectionResetError, not a URLError — catch Exception in the poll loop or a network
blip discards a billed job.
"""
import argparse, base64, json, mimetypes, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

QUEUE = "https://queue.fal.run"

# Published rates read from fal 2026-08-31, USD per second of generated video.
ENGINES = {
    "seedance": {
        "i2v": "bytedance/seedance-2.5/image-to-video",
        "r2v": "bytedance/seedance-2.5/reference-to-video",
        "rates": {"480p": 0.2205, "720p": 0.4730, "1080p": 1.164},
        "res_default": "480p",
        "duration_range": (4, 30),
        # fal's own schema, read free 2026-09-17. The TOTAL is the cap the vendor states in prose
        # ("total files across all modalities must not exceed 50"); the per-array caps are stated
        # there too. 2.5 states them in PROSE ONLY — the arrays carry no maxItems — so nothing but
        # this check stops an over-cap body reaching the runner and failing after the queue accepts it.
        "ref_caps": {"image": 30, "video": 10, "audio": 10, "total": 50},
    },
    "h3": {
        # H3 has no i2v-with-references split; r2v carries images, videos and audio.
        "r2v": "minimax/h3/reference-to-video",
        "rates": {"480P": 0.05, "768P": 0.06, "2K": 0.13, "4K": 0.16},
        # OPERATOR RULE 2026-09-01: H3 gens are 768P MINIMUM. 480P stays in the rate table for
        # cost arithmetic only; the floor check below refuses it.
        "res_default": "768P",
        "res_floor": ("480P",),
        "duration_range": (5, 15),   # hard, per fal's own OpenAPI schema
        # Re-read 2026-09-17: the combined 12 is right ("must add up to at most 12 files"), but each
        # array carries a REAL maxItems that is tighter, and checking the total alone lets 12 images
        # through our gate for fal to reject.
        "ref_caps": {"image": 9, "video": 3, "audio": 3, "total": 12},
    },
}


def fal_key() -> str:
    k = os.environ.get("FAL_KEY", "").strip().strip("\"'")
    if not k:
        sys.exit("FAL_KEY is not set — source the env file first (set -a; . <file>; set +a)")
    return k


def data_uri(p: Path) -> str:
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def req(url: str, key: str, data: bytes | None = None, method: str = "GET"):
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", f"Key {key}")
    if data:
        r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=120) as resp:
        return resp.status, dict(resp.headers), resp.read()


ROOT = Path(".")


def ledger(line: str):
    (ROOT / "receipts").mkdir(exist_ok=True)
    with open(ROOT / "receipts" / "fal-requests.log", "a") as f:
        f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--engine", default="h3", choices=list(ENGINES))
    ap.add_argument("--mode", default="r2v", choices=["i2v", "r2v"])
    ap.add_argument("--image", help="seedance i2v: start frame")
    ap.add_argument("--end-image", help="seedance i2v: optional end frame")
    ap.add_argument("--refs", help="r2v: comma-separated paths, in prompt-citation order")
    ap.add_argument("--ref-videos", help="h3 only: comma-separated video paths (2-15s each)")
    ap.add_argument("--aspect-ratio", default="16:9")
    ap.add_argument("--duration", default="auto")
    ap.add_argument("--resolution")
    ap.add_argument("--bitrate-mode", default="high", choices=["standard", "high"])
    ap.add_argument("--expansion", default="fast",
                    help="h3 prompt_expansion_mode — it REWRITES your prompt; 'fast' is least invasive")
    ap.add_argument("--no-audio", action="store_true", help="seedance only")
    ap.add_argument("--name", default="take")
    ap.add_argument("--go", action="store_true", help="actually spend")
    a = ap.parse_args()
    global ROOT
    ROOT = Path(a.root).resolve()

    eng = ENGINES[a.engine]
    res = a.resolution or eng["res_default"]
    if res in eng.get("res_floor", ()):
        sys.exit(f"{a.engine}: {res} is below the floor — H3 gens are 768P minimum (house rule, 2026-09-01). "
                 f"Use --resolution 768P or 2K.")
    if res not in eng["rates"]:
        sys.exit(f"{a.engine}: resolution must be one of {list(eng['rates'])} (case matters)")
    if a.mode not in eng:
        sys.exit(f"{a.engine} has no {a.mode} endpoint")
    model = eng[a.mode]
    prompt = Path(a.prompt_file).read_text().strip()

    lo, hi = eng["duration_range"]
    if a.duration != "auto":
        if not lo <= int(a.duration) <= hi:
            sys.exit(f"{a.engine} duration must be {lo}-{hi}s; got {a.duration}")
    elif a.engine == "h3":
        sys.exit("h3 has no 'auto' duration — pass --duration 5..15")

    start = end = None
    srcs, vids = [], []
    if a.mode == "i2v":
        if not a.image:
            sys.exit("--mode i2v needs --image")
        start = Path(a.image)
        end = Path(a.end_image) if a.end_image else None
        srcs = [start] + ([end] if end else [])
    else:
        if not a.refs:
            sys.exit("--mode r2v needs --refs")
        srcs = [Path(x.strip()) for x in a.refs.split(",") if x.strip()]
        vids = [Path(x.strip()) for x in (a.ref_videos or "").split(",") if x.strip()]
        caps = eng["ref_caps"]
        # PER-ARRAY first, then the total. The total alone is not the vendor's rule: fal caps each
        # modality separately AND caps their sum, and a body inside the sum can still be over on one
        # array. The queue accepts any body and validates on the runner, so a cap missed here surfaces
        # as a COMPLETED-then-422 long after the submit looked fine.
        for n, kind in ((len(srcs), "image"), (len(vids), "video")):
            if n > caps[kind]:
                sys.exit(f"{a.engine} r2v takes at most {caps[kind]} {kind} references; got {n}")
        if len(srcs) + len(vids) > caps["total"]:
            sys.exit(f"{a.engine} r2v takes at most {caps['total']} reference files in total; "
                     f"got {len(srcs)+len(vids)}")
    for p in srcs + vids:
        if not p.exists():
            sys.exit(f"missing: {p}")

    if a.engine == "h3":
        body = {
            "prompt": prompt,
            "duration": int(a.duration),
            "resolution": res,
            "aspect_ratio": a.aspect_ratio,
            "reference_image_urls": [data_uri(p) for p in srcs],
            "prompt_expansion_mode": a.expansion,
        }
        if vids:
            body["reference_video_urls"] = [data_uri(p) for p in vids]
    else:
        body = {
            "prompt": prompt,
            "resolution": res,
            "duration": a.duration,
            "generate_audio": not a.no_audio,
            "bitrate_mode": a.bitrate_mode,
        }
        if a.mode == "i2v":
            body["image_url"] = data_uri(start)
            body["aspect_ratio"] = "auto"   # i2v inherits the start frame's ratio
            if end:
                body["end_image_url"] = data_uri(end)
        else:
            body["image_urls"] = [data_uri(p) for p in srcs]
            body["aspect_ratio"] = a.aspect_ratio

    secs = 0 if a.duration == "auto" else int(a.duration)
    est = secs * eng["rates"][res]
    if a.engine == "h3":
        est += 0.08 * max(0, len(srcs) - 5)     # first 5 reference images are free

    shown = dict(body)
    for k in ("image_url", "end_image_url"):
        if k in shown:
            shown[k] = f"<{Path(a.image if k=='image_url' else a.end_image).name}, {len(shown[k])/1e6:.1f} MB>"
    for k, label, paths in (("image_urls", "Image", srcs), ("reference_image_urls", "Image", srcs),
                            ("reference_video_urls", "Video", vids)):
        if k in shown:
            shown[k] = [f"{label} {i+1} = {p.name} ({len(u)/1e6:.1f} MB)"
                        for i, (p, u) in enumerate(zip(paths, body[k]))]

    print(f"\nPOST {QUEUE}/{model}")
    print(json.dumps({**shown, "prompt": prompt[:150] + " …"}, indent=2))
    print(f"\nengine      {a.engine} · {a.mode}")
    print(f"prompt      {len(prompt)} chars")
    if a.mode == "i2v":
        print(f"start       {start.name}\nend         {end.name if end else '—'}")
    else:
        print(f"refs        {len(srcs)} images, {len(vids)} videos · aspect {a.aspect_ratio}")
    print(f"estimate    {res} x {a.duration}s = ${est:.2f}" if secs else
          f"estimate    {res} x auto — UNKNOWN until the model picks a duration")

    if not a.go:
        print("\nDRY RUN — nothing submitted. Re-run with --go to spend.\n")
        return

    key = fal_key()
    status, _, raw = req(f"{QUEUE}/{model}", key, json.dumps(body).encode(), "POST")
    sub = json.loads(raw)
    rid = sub.get("request_id")
    # COMMIT boundary: persist the handle before anything can fail.
    ledger(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {a.name} {model} {rid} {sub.get('status_url','')}")
    print(f"\n  queued (BILLABLE): {rid}")

    status_url, response_url = sub["status_url"], sub["response_url"]
    misses = 0
    while True:
        time.sleep(5)
        try:
            _, _, s = req(status_url, key)
            st = json.loads(s)
        except Exception as e:                    # NOT urllib.error.URLError — see docstring
            misses += 1
            if misses > 40:
                sys.exit(f"polling failed {misses}x, last: {e}\n  recover by hand: {response_url}")
            continue
        state = st.get("status")
        print(f"  {state}", flush=True)
        if state in ("COMPLETED", "FAILED", "ERROR"):
            break

    # COMPLETED is not success. Only a 2xx on the RESULT is.
    try:
        rstatus, rheaders, rraw = req(response_url, key)
    except urllib.error.HTTPError as e:
        sys.exit(f"\nRESULT FETCH {e.code} — the runner rejected the request.\n{e.read().decode()[:900]}")

    out = json.loads(rraw)
    # X-Fal-Billable-Units is LATE, not absent: unset on this first fetch, populated moments later.
    # Re-fetch the same URL until it appears, so the cost is a receipt and not arithmetic.
    units = rheaders.get("X-Fal-Billable-Units")
    for _ in range(6):
        if units is not None:
            break
        time.sleep(5)
        try:
            _, h2, _ = req(response_url, key)
            units = h2.get("X-Fal-Billable-Units")
        except Exception:
            break
    vurl = (out.get("video") or {}).get("url")
    expanded = out.get("expanded_prompt")
    print(f"\n  result {rstatus} · billable units {units} · seed {out.get('seed')}")
    if expanded and expanded.strip() != prompt.strip():
        print(f"  ⚠️  PROMPT WAS REWRITTEN by expansion ({len(expanded)} chars) — see receipt")

    (ROOT / "takes").mkdir(exist_ok=True)
    dest = ROOT / "takes" / f"{a.name}.mp4"
    urllib.request.urlretrieve(vurl, dest)
    receipt = ROOT / "receipts" / f"fal-{a.name}-{rid}.json"
    receipt.write_text(json.dumps({
        "engine": a.engine, "mode": a.mode, "model": model, "request_id": rid,
        "seed": out.get("seed"), "billable_units": units, "estimate_usd": est,
        "resolution": res, "duration": a.duration, "video_url": vurl, "file": str(dest),
        "refs": [str(p) for p in srcs], "ref_videos": [str(p) for p in vids],
        "start": str(start) if start else None, "end": str(end) if end else None,
        "prompt_chars": len(prompt), "expanded_prompt": expanded,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }, indent=2))
    print(f"  saved   {dest}\n  receipt {receipt}\n")


if __name__ == "__main__":
    main()
