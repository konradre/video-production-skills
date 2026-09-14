/**
 * Hybrid Dynamic Spectral Processor
 * Combines Dynamic EQ, Multiband Compression, and De-esser processing
 * 
 * Designed for AI-generated audio artifact reduction with musical transparency
 * 
 * Features:
 * - Per-band envelope followers with independent attack/release
 * - Resonance detection for surgical peak cutting
 * - Soft-knee compression curves
 * - Frequency-weighted sidechain for intelligent detection
 */

import { FFTProcessor } from './fft.js';
import { linearToDb, dbToLinear } from './utils.js';

/**
 * Envelope follower with configurable attack/release
 */
class EnvelopeFollower {
  constructor(sampleRate, attackMs = 5, releaseMs = 50) {
    this.sampleRate = sampleRate;
    this.envelope = 0;
    this.setTimes(attackMs, releaseMs);
  }

  setTimes(attackMs, releaseMs) {
    // Convert ms to coefficient (exponential smoothing)
    this.attackCoef = Math.exp(-1 / (this.sampleRate * attackMs / 1000));
    this.releaseCoef = Math.exp(-1 / (this.sampleRate * releaseMs / 1000));
  }

  process(input) {
    const abs = Math.abs(input);
    if (abs > this.envelope) {
      // Attack - rising
      this.envelope = this.attackCoef * this.envelope + (1 - this.attackCoef) * abs;
    } else {
      // Release - falling
      this.envelope = this.releaseCoef * this.envelope + (1 - this.releaseCoef) * abs;
    }
    return this.envelope;
  }

  reset() {
    this.envelope = 0;
  }
}

/**
 * Soft-knee compressor gain computer
 */
class GainComputer {
  constructor(thresholdDb = -20, ratio = 4, kneeDb = 6) {
    this.thresholdDb = thresholdDb;
    this.ratio = ratio;
    this.kneeDb = kneeDb;
    this.kneeStart = thresholdDb - kneeDb / 2;
    this.kneeEnd = thresholdDb + kneeDb / 2;
  }

  setParams(thresholdDb, ratio, kneeDb) {
    this.thresholdDb = thresholdDb;
    this.ratio = ratio;
    this.kneeDb = kneeDb;
    this.kneeStart = thresholdDb - kneeDb / 2;
    this.kneeEnd = thresholdDb + kneeDb / 2;
  }

  /**
   * Compute gain reduction in dB for input level in dB
   * @param {number} inputDb - Input level in dB
   * @returns {number} Gain reduction in dB (negative or zero)
   */
  computeGainDb(inputDb) {
    if (inputDb <= this.kneeStart) {
      // Below knee - no reduction
      return 0;
    } else if (inputDb >= this.kneeEnd) {
      // Above knee - full compression
      const excess = inputDb - this.thresholdDb;
      const compressed = excess / this.ratio;
      return compressed - excess; // This is negative (reduction)
    } else {
      // In knee - soft transition (quadratic interpolation)
      const kneeProgress = (inputDb - this.kneeStart) / this.kneeDb;
      const fullReduction = (inputDb - this.thresholdDb) * (1 - 1 / this.ratio);
      return -fullReduction * kneeProgress * kneeProgress;
    }
  }
}

/**
 * Band configuration for the multiband processor
 */
const DEFAULT_BANDS = [
  {
    name: 'sub',
    freqLow: 0,
    freqHigh: 80,
    attackMs: 30,
    releaseMs: 200,
    thresholdDb: -12,
    ratio: 2,
    kneeDb: 10,
    enabled: true
  },
  {
    name: 'bass',
    freqLow: 80,
    freqHigh: 250,
    attackMs: 20,
    releaseMs: 150,
    thresholdDb: -15,
    ratio: 2.5,
    kneeDb: 8,
    enabled: true
  },
  {
    name: 'lowMid',
    freqLow: 250,
    freqHigh: 1000,
    attackMs: 10,
    releaseMs: 100,
    thresholdDb: -18,
    ratio: 3,
    kneeDb: 6,
    enabled: true
  },
  {
    name: 'mid',
    freqLow: 1000,
    freqHigh: 3000,
    attackMs: 8,
    releaseMs: 80,
    thresholdDb: -20,
    ratio: 3.5,
    kneeDb: 6,
    enabled: true
  },
  {
    name: 'presence',
    freqLow: 3000,
    freqHigh: 6000,
    attackMs: 2,        // Faster attack for harsh transients
    releaseMs: 40,
    thresholdDb: -26,   // Lower threshold for Suno harshness (Was -24)
    ratio: 5,           // Higher ratio
    kneeDb: 4,
    enabled: true
  },
  {
    name: 'brilliance',
    freqLow: 6000,
    freqHigh: 12000,
    attackMs: 2,        // Very fast
    releaseMs: 30,
    thresholdDb: -28,   // Aggressive on the "swirl" (Was -26)
    ratio: 6,
    kneeDb: 3,
    enabled: true
  },
  {
    name: 'air',
    freqLow: 12000,
    freqHigh: 20000,
    attackMs: 5,
    releaseMs: 50,
    thresholdDb: -22,
    ratio: 3,
    kneeDb: 6,
    enabled: true
  }
];

/**
 * Resonance detector for dynamic EQ behavior
 * Finds peaks that stick out from the average spectrum
 */
class ResonanceDetector {
  constructor(numBins, smoothingFactor = 0.3) {
    this.numBins = numBins;
    this.smoothingFactor = smoothingFactor;
    this.averageSpectrum = new Float32Array(numBins);
    this.peakSpectrum = new Float32Array(numBins);
    this.initialized = false;
  }

  /**
   * Analyze spectrum and detect resonant peaks
   * @param {Float32Array} magnitudes - Current frame magnitudes
   * @returns {Float32Array} Resonance amounts (0-1) per bin
   */
  analyze(magnitudes) {
    const resonance = new Float32Array(this.numBins);

    if (!this.initialized) {
      // First frame - initialize averages
      for (let i = 0; i < this.numBins; i++) {
        this.averageSpectrum[i] = magnitudes[i];
        this.peakSpectrum[i] = magnitudes[i];
      }
      this.initialized = true;
      return resonance;
    }

    // Update running average and detect peaks
    for (let i = 0; i < this.numBins; i++) {
      const mag = magnitudes[i];

      // Exponential smoothing for average
      this.averageSpectrum[i] =
        this.smoothingFactor * mag +
        (1 - this.smoothingFactor) * this.averageSpectrum[i];

      // Peak tracking (slow decay)
      if (mag > this.peakSpectrum[i]) {
        this.peakSpectrum[i] = mag;
      } else {
        this.peakSpectrum[i] *= 0.999; // Slow decay
      }

      // Resonance = how much current exceeds average
      const avg = this.averageSpectrum[i];
      if (avg > 1e-10 && mag > avg * 1.5) {
        // More than 1.5x average = resonant
        const excess = mag / avg;
        resonance[i] = Math.min(1, (excess - 1.5) / 2); // Normalize 1.5-3.5x to 0-1
      }
    }

    return resonance;
  }

  reset() {
    this.averageSpectrum.fill(0);
    this.peakSpectrum.fill(0);
    this.initialized = false;
  }
}

/**
 * Main Hybrid Dynamic Processor class
 */
export class HybridDynamicProcessor {
  /**
   * Create a hybrid dynamic processor
   * @param {Object} options - Configuration options
   */
  constructor(options = {}) {
    this.fftSize = options.fftSize || 2048;
    this.hopSize = options.hopSize || 512;
    this.numBins = this.fftSize / 2;

    // Processing components
    this.processor = new FFTProcessor(this.fftSize, this.hopSize);
    this.resonanceDetector = new ResonanceDetector(this.numBins);

    // Band configuration (deep copy to allow modification)
    this.bands = JSON.parse(JSON.stringify(options.bands || DEFAULT_BANDS));

    // Per-band processors (initialized on first use with sample rate)
    this.bandEnvelopes = null;
    this.bandCompressors = null;
    this.sampleRate = null;

    // Global settings
    this.dryWetMix = options.dryWetMix ?? 1.0; // 0 = dry, 1 = wet

    // Dynamic EQ settings
    this.dynamicEqEnabled = options.dynamicEqEnabled ?? true;
    this.dynamicEqSensitivity = options.dynamicEqSensitivity ?? 0.5;
    this.dynamicEqMaxCut = options.dynamicEqMaxCut ?? -12; // Max cut in dB

    // AI artifact targeting
    this.aiArtifactMode = options.aiArtifactMode ?? true;
  }

  /**
   * Initialize per-band processors for given sample rate
   * @private
   */
  _initBandProcessors(sampleRate) {
    if (this.sampleRate === sampleRate && this.bandEnvelopes) {
      return; // Already initialized
    }

    this.sampleRate = sampleRate;
    this.bandEnvelopes = [];
    this.bandCompressors = [];

    for (const band of this.bands) {
      this.bandEnvelopes.push(
        new EnvelopeFollower(sampleRate, band.attackMs, band.releaseMs)
      );
      this.bandCompressors.push(
        new GainComputer(band.thresholdDb, band.ratio, band.kneeDb)
      );
    }
  }

  /**
   * Get band index for a frequency
   * @private
   */
  _getBandForFreq(freq) {
    for (let i = 0; i < this.bands.length; i++) {
      if (freq >= this.bands[i].freqLow && freq < this.bands[i].freqHigh) {
        return i;
      }
    }
    return this.bands.length - 1; // Default to last band
  }

  /**
   * Compute per-bin gain based on all processing stages
   * @private
   */
  _computeBinGains(magnitudes, sampleRate) {
    const gains = new Float32Array(this.numBins);
    gains.fill(1); // Start with unity gain

    // 1. Compute band energies
    const bandEnergies = new Float32Array(this.bands.length);
    const bandBinCounts = new Float32Array(this.bands.length);

    for (let bin = 0; bin < this.numBins; bin++) {
      const freq = this.processor.binToFrequency(bin, sampleRate);
      const bandIdx = this._getBandForFreq(freq);
      bandEnergies[bandIdx] += magnitudes[bin] * magnitudes[bin];
      bandBinCounts[bandIdx]++;
    }

    // RMS per band
    for (let i = 0; i < this.bands.length; i++) {
      if (bandBinCounts[i] > 0) {
        bandEnergies[i] = Math.sqrt(bandEnergies[i] / bandBinCounts[i]);
      }
    }

    // 2. Compute compression gain per band
    const bandGainsDb = new Float32Array(this.bands.length);
    for (let i = 0; i < this.bands.length; i++) {
      if (!this.bands[i].enabled) continue;

      const energyDb = linearToDb(bandEnergies[i]);
      const envelope = this.bandEnvelopes[i].process(bandEnergies[i]);
      const envelopeDb = linearToDb(envelope);

      // Use envelope for compression calculation (smoother)
      bandGainsDb[i] = this.bandCompressors[i].computeGainDb(envelopeDb);
    }

    // 3. Resonance detection for dynamic EQ
    let resonance = null;
    if (this.dynamicEqEnabled) {
      resonance = this.resonanceDetector.analyze(magnitudes);
    }

    // 4. Apply gains per bin
    for (let bin = 0; bin < this.numBins; bin++) {
      const freq = this.processor.binToFrequency(bin, sampleRate);
      const bandIdx = this._getBandForFreq(freq);

      // Start with multiband compression gain
      let gainDb = bandGainsDb[bandIdx];

      // Add dynamic EQ cut for resonant peaks
      if (this.dynamicEqEnabled && resonance[bin] > 0) {
        const dynEqCut = this.dynamicEqMaxCut * resonance[bin] * this.dynamicEqSensitivity;
        gainDb += dynEqCut;
      }

      // AI artifact mode: extra sensitivity in problematic range
      if (this.aiArtifactMode && freq >= 5000 && freq <= 12000) {
        // Additional compression in AI artifact range (add extra dB reduction, not multiply)
        gainDb += gainDb * 0.3; // 30% more reduction (if gainDb is -6, becomes -7.8)
      }

      // Convert to linear gain
      gains[bin] = dbToLinear(gainDb);
    }

    return gains;
  }

  /**
   * Process audio buffer
   * @param {AudioBuffer} buffer - Input audio buffer
   * @param {Function} onProgress - Progress callback (0-1)
   * @returns {AudioBuffer} Processed audio buffer
   */
  process(buffer, onProgress = null) {
    this._initBandProcessors(buffer.sampleRate);

    const outputBuffer = new AudioBuffer({
      numberOfChannels: buffer.numberOfChannels,
      length: buffer.length,
      sampleRate: buffer.sampleRate
    });

    const totalChannels = buffer.numberOfChannels;

    for (let ch = 0; ch < totalChannels; ch++) {
      const input = buffer.getChannelData(ch);
      const output = outputBuffer.getChannelData(ch);
      output.fill(0);

      // Reset per-channel state
      this._resetChannelState();

      this._processChannel(input, output, buffer.sampleRate, (progress) => {
        if (onProgress) {
          onProgress((ch + progress) / totalChannels);
        }
      });

      // Apply dry/wet mix
      if (this.dryWetMix < 1) {
        for (let i = 0; i < output.length; i++) {
          output[i] = input[i] * (1 - this.dryWetMix) + output[i] * this.dryWetMix;
        }
      }
    }

    return outputBuffer;
  }

  /**
   * Reset per-channel processing state
   * @private
   */
  _resetChannelState() {
    for (const env of this.bandEnvelopes) {
      env.reset();
    }
    this.resonanceDetector.reset();
  }

  /**
   * Process single channel
   * @private
   */
  _processChannel(input, output, sampleRate, onProgress) {
    const numFrames = Math.floor((input.length - this.fftSize) / this.hopSize);
    const magnitudes = new Float32Array(this.numBins);

    for (let frame = 0; frame < numFrames; frame++) {
      const pos = frame * this.hopSize;
      const block = input.subarray(pos, pos + this.fftSize);

      // Forward FFT
      const spectrum = this.processor.forward(block);

      // Extract magnitudes
      for (let bin = 0; bin < this.numBins; bin++) {
        const re = spectrum[bin * 2];
        const im = spectrum[bin * 2 + 1];
        magnitudes[bin] = Math.sqrt(re * re + im * im);
      }

      // Compute gains
      const gains = this._computeBinGains(magnitudes, sampleRate);

      // Apply gains to spectrum
      for (let bin = 0; bin < this.numBins; bin++) {
        const gain = gains[bin];
        spectrum[bin * 2] *= gain;
        spectrum[bin * 2 + 1] *= gain;

        // Mirror for negative frequencies
        if (bin > 0 && bin < this.numBins) {
          const mirrorBin = this.fftSize - bin;
          spectrum[mirrorBin * 2] = spectrum[bin * 2];
          spectrum[mirrorBin * 2 + 1] = -spectrum[bin * 2 + 1];
        }
      }

      // Inverse FFT
      const processed = this.processor.inverse(spectrum);

      // Overlap-add
      for (let i = 0; i < this.fftSize; i++) {
        if (pos + i < output.length) {
          output[pos + i] += processed[i];
        }
      }

      // Progress
      if (onProgress && frame % 100 === 0) {
        onProgress(frame / numFrames);
      }
    }

    // Normalize by overlap factor
    const overlapFactor = this.fftSize / this.hopSize;
    for (let i = 0; i < output.length; i++) {
      output[i] /= overlapFactor;
    }
  }

  /**
   * Get current band configuration
   * @returns {Array} Band configurations
   */
  getBands() {
    return JSON.parse(JSON.stringify(this.bands));
  }

  /**
   * Update band settings
   * @param {number} bandIndex - Band index to update
   * @param {Object} settings - New settings
   */
  updateBand(bandIndex, settings) {
    if (bandIndex < 0 || bandIndex >= this.bands.length) {
      throw new Error(`Invalid band index: ${bandIndex}`);
    }

    Object.assign(this.bands[bandIndex], settings);

    // Update processors if initialized
    if (this.bandEnvelopes) {
      const band = this.bands[bandIndex];
      this.bandEnvelopes[bandIndex].setTimes(band.attackMs, band.releaseMs);
      this.bandCompressors[bandIndex].setParams(
        band.thresholdDb,
        band.ratio,
        band.kneeDb
      );
    }
  }

  /**
   * Create preset for gentle AI artifact reduction
   * @returns {HybridDynamicProcessor}
   */
  static createGentlePreset() {
    return new HybridDynamicProcessor({
      dynamicEqSensitivity: 0.3,
      dynamicEqMaxCut: -6,
      aiArtifactMode: true,
      bands: DEFAULT_BANDS.map(band => ({
        ...band,
        thresholdDb: band.thresholdDb + 6, // Higher thresholds
        ratio: Math.max(2, band.ratio - 1)  // Lower ratios
      }))
    });
  }

  /**
   * Create preset for aggressive AI artifact reduction
   * @returns {HybridDynamicProcessor}
   */
  static createAggressivePreset() {
    return new HybridDynamicProcessor({
      dynamicEqSensitivity: 0.8,
      dynamicEqMaxCut: -18,
      aiArtifactMode: true,
      bands: DEFAULT_BANDS.map(band => ({
        ...band,
        thresholdDb: band.thresholdDb - 6, // Lower thresholds
        ratio: band.ratio + 2               // Higher ratios
      }))
    });
  }

  /**
   * Create preset for mastering (transparent)
   * @returns {HybridDynamicProcessor}
   */
  static createMasteringPreset() {
    return new HybridDynamicProcessor({
      dynamicEqSensitivity: 0.2,   // Very gentle
      dynamicEqMaxCut: -3,         // Minimal cuts
      aiArtifactMode: false,       // Neutral
      dryWetMix: 0.15,             // 15% wet, 85% dry for maximum transparency
      bands: DEFAULT_BANDS.map(band => ({
        ...band,
        thresholdDb: band.thresholdDb + 12, // Raise thresholds 12dB (much less compression)
        kneeDb: band.kneeDb + 8,            // Very soft knees
        ratio: Math.max(1.2, band.ratio - 1.5) // Very gentle ratios
      }))
    });
  }
}

/**
 * Convenience function for quick processing
 * @param {AudioBuffer} buffer - Input audio
 * @param {string} preset - 'gentle', 'aggressive', or 'mastering'
 * @param {Function} onProgress - Progress callback
 * @returns {AudioBuffer} Processed audio
 */
export function processHybridDynamic(buffer, preset = 'gentle', onProgress = null) {
  let processor;
  switch (preset) {
    case 'aggressive':
      processor = HybridDynamicProcessor.createAggressivePreset();
      break;
    case 'mastering':
      processor = HybridDynamicProcessor.createMasteringPreset();
      break;
    case 'gentle':
    default:
      processor = HybridDynamicProcessor.createGentlePreset();
  }
  return processor.process(buffer, onProgress);
}

export { DEFAULT_BANDS, EnvelopeFollower, GainComputer, ResonanceDetector };
