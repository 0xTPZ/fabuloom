import assert from "node:assert/strict";
import test from "node:test";
import {
  NARRATOR_CANVAS,
  avatarCircleBounds,
  createNarratorAvatarPack,
  createNarratorModeDescriptor,
  createNarratorTimeline,
  facialPoseAt,
  segmentAt,
  validateNarratorManifest,
} from "../src/narrator-mode.mjs";

const manifest = {
  id: "narrator-test",
  duration_ms: 2400,
  metadata: { voice_id: "pm_santa" },
  segments: [
    { id: "one", text: "Olá, viajante!", start_ms: 0, end_ms: 1000, voice_id: "pm_santa", audio_uri: "file:///one.wav" },
    { id: "two", text: "A história começa.", start_ms: 1200, end_ms: 2400, voice_id: "pm_santa", audio_uri: "file:///two.wav" },
  ],
};

test("narrator timeline preserves measured segment ranges and does not invent word timing", () => {
  const timeline = createNarratorTimeline(manifest);
  assert.equal(timeline.durationMs, 2400);
  assert.equal(segmentAt(timeline, 500).id, "one");
  assert.equal(segmentAt(timeline, 1000), null);
  assert.equal(segmentAt(timeline, 1800).id, "two");
  assert.deepEqual(timeline.segments[0].wordTimings, []);
  assert.equal(timeline.segments[0].timingSource, "measured_wav_segment");
});

test("manifest validation rejects unordered or invalid measured ranges", () => {
  assert.doesNotThrow(() => validateNarratorManifest(manifest));
  assert.throws(() => validateNarratorManifest({ ...manifest, duration_ms: 0 }), /duration_ms/);
  assert.throws(() => validateNarratorManifest({ ...manifest, segments: [{ ...manifest.segments[0], end_ms: 0 }] }), /invalid measured range/);
  assert.throws(() => validateNarratorManifest({ ...manifest, segments: [{ ...manifest.segments[0], start_ms: 1400, end_ms: 2000 }, manifest.segments[1]] }), /ordered timeline/);
});

test("avatar circle is contained and its defaults are horizontal Narrator Mode safe", () => {
  const bounds = avatarCircleBounds(NARRATOR_CANVAS.width, NARRATOR_CANVAS.height);
  assert.equal(bounds.right <= NARRATOR_CANVAS.width, true);
  assert.equal(bounds.bottom <= NARRATOR_CANVAS.height, true);
  assert.throws(() => avatarCircleBounds(100, 100, { x: 80, y: 0, size: 30 }), /inside/);
});

test("Santa face pack contains only facial layers and uses head-local hierarchy", () => {
  const pack = createNarratorAvatarPack();
  assert.deepEqual(pack.layers.map((layer) => layer.id), ["hair_back", "neck", "head", "hair_front", "eyes", "eyelids", "brows", "glasses", "beard", "mouth"]);
  assert.equal(pack.layers.some((layer) => ["left_hand", "right_hand", "torso"].includes(layer.id)), false);
  assert.equal(pack.layers.find((layer) => layer.id === "neck").parent, null);
  assert.equal(pack.layers.find((layer) => layer.id === "head").parent, "neck");
});

test("facial motion is deterministic and mouth follows RMS only while playing", () => {
  assert.deepEqual(facialPoseAt(1800, 0.72, true), facialPoseAt(1800, 0.72, true));
  assert.equal(facialPoseAt(1800, 0.72, true).mouth_open, 0.72);
  assert.equal(facialPoseAt(1800, 0.72, false).mouth_open, 0);
  assert.ok(facialPoseAt(4300, 0, true).eye_open < 1);
});

test("descriptor exposes real segment timing and horizontal export geometry", () => {
  const descriptor = createNarratorModeDescriptor(manifest);
  assert.equal(descriptor.format, "fabuloom.narrator-mode/0.1");
  assert.deepEqual(descriptor.canvas, { width: 1920, height: 1080 });
  assert.equal(descriptor.timingSource, "measured_wav_segments");
  assert.equal(descriptor.wordTiming, "unavailable");
});

