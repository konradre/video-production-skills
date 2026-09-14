#!/usr/bin/env python3
"""shotlist_scaffold.py — the per-spot SHOTLIST.md skeleton from the beat list, in the fixed section order, so nothing that
must be decided before the first prompt is left to memory: the method line (refs gate, cost gate, partition-first), the script
pointer and the generator's maximum duration, the kit table (reused vs to build, by spot type), the room geometry pin, the
characters, the PARTITIONS table, the rounds and cost, the audio plan, the acceptance rows (row 0 = geometry), the submission
commands. Every row quotes the script lines it serves IN FULL — never truncated.
A continuity PARTITION is a maximal run of beats that must hold the same people, objects, setting and look; it is ONE
generation when it fits the generator's cap. Beats that carry "partition" in the beat list are grouped into one row; beats
without one get a row each, to be merged.

  shotlist_scaffold.py --beats prompts/<SPOT>-beats.json --out prompts/r2v/<SPOT>-SHOTLIST.md [--spot-type product|ugc]
                       [--max-duration 30 --duration-source "<where it was read>"] [--sku "<SKU name>"] [--elements ELEM-FILL-<colour>]
--spot-type product (default): the product kit — sheets, size crop, turntable, drift, the signature wall, end card + signature.
--spot-type ugc: no product on screen, no designed card, no wipe — people, setting and look references; characters come from
  the client's approved photos (imported with provenance) or the first keeper.
--max-duration: the generator's maximum single-generation duration, READ from the vendor (its schema, estimator or error) and
  written in the header; absent, the header says UNKNOWN and no action may be split until it is read.
"""
import argparse, json, os, time


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--beats', required=True); ap.add_argument('--out', required=True); ap.add_argument('--sku', default='<SKU>'); ap.add_argument('--elements', default='ELEM-FILL-<colour>')
    ap.add_argument('--spot-type', choices=['product', 'ugc'], default='product')
    ap.add_argument('--max-duration', type=float); ap.add_argument('--duration-source', default='<the vendor schema / estimator / error, and the date>')
    a = ap.parse_args(); B = json.load(open(a.beats, encoding='utf-8')); spot = B.get('spot', 'SPOT'); assert not os.path.exists(a.out), f'{a.out} exists — a new version is a new file'
    parts = []
    for b in B['beats']:
        pid = b.get('partition')
        if pid and parts and parts[-1][0] == pid: parts[-1][1].append(b)
        else: parts.append((pid or b['beat'], [b]))
    quoted = lambda s: s if ('“' in s or '"' in s) else f'“{s}”'   # a beat's script usually carries its own quotes already
    rows = '\n'.join(f"| **{pid}** | {', '.join(x['beat'] for x in bs)} | {', '.join(e for x in bs for e in x.get('events', []))} | <s> | "
                     f"{' '.join(quoted(x.get('script', '')) for x in bs)} | omni_reference (refs only) / t2v / designed | @1 … | takes/{pid}-s1.mp4 | <cr> | |" for pid, bs in parts)
    cap = (f"{a.max_duration:g} s — read from {a.duration_source}" if a.max_duration
           else 'UNKNOWN — read it from the vendor (schema, estimator or error) before any action is split; never infer it from the longest take you ran')
    product = a.spot_type == 'product'
    kit_product = f"""| product sheet (front + ¾ on grey) | references/sheets/PRODUCT-sheet-<sku>.png — venue upload id | ☐ |
| exact-silhouette sheet of the pieces | references/sheets/PIECES-sheet-exact-<fill>.png | ☐ |
| in-world SIZE crop (size relative to a body part) | references/single/<SPOT>-PIECES-scale-ref.png | ☐ |
| turntable, {a.sku} label, <len> | hyper/<name>-<len>/renders/… | ☐ |
| drift rain, <len> | hyper/drift-<fill>-<len>/frames/frame_%06d.png | ☐ |
| the signature wall (the wipe over the match cut) | hyper/wall-<fill>/frames/ (1.0 s, opaque from +0.29 s) | ☐ |
| end card + audio signature | hyper/<card>/renders/<card>.mp4 (FULL length) · audio/sfx/<signature>.wav | ☐ |
| before cue → wipe · after cue · closing bed | audio/music/… (each cue ≥ its span) | ☐ |
| B plate (the transformed room, SAME camera as A) | image-to-image FROM the A keeper's frame 0 → the START IMAGE of the transformation scene | ☐ |
"""
    kit_ugc = """| character refs — one per recurring person | the client's approved photos IMPORTED with provenance (refs_gate.py --import), or crops of the first keeper | ☐ |
| setting ref — the establishing frame with its cast | the first accepted keeper, or an accepted still | ☐ |
| music bed | audio/music/… (≥ its span); its level and duck MEASURED off the client's reference when it exists | ☐ |
"""
    kit_common = """| look plate — one per light context, look-only role | a template-free still per light context, enumerated against the partitions | ☐ |
| the reference dress rehearsal — one still per partition from the SAME reference set | gen_stills.py (cents), read before the video call (video-gen-cost-gate) | ☐ |
| narrator VO — timed before partition durations are fixed · O.S. voice · dubs | spot-audio-assembly (one voice + one model per role; vo_word_times.py) | ☐ |
"""
    doc = f"""# {spot} — r2v shot list (connected document) · {time.strftime('%Y-%m-%d %H:%M')}

**Method:** 🔴 REFS GATE — every generation call runs the refs gate (video-refs-continuity) and every billed call carries a cost line and the operator's GO (video-gen-cost-gate); the shot list is built from CONTINUITY PARTITIONS of the script, never from shots — everything that must hold the same people, objects, setting and look is ONE generation when it fits the cap; short generations come after, for gaps and fixes, or where consistency across shots is not required; a rejected cut is evidence about defects, never a source of structure; the venue's dialect decides the prompt (video-prompt-dialects).
**Script:** {B.get('source', '<the client text, verbatim, saved beside this file>')} — the SSOT. This list is its derivation: framing, coverage and timing may be added; a character, a beat or a line may not (client-literal is the default).
**Generator maximum duration:** {cap}
""" + (f"**Fill:** {a.sku} → {a.elements} — every partition that shows the product's pieces names it.\n" if product else '') + f"""
## Kit — reused vs to build ({a.spot_type})
| asset | source | status |
|---|---|---|
{kit_product if product else kit_ugc}{kit_common}
## Room geometry (pinned for every partition — the first keeper's frame re-pins it after the pick)
<the room from its camera end: walls, furniture, who sits where, the door's wall, the light>

## Characters ({'prose-born in the first scene; refs cut from keepers' if product else "from the client's approved photos, imported with provenance, or the first keeper"}; cast CLOSED after the first keeper)
<name age hair wardrobe, one line each; a cast ref that resembles a public figure is re-rolled>

## Partitions (one row = ONE generation within the cap; a row that splits one action records `split: <why>` in its last cell)
| partition | beats | events | duration | the script lines it serves | mode | refs (@Image order) | file | credits/seed | split |
|---|---|---|---|---|---|---|---|---|---|
{rows}

## Rounds and cost (`cost_plan.py`; the venue's rate; balance at the time of writing)
1. Round 1 = <partitions with no dependency> × 3 seeds … = <cr> — GO?
2. Round 2 = <partitions that need round 1's keeper frames> … — GO?

## Audio plan against the gens
<the VO lines timed (word times) BEFORE the partition durations are fixed — a sum that hits the runtime is not a timing; which line rides where; the O.S. line in post audio, never in a video prompt{'; the wipe marker; the audio signature on the card' if product else ''}>

## Acceptance (per take, before any keeper is cut — video-take-review)
0. geometry/continuity: the room, the door's wall, who sits where — first and hard-fail
1. consistency across every composed cut: face, wardrobe, room, light, performance register — a cut inside one generation is descriptive, never a fail
2. the script beat (cause before reaction; nothing invented) · 3. anatomy per person at 3× · 4. faces well above the ~60 px floor (face height in the take's native pixels, measured at 480p) for any beat a face carries{' · 5. product shape and size' if product else ''} · eyelines · audio · named state · dignity · realism

## Submission (after the GO — never resubmit a billed job; list the venue's jobs first)
<the exact commands per partition, with the ledger record before polling>
"""
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True); open(a.out, 'w', encoding='utf-8').write(doc)
    print(f'wrote {a.out}: {len(parts)} partition row(s) from {len(B["beats"])} beats ({a.spot_type}); generator cap {a.max_duration if a.max_duration else "UNKNOWN"}')


if __name__ == '__main__':
    main()
