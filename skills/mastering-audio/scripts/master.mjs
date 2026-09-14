#!/usr/bin/env node
/**
 * Audio Mastering CLI Tool
 *
 * Processes audio files using the Web-Audio-Mastering DSP modules
 * Optimized for AI-generated music (Suno, Udio, etc.)
 *
 * Usage:
 *   node master.mjs <input> [output] [options]
 *
 * Options:
 *   --analyze          Only analyze, no processing
 *   --target-lufs N    Target LUFS (default: -14)
 *   --ceiling N        True peak ceiling in dB (default: -1)
 *   --deharsh          Apply de-harsh processing (recommended for Suno)
 *   --add-air          Add high-frequency sparkle
 *   --warmth           Add tape warmth/saturation
 *   --punch            Enhance transients
 *   --stereo-width N   Stereo width percentage (default: 100)
 *   --bit-depth N      Output bit depth: 16 or 24 (default: 24)
 *   --sample-rate N    Output sample rate (default: 48000)
 *   --preset NAME      Use preset: streaming, loud, dynamic, suno
 *   --json             Output results as JSON
 */

import { execSync, spawn } from 'child_process';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { basename, dirname, extname, join } from 'path';
import { fileURLToPath } from 'url';

// Initialize AudioBuffer shim before importing DSP modules
const __dirname = dirname(fileURLToPath(import.meta.url));

// Preflight: lib/dsp/fft.js imports the npm package `fft.js`, so a skill that has
// never had `npm install` run dies on the dynamic DSP import below with
// ERR_MODULE_NOT_FOUND naming an internal file — a raw Node stack trace that does
// not tell the caller the fix (ISS-20260719-001). Fail with the command instead.
// Runs in the module body, which is safe here because the two static imports that
// hoist above it (wav-encoder, audio-buffer-shim) have no imports of their own.
const SKILL_ROOT = join(__dirname, '..');
const missingDeps = (() => {
  try {
    const pkg = JSON.parse(readFileSync(join(SKILL_ROOT, 'package.json'), 'utf8'));
    return Object.keys(pkg.dependencies ?? {})
      .filter((dep) => !existsSync(join(SKILL_ROOT, 'node_modules', dep)));
  } catch {
    return []; // no/unreadable package.json — let the real import surface the error
  }
})();
if (missingDeps.length > 0) {
  console.error(`\nmastering-audio: missing npm ${missingDeps.length === 1 ? 'dependency' : 'dependencies'}: ${missingDeps.join(', ')}`);
  console.error(`Install once, then re-run:\n  npm install --prefix "${SKILL_ROOT}"\n`);
  process.exit(1);
}

await import(join(__dirname, '../lib/src/audio-buffer-shim.js'));

// Import DSP modules (bundled in skill)
const DSP_PATH = join(__dirname, '../lib/dsp');

const {
  measureLUFS,
  findTruePeak,
  normalizeToLUFS,
  applyGain,
  processHybridDynamic,
  applyExciter,
  applyTapeWarmth,
  applyMultibandTransient,
  adjustStereoWidth,
  applyBassMono,
  applyLookaheadLimiter,
  applyFinalFilters,
  detectDCOffset,
  removeDCOffsetBuffer,
  analyzeStereo
} = await import(join(DSP_PATH, 'index.js'));

import { encodeWAV } from '../lib/src/wav-encoder.js';
import { AudioBuffer, createAudioBufferFromInterleaved } from '../lib/src/audio-buffer-shim.js';

// ============================================================================
// Configuration & Presets
// ============================================================================

const PRESETS = {
  streaming: {
    targetLufs: -14,
    ceiling: -1,
    deharsh: true,
    addAir: false,
    warmth: false,
    punch: false,
    stereoWidth: 100,
    bassMono: true
  },
  loud: {
    targetLufs: -9,
    ceiling: -0.3,
    deharsh: true,
    addAir: true,
    warmth: true,
    punch: true,
    stereoWidth: 105,
    bassMono: true
  },
  dynamic: {
    targetLufs: -16,
    ceiling: -1,
    deharsh: false,
    addAir: false,
    warmth: false,
    punch: false,
    stereoWidth: 100,
    bassMono: false
  },
  suno: {
    // Optimized for Suno AI characteristics
    targetLufs: -14,
    ceiling: -1,
    deharsh: true,      // Reduce 2-4kHz harshness
    addAir: true,       // Restore high-end sparkle
    warmth: false,      // Suno already has warmth
    punch: true,        // Enhance transient definition
    stereoWidth: 102,   // Subtle widening
    bassMono: true      // Clean up stereo bass
  }
};

// ============================================================================
// Audio I/O
// ============================================================================

/**
 * Decode audio file to raw PCM using ffmpeg
 */
function decodeAudio(inputPath, targetSampleRate = 48000) {
  const tempPcm = `/tmp/audio_decode_${Date.now()}.raw`;

  try {
    // Decode to 32-bit float stereo PCM
    execSync(
      `ffmpeg -y -i "${inputPath}" -f f32le -acodec pcm_f32le -ar ${targetSampleRate} -ac 2 "${tempPcm}"`,
      { stdio: 'pipe' }
    );

    const rawData = readFileSync(tempPcm);
    const float32Data = new Float32Array(rawData.buffer, rawData.byteOffset, rawData.length / 4);

    // Clean up temp file
    execSync(`rm "${tempPcm}"`, { stdio: 'pipe' });

    return createAudioBufferFromInterleaved(float32Data, 2, targetSampleRate);
  } catch (error) {
    throw new Error(`Failed to decode audio: ${error.message}`);
  }
}

/**
 * Get audio duration using ffprobe
 */
function getAudioInfo(inputPath) {
  try {
    const result = execSync(
      `ffprobe -v quiet -print_format json -show_format -show_streams "${inputPath}"`,
      { encoding: 'utf8' }
    );
    return JSON.parse(result);
  } catch (error) {
    return null;
  }
}

// ============================================================================
// Analysis
// ============================================================================

/**
 * Analyze audio and return metrics
 */
function analyzeAudio(audioBuffer) {
  const lufs = measureLUFS(audioBuffer);
  const truePeak = findTruePeak(audioBuffer);
  const stereo = analyzeStereo(audioBuffer);
  const dcOffset = detectDCOffset(audioBuffer.getChannelData(0));

  // Detect potential issues
  const issues = [];

  if (lufs > -10) {
    issues.push({ type: 'loudness', severity: 'high', message: `Very loud (${lufs.toFixed(1)} LUFS) - may cause streaming normalization` });
  } else if (lufs > -12) {
    issues.push({ type: 'loudness', severity: 'medium', message: `Loud (${lufs.toFixed(1)} LUFS) - consider reducing for streaming` });
  }

  if (truePeak > 0) {
    issues.push({ type: 'clipping', severity: 'high', message: `Clipping detected (${truePeak.toFixed(1)} dBTP)` });
  } else if (truePeak > -0.5) {
    issues.push({ type: 'headroom', severity: 'medium', message: `Low headroom (${truePeak.toFixed(1)} dBTP)` });
  }

  if (Math.abs(dcOffset) > 0.01) {
    issues.push({ type: 'dc_offset', severity: 'low', message: `DC offset detected (${(dcOffset * 100).toFixed(2)}%)` });
  }

  return {
    lufs: lufs,
    truePeak: truePeak,
    stereoCorrelation: stereo?.correlation || 0,
    stereoWidth: stereo?.width || 1,
    dcOffset: dcOffset,
    duration: audioBuffer.duration,
    sampleRate: audioBuffer.sampleRate,
    channels: audioBuffer.numberOfChannels,
    issues: issues
  };
}

// ============================================================================
// Processing
// ============================================================================

/**
 * Apply full mastering chain
 */
async function masterAudio(audioBuffer, options, onProgress = null) {
  let processed = audioBuffer;
  const log = options.json ? () => {} : console.log;

  const report = (step, msg) => {
    log(`[${step}] ${msg}`);
    if (onProgress) onProgress(step, msg);
  };

  // Step 1: Remove DC offset if present
  const dcOffset = detectDCOffset(processed.getChannelData(0));
  if (Math.abs(dcOffset) > 0.001) {
    report('DC', `Removing DC offset (${(dcOffset * 100).toFixed(3)}%)`);
    processed = removeDCOffsetBuffer(processed);
  }

  // Step 2: De-harsh (multiband dynamics + dynamic EQ)
  if (options.deharsh) {
    report('DEHARSH', 'Applying hybrid dynamic processor');
    processed = await processHybridDynamic(processed, 'mastering');
  }

  // Step 3: Exciter (add air/sparkle)
  if (options.addAir) {
    report('EXCITER', 'Adding high-frequency enhancement');
    processed = await applyExciter(processed);
  }

  // Step 4: Tape warmth (multiband saturation)
  if (options.warmth) {
    report('WARMTH', 'Applying tape warmth');
    processed = await applyTapeWarmth(processed);
  }

  // Step 5: Transient enhancement (punch)
  if (options.punch) {
    report('PUNCH', 'Enhancing transients');
    processed = await applyMultibandTransient(processed);
  }

  // Step 6: Stereo processing
  if (options.stereoWidth !== 100) {
    report('STEREO', `Adjusting stereo width to ${options.stereoWidth}%`);
    processed = adjustStereoWidth(processed, options.stereoWidth / 100);
  }

  // Step 7: Bass mono (if enabled)
  if (options.bassMono) {
    report('BASS', 'Applying mono bass (< 200 Hz)');
    processed = applyBassMono(processed, 200);
  }

  // Step 8: Final filters (high-pass 30Hz, low-pass 18kHz)
  report('FILTERS', 'Applying final filters');
  processed = applyFinalFilters(processed, { highPass: 30, lowPass: 18000 });

  // Step 9: LUFS normalization
  const preLufs = measureLUFS(processed);
  report('NORMALIZE', `Normalizing: ${preLufs.toFixed(1)} LUFS → ${options.targetLufs} LUFS`);
  processed = normalizeToLUFS(processed, options.targetLufs, options.ceiling, { skipLimiter: true });

  // Step 10: True peak limiting
  const ceilingLinear = Math.pow(10, options.ceiling / 20);
  report('LIMITER', `Applying lookahead limiter (ceiling: ${options.ceiling} dBTP)`);
  processed = applyLookaheadLimiter(processed, ceilingLinear, 3, 100);

  return processed;
}

// ============================================================================
// CLI Interface
// ============================================================================

function parseArgs(args) {
  const options = {
    input: null,
    output: null,
    analyzeOnly: false,
    targetLufs: -14,
    ceiling: -1,
    deharsh: false,
    addAir: false,
    warmth: false,
    punch: false,
    stereoWidth: 100,
    bassMono: true,
    bitDepth: 24,
    sampleRate: 48000,
    preset: null,
    json: false
  };

  const positional = [];

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--analyze') {
      options.analyzeOnly = true;
    } else if (arg === '--target-lufs') {
      options.targetLufs = parseFloat(args[++i]);
    } else if (arg === '--ceiling') {
      options.ceiling = parseFloat(args[++i]);
    } else if (arg === '--deharsh') {
      options.deharsh = true;
    } else if (arg === '--add-air') {
      options.addAir = true;
    } else if (arg === '--warmth') {
      options.warmth = true;
    } else if (arg === '--punch') {
      options.punch = true;
    } else if (arg === '--stereo-width') {
      options.stereoWidth = parseFloat(args[++i]);
    } else if (arg === '--bit-depth') {
      options.bitDepth = parseInt(args[++i]);
    } else if (arg === '--sample-rate') {
      options.sampleRate = parseInt(args[++i]);
    } else if (arg === '--preset') {
      options.preset = args[++i];
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '--help' || arg === '-h') {
      console.log(`
Audio Mastering CLI - Optimized for AI-generated music

Usage: node master.mjs <input> [output] [options]

Options:
  --analyze          Only analyze, no processing
  --target-lufs N    Target LUFS (default: -14)
  --ceiling N        True peak ceiling in dB (default: -1)
  --deharsh          Apply de-harsh processing
  --add-air          Add high-frequency sparkle
  --warmth           Add tape warmth/saturation
  --punch            Enhance transients
  --stereo-width N   Stereo width % (default: 100)
  --bit-depth N      16 or 24 (default: 24)
  --sample-rate N    Output sample rate (default: 48000)
  --preset NAME      streaming, loud, dynamic, suno
  --json             Output as JSON

Examples:
  node master.mjs song.mp3 --analyze
  node master.mjs song.mp3 song_mastered.wav --preset suno
  node master.mjs song.mp3 --deharsh --add-air --target-lufs -14
`);
      process.exit(0);
    } else if (!arg.startsWith('-')) {
      positional.push(arg);
    }
  }

  options.input = positional[0];
  options.output = positional[1];

  // Apply preset if specified
  if (options.preset && PRESETS[options.preset]) {
    Object.assign(options, PRESETS[options.preset]);
  }

  return options;
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.error('Usage: node master.mjs <input> [output] [options]');
    console.error('Use --help for more information');
    process.exit(1);
  }

  const options = parseArgs(args);

  if (!options.input) {
    console.error('Error: Input file required');
    process.exit(1);
  }

  if (!existsSync(options.input)) {
    console.error(`Error: Input file not found: ${options.input}`);
    process.exit(1);
  }

  const log = options.json ? () => {} : console.log;

  // Get file info
  const info = getAudioInfo(options.input);
  log(`\nInput: ${options.input}`);
  if (info?.format?.duration) {
    log(`Duration: ${parseFloat(info.format.duration).toFixed(1)}s`);
  }

  // Decode audio
  log('\nDecoding audio...');
  const audioBuffer = decodeAudio(options.input, options.sampleRate);
  log(`Loaded: ${audioBuffer.duration.toFixed(1)}s, ${audioBuffer.sampleRate}Hz, ${audioBuffer.numberOfChannels}ch`);

  // Analyze
  log('\nAnalyzing...');
  const analysis = analyzeAudio(audioBuffer);

  if (options.json && options.analyzeOnly) {
    console.log(JSON.stringify({ analysis }, null, 2));
    return;
  }

  log(`  LUFS: ${analysis.lufs.toFixed(1)}`);
  log(`  True Peak: ${analysis.truePeak.toFixed(1)} dBTP`);
  log(`  Stereo Width: ${(analysis.stereoWidth * 100).toFixed(0)}%`);

  if (analysis.issues.length > 0) {
    log('\nDetected issues:');
    for (const issue of analysis.issues) {
      log(`  [${issue.severity.toUpperCase()}] ${issue.message}`);
    }
  }

  if (options.analyzeOnly) {
    return;
  }

  // Generate output path if not specified
  if (!options.output) {
    const dir = dirname(options.input);
    const base = basename(options.input, extname(options.input));
    options.output = join(dir, `${base}_mastered.wav`);
  }

  // Process
  log('\nProcessing...');
  const processed = await masterAudio(audioBuffer, options);

  // Final analysis
  const finalAnalysis = analyzeAudio(processed);
  log('\nFinal:');
  log(`  LUFS: ${finalAnalysis.lufs.toFixed(1)}`);
  log(`  True Peak: ${finalAnalysis.truePeak.toFixed(1)} dBTP`);

  // Encode and save
  log('\nEncoding WAV...');
  const wavBuffer = encodeWAV(processed, {
    bitDepth: options.bitDepth,
    sampleRate: options.sampleRate
  });

  writeFileSync(options.output, wavBuffer);
  log(`\nSaved: ${options.output}`);
  log(`  Size: ${(wavBuffer.length / 1024 / 1024).toFixed(1)} MB`);
  log(`  Format: ${options.sampleRate}Hz / ${options.bitDepth}-bit`);

  if (options.json) {
    console.log(JSON.stringify({
      input: options.input,
      output: options.output,
      before: analysis,
      after: finalAnalysis,
      settings: {
        targetLufs: options.targetLufs,
        ceiling: options.ceiling,
        deharsh: options.deharsh,
        addAir: options.addAir,
        warmth: options.warmth,
        punch: options.punch,
        stereoWidth: options.stereoWidth
      }
    }, null, 2));
  }
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
