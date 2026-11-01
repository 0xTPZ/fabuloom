/** Deterministic PCM/WAV helpers shared by cinematic frame capture and tests. */

const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, value));

function ascii(view, offset, length) {
  let text = "";
  for (let index = 0; index < length; index += 1) text += String.fromCharCode(view.getUint8(offset + index));
  return text;
}

function asDataView(buffer) {
  if (buffer instanceof DataView) return buffer;
  if (buffer instanceof ArrayBuffer) return new DataView(buffer);
  if (ArrayBuffer.isView(buffer)) return new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
  throw new TypeError("WAV input must be an ArrayBuffer or ArrayBufferView");
}

/** Decode the deliberately narrow format emitted by the Kokoro provider. */
export function decodeMonoPcm16Wav(buffer) {
  const view = asDataView(buffer);
  if (view.byteLength < 44 || ascii(view, 0, 4) !== "RIFF" || ascii(view, 8, 4) !== "WAVE") {
    throw new TypeError("invalid RIFF/WAVE header");
  }
  let offset = 12;
  let sampleRate = 0;
  let channels = 0;
  let bitsPerSample = 0;
  let audioFormat = 0;
  let dataOffset = -1;
  let dataLength = 0;
  while (offset + 8 <= view.byteLength) {
    const chunkId = ascii(view, offset, 4);
    const chunkLength = view.getUint32(offset + 4, true);
    const chunkStart = offset + 8;
    const chunkEnd = chunkStart + chunkLength;
    if (chunkEnd > view.byteLength) throw new TypeError(`truncated WAV chunk: ${chunkId}`);
    if (chunkId === "fmt " && chunkLength >= 16) {
      audioFormat = view.getUint16(chunkStart, true);
      channels = view.getUint16(chunkStart + 2, true);
      sampleRate = view.getUint32(chunkStart + 4, true);
      bitsPerSample = view.getUint16(chunkStart + 14, true);
    } else if (chunkId === "data") {
      dataOffset = chunkStart;
      dataLength = chunkLength;
    }
    offset = chunkEnd + (chunkLength % 2);
  }
  if (audioFormat !== 1 || channels !== 1 || bitsPerSample !== 16 || !Number.isInteger(sampleRate) || sampleRate <= 0) {
    throw new TypeError("capture requires mono PCM-16 WAV");
  }
  if (dataOffset < 0) throw new TypeError("WAV data chunk is missing");
  const sampleCount = Math.floor(dataLength / 2);
  const samples = new Float32Array(sampleCount);
  for (let index = 0; index < sampleCount; index += 1) {
    samples[index] = view.getInt16(dataOffset + index * 2, true) / 32768;
  }
  return Object.freeze({ sampleRate, samples });
}

export function composePcmSegments(manifest, decodedSegments, sampleRate) {
  if (!manifest || !Array.isArray(manifest.segments) || manifest.segments.length !== decodedSegments.length) {
    throw new TypeError("manifest and decoded segment counts must match");
  }
  if (!Number.isInteger(sampleRate) || sampleRate <= 0) throw new TypeError("sampleRate must be a positive integer");
  const totalSamples = Math.max(1, Math.round(manifest.duration_ms * sampleRate / 1000));
  const samples = new Float32Array(totalSamples);
  for (const [index, segment] of manifest.segments.entries()) {
    const decoded = decodedSegments[index];
    if (!decoded || decoded.sampleRate !== sampleRate) throw new TypeError("all WAV segments must share the selected sample rate");
    const start = Math.max(0, Math.round(segment.start_ms * sampleRate / 1000));
    if (start < totalSamples) samples.set(decoded.samples.subarray(0, totalSamples - start), start);
  }
  return samples;
}

/**
 * Return an absolute-time RMS reader. It has no mutable clock state, so seek
 * and out-of-order frame capture produce the same amplitude values.
 */
export function createRmsReader(samples, sampleRate, options = {}) {
  if (!samples || typeof samples.length !== "number") throw new TypeError("samples are required");
  if (!Number.isInteger(sampleRate) || sampleRate <= 0) throw new TypeError("sampleRate must be a positive integer");
  const windowMs = Number(options.windowMs ?? 18);
  const noiseFloor = Number(options.noiseFloor ?? 0.012);
  const gain = Number(options.gain ?? 7);
  if (![windowMs, noiseFloor, gain].every(Number.isFinite) || windowMs <= 0 || noiseFloor < 0 || gain <= 0) {
    throw new TypeError("RMS options must be finite and positive");
  }
  const halfWindow = Math.max(1, Math.round(sampleRate * windowMs / 2000));
  return (timeMs) => {
    const safeTime = Number(timeMs);
    if (!Number.isFinite(safeTime) || safeTime < 0) return 0;
    const center = Math.round(safeTime / 1000 * sampleRate);
    const start = Math.max(0, center - halfWindow);
    const end = Math.min(samples.length, center + halfWindow + 1);
    if (end <= start) return 0;
    let sumSquares = 0;
    for (let index = start; index < end; index += 1) sumSquares += samples[index] * samples[index];
    const rms = Math.sqrt(sumSquares / (end - start));
    return clamp((rms - noiseFloor) * gain);
  };
}
