/**
 * DSP Constants
 * ITU-R BS.1770-4 compliant constants for audio processing
 */

// ITU-R BS.1770-4 K-weighting filter specifications
export const K_WEIGHTING = {
  HIGH_SHELF_FREQ: 1681.97,   // Hz - Head-related transfer function correction
  HIGH_SHELF_GAIN: 4.0,       // dB
  HIGH_SHELF_Q: 0.71,         // Q factor (approximately 1/sqrt(2))
  HIGH_PASS_FREQ: 38.14,      // Hz - DC blocking / rumble filter
  HIGH_PASS_Q: 0.5            // Q factor
};

// LUFS gating thresholds (ITU-R BS.1770-4)
export const LUFS_CONSTANTS = {
  BLOCK_SIZE_SEC: 0.4,           // 400ms measurement blocks
  BLOCK_OVERLAP: 0.75,           // 75% overlap (100ms hop)
  ABSOLUTE_GATE_LUFS: -70,       // Absolute threshold in LUFS
  ABSOLUTE_GATE_LINEAR: 1e-7,    // Math.pow(10, -70/10) = 1e-7
  RELATIVE_GATE_OFFSET: 0.1,     // -10 dB below ungated mean (10^(-10/10) = 0.1)
  LOUDNESS_OFFSET: -0.691        // Reference offset for LUFS calculation
};

// Default limiter settings
export const LIMITER_DEFAULTS = {
  CEILING_DB: -1,           // Default ceiling in dB
  CEILING_LINEAR: 0.891,    // Math.pow(10, -1/20)
  LOOKAHEAD_MS: 3,          // Lookahead time in ms
  RELEASE_MS: 100,          // Release time in ms
  KNEE_DB: 3,               // Soft knee width in dB
  PRESERVE_TRANSIENTS: true // Enable transient preservation
};

// Exciter defaults
export const EXCITER_DEFAULTS = {
  hpfFreq: 6000,  // Higher cutoff (was 3500) to avoid exciting harsh mid-range artifacts
  hpfSlope: 12,   // dB/oct
  drive: 0.5,     // Saturation amount
  bias: 0.2,      // Distort bias
  mix: 0.15       // Parallel mix amount (was 18% in comment, but usually 0-1 range or 0-100)
};

// Audio processing defaults
export const AUDIO_DEFAULTS = {
  SAMPLE_RATE: 48000,
  BIT_DEPTH: 24,
  TARGET_LUFS: -14
};
