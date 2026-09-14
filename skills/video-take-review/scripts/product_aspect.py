#!/usr/bin/env python3
"""product_aspect.py — MEASURE a held product's proportions in a take (a cross-check for the client's "too big / too wide" note):
per sampled frame, the product = the largest blob of saturated label colours inside --box (x0,y0,x1,y1 in frame px); its principal
axis (PCA) gives length and width → width:length. ⚠ BLIND at 480p: a known-good 1:4.75 tube read 1:2.6 at 30 px, and burst
frames merge blobs — the number of record is a 4× visual crop beside the product photo, on the upscaled frame when one exists.
Usage: product_aspect.py <take.mp4> --from 1.0 --to 3.0 [--step 0.25] [--box 0,0,480,600] [--minsat 110] [--sku-aspect 4.75]"""
import sys, subprocess, numpy as np
if '--help' in sys.argv or '-h' in sys.argv or len(sys.argv) < 2:
    print(__doc__); sys.exit(0)
from PIL import Image
from io import BytesIO
from scipy import ndimage
A={}; k=None; pos=[]
for a in sys.argv[1:]:
    if a.startswith('--'): k=a; A[k]=True
    elif k: A[k]=a; k=None
    else: pos.append(a)
take=pos[0]; t0=float(A.get('--from',0)); t1=float(A.get('--to',3)); st=float(A.get('--step',0.25)); ms=int(A.get('--minsat',110))
box=[int(v) for v in A.get('--box','0,0,480,854').split(',')]; SKU=float(A.get('--sku-aspect',4.75))
vals=[]; t=t0
while t<=t1+1e-9:
    r=subprocess.run(['ffmpeg','-v','error','-ss',f'{t:.3f}','-i',take,'-frames:v','1','-f','image2pipe','-vcodec','png','-'],capture_output=True).stdout
    im=Image.open(BytesIO(r)).convert('RGB'); hsv=np.asarray(im.convert('HSV')).astype(int)
    m=np.zeros(hsv.shape[:2],bool); x0,y0,x1,y1=box; sub=hsv[y0:y1,x0:x1]
    # label colours: saturated and not skin (skin hue ~10-30 at low-mid sat); keep sat>ms and value>60
    mm=(sub[...,1]>ms)&(sub[...,2]>60)&~((sub[...,0]>5)&(sub[...,0]<35)&(sub[...,1]<170))
    mm&=~(((sub[...,0]<15)|(sub[...,0]>235))&(sub[...,2]<175))   # exclude dark reds (clothing); the label's red band is brighter
    mm=ndimage.binary_opening(mm,iterations=1); mm=ndimage.binary_closing(mm,iterations=2)
    lab,n=ndimage.label(mm)
    if n==0: print(f'{t:6.2f}s  no product blob'); t+=st; continue
    sizes=ndimage.sum(mm,lab,range(1,n+1)); j=int(np.argmax(sizes))+1; ys,xs=np.where(lab==j)
    pts=np.stack([xs,ys],1).astype(float); pts-=pts.mean(0); u,s,vt=np.linalg.svd(pts,full_matrices=False); proj=pts@vt.T
    L=proj[:,0].max()-proj[:,0].min(); Wd=proj[:,1].max()-proj[:,1].min(); asp=Wd/max(L,1)
    vals.append(asp); print(f'{t:6.2f}s  blob {int(sizes[j-1])} px  length {L:5.1f}  width {Wd:5.1f}  width:length 1:{1/max(asp,1e-6):.2f}')
    t+=st
if vals: print(f'MEDIAN width:length = 1:{1/np.median(vals):.2f}   (SKU = 1:{SKU:.2f}; a cross-check only — blind at 480p)')
