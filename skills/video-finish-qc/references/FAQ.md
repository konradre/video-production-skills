# Post questions — and the answers that held

| question | answer |
|---|---|
| Watermark now, or after the grade and the upscale? | After everything: on the final master, overlaid AFTER the downscale so the mark stays crisp; an un-watermarked master is archived clean (`video-finish` §7). |
| Flatten the multi-cut edit first, then bring it back as one file for Dehancer / LUT? | No. Upscale and grade the KEEPERS individually (the hero chain), then conform: flattening a 480p timeline throws away every take's native detail before the upscaler sees it, and a temporal upscaler smears across the cuts of a flattened edit. |
| What resolution for the flattened output? | The mezzanine raster the upscale produced (2160×3840 for a ×4.5 vertical), never the delivery raster; the deliver leg downscales, which is what keeps the grain. |
| DNxHR HQX 12-bit or 10-bit? | 10-bit 4:2:2 is the floor for every intermediate (ProRes 422 HQ first, DNxHR HQX second); the upscaled mezzanine is 10-bit 4:2:0 from the tool anyway, so 12 bits buy nothing downstream. Probe the file — a request for 10 bits can silently give 8. |
| Upscale first, or Dehancer / LUT then upscale? | Upscale first. Grade before the upscale and the reconstructor rebuilds the halation as photographed detail. |
| Which upscaler, and why? | The reconstructive tier (Rhea local by default; Starlight Precise 2.6 from the take where faces are small or text must read); a faithful upscaler on 480p produces enlarged 480p. Local Rhea is $0 and hours; hosted Starlight is dollars and minutes — and the tier is chosen per SHOT, not per pipeline. |
| Is the Rhea route the alternative when Starlight 2.6 is not used? | Yes — and the finish follows `video-finish` tailored to ads for the Dehancer pass and the LUT: the ads pair is the clean look (`ads-clean` cube + its `.drx`); the film pairs are for film. |
| Does Resolve need to be open with the clip on a timeline? | Open with a PROJECT loaded and the bridge script started; the pass creates its own timeline per clip. One job at a time. |
| What about the film grain — is there a free alternative to Dehancer? | Grain is a bitrate decision, not an aesthetic one: skip it for phone-tier placements; coarse only, on a mezzanine above delivery resolution; ffmpeg's native grain is a valid free arm; never a second pass over a `.drx` that already carries grain (`video-finish` §6). |
| Should the after-grade A/B decide the upscaler? | Yes — the finish factor and the arm are judged on graded, delivery-encoded output, not on raw upscales. |
| 720p previews for chat? | No — 1080p masters only; a file over 30 MiB is named by its path. |
| Does a custom high bitrate force X to serve the highest resolution? | No (looked up before changing the encode): X re-encodes everything, 1080p ceiling. |
| The music swells in and out around the voice — is a second track playing? | Measure before listening in the mix: difference the short-term loudness against a static sum of the same parts (a flat line = no processing), then read each VO file's gap floor. Two causes have produced it — a dynamic loudness pass riding the programme, and VO files lifted from a finished cut that carry its bed (`spot-audio-assembly` MIX-AND-QC.md). |
| What loudness when the client supplied a reference video? | Its own measured level — the client approved it. The finisher prints the loudest limiting-free target for the mix; the house −14 LUFS is the default only when there is no reference. |
