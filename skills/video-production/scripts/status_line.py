#!/usr/bin/env python3
"""status_line.py — the status template every turn of a video production carries: the deliverable path, the balances
(read where an API allows a FREE read; said to be UNREADABLE where it does not — never shown as 0), the free space on the working drive (a mezzanine pair per version fills
it), the background jobs (named, or "none"), and the open items. Nothing here spends; every read is free.

  status_line.py --root <project> [--deliverable deliver/<file>.mp4] [--drive /mnt/c] [--min-free-gb 6]
                 [--higgsfield] [--higgsfield-api] [--monid] [--treg] [--elevenlabs] [--open "the client's verdict on S02"] [--job "rhea A2F (log: …)"]
--higgsfield runs `higgsfield account status` (the CLI's free read: balance, plan, recent transactions) when the CLI is on the PATH —
the SUBSCRIPTION's wallet only; the Higgsfield API bills a separate wallet that command cannot see. --higgsfield-api reports that API
wallet from the ledger `video-gen-cost-gate/scripts/hf_api.py` keeps ($HF_API_LEDGER): the API has no balance endpoint, so the figure
is our own arithmetic and is labelled an ESTIMATE, and with no ledger it is unreadable, never 0. --monid runs `monid balance`, the
pay-as-you-go wallet in dollars (also free); --treg runs `treg balance --json` (free: the prepaid wallet and any call in flight);
--elevenlabs reads the plan's character count with ELEVENLABS_API_KEY from the environment. Vendors with no balance endpoint are
reported as unreadable.
A balance is REPORTED, never ranked on: venue choice is by marginal cost, and a low wallet is a funding question
(`video-gen-cost-gate/references/VENUES.md` § Venue ranking).
"""
import argparse, json, os, re, shutil, subprocess, time, urllib.request


def sh(cmd, timeout=20):
    try: r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout); return r.stdout.strip() or r.stderr.strip()
    except Exception as ex: return f'unreadable ({type(ex).__name__})'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--deliverable'); ap.add_argument('--drive', default='.'); ap.add_argument('--min-free-gb', type=float, default=40, help='the render floor: under it no finish starts (finish_spot.py --min-free-gb)')
    ap.add_argument('--keep-tags', default='', help='spot=tag,… the current versions; everything else derived is SUPERSEDED (project_size.py)')
    ap.add_argument('--higgsfield', action='store_true', help='the SUBSCRIPTION wallet (higgsfield account status)'); ap.add_argument('--higgsfield-api', action='store_true', help="the API wallet, from hf_api.py's local ledger — an ESTIMATE")
    ap.add_argument('--monid', action='store_true'); ap.add_argument('--treg', action='store_true'); ap.add_argument('--elevenlabs', action='store_true'); ap.add_argument('--open', action='append', default=[]); ap.add_argument('--job', action='append', default=[])
    a = ap.parse_args(); os.chdir(a.root); now = time.strftime('%Y-%m-%d %H:%M'); lines = [f'STATUS {now}']
    if a.deliverable:
        ok = os.path.exists(a.deliverable); lines.append(f"deliverable: {a.deliverable}" + (f" ({os.path.getsize(a.deliverable) / 2 ** 20:.1f} MiB)" if ok else ' — MISSING'))
    du = shutil.disk_usage(a.drive); free = du.free / 1e9; lines.append(f"drive {a.drive}: {free:.0f} GB free" + (f' — ⚠ under the render floor ({a.min_free_gb:g} GB): no finish starts; free space or name superseded files' if free < a.min_free_gb else '') + ' (the HOST drive; a VM image never shrinks)')
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location('project_size', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'project_size.py')); ps = importlib.util.module_from_spec(spec); spec.loader.exec_module(ps)
        keep = {kv.split('=')[0]: kv.split('=')[1] for kv in a.keep_tags.split(',') if '=' in kv}
        rows = ps.classify('.', keep, ps.SUBSTRATE, ps.DERIVED); tot = {k: sum(sz for _, sz in v) / 1e9 for k, v in rows.items()}
        lines.append(f"project: {sum(tot.values()):.1f} GB — substrate {tot['substrate']:.1f} · derived current {tot['derived-current']:.1f} · SUPERSEDED {tot['derived-superseded']:.1f} GB ({len(rows['derived-superseded'])} files; list them with project_size.py --plan and name what goes)")
    except Exception as ex: lines.append(f'project: size unreadable ({type(ex).__name__})')
    bal = []
    if a.higgsfield: bal.append('Higgsfield subscription: ' + (sh(['higgsfield', 'account', 'status']).splitlines()[0] if shutil.which('higgsfield') else 'unreadable (CLI not on PATH)'))
    if a.higgsfield_api:
        # No balance endpoint exists: the only copy of this wallet is the ledger hf_api_submit.py and hf_api_poll.py write.
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location('hf_api', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'video-gen-cost-gate', 'scripts', 'hf_api.py')); hf = importlib.util.module_from_spec(spec); spec.loader.exec_module(hf)
            b = hf.balance()
            bal.append(f"Higgsfield API: ${b['usd']:.2f} / {b['credits']:.1f} cr — ESTIMATE from the local ledger (no balance endpoint)" if b['entries'] else f'Higgsfield API: unreadable (no ledger at {hf.LEDGER}; record the purchase with hf_api.py load)')
        except Exception as ex: bal.append(f'Higgsfield API: unreadable ({type(ex).__name__})')
    if a.monid:
        if not shutil.which('monid'): bal.append('monid: unreadable (CLI not on PATH)')
        else:
            # `monid balance` prints a decorated banner; the wallet is the line carrying a figure.
            raw = re.sub(r'\x1b\[[0-9;]*m', '', sh(['monid', 'balance']))
            hit = [ln.strip() for ln in raw.splitlines() if '$' in ln]
            bal.append('monid: ' + (hit[0] if hit else f'unreadable ({raw.splitlines()[-1][:40] if raw else "no output"})'))
    if a.treg:
        if not shutil.which('treg'): bal.append('treg: unreadable (CLI not on PATH)')
        else:
            raw = sh(['treg', 'balance', '--json'], timeout=30)
            try: o = json.loads(raw); held = len(o.get('holds') or []); bal.append(f"treg: ${o['balance_usd']:.2f}" + (f' ({held} call(s) in flight, held)' if held else ''))
            except Exception: bal.append(f'treg: unreadable ({raw.splitlines()[-1][:40] if raw else "no output"})')
    if a.elevenlabs:
        key = os.environ.get('ELEVENLABS_API_KEY')
        if not key: bal.append('ElevenLabs: unreadable (no ELEVENLABS_API_KEY in the environment)')
        else:
            try: o = json.load(urllib.request.urlopen(urllib.request.Request('https://api.elevenlabs.io/v1/user/subscription', headers={'xi-api-key': key}), timeout=20)); bal.append(f"ElevenLabs: {o['character_count']}/{o['character_limit']} chars ({o.get('tier', '?')})")
            except Exception as ex: bal.append(f'ElevenLabs: unreadable ({type(ex).__name__})')
    bal.append('other vendors: no balance endpoint (track spend from the receipts)')
    lines.append('balances: ' + ' · '.join(bal))
    lines.append('background jobs: ' + ('; '.join(a.job) if a.job else 'none'))
    lines.append('open: ' + ('; '.join(a.open) if a.open else '—'))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
