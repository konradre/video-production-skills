/**
 * DSP Module - Barrel Export
 * All DSP functions for audio processing
 */

// Constants
export {
  K_WEIGHTING,
  LUFS_CONSTANTS,
  LIMITER_DEFAULTS,
  AUDIO_DEFAULTS
} from './constants.js';

// Utilities
export {
  applyBiquadFilter,
  calcHighShelfCoeffs,
  calcHighPassCoeffs,
  dbToLinear,
  linearToDb,
  createHannWindow,
  calculateRMS,
  findPeak
} from './utils.js';

// True Peak Detection
export {
  calculateTruePeakSample,
  findTruePeak,
  findChannelTruePeak
} from './true-peak.js';

// LUFS Measurement
export {
  measureLUFS,
  measureShortTermLUFS,
  measureMomentaryLUFS
} from './lufs.js';

// Limiter
export {
  applySoftKneeCurve,
  applySoftKneeOversampled,
  applyLookaheadLimiter
} from './limiter.js';

// Final Filters
export {
  applyBiquadToChannel,
  applyOnePoleLP,
  applyFinalFilters
} from './final-filters.js';

// Normalizer
export {
  normalizeToLUFS,
  applyGain,
  normalizeToPeak,
  calculateLufsGain
} from './normalizer.js';

// FFT
export {
  FFT,
  FFTProcessor,
  processWithFFT,
  analyzeSpectrum
} from './fft.js';

// Saturation
export {
  SATURATION_DEFAULTS,
  Saturator,
  createSaturationCurve,
  createExciterCurve,
  applySaturation,
  applyWarmth,
  applyTapeSaturation
} from './saturation.js';

// Dynamic Leveler
export {
  DYNAMIC_LEVELER_DEFAULTS,
  DynamicLeveler,
  applyDynamicLeveling,
  analyzeDynamics,
  applyVoiceLeveling,
  applyMusicLeveling
} from './dynamic-leveler.js';

// Multiband Compression
export {
  CROSSOVER_DEFAULTS,
  MULTIBAND_PRESETS,
  MultibandCompressor,
  applyMultibandCompression,
  applyGentleCompression,
  applyMasteringCompression
} from './multiband.js';

// Transient Shaper
export {
  TRANSIENT_DEFAULTS,
  TRANSIENT_PRESETS,
  TransientShaper,
  shapeTransients,
  applyTransientPreset,
  addPunch,
  smoothTransients,
  tightenSound
} from './transient.js';

// Multiband Transient Shaper (Suno Optimization)
export {
  applyMultibandTransient
} from './multiband-transient.js';

// Stereo Processing
export {
  STEREO_DEFAULTS,
  STEREO_PRESETS,
  StereoProcessor,
  adjustStereoWidth,
  applyStereoPreset,
  stereoToMono,
  widenStereo,
  applyBassMono,
  analyzeStereo
} from './stereo.js';

// DC Offset Detection/Removal
export {
  detectDCOffset,
  detectDCOffsetBuffer,
  removeDCOffset,
  removeDCOffsetBuffer,
  removeDCOffsetFiltered,
  DC_OFFSET_SEVERITY,
  getDCOffsetSeverity
} from './dc-offset.js';

// Multiband Saturation
export {
  CROSSOVER_DEFAULTS as SATURATION_CROSSOVER_DEFAULTS,
  MULTIBAND_SATURATION_PRESETS,
  MultibandSaturator,
  applyTapeWarmth,
  applyAnalogConsole,
  applyTubePreamp,
  applyMultibandSaturation
} from './multiband-saturation.js';

// Exciter (harmonic enhancement)
export {
  EXCITER_DEFAULTS,
  Exciter,
  applyExciter,
  applyExciterWithOptions
} from './exciter.js';

// Hybrid Dynamic Processor (multiband compression + dynamic EQ + de-esser)
export {
  DEFAULT_BANDS as HYBRID_DYNAMIC_BANDS,
  EnvelopeFollower,
  GainComputer,
  ResonanceDetector,
  HybridDynamicProcessor,
  processHybridDynamic
} from './dynamic-processor.js';

// Soft Clipper (peak reduction before limiting)
export {
  SOFT_CLIPPER_DEFAULTS,
  applySoftClip,
  applyTwoStageSoftClip,
  applyMasteringSoftClip
} from './soft-clipper.js';

