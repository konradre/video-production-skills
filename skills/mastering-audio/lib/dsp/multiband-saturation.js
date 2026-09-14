/**
 * Multiband Saturation Module
 * Combines frequency-selective saturation with intelligent bypass
 *
 * Features:
 * - 3-band Linkwitz-Riley crossover (LR4, -24dB/oct)
 * - Per-band drive, bias, mix, and gain
 * - Bias control for even harmonics (tube/tape character)
 * - Intelligent bypass envelope to prevent noise amplification
 * - Presets for different saturation characters
 */

import { dbToLinear } from './utils.js';

/**
 * Crossover frequencies
 */
export const CROSSOVER_DEFAULTS = {
  LOW_MID: 200,   // Hz - separates bass from mids
  MID_HIGH: 4000, // Hz - separates mids from highs
};

/**
 * Multiband saturation presets
 */
export const MULTIBAND_SATURATION_PRESETS = {
  tapeWarmth: {
    name: 'Tape Warmth',
    description: 'Subtle vintage warmth, gentle harmonics',
    f1: 200,
    f2: 4000,
    low:  { drive: 0.2, bias: 0.0,  mix: 0.3, gain: 0 },
    mid:  { drive: 0.4, bias: 0.1,  mix: 0.5, gain: 0 },
    high: { drive: 0.3, bias: 0.05, mix: 0.4, gain: 0 },
    bypass: { thresholdDb: -24, kneeDb: 6, windowMs: 100, lookaheadMs: 5 }
  },
  analogConsole: {
    name: 'Analog Console',
    description: 'Punchy mix glue, classic desk sound',
    f1: 200,
    f2: 4000,
    low:  { drive: 0.3, bias: 0.0,  mix: 0.4, gain: 0 },
    mid:  { drive: 0.5, bias: 0.15, mix: 0.6, gain: 0 },
    high: { drive: 0.4, bias: 0.1,  mix: 0.5, gain: 0 },
    bypass: { thresholdDb: -24, kneeDb: 6, windowMs: 100, lookaheadMs: 5 }
  },
  tubePreamp: {
    name: 'Tube Preamp',
    description: 'Rich harmonics, vintage character',
    f1: 200,
    f2: 4000,
    low:  { drive: 0.4, bias: 0.1,  mix: 0.5, gain: 0 },
    mid:  { drive: 0.6, bias: 0.2,  mix: 0.7, gain: 0 },
    high: { drive: 0.3, bias: 0.15, mix: 0.4, gain: 0 },
    bypass: { thresholdDb: -24, kneeDb: 6, windowMs: 100, lookaheadMs: 5 }
  }
};

/**
 * Calculate Linkwitz-Riley filter coefficients
 * LR4 = two cascaded Butterworth 2nd order filters (-24dB/oct)
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
function applyBiquad(samples, coeffs) {
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
 * Split signal into 3 bands using Linkwitz-Riley crossover
 */
function splitBands(samples, sampleRate, f1, f2) {
  // First crossover: split into low and mid+high
  const lpCoeffs1 = calcLinkwitzRileyCoeffs(sampleRate, f1, 'lowpass');
  const hpCoeffs1 = calcLinkwitzRileyCoeffs(sampleRate, f1, 'highpass');

  // LR4: apply twice for 24dB/oct slope
  let low = applyBiquad(samples, lpCoeffs1);
  low = applyBiquad(low, lpCoeffs1);

  let midHigh = applyBiquad(samples, hpCoeffs1);
  midHigh = applyBiquad(midHigh, hpCoeffs1);

  // Second crossover: split mid+high into mid and high
  const lpCoeffs2 = calcLinkwitzRileyCoeffs(sampleRate, f2, 'lowpass');
  const hpCoeffs2 = calcLinkwitzRileyCoeffs(sampleRate, f2, 'highpass');

  let mid = applyBiquad(midHigh, lpCoeffs2);
  mid = applyBiquad(mid, lpCoeffs2);

  let high = applyBiquad(midHigh, hpCoeffs2);
  high = applyBiquad(high, hpCoeffs2);

  return { low, mid, high };
}

/**
 * Multiband Saturator class
 */
export class MultibandSaturator {
  /**
   * Create a multiband saturator
   * @param {Object} options - Configuration options or preset name
   */
  constructor(options = {}) {
    // Load preset if specified
    const preset = typeof options.preset === 'string'
      ? MULTIBAND_SATURATION_PRESETS[options.preset]
      : null;

    // Crossover frequencies
    this.f1 = options.f1 ?? preset?.f1 ?? CROSSOVER_DEFAULTS.LOW_MID;
    this.f2 = options.f2 ?? preset?.f2 ?? CROSSOVER_DEFAULTS.MID_HIGH;

    // Per-band settings
    this.bands = {
      low: {
        drive: options.low?.drive ?? preset?.low?.drive ?? 0.3,
        bias: options.low?.bias ?? preset?.low?.bias ?? 0,
        mix: options.low?.mix ?? preset?.low?.mix ?? 0.5,
        gain: options.low?.gain ?? preset?.low?.gain ?? 0
      },
      mid: {
        drive: options.mid?.drive ?? preset?.mid?.drive ?? 0.3,
        bias: options.mid?.bias ?? preset?.mid?.bias ?? 0,
        mix: options.mid?.mix ?? preset?.mid?.mix ?? 0.5,
        gain: options.mid?.gain ?? preset?.mid?.gain ?? 0
      },
      high: {
        drive: options.high?.drive ?? preset?.high?.drive ?? 0.3,
        bias: options.high?.bias ?? preset?.high?.bias ?? 0,
        mix: options.high?.mix ?? preset?.high?.mix ?? 0.5,
        gain: options.high?.gain ?? preset?.high?.gain ?? 0
      }
    };

    // Bypass envelope settings
    this.bypassThresholdDb = options.bypass?.thresholdDb ?? preset?.bypass?.thresholdDb ?? -24;
    this.bypassKneeDb = options.bypass?.kneeDb ?? preset?.bypass?.kneeDb ?? 6;
    this.windowMs = options.bypass?.windowMs ?? preset?.bypass?.windowMs ?? 50;
    this.lookaheadMs = options.bypass?.lookaheadMs ?? preset?.bypass?.lookaheadMs ?? 5;
  }

  /**
   * Create bypass envelope based on signal level
   * Prevents saturating quiet sections which would amplify noise
   *
   * @param {AudioBuffer} buffer - Input audio buffer
   * @returns {Float32Array} Bypass envelope (0 = bypass, 1 = full saturation)
   */
  createBypassEnvelope(buffer) {
    const sampleRate = buffer.sampleRate;
    const windowSamples = Math.floor(sampleRate * this.windowMs / 1000);
    const numWindows = Math.ceil(buffer.length / windowSamples);

    const envelope = new Float32Array(numWindows);
    const threshold = dbToLinear(this.bypassThresholdDb);
    const kneeStart = dbToLinear(this.bypassThresholdDb - this.bypassKneeDb);

    // Use first channel for level detection (or max of stereo)
    const channel = buffer.getChannelData(0);
    const hasSecondChannel = buffer.numberOfChannels > 1;
    const channel2 = hasSecondChannel ? buffer.getChannelData(1) : null;

    // Analyze peak levels per window
    for (let w = 0; w < numWindows; w++) {
      const start = w * windowSamples;
      const end = Math.min(start + windowSamples, buffer.length);

      let peak = 0;
      for (let i = start; i < end; i += 4) { // Sample every 4th for speed
        let sample = Math.abs(channel[i]);
        if (channel2) {
          sample = Math.max(sample, Math.abs(channel2[i]));
        }
        if (sample > peak) peak = sample;
      }

      // Calculate saturation amount based on level
      if (peak >= threshold) {
        envelope[w] = 1.0;
      } else if (peak >= kneeStart) {
        // Soft knee transition
        const ratio = (peak - kneeStart) / (threshold - kneeStart);
        envelope[w] = ratio * ratio; // Quadratic for smooth transition
      } else {
        envelope[w] = 0.0;
      }
    }

    // Smooth the envelope (moderate attack, slow release to avoid pumping)
    const smoothed = new Float32Array(numWindows);
    const attackCoef = 0.5;  // Moderate attack (was 0.8)
    const releaseCoef = 0.03; // Very slow release to avoid pumping (was 0.1)

    smoothed[0] = envelope[0];
    for (let i = 1; i < numWindows; i++) {
      const coef = envelope[i] > smoothed[i - 1] ? attackCoef : releaseCoef;
      smoothed[i] = smoothed[i - 1] + (envelope[i] - smoothed[i - 1]) * coef;
    }

    // Apply lookahead by shifting envelope backwards in time
    // This makes the envelope open before transients arrive
    const lookaheadWindows = Math.ceil(sampleRate * this.lookaheadMs / 1000 / windowSamples);
    if (lookaheadWindows > 0) {
      const lookaheadEnvelope = new Float32Array(numWindows);
      for (let i = 0; i < numWindows; i++) {
        // Read from future window (or last value if at end)
        const futureIdx = Math.min(i + lookaheadWindows, numWindows - 1);
        lookaheadEnvelope[i] = smoothed[futureIdx];
      }
      return { envelope: lookaheadEnvelope, windowSamples };
    }

    return { envelope: smoothed, windowSamples };
  }

  /**
   * Saturate samples with bias and envelope-controlled mix
   *
   * @param {Float32Array} samples - Input samples
   * @param {Object} bandSettings - Band settings (drive, bias, mix, gain)
   * @param {Float32Array} envelope - Bypass envelope
   * @param {number} windowSamples - Samples per envelope window
   * @returns {Float32Array} Saturated samples
   */
  saturateBand(samples, bandSettings, envelope, windowSamples) {
    const { drive, bias, mix, gain } = bandSettings;
    const output = new Float32Array(samples.length);

    // Pre-calculate bias offset to prevent DC shift
    const biasOffset = Math.tanh(drive * bias);
    const gainLinear = Math.pow(10, gain / 20);

    // Makeup gain to compensate for tanh level reduction
    // tanh(drive * 1) / tanh(drive) = 1, so full-scale signals stay at full scale
    const makeupGain = 1 / Math.tanh(Math.max(drive, 0.1));

    for (let i = 0; i < samples.length; i++) {
      const dry = samples[i];

      // Apply saturation with bias and makeup gain
      // Formula: wet = (tanh(drive * (sample + bias)) - biasOffset) * makeupGain
      const wet = (Math.tanh(drive * (dry + bias)) - biasOffset) * makeupGain;

      // Get envelope value for this sample
      const windowIdx = Math.floor(i / windowSamples);
      const envValue = envelope[Math.min(windowIdx, envelope.length - 1)];

      // Apply saturation scaled by envelope and mix
      // When envValue = 0 (quiet): output = dry
      // When envValue = 1 (loud): output = dry * (1-mix) + wet * mix
      const satAmount = envValue * mix;
      output[i] = (dry * (1 - satAmount) + wet * satAmount) * gainLinear;
    }

    return output;
  }

  /**
   * Process audio buffer with multiband saturation
   *
   * @param {AudioBuffer} buffer - Input audio buffer
   * @param {Function} onProgress - Progress callback (0-1)
   * @returns {AudioBuffer} Processed audio buffer
   */
  process(buffer, onProgress = null) {
    // 1. Create bypass envelope (analyzes overall signal level)
    const { envelope, windowSamples } = this.createBypassEnvelope(buffer);

    const output = new AudioBuffer({
      numberOfChannels: buffer.numberOfChannels,
      length: buffer.length,
      sampleRate: buffer.sampleRate
    });

    for (let ch = 0; ch < buffer.numberOfChannels; ch++) {
      const input = buffer.getChannelData(ch);
      const out = output.getChannelData(ch);

      // 2. Split into 3 bands using Linkwitz-Riley crossover
      const { low, mid, high } = splitBands(input, buffer.sampleRate, this.f1, this.f2);

      if (onProgress) onProgress((ch + 0.2) / buffer.numberOfChannels);

      // 3. Saturate each band with envelope-controlled processing
      const satLow = this.saturateBand(low, this.bands.low, envelope, windowSamples);
      const satMid = this.saturateBand(mid, this.bands.mid, envelope, windowSamples);
      const satHigh = this.saturateBand(high, this.bands.high, envelope, windowSamples);

      if (onProgress) onProgress((ch + 0.8) / buffer.numberOfChannels);

      // 4. Sum bands back together
      for (let i = 0; i < input.length; i++) {
        out[i] = satLow[i] + satMid[i] + satHigh[i];
      }

      if (onProgress) onProgress((ch + 1) / buffer.numberOfChannels);
    }

    return output;
  }
}

/**
 * Apply tape warmth saturation (preset)
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Processed audio buffer
 */
export function applyTapeWarmth(buffer, onProgress = null) {
  const saturator = new MultibandSaturator({ preset: 'tapeWarmth' });
  return saturator.process(buffer, onProgress);
}

/**
 * Apply analog console saturation (preset)
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Processed audio buffer
 */
export function applyAnalogConsole(buffer, onProgress = null) {
  const saturator = new MultibandSaturator({ preset: 'analogConsole' });
  return saturator.process(buffer, onProgress);
}

/**
 * Apply tube preamp saturation (preset)
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Processed audio buffer
 */
export function applyTubePreamp(buffer, onProgress = null) {
  const saturator = new MultibandSaturator({ preset: 'tubePreamp' });
  return saturator.process(buffer, onProgress);
}

/**
 * Apply multiband saturation with custom settings
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {Object} options - Custom settings
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Processed audio buffer
 */
export function applyMultibandSaturation(buffer, options = {}, onProgress = null) {
  const saturator = new MultibandSaturator(options);
  return saturator.process(buffer, onProgress);
}
