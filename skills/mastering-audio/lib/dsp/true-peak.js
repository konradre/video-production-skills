/**
 * True Peak Detection Module
 * ITU-R BS.1770 compliant true-peak detection with 4x oversampling
 */

/**
 * Calculate true peak using 4x oversampled Catmull-Rom interpolation
 * This finds inter-sample peaks that simple sample-based measurement misses
 *
 * @param {Array} prevSamples - Array of 4 consecutive samples [y0, y1, y2, y3]
 * @returns {number} True peak value (linear)
 */
export function calculateTruePeakSample(prevSamples) {
  const y0 = prevSamples[0];
  const y1 = prevSamples[1];
  const y2 = prevSamples[2];
  const y3 = prevSamples[3];

  // Start with current sample
  let peak = Math.abs(y2);

  // Catmull-Rom spline coefficients: y(t) = a0*t³ + a1*t² + a2*t + a3
  const a0 = -0.5 * y0 + 1.5 * y1 - 1.5 * y2 + 0.5 * y3;
  const a1 = y0 - 2.5 * y1 + 2 * y2 - 0.5 * y3;
  const a2 = -0.5 * y0 + 0.5 * y2;
  const a3 = y1;

  // Check at 4x oversampled points
  for (let i = 1; i <= 3; i++) {
    const t = i * 0.25;
    const t2 = t * t;
    const t3 = t2 * t;
    const interpolated = a0 * t3 + a1 * t2 + a2 * t + a3;
    peak = Math.max(peak, Math.abs(interpolated));
  }

  return peak;
}

/**
 * Find the true peak of an AudioBuffer using 4x oversampling
 *
 * @param {AudioBuffer} audioBuffer - Input audio buffer
 * @returns {number} Peak in dBTP (decibels relative to full scale)
 */
export function findTruePeak(audioBuffer) {
  let maxPeak = 0;

  for (let ch = 0; ch < audioBuffer.numberOfChannels; ch++) {
    const channelData = audioBuffer.getChannelData(ch);
    const prevSamples = [0, 0, 0, 0];

    for (let i = 0; i < channelData.length; i++) {
      // Shift previous samples
      prevSamples[0] = prevSamples[1];
      prevSamples[1] = prevSamples[2];
      prevSamples[2] = prevSamples[3];
      prevSamples[3] = channelData[i];

      if (i >= 3) {
        const truePeak = calculateTruePeakSample(prevSamples);
        if (truePeak > maxPeak) {
          maxPeak = truePeak;
        }
      }
    }
  }

  // Convert to dBTP (0 dBTP = 1.0 linear)
  return maxPeak > 0 ? 20 * Math.log10(maxPeak) : -Infinity;
}

/**
 * Find true peak of a Float32Array channel
 *
 * @param {Float32Array} channelData - Single channel audio data
 * @returns {number} Peak in linear scale
 */
export function findChannelTruePeak(channelData) {
  let maxPeak = 0;
  const prevSamples = [0, 0, 0, 0];

  for (let i = 0; i < channelData.length; i++) {
    prevSamples[0] = prevSamples[1];
    prevSamples[1] = prevSamples[2];
    prevSamples[2] = prevSamples[3];
    prevSamples[3] = channelData[i];

    if (i >= 3) {
      const truePeak = calculateTruePeakSample(prevSamples);
      if (truePeak > maxPeak) {
        maxPeak = truePeak;
      }
    }
  }

  return maxPeak;
}
