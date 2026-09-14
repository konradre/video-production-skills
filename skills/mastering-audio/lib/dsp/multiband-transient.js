/**
 * Multiband Transient Shaper
 * Applies transient shaping per frequency band for punch and snap
 *
 * Uses Linkwitz-Riley crossover filters and envelope followers
 * to detect and shape transients independently per band.
 */

/**
 * Apply multiband transient shaping to an AudioBuffer
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {Function} onProgress - Progress callback (0-1)
 * @returns {AudioBuffer} - Processed audio buffer
 */
export function applyMultibandTransient(buffer, onProgress = () => { }) {
  const sampleRate = buffer.sampleRate;
  const numChannels = buffer.numberOfChannels;
  const length = buffer.length;

  // Crossover frequencies
  const f1 = 200;   // Low-Mid crossover
  const f2 = 4000;  // Mid-High crossover

  // Band settings from user specification (Updated for Suno Optimization)
  const bands = {
    low: {
      fastAttack: 0.005,    // 5ms
      fastRelease: 0.050,   // 50ms
      slowAttack: 0.025,    // 25ms
      slowRelease: 0.250,   // 250ms
      transientGain: 2,     // +2dB (Reduced from +4dB to prevent limiter slamming)
      sustainGain: -1,      // -1dB (Gentler cleanup)
      smoothing: 0.020      // 20ms
    },
    mid: {
      fastAttack: 0.001,    // 1ms (Super fast to catch smeared transients)
      fastRelease: 0.040,   // 40ms
      slowAttack: 0.020,    // 20ms
      slowRelease: 0.200,   // 200ms
      transientGain: 6,     // +6dB (Aggressive snap for snare/vocals)
      sustainGain: 0,       // 0dB
      smoothing: 0.020      // 20ms
    },
    high: {
      fastAttack: 0.003,    // 3ms
      fastRelease: 0.030,   // 30ms
      slowAttack: 0.015,    // 15ms
      slowRelease: 0.150,   // 150ms
      transientGain: 2,     // +2dB (Add some click)
      sustainGain: 0,       // 0dB
      smoothing: 0.020      // 20ms
    }
  };

  // Create output buffer (using AudioBuffer directly, works in both main thread and workers)
  const outputBuffer = new AudioBuffer({
    numberOfChannels: numChannels,
    length: length,
    sampleRate: sampleRate
  });

  // Process each channel
  for (let ch = 0; ch < numChannels; ch++) {
    const input = buffer.getChannelData(ch);
    const output = outputBuffer.getChannelData(ch);

    // Split into bands using Linkwitz-Riley filters
    const lowBand = new Float32Array(length);
    const midBand = new Float32Array(length);
    const highBand = new Float32Array(length);

    // Apply crossover filters
    splitBands(input, lowBand, midBand, highBand, f1, f2, sampleRate);

    // Process each band with transient shaping
    const lowProcessed = processTransients(lowBand, bands.low, sampleRate);
    const midProcessed = processTransients(midBand, bands.mid, sampleRate);
    const highProcessed = processTransients(highBand, bands.high, sampleRate);

    // Sum bands back together
    for (let i = 0; i < length; i++) {
      output[i] = lowProcessed[i] + midProcessed[i] + highProcessed[i];
    }

    onProgress((ch + 1) / numChannels);
  }

  return outputBuffer;
}

/**
 * Split audio into 3 bands using Linkwitz-Riley crossover
 */
function splitBands(input, low, mid, high, f1, f2, sampleRate) {
  const length = input.length;

  // Linkwitz-Riley is two cascaded Butterworth filters
  // We'll use biquad lowpass/highpass filters cascaded

  // First crossover at f1 (200Hz)
  const lp1a = createBiquadCoeffs('lowpass', f1, sampleRate, 0.707);
  const lp1b = createBiquadCoeffs('lowpass', f1, sampleRate, 0.707);
  const hp1a = createBiquadCoeffs('highpass', f1, sampleRate, 0.707);
  const hp1b = createBiquadCoeffs('highpass', f1, sampleRate, 0.707);

  // Second crossover at f2 (4000Hz)
  const lp2a = createBiquadCoeffs('lowpass', f2, sampleRate, 0.707);
  const lp2b = createBiquadCoeffs('lowpass', f2, sampleRate, 0.707);
  const hp2a = createBiquadCoeffs('highpass', f2, sampleRate, 0.707);
  const hp2b = createBiquadCoeffs('highpass', f2, sampleRate, 0.707);

  // Temp buffers
  const temp1 = new Float32Array(length);
  const temp2 = new Float32Array(length);
  const midLow = new Float32Array(length);

  // Low band: cascaded lowpass at f1
  applyBiquad(input, temp1, lp1a);
  applyBiquad(temp1, low, lp1b);

  // High-passed at f1
  applyBiquad(input, temp1, hp1a);
  applyBiquad(temp1, temp2, hp1b);

  // Mid band: highpass at f1, then lowpass at f2
  applyBiquad(temp2, temp1, lp2a);
  applyBiquad(temp1, mid, lp2b);

  // High band: highpass at f2
  applyBiquad(temp2, temp1, hp2a);
  applyBiquad(temp1, high, hp2b);
}

/**
 * Create biquad filter coefficients
 */
function createBiquadCoeffs(type, freq, sampleRate, Q) {
  const w0 = 2 * Math.PI * freq / sampleRate;
  const cosw0 = Math.cos(w0);
  const sinw0 = Math.sin(w0);
  const alpha = sinw0 / (2 * Q);

  let b0, b1, b2, a0, a1, a2;

  if (type === 'lowpass') {
    b0 = (1 - cosw0) / 2;
    b1 = 1 - cosw0;
    b2 = (1 - cosw0) / 2;
    a0 = 1 + alpha;
    a1 = -2 * cosw0;
    a2 = 1 - alpha;
  } else { // highpass
    b0 = (1 + cosw0) / 2;
    b1 = -(1 + cosw0);
    b2 = (1 + cosw0) / 2;
    a0 = 1 + alpha;
    a1 = -2 * cosw0;
    a2 = 1 - alpha;
  }

  return {
    b0: b0 / a0,
    b1: b1 / a0,
    b2: b2 / a0,
    a1: a1 / a0,
    a2: a2 / a0,
    x1: 0, x2: 0, y1: 0, y2: 0
  };
}

/**
 * Apply biquad filter to signal
 */
function applyBiquad(input, output, coeffs) {
  const { b0, b1, b2, a1, a2 } = coeffs;
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;

  for (let i = 0; i < input.length; i++) {
    const x0 = input[i];
    const y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;

    x2 = x1;
    x1 = x0;
    y2 = y1;
    y1 = y0;

    output[i] = y0;
  }
}

/**
 * Process transients for a single band
 */
function processTransients(band, settings, sampleRate) {
  const length = band.length;
  const output = new Float32Array(length);

  // Convert time constants to coefficients
  const fastAttackCoeff = Math.exp(-1 / (settings.fastAttack * sampleRate));
  const fastReleaseCoeff = Math.exp(-1 / (settings.fastRelease * sampleRate));
  const slowAttackCoeff = Math.exp(-1 / (settings.slowAttack * sampleRate));
  const slowReleaseCoeff = Math.exp(-1 / (settings.slowRelease * sampleRate));
  const smoothingCoeff = Math.exp(-1 / (settings.smoothing * sampleRate));

  // Convert dB gains to linear
  const transientGainLinear = Math.pow(10, settings.transientGain / 20);
  const sustainGainLinear = Math.pow(10, settings.sustainGain / 20);

  // Envelope followers
  let fastEnv = 0;
  let slowEnv = 0;
  let smoothedGain = 1;

  for (let i = 0; i < length; i++) {
    const sample = band[i];
    const absVal = Math.abs(sample);

    // Fast envelope follower
    if (absVal > fastEnv) {
      fastEnv = fastAttackCoeff * fastEnv + (1 - fastAttackCoeff) * absVal;
    } else {
      fastEnv = fastReleaseCoeff * fastEnv + (1 - fastReleaseCoeff) * absVal;
    }

    // Slow envelope follower
    if (absVal > slowEnv) {
      slowEnv = slowAttackCoeff * slowEnv + (1 - slowAttackCoeff) * absVal;
    } else {
      slowEnv = slowReleaseCoeff * slowEnv + (1 - slowReleaseCoeff) * absVal;
    }

    // Transient detection: difference between fast and slow envelopes
    // Positive = transient, Negative = sustain
    const diff = fastEnv - slowEnv;

    // Calculate gain based on transient/sustain
    let targetGain = 1;
    if (diff > 0) {
      // Transient: apply transient gain scaled by detection strength
      // Normalize by slow envelope to get relative difference
      // When slowEnv is very small, clamp the fallback to avoid extreme values
      const transientStrength = slowEnv > 0.0001
        ? Math.min(diff / slowEnv, 1)
        : Math.min(diff / 0.0001, 1);
      targetGain = 1 + (transientGainLinear - 1) * transientStrength;
    } else {
      // Sustain: apply sustain gain scaled by detection strength
      // Same robust handling for small envelope values
      const sustainStrength = slowEnv > 0.0001
        ? Math.min(-diff / slowEnv, 1)
        : Math.min(-diff / 0.0001, 1);
      targetGain = 1 + (sustainGainLinear - 1) * sustainStrength;
    }

    // Smooth the gain to avoid artifacts
    smoothedGain = smoothingCoeff * smoothedGain + (1 - smoothingCoeff) * targetGain;

    // Apply gain
    output[i] = sample * smoothedGain;
  }

  return output;
}

export default applyMultibandTransient;
