# The spot pipeline — from approved keepers to a delivered master

`video-finish` fixes the ORDER for one clip (upscale → grade → grain → watermark → downscale → encode).
This file is the same order run over a whole spot from its EDL, with the campaign's contracts.

## Stages and files

| stage | input | output | codec | who |
|---|---|---|---|---|
| upscale, per shot | the APPROVED take (480p) | `edit/upscale-out/<take>__rhea-1x4.mp4` (local) or `edit/upscale-out/<id>.mp4` (hosted) | 10-bit where the tool allows | `upscale_local.sh` / `upscale_fal_topaz.py` |
| normalise, per shot | the source window (real footage at its display shape) or the upscaled mezzanine | `edit/flat/<id>.mov` ProRes 422 HQ 10-bit 4:2:2, BT.709, limited range, starting at pts 0 | `normalise_shots.py measure` → `flatten` |
| hero pass, per clip | the flat or the upscaled mezzanine | `edit/hero/<stem>__<look>.mov` DNxHR HQX / ProRes 422 HQ 10-bit 4:2:2, pre-graded | `hero_pass.sh` (Resolve + Dehancer, `--transport auto`), then `normalise_shots.py verify` |
| cut | the EDL: heroes (`src`, look `none`), upscaled mezzanines (a cube), designed renders | `edit/mezz/<SPOT>-footage-graded<tag>.mov` ProRes 422 HQ at the mezzanine raster, footage only | `finish_spot.py --stage cut` |
| master | + post layers, the card when the spot has one, the VO stem (rebuilt), sfx, cues, native beds — a static sum, no loudness processing | `edit/mezz/<SPOT>-master-<W>x<H><tag>.mov` ProRes 422 HQ + PCM 24-bit | `finish_spot.py --stage master` |
| deliver | the master | `deliver/<deliver_base><tag>.mp4` at the EDL's `canvas` (1080×1920 for a vertical spot) H.264 High CRF 17, AAC 192k; one measured static gain, a limiter at 192 kHz and again at 48 kHz; captions overlaid after the downscale; the length capped at the runtime | `finish_spot.py --stage deliver` |
| finals | every approved spot's `-final` EDL | `deliver/final/<deliver_base>-final.mp4` after QC | `final_renders.sh` |

Every intermediate is 10-bit 4:2:2 or better; 4:2:0 and 8 bits appear only in the deliverable. Probe
every mezzanine for `yuv422p10le` — a codec name does not tell you its bit depth (`video-finish` §5b).
The script-fidelity gate runs before stage 1 (`video-edit-edl`); the VO stem is rebuilt before the master;
the captions are rendered before the deliver leg. A stage log ends with `FINISH-END <stage>` or it failed.

## The per-shot upscale tier (SOP 92 / 105)

```
approved take (the operator's pick)
  head ≥ ~50 px tall in the 480×854 take, or no text to read
        → local Rhea ×4 (free, ~6 min per 5 s take; the cleanest arm: least flat-area noise, least flicker)
  head < ~50 px (≈ 1/15 of frame height — any full-body wide), or text / fine graphics that must read
        → hosted Starlight Precise 2.6 ×4 FROM THE ORIGINAL TAKE (never stacked on Rhea); cost line + GO first;
          then check identity across cuts (a small face is reconstructed plausibly, not faithfully) and invented small text
  a punch-in (zoom) on a Rhea hero → Iris ×1 after Rhea, marginal; Iris ×4 alone is softer than Rhea
  a take generated above 480 native → upscale from its native version, never from a flattened master
```

Do not post-scale in the upscale pass: the deliver leg does the downscale, which is what keeps the grain.
Real footage already at the delivery raster, with no grain on the deliverable, takes NO upscale arm: the normalise resamples
it to the display shape by lanczos and nothing is redrawn (since 2026-09-26: 1080p deliverables only, no footage warped).

## The per-shot normalise — before the look (P31, 2026-09-26)

A cube or a `.drx` is the grade step and assumes normalised input. On an auction spot the library look alone read pale
beside a hand-written level chain (the raw clips spanned 32–185 of 0–255 at saturation 2–4 where the approved grade read
12): the hand chain WAS the normalise step, and the cube had replaced it instead of following it.
`normalise_shots.py` makes the step explicit, per shot:

- **levels** — the 0.5/99.5 luma percentiles over five frames of the window → 0.02/0.88, the black point kept ≤ 0.30, the
  white point ≥ 0.70 and the stretch capped at ×1.8 (a normalise, never a creative contrast push). Mapping to 0/1 clipped
  7–30 % of the brightest shots under the look's own gain and exposure; at 0.02/0.88 the Dehancer heroes clipped ≤ 0.01 %.
- **saturation** — a factor about BT.709 luma (a `colorchannelmixer` matrix) that lands the levelled chroma on
  `t-scale × the median chroma of footage the operator approved`, clamped to ×0.70–×1.80. The Dehancer `ads-clean.drx`
  (250D/2383, TI 35) finishes ~27 % less saturated than the cube's estimate: at `--t-scale 0.75` the heroes read 0.0249
  against a 0.0302 target; at 0.91 the client shots' median read 0.0301. Use 0.75 when the grade is the cube alone.
- **the flat** — 16-bit RGB in, ProRes 422 HQ 10-bit limited range out, BT.709 tags, an untagged HD source read as BT.709
  (swscale's own default is BT.601 at every size), the display shape by lanczos (scaled up to a 1080 short side, never
  down: a 4K source keeps its pixels for the crops downstream), and the first frame at pts 0.
- **the read-back** — `verify` per hero: 10-bit, raster, frames, the flat's start, mean |dY| > 1/255, a (0, 0) phase
  correlation, the frame alignment. It does NOT see what happens after the hero: the plan's seek into it is the next
  place a frame can slip (below), and `qc_deliverable.py --prev <pre-finish> --prev-expect finish` is the row that does.
- **the seek into a hero** — the target frame is the one NEAREST the plan's in-time (`round(in × fps)`: ±0.5 frame of
  picture-to-sound sync; `ceil` leaves the picture up to a frame early on a synced shot), and the seek is that frame's own
  start, floored at the decimals the plan keeps: `in = floor((f_in − f0) / fps)`. **A seek between frames followed by an
  `fps` filter doubles the first frame whenever the next frame starts more than half a frame after the seek point**: the
  filter rounds that frame into output slot 1 and the muxer copies it into slot 0, so the whole event plays one frame
  late. On one spot (2026-09-26) in-points at x.2 and x.4 of a frame had done it to 4 of 22 events in the approved version
  itself; a half-frame in-point into the heroes, `(k − 0.5) / fps`, came out of their 1/12288 s timebase as an exact
  0.5-frame tie that rounded up and did it to 14 of 22; where `f_in = f0` it went negative and did it anyway. A builder
  closes the whole class with `setpts=PTS-STARTPTS` before its `fps` filter. No per-hero check can see it — the finished
  spot against the previous version can (`qc_deliverable.py --prev … --prev-expect finish`), and it reads the approved
  version's own slips as `retimed` until the in-points take the nearest frame.

The look sheet renders every candidate on the normalised frame (`look_sheet.py --normalise auto`), beside a
normalised-only column; a sheet pick is provisional until one spot has been watched in motion at full size.
Generate clean at 480p — no grain, halation or bloom in a prompt (baked grain upscales to smeared noise).
Budget shape for a seven-spot campaign: all-Starlight ≈ $55, wides only ≈ $13, Rhea everywhere $0 + ~4 h GPU.

## Running the chain

Each step earns a cheap verification immediately before it runs (`QC.md` § audio provenance): a 1:1 crop
before a grain step (the `.drx` may already lay it), a correlation before an audio re-lay, `ffprobe` before
a crop. A plan step is a hypothesis about a file you have not read yet.

- **Local upscale**: detached (`video-production/scripts/detach.py --log <abs log> -- …`), every path absolute, a
  timeout above the job; a Bash-backgrounded run dies at 10 min. Poll the log on demand. **A missing
  completion sentinel = failure whatever the file size** — a truncated mezzanine silently shortens the
  deliverable. Nothing else touches that GPU while it runs.
- **The hero pass**: **Resolve 21** open with a PROJECT loaded (not the project picker), driven on
  **`--transport auto`** — the ladder tries Local external scripting first and falls through to the in-app
  bridge (Workspace › Scripts › resolve_bridge; it runs silently, so check the PORT, never a window).
  **Never pin `--transport local`: it `die()`s rather than falling through**, so a transport that is merely
  unavailable reads as a hard failure. **Local's availability is NOT predictable from who launched Resolve.**
  An earlier reading — that the refusal is scoped to WHO LAUNCHED the instance — was refuted: a human-launched
  Studio 21 with a project open refused `scriptapp("Resolve")` under both an 18.5 and the portable 21's own
  `RESOLVE_SCRIPT_LIB`, while the in-app bridge answered and `auto` rendered. What differed was the LAUNCHER —
  a portable Resolve started through its own launcher installs the sandbox junctions that redirect
  `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve` at the portable's tree, and a direct `Resolve.exe` start
  does not. Treat Local as the preferred rung and the bridge as the one that always answers; let `auto` decide
  per run. Measured again later: a GUI instance started from the portable's `Resolve.exe` directly — no launcher
  process, both Blackmagic data trees plain folders rather than the launcher's junctions — refused Local; the
  bridge answered and `auto` rendered every hero. Without the junctions a direct start presumably reads and writes
  the installed version's own data trees, worth one line to whoever runs Resolve. Until then `hero_pass.sh` passed
  `--transport bridge` whatever its header said. **Diagnose before escalating** — a scripting probe answers "is it
  reachable, and on what project" for free, and the window title names the open project; process memory size is
  not evidence about whether a project is open. One clip per call, one render job at a time, fresh timeline names.
  The media pool caches paths: a re-imported
  path returns an empty list and a render of the OLD duration — fresh filenames per version.
- **Heroes of equal frame count have identical byte sizes** (DNxHR) — verify distinctness by frame hash
  (`hero_distinct.py`) before trusting a listing.
- **Hosted upscale** (`upscale_fal_topaz.py`): pre-flight prints clips and seconds; `--confirmed` is the echo
  of the GO; the request id is logged BEFORE polling and `--resume` re-attaches — a billed job is never
  resubmitted; `COMPLETED` is not success until the file is on disk and probed; the billing header is late
  (re-fetched after 20 s) and the receipt keeps both reads.
- **Disk**: a ProRes pair per version fills a drive (a drive at 4.7 GB free took the whole environment down); the free space of the
  target is part of every status line; check before moving anything (a project tree reaches 200 GB quickly). Three rules
  from the second outage (2026-09-15, 62 GB of superseded mezzanines in one day, the host drive full under a build):
  the free space that matters is the HOST drive's — a VM's disk image never shrinks, so `df` inside the guest is not free
  space; scratch and intermediates live on the host drive, where a deleted file frees space at once; a mezzanine is never
  `.bak`-copied (a copy doubles the footprint — `.bak` is for small project files). `finish_spot.py` refuses to start under
  its floor (`--min-free-gb`, 40 GB or 3x the spot's mezzanine pair), and at every phase boundary
  `video-production/scripts/project_size.py` lists the superseded derived set by category for the operator to name.

## The deliverable contract

- **1080p masters only**; H.264 High 4:2:0, CFR at the EDL's fps, AAC 48 kHz 192k, faststart; the campaign's TP target sits
  ≈ 1 dB under the platform ceiling because AAC overshoots (`spot-audio-assembly` § mix).
- **Chat send only ≤ 30 MiB** (uploads over ~20 MiB time out); otherwise the full path in the ask; a
  section excerpt as a small clip is fine.
- **Never re-encode a deliverable** to make a variant; every variant comes from the graded mezzanine;
  a byte-capped variant is two-pass at a derived bitrate ~6 % under (`video-finish` §8).
- **Finals**: named versions per spot, each a `-final` EDL with the card event swapped, rendered by ONE sequential script into
  `deliver/final/`; a per-shot Starlight replacement goes INTO final and the Rhea version stays in
  `deliver/`.
- Platform folklore is answered by a lookup before an encode changes (the X "custom bitrate forces highest
  res" claim was false: X re-encodes everything, 1080p ceiling). YouTube: upload 1440p so the VP9/AV1
  ladder serves 1080p playback with the grain intact.
- Ads delivery spec (paid social, 2026): 9:16 1080×1920 · H.264 progressive (never HEVC for paid) · CFR ·
  AAC stereo 48 kHz ≥ 128 kbps · Rec.709, no HDR · safe zones top 150 px / bottom 350 px / right 10 % ·
  TikTok ≤ 500 MB, Meta < 200 MB. Ship 24 fps CFR at the EDL's rate; a 30 fps request is
  `fps=30` duplication, never optical flow on dialogue.
