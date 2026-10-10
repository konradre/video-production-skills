#!/usr/bin/env python3
"""compare_versions.py — version N against N−1 on ONE offline page, played in sync, for the operator's review of a round.

Two delivered files side by side, stacked, or as a wipe. With both EDLs the two are lined up by EVENT, never by clock: a
moment of the new version shows the same take time of the same event in the old one, so a re-timed shot, an insert or a
trim never slides the comparison onto another beat. Per event of the new version:
  same      the same event, take and window ("moved" when only its place on the timeline changed)
  retimed   the same event and take, another window — the old version HOLDS its first or last frame where it lacks the take time
  replaced  the same event id on another take — the old event is stretched over the new one's span
  inserted  an id the old version lacks — the old version holds where it stood
Every old event the new one lacks is listed as removed, with a button that plays it alone. Without EDLs the two play on
one clock. With --round, the round's notes for this spot (and every "*" note) are marks at their anchors — times in the version the client saw,
passed as --a — and a spot note rings its spot on the old picture.
The page is the operator's review, never the client's: one HTML file that names the two videos by relative path (keep it
in the project tree), fetches nothing, and never overwrites. `qc_deliverable.py --prev` is its measured twin.
Pattern: Barty-Bart/motion-graphics templates/compare.html (side by side, stacked or a wipe, one master clock).

  compare_versions.py --root <project> --a deliver/<SPOT>-v8.mp4 --b deliver/<SPOT>-v9.mp4 [--edl-a edit/<SPOT>-EDL-v8.json
                      --edl-b edit/<SPOT>-EDL-v9.json] [--round prompts/CLIENT-ROUND-<date>.json] [--spot S01] --out review/<SPOT>-v8-v9.html
  compare_versions.py --selftest
Sentinel: COMPARE-END ok.
"""
import argparse, html, json, os, shutil, subprocess, sys, tempfile, urllib.parse

EPS = 1e-4


def probe(path):
    """(duration s, width, height, fps) of a video file"""
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate:format=duration',
                        '-of', 'json', path], capture_output=True, text=True)
    j = json.loads(r.stdout or '{}'); s = (j.get('streams') or [{}])[0]
    num, _, den = (s.get('r_frame_rate') or '24/1').partition('/')
    fps = float(num) / float(den) if den and float(den) else 24.0
    return float((j.get('format') or {}).get('duration') or 0), int(s.get('width') or 1080), int(s.get('height') or 1920), fps


def events(E):
    return [{'id': x['id'], 'take': x.get('take'), 'in': float(x['in']), 'out': float(x['out']), 't0': float(x['tl'][0]), 't1': float(x['tl'][1])}
            for x in E.get('events', [])]


def segments(A, B, fps_a):
    """B time → A time, piecewise linear: [b0, b1, a0, a1, kind, event id]; a0 == a1 means the old version HOLDS that frame.
    Returns (segments, status per new event, removed old events)."""
    half = 0.5 / fps_a; by = {e['id']: e for e in A}; seg, status, hold = [], {}, 0.0
    for e in B:
        o = by.get(e['id'])
        if o is None:
            seg.append([e['t0'], e['t1'], hold, hold, 'inserted', e['id']]); status[e['id']] = 'inserted'; continue
        last = o['t1'] - half                                   # the old event's last frame (tl is [start, end))
        if o['take'] != e['take']:
            seg.append([e['t0'], e['t1'], o['t0'], last, 'replaced', e['id']]); status[e['id']] = 'replaced'; hold = last; continue
        at = lambda s: min(o['t0'] + (s - o['in']), last)       # a take time → the old timeline, never past the event's last frame
        lo, hi = max(e['in'], o['in']), min(e['out'], o['out'])
        same = abs(e['in'] - o['in']) < EPS and abs(e['out'] - o['out']) < EPS
        if hi <= lo + EPS:                                      # the two windows share no take time
            seg.append([e['t0'], e['t1'], at(o['in']), at(o['in']), 'retimed', e['id']])
        else:
            b_lo, b_hi = e['t0'] + (lo - e['in']), e['t0'] + (hi - e['in'])
            if b_lo > e['t0'] + EPS: seg.append([e['t0'], b_lo, at(lo), at(lo), 'retimed', e['id']])      # take time the old cut lacked
            seg.append([b_lo, b_hi, o['t0'] + (lo - o['in']), o['t0'] + (hi - o['in']), 'same' if same else 'retimed', e['id']])
            if e['t1'] > b_hi + EPS: seg.append([b_hi, e['t1'], last, last, 'retimed', e['id']])
        status[e['id']] = ('moved' if abs(e['t0'] - o['t0']) > EPS else 'same') if same else 'retimed'
        hold = last
    kept = {e['id'] for e in B}
    return seg, status, [o for o in A if o['id'] not in kept]


def a_to_b(t, A, B, fps_b):
    """an old-version time → the new version's time of the same take frame; None when its event was removed"""
    o = next((x for x in A if x['t0'] - EPS <= t < x['t1']), A[-1] if A and t >= A[-1]['t1'] else None)
    e = next((x for x in B if o and x['id'] == o['id']), None)
    if e is None: return None
    if e['take'] != o['take']: return e['t0'] + (t - o['t0']) / max(o['t1'] - o['t0'], EPS) * (e['t1'] - e['t0'])
    return min(max(e['t0'] + (o['in'] + (t - o['t0']) - e['in']), e['t0']), e['t1'] - 0.5 / fps_b)


def build(root, va, vb, edl_a, edl_b, rnd, spot, out):
    os.chdir(root)
    for p in (va, vb):
        if not os.path.isfile(p): sys.exit(f'no video at {p}')
    if os.path.exists(out): sys.exit(f'refusing to overwrite {out}')
    dur_a, w_a, h_a, fps_a = probe(va); dur_b, w_b, h_b, fps_b = probe(vb)
    if edl_a:
        EA, EB = json.load(open(edl_a, encoding='utf-8')), json.load(open(edl_b, encoding='utf-8'))
        A, B = events(EA), events(EB); fps_a, fps_b = float(EA.get('fps', fps_a)), float(EB.get('fps', fps_b))
        seg, status, removed = segments(A, B, fps_a); mode = 'event'; spot = spot or EB.get('spot')
        to_b = lambda t: a_to_b(t, A, B, fps_b)
    else:
        A, B = [], []; seg, status, removed = [[0.0, dur_b, 0.0, dur_b, 'clock', '']], {}, []; mode = 'clock'
        to_b = lambda t: min(t, dur_b)
    notes = []
    if rnd:
        for it in json.load(open(rnd, encoding='utf-8')).get('items', []):
            if it.get('class') == 'CHAT' or (spot and it.get('spot') not in (spot, '*')): continue   # a greeting or a sign-off is no note
            an, ans = it.get('anchor') or {}, it.get('answer') or {}
            t = an.get('at', an.get('from'))
            notes.append({'n': it.get('n'), 'kind': it.get('kind') or it.get('class'), 'words': ' '.join((it.get('words') or '').split())[:160],
                          'at': t, 'to': an.get('to'), 'tb': None if t is None else to_b(t), 'tb_to': None if an.get('to') is None else to_b(an['to']),
                          'x': an.get('x'), 'y': an.get('y'), 'estimate': bool(an.get('estimate')), 'whole': bool(an.get('whole')),
                          'answer': (ans.get('status', '').replace('_', ' ') + (': ' + ans['change'] if ans.get('change') else '')) or 'no answer yet'})
    rel = lambda p: urllib.parse.quote(os.path.relpath(os.path.abspath(p), os.path.dirname(os.path.abspath(out))).replace(os.sep, '/'))
    name = lambda p: os.path.basename(p)
    title = f"{spot + ' · ' if spot else ''}{name(va)} → {name(vb)}"
    data = {'title': title, 'mode': mode,
            'sub': ('lined up by EDL event' if mode == 'event' else 'one clock — no EDLs given') + f" · old {dur_a:.2f} s · new {dur_b:.2f} s",
            'a': {'src': rel(va), 'name': name(va), 'dur': dur_a, 'fps': fps_a, 'w': w_a, 'h': h_a},
            'b': {'src': rel(vb), 'name': name(vb), 'dur': dur_b, 'fps': fps_b, 'w': w_b, 'h': h_b},
            'segments': seg, 'events': [{'id': e['id'], 't0': e['t0'], 't1': e['t1'], 'status': status.get(e['id'], 'same')} for e in B],
            'removed': [{'id': o['id'], 't0': o['t0'], 't1': o['t1']} for o in removed], 'notes': notes}
    page = PAGE.replace('__TITLE__', html.escape(title)).replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f: f.write(page)
    counts = {}
    for s in data['events']: counts[s['status']] = counts.get(s['status'], 0) + 1
    print(f"wrote {out}: {mode}" + (f" · {', '.join(f'{v} {k}' for k, v in sorted(counts.items()))} · {len(removed)} removed" if mode == 'event' else '')
          + (f" · {len(notes)} note(s), {sum(n['tb'] is not None for n in notes)} marked" if rnd else ''))
    print('COMPARE-END ok')
    return data


PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f2f0ec;--panel:#fff;--ink:#141414;--muted:#6f6b64;--line:#d9d4cc;--soft:#ebe8e2;--same:#8f98a3;--moved:#5f86ad;--retimed:#c97a1e;
--replaced:#b5442c;--inserted:#2f8f5b;--note:#8a3fd0;--ui:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;--mono:ui-monospace,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#121211;--panel:#1c1b19;--ink:#efece6;--muted:#9a958c;--line:#35332f;--soft:#26241f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 var(--ui)}
.wrap{max-width:1500px;margin:0 auto;padding:18px 16px 40px;display:grid;gap:14px}
header{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;justify-content:space-between}
h1{margin:0;font-size:20px;font-weight:650;letter-spacing:-.01em;overflow-wrap:anywhere}.sub{color:var(--muted);font-size:13px}
.seg{display:inline-flex;background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:3px;gap:2px}
.seg button{font:inherit;font-size:13px;border:0;background:transparent;color:var(--ink);border-radius:8px;padding:5px 11px;cursor:pointer}
.seg button[aria-pressed=true]{background:var(--ink);color:var(--bg)}
.stage{display:grid;gap:12px}.stage.side{grid-template-columns:repeat(2,minmax(0,1fr))}.stage.stack,.stage.wipe{grid-template-columns:minmax(0,1fr)}
@media (max-width:700px){.stage.side{grid-template-columns:minmax(0,1fr)}}
.pane{position:relative;background:#000;border-radius:12px;overflow:hidden;aspect-ratio:var(--ar);width:100%;max-width:calc(74vh * var(--ar));justify-self:center}
.stage.wipe .pane{grid-area:1/1}.stage.wipe #pB{clip-path:inset(0 0 0 var(--wipe,50%))}
video{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;display:block}
.tag{position:absolute;top:8px;left:8px;font:600 12px var(--ui);color:#fff;background:rgba(0,0,0,.6);border-radius:999px;padding:3px 10px;z-index:2;max-width:70%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.stage.wipe #pB .tag{left:auto;right:8px}
.hold{position:absolute;bottom:8px;left:8px;font:600 12px var(--ui);color:#111;background:#ffd36b;border-radius:6px;padding:3px 8px;z-index:2;display:none}
.handle{display:none;position:absolute;top:0;bottom:0;width:2px;background:#fff;left:var(--wipe,50%);z-index:3;pointer-events:none;box-shadow:0 0 0 1px rgba(0,0,0,.35)}
.stage.wipe .handle{display:block}.stage.wipe{cursor:ew-resize;touch-action:none}
.ring{position:absolute;width:46px;height:46px;margin:-23px 0 0 -23px;border:3px solid var(--note);border-radius:50%;z-index:2;display:none;pointer-events:none}
.bar{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:grid;gap:10px}
.ctl{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center}
.btn{font:inherit;font-size:14px;border:1px solid var(--line);background:var(--soft);color:var(--ink);border-radius:9px;padding:6px 12px;cursor:pointer}
.btn.main{background:var(--ink);color:var(--bg);border-color:var(--ink);min-width:80px}
.time{font:13px var(--mono);color:var(--muted)}.now{font-size:14px}
.track{position:relative;height:46px;cursor:pointer;touch-action:none}
.ev{position:absolute;top:4px;height:22px;border-radius:4px;font:10px var(--mono);color:#fff;overflow:hidden;white-space:nowrap;padding:3px 4px;border-right:1px solid var(--panel)}
.nm{position:absolute;top:30px;width:10px;height:10px;margin-left:-5px;border-radius:50%;background:var(--note)}.nm.span{height:6px;margin-left:0;border-radius:3px;top:32px}
.knob{position:absolute;top:0;bottom:0;width:2px;background:var(--ink);pointer-events:none}
.lists{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.box{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 14px}
.box h2{font-size:12px;margin:2px 0 8px;color:var(--muted);font-weight:650;text-transform:uppercase;letter-spacing:.06em}
.box ul{list-style:none;margin:0;padding:0;display:grid;gap:6px}.box li{font-size:14px;cursor:pointer}.box li:hover{text-decoration:underline}
.k{display:inline-block;font:11px var(--mono);border-radius:4px;padding:1px 6px;color:#fff;margin-right:6px;background:var(--same)}
.foot{font-size:12.5px;color:var(--muted);margin:0}
</style></head><body>
<div class="wrap">
 <header><div><h1 id="title"></h1><div class="sub" id="sub"></div></div>
  <div class="seg" role="group" aria-label="Layout" id="modes"><button type="button" data-mode="side" aria-pressed="true">Side by side</button><button type="button" data-mode="stack" aria-pressed="false">Stacked</button><button type="button" data-mode="wipe" aria-pressed="false">Wipe</button></div></header>
 <div class="stage side" id="stage">
  <div class="pane" id="pA"><video id="vA" playsinline preload="auto" muted></video><span class="tag" id="tagA"></span><span class="hold" id="holdA"></span></div>
  <div class="pane" id="pB"><video id="vB" playsinline preload="auto"></video><span class="tag" id="tagB"></span><div class="handle"></div></div>
 </div>
 <div class="bar">
  <div class="ctl">
   <button class="btn main" id="play" type="button">Play</button>
   <button class="btn" id="back" type="button" title="one frame back (←)">◀ frame</button><button class="btn" id="fwd" type="button" title="one frame on (→)">frame ▶</button>
   <div class="seg" role="group" aria-label="Sound" id="sound"><button type="button" data-snd="new" aria-pressed="true">Sound: new</button><button type="button" data-snd="old" aria-pressed="false">old</button><button type="button" data-snd="off" aria-pressed="false">off</button></div>
   <span class="time" id="time"></span><span class="now" id="now"></span>
  </div>
  <div class="track" id="track" role="slider" aria-label="Seek the new version" tabindex="0"></div>
 </div>
 <div class="lists" id="lists"></div>
 <p class="foot" id="foot"></p>
</div>
<script type="application/json" id="data">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const $ = id => document.getElementById(id), vA = $('vA'), vB = $('vB'), stage = $('stage'), track = $('track');
const FA = 1 / D.a.fps, FB = 1 / D.b.fps, T = D.b.dur || 1;
const COLOR = {same: 'var(--same)', moved: 'var(--moved)', retimed: 'var(--retimed)', replaced: 'var(--replaced)', inserted: 'var(--inserted)', clock: 'var(--same)', removed: 'var(--muted)'};
const SAY = {same: 'the same window', moved: 'the same window, moved on the timeline', retimed: 're-timed — another window of the same take',
  replaced: 'replaced — another take', inserted: 'inserted — not in the old version', clock: 'one clock'};
const fmt = t => { t = Math.max(0, t || 0); const m = Math.floor(t / 60), s = t - 60 * m; return m + ':' + (s < 10 ? '0' : '') + s.toFixed(2); };
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
document.title = D.title; $('title').textContent = D.title; $('sub').textContent = D.sub;
$('tagA').textContent = 'old · ' + D.a.name; $('tagB').textContent = 'new · ' + D.b.name;
$('pA').style.setProperty('--ar', D.a.w + ' / ' + D.a.h); $('pB').style.setProperty('--ar', D.b.w + ' / ' + D.b.h);
vA.src = D.a.src; vB.src = D.b.src;

function segAt(t) { const S = D.segments; let lo = 0, hi = S.length - 1, k = 0;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (S[m][0] <= t + 1e-6) { k = m; lo = m + 1; } else hi = m - 1; } return S[k]; }
function mapB(t) { const s = segAt(t), span = s[1] - s[0], r = span > 1e-9 ? (s[3] - s[2]) / span : 0;
  return {s, a: s[2] + Math.max(0, Math.min(t, s[1]) - s[0]) * r, hold: Math.abs(s[3] - s[2]) < 1e-6, rate: r}; }
function evAt(t) { return D.events.find(e => e.t0 - 1e-6 <= t && t < e.t1) || D.events[D.events.length - 1]; }
let solo = null;            // an old-only stretch (a removed event) playing alone: {until}
function sync() {
  if (solo) { if (vA.paused || vA.currentTime >= solo.until) { vA.pause(); solo = null; } paint(null); return; }
  const t = vB.currentTime, m = mapB(t), playing = !vB.paused && !vB.ended;
  if (m.hold || !playing) {
    if (!vA.paused) vA.pause();
    if (Math.abs(vA.currentTime - m.a) > FA / 2) vA.currentTime = m.a;
  } else {
    const r = Math.min(16, Math.max(0.0625, m.rate));
    if (Math.abs(vA.playbackRate - r) > 1e-3) vA.playbackRate = r;
    if (Math.abs(vA.currentTime - m.a) > Math.max(0.08, 2 * FA)) vA.currentTime = m.a;
    if (vA.paused) vA.play().catch(() => {});
  }
  paint(m);
}
function paint(m) {
  const t = vB.currentTime; $('knob').style.left = (t / T * 100) + '%';
  $('time').textContent = 'new ' + fmt(t) + ' · old ' + fmt(vA.currentTime);
  const h = $('holdA');
  if (solo) { $('now').textContent = 'the old version alone — a removed event'; h.style.display = 'none'; }
  else { const e = D.mode === 'event' ? evAt(t) : null; $('now').textContent = e ? e.id + ' — ' + SAY[e.status] : '';
    if (m && m.hold) { h.style.display = 'block'; h.textContent = m.s[4] === 'inserted' ? 'old: not in this version — holding' : 'old: lacks this take time — holding'; }
    else h.style.display = 'none'; }
  for (const n of D.notes) if (n.ring) n.ring.style.display = Math.abs(vA.currentTime - n.at) < 0.6 ? 'block' : 'none';
}
function loop() { sync(); requestAnimationFrame(loop); }
function seekB(t) { solo = null; vB.currentTime = Math.max(0, Math.min(T - FB / 2, t)); }
function soloA(t0, t1) { vB.pause(); vA.playbackRate = 1; vA.currentTime = t0; solo = {until: t1}; vA.play().catch(() => {}); }

for (const e of D.events) { const d = el('div', 'ev', e.id); d.style.left = (e.t0 / T * 100) + '%'; d.style.width = ((e.t1 - e.t0) / T * 100) + '%';
  d.style.background = COLOR[e.status]; d.title = e.id + ' — ' + SAY[e.status]; track.appendChild(d); }
if (D.mode === 'clock') { const d = el('div', 'ev', 'one clock'); d.style.left = '0'; d.style.width = '100%'; d.style.background = COLOR.clock; track.appendChild(d); }
for (const n of D.notes) {
  if (n.tb != null) { const d = el('div', 'nm' + (n.tb_to != null ? ' span' : '')); d.style.left = (n.tb / T * 100) + '%';
    if (n.tb_to != null) d.style.width = Math.max(0.4, (n.tb_to - n.tb) / T * 100) + '%'; d.title = n.n + ' · ' + n.words; track.appendChild(d); }
  if (n.x != null && n.y != null && n.at != null) { n.ring = el('div', 'ring'); n.ring.style.left = (n.x * 100) + '%'; n.ring.style.top = (n.y * 100) + '%'; $('pA').appendChild(n.ring); }
}
track.appendChild(Object.assign(el('div', 'knob'), {id: 'knob'}));
function box(title, items) { if (!items.length) return; const b = el('div', 'box'); b.appendChild(el('h2', null, title)); const ul = el('ul'); b.appendChild(ul);
  for (const [label, kind, text, go] of items) { const li = el('li'); const k = el('span', 'k', label); k.style.background = COLOR[kind] || 'var(--note)';
    li.appendChild(k); li.appendChild(document.createTextNode(text)); li.onclick = go; ul.appendChild(li); } $('lists').appendChild(b); }
box('What changed', D.events.filter(e => e.status !== 'same').map(e => [e.status, e.status, e.id + ' · new ' + fmt(e.t0) + '–' + fmt(e.t1), () => seekB(e.t0)]));
box('Removed from the old version', D.removed.map(o => ['removed', 'removed', o.id + ' · old ' + fmt(o.t0) + '–' + fmt(o.t1) + ' — play it alone', () => soloA(o.t0, o.t1)]));
box('The round\'s notes', D.notes.map(n => [String(n.n), 'note', (n.whole ? 'whole · ' : n.at != null ? fmt(n.at) + (n.to != null ? '–' + fmt(n.to) : '') + (n.estimate ? ' (est.)' : '') + ' · ' : '')
  + (n.kind || '') + ' · ' + n.words + ' → ' + n.answer + (n.at != null && n.tb == null ? ' (its event was removed)' : ''),
  () => { if (n.tb != null) seekB(n.tb); else if (n.at != null) soloA(n.at, n.to != null ? n.to : n.at + 2); }]));
$('foot').textContent = (D.mode === 'event' ? 'Lined up by EDL event: a moment of the new version shows the same take time of the same event in the old one; the old side holds (yellow tag) where it lacks that take time or the event is new. ' : 'One clock: no EDLs were given, so the two play at the same time, not the same event. ')
  + 'Space plays · ←/→ one frame · Shift+←/→ one second. A review page for the operator, never for the client.';

$('play').onclick = () => { solo = null; if (vB.paused || vB.ended) vB.play().catch(() => {}); else vB.pause(); };
vB.addEventListener('play', () => { $('play').textContent = 'Pause'; }); vB.addEventListener('pause', () => { $('play').textContent = 'Play'; });
vB.addEventListener('loadedmetadata', () => paint(mapB(vB.currentTime)));
const step = k => { vB.pause(); seekB(vB.currentTime + k); };
$('back').onclick = () => step(-FB); $('fwd').onclick = () => step(FB);
document.addEventListener('keydown', ev => { if (ev.target.tagName === 'INPUT') return;
  if (ev.key === ' ') { ev.preventDefault(); $('play').click(); }
  else if (ev.key === 'ArrowLeft') { ev.preventDefault(); step(ev.shiftKey ? -1 : -FB); }
  else if (ev.key === 'ArrowRight') { ev.preventDefault(); step(ev.shiftKey ? 1 : FB); } });
let snd = 'new'; const sound = () => { vB.muted = snd !== 'new'; vA.muted = snd !== 'old'; };
for (const b of $('sound').querySelectorAll('button')) b.onclick = () => { snd = b.dataset.snd; sound();
  for (const x of $('sound').querySelectorAll('button')) x.setAttribute('aria-pressed', String(x === b)); };
for (const b of $('modes').querySelectorAll('button')) b.onclick = () => { stage.className = 'stage ' + b.dataset.mode;
  for (const x of $('modes').querySelectorAll('button')) x.setAttribute('aria-pressed', String(x === b)); };
let drag = false; const tAt = e => { const r = track.getBoundingClientRect(); return (e.clientX - r.left) / r.width * T; };
track.addEventListener('pointerdown', e => { drag = true; track.setPointerCapture(e.pointerId); seekB(tAt(e)); });
track.addEventListener('pointermove', e => { if (drag) seekB(tAt(e)); }); track.addEventListener('pointerup', () => { drag = false; });
let wd = false; const wipe = e => { const r = $('pA').getBoundingClientRect(); stage.style.setProperty('--wipe', (Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * 100) + '%'); };
stage.addEventListener('pointerdown', e => { if (!stage.classList.contains('wipe')) return; wd = true; stage.setPointerCapture(e.pointerId); wipe(e); });
stage.addEventListener('pointermove', e => { if (wd) wipe(e); }); stage.addEventListener('pointerup', () => { wd = false; });
sound(); requestAnimationFrame(loop);
window.__cmp = {mapB, segAt, D};   // for a scripted check of the alignment
</script></body></html>
'''


def selftest():
    F = 24.0; half = 0.5 / F
    A = [{'id': 'E1', 'take': 't1', 'in': 0.0, 'out': 2.0, 't0': 0.0, 't1': 2.0}, {'id': 'E2', 'take': 't2', 'in': 1.0, 'out': 3.0, 't0': 2.0, 't1': 4.0},
         {'id': 'E3', 'take': 't3', 'in': 0.0, 'out': 1.0, 't0': 4.0, 't1': 5.0}, {'id': 'E4', 'take': 't4', 'in': 0.0, 'out': 2.0, 't0': 5.0, 't1': 7.0}]
    B = [{'id': 'E1', 'take': 't1', 'in': 0.0, 'out': 2.0, 't0': 0.0, 't1': 2.0}, {'id': 'E2', 'take': 't2', 'in': 0.5, 'out': 3.5, 't0': 2.0, 't1': 5.0},
         {'id': 'X', 'take': 'tx', 'in': 0.0, 'out': 1.0, 't0': 5.0, 't1': 6.0}, {'id': 'E4', 'take': 't4b', 'in': 0.0, 'out': 2.0, 't0': 6.0, 't1': 8.0}]
    seg, st, rem = segments(A, B, F)
    want = [[0.0, 2.0, 0.0, 2.0, 'same', 'E1'], [2.0, 2.5, 2.0, 2.0, 'retimed', 'E2'], [2.5, 4.5, 2.0, 4.0, 'retimed', 'E2'],
            [4.5, 5.0, 4.0 - half, 4.0 - half, 'retimed', 'E2'], [5.0, 6.0, 4.0 - half, 4.0 - half, 'inserted', 'X'], [6.0, 8.0, 5.0, 7.0 - half, 'replaced', 'E4']]
    close = lambda x, y: len(x) == len(y) and all(abs(p - q) < 1e-6 if isinstance(p, float) else p == q for r, w in zip(x, y) for p, q in zip(r, w))
    moved = segments([dict(A[0], t0=1.0, t1=3.0)], [A[0]], F)[1]
    chk = [('the segments, one per stretch of the new version', close(seg, want)),
           ('each new event classed: same · retimed · inserted · replaced', st == {'E1': 'same', 'E2': 'retimed', 'X': 'inserted', 'E4': 'replaced'}),
           ('an old event the new version lacks is listed removed', [o['id'] for o in rem] == ['E3']),
           ('the same window at another place on the timeline reads moved', moved == {'E1': 'moved'}),
           ('a note at old 1.0 s (E1) → new 1.0 s', abs(a_to_b(1.0, A, B, F) - 1.0) < 1e-6),
           ('a note at old 3.0 s (E2, take 2.0 s) → new 3.5 s', abs(a_to_b(3.0, A, B, F) - 3.5) < 1e-6),
           ('a note on the removed E3 → no mark', a_to_b(4.5, A, B, F) is None),
           ('a note on the replaced E4 → stretched: old 6.0 s → new 7.0 s', abs(a_to_b(6.0, A, B, F) - 7.0) < 1e-6)]
    d = tempfile.mkdtemp(prefix='compare-versions-selftest-')
    try:
        for n, s in (('a.mp4', 7), ('b.mp4', 8)):
            os.makedirs(os.path.join(d, 'deliver'), exist_ok=True)
            subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-f', 'lavfi', '-i', f'testsrc2=size=96x170:rate=24:duration={s}', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                            os.path.join(d, 'deliver', n)], check=True)
        tl = lambda E: {'spot': 'S01', 'fps': 24, 'events': [{'id': e['id'], 'take': e['take'], 'in': e['in'], 'out': e['out'], 'tl': [e['t0'], e['t1']]} for e in E]}
        os.makedirs(os.path.join(d, 'edit')); json.dump(tl(A), open(os.path.join(d, 'edit', 'a.json'), 'w')); json.dump(tl(B), open(os.path.join(d, 'edit', 'b.json'), 'w'))
        json.dump({'items': [{'n': 1, 'spot': 'S01', 'kind': 'ERROR', 'words': 'the price </script><b>x</b>', 'anchor': {'at': 3.0, 'x': 0.5, 'y': 0.2, 'estimate': True},
                              'answer': {'status': 'done', 'change': 'corrected'}},
                             {'n': 2, 'spot': 'S02', 'kind': 'TASTE', 'words': 'another spot', 'anchor': {'at': 1.0}}]}, open(os.path.join(d, 'round.json'), 'w'))
        cwd = os.getcwd(); data = build(d, 'deliver/a.mp4', 'deliver/b.mp4', 'edit/a.json', 'edit/b.json', 'round.json', None, 'review/p.html'); os.chdir(cwd)
        page = open(os.path.join(d, 'review', 'p.html'), encoding='utf-8').read()
        again = subprocess.run([sys.executable, os.path.abspath(__file__), '--root', d, '--a', 'deliver/a.mp4', '--b', 'deliver/b.mp4', '--out', 'review/p.html'], capture_output=True, text=True)
        clock = subprocess.run([sys.executable, os.path.abspath(__file__), '--root', d, '--a', 'deliver/a.mp4', '--b', 'deliver/b.mp4', '--out', 'review/c.html'], capture_output=True, text=True)
        cpage = open(os.path.join(d, 'review', 'c.html'), encoding='utf-8').read() if clock.returncode == 0 else ''
        chk += [('the page names the videos by relative path', data['a']['src'] == '../deliver/a.mp4' and data['b']['src'] == '../deliver/b.mp4'),
                ("only this spot's notes, mapped to the new clock", [n['n'] for n in data['notes']] == [1] and abs(data['notes'][0]['tb'] - 3.5) < 1e-6),
                ('note text cannot close the data script', '</script><b>' not in page and '<\\/script>' in page),
                ('a second run refuses to overwrite', again.returncode != 0 and 'refusing to overwrite' in (again.stderr + again.stdout)),
                ('without EDLs: one clock, one segment', '"mode": "clock"' in cpage and '"segments": [[0.0, 8.0, 0.0, 8.0, "clock", ""]]' in cpage)]
    finally:
        shutil.rmtree(d, ignore_errors=True)
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--a', help='the version the client saw (N-1)'); ap.add_argument('--b', help='the new version (N)')
    ap.add_argument('--edl-a'); ap.add_argument('--edl-b'); ap.add_argument('--round'); ap.add_argument('--spot'); ap.add_argument('--out'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest: return selftest()
    if not (a.a and a.b and a.out): ap.error('--a, --b and --out are required (or --selftest)')
    if bool(a.edl_a) != bool(a.edl_b): ap.error('--edl-a and --edl-b go together: both EDLs, or neither for one clock')
    build(a.root, a.a, a.b, a.edl_a, a.edl_b, a.round, a.spot, a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
