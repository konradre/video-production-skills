# Instruments — what each measures, and its self-test

Every measurement script prints a known-answer case beside the real one, or its number is not
evidence: a scale metric once matched a frame to ITSELF at 0.90× and had already been used to make
claims; a hair-blob camera-lock metric was contaminated by loose pieces after a burst. When the ear or the
eye disagrees with the metric, the metric is the thing that gets fixed.

| script | measures | notes |
|---|---|---|
| `qc_seed.py <take> [--plate] [--out] [--thr 0.12] [--ratio 3] [--no-whisper] [--record]` · `--read` · `--note "…"` · `--selftest` | the take's cut list — a cut is a one-frame SPIKE on the 48×27 grey-thumb diff: above `--thr` AND above `--ratio` × the median of its ±12 neighbours, cuts < 4 frames apart merged; the continuity sheet (plate \| first frame of every cut \| last frame); a 1 fps tile; the native-audio RMS peak in 25 ms windows (the hit); a faster-whisper transcript with word times; `--record` writes `<take>.review.json` beside the take (sha256 + bytes, every measurement with its instrument and rule, the sheet path, notes[]) | measured 2026-09-10 on 22 takes: the spike rule at 0.12 matched ffmpeg's `scene>0.3` frame for frame (13 cuts, incl. three seeds of one shot at f69), the old 0.28 threshold alone had found ONE of them, and the burst takes stayed clean; `--selftest` proves the rule on synthetic frames (a hard cut, 40 frames of sustained motion, a slow pan then a cut); the record is read FIRST on a resumed session (`--read` refuses a stale record — bytes, then sha256) and strips are re-viewed only for the claim at hand; `--note` appends a reviewer note to a fresh record and never touches a measurement; the sheet is the FIRST read; the peak time seeds the EDL's beat; whisper garbles slang — the ear decides those |
| `cut_consistency.py <take> [--cuts a,b] [--gap 0.5] [--box "t:x0,y0,x1,y1:x0,y0,x1,y1"] [--out] [--json]` · `--selftest` | consistency ACROSS the take's cuts: light (mean L*), contrast (σ L*), white balance (the mean a*b* shift) and palette (a*b* histogram, Bhattacharyya distance) in the `--gap` windows either side of every cut, each printed as a multiple of the take's own within-shot maximum and ABOVE when over it; a segment-similarity matrix (NCC of mid-shot grey thumbnails); `<take>-cuts.jpg`, the frames either side of every cut (survey), and `--box` crops either side (verdict, q95 4:4:4); the cut list from `--cuts` or the take's `qc_seed.py` record | a measurement beside the eye, never a verdict — identity and wardrobe are READ on its images. Calibrated 2026-09-13: a client-accepted 20 s take's two composed cuts to new angles read ABOVE on light (1.4–1.6×) and palette (2.3×) and far under on white balance (0.0–0.4×) and contrast (0.0–0.1×); four joins between separate generations — three seed swaps inside one shot, one join of two shots — read ABOVE on all four rows (white balance 1.2–12.9×, contrast 1.5–25.1×). Raw values did NOT separate them across takes (a seed swap's light step 1.35, a composed cut's 9.39): compare multiples inside one take, never raw numbers between takes, and a quiet take's small baseline inflates every multiple. Two composed cuts from one take are a lead, not a threshold. `--selftest` runs before every read: a new angle in the same grade against a spliced grade, the splice ABOVE on white balance at more than 3× the composed cut; a record with no cut list (another reviewer's format) is refused, never guessed |
| `contact_sheet.sh <take> [cols] [rows] [font]` | evenly spaced frames with burned-in timecode → `review/<take>-contact.jpg` (survey) | the agent's notes; never the review the operator sees; a hypothesis generator — a wardrobe drift read off a small sheet was withdrawn on a larger sample |
| `window_frames.py --in --from --to [--box] [--zoom 4] [--gamma 1.6] --out` | EVERY frame of a window, cropped and enlarged, gamma-lifted for dark cavities; `--out *.jpg` writes q95 4:4:4 (a verdict image), `*.png` lossless | the named-state check (mouth, hands, pane); a 1.5× sample is not a check |
| `frame_match.py --take <take> <frame.png> [--fps 24]` | the take time whose frame best matches a screenshot (NCC on grey thumbs) | answers "which event is this?" for an operator-posted frame BEFORE any fix is proposed; run it against every candidate take |
| `frame_psnr.py <take> [--step 0.25] [--tail 1.5]` | adjacent-frame PSNR on a 240 px grey downscale: the motion curve at `--step` intervals, its minimum and when, the last `--tail` seconds against the take mean | > 45 dB frozen · 30–40 breathing only · 18–28 an action · < 15 a cut; a written beat must be a DIP at its time (a peak there = the beat did not happen); a tail whose mean leaves the take's band while the body holds = a tail anomaly (the H3 open-weight collapse) — `--selftest` proves the direction on synthetic frames; H3A 09-10 read flat 36–40 with no tail change, a static Seedance take 45–66 with dips at its two motion events |
| `designed_frame_metrics.py <clip\|frames> [--content x0,y0,x1,y1] [--shots "id:a-b,…"] [--from --to] [--json]` · `<images> --each` · `--selftest` | DESIGNED motion only — explainer scenes, kinetic titles, cards: per shot, the hero's median size as a fraction of the content box (the largest foreground object after a dilation that merges a line of type), the longest EMPTY run (no hero reaching 0.21 of the box), the share of STILL samples 0.1 s apart and the longest HOLD, classed TRUE-STILL / SMALL-MOTION / ACTION by changed pixels. The flags SMALL (< 0.33) · EMPTY (> 1.5 s) · STILL (> 40 %) · HOLD (> 1.0 s) are judgement rows | calibrated 2026-09-12: it reproduces the upstream explainer kit's own hero heights on its twelve reference frames to the pixel, and at 0.33 it flags every reference frame whose defect was size plus one good frame (a big number at 0.30) — read the frame; an accepted 2160×3840 end card reads hero 0.45 and 3 % still (OK), an accepted turntable display 0.56, 29 % still and a 0.92 s hold classed SMALL-MOTION (OK, near the limit); a 249 s narrated slide walkthrough reads 97 % still with 5.6–7.8 s holds and EMPTY on its text slides — the still and empty rows bind motion graphics, never slides or card holds; measured at a 720-px short side with frames streamed (that walkthrough: 35 s, 0.2 GB); OpenCV and scipy give identical numbers; `--selftest` covers an empty canvas, a moving and a held hero, the type-line merge, small-area motion and the video decode path |
| `product_aspect.py <take> --from --to --box --sku-aspect 4.75` | the held product's width:length from the largest saturated blob (PCA) | BLIND at 480p (a known-good 1:4.75 read 1:2.6 at 30 px; burst frames merge blobs) — the number of record comes from a 4× visual crop beside the product photo, on the Rhea frame when one exists |
| whisper on each seed's native track | words, onsets | word-like events on an unscripted mouth = "shouting"; the first word of each scripted line (a layout dropped it 2/2) |
| a 50 ms spectral-flatness scan of the audio head | a generated tone (flatness < 0.3 with a stable peak) | a 520 Hz note under a quiet cut reads as a musical artifact |
| camera-lock: NCC scale-match of the upper 45 % of frame N against frame 0 | drift vs lock | the hair-blob version failed after a burst; self-test on a static clip |
| motion energy per frame (mean \|Δ\| in a band) | the last STILL frame before heads swivel; the onset the operator means by "just before she trips" | the eye is one to two frames late |
| the 4× crop beside the SKU photo | product proportion | the acceptance instrument for "too big / too wide" |
| Laplacian variance per ROI | a focus rack's timing (face vs glass) | fixes both the cut points and the VO slot |
| face detail at equal size — Laplacian variance of every face crop resampled to ONE common size | under-rendered vs only framed small | the equal-size control IS the measurement: a rejected face carried 1.7–1.9× less detail than two accepted faces at identical pixel size, and upscaling it widened the gap to 5.37× (no recoverable detail); every detector box is confirmed by eye first — a face cascade returned seven confident false positives on a two-shot and missed both real faces |
| splice spike — the frame-to-frame change against the shot's own median | a join hidden inside a shot | a splice SPIKES between two still frames (60× the shot median, 9.5× its p90, bracketed by the two quietest frames around it); a real movement ramps; audio running through it is why it reads as a broken join rather than a cut |
| dead-flat blocks — the share of 8×8 blocks with zero variance, beside the noise floor | absent grain in a generated frame | a measurement, not a look decision: 27.8 % of every frame dead-flat at a 0.00 noise floor, and grain injected at σ 0.5/1/2/4 read back 0.45/0.90/1.78/3.50 with the share at 0 % — the metric responds linearly; whether a look carries grain is `video-finish`'s call |

## Review images — by purpose

A review image is written for what it is FOR, and its bytes are paid in every request an agent session replays. Two
review sessions died on `400 Invalid JSON: length limit exceeded` at about half their compaction trigger, carrying 37
lossless full frames (15.3 MB of base64): images are cheap in tokens and large in bytes, so a token-percentage
compaction never fires in time, and a resume replays the whole history in its first request.

| tier | what | format | downscale? |
|---|---|---|---|
| VERDICT — skin texture, identity, hands, teeth, a garment, a named state | a crop of the thing judged, at native size or larger | JPEG q95 4:4:4, or PNG when the crop is already small | **never** |
| SURVEY — the continuity sheet, the 1 fps tile, a contact sheet, a cut sheet | whole frames, read for layout | JPEG q85 | yes — composition survives it |
| GENERATOR INPUT — a start image, a look plate, a reference sheet | fed to a model, not read by one | PNG, never recompressed | never |

Measured on a face crop: q95 kept all of the lossless crop's high-frequency energy at 44 dB PSNR and was ~5× smaller;
a 480×854 frame is ~350 KB lossless and ~45 KB at q85. High-frequency energy measures texture presence, not fidelity,
so a PSNR above ~40 dB is the guard. Cropping, not compressing, is the lever; no dimension cap applies to a verdict
image — the cap once proposed was inferred from another model's behaviour and never measured. Write findings to disk as
they are reached. The scripts write these tiers by default: `qc_seed.py` `-sheet.jpg` and `-frames.jpg`,
`contact_sheet.sh` `-contact.jpg`, `cut_consistency.py` `-cuts.jpg` (survey) and `-box.jpg` (verdict),
`window_frames.py --out *.jpg` (verdict).

## Reading discipline

- A whole-frame downscale assesses composition only. Identity, anatomy, teeth, product: 1:1 crops or
  larger.
- Every background element in every cut — tile the shelf from every cut that shows it.
- A named state: every frame of every window, wides included.
- When the operator says they see it in motion, they see it: locate it, do not argue the crop.
- `COMPLETED`, a big file, a passing per-shot check — none is success; the delivered file is what is read.
- Never invent a numeric tolerance ("~70 % of the sibling's height") and grade against it.
- A contact sheet generates hypotheses; it does not settle them. A framing drift asserted from a downscaled
  tile measured dx = 0, dy = 0 with the self-test passing; a join "defect" measured 1.00× at corr 0.908
  while the real fault was a camera move. Measure before claiming, and name the instrument in the claim.
- **An instrument measures what it measures, not what you named it.** Three cases where a number was
  confidently read as the wrong thing (local H3 probe, 2026-09-11):
  - **An edge-strip "camera hold" reads a global GRADE shift as camera drift.** A take scored 44/33/18/13
    on the four edges — a drifting frame by the threshold — with the framing perfectly locked; what moved
    was the colour, swinging warm from ~3.5 s. Read the frame strip before calling an edge number a move.
  - **Laplacian "detail" is INVERTED by an overlay artifact.** A take carrying wireframe outlines scored
    448 against a clean take's 379: the metric was measuring artifact edges. Detail compares only between
    takes already confirmed artifact-free by eye, and a *flat* detail trace across sampled frames is itself
    the artifact-free signal — a spiky one is the tell.
  - **A frame-0 correlation against a reference still can stay high while the content is wrong.** An
    additive overlay left the underlying frame correctly reconstructed, so the lock read 0.98 with a grid
    drawn over it. A high lock says the frame was reproduced, never that nothing was added.
- **A fixed box over a moving element reads its motion as a missing event.** A brightness trace in a fixed box over a
  sliding card came out smooth, and a flicker was reported missing; the element did flicker — outside the box. Track
  the element's box, or read the frames (upstream explainer QC, 2026-09).
- **A reduced render reads motion loose; the delivered frames are the verdict.** Upstream, 48 of 48 shots passed the
  sustained-action check on half-resolution previews and 11 failed on the delivered frames.
- **Verify a designed composition at NAMED seconds; a full render is an export, never a check.** An agent cannot
  watch a film, it can only look at frames — so freeze the timeline at 6–20 chosen times (each scene's first frame,
  each text entrance, each transition, each set piece's landing) and read that sheet like a director: clipped,
  overlapping, arriving before the camera settled, still reading as a slide. Rendering every frame to check is 3,600
  images for one minute and is not a verification of anything; it is what the export step does once, when a master is
  wanted. Capture through the composition's seek — `designed-elements` HYPERFRAMES-CONTRACT § index.html has the
  contract and the two traps that otherwise hand you a frame from the wrong tick.
- **A composition's STRUCTURE is read off its source, not its frames.** A film can pass hero size, empty runs and
  still share and still be a deck — scenes switched by opacity with nothing moving the world, a kicker/title/body
  stack, one kind of transition at every cut. `designed-elements` `slide_structure_audit.py` reads those four off
  `index.html` and exits 2, never 0, when it cannot segment the composition into scenes.
- **The frame instrument sees luminance, not hue.** A dark gradient card on a dark ground read hero 0.12 and EMPTY;
  the same card with a light stroke read 0.42 (explainer pilot, 2026-09-12). Before calling a scene empty, check the
  hero against the ground on the frame.
- A defect note names the hash-suffixed file it was written about, and the re-roll that fixes it clears the
  note in the same step — a verdict attached to a logical name transfers to footage it was never about
  (`video-refs-continuity` ASSET-HYGIENE).
- **Prove the query before believing an empty result.** A cut-map query returned zero cuts on a seven-shot deliverable;
  a broken query reads exactly like an absence. Run it on a case with a known answer first.
- **A detector that fails confidently reads like one that works.** Confirm every box by eye before a number is taken
  from it.
- **Texture compares only between matched-motion windows.** A wrinkle claim that compared a near-static window with a
  moving one established nothing; without the matched control the claim is not established, and says so.
- **Record a withdrawn or refuted finding beside the finding.** A wardrobe drift read off a small sheet (the same shirt in
  every shot on a larger sample) and flat shading as the cause of unreal light (the rejected shot's shading spread sat
  between the accepted shots') were both written down as withdrawn, so the next session does not inherit them.
