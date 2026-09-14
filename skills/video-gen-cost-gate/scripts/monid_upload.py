#!/usr/bin/env python3
"""monid_upload.py — host a reference on monid's Simple FS (`sfs`) so a monid generation can cite it by
public URL. FREE: every sfs endpoint is $0.00 PER_CALL, 1 GB per workspace. This is the reason no monid
venue is blocked on "needs a public URL".

  monid_upload.py --root <project> <file> --name NAME [--ttl 7d] [--prefix refs] [--go]
  monid_upload.py --root <project> --list
  monid_upload.py --root <project> --rm NAME [--go]

Writes {NAME: url} into <root>/monid-urls.json, which is what refs_gate.py --target monid reads.

WIRE FACTS, measured 2026-09-14 — do not rediscover them (VENUES.md § monid · sfs):

  1. `/put` returns an uploadUrl; the BYTES go to that URL by RAW PUT (`curl -T`), never multipart
     (`-F`). A multipart upload is accepted and stores the MIME envelope as the file.
  2. `sizeBytes` is REQUIRED and is a cap PINNED INTO the signed URL — an upload over it is rejected
     MID-STREAM, after a 200 on the handshake. It is computed from the file here, never passed by hand.
  3. `ttl` bounds the URL, NEVER the file's lifetime. An expired URL just needs a fresh `/cat`, free.
     So a stale entry in monid-urls.json is re-issued, not re-uploaded.
  4. Files NEVER auto-delete. `/rm` is what frees the 1 GB quota.
  5. An invalid body returns a bare {"error": {...}} with NO runId — no run is created and nothing is
     billed. That is why the shape-safe extraction below treats a missing runId as a hard failure
     rather than as a pending run.
  6. MERGE into the ledger, never overwrite: a `--json-out` overwrite on the kie leg once dropped
     eleven live URLs (EVIDENCE.md 09-05).
"""
import argparse, json, os, shutil, subprocess, sys, time


def run_monid(endpoint, body, what):
    """`monid run -p sfs -e <endpoint>` → parsed JSON. Raises on an error envelope."""
    if not shutil.which('monid'):
        sys.exit('monid CLI not found — npm install -g @monid-ai/cli, then `monid keys add`')
    cmd = ['monid', 'run', '-p', 'sfs', '-e', endpoint, '-i', json.dumps(body), '--json']
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        o = json.loads(r.stdout)
    except Exception:
        sys.exit(f'{what}: unparsed monid reply\n  stdout: {r.stdout[:400]}\n  stderr: {r.stderr[:400]}')
    if isinstance(o, dict) and o.get('error') and not find_key(o, 'runId'):
        sys.exit(f"{what}: {json.dumps(o['error'])} — no run was created, nothing billed")
    return o


def find_key(o, key):
    """the first value for `key` anywhere in the structure — the reply shape moves between versions"""
    if isinstance(o, dict):
        if key in o:
            return o[key]
        for v in o.values():
            f = find_key(v, key)
            if f is not None:
                return f
    elif isinstance(o, list):
        for v in o:
            f = find_key(v, key)
            if f is not None:
                return f
    return None


def ledger_path(root):
    return os.path.join(root, 'monid-urls.json')


def read_ledger(root):
    p = ledger_path(root)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def merge_ledger(root, name, url, remote):
    """MERGE — never overwrite. An overwrite on the kie leg once dropped 11 live URLs."""
    d = read_ledger(root)
    d[name] = url
    meta = d.setdefault('_paths', {})
    meta[name] = remote
    tmp = ledger_path(root) + '.tmp'
    json.dump(d, open(tmp, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    os.replace(tmp, ledger_path(root))
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file', nargs='?', help='local file to host')
    ap.add_argument('--root', default='.')
    ap.add_argument('--name', help='reference NAME the gate and the prompt use')
    ap.add_argument('--ttl', default='7d', choices=['1h', '1d', '7d', '30d'], help='bounds the URL, not the file')
    ap.add_argument('--prefix', default='refs', help='remote directory under the workspace')
    ap.add_argument('--list', action='store_true', help='print the local ledger')
    ap.add_argument('--rm', help='remove NAME from sfs and the ledger (frees quota)')
    ap.add_argument('--go', action='store_true', help='sfs is FREE; --go is kept so every venue leg reads the same')
    a = ap.parse_args()
    root = os.path.abspath(a.root)

    if a.list:
        d = read_ledger(root)
        paths = d.get('_paths', {})
        for k, v in sorted(d.items()):
            if k == '_paths':
                continue
            print(f'  {k:<28} {paths.get(k, "?"):<40} {v[:70]}…')
        print(f'{len([k for k in d if k != "_paths"])} hosted · {ledger_path(root)}')
        return

    if a.rm:
        d = read_ledger(root)
        remote = d.get('_paths', {}).get(a.rm)
        if not remote:
            sys.exit(f'{a.rm} is not in {ledger_path(root)} — nothing to remove')
        if not a.go:
            print(f'DRY RUN — would /rm {remote} and drop {a.rm} from the ledger. Re-run with --go.')
            return
        run_monid('/rm', {'path': remote, 'force': True}, '/rm')
        d.pop(a.rm, None); d.get('_paths', {}).pop(a.rm, None)
        json.dump(d, open(ledger_path(root), 'w', encoding='utf-8'), indent=1, sort_keys=True)
        print(f'removed {a.rm} ({remote}) — quota freed')
        return

    if not a.file or not a.name:
        ap.error('a file and --name are required (or --list / --rm)')
    src = a.file if os.path.isabs(a.file) else os.path.join(root, a.file)
    if not os.path.exists(src):
        sys.exit(f'missing: {src}')
    size = os.path.getsize(src)                      # the cap pinned into the signed URL — never by hand
    remote = f"{a.prefix}/{a.name}{os.path.splitext(src)[1]}"

    print(f'{a.name}  {os.path.relpath(src, root)}  {size} B  →  sfs:{remote}  (ttl {a.ttl}, $0.00)')
    if not a.go:
        print('DRY RUN — nothing uploaded. sfs is free; re-run with --go.')
        return

    put = run_monid('/put', {'path': remote, 'sizeBytes': size, 'ttl': a.ttl}, '/put')
    up = find_key(put, 'uploadUrl')
    if not up:
        sys.exit(f'/put returned no uploadUrl — reply: {json.dumps(put)[:500]}')

    if not shutil.which('curl'):
        sys.exit('curl not found — the bytes go by RAW PUT (curl -T), and multipart is silently wrong')
    # RAW PUT. `-F` would store the multipart envelope as the file.
    r = subprocess.run(['curl', '-sS', '-w', '%{http_code}', '-o', '/dev/null', '-T', src, up],
                       capture_output=True, text=True)
    code = (r.stdout or '').strip()[-3:]
    if code not in ('200', '201', '204'):
        sys.exit(f'upload HTTP {code or "?"} — {r.stderr[:300]}\n'
                 f'  an oversize file is rejected MID-STREAM: sizeBytes is a cap, not a hint')
    print(f'  uploaded HTTP {code}')

    cat = run_monid('/cat', {'path': remote, 'ttl': a.ttl}, '/cat')
    url = find_key(cat, 'downloadUrl') or find_key(cat, 'url')
    if not url:
        sys.exit(f'/cat returned no URL — reply: {json.dumps(cat)[:500]}')
    merge_ledger(root, a.name, url, remote)
    print(f'  {a.name} → {url[:90]}…\n  ledger {ledger_path(root)} (merged, {time.strftime("%Y-%m-%d %H:%M")})')
    print('  the URL expires with its ttl; the FILE does not — re-issue with a free /cat, never a re-upload')


if __name__ == '__main__':
    main()
