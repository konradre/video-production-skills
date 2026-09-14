#!/usr/bin/env python3
"""qc_seed.py — the per-seed READ (continuity = the FIRST acceptance test). For one take: cut list (per-frame diff on a
48x27 grey thumb — a cut is a one-frame SPIKE: above --thr AND above --ratio × the median of its ±12 neighbours, so a pan,
a burst or a flash is not a cut), a CONTINUITY SHEET = plate | first frame of EVERY cut | last frame, a fps=1 frames tile,
the native-audio RMS peak (a hit shows as the max 25 ms window), and a faster-whisper transcript of the native audio.
Usage: qc_seed.py <take.mp4> [--plate <png>] [--out review] [--thr 0.12] [--ratio 3] [--no-whisper] [--record]
       qc_seed.py <take.mp4> --read            print the take's record if it is FRESH (bytes, then sha256); exit 1 if stale/missing
       qc_seed.py <take.mp4> --note "text"     append a reviewer note to a FRESH record (never edits the measurements)
       qc_seed.py --selftest                   the cut rule on synthetic frames: one hard cut found, a 40-frame pan found NOT a cut
The record (--record) is `<take>.review.json` beside the take: sha256 + bytes of the take, every measurement with the rule
that produced it, the sheet path, and notes[] — a resumed session reads the record FIRST and re-views strips only for the
claim it acts on. A record whose bytes/sha256 no longer match the take is STALE and is refused, never trusted or hand-fixed.
Self-test: the printed cut list is checked against the frame count (every cut index < n); --selftest proves the rule."""
import sys, os, subprocess, json, hashlib, time, numpy as np
if '--help' in sys.argv or '-h' in sys.argv or len(sys.argv) < 2:
    print(__doc__); sys.exit(0)
A={}; k=None; pos=[]
for a in sys.argv[1:]:
    if a.startswith('--'):
        k=a; A[k]=True
    elif k and A.get(k) is True and k in ('--plate','--out','--thr','--ratio','--note'): A[k]=a; k=None
    else: pos.append(a); k=None
RATIO=float(A.get('--ratio',3.0)) if A.get('--ratio') not in (None,True) else 3.0
thr=float(A.get('--thr',0.12)) if A.get('--thr') not in (None,True) else 0.12   # measured 2026-09-10: 0.12 + the ratio matched ffmpeg scene>0.3 frame for frame on 22 takes; 0.28 alone found 1 of 13 cuts

def cut_frames(d, thr, ratio, merge=4, win=12):
    """Cut = frame i whose diff is above thr AND above ratio × the median of the ±win neighbours (i excluded). Cuts closer than
    `merge` frames collapse to the first. A cut is a one-frame spike; sustained motion raises many consecutive diffs and fails the
    ratio, a real cut stands alone (the rule ffmpeg-skill measured to double precision at equal recall)."""
    cuts=[]
    for i,v in enumerate(d):
        if v<=thr: continue
        nb=np.concatenate([d[max(0,i-win):i], d[i+1:i+1+win]])
        med=float(np.median(nb)) if len(nb) else 0.0
        if v>ratio*med: cuts.append(i+1)
    m=[]
    for c in cuts:
        if not m or c-m[-1]>merge: m.append(c)
    return m

def selftest():
    """Three synthetic sequences on the 48x27 grey thumb: a hard cut in a static shot; 40 frames of sustained fast motion (every
    diff above thr — the case the threshold-only rule mis-read as 39 cuts); a SLOW pan (a smooth field shifted 1 px per frame,
    diffs below thr) followed by a hard cut. The rule must find [40], [], [40]."""
    rng=np.random.default_rng(7); Aimg=rng.random((27,48)); Bimg=1.0-Aimg
    seq=np.stack([Aimg]*40+[Bimg]*40); d=np.abs(seq[1:]-seq[:-1]).mean((1,2)); hard=cut_frames(d,thr,RATIO)
    fast=rng.random((27,48+40)); pan=np.stack([fast[:,i:i+48] for i in range(40)]); dp=np.abs(pan[1:]-pan[:-1]).mean((1,2))
    old=[i+1 for i,v in enumerate(dp) if v>thr]; motion=cut_frames(dp,thr,RATIO)
    k=np.ones(9)/9; smooth=np.apply_along_axis(lambda r: np.convolve(r,k,mode='same'), 1, rng.random((27,48+40)))
    bright=0.9+0.1*rng.random((27,48))   # the cut after the pan: a smooth mid-grey field to a near-white frame
    slow=np.stack([smooth[:,i:i+48] for i in range(40)]); seq2=np.concatenate([slow, np.stack([bright]*20)]); d2=np.abs(seq2[1:]-seq2[:-1]).mean((1,2)); mixed=cut_frames(d2,thr,RATIO)
    ok = hard==[40] and motion==[] and mixed==[40]
    print(f"selftest  static+cut → {hard} (want [40]) | sustained fast motion (diffs {dp.min():.2f}–{dp.max():.2f}): threshold-only {len(old)} cuts, spike rule {motion} (want []) | slow pan (diffs ≈ {d2[:39].mean():.3f}) then cut → {mixed} (want [40]) → {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
if A.get('--selftest'): selftest()

take=pos[0]; name=os.path.splitext(os.path.basename(take))[0]; REC=take+'.review.json'
def fingerprint(p):
    h=hashlib.sha256(); n=0
    with open(p,'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''): h.update(chunk); n+=len(chunk)
    return h.hexdigest(), n
def load_fresh():
    """The record is FRESH iff bytes match (O(1)) and then sha256 matches; anything else is refused (exit 1)."""
    if not os.path.exists(REC): print(f'NO RECORD {REC}'); sys.exit(1)
    r=json.load(open(REC,encoding='utf-8')); size=os.path.getsize(take)
    if size!=r.get('bytes'): print(f'STALE record {REC}: bytes {size} != {r.get("bytes")} — re-run --record'); sys.exit(1)
    sha,_=fingerprint(take)
    if sha!=r.get('sha256'): print(f'STALE record {REC}: sha256 differs — re-run --record'); sys.exit(1)
    return r
if A.get('--read'):
    r=load_fresh(); print(json.dumps(r,indent=1,ensure_ascii=False)); sys.exit(0)
if A.get('--note') not in (None,True):
    r=load_fresh(); r.setdefault('notes',[]).append({'ts':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'text':A['--note']})
    json.dump(r,open(REC,'w',encoding='utf-8'),indent=1,ensure_ascii=False); print(f'note appended → {REC} ({len(r["notes"])} notes)'); sys.exit(0)

from PIL import Image, ImageDraw
out=A.get('--out','review') if A.get('--out') not in (None,True) else 'review'; os.makedirs(out,exist_ok=True)
def run(c): return subprocess.run(c,capture_output=True,text=True)
p=run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=r_frame_rate,nb_frames,width,height','-of','json',take]); st=json.loads(p.stdout)['streams'][0]
num,den=st['r_frame_rate'].split('/'); fps=float(num)/float(den); W,H=int(st['width']),int(st['height'])
# 1. per-frame diff on a tiny grey thumb → the spike rule
raw=subprocess.run(['ffmpeg','-v','error','-i',take,'-vf','scale=48:27,format=gray','-f','rawvideo','-'],capture_output=True).stdout
fr=np.frombuffer(raw,np.uint8).reshape(-1,27,48).astype(float)/255; n=len(fr)
d=np.abs(fr[1:]-fr[:-1]).mean((1,2)); cuts=cut_frames(d,thr,RATIO); dur=n/fps
assert all(0 < c < n for c in cuts), 'cut index outside the frame range — instrument broken'
print(f'{name}: {n} f @ {fps:.3f} fps = {dur:.3f} s · {W}x{H} · cuts at frames {cuts} = ' + ', '.join(f'{c/fps:.3f}' for c in cuts) + f'  (spike rule: > {thr} and > {RATIO:g}× the ±12 median)')
# 2. continuity sheet: plate | first frame of every cut | last frame
def frame(i):
    r=subprocess.run(['ffmpeg','-v','error','-i',take,'-vf',f'select=eq(n\\,{i})','-vframes','1','-f','image2pipe','-vcodec','png','-'],capture_output=True).stdout
    from io import BytesIO; return Image.open(BytesIO(r)).convert('RGB')
idx=[0]+cuts+[n-1]; tiles=[]; labels=[]
if A.get('--plate') not in (None,True): tiles.append(Image.open(A['--plate']).convert('RGB')); labels.append('PLATE')
for i in idx: tiles.append(frame(i)); labels.append(f'f{i} {i/fps:.2f}s')
h=640; tiles=[t.resize((int(t.width*h/t.height),h)) for t in tiles]
sheet=Image.new('RGB',(sum(t.width for t in tiles)+8*(len(tiles)-1),h+22),'black'); x=0; dr=ImageDraw.Draw(sheet)
for t,l in zip(tiles,labels): sheet.paste(t,(x,22)); dr.text((x+4,4),l,fill='white'); x+=t.width+8
sp=f'{out}/{name}-sheet.jpg'; sheet.save(sp,quality=85)   # SURVEY image: JPEG q85 — a lossless full-frame sheet costs ~8x the bytes for the same read (INSTRUMENTS § review images)
# 3. fps=1 frames tile (survey, JPEG)
subprocess.run(['ffmpeg','-v','error','-y','-i',take,'-vf',f'fps=1,scale=-2:400,tile={int(np.ceil(dur))}x1','-frames:v','1','-q:v','3',f'{out}/{name}-frames.jpg'])
# 4. audio RMS peak (25 ms windows)
wav=subprocess.run(['ffmpeg','-v','error','-i',take,'-ac','1','-ar','16000','-f','s16le','-'],capture_output=True).stdout
s=np.frombuffer(wav,np.int16).astype(float)/32768; win=400; k2=len(s)//win; rms=np.sqrt((s[:k2*win].reshape(k2,win)**2).mean(1)) if k2 else np.array([1e-9]); pk=int(np.argmax(rms))
peak_db=20*np.log10(rms[pk]+1e-9); mean_db=20*np.log10(rms.mean()+1e-9)
print(f'audio: peak RMS {peak_db:.1f} dBFS at {pk*0.025:.3f} s; mean {mean_db:.1f} dBFS')
# 5. transcript
words=[]
if not A.get('--no-whisper'):
    try:
        from faster_whisper import WhisperModel
        mdl=WhisperModel('base',device='cpu',compute_type='int8'); segs,_=mdl.transcribe(take,word_timestamps=True)
        for sg in segs:
            print(f'  {sg.start:6.2f}–{sg.end:6.2f}  {sg.text.strip()}'); words.append({'start':round(sg.start,3),'end':round(sg.end,3),'text':sg.text.strip()})
    except Exception as e: print('whisper skipped:',e)
print('sheet',sp)
# 6. the record beside the take (hash-bound; measurements carry their instrument and rule)
if A.get('--record'):
    sha,size=fingerprint(take)
    rec={'video':os.path.basename(take),'sha256':sha,'bytes':size,'created':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'generator':'video-take-review/qc_seed.py',
         'fps':fps,'frames':n,'width':W,'height':H,'duration_s':round(dur,4),
         'cuts':{'frames':cuts,'times_s':[round(c/fps,3) for c in cuts],'instrument':'mean |Δ| on a 48x27 grey thumb','rule':f'> {thr} and > {RATIO:g}× the median of the ±12 neighbours; merges < 4 frames'},
         'audio_peak':{'t_s':round(pk*0.025,3),'dbfs':round(float(peak_db),1),'mean_dbfs':round(float(mean_db),1),'instrument':'RMS in 25 ms windows, mono 16 kHz'},
         'transcript':{'segments':words,'instrument':'faster-whisper base int8' if words else 'none'},
         'sheet':sp,'notes':[]}
    if os.path.exists(REC):
        try: rec['notes']=json.load(open(REC,encoding='utf-8')).get('notes',[])   # notes survive a re-measure of the SAME bytes only
        except Exception: pass
        if rec['notes'] and json.load(open(REC,encoding='utf-8')).get('sha256')!=sha: rec['notes']=[]
    json.dump(rec,open(REC,'w',encoding='utf-8'),indent=1,ensure_ascii=False); print('record',REC)
