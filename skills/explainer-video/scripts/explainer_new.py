#!/usr/bin/env python3
"""explainer_new.py — scaffold a narrated explainer as a HyperFrames project that already obeys the contract.

  explainer_new.py --out <dir>/<name> --scenes s01-hook,s02-point,s03-close [--canvas 1080x1920] [--fps 30]
                   [--target 60] [--seed 7] [--bg "#0b0d12"] [--hf-version 0.8.18]
  explainer_new.py --out <dir>/<name> --add s04-extra                 # a scene added to an existing project
  explainer_new.py --selftest

Writes a THIN host index.html (one slot per scene, a captions slot, the voice as an <audio> at the root, a
near-empty root timeline) and one sub-composition per scene in compositions/scenes/<id>.html: everything inside
<template>, the root styled by #root, element ids prefixed with the scene id, one paused timeline registered under
the scene id, entrances that start above zero opacity, a BEATS object the timeline reads (explainer_timeline.py
writes it from the narration), a COPY object holding every on-screen string, a seeded PRNG, a sustained action and
an exit that reaches zero. Plus explainer.json (canvas, fps, target, caption style, the content box above the
caption band), script.md, storyboard.json, copy.md, facts.md, hyperframes.json and package.json. A scene id is its
file name, its composition id and its timeline key. The display face goes at assets/fonts/Display.ttf (captions are
measured with it) and the voice at assets/audio/vo.wav.
"""
import argparse, json, re, sys, tempfile
from pathlib import Path

GSAP = '<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>'

HOST = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=%W%, height=%H%" />
<title>%NAME%</title>
%GSAP%
<style>
  @font-face { font-family:'Display'; src:url('assets/fonts/Display.ttf') format('truetype'); }
  html, body { margin:0; background:%BG%; }
  #root { position:relative; width:%W%px; height:%H%px; overflow:hidden; background:%BG%; }
  [data-composition-id="%NAME%"] > div[data-composition-src] { position:absolute; inset:0; }
</style>
</head>
<body>
<div id="root" data-composition-id="%NAME%" data-start="0" data-width="%W%" data-height="%H%" data-duration="%TOTAL%" data-fps="%FPS%">
<!-- SLOTS:BEGIN -->
%SLOTS%
<!-- SLOTS:END -->
<audio id="%NAME%-vo" src="assets/audio/vo.wav" data-start="0" data-track-index="10" data-volume="1"></audio>
</div>
<script>
  window.__timelines["%NAME%"] = gsap.timeline({ paused: true });
</script>
</body>
</html>
"""

SCENE = """<!doctype html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body>
<template id="%SID%-template">
<style>
  @font-face { font-family:'Display'; src:url('assets/fonts/Display.ttf') format('truetype'); }
  #root { position:absolute; inset:0; overflow:hidden; color:#fff; font-family:'Display', sans-serif; }
  /* the hero reads by LUMINANCE against the ground: a light stroke or fill — a dark card on a dark ground reads empty */
  .hero { position:absolute; left:%HERO_L%px; top:%HERO_T%px; width:%HERO_W%px; height:%HERO_H%px; border-radius:%RADIUS%px;
          box-sizing:border-box; border:%STROKE%px solid #e8eeff; background:linear-gradient(160deg, #34436e, #161b2b);
          box-shadow:0 0 %GLOW%px %GLOW2%px rgba(110,150,255,.45); }
  .title { position:absolute; left:%PAD%px; right:%PAD%px; top:%TITLE_T%px; font-size:%TITLE_PX%px; font-weight:800;
           line-height:1.05; text-align:center; opacity:0; }
  .small { position:absolute; left:%PAD%px; right:%PAD%px; top:%SMALL_T%px; font-size:%SMALL_PX%px; line-height:1.2;
           text-align:center; color:#c9d2e6; opacity:0; }
  .dot { position:absolute; width:%DOT%px; height:%DOT%px; border-radius:50%; background:#8fb2ff; }
</style>
<div id="root" data-composition-id="%SID%" data-width="%W%" data-height="%H%" data-duration="%DUR%">
  <div id="%SID%-hero" class="hero"></div>
  <div id="%SID%-title" class="title"></div>
  <div id="%SID%-small" class="small"></div>
</div>
<script>
(function () {
  /* BEATS:BEGIN — written by explainer_timeline.py from the narration; never hand-edit */
  var BEATS = {"start": 0, "end": %DUR%};
  /* BEATS:END */
  var ID = '%SID%';
  var COPY = { title: 'Replace with the approved title', small: 'Source: replace with the approved source line' };
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  var rnd = mulberry32(%SEED%);
  function el(n) { return document.getElementById(ID + '-' + n); }
  el('title').textContent = COPY.title;
  el('small').textContent = COPY.small;
  var root = el('hero').parentNode, dots = [];
  for (var i = 0; i < 6; i++) { var d = document.createElement('div'); d.className = 'dot'; root.appendChild(d); dots.push(d); }
  var dur = BEATS.end - BEATS.start, exitAt = Math.max(0.1, dur - 0.3);
  var tl = gsap.timeline({ paused: true });
  // the hero enters on the scene's first frame, already visible
  tl.fromTo(el('hero'), { scale: 0.9, opacity: 0.3 }, { scale: 1, opacity: 1, duration: 0.45, ease: 'power3.out' }, 0);
  // small print on the FIRST beat: it holds >= 2.5 s at >= 50 % opacity before the exit (explainer_timeline.py checks)
  tl.fromTo(el('small'), { opacity: 0.3 }, { opacity: 0.85, duration: 0.3, ease: 'none', immediateRender: false }, 0.05);
  // the title lands on its beat — a beat named "title" in storyboard.json
  tl.fromTo(el('title'), { y: %RISE%, opacity: 0.3 }, { y: 0, opacity: 1, duration: 0.4, ease: 'power2.out', immediateRender: false },
            BEATS.title !== undefined ? BEATS.title : 0.15);
  // sustained action until the exit: the hero pushes 1.0 -> 1.05 and the dots keep orbiting it
  tl.to(el('hero'), { scale: 1.05, duration: Math.max(0.1, exitAt - 0.45), ease: 'none' }, 0.45);
  dots.forEach(function (d) {
    var st = { a: rnd() * Math.PI * 2 }, a0 = st.a;
    function draw() { d.style.left = (%CX% + Math.cos(st.a) * %ORBIT% - %DOT_HALF%) + 'px'; d.style.top = (%CY% + Math.sin(st.a) * %ORBIT% * 0.6 - %DOT_HALF%) + 'px'; }
    draw(); tl.to(st, { a: a0 + Math.PI * 1.2, duration: exitAt, ease: 'none', onUpdate: draw }, 0);
  });
  // the exit reaches zero before the cut: opacity 1 - (n/N)^1.5 over the last 0.3 s
  tl.to([el('hero'), el('title'), el('small')].concat(dots), { opacity: 0, duration: dur - exitAt, ease: function (t) { return Math.pow(t, 1.5); } }, exitAt);
  window.__timelines[ID] = tl;
})();
</script>
</template>
</body>
</html>
"""

CAPTIONS_EMPTY = """<!doctype html>
<html lang="en">
<head><meta charset="UTF-8" /></head>
<body>
<template id="captions-template">
<div id="root" data-composition-id="captions" data-width="%W%" data-height="%H%" data-duration="%TOTAL%"></div>
<script>
  window.__timelines['captions'] = gsap.timeline({ paused: true });
</script>
</template>
</body>
</html>
"""


def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace(f"%{k}%", str(v))
    left = re.findall(r"%[A-Z_0-9]+%", tpl)
    if left:
        raise SystemExit(f"template placeholders left unfilled: {sorted(set(left))}")
    return tpl


def layout(W, H):
    portrait = H >= W
    cap = {"font": "assets/fonts/Display.ttf", "size_frac": 0.028 if portrait else 0.045, "top_frac": 0.8 if portrait else 0.86,
           "width_frac": 0.86, "lines": 2, "weight": 800, "lead_s": 0.05, "hold_s": 0.5, "gap_hold_s": 0.6}
    content_h = cap["top_frac"] * H * 0.97
    hero_h = round(0.40 * content_h); hero_w = round(min(0.72 * W, hero_h * 1.3))
    return cap, {"HERO_W": hero_w, "HERO_H": hero_h, "HERO_L": round((W - hero_w) / 2), "HERO_T": round(0.30 * content_h),
                 "RADIUS": round(hero_h * 0.06), "GLOW": round(hero_h * 0.16), "GLOW2": round(hero_h * 0.02),
                 "STROKE": max(3, round(0.006 * min(W, H))),
                 "PAD": round(0.07 * W), "TITLE_T": round(0.09 * content_h), "TITLE_PX": round(0.055 * min(W, H) * (1.6 if portrait else 1.0)),
                 "SMALL_T": round(0.30 * content_h + hero_h + 0.06 * content_h), "SMALL_PX": round(0.024 * min(W, H) * (1.4 if portrait else 1.0)),
                 "DOT": round(0.018 * min(W, H)), "DOT_HALF": round(0.009 * min(W, H)), "CX": round(W / 2),
                 "CY": round(0.30 * content_h + hero_h / 2), "ORBIT": round(hero_w * 0.62), "RISE": round(0.02 * H)}, \
        [0, 0, 1, round(cap["top_frac"] * 0.97, 3)]


def scene_html(sid, W, H, dur, seed):
    _, geo, _ = layout(W, H)
    return fill(SCENE, SID=sid, W=W, H=H, DUR=f"{dur:.3f}", SEED=seed, **geo)


def slot(sid, start, dur):
    return (f'<div id="el-{sid}" data-composition-id="{sid}" data-composition-src="compositions/scenes/{sid}.html" '
            f'data-start="{start:.3f}" data-duration="{dur:.3f}" data-track-index="1"></div>')


def scaffold(out, scenes, W, H, fps, target, seed, bg, hfv):
    root = Path(out); name = root.name
    if (root / "index.html").exists():
        raise SystemExit(f"{root}/index.html exists — add a scene with --add, or scaffold a new project name")
    for d in ("compositions/scenes", "assets/fonts", "assets/audio", "renders"):
        (root / d).mkdir(parents=True, exist_ok=True)
    cap, _, box = layout(W, H); each = round(target / len(scenes), 3)
    slots = "\n".join(slot(s, i * each, each) for i, s in enumerate(scenes))
    slots += f'\n<div id="el-captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{target:.3f}" data-track-index="5"></div>'
    (root / "index.html").write_text(fill(HOST, NAME=name, W=W, H=H, FPS=fps, BG=bg, GSAP=GSAP, TOTAL=f"{target:.3f}", SLOTS=slots))
    (root / "compositions" / "captions.html").write_text(fill(CAPTIONS_EMPTY, W=W, H=H, TOTAL=f"{target:.3f}"))
    for i, s in enumerate(scenes):
        (root / "compositions" / "scenes" / f"{s}.html").write_text(scene_html(s, W, H, each, seed + i))
    (root / "explainer.json").write_text(json.dumps({
        "name": name, "canvas": f"{W}x{H}", "fps": fps, "target_s": target, "lang": "en",
        "lead_s": 0.25, "tail_s": 1.0, "exit_s": 0.3, "ending_fade_s": 0.5, "caption": cap, "content_box": box,
        "hf_version": hfv}, indent=1) + "\n")
    (root / "script.md").write_text(
        f"# {name} — narration, written the way it must READ on screen\n\n"
        "<!-- One `## <scene-id> <title>` per scene, in order; the lines under it are spoken in that scene.\n"
        "     One sentence per beat, 20 words at most. A pronunciation respelling lives only in the voice's input, never here. -->\n\n"
        + "".join(f"## {s} {s.split('-', 1)[-1].replace('-', ' ').title()}\nWrite the first sentence spoken in this scene.\n\n" for s in scenes))
    (root / "storyboard.json").write_text(json.dumps({"scenes": [
        {"id": s, "anchor": "", "beats": {"title": ""}, "hero": "", "size": "a third of the content box at least",
         "light": "", "action": "", "camera": "", "angle": "", "entities": [], "join_in": "", "join_out": "",
         "set_piece": "", "emphasis": "", "small_print": [], "last_text": ""} for s in scenes]}, indent=1) + "\n")
    (root / "copy.md").write_text("# Approved on-screen copy — one string per line, exactly as it may appear\n\n")
    (root / "facts.md").write_text("# Facts — every on-screen number, name, year and term, with its source URL and the date it was read\n\n")
    (root / "hyperframes.json").write_text(json.dumps({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                                                      "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
                                                      "media": {"autoProxy": True}}, indent=2) + "\n")
    hf = f"npx --yes hyperframes@{hfv}"
    (root / "package.json").write_text(json.dumps({"name": name, "private": True, "type": "module",
                                                  "scripts": {"dev": f"{hf} preview", "lint": f"{hf} lint", "check": f"{hf} check", "render": f"{hf} render"}}, indent=2) + "\n")
    return root


def add_scene(out, sid, seed):
    root = Path(out); cfg = json.loads((root / "explainer.json").read_text())
    W, H = (int(v) for v in cfg["canvas"].split("x")); p = root / "compositions" / "scenes" / f"{sid}.html"
    if p.exists():
        raise SystemExit(f"{p} exists")
    p.write_text(scene_html(sid, W, H, 3.0, seed))
    board = json.loads((root / "storyboard.json").read_text())
    board["scenes"].append({"id": sid, "anchor": "", "beats": {"title": ""}, "angle": "", "entities": [],
                            "small_print": [], "last_text": ""})
    (root / "storyboard.json").write_text(json.dumps(board, indent=1) + "\n")
    with open(root / "script.md", "a") as f:
        f.write(f"## {sid} {sid.split('-', 1)[-1].replace('-', ' ').title()}\nWrite the first sentence spoken in this scene.\n\n")
    return p


def selftest():
    ok = True
    with tempfile.TemporaryDirectory() as td:
        root = scaffold(Path(td) / "demo-explainer", ["s01-hook", "s02-point"], 1080, 1920, 30, 12.0, 7, "#0b0d12", "0.8.18")
        host = (root / "index.html").read_text(); s1 = (root / "compositions" / "scenes" / "s01-hook.html").read_text()
        checks = {
            "host slots": host.count('data-composition-src="') == 3,
            "host root id + duration": 'data-composition-id="demo-explainer"' in host and 'data-duration="12.000"' in host,
            "voice at the root with an id": '<audio id="demo-explainer-vo"' in host,
            "scene inside <template>": s1.index("<template") < s1.index("<style") < s1.index("data-composition-id") < s1.index("</template>"),
            "scene id = composition id = timeline key": 'data-composition-id="s01-hook"' in s1 and "var ID = 's01-hook'" in s1 and "window.__timelines[ID]" in s1,
            "BEATS markers": "/* BEATS:BEGIN" in s1 and "/* BEATS:END */" in s1,
            "COPY object": "var COPY = {" in s1,
            "no unfilled placeholders": not re.search(r"%[A-Z_]+%", host + s1),
            "storyboard rows": len(json.loads((root / "storyboard.json").read_text())["scenes"]) == 2,
        }
        add_scene(root, "s03-close", 9)
        checks["--add"] = (root / "compositions" / "scenes" / "s03-close.html").exists() and "## s03-close" in (root / "script.md").read_text()
        for k, v in checks.items():
            ok &= v; print(f"selftest {k:42} {'PASS' if v else 'FAIL'}")
    print("SELFTEST " + ("PASS" if ok else "FAIL"))
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out"); ap.add_argument("--scenes", default="s01-hook,s02-point,s03-close"); ap.add_argument("--add")
    ap.add_argument("--canvas", default="1080x1920"); ap.add_argument("--fps", type=int, default=30); ap.add_argument("--target", type=float, default=60.0)
    ap.add_argument("--seed", type=int, default=7); ap.add_argument("--bg", default="#0b0d12"); ap.add_argument("--hf-version", default="0.8.18")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not a.out:
        ap.error("--out is required (or --selftest)")
    if a.add:
        print("added", add_scene(a.out, a.add, a.seed)); return
    scenes = [s.strip() for s in a.scenes.split(",") if s.strip()]
    bad = [s for s in scenes if not re.fullmatch(r"[a-z][a-z0-9-]*", s)]
    if bad:
        ap.error(f"scene ids must be lowercase letters, digits and hyphens, starting with a letter: {bad}")
    W, H = (int(v) for v in a.canvas.lower().split("x"))
    root = scaffold(a.out, scenes, W, H, a.fps, a.target, a.seed, a.bg, a.hf_version)
    print(f"{root}: {len(scenes)} scenes, {W}x{H} @ {a.fps} fps, target {a.target:g} s — put the display face at assets/fonts/Display.ttf "
          f"and the voice at assets/audio/vo.wav, write script.md and storyboard.json, then run explainer_timeline.py")


if __name__ == "__main__":
    main()
