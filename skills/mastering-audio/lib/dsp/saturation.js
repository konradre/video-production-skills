/**
 * Saturation Module
 * Transparent saturation with automatic bypass for quiet sections
 *
 * Features:
 * - Tanh-based saturation curve for warm harmonic generation
 * - Automatic bypass for quiet sections (prevents pumping/noise)
 * - Configurable drive and threshold
 * - Preserves transients through level-dependent processing
 */

import { linearToDb, dbToLinear } from './utils.js';

/**
 * Default saturation settings
 */
export const SATURATION_DEFAULTS = {
  DRIVE: 0.5,              // 0-1, amount of saturation
  THRESHOLD_DB: -18,       // Below this, bypass saturation
  KNEE_DB: 6,              // Transition zone width
  MIX: 1.0,                // Dry/wet mix (1.0 = 100% wet)
  WINDOW_MS: 50,           // Analysis window for level detection
};

/**
 * Saturator class
 * Provides warm harmonic saturation with intelligent bypass
 */
export class Saturator {
  /**
   * Create a saturator
   * @param {Object} options - Configuration options
   */
  constructor(options = {}) {
    this.drive = options.drive ?? SATURATION_DEFAULTS.DRIVE;
    this.thresholdDB = options.thresholdDB ?? SATURATION_DEFAULTS.THRESHOLD_DB;
    this.kneeDB = options.kneeDB ?? SATURATION_DEFAULTS.KNEE_DB;
    this.mix = options.mix ?? SATURATION_DEFAULTS.MIX;
    this.windowMs = options.windowMs ?? SATURATION_DEFAULTS.WINDOW_MS;

    // Pre-generate saturation curve for efficiency
    this.curveResolution = 65536;
    this.curve = this._createCurve(this.drive, this.curveResolution);
  }

  /**
   * Create tanh-based saturation curve
   * Linear below threshold, soft saturation above
   *
   * @param {number} drive - Saturation drive 0-1
   * @param {number} resolution - Curve resolution
   * @returns {Float32Array} Saturation curve
   */
  _createCurve(drive, resolution) {
    const curve = new Float32Array(resolution);
    const driveAmount = 1 + drive * 3; // 1x to 4x drive

    for (let i = 0; i < resolution; i++) {
      // Map index to -1..1
      const x = (i * 2 / resolution) - 1;
      const absX = Math.abs(x);

      if (absX < 0.7) {
        // Linear passthrough in quiet region
        curve[i] = x;
      } else if (absX < 0.85) {
        // Soft transition zone
        const blend = (absX - 0.7) / 0.15;
        const saturated = Math.tanh(x * driveAmount) / Math.tanh(driveAmount);
        curve[i] = x * (1 - blend) + saturated * blend;
      } else {
        // Full saturation
        curve[i] = Math.tanh(x * driveAmount) / Math.tanh(driveAmount);
      }
    }

    return curve;
  }

  /**
   * Create bypass envelope based on signal level
   * Avoids saturating quiet sections which would amplify noise
   *
   * @param {AudioBuffer} buffer - Input audio buffer
   * @returns {Float32Array} Bypass envelope (0 = bypass, 1 = full saturation)
   */
  createBypassEnvelope(buffer) {
    const sampleRate = buffer.sampleRate;
    const windowSamples = Math.floor(sampleRate * this.windowMs / 1000);
    const numWindows = Math.ceil(buffer.length / windowSamples);

    const envelope = new Float32Array(numWindows);
    const threshold = dbToLinear(this.thresholdDB);
    const kneeStart = dbToLinear(this.thresholdDB - this.kneeDB);

    // Use first channel for level detection (or sum for stereo)
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

    // Smooth the envelope (fast attack, slow release)
    const smoothed = new Float32Array(numWindows);
    const attackCoef = 0.8;  // Fast attack
    const releaseCoef = 0.1; // Slow release

    smoothed[0] = envelope[0];
    for (let i = 1; i < numWindows; i++) {
      const coef = envelope[i] > smoothed[i - 1] ? attackCoef : releaseCoef;
      smoothed[i] = smoothed[i - 1] + (envelope[i] - smoothed[i - 1]) * coef;
    }

    return smoothed;
  }

  /**
   * Apply saturation curve to a sample
   * @private
   */
  _saturateSample(sample) {
    // Map sample to curve index
    const normalized = (sample + 1) * 0.5; // 0 to 1
    const index = Math.floor(normalized * (this.curveResolution - 1));
    const clampedIndex = Math.max(0, Math.min(index, this.curveResolution - 1));
    return this.curve[clampedIndex];
  }

  /**
   * Process audio buffer with saturation
   *
   * @param {AudioBuffer} buffer - Input audio buffer
   * @param {Float32Array} bypassEnvelope - Optional bypass envelope from createBypassEnvelope
   * @param {Function} onProgress - Progress callback
   * @returns {AudioBuffer} Saturated audio buffer
   */
  process(buffer, bypassEnvelope = null, onProgress = null) {
    // Create bypass envelope if not provided
    if (!bypassEnvelope) {
      bypassEnvelope = this.createBypassEnvelope(buffer);
    }

    const output = new AudioBuffer({
      numberOfChannels: buffer.numberOfChannels,
      length: buffer.length,
      sampleRate: buffer.sampleRate
    });

    const windowSamples = Math.floor(buffer.sampleRate * this.windowMs / 1000);
    const totalSamples = buffer.length * buffer.numberOfChannels;
    let processedSamples = 0;

    for (let ch = 0; ch < buffer.numberOfChannels; ch++) {
      const input = buffer.getChannelData(ch);
      const out = output.getChannelData(ch);

      for (let i = 0; i < input.length; i++) {
        // Get bypass amount for this sample
        const windowIdx = Math.min(
          Math.floor(i / windowSamples),
          bypassEnvelope.length - 1
        );
        const wetAmount = bypassEnvelope[windowIdx] * this.mix;

        // Apply saturation
        const saturated = this._saturateSample(input[i]);

        // Blend dry/wet based on bypass envelope
        out[i] = input[i] * (1 - wetAmount) + saturated * wetAmount;

        processedSamples++;
      }

      if (onProgress) {
        onProgress((ch + 1) / buffer.numberOfChannels);
      }
    }

    return output;
  }

  /**
   * Update saturation drive (regenerates curve)
   * @param {number} drive - New drive value 0-1
   */
  setDrive(drive) {
    this.drive = Math.max(0, Math.min(1, drive));
    this.curve = this._createCurve(this.drive, this.curveResolution);
  }
}

/**
 * Create a saturation curve for use with WaveShaperNode
 * Can be used with Web Audio API for real-time processing
 *
 * @param {number} drive - Saturation drive 0-1
 * @param {number} resolution - Curve resolution (default 65536)
 * @returns {Float32Array} Saturation curve
 */
export function createSaturationCurve(drive = 0.5, resolution = 65536) {
  const saturator = new Saturator({ drive });
  return saturator.curve;
}

/**
 * Create exciter curve for WaveShaper (with bias for even harmonics)
 * Used for real-time preview of Add Air effect
 *
 * @param {number} drive - Saturation drive (default 2.0)
 * @param {number} bias - Bias for even harmonics (default 0.1)
 * @param {number} resolution - Curve resolution
 * @returns {Float32Array} Exciter curve
 */
export function createExciterCurve(drive = 2.0, bias = 0.1, resolution = 65536) {
  const curve = new Float32Array(resolution);

  for (let i = 0; i < resolution; i++) {
    const x = (i * 2 / resolution) - 1; // -1 to +1
    // Exciter formula: tanh(drive * (x + bias))
    curve[i] = Math.tanh(drive * (x + bias));
  }

  return curve;
}

/**
 * Convenience function for quick saturation
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {number} drive - Saturation drive 0-1 (default 0.5)
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Saturated audio buffer
 */
export function applySaturation(buffer, drive = 0.5, onProgress = null) {
  const saturator = new Saturator({ drive });
  const bypassEnvelope = saturator.createBypassEnvelope(buffer);
  return saturator.process(buffer, bypassEnvelope, onProgress);
}

/**
 * Apply gentle warming saturation
 * Preset for subtle harmonic enhancement
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Processed audio buffer
 */
export function applyWarmth(buffer, onProgress = null) {
  const saturator = new Saturator({
    drive: 0.3,
    thresholdDB: -24,
    mix: 0.5
  });
  return saturator.process(buffer, null, onProgress);
}

/**
 * Apply tape-style saturation
 * Preset for more aggressive analog-style saturation
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Processed audio buffer
 */
export function applyTapeSaturation(buffer, onProgress = null) {
  const saturator = new Saturator({
    drive: 0.7,
    thresholdDB: -12,
    kneeDB: 8,
    mix: 0.8
  });
  return saturator.process(buffer, null, onProgress);
}
