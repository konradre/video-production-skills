#!/usr/bin/env python3
"""venue_drift.py — has a venue changed the contract VENUES.md was written against? Vendors move a cap, an enum, a
role or a price without notice, and the first sign is otherwise a billed call that behaves differently. This reads
each watched venue's OWN machine-readable contract — free reads only: `monid inspect`, `treg catalog get`, fal's
public OpenAPI — keeps the load-bearing part (inputs, caps, enums, prices; never live latency or success counts),
hashes it, and compares it with the baseline accepted when VENUES.md was last reconciled against it.

  venue_drift.py [--watch FILE] [--state FILE] [--only NAME,NAME]     → OK | NEW | DRIFT | ERROR per target
  venue_drift.py --accept NAME[,NAME]|all [--only …]                  → the current contract becomes the baseline
  venue_drift.py --selftest

A DRIFT prints a unified diff of the normalised contract and the VENUES.md row to reconcile, and the baseline moves
ONLY on --accept — after the row is updated — so the alarm keeps firing until someone has read the change. NEW means no
baseline yet: read the contract against its row, then --accept. An ERROR (a failed read) is never drift and never moves
the baseline. A watch target is a free read by construction: a command outside FREE_READS is refused unrun.
Exit 0 every target OK or NEW · 1 any DRIFT · 2 every target errored.
State: $VENUE_DRIFT_STATE, default ~/.local/state/video-gen-cost-gate/venue-drift.json (per machine, outside any repo).
Watch list: references/venue-watch.json beside this skill. Pattern: cclank/lanshu-awesome-ai-video-kit
scripts/monitor_models.py (a vendor page hashed against a baseline) — narrowed here to machine-readable contracts, and
its re-baseline on every run replaced by an explicit accept, so a change cannot fire once and fall silent.
"""
import argparse, difflib, hashlib, json, os, subprocess, sys, tempfile, threading, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WATCH = os.path.join(HERE, '..', 'references', 'venue-watch.json')
STATE = os.environ.get('VENUE_DRIFT_STATE', os.path.expanduser('~/.local/state/video-gen-cost-gate/venue-drift.json'))
FREE_READS = [('monid', 'inspect'), ('treg', 'catalog', 'get')]


def free(cmd):
    return any(tuple(cmd[:len(f)]) == f for f in FREE_READS)


def fetch(t, timeout=60):
    if 'cmd' in t:
        if not free(t['cmd']):
            raise ValueError(f"{' '.join(t['cmd'][:3])} is not a free read ({FREE_READS}) — refused unrun")
        p = subprocess.run(t['cmd'], capture_output=True, text=True, timeout=timeout)
        if p.returncode != 0:
            raise RuntimeError(f"exit {p.returncode}: {(p.stderr or p.stdout).strip()[:160]}")
        return p.stdout
    req = urllib.request.Request(t['url'], headers={'User-Agent': 'venue-drift/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def normalise(t, raw):
    if t.get('format') == 'json':
        d = json.loads(raw)
        if t.get('keep'):
            d = {k: d.get(k) for k in t['keep']}
        return json.dumps(d, sort_keys=True, indent=1, ensure_ascii=False) + '\n'
    lines = raw.splitlines()
    a, b = t.get('between', [None, None])
    if a:
        i = next((n for n, l in enumerate(lines) if l.strip().startswith(a)), None)
        if i is None: raise ValueError(f'section marker {a!r} not found — the page changed shape')
        lines = lines[i:]
    if b:
        j = next((n for n, l in enumerate(lines) if l.strip().startswith(b)), None)
        if j is not None: lines = lines[:j]
    out, blank = [], False
    for l in (l.rstrip() for l in lines):
        if not l and blank: continue
        blank = not l; out.append(l)
    return '\n'.join(out).strip() + '\n'


def read_state(path):
    try:
        return json.load(open(path, encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def write_state(path, st):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    json.dump(st, open(tmp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False); os.replace(tmp, path)


def run(watch, state_path, only=None, accept=None, out=print):
    targets = [t for t in json.load(open(watch, encoding='utf-8'))['targets'] if not only or t['name'] in only]
    st = read_state(state_path); counts = {'OK': 0, 'NEW': 0, 'DRIFT': 0, 'ERROR': 0}; changed = False
    for t in targets:
        try:
            text = normalise(t, fetch(t))
        except Exception as e:
            counts['ERROR'] += 1; out(f"ERROR  {t['name']}: {type(e).__name__}: {str(e)[:200]}"); continue
        h = hashlib.sha256(text.encode()).hexdigest(); base = st.get(t['name'])
        if accept and ('all' in accept or t['name'] in accept):
            st[t['name']] = {'sha256': h, 'text': text, 'accepted': time.strftime('%Y-%m-%d %H:%M'), 'venues': t.get('venues', '')}
            changed = True; out(f"ACCEPT {t['name']} {h[:12]} — the baseline for {t.get('venues', '')}"); counts['OK'] += 1; continue
        if not base:
            counts['NEW'] += 1; out(f"NEW    {t['name']} {h[:12]} — no baseline: read it against {t.get('venues', 'its VENUES row')}, then --accept {t['name']}")
        elif base['sha256'] == h:
            counts['OK'] += 1; out(f"OK     {t['name']} {h[:12]} (accepted {base.get('accepted', '?')})")
        else:
            counts['DRIFT'] += 1
            out(f"DRIFT  {t['name']} {base['sha256'][:12]} → {h[:12]} — reconcile {t.get('venues', 'its VENUES row')}, then --accept {t['name']}")
            diff = list(difflib.unified_diff(base['text'].splitlines(), text.splitlines(), 'accepted', 'now', n=1, lineterm=''))
            for l in diff[:60]: out('       ' + l)
            if len(diff) > 60: out(f'       … {len(diff) - 60} more diff lines')
    if changed: write_state(state_path, st)
    out(f"VENUE-DRIFT {'DRIFT' if counts['DRIFT'] else 'OK'} — " + ' · '.join(f'{v} {k}' for k, v in counts.items()))
    if counts['DRIFT']: return 1
    return 2 if targets and counts['ERROR'] == len(targets) else 0


def selftest():
    import http.server
    pages = {'/j': json.dumps({'input': {'duration': {'max': 30}}, 'price': 10.7, 'metrics': {'p50': 1}}),
             '/t': 'HEADER\n  WORKS 100% (9)\nPARAMS\n  duration  integer  4-30\nPRICE TABLE\n  480p  $0.1186\nRUN IT\n  treg call …\n'}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = pages.get(self.path)
            if body is None: self.send_response(404); self.end_headers(); return
            self.send_response(200); self.end_headers(); self.wfile.write(body.encode())
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{srv.server_port}'
    cases = []
    with tempfile.TemporaryDirectory() as d:
        watch, state = os.path.join(d, 'watch.json'), os.path.join(d, 'state.json')
        json.dump({'targets': [{'name': 'json', 'url': base + '/j', 'format': 'json', 'keep': ['input', 'price'], 'venues': 'row J'},
                               {'name': 'text', 'url': base + '/t', 'format': 'text', 'between': ['PARAMS', 'RUN IT'], 'venues': 'row T'}]},
                  open(watch, 'w'))
        log = []; say = log.append
        rc = run(watch, state, out=say); cases.append(('first read → NEW, no baseline written', rc == 0 and sum(l.startswith('NEW ') for l in log) == 2 and not os.path.exists(state)))
        log.clear(); rc = run(watch, state, accept={'all'}, out=say); cases.append(('--accept all writes the baselines', rc == 0 and os.path.exists(state)))
        log.clear(); rc = run(watch, state, out=say); cases.append(('an unchanged contract → OK', rc == 0 and sum(l.startswith('OK ') for l in log) == 2))
        pages['/j'] = json.dumps({'input': {'duration': {'max': 30}}, 'price': 10.7, 'metrics': {'p50': 999}})
        pages['/t'] = pages['/t'].replace('WORKS 100% (9)', 'WORKS 97% (40)')
        log.clear(); rc = run(watch, state, out=say); cases.append(('a live metric outside the kept part moves → still OK', rc == 0 and sum(l.startswith('OK ') for l in log) == 2))
        pages['/j'] = json.dumps({'input': {'duration': {'max': 15}}, 'price': 10.7})
        log.clear(); rc = run(watch, state, out=say)
        cases.append(('a cap moves → DRIFT with the diff and the row to reconcile', rc == 1 and any('DRIFT  json' in l and 'row J' in l for l in log) and any('"max": 15' in l for l in log)))
        log.clear(); rc = run(watch, state, out=say); cases.append(('the baseline did not move: DRIFT again on the next run', rc == 1))
        pages['/t'] = pages['/t'].replace('$0.1186', '$0.1299')
        log.clear(); rc = run(watch, state, only={'text'}, out=say); cases.append(('a price inside the section moves → DRIFT', rc == 1 and any('DRIFT  text' in l for l in log)))
        log.clear(); rc = run(watch, state, accept={'json', 'text'}, out=say); log.clear(); rc = run(watch, state, out=say)
        cases.append(('--accept after the row is reconciled → OK', rc == 0))
        del pages['/j']; del pages['/t']
        log.clear(); rc = run(watch, state, out=say); cases.append(('failed reads → ERROR, never drift; all errored → exit 2', rc == 2 and sum(l.startswith('ERROR') for l in log) == 2))
        cases.append(('the baselines survived the failed reads', set(read_state(state)) == {'json', 'text'}))
        json.dump({'targets': [{'name': 'bad', 'cmd': ['rm', '-rf', '/tmp/nothing'], 'format': 'text'}]}, open(watch, 'w'))
        log.clear(); rc = run(watch, state, out=say); cases.append(('a command outside the free reads is refused unrun', rc == 2 and any('refused unrun' in l for l in log)))
        cases.append(('monid inspect and treg catalog get are free reads', free(['monid', 'inspect', '-p', 'x']) and free(['treg', 'catalog', 'get', 'x']) and not free(['treg', 'call', 'x'])))
    srv.shutdown()
    for name, ok in cases: print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in cases); print(f"venue_drift selftest {'PASS' if ok else 'FAIL'}"); return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--watch', default=WATCH); ap.add_argument('--state', default=STATE)
    ap.add_argument('--only', help='comma-separated target names'); ap.add_argument('--accept', help='NAME[,NAME] or all')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    csv = lambda s: {x.strip() for x in (s or '').split(',') if x.strip()} or None
    sys.exit(run(a.watch, a.state, csv(a.only), csv(a.accept)))


if __name__ == '__main__':
    main()
