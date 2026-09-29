# The acceptance matrix — rows, reads, and what a miss looks like

Output a table per seed, never a score. The continuity row is first and hard-fails. **In a single
generation, cut presence is descriptive; consistency across the cut is the verdict** — a cut the model
composed carries the world across it by construction, a join between two generations gambles on it, and
a take is never failed for containing a cut or graded on the cut's motivation. Rows 5 and 11 exist only when a
product is on screen; the brand's standards and the genre's tone set row 9; the pixel numbers were measured on 480p
takes (`video-production/references/WHAT-VARIES.md`). Rows in reading order:

| # | row | how it is read | breaks as |
|---|---|---|---|
| 0 | **continuity / geometry** — landmarks per camera position across the take's own cuts and against the established shots; the previous keeper's last state at frame 0 | the continuity sheet at 2–4× | the door on the wrong wall; the couch turned the other way; a character on the wrong side of the room |
| 0b | **consistency across composed cuts** — the same faces, wardrobe, room, light and performance register either side of every cut the model composed | `cut_consistency.py`: light, contrast, white balance and palette as multiples of the take's own within-shot baseline; its before/after sheet and `--box` crops at native size for identity and wardrobe | a face that changes across the cut; a garment that changes colour; a room rearranged; a light jump; a performance that resets — never the cut itself |
| 1 | **script beat** — the scripted action is the action; cause before reaction; nothing invented; the reveal at the right frame | the transcript + the tile against the beat list | the model's verb instead of the script's; the reveal shot missing from the cut |
| 2 | **technical** — dims, fps, CFR, duration; the file plays; the internal cut list — DESCRIPTIVE, handed to the edit (a keeper's composed cuts are declared there as `accepted_cuts`), never a fail condition | `ffprobe`, `qc_seed.py` | a short low-angle piece inside a take read as a "zoom shift"; a good long take VOIDed for the cuts it composed |
| 3 | **anatomy** — per person at 3× in a per-person crop | `window_frames.py --box` per person | a double arm from the elbow; a hand missing on one arm |
| 4 | **faces** — undistorted; ≥ ~60 px of face height in the take's native pixels (measured at 480p) where the beat lives — a FLOOR, not a target; identity vs the close shots | 1:1 crops, never a downscale; detail (Laplacian variance) compared with every crop resampled to one size; every detector box confirmed by eye | a distorted nose; a different face after the upscale (a per-shot tier decision); a face over the floor rejected as under-rendered, with less detail at equal size than the accepted faces (`INSTRUMENTS.md` — face detail at equal size) |
| 4b | **attachment** — every reference the take was gated on was sent as a model input, and the product is visible and matches its reference (row 5) | `attach_proof.py --take <take>`: the gate's submission record against the receipt's request record (`inputs`, written from 2026-09-29); an older receipt or a fal take is `UNPROVEN` → the venue's own job record (kie `recordInfo` `param`, the monid run input, the Higgsfield job detail) | a take that looks right with the product sheet never sent — the model drew a plausible product from the prompt's words; a prompt citing a reference whose upload lapsed (1229119561Weike/ai-ugc-factory: MODEL_INPUT_IMAGES_ACTUALLY_ATTACHED, PRODUCT_VISIBLE_AND_MATCHES_REAL_ASSET) |
| 5 | **product** — shape at 2× (exact silhouette, random angles), size by a 4× crop beside the product photo | crop + the SKU photo side by side; `product_aspect.py` only as a cross-check | pieces that read as a different object; pieces aligned in rows; a product too wide for the real SKU |
| 6 | **composition / eyelines** — nobody into the lens; the line-deliverer faces the camera (never back-to-camera); every gesture motivated in this framing; the reaction faces its cause; the emotion matches; no focus pull off the face; the camera holds its lock | the tile + NCC scale-match of the upper 45 % between frames | a character looking into the camera; a back to the camera; an unmotivated gesture; joy at a collapse; a focus shift to the background |
| 7 | **audio** — whisper each seed: word-like events on an unscripted mouth = shouting; scripted words intelligible; a generated tone at the head; the hit's RMS peak time | `qc_seed.py` transcript + peak; a 50 ms flatness/peak scan | an unscripted character shouting over the music; a near-homophone of the scripted word; a background music artifact |
| 8 | **named state** — every frame of every window after the event, wides included, at 4× with gamma lifted in dark cavities | `window_frames.py --zoom 4 --gamma 1.6` | the state undone in a later frame (teeth back in) — in the wide too |
| 9 | **dignity** — awake; nobody touched unless scripted; nobody left lying under an effect; hands high, visible, held; no hand at the bottom edge of a chest-up two-shot | the tile at 2× | a depiction that reads as abuse; a hand where it cannot be shown |
| 10 | **realism** — natural poses; dance not jerky; no phantom extra; a runner from behind; the subject in the last frame. On a creator-style / UGC take, the TELLS pass: read with the sound OFF first; the hands and fingers on the product; a torso static longer than ~6–7 s (`frame_psnr.py` reads > 45 dB); consonant lip drift inside the first 1–2 s of a line; the product changing between shots; the background warping when the subject moves, lines going wavy, shadows not following; a phone or a camera UI in frame; the same face on screen past its budget (the composited real proof at the demo beat is what relieves it) | the tile; `frame_psnr.py`; the 1:1 crops on hands and mouth | unnatural poses; another person in the background; a runner running backwards while facing the camera, fading out at the end; on a UGC take: a hand with the wrong fingers on the jar, a presenter frozen from the shoulders down, a mouth a syllable late on every "p" and "b", a jar that changed shape at the cut, a kitchen whose tiles bent, a phone drawn into her hand |
| 11 | **plausibility of the product's fall** — haphazard placement, not aligned; landed pieces not raining before a burst | the sheet | pieces raining before anything has fired |

## The lever a miss pulls

A void names its row, and the row names what the NEXT generation changes — so a miss re-rolls a cause, never the same
request (studiomi300's shot critic labels its misses "so the planner knows which lever to pull on retry"; its labels map
onto our rows, in brackets). Where the house rules already name the lever, it is quoted from them.

| row | the lever on a miss |
|---|---|
| 0 continuity / geometry | the start image = the previous keeper's LAST frame (the standing rule); the scene proxy's grey frame for a new angle — never more prose (`video-gen-cost-gate` § 1, the mode table) |
| 0b across composed cuts [CHARACTER_DRIFT, WARDROBE_DRIFT] | one continuity partition as ONE refs-only generation with a look plate per light context; the references, not the prompt, carry identity and wardrobe |
| 1 script beat [WALKING_BACKWARDS] | the script's verb in the prompt, cause before reaction as timecoded beats; the reveal on its frame |
| 3 anatomy [HAND_FINGER_ARTIFACT] | another seed on the same prompt (the miss is stochastic); after two, fewer hands in frame or a tighter framing |
| 4 faces | the face at its floor size in the start image or a tight reference — the face decides, not the mode (§ 1 mode table) |
| 4b attachment | re-host the lapsed reference and resubmit under a NEW scene key; an input the gate never saw is gated before the next call |
| 5 product [OBJECT_MORPHING] | the product sheet in the set and ONE still first (the reference dress rehearsal) |
| 6 composition / eyelines [CAMERA_IGNORED] | who looks where, stated; a camera move as the clause plus the proxy clip, never the clause alone (`video-prompt-dialects`) |
| 7 audio | a locked line as an audio reference with its words ABSENT from the prompt (DIALECTS § Supplied-audio polarity); a generated tone at the head → cut it in the edit, not a regen |
| 8 named state | the state in the start image (an exact continuation), or a reference of it |
| 9 dignity [RANDOM_INTIMACY] | restage it in the prompt; never re-roll the same prompt hoping |
| 10 realism [STYLIZED_AI_LOOK, NEON_GLOW_LEAK, EXTRAS_INVADE_FRAME] | another seed first; a repeated tell named in the negative tail; a phantom extra kept out of the partition's references |
| 11 plausibility | haphazard placement stated in the prompt; a still first |

## The window

A keeper is `take + in + out + the state at out`. The operator's trims come as time or fraction ("only
the first 0.9 s", "without the first third", "cut a little off the start", "shave a quarter second off
the end", "cut in to just before the trip", "cut before the heads swivel" = the last still frame by
motion energy). The out-point sits at least one frame before the take's own internal cut. A window whose
last frame hides the face is not continuable by a gen.

## Reporting

One line per seed to the operator: `S02-G4-s2 — VOID: friend seated again at 0 s (continuity)`;
`S02-G4-s1 — KEEPER 0.75→7.8: holds; residual: a stray fleck on the lamp 4.1–4.6 s`;
`S04-P1-s2 — KEEPER 0→15.0: composed cuts at 5.5 and 9.25 s hold on all five axes (declared for the edit)`. Clips by path.
The headline is the worst row, never the best. "not bad" from the operator is not a pick — wait for the
path.
