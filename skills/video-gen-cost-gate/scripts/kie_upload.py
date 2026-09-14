#!/usr/bin/env python3
"""
kie_upload.py — upload local images to kie.ai and print the hosted URLs; --json-out MERGES {name: url} into the
project ledger (refs-urls.json). Uploads expire in ~24 h — re-upload per session; "Image fetch failed" = expired.
KIE_API_KEY comes from the environment (set -a; . <env file>; set +a).

  kie_upload.py <img.png> [...] [--max-px 1600] [--quality 90] [--json-out refs-urls.json]

kie.ai's generate endpoint takes `image_input` as URLs only — it rejects data: URIs outright
("image_input file type not supported"). Its own file-upload API is the way to reference a local
file without handing the image to a third-party host.

Images are downscaled first: a reference plate does not need 2.5K, and the base64 payload of a
6 MB PNG is ~8 MB of JSON.
"""
import argparse, base64, io, json, os, sys, urllib.request, urllib.error

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
from pathlib import Path
from PIL import Image

# NOT api.kie.ai — the upload API lives on a different host and 404s there.
# Uploads are temporary: kie.ai deletes them after ~24 h, so re-upload per session.
UPLOAD = "https://kieai.redpandaai.co/api/file-base64-upload"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--max-px", type=int, default=1600)
    ap.add_argument("--quality", type=int, default=90)
    ap.add_argument("--path", default="images")
    ap.add_argument("--json-out", default=None, help="write {name: url} here")
    a = ap.parse_args()

    key = os.environ.get("KIE_API_KEY", "").strip()
    if not key:
        sys.exit("KIE_API_KEY is not set.")

    out = {}
    for f in a.files:
        p = Path(f)
        if not p.exists():
            sys.exit(f"not found: {f}")
        im = Image.open(p).convert("RGB")
        im.thumbnail((a.max_px, a.max_px))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=a.quality)
        b = buf.getvalue()
        name = p.stem + ".jpg"
        body = {"base64Data": "data:image/jpeg;base64," + base64.b64encode(b).decode(),
                "uploadPath": a.path, "fileName": name}
        req = urllib.request.Request(
            UPLOAD, data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                     "User-Agent": UA, "Accept": "*/*"})
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=180).read())
        except urllib.error.HTTPError as e:
            print(f"  {p.name}: HTTP {e.code} — {e.read()[:300].decode(errors='replace')}", flush=True)
            continue
        except Exception as e:
            print(f"  {p.name}: UPLOAD FAILED {e}", flush=True)
            continue
        if d.get("code") != 200:
            print(f"  {p.name}: error {d.get('code')} {d.get('msg')}", flush=True)
            continue
        url = (d.get("data") or {}).get("downloadUrl") or (d.get("data") or {}).get("fileUrl")
        out[p.stem] = url
        print(f"  {p.name}  {im.size[0]}x{im.size[1]}  {len(b)//1024} KB  ->  {url}", flush=True)

    if a.json_out and out:
        # MERGE into the ledger — 2026-09-05 this overwrote refs-urls.json and dropped 11 live urls (uploads last ~24 h; a re-upload is free but the loss is silent)
        prev = {}
        if Path(a.json_out).exists():
            try: prev = json.loads(Path(a.json_out).read_text())
            except Exception: prev = {}
        prev.update(out)
        Path(a.json_out).write_text(json.dumps(prev, indent=2) + "\n")
        print(f"\nwrote {a.json_out} ({len(out)} new, {len(prev)} urls)")


if __name__ == "__main__":
    main()
