#!/usr/bin/env python3
"""finish_spot.py — the EDL-driven finish of one spot, in video-finish's order: upscale (already done, per shot) →
grade (a cube on upscaled mezzanines; heroes arrive pre-graded, look "none") → composite (post layers + the end card, when
the EDL has one) → mix → downscale → encode. Three stages, each re-runnable:
  cut      edit/mezz/<SPOT>-footage-graded<tag>.mov   ProRes 422 HQ 10-bit 4:2:2 at the mezzanine raster, footage only
  master   edit/mezz/<SPOT>-master-<W>x<H><tag>.mov   + layers + card, PCM 24-bit STATIC mix (the VO stem is REBUILT first); no
                                                      loudness processing — the master is a mix, the level is set once, at deliver
  deliver  deliver/<deliver_base><tag|-v1>.mp4        measure → ONE static gain to the EDL's I → aresample 192 kHz → alimiter at TP →
                                                      aresample 48k → alimiter again (the limiting the target costs is printed);
                                                      captions overlaid AFTER the downscale; H.264 High CRF 17 slow, AAC 192k,
                                                      faststart, the length capped at runtime_s
The script-fidelity gate (beat_sheet.py) runs BEFORE stage 1 when the beats file exists: a FAIL = no finish. A spot with no
role:"endcard" event (a beat list may forbid a card) cuts its footage at the runtime.

  finish_spot.py --root <project> --edl edit/<SPOT>-EDL.json [--stage cut|master|deliver|all] [--look ads-clean]
                 [--in-dir edit/upscale-out] [--tag=-v3] [--cubes <dir of <look>_33.cube>] [--canvas 2160x3840] [--fps 24]
                 [--beat-gate <beat_sheet.py>] [--stem-builder <build_vo_stem.py>] [--captions-builder <build_captions.py>] [--no-gate]
Sources per event: designed → its own render at native raster; generated → <in-dir>/<id>.mov | <id>__*.mov | <id>.mp4,
or the event's own `src` (a hero under a fresh name), sought by handle_head (a FULL-TAKE hero needs handle_head = in).
Prints FINISH-END <stage> as the sentinel; a log without it is a failure whatever the file sizes say.
Before any stage the HOST drive's free space is read; under the floor (--min-free-gb 40, or 3x the spot's estimated mezzanine
pair) the finish refuses to start — a mezzanine pair per version fills a drive, and on a VM the guest's free space is not the
host's.
"""
import argparse, glob, json, os, subprocess, sys

SK = os.path.expanduser('~/.claude/skills')


def ff_path(p):
    """A file path inside a filter graph is parsed TWICE (the graph, then the filter's options), so every special character is
    escaped for both: backslashes become slashes, a drive colon `D:` becomes `D\\\\:`, and `' ; , [ ]` take one backslash.
    Without it every caption / LUT job on a Windows path fails inside ffmpeg (ffmpeg-skill measured it on 8.1 / 9.0)."""
    p = p.replace('\\', '/')
    for ch, rep in ((':', '\\\\:'), ("'", "\\'"), (';', '\\;'), (',', '\\,'), ('[', '\\['), (']', '\\]')): p = p.replace(ch, rep)
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default='.'); ap.add_argument('--edl', required=True); ap.add_argument('--stage', default='all', choices=['cut', 'master', 'deliver', 'all'])
    ap.add_argument('--look', default='ads-clean'); ap.add_argument('--in-dir', default='edit/upscale-out'); ap.add_argument('--tag', default='')
    ap.add_argument('--cubes', default=os.environ.get('LOOK_LIBRARY_CUBES', os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'look-library', 'cubes')), help='the baked <look>_33.cube files (look-library/GUIDE.md: bake them first)')
    ap.add_argument('--canvas', default='2160x3840'); ap.add_argument('--fps', type=int, default=24); ap.add_argument('--handle', type=float, default=None, help='default head handle for upscaled sources (default 4 frames)')
    ap.add_argument('--beat-gate', default=f'{SK}/video-edit-edl/scripts/beat_sheet.py'); ap.add_argument('--stem-builder', default=f'{SK}/spot-audio-assembly/scripts/build_vo_stem.py')
    ap.add_argument('--captions-builder', default=f'{SK}/spot-audio-assembly/scripts/build_captions.py'); ap.add_argument('--no-gate', action='store_true')
    ap.add_argument('--min-free-gb', type=float, default=40.0, help='the HOST drive floor under which no stage starts (or 3x the spot\'s mezzanine footprint, whichever is larger); --min-free-gb 0 disables')
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
        if _free < _floor: sys.exit(f'FINISH REFUSED: {_free:.0f} GB free on the drive holding the project, floor {_floor:.0f} GB (3x an estimated {_est:.1f} GB mezzanine pair, min {a.min_free_gb:g}). Free space or name superseded mezzanines for deletion (video-production/scripts/project_size.py); --min-free-gb 0 overrides.')
        print(f'disk: {_free:.0f} GB free, floor {_floor:.0f} GB', flush=True)
    W, H = (int(v) for v in a.canvas.lower().split('x')); FPS = a.fps; HANDLE = a.handle if a.handle is not None else 4 / FPS
    edl = json.load(open(a.edl, encoding='utf-8')); RUN = float(edl['runtime_s']); AU = edl['audio']; SPOT = edl.get('spot', 'SPOT'); DBASE = edl.get('deliver_base', SPOT)
    FOOT = f'edit/mezz/{SPOT}-footage-graded{a.tag}.mov'; MASTER = f'edit/mezz/{SPOT}-master-{W}x{H}{a.tag}.mov'; DELIV = f'deliver/{DBASE}{a.tag or "-v1"}.mp4'
    os.makedirs('edit/mezz', exist_ok=True); os.makedirs('deliver', exist_ok=True)
    ecs = [e for e in edl['events'] if e.get('role') == 'endcard']; assert len(ecs) <= 1, f'{len(ecs)} endcard events — at most one (role: endcard)'
    EC = ecs[0] if ecs else None   # optional: edl_check --require-endcard holds a card where the script has one
    ev = [e for e in edl['events'] if e.get('role') != 'endcard']
    for e in ev: assert e.get('take'), f"{e['id']}: take is null — pick a keeper in the EDL first"
    FOOT_END = float(EC['tl'][0]) if EC else RUN
    beats = f"prompts/{SPOT}-beats.json"
    if not a.no_gate and os.path.exists(beats):
        subprocess.run([sys.executable, os.path.expanduser(a.beat_gate), '--root', '.', '--edl', a.edl, '--beats', beats], check=True)   # SCRIPT-FIDELITY GATE: FAIL = no finish
    elif not a.no_gate: print(f'WARNING no beats file at {beats} — the script-fidelity gate did not run', flush=True)

    def run(cmd): print('$', ' '.join(cmd)[:400], flush=True); subprocess.run(cmd, check=True)

    def probe(p): return subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_frames,duration', '-of', 'default=nw=1', p], capture_output=True, text=True).stdout

    def first(pat):
        for p in (pat or '').split('|'):
            g = sorted(glob.glob(p))
            if g: return g[0]
        return None

    def ms(t): v = int(round(t * 1000)); return f'{v}|{v}'

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
            inputs += ['-ss', f'{ss:.6f}', '-t', f'{dur:.6f}', '-i', src]
            lut = f"format=gbrp16le,lut3d=file={ff_path(f'{a.cubes}/{look}_33.cube')}:interp=tetrahedral," if look != 'none' else ''   # look "none" = pre-graded hero (Resolve/Dehancer pass)
            z = float(e.get('zoom', 1) or 1); zc = ''
            if z > 1.0001:                                                                                   # per-event punch-in: crop 1/z around the anchor, then the normal scale
                ax, ay = e.get('anchor', [0.5, 0.5]); cw, ch = f'iw/{z:.4f}', f'ih/{z:.4f}'
                zc = f"crop={cw}:{ch}:clip((iw*{ax:.4f})-({cw})/2\\,0\\,iw-({cw})):clip((ih*{ay:.4f})-({ch})/2\\,0\\,ih-({ch})),"
            fc.append(f"[{i}:v]{zc}scale={W}:{H}:flags=lanczos,fps={FPS},{lut}format=yuv422p10le,setsar=1[v{i}]")
            print(e['id'], 'src', src, 'ss', round(ss, 4), 'look', look, 'dur', dur, 'tl', e['tl'])
        fc.append(''.join(f'[v{i}]' for i in range(len(ev))) + f'concat=n={len(ev)}:v=1:a=0[out]')
        run(['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex', ';'.join(fc), '-map', '[out]', '-c:v', 'prores_ks', '-profile:v', '3', '-vendor', 'apl0', '-pix_fmt', 'yuv422p10le', '-r', str(FPS), FOOT])
        print(probe(FOOT))
    # ---- 2. master: composite layers + end card at the mezzanine raster, mix the audio ----
    if a.stage in ('master', 'all'):
        subprocess.run([sys.executable, os.path.expanduser(a.stem_builder), '--root', '.', '--edl', a.edl], check=True)   # ALWAYS rebuild the stem from the EDL — a stale stem shipped a line at its old time
        inp = ['-i', FOOT] + (['-i', EC['take']] if EC else []) + ['-i', AU['vo']['stem']]
        STEM = 2 if EC else 1; n = STEM + 1   # input indices are DERIVED — a hard-coded stem index is where a card-less patch breaks the audio map
        v = ([f"[1:v]scale={W}:{H}:flags=lanczos,format=yuv422p10le,setpts=PTS-STARTPTS[ec]"] if EC else []) + ["[0:v]format=yuv422p10le,tpad=stop_mode=clone:stop_duration=0.05[b0]"]; last = 'b0'
        for k, L in enumerate(edl.get('post_layers', [])):
            inp += ['-framerate', str(FPS), '-i', L['frames']]
            v.append(f"[{n}:v]scale={W}:{H}:flags=lanczos,format=rgba,setpts=PTS-STARTPTS+{L['at']}/TB[ov{k}]"); n += 1
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
            if m.get('duck'):                              # ducks [[tl_from, tl_to, gain]] in TIMELINE seconds — linear ramps of duck_ramp s either side, per frame in cue-local time
                r = float(m.get('duck_ramp', 0.25)); ex = '1'
                for da, db, dg in m['duck']:
                    la, lb = da - t0, db - t0; assert 0 <= la < lb <= d + 1e-6, (name, 'duck outside the cue span', da, db, t0, t1)
                    ex = f"({ex})*if(lt(t\\,{la - r:.3f})\\,1\\,if(lt(t\\,{la:.3f})\\,1-(1-{dg})*(t-{la - r:.3f})/{r}\\,if(lt(t\\,{lb:.3f})\\,{dg}\\,if(lt(t\\,{lb + r:.3f})\\,{dg}+(1-{dg})*(t-{lb:.3f})/{r}\\,1))))"
                ch += f",volume=volume={m.get('vol', 0.7)}*{ex}:eval=frame,adelay={ms(t0)}[{name}]"
            else: ch += f",volume={m.get('vol', 0.7)},adelay={ms(t0)}[{name}]"
            au.append(ch); mix.append(f'[{name}]'); used[name] = f
        for e in ev:                                   # the take's own audio as a bed, only when the keeper earned it
            vol = e.get('native_audio_vol', 0)
            if not vol: continue
            nf = float(e.get('native_audio_from', e['in'])); assert e['in'] <= nf < e['out'], f"{e['id']}: native_audio_from outside [in,out)"
            nt = float(e.get('native_audio_to', e['out'])); assert nf < nt <= e['out'], f"{e['id']}: native_audio_to outside (from,out]"
            inp += ['-ss', f"{nf:.4f}", '-t', f"{nt - nf:.4f}", '-i', e['take']]
            fi = 'afade=t=in:st=0:d=0.02,' if nf > e['in'] else ''; fo = f"afade=t=out:st={max(0, nt - nf - 0.03):.3f}:d=0.03," if nt < e['out'] else ''
            au.append(f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,{fi}{fo}volume={vol},adelay={ms(e['tl'][0] + nf - e['in'])}[na{e['id']}]"); mix.append(f"[na{e['id']}]"); n += 1; used['native:' + e['id']] = f"{e['take']} from take {nf}"
        # NO loudness processing in the master: a single-pass loudnorm is DYNAMIC — it rides the programme, lifting the bed in
        # every gap between lines, and every later stage inherits a ride it cannot undo. The master is a static sum; deliver
        # sets the level once with one measured gain (spot-audio-assembly MIX-AND-QC.md § The delivery loudness pass).
        au.append(''.join(mix) + f"amix=inputs={len(mix)}:normalize=0,atrim=0:{RUN}[aout]")
        run(['ffmpeg', '-v', 'error', '-y'] + inp + ['-filter_complex', ';'.join(v + au), '-map', '[vout]', '-map', '[aout]', '-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le', '-r', str(FPS), '-c:a', 'pcm_s24le', '-ar', '48000', '-t', f'{RUN}', MASTER])
        print(probe(MASTER)); print('audio inputs used:', json.dumps(used))
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
            cin += ['-i', c['file']]; chain += f";[{last}][{k + 1}:v]overlay=0:0:enable='between(t,{c['tl'][0]},{c['tl'][1]})'[v{k + 1}]"; last = f'v{k + 1}'
        lim = f"alimiter=limit={10 ** (ln['TP'] / 20):.4f}:attack=5:release=60:level=false"
        af = f"volume={g:.3f}dB,aresample=192000,{lim},aresample=48000,{lim}"   # limit at 192 kHz, where inter-sample peaks are visible; 48 kHz; limit again
        # Measured on a real master (TP target -2.4, AAC 192k): limiter after the resample only -> -1.0 dBTP; before only -> -2.0; both -> -2.1; none -> -1.9.
        run(['ffmpeg', '-v', 'error', '-y', '-i', MASTER] + cin + ['-filter_complex', chain, '-map', f'[{last}]', '-map', '0:a', '-af', af, '-ar', '48000', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-tune', 'film', '-profile:v', 'high', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-level', '4.1', '-g', str(2 * FPS), '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-t', f'{RUN}', DELIV])   # -t: the picture is authoritative — without it AAC priming + padding set the container duration
        print(probe(DELIV)); print(os.path.getsize(DELIV) / 1e6, 'MB', DELIV)
    print('FINISH-END stage', a.stage)


if __name__ == '__main__':
    main()
