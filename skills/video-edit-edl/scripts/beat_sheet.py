#!/usr/bin/env python3
"""beat_sheet.py — the SCRIPT-FIDELITY GATE. Prints the EDL as a beat sheet against the spot's beat list and checks
it BY CODE: every non-optional beat's events present IN ORDER; each beat's VO/SFX inside the beat's span; audio order
rules (sfx:knock -> vo:OS -> marker:ME); a VO ending before a marker; music cue edges on a marker or on the beat's
first event; a post layer placed N s before the next beat; minimum durations; every placed VO line claimed by a beat;
every EDL event claimed by a beat (an unclaimed event = an INVENTED beat); forbidden EVENT and LAYER ids absent.
Exit 1 on any FAIL — no finish runs on a FAIL, and the printed sheet rides in the deliverable ask.

  beat_sheet.py --root <project> --edl edit/<SPOT>-EDL.json [--beats prompts/<SPOT>-beats.json]

Paths inside the EDL and the beats file are relative to --root (default: the current directory).
Schema of the beats file: references/BEATS-CONTRACT.md.
"""
import argparse, json, os, subprocess, sys


def vdur(v):
    if v.get('dur') is None:
        v['dur'] = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', v['file']], capture_output=True, text=True).stdout or 0)
    return v['dur']


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.', help='project root; EDL/beats paths are relative to it')
    ap.add_argument('--edl', required=True); ap.add_argument('--beats', help='default prompts/<spot>-beats.json')
    a = ap.parse_args(); os.chdir(a.root)
    e = json.load(open(a.edl, encoding='utf-8')); bp = a.beats or f"prompts/{e.get('spot', 'SPOT')}-beats.json"
    B = json.load(open(bp, encoding='utf-8'))
    ev = {x['id']: x for x in e['events']}; order = [x['id'] for x in e['events']]; au = e['audio']; vo = au['vo']
    sfx = au.get('sfx', {}); mus = au.get('music', {}); lay = {l['id'].split()[0]: l for l in e.get('post_layers', [])}

    def mark(name):
        m = B['markers'][name]; x = ev[m['event']]; return round(x['tl'][0] + m['take'] - x['in'], 6)

    rows, fails, seen = [], [], set()

    def chk(cond, msg): (rows if cond else fails).append(('PASS ' if cond else 'FAIL ') + msg)

    prev = -1
    for b in B['beats']:
        ids = [i for i in b['events'] if i in ev]; missing = [i for i in b['events'] if i not in ev]
        if not ids and b.get('optional'): rows.append(f"skip {b['beat']} (optional, not in this cut)"); continue
        chk(not missing, f"{b['beat']} events {b['events']} present" + (f" — MISSING {missing}" if missing else ''))
        if not ids: continue
        pos = [order.index(i) for i in ids]; chk(min(pos) >= prev and pos == sorted(pos), f"{b['beat']} in script order"); prev = max(pos)
        t0 = min(ev[i]['tl'][0] for i in ids); t1 = max(ev[i]['tl'][1] for i in ids)
        for L in b.get('vo', []):
            v = vo.get(L); chk(v is not None and t0 - 0.05 <= v['at'] < t1, f"{b['beat']} VO {L} at {v['at'] if v else None} inside [{t0},{t1}]"); seen.add(L)
        for S in b.get('sfx', []):
            s = sfx.get(S); chk(s is not None and t0 - 0.05 <= s['at'] < t1, f"{b['beat']} SFX {S} at {s['at'] if s else None} inside [{t0},{t1}]")
        if 'order' in b:
            ts = []
            for o in b['order']:
                k, n = o.split(':'); ts.append(sfx[n]['at'] if k == 'sfx' else vo[n]['at'] if k == 'vo' else mark(n))
            chk(ts == sorted(ts), f"{b['beat']} audio order {b['order']} = {ts}")
        if 'vo_ends_before' in b:
            for L in b.get('vo', []):
                end = round(vo[L]['at'] + vdur(vo[L]), 3); chk(end <= mark(b['vo_ends_before']), f"{b['beat']} VO {L} ends {end} before {b['vo_ends_before']} {mark(b['vo_ends_before'])}")
        if 'music_end_at' in b:
            c, m = b['music_end_at']; chk(abs(mus[c]['tl'][1] - mark(m)) < 0.002, f"{b['beat']} {c} ends at {m} {mus[c]['tl'][1]} vs {mark(m)}")
        if 'music_start_at' in b:
            c, m = b['music_start_at']; tgt = t0 if m == 'event' else mark(m); chk(abs(mus[c]['tl'][0] - tgt) < 0.002, f"{b['beat']} {c} starts at {m} {mus[c]['tl'][0]} vs {tgt}")
        if 'layer_before_next' in b:
            lid, lead = b['layer_before_next']; nxt = order[prev + 1]; want = round(ev[nxt]['tl'][0] - lead, 6); L = lay.get(lid)
            chk(L is not None and abs(L['at'] - want) < 0.002, f"{b['beat']} layer {lid} at {L['at'] if L else None} = next beat {nxt} {ev[nxt]['tl'][0]} − {lead}")
        if 'min_dur' in b: chk(t1 - t0 >= b['min_dur'] - 1e-6, f"{b['beat']} duration {round(t1 - t0, 3)} ≥ {b['min_dur']}")
    for L, where in B.get('extra_vo', {}).items():
        where = [where] if isinstance(where, str) else where; host = next((w for w in where if w in ev), None); v = vo.get(L)
        chk(v is not None and host is not None and ev[host]['tl'][0] - 0.05 <= v['at'] < ev[host]['tl'][1] + 0.5, f"extra VO {L} at {v['at'] if v else None} over {host}"); seen.add(L)
    placed = sorted(k for k in vo if isinstance(vo[k], dict) and 'file' in vo[k])
    chk(all(k in seen for k in placed), f"every placed VO line is accounted for by a beat: {placed}")
    claimed = set(i for b in B['beats'] for i in b['events']); unclaimed = [x['id'] for x in e['events'] if x['id'] not in claimed]
    chk(not unclaimed, f"every EDL event is claimed by a beat (an unclaimed event = an INVENTED beat): unclaimed {unclaimed}")
    for fid, why in B.get('forbidden_events', {}).items():   # a forbidden LAYER once passed vacuously because only events were tested
        chk(fid not in ev and fid not in lay, f"forbidden event/layer {fid} absent — {why}")
    # the sheet
    print(f"BEAT SHEET {a.edl} v{e.get('version')} runtime {e['runtime_s']} s — {B.get('source', '')}")
    for x in e['events']:
        beat = next((b['beat'] for b in B['beats'] if x['id'] in b['events']), '—')
        print(f" {x['tl'][0]:7.3f}–{x['tl'][1]:7.3f} {x['id']:9} {beat:9} {os.path.basename(x['take']):28} take {x['in']:.3f}–{x['out']:.3f}  {x.get('note', '')[:70]}")
    lines = [(v['at'], f"VO {k} «{v.get('text', '')}» {v['at']:.2f}–{v['at'] + vdur(v):.2f}") for k, v in vo.items() if isinstance(v, dict) and 'file' in v]
    lines += [(s['at'], f"SFX {k} {s['at']:.2f}–{s['at'] + s.get('dur', 0):.2f}") for k, s in sfx.items()]
    lines += [(m['tl'][0], f"MUSIC {k} {m['tl'][0]:.2f}–{m['tl'][1]:.2f}") for k, m in mus.items()]
    lines += [(l['at'], f"LAYER {l['id']} {l['at']:.2f}–{l['at'] + l['dur']:.2f}") for l in e.get('post_layers', [])]
    lines += [(mark(m), f"MARKER {m} {mark(m):.3f}") for m in B.get('markers', {})]
    for t, s in sorted(lines): print(f"   {t:7.3f} {s}")
    for r in rows + fails: print(' ', r)
    print('BEAT-SHEET PASS' if not fails else f'BEAT-SHEET FAIL ({len(fails)})'); sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
