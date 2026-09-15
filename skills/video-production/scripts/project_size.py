#!/usr/bin/env python3
"""project_size.py — the project's size split into SUBSTRATE (what the spots are made from) and DERIVED (what the builds make),
and inside derived the SUPERSEDED set: versions older than the kept tags, `.bak` copies, scratch. It classifies by directory
role and by name, prints the table, and writes a plan file the operator names deletions from — it never deletes anything.
The cleanup prompt at every phase boundary is this table (video-production § 5).

  project_size.py --root <project> [--keep-tags super=v7p,short=v7p,cutC=v7h] [--plan CLEANUP-PLAN-<date>.txt]
  project_size.py --selftest
Roles (overridable with --substrate-dirs / --derived-dirs, comma lists relative to the root):
  substrate: assets takes references startframes prompts tools docs brand logs receipts audio/vo audio/music audio/sfx audio/clean gen
  derived:   edit review deliver scratch audio/mixes audio/reels
A derived file is SUPERSEDED when its name carries a version tag (`-v\\d+[a-z]?`) that is not the kept tag of its spot, when
it is a `.bak-*` copy, or when it sits under scratch. A file under neither role is listed as "other" and never proposed.
"""
import argparse, os, re, sys, tempfile, time

SUBSTRATE = ['assets', 'takes', 'references', 'startframes', 'prompts', 'tools', 'docs', 'brand', 'logs', 'receipts', 'audio/vo', 'audio/music', 'audio/sfx', 'audio/clean', 'gen']
DERIVED = ['edit', 'review', 'deliver', 'scratch', 'audio/mixes', 'audio/reels']
TAG = re.compile(r'-(v\d+[a-z]?)(?=[.-]|$)')


def classify(root, keep, substrate, derived):
    rows = {'substrate': [], 'derived-current': [], 'derived-superseded': [], 'other': []}
    for dp, dn, fn in os.walk(root):
        rel_dir = os.path.relpath(dp, root).replace(os.sep, '/'); rel_dir = '' if rel_dir == '.' else rel_dir
        for f in fn:
            rel = f'{rel_dir}/{f}' if rel_dir else f
            try: sz = os.path.getsize(os.path.join(dp, f))
            except OSError: continue
            role = 'other'
            if any(rel == d or rel.startswith(d + '/') for d in derived): role = 'derived'
            elif any(rel == d or rel.startswith(d + '/') for d in substrate): role = 'substrate'
            if role == 'derived':
                sup = '.bak-' in f or rel.startswith('scratch/')
                m = TAG.search(f)
                if m and not sup:
                    spot = next((k for k in keep if k and k in f), None)
                    sup = (keep.get(spot) != m.group(1)) if spot else (m.group(1) not in keep.values())
                role = 'derived-superseded' if sup else 'derived-current'
            rows[role].append((rel, sz))
    return rows


def report(rows, plan=None):
    out = []
    for k in ('substrate', 'derived-current', 'derived-superseded', 'other'):
        tot = sum(s for _, s in rows[k]); out.append(f'{tot / 1e9:8.2f} GB  {len(rows[k]):6d} files  {k}')
    sup = sorted(rows['derived-superseded'], key=lambda x: -x[1])
    if sup:
        by = {}
        for rel, sz in sup: by.setdefault(rel.split('/')[0] + ('/' + rel.split('/')[1] if rel.count('/') > 1 else ''), []).append((rel, sz))
        out.append('superseded by category (the operator names what goes; one delete per category):')
        for cat, items in sorted(by.items(), key=lambda kv: -sum(s for _, s in kv[1])): out.append(f'  {sum(s for _, s in items) / 1e9:7.2f} GB  {len(items):5d}  {cat}')
    if plan:
        with open(plan, 'w', encoding='utf-8') as w:
            w.write(f'# cleanup plan {time.strftime("%Y-%m-%d %H:%M")} — proposal; nothing deleted; the operator names categories or paths\n\n' + '\n'.join(out) + '\n\n## derived-superseded (exact paths)\n')
            for rel, sz in sup: w.write(f'{sz / 1e6:10.1f} MB  {rel}\n')
        out.append(f'plan written: {plan}')
    return '\n'.join(out)


def selftest():
    d = tempfile.mkdtemp()
    def mk(rel, n):
        p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'wb').write(b'x' * n)
    mk('assets/C1.mp4', 1000); mk('edit/mezz/spot-1080x1920-v7n-composite.mov', 3000); mk('edit/mezz/spot-1080x1920-v7o-composite.mov', 4000)
    mk('edit/mezz/spot-1080x1920-v7o-composite.mov.bak-2026-rebuild', 500); mk('scratch/x/ev_a1.mov', 200); mk('deliver/final/spot-1080x1920-v7o.mp4', 100); mk('notes.txt', 10)
    r = classify(d, {'spot': 'v7o'}, SUBSTRATE, DERIVED)
    got = {k: sum(s for _, s in v) for k, v in r.items()}
    want = {'substrate': 1000, 'derived-current': 4100, 'derived-superseded': 3700, 'other': 10}
    ok = got == want
    print(f"SELFTEST {'PASS' if ok else 'FAIL'}: {got} (want {want})"); sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--keep-tags', default='', help='spot=tag,… — the versions that are current')
    ap.add_argument('--plan', default=None); ap.add_argument('--substrate-dirs', default=','.join(SUBSTRATE)); ap.add_argument('--derived-dirs', default=','.join(DERIVED))
    ap.add_argument('--selftest', action='store_true'); a = ap.parse_args()
    if a.selftest: selftest()
    keep = {kv.split('=')[0]: kv.split('=')[1] for kv in a.keep_tags.split(',') if '=' in kv}
    rows = classify(a.root, keep, [x for x in a.substrate_dirs.split(',') if x], [x for x in a.derived_dirs.split(',') if x])
    print(report(rows, a.plan))


if __name__ == '__main__':
    main()
