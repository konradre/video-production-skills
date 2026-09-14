import { EXCITER_DEFAULTS } from './constants.js';
import { interpolateCatmullRom } from './utils.js';

/**
 * Exciter defaults
 */
export { EXCITER_DEFAULTS }; // Re-export for convenience

/**
 * Calculate 2nd order Butterworth high-pass filter coefficients
 * @param {number} sampleRate - Sample rate
 * @param {number} frequency - Cutoff frequency
 * @returns {Object} Filter coefficients
 */
function calcHighPassCoeffs(sampleRate, frequency) {
  const omega = Math.tan(Math.PI * frequency / sampleRate);
  const omega2 = omega * omega;
  const sqrt2 = Math.SQRT2;
  const n = 1 / (1 + sqrt2 * omega + omega2);

  return {
    b0: n,
    b1: -2 * n,
    b2: n,
    a1: 2 * (omega2 - 1) * n,
    a2: (1 - sqrt2 * omega + omega2) * n
  };
}

/**
 * Apply 2nd order high-pass filter to samples
 * @param {Float32Array} samples - Input samples
 * @param {Object} coeffs - Filter coefficients
 * @returns {Float32Array} Filtered samples
 */
function applyHighPass(samples, coeffs) {
  const output = new Float32Array(samples.length);
  const { b0, b1, b2, a1, a2 } = coeffs;

  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;

  for (let i = 0; i < samples.length; i++) {
    const x0 = samples[i];
    const y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;

    x2 = x1;
    x1 = x0;
    y2 = y1;
    y1 = Math.abs(y0) < 1e-25 ? 0 : y0; // Denormal prevention

    output[i] = y1;
  }

  return output;
}

/**
 * Exciter class
 */
export class Exciter {
  /**
   * Create an exciter
   * @param {Object} options - Configuration options
   */
  constructor(options = {}) {
    this.hpfFreq = options.hpfFreq ?? EXCITER_DEFAULTS.hpfFreq;
    this.hpfSlope = options.hpfSlope ?? EXCITER_DEFAULTS.hpfSlope;
    this.drive = options.drive ?? EXCITER_DEFAULTS.drive;
    this.bias = options.bias ?? EXCITER_DEFAULTS.bias;
    this.mix = options.mix ?? EXCITER_DEFAULTS.mix;
    this.oversample = options.oversample ?? true; // Default to true for quality
  }

  /**
   * Process audio buffer with exciter
   * @param {AudioBuffer} buffer - Input audio buffer
   * @param {Function} onProgress - Progress callback (0-1)
   * @returns {AudioBuffer} Processed audio buffer
   */
  process(buffer, onProgress = null) {
    const output = new AudioBuffer({
      numberOfChannels: buffer.numberOfChannels,
      length: buffer.length,
      sampleRate: buffer.sampleRate
    });

    const hpfCoeffs = calcHighPassCoeffs(buffer.sampleRate, this.hpfFreq);
    const mixRatio = this.mix / 100;
    const drive = this.drive;
    const bias = this.bias;

    for (let ch = 0; ch < buffer.numberOfChannels; ch++) {
      const input = buffer.getChannelData(ch);
      const out = output.getChannelData(ch);

      // Apply high-pass filter to isolate highs
      let filtered = applyHighPass(input, hpfCoeffs);

      // Apply second pass for 12dB/oct (LR2 equivalent)
      if (this.hpfSlope === 12) {
        filtered = applyHighPass(filtered, hpfCoeffs);
      }

      if (onProgress) onProgress((ch + 0.5) / buffer.numberOfChannels);

      // Apply saturation and parallel mix
      if (this.oversample) {
        // 2x Oversampling
        const prevSamples = [0, 0, 0, 0];

        for (let i = 0; i < input.length; i++) {
          const dry = input[i];
          const x = filtered[i];

          // Shift history
          prevSamples[0] = prevSamples[1];
          prevSamples[1] = prevSamples[2];
          prevSamples[2] = prevSamples[3];
          prevSamples[3] = x;

          // Process original sample (t=0, at y2 position in history wait... y2 is current input?)
          // In loop i: prevSamples[3] is current x[i].
          // Catmull needs y0, y1, y2, y3. 
          // At step i, we want to produce output for step i.
          // BUT oversampling usually introduces latency.
          // Let's assume standard behavior:
          // y1 is current sample, we interpolate between y1 and y2? 
          // Let's stick to the limiter implementation style: history holds previous inputs.

          // Actually, precise 2x oversampling:
          // 1. Upsample: Insert zero or hold? Catmull-Rom interpolates the mid-point.
          //    We need output at t and t+0.5.
          //    If sample matches "y2" in the history buffer context...

          // Let's use a simpler history logic for clarity:
          // We have x[i]. We need x[i-0.5].
          // interpolateCatmullRom(y0, y1, y2, y3, t)
          // y2 is current sample. y1 is previous. t=0.5 gives midway between y1 and y2.

          const y0 = prevSamples[0];
          const y1 = prevSamples[1];
          const y2 = prevSamples[2];
          const y3 = prevSamples[3];

          // Sample at regular time
          const wet1 = Math.tanh(y2 * drive + bias);

          // Sample at +0.5 offset (midway between y2 and y3? No, between y1 and y2 is past?)
          // Doing causal interpolation (between y2 and y3) requires lookahead (y3).
          // With current buffer [y0, y1, y2, y3], y3 is "current", y2 is "previous".
          // So we can interpolate between y2 and y3 (t=0.5).

          // But 'filtered' array is fully available! We don't need a rolling buffer, we can just look ahead.
          // It's much faster to just index the array.
        }

        // Faster array-access approach
        for (let i = 0; i < input.length; i++) {
          const dry = input[i];

          // Get context samples from 'filtered' array
          const p0 = filtered[i - 2] || 0;
          const p1 = filtered[i - 1] || 0;
          const p2 = filtered[i] || 0;
          const p3 = filtered[i + 1] || 0;

          // Original sample
          const s1 = p2;
          // Half-sample (oversampled)
          const s2 = interpolateCatmullRom(p0, p1, p2, p3, 0.5); // Interpolates between p1 and p2

          // Wait, interpolateCatmullRom(y0, y1, y2, y3, t) in my utils means t is between y1 and y2.
          // If I pass p0, p1, p2, p3, it interpolates between p1 and p2.
          // p2 is current sample i. p1 is i-1.
          // So s2 is sample at i - 0.5.
          // We want i and i + 0.5?

          // Let's define:
          // Sample A: at i (using p2 directly is cleaner than interp? No, interp at t=1 is y2)
          // Sample B: at i + 0.5 (between p2 and p3).
          // To get between p2 and p3, I need: p1, p2, p3, p4.
          // interpolate(p1, p2, p3, p4, 0.5) -> value at i + 0.5

          const p4 = filtered[i + 2] || 0;

          // Process original
          const wetA = Math.tanh(p2 * drive + bias);

          // Process interpolated (i + 0.5)
          const sB = interpolateCatmullRom(p1, p2, p3, p4, 0.5);
          const wetB = Math.tanh(sB * drive + bias);

          // Downsample (Simple Average LPF)
          // (wetA + wetB) * 0.5
          const wet = (wetA + wetB) * 0.5;

          out[i] = dry + wet * mixRatio;
        }

      } else {
        // Original non-oversampled loop
        for (let i = 0; i < input.length; i++) {
          const dry = input[i];
          const wet = Math.tanh(filtered[i] * drive + bias);
          // Parallel addition: dry + wet * mix (not blend)
          out[i] = dry + wet * mixRatio;
        }
      }

      if (onProgress) onProgress((ch + 1) / buffer.numberOfChannels);
    }

    return output;
  }
}

/**
 * Apply exciter with default settings (Add Air replacement)
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Processed audio buffer
 */
export function applyExciter(buffer, onProgress = null) {
  const exciter = new Exciter();
  return exciter.process(buffer, onProgress);
}

/**
 * Apply exciter with custom settings
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {Object} options - Custom settings
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Processed audio buffer
 */
export function applyExciterWithOptions(buffer, options, onProgress = null) {
  const exciter = new Exciter(options);
  return exciter.process(buffer, onProgress);
}
