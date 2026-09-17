#!/usr/bin/env python3
"""hf_api_upload.py — host a reference on Higgsfield's own store for the REST API lane and record its
public URL under a NAME in <root>/hf-api-urls.json (what the refs gate and hf_api_submit.py resolve).
FREE: generate-upload-url and the PUT are control-plane calls, and nothing here generates.

  hf_api_upload.py --root <project> <file> [--name NAME]
  hf_api_upload.py --root <project> --batch 'references/*.png'      # idempotent, sha256-keyed
  hf_api_upload.py --root <project> --verify                        # HEAD every recorded url, free
  hf_api_upload.py --root <project> --refresh NAME                  # re-upload (the bytes move again)

FOUR wire facts, each one a silent failure:

  1. 🔴 NO MP3. The store accepts image/jpeg|jpg|png|webp|gif, audio/wav|x-wav and video/mp4 — and
     NOTHING else. Voice-over is commonly cut as mp3, so an audio reference for this lane is CONVERTED
     here rather than uploaded as found. `.mov` is refused too, although `output_format` will happily
     RETURN one.
  2. The upload URL expires in ONE HOUR. Mint it and PUT immediately; never mint a batch of them first.
  3. NEVER send the Higgsfield credential to the presigned storage URL — it is a different host, and the
     signature is already in the query string. The PUT carries the vendor's returned headers and nothing
     else. (`api()` is called with auth=False for exactly this reason.)
  4. The PUBLIC URL's lifetime is UNMEASURED. Outputs are documented as ≥ 7 days; uploads say nothing.
     So `expiresAt` is recorded as null with `lifetime: UNMEASURED`, and the gate raises a WARN rather
     than a pass — the honest state is "unknown", and a reference that has quietly lapsed bills the whole
     batch at acceptance and returns nothing. `--verify` is the free way to convert that WARN into a fact.
"""
import argparse, glob, hashlib, importlib.util, json, mimetypes, os, subprocess, sys, time

_spec = importlib.util.spec_from_file_location(
    'hf_api', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hf_api.py'))
hf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hf)

LEDGER_NAME = 'hf-api-urls.json'
# The store's ENTIRE accepted set, from the vendor's own upload contract. Anything absent is refused
# here rather than at the PUT, so the failure names the fix instead of a 4xx from a storage host.
ACCEPTED = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp',
            '.gif': 'image/gif', '.wav': 'audio/wav', '.mp4': 'video/mp4'}
CONVERT = {'.mp3': '.wav', '.m4a': '.wav', '.aac': '.wav', '.flac': '.wav', '.ogg': '.wav', '.opus': '.wav'}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def to_wav(src):
    """The WAV convert the store forces. 48 kHz 16-bit PCM mono-or-as-found, written beside the source
    and REUSED when it already exists — this never overwrites an operator's file."""
    dst = os.path.splitext(src)[0] + '.wav'
    if os.path.exists(dst):
        print(f'  wav: reusing {os.path.basename(dst)} (already present — not overwritten)')
        return dst
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-c:a', 'pcm_s16le', '-ar', '48000', dst],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dst):
        sys.exit(f'ffmpeg could not convert {src} to WAV: {(r.stderr or "")[:300]}')
    print(f'  wav: {os.path.basename(src)} → {os.path.basename(dst)} '
          f'({os.path.getsize(dst):,} B) — the store accepts NO mp3')
    return dst


def content_type(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in ACCEPTED:
        return ACCEPTED[ext]
    if ext in CONVERT:
        return None                        # caller converts first
    sys.exit(f'{os.path.basename(path)}: {ext or "no extension"} is not accepted by the Higgsfield store.\n'
             f'  accepted: {", ".join(sorted(ACCEPTED))}   (audio arrives as WAV; .mov is NOT accepted)')


def read_ledger(root):
    p = os.path.join(root, LEDGER_NAME)
    if not os.path.exists(p):
        return {}, p
    with open(p, encoding='utf-8') as f:
        return json.load(f), p


def write_ledger(d, p):
    """MERGE, never replace. A whole-file overwrite once dropped eleven live reference URLs on the kie
    lane; the same mistake here costs a re-upload per reference and a stale gate table."""
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, p)


def upload_one(root, path, name=None, force=False):
    d, lp = read_ledger(root)
    name = name or os.path.splitext(os.path.basename(path))[0]
    if os.path.splitext(path)[1].lower() in CONVERT:
        path = to_wav(path)
    ct = content_type(path)
    digest = sha256(path)
    meta = (d.get('_meta') or {}).get(name) or {}
    if not force and isinstance(d.get(name), str) and meta.get('sha256') == digest:
        print(f'{name}: already hosted, bytes unchanged → {d[name][:70]}…')
        return d[name]

    code, out = hf.api('POST', '/files/generate-upload-url', {'content_type': ct})
    if str(code) != '200' or not isinstance(out, dict) or not out.get('upload_url'):
        sys.exit(f'{name}: generate-upload-url HTTP {code} — '
                 f'{json.dumps(out)[:300] if not isinstance(out, str) else out}')
    # EVERY returned header, verbatim and unaltered. The presigned PUT signs
    # `content-type;host;x-amz-tagging`, so adding, dropping or replacing one of them is a 403
    # SignatureDoesNotMatch that reads exactly like a bad key (measured 2026-09-18 — our own
    # `Content-Type: application/octet-stream` was the cause). auth=False: the presigned URL is a
    # storage host and our Higgsfield key has no business being sent there.
    hdrs = out.get('upload_headers') or {}
    headers = [f'{k}: {v}' for k, v in hdrs.items()]
    if not any(h.lower().startswith('content-type:') for h in headers):
        headers.append(f"Content-Type: {out.get('content_type') or ct}")
    pcode, pout = hf.api('PUT', out['upload_url'], headers=headers, upload_file=path,
                         auth=False, timeout=600)
    if not (pcode and pcode.startswith('2')):
        sys.exit(f'{name}: PUT HTTP {pcode} — {pout if isinstance(pout, str) else json.dumps(pout)[:300]}')

    d[name] = out['public_url']
    d.setdefault('_meta', {})[name] = {
        'sha256': digest, 'bytes': os.path.getsize(path), 'content_type': ct,
        'source': os.path.relpath(path, root) if path.startswith(root) else path,
        'uploaded': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'tagging': hdrs.get('x-amz-tagging'),
        # 🔴 The vendor signs the PUT with `x-amz-tagging: retention=temporary` (measured 2026-09-18),
        # so the object is explicitly TRANSIENT — some lifecycle rule reclaims it and no documented
        # window says when. Recorded as unknown on purpose: a guessed expiry that is wrong bills the
        # whole batch at acceptance and returns nothing. `--verify` is the free way to find out.
        'expiresAt': None,
        'lifetime': 'UNMEASURED — the vendor tags the object retention=temporary; '
                    'free check: hf_api_upload.py --verify'}
    write_ledger(d, lp)
    print(f'{name} → {out["public_url"][:78]}…  ({os.path.getsize(path):,} B, {ct})')
    return out['public_url']


def verify(root):
    """Free: a HEAD per recorded url. This is the only thing that turns the UNMEASURED lifetime above
    into a fact, and it is what the gate's WARN points at."""
    d, _ = read_ledger(root)
    names = [k for k in d if k != '_meta']
    if not names:
        print(f'no {LEDGER_NAME} in {root}'); return 0
    bad = 0
    for n in sorted(names):
        code, _ = hf.api('HEAD', d[n], auth=False, timeout=30)
        ok = bool(code and code.startswith(('2', '3')))
        bad += (not ok)
        age = ((d.get('_meta') or {}).get(n) or {}).get('uploaded', '?')
        print(f"  {'ok  ' if ok else 'GONE'} {n:<28} HTTP {code}  uploaded {age}")
    print(f'{len(names) - bad} of {len(names)} still resolve'
          + ('' if not bad else f' — re-host the {bad} missing: --refresh <NAME>'))
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file', nargs='?')
    ap.add_argument('--root', default='.')
    ap.add_argument('--name')
    ap.add_argument('--batch', help='glob, relative to --root; names come from the file stems')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--refresh', help='NAME — re-upload it (the bytes move again)')
    a = ap.parse_args()
    root = os.path.abspath(a.root)

    if a.verify:
        sys.exit(1 if verify(root) else 0)
    if a.refresh:
        d, _ = read_ledger(root)
        src = ((d.get('_meta') or {}).get(a.refresh) or {}).get('source')
        if not src:
            sys.exit(f'{a.refresh}: no recorded source in {LEDGER_NAME} — upload it by path instead')
        upload_one(root, src if os.path.isabs(src) else os.path.join(root, src), a.refresh, force=True)
        return
    if a.batch:
        files = sorted(glob.glob(os.path.join(root, a.batch)))
        if not files:
            sys.exit(f'no files match {a.batch} under {root}')
        for f in files:
            upload_one(root, f)
        return
    if not a.file:
        ap.print_help(); sys.exit(2)
    upload_one(root, a.file if os.path.isabs(a.file) else os.path.join(root, a.file), a.name)


if __name__ == '__main__':
    main()
