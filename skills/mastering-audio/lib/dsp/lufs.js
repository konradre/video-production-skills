/**
 * LUFS Loudness Measurement Module
 * ITU-R BS.1770-4 compliant loudness measurement
 */

import { K_WEIGHTING, LUFS_CONSTANTS } from './constants.js';
import { applyBiquadFilter, calcHighShelfCoeffs, calcHighPassCoeffs } from './utils.js';

/**
 * Measure integrated loudness (LUFS) of an AudioBuffer
 * Based on ITU-R BS.1770-4
 *
 * @param {AudioBuffer} audioBuffer - Input audio buffer
 * @param {number} fallbackLufs - Value to return if audio too short (default -14)
 * @returns {number} Integrated loudness in LUFS
 */
export function measureLUFS(audioBuffer, fallbackLufs = -14) {
  const sampleRate = audioBuffer.sampleRate;
  const numChannels = audioBuffer.numberOfChannels;
  const length = audioBuffer.length;

  // Minimum block size required for LUFS measurement
  if (audioBuffer.duration < LUFS_CONSTANTS.BLOCK_SIZE_SEC) {
    console.warn(`[LUFS] Audio too short for reliable measurement (< ${LUFS_CONSTANTS.BLOCK_SIZE_SEC * 1000}ms)`);
    return fallbackLufs;
  }

  const channels = [];
  for (let ch = 0; ch < numChannels; ch++) {
    channels.push(audioBuffer.getChannelData(ch));
  }

  // Apply K-weighting filters (ITU-R BS.1770-4)
  const highShelfCoeffs = calcHighShelfCoeffs(
    sampleRate,
    K_WEIGHTING.HIGH_SHELF_FREQ,
    K_WEIGHTING.HIGH_SHELF_GAIN,
    K_WEIGHTING.HIGH_SHELF_Q
  );
  const highPassCoeffs = calcHighPassCoeffs(
    sampleRate,
    K_WEIGHTING.HIGH_PASS_FREQ,
    K_WEIGHTING.HIGH_PASS_Q
  );

  const filteredChannels = channels.map(ch => {
    let filtered = applyBiquadFilter(ch, highShelfCoeffs);
    filtered = applyBiquadFilter(filtered, highPassCoeffs);
    return filtered;
  });

  // Calculate mean square per block with overlap (ITU-R BS.1770-4)
  const blockSize = Math.floor(sampleRate * LUFS_CONSTANTS.BLOCK_SIZE_SEC);
  const hopSize = Math.floor(sampleRate * LUFS_CONSTANTS.BLOCK_SIZE_SEC * (1 - LUFS_CONSTANTS.BLOCK_OVERLAP));
  const blocks = [];

  for (let start = 0; start + blockSize <= length; start += hopSize) {
    let sumSquares = 0;
    for (let ch = 0; ch < numChannels; ch++) {
      const channelData = filteredChannels[ch];
      for (let i = start; i < start + blockSize; i++) {
        sumSquares += channelData[i] * channelData[i];
      }
    }
    blocks.push(sumSquares / (blockSize * numChannels));
  }

  if (blocks.length === 0) return -Infinity;

  // Absolute threshold gating (blocks below -70 LUFS are ignored)
  let gatedBlocks = blocks.filter(ms => ms > LUFS_CONSTANTS.ABSOLUTE_GATE_LINEAR);
  if (gatedBlocks.length === 0) return -Infinity;

  // Relative threshold gating (-10 dB below ungated mean)
  const ungatedMean = gatedBlocks.reduce((a, b) => a + b, 0) / gatedBlocks.length;
  gatedBlocks = gatedBlocks.filter(ms => ms > ungatedMean * LUFS_CONSTANTS.RELATIVE_GATE_OFFSET);
  if (gatedBlocks.length === 0) return -Infinity;

  // Calculate integrated loudness
  const gatedMean = gatedBlocks.reduce((a, b) => a + b, 0) / gatedBlocks.length;
  return LUFS_CONSTANTS.LOUDNESS_OFFSET + 10 * Math.log10(gatedMean);
}

/**
 * Measure short-term loudness (3 second window)
 *
 * @param {AudioBuffer} audioBuffer - Input audio buffer
 * @param {number} position - Position in seconds
 * @returns {number} Short-term loudness in LUFS
 */
export function measureShortTermLUFS(audioBuffer, position = 0) {
  const sampleRate = audioBuffer.sampleRate;
  const windowMs = 3000; // 3 second window
  const windowSamples = Math.floor(sampleRate * windowMs / 1000);
  const startSample = Math.floor(position * sampleRate);
  const endSample = Math.min(startSample + windowSamples, audioBuffer.length);

  if (endSample - startSample < windowSamples * 0.5) {
    return -Infinity;
  }

  // Create a temporary buffer with the window
  const numChannels = audioBuffer.numberOfChannels;
  const tempBuffer = new AudioBuffer({
    numberOfChannels: numChannels,
    length: endSample - startSample,
    sampleRate: sampleRate
  });

  for (let ch = 0; ch < numChannels; ch++) {
    const source = audioBuffer.getChannelData(ch);
    const dest = tempBuffer.getChannelData(ch);
    for (let i = 0; i < dest.length; i++) {
      dest[i] = source[startSample + i];
    }
  }

  return measureLUFS(tempBuffer);
}

/**
 * Measure momentary loudness (400ms window)
 *
 * @param {AudioBuffer} audioBuffer - Input audio buffer
 * @param {number} position - Position in seconds
 * @returns {number} Momentary loudness in LUFS
 */
export function measureMomentaryLUFS(audioBuffer, position = 0) {
  const sampleRate = audioBuffer.sampleRate;
  const windowMs = 400; // 400ms window
  const windowSamples = Math.floor(sampleRate * windowMs / 1000);
  const startSample = Math.floor(position * sampleRate);
  const endSample = Math.min(startSample + windowSamples, audioBuffer.length);

  if (endSample - startSample < windowSamples * 0.5) {
    return -Infinity;
  }

  const numChannels = audioBuffer.numberOfChannels;
  const channels = [];
  for (let ch = 0; ch < numChannels; ch++) {
    channels.push(audioBuffer.getChannelData(ch).subarray(startSample, endSample));
  }

  // Apply K-weighting
  const highShelfCoeffs = calcHighShelfCoeffs(
    sampleRate,
    K_WEIGHTING.HIGH_SHELF_FREQ,
    K_WEIGHTING.HIGH_SHELF_GAIN,
    K_WEIGHTING.HIGH_SHELF_Q
  );
  const highPassCoeffs = calcHighPassCoeffs(
    sampleRate,
    K_WEIGHTING.HIGH_PASS_FREQ,
    K_WEIGHTING.HIGH_PASS_Q
  );

  let sumSquares = 0;
  for (let ch = 0; ch < numChannels; ch++) {
    let filtered = applyBiquadFilter(channels[ch], highShelfCoeffs);
    filtered = applyBiquadFilter(filtered, highPassCoeffs);
    for (let i = 0; i < filtered.length; i++) {
      sumSquares += filtered[i] * filtered[i];
    }
  }

  const meanSquare = sumSquares / ((endSample - startSample) * numChannels);
  if (meanSquare <= 0) return -Infinity;

  return LUFS_CONSTANTS.LOUDNESS_OFFSET + 10 * Math.log10(meanSquare);
}
