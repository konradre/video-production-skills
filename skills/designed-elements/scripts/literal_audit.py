#!/usr/bin/env python3
"""literal_audit.py — the on-screen text of a designed composition, read from its SOURCE, checked against the
approved copy. A pixel QC samples frames; a string that shows for a few frames between samples (a counter's
intermediate, a label on a transition) is invisible to it and plain in the source.

  literal_audit.py <composition dir | file.html | file.js> … --approved <copy.txt|.md|.json> [--strict] [--json out.json]
  literal_audit.py --selftest

Reads, per composition: (1) HTML text nodes outside <script>, <style> and <title>; (2) string literals in a
text-rendering context — fillText / strokeText, .textContent / .innerText / .innerHTML =, a GSAP `text:` tween,
a data-text attribute, and every literal inside a `COPY = { … }` object (the convention: keep a composition's
display copy in one COPY object, so this audit is exact); (3) any other literal that reads as prose (a space and
a letter, no CSS or path shape) — listed as OTHER, because the audit cannot prove it never renders.
A literal is APPROVED when its normalised form (case-folded, whitespace collapsed, edge punctuation stripped)
occurs inside the normalised approved copy. Exit 1 when a (1)/(2) literal is unapproved; with --strict, OTHER
literals fail too. node_modules/, renders/, frames/ and assets/ are skipped. Labels assembled in code from
fragments (a counter's value, 'Page ' + n) are not seen — keep display copy whole in the HTML or the COPY object.
"""
import argparse, bisect, json, re, sys, tempfile
from html.parser import HTMLParser
from pathlib import Path

SKIP_DIRS = {"node_modules", "renders", "frames", "assets", ".git"}
CONTEXT_BEFORE = re.compile(r"""(?:(?:fillText|strokeText)\(\s*|\.(?:textContent|innerText|innerHTML)\s*=\s*|\btext\s*:\s*)$""")
COPY_OPEN = re.compile(r"""\bCOPY\s*=\s*\{""")
NOISE = re.compile(r"""^(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\(|[\w.$-]+\(.*\)$|[./~]|https?:|data:|[\w-]+\.(png|jpe?g|svg|webp|ttf|otf|woff2?|mp4|mp3|wav|json|js|css|html)$)""")
CSSLIKE = re.compile(r"""(:\s*[^\s].*;|\bpx\b|\d+px|\bem\b|\bvh\b|\bvw\b|gradient\(|cubic-bezier|translate|rotate[XYZ]?\(|scale\(|\$\{)""")


def norm(s):
    s = s.casefold().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip(" \t\"'`.,;:!?()[]{}")


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.skip = 0; self.out = []; self.scripts = []; self._buf = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "title"):
            self.skip += 1
            if tag == "script":
                self._buf = []
        for k, v in attrs:
            if k == "data-text" and v:
                self.out.append((self.getpos()[0], v, "text"))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "title") and self.skip:
            self.skip -= 1
            if tag == "script" and self._buf is not None:
                self.scripts.append(("".join(t for _, t in self._buf), self._buf[0][0] if self._buf else 0)); self._buf = None

    def handle_data(self, data):
        if self._buf is not None:
            self._buf.append((self.getpos()[0], data)); return
        if not self.skip and re.search(r"\w", data):
            self.out.append((self.getpos()[0], re.sub(r"\s+", " ", data).strip(), "text"))


def js_strings(src):
    """(start, end, text) of every string literal; comments skipped, so an apostrophe in a comment opens nothing."""
    out = []; i = 0; n = len(src)
    while i < n:
        if src.startswith("//", i):
            j = src.find("\n", i); i = n if j < 0 else j; continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        c = src[i]
        if c in "'\"`":
            j = i + 1
            while j < n and src[j] != c and (c == "`" or src[j] != "\n"):
                j += 2 if src[j] == "\\" else 1
            if j < n and src[j] == c:
                out.append((i + 1, j, src[i + 1:j]))
            i = j + 1; continue
        i += 1
    return out


def js_literals(src, line0):
    strings = js_strings(src); n = len(src); mask = bytearray(n)
    newlines = [k for k, ch in enumerate(src) if ch == "\n"]
    for a, b, _ in strings:
        mask[a - 1:b + 1] = b"\x01" * (b + 1 - (a - 1))
    copies = []
    for m in COPY_OPEN.finditer(src):
        depth = 0
        for k in range(m.end() - 1, n):
            if mask[k]:
                continue
            if src[k] == "{":
                depth += 1
            elif src[k] == "}":
                depth -= 1
                if depth == 0:
                    copies.append((m.end(), k)); break
    found = []
    for a, b, txt in strings:
        line = line0 + bisect.bisect_left(newlines, a)
        if any(s <= a < e for s, e in copies):
            if not src[b + 1:b + 8].lstrip().startswith(":"):          # a value, not a key
                found.append((line, txt, "context"))
            continue
        if CONTEXT_BEFORE.search(src[max(0, a - 41):a - 1]):
            found.append((line, re.sub(r"<[^>]+>", " ", txt), "context")); continue
        s = txt.strip()
        if " " in s and re.search(r"[A-Za-z]{2}", s) and not NOISE.match(s) and not CSSLIKE.search(s):
            found.append((line, s, "other"))
    return found


def audit_file(p):
    text = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix.lower() in (".html", ".htm"):
        parser = Text(); parser.feed(text); parser.close(); items = list(parser.out)
        for src, _ in parser.scripts:
            base = text.find(src[:80]) if src else -1
            items += js_literals(src, text.count("\n", 0, base) + 1 if base >= 0 else 1)
        return items
    return js_literals(text, 1)


def collect(paths):
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files += [f for f in sorted(p.rglob("*")) if f.suffix.lower() in (".html", ".htm", ".js")
                      and not SKIP_DIRS.intersection(f.relative_to(p).parts[:-1])]
        else:
            files.append(p)
    return files


def load_approved(path):
    p = Path(path); raw = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        data = json.loads(raw); flat = []

        def walk(v):
            if isinstance(v, str):
                flat.append(v)
            elif isinstance(v, dict):
                [walk(x) for x in v.values()]
            elif isinstance(v, list):
                [walk(x) for x in v]
        walk(data); raw = "\n".join(flat)
    return " \n ".join(norm(line) for line in raw.splitlines())


def run(paths, approved, strict):
    sources = [approved] if isinstance(approved, (str, Path)) else approved
    ok_text = " \n ".join(load_approved(p) for p in sources); rows = []; bad = 0
    for f in collect(paths):
        for line, lit, kind in audit_file(f):
            n = norm(lit)
            if not n or not re.search(r"\w", n):
                continue
            verdict = "approved" if n in ok_text else ("UNAPPROVED" if kind != "other" else "OTHER")
            rows.append({"file": str(f), "line": line, "kind": kind, "literal": lit, "verdict": verdict})
            if verdict == "UNAPPROVED" or (strict and verdict == "OTHER"):
                bad += 1
    for r in rows:
        if r["verdict"] != "approved":
            print(f"{r['verdict']:10} {r['file']}:{r['line']} [{r['kind']}] {r['literal']!r}")
    print(f"literals read: {len(rows)} · approved {sum(r['verdict'] == 'approved' for r in rows)} · "
          f"unapproved {sum(r['verdict'] == 'UNAPPROVED' for r in rows)} · other {sum(r['verdict'] == 'OTHER' for r in rows)}"
          f" → {'FAIL' if bad else 'PASS'}")
    return rows, bad


def selftest():
    html = """<!doctype html><html><head><title>Internal title</title><style>.a{color:#fff;font:700 96px 'Display'}</style></head>
<body><div id="root" data-composition-id="demo"><h1 id="t">One million tokens</h1><p data-text="Source: Anthropic, 2024"></p>
<div class="kicker">Retrieval first</div></div>
<script>
var COPY = { title: 'One million tokens', unit: "tokens", kicker: 'Retrieval first' };
var ease = 'power3.out', font = 'assets/fonts/Display.ttf', grad = 'linear-gradient(90deg, #000 0%, #fff 100%)';
document.getElementById('t').textContent = '37 ms';
ctx.fillText('1995', 20, 40);
var note = 'this sentence never renders';
</script></body></html>"""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "demo"; d.mkdir(); (d / "index.html").write_text(html)
        (Path(td) / "copy.txt").write_text("One million tokens\nSource: Anthropic, 2024\nRetrieval first\n")
        rows, bad = run([d], Path(td) / "copy.txt", False)
    unapproved = sorted(r["literal"] for r in rows if r["verdict"] == "UNAPPROVED")
    other = [r["literal"] for r in rows if r["verdict"] == "OTHER"]
    ok = unapproved == ["1995", "37 ms"] and other == ["this sentence never renders"] and bad == 2 \
        and not any("power3" in r["literal"] or "Display.ttf" in r["literal"] or "gradient" in r["literal"] for r in rows)
    print(f"selftest: unapproved {unapproved} (want ['1995', '37 ms']) · other {other} · {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*"); ap.add_argument("--strict", action="store_true")
    ap.add_argument("--approved", action="append", help="an approved copy file (.txt/.md/.json); repeat it — the copy and the narration script")
    ap.add_argument("--json"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not a.paths or not a.approved:
        ap.error("composition paths and --approved are required (or --selftest)")
    rows, bad = run(a.paths, a.approved, a.strict)
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
