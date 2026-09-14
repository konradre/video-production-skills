#!/usr/bin/env python3
"""explainer_timeline.py — time an explainer's scenes, beats and captions FROM THE NARRATION, never by hand.

  explainer_timeline.py --project <dir> --timing <timing.json> [--offsets '{"L1": 0.0}'] [--vo <file>] [--check]
  explainer_timeline.py --selftest

Reads <project>/explainer.json (name, canvas, fps, target_s, lead/tail/exit/ending-fade seconds, caption style),
<project>/script.md (the narration as it must READ on screen: one `## <scene-id> <title>` header per scene, then
its lines) and <project>/storyboard.json (per scene: `anchor` = the first words spoken in it; `beats` = {name: a
phrase spoken inside it}; `small_print` = [{text, beat}]; optional `last_text` = the beat of its last text
entrance). Timing: a word list [[word, start, end], …] or {"words": […]}; a per-line file from spot-audio-assembly's
vo_word_times.py with --offsets (each line's `at`); or a voice-clone joins sidecar ({"segments_detail": [{text,
start, end}]} — a time inside a segment is character-proportional and reported as approx).

Every anchor and beat resolves by an exact phrase match in spoken order; a phrase that is missing, or that occurs
more than once, stops the run — lengthen it. Then it WRITES: the host slots and the root duration in index.html
(between <!-- SLOTS:BEGIN --> and <!-- SLOTS:END -->); every scene's BEATS object in scene-local seconds (between
/* BEATS:BEGIN */ and /* BEATS:END */) and its root duration; compositions/captions.html (blocks built from the
AUTHORED text aligned position by position to the spoken words, broken by the caption font's measured advance); and
timeline.json. It exits 1 and writes nothing on: an empty timing result; a runtime outside ±15 % of target_s; small
print held under 2.5 s before its scene's exit; a closing window under 1.0 s; a caption word wider than the caption
width; a capitalised or numeric authored word the audio never says; storyboard and script scene lists that differ.
--check measures and reports, and writes nothing.
"""
import argparse, difflib, html, json, re, subprocess, sys, tempfile, wave
from pathlib import Path

WORD = re.compile(r"[\w'’]+")
SMALL_PRINT_S, CLOSING_S, RUNTIME_TOL = 2.5, 1.0, 0.15
DEFAULTS = {"fps": 30, "target_s": 0, "lead_s": 0.25, "tail_s": 1.0, "exit_s": 0.3, "ending_fade_s": 0.5,
            "caption": {"font": "assets/fonts/Display.ttf", "size_frac": 0.028, "top_frac": 0.8, "width_frac": 0.86,
                        "lines": 2, "weight": 800, "lead_s": 0.05, "hold_s": 0.5, "gap_hold_s": 0.6}}


def ntok(w):
    return w.replace("’", "'").lower().strip("'")


def norm_tokens(text):
    return [t for t in (ntok(x) for x in WORD.findall(text)) if t]


def load_cfg(root):
    cfg = json.loads((root / "explainer.json").read_text(encoding="utf-8"))
    out = {**DEFAULTS, **cfg}; out["caption"] = {**DEFAULTS["caption"], **cfg.get("caption", {})}
    return out


def load_script(path):
    scenes, cur, in_comment = [], None, False
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if in_comment or s.startswith("<!--"):
            in_comment = "-->" not in s
            continue
        m = re.match(r"^##\s+(\S+)\s*(.*)$", s)
        if m:
            cur = {"id": m.group(1), "title": m.group(2), "text": []}; scenes.append(cur)
        elif cur is not None and s and not s.startswith("#"):
            cur["text"].append(s)
    return scenes


def load_timing(path, offsets=None):
    j = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(j, dict) and "segments_detail" in j:
        words = []
        for seg in j["segments_detail"]:
            toks = [t for t in seg.get("text", "").split() if WORD.search(t)]
            if not toks:
                continue
            s, e = float(seg["start"]), float(seg["end"]); n = sum(len(t) for t in toks); t0 = s
            for k, t in enumerate(toks):
                d = (e - s) * len(t) / n
                words.append({"w": t, "s": round(t0, 3), "e": round(t0 + d, 3), "exact": k == 0}); t0 += d
        return words
    if isinstance(j, dict) and "words" in j:
        j = j["words"]
    if isinstance(j, dict):
        if not offsets:
            sys.exit("a per-line word-times file needs --offsets '{\"L1\": 0.0, …}' (each line's `at` on the timeline)")
        words = []
        for line in sorted(j, key=lambda k: offsets[k]):
            words += [{"w": w, "s": round(offsets[line] + s, 3), "e": round(offsets[line] + e, 3), "exact": True} for w, s, e in j[line]]
        return words
    return [{"w": w, "s": float(s), "e": float(e), "exact": True} for w, s, e in j]


def audio_duration(path):
    p = Path(path)
    if not p.is_file():
        return None
    if p.suffix.lower() == ".wav":
        with wave.open(str(p)) as w:
            return w.getnframes() / float(w.getframerate())
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True).stdout.strip()
    return float(out) if out else None


def resolve(board, words, cfg, total):
    toks = [(t, i) for i, w in enumerate(words) for t in norm_tokens(w["w"])]
    tn = [t for t, _ in toks]; problems = []

    def hits(phrase, lo=0, hi=None):
        p = norm_tokens(phrase or ""); hi = len(tn) if hi is None else hi
        return [k for k in range(lo, hi - len(p) + 1) if p and tn[k:k + len(p)] == p]

    pos = []
    for sc in board["scenes"]:
        h = hits(sc.get("anchor"))
        if len(h) != 1:
            problems.append(f"{sc['id']}: anchor {sc.get('anchor')!r} occurs {len(h)} time(s) in the narration — an anchor is one unique spoken phrase")
        pos.append(h[0] if len(h) == 1 else None)
    if problems:
        return None, problems
    if pos != sorted(pos):
        return None, ["scene anchors are out of spoken order: " + " → ".join(sc["id"] for _, sc in sorted(zip(pos, board["scenes"]), key=lambda x: x[0]))]
    starts = [0.0 if i == 0 else max(0.0, words[toks[k][1]]["s"] - cfg["lead_s"]) for i, k in enumerate(pos)]
    scenes = []
    for i, sc in enumerate(board["scenes"]):
        a = starts[i]; b = starts[i + 1] if i + 1 < len(starts) else total
        lo = pos[i]; hi = pos[i + 1] if i + 1 < len(pos) else len(tn)
        beats = {"start": 0.0, "end": round(b - a, 3)}; approx = [] if words[toks[pos[i]][1]]["exact"] else ["anchor"]
        for name, phrase in (sc.get("beats") or {}).items():
            h = hits(phrase, lo, hi)
            if len(h) != 1:
                problems.append(f"{sc['id']}: beat {name} {phrase!r} occurs {len(h)} time(s) inside the scene — a beat is one unique phrase spoken in it")
                continue
            w = words[toks[h[0]][1]]; beats[name] = round(max(0.0, w["s"] - a), 3)
            if not w["exact"]:
                approx.append(name)
        scenes.append({"id": sc["id"], "start": round(a, 3), "end": round(b, 3), "dur": round(b - a, 3), "beats": beats, "approx": approx})
    return scenes, problems


def check_time(cfg, board, scenes, vo_dur):
    problems = []; notes = []; target = float(cfg.get("target_s") or 0); by_id = {s["id"]: s for s in scenes}
    if target and abs(vo_dur - target) > RUNTIME_TOL * target:
        problems.append(f"runtime {vo_dur:.1f} s is outside ±15 % of the {target:g} s target — add or cut sentences, never change the voice's speed")
    for sc in board["scenes"]:
        s = by_id[sc["id"]]
        for sp in sc.get("small_print") or []:
            t = s["beats"].get(sp.get("beat", "start"))
            if t is None:
                problems.append(f"{sc['id']}: small print {sp.get('text', '')[:40]!r} names beat {sp.get('beat')!r}, which the scene does not define"); continue
            held = s["dur"] - cfg["exit_s"] - t
            if held < SMALL_PRINT_S:
                problems.append(f"{sc['id']}: small print {sp.get('text', '')[:40]!r} holds {held:.2f} s before the exit (under {SMALL_PRINT_S} s) — move it to an earlier beat")
    # the point of view may not sit still for three scenes running (STORYBOARD § Point of view). An
    # unfilled angle is not a violation — it is an unfinished row, reported once, not per run.
    angles = [(sc["id"], (sc.get("angle") or "").strip().lower()) for sc in board["scenes"]]
    blank = [i for i, a in angles if not a]
    if blank:
        notes.append(f"angle is empty on {len(blank)} scene(s) ({', '.join(blank[:4])}"
                     f"{', …' if len(blank) > 4 else ''}) — an unfinished row, so the "
                     "three-in-a-row check skipped it (STORYBOARD § Point of view)")
    run = 1
    for i in range(1, len(angles)):
        prev, cur = angles[i - 1][1], angles[i][1]
        run = run + 1 if cur and cur == prev else 1
        if run >= 3:
            problems.append(f"{angles[i - 2][0]} → {angles[i][0]}: three scenes running are seen from "
                            f"{cur!r} — change the point of view, and give the new fact its own instrument "
                            "(STORYBOARD § Point of view)")
    last = board["scenes"][-1]; s = by_id[last["id"]]
    lt = s["beats"].get(last["last_text"]) if last.get("last_text") else max(v for k, v in s["beats"].items() if k != "end")
    if lt is None:
        problems.append(f"{last['id']}: last_text {last.get('last_text')!r} is not a beat of the scene")
    else:
        window = s["dur"] - cfg["ending_fade_s"] - lt
        if window < CLOSING_S:
            problems.append(f"{last['id']}: the closing window is {window:.2f} s (the last text at {lt:.2f} s, the fade from {s['dur'] - cfg['ending_fade_s']:.2f} s) — under {CLOSING_S} s; bring the last line forward")
    return problems, notes


def caption_blocks(cfg, root, script, words, W, H):
    from PIL import ImageFont
    cap = cfg["caption"]; px = round(cap["size_frac"] * H); maxw = cap["width_frac"] * W; problems = []
    font = ImageFont.load_default(size=px) if cap["font"] == "default" else ImageFont.truetype(str(root / cap["font"]), px)
    display = [t for sc in script for line in sc["text"] for t in line.split()]
    dtoks = [(t, j) for j, d in enumerate(display) for t in norm_tokens(d)]
    spoken = [(t, i) for i, w in enumerate(words) for t in norm_tokens(w["w"])]
    times = [None] * len(display)
    sm = difflib.SequenceMatcher(None, [t for t, _ in dtoks], [t for t, _ in spoken], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                j = dtoks[i1 + k][1]; w = words[spoken[j1 + k][1]]
                times[j] = (min(times[j][0], w["s"]), max(times[j][1], w["e"])) if times[j] else (w["s"], w["e"])
        elif op == "replace":
            s0, e0 = words[spoken[j1][1]]["s"], words[spoken[j2 - 1][1]]["e"]
            js = sorted({dtoks[k][1] for k in range(i1, i2)}); chars = sum(len(display[j]) for j in js) or 1; t = s0
            for j in js:
                d = (e0 - s0) * len(display[j]) / chars
                times[j] = times[j] or (t, t + d); t += d
        elif op == "delete":
            for j in sorted({dtoks[k][1] for k in range(i1, i2)}):
                raw = display[j].strip(".,;:!?\"'()“”‘’")
                if times[j] is None and (raw[:1].isupper() or any(c.isdigit() for c in raw)):
                    problems.append(f"caption word {display[j]!r} is authored but never spoken — captions show only what the audio says")
    items = [(display[j], times[j]) for j in range(len(display)) if times[j] is not None]
    dropped = [display[j] for j in range(len(display)) if times[j] is None]
    blocks, lines = [], [[]]

    def flush():
        nonlocal lines
        if any(lines):
            blocks.append([l for l in lines if l])
        lines = [[]]

    for raw, (s, e) in items:
        if font.getlength(raw) > maxw:
            problems.append(f"caption word {raw!r} is wider than the caption width at {px} px — shorten it or lower the caption size")
        if lines[-1] and font.getlength(" ".join(r for r, _, _ in lines[-1]) + " " + raw) > maxw:
            if len(lines) >= cap["lines"]:
                flush()
            else:
                lines.append([])
        lines[-1].append((raw, s, e))
        if raw.rstrip("\"')”’").endswith((".", "!", "?")):
            flush()
    flush()
    out, frame = [], 1.0 / cfg["fps"]
    for k, b in enumerate(blocks):
        first, last = b[0][0], b[-1][-1]
        show = max(0.0, first[1] - cap["lead_s"]); hide = last[2] + cap["hold_s"]
        if k + 1 < len(blocks):
            nxt = max(0.0, blocks[k + 1][0][0][1] - cap["lead_s"])
            hide = nxt - frame if nxt - last[2] < cap["gap_hold_s"] else min(hide, nxt - frame)
        out.append({"lines": [" ".join(r for r, _, _ in l) for l in b], "show": round(show, 3), "hide": round(max(hide, show + frame), 3)})
    return out, problems, dropped, px


def captions_html(blocks, cfg, W, H, total, px):
    cap = cfg["caption"]; top = round(cap["top_frac"] * H); side = round((1 - cap["width_frac"]) / 2 * W)
    divs = "\n".join(f'  <div id="captions-c{k:03d}" class="cap">' + "".join(f'<div class="ln">{html.escape(l)}</div>' for l in b["lines"]) + "</div>"
                     for k, b in enumerate(blocks))
    sets = ", ".join(f"[{k}, {b['show']:.3f}, {b['hide']:.3f}]" for k, b in enumerate(blocks))
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body>
<template id="captions-template">
<style>
  @font-face {{ font-family:'Display'; src:url('assets/fonts/Display.ttf') format('truetype'); }}
  #root {{ position:absolute; inset:0; pointer-events:none; }}
  .cap {{ position:absolute; left:{side}px; right:{side}px; top:{top}px; opacity:0; text-align:center; color:#fff;
         font-family:'Display', sans-serif; font-weight:{cap['weight']}; font-size:{px}px; line-height:1.18;
         text-shadow:0 0 {max(2, px // 8)}px #000, 0 {max(1, px // 20)}px {max(2, px // 10)}px #000; }}
  .ln {{ white-space:nowrap; }}
</style>
<div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}" data-duration="{total:.3f}">
{divs}
</div>
<script>
(function () {{
  /* written by explainer_timeline.py from the narration; never hand-edit — [block, show, hide] in seconds */
  var C = [{sets}];
  var tl = gsap.timeline({{ paused: true }});
  C.forEach(function (c) {{
    var el = document.getElementById('captions-c' + ('00' + c[0]).slice(-3));
    tl.set(el, {{ opacity: 1 }}, c[1]); tl.set(el, {{ opacity: 0 }}, c[2]);
  }});
  window.__timelines['captions'] = tl;
}})();
</script>
</template>
</body>
</html>
"""


def run(project, timing, offsets=None, check=False, vo=None):
    root = Path(project); cfg = load_cfg(root); W, H = (int(v) for v in cfg["canvas"].lower().split("x"))
    board = json.loads((root / "storyboard.json").read_text(encoding="utf-8")); script = load_script(root / "script.md")
    words = load_timing(timing, offsets)
    if not words:
        return [f"{timing} holds no words — an empty timing result is never interpolated"], None
    ids_board, ids_script = [s["id"] for s in board["scenes"]], [s["id"] for s in script]
    if ids_board != ids_script:
        return [f"storyboard scenes {ids_board} differ from script scenes {ids_script}"], None
    vo_dur = audio_duration(vo or root / "assets" / "audio" / "vo.wav") or words[-1]["e"]
    total = round(vo_dur + cfg["tail_s"], 3)
    scenes, problems = resolve(board, words, cfg, total)
    if scenes is None:
        return problems, None
    timing_problems, notes = check_time(cfg, board, scenes, vo_dur); problems += timing_problems
    blocks, cap_problems, dropped, px = caption_blocks(cfg, root, script, words, W, H); problems += cap_problems
    report = {"notes": notes, "name": cfg["name"], "canvas": [W, H], "vo_s": round(vo_dur, 3), "total_s": total, "scenes": scenes,
              "captions": {"blocks": len(blocks), "px": px, "dropped_words": dropped}, "problems": problems}
    if problems or check:
        return problems, report
    host = root / "index.html"; s = host.read_text(encoding="utf-8")
    slots = "\n".join(f'<div id="el-{sc["id"]}" data-composition-id="{sc["id"]}" data-composition-src="compositions/scenes/{sc["id"]}.html" '
                      f'data-start="{sc["start"]:.3f}" data-duration="{sc["dur"]:.3f}" data-track-index="1"></div>' for sc in scenes)
    slots += (f'\n<div id="el-captions" data-composition-id="captions" data-composition-src="compositions/captions.html" '
              f'data-start="0" data-duration="{total:.3f}" data-track-index="5"></div>')
    s, n = re.subn(r"<!-- SLOTS:BEGIN -->.*?<!-- SLOTS:END -->", lambda m: f"<!-- SLOTS:BEGIN -->\n{slots}\n<!-- SLOTS:END -->", s, flags=re.S)
    s, m = re.subn(r'(<div id="root"[^>]*?data-duration=")[^"]*(")', lambda g: f"{g.group(1)}{total:.3f}{g.group(2)}", s, count=1)
    if n != 1 or m != 1:
        return [f"{host}: the SLOTS markers or the root data-duration are missing — re-scaffold with explainer_new.py"], report
    scene_texts = {}
    for sc in scenes:
        p = root / "compositions" / "scenes" / f"{sc['id']}.html"
        if not p.is_file():
            return [f"{p} does not exist — scaffold the scene (explainer_new.py --add {sc['id']})"], report
        t = p.read_text(encoding="utf-8")
        t, n = re.subn(r"/\* BEATS:BEGIN.*?\*/.*?/\* BEATS:END \*/",
                       lambda g: "/* BEATS:BEGIN — written by explainer_timeline.py from the narration; never hand-edit */\n"
                                 f"  var BEATS = {json.dumps(sc['beats'])};\n  /* BEATS:END */", t, flags=re.S)
        t, m = re.subn(rf'(data-composition-id="{re.escape(sc["id"])}"[^>]*?data-duration=")[^"]*(")', lambda g: f"{g.group(1)}{sc['dur']:.3f}{g.group(2)}", t, count=1)
        if n != 1 or m != 1:
            return [f"{p}: the BEATS markers or the scene root's data-duration are missing"], report
        scene_texts[p] = t
    host.write_text(s, encoding="utf-8")
    for p, t in scene_texts.items():
        p.write_text(t, encoding="utf-8")
    (root / "compositions").mkdir(exist_ok=True)
    (root / "compositions" / "captions.html").write_text(captions_html(blocks, cfg, W, H, total, px), encoding="utf-8")
    (root / "timeline.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return problems, report


def print_report(report, problems):
    if report:
        print(f"{report['name']} {report['canvas'][0]}x{report['canvas'][1]} | voice {report['vo_s']} s | total {report['total_s']} s | "
              f"captions {report['captions']['blocks']} blocks at {report['captions']['px']} px")
        for sc in report["scenes"]:
            beats = " ".join(f"{k}={v}" for k, v in sc["beats"].items() if k not in ("start", "end"))
            print(f"  {sc['id']:18} {sc['start']:>8.3f} → {sc['end']:>8.3f}  ({sc['dur']:.2f} s)  {beats}" + (f"  approx: {sc['approx']}" if sc["approx"] else ""))
        for n in report.get("notes") or []:
            print(f"NOTE {n}")
        if report["captions"]["dropped_words"]:
            print(f"  caption words with no spoken counterpart, dropped: {report['captions']['dropped_words']}")
    for p in problems:
        print("FAIL", p)
    print("TIMELINE " + ("FAIL" if problems else "PASS"))


def selftest():
    ok = True

    def project(td, script, board, target=8.0):
        root = Path(td) / "demo"; (root / "compositions" / "scenes").mkdir(parents=True)
        (root / "explainer.json").write_text(json.dumps({"name": "demo", "canvas": "1080x1920", "fps": 30, "target_s": target,
                                                         "caption": {"font": "default"}}))
        (root / "script.md").write_text(script); (root / "storyboard.json").write_text(json.dumps(board))
        (root / "index.html").write_text('<div id="root" data-composition-id="demo" data-duration="1">\n<!-- SLOTS:BEGIN -->\n<!-- SLOTS:END -->\n</div>')
        for sc in board["scenes"]:
            (root / "compositions" / "scenes" / f"{sc['id']}.html").write_text(
                f'<template><div id="root" data-composition-id="{sc["id"]}" data-duration="1"></div><script>\n'
                '/* BEATS:BEGIN */\n  var BEATS = {};\n  /* BEATS:END */\n</script></template>')
        return root

    def words(text, t0=0.5, step=0.35):
        return [[w, round(t0 + i * step, 3), round(t0 + i * step + step * 0.9, 3)] for i, w in enumerate(norm_tokens(text))]

    good = "## s01 Hook\nMost videos lose half their viewers in three seconds. Source: a 2024 platform report.\n## s02 Fix\nPut the payoff first, then explain it.\n"
    spoken = "most videos lose half their viewers in three seconds source a 2024 platform report put the payoff first then explain it"
    board = {"scenes": [{"id": "s01", "anchor": "most videos lose", "beats": {"hero": "half their viewers"},
                         "small_print": [{"text": "Source: a 2024 platform report.", "beat": "start"}]},
                        {"id": "s02", "anchor": "put the payoff", "beats": {"b1": "then explain"}, "last_text": "b1"}]}

    def case(name, script, board, spoken_words, want, target=8.0):
        nonlocal ok
        with tempfile.TemporaryDirectory() as td:
            root = project(td, script, board, target); tf = Path(td) / "t.json"; tf.write_text(json.dumps(spoken_words))
            problems, report = run(root, tf)
            passed, detail = want(problems, report, root)
            ok &= passed; print(f"selftest {name:18} {'PASS' if passed else 'FAIL'}  {detail}")

    def good_want(problems, report, root):
        s02 = (root / "compositions" / "scenes" / "s02.html").read_text(); host = (root / "index.html").read_text()
        caps = (root / "compositions" / "captions.html").read_text() if (root / "compositions" / "captions.html").exists() else ""
        cap_text = " ".join(re.findall(r'<div class="ln">([^<]*)</div>', caps))       # the blocks' lines, however they broke
        passed = (not problems and '"b1": 1.65' in s02 and host.count('data-composition-src="') == 3 and "Source: a 2024 platform report." in cap_text
                  and 'data-duration="3.665"' in s02 and report["scenes"][1]["start"] == 5.15)   # 21 words: last ends 7.815, + tail 1.0 = 8.815
        return passed, f"problems {problems} · s02 start {report['scenes'][1]['start'] if report else None} · slots {host.count('data-composition-src')}"

    case("pass-writes", good, board, words(spoken), good_want)
    late = json.loads(json.dumps(board)); late["scenes"][0]["beats"]["src"] = "platform report"; late["scenes"][0]["small_print"][0]["beat"] = "src"
    case("small-print-late", good, late, words(spoken), lambda p, r, root: (any("small print" in x for x in p) and not (root / "timeline.json").exists(), p))
    dup = "## s01 Hook\nMost videos lose half their viewers in the first three seconds.\n## s02 Fix\nPut the payoff first, then explain it.\n"
    dboard = {"scenes": [{"id": "s01", "anchor": "most videos"}, {"id": "s02", "anchor": "the"}]}
    case("duplicate-anchor", dup, dboard, words("most videos lose half their viewers in the first three seconds put the payoff first then explain it"),
         lambda p, r, root: (any("occurs 2 time(s)" in x for x in p), p))
    case("empty-timing", good, board, [], lambda p, r, root: (any("holds no words" in x for x in p), p))
    unsaid = good.replace("explain it.", "explain it on Netflix.")
    case("unsaid-word", unsaid, board, words(spoken), lambda p, r, root: (any("'Netflix.'" in x for x in p), p))
    case("runtime", good, board, words(spoken), lambda p, r, root: (any("outside ±15 %" in x for x in p), p), target=20.0)
    # the point-of-view run: two scenes on one angle pass, three do not, and a blank angle only notes
    two_same = json.loads(json.dumps(board))
    for sc in two_same["scenes"]:
        sc["angle"] = "side"
    case("angle-two-same", good, two_same, words(spoken),
         lambda p, r, root: (not any("three scenes running" in x for x in p) and not (r or {}).get("notes"),
                             f"problems {p} · notes {(r or {}).get('notes')}"))
    three = "## s01 A\nMost videos lose half their viewers in three seconds.\n## s02 B\nPut the payoff first.\n## s03 C\nThen explain it slowly.\n"
    tboard = {"scenes": [{"id": "s01", "anchor": "most videos", "angle": "side"},
                         {"id": "s02", "anchor": "put the payoff", "angle": "Side"},
                         {"id": "s03", "anchor": "then explain", "angle": " side ", "last_text": "start"}]}
    case("angle-three-same", three, tboard,
         words("most videos lose half their viewers in three seconds put the payoff first then explain it slowly"),
         lambda p, r, root: (any("three scenes running" in x and "s01" in x and "s03" in x for x in p), p), target=10.0)
    blank = json.loads(json.dumps(board))
    case("angle-blank-notes-only", good, blank, words(spoken),
         lambda p, r, root: (not p and any("angle is empty" in n for n in (r or {}).get("notes") or []),
                             f"problems {p} · notes {(r or {}).get('notes')}"))
    print("SELFTEST " + ("PASS" if ok else "FAIL"))
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project"); ap.add_argument("--timing"); ap.add_argument("--offsets", help="JSON {line: at-seconds} for a per-line word-times file")
    ap.add_argument("--vo", help="the voice file (default <project>/assets/audio/vo.wav)"); ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not a.project or not a.timing:
        ap.error("--project and --timing are required (or --selftest)")
    problems, report = run(a.project, a.timing, json.loads(a.offsets) if a.offsets else None, a.check, a.vo)
    print_report(report, problems)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
