/**
 * Stereo Processing Module
 * Mid/Side stereo processing with width control and bass mono
 *
 * Features:
 * - M/S encoding/decoding
 * - Stereo width control
 * - Bass mono (mono below frequency threshold)
 * - Side channel filtering
 * - Stereo balance adjustment
 */

import { dbToLinear, linearToDb } from './utils.js';

/**
 * Default stereo processing settings
 */
export const STEREO_DEFAULTS = {
  WIDTH: 1.0,           // 0 = mono, 1 = normal, 2 = extra wide
  BASS_MONO: true,      // Enable bass mono
  BASS_FREQ: 200,       // Frequency below which to mono
  BALANCE: 0.0,         // -1 = left, 0 = center, 1 = right
  MID_GAIN: 0,          // Mid channel gain in dB
  SIDE_GAIN: 0,         // Side channel gain in dB
};

/**
 * Stereo width presets
 */
export const STEREO_PRESETS = {
  mono: { width: 0, bassMono: false, bassFreq: 200 },
  narrow: { width: 0.5, bassMono: true, bassFreq: 200 },
  normal: { width: 1.0, bassMono: true, bassFreq: 200 },
  wide: { width: 1.3, bassMono: true, bassFreq: 150 },
  extraWide: { width: 1.6, bassMono: true, bassFreq: 120 },
  superWide: { width: 2.0, bassMono: true, bassFreq: 100 },
};

/**
 * Simple highpass filter coefficients
 */
function calcHighpassCoeffs(sampleRate, frequency) {
  const omega = 2 * Math.PI * frequency / sampleRate;
  const cos = Math.cos(omega);
  const sin = Math.sin(omega);
  const alpha = sin / (2 * 0.7071);

  const b0 = (1 + cos) / 2;
  const b1 = -(1 + cos);
  const b2 = (1 + cos) / 2;
  const a0 = 1 + alpha;
  const a1 = -2 * cos;
  const a2 = 1 - alpha;

  return {
    b0: b0 / a0,
    b1: b1 / a0,
    b2: b2 / a0,
    a1: a1 / a0,
    a2: a2 / a0
  };
}

/**
 * Apply biquad filter
 */
function applyFilter(samples, coeffs) {
  const output = new Float32Array(samples.length);
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;

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

  return output;
}

/**
 * Stereo Processor class
 */
export class StereoProcessor {
  /**
   * Create a stereo processor
   * @param {Object} options - Configuration options
   */
  constructor(options = {}) {
    this.width = options.width ?? STEREO_DEFAULTS.WIDTH;
    this.bassMono = options.bassMono ?? STEREO_DEFAULTS.BASS_MONO;
    this.bassFreq = options.bassFreq ?? STEREO_DEFAULTS.BASS_FREQ;
    this.balance = options.balance ?? STEREO_DEFAULTS.BALANCE;
    this.midGain = options.midGain ?? STEREO_DEFAULTS.MID_GAIN;
    this.sideGain = options.sideGain ?? STEREO_DEFAULTS.SIDE_GAIN;
  }

  /**
   * Encode L/R to M/S
   *
   * @param {Float32Array} left - Left channel
   * @param {Float32Array} right - Right channel
   * @returns {Object} { mid, side }
   */
  encodeMS(left, right) {
    const mid = new Float32Array(left.length);
    const side = new Float32Array(left.length);

    for (let i = 0; i < left.length; i++) {
      mid[i] = (left[i] + right[i]) * 0.5;
      side[i] = (left[i] - right[i]) * 0.5;
    }

    return { mid, side };
  }

  /**
   * Decode M/S to L/R
   *
   * @param {Float32Array} mid - Mid channel
   * @param {Float32Array} side - Side channel
   * @returns {Object} { left, right }
   */
  decodeMS(mid, side) {
    const left = new Float32Array(mid.length);
    const right = new Float32Array(mid.length);

    for (let i = 0; i < mid.length; i++) {
      left[i] = mid[i] + side[i];
      right[i] = mid[i] - side[i];
    }

    return { left, right };
  }

  /**
   * Process audio buffer with stereo enhancement
   *
   * @param {AudioBuffer} buffer - Input audio buffer (must be stereo)
   * @param {Function} onProgress - Progress callback
   * @returns {AudioBuffer} Processed audio buffer
   */
  process(buffer, onProgress = null) {
    if (buffer.numberOfChannels !== 2) {
      console.warn('[Stereo] Input is not stereo, returning unchanged');
      return buffer;
    }

    const output = new AudioBuffer({
      numberOfChannels: 2,
      length: buffer.length,
      sampleRate: buffer.sampleRate
    });

    const left = buffer.getChannelData(0);
    const right = buffer.getChannelData(1);
    const outLeft = output.getChannelData(0);
    const outRight = output.getChannelData(1);

    // Encode to M/S
    const { mid, side } = this.encodeMS(left, right);

    if (onProgress) onProgress(0.2);

    // Apply bass mono (highpass filter on side channel)
    let processedSide = side;
    if (this.bassMono && this.bassFreq > 0) {
      const hpCoeffs = calcHighpassCoeffs(buffer.sampleRate, this.bassFreq);
      processedSide = applyFilter(side, hpCoeffs);
    }

    if (onProgress) onProgress(0.4);

    // Apply width
    const midGainLin = dbToLinear(this.midGain);
    const sideGainLin = dbToLinear(this.sideGain) * this.width;

    const processedMid = new Float32Array(mid.length);
    const processedSideFinal = new Float32Array(processedSide.length);

    for (let i = 0; i < mid.length; i++) {
      processedMid[i] = mid[i] * midGainLin;
      processedSideFinal[i] = processedSide[i] * sideGainLin;
    }

    if (onProgress) onProgress(0.6);

    // Decode back to L/R
    const decoded = this.decodeMS(processedMid, processedSideFinal);

    // Apply balance
    const balanceL = this.balance < 0 ? 1 : 1 - this.balance;
    const balanceR = this.balance > 0 ? 1 : 1 + this.balance;

    for (let i = 0; i < decoded.left.length; i++) {
      outLeft[i] = decoded.left[i] * balanceL;
      outRight[i] = decoded.right[i] * balanceR;
    }

    if (onProgress) onProgress(1.0);

    return output;
  }

  /**
   * Apply a preset
   * @param {string} presetName - Preset name
   */
  applyPreset(presetName) {
    const preset = STEREO_PRESETS[presetName];
    if (preset) {
      this.width = preset.width;
      this.bassMono = preset.bassMono;
      this.bassFreq = preset.bassFreq;
    }
  }
}

/**
 * Convenience function for stereo width adjustment
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {number} width - Width (0 = mono, 1 = normal, 2 = extra wide)
 * @param {boolean} bassMono - Enable bass mono
 * @param {number} bassFreq - Bass mono frequency
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Processed audio buffer
 */
export function adjustStereoWidth(buffer, width = 1.0, bassMono = true, bassFreq = 200, onProgress = null) {
  const processor = new StereoProcessor({ width, bassMono, bassFreq });
  return processor.process(buffer, onProgress);
}

/**
 * Apply preset-based stereo processing
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {string} preset - Preset name
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Processed audio buffer
 */
export function applyStereoPreset(buffer, preset = 'normal', onProgress = null) {
  const processor = new StereoProcessor();
  processor.applyPreset(preset);
  return processor.process(buffer, onProgress);
}

/**
 * Convert stereo to mono
 */
export function stereoToMono(buffer, onProgress = null) {
  return applyStereoPreset(buffer, 'mono', onProgress);
}

/**
 * Widen stereo image
 */
export function widenStereo(buffer, amount = 1.3, onProgress = null) {
  return adjustStereoWidth(buffer, amount, true, 200, onProgress);
}

/**
 * Apply bass mono (mono bass, stereo highs)
 */
export function applyBassMono(buffer, frequency = 200, onProgress = null) {
  return adjustStereoWidth(buffer, 1.0, true, frequency, onProgress);
}

/**
 * Analyze stereo correlation
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @returns {Object} { correlation, width, balance }
 */
export function analyzeStereo(buffer) {
  if (buffer.numberOfChannels !== 2) {
    return { correlation: 1, width: 0, balance: 0 };
  }

  const left = buffer.getChannelData(0);
  const right = buffer.getChannelData(1);

  let sumL = 0, sumR = 0, sumLR = 0;
  let sumL2 = 0, sumR2 = 0;
  let peakL = 0, peakR = 0;

  for (let i = 0; i < left.length; i += 100) {
    const l = left[i];
    const r = right[i];

    sumL += l;
    sumR += r;
    sumLR += l * r;
    sumL2 += l * l;
    sumR2 += r * r;

    peakL = Math.max(peakL, Math.abs(l));
    peakR = Math.max(peakR, Math.abs(r));
  }

  const n = Math.floor(left.length / 100);
  const meanL = sumL / n;
  const meanR = sumR / n;

  // Pearson correlation coefficient
  const numerator = sumLR - n * meanL * meanR;
  const denominator = Math.sqrt((sumL2 - n * meanL * meanL) * (sumR2 - n * meanR * meanR));
  const correlation = denominator > 0 ? numerator / denominator : 1;

  // Stereo width estimate (0 = mono, 1 = normal stereo)
  const width = 1 - Math.abs(correlation);

  // Balance (-1 = left, 0 = center, 1 = right)
  const totalPeak = peakL + peakR;
  const balance = totalPeak > 0 ? (peakR - peakL) / totalPeak : 0;

  return {
    correlation: Math.round(correlation * 100) / 100,
    width: Math.round(width * 100) / 100,
    balance: Math.round(balance * 100) / 100
  };
}
