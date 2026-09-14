---
name: mastering-audio
description: >
  Master audio files (especially Suno/Udio AI music) for streaming release with LUFS normalization, true peak
  limiting, and optional enhancements. Triggers — "master this", "master the track", "LUFS normalize", "optimize
  for streaming". Not for a spot's or film's delivery loudness — use video-finish-qc.
triggers:
  - master audio
  - master song
  - master track
  - optimize for streaming
  - suno mastering
  - lufs normalize
---

# Audio Mastering Skill

Master audio files for streaming release using DSP analysis and processing.

## Tool Location

```
~/.claude/skills/mastering-audio/scripts/master.mjs
```

## Workflow

### Phase 1: Analyzing Audio

Run analysis to understand the audio characteristics:

```bash
node ~/.claude/skills/mastering-audio/scripts/master.mjs "<INPUT_FILE>" --analyze --json
```

**Metrics to evaluate:**
- LUFS (loudness) - streaming target is -14 LUFS
- True Peak - should be below -1 dBTP
- Stereo width and correlation
- DC offset presence
- Detected issues (clipping, low headroom, etc.)

### Phase 2: Selecting Approach

Based on analysis, determine processing approach:

**If Suno/Udio AI music:**
- Use `--preset suno` (optimized for AI music characteristics)
- Addresses: harsh 2-4kHz, clipping, overloud output

**If targeting streaming platforms:**
- Use `--preset streaming` for -14 LUFS, conservative processing

**If maximum loudness needed:**
- Use `--preset loud` for -9 LUFS with saturation/punch

**If preserving dynamics:**
- Use `--preset dynamic` for -16 LUFS, minimal processing

**Custom approach (advanced):**
```
--target-lufs N     Target LUFS (default: -14)
--ceiling N         True peak ceiling dB (default: -1)
--deharsh           Reduce harsh frequencies
--add-air           High-frequency sparkle
--warmth            Tape saturation
--punch             Transient enhancement
--stereo-width N    Width percentage (100 = unchanged)
--bit-depth N       16 or 24 (default: 24)
--sample-rate N     Output rate (default: 48000)
```

### Phase 3: Processing Audio

Execute mastering with chosen settings:

```bash
# Using preset
node ~/.claude/skills/mastering-audio/scripts/master.mjs "<INPUT_FILE>" "<OUTPUT_FILE>" --preset suno

# Custom settings
node ~/.claude/skills/mastering-audio/scripts/master.mjs "<INPUT_FILE>" "<OUTPUT_FILE>" --target-lufs -14 --ceiling -1 --deharsh --add-air
```

**Default output:** If no output specified, creates `<input>_mastered.wav` in same directory.

### Phase 4: Verifying Results

Run analysis on processed file to confirm:

```bash
node ~/.claude/skills/mastering-audio/scripts/master.mjs "<OUTPUT_FILE>" --analyze
```

**Success criteria:**
- LUFS within ±0.5 of target
- True peak at or below ceiling
- No clipping warnings
- Stereo correlation positive (not phase-inverted)

## Presets Reference

| Preset    | LUFS | Ceiling | De-harsh | Air | Warmth | Punch | Width |
|-----------|------|---------|----------|-----|--------|-------|-------|
| streaming | -14  | -1      | Yes      | No  | No     | No    | 100%  |
| loud      | -9   | -0.3    | Yes      | Yes | Yes    | Yes   | 105%  |
| dynamic   | -16  | -1      | No       | No  | No     | No    | 100%  |
| suno      | -14  | -1      | Yes      | Yes | No     | Yes   | 102%  |

## Processing Chain

1. DC offset removal
2. Hybrid dynamic processor (de-harsh)
3. High-frequency exciter (air)
4. Tape warmth saturation
5. Multiband transient enhancement (punch)
6. Stereo width adjustment
7. Bass mono (< 200 Hz)
8. Final filters (30 Hz HPF, 18 kHz LPF)
9. LUFS normalization
10. Lookahead true peak limiter

## Dependencies

- Node.js 18+
- ffmpeg (for audio decoding)
- npm dependencies (run `npm install` in skill directory once)

## Example Session

```
User: master this suno track for spotify release
Assistant:
1. Analyzing: node master.mjs song.mp3 --analyze --json
   → LUFS: -9.2, True Peak: +0.3 dBTP (clipping detected)

2. Selecting: Using suno preset (AI music, targeting -14 LUFS)

3. Processing: node master.mjs song.mp3 song_mastered.wav --preset suno
   → Applied: de-harsh, air, punch, bass mono, LUFS normalization, limiting

4. Verifying: node master.mjs song_mastered.wav --analyze
   → LUFS: -14.0, True Peak: -1.0 dBTP (no issues)
   → Ready for streaming release
```
- Deeper context — the upstream projects behind the rules here: `video-production/references/CONTEXT-MAP.md` § Where the deeper context lives.
