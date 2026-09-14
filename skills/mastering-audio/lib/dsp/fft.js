/**
 * FFT Module
 * Wrapper around fft.js with utility functions for audio processing
 */

import FFT from 'fft.js';
import { createHannWindow } from './utils.js';

/**
 * FFT Processor class for audio spectral processing
 * Provides overlap-add processing with windowing
 */
export class FFTProcessor {
  /**
   * Create an FFT processor
   * @param {number} size - FFT size (must be power of 2)
   * @param {number} hopSize - Hop size for overlap-add (default: size/2)
   */
  constructor(size = 2048, hopSize = null) {
    if ((size & (size - 1)) !== 0) {
      throw new Error('FFT size must be power of 2');
    }

    this.size = size;
    this.hopSize = hopSize || size / 2;
    this.fft = new FFT(size);
    this.window = createHannWindow(size);

    // Pre-allocate buffers
    this.inputBuffer = new Float32Array(size);
    this.outputBuffer = new Float32Array(size);
    this.spectrum = this.fft.createComplexArray();
    this.inverseBuffer = this.fft.createComplexArray();
  }

  /**
   * Perform forward FFT on a windowed block
   * @param {Float32Array} input - Input samples (length = fftSize)
   * @returns {Float32Array} Complex spectrum [re0, im0, re1, im1, ...]
   */
  forward(input) {
    // Apply window
    for (let i = 0; i < this.size; i++) {
      this.inputBuffer[i] = (input[i] || 0) * this.window[i];
    }

    // Real to complex FFT
    this.fft.realTransform(this.spectrum, this.inputBuffer);
    this.fft.completeSpectrum(this.spectrum);

    return this.spectrum;
  }

  /**
   * Perform inverse FFT
   * @param {Float32Array} spectrum - Complex spectrum
   * @returns {Float32Array} Time domain output
   */
  inverse(spectrum) {
    this.fft.inverseTransform(this.inverseBuffer, spectrum);

    // Extract real part and apply synthesis window
    for (let i = 0; i < this.size; i++) {
      this.outputBuffer[i] = this.inverseBuffer[i * 2] * this.window[i];
    }

    return this.outputBuffer;
  }

  /**
   * Get magnitude spectrum in dB
   * @param {Float32Array} spectrum - Complex spectrum
   * @returns {Float32Array} Magnitude in dB (length = fftSize/2)
   */
  getMagnitudeDB(spectrum) {
    const numBins = this.size / 2;
    const magnitude = new Float32Array(numBins);

    for (let i = 0; i < numBins; i++) {
      const re = spectrum[i * 2];
      const im = spectrum[i * 2 + 1];
      const mag = Math.sqrt(re * re + im * im);
      magnitude[i] = mag > 0 ? 20 * Math.log10(mag) : -120;
    }

    return magnitude;
  }

  /**
   * Get phase spectrum
   * @param {Float32Array} spectrum - Complex spectrum
   * @returns {Float32Array} Phase in radians (length = fftSize/2)
   */
  getPhase(spectrum) {
    const numBins = this.size / 2;
    const phase = new Float32Array(numBins);

    for (let i = 0; i < numBins; i++) {
      const re = spectrum[i * 2];
      const im = spectrum[i * 2 + 1];
      phase[i] = Math.atan2(im, re);
    }

    return phase;
  }

  /**
   * Set magnitude while preserving phase
   * @param {Float32Array} spectrum - Complex spectrum (modified in place)
   * @param {Float32Array} magnitude - New magnitude values (linear, not dB)
   */
  setMagnitude(spectrum, magnitude) {
    const numBins = this.size / 2;

    for (let i = 0; i < numBins; i++) {
      const re = spectrum[i * 2];
      const im = spectrum[i * 2 + 1];
      const currentMag = Math.sqrt(re * re + im * im);

      if (currentMag > 1e-10) {
        const scale = magnitude[i] / currentMag;
        spectrum[i * 2] = re * scale;
        spectrum[i * 2 + 1] = im * scale;
      }
    }
  }

  /**
   * Get frequency for a given bin index
   * @param {number} binIndex - FFT bin index
   * @param {number} sampleRate - Sample rate in Hz
   * @returns {number} Frequency in Hz
   */
  binToFrequency(binIndex, sampleRate) {
    return binIndex * sampleRate / this.size;
  }

  /**
   * Get bin index for a given frequency
   * @param {number} frequency - Frequency in Hz
   * @param {number} sampleRate - Sample rate in Hz
   * @returns {number} Bin index
   */
  frequencyToBin(frequency, sampleRate) {
    return Math.round(frequency * this.size / sampleRate);
  }
}

/**
 * Process an entire audio buffer with overlap-add FFT
 *
 * @param {Float32Array} input - Input channel data
 * @param {number} fftSize - FFT size
 * @param {number} hopSize - Hop size
 * @param {Function} processCallback - Function(spectrum, binFrequencies) to modify spectrum
 * @param {number} sampleRate - Sample rate for frequency calculation
 * @returns {Float32Array} Processed output
 */
export function processWithFFT(input, fftSize, hopSize, processCallback, sampleRate) {
  const processor = new FFTProcessor(fftSize, hopSize);
  const output = new Float32Array(input.length);

  // Pre-calculate bin frequencies
  const binFrequencies = new Float32Array(fftSize / 2);
  for (let i = 0; i < fftSize / 2; i++) {
    binFrequencies[i] = processor.binToFrequency(i, sampleRate);
  }

  // Process with overlap-add
  for (let pos = 0; pos + fftSize <= input.length; pos += hopSize) {
    // Extract block
    const block = input.subarray(pos, pos + fftSize);

    // Forward FFT
    const spectrum = processor.forward(block);

    // Apply processing callback
    processCallback(spectrum, binFrequencies);

    // Inverse FFT
    const processed = processor.inverse(spectrum);

    // Overlap-add
    for (let i = 0; i < fftSize; i++) {
      if (pos + i < output.length) {
        output[pos + i] += processed[i];
      }
    }
  }

  // Normalize by overlap factor
  const overlapFactor = fftSize / hopSize;
  for (let i = 0; i < output.length; i++) {
    output[i] /= overlapFactor;
  }

  return output;
}

/**
 * Analyze spectrum of a buffer section
 *
 * @param {Float32Array} input - Input samples
 * @param {number} fftSize - FFT size
 * @param {number} sampleRate - Sample rate
 * @returns {Object} {magnitudeDB, phase, frequencies}
 */
export function analyzeSpectrum(input, fftSize, sampleRate) {
  const processor = new FFTProcessor(fftSize);

  // Zero-pad if needed
  const paddedInput = new Float32Array(fftSize);
  const copyLength = Math.min(input.length, fftSize);
  for (let i = 0; i < copyLength; i++) {
    paddedInput[i] = input[i];
  }

  const spectrum = processor.forward(paddedInput);
  const magnitudeDB = processor.getMagnitudeDB(spectrum);
  const phase = processor.getPhase(spectrum);

  const frequencies = new Float32Array(fftSize / 2);
  for (let i = 0; i < fftSize / 2; i++) {
    frequencies[i] = processor.binToFrequency(i, sampleRate);
  }

  return { magnitudeDB, phase, frequencies };
}

// Re-export FFT for direct use
export { FFT };
