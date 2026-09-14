# The scene proxy — the room as a model the agent computes against, not a frame it remembers

A keeper frame becomes a labelled grey-box scene: every person, sofa, chair, table, door, window, lamp and
fireplace the segmenter finds as a closed box with a position, a size, a yaw and a confidence, plus the floor
(and sometimes the walls) and the keeper's own camera at the photo's field of view. From that scene the agent
places ANY camera — a reverse, an over-the-shoulder, a punch-in from the other wall — and reads, rather than
guesses, what that camera sees: which object is left or right, nearer or farther, in frame, occluded, or out
of frame. That table is the ledger's *Room geometry per cut* row and the source of every geometry sentence
in a prompt. It answers the failure that cost the most rounds: a new angle written from memory ("suddenly his
couch is turned the opposite way with the door and her behind it" — three seeds of one shot).

## When

- Any scene that will be shot from more than one camera position, before the second angle's prompt is written.
- Any reverse, OTS or insert whose start image cannot be a crop of the keeper (the crop is still the
  reference; the proxy is the geometry).
- A move that has to clear the set — the backward geometry check (`film-preprod` MUSIC-VIDEO § 7) — run the
  authored move through the proxy and read the framing table before the gen.

## Build it — `scripts/scene_blockout.py`

```
COMFY_HOST=<your ComfyUI URL> python3 scripts/scene_blockout.py <keeper-frame.png> \
    --labels "person,sofa,armchair,table,fireplace,lamp,window,door" --out S02-ROOM
```

Runs headless through the ComfyUI server's OmniCam job route (MoGe depth + SAM3 instances → deterministic
box fitting); ~15–25 s per frame on a 24 GB GPU; $0. It writes `<out>.scene.json` (the scene + the run
summary) and prints the object table. Requirements, all one-time: the ComfyUI server RUNNING as a headless
server (`python3 scripts/comfy_ready.py` says whether it and its two providers answer; `scripts/comfy_up.sh`
starts one from the env — § ComfyUI as a server), the OmniCam custom node, a MoGe checkpoint under
`models/geometry_estimation/`, a `sam3*` checkpoint under `models/checkpoints/`. The script fails closed with
the route's own reason when any is missing.

**The label list is the precision lever.** SAM3 forces a match for every label it is given, so a default
list asked of a night street returns a shopfront as a cabinet. Write the list PER SCENE from what the frame
actually contains; raise `--threshold` (default 0.55) to drop low-score phantoms. Expect, and read past:

- an occluded piece missed (a sofa under five people; a lamp behind an armchair);
- one phantom per busy frame (a mantel read as a `desk`, a can on the floor as a `coffee table`);
- a POV frame's foreground body parts fitted as a `person`;
- walls only sometimes, at low confidence; the floor always;
- **relative scale** — a seated person ≈ 0.9 units, a standing one ≈ 1.4; consistent inside one scene,
  never metric. Size questions keep their instrument (an in-world crop beside a known object).

**Audit the table against the keeper's fixed set before the scene is used.** A fixed-set object the segmenter
missed (the S02 floor lamp, cut by the frame edge) is not a blank — it is an absence the proxy teaches: the
take that rode the lamp-less proxy as `@Video1` REMOVED the lamp from a shot whose start image had it
(A/B 2026-09-10, § proxy clip). Add the missing box by hand in `<out>.scene.json` (an `objects[]` entry —
`type: cube`, `position` and `size` read off a neighbour) before any render that will ride as a reference,
or keep the scene off every reference slot; the table's other rows stay good.

**A hand-added box is anchored in DEPTH, not only in x/y.** Give it the depth of the detected object it stands
against (a lamp beside the fireplace takes the fireplace's z, not the armchair's), then render the SOURCE camera
and check the box against the keeper by SIZE as well as position — a 1.3 m lamp at 3.9 m renders ~35 % taller
than at 5.3 m, so a footprint at the right x/y proves nothing about depth. The S02 lamp placed at the armchair's
depth predicted "in frame" for an end camera the real lamp had already left, and two correct takes were read
as drops for an hour (2026-09-10 § 6e of the OmniCam analysis): the far plane slides WITH a camera-right orbit,
the near plane against it, and a box on the wrong side of the target distance moves the wrong way.

Pilot 2026-09-10, four keeper frames (a family room, a boardroom, a lounge, a couch POV): every fixed object
at the right left/right AND near/far order on every frame; cameras placed at two accepted keeper angles of
the boardroom reproduced those keepers' order; the couch POV came out blinds LEFT · door CENTRE · lamp
RIGHT, exactly the geometry three earlier seeds had broken.

## Read it — `scripts/scene_proxy.py`

```
python3 scripts/scene_proxy.py S02-ROOM.scene.json S02 source            # the keeper's own camera — sanity check
python3 scripts/scene_proxy.py S02-ROOM.scene.json S02 top               # the floor plan
python3 scripts/scene_proxy.py S02-ROOM.scene.json S02 "0.5,1.3,-2.9,-0.5,0.7,-0.6,60"   # an explicit camera
```

Each call writes `<out>-<view>-gray.png` (a labelled grey-box frame) and `-depth.png`, and prints the table:
object · x % · y % · depth · pixels · read (`left/centre/right, in frame | occluded | out of frame | behind
the camera`). Numpy + Pillow only; no server, no browser. Author the camera in scene units: read the source
camera's position and the object centres from the JSON, then place the new one by relationship ("at the
fireplace, looking at the sofa" = the fireplace's position, aimed at the sofa group's centre).

**From table to prompt.** The prompt's geometry sentence is copied FROM the row, as the ledger already
requires — "the white front door at the right of the frame, the floor lamp beside it" — never re-derived;
the table decides the "at most ONE anchor coordinate; everyone else by relationship" order for the subjects
block. A row that says `occluded` is a sightline decision (move the camera or accept the occlusion), made
before the gen, not discovered in a seed.

## One geometry, three channels

The render and the table are read by the AGENT first — every left/right, near/far, in/out word and the camera clause
are copied off them before a prompt is written — and the same scene then supplies the models: the grey frame of a
camera as a layout-only reference when a start or end still is generated, and that frame or the clip as the video
model's geometry reference. One source for the prompt, the stills and the references means the three cannot disagree,
which is what buys a usable first seed; a take is never the instrument that discovers geometry. Spend order: proxy $0
→ still ≈2 cr → take. The layout-only role for a grey STILL: `@ImageN is the layout and camera reference only: take where each person and piece of furniture stands in the frame and how the frame is framed from it; never its grey boxes, black void or materials` (`video-prompt-dialects` DIALECTS § Seedance roles; LINT L26).

## Bake the geometry into the stills

- **A move on Seedance 2.5** = a start image (the keeper, or an accepted still) + an END still composed from the grey
  frame of the arrival camera (GPT Image 2.5, kie first — `gpt-image-2-5-flare-image-to-image`, $0.05 at 2K — Higgsfield
  `gpt_image_2_5` second; Nano Banana Pro the fallback: the keeper + the cast refs + the grey frame under the layout-only
  role), shipped as `end_image`; the clause states the arrival. Tested 2026-09-10: a smooth arc with true parallax,
  the last frame = the still — defects included, so the still is accepted like a seed with the frame EDGES zoomed (an
  invented foreground pole rode into the take). The clip is unnecessary there.
- **A static new angle in r2v** = the grey frame of that camera as `@ImageN` under the layout-only role beside the
  room and cast refs, no start image: frame 0 opens on that angle (tested, first try).
- **A move on H3** = the clip (next section). A grey still on H3 is untested.
- An end still is gated like a start image — its own PASS + ACCEPTED record before it ships.
- Start image or refs-only is a per-shot choice by what the shot must hold — the table in `video-gen-cost-gate`
  SKILL § Mode by what the shot must hold (a fresh angle → refs + the grey frame; an exact continuation or a
  defined Seedance move → a start image, plus the end still for the move).

## A proxy clip — `--move`

```
python3 scripts/scene_proxy.py S02-ROOM.scene.json S02 \
    --move "-0.05,1.19,2.33,-0.04,1.01,1.34,60 -> 0.3,1.1,0.4,-0.1,0.9,-1.4,60" --seconds 4 --fps 24 --mp4 S02-push.mp4
```

Renders the eased move frame by frame on the shot's real frame times (`[0, (n−1)/fps]`, `video-edit-edl`
EDL-CONTRACT § Frame-time sampling) and writes `S02-push.mp4` plus `S02-push.mp4.json` — the sidecar
carrying the scene's sha256, both cameras and both tables. The clause the prompt needs for that move comes
from `video-prompt-dialects/scripts/camera_clause.py --sidecar S02-push.mp4.json`.

**As a reference the clip is a camera driver on MiniMax H3 and a half-measure on Seedance 2.5 — TESTED
2026-09-10** (Higgsfield, one take per arm — the H3 clip arm twice — the same 25° camera-right orbit through one family-room scene, 92 cr in all):

| venue · set-up | the camera | the room |
|---|---|---|
| Seedance 2.5 `omni_reference`: start image + `@Video1` under the motion-only role | ≈3° of 25°, back-loaded — the start image dictates | no grey leaked; the floor lamp the scene lacked was REMOVED while the frame stood still — a leak by absence |
| Seedance 2.5 refs only (the keeper as `@Image1`, no start image) + a complete `@Video1` | frame 0 = the keeper; ≈55 % of the arc by the far wall (+38 of 67 px) and the armchair (−48 of 86), back-loaded (4 · 8 · 18 · 38 px at 1–4 s) | held; the lamp (back wall — the far plane) left the right edge by 1.5 s, a correct EXIT once the box was placed at its true depth |
| MiniMax H3 (2K): `<Video 1>` + the timecoded clause + the role sentence | ≈ the full arc by the window (+62 of 67 px), the armchair −65, paced near the ease | held throughout; no grey; the lamp exited by 1.9 s as the far plane must; adjacent-frame PSNR flat 36–40 dB to the last frame — no tail collapse |
| MiniMax H3, the same set-up, a second seed | the same arc, a touch wider — the last frame matches the end table: window at the left edge, the nearest sitter cut, the subject centred, the armchair right, the lamp out of frame | held; no grey; 42 → 33 dB smooth, clean tail — 2 of 2 seeds |
| MiniMax H3: the clause alone | re-staged the shot from behind a sofa that is not in the reference, the window gone | broken |
| Nano Banana Pro still (the fallback model): keeper + cast ref + the grey END frame (layout-only role) | — | the new angle first try, order and sides right, rotation ~15 % short; one invented foreground pole at the right edge; no grey |
| kie GPT Image 2.5 still (the default, $0.05): the same three refs, the kie i2i dialect | — | the new angle first try, closer to the table (armchair 70 % vs 66, lamp in view), NO invented element, faces held |
| Seedance 2.5 r2v, static: keeper + cast ref + the grey end frame as `@Image3` | frame 0 ON the new angle, held | held; no grey |
| Seedance 2.5: start = keeper, END = the accepted still, no clip | a smooth arc with true parallax (21 · 42 · 71 · 100 %), arriving on the still | held; the still's defect rode in |
| MiniMax H3 (2K), a static NEW angle: keeper as `<Picture 1>`, cast ref, the grey end frame as `<Picture 3>` under the layout-only role, no clip | frame 0 = the KEEPER's angle — the grey still was ignored; then an invented push-in to a close-up (58 → 21 dB), "static camera" overridden | the room held while it lasted; the mouth opened against "nobody speaks" |
| MiniMax H3 (2K), a STATIC shot: keeper as `<Picture 1>`, cast ref, a static proxy clip (one camera, `--move "A -> A"`, 5 s) as `<Video 1>` with the derived clause "holds a locked, static frame" and the role sentence | frame 0 = the keeper's angle; the framing identical at 0 / 2.5 / 5 s; the first-vs-last difference is the people's micro-motion only; adjacent-frame PSNR 54–66 dB throughout (the H3D push-in had fallen to 21) | held; no grey; the mouth stayed shut, nobody moved — the static clip pins the camera (n=1) |
| MiniMax H3 (2K), a static NEW angle, the pairing: the kie still of the new camera as `<Picture 1>` "is the whole frame", the cast ref, the keeper as `<Picture 3>` for faces, garments and light, a static proxy clip at the NEW camera as `<Video 1>` | frame 0 = the KEEPER's angle again — the still did not set it and the static clip carried no angle; the camera then held (60 dB, one 44 dB dip = two sitters shifting) | held; no grey; with the keeper in the set H3 frames on the keeper in either position (n=2) |
| MiniMax H3 (2K), the static-clip set-up plus one spoken line in `<d>` | the camera held (50–60 dB, min 49.5 at the line); the line landed verbatim at 3.2–4.6 s against a 1.0–3.8 s clause, the look beat at 2.5 s, the seated four silent | held; the static clip does not freeze the performance (n=1) |
| MiniMax H3 (2K), a static NEW angle, the keeper OUT: the kie still of the new camera ACCEPTED as a room ref and cited as `<Picture 1>` "is the whole frame", the cast ref, a static proxy clip at the NEW camera as `<Video 1>` | frame 0 = the STILL's angle (grey-frame correlation 0.957 with the still, 0.542 with the keeper): the nearest sitter cut left, the lamp in on the right; the camera then held (52–65 dB) | held; faces held; no grey; the subject's mouth flapped against "nobody speaks" as in H3D (n=1) |
| MiniMax H3 (2K), the same keeper-OUT set-up, a second seed | frame 0 on the still again (0.991); held | held; the same first-second mouth flap (n=2) |
| MiniMax H3 (2K), keeper OUT, the subject told "keeps his mouth naturally closed" instead of "nobody speaks" | frame 0 on the still (0.982); held | held; the standing subject STILL mouthed a silent syllable in the first second — the wording does not stop it; trim the head or write the line (n=1) |
| MiniMax H3 (2K), keeper OUT + the static clip + one `<d>` line — the production combination | frame 0 on the still (0.948); the camera held (edges ≈1 of 255; PSNR min 45 dB at the line) | held; the line verbatim at 3.3–4.7 s; the mouth on the line; the eyeline drifted toward the lens at this angle (n=1) |

So: on H3 the proxy clip SHIPS with EVERY shot, a static one included (`<Video N>` + `camera_clause.py --h3`; the
clause alone is the lint, `video-prompt-dialects` LINT L27), and H3 frames on the KEEPER whenever the keeper is in the
reference set — in either position, whatever picture the prompt calls the whole frame (n=2): a grey still cited as
`<Picture N>` sets nothing (n=1), a baked still beside the keeper sets nothing either (n=1), and a static clip carries
no angle; with the keeper OUT of the set the baked still cited as `<Picture 1>` sets the angle and a static clip at
that camera holds it (3 of 3), a spoken line included (1 of 1) — so a NEW static angle on H3 = bake the still, ACCEPT it as a room ref, cite it as the only
room picture, ship the static clip at that camera, keep the keeper out; a new angle WITH a move stays the orbit clip
(2 of 2); without a
`<Video N>` the camera invents its own move even when the prompt says static (2 of 2), and a STATIC proxy clip as
`<Video 1>` pins it — frame 0 on the keeper, 54–66 dB to the last frame, no drift (n=1) — so a static shot ships a
clip rendered from one camera (`scene_proxy.py --move "A -> A"`); on Seedance it rides only without a start image, carries
about half the magnitude, and the clause still states the arrival — beside a start image it is inert, and a move
there is better served by an end still (§ Bake the geometry into the stills). In every
case the scene is complete first (§ Build it), the role line is mandatory (L26), and the take's LAST frame is
read against the sidecar's end table: the x % per object is the acceptance row, not taste.

**Read the end table with its PLANES.** Every object nearer than the target distance slides AGAINST the
camera's direction, every object beyond it slides WITH it, and the sidecar's per-object Δx (table A → table B)
carries that sign — a take whose landmarks reproduce the signs moved the camera, whatever its magnitude. An
object absent at the end is a DROP only when the end table says *in frame*; when it says *out of frame* the
absence is an EXIT and the take is right. The S02 lamp read as a drop for two takes with its box mis-placed on
the near side of the target, and as the exit it was once the box stood on the back wall (§ Build it).

## Check the shell at the move's extremes — `--extremes`

A scene built from the keeper's frame is a stage set for the keeper's camera: the pilot blockouts carry a floor the
size of the reconstruction's footprint, no ceiling and no walls, so that camera already reads 100 % void on its top
band and about half on each side. A move shows what the set never built.

```
python3 scripts/scene_proxy.py S02-ROOM.scene.json S02 --move "A -> B" --extremes      # --band 0.1 --rise 0.15 --samples 9
```

It prints each edge's void — the share of a 10 % edge band whose rays hit nothing — at nine points of the eased move,
beside the keeper's camera, and a SHELL SHORT line for every edge whose void rises more than 15 points. Measured
2026-09-12 on the family-room scene: both 25° orbits, the push and the arc each rise on a side band and on the bottom
band (the floor ends; an orbit's arrival reads 100 % bottom void) — while the two H3 takes that rode the orbit clip
beside the keeper held the room 2 of 2. So the read is a decision per channel, never a gate:

| the proxy rides as | an edge that reads SHELL SHORT |
|---|---|
| a grey END or new-angle frame under the layout-only role — a still is composed from it | add the missing wall, floor or box by hand first (§ Build it): the still model composes that edge from nothing; zoom that edge when the still is accepted |
| a proxy clip beside the keeper on H3 | tolerated as tested (2 of 2 orbits held the room): ship it, and read the take's edges at the arrival |
| a grey frame that is the ONLY room picture (the keeper out of the set) | add the geometry first — nothing else in the set describes that edge; `--strict` exits 1 here |

Upstream precedent (an explainer kit that projected real cameras, 2026-09): a back wall with no side walls went pure
black once the camera yawed past about 8°, and three shots cut their moves (42° → 22°, 60° → 26°) until two side walls
went in. Build the set for the most extreme planned move, not the default angle. `--selftest` proves the check on
that case — a back wall alone: the leading edge rises; add the side walls: nothing rises.

## ComfyUI as a server (headless)

ComfyUI opens no browser unless told to (`--auto-launch`), so "headless" is a detached server process the
skill reaches over HTTP; the skill never manages a machine's process lifecycle beyond two env-driven pieces:

```
python3 scripts/comfy_ready.py                        # exit 0 when $COMFY_HOST answers and the OmniCam route lists MoGe + SAM3
scripts/comfy_up.sh && python3 scripts/comfy_ready.py --wait 120    # start one (local, or over ssh) and wait for it
```

`comfy_up.sh` reads `COMFY_DIR` (the ComfyUI checkout), `COMFY_VENV` (its virtualenv, optional), `COMFY_ARGS`
(default `--listen 0.0.0.0 --port 8188 --disable-auto-launch`), `COMFY_LOG`, and — when the server lives on
another box — `COMFY_SSH=user@host`, in which case the same detached command runs there over ssh. The values
live in the env file (`.env.example`), never in this skill; a server already answering is left alone. Three
rules from a measured local generation lane (`minimax-h3-notes`, 2026-09): ComfyUI does not answer HTTP while
it SAMPLES (a 6 s poll stalled generation 18–43 s) — the 2 s job poll is for the reconstruction route, never
run beside a local generation; a server that has slowed to ~1.8× its normal clip time is degrading ahead of a
CUDA failure — restart it rather than wait for the crash; never time or judge a cold first run, and change the
seed between runs (an identical graph is served from cache). And a readiness probe has three answers, not two: a
listing or route it cannot read is **unknown** — never reported missing (an installed provider is not absent) and
never a pass (a failed detection is not readiness); `comfy_ready.py` says which of server, route and provider it
could not prove.

**Running GENERATION on that server, not just reconstruction.** The same headless server is the local
generation venue (`video-gen-cost-gate` references/LOCAL-H3.md for the recipe and cost). Four operating
rules, all measured 2026-09:

- **`COMFY_VENV` is load-bearing and its failure is silent.** The fast attention kernels need a current
  CUDA build of the tensor library; on an older build the server logs a warning at startup and runs
  everything **2.1× slower**. Build a second virtualenv rather than upgrading the one other tools on the
  box depend on, and point `COMFY_VENV` at it permanently. Custom-node *folders* are shared between
  virtualenvs — only the Python dependencies are per-venv, so a new venv needs the packs' requirements
  installed and any pack with compiled CUDA extensions rebuilt before it is used from there.
- **Bracket the card, and restore only what you stopped.** Local generation takes the whole GPU. Stop the
  resident GPU services, record exactly which ones were stopped to a state file, and restore only those on
  close; hold a lock and trap the signals so a killed run does not strand them. Close the bracket when the
  queue drains, not when a take finishes.
- **A partially-valid graph returns HTTP 200 with a prompt id** and a `node_errors` map, and the valid
  outputs are queued anyway. Treat any non-empty `node_errors` as a failure and delete the queued prompt by
  its **full** id — a short id is accepted and silently does nothing. Never read the 200 as success.
- **Poll on demand, never hold a session open.** Submit, then poll the history route; a detached remote job
  outlives the local shell, so killing the local caller does not stop the run. One drain loop that
  downloads each output as it lands beats a waiter per job.

## Hygiene

- The sidecar's `scene_sha256` is the fingerprint the gate diffs: a clip rendered from an older scene than
  the one the prompt was written against is stale and is re-rendered, never shipped
  (`ASSET-HYGIENE.md` § A derived artefact carries the fingerprint of the state it was derived from).
- One scene per keeper frame, named for the shot (`S02-ROOM.scene.json`); a recast or a re-dressed plate
  gets a new scene, and the old one is struck from the shot list the way a superseded plate is.
- The scene is relative and per frame: never compare positions ACROSS two scenes; compare inside one.

## Failure behavior

- Server down, node missing, checkpoint missing, job FAILED → `scene_blockout.py` exits with the route's
  reason. Say "no scene proxy for this shot" in the GO ask and fall back to the frame + the ledger; never
  write geometry from memory and call it computed.
- A frame with no detections → try a scene-specific label list and a lower threshold once; then the frame
  is not proxy-able (a bare wall, a close-up) and the ledger row is read off the frame as before.
- Fewer than two fixed objects in the table → the proxy cannot order a new angle; say so.
