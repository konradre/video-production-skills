#!/usr/bin/env python3
"""comfy_preflight.py — will this ComfyUI graph SAVE what the job is for? Checked before it is queued, fail closed.

ComfyUI accepts a graph whose only output is a preview (it writes to temp/, gone at the next restart) or a
VHS_VideoCombine with save_output false, runs it to the end, and reports success. This refuses both, and a graph with
no output of the kind the job needs (a video job that only saves stills), before any GPU time is spent.

  structure  API format (a UI export with "nodes"/"links" is refused: File > Export (API)); every node has a
             class_type and inputs; no link to a node id the graph does not have
  outputs    at least one PERSISTENT output node: not a preview/display class, not save_output false, fed by at
             least one link; of the --expect kind (with no --expect, a MiniMax H3 sampler in the graph means video)
  schema     with --host (live /object_info, COMFY_HOST by default) or --object-info <snapshot.json>: every class
             exists on that server, every required input is set, a combo value outside its list is a WARN; the
             server's own output_node flag decides what counts as an output

  python3 scripts/comfy_preflight.py <graph.json> [--expect video|image|audio|any] [--host URL | --object-info FILE] [--json]
  python3 scripts/comfy_preflight.py --selftest

Exit 0 PASS, 1 FAIL, 2 unusable (unreadable graph, schema asked for and unreachable). Sentinel PREFLIGHT PASS|FAIL.
A PASS says the graph will write a file. It does not say the file will look right: that is read off the frames.
Pattern: piorunkulaga174/dsh-comfyui scripts/comfyui_probe.py (preflight, output_kind), plus the save_output check.
"""
import argparse, json, os, sys, urllib.error, urllib.request

PREVIEW = ('preview', 'showtext', 'display', 'show_text')
SAVE = ('save', 'export', 'combine')
H3 = {'MiniMaxH3ImageToVideo', 'MiniMaxH3ReferenceToVideo'}


def kind_of(cls):
    low = cls.lower()
    if 'video' in low or cls == 'VHS_VideoCombine': return 'video'
    if 'audio' in low: return 'audio'
    if any(h in low for h in ('image', 'webp', 'gif', 'png', 'jpg')): return 'image'
    return 'any'


def is_link(v, ids):
    return isinstance(v, list) and len(v) == 2 and isinstance(v[0], (str, int)) and isinstance(v[1], int)


def preflight(graph, expect='any', schema=None):
    errors, warnings, outputs = [], [], []
    if not isinstance(graph, dict) or ('nodes' in graph and 'links' in graph):
        return {'ok': False, 'errors': [('', 'ui-format', 'a UI export, not the API format: File > Export (API)')], 'warnings': [], 'outputs': [], 'expect': expect}
    ids = {str(k) for k in graph}
    has_h3 = False
    for nid, node in graph.items():
        if not isinstance(node, dict) or not isinstance(node.get('class_type'), str) or not isinstance(node.get('inputs'), dict):
            errors.append((nid, 'bad-node', 'needs class_type and an inputs object')); continue
        cls, inp = node['class_type'], node['inputs']; has_h3 |= cls in H3
        for k, v in inp.items():
            if is_link(v, ids) and str(v[0]) not in ids: errors.append((nid, 'dangling-link', f'{k} → node {v[0]}, which the graph does not have'))
        sch = schema.get(cls) if schema is not None else None
        if schema is not None and not isinstance(sch, dict):
            errors.append((nid, 'unknown-class', f'{cls} is not on this server')); continue
        if sch:
            for k, spec in (sch.get('input', {}).get('required') or {}).items():
                if k not in inp: errors.append((nid, 'missing-input', f'{cls}.{k} is required')); continue
                if isinstance(spec, list) and spec and isinstance(spec[0], list) and isinstance(inp[k], str) and inp[k] not in spec[0]:
                    warnings.append((nid, 'combo-value', f'{cls}.{k}={inp[k]!r} is not in the server list'))
        low = cls.lower()
        if any(h in low for h in PREVIEW): continue
        flagged = sch.get('output_node') is True if sch else any(h in low for h in SAVE)
        if not flagged: continue
        if inp.get('save_output') is False:
            warnings.append((nid, 'not-persistent', f'{cls} has save_output false: it writes to temp/, not output/')); continue
        if not any(is_link(v, ids) for v in inp.values()):
            errors.append((nid, 'unfed-output', f'{cls} has no input link: it saves nothing')); continue
        outputs.append((nid, cls, kind_of(cls)))
    need = expect if expect != 'any' else ('video' if has_h3 else 'any')   # an explicit --expect wins; an H3 sampler sets the default
    if not outputs: errors.append(('', 'no-persistent-output', 'no save/export node that writes to output/ — the job would finish and leave nothing'))
    elif need != 'any' and not any(k == need for _, _, k in outputs):
        errors.append(('', 'wrong-output-kind', f'the job needs a {need} output; the graph saves only {sorted({k for _, _, k in outputs})}'))
    return {'ok': not errors, 'errors': errors, 'warnings': warnings, 'outputs': outputs, 'expect': need}


def fetch_schema(host):
    with urllib.request.urlopen(host.rstrip('/') + '/object_info', timeout=30) as r:
        return json.load(r)


def report(path, res):
    outs = ', '.join(f'node {n} {c} ({k})' for n, c, k in res['outputs']) or 'none'
    print(f'{path}: expects {res["expect"]} · persistent outputs: {outs}')
    for n, code, msg in res['errors']: print(f'  FAIL {code}{" node " + str(n) if n else ""}: {msg}')
    for n, code, msg in res['warnings']: print(f'  WARN {code} node {n}: {msg}')
    print(f"PREFLIGHT {'PASS' if res['ok'] else 'FAIL'} — {'the graph will write a file; whether it looks right is read off the frames' if res['ok'] else 'nothing queued'}")


def selftest():
    S = {'LoadImage': {'input': {'required': {'image': [['a.png', 'b.png']]}}, 'output_node': False},
         'KSampler': {'input': {'required': {'seed': ['INT'], 'sampler_name': [['euler', 'dpmpp_2m']], 'model': ['MODEL']}}, 'output_node': False},
         'VAEDecode': {'input': {'required': {'samples': ['LATENT']}}, 'output_node': False},
         'SaveImage': {'input': {'required': {'images': ['IMAGE'], 'filename_prefix': ['STRING']}}, 'output_node': True},
         'PreviewImage': {'input': {'required': {'images': ['IMAGE']}}, 'output_node': True},
         'VHS_VideoCombine': {'input': {'required': {'images': ['IMAGE'], 'save_output': ['BOOLEAN']}}, 'output_node': True}}
    base = lambda: {'1': {'class_type': 'LoadImage', 'inputs': {'image': 'a.png'}}, '2': {'class_type': 'KSampler', 'inputs': {'seed': 1, 'sampler_name': 'euler', 'model': ['1', 0]}},
                    '3': {'class_type': 'VAEDecode', 'inputs': {'samples': ['2', 0]}}}
    def g(**extra):
        x = base(); x.update(extra); return x
    save = {'9': {'class_type': 'SaveImage', 'inputs': {'images': ['3', 0], 'filename_prefix': 'x'}}}
    cases = [
        ('a SaveImage graph, image job', g(**save), 'image', S, True, None),
        ('the same with no schema (class-name rules)', g(**save), 'image', None, True, None),
        ('only a PreviewImage → FAIL no-persistent-output', g(**{'9': {'class_type': 'PreviewImage', 'inputs': {'images': ['3', 0]}}}), 'any', S, False, 'no-persistent-output'),
        ('VHS_VideoCombine save_output false → FAIL', g(**{'9': {'class_type': 'VHS_VideoCombine', 'inputs': {'images': ['3', 0], 'save_output': False}}}), 'video', S, False, 'no-persistent-output'),
        ('VHS_VideoCombine save_output true, video job → PASS', g(**{'9': {'class_type': 'VHS_VideoCombine', 'inputs': {'images': ['3', 0], 'save_output': True}}}), 'video', S, True, None),
        ('a video job that only saves stills → FAIL wrong-output-kind', g(**save), 'video', S, False, 'wrong-output-kind'),
        ('an H3 sampler forces video → FAIL on a stills-only graph', g(**save, **{'5': {'class_type': 'MiniMaxH3ReferenceToVideo', 'inputs': {}}}), 'any', None, False, 'wrong-output-kind'),
        ('an explicit --expect image wins over the H3 default → PASS on the stills graph', g(**save, **{'5': {'class_type': 'MiniMaxH3ReferenceToVideo', 'inputs': {}}}), 'image', None, True, None),
        ('a link to a missing node → FAIL dangling-link', g(**{'9': {'class_type': 'SaveImage', 'inputs': {'images': ['7', 0], 'filename_prefix': 'x'}}}), 'image', S, False, 'dangling-link'),
        ('a class the server lacks → FAIL unknown-class', g(**save, **{'4': {'class_type': 'SaveImageExtended', 'inputs': {}}}), 'image', S, False, 'unknown-class'),
        ('a required input missing → FAIL missing-input', g(**{'9': {'class_type': 'SaveImage', 'inputs': {'images': ['3', 0]}}}), 'image', S, False, 'missing-input'),
        ('a save node with no input link → FAIL unfed-output', g(**{'9': {'class_type': 'SaveImage', 'inputs': {'images': 'x', 'filename_prefix': 'x'}}}), 'image', None, False, 'unfed-output'),
        ('a UI export → FAIL ui-format', {'nodes': [], 'links': []}, 'any', None, False, 'ui-format'),
    ]
    ok = True
    for label, graph, exp, sch, want, code in cases:
        r = preflight(graph, exp, sch); got = [c for _, c, _ in r['errors']]
        good = r['ok'] == want and (code is None or code in got); ok &= good
        print(f"  {'ok ' if good else 'BAD'} {label}  (errors {got})")
    w = preflight(g(**save, **{'2': {'class_type': 'KSampler', 'inputs': {'seed': 1, 'sampler_name': 'eulerx', 'model': ['1', 0]}}}), 'image', S)
    good = w['ok'] and any(c == 'combo-value' for _, c, _ in w['warnings']); ok &= good
    print(f"  {'ok ' if good else 'BAD'} a combo value outside the server list → WARN, still PASS")
    print(f"SELFTEST {'PASS' if ok else 'FAIL'}"); return 0 if ok else 1


def main():
    if '--selftest' in sys.argv: sys.exit(selftest())
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('graph'); ap.add_argument('--expect', choices=['video', 'image', 'audio', 'any'], default='any')
    ap.add_argument('--host', nargs='?', const=os.environ.get('COMFY_HOST', 'http://127.0.0.1:8188'), help='read the live /object_info (COMFY_HOST when no URL is given)')
    ap.add_argument('--object-info', help='a saved /object_info snapshot instead of a live server'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    try: graph = json.load(open(a.graph))
    except (OSError, ValueError) as e: print(f'unreadable graph {a.graph}: {e}'); sys.exit(2)
    schema = None
    try:
        if a.object_info: schema = json.load(open(a.object_info))
        elif a.host: schema = fetch_schema(a.host)
    except (OSError, ValueError, urllib.error.URLError) as e: print(f'schema unreachable ({a.object_info or a.host}): {e} — nothing checked against the server'); sys.exit(2)
    res = preflight(graph, a.expect, schema)
    if a.json: print(json.dumps(res, indent=2)); sys.exit(0 if res['ok'] else 1)
    report(a.graph, res); sys.exit(0 if res['ok'] else 1)


if __name__ == '__main__':
    main()
