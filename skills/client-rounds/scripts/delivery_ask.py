#!/usr/bin/env python3
"""delivery_ask.py — the message that goes with a deliverable, in the form the operator reads on a phone between clips:
the file by its full path (a chat attachment only when ≤ 30 MiB — otherwise the path IS the delivery), its runtime and
size, the VO script table from the EDL (every placed line, verbatim), the QC
line, what changed since the previous version, the residual doubts WITH frame times (never a re-roll question), what is
frozen, and the decisions as NUMBERED plain questions with the cost inline. Rationale goes in the notes beside the clips,
never inside the questions.

  delivery_ask.py --root <project> --edl edit/<SPOT>-EDL-v9.json --deliv deliver/<file>.mp4 --winroot 'C:\\path\\to\\project'
                  [--qc logs/qc.txt] [--changed "..."] [--doubt "0:41 a stray fleck on the lamp"] [--frozen "S02 v4 (client: looks solid)"]
                  [--q "Redo scene C by extending B (3 seeds, 37.5 cr) — yes or no?"] [--default "say defaults"]
"""
import argparse, json, os, re, subprocess


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl', required=True); ap.add_argument('--deliv', required=True); ap.add_argument('--winroot', required=True)
    ap.add_argument('--qc'); ap.add_argument('--changed', action='append', default=[]); ap.add_argument('--doubt', action='append', default=[]); ap.add_argument('--frozen', action='append', default=[])
    ap.add_argument('--q', action='append', default=[]); ap.add_argument('--default'); ap.add_argument('--chat-limit-mib', type=float, default=30)
    a = ap.parse_args(); os.chdir(a.root); e = json.load(open(a.edl, encoding='utf-8'))
    size = os.path.getsize(a.deliv); mib = size / 2 ** 20; win = a.winroot.rstrip('\\') + '\\' + a.deliv.replace('/', '\\')
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a.deliv], capture_output=True, text=True).stdout or 0)
    lines = [f"**{e.get('spot', '?')} v{e.get('version', '?')}** — `{win}`", f"{dur:.1f} s · {mib:.1f} MiB ({size / 1e6:.1f} MB) · " + ('attached below' if mib <= a.chat_limit_mib else f'over {a.chat_limit_mib:.0f} MiB — open it at the path'), '']
    if a.changed: lines += ['**Changed since the previous version**'] + [f'- {c}' for c in a.changed] + ['']
    vo = e.get('audio', {}).get('vo', {}); placed = [(k, v) for k, v in vo.items() if isinstance(v, dict) and 'file' in v]
    if placed:
        lines += ['**VO script (as placed)**', '', '| line | at | text |', '|---|---|---|'] + [f"| {k} | {v['at']:.2f} | {v.get('text', '')} |" for k, v in sorted(placed, key=lambda kv: kv[1]['at'])] + ['']
    if a.qc and os.path.exists(a.qc):
        q = open(a.qc, encoding='utf-8').read(); verdict = re.findall(r'(QC-DELIVERABLE (?:PASS|FAIL[^\n]*))', q); lines += [f"**QC** {verdict[-1] if verdict else 'see the log'}" + (f" — `{a.qc}`" if verdict else ''), '']
    if a.doubt: lines += ['**Residual doubts (in the note, not a re-roll ask)**'] + [f'- {d}' for d in a.doubt] + ['']
    if a.frozen: lines += ['**Frozen (approved, untouched)**'] + [f'- {f}' for f in a.frozen] + ['']
    if a.q: lines += ['**Decisions**'] + [f'{i}. {q}' for i, q in enumerate(a.q, 1)] + ([f'({a.default})'] if a.default else []) + ['']
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
