#!/usr/bin/env python3
"""prompt_lint.py — the mechanical prompt checks that precede the refs gate. Each row is an incident (see
references/LINT.md). FAIL rows (slots, char cap) exit 1; WARN rows are printed and must be answered in the
prompt or in the GO ask.

  prompt_lint.py [--dialect seedance-2.5|seedance-2.0|minimax-h3|create-a-meme|kie] [--refs A,B,C]
                 [--cap N] [--caps-stoplist WORD,WORD] [--locked <first-line prompt>] [--strict] <prompt.txt>
  prompt_lint.py --selftest     the photoreal rows L38-L41 against known-good and known-bad prompts

--refs   the reference NAMES in slot order (their count is the slot maximum the prompt may cite)
--locked the prompt a model-voiced series was calibrated on (its first line): any sentence that differs outside the
         quoted line WARNs (L36) — only the words change between lines
--strict promote every WARN to FAIL

A quoted or braced line is DIALOGUE: its words are spoken, never subjects and never prohibitions. The negation scan (L3)
and the caps scan (L4) skip it; a capitalised word inside it is the stress mark (house rule, 2026-09-25), and only a
shouted line — more than two capitalised words — warns.
"""
import argparse, re, sys

CAPS = {'seedance-2.5': 8000, 'seedance-2.0': 6000, 'minimax-h3': 7000, 'create-a-meme': 2000, 'kie': 32000}
WARN_AT = {'seedance-2.5': 5000, 'seedance-2.0': 5000, 'minimax-h3': 6000, 'create-a-meme': 1800, 'kie': 6000}
SLOT_MAX = {'seedance-2.5': 30, 'seedance-2.0': 9, 'minimax-h3': 9, 'create-a-meme': 9, 'kie': 4}
SLOT_RE = {'create-a-meme': r'@ref\s?(\d+)', 'minimax-h3': r'<(?:Subject|Picture|Video|Audio)\s?(\d+)>', 'kie': r'@ref\s?(\d+)'}
DEFAULT_STOP = {'BOOM', 'CLANG', 'WHACK', 'KNOCK', 'KNOCKS', 'SILENCE', 'POV', 'OTS', 'MCU', 'VO', 'SFX', 'CTA', 'SKU', 'LEFT', 'RIGHT', 'FAR', 'NEAR',
                'FRONT', 'DOOR', 'ONE', 'ONLY', 'NO', 'NOT', 'AND', 'THE', 'START', 'FRAME', 'SHAPE', 'SIZE', 'VOICE', 'LED', 'TV', 'OK', 'AM', 'PM', 'A', 'I'}
MODERATION = {
    'seedance-2.5': ['penis', 'penises', 'dick', 'dicks', 'cock', 'thrusting', 'thrusts', 'genitals', 'nude', 'naked', 'topless',
                     ' hit ', 'hits ', 'strike', 'crush', 'knocked out', 'knocks out', 'bleeding', 'blood'],
}
MODERATION['seedance-2.0'] = MODERATION['seedance-2.5']; MODERATION['create-a-meme'] = MODERATION['seedance-2.5']
GAIT = ['heel strike', 'toe-off', 'toe off', 'hip extension', 'knee lock', 'knees lock', 'knees never lock', 'stride length', 'cadence', 'gait',
        'lumber', 'gallop', 'trot', 'bound', 'lope', 'sprint', 'jog', 'run ', 'runs ', 'running']
CATEGORY = [r'like (?:big|large|wild|small) (?:wild )?animals', r'like (?:a |an )?(?:large|big) (?:predator|animal|beast)']
OFF_FRAME = re.compile(r'([A-Za-z\']+ [a-z]+ ?[a-z]*)\s*\((?:below|out of|outside|off)[^)]*frame[^)]*\)|\b(?:his|her|their|the) ([a-z]+)\b[^.;]{0,40}\b(?:below the frame|out of frame|out of the frame|off-screen|offscreen)', re.I)
SHOT_SIZE = re.compile(r'\b(wide|medium|close-up|close up|macro|insert|two-shot|over-the-shoulder|OTS|point of view|POV|full[- ]body|chest-up|knees-down|waist-up|low angle|high angle|profile|three-quarter|from the (?:front|side|left|right|doorway|behind))\b', re.I)
PARAMS = re.compile(r'\b(480p|720p|1080p|2160p|4k|2k|\d+\s?fps|seedance|minimax|veo|kling|\d{1,2}\s?seconds? long|\d{1,2}-second video|aspect ratio)\b', re.I)
NEG = re.compile(r'\b(no|never|not|nothing|nobody|without|nor|cannot|can\'t|doesn\'t|does not|don\'t)\b', re.I)
ACTION_VERB = re.compile(r'\b(\w+?(?:s|es))\b', re.I)  # crude: third-person verbs; used only for density
QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”|\{[^{}\n]*\}|<d>.*?</d>', re.S)   # dialogue spans: straight/curly quotes, {braces}, H3 <d>
CAPWORD = re.compile(r"\b[A-Z][A-Z']{1,}\b")
CUT = re.compile(r'(?:Cut|Shot|Stage)\s*(\d+)\s*\((\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)\s*s\)\s*:\s*(.*?)(?=(?:Cut|Shot|Stage)\s*\d+\s*\(|【|$)', re.S)


def _selftest():
    """Each photoreal row fires on its incident and stays silent on a known-good prompt (MiniMax's own examples, the
    sanctioned tail, a clean still). Runs this file as a subprocess per case; exit 0 only when every case holds."""
    import os, subprocess, tempfile
    cases = [  # (dialect, prompt, row, fires)
        ('kie', 'A hyperrealistic 8K masterpiece of a desert at night.', 'L38', True),
        ('kie', 'A cinematic photograph of a campfire at night.', 'L38', True),
        ('minimax-h3', '[Shot 1] Live-action, cinematic, a medium-wide shot frames a baker opening the shutters.', 'L38', False),
        ('minimax-h3', 'Live-action night footage. (S1) sings: <d>[English] A stunning masterpiece, no fire, no stars</d>', 'L38', False),
        ('kie', 'A real, unretouched photograph, ISO 3200. A clean, noise-free image. No HDR look, no glow or bloom, '
                'no over-sharpening, no painterly or CGI rendering, no film grain, without chromatic aberration.', 'L39', False),
        ('kie', 'A real photograph with fine sensor noise in the shadows and visible film grain.', 'L39', True),
        ('kie', 'The worn wood grain of the tailgate planks in firelight.', 'L39', False),
        ('minimax-h3', 'Live-action night footage. The flames stay small and low. No subtitles, on-screen text, '
                       'watermarks, animation styling or over-smoothed skin.', 'L40', False),
        ('minimax-h3', 'Live-action night footage of a small campfire, no blaze, no sparks, no drifting embers.', 'L40', True),
        ('minimax-h3', 'Live-action night footage of the desert; the moon itself never in frame.', 'L40', True),
        ('minimax-h3', 'Live-action, low at the foot of a trunk - the tree above it never in frame.', 'L40', True),
        ('minimax-h3', 'Live-action night footage. (S1) sings: <d>[English] No light, no love, no stars</d>', 'L40', False),
        ('minimax-h3', 'A medium close-up frames a man beside a fire. Live-action night footage.', 'L41', True),
        ('minimax-h3', 'Live-action night footage from a full-frame cinema camera. A medium close-up frames a man.', 'L41', False),
        ('minimax-h3', 'integrated_multimodal_description: [Shot 1] Live-action, cinematic, a close shot begins on a glass.', 'L41', False),
        ('minimax-h3', 'The target video is live-action, natural colour. [Shot 1] A wide shot frames a ridge at dusk.', 'L41', False),
        ('minimax-h3', 'For the target video, <Picture 1> (from [Shot 1]) is fully referenced. integrated_multimodal_description: '
                       '[Shot 1] Live-action, cinematic, the woman in <Picture 1> stays by the window.', 'L41', False),
    ]
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        for i, (dialect, prompt, row, fires) in enumerate(cases):
            f = os.path.join(d, f'case{i}.txt')
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write(prompt)
            out = subprocess.run([sys.executable, os.path.abspath(__file__), '--dialect', dialect, f],
                                 capture_output=True, text=True).stdout
            got = f' {row} ' in out
            ok = got == fires
            bad += not ok
            print(f'  {"PASS" if ok else "FAIL"}  {row} {"fires" if fires else "silent"}  [{dialect}] {prompt[:60]}')
    print(f'SELFTEST {"OK" if not bad else "FAIL"}  {len(cases) - bad}/{len(cases)}')
    return 1 if bad else 0


def main():
    if '--selftest' in sys.argv[1:]:
        sys.exit(_selftest())
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('prompt')
    ap.add_argument('--dialect', default='seedance-2.5', choices=list(CAPS))
    ap.add_argument('--refs', default='')
    ap.add_argument('--cap', type=int)
    ap.add_argument('--caps-stoplist', default='')
    ap.add_argument('--rules', help='refs-required.json — its ruled names and caps_stoplist join the ALL-CAPS stoplist')
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--duration', type=float, help='the call duration in seconds (it rides on the call, never in the prose) — scopes L34')
    ap.add_argument('--locked', help='the first-line prompt this series was calibrated on — any sentence that differs outside the quoted line WARNs (L36)')
    a = ap.parse_args()
    text = open(a.prompt, encoding='utf-8').read()
    refs = [r for r in a.refs.split(',') if r]
    rows = []  # (level, id, message)

    # L2 char cap
    cap = a.cap or CAPS[a.dialect]; n = len(text)
    if n > cap: rows.append(('FAIL', 'L2', f'{n} chars > cap {cap}'))
    elif n > WARN_AT[a.dialect]: rows.append(('WARN', 'L2', f'{n} chars (warn above {WARN_AT[a.dialect]}; {cap} hard)'))

    # L1 slots
    slot_re = SLOT_RE.get(a.dialect, r'@Image\s?(\d+)')
    ranges = re.findall(slot_re.replace(r'(\d+)', r'(\d+)\s?[–-]\s?') + r'(?:@ref|@Image|<(?:Subject|Picture|Video|Audio)\s?)?(\d+)', text)
    cited = set()
    for m in re.finditer(slot_re, text): cited.add(int(m.group(1)))
    for lo, hi in ranges:
        lo, hi = int(lo), int(hi)
        if hi < lo: rows.append(('FAIL', 'L1', f'range {lo}–{hi} runs backwards'))
        cited |= set(range(lo, hi + 1))
    if cited:
        mx = max(cited); smax = SLOT_MAX[a.dialect]
        if mx > smax: rows.append(('FAIL', 'L1', f'slot @{mx} cited; the venue takes ≤ {smax}'))
        if refs and mx > len(refs): rows.append(('FAIL', 'L1', f'slot @{mx} cited but only {len(refs)} refs are being passed ({", ".join(refs)})'))
        gaps = sorted(set(range(1, mx + 1)) - cited)
        if gaps: rows.append(('WARN', 'L1', f'slots never cited: {gaps} — an upload with no role; list it as unused or drop it'))
        # two meanings for one slot: a slot cited with two different role nouns in "@ImageN is X" / "@ImageN controls only X"
        roles = {}
        for m in re.finditer(r'@(?:Image|ref)\s?(\d+)\s+(?:is|controls only|is used for|defines|shows)\s+([^.;:,]{3,60})', text):
            roles.setdefault(int(m.group(1)), set()).add(m.group(2).strip().lower())
        for k, v in roles.items():
            if len(v) > 1: rows.append(('WARN', 'L1', f'slot @{k} carries two role statements: {sorted(v)}'))
    pair_roles = {}
    pair_src = text if a.dialect == 'create-a-meme' else ' '.join(v for k, v in re.findall(r'(【[^】]*[Rr]ole[^】]*】)([^【]*)', text))
    for m in re.finditer(r'@(?:ref|Image)\s?(\d+)(?:\s?[–-]\s?@?(?:ref|Image)?\s?(\d+))?\s+([^,;.@]{2,40})', pair_src):
        lo = int(m.group(1)); hi = int(m.group(2)) if m.group(2) else lo
        role = m.group(3).strip().lower()
        if re.match(r'(is|controls|defines|shows|are)\b', role): continue
        for k in range(lo, hi + 1): pair_roles.setdefault(k, set()).add(role)
    for k, v in sorted(pair_roles.items()):
        if len(v) > 1 and not any(v2 in v1 or v1 in v2 for v1 in v for v2 in v if v1 != v2):
            rows.append(('FAIL', 'L1', f'slot {k} carries two meanings: {sorted(v)} — a range closed at the wrong slot?'))
    if refs and not cited and a.dialect != 'kie':
        rows.append(('WARN', 'L1', f'{len(refs)} refs passed but the prompt cites no slot'))

    # body vs tail: the tail = the last 【】 section (Maintain Consistency / Constraints) or the last sentence group
    parts = re.split(r'(【[^】]+】)', text)
    sections = {}
    cur = 'prefix'
    for p in parts:
        if p.startswith('【'): cur = p.strip('【】'); sections.setdefault(cur, '')
        else: sections[cur] = sections.get(cur, '') + p
    tail_keys = [k for k in sections if re.search(r'consist|constraint|exclude', k, re.I)]
    body_keys = [k for k in sections if k not in tail_keys and k != 'prefix']
    body = ' '.join(sections[k] for k in body_keys) if body_keys else text

    # L3 negation in the body (outside the audio line's sanctioned "no music/no words")
    ev_keys = [k for k in sections if re.search(r'event|script|timeline', k, re.I)]
    ev = ' '.join(sections[k] for k in ev_keys) if ev_keys else body
    negs = [m.group(0) for m in re.finditer(r'[^.;:]*\b(?:no|never|not|nothing|nobody|without)\b[^.;:]*', QUOTED.sub(' ', ev))]
    negs = [s.strip() for s in negs if not re.search(r'no music|no words|no other|no narration|nobody shouts|no dialogue|no subtitles|no lettering|no text|no cut|no change of angle|without any cut|nothing happens|nobody moves|no bang|never seen|heard only|at nothing|into nothing|\bonly\b|\bstill\b|no longer|does not reframe|never pulls', s, re.I)]
    for s in negs[:8]: rows.append(('WARN', 'L3', f'negation in the body: "{s[:90]}" — state the positive; prohibitions go in the tail'))

    # L4 ALL-CAPS tokens
    stop = DEFAULT_STOP | {w for w in a.caps_stoplist.split(',') if w}
    if a.rules:
        import json
        rj = json.load(open(a.rules, encoding='utf-8')); stop |= set(rj.get('caps_stoplist', []))
        for rule in rj.get('rules', []):
            stop |= {t.upper() for t in re.findall(r'[A-Za-z][A-Za-z0-9]{1,}', re.sub(r'\\[bBwWdDsS]|\(\?<!|\(\?!', ' ', rule['regex']))}
            stop |= {k.upper() for k in rule.get('roles', {})}
    caps = sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{2,}\b', QUOTED.sub(' ', text))) - stop)
    if caps: rows.append(('WARN', 'L4', f'ALL-CAPS tokens: {caps} — role names must be gate-ruled; a capital inside a quoted line is a stress mark and is not counted'))
    for m in QUOTED.finditer(text):
        shouted = [w for w in CAPWORD.findall(m.group(0)) if w not in {'OK', 'TV', 'AM', 'PM', 'VO'}]
        if len(shouted) > 2:
            rows.append(('WARN', 'L4', f'a shouted line: {m.group(0)[:70]!r} — capitalise one or two stressed words, never the line'))

    # L5 moderation words
    low = ' ' + text.lower() + ' '
    hits = sorted({w.strip() for w in MODERATION.get(a.dialect, []) if re.search(r'\b' + re.escape(w.strip()) + r'\b', low)})
    if hits: rows.append(('WARN', 'L5', f'venue moderation words: {hits} — paraphrase the shape; slapstick without injury words; a refused line becomes a mouth-shape twin'))

    # L6 parameters in prose (prefix exempt for the aspect token)
    pm = sorted({m.group(0) for m in PARAMS.finditer(body)})
    if pm: rows.append(('WARN', 'L6', f'parameters in the prose: {pm} — they ride on the call'))

    # L7 off-frame object named
    for m in OFF_FRAME.finditer(text):
        rows.append(('WARN', 'L7', f'off-frame object NAMED: "{m.group(0)[:80]}" — write the look, never the thing'))

    # L8 category referents / gait mechanics
    for pat in CATEGORY:
        if re.search(pat, text, re.I): rows.append(('WARN', 'L8', f'category referent ({pat}) — name ONE familiar filmed motion + the result'))
    gait_hits = [g for g in GAIT if g in low]
    if len(gait_hits) > 2: rows.append(('WARN', 'L8', f'{len(gait_hits)} locomotion/gait terms {gait_hits} — keep to ~2; never joint mechanics'))

    # L9 aerial view
    if 'aerial view' in low: rows.append(('WARN', 'L9', '"aerial view" fails — "a wide landscape photograph taken from a high ridge top"'))

    # L10 camera move vs diverging subjects
    if re.search(r'\b(push(?:es|ing)? in|dolly in|moves in|closes in)\b', low) and re.search(r'\b(diverge|run apart|scatter|separate|split up|spread out)\b', low):
        rows.append(('WARN', 'L10', 'a push-in while subjects diverge cannot hold them — bind the camera to ONE subject'))

    # L11 framing on its own clause + L12 beat density, per cut
    cuts = CUT.findall(text)
    for num, t0, t1, bodytxt in cuts:
        dur = float(t1) - float(t0)
        first_clause = re.split(r'[:;]', bodytxt, 1)[0]
        if not SHOT_SIZE.search(first_clause[:140]) and 'start frame' not in first_clause.lower():
            rows.append(('WARN', 'L11', f'Cut {num}: no shot-size token in its first clause — put the framing first, on its own clause'))
        beats = len([seg for seg in re.split(r';', bodytxt) if re.search(r'\b\w+(?:s|es)\b', seg)])
        if dur > 0 and beats / dur > 0.5 and dur >= 3:
            rows.append(('WARN', 'L12', f'Cut {num}: ~{beats} action segments in {dur:g} s (> 1 per 2 s) — the model rushes; cut beats before seconds'))

    # L37 multi-shot load (Emily2040/seedance-2.0 references/multishot-grammar.md, an authored heuristic first calibrated
    # on three rendered takes): seconds per load point S = duration ÷ (beats + load). A beat is a cut (a reaction or insert
    # with no line and no move counts half); load is 0.5 per camera move inside a cut and 1 per spoken line per 8 words
    # (12 CJK characters). Extra actors, contact, location changes and sound cues also load a clip but cannot be read off
    # the text, so this is a FLOOR: a clip that is Ambitious here is Ambitious for certain. It guards SPOKEN clips only:
    # silent quick cuts are a montage, whose density L12 already reads per cut (our house skeleton cuts at 1.5–2 s).
    if len(cuts) >= 2 and any(QUOTED.search(c[3]) for c in cuts):
        MOVE = re.compile(r'\b(push(?:es)?[- ]in|pull(?:s)?[- ](?:back|out)|dolly|dollies|pans?|panning|tilts?|tilting|orbits?|orbiting|tracking|crane|whip[- ]pans?|zooms?|zooming|arcs?|arcing|trucks?)\b', re.I)
        beats = load = 0.0
        for num, t0, t1, bodytxt in cuts:
            lines = QUOTED.findall(bodytxt); moved = bool(MOVE.search(QUOTED.sub(' ', bodytxt)))
            head = re.split(r'[:;,.]', bodytxt, 1)[0].lower()
            beats += 0.5 if (not lines and not moved and re.search(r'\b(insert|reaction)\b', head)) else 1.0
            load += 0.5 if moved else 0.0
            for q in lines:
                cjk = len(re.findall(r'[぀-ヿ㐀-鿿가-힯]', q))
                load += max(1.0, cjk / 12 if cjk else len(re.findall(r"[A-Za-z0-9']+", q)) / 8)
        D = a.duration or max(float(c[2]) for c in cuts)
        S = D / (beats + load) if beats + load else 0
        if S and S < 2.0:
            rows.append(('WARN', 'L37', f'multi-shot load: {D:g} s over {beats:g} beats + at least {load:g} load points = {S:.1f} s per point — '
                                        'Ambitious (under 2): lines start to garble and reactions get cut; merge the two lightest beats or '
                                        'split into two generations that keep every beat (DIALECTS § Multi-shot, multi-person direction)'))

    # L34 single-shot negatives on a generation that composes its own coverage. "No unmotivated cut / hidden splice / abrupt
    # push-in" belongs to ONE continuous shot of a few seconds; carried into a multi-cut or long generation it forbids the
    # coverage the long take was bought for — a cut inside one generation is descriptive, consistency across it is the verdict.
    SINGLE = re.compile(r'\b(?:no|never|without)\b[^.;]{0,60}?\b(unmotivated cuts?|hidden splices?|abrupt push-?ins?|jump cuts?)\b', re.I)
    sm = SINGLE.search(text); span = max([float(c[2]) for c in cuts] + [a.duration or 0])
    if sm and (len(cuts) > 1 or span > 6):
        rows.append(('WARN', 'L34', f'single-shot negatives ("{sm.group(0)[:70]}") on a generation of {len(cuts)} cut(s) / {span:g} s — they forbid the coverage a long generation composes; keep them only on one continuous shot of ≤ 6 s'))

    # L13 a reference described (appearance adjectives right after a slot citation)
    roles_txt = ' '.join(sections[k] for k in sections if re.search(r'role', k, re.I)) or ''
    for m in re.finditer(r'@(?:Image|ref)\s?\d+\s+(?:is|—|-)\s+([^.;]{0,80})', roles_txt):
        seg = m.group(1).lower()
        if re.search(r'\b(red|blue|green|brown|blonde|grey|gray|silver|dark|pale|tall|short|slim|stocky|ginger|long face|bare chest)\b', seg) and not re.search(r'use only|use its|never|do not|shape|size|silhouette|face and clothes|face, hair', seg):
            rows.append(('WARN', 'L13', f'a reference described: "@… {seg[:70]}" — point at it; adjectives can only contradict the asset'))

    # L16 cast not closed
    if re.search(r'\b(guests|crowd|partygoers|extras|everyone else|packed with|the other women|other men)\b', low) and not re.search(r'only these|the only people|no other', low):
        rows.append(('WARN', 'L16', 'crowd words without a closed cast — "the ONLY people in the shot are …; no other guests, no men"'))

    # L18 body asks for text/labels while the tail forbids them
    if re.search(r'\b(label|lettering|text|sign|caption)\b', body, re.I) and re.search(r'no (?:on-screen )?text|no lettering|no labels', low):
        if not re.search(r'no lettering on it|no lettering anywhere', low):
            rows.append(('WARN', 'L18', 'the body asks for text/label/lettering while the tail forbids text — pin the string on the item, or drop the request'))

    # L31 a clause that references an input the call does not carry (minimax-h3)
    # H3 has ONE positive stream and no negative prompt, so "do not reproduce its grid, markers"
    # with no <Video N> passed is an instruction to DRAW them. Measured 2026-09-11: the clause left
    # in after the clip was dropped painted a floor grid + cyan/red markers on every take.
    if a.dialect == 'minimax-h3':
        VID_EXT = ('.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v')
        vid_refs = [r for r in refs if r.lower().endswith(VID_EXT)]
        cites_video = re.search(r'<Video\s?\d+>', text)
        role_line = re.search(r'do not reproduce its proxy geometry|proxy geometry, grid, markers', text, re.I)
        if cites_video and not vid_refs:
            rows.append(('FAIL', 'L31', f'the prompt cites <Video N> but no video ref is passed ({refs or "none"}) — '
                                        'H3 renders the nouns of a clause whose referent is absent; pass the clip or delete the clause'))
        if role_line and not cites_video:
            rows.append(('FAIL', 'L31', 'the proxy-clip role line ("do not reproduce its proxy geometry, grid, markers...") '
                                        'is present but no <Video N> is cited — that negation has nothing to bind to and draws a grid'))

    # L32 a speech tag outside the trained dialogue envelope (minimax-h3)
    # A bare tag gets SPOKEN: measured community-side as "br" / "le-incredible" (the model reading the
    # bracket). The envelope (S<n>) says: <d>[English] ... </d> stops it.
    if a.dialect == 'minimax-h3':
        spans = [m.span() for m in re.finditer(r'<d>.*?</d>', text, re.S)]
        def inside(i):
            return any(lo <= i < hi for lo, hi in spans)
        TAG = re.compile(r'<(?:i|b|em|whisper|laughs?|chuckle|sighs?|pause|long pause|gasp|groan|inhale|exhale|'
                         r'stutter|hmm|cough|clears throat|smacks lips|scream|phew|nervous|catches breath)>', re.I)
        stray = sorted({m.group(0) for m in TAG.finditer(text) if not inside(m.start())})
        if stray:
            rows.append(('WARN', 'L32', f'speech tag outside the <d>...</d> envelope: {stray} — '
                                        'wrap the line as (S1) says: <d>[English] ... </d> or the tag is read aloud'))

    # L33 beauty-adjective phrasing in an identity description (minimax-h3)
    # Reported upstream to activate the model's generalised beauty prior and overwrite the face the
    # reference carries. Only fires when an identity reference is actually cited — the words compete
    # with the reference, so with no reference there is nothing to overwrite.
    if a.dialect == 'minimax-h3':
        BEAUTY = re.compile(
            r'\b(attractive|beautiful|gorgeous|handsome|stunning|pretty|lovely|striking|'
            r'flawless|perfect(?:ly)? (?:symmetrical|proportioned|smooth)|blemish-free|'
            r'chiselled|chiseled|photogenic|model-like|doll-like)\b'
            r'|\bsoft oval face\b|\bstraight slender nose\b|\bdoe[- ]eyed\b|\bporcelain skin\b',
            re.I)
        cites_identity = re.search(r'<(?:Picture|Subject)\s?\d+>', text)
        hits = sorted({m.group(0).lower() for m in BEAUTY.finditer(text)})
        if hits and cites_identity:
            rows.append(('WARN', 'L33', f'beauty-adjective phrasing beside an identity reference: {hits} — '
                                        'reported to overwrite the reference face with the model\'s beauty prior; '
                                        'write biometric traits (nose, jaw, eye colour and spacing, hairline, marks, age)'))

    # L36 a per-line prompt that drifted from the prompt its series was locked on (only the quoted line may change)
    if a.locked:
        def frame_of(t):
            t = re.sub(r'[ \t]+', ' ', QUOTED.sub('"…"', t))
            return [s.strip() for s in re.split(r'(?<=[.;!?])\s+|\n+', t) if s.strip()]
        lock, cur = frame_of(open(a.locked, encoding='utf-8').read()), frame_of(text)
        if lock != cur:
            gone = [s for s in lock if s not in cur]; new = [s for s in cur if s not in lock]
            what = '; '.join([f'- "{s[:60]}"' for s in gone[:2]] + [f'+ "{s[:60]}"' for s in new[:2]]) or 'the same sentences in a different order'
            rows.append(('WARN', 'L36', f'drifted from the locked prompt {a.locked}: {what} — only the quoted line changes between lines; re-lock on purpose'))

    # L38-L41 photoreal rows (references/REALISM.md). Dialogue is skipped: a sung or spoken word is never an instruction.
    plain = QUOTED.sub(' ', text)

    # L38 quality words push the generic glossy render (REALISM.md § 1). "cinematic" and "epic" only in a still prompt:
    # MiniMax's own H3 examples open "Live-action, cinematic, ...", where it is a style word. 2K/4K are L6's.
    QUALITY = (r'\b(?:8|16)k\b|\bhyper[- ]?realistic\b|\bhyper[- ]?real\b|\bultra[- ]?realistic\b|\bphoto[- ]?realistic\b'
               r'|\bphotorealism\b|\bmasterpiece\b|\baward[- ]winning\b|\bstunning\b|\bbreathtaking\b'
               r'|\b(?:highly|ultra|hyper)[- ]detailed\b|\bbest quality\b|\bhigh[- ]quality\b|\btrending on artstation\b'
               r'|\boctane render\b|\bunreal engine\b')
    if a.dialect == 'kie':
        QUALITY += r'|\bcinematic\b|\bepic\b'
    q = sorted({m.group(0).lower() for m in re.finditer(QUALITY, plain, re.I)})
    if q:
        rows.append(('WARN', 'L38', f'quality words {q} — they push the generic render; describe the capture '
                                    '(camera, lens, exposure) and the light (REALISM.md § 1)'))

    # L39 grain or noise asked of a still (REALISM.md § 2.4): the video copies a reference's grain and adds its own.
    if a.dialect == 'kie':
        GRAIN = re.compile(r'\b(?:film|fine|coarse|natural|heavy|light|subtle|visible|analog(?:ue)?|photographic)[- ]grain\b'
                           r'|\bgrainy\b|\b(?:sensor|digital|luminance|shadow|colou?r) noise\b|\bnoise in the shadows\b'
                           r'|\bnoisy\b|\bhalation\b|\bchromatic aberration\b', re.I)
        g = []
        for m in GRAIN.finditer(plain):
            before = plain[max(0, m.start() - 40):m.start()]
            if re.search(r'\b(?:no|without|free of|zero|never)\b[^.;]*$', before, re.I):
                continue
            g.append(m.group(0).lower())
        if g:
            rows.append(('WARN', 'L39', f'grain or noise asked of a still: {sorted(set(g))} — the video copies it and adds '
                                        'its own; ask for "a clean, noise-free image" and put grain in the video prompt (REALISM.md § 2.4)'))

    # L40 a negation naming a scene object on H3 (REALISM.md § 3.5): ONE positive stream, so a named thing can be drawn
    # (the L31 grid). The tail may name artifacts that are not objects in the scene; anything else is stated positively.
    if a.dialect == 'minimax-h3':
        ARTIFACT = re.compile(r'subtitle|caption|text|lettering|letters|words|watermark|logo|brand|animat|cartoon|anime|styli[sz]'
                              r'|cgi|\bcg\b|render|skin|smooth|plastic|waxy|hdr|glow|bloom|halation|grad(?:e|ing)|saturat|sharpen'
                              r'|artifact|morph|warp|distort|blur|music|score|narration|voice-?over|dialogue|speech|\bcuts?\b|splice'
                              r'|transition|jump|frame rate|stutter|jitter|painterly|illustrat|drawing|\b3d\b|video game|daylight'
                              r'|lighting|performance|acting|angle|reframe|camera|change|longer', re.I)
        found = []
        for m in re.finditer(r'\b(?:no|nor)\s+([^.;:!?\n]+)', plain, re.I):
            for item in re.split(r',|\bor\b|\band\b|\bnor\b|\bno\b', m.group(1), flags=re.I):
                item = item.strip(' -–—')
                if item and not ARTIFACT.search(item):
                    found.append(item)
        for m in re.finditer(r'\b(?:never|without)\s+(?:a|an|the|any)\s+([a-z][^.;:!?,\n]{1,40})', plain, re.I):
            if not ARTIFACT.search(m.group(1)):
                found.append(m.group(1).strip())
        for m in re.finditer(r'\b((?:[a-z][a-z-]+ ){0,2}[a-z][a-z-]+)(?: itself)? (?:is |stays |remains )?(?:never|not) (?:in|inside|within|enters?|appears? in) '
                             r'(?:the )?(?:frame|shot|picture)', plain, re.I):
            if not ARTIFACT.search(m.group(1)):
                found.append(m.group(1))
        if found:
            rows.append(('WARN', 'L40', f'a negation names scene objects {found[:6]} — H3 can draw what a negation names; '
                                        'state the wanted state ("the flames stay small and low"; "the light falls from '
                                        'behind the camera") and keep the tail to artifacts (REALISM.md § 3.5)'))

    # L41 H3 reads the style first (REALISM.md § 3.1): "[Shot 1] Live-action, cinematic, ...", or the style sentence
    # just before [Shot 1] in the full-reference form; a front-end scene text opens with it.
    if a.dialect == 'minimax-h3':
        STYLE = re.compile(r'live[- ]action|cinematic|documentary|2d[- ]animated|3d cg|claymation|watercolou?r|vintage film'
                           r'|stop[- ]motion|animated|realistic|realism|naturalistic', re.I)
        m = re.search(r'\[Shot 1\]\s+(?=[A-Za-z<])', text)   # the shot's start, never a citation "(from [Shot 1])"
        if m:
            after = text[m.end():].strip()
            lead = text[max(0, m.start() - 300):m.start()] + ' ' + re.split(r'(?<=[.!?])\s', after, maxsplit=1)[0]
        else:
            start = re.sub(r'^\s*(?:integrated_multimodal_description|detailed_description)\s*:\s*', '', text)
            lead = re.split(r'(?<=[.!?])\s', start.strip(), maxsplit=1)[0]
        if not STYLE.search(lead):
            rows.append(('WARN', 'L41', f'the first shot does not open with a style word — "Live-action, …" first, then the '
                                        f'composition (REALISM.md § 3.1): "{lead.strip()[:70]}"'))

    # report
    order = {'FAIL': 0, 'WARN': 1}
    rows.sort(key=lambda r: (order[r[0]], r[1]))
    for lvl, rid, msg in rows: print(f'  {lvl:<4} {rid:<4} {msg}')
    fails = [r for r in rows if r[0] == 'FAIL'] + ([r for r in rows if r[0] == 'WARN'] if a.strict else [])
    warns = [r for r in rows if r[0] == 'WARN']
    print(f'PROMPT-LINT {"FAIL" if fails else "OK"}  {a.prompt}  {n} chars · {len(cited)} slots · {len(cuts)} cuts · {len(warns)} warnings')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
