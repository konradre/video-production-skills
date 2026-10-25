# SFX and music — sourcing, the syllable map, cues, ducks

## SFX sourcing ladder

1. **The take's own sound** — the knock, the thud, the tear, the shout: cut from the take at the frame
   and placed as an sfx where the picture needs it (`video-edit-edl` § carried sound), the native muted
   where it played. Free, and it is the room.
2. **A library sound** — Freesound through a domain-scoped search plus the constructed HQ preview URL
   (the site's search pages are a JS login shell); read the licence line per sound: CC0 = no credit,
   CC BY = a credit line in the post copy, which is the operator's send-time call.
3. **Generated sound** — ElevenLabs sound generation as the paid fallback (a fixed credit cost per
   generation → cost line + GO).
4. "Something zanier" from the operator = a sourcing round, not a filter tweak.

## Reel → syllable map → cut

A pick from a reel is confirmed as a **syllable map before cutting**: which onsets, in which order, the
bitten-off one excluded — the map is read back to the operator and confirmed before the cut.
`sfx_onsets.py` lists every onset by ordinal and time so the operator's ordinal ("the second last one
that starts at 0:43") is a sample-exact `--cut a:b`. Cuts carry 5 ms fades; every sfx is 48 kHz 24-bit
WAV.

## Placement rules

- **A sound is placed by its SYNC POINT on the visual event it belongs to, never by a guessed offset** (mg-styles-15
  `lib/audio/README.md` § 1): a one-shot or an impact syncs on its transient, a whoosh on its pass-by peak (its loudest
  moment), a riser, a reverse cymbal or a swell on its END — the hit it drives into. A riser placed by its start lands early
  by however long its build runs. `scripts/sfx_onsets.py <file> --sync transient|peak|end [--src-in --dur] --event <T>`
  reads the point (a one-shot trimmed tight to its hit included) and prints the `at` that puts it on T, the EDL's `sync`
  block and the file's `derived` stamp; a plan sfx with a `sync` and no `at` is placed by it (`edl_build.py`), and
  `edl_check.py` fails a sound whose sync point has left its event — a re-timed marker, an insert.
- **Levels by construction**: bring every effect to one common level before it is placed (the donor normalises each to
  ≈ −18 dB short-term, peak ≤ −1 dBFS, which sits it about 2 dB over its bed), so `vol` states intent only — about −6 dB
  for a subtle sound, +2 for the hero hit — never a repair for a file that arrived at another level.
- **VO never overlaps an sfx** — stagger; a couplet's halves sit either side of the sound.
- **The audio signature sits on the END CARD** and its hit lands on the card's burst: the file starts
  a hair after the card cut (`card + 0.02`) so that the hit inside the file (at +T0, e.g. 0.83 s) meets
  the card's burst frame; the card's burst frame is what moves to meet it (`designed-elements`), found by
  PSNR and verified by region brightness.
- A native artifact — a tiny click where a shot cuts, a distorted onset, a generated drone — is muted by
  `native_audio_from/to`, and the hole is filled with **synthesized room tone** (`roomtone_synth.py`):
  a pasted slice carries the take's artifacts, and a hard mute reads as a hole.
- Designed-sound extras (the name-pop chimes on a product display) are **opt-in, default off**.
- **A creator-style spot has no music under the open** — room tone carries the hook; a cue may enter under the demo,
  ducked under every line; the disclosure line is never ducked over or covered by an sfx; no sign-off signature (the
  sub-genre carries none — `ad-spot-preprod` UGC-GRAMMAR.md § The beats, MIX-AND-QC.md § The phone-mic register).

## Sound direction — silences, suck-outs, impacts, the low end

lemo-opuscar judges a film by its sound first (`DIRECTOR.md` §§ 6, 11; `styles/satellite-briefing/STYLE.md` § Mix; the
suck-outs in its `demo/mix.py` files). These hold for every genre unless a line says otherwise.

- **Two real silences before the turn — films and music videos** (a 15 s ad already carries its one
  silence, before the hit). At least two silences or near-silences before the turn or the emotional peak, and the first
  sound after one is among the most important sounds in the piece. A suck-out is its own rule, never one of the two. The
  EDL names the turn's marker in `qc.turn`.
- **A suck-out before each designed impact**: 0.25–0.6 s in which the music and the foley drop 25–30 dB, reached by a
  50–80 ms ramp and released ON the impact (lemo's windows: 0.27–0.63 s at −26 to −30 dB, ramps of 50 and 80 ms). The
  music's half is a duck carrying its own ramps, `[from, to, 0.03, 0.06, 0]` — −30 dB, a 60 ms ramp in, full again AT `to`,
  the hit (`video-edit-edl` EDL-CONTRACT.md § audio). The foley's half is placement: an sfx ends at the suck-out's start
  (its `dur`), a take's own sound at `native_audio_to` or a cut on the hit, and a riser or sweep that drives INTO the hit is
  synced on it and stays. `edl_check.py` warns on any sfx, take sound or line that plays inside a suck-out.
- **The two or three designed impacts are the loudest moments of the mix.** The master is a static sum, so nothing
  compresses them; the read is the delivered file's loudest 400 ms windows and what the EDL places there.
- **The low end stays lean**: 20–60 Hz about 15 dB under the full band, music and foley high-passed around 36–44 Hz (lemo's
  mixes: 35–46 Hz). A cue that arrives heavier is filtered before it is placed.
- **Every row of the sound table is in the mix, and the EDL's audio block is the table.** On the delivered file: each sfx at
  its `at`, read around its sync point when it has one (`qc_deliverable.py`'s sfx row), each sync point on its event
  (`edl_check.py`), and each music cue's presence across its span, each suck-out's depth, the silences before the turn, the
  loudest moments and the low end (`scripts/sound_table.py` — INFO rows only until the reads are measured on two real
  deliverables).

## Music

- **The AceDataCloud Suno API is the DEFAULT music route** (house rule, 2026-09-12). `POST
  https://api.acedata.cloud/suno/audios`, `Authorization: Bearer $ACEDATACLOUD_API_TOKEN` sourced from the
  env file that holds it and never placed on a command line. Model **`chirp-v5-5`** — the vendor's own
  client ships an `.env.example` pinning `chirp-v4-5`, so never copy that file into place. `instrumental: true` for a bed; custom mode
  (`custom: true` with `lyric`, `title`, `style`, `vocal_gender`) when the cue is written rather than
  described. **Always async:** the call returns a task id; poll `POST /suno/tasks` with `{"id": "<task id>"}`
  every 3–5 s, ≈ 2 min 20 s to finish. **One call ≈ 0.56 credits ≈ $0.08 and returns TWO takes**
  (≈ $0.04 a take) — a billed generation, so it goes behind the cost line and the operator's GO like every
  other venue. `duration` (10–360 s) applies only to a custom-mode call and is a target, not a cap: an
  unguided generation returned 5.5 minutes. Downloads are **Opus inside `.m4a`** — Resolve rejects them, so
  transcode before anything reads them: `ffmpeg -i <cue>.m4a -ar 48000 -c:a pcm_s24le <cue>.wav`. The vendor
  exposes no balance endpoint — track spend from the receipts. No music client ships here: the call above is
  the whole contract, and the vendor publishes its own skill for it.
- **Every other music route is a FALLBACK and needs the operator's permission first** — the operator's own
  candidates under `audio/music/candidates/`, or a library bed with its licence line read. Name which route
  and why, then wait. A vendor outage or a refused cue is a reason to ask, never a reason to switch quietly.
- The reseller licence question for a paying-client deliverable is the operator's call, raised once.
- **A cue is cut to the marker it ends on** (the before cue to the HIT) from the head of the candidate;
  the file name carries the length. **A cue shorter than its span is looped on its own beat grid by whole bars, the
  take's ending kept, before a longer cue is priced** — `scripts/music_loop.py` plays the take to a beat A, jumps back a
  bar multiple to a beat B on the same bar phase, crossfades the join (40 ms, equal power) and plays through the take's
  own ending, whose hit then lands exactly the jump later; the operator listens across the join before it enters a build.
  With no `--bpm` the grid comes from `scripts/beat_grid.py`, which CHECKS it: a least-squares line through the tracked
  beats (a tracker's tempo number was 2 % off; its beat times were right), accepted only when the beats sit within ±15 ms
  of it and the kicks drift under 10 ms across the take, its phase taken from the kicks (a tracker locked onto off-beat hats
  put a synthetic grid half a beat off — measured 2026-09-29); 2x or 0.5x only when the kicks say so. A BEAT-MAP verdict
  (the tempo moves) loops on the tracked beats, and an irregular interval is named — a skipped beat breaks the bar phase
  (a 38.8 s take under a 57.9 s spot, zero spend, 2026-09-15). A cue neither looped nor long enough just ENDS mid-shot —
  `edl_check` fails it.
- **The earlier accepted cue wins** — a cue the operator approved is the campaign's cue for that beat.
- A cue slams in ON the reveal marker (`fade_in: 0`); the bed under the turntable and card runs to the
  end; the hit shot and the line after it carry only native sound.
- **Ducks** under speech, per cue: `[[from, to, gain]]` timeline seconds with 0.25 s linear ramps,
  rendered as a per-frame volume expression by the finisher — 0.25 under a disclaimer, 0.5 under a dub or
  a shout, 0.32 under the closer; the music never fights the VO. A duck may carry its own ramp, `[from, to, gain, ramp]`,
  or two, `[from, to, gain, ramp_in, ramp_out]` — a suck-out's `ramp_out` is 0 (§ Sound direction).
- A cue spanning an insert keeps playing under it (`edl_insert.py` moves only its end).
