/**
 * AudioBuffer Shim for Node.js
 * Provides Web Audio API AudioBuffer interface for DSP module compatibility
 */

/**
 * AudioBuffer-compatible class for Node.js environments
 * Matches Web Audio API interface used by DSP modules
 */
export class AudioBuffer {
  /**
   * @param {Object} options
   * @param {number} options.numberOfChannels - Number of audio channels
   * @param {number} options.length - Number of samples per channel
   * @param {number} options.sampleRate - Sample rate in Hz
   */
  constructor({ numberOfChannels, length, sampleRate }) {
    this._numberOfChannels = numberOfChannels;
    this._length = length;
    this._sampleRate = sampleRate;
    this._channels = [];

    for (let i = 0; i < numberOfChannels; i++) {
      this._channels.push(new Float32Array(length));
    }
  }

  get numberOfChannels() {
    return this._numberOfChannels;
  }

  get length() {
    return this._length;
  }

  get sampleRate() {
    return this._sampleRate;
  }

  get duration() {
    return this._length / this._sampleRate;
  }

  /**
   * Get channel data as Float32Array
   * @param {number} channel - Channel index
   * @returns {Float32Array}
   */
  getChannelData(channel) {
    if (channel < 0 || channel >= this._numberOfChannels) {
      throw new RangeError(`Channel ${channel} out of range`);
    }
    return this._channels[channel];
  }

  /**
   * Copy data to a channel
   * @param {Float32Array} source - Source data
   * @param {number} channelNumber - Target channel
   * @param {number} startInChannel - Start offset in channel
   */
  copyToChannel(source, channelNumber, startInChannel = 0) {
    const dest = this.getChannelData(channelNumber);
    for (let i = 0; i < source.length && (startInChannel + i) < dest.length; i++) {
      dest[startInChannel + i] = source[i];
    }
  }

  /**
   * Copy data from a channel
   * @param {Float32Array} destination - Destination array
   * @param {number} channelNumber - Source channel
   * @param {number} startInChannel - Start offset in channel
   */
  copyFromChannel(destination, channelNumber, startInChannel = 0) {
    const src = this.getChannelData(channelNumber);
    for (let i = 0; i < destination.length && (startInChannel + i) < src.length; i++) {
      destination[i] = src[startInChannel + i];
    }
  }
}

/**
 * Create AudioBuffer from interleaved Float32Array
 * @param {Float32Array} data - Interleaved audio data
 * @param {number} channels - Number of channels
 * @param {number} sampleRate - Sample rate
 * @returns {AudioBuffer}
 */
export function createAudioBufferFromInterleaved(data, channels, sampleRate) {
  const samplesPerChannel = Math.floor(data.length / channels);
  const buffer = new AudioBuffer({
    numberOfChannels: channels,
    length: samplesPerChannel,
    sampleRate: sampleRate
  });

  // Deinterleave
  for (let ch = 0; ch < channels; ch++) {
    const channelData = buffer.getChannelData(ch);
    for (let i = 0; i < samplesPerChannel; i++) {
      channelData[i] = data[i * channels + ch];
    }
  }

  return buffer;
}

/**
 * Convert AudioBuffer to interleaved Float32Array
 * @param {AudioBuffer} buffer - Audio buffer
 * @returns {Float32Array} - Interleaved data
 */
export function audioBufferToInterleaved(buffer) {
  const channels = buffer.numberOfChannels;
  const length = buffer.length;
  const interleaved = new Float32Array(length * channels);

  for (let i = 0; i < length; i++) {
    for (let ch = 0; ch < channels; ch++) {
      interleaved[i * channels + ch] = buffer.getChannelData(ch)[i];
    }
  }

  return interleaved;
}

// Make globally available for DSP modules
globalThis.AudioBuffer = AudioBuffer;

export default AudioBuffer;
