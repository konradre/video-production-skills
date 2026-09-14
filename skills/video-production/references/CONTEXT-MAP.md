# The context map — every phase, its skill, its gate, what it takes in and hands on

The map another agent or session needs to pick the work up. Phases run downhill; a phase's output is the next
phase's input, and each phase carries its own gate.

| # | phase | skill | fires on | gate before spending | takes in | hands on |
|---|---|---|---|---|---|---|
| 0 | entry / resume | `video-production` (this) | the operator by name, or the agent when a request names no phase | — | the project root, the genre, the RESUME block | the next phase, named |
| 1a | pre-production (ads) | `ad-spot-preprod` | a brief, a client script, "shot list", "cost plan" | the client text saved verbatim; `script_diff` PASS | the brief, the script, the assets | the shot list, the kit table, the beats, the cost lines |
| 1b | pre-production (film · music video) | `film-preprod` | "story beats", "the premise", "track map" | `arc_check` PASS; the veto map; the hero shot storyboarded; `script_diff` PASS (PREPRODUCTION-CORE.md) | the judges/audience, the track | the beat sheet in seconds, the gens table, the format |
| 2 | references and continuity | `video-refs-continuity` | "continuity", "refs gate", "start image" | 🔴 the REFS GATE (rules + ledger + accepted stills) | the kit, the previous keeper's last state | the accepted reference set by NAME, the start image, the ledger |
| 3 | the prompt | `video-prompt-dialects` | "write the prompt", "lint the prompt" | `prompt_lint` PASS for the venue | the reference set, the script line, the venue | the compiled prompt |
| 4 | the generation call | `video-gen-cost-gate` | "cost line", "GO", "submit the seeds" | 🔴 the cost line + the operator's GO, per call | the prompt, the refs, the venue | the seeds as clips, the receipt |
| 5 | the read | `video-take-review` | "review the seeds", "which take", "check every frame" | continuity FIRST, the acceptance matrix | the seeds, the ledger | keepers with windows, voids with reasons, clips to the operator |
| 6 | the cut | `video-edit-edl` | "build the EDL", "move the line to", "new version" | the beat gate (`beat_sheet` PASS) + `edl_check` | the keepers, the script beats | the EDL version file |
| 7 | the sound | `spot-audio-assembly` | "generate the VO", "dub the line", "the sting", "captions" | 🔴 the cost line per TTS/STT/clone call | the EDL, the script lines | the stem, the cues, the captions, the placement read |
| 7b | music by API · a standalone master | `spot-audio-assembly` (its music route) · `mastering-audio` | a cue to generate, "master this" | 🔴 the cost line + GO per music call; the master's loudness and true peak, measured | the cue brief · the finished mix | cue WAVs at 48 kHz · the mastered file |
| 8 | designed elements | `designed-elements` | "end card", "the turntable", "the wall" | the render's sentinel; the delivered-frame check | the client's art, the kit | renders and PNG layers at their lengths |
| E | a narrated explainer — its own pipeline, designed motion only | `explainer-video` | "make an explainer about", "animated explainer", "turn this article into a video" | the script sign-off and the pilot sign-off; `explainer_timeline.py` PASS; 🔴 the cost line per TTS call | a topic or a text, the approved copy, the voice | the rendered explainer, its `timeline.json`, the QC list |
| 9 | the finish | `video-finish-qc` (runs by `video-finish`) | "render the spot", "final renders", "QC the deliverable" | 🔴 no upscale before approval; the hosted upscale's GO | the EDL, the heroes | the 1080p master, `QC-DELIVERABLE PASS`, finals |
| 9b | one clip's finish | `video-finish` | "which Topaz model", "add the film look", "fit it under Discord's limit" | 🔴 no upscale before approval; a hosted upscale's GO | one approved clip or its graded mezzanine | the tier, the look, the grain decision, a byte-capped variant |
| 10 | the client round | `client-rounds` | "client feedback", "curate the list", "send this" | the operator's per-item answers | the notes, the delivered file | the curated list, the new version, the ask |

## The genre switch

| | ads | film | music video | explainer |
|---|---|---|---|---|
| pre-production | `ad-spot-preprod` | `film-preprod` | `film-preprod` § music video | `explainer-video` §§ 1–4 |
| the unit | a spot (13–60 s), standalone | the film (runtime set by the story) | the track (every second allocated) | the film (runtime from the measured voice) |
| the SSOT | the client's script | the self-revelation paragraph → the beat sheet | the track map | the signed-off script; `facts.md` for every claim |
| the look pair | the clean ads pair | a film pair, chosen by rendering | a film pair | none — designed motion, the palette in the shared layer |
| captions | burned in, narrator only | none | none | in the composition, measured to fit, timed from the narration |
| the sign-off | the card + the audio signature, every spot | none | none | none unless briefed |
| upscale | per shot (Rhea default, Starlight for small faces) | ONE pass on the locked cut | ONE pass on the locked cut | none — rendered at the delivery raster |
| audio | VO stem + cues + captions | generated where required; the mix crests with the push-in | the track itself; the master carries the cut's own audio | the voice at the host's root, loudness-normalised |
| the cut's grammar | hook → reveal → product → turntable → card | the 7-step DNA, the self-revelation at 90 % | placements on the hits, paid by trimming | why → how, step by step → limits → back to the metaphor |

## What every phase shares

- 🔴 A cost line and the operator's GO before ANY billed call (video, image, music, TTS, STT, clone,
  hosted upscale), however small; local upscales, the hero pass, renders, local transcription and uploads are free.
- 🔴 Nothing is upscaled before the operator approved the take; the picks come back as clips by path.
- The client's text is the SSOT; the cast is closed after the first keeper; continuity is the first
  test; the start image is the previous shot's last state.
- Every writer drops a `.bak-<ts>-<why>` beside the file it edits — project trees carry no VCS.
- 1080p masters only; ≤ 30 MiB in chat, else the path; decisions as numbered questions with the cost
  and the full path inline.
- Skills are INVOKED through the Skill tool at the phase they govern, never recalled from memory.

## Where the deeper context lives

The skills carry the rules. Many of those rules were extracted from the open-source projects below, and the
measurements behind the finishing rules are in `video-finish/references/EVIDENCE.md`. Open a project when a rule
is questioned, a venue changes, a new element type appears, or a probe is being designed.

| project | upstream | what it answers |
|---|---|---|
| `ComfyUI-Majoor-OmniCam` | https://github.com/MajoorWaldi/ComfyUI-Majoor-OmniCam | a labelled 3-D scene from one photo (MoGe + SAM3): the blockout behind `scene_blockout.py` / `scene_proxy.py` |
| `h3-storyboard-skill` | https://github.com/phileiny/h3-storyboard-skill | MiniMax H3 storyboard rules — beat density, `<d>`, time steal, the tail |
| `minimax-h3-notes` | https://github.com/matsuo-koya/minimax-h3-notes | H3 prompt-form notes; the local H3 route, declined on estimates and opened once measured (`video-gen-cost-gate/references/LOCAL-H3.md`) |
| `ffmpeg-skill` | https://github.com/kajisho5/ffmpeg-skill | the spike cut rule behind `qc_seed.py`; ffmpeg filter recipes |
| `cdaf` | https://github.com/UditAkhourii/cdaf | the sidecar take-record format behind `qc_seed.py --record / --read / --note` |
| `hyperframes` | https://github.com/heygen-com/hyperframes | the composition and render contract every designed element obeys |
| `VRGDG-SeedVR2-TensorRT-Studio` | https://github.com/vrgamegirl19/VRGDG-SeedVR2-TensorRT-Studio | diffusion restoration as a third upscale tier (the probe is queued, not run) |
| `comfyui-vrgamedevgirl` | https://github.com/vrgamegirl19/comfyui-vrgamedevgirl | API-format graphs driven over HTTP; the dataset → LoRA loop |
| `shrimply` | https://github.com/soirihiroka/shrimply | an agent seam over a live NLE project: read state, typed atomic edits, never the file |
| `WolfCut` | https://github.com/jub0t/WolfCut | an editor architecture doc worth reading before any NLE bridge |
| `wasserman/blockout`, `motion-previs-studio` | https://github.com/wassermanproductions/motion-previs-studio | staged grey-box previs; reference video → pose, depth and a camera solve |
| `anything2explainer` | https://github.com/Vincentwei1021/anything2explainer | a code-drawn narrated explainer kit with a measured craft layer — the composition drivers, readable-time arithmetic, the frame, motion and source instruments; patterns re-authored, no code carried (the toolkit is PolyForm-Noncommercial) |

A rule that cites one of these projects names the project, never a line number in its code, because lines move.
