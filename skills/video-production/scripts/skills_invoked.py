#!/usr/bin/env python3
"""skills_invoked.py — the "skills consulted" line MEASURED from the session transcript, never typed from memory.

Reads a Claude Code transcript (~/.claude/projects/<cwd-slug>/<session>.jsonl) and lists every skill invoked through
the Skill tool (assistant `tool_use` blocks named Skill, plus a user-typed `/skill` line), with timestamps, and every
compaction (a compaction drops the skill bodies from the context — "invoked earlier this session" is not "loaded").
Given the project's phase rules (`.claude/skill-gate.json`, written at intake from references/SKILL-GATE-TEMPLATE.json),
it replays the session's tool calls against them and reports the GAPS: phases whose actions ran without their skill.

  skills_invoked.py --transcript <jsonl|latest> [--since ISO] [--until ISO]           the invocation list
  skills_invoked.py --transcript … --phases <rules.json> --root <project> [--calls]   … plus the gap list per phase
  skills_invoked.py --transcript … [--phases … --root …] --line                       one line for the pause block
  skills_invoked.py --install-gate --root <project> [--registry <file>] [--genre ads]  write the project's rules file
  skills_invoked.py --selftest

`--transcript latest` picks the most recently written transcript under ~/.claude/projects — the live session in
the common case; pass the path when several sessions run. The rules engine here is the twin of the PreToolUse gate
hook (skill-gate.py): a call is a phase ACTION unless every segment only reads; data heredoc bodies are ignored and
interpreter heredoc bodies are the action; rules match in order, first match governs; an invocation satisfies a rule
only after the last compaction (scope "since-compaction", the default) or anywhere in the session (scope "session"),
and `max_age_min` demands a fresh one after N minutes. Change the twin and this file together.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import shlex
import shutil
import sys
import tempfile

HOME = os.path.expanduser("~")
PROJECTS_DIR = os.path.join(HOME, ".claude", "projects")
GATED_TOOLS = ("Bash", "Edit", "Write", "MultiEdit", "NotebookEdit")
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "SKILL-GATE-TEMPLATE.json")

# ----------------------------------------------------------------------------- transcript
SKILL_TOKEN = b'"Skill"'
SLASH_RE = re.compile(rb'"content":\s*"/')
COMPACT_TOKEN = b'isCompactSummary'
SLASH_NAME = re.compile(r"[A-Za-z0-9][\w.:-]*")
# Built-in slash commands are not skills; a typed line naming one is not an invocation.
BUILTIN_SLASH = {
    "compact", "clear", "model", "help", "mcp", "status", "config", "cost", "exit", "quit", "resume", "rename",
    "permissions", "hooks", "memory", "doctor", "init", "login", "logout", "bug", "terminal-setup", "vim", "add-dir",
    "agents", "skills", "plugins", "context", "usage", "rewind", "fast", "list-agents", "peers", "artifacts",
    "workflows", "export", "release-notes", "upgrade", "install", "ide", "statusline", "share", "output-style",
    "privacy-settings", "theme", "effort", "btw", "tasks", "stats", "insights", "chrome", "sandbox", "tf",
}


def parse_ts(ts):
    if not ts:
        return None
    try:
        return dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def prefilter(line):
    return SKILL_TOKEN in line or COMPACT_TOKEN in line or SLASH_RE.search(line) is not None


def parse_record(line, line_no):
    """One transcript line -> (invocations, compaction marker or None)."""
    inv, compact = [], None
    if not prefilter(line):
        return inv, compact
    try:
        r = json.loads(line)
    except Exception:
        return inv, compact
    if not isinstance(r, dict) or r.get("isSidechain"):
        return inv, compact
    ts = r.get("timestamp")
    if r.get("isCompactSummary"):
        compact = {"ts": ts, "line": line_no}
    m = r.get("message")
    t = r.get("type")
    if t == "assistant" and isinstance(m, dict) and isinstance(m.get("content"), list):
        for b in m["content"]:
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Skill":
                sk = (b.get("input") or {}).get("skill")
                if isinstance(sk, str) and sk.strip():
                    inv.append({"skill": sk.strip(), "ts": ts, "line": line_no, "source": "tool_use",
                                "args": ((b.get("input") or {}).get("args") or "")[:80]})
    elif t == "user" and isinstance(m, dict) and isinstance(m.get("content"), str):
        c = m["content"]
        if c.startswith("/"):
            head_ = c[1:].split()
            if head_ and SLASH_NAME.fullmatch(head_[0]) and head_[0].lower() not in BUILTIN_SLASH:
                inv.append({"skill": head_[0], "ts": ts, "line": line_no, "source": "slash", "args": ""})
    return inv, compact


def iter_events(transcript):
    """Yield ('skill', line, ts, inv) · ('compact', line, ts, marker) · ('call', line, ts, {tool, input, cwd})."""
    with open(transcript, "rb") as f:
        n = 0
        for line in f:
            n += 1
            if b'"tool_use"' not in line and not prefilter(line):
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if not isinstance(r, dict) or r.get("isSidechain"):
                continue
            inv, compact = parse_record(line, n)
            for i in inv:
                yield "skill", n, i["ts"], i
            if compact:
                yield "compact", n, compact["ts"], compact
            m = r.get("message")
            if r.get("type") == "assistant" and isinstance(m, dict) and isinstance(m.get("content"), list):
                for b in m["content"]:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in GATED_TOOLS:
                        yield "call", n, r.get("timestamp"), {"tool": b["name"], "input": b.get("input") or {}, "cwd": r.get("cwd")}


def latest_transcript(projects_dir=PROJECTS_DIR):
    cands = glob.glob(os.path.join(projects_dir, "*", "*.jsonl"))
    cands = [c for c in cands if os.path.isfile(c)]
    if not cands:
        return None
    return max(cands, key=os.path.getmtime)


# ----------------------------------------------------------------------------- command analysis (twin of the gate)
HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
INTERP_RE = re.compile(r"(?:^|\s)(?:python3?|py|bash|sh|zsh|ksh|node|deno|bun|perl|ruby|php)\s")
SEG_SPLIT_RE = re.compile(r"&&|\|\||[;|]")
READ_ONLY = {
    "cat", "ls", "head", "tail", "wc", "stat", "grep", "egrep", "fgrep", "rg", "ugrep", "find", "echo",
    "printf", "date", "df", "du", "pwd", "file", "ffprobe", "mediainfo", "sha256sum", "md5sum", "diff",
    "cmp", "less", "more", "tree", "which", "type", "test", "[", "[[", "true", "false", "readlink",
    "realpath", "basename", "dirname", "sort", "uniq", "cut", "tr", "awk", "jq", "xxd", "od", "strings",
    "sleep", "uptime", "free", "nproc", "id", "whoami", "env", "printenv", "hostname", "column", "nl",
    "tac", "rev", "seq", "identify", "exiftool", "sed", "pgrep", "ps", "lsof", "getconf", "locale",
}
TRIVIAL = {"cd", "pushd", "popd", "true", ":", "set", "umask", "export", "unset", "shift", "wait", "trap"}
WRAPPERS = {"sudo", "doas", "env", "nohup", "setsid", "command", "exec", "nice", "ionice", "stdbuf", "time"}
OPERATORS = {"&&", "||", ";", "|", "&", "\n", "(", ")"}
PATH_RE = re.compile(r"(?<![\w@:.])(?:~|\$HOME|\$\{HOME\})?/(?:[\w.\-+@%]+/)*[\w.\-+@%]*")


def heredoc_feeds_interpreter(line, opener_start):
    seg = SEG_SPLIT_RE.split(line[:opener_start])[-1]
    return INTERP_RE.search(" " + seg + " ") is not None


def strip_data_heredocs(cmd):
    out, i, lines = [], 0, cmd.split("\n")
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = HEREDOC_RE.search(line)
        if m:
            keep = heredoc_feeds_interpreter(line, m.start())
            term = m.group(2)
            i += 1
            while i < len(lines) and lines[i].strip() != term:
                if keep:
                    out.append(lines[i])
                i += 1
            if i < len(lines) and keep:
                out.append(lines[i])
        i += 1
    return "\n".join(out)


def segments(cmd):
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    segs, cur = [], []
    for t in lex:
        if t in OPERATORS or (t and set(t) <= {"&", "|", ";"}):
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    return segs


def head(seg):
    i = 0
    while i < len(seg):
        w = seg[i].split("/")[-1]
        if w in WRAPPERS:
            i += 1
            continue
        if w == "timeout":
            i += 2 if i + 2 < len(seg) else 1
            continue
        if "=" in w and not w.startswith("-") and i == 0:
            i += 1
            continue
        return w
    return ""


def writes_via_redirect(seg):
    for j, t in enumerate(seg):
        if t in (">", ">>", "&>", "&>>") or (t.startswith(">") and not t.startswith(">&")):
            target = seg[j + 1] if j + 1 < len(seg) else ""
            if target not in ("/dev/null",) and not target.startswith("&"):
                return True
    return False


def is_read_only(seg):
    h = head(seg)
    if h in TRIVIAL or h == "":
        return True
    if h not in READ_ONLY:
        return False
    if writes_via_redirect(seg):
        return False
    if h == "sed" and any(t == "-i" or t.startswith("-i") and len(t) <= 3 or t.startswith("--in-place") for t in seg):
        return False
    if h == "find" and ("-delete" in seg or "-exec" in seg or "-execdir" in seg):
        return False
    return True


def action_text(cmd):
    stripped = strip_data_heredocs(cmd)
    try:
        segs = [s for s in segments(stripped) if s]
    except ValueError:
        return stripped, False
    actions = [" ".join(s) for s in segs if not is_read_only(s)]
    return "\n".join(actions), (len(actions) == 0)


def extract_paths(cmd, cwd):
    out = []
    if cwd:
        out.append(cwd)
    for m in PATH_RE.finditer(cmd):
        p = m.group(0)
        if p.startswith("~"):
            p = HOME + p[1:]
        elif p.startswith("$HOME") or p.startswith("${HOME}"):
            p = HOME + p[p.index("/"):]
        if len(p) > 1:
            out.append(p.rstrip("/") or "/")
    return out


def call_targets(tool, tool_input, cwd):
    if tool == "Bash":
        return extract_paths(tool_input.get("command") or "", cwd)
    for k in ("file_path", "notebook_path", "path"):
        v = tool_input.get(k)
        if isinstance(v, str) and v:
            return [os.path.abspath(os.path.expanduser(v))]
    return []


def rel_under(root, path):
    ap = os.path.abspath(path)
    if ap == root:
        return "."
    if ap.startswith(root + os.sep):
        return os.path.relpath(ap, root)
    return None


# ----------------------------------------------------------------------------- rules (twin of the gate)
def rule_matches(rule, tool, action, rel_paths):
    when = rule.get("when") or {}
    tools = when.get("tool") or list(GATED_TOOLS)
    if tool not in tools:
        return False
    preds = []
    if "command" in when and tool == "Bash":
        try:
            preds.append(bool(re.search(when["command"], action, re.M)))
        except re.error:
            preds.append(False)
    if "path" in when:
        try:
            preds.append(any(re.search(when["path"], rp) for rp in rel_paths))
        except re.error:
            preds.append(False)
    if not preds:
        return "command" not in when and "path" not in when
    return any(preds)


def compaction_cut(compactions, before_line=None):
    cut = 0
    for c in compactions or []:
        if before_line is not None and c["line"] >= before_line:
            break
        cut = c["line"]
    return cut


def satisfied(rule, doc, invocations, now, before_line, compactions):
    need = rule.get("require_any") or []
    max_age = rule.get("max_age_min", doc.get("max_age_min"))
    scope = rule.get("scope", doc.get("scope", "since-compaction"))
    cut = compaction_cut(compactions, before_line) if scope == "since-compaction" else 0
    latest, seen, older = None, [], None
    for inv in invocations:
        if before_line is not None and inv["line"] >= before_line:
            continue
        if inv["skill"] not in need:
            continue
        if inv["line"] <= cut:
            older = inv
            continue
        seen.append(inv)
        t = parse_ts(inv.get("ts"))
        if t is not None and (latest is None or t > latest):
            latest = t
    if not seen:
        return False, older, ("before a compaction" if older else "never")
    if max_age and latest is not None and now is not None and now - latest > max_age * 60:
        return False, seen[-1], f"older than {max_age} min"
    return True, seen[-1], ""


def evaluate(call, root, doc, invocations, compactions, line, now):
    """One tool call against the project's rules -> {decision: read|noproj|allow|deny, rule, why}."""
    tool, ti, cwd = call["tool"], call["input"], call.get("cwd") or ""
    targets = call_targets(tool, ti, cwd)
    rel_paths = [rp for rp in (rel_under(root, t) for t in targets) if rp is not None]
    if not rel_paths:
        return {"decision": "noproj"}
    action = ""
    if tool == "Bash":
        action, all_read = action_text(ti.get("command") or "")
        if all_read:
            return {"decision": "read"}
    for rule in doc.get("rules") or []:
        if not rule_matches(rule, tool, action, rel_paths):
            continue
        if rule.get("allow"):
            return {"decision": "allow", "rule": rule.get("id")}
        ok, last, why = satisfied(rule, doc, invocations, now, line, compactions)
        return {"decision": "allow" if ok else "deny", "rule": rule.get("id"), "require_any": rule.get("require_any") or [],
                "why": why, "by": last["skill"] if (ok and last) else None}
    return {"decision": "allow", "rule": None}


# ----------------------------------------------------------------------------- the report
def scan(transcript, since=None, until=None, rules=None, root=None):
    since_t, until_t = parse_ts(since), parse_ts(until)
    doc = None
    if rules:
        with open(rules, encoding="utf-8") as f:
            doc = json.load(f)
        root = os.path.abspath(os.path.expanduser(root)).rstrip("/")
    invocations, compactions, calls = [], [], []
    for kind, n, ts, obj in iter_events(transcript):
        t = parse_ts(ts)
        in_window = (since_t is None or (t or 0) >= since_t) and (until_t is None or (t or 0) <= until_t)
        if kind == "skill":
            invocations.append(obj)
        elif kind == "compact":
            compactions.append(obj)
        elif kind == "call" and doc is not None and in_window:
            d = evaluate(obj, root, doc, invocations, compactions, n, t)
            if d["decision"] in ("allow", "deny"):
                calls.append({"line": n, "ts": ts, "tool": obj["tool"], **d,
                              "what": ((obj["input"].get("command") or obj["input"].get("file_path") or obj["input"].get("notebook_path") or "").replace("\n", " ")[:100])})
    win_inv = [i for i in invocations if (since_t is None or (parse_ts(i["ts"]) or 0) >= since_t) and (until_t is None or (parse_ts(i["ts"]) or 0) <= until_t)]
    win_comp = [c for c in compactions if (since_t is None or (parse_ts(c["ts"]) or 0) >= since_t) and (until_t is None or (parse_ts(c["ts"]) or 0) <= until_t)]
    gaps = {}
    for c in calls:
        if c["decision"] != "deny":
            continue
        g = gaps.setdefault(c["rule"], {"rule": c["rule"], "require_any": c["require_any"], "calls": 0, "first": c["ts"], "last": c["ts"]})
        g["calls"] += 1
        g["last"] = c["ts"]
    return {"transcript": transcript, "invocations": win_inv, "compactions": win_comp, "calls": calls,
            "gaps": sorted(gaps.values(), key=lambda g: -g["calls"]),
            "allowed": sum(1 for c in calls if c["decision"] == "allow")}


def hhmm(ts):
    t = parse_ts(ts)
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%m-%d %H:%MZ") if t else "?"


def one_line(rep):
    inv = rep["invocations"]
    comp = rep["compactions"]
    cut = comp[-1]["line"] if comp else 0
    since_last = [i for i in inv if i["line"] > cut]
    parts = [f"measured from {os.path.basename(rep['transcript'])} — {len(inv)} Skill call(s)"]
    parts.append("invoked: " + (", ".join(f"{i['skill']} {hhmm(i['ts'])}" for i in inv) if inv else "none"))
    if comp:
        parts.append(f"since the last compaction ({hhmm(comp[-1]['ts'])}): " + (", ".join(i["skill"] for i in since_last) if since_last else "NONE — re-invoke before the next phase action"))
    if rep.get("gaps"):
        parts.append("gaps (phase actions without their skill): " + "; ".join(f"{g['rule']} ×{g['calls']} ({'|'.join(g['require_any'])})" for g in rep["gaps"]))
    elif "calls" in rep and rep["calls"]:
        parts.append(f"gaps: none ({rep['allowed']} phase actions, every one after its skill)")
    return " · ".join(parts)


def print_report(rep, show_calls=False):
    print(f"transcript: {rep['transcript']}")
    print(f"Skill invocations: {len(rep['invocations'])}   compactions: {len(rep['compactions'])}")
    for i in rep["invocations"]:
        print(f"  {hhmm(i['ts'])}  L{i['line']:<6d} {i['skill']:26s} {i['source']:8s} {i.get('args','')}")
    for c in rep["compactions"]:
        print(f"  {hhmm(c['ts'])}  L{c['line']:<6d} — compaction —")
    if rep["calls"]:
        print(f"\nphase actions: {len(rep['calls'])}  allowed: {rep['allowed']}  gaps: {sum(g['calls'] for g in rep['gaps'])}")
        for g in rep["gaps"]:
            print(f"  GAP  {g['rule']:12s} ×{g['calls']:<4d} needs Skill({' | '.join(g['require_any'])})   {hhmm(g['first'])} → {hhmm(g['last'])}")
        if show_calls:
            for c in rep["calls"]:
                print(f"  {hhmm(c['ts'])}  L{c['line']:<6d} {c['decision']:5s} {c['tool']:6s} {c.get('rule') or '':12s} {c['what']}")
    print("\n" + one_line(rep))


def install_gate(root, registry=None, genre=None, template=TEMPLATE):
    root = os.path.abspath(os.path.expanduser(root)).rstrip("/")
    with open(template, encoding="utf-8") as f:
        doc = json.load(f)
    doc["project"] = os.path.basename(root)
    if genre:
        doc["genre"] = genre
    doc.pop("_about", None)
    if registry:
        reg_path = os.path.expanduser(registry)
        reg = {}
        if os.path.exists(reg_path):
            with open(reg_path, encoding="utf-8") as f:
                reg = json.load(f) or {}
        rules_dir = os.path.join(os.path.dirname(reg_path), "projects")
        os.makedirs(rules_dir, exist_ok=True)
        out = os.path.join(rules_dir, doc["project"] + ".json")
        if os.path.exists(out):
            shutil.copy(out, out + ".bak-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-pre-install-gate")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
            f.write("\n")
        reg[root] = os.path.relpath(out, os.path.dirname(reg_path))
        with open(reg_path, "w", encoding="utf-8") as f:
            json.dump(reg, f, indent=1, ensure_ascii=False)
            f.write("\n")
        return out
    out = os.path.join(root, ".claude", "skill-gate.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        shutil.copy(out, out + ".bak-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-pre-install-gate")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return out


# ----------------------------------------------------------------------------- selftest
def _selftest():
    tmp = tempfile.mkdtemp(prefix="skills-invoked-selftest-")
    root = os.path.join(tmp, "proj")
    os.makedirs(os.path.join(root, "edit"))
    rules = os.path.join(tmp, "rules.json")
    with open(rules, "w") as f:
        json.dump({"project": "t", "rules": [
            {"id": "finish", "when": {"tool": ["Bash", "Edit", "Write"], "command": r"ffmpeg|build\.py", "path": r"build\.py$"}, "require_any": ["video-finish-qc", "video-finish"]},
            {"id": "edl", "when": {"tool": ["Edit", "Write"], "path": r"EDL.*\.json$"}, "require_any": ["video-edit-edl"]},
            {"id": "any", "when": {"path": ".*", "command": ".*"}, "require_any": ["video-production"]},
        ]}, f)

    def rec(kind, ts, **kw):
        base = {"type": kind, "timestamp": ts, "isSidechain": False, "cwd": root}
        base.update(kw)
        return json.dumps(base)

    def skill(name, ts):
        return rec("assistant", ts, message={"role": "assistant", "content": [{"type": "tool_use", "id": "s", "name": "Skill", "input": {"skill": name, "args": "x"}}]})

    def call(tool, inp, ts):
        return rec("assistant", ts, message={"role": "assistant", "content": [{"type": "tool_use", "id": "c", "name": tool, "input": inp}]})

    t = os.path.join(tmp, "t.jsonl")
    with open(t, "w") as f:
        f.write(skill("video-production", "2026-09-16T00:00:00Z") + "\n")
        f.write(call("Bash", {"command": f"cd {root} && mkdir -p review"}, "2026-09-16T00:00:10Z") + "\n")          # allow any
        f.write(call("Bash", {"command": f"cd {root} && ffmpeg -i a o"}, "2026-09-16T00:00:20Z") + "\n")            # deny finish
        f.write(call("Bash", {"command": f"cat {root}/tools/build.py"}, "2026-09-16T00:00:25Z") + "\n")             # read
        f.write(skill("video-finish-qc", "2026-09-16T00:01:00Z") + "\n")
        f.write(call("Bash", {"command": f"cd {root} && ffmpeg -i a o"}, "2026-09-16T00:01:20Z") + "\n")            # allow finish
        f.write(rec("user", "2026-09-16T00:02:00Z", isCompactSummary=True, message={"role": "user", "content": "s"}) + "\n")
        f.write(call("Bash", {"command": f"cd {root} && ffmpeg -i a o"}, "2026-09-16T00:02:20Z") + "\n")            # deny finish (compacted)
        f.write(call("Edit", {"file_path": os.path.join(root, "edit", "X-EDL.json")}, "2026-09-16T00:02:30Z") + "\n")  # deny edl
        f.write(rec("user", "2026-09-16T00:02:40Z", message={"role": "user", "content": "/video-edit-edl cut it"}) + "\n")
        f.write(call("Edit", {"file_path": os.path.join(root, "edit", "X-EDL.json")}, "2026-09-16T00:02:50Z") + "\n")  # allow edl (slash)
        f.write(call("Edit", {"file_path": os.path.join(tmp, "elsewhere.md")}, "2026-09-16T00:02:55Z") + "\n")      # noproj
        f.write(rec("assistant", "2026-09-16T00:03:00Z", isSidechain=True, message={"role": "assistant", "content": [{"type": "tool_use", "id": "z", "name": "Skill", "input": {"skill": "sidechain-skip"}}]}) + "\n")
    rep = scan(t, rules=rules, root=root)
    names = [i["skill"] for i in rep["invocations"]]
    decisions = [(c["decision"], c["rule"]) for c in rep["calls"]]
    checks = [
        ("invocations in order, slash included, sidechain excluded", names == ["video-production", "video-finish-qc", "video-edit-edl"]),
        ("one compaction seen", len(rep["compactions"]) == 1),
        ("decisions: allow any · deny finish · allow finish · deny finish (post-compaction) · deny edl · allow edl",
         decisions == [("allow", "any"), ("deny", "finish"), ("allow", "finish"), ("deny", "finish"), ("deny", "edl"), ("allow", "edl")]),
        ("gap list: finish ×2, edl ×1", [(g["rule"], g["calls"]) for g in rep["gaps"]] == [("finish", 2), ("edl", 1)]),
        ("one-line form names the gaps and the post-compaction set", "gaps (phase actions without their skill): finish ×2" in one_line(rep) and "since the last compaction" in one_line(rep) and "video-edit-edl" in one_line(rep)),
        ("window filter", len(scan(t, since="2026-09-16T00:01:00Z", rules=rules, root=root)["invocations"]) == 2),
    ]
    # install-gate: template -> project file; registry form
    tpl = os.path.join(tmp, "tpl.json")
    with open(tpl, "w") as f:
        json.dump({"project": "<project>", "_about": "x", "rules": [{"id": "any", "when": {"path": ".*"}, "require_any": ["video-production"]}]}, f)
    out = install_gate(root, template=tpl)
    with open(out) as f:
        got = json.load(f)
    checks.append(("install-gate writes <root>/.claude/skill-gate.json with the project name, _about dropped", out.endswith(os.path.join(".claude", "skill-gate.json")) and got["project"] == "proj" and "_about" not in got))
    reg = os.path.join(tmp, "gate", "projects.json")
    os.makedirs(os.path.dirname(reg))
    out2 = install_gate(root, registry=reg, template=tpl, genre="ads")
    with open(reg) as f:
        r = json.load(f)
    checks.append(("install-gate --registry registers the root -> projects/<name>.json", r.get(root) == os.path.join("projects", "proj.json") and os.path.exists(out2) and json.load(open(out2))["genre"] == "ads"))
    bad = 0
    for label, ok in checks:
        bad += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    print(f"\n{len(checks) - bad}/{len(checks)} passed")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--transcript", help="path, or 'latest' (newest transcript under ~/.claude/projects)")
    ap.add_argument("--since"); ap.add_argument("--until")
    ap.add_argument("--phases", help="the project's rules file (.claude/skill-gate.json)")
    ap.add_argument("--root", help="the project root the rules apply to")
    ap.add_argument("--calls", action="store_true", help="list every phase action with its decision")
    ap.add_argument("--line", action="store_true", help="print only the one-line form for the pause block")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--install-gate", action="store_true", help="write <root>/.claude/skill-gate.json from the genre template")
    ap.add_argument("--registry", help="with --install-gate: register the root in this projects.json instead of writing into the tree")
    ap.add_argument("--genre")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    if a.install_gate:
        if not a.root:
            ap.error("--install-gate needs --root")
        out = install_gate(a.root, a.registry, a.genre)
        print(f"wrote {out}")
        return
    if not a.transcript:
        ap.error("--transcript <path|latest> is required")
    t = latest_transcript() if a.transcript == "latest" else os.path.expanduser(a.transcript)
    if not t or not os.path.isfile(t):
        print(f"no transcript at {a.transcript}", file=sys.stderr)
        sys.exit(2)
    if a.transcript == "latest":
        print(f"transcript: {t}", file=sys.stderr)
    if a.phases and not a.root:
        ap.error("--phases needs --root")
    rep = scan(t, a.since, a.until, a.phases, a.root)
    if a.json:
        print(json.dumps(rep, indent=1, ensure_ascii=False))
    elif a.line:
        print(one_line(rep))
    else:
        print_report(rep, a.calls)


if __name__ == "__main__":
    main()
