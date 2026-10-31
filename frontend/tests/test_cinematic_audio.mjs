import assert from "node:assert/strict";
import test from "node:test";
import { composePcmSegments, createRmsReader, decodeMonoPcm16Wav } from "../src/cinematic-audio.mjs";

function wavPcm16(samples, sampleRate = 1000) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const write = (offset, text) => [...text].forEach((character, index) => view.setUint8(offset + index, character.charCodeAt(0)));
  write(0, "RIFF"); view.setUint32(4, buffer.byteLength - 8, true); write(8, "WAVE"); write(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true); view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true); write(36, "data"); view.setUint32(40, samples.length * 2, true);
  samples.forEach((sample, index) => view.setInt16(44 + index * 2, sample, true));
  return buffer;
}

test("decodes Kokoro-style mono PCM-16 WAV and rejects malformed data", () => {
  const decoded = decodeMonoPcm16Wav(wavPcm16([0, 16384, -16384, 32767], 24000));
  assert.equal(decoded.sampleRate, 24000);
  assert.equal(decoded.samples.length, 4);
  assert.ok(Math.abs(decoded.samples[1] - 0.5) < 0.001);
  assert.throws(() => decodeMonoPcm16Wav(new ArrayBuffer(44)), /RIFF\/WAVE/);
});

test("composes measured segments at their absolute manifest positions", () => {
  const manifest = { duration_ms: 400, segments: [{ start_ms: 0 }, { start_ms: 200 }] };
  const first = { sampleRate: 1000, samples: Float32Array.from([0.1, 0.1]) };
  const second = { sampleRate: 1000, samples: Float32Array.from([0.8, 0.8]) };
  const composed = composePcmSegments(manifest, [first, second], 1000);
  assert.ok(Math.abs(composed[0] - 0.1) < 0.000001);
  assert.ok(Math.abs(composed[1] - 0.1) < 0.000001);
  assert.equal(composed[2], 0);
  assert.ok(Math.abs(composed[200] - 0.8) < 0.000001);
});

test("RMS reader is absolute-time, silence-aware and clamps speech amplitude", () => {
  const samples = new Float32Array(1000);
  samples.fill(0.5, 400, 600);
  const amplitudeAt = createRmsReader(samples, 1000, { windowMs: 20, noiseFloor: 0.01, gain: 2 });
  assert.equal(amplitudeAt(100), 0);
  assert.ok(amplitudeAt(500) > 0.9);
  assert.equal(amplitudeAt(500), amplitudeAt(500));
  assert.ok(amplitudeAt(-1) === 0);
});

test("RMS reader preserves gaps and rejects mismatched segment sample rates", () => {
  const manifest = { duration_ms: 300, segments: [{ start_ms: 0 }] };
  assert.throws(() => composePcmSegments(manifest, [{ sampleRate: 24000, samples: new Float32Array(1) }], 16000), /sample rate/);
  const reader = createRmsReader(Float32Array.from([0, 0, 0, 0]), 1000);
  assert.equal(reader(100), 0);
});
