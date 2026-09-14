/**
 * Multiband Compression Module
 * 3-band compressor with crossover filters
 *
 * Bands:
 * - Low: < 250Hz
 * - Mid: 250Hz - 5kHz
 * - High: > 5kHz
 *
 * Features:
 * - Linkwitz-Riley crossover filters for phase coherence
 * - Per-band threshold, ratio, attack, release
 * - Makeup gain per band
 * - Presets for different use cases
 */

import { dbToLinear, linearToDb } from './utils.js';

/**
 * Crossover frequencies for 3-band split
 */
export const CROSSOVER_DEFAULTS = {
  LOW_MID: 250,    // Hz
  MID_HIGH: 5000,  // Hz
};

/**
 * Multiband compression presets
 */
export const MULTIBAND_PRESETS = {
  gentle: {
    low: { threshold: -20, ratio: 2.0, attack: 30, release: 150, makeup: 0 },
    mid: { threshold: -18, ratio: 1.8, attack: 25, release: 120, makeup: 0 },
    high: { threshold: -16, ratio: 1.5, attack: 20, release: 100, makeup: 0 }
  },
  balanced: {
    low: { threshold: -24, ratio: 3.0, attack: 25, release: 120, makeup: 1 },
    mid: { threshold: -22, ratio: 2.2, attack: 20, release: 100, makeup: 1 },
    high: { threshold: -20, ratio: 2.0, attack: 15, release: 80, makeup: 1 }
  },
  aggressive: {
    low: { threshold: -28, ratio: 4.0, attack: 20, release: 100, makeup: 2 },
    mid: { threshold: -26, ratio: 2.8, attack: 18, release: 80, makeup: 2 },
    high: { threshold: -24, ratio: 2.5, attack: 12, release: 60, makeup: 2 }
  },
  master: {
    low: { threshold: -18, ratio: 2.5, attack: 30, release: 200, makeup: 0 },
    mid: { threshold: -16, ratio: 2.0, attack: 20, release: 150, makeup: 0 },
    high: { threshold: -14, ratio: 1.8, attack: 15, release: 100, makeup: 0 }
  }
};

/**
 * Biquad filter coefficients for Linkwitz-Riley crossover
 * LR4 = two cascaded Butterworth 2nd order filters
 */
function calcLinkwitzRileyCoeffs(sampleRate, frequency, type) {
  const omega = 2 * Math.PI * frequency / sampleRate;
  const sin = Math.sin(omega);
  const cos = Math.cos(omega);
  const Q = 0.7071067811865476; // 1/sqrt(2) for Butterworth

  const alpha = sin / (2 * Q);

  let b0, b1, b2, a0, a1, a2;

  if (type === 'lowpass') {
    b0 = (1 - cos) / 2;
    b1 = 1 - cos;
    b2 = (1 - cos) / 2;
    a0 = 1 + alpha;
    a1 = -2 * cos;
    a2 = 1 - alpha;
  } else { // highpass
    b0 = (1 + cos) / 2;
    b1 = -(1 + cos);
    b2 = (1 + cos) / 2;
    a0 = 1 + alpha;
    a1 = -2 * cos;
    a2 = 1 - alpha;
  }

  return {
    b0: b0 / a0,
    b1: b1 / a0,
    b2: b2 / a0,
    a1: a1 / a0,
    a2: a2 / a0
  };
}

/**
 * Apply biquad filter to samples
 */
function applyBiquad(samples, coeffs, state = null) {
  const output = new Float32Array(samples.length);
  let x1 = state?.x1 || 0;
  let x2 = state?.x2 || 0;
  let y1 = state?.y1 || 0;
  let y2 = state?.y2 || 0;

  const { b0, b1, b2, a1, a2 } = coeffs;

  for (let i = 0; i < samples.length; i++) {
    const x0 = samples[i];
    const y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;

    x2 = x1;
    x1 = x0;
    y2 = y1;
    y1 = y0;

    output[i] = y0;
  }

  if (state) {
    state.x1 = x1;
    state.x2 = x2;
    state.y1 = y1;
    state.y2 = y2;
  }

  return output;
}

/**
 * Split signal into 3 bands using Linkwitz-Riley crossover
 */
function splitBands(samples, sampleRate, lowMidFreq, midHighFreq) {
  // First crossover: split into low and mid+high
  const lpCoeffs1 = calcLinkwitzRileyCoeffs(sampleRate, lowMidFreq, 'lowpass');
  const hpCoeffs1 = calcLinkwitzRileyCoeffs(sampleRate, lowMidFreq, 'highpass');

  // LR4: apply twice for 24dB/oct slope
  let low = applyBiquad(samples, lpCoeffs1);
  low = applyBiquad(low, lpCoeffs1);

  let midHigh = applyBiquad(samples, hpCoeffs1);
  midHigh = applyBiquad(midHigh, hpCoeffs1);

  // Second crossover: split mid+high into mid and high
  const lpCoeffs2 = calcLinkwitzRileyCoeffs(sampleRate, midHighFreq, 'lowpass');
  const hpCoeffs2 = calcLinkwitzRileyCoeffs(sampleRate, midHighFreq, 'highpass');

  let mid = applyBiquad(midHigh, lpCoeffs2);
  mid = applyBiquad(mid, lpCoeffs2);

  let high = applyBiquad(midHigh, hpCoeffs2);
  high = applyBiquad(high, hpCoeffs2);

  return { low, mid, high };
}

/**
 * Simple compressor for a single band
 */
function compressBand(samples, sampleRate, settings) {
  const {
    threshold = -20,
    ratio = 2.0,
    attack = 20,
    release = 100,
    makeup = 0
  } = settings;

  const output = new Float32Array(samples.length);
  const thresholdLin = dbToLinear(threshold);
  const makeupLin = dbToLinear(makeup);

  const attackCoef = Math.exp(-1 / (attack * sampleRate / 1000));
  const releaseCoef = Math.exp(-1 / (release * sampleRate / 1000));

  let envelope = 0;

  for (let i = 0; i < samples.length; i++) {
    const inputAbs = Math.abs(samples[i]);

    // Envelope follower
    if (inputAbs > envelope) {
      envelope = attackCoef * envelope + (1 - attackCoef) * inputAbs;
    } else {
      envelope = releaseCoef * envelope + (1 - releaseCoef) * inputAbs;
    }

    // Calculate gain reduction
    let gain = 1.0;
    if (envelope > thresholdLin) {
      const overDB = linearToDb(envelope / thresholdLin);
      const reductionDB = overDB * (1 - 1 / ratio);
      gain = dbToLinear(-reductionDB);
    }

    output[i] = samples[i] * gain * makeupLin;
  }

  return output;
}

/**
 * Multiband Compressor class
 */
export class MultibandCompressor {
  /**
   * Create a multiband compressor
   * @param {Object} options - Configuration options
   */
  constructor(options = {}) {
    this.lowMidFreq = options.lowMidFreq || CROSSOVER_DEFAULTS.LOW_MID;
    this.midHighFreq = options.midHighFreq || CROSSOVER_DEFAULTS.MID_HIGH;
    this.preset = options.preset || 'balanced';
  }

  /**
   * Get settings for a preset
   * @param {string} presetName - Preset name
   * @returns {Object} Band settings
   */
  getPresetSettings(presetName) {
    return MULTIBAND_PRESETS[presetName] || MULTIBAND_PRESETS.balanced;
  }

  /**
   * Process audio buffer with multiband compression
   *
   * @param {AudioBuffer} buffer - Input audio buffer
   * @param {string|Object} settings - Preset name or custom settings
   * @param {Function} onProgress - Progress callback
   * @returns {AudioBuffer} Compressed audio buffer
   */
  process(buffer, settings = 'balanced', onProgress = null) {
    const bandSettings = typeof settings === 'string'
      ? this.getPresetSettings(settings)
      : settings;

    const output = new AudioBuffer({
      numberOfChannels: buffer.numberOfChannels,
      length: buffer.length,
      sampleRate: buffer.sampleRate
    });

    for (let ch = 0; ch < buffer.numberOfChannels; ch++) {
      const input = buffer.getChannelData(ch);
      const out = output.getChannelData(ch);

      // Split into bands
      const bands = splitBands(input, buffer.sampleRate, this.lowMidFreq, this.midHighFreq);

      if (onProgress) onProgress((ch + 0.3) / buffer.numberOfChannels);

      // Compress each band
      const compressedLow = compressBand(bands.low, buffer.sampleRate, bandSettings.low);
      const compressedMid = compressBand(bands.mid, buffer.sampleRate, bandSettings.mid);
      const compressedHigh = compressBand(bands.high, buffer.sampleRate, bandSettings.high);

      if (onProgress) onProgress((ch + 0.8) / buffer.numberOfChannels);

      // Sum bands back together
      for (let i = 0; i < input.length; i++) {
        out[i] = compressedLow[i] + compressedMid[i] + compressedHigh[i];
      }

      if (onProgress) onProgress((ch + 1) / buffer.numberOfChannels);
    }

    return output;
  }
}

/**
 * Convenience function for multiband compression
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {string} preset - Preset name ('gentle', 'balanced', 'aggressive', 'master')
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Compressed audio buffer
 */
export function applyMultibandCompression(buffer, preset = 'balanced', onProgress = null) {
  const compressor = new MultibandCompressor();
  return compressor.process(buffer, preset, onProgress);
}

/**
 * Apply gentle multiband compression for subtle control
 */
export function applyGentleCompression(buffer, onProgress = null) {
  return applyMultibandCompression(buffer, 'gentle', onProgress);
}

/**
 * Apply mastering-style multiband compression
 */
export function applyMasteringCompression(buffer, onProgress = null) {
  return applyMultibandCompression(buffer, 'master', onProgress);
}
