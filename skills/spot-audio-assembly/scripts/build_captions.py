#!/usr/bin/env python3
"""build_captions.py — word-synced caption cards as RGBA PNG layers at DELIVERY resolution + a manifest the finisher
overlays AFTER the downscale (so the type stays pixel-crisp). Cards come from the EDL (audio.captions: {line, words:[i,j]})
and the word times (audio.word_times, relative to each VO file); timeline time = audio.vo[line].at + word time.
The DISPLAY TEXT is the script's (audio.vo[line].text), the TIMING the transcript's: a transcript's capitalisation and
spelling are not the client's copy, so script word i is paired with time i only when the two counts agree — otherwise
nothing is rendered. Hyphenated compounds split into two words, the way vo_word_times.py times them.
Style = audio.caption_style, every key checked — an unknown key stops the build (a style block whose names matched nothing
the builder read rendered its defaults for a whole job and looked deliberate). House default: one font, white, black
stroke + soft shadow, ALL CAPS, NO PUNCTUATION — ever — the spoken word highlighted in the brand colour; highlight "none"
renders one plain layer per card. A card ends a frame before the next card's lead (two cards once shared a frame on a
back-to-back word) and never runs over the end card.

  build_captions.py --root <project> --edl edit/<SPOT>-EDL.json [--out-dir <captions_dir>] [--fonts-dir hyper/fonts]
                    [--canvas 1080x1920]
caption_style: font (A = Bangers-Regular.ttf · B = Inter.ttf · C = Nunito.ttf · or a font file name, all under --fonts-dir)
  · weight (a variable font's named instance: Black, SemiBold; B defaults to Black) · size_h, stroke_h, shadow_h (fractions
  of the canvas height) · shadow_alpha (0-255) · line_h (line pitch as a multiple of the size) · y (block centre, fraction
  of height) · max_w (fraction of width) · highlight (#rrggbb or none) · upper (true/false) · lead, hold (s). "_" keys are notes.
"""
import argparse, json, os, re, sys
from PIL import Image, ImageDraw, ImageFont

STYLE_KEYS = {'font', 'weight', 'size_h', 'stroke_h', 'shadow_h', 'shadow_alpha', 'line_h', 'y', 'max_w', 'highlight', 'upper', 'lead', 'hold'}
FONTS = {'A': 'Bangers-Regular.ttf', 'B': 'Inter.ttf', 'C': 'Nunito.ttf'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl', required=True); ap.add_argument('--out-dir'); ap.add_argument('--fonts-dir', default='hyper/fonts')
    ap.add_argument('--canvas', default='1080x1920')
    a = ap.parse_args(); os.chdir(a.root)
    edl = json.load(open(a.edl, encoding='utf-8')); A = edl['audio']; st = A.get('caption_style', {}); caps = A.get('captions', []); vo = A['vo']
    bad = sorted(k for k in st if k not in STYLE_KEYS and not k.startswith('_'))
    if bad: sys.exit(f'caption_style: unknown key(s) {bad} — the builder reads {sorted(STYLE_KEYS)}')
    capd = a.out_dir or A.get('captions_dir', 'edit/captions'); WT = json.load(open(A.get('word_times', f"{A.get('captions_dir', 'edit/captions')}/word-times.json"), encoding='utf-8'))
    W, H = (int(v) for v in a.canvas.lower().split('x'))
    fk = st.get('font', 'A'); font_file = f'{a.fonts_dir}/{FONTS.get(fk, fk)}'
    if not os.path.exists(font_file): sys.exit(f'caption font missing: {font_file}')
    size = int(H * st.get('size_h', 0.058)); stroke = int(H * st.get('stroke_h', 0.0055)); shadow = int(H * st.get('shadow_h', 0.004)); ybase = st.get('y', 0.70); maxw = st.get('max_w', 0.86)
    hi = st.get('highlight', '#ffe01b'); HI = None if str(hi).lower() in ('none', 'off') else tuple(int(hi.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    HOLD = st.get('hold', 0.5); LEAD = st.get('lead', 0.05); LH = st.get('line_h', 1.12); SA = int(st.get('shadow_alpha', 150))
    font = ImageFont.truetype(font_file, size)
    weight = st.get('weight', 'Black' if fk == 'B' else None)
    if weight:
        try: font.set_variation_by_name(weight)
        except Exception as ex: sys.exit(f'caption font {font_file}: no named instance {weight!r} ({ex})')

    def clean(w):
        w = w.replace('-', ''); w = re.sub(r"[^\w\s']", '', w); return w.upper() if st.get('upper', True) else w

    def layout(words, d):
        lines = [[]]
        for w in words:
            trial = ' '.join(lines[-1] + [w])
            if d.textlength(trial, font=font) > W * maxw and lines[-1]: lines.append([w])
            else: lines[-1].append(w)
        return lines

    def script_words(L):
        toks = [w for w in (vo[L].get('text') or '').split() if re.sub(r"[^\w']", '', w)]   # a bare dash or ellipsis is not a word
        parts = [p for w in toks for p in w.split('-') if re.sub(r"[^\w']", '', p)]
        n = len(WT[L])
        if len(parts) == n: return parts
        if len(toks) == n: return toks   # word times made with --keep-hyphens
        sys.exit(f'{L}: the script has {len(parts)} words ({len(toks)} with hyphens kept), the word times {n} — re-run vo_word_times.py --only {L}; nothing rendered')

    os.makedirs(capd, exist_ok=True); man = []; n = 0; SW = {}
    card = [e for e in edl['events'] if e.get('role') == 'endcard']
    for ci, c in enumerate(caps):
        L = c['line']; i, j = c['words']; ws = WT[L][i:j]; at = vo[L]['at']
        if L not in SW: SW[L] = script_words(L)
        texts = [clean(w) for w in SW[L][i:j]]; times = [(round(at + w[1], 3), round(at + w[2], 3)) for w in ws]
        nxt = at + WT[L][caps[ci + 1]['words'][0]][1] if ci + 1 < len(caps) and caps[ci + 1]['line'] == L else None
        show0 = round(times[0][0] - LEAD, 3); show1 = round(min(times[-1][1] + HOLD, nxt - LEAD - 1 / 24) if nxt else times[-1][1] + HOLD, 3)
        if card: show1 = min(show1, round(card[0]['tl'][0] - 0.02, 3))
        for k in (range(len(ws)) if HI else [None]):
            img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img); lines = layout(texts, d); lh = int(size * LH); y0 = int(H * c.get('y', ybase)) - lh * len(lines) // 2
            idx = 0
            for li, line in enumerate(lines):
                tw = d.textlength(' '.join(line), font=font); x = (W - tw) // 2; yy = y0 + li * lh
                for w in line:
                    col = HI if HI and idx == k else (255, 255, 255)
                    d.text((x + shadow, yy + shadow), w, font=font, fill=(0, 0, 0, SA), stroke_width=stroke, stroke_fill=(0, 0, 0, SA))
                    d.text((x, yy), w, font=font, fill=col + (255,), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
                    x += d.textlength(w + ' ', font=font); idx += 1
            if k is None: t0, t1 = show0, show1
            else: t0 = show0 if k == 0 else times[k][0]; t1 = show1 if k == len(ws) - 1 else times[k + 1][0]
            out = f'{capd}/cap-{n:02d}.png'; img.save(out); man.append({'file': out, 'tl': [round(t0, 3), round(t1, 3)], 'text': ' '.join(texts), 'hi': texts[k] if k is not None else None}); n += 1
        print(f"{L} {' '.join(texts)}  show {show0}-{show1}")
    json.dump(man, open(f'{capd}/manifest.json', 'w', encoding='utf-8'), indent=1); print('caption layers', len(man), 'style', fk, 'highlight', hi, '->', capd)


if __name__ == '__main__':
    main()
