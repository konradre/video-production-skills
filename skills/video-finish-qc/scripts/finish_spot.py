#!/usr/bin/env python3
"""finish_spot.py — the EDL-driven finish of one spot, in video-finish's order: upscale (already done, per shot) →
grade (a cube on upscaled mezzanines; heroes arrive pre-graded, look "none") → composite (post layers + the end card, when
the EDL has one) → mix → downscale → encode. Three stages, each re-runnable:
  cut      edit/mezz/<SPOT>-footage-graded<tag>.mov   ProRes 422 HQ 10-bit 4:2:2 at the mezzanine raster, footage only
  master   edit/mezz/<SPOT>-master-<W>x<H><tag>.mov   + layers + card, PCM 24-bit STATIC mix (the VO stem is REBUILT first); no
                                                      loudness processing — the master is a mix, the level is set once, at deliver
  deliver  deliver/<deliver_base><tag|-v1>.mp4        measure → ONE static gain to the EDL's I → aresample 192 kHz → alimiter at TP →
                                                      aresample 48k → alimiter again (the limiting the target costs is printed,
                                                      and the limiter's deepest cut inside each designed impact → edit/mezz/
                                                      <deliverable>.limiter.json, which spot-audio-assembly sound_table.py reads);
                                                      captions overlaid AFTER the downscale; H.264 High CRF 17 slow, AAC 256k,
                                                      faststart, the length capped at runtime_s
The deliver encode is CRF 17 slow, -tune film unless the EDL sets `deliver_encode` {crf, tune: film|grain|none, preset}: a look
that carries grain buys it there (measured 2026-10-28 on a Dehancer 16 mm grain: CRF 17 film kept 37-83 % of the master's moving
grain, CRF 12 grain 65-96 % at 3.2x the bytes, 74 -> 234 MB for 47 s). It is for a deliverable with NO byte cap; a capped
outlet gets its own variant from the mezzanine (video-finish § 8: two-pass at a derived bitrate, -tune film). An unknown key
stops the finish before stage 1.
The script-fidelity gate (beat_sheet.py) runs BEFORE stage 1 when the beats file exists: a FAIL = no finish. So does the
cut-edge gate (video-edit-edl edge_audit.py) wherever a take's own sound plays: a word bitten at an edge = no finish. A spot with no
role:"endcard" event (a beat list may forbid a card) cuts its footage at the runtime.

  finish_spot.py --root <project> --edl edit/<SPOT>-EDL.json [--stage cut|master|deliver|all] [--look ads-clean]
                 [--in-dir edit/upscale-out] [--tag=-v3] [--cubes <dir of <look>_33.cube>] [--canvas 2160x3840] [--fps 24]
                 [--beat-gate <beat_sheet.py>] [--beats prompts/<SPOT>-beats.json] [--edge-gate <edge_audit.py>]
                 [--stem-builder <build_vo_stem.py>] [--captions-builder <build_captions.py>] [--no-gate]
The gate's beat list: --beats, else the EDL's `beats`, else prompts/<SPOT>-beats.json; a named list that does not exist stops
the finish, and the log names the list the gate read.
Sources per event: designed → its own render at native raster; generated → <in-dir>/<id>.mov | <id>__*.mov | <id>.mp4,
or the event's own `src` (a hero under a fresh name), sought by handle_head (a FULL-TAKE hero needs handle_head = in).
  finish_spot.py --selftest-limiter      the limiter-cut read on a synthetic master with a known answer
Prints FINISH-END <stage> as the sentinel; a log without it is a failure whatever the file sizes say.
Before any stage the HOST drive's free space is read; under the floor (--min-free-gb 40, or 3x the spot's estimated mezzanine
pair) the finish WARNS with the numbers and runs — the floor is a buffer, not a gate (since 2026-10-09). A
mezzanine pair per version fills a drive, and on a VM the guest's free space is not the host's.
"""
import argparse, glob, hashlib, json, os, subprocess, sys

SK = os.path.expanduser('~/.claude/skills')


def ff_path(p):
    """A file path inside a filter graph is parsed TWICE (the graph, then the filter's options), so every special character is
    escaped for both: backslashes become slashes, a drive colon `D:` becomes `D\\\\:`, and `' ; , [ ]` take one backslash.
    Without it every caption / LUT job on a Windows path fails inside ffmpeg (ffmpeg-skill measured it on 8.1 / 9.0)."""
    p = p.replace('\\', '/')
    for ch, rep in ((':', '\\\\:'), ("'", "\\'"), (';', '\\;'), (',', '\\,'), ('[', '\\['), (']', '\\]')): p = p.replace(ch, rep)
    return p


TO709 = 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int'   # EVERY RGB → YUV step names its matrix: ffmpeg's default is BT.601 while the
# files are tagged bt709, and a saturated patch read back up to 40 levels off (measured 2026-10-21). Grey, black and white do not
# move, which is why no grey check saw it. `matrix_check.py` is the regression. Every RGB <-> YUV crossing also rounds
# accurately: swscale's default rounding lost 2-4 levels per crossing (measured 2026-10-25).



def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def verified(path):
    """True when edit/mezz/<file>.finish.json names this file's current content"""
    try: r = json.load(open(f'edit/mezz/{os.path.basename(path)}.finish.json'))
    except (OSError, ValueError): return False
    return isinstance(r, dict) and r.get('sha256') == _sha256(path)


def provenance(path, parent=None):
    """write edit/mezz/<file>.finish.json for a stage's output — qc_deliverable.py reads a deliverable's record as 'made by
    this finisher'. A stage writes one only when its input carries a matching record, so a deliver-only re-run over an older,
    unchecked master never certifies the result (measured 2026-10-25: a BT.601 master re-delivered read as finished)."""
    if parent is not None and not verified(parent):
        print(f"INFO provenance: none written for {path} — its input {parent} has no matching record from this finisher; "
              "re-run from the cut stage (--stage all)", flush=True)
        return
    json.dump({'tool': 'finish_spot.py', 'file': path, 'sha256': _sha256(path), 'bytes': os.path.getsize(path)},
              open(f'edit/mezz/{os.path.basename(path)}.finish.json', 'w'), indent=1)


def impact_windows(au, dur=0.4):
    """[(from, to, source)] — each designed impact: the hit a suck-out releases ON (a music duck with gain ≤ 0.1 lasting
    0.2–0.7 s, spot-audio-assembly SFX-AND-MUSIC.md § Sound direction); the EDL marks impacts no other way"""
    out = []
    for name, m in ((au or {}).get('music') or {}).items():
        for dk in (m.get('duck') or []) if isinstance(m, dict) else []:
            a, b, g = (float(v) for v in dk[:3])
            if g <= 0.1 and 0.2 <= b - a <= 0.7: out.append((round(b, 3), round(b + dur, 3), f"impact after {name}'s suck-out at {b:.2f} s"))
    return sorted(out)


def limiter_cut(master, gain_db, lim, windows, blk=0.01):
    """the delivery limiter's gain reduction, read by rendering the master twice — the static gain alone, and the gain plus the
    limiter chain the deliverable gets — and comparing 10 ms block peaks. Returns {per_100ms (sparse: ≥ 0.1 dB), windows
    (each impact's deepest cut; with no impact in the EDL, the three loudest 400 ms windows stand in, named so), deepest}."""
    import numpy as np
    def peaks(af):
        n = int(48000 * blk) * 2; pr = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', master, '-af', af, '-f', 'f32le', '-ac', '2', '-ar', '48000', '-'], stdout=subprocess.PIPE)
        out, buf = [], b''
        while True:
            ch = pr.stdout.read(4 * n * 2000)
            if not ch: break
            buf += ch; m = len(buf) // (4 * n)
            if m: out.append(np.abs(np.frombuffer(buf[:m * 4 * n], np.float32).reshape(m, n)).max(axis=1)); buf = buf[m * 4 * n:]
        if pr.wait(): raise RuntimeError(f'ffmpeg failed rendering {af}')
        return np.concatenate(out) if out else np.zeros(0)
    rs = f"volume={gain_db:.3f}dB,aresample=192000"                          # both through the same resample path: only the limiters differ
    pre = peaks(f"{rs},aresample=48000"); post = peaks(f"{rs},{lim},aresample=48000,{lim}")
    k = min(len(pre), len(post)); pre, post = pre[:k], post[:k]
    gr = np.where(pre > 1e-4, 20 * np.log10(np.maximum(pre, 1e-9) / np.maximum(post, 1e-9)), 0.0).clip(min=0)
    per = [{'t': round(i * 0.1, 2), 'db': round(float(v), 2)} for i, v in enumerate(gr[:len(gr) // 10 * 10].reshape(-1, 10).max(axis=1)) if v >= 0.1]
    if not windows:
        e = np.convolve(pre ** 2, np.ones(40) / 40, 'valid'); picks = []
        for i in np.argsort(-e):
            if all(abs(i * blk - p) >= 1.0 for p in picks): picks.append(i * blk)
            if len(picks) == 3: break
        windows = [(round(p, 2), round(p + 0.4, 2), 'a loudest 400 ms window (no suck-out in the EDL marks an impact)') for p in sorted(picks)]
    wins = [{'from': a, 'to': b, 'source': s, 'deepest_cut_db': round(float(gr[int(a / blk):int(b / blk) + 1].max(initial=0.0)), 2)} for a, b, s in windows]
    i = int(np.argmax(gr)) if len(gr) else 0
    return {'per_100ms': per, 'windows': wins, 'deepest': {'t': round(i * blk, 2), 'db': round(float(gr[i]) if len(gr) else 0.0, 2)}}


def selftest_limiter():
    """a -30 dBFS bed with one loud hit at 4.0 s, gained +12 dB into a -2.4 dBTP limiter: the hit is cut, the bed is not"""
    import numpy as np, tempfile
    sr = 48000; rng = np.random.default_rng(11); n = 6 * sr; x = 0.03 * rng.standard_normal((n, 2))
    k = np.arange(int(0.4 * sr)); x[4 * sr:4 * sr + len(k)] += (0.5 * rng.standard_normal(len(k)) * np.exp(-k / (0.1 * sr)))[:, None]
    d = tempfile.mkdtemp(prefix='limiter-selftest-'); wav = os.path.join(d, 'master.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(sr), '-ac', '2', '-i', '-', '-c:a', 'pcm_s24le', wav], input=np.clip(x, -1, 1).astype(np.float32).tobytes(), check=True)
    lim = f"alimiter=limit={10 ** (-2.4 / 20):.4f}:attack=5:release=60:level=false:latency=1"
    au = {'music': {'bed': {'tl': [0, 6], 'duck': [[3.6, 4.0, 0.03, 0.06, 0]], 'fade_in': 1}}}
    r = limiter_cut(wav, 12.0, lim, impact_windows(au)); q = limiter_cut(wav, 12.0, lim, [(1.0, 1.4, 'the bed alone')])
    r0 = limiter_cut(wav, 12.0, lim, [])
    chk = [('the impact window comes from the suck-out: 4.00–4.40 s', [(w['from'], w['to']) for w in r['windows']] == [(4.0, 4.4)]),
           ('the hit is cut ≥ 3 dB inside its window', r['windows'][0]['deepest_cut_db'] >= 3),
           ('the bed alone is cut < 0.2 dB', q['windows'][0]['deepest_cut_db'] < 0.2),
           ('the deepest cut anywhere sits inside the impact window', 4.0 <= r['deepest']['t'] <= 4.4),
           ('per 100 ms is sparse: no block of the bed (0–3.5 s) carries a cut', not any(e['t'] < 3.5 for e in r['per_100ms'])),
           ('no suck-out: the loudest 400 ms windows stand in, and the first one holds the hit', any(w['from'] <= 4.0 <= w['to'] + 0.05 for w in r0['windows']) and 'no suck-out' in r0['windows'][0]['source'])]
    for name, ok in chk: print(f"{'ok  ' if ok else 'FAIL'} {name}")
    ok = all(v for _, v in chk); print(f"LIMITER SELFTEST {'PASS' if ok else 'FAIL'} ({sum(v for _, v in chk)}/{len(chk)})"); return ok


def main():
    if '--selftest-limiter' in sys.argv[1:]: sys.exit(0 if selftest_limiter() else 2)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl', required=True); ap.add_argument('--stage', default='all', choices=['cut', 'master', 'deliver', 'all'])
    ap.add_argument('--look', default='ads-clean'); ap.add_argument('--in-dir', default='edit/upscale-out'); ap.add_argument('--tag', default='')
    ap.add_argument('--cubes', default=os.environ.get('LOOK_LIBRARY_CUBES', os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'look-library', 'cubes')), help='the baked <look>_33.cube files (look-library/GUIDE.md: bake them first)')
    ap.add_argument('--canvas', default='2160x3840'); ap.add_argument('--fps', type=int, default=24); ap.add_argument('--handle', type=float, default=None, help='default head handle for upscaled sources (default 4 frames)')
    ap.add_argument('--beat-gate', default=f'{SK}/video-edit-edl/scripts/beat_sheet.py'); ap.add_argument('--stem-builder', default=f'{SK}/spot-audio-assembly/scripts/build_vo_stem.py')
    ap.add_argument('--captions-builder', default=f'{SK}/spot-audio-assembly/scripts/build_captions.py'); ap.add_argument('--no-gate', action='store_true')
    ap.add_argument('--beats', default=None, help='the beat list the gate reads (default prompts/<SPOT>-beats.json); a versioned EDL names its own')
    ap.add_argument('--edge-gate', default=f'{SK}/video-edit-edl/scripts/edge_audit.py', help='the cut-edge gate: no word bitten where a take\'s sound plays')
    ap.add_argument('--min-free-gb', type=float, default=40.0, help='the HOST drive floor under which the finish warns before it runs (or 3x the spot\'s mezzanine footprint, whichever is larger); --min-free-gb 0 skips the read')
    argv = sys.argv[1:]
    for i, x in enumerate(argv[:-1]):   # --tag -final: a value that starts with '-' must be joined for argparse
        if x == '--tag' and argv[i + 1].startswith('-'): argv[i:i + 2] = [f'--tag={argv[i + 1]}']
    a = ap.parse_args(argv); os.chdir(a.root)
    if a.min_free_gb > 0:   # the drive that matters is the one the mezzanines land on — on a VM that is the HOST drive, whose image never shrinks
        import shutil as _sh
        _free = _sh.disk_usage('.').free / 1e9
        try:
            _e = json.load(open(a.edl, encoding='utf-8')); _W, _H = (int(v) for v in a.canvas.lower().split('x'))
            _est = float(_e.get('runtime_s', 30)) * _W * _H * a.fps * 3.8 / 8 / 1e9 * 2   # two ProRes HQ mezzanines (~3.8 bit/px)
        except Exception: _est = 0.0
        _floor = max(a.min_free_gb, 3 * _est)
        if _free < _floor:   # a buffer, not a gate: say the numbers and run (since 2026-10-09)
            print(f'⚠ DISK: {_free:.0f} GB free on the drive holding the project, under the floor of {_floor:.0f} GB (3x an estimated {_est:.1f} GB mezzanine pair, min {a.min_free_gb:g})'
                  + (f' — LESS than this finish writes ({_est:.1f} GB): it can fill the drive' if _free < _est else '')
                  + '. The finish runs; name superseded mezzanines for deletion (video-production/scripts/project_size.py) to restore the buffer.', flush=True)
        else: print(f'disk: {_free:.0f} GB free, floor {_floor:.0f} GB', flush=True)
    W, H = (int(v) for v in a.canvas.lower().split('x')); FPS = a.fps; HANDLE = a.handle if a.handle is not None else 4 / FPS
    edl = json.load(open(a.edl, encoding='utf-8')); RUN = float(edl['runtime_s']); AU = edl['audio']; SPOT = edl.get('spot', 'SPOT'); DBASE = edl.get('deliver_base', SPOT)
    FOOT = f'edit/mezz/{SPOT}-footage-graded{a.tag}.mov'; MASTER = f'edit/mezz/{SPOT}-master-{W}x{H}{a.tag}.mov'; DELIV = f'deliver/{DBASE}{a.tag or "-v1"}.mp4'
    os.makedirs('edit/mezz', exist_ok=True); os.makedirs('deliver', exist_ok=True)
    ecs = [e for e in edl['events'] if e.get('role') == 'endcard']; assert len(ecs) <= 1, f'{len(ecs)} endcard events — at most one (role: endcard)'
    EC = ecs[0] if ecs else None   # optional: edl_check --require-endcard holds a card where the script has one
    ev = [e for e in edl['events'] if e.get('role') != 'endcard']
    for e in ev: assert e.get('take'), f"{e['id']}: take is null — pick a keeper in the EDL first"
    for e in edl['events']: assert e.get('in_matrix') in (None, 'bt709', 'bt601', 'bt2020nc'), f"{e['id']}: in_matrix {e.get('in_matrix')!r} — bt709 | bt601 | bt2020nc"
    FOOT_END = float(EC['tl'][0]) if EC else RUN
    DENC = {'crf': 17, 'tune': 'film', 'preset': 'slow'}; _de = edl.get('deliver_encode') or {}   # grain is a bitrate tax the EDL buys on purpose
    _bad = sorted(k for k in _de if k not in DENC and not k.startswith('_'))
    assert not _bad, f'deliver_encode: unknown key(s) {_bad} — the finisher reads {sorted(DENC)}'
    DENC.update({k: v for k, v in _de.items() if not k.startswith('_')})
    assert DENC['tune'] in ('film', 'grain', 'none') and 0 <= float(DENC['crf']) <= 51, f"deliver_encode {DENC}: tune film|grain|none, crf 0-51"
    VENC = ['-preset', str(DENC['preset']), '-crf', str(DENC['crf'])] + ([] if DENC['tune'] == 'none' else ['-tune', DENC['tune']])
    beats = a.beats or edl.get('beats') or f"prompts/{SPOT}-beats.json"   # a versioned EDL names its own list (EDL-CONTRACT.md)
    if (a.beats or edl.get('beats')) and not os.path.exists(beats): sys.exit(f'beats {beats}: no such file — the gate would read nothing')   # 2026-10-28: the default name held a superseded list
    if not a.no_gate and os.path.exists(beats):
        print(f'gate: beat list {beats}', flush=True)
        subprocess.run([sys.executable, os.path.expanduser(a.beat_gate), '--root', '.', '--edl', a.edl, '--beats', beats], check=True)   # SCRIPT-FIDELITY GATE: FAIL = no finish
    elif not a.no_gate: print(f'WARNING no beats file at {beats} — the script-fidelity gate did not run', flush=True)
    NATIVE_PROG = bool((edl.get('qc') or {}).get('native_programme'))   # the takes' own speech IS the programme: a bitten edge stops the finish
    UNDECLARED = 'native_programme' not in (edl.get('qc') or {}) and not any('native_audio_vol' in e for e in ev)   # the EDL never says whose sound plays
    if not a.no_gate and (UNDECLARED or any(e.get('source') != 'designed' and (NATIVE_PROG or float(e.get('native_audio_vol', 0) or 0) > 0) for e in ev)):
        if not os.path.exists(os.path.expanduser(a.edge_gate)):
            print(f'WARNING no cut-edge gate at {a.edge_gate} — a word bitten at an edge would not be caught before the render', flush=True)
        elif NATIVE_PROG or UNDECLARED:   # undeclared: the gate exits 2 NOT READ when a take carries sound — no finish until the EDL says whose sound plays
            subprocess.run([sys.executable, os.path.expanduser(a.edge_gate), '--root', '.', '--edl', a.edl], check=True)   # CUT-EDGE GATE: a bitten word = no finish
        elif subprocess.run([sys.executable, os.path.expanduser(a.edge_gate), '--root', '.', '--edl', a.edl]).returncode:
            print('WARNING cut edges: an earned native bed is cut through a sound (above) — the read is of SOUND, not words: listen at '
                  'each flagged edge, declare a meant cut (a knock on its hit) in accepted_edges, move a bitten word', flush=True)

    def run(cmd): print('$', ' '.join(cmd)[:400], flush=True); subprocess.run(cmd, check=True)

    def probe(p): return subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_frames,duration', '-of', 'default=nw=1', p], capture_output=True, text=True).stdout

    def first(pat):
        for p in (pat or '').split('|'):
            g = sorted(glob.glob(p))
            if g: return g[0]
        return None

    def ms(t): v = int(round(t * 1000)); return f'{v}|{v}'

    SFPS = {}
    def src_fps(p):
        """a CFR source's frame rate (r_frame_rate == avg_frame_rate), else None — a VFR source keeps the fps filter's rounding"""
        if p not in SFPS:
            r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate,avg_frame_rate', '-of', 'csv=p=0', p],
                               capture_output=True, text=True).stdout.strip().split(',')
            try:
                q = [float(n) / float(d) for n, d in (x.split('/') for x in r[:2])]; SFPS[p] = q[0] if len(q) == 2 and q[0] > 0 and abs(q[0] - q[1]) < 1e-3 else None
            except (ValueError, ZeroDivisionError): SFPS[p] = None
        return SFPS[p]
    SMX = {}
    def src_colour(p, decl=None):
        """(matrix, range, rgb) a source is decoded with — the event's declared in_matrix, else the tag, else BT.709 at HD
        and above and BT.601 below (normalise_shots.py's rule, the one players apply to untagged video;
        measured 2026-10-25). The size rule picking BT.601 prints a WARN, the cue to declare: an untagged SD clip encoded BT.709 reads 26 off."""
        if (p, decl) not in SMX:
            r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name,pix_fmt,color_space,color_range,width,height',
                                '-of', 'json', p], capture_output=True, text=True).stdout
            st = (json.loads(r or '{}').get('streams') or [{}])[0]; cs = st.get('color_space') or ''
            tagged = cs in ('bt709', 'bt470bg', 'smpte170m', 'bt2020nc')
            m = decl or (cs if tagged else ('bt709' if st.get('height', 0) >= 720 or st.get('width', 0) >= 1280 else 'bt601'))
            pf = st.get('pix_fmt') or ''
            rgb = st.get('codec_name') == 'png' or pf.startswith(('rgb', 'bgr', 'gbr', 'argb', 'abgr', '0rgb', '0bgr', 'pal'))
            kind = 'rgb' if rgb else 'gray' if pf.startswith(('gray', 'ya', 'mono')) else 'yuv'
            if decl and kind != 'yuv':   # RGB and luma-only carry no YUV matrix: a declaration there would only force a range
                print(f"WARN {p}: in_matrix {decl} ignored — a {kind} source has no YUV matrix", flush=True)
            if decl and kind == 'yuv' and tagged and {'bt709': 'bt709', 'bt470bg': 'bt601', 'smpte170m': 'bt601', 'bt2020nc': 'bt2020nc'}[cs] != decl:   # the declaration describes the file READ (src), never the take behind a re-encoded hero
                print(f"WARN {p}: in_matrix {decl} overrides its own tag {cs} — right only when that tag is wrong", flush=True)
            if kind == 'yuv' and not tagged and not decl and m == 'bt601':   # untagged HD reads BT.709, as players do: no WARN
                print(f"WARN {p}: untagged — read as {m} by the size rule ({st.get('width')}x{st.get('height')}); declare the event's in_matrix if the source says otherwise", flush=True)
            SMX[(p, decl)] = (m, 'pc' if st.get('color_range') == 'pc' else 'tv', kind)
        return SMX[(p, decl)]
    def src_matrix(p, decl=None):
        """the named decode a cube's input gets — never ffmpeg's BT.601 default (an untagged upscale decoded as BT.601 shifts)"""
        m, rng, kind = src_colour(p, decl)
        if kind == 'gray': return "scale=flags=accurate_rnd+full_chroma_int"   # luma keeps swscale's own gray step: a forced tv read clipped 16/235 to 0/255
        return f"scale=in_color_matrix={m}:in_range={rng}:flags=accurate_rnd+full_chroma_int"
    def to709(p, decl=None):
        """'' for a BT.709 tv-range YUV source (it passes untouched, as before); otherwise the named conversion into the
        bt709 mezzanine — an RGB source (a png-codec render) by TO709, a BT.601 or full-range YUV source through 16-bit RGB"""
        m, rng, kind = src_colour(p, decl)
        if kind == 'rgb': return f"{TO709},"
        if kind == 'gray': return ''   # no matrix: the final format= step keeps its levels
        if m == 'bt709' and rng == 'tv': return ''
        return f"{src_matrix(p, decl)},format=gbrp16le,{TO709},"

    # ---- 1. graded mezzanine cut (footage only, 0–FOOT_END) ----
    if a.stage in ('cut', 'all'):
        fc = []; inputs = []
        for i, e in enumerate(ev):
            dur = e['out'] - e['in']; look = e.get('look') or a.look
            assert abs((e['tl'][1] - e['tl'][0]) - dur) < 1e-6, f"{e['id']}: tl span != out-in"
            if e.get('source') == 'designed': src = e['take']; ss = e['in']                                   # a native-raster render, no handles
            else:
                cands = sorted(glob.glob(f"{a.in_dir}/{e['id']}.mov")) + sorted(glob.glob(f"{a.in_dir}/{e['id']}__*.mov")) + sorted(glob.glob(f"{a.in_dir}/{e['id']}.mp4"))
                if e.get('src'): cands = [e['src']]
                src = cands[0] if cands else f"{a.in_dir}/{e['id']}.mp4"; ss = float(e.get('handle_head', HANDLE))
                if e['in'] > 0 and ss == 0: print(f"WARNING {e['id']}: in={e['in']} but handle_head=0 -> the source is assumed to START at the in-point; a FULL-TAKE hero needs handle_head=in", flush=True)
            assert os.path.exists(src), f"{e['id']}: source missing {src}"
            # FRAMES FROM THE TIMELINE, never from each window: ffmpeg gives a -ss/-t window its OWN frame count (0.721 s at 24 fps
            # → 18 frames, not 17.3), and a concat of 40 off-grid windows ran 36 frames long — every VO line after it late by up to
            # 1.5 s (av_sync_regress.py, 2026-09-29; bridgeclip's cumulative frame allocation). Event k gets exactly
            # round(tl1*fps) - round(tl0*fps) frames, its first frame the source at in + (T0 - tl0), so the sum telescopes.
            f0, f1 = round(e['tl'][0] * FPS), round(e['tl'][1] * FPS); nfr = f1 - f0; ss = max(0.0, ss + f0 / FPS - e['tl'][0])
            sf = src_fps(src)   # seek onto the source's own frame grid, a quarter frame early: at a half-frame offset the fps filter's
            if sf: ss = max(0.0, round(ss * sf) / sf - 0.25 / sf)   # nearest-frame choice flips on 1 ms timestamps (Matroska) → a frame shown twice
            inputs += ['-ss', f'{ss:.6f}', '-t', f'{(nfr + 2) / FPS:.6f}', '-i', src]
            lut = f"{src_matrix(src, e.get('in_matrix'))},format=gbrp16le,lut3d=file={ff_path(f'{a.cubes}/{look}_33.cube')}:interp=tetrahedral,{TO709}," if look != 'none' else to709(src, e.get('in_matrix'))   # look "none" = pre-graded hero (Resolve/Dehancer pass); both matrices named
            z = float(e.get('zoom', 1) or 1); zc = ''
            if z > 1.0001:                                                                                   # per-event punch-in: crop 1/z around the anchor, then the normal scale
                ax, ay = e.get('anchor', [0.5, 0.5]); cw, ch = f'iw/{z:.4f}', f'ih/{z:.4f}'
                zc = f"crop={cw}:{ch}:clip((iw*{ax:.4f})-({cw})/2\\,0\\,iw-({cw})):clip((ih*{ay:.4f})-({ch})/2\\,0\\,ih-({ch})),"
            fc.append(f"[{i}:v]{zc}scale={W}:{H}:flags=lanczos,fps={FPS},tpad=stop_mode=clone:stop=2,trim=end_frame={nfr},setpts=N/({FPS}*TB),{lut}format=yuv422p10le,setsar=1[v{i}]")
            print(e['id'], 'src', src, 'ss', round(ss, 4), 'look', look, 'dur', dur, 'tl', e['tl'], 'frames', nfr)
        fc.append(''.join(f'[v{i}]' for i in range(len(ev))) + f'concat=n={len(ev)}:v=1:a=0[out]')
        run(['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex', ';'.join(fc), '-map', '[out]', '-c:v', 'prores_ks', '-profile:v', '3', '-vendor', 'apl0', '-pix_fmt', 'yuv422p10le', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-r', str(FPS), FOOT])
        print(probe(FOOT))
        provenance(FOOT)
    # ---- 2. master: composite layers + end card at the mezzanine raster, mix the audio ----
    if a.stage in ('master', 'all'):
        subprocess.run([sys.executable, os.path.expanduser(a.stem_builder), '--root', '.', '--edl', a.edl], check=True)   # ALWAYS rebuild the stem from the EDL — a stale stem shipped a line at its old time
        inp = ['-i', FOOT] + (['-i', EC['take']] if EC else []) + ['-i', AU['vo']['stem']]
        STEM = 2 if EC else 1; n = STEM + 1   # input indices are DERIVED — a hard-coded stem index is where a card-less patch breaks the audio map
        v = ([f"[1:v]scale={W}:{H}:flags=lanczos,{to709(EC['take'], EC.get('in_matrix'))}format=yuv422p10le,setpts=PTS-STARTPTS[ec]"] if EC else []) + ["[0:v]format=yuv422p10le,tpad=stop_mode=clone:stop_duration=0.05[b0]"]; last = 'b0'
        for k, L in enumerate(edl.get('post_layers', [])):
            inp += ['-framerate', str(FPS), '-i', L['frames']]
            v.append(f"[{n}:v]scale={W}:{H}:flags=lanczos,{TO709},format=yuva422p10le,setpts=PTS-STARTPTS+{L['at']}/TB[ov{k}]"); n += 1   # RGBA → YUVA here, by the named matrix — never inside overlay
            v.append(f"[{last}][ov{k}]overlay=eof_action=pass:format=yuv422p10[b{k + 1}]"); last = f'b{k + 1}'
        v += ([f"[{last}]trim=0:{FOOT_END},setpts=PTS-STARTPTS[fo]", "[fo][ec]concat=n=2:v=1:a=0[vout]"] if EC
              else [f"[{last}]trim=0:{FOOT_END},setpts=PTS-STARTPTS[vout]"])
        au = [f"[{STEM}:a]aformat=sample_rates=48000:channel_layouts=stereo[vo]"]; mix = ['[vo]']; used = {}
        for name, s in AU.get('sfx', {}).items():
            if not isinstance(s, dict): continue
            f = first(s.get('file'))
            if not f: used[name] = None; print(f'WARNING sfx {name}: no file for {s.get("file")}', flush=True); continue
            inp += ['-i', f]; ch = f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo"; n += 1
            if s.get('src_in') is not None: ch += f",atrim={s['src_in']}:{s['src_in'] + s['dur']},asetpts=PTS-STARTPTS"
            elif s.get('dur'): ch += f",atrim=0:{s['dur']}"
            if s.get('dur'): ch += f",afade=t=out:st={max(0, s['dur'] - 0.1):.3f}:d=0.1"
            ch += f",volume={s.get('vol', 1)},adelay={ms(s['at'])}[{name}]"; au.append(ch); mix.append(f'[{name}]'); used[name] = f
        for name, m in AU.get('music', {}).items():
            if not isinstance(m, dict): continue
            f = first(m.get('file'))
            if not f: used[name] = None; print(f'WARNING music {name}: no file for {m.get("file")}', flush=True); continue
            t0, t1 = m['tl']; d = t1 - t0; inp += ['-i', f]; ch = f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{d}"; n += 1
            fd = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], capture_output=True, text=True).stdout.strip() or 0)
            if fd + 1e-3 < d: print(f"WARNING {name}: {f} is {fd:.2f} s but its span is {d:.2f} s -> the cue just ENDS at tl {t0 + fd:.2f} (no loop, no fade); cut a longer excerpt", flush=True)
            if m.get('fade_in'): ch += f",afade=t=in:st=0:d={m['fade_in']}"
            fo = m.get('fade_out', 0.15); ch += f",afade=t=out:st={max(0, d - fo):.3f}:d={fo}"
            if m.get('duck'):                              # ducks [[tl_from, tl_to, gain(, ramp | , ramp_in, ramp_out)]] in TIMELINE seconds — linear ramps (duck_ramp s unless the duck names its own) either side, per frame in cue-local time
                r = float(m.get('duck_ramp', 0.25)); ex = '1'; fine = False
                for dk in m['duck']:
                    assert len(dk) in (3, 4, 5), (name, 'a duck is [from, to, gain] + an optional ramp or ramp_in, ramp_out', dk)
                    da, db, dg = dk[:3]; ri = float(dk[3]) if len(dk) > 3 else r; ro = float(dk[4]) if len(dk) > 4 else ri
                    assert ri >= 0 and ro >= 0, (name, 'a negative ramp', dk); fine |= len(dk) > 3 and min(ri, ro) < 0.1   # a 3-value duck renders exactly as before
                    la, lb = da - t0, db - t0; assert 0 <= la < lb <= d + 1e-6, (name, 'duck outside the cue span', da, db, t0, t1)
                    up = f"1-(1-{dg})*(t-{la - ri:.3f})/{ri}" if ri > 0 else f"{dg}"     # ramp 0: straight to the gain at `from`
                    dn = f"{dg}+(1-{dg})*(t-{lb:.3f})/{ro}" if ro > 0 else "1"           # ramp_out 0: back to full AT `to` — a suck-out's hit
                    ex = f"({ex})*if(lt(t\\,{la - ri:.3f})\\,1\\,if(lt(t\\,{la:.3f})\\,{up}\\,if(lt(t\\,{lb:.3f})\\,{dg}\\,if(lt(t\\,{lb + ro:.3f})\\,{dn}\\,1))))"
                # eval=frame steps the gain once per audio frame (1024 samples, 21 ms): a duck carrying its own ramp under 0.1 s gets
                # 48-sample (1 ms) frames — measured 2026-10-25: 1024-sample frames returned a suck-out 7–17 ms after its hit; a
                # 256-sample frame still left an unaligned `to` 4.3 ms late; 48 holds every edge within 1 ms
                ch += (",asetnsamples=n=48:p=0" if fine else "") + f",volume=volume={m.get('vol', 0.7)}*{ex}:eval=frame,adelay={ms(t0)}[{name}]"
            else: ch += f",volume={m.get('vol', 0.7)},adelay={ms(t0)}[{name}]"
            au.append(ch); mix.append(f'[{name}]'); used[name] = f
        for e in ev:                                   # the take's own audio as a bed, only when the keeper earned it
            vol = e.get('native_audio_vol', 0)
            if not vol: continue
            nf = float(e.get('native_audio_from', e['in'])); assert e['in'] <= nf < e['out'], f"{e['id']}: native_audio_from outside [in,out)"
            nt = float(e.get('native_audio_to', e['out'])); assert nf < nt <= e['out'], f"{e['id']}: native_audio_to outside (from,out]"
            inp += ['-ss', f"{nf:.4f}", '-t', f"{nt - nf:.4f}", '-i', e['take']]
            fi = 'afade=t=in:st=0:d=0.02,' if nf > e['in'] else ''; fo = f"afade=t=out:st={max(0, nt - nf - 0.03):.3f}:d=0.03," if nt < e['out'] else ''
            # the take's audio on ITS presentation clock: a late track keeps its offset, missing packets become silence instead of
            # pulling everything after them early (0.49 s on a 0.5 s gap, av_sync_regress.py 2026-09-29)
            au.append(f"[{n}:a]aresample=48000:async=1:first_pts=0:min_hard_comp=0.001,aformat=sample_rates=48000:channel_layouts=stereo,{fi}{fo}volume={vol},adelay={ms(e['tl'][0] + nf - e['in'])}[na{e['id']}]"); mix.append(f"[na{e['id']}]"); n += 1; used['native:' + e['id']] = f"{e['take']} from take {nf}"
        # NO loudness processing in the master: a single-pass loudnorm is DYNAMIC — it rides the programme, lifting the bed in
        # every gap between lines, and every later stage inherits a ride it cannot undo. The master is a static sum; deliver
        # sets the level once with one measured gain (spot-audio-assembly MIX-AND-QC.md § The delivery loudness pass).
        au.append(''.join(mix) + f"amix=inputs={len(mix)}:normalize=0,atrim=0:{RUN}[aout]")
        run(['ffmpeg', '-v', 'error', '-y'] + inp + ['-filter_complex', ';'.join(v + au), '-map', '[vout]', '-map', '[aout]', '-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-r', str(FPS), '-c:a', 'pcm_s24le', '-ar', '48000', '-t', f'{RUN}', MASTER])
        print(probe(MASTER)); print('audio inputs used:', json.dumps(used))
        provenance(MASTER, FOOT)
    # ---- 3. deliverable: downscale from the mezzanine, H.264 ----
    if a.stage in ('deliver', 'all'):
        ln = AU.get('loudnorm', {'I': -14, 'TP': -1, 'LRA': 9})
        meas = subprocess.run(['ffmpeg', '-v', 'info', '-i', MASTER, '-af', f"loudnorm=I={ln['I']}:TP={ln['TP']}:LRA={ln['LRA']}:print_format=json", '-f', 'null', '-'], capture_output=True, text=True).stderr
        m = json.loads(meas[meas.rfind('{'):meas.rfind('}') + 1])   # a MEASUREMENT of the master; nothing below applies loudnorm
        # ONE static gain, never loudnorm: `linear=true` is a request, not a guarantee — loudnorm falls back to DYNAMIC, silently,
        # whenever the linear gain would push the true peak past its TP target. A static gain plus oversampled PEAK limiting reaches
        # the target without moving the programme level; the limiter acts on peaks at 5/60 ms, not on a loudness window.
        mi, mtp, TPT = float(m['input_i']), float(m['input_tp']), float(ln['TP']); g = float(ln['I']) - mi; over = mtp + g - TPT
        print(f"loudness: measured I {mi:.2f} LUFS / TP {mtp:.2f} dBTP -> static gain {g:+.2f} dB -> "
              + (f"PEAK LIMITING {over:.2f} dB to hold TP {TPT:g}" if over > 0 else f"limiting-free, {-over:.2f} dB under TP {TPT:g}")
              + f"; the loudest limiting-free target on this mix is {mi - mtp + TPT:.1f} LUFS", flush=True)
        subprocess.run([sys.executable, os.path.expanduser(a.captions_builder), '--root', '.', '--edl', a.edl], check=True)   # cards at delivery res, overlaid AFTER the downscale
        CAPD = AU.get('captions_dir', 'edit/captions'); caps = json.load(open(f'{CAPD}/manifest.json')) if os.path.exists(f'{CAPD}/manifest.json') else []
        cin = []; chain = f'[0:v]scale={edl.get("canvas", [1080, 1920])[0]}:{edl.get("canvas", [1080, 1920])[1]}:flags=lanczos,format=yuv420p[v0]'; last = 'v0'
        for k, c in enumerate(caps):
            # HALF-OPEN, never between(): between(t,a,b) is inclusive at BOTH ends, so two cards that share a
            # boundary (every word-highlight layer inside one card does — build_captions.py hands layer k the
            # t1 that is layer k+1's t0) BOTH composite on the frame that lands exactly on it. Measured
            # 2026-09-17, 24 fps, boundary t=1.0: with between() one frame showed both layers; with
            # gte()*lt() zero frames showed both AND zero showed neither. An epsilon trim is the wrong fix —
            # it trades a measure-zero double for a real uncovered window.
            cin += ['-i', c['file']]; chain += f";[{k + 1}:v]{TO709},format=yuva420p[c{k}];[{last}][c{k}]overlay=0:0:enable='gte(t,{c['tl'][0]})*lt(t,{c['tl'][1]})'[v{k + 1}]"; last = f'v{k + 1}'   # the RGBA card converts by the named matrix first
        if edl.get('poster_at') is not None:   # the platform thumbnail is frame 0 (X, Slack, Discord): bake the chosen master frame there (brag)
            k = len(caps) + 1; cw, chh = edl.get("canvas", [1080, 1920]); pss = max(0.0, int(float(edl['poster_at']) * FPS + 1e-6) / FPS - 0.25 / FPS)   # the frame ON SCREEN at poster_at
            cin += ['-ss', f"{pss:.4f}", '-i', MASTER]
            chain += f";[{k}:v]scale={cw}:{chh}:flags=lanczos,format=yuv420p,trim=end_frame=1,setpts=PTS-STARTPTS[pst];[{last}][pst]overlay=eof_action=pass:enable='eq(n,0)'[vpst]"; last = 'vpst'
        lim = f"alimiter=limit={10 ** (ln['TP'] / 20):.4f}:attack=5:release=60:level=false:latency=1"   # latency=1: the lookahead is compensated — two limiters left the audio 10 ms late (av_sync_regress.py, 2026-09-29)
        af = f"volume={g:.3f}dB,aresample=192000,{lim},aresample=48000,{lim}"   # limit at 192 kHz, where inter-sample peaks are visible; 48 kHz; limit again
        # Measured on a real master (TP target -2.4, AAC 192k): limiter after the resample only -> -1.0 dBTP; before only -> -2.0; both -> -2.1; none -> -1.9.
        print(f"deliver encode: libx264 {' '.join(VENC)}" + (' (deliver_encode)' if edl.get('deliver_encode') else ''), flush=True)
        run(['ffmpeg', '-v', 'error', '-y', '-i', MASTER] + cin + ['-filter_complex', chain, '-map', f'[{last}]', '-map', '0:a', '-af', af, '-ar', '48000', '-c:v', 'libx264'] + VENC + ['-profile:v', 'high', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-level', '4.1', '-g', str(2 * FPS), '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-t', f'{RUN}', DELIV])   # -t: the picture is authoritative — without it AAC priming + padding set the container duration
        print(probe(DELIV)); print(os.path.getsize(DELIV) / 1e6, 'MB', DELIV)
        # the limiter's cut INSIDE each designed impact: the total hides a limiter that takes dB off exactly the loudest moments
        # the mix was built around (makevoid/motion-graphics-music-video-skill sfx_mix.py). Rendered twice; a read, not a gate.
        try:   # a read, never a gate: a failure here leaves the deliverable standing and says so
            LJ = f'edit/mezz/{os.path.basename(DELIV)}.limiter.json'   # beside the provenance record, never in deliver/: the client folder
            if over > -0.05: lc = limiter_cut(MASTER, g, lim, impact_windows(AU))
            else: lc = {'per_100ms': [], 'deepest': {'t': 0.0, 'db': 0.0}, 'note': 'limiting-free: the peak after the gain sits under the TP target, so nothing was rendered',
                        'windows': [{'from': a_, 'to': b_, 'source': s_, 'deepest_cut_db': 0.0} for a_, b_, s_ in impact_windows(AU)]}
            lc.update({'deliverable': DELIV, 'sha256': _sha256(DELIV), 'gain_db': round(g, 3), 'tp_target': TPT, 'limiting_db': round(over, 2)})
            json.dump(lc, open(LJ, 'w'), indent=1)
            print('limiter: ' + '; '.join(f"{w['from']:.2f} s {w['deepest_cut_db']:.1f} dB ({w['source']})" for w in lc['windows'])
                  + f"; deepest anywhere {lc['deepest']['db']:.1f} dB at {lc['deepest']['t']:.2f} s -> {LJ}", flush=True)
        except Exception as ex:   # the record is REPLACED by a failure note: a previous render's cuts must never read as this one's
            try:
                json.dump({'deliverable': DELIV, 'sha256': _sha256(DELIV), 'failed': f'{type(ex).__name__}: {ex}'}, open(f'edit/mezz/{os.path.basename(DELIV)}.limiter.json', 'w'), indent=1)
                said = 'the record says so'
            except Exception as ex2: said = f'and its failure record could not be written either ({type(ex2).__name__}) — sound_table will read no record'
            print(f'limiter: the read failed ({type(ex).__name__}: {ex}) — the deliverable stands; {said}', flush=True)
        provenance(DELIV, MASTER)
    print('FINISH-END stage', a.stage)


if __name__ == '__main__':
    main()
