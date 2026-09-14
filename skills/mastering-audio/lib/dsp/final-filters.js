/**
 * Final Filters Module
 * HPF/LPF cleanup filters for the end of the chain
 */

/**
 * Apply biquad filter to a channel in-place
 * @param {Float32Array} data - Channel data
 * @param {'highpass'|'lowpass'} type - Filter type
 * @param {number} freq - Frequency in Hz
 * @param {number} sampleRate - Sample rate in Hz
 * @param {number} Q - Q factor
 */
export function applyBiquadToChannel(data, type, freq, sampleRate, Q) {
  const w0 = 2 * Math.PI * freq / sampleRate;
  const cosw0 = Math.cos(w0);
  const sinw0 = Math.sin(w0);
  const alpha = sinw0 / (2 * Q);

  let b0, b1, b2, a0, a1, a2;

  if (type === 'highpass') {
    b0 = (1 + cosw0) / 2;
    b1 = -(1 + cosw0);
    b2 = (1 + cosw0) / 2;
    a0 = 1 + alpha;
    a1 = -2 * cosw0;
    a2 = 1 - alpha;
  } else {
    b0 = (1 - cosw0) / 2;
    b1 = 1 - cosw0;
    b2 = (1 - cosw0) / 2;
    a0 = 1 + alpha;
    a1 = -2 * cosw0;
    a2 = 1 - alpha;
  }

  // Normalize coefficients
  const nb0 = b0 / a0;
  const nb1 = b1 / a0;
  const nb2 = b2 / a0;
  const na1 = a1 / a0;
  const na2 = a2 / a0;

  // Direct Form I
  let x1 = 0;
  let x2 = 0;
  let y1 = 0;
  let y2 = 0;

  for (let i = 0; i < data.length; i++) {
    const x0 = data[i];
    const y0 = nb0 * x0 + nb1 * x1 + nb2 * x2 - na1 * y1 - na2 * y2;
    x2 = x1;
    x1 = x0;
    y2 = y1;
    y1 = y0;
    data[i] = y0;
  }
}

/**
 * Apply 1-pole lowpass filter (6dB/oct) in-place
 * @param {Float32Array} data - Channel data
 * @param {number} freq - Cutoff frequency in Hz
 * @param {number} sampleRate - Sample rate in Hz
 */
export function applyOnePoleLP(data, freq, sampleRate) {
  const rc = 1 / (2 * Math.PI * freq);
  const dt = 1 / sampleRate;
  const alpha = dt / (rc + dt);

  let y = data[0] || 0;
  for (let i = 0; i < data.length; i++) {
    y = y + alpha * (data[i] - y);
    data[i] = y;
  }
}

/**
 * Apply final cleanup filters.
 *
 * Defaults:
 * - HPF 30Hz (12dB/oct): one biquad highpass
 * - LPF 18kHz (6dB/oct): one-pole lowpass
 *
 * @param {AudioBuffer} buffer - Input audio buffer
 * @param {Object} options
 * @param {boolean} [options.highpass=true] - Enable HPF
 * @param {boolean} [options.lowpass=true] - Enable LPF
 * @param {number} [options.highpassFreq=30] - HPF frequency in Hz
 * @param {number} [options.lowpassFreq=18000] - LPF frequency in Hz
 * @param {number} [options.highpassQ=0.707] - HPF Q factor
 * @returns {AudioBuffer} Filtered buffer
 */
export function applyFinalFilters(buffer, options = {}) {
  const {
    highpass = true,
    lowpass = true,
    highpassFreq = 30,
    lowpassFreq = 18000,
    highpassQ = 0.707
  } = options;

  const sampleRate = buffer.sampleRate;
  const numChannels = buffer.numberOfChannels;
  const length = buffer.length;

  const outputBuffer = new AudioBuffer({
    numberOfChannels: numChannels,
    length,
    sampleRate
  });

  for (let ch = 0; ch < numChannels; ch++) {
    const input = buffer.getChannelData(ch);
    const output = outputBuffer.getChannelData(ch);

    output.set(input);

    if (highpass) {
      applyBiquadToChannel(output, 'highpass', highpassFreq, sampleRate, highpassQ);
    }

    if (lowpass) {
      applyOnePoleLP(output, lowpassFreq, sampleRate);
    }
  }

  return outputBuffer;
}

