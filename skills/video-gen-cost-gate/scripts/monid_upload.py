#!/usr/bin/env python3
"""monid_upload.py — host references on monid's Simple FS (`sfs`) so a monid generation can cite them by
public URL. FREE: every sfs endpoint is $0.00 PER_CALL, 1 GB per workspace. This is why no monid venue is
blocked on "needs a public URL".

  monid_upload.py --root <project> <file> [--name NAME] [--ttl 7d] [--prefix refs] --go
  monid_upload.py --root <project> --batch refs/*.png [--ttl 7d] --go     names from file stems
  monid_upload.py --root <project> --refresh [NAME ...] --go              re-issue LAPSED urls, free
  monid_upload.py --root <project> --verify                               one recursive /ls, free
  monid_upload.py --root <project> --list
  monid_upload.py --root <project> --rm NAME --go

Writes <root>/monid-urls.json — {NAME: url} plus a `_meta` block — which is what
`refs_gate.py --target monid` and `monid_submit.py` read.

THE LIFECYCLE THIS SCRIPT EXISTS TO GET RIGHT. monid is a THIRD case, and neither sibling's shape fits:

    Higgsfield   upload once, a UUID that never lapses   -> hf_upload.py: one file, skip if present
    kie          the URL dies in ~24 h                    -> kie_upload.py: batch, re-upload every session
    monid/sfs    the FILE persists forever, the URL lapses with its ttl, and re-issuing is a FREE /cat

So this script does both: it hosts like Higgsfield (once, idempotent) and refreshes like nothing else
(`--refresh`, which never re-uploads a byte). Three measured facts drive the rest:

  1. `/cat` returns `expiresAt` (ISO 8601) alongside the url, and the url itself carries `?e=<unix>`.
     Both are recorded, so expiry is checked LOCALLY at zero calls — and recoverable from the url alone
     if the ledger is ever lost.
  2. `/ls` returns `entries[]` of {path, type, sizeBytes, lastModified} and takes `recursive` — so ONE
     free call verifies the whole reference set, not one call per reference.
  3. `/rm` revokes the LINK but does not recall a copy already served: a never-fetched url 404s at once,
     one fetched first kept serving from an edge cache. An sfs url that has left the machine is public
     until its ttl lapses — so a client's own asset gets a SHORT ttl, not the default.

And two wire rules that fail silently if broken: the bytes go by RAW PUT (`curl -T`), never multipart
(`-F`), and `sizeBytes` is REQUIRED and is a cap PINNED INTO the signed url — an oversize upload is
rejected mid-stream, after a 200 on the handshake. It is computed from the file here, never passed by hand.
"""
import argparse, datetime, glob, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.parse

TTLS = ['1h', '1d', '7d', '30d']


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def find_key(o, key):
    """the first value for `key` anywhere in the structure — reply shapes move between versions"""
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


def run_sfs(endpoint, body, what):
    if not shutil.which('monid'):
        sys.exit('monid CLI not found — npm install -g @monid-ai/cli, then `monid keys add`')
    r = subprocess.run(['monid', 'run', '-p', 'sfs', '-e', endpoint, '-i', json.dumps(body), '--json'],
                       capture_output=True, text=True)
    try:
        o = json.loads(r.stdout)
    except Exception:
        sys.exit(f'{what}: unparsed monid reply\n  stdout: {r.stdout[:400]}\n  stderr: {r.stderr[:400]}')
    # A body the gateway refuses returns a bare {"error": ...} with NO runId: no run, nothing billed.
    if isinstance(o, dict) and o.get('error') and not find_key(o, 'runId'):
        return None, f"{json.dumps(o['error'])} — no run created, $0.00"
    # status COMPLETED is the RUN finishing; the provider's own result is providerResponse.httpStatus.
    http = (o.get('providerResponse') or {}).get('httpStatus')
    if isinstance(http, int) and not 200 <= http < 300:
        err = json.dumps((o.get('providerResponse') or {}).get('error') or {})[:200]
        return None, f'provider HTTP {http} {err} (not charged)'
    return o, None


def url_expiry(url, meta_expires=None):
    """seconds until the signed url lapses. Prefers the recorded expiresAt; falls back to the url's own
    `?e=<unix>`, so expiry survives a lost ledger."""
    if meta_expires:
        try:
            t = datetime.datetime.fromisoformat(meta_expires.replace('Z', '+00:00'))
            return (t - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        except Exception:
            pass
    m = re.search(r'[?&]e=(\d+)', url or '')
    if m:
        return int(m.group(1)) - time.time()
    return None


def human(secs):
    if secs is None:
        return 'unknown'
    if secs <= 0:
        return 'EXPIRED'
    if secs < 3600:
        return f'{secs / 60:.0f} min'
    if secs < 86400:
        return f'{secs / 3600:.1f} h'
    return f'{secs / 86400:.1f} d'


class Ledger:
    def __init__(self, root):
        self.path = os.path.join(root, 'monid-urls.json')
        self.d = json.load(open(self.path, encoding='utf-8')) if os.path.exists(self.path) else {}
        self.d.setdefault('_meta', {})
        for name, p in (self.d.pop('_paths', None) or {}).items():     # migrate the v1 shape
            self.d['_meta'].setdefault(name, {})['path'] = p

    def names(self):
        return sorted(k for k in self.d if not k.startswith('_'))

    def meta(self, name):
        return self.d['_meta'].get(name, {})

    def put(self, name, url, **meta):
        """MERGE — never overwrite. A --json-out overwrite on the kie leg once dropped 11 live URLs."""
        self.d[name] = url
        self.d['_meta'].setdefault(name, {}).update(meta)

    def drop(self, name):
        self.d.pop(name, None)
        self.d['_meta'].pop(name, None)

    def save(self):
        tmp = self.path + '.tmp'
        json.dump(self.d, open(tmp, 'w', encoding='utf-8'), indent=1, sort_keys=True)
        os.replace(tmp, self.path)


def cat(path, ttl, what):
    o, err = run_sfs('/cat', {'path': path, 'ttl': ttl}, what)
    if err:
        return None, None, err
    out = o.get('output') or {}
    return (find_key(out, 'url'), out.get('expiresAt'), None)


def host_one(led, root, src, name, ttl, prefix, force):
    """upload one file; returns a one-word disposition"""
    digest = sha256(src)
    m = led.meta(name)
    if not force and name in led.d and m.get('sha256') == digest:
        left = url_expiry(led.d[name], m.get('expiresAt'))
        if left is not None and left > 0:
            return 'skip', f'already hosted, url good for {human(left)}'
        url, exp, err = cat(m.get('path') or f'{prefix}/{name}{os.path.splitext(src)[1]}', ttl, '/cat')
        if err:
            return 'FAIL', f'refresh failed: {err}'
        led.put(name, url, expiresAt=exp)
        return 'refresh', f'file intact, url re-issued free — good for {human(url_expiry(url, exp))}'
    if not force and name in led.d and m.get('sha256') and m['sha256'] != digest:
        note = 'changed'
    else:
        note = 'hosted'
    remote = f'{prefix}/{name}{os.path.splitext(src)[1]}'
    size = os.path.getsize(src)                       # the cap pinned into the signed url
    o, err = run_sfs('/put', {'path': remote, 'sizeBytes': size, 'ttl': ttl}, '/put')
    if err:
        return 'FAIL', err
    up = find_key(o, 'uploadUrl')
    if not up:
        return 'FAIL', 'no uploadUrl in reply'
    # RAW PUT. `-F` would store the multipart envelope as the file.
    r = subprocess.run(['curl', '-sS', '-w', '%{http_code}', '-o', '/dev/null', '-T', src, up],
                       capture_output=True, text=True)
    code = (r.stdout or '').strip()[-3:]
    if code not in ('200', '201', '204'):
        return 'FAIL', f'upload HTTP {code or "?"} — oversize is rejected MID-STREAM ({r.stderr[:120]})'
    url, exp, err = cat(remote, ttl, '/cat')
    if err:
        return 'FAIL', f'uploaded but /cat failed: {err}'
    led.put(name, url, path=remote, sha256=digest, sizeBytes=size, expiresAt=exp,
            resourceId=(find_key(o, 'resourceId') or ''), hostedAt=time.strftime('%Y-%m-%d %H:%M'))
    prefix_msg = 'LOCAL FILE CHANGED since hosting — re-uploaded; ' if note == 'changed' else ''
    return note, f'{prefix_msg}{size} B → {remote}, url good for {human(url_expiry(url, exp))}'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file', nargs='?')
    ap.add_argument('--root', default='.')
    ap.add_argument('--name', help='reference NAME (default: the file stem)')
    ap.add_argument('--batch', nargs='+', metavar='FILE', help='host many; each NAME is its file stem')
    ap.add_argument('--refresh', nargs='*', metavar='NAME',
                    help='re-issue lapsed urls with a free /cat (no NAME = every lapsed one)')
    ap.add_argument('--verify', action='store_true', help='one recursive /ls: do the files still exist?')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--rm', metavar='NAME')
    ap.add_argument('--ttl', default='7d', choices=TTLS, help='bounds the URL, never the file')
    ap.add_argument('--prefix', default='refs')
    ap.add_argument('--force', action='store_true', help='re-upload even when the digest matches')
    ap.add_argument('--warn-under-min', type=float, default=30,
                    help='flag a url with less than this many minutes left (a gen p95 is ~10 min)')
    ap.add_argument('--go', action='store_true', help='sfs is FREE; --go is kept so every venue leg reads alike')
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    led = Ledger(root)

    if a.list:
        for n in led.names():
            m = led.meta(n)
            print(f"  {n:<26} {str(m.get('path','?')):<34} {human(url_expiry(led.d[n], m.get('expiresAt'))):>9}  "
                  f"{(m.get('sha256') or '')[:10]}")
        print(f'{len(led.names())} hosted · {led.path}')
        return

    if a.verify:
        o, err = run_sfs('/ls', {'path': a.prefix, 'recursive': True, 'limit': 1000}, '/ls')
        if err:
            sys.exit(f'/ls {a.prefix}: {err}')
        live = {e['path'] for e in ((o.get('output') or {}).get('entries') or []) if e.get('type') == 'file'}
        bad = 0
        for n in led.names():
            m = led.meta(n)
            p = m.get('path')
            left = url_expiry(led.d[n], m.get('expiresAt'))
            gone = p not in live
            stale = left is not None and left <= 0
            if gone:
                print(f'  ✗ {n:<24} FILE MISSING on sfs ({p}) — re-upload it'); bad += 1
            elif stale:
                print(f'  ⚠ {n:<24} url EXPIRED, file intact — free fix: --refresh {n}'); bad += 1
            elif left is not None and left < a.warn_under_min * 60:
                print(f'  ⚠ {n:<24} url lapses in {human(left)} — --refresh {n} before the GO'); bad += 1
            else:
                print(f'  ✓ {n:<24} file present, url good for {human(left)}')
        print(f'\n{len(led.names())} references · {bad} need attention · one /ls call · $0.00')
        sys.exit(1 if bad else 0)

    if a.refresh is not None:
        want = a.refresh or led.names()
        todo = []
        for n in want:
            if n not in led.d:
                print(f'  {n}: not in the ledger — host it first'); continue
            m = led.meta(n)
            left = url_expiry(led.d[n], m.get('expiresAt'))
            if a.refresh or left is None or left < a.warn_under_min * 60:
                todo.append(n)
        if not todo:
            print('every url is still good — nothing to refresh'); return
        print(f'{len(todo)} to re-issue by free /cat (no bytes move): {", ".join(todo)}')
        if not a.go:
            print('DRY RUN — re-run with --go. This is free.'); return
        for n in todo:
            m = led.meta(n)
            url, exp, err = cat(m.get('path'), a.ttl, '/cat')
            if err:
                print(f'  ✗ {n}: {err}'); continue
            led.put(n, url, expiresAt=exp)
            print(f'  ✓ {n} → good for {human(url_expiry(url, exp))}')
        led.save()
        print(f'ledger {led.path}')
        return

    if a.rm:
        m = led.meta(a.rm)
        if a.rm not in led.d:
            sys.exit(f'{a.rm} is not in {led.path}')
        if not a.go:
            print(f"DRY RUN — would /rm {m.get('path')} and drop {a.rm}. Re-run with --go."); return
        _, err = run_sfs('/rm', {'path': m.get('path'), 'force': True}, '/rm')
        if err:
            print(f'  /rm: {err}')
        led.drop(a.rm); led.save()
        print(f"removed {a.rm} ({m.get('path')}) — quota freed.\n"
              f"  ⚠ this revokes the LINK; a copy already fetched can still serve from cache until the ttl lapses")
        return

    srcs = []
    if a.batch:
        for pat in a.batch:
            # resolve against --root, not the cwd: every other path in this script does, and a shell
            # that did not expand the glob would otherwise silently match nothing
            pat_abs = pat if os.path.isabs(pat) else os.path.join(root, pat)
            hits = sorted(glob.glob(pat_abs)) or ([pat_abs] if os.path.exists(pat_abs) else [])
            if not hits:
                sys.exit(f'no file matches: {pat}  (looked under {root})')
            srcs += [(h, os.path.splitext(os.path.basename(h))[0]) for h in hits]
    elif a.file:
        srcs = [(a.file, a.name or os.path.splitext(os.path.basename(a.file))[0])]
    else:
        ap.error('give a file, --batch, --refresh, --verify, --list or --rm')

    for p, _ in srcs:
        if not os.path.exists(p if os.path.isabs(p) else os.path.join(root, p)):
            sys.exit(f'missing: {p}')
    if len(srcs) > 30:
        print(f'⚠ {len(srcs)} files — seedance cites at most 30 reference images per call '
              f'(hosting more is fine; the CALL is what caps)')

    print(f'{len(srcs)} reference(s) → sfs:{a.prefix}/ (ttl {a.ttl}, $0.00 — every sfs call is free)')
    for p, n in srcs:
        print(f'  {n:<26} {p}')
    if not a.go:
        print('\nDRY RUN — nothing uploaded. sfs is free; re-run with --go.')
        return

    tally = {}
    for p, n in srcs:
        src = p if os.path.isabs(p) else os.path.join(root, p)
        what, msg = host_one(led, root, src, n, a.ttl, a.prefix, a.force)
        tally[what] = tally.get(what, 0) + 1
        mark = {'skip': '·', 'refresh': '↻', 'FAIL': '✗'}.get(what, '✓')
        print(f'  {mark} {n:<26} {msg}')
        led.save()                                     # after EACH — a kill mid-batch loses nothing
    print(f"\n{led.path} — " + ' · '.join(f'{v} {k}' for k, v in sorted(tally.items())))
    if tally.get('FAIL'):
        sys.exit(1)


if __name__ == '__main__':
    main()
