#!/usr/bin/env python3
"""pause_block.py — the "STATE AT PAUSE — READ THIS FIRST ON RESUME" block appended to the project's RESUME document
before a compaction or a pause: the deliverable, the exact builder line (the slot SSOT — re-run it to regenerate the
EDL), the keepers and voids, the reference ledger state, the balances, the open items, the background jobs, and the exact
resume commands. The timestamp comes from the clock (`date`), never from memory. A .bak of the RESUME lands first.

The "skills consulted" line is MEASURED from the session transcript (skills_invoked.py: the Skill tool_use blocks, the
compactions, and — with the project's rules file — the phases whose actions ran without their skill). It is never typed
from memory: `--skills` (the declared-not-applicable text) rides only next to `--transcript`; `--skills-unmeasured`
writes a typed line and labels it so.

  pause_block.py --resume RESUME.md --deliverable deliver/<file>.mp4 --next "the client's verdict on S02" [--builder "python3 scripts/…"]
                 [--keepers "S02-AB3-s1 0–11.79 · S02-G3-s1 …"] [--refs "gate-accepted: …"] [--balances "$(status_line.py …)"]
                 [--open "…"] [--job "…"] [--resume-cmd "python3 …"] [--sent "to the client 04:3x by the operator"]
                 [--substrate "assets/ · gen/aerial/ · audio/music/ · prompts/ · tools/"]
                 --transcript latest --phases .claude/skill-gate.json --root <project> [--skills "video-finish § 1–4 n/a (1080p source)"]
"""
import argparse, os, shutil, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def measured_skills_line(transcript, phases, root):
    import skills_invoked as si
    t = si.latest_transcript() if transcript == "latest" else os.path.expanduser(transcript)
    if not t or not os.path.isfile(t):
        sys.exit(f"pause_block: no transcript at {transcript!r} — pass the session's .jsonl path")
    if phases and not root:
        sys.exit("pause_block: --phases needs --root")
    return si.one_line(si.scan(t, rules=phases, root=root))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--resume', required=True); ap.add_argument('--deliverable', required=True); ap.add_argument('--next', required=True)
    for k in ('builder', 'keepers', 'refs', 'balances', 'sent', 'substrate', 'skills'): ap.add_argument(f'--{k}')
    for k in ('open', 'job', 'resume-cmd'): ap.add_argument(f'--{k}', action='append', default=[])
    ap.add_argument('--transcript', help="the session transcript (.jsonl) or 'latest' — the source of the skills line")
    ap.add_argument('--phases', help="the project's rules file (.claude/skill-gate.json) — adds the phase gaps to the line")
    ap.add_argument('--root', help="the project root the rules apply to")
    ap.add_argument('--skills-unmeasured', action='store_true', help="write --skills as a typed line, labelled as unmeasured")
    a = ap.parse_args(); ts = time.strftime('%Y-%m-%d %H:%M')
    if a.skills and not a.transcript and not a.skills_unmeasured:
        sys.exit("pause_block: the skills-consulted line is measured from the transcript — pass --transcript <path|latest> "
                 "(and --phases <rules> --root <project> for the gaps), or --skills-unmeasured to write a typed line as such")
    b = [f'\n## 🔴 STATE AT PAUSE {ts} — READ THIS FIRST ON RESUME', '',
         f"**Delivered:** `{a.deliverable}`" + (f" — {a.sent}" if a.sent else '') + f". **NEXT = {a.next}.**"]
    if a.builder: b += ['', f"**The exact build (re-run this to regenerate the EDL):** `{a.builder}`"]
    if a.keepers: b += ['', f"**Keepers / VOID:** {a.keepers}"]
    if a.refs: b += ['', f"**Reference set:** {a.refs}"]
    if a.substrate: b += ['', f"**Substrate (what the spots are made from — never a derived file):** {a.substrate}"]
    if a.transcript:
        line = measured_skills_line(a.transcript, a.phases, a.root)
        if a.skills: line += f" · declared not applicable: {a.skills}"
        b += ['', f"**Skills consulted (measured from the transcript) / declared not applicable:** {line}"]
    elif a.skills:
        b += ['', f"**Skills consulted / declared not applicable (typed, NOT measured):** {a.skills}"]
    if a.balances: b += ['', f"**Balances / disk:** {a.balances}"]
    b += ['', '**Background jobs at pause:** ' + ('; '.join(a.job) if a.job else 'none — every monitor stopped, every chain complete')]
    b += ['', '**Open:** ' + (' · '.join(a.open) if a.open else '—')]
    if a.resume_cmd: b += ['', '**Resume commands (in order):**'] + [f'{i}. `{c}`' for i, c in enumerate(a.resume_cmd, 1)]
    b += ['', 'Rehydrate first: read the full files this block names before acting on any refinement; resume from the LATEST deliverable; re-check any background job by its output file, not by memory; invoke the phase skill through the Skill tool before the next phase action — a compaction dropped the skill bodies.', '']
    if os.path.exists(a.resume): shutil.copy(a.resume, f"{a.resume}.bak-{time.strftime('%Y%m%d-%H%M%S')}-pre-pause")
    open(a.resume, 'a', encoding='utf-8').write('\n'.join(b)); print(f'appended the pause block ({ts}) to {a.resume}')


if __name__ == '__main__':
    main()
