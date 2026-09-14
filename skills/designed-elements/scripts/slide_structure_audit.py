#!/usr/bin/env python3
"""Audit a designed composition's SOURCE for the four structures that read as a slide deck.

Every other instrument in this kit reads the delivered frames. This one reads index.html, because
the defect it looks for is structural: a composition can pass hero size, empty runs and still share
and still be a deck, and the frames cannot tell you why. The four rules come from an upstream kit
whose author restated his own anti-slide doctrine as greps after a model that had read the doctrine
produced a deck anyway (research/reference/bang-motion-analysis.md L1).

Each rule is a JUDGEMENT row, like the frame instrument's flags: it names a structure to go and
look at, not a verdict. Read the composition before acting on a FAIL.

It FAILS CLOSED on its own blind spot. Three of the four rules need the composition segmented into
scenes; when fewer than two are found they report INCONCLUSIVE and the exit code is 2, never a clean
0 — measured on three real upstream compositions, two of which segment to zero scenes because their
scenes are camera positions in one world rather than sections. A tool that cannot segment a
composition has not cleared it.

  R1 FADED-SCENES      three or more scenes and nothing ever moves the world or the camera
  R2 TEXT-STACK        one container holding three or more text elements at three or more sizes
  R3 ONE-MOTION        scale is the only geometric property the whole timeline animates
  R4 SAME-TRANSITION   every scene boundary animates the same property set (two cuts are enough:
                       the rule a film fails here is "at least two kinds of transition")

Usage:
  slide_structure_audit.py <project-dir|index.html> [--lead 0.6] [--json]
  slide_structure_audit.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

# Properties that move a thing through space. `scale` is deliberately listed and then singled out
# by R3: it is geometric, and on its own it is the Ken Burns push that reads as a deck.
GEOMETRIC = {
    "x", "y", "z", "xPercent", "yPercent", "scale", "scaleX", "scaleY",
    "rotation", "rotationX", "rotationY", "rotate", "skewX", "skewY", "transform", "top", "left",
}
# Selectors that name a camera rig / world container rather than one element inside a scene.
RIG = re.compile(r"(?:#|\.|\b)(world|rig|stage|camera|cam|scene-?root|viewport)\b", re.I)
TEXT_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "div", "figcaption", "li", "strong", "em"}


# --------------------------------------------------------------------------- HTML

class _Tree(HTMLParser):
    """A tolerant element tree. Only what the rules need: tag, attrs, text, children."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = {"tag": "#root", "attrs": {}, "text": "", "children": []}
        self._stack = [self.root]
        self.scripts: list[str] = []
        self.styles: list[str] = []
        self._capture: str | None = None

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "text": "", "children": []}
        self._stack[-1]["children"].append(node)
        if tag in ("script", "style"):
            self._capture = tag
        # void elements never get a close tag; keep the stack honest
        if tag not in ("br", "img", "hr", "meta", "link", "input", "source", "use", "path"):
            self._stack.append(node)

    def handle_endtag(self, tag):
        self._capture = None
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i]["tag"] == tag:
                del self._stack[i:]
                break

    def handle_data(self, data):
        if self._capture == "script":
            self.scripts.append(data)
        elif self._capture == "style":
            self.styles.append(data)
        elif data.strip():
            self._stack[-1]["text"] += data


def walk(node):
    yield node
    for c in node["children"]:
        yield from walk(c)


# --------------------------------------------------------------------------- CSS

def class_sizes(styles: str) -> dict[str, float]:
    """class name -> font-size in px, for the rules that compare text sizes."""
    out: dict[str, float] = {}
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", styles):
        m = re.search(r"font-size\s*:\s*([0-9.]+)\s*(px|rem|em)", body)
        if not m:
            continue
        size = float(m.group(1)) * (16.0 if m.group(2) in ("rem", "em") else 1.0)
        for one in sel.split(","):
            for cls in re.findall(r"\.([A-Za-z0-9_-]+)", one):
                out.setdefault(cls, size)
    return out


def element_size(node, sizes: dict[str, float]) -> float | None:
    style = node["attrs"].get("style", "")
    m = re.search(r"font-size\s*:\s*([0-9.]+)\s*(px|rem|em)", style)
    if m:
        return float(m.group(1)) * (16.0 if m.group(2) in ("rem", "em") else 1.0)
    for cls in node["attrs"].get("class", "").split():
        if cls in sizes:
            return sizes[cls]
    return None


# --------------------------------------------------------------------------- JS

def _args(src: str, open_paren: int) -> list[str]:
    """Split one call's argument list at top level. open_paren indexes the '('."""
    depth, start, out, i = 0, open_paren + 1, [], open_paren
    quote = None
    while i < len(src):
        ch = src[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'`":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth == 1 and ch == ")":
                out.append(src[start:i])
                return out
            depth -= 1
        elif ch == "," and depth == 1:
            out.append(src[start:i])
            start = i + 1
        i += 1
    return out


def tweens(script: str) -> list[dict]:
    """Every timeline call, as {target, props, at}. Tolerant by design: a call it cannot read
    contributes no properties, which can only make a rule quieter, never louder."""
    found = []
    for m in re.finditer(r"\b(?:tl|gsap|timeline)\s*\.\s*(to|from|fromTo|set)\s*\(", script):
        kind = m.group(1)
        args = _args(script, m.end() - 1)
        if len(args) < 2:
            continue
        target = args[0].strip()
        var_args = args[1:3] if kind == "fromTo" else args[1:2]
        props: set[str] = set()
        for a in var_args:
            props |= {k for k in re.findall(r"(?:^|[{,\s])([A-Za-z_][A-Za-z0-9_]*)\s*:", a)}
        at = None
        if kind != "set" and len(args) >= (4 if kind == "fromTo" else 3):
            tail = args[-1].strip()
            if re.fullmatch(r"[-+]?[0-9.]+", tail):
                at = float(tail)
        elif kind == "set" and len(args) >= 3:
            tail = args[-1].strip()
            if re.fullmatch(r"[-+]?[0-9.]+", tail):
                at = float(tail)
        props -= {"duration", "ease", "stagger", "delay", "repeat", "yoyo", "onUpdate",
                  "onComplete", "immediateRender", "transformOrigin", "overwrite", "paused"}
        found.append({"target": target, "props": props, "at": at, "kind": kind})
    return found


# --------------------------------------------------------------------------- rules

def audit(html: str, lead: float = 0.6) -> dict:
    tree = _Tree()
    tree.feed(html)
    script = "\n".join(tree.scripts)
    sizes = class_sizes("\n".join(tree.styles))

    scenes = [n for n in walk(tree.root)
              if "data-start" in n["attrs"] and "data-duration" in n["attrs"]]
    if not scenes:
        scenes = [n for n in walk(tree.root)
                  if "scene" in n["attrs"].get("class", "").split()
                  or "clip" in n["attrs"].get("class", "").split()]

    def fnum(node, key):
        try:
            return float(node["attrs"].get(key, ""))
        except ValueError:
            return None

    starts = sorted(s for s in (fnum(n, "data-start") for n in scenes) if s is not None)
    tws = tweens(script)
    rows = []

    # R1 — nothing ever moves the world
    rig_moves = [t for t in tws if RIG.search(t["target"]) and (t["props"] & GEOMETRIC)]
    segmented = len(scenes) >= 2
    rows.append({
        "rule": "R1 FADED-SCENES",
        "fail": segmented and len(scenes) >= 3 and not rig_moves,
        "inconclusive": not segmented,
        "detail": f"{len(scenes)} scenes, {len(rig_moves)} rig/world moves"
                  + ("" if rig_moves else " — a scene can only change by opacity"),
    })

    # R2 — a kicker/title/body stack in one container
    worst = (0, 0, None)
    for sc in (scenes or [tree.root]):
        for container in walk(sc):
            kids = [k for k in container["children"]
                    if k["tag"] in TEXT_TAGS and k["text"].strip()]
            vals = {element_size(k, sizes) for k in kids}
            vals.discard(None)
            if len(kids) >= 3 and len(vals) >= 3 and len(vals) > worst[1]:
                label = (sc["attrs"].get("data-composition-id") or sc["attrs"].get("id")
                         or sc["attrs"].get("data-start") or "the whole document")
                worst = (len(kids), len(vals), label)
    rows.append({
        "rule": "R2 TEXT-STACK",
        "fail": worst[1] >= 3,
        "detail": (f"one container in scene {worst[2]} stacks {worst[0]} text elements at "
                   f"{worst[1]} sizes") if worst[1] >= 3 else "no three-size text stack",
    })

    # R3 — scale is the only geometric language
    geo = set().union(*[t["props"] & GEOMETRIC for t in tws]) if tws else set()
    rows.append({
        "rule": "R3 ONE-MOTION",
        "fail": segmented and len(scenes) >= 3 and geo <= {"scale", "scaleX", "scaleY"} and bool(geo),
        "inconclusive": not segmented,
        "detail": "geometric properties animated: " + (", ".join(sorted(geo)) or "none"),
    })

    # R4 — every boundary animates the same set
    sigs = []
    for b in starts[1:]:
        s = frozenset().union(*[t["props"] for t in tws
                                if t["at"] is not None and b - lead <= t["at"] <= b + lead]) \
            if any(t["at"] is not None and b - lead <= t["at"] <= b + lead for t in tws) else frozenset()
        sigs.append(s)
    distinct = {s for s in sigs if s}
    rows.append({
        "rule": "R4 SAME-TRANSITION",
        "fail": segmented and len(sigs) >= 2 and len(distinct) == 1,
        "inconclusive": not segmented,
        "detail": f"{len(sigs)} boundaries, {len(distinct)} distinct property sets"
                  + (f" ({', '.join(sorted(next(iter(distinct))))})" if len(distinct) == 1 else ""),
    })

    return {"scenes": len(scenes), "tweens": len(tws), "rows": rows,
            "fails": [r["rule"] for r in rows if r["fail"]],
            "inconclusive": [r["rule"] for r in rows if r.get("inconclusive")]}


# --------------------------------------------------------------------------- selftest

CLEAN = """<style>.kick{font-size:34px}.title{font-size:120px}.body{font-size:44px}</style>
<div id="root"><section class="clip" data-start="0" data-duration="3"><h1 class="title">One</h1></section>
<section class="clip" data-start="3" data-duration="3"><h1 class="title">Two</h1></section>
<section class="clip" data-start="6" data-duration="3"><h1 class="title">Three</h1></section></div>
<script>
tl.to('#world', {scale: 1.2, x: -40, duration: 1}, 2.6);
tl.to('.title', {opacity: 0, yPercent: -60, duration: .4}, 2.8);
tl.fromTo('.title', {opacity: 0}, {opacity: 1, duration: .6}, 3.0);
tl.to('#world', {rotation: 4, duration: 1}, 5.6);
tl.to('.title', {opacity: 0, duration: .4}, 5.8);
</script>"""

DECK = """<style>.kick{font-size:34px}.title{font-size:120px}.body{font-size:44px}</style>
<div id="root">
<section class="clip" data-start="0" data-duration="3"><div class="col">
  <p class="kick">01 - FEATURES</p><h1 class="title">One</h1><p class="body">Supporting line here</p></div></section>
<section class="clip" data-start="3" data-duration="3"><div class="col">
  <p class="kick">02 - MORE</p><h1 class="title">Two</h1><p class="body">Another line here</p></div></section>
<section class="clip" data-start="6" data-duration="3"><div class="col">
  <p class="kick">03 - END</p><h1 class="title">Three</h1><p class="body">A third line here</p></div></section></div>
<script>
tl.to('.clip', {opacity: 0, duration: .5}, 2.8);
tl.to('.photo', {scale: 1.05, duration: 3}, 0);
tl.to('.clip', {opacity: 0, duration: .5}, 5.8);
tl.to('.clip', {opacity: 0, duration: .5}, 8.8);
</script>"""


def selftest() -> int:
    ok = True

    def check(name, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {name}: {got!r}" + ("" if good else f" != {want!r}"))

    print("clean composition (a rig that moves, one text level, varied transitions):")
    c = audit(CLEAN)
    check("scenes found", c["scenes"], 3)
    check("no failures", c["fails"], [])

    print("deck composition (sections faded, kicker/title/body, Ken Burns, one transition):")
    d = audit(DECK)
    check("scenes found", d["scenes"], 3)
    check("R1 fires", "R1 FADED-SCENES" in d["fails"], True)
    check("R2 fires", "R2 TEXT-STACK" in d["fails"], True)
    check("R3 fires", "R3 ONE-MOTION" in d["fails"], True)
    check("R4 fires", "R4 SAME-TRANSITION" in d["fails"], True)

    print("a two-scene deck does not trip the count-gated rules:")
    two = DECK.replace('<section class="clip" data-start="6" data-duration="3"><div class="col">\n'
                       '  <p class="kick">03 - END</p><h1 class="title">Three</h1>'
                       '<p class="body">A third line here</p></div></section>', "")
    t = audit(two)
    check("scenes found", t["scenes"], 2)
    check("R1 silent", "R1 FADED-SCENES" in t["fails"], False)
    check("R3 silent", "R3 ONE-MOTION" in t["fails"], False)
    check("R2 still fires", "R2 TEXT-STACK" in t["fails"], True)

    print("a composition with no scene markers is INCONCLUSIVE, never a clean pass:")
    n = audit("<div id=\"root\"><h1 style=\"font-size:120px\">Only</h1></div>"
              "<script>tl.to('.x', {opacity: 1, duration: 1}, 0);</script>")
    check("scenes found", n["scenes"], 0)
    check("no failures claimed", n["fails"], [])
    check("three rules inconclusive", len(n["inconclusive"]), 3)

    print("an unparsable timeline cannot silence a rule by accident:")
    e = audit(DECK.replace("<script>", "<script>tl.to(", 1))
    check("R1 still fires", "R1 FADED-SCENES" in e["fails"], True)

    print("PASS" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="a project dir or an index.html")
    ap.add_argument("--lead", type=float, default=0.6,
                    help="seconds either side of a scene boundary counted as its transition")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.target:
        ap.error("a project dir or an index.html is required (or --selftest)")

    p = Path(a.target)
    if p.is_dir():
        p = p / "index.html"
    if not p.is_file():
        print(f"ERROR no composition at {p}", file=sys.stderr)
        return 2

    res = audit(p.read_text(encoding="utf-8", errors="replace"), lead=a.lead)
    res["composition"] = str(p)
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"{p}  —  {res['scenes']} scenes, {res['tweens']} timeline calls")
        for r in res["rows"]:
            mark = "FAIL" if r["fail"] else ("????" if r.get("inconclusive") else "ok  ")
            print(f"  {mark} {r['rule']:<20} {r['detail']}")
        if res["inconclusive"]:
            print(f"\nINCONCLUSIVE — {res['scenes']} scene(s) segmented, so "
                  f"{', '.join(res['inconclusive'])} could not be evaluated. Scenes are read from "
                  "`data-start` + `data-duration` (HYPERFRAMES-CONTRACT § index.html), else a "
                  "`scene`/`clip` class. A composition this tool cannot segment is not a composition "
                  "it has cleared.")
        if res["fails"]:
            print("\nJudgement rows, not verdicts — read the composition before you change it.")
    if res["fails"]:
        return 1
    return 2 if res["inconclusive"] else 0


if __name__ == "__main__":
    sys.exit(main())
