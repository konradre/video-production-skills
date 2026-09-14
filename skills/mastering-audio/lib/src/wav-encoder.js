/**
 * WAV Encoder for Node.js
 * Encodes AudioBuffer to WAV format (16-bit or 24-bit)
 */

/**
 * Encode AudioBuffer to WAV format
 * @param {AudioBuffer} audioBuffer - Source audio buffer
 * @param {Object} options
 * @param {number} options.bitDepth - 16 or 24 (default: 24)
 * @param {number} options.sampleRate - Override sample rate (default: buffer's rate)
 * @returns {Buffer} - WAV file as Node.js Buffer
 */
export function encodeWAV(audioBuffer, options = {}) {
  const bitDepth = options.bitDepth || 24;
  const numChannels = audioBuffer.numberOfChannels;
  const sampleRate = options.sampleRate || audioBuffer.sampleRate;
  const bytesPerSample = bitDepth / 8;

  const channelData = [];
  for (let ch = 0; ch < numChannels; ch++) {
    channelData.push(audioBuffer.getChannelData(ch));
  }

  const numSamples = channelData[0].length;
  const dataSize = numSamples * numChannels * bytesPerSample;
  const buffer = Buffer.alloc(44 + dataSize);

  // RIFF header
  buffer.write('RIFF', 0);
  buffer.writeUInt32LE(36 + dataSize, 4);
  buffer.write('WAVE', 8);

  // fmt chunk
  buffer.write('fmt ', 12);
  buffer.writeUInt32LE(16, 16); // chunk size
  buffer.writeUInt16LE(1, 20);  // PCM format
  buffer.writeUInt16LE(numChannels, 22);
  buffer.writeUInt32LE(sampleRate, 24);
  buffer.writeUInt32LE(sampleRate * numChannels * bytesPerSample, 28); // byte rate
  buffer.writeUInt16LE(numChannels * bytesPerSample, 32); // block align
  buffer.writeUInt16LE(bitDepth, 34);

  // data chunk
  buffer.write('data', 36);
  buffer.writeUInt32LE(dataSize, 40);

  // Write samples (interleaved)
  let offset = 44;
  const maxVal = bitDepth === 16 ? 32767 : 8388607;

  for (let i = 0; i < numSamples; i++) {
    for (let ch = 0; ch < numChannels; ch++) {
      const sample = Math.max(-1, Math.min(1, channelData[ch][i]));
      const intSample = Math.round(sample * maxVal);

      if (bitDepth === 16) {
        buffer.writeInt16LE(intSample, offset);
        offset += 2;
      } else {
        // 24-bit: write 3 bytes LE
        const clamped = Math.max(-8388607, Math.min(8388607, intSample));
        buffer.writeUInt8(clamped & 0xFF, offset);
        buffer.writeUInt8((clamped >> 8) & 0xFF, offset + 1);
        buffer.writeUInt8((clamped >> 16) & 0xFF, offset + 2);
        offset += 3;
      }
    }
  }

  return buffer;
}

/**
 * Decode WAV file to AudioBuffer
 * Simple decoder for standard PCM WAV files
 * @param {Buffer} wavBuffer - WAV file buffer
 * @returns {Promise<AudioBuffer>}
 */
export async function decodeWAV(wavBuffer) {
  // Validate RIFF header
  if (wavBuffer.toString('ascii', 0, 4) !== 'RIFF') {
    throw new Error('Not a valid WAV file: missing RIFF header');
  }
  if (wavBuffer.toString('ascii', 8, 12) !== 'WAVE') {
    throw new Error('Not a valid WAV file: missing WAVE format');
  }

  // Find fmt chunk
  let offset = 12;
  let fmtFound = false;
  let numChannels, sampleRate, bitDepth;

  while (offset < wavBuffer.length - 8) {
    const chunkId = wavBuffer.toString('ascii', offset, offset + 4);
    const chunkSize = wavBuffer.readUInt32LE(offset + 4);

    if (chunkId === 'fmt ') {
      const format = wavBuffer.readUInt16LE(offset + 8);
      if (format !== 1 && format !== 3) {
        throw new Error(`Unsupported WAV format: ${format} (only PCM supported)`);
      }
      numChannels = wavBuffer.readUInt16LE(offset + 10);
      sampleRate = wavBuffer.readUInt32LE(offset + 12);
      bitDepth = wavBuffer.readUInt16LE(offset + 22);
      fmtFound = true;
    }

    if (chunkId === 'data' && fmtFound) {
      const dataStart = offset + 8;
      const dataSize = chunkSize;
      const bytesPerSample = bitDepth / 8;
      const numSamples = Math.floor(dataSize / (numChannels * bytesPerSample));

      // Import AudioBuffer (will be available via shim)
      const { AudioBuffer } = await import('./audio-buffer-shim.js');

      const audioBuffer = new AudioBuffer({
        numberOfChannels: numChannels,
        length: numSamples,
        sampleRate: sampleRate
      });

      // Read samples
      let readOffset = dataStart;
      for (let i = 0; i < numSamples; i++) {
        for (let ch = 0; ch < numChannels; ch++) {
          let sample;
          if (bitDepth === 8) {
            sample = (wavBuffer.readUInt8(readOffset) - 128) / 128;
            readOffset += 1;
          } else if (bitDepth === 16) {
            sample = wavBuffer.readInt16LE(readOffset) / 32768;
            readOffset += 2;
          } else if (bitDepth === 24) {
            let val = wavBuffer.readUInt8(readOffset) |
                      (wavBuffer.readUInt8(readOffset + 1) << 8) |
                      (wavBuffer.readUInt8(readOffset + 2) << 16);
            if (val & 0x800000) val |= 0xFF000000; // sign extend
            sample = val / 8388608;
            readOffset += 3;
          } else if (bitDepth === 32) {
            sample = wavBuffer.readFloatLE(readOffset);
            readOffset += 4;
          }
          audioBuffer.getChannelData(ch)[i] = sample;
        }
      }

      return audioBuffer;
    }

    offset += 8 + chunkSize;
    if (chunkSize % 2 === 1) offset++; // padding byte
  }

  throw new Error('Could not find data chunk in WAV file');
}

export default { encodeWAV, decodeWAV };
