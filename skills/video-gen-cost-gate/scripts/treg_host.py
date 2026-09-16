#!/usr/bin/env python3
"""treg_host.py — host references on treg so a treg generation can cite them by public URL. FREE:
hosting is deliberately un-metered, the same courtesy polling gets, so it never touches the prepaid
balance. This is why `--target treg` never has to weigh "does a reference cost anything".

  treg_host.py --root <project> <file> [--name NAME] --go
  treg_host.py --root <project> --batch refs/*.png --go          names from file stems
  treg_host.py --root <project> --refresh [NAME ...] --go         re-host what has lapsed (a NEW url)
  treg_host.py --root <project> --verify                          read every recorded expiry; zero calls
  treg_host.py --root <project> --list

Writes <root>/treg-urls.json — {NAME: url} plus a `_meta` block — which is what
`refs_gate.py --target treg` reads.

THE LIFECYCLE, AND WHY IT IS A FOURTH CASE. Neither sibling's shape fits, so neither sibling's script does:

    Higgsfield   upload once, a UUID that never lapses          -> hf_upload.py: one file, skip if present
    kie          the URL dies in ~24 h                          -> kie_upload.py: re-upload every session
    monid/sfs    the FILE persists, the URL lapses with its ttl  -> monid_upload.py --refresh: a free /cat
                                                                    that moves no bytes, and the url's own
                                                                    `?e=` outlives a lost ledger
    treg         the BYTES and the URL die TOGETHER at 7 days,   -> this script: a refresh RE-UPLOADS, mints
                 and the url is an opaque token encoding nothing    a NEW url, and rewrites the ledger row

Three consequences the other two do not have, each read out of `superdesigndev/treg`'s own
`application/media.py` (Apache-2.0):

  1. **An unrecorded expiry is unrecoverable.** monid's `?e=<unix>` lets a lost ledger be rebuilt from
     the url. `treg host` returns `secrets.token_urlsafe(24)` and nothing else, so the ledger IS the
     only record — which is why refs_gate FAILS (not WARNs) on a treg reference with no expiry.
  2. **A refresh spends quota.** There is no dedup: re-hosting identical bytes inserts a new row with a
     new token. So a refresh is free in money and NOT free in the daily byte quota.
  3. **The quota is the real ceiling: 300 MB per org per 24 h, 30 MB per file** (MAX_BYTES /
     DAILY_ORG_BYTES). Ten maximal files a day, and the server's refusal is a 429 AFTER the upload
     streamed. This script counts the bytes it has hosted in the last 24 h from its own ledger and
     refuses first, because a reference batch is exactly the shape that walks into that wall.

Not a treg CLI wrapper beyond `treg host <file> --json`: the token stays in ~/.treg/config.json and
never reaches a command line here.
"""
import argparse, datetime, glob, hashlib, json, os, subprocess, sys, time

MAX_BYTES = 30 * 1024 * 1024          # treg application/media.py MAX_BYTES
DAILY_ORG_BYTES = 300 * 1024 * 1024   # treg application/media.py DAILY_ORG_BYTES — per ORG, not per project
TTL_DAYS = 7                          # treg application/media.py TTL
ALLOWED = ('image/', 'audio/', 'video/')
FMTS = ('%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z')   # isoformat() drops .%f at a whole second


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def parse_iso(s):
    """-> epoch seconds, or None. treg answers `<naive UTC isoformat>Z` (routers/media.py)."""
    if not s:
        return None
    for fmt in FMTS:
        try:
            t = time.strptime(s.replace('Z', '+0000'), fmt)
            return time.mktime(t) - time.timezone
        except Exception:
            continue
    return None


def human(secs):
    if secs is None:
        return 'unknown'
    if secs <= 0:
        return 'EXPIRED'
    return f'{secs/3600:.1f} h' if secs < 48 * 3600 else f'{secs/86400:.1f} d'


def load(root):
    p = os.path.join(root, 'treg-urls.json')
    if not os.path.exists(p):
        return {'_meta': {}}
    d = json.load(open(p, encoding='utf-8'))
    d.setdefault('_meta', {})
    return d


def save(root, d):
    p = os.path.join(root, 'treg-urls.json')
    json.dump(d, open(p, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    return p


def bytes_last_24h(led):
    cut = time.time() - 24 * 3600
    return sum(int(m.get('size') or 0) for m in led['_meta'].values()
               if (parse_iso(m.get('hosted_at')) or 0) >= cut)


def host_one(led, root, src, name, force, go):
    """-> (status, note). Idempotent: a recorded name whose file has not changed and whose url has more
    than a day left is left alone, because a re-host would spend quota to produce an identical reference."""
    if not os.path.isfile(src):
        return 'ERR', f'no file at {src}'
    size = os.path.getsize(src)
    if size > MAX_BYTES:
        return 'ERR', f'{size} bytes; treg refuses anything over {MAX_BYTES} (30 MB) — downscale it first'
    if size == 0:
        return 'ERR', 'empty file; treg refuses an empty body'
    dg = sha256(src)
    m = led['_meta'].get(name) or {}
    left = (parse_iso(m.get('expires_at')) or 0) - time.time()
    if not force and led.get(name) and m.get('sha256') == dg and left > 86400:
        return 'skip', f'unchanged and good for {human(left)}'
    used = bytes_last_24h(led)
    if used + size > DAILY_ORG_BYTES:
        return 'ERR', (f'this ledger has hosted {used/(1<<20):.0f} MB in the last 24 h and the org quota is '
                       f'{DAILY_ORG_BYTES/(1<<20):.0f} MB — treg answers 429 AFTER the upload streams. Wait, or '
                       f'host fewer/smaller references')
    if not go:
        return 'plan', f'would host {size/(1<<20):.1f} MB (free; {(used+size)/(1<<20):.0f}/{DAILY_ORG_BYTES/(1<<20):.0f} MB of the 24 h quota)'
    r = subprocess.run(['treg', 'host', src, '--json'], capture_output=True, text=True)
    if r.returncode != 0:
        return 'ERR', f'treg host failed: {(r.stderr or r.stdout).strip()[:200]}'
    try:
        body = json.loads(r.stdout)
    except Exception:
        return 'ERR', f'treg host did not answer json: {r.stdout.strip()[:200]}'
    url, exp = body.get('url'), body.get('expires_at')
    if not url:
        return 'ERR', f'treg host answered without a url: {r.stdout.strip()[:200]}'
    ctype = body.get('content_type') or ''
    if not ctype.startswith(ALLOWED):
        return 'ERR', f'treg hosted it as {ctype!r}; only image/*, audio/* and video/* are fetchable by a vendor'
    led[name] = url
    led['_meta'][name] = {'expires_at': exp, 'sha256': dg, 'size': size, 'content_type': ctype,
                          'source': os.path.relpath(src, root), 'hosted_at':
                          datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'}
    return 'ok', f'{url}  expires {exp} ({human((parse_iso(exp) or 0) - time.time())})'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file', nargs='?')
    ap.add_argument('--root', default='.')
    ap.add_argument('--name', help='reference NAME (default: the file stem)')
    ap.add_argument('--batch', nargs='+', metavar='FILE', help='host many; each NAME is its file stem')
    ap.add_argument('--refresh', nargs='*', metavar='NAME',
                    help='re-host lapsed references (no NAME = every one under 24 h). A refresh RE-UPLOADS '
                         'and mints a NEW url; the bytes died with the old one')
    ap.add_argument('--verify', action='store_true', help='read every recorded expiry locally; zero API calls')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--force', action='store_true', help='re-host even when the digest matches and the url is live')
    ap.add_argument('--go', action='store_true', help='hosting is FREE; --go is kept so every venue leg reads alike')
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    led = load(root)

    if a.list or a.verify:
        now = time.time()
        names = sorted(k for k in led if k != '_meta')
        if not names:
            print('treg-urls.json holds no references'); return 0
        bad = 0
        for n in names:
            m = led['_meta'].get(n) or {}
            e = parse_iso(m.get('expires_at'))
            left = None if e is None else e - now
            gone = e is None or left <= 0
            bad += gone
            print(f'  {"STALE" if gone else "live "} {n:<22} {human(left):>8}  {led[n]}')
        print(f'{len(names)} references, {bad} need a re-host; '
              f'{bytes_last_24h(led)/(1<<20):.0f}/{DAILY_ORG_BYTES/(1<<20):.0f} MB of the 24 h org quota used')
        if bad:
            print(f'free fix: treg_host.py --root {a.root} --refresh --go')
        return 1 if bad else 0

    jobs = []
    if a.refresh is not None:
        names = a.refresh or [k for k in led if k != '_meta']
        for n in sorted(names):
            m = led['_meta'].get(n) or {}
            src = m.get('source')
            if not src:
                print(f'  ERR   {n}: no source recorded — host it by path'); continue
            e = parse_iso(m.get('expires_at'))
            if not a.refresh and e is not None and e - time.time() > 86400:
                continue
            jobs.append((os.path.join(root, src), n))
    elif a.batch:
        for f in [g for pat in a.batch for g in sorted(glob.glob(pat)) or [pat]]:
            jobs.append((f, os.path.splitext(os.path.basename(f))[0]))
    elif a.file:
        jobs.append((a.file, a.name or os.path.splitext(os.path.basename(a.file))[0]))
    else:
        ap.error('give a file, --batch, --refresh, --list or --verify')

    rc = 0
    for src, name in jobs:
        st, note = host_one(led, root, src, name, a.force or a.refresh is not None, a.go)
        print(f'  {st:<5} {name:<22} {note}')
        rc |= int(st == 'ERR')
    if a.go:
        print('wrote', save(root, led))
    else:
        print('nothing written — add --go')
    return rc


if __name__ == '__main__':
    sys.exit(main())
