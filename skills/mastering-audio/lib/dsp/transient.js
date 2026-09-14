/**
 * Transient Shaper Module
 * Envelope-based transient detection and shaping
 *
 * Features:
 * - Fast attack envelope detection
 * - Transient region identification via derivative
 * - Attack boost/cut control
 * - Sustain boost/cut control
 * - Sensitivity adjustment
 */

import { linearToDb, dbToLinear } from './utils.js';

/**
 * Default transient shaper settings
 */
export const TRANSIENT_DEFAULTS = {
  ATTACK: 0.0,          // -1 to 1 (negative = softer, positive = punchier)
  SUSTAIN: 0.0,         // -1 to 1 (negative = tighter, positive = fuller)
  SENSITIVITY: 0.6,     // 0 to 1 (higher = more sensitive)
  ATTACK_TIME_MS: 1,    // Envelope attack time
  RELEASE_TIME_MS: 50,  // Envelope release time
  LOOKBACK_MS: 5,       // Transient detection lookback
};

/**
 * Transient shaper presets
 */
export const TRANSIENT_PRESETS = {
  punch: { attack: 0.5, sustain: -0.2, sensitivity: 0.6 },
  snap: { attack: 0.7, sustain: -0.4, sensitivity: 0.7 },
  smooth: { attack: -0.3, sustain: 0.2, sensitivity: 0.5 },
  tight: { attack: 0.2, sustain: -0.5, sensitivity: 0.6 },
  full: { attack: 0.3, sustain: 0.4, sensitivity: 0.5 },
  drums: { attack: 0.6, sustain: -0.3, sensitivity: 0.8 },
};

/**
 * Transient Shaper class
 */
export class TransientShaper {
  /**
   * Create a transient shaper
   * @param {Object} options - Configuration options
   */
  constructor(options = {}) {
    this.attack = options.attack ?? TRANSIENT_DEFAULTS.ATTACK;
    this.sustain = options.sustain ?? TRANSIENT_DEFAULTS.SUSTAIN;
    this.sensitivity = options.sensitivity ?? TRANSIENT_DEFAULTS.SENSITIVITY;
    this.attackTimeMs = options.attackTimeMs ?? TRANSIENT_DEFAULTS.ATTACK_TIME_MS;
    this.releaseTimeMs = options.releaseTimeMs ?? TRANSIENT_DEFAULTS.RELEASE_TIME_MS;
    this.lookbackMs = options.lookbackMs ?? TRANSIENT_DEFAULTS.LOOKBACK_MS;
  }

  /**
   * Detect envelope using fast attack, slow release
   *
   * @param {Float32Array} channel - Input samples
   * @param {number} sampleRate - Sample rate
   * @returns {Float32Array} Envelope
   */
  detectEnvelope(channel, sampleRate) {
    const envelope = new Float32Array(channel.length);

    const attackSamples = this.attackTimeMs * sampleRate / 1000;
    const releaseSamples = (this.releaseTimeMs + (1 - this.sensitivity) * 100) * sampleRate / 1000;

    const attackCoef = Math.exp(-1 / Math.max(1, attackSamples));
    const releaseCoef = Math.exp(-1 / Math.max(1, releaseSamples));

    let level = 0;

    for (let i = 0; i < channel.length; i++) {
      const abs = Math.abs(channel[i]);

      if (abs > level) {
        level = attackCoef * level + (1 - attackCoef) * abs;
      } else {
        level = releaseCoef * level + (1 - releaseCoef) * abs;
      }

      envelope[i] = level;
    }

    return envelope;
  }

  /**
   * Detect transient regions from envelope derivative
   *
   * @param {Float32Array} envelope - Envelope from detectEnvelope
   * @param {number} sampleRate - Sample rate
   * @returns {Float32Array} Transient map (0-1)
   */
  detectTransients(envelope, sampleRate) {
    const transients = new Float32Array(envelope.length);
    const lookback = Math.floor(this.lookbackMs * sampleRate / 1000);

    // Calculate derivative (rate of change)
    for (let i = lookback; i < envelope.length; i++) {
      const diff = envelope[i] - envelope[i - lookback];

      if (diff > 0) {
        // Positive derivative = rising edge = transient
        // Scale by sensitivity
        transients[i] = Math.min(1, diff * 20 * (0.5 + this.sensitivity));
      }
    }

    // Smooth the transient map
    const smoothed = new Float32Array(envelope.length);
    const smoothWindow = Math.floor(0.002 * sampleRate); // 2ms

    for (let i = smoothWindow; i < envelope.length - smoothWindow; i++) {
      let sum = 0;
      for (let j = -smoothWindow; j <= smoothWindow; j++) {
        sum += transients[i + j];
      }
      smoothed[i] = sum / (smoothWindow * 2 + 1);
    }

    return smoothed;
  }

  /**
   * Calculate sustain map (inverse of transients)
   *
   * @param {Float32Array} transients - Transient map
   * @param {Float32Array} envelope - Signal envelope
   * @returns {Float32Array} Sustain map (0-1)
   */
  detectSustain(transients, envelope) {
    const sustain = new Float32Array(transients.length);
    const threshold = 0.001; // Minimum envelope level to consider

    for (let i = 0; i < transients.length; i++) {
      if (envelope[i] > threshold) {
        // Sustain is where we have signal but no transient
        sustain[i] = Math.max(0, 1 - transients[i] * 2);
      }
    }

    return sustain;
  }

  /**
   * Process audio buffer with transient shaping
   *
   * @param {AudioBuffer} buffer - Input audio buffer
   * @param {Function} onProgress - Progress callback
   * @returns {AudioBuffer} Shaped audio buffer
   */
  process(buffer, onProgress = null) {
    const output = new AudioBuffer({
      numberOfChannels: buffer.numberOfChannels,
      length: buffer.length,
      sampleRate: buffer.sampleRate
    });

    for (let ch = 0; ch < buffer.numberOfChannels; ch++) {
      const input = buffer.getChannelData(ch);
      const out = output.getChannelData(ch);

      // Detect envelope
      const envelope = this.detectEnvelope(input, buffer.sampleRate);

      if (onProgress) onProgress((ch + 0.3) / buffer.numberOfChannels);

      // Detect transients and sustain
      const transients = this.detectTransients(envelope, buffer.sampleRate);
      const sustain = this.detectSustain(transients, envelope);

      if (onProgress) onProgress((ch + 0.6) / buffer.numberOfChannels);

      // Apply shaping
      for (let i = 0; i < input.length; i++) {
        let gain = 1.0;

        // Attack shaping
        if (transients[i] > 0.1) {
          // Boost or cut transients
          const attackGain = 1 + this.attack * 0.5 * transients[i];
          gain *= attackGain;
        }

        // Sustain shaping
        if (sustain[i] > 0.1) {
          // Boost or cut sustain
          const sustainGain = 1 + this.sustain * 0.3 * sustain[i];
          gain *= sustainGain;
        }

        out[i] = input[i] * gain;
      }

      if (onProgress) onProgress((ch + 1) / buffer.numberOfChannels);
    }

    return output;
  }

  /**
   * Apply a preset
   * @param {string} presetName - Preset name
   */
  applyPreset(presetName) {
    const preset = TRANSIENT_PRESETS[presetName];
    if (preset) {
      this.attack = preset.attack;
      this.sustain = preset.sustain;
      this.sensitivity = preset.sensitivity;
    }
  }
}

/**
 * Convenience function for transient shaping
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {number} attack - Attack amount (-1 to 1)
 * @param {number} sustain - Sustain amount (-1 to 1)
 * @param {number} sensitivity - Sensitivity (0 to 1)
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Shaped audio buffer
 */
export function shapeTransients(buffer, attack = 0.35, sustain = -0.15, sensitivity = 0.6, onProgress = null) {
  const shaper = new TransientShaper({ attack, sustain, sensitivity });
  return shaper.process(buffer, onProgress);
}

/**
 * Apply preset-based transient shaping
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {string} preset - Preset name
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Shaped audio buffer
 */
export function applyTransientPreset(buffer, preset = 'punch', onProgress = null) {
  const shaper = new TransientShaper();
  shaper.applyPreset(preset);
  return shaper.process(buffer, onProgress);
}

/**
 * Add punch to drums/percussion
 */
export function addPunch(buffer, onProgress = null) {
  return applyTransientPreset(buffer, 'punch', onProgress);
}

/**
 * Smooth out harsh transients
 */
export function smoothTransients(buffer, onProgress = null) {
  return applyTransientPreset(buffer, 'smooth', onProgress);
}

/**
 * Tighten up the sound (more attack, less sustain)
 */
export function tightenSound(buffer, onProgress = null) {
  return applyTransientPreset(buffer, 'tight', onProgress);
}
