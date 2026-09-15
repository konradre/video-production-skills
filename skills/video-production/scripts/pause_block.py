#!/usr/bin/env python3
"""pause_block.py — the "STATE AT PAUSE — READ THIS FIRST ON RESUME" block appended to the project's RESUME document
before a compaction or a pause: the deliverable, the exact builder line (the slot SSOT — re-run it to regenerate the
EDL), the keepers and voids, the reference ledger state, the balances, the open items, the background jobs, and the exact
resume commands. The timestamp comes from the clock (`date`), never from memory. A .bak of the RESUME lands first.

  pause_block.py --resume RESUME.md --deliverable deliver/<file>.mp4 --next "the client's verdict on S02" [--builder "python3 scripts/…"]
                 [--keepers "S02-AB3-s1 0–11.79 · S02-G3-s1 …"] [--refs "gate-accepted: …"] [--balances "$(status_line.py …)"]
                 [--open "…"] [--job "…"] [--resume-cmd "python3 …"] [--sent "to the client 04:3x by the operator"]
                 [--substrate "assets/ · gen/aerial/ · audio/music/ · prompts/ · tools/"] [--skills "video-finish § 5b applies; § 1–4 n/a (1080p source)"]
"""
import argparse, os, shutil, time


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--resume', required=True); ap.add_argument('--deliverable', required=True); ap.add_argument('--next', required=True)
    for k in ('builder', 'keepers', 'refs', 'balances', 'sent', 'substrate', 'skills'): ap.add_argument(f'--{k}')
    for k in ('open', 'job', 'resume-cmd'): ap.add_argument(f'--{k}', action='append', default=[])
    a = ap.parse_args(); ts = time.strftime('%Y-%m-%d %H:%M')
    b = [f'\n## 🔴 STATE AT PAUSE {ts} — READ THIS FIRST ON RESUME', '',
         f"**Delivered:** `{a.deliverable}`" + (f" — {a.sent}" if a.sent else '') + f". **NEXT = {a.next}.**"]
    if a.builder: b += ['', f"**The exact build (re-run this to regenerate the EDL):** `{a.builder}`"]
    if a.keepers: b += ['', f"**Keepers / VOID:** {a.keepers}"]
    if a.refs: b += ['', f"**Reference set:** {a.refs}"]
    if a.substrate: b += ['', f"**Substrate (what the spots are made from — never a derived file):** {a.substrate}"]
    if a.skills: b += ['', f"**Skills consulted / declared not applicable:** {a.skills}"]
    if a.balances: b += ['', f"**Balances / disk:** {a.balances}"]
    b += ['', '**Background jobs at pause:** ' + ('; '.join(a.job) if a.job else 'none — every monitor stopped, every chain complete')]
    b += ['', '**Open:** ' + (' · '.join(a.open) if a.open else '—')]
    if a.resume_cmd: b += ['', '**Resume commands (in order):**'] + [f'{i}. `{c}`' for i, c in enumerate(a.resume_cmd, 1)]
    b += ['', 'Rehydrate first: read the full files this block names before acting on any refinement; resume from the LATEST deliverable; re-check any background job by its output file, not by memory.', '']
    if os.path.exists(a.resume): shutil.copy(a.resume, f"{a.resume}.bak-{time.strftime('%Y%m%d-%H%M%S')}-pre-pause")
    open(a.resume, 'a', encoding='utf-8').write('\n'.join(b)); print(f'appended the pause block ({ts}) to {a.resume}')


if __name__ == '__main__':
    main()
