# The EDL — what the finisher reads, field by field

One JSON per version, paths relative to the project root. The finisher's stages (cut → master → deliver)
read nothing else; the VO stem, the captions and the loudness pass are all rebuilt from it. A time in
this file is DERIVED by a builder — a typed number is a defect waiting for the next re-version.

```
{ spot, deliver_base, version, fps, canvas:[w,h], runtime_s, source, source_script, grade_note,
  events:[…], post_layers:[…], audio:{vo, music, sfx, captions, caption_style, loudnorm,
  captions_dir, word_times, silence?}, markers:{NAME: absolute s} }
```

## events[] — one per cut, in timeline order

| field | meaning | trap |
|---|---|---|
| `id` | `<SPOT>-<shot>` in the shot-list vocabulary; a floor insert `C1f`; a montage copy `M3` | an id absent from the beat list = an invented beat (the gate fails it) |
| `take` | the keeper's source file | null = no keeper picked yet — the finisher refuses to run |
| `in`, `out` | take seconds, rounded to the frame; the window = the keeper | the out-point sits ≥ 1 frame BEFORE the take's own next cut (rogue frames at 0:16 shipped once) |
| `tl` | `[start, end]` on the timeline; `end − start == out − in` | accumulated by the builder, never typed |
| `src` | the pre-graded hero (`edit/hero/<stem>__rhea-1x4__ads-clean.mov` or a windowed `-win` hero); `a|b` alternatives resolve by the finisher's file rule, the first that exists | with a `src` the event's `look` is `none` — the hero pass already graded it |
| `look` | `none` (pre-graded hero) · a cube name (`ads-clean`) for an upscaled mezzanine or a designed render | a look on a hero grades it twice |
| `source` | `designed` for a rendered element (turntable, card); no `src`, native resolution, no handles | |
| `role` | `endcard` on at most one event — the finisher cuts the footage at its `tl[0]` and concatenates the card; a spot whose beat list forbids a card has none | the card is 2.5 s FULL; captions never run over it; `edl_check --require-endcard` holds a card where the script has one |
| `handle_head` | where the in-point sits inside the SOURCE the finisher seeks | **the seek convention**: a full-take hero needs `handle_head = in`; a pre-trimmed upscale input needs the handle written by `trim_for_upscale.py`; `0` with `in > 0` ran a spot 0.3 s late for four versions |
| `native_audio_vol` | the take's own audio as a bed (0 = muted) | only when the keeper EARNED it (its knock, its thud, its rip) |
| `native_audio_from` / `_to` | take seconds between which the native plays | mute a generated drone before the hit; mute from a dub's onset; mute a rap the cut would truncate into a click |
| `zoom`, `anchor` | a punch-in: crop 1/zoom around `[ax, ay]` fractions | keeps a stale state out of a close-up without a regen |
| `accepted_cuts` | take seconds of cuts INSIDE the window that belong to the keeper — a long generation composed them and the operator kept them; `accepted_cuts_note` says why | cut presence is descriptive, consistency across the cut is the verdict (`video-take-review`); undeclared, `edl_check --cuts` and the delivery QC's leak row fail a keeper the operator chose |
| `montage_of` | `{edl, event}` when the event is a COPY of a delivered spot's event | the window may run past the delivered event; `handle_head` shifts with the new in |
| `note` | the script line it serves + the operator's words that shaped it | the note is the audit trail; keep the quote |

## post_layers[] — RGBA frame sequences composited at the mezzanine

`{id, frames (printf pattern), at, dur, note}`. A layer that must clear on a beat is placed by
`layer_before_next = [id, lead]` in the beats file (the wipe wall: opaque from +0.29 s, placed at
the join − 0.5 s; the after cue slams in when it clears = the REVEAL marker).

**The hit shot plays the take's OWN burst nearly to the take's end** (out ≈ the take's end − 0.25 s),
and the transition wall over it is a per-spot choice, never a default: an out-point 0.75 s after the bang
under a 0.5 s wall lead was rejected twice as cut too early, and the transition itself was struck. Dropping the
wall means the builder's `--no-wall` AND removing that beat's `layer_before_next` together. Keep the take's
native audio through the shower (the bang and the paper whoosh live there); a whispered "repeat" of the
shouted line inside the bang IS the bang, not a voice — read the RMS profile before muting anything. An
out-point re-cut is a four-minute re-render: offer the knob, never guess the taste twice.

## audio

- `vo` — scalars `stem` (never another spot's file), `target_lufs`, `peak_cap_dbfs`; then one entry per
  placed line `{file, at, dur, lufs, text, source, lip_synced?, floor_ok?, note}`. The stem builder places EVERY
  entry with a `file` (a `startswith('L')` filter once dropped the O.S. line). `vo_full` may carry the unplaced full
  lines. `text` is the script's words and the captions' display text. `source` says where the file came from — a TTS
  job id, a clone id, or `extracted_from: <path> @ <s>` (an excerpt of a finished mix carries its bed). `lip_synced:
  true` marks a line the picture was generated to: its `at` is re-measured against the take whenever the file
  changes. `floor_ok: "<why>"` admits a line whose gap floor the stem builder would refuse.
- `music` — `{file (a|b alternatives, globs), tl:[a,b], vol, fade_in, fade_out, duck:[[from,to,gain]…],
  duck_ramp}`. A cue SHORTER than its span just ends (no loop, no fade) — cut a longer excerpt. Ducks are
  timeline seconds inside the cue span.
- `sfx` — `{file, at, dur, vol, src_in?}`; `src_in` windows a longer file. A take's own sound re-timed
  (a knock a beat earlier, a word's tail over the next shot, a tear carried across the cut) is an sfx
  cut from the take, with the native muted where it played.
- `captions` — `[{line, words:[i,j]}]` word ranges on the narrator's lines ONLY; `caption_style` is the
  campaign standard (no punctuation; every key checked — `spot-audio-assembly` CAPTIONS.md); word times from
  `word_times` (Scribe or faster-whisper, hand patches preserved by `--only`). Two cards never share a frame; none
  over the card.
- `loudnorm` — `{I, TP, LRA}`: `I` is the target the deliver leg reaches with ONE measured static gain, `TP` the
  limiter ceiling; the client reference's own level when there is one. Verified on the DELIVERED file every time.

## markers — absolute timeline seconds, written by the builder

`HIT` (the hit's RMS peak), `ME` (a word onset), `REVEAL` (the frame a wall clears), `MONTAGE`
`[a,b]`. The beats file holds the same markers as `{event, take}`; the builder rewrites them so the
gate stays in step when a pick moves.

## Derived constants — stamped with their inputs

A number the plan MEASURED from files — a bed's `vol` sized against the VO stem, a duck gain, a lip-synced line's
`at`, a loudness target read off a reference — carries a `derived` block on the entry that holds it:

```
"derived": {"from": ["audio/ref/stem-vo.wav", "audio/vo/stem.wav"], "method": "music-under-voice, 50 ms blocks …",
            "sha256": {"audio/ref/stem-vo.wav": "…", "audio/vo/stem.wav": "…"}}
```

`edl_build.py` re-hashes every input on every build and FAILS when one changed since the number was derived: the
prose note beside a constant is exactly what goes stale in silence when an input is replaced. `--stamp-derived`
records the hash of an input that has none — run it right after the measurement, never to silence a FAIL (a stale
constant is re-measured, then re-stamped). `--allow-stale-derived` builds anyway and prints every stale input.

## Files and versions

- `edit/<SPOT>-EDL.json` is the working file; a shipped EDL is never edited again. A re-version is a
  NEW file (`-v9i`), a final is `-final` with the card event swapped; the older versions stand.
- Every writer drops `<file>.bak-<ts>-<why>` beside the file first — the project tree has no VCS.
- An alternate deliverable is its own EDL with its own audio map and captions, never a flag on the main one.

## The plan (`edl_build.py`)

The plan is the EDL with every time replaced by a reference. `events[]` carry `take/in/out` (+ `src`,
`look`, `source`, `role`, `vol`, `native_from/to`, `zoom/anchor`, `accepted_cuts/accepted_cuts_note`, `note`);
`vo` lines carry `file`, `at`, `text` (+ `source`, `lip_synced`, `floor_ok`); any entry may carry `derived`;
`markers` are `{event, take}` MEASURED on the keeper; every `at` and `tl` is a **time ref**:

| ref | resolves to |
|---|---|
| `12.5` | the number (only for a measured absolute — rare) |
| `"start"` / `"end"` | 0 / the runtime |
| `"HIT"` | the marker |
| `"S01B-13"` / `"S01B-13.end"` | the event's tl start / end |
| `{"marker":"HIT","offset":-0.5}` | marker + offset |
| `{"event":"S01B-A1","take":1.958}` | a take time inside the event (the O.S. line at its take time) |
| `{"event_start":"S01B-14","offset":0.02}` | the sting on the card |
| `{"vo_ends_before":"HIT","gap":0.5}` | this line ENDS 0.5 s before the hit, floored to the frame |
| `{"before_vo":"L0","gap":0.1}` | this line ends 0.1 s before L0 starts (the narrator chain, derived backwards) |
| `{"after_vo":"L1","gap":0.3}` | this entry starts 0.3 s after L1 ends |

A spot-specific builder (a Python file with argparse where every slot is a flag) is the same thing with
the plan inlined; keep one when the derivations are richer than the table (a montage windowed on word
times, a wall lead that moves a cue). Either way: `--help` never builds, and the `.bak` lands first.

## Frame-time sampling

Any per-frame plan — a trajectory, a proxy move, a marker walk — is sampled on the shot's real frame times
`[0, (n−1)/fps]`, never across its playing duration `[0, n/fps]`. A 5-frame shot at 5 fps has frames at 0,
0.2, 0.4, 0.6 and 0.8 s: a key placed exactly at the duration lands one frame PAST the last image and never
shows, and sampling across the duration stretches every track by one frame (1/23.5 s per step instead of
1/24 s on a 2 s shot). The same off-by-one moves a hit by a frame at 24 fps; the out-point rule
(`end − 0.25 s`) is measured on frame times.
