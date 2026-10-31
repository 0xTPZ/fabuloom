import assert from "node:assert/strict";
import test from "node:test";
import {
  adjustNarratorFaceCrop,
  NARRATOR_CANVAS,
  NARRATOR_FACE_CROP,
  NARRATOR_FACE_ALPHA_TARGETS,
  NARRATOR_FACE_ALPHA_BOUNDS,
  NARRATOR_FACE_REFERENCE,
  NARRATOR_FACE_SAFE_AREA,
  avatarCircleBounds,
  createNarratorAvatarPack,
  createNarratorModeDescriptor,
  createNarratorTimeline,
  faceSafeAreaForCrop,
  facialPoseAt,
  mouthStateAt,
  NarratorFacialRig,
  segmentAt,
  validateNarratorFaceCrop,
  validateNarratorFaceSafeArea,
  validateNarratorManifest,
} from "../src/narrator-mode.mjs";
import { buildLayerDrawPlan, LayeredCharacterRenderer } from "../src/layered-character.ts";

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

test("facial crop and safe area are square, bounded and deterministic", () => {
  assert.deepEqual(NARRATOR_FACE_CROP, { x: 245, y: 35, width: 590, height: 590 });
  assert.deepEqual(validateNarratorFaceCrop(NARRATOR_FACE_CROP), NARRATOR_FACE_CROP);
  assert.deepEqual(validateNarratorFaceSafeArea(NARRATOR_FACE_SAFE_AREA), NARRATOR_FACE_SAFE_AREA);
  const safe = faceSafeAreaForCrop();
  assert.ok(safe.left > NARRATOR_FACE_CROP.x && safe.top > NARRATOR_FACE_CROP.y);
  assert.ok(safe.right < NARRATOR_FACE_CROP.x + NARRATOR_FACE_CROP.width);
  assert.ok(safe.bottom < NARRATOR_FACE_CROP.y + NARRATOR_FACE_CROP.height);
  assert.throws(() => validateNarratorFaceCrop({ x: 0, y: 0, width: 500, height: 480 }), /square/);
  assert.throws(() => validateNarratorFaceCrop({ x: 600, y: 0, width: 600, height: 600 }), /source canvas/);
  const adjusted = adjustNarratorFaceCrop(NARRATOR_FACE_CROP, { offsetX: 24, offsetY: -18, zoom: 1.12 });
  assert.deepEqual(adjusted, adjustNarratorFaceCrop(NARRATOR_FACE_CROP, { offsetX: 24, offsetY: -18, zoom: 1.12 }));
  assert.equal(adjusted.width, adjusted.height);
  assert.ok(adjusted.x >= 0 && adjusted.y >= 0);
});

test("Santa face pack contains only facial layers and uses head-local hierarchy", () => {
  const pack = createNarratorAvatarPack();
  assert.deepEqual(pack.layers.map((layer) => layer.id), ["hair_back", "neck", "head", "hair_front", "eyes", "eyelids", "brows", "glasses", "beard", "mouth"]);
  assert.equal(pack.layers.some((layer) => ["left_hand", "right_hand", "torso"].includes(layer.id)), false);
  assert.equal(pack.layers.find((layer) => layer.id === "neck").parent, null);
  assert.equal(pack.layers.find((layer) => layer.id === "head").parent, "neck");
  assert.equal(pack.layers.find((layer) => layer.id === "beard").opacity, 0);
  const aligned = pack.layers.filter((layer) => Object.hasOwn(NARRATOR_FACE_ALPHA_TARGETS, layer.id));
  assert.deepEqual(aligned.map((layer) => layer.id), ["hair_front", "eyes", "eyelids", "brows", "glasses", "mouth"]);
  for (const layer of aligned) {
    assert.equal(layer.face_coordinate_system, NARRATOR_FACE_REFERENCE.coordinateSystem);
    assert.deepEqual(layer.face_alpha_target, NARRATOR_FACE_ALPHA_TARGETS[layer.id]);
    assert.ok(layer.size.every((value) => value > 0));
  }
  assert.deepEqual(NARRATOR_FACE_ALPHA_BOUNDS["eyes-open.png"], [196, 279, 1579, 627]);
  assert.ok(pack.layers.find((layer) => layer.id === "mouth").size[1] > 0.5);
});

test("facial motion is deterministic and mouth follows RMS only while playing", () => {
  assert.deepEqual(facialPoseAt(1800, 0.72, true), facialPoseAt(1800, 0.72, true));
  assert.equal(facialPoseAt(1800, 0.72, true).mouth_open, 0.72);
  assert.equal(facialPoseAt(1800, 0.72, false).mouth_open, 0);
  assert.ok(facialPoseAt(4300, 0, true).eye_open < 1);
});

test("NarratorFacialRig feeds the actual draw plan and exposes explicit mouth states", () => {
  const pack = createNarratorAvatarPack();
  const rig = new NarratorFacialRig();
  rig.setSpeechAmplitude(0.82);
  rig.update(4330, true);
  const pose = rig.pose();
  const plan = buildLayerDrawPlan(pack, 1080, 1920, pose);
  const head = plan.find((entry) => entry.layer.id === "head");
  const eyelids = plan.find((entry) => entry.layer.id === "eyelids");
  const mouth = plan.find((entry) => entry.layer.id === "mouth");
  assert.equal(pose.mouth_open, 0.82);
  assert.ok(pose.eye_open < 1);
  assert.ok(Math.abs(head.matrix.b) > 0);
  assert.equal(eyelids.opacity, 1);
  assert.ok(mouth.drawHeight > 0);
  assert.equal(mouthStateAt(0, true), "closed");
  assert.equal(mouthStateAt(0.2, true), "slight");
  assert.equal(mouthStateAt(0.5, true), "moderate");
  assert.equal(mouthStateAt(0.9, true), "open");

  const canvas = { width: 1080, height: 1920, getContext: () => ({}) };
  const renderer = new LayeredCharacterRenderer(canvas, rig, pack, {
    assetResolver: (layer, currentPose, expressionAsset) => layer.id === "mouth" && currentPose.mouth_open >= 0.34
      ? "assets/characters/topazio-narrators-v5/santa/mouth-open.png"
      : expressionAsset,
  });
  assert.equal(renderer.resolvedAsset(pack.layers.find((layer) => layer.id === "mouth")), "assets/characters/topazio-narrators-v5/santa/mouth-open.png");
});

test("descriptor exposes real segment timing and horizontal export geometry", () => {
  const descriptor = createNarratorModeDescriptor(manifest);
  assert.equal(descriptor.format, "fabuloom.narrator-mode/0.1");
  assert.deepEqual(descriptor.canvas, { width: 1920, height: 1080 });
  assert.equal(descriptor.timingSource, "measured_wav_segments");
  assert.equal(descriptor.wordTiming, "unavailable");
});

