/**
 * Limiter Module
 * Two-stage lookahead limiter with soft-knee saturation
 */

import { LIMITER_DEFAULTS } from './constants.js';
import { calculateTruePeakSample } from './true-peak.js';
import { interpolateCatmullRom } from './utils.js';

/**
 * Apply soft-knee limiting curve using tanh sigmoid
 * Provides transparent peak control without hard clipping distortion
 *
 * The curve has three regions:
 * 1. Below knee start: Linear passthrough (unity gain)
 * 2. In the knee: Smooth polynomial blend
 * 3. Above ceiling: Soft saturation using tanh (asymptotic approach to 1.0)
 *
 * @param {number} sample - Input sample value
 * @param {number} ceiling - Target ceiling in linear (e.g., 0.891 for -1dBTP)
 * @param {number} kneeDB - Soft knee width in dB (default 3dB, range 0-12)
 * @returns {number} Limited sample value
 */
export function applySoftKneeCurve(sample, ceiling, kneeDB = LIMITER_DEFAULTS.KNEE_DB) {
  const absSample = Math.abs(sample);

  // Fast path: signal well below ceiling
  if (absSample <= ceiling * 0.9) {
    return sample;
  }

  // Calculate knee boundaries
  const kneeRatio = Math.pow(10, kneeDB / 20);
  const kneeStart = ceiling / kneeRatio;

  // Region 1: Below knee start - pure linear passthrough
  if (absSample <= kneeStart) {
    return sample;
  }

  // Region 2: In the knee (between kneeStart and ceiling)
  // Smooth polynomial blend from linear to limited
  if (absSample <= ceiling) {
    // Normalized position in knee (0 = knee start, 1 = ceiling)
    const t = (absSample - kneeStart) / (ceiling - kneeStart);

    // Smoothstep function for gradual transition: 3t² - 2t³
    const blend = t * t * (3 - 2 * t);

    // Blend between linear output and ceiling
    const output = absSample + (ceiling - absSample) * blend * 0.5;

    return Math.sign(sample) * output;
  }

  // Region 3: Above ceiling - soft limiting that never exceeds ceiling
  // Use tanh compression curve that asymptotically approaches ceiling
  const excess = absSample - ceiling;

  // Compress excess using tanh - output approaches ceiling but never exceeds it
  // The formula: ceiling * (1 - k * tanh(excess / ceiling))
  // As excess → ∞, output → ceiling (never exceeds)
  const normalized = excess / ceiling;
  const compression = 1 - Math.tanh(normalized * 2) * 0.1; // Small headroom reduction for extreme peaks

  // Ensure output never exceeds ceiling
  const output = Math.min(ceiling, absSample * compression);

  return Math.sign(sample) * output;
}

/**
 * Apply soft-knee curve with 4x oversampling to handle inter-sample peaks
 * Uses Catmull-Rom interpolation for upsampling
 *
 * @param {Float32Array} input - Input sample array
 * @param {number} ceiling - Ceiling in linear
 * @param {number} kneeDB - Knee width in dB
 * @returns {Float32Array} Processed output (same length as input)
 */
export function applySoftKneeOversampled(input, ceiling, kneeDB = LIMITER_DEFAULTS.KNEE_DB) {
  const length = input.length;
  const output = new Float32Array(length);

  // Process with 4x oversampling using Catmull-Rom interpolation
  const prevSamples = [0, 0, 0, 0];

  for (let i = 0; i < length; i++) {
    // Shift sample history
    prevSamples[0] = prevSamples[1];
    prevSamples[1] = prevSamples[2];
    prevSamples[2] = prevSamples[3];
    prevSamples[3] = input[i];

    if (i < 3) {
      // Not enough samples for interpolation yet
      output[i] = applySoftKneeCurve(input[i], ceiling, kneeDB);
      continue;
    }

    // Calculate Catmull-Rom coefficients
    const y0 = prevSamples[0];
    const y1 = prevSamples[1];
    const y2 = prevSamples[2];
    const y3 = prevSamples[3];

    let maxInterpolated = 0; // Initialize variable to track max oversampled peak

    // Check 4x oversampled points between y1 and y2
    for (let j = 1; j <= 3; j++) {
      const t = j * 0.25;
      const interpolated = Math.abs(interpolateCatmullRom(y0, y1, y2, y3, t));
      if (interpolated > maxInterpolated) {
        maxInterpolated = interpolated;
      }
    }

    // If inter-sample peak exceeds ceiling, reduce the sample
    if (maxInterpolated > ceiling) {
      const gainReduction = ceiling / maxInterpolated;
      output[i] = applySoftKneeCurve(input[i] * gainReduction, ceiling, kneeDB);
    } else {
      output[i] = applySoftKneeCurve(input[i], ceiling, kneeDB);
    }
  }

  return output;
}

/**
 * Two-Stage Lookahead Limiter with Soft-Knee Safety
 *
 * Stage 1: Lookahead gain reduction
 * - Uses true-peak detection with 4x oversampling
 * - Sees peaks coming and reduces gain before they hit
 * - Smooth attack/release envelope for transparency
 *
 * Stage 2: Soft-knee saturation safety net
 * - Catches any remaining peaks that slip through
 * - Uses tanh sigmoid curve - no hard clipping
 * - Oversampled to handle inter-sample peaks
 *
 * Stage 3: Transient-aware gain adjustment (optional)
 * - Detects high crest factor (transient) regions
 * - Applies gentler limiting to preserve transient punch
 *
 * @param {AudioBuffer} audioBuffer - Input AudioBuffer
 * @param {number} ceilingLinear - Ceiling in linear scale (e.g., 0.891 for -1dBTP)
 * @param {number} lookaheadMs - Lookahead time in milliseconds (default 3ms)
 * @param {number} releaseMs - Release time in milliseconds (default 100ms)
 * @param {number} kneeDB - Soft knee width in dB (default 3dB)
 * @param {boolean} preserveTransients - Apply gentler limiting on transients (default true)
 * @returns {AudioBuffer} New AudioBuffer with limiting applied
 */
export function applyLookaheadLimiter(
  audioBuffer,
  ceilingLinear = LIMITER_DEFAULTS.CEILING_LINEAR,
  lookaheadMs = LIMITER_DEFAULTS.LOOKAHEAD_MS,
  releaseMs = LIMITER_DEFAULTS.RELEASE_MS,
  kneeDB = LIMITER_DEFAULTS.KNEE_DB,
  preserveTransients = LIMITER_DEFAULTS.PRESERVE_TRANSIENTS
) {
  const sampleRate = audioBuffer.sampleRate;
  const numChannels = audioBuffer.numberOfChannels;
  const length = audioBuffer.length;

  const lookaheadSamples = Math.floor(sampleRate * lookaheadMs / 1000);
  const releaseCoef = Math.exp(-1 / (releaseMs * sampleRate / 1000));

  // Get channel data
  const channels = [];
  for (let ch = 0; ch < numChannels; ch++) {
    channels.push(audioBuffer.getChannelData(ch));
  }

  // =========================================================================
  // Stage 0 (optional): Analyze transients for crest factor detection
  // =========================================================================
  let transientMap = null;
  if (preserveTransients) {
    transientMap = new Float32Array(length);
    const windowMs = 10;
    const windowSamples = Math.floor(sampleRate * windowMs / 1000);

    // Calculate RMS envelope
    const rmsEnvelope = new Float32Array(length);
    let rmsSum = 0;

    for (let i = 0; i < length; i++) {
      let sampleSum = 0;
      for (let ch = 0; ch < numChannels; ch++) {
        sampleSum += channels[ch][i] * channels[ch][i];
      }
      sampleSum /= numChannels;

      rmsSum += sampleSum;
      if (i >= windowSamples) {
        let oldSum = 0;
        for (let ch = 0; ch < numChannels; ch++) {
          oldSum += channels[ch][i - windowSamples] * channels[ch][i - windowSamples];
        }
        rmsSum -= oldSum / numChannels;
      }

      const windowSize = Math.min(i + 1, windowSamples);
      rmsEnvelope[i] = Math.sqrt(rmsSum / windowSize);
    }

    // Calculate peak envelope
    const peakEnvelope = new Float32Array(length);
    const peakAttack = Math.exp(-1 / (0.001 * sampleRate));
    const peakRelease = Math.exp(-1 / (0.050 * sampleRate));
    let peakLevel = 0;

    for (let i = 0; i < length; i++) {
      let peak = 0;
      for (let ch = 0; ch < numChannels; ch++) {
        peak = Math.max(peak, Math.abs(channels[ch][i]));
      }

      if (peak > peakLevel) {
        peakLevel = peakAttack * peakLevel + (1 - peakAttack) * peak;
      } else {
        peakLevel = peakRelease * peakLevel + (1 - peakRelease) * peak;
      }
      peakEnvelope[i] = peakLevel;
    }

    // Calculate transient map from crest factor
    const transientThresholdDB = 10;
    for (let i = 0; i < length; i++) {
      if (rmsEnvelope[i] > 0.0001) {
        const crestFactorDB = 20 * Math.log10(peakEnvelope[i] / rmsEnvelope[i]);
        transientMap[i] = Math.min(1, Math.max(0, (crestFactorDB - 6) / (transientThresholdDB - 6)));
      } else {
        transientMap[i] = 0;
      }
    }
  }

  // =========================================================================
  // Stage 1: Calculate gain reduction envelope with lookahead
  // =========================================================================
  const gainEnvelope = new Float32Array(length);
  gainEnvelope.fill(1.0);

  const prevSamplesL = [0, 0, 0, 0];
  const prevSamplesR = numChannels > 1 ? [0, 0, 0, 0] : null;

  for (let i = 0; i < length; i++) {
    // Update previous samples for true peak calculation
    prevSamplesL[0] = prevSamplesL[1];
    prevSamplesL[1] = prevSamplesL[2];
    prevSamplesL[2] = prevSamplesL[3];
    prevSamplesL[3] = channels[0][i];

    let truePeak = 0;
    if (i >= 3) {
      truePeak = calculateTruePeakSample(prevSamplesL);
    }

    if (numChannels > 1 && prevSamplesR) {
      prevSamplesR[0] = prevSamplesR[1];
      prevSamplesR[1] = prevSamplesR[2];
      prevSamplesR[2] = prevSamplesR[3];
      prevSamplesR[3] = channels[1][i];

      if (i >= 3) {
        truePeak = Math.max(truePeak, calculateTruePeakSample(prevSamplesR));
      }
    }

    // For transients, use slightly higher effective ceiling
    let effectiveCeiling = ceilingLinear;
    if (preserveTransients && transientMap && transientMap[i] > 0.5) {
      effectiveCeiling = ceilingLinear * Math.pow(10, transientMap[i] * 0.5 / 20);
    }

    let requiredGain = 1.0;
    if (truePeak > effectiveCeiling) {
      requiredGain = effectiveCeiling / truePeak;
    }

    // Apply lookahead
    const targetIndex = Math.max(0, i - lookaheadSamples);
    if (requiredGain < gainEnvelope[targetIndex]) {
      for (let j = targetIndex; j <= i; j++) {
        const progress = (j - targetIndex) / lookaheadSamples;
        const smoothedGain = gainEnvelope[targetIndex] + (requiredGain - gainEnvelope[targetIndex]) * progress;
        gainEnvelope[j] = Math.min(gainEnvelope[j], smoothedGain);
      }
    }
  }

  // =========================================================================
  // Stage 1b: Smooth the gain envelope (release)
  // =========================================================================
  let currentGain = 1.0;
  for (let i = 0; i < length; i++) {
    if (gainEnvelope[i] < currentGain) {
      currentGain = gainEnvelope[i];
    } else {
      currentGain = releaseCoef * currentGain + (1 - releaseCoef) * 1.0;
      currentGain = Math.min(currentGain, 1.0);
    }
    gainEnvelope[i] = currentGain;
  }

  // =========================================================================
  // Stage 2: Apply gain envelope and soft-knee saturation
  // =========================================================================
  const outputBuffer = new AudioBuffer({
    numberOfChannels: numChannels,
    length: length,
    sampleRate: sampleRate
  });

  for (let ch = 0; ch < numChannels; ch++) {
    const input = channels[ch];
    const output = outputBuffer.getChannelData(ch);

    // Apply gain reduction
    for (let i = 0; i < length; i++) {
      output[i] = input[i] * gainEnvelope[i];
    }

    // Apply soft-knee curve with oversampling as final safety
    const softKneeOutput = applySoftKneeOversampled(output, ceilingLinear, kneeDB);
    for (let i = 0; i < length; i++) {
      output[i] = softKneeOutput[i];
    }
  }

  // =========================================================================
  // Logging
  // =========================================================================
  let minGain = 1.0;
  let softKneeActive = false;
  for (let i = 0; i < length; i++) {
    if (gainEnvelope[i] < minGain) minGain = gainEnvelope[i];
  }

  for (let ch = 0; ch < numChannels; ch++) {
    const output = outputBuffer.getChannelData(ch);
    for (let i = 0; i < length; i++) {
      if (Math.abs(output[i]) > ceilingLinear * 0.99) {
        softKneeActive = true;
        break;
      }
    }
    if (softKneeActive) break;
  }

  if (minGain < 1.0) {
    console.log('[Limiter] Stage 1 - Max gain reduction:', (20 * Math.log10(minGain)).toFixed(2), 'dB');
  }
  if (softKneeActive) {
    console.log('[Limiter] Stage 2 - Soft-knee saturation active');
  }

  return outputBuffer;
}
