# The spot pipeline — from approved keepers to a delivered master

`video-finish` fixes the ORDER for one clip (upscale → grade → grain → watermark → downscale → encode).
This file is the same order run over a whole spot from its EDL, with the campaign's contracts.

## Stages and files

| stage | input | output | codec | who |
|---|---|---|---|---|
| upscale, per shot | the APPROVED take (480p) | `edit/upscale-out/<take>__rhea-1x4.mp4` (local) or `edit/upscale-out/<id>.mp4` (hosted) | 10-bit where the tool allows | `upscale_local.sh` / `upscale_fal_topaz.py` |
| hero pass, per clip | the upscaled mezzanine | `edit/hero/<stem>__<look>.mov` DNxHR HQX / ProRes 422 HQ 10-bit 4:2:2, pre-graded | `hero_pass.sh` (Resolve + Dehancer over the bridge) |
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
- **The hero pass**: Resolve open with a PROJECT loaded (not the project picker) and Workspace › Scripts ›
  resolve_bridge started BY THE OPERATOR (it runs silently — check the port, not a window); an agent-launched
  Resolve refuses external scripting. One clip per call, one render job at a time, fresh timeline names. "external scripting refused" = the bridge is
  down → stop and ask the operator to reopen it, then retry. The media pool caches paths: a re-imported
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
