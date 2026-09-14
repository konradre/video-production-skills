#!/usr/bin/env python3
"""hyper_new.py — scaffold a HyperFrames composition project that already obeys the contract the renderer needs:
#root carries data-composition-id / data-width / data-height / data-duration / data-fps, one paused GSAP timeline is
registered on window.__timelines[id] (+ __hfForceTimelineRebind), every random number comes from a SEEDED PRNG, fonts and
images are local files under assets/, and the length is baked into the project NAME (a new length = a new project).

  hyper_new.py --out hyper/<name> --kind card|turntable|layer [--dur 2.5] [--fps 24] [--canvas 2160x3840] [--seed 606] [--hf-version 0.8.18]

  card       an end card: wordmark + character slots (assets/wordmark.png, assets/character.png), a seeded canvas burst that
             fires at T0 (sync it to the sound's hit — e.g. a hit at +0.83 s in the sfx file, the file placed at card+0.02 s)
  turntable  a product on a studio turntable: a CSS-3D cylinder built from the label texture (assets/tex-product.png, N strips
             rotateY·translateZ, a shading overlay and a cap disc) — packaging is DESIGNED, never generated (a gen printed "WARNIGY")
  layer      a transparent element for the finisher's post_layers (a piece wall / a drift): canvas over a transparent body,
             rendered as a PNG sequence with alpha (frames/frame_%06d.png)
"""
import argparse, json, os

GSAP = '<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>'
PRNG = "function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;}}"
REG = "window.__timelines=window.__timelines||{}; window.__timelines[ID]=tl; if(window.__hfForceTimelineRebind) window.__hfForceTimelineRebind();"


def head(title, W, H, bg):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{title}</title>
{GSAP}
<style>
  @font-face {{ font-family:'Display'; src:url('assets/fonts/Display.ttf') format('truetype'); }}
  html, body {{ margin:0; background:{bg}; }}
  #root {{ position:relative; width:{W}px; height:{H}px; overflow:hidden; background:{bg}; }}
  .clip {{ position:absolute; inset:0; }}
</style>
</head>
<body>"""


def root(name, W, H, dur, fps):
    return f'<div id="root" data-composition-id="{name}" data-start="0" data-width="{W}" data-height="{H}" data-duration="{dur}" data-fps="{fps}">\n<section class="clip" data-start="0" data-duration="{dur}">'


def card(name, W, H, dur, fps, seed):
    return head(f'{name} — end card', W, H, '#111') + f"""
<style>
  #wordmark {{ position:absolute; left:{int(W*0.03)}px; top:{int(H*0.04)}px; width:{int(W*0.94)}px; transform-origin:50% 55%; }}
  #character {{ position:absolute; left:{int(W*0.13)}px; top:{int(H*0.37)}px; width:{int(W*0.6)}px; transform-origin:50% 100%; }}
  canvas {{ position:absolute; left:0; top:0; }}
</style>
{root(name, W, H, dur, fps)}
  <canvas id="burst" width="{W}" height="{H}"></canvas>
  <img id="character" src="assets/character.png" alt="" />
  <img id="wordmark" src="assets/wordmark.png" alt="" />
</section>
</div>
<script>
(function(){{
  var ID='{name}', W={W}, H={H};
  {PRNG}
  var rnd=mulberry32({seed}), T0=0.83, G=3000, P=[];          // T0 = the hit the burst fires on (the sound decides it; the COMP constant moves)
  for(var i=0;i<420;i++){{ var a=-Math.PI/2+(rnd()-0.5)*1.4, sp=1400+rnd()*1600; P.push({{x:W*(0.3+0.4*rnd()), y:H*0.62, vx:Math.cos(a)*sp, vy:Math.sin(a)*sp, r:rnd()*6.28, w:(rnd()-0.5)*12, s:0.6+rnd()*1.0, d0:rnd()*0.12, k:i%3}}); }}
  var cv=document.getElementById('burst'), cx=cv.getContext('2d'), st={{t:0}};
  function draw(){{ var t=st.t; cx.clearRect(0,0,W,H);
    for(var i=0;i<P.length;i++){{ var p=P[i], u=t-T0-p.d0; if(u<=0) continue; var x=p.x+p.vx*u, y=p.y+p.vy*u+0.5*G*u*u; if(y>H+100) continue;
      cx.save(); cx.translate(x,y); cx.rotate(p.r+p.w*u); cx.fillStyle=['#ff4fa3','#ffe7b0','#ffffff'][p.k]; var s=44*p.s; cx.fillRect(-s/2,-s/4,s,s/2); cx.restore(); }} }}
  var tl=gsap.timeline({{paused:true}});
  tl.from('#wordmark',{{scale:1.32,rotation:-7,opacity:0,duration:0.38,ease:'back.out(1.7)'}},0.05);
  tl.from('#character',{{y:160,opacity:0,duration:0.42,ease:'power3.out'}},0.14);
  tl.to(st,{{t:{dur},duration:{dur},ease:'none',onUpdate:draw}},0);
  draw(); {REG}
}})();
</script>
</body>
</html>
"""


def turntable(name, W, H, dur, fps, seed):
    return head(f'{name} — product turntable', W, H, '#e6e6e6') + f"""
<style>
  #root {{ background: radial-gradient(ellipse at 50% 32%, #ffffff 0%, #f4f4f4 42%, #dcdcdc 100%); }}
  #disc {{ position:absolute; left:50%; top:{int(H*0.77)}px; width:{int(W*0.7)}px; height:{int(W*0.18)}px; margin-left:-{int(W*0.35)}px; border-radius:50%;
           background: radial-gradient(ellipse at 50% 42%, #ffffff 0%, #f7f7f7 55%, #e4e4e4 100%); box-shadow: 0 36px 70px rgba(0,0,0,.2), 0 6px 14px rgba(0,0,0,.1); }}
  #scene {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; perspective:{int(W*3.3)}px; perspective-origin:50% 40%; }}
  #stage {{ position:absolute; left:50%; top:{int(H*0.84)}px; width:0; height:0; transform-style:preserve-3d; transform:rotateX(-5deg); }}
  #cyl {{ position:absolute; left:0; top:0; width:0; height:0; transform-style:preserve-3d; }}
  .strip {{ position:absolute; backface-visibility:hidden; background-repeat:no-repeat; }}
  #cap {{ position:absolute; border-radius:50%; background: radial-gradient(circle at 46% 44%, #4a4a4a 0%, #2b2b2b 52%, #5c5c5c 74%, #1c1c1c 100%); }}
  #shade {{ position:absolute; pointer-events:none; border-radius:40px / 12px;
           background: linear-gradient(90deg, rgba(0,0,0,.58) 0%, rgba(0,0,0,.26) 17%, rgba(0,0,0,.02) 33%, rgba(255,255,255,.17) 42%, rgba(255,255,255,.05) 52%, rgba(0,0,0,.07) 65%, rgba(0,0,0,.33) 83%, rgba(0,0,0,.66) 100%); }}
</style>
{root(name, W, H, dur, fps)}
  <div id="disc"></div>
  <div id="scene"><div id="stage"><div id="cyl"></div><div id="cap"></div></div></div>
  <div id="shade"></div>
</section>
</div>
<script>
(function(){{
  var ID='{name}';
  // the label texture wraps the cylinder: TW×TH = the texture's pixels, Hpx = the tube's height on the canvas; circumference follows the texture's aspect
  var TEX='assets/tex-product.png', TW=2048, TH=4019, Hpx={int(H*0.5)}, a0=-220, a1=-158, N=80;
  var C=Hpx*TW/TH, r=C/(2*Math.PI), w=C/N, cyl=document.getElementById('cyl');
  for(var i=0;i<N;i++){{ var s=document.createElement('div'); s.className='strip'; s.style.width=(w+1.5)+'px'; s.style.height=Hpx+'px'; s.style.left=(-(w+1.5)/2)+'px'; s.style.top=(-Hpx)+'px';
    s.style.backgroundImage='url('+TEX+')'; s.style.backgroundSize=C+'px '+Hpx+'px'; s.style.backgroundPosition=(-i*w)+'px 0px'; s.style.transform='rotateY('+(i*360/N)+'deg) translateZ('+r+'px)'; cyl.appendChild(s); }}
  var cap=document.getElementById('cap'); cap.style.width=cap.style.height=(2*r)+'px'; cap.style.left=(-r)+'px'; cap.style.top=(-Hpx-r)+'px'; cap.style.transform='rotateX(90deg)';
  var sh=document.getElementById('shade'); sh.style.left=({W}/2-r*1.03)+'px'; sh.style.width=(2*r*1.06)+'px'; sh.style.top=({int(H*0.84)}-Hpx+6)+'px'; sh.style.height=(Hpx-2)+'px';
  var rot={{a:a0}}; function apply(){{ cyl.style.transform='rotateY('+rot.a+'deg)'; }} apply();
  var tl=gsap.timeline({{paused:true}}); tl.to(rot,{{a:a1,duration:{dur},ease:'power1.inOut',onUpdate:apply}},0);
  {REG}
}})();
</script>
</body>
</html>
"""


def layer(name, W, H, dur, fps, seed):
    return head(f'{name} — transparent layer (png-sequence with alpha)', W, H, 'transparent') + f"""
<style> canvas {{ position:absolute; left:0; top:0; }} </style>
{root(name, W, H, dur, fps)}
  <canvas id="c" width="{W}" height="{H}"></canvas>
</section>
</div>
<script>
(function(){{
  var ID='{name}', W={W}, H={H};
  {PRNG}
  var rnd=mulberry32({seed}), NAMES=['piece-0','piece-1','piece-2','piece-3'], imgs=[], loaded=0;   // sprites cut from the SKU's own silhouette sheet, under assets/
  var D=[]; for(var i=0;i<700;i++){{ D.push({{x:rnd()*W, y:-H*0.2+rnd()*H*1.2, v:H*(0.25+rnd()*0.35), r:rnd()*6.28, w:(rnd()-0.5)*4, s:0.7+rnd()*0.9, k:Math.floor(rnd()*NAMES.length)}}); }}
  var cv=document.getElementById('c'), cx=cv.getContext('2d'), st={{p:0}};
  function draw(){{ var t=st.p*{dur}; cx.clearRect(0,0,W,H);
    for(var i=0;i<D.length;i++){{ var d=D[i], im=imgs[d.k]; if(!im) continue; var y=(d.y+d.v*t)%(H*1.2)-H*0.1; cx.save(); cx.translate(d.x,y); cx.rotate(d.r+d.w*t); var w=W*0.036*d.s, h=w*im.height/im.width; cx.drawImage(im,-w/2,-h/2,w,h); cx.restore(); }} }}
  function build(){{ var tl=gsap.timeline({{paused:true}}); tl.to(st,{{p:1,duration:{dur},ease:'none',onUpdate:draw}},0); draw(); {REG} }}
  for(var i=0;i<NAMES.length;i++){{ var im=new Image(); im.onload=im.onerror=function(){{ if(++loaded===NAMES.length) build(); }}; im.src='assets/'+NAMES[i]+'.png'; imgs.push(im); }}
}})();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True); ap.add_argument('--kind', choices=['card', 'turntable', 'layer'], required=True)
    ap.add_argument('--dur', type=float, default=2.5); ap.add_argument('--fps', type=int, default=24); ap.add_argument('--canvas', default='2160x3840'); ap.add_argument('--seed', type=int, default=606); ap.add_argument('--hf-version', default='0.8.18')
    a = ap.parse_args(); W, H = (int(v) for v in a.canvas.lower().split('x')); name = os.path.basename(os.path.normpath(a.out))
    assert not os.path.exists(os.path.join(a.out, 'index.html')), f'{a.out}/index.html exists — a new length or a new design is a NEW project name'
    os.makedirs(os.path.join(a.out, 'assets', 'fonts'), exist_ok=True); os.makedirs(os.path.join(a.out, 'renders'), exist_ok=True)
    html = {'card': card, 'turntable': turntable, 'layer': layer}[a.kind](name, W, H, a.dur, a.fps, a.seed)
    open(os.path.join(a.out, 'index.html'), 'w', encoding='utf-8').write(html)
    json.dump({'$schema': 'https://hyperframes.heygen.com/schema/hyperframes.json', 'paths': {'blocks': 'compositions', 'components': 'compositions/components', 'assets': 'assets'}, 'media': {'autoProxy': True}}, open(os.path.join(a.out, 'hyperframes.json'), 'w'), indent=2)
    hf = f'npx --yes hyperframes@{a.hf_version}'
    json.dump({'name': name, 'private': True, 'type': 'module', 'scripts': {'dev': f'{hf} preview', 'check': f'{hf} check', 'render': f'{hf} render'}}, open(os.path.join(a.out, 'package.json'), 'w'), indent=2)
    print(f'{a.out}: {a.kind} {W}x{H} {a.dur} s @ {a.fps} fps, seed {a.seed} — put the assets under assets/ (fonts/Display.ttf, ' + {'card': 'wordmark.png, character.png', 'turntable': 'tex-product.png', 'layer': 'piece-0..3.png'}[a.kind] + '), then render_hyper.sh')


if __name__ == '__main__':
    main()
