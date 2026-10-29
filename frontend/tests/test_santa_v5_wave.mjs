import assert from "node:assert/strict";
import { test } from "node:test";

import { buildLayerDrawPlan } from "../src/layered-character.ts";
import { resolveLandmarks } from "../src/character-landmarks.mjs";
import { SANTA_V5_ANATOMICAL_LANDMARKS } from "../src/santa-v5-calibration.mjs";
import { SANTA_V5_ANIMATION_LIBRARY, SANTA_V5_WAVE_HELLO_CLIP, SantaV5Rig } from "../src/santa-v5-engine.ts";
import { SANTA_V5_PACK } from "../src/santa-v5-pack.mjs";

const sizes = new Map(SANTA_V5_PACK.layers.map((layer) => [layer.asset, [1024, 1536]]));

test("WAVE_HELLO is a reusable validated keyframe clip", () => {
  assert.equal(SANTA_V5_WAVE_HELLO_CLIP.id, "WAVE_HELLO");
  assert.equal(SANTA_V5_WAVE_HELLO_CLIP.durationMs, 4600);
  assert.equal(typeof SANTA_V5_ANIMATION_LIBRARY.WAVE_HELLO.sample, "function");
  assert.deepEqual(SANTA_V5_ANIMATION_LIBRARY.WAVE_HELLO.sample(0), SANTA_V5_ANIMATION_LIBRARY.WAVE_HELLO.sample(0));
});

test("WAVE_HELLO coordinates shoulder, elbow, wrist/hand and head with bounded values", () => {
  const rig = new SantaV5Rig(); rig.setSceneDuration(20450); rig.setAnimation("WAVE_HELLO");
  const samples = [0, 320, 1180, 1680, 2120, 2560, 3000, 3560, 4600].map((timeMs) => rig.poseAt(timeMs, false));
  assert.equal(samples[0].right_arm_rotation, 0);
  assert.ok(samples[2].right_arm_rotation > 0.5);
  assert.ok(samples[4].right_hand_rotation > 0.15);
  assert.ok(samples[5].right_hand_rotation < -0.1);
  assert.ok(Math.abs(samples[4].head_rotation) < 0.1);
  assert.ok(Math.abs(samples[4].right_arm_rotation) <= 1.12);
  assert.ok(Math.abs(samples[4].right_forearm_rotation) <= 1.32);
  assert.equal(samples.at(-1).right_arm_rotation, 0);
  assert.equal(samples.at(-1).right_hand_rotation, 0);
});

test("WAVE_HELLO keeps joints deterministic and reasonably continuous after seeks", () => {
  const rig = new SantaV5Rig(); rig.setSceneDuration(20450); rig.setAnimation("WAVE_HELLO");
  const first = rig.poseAt(2120, false);
  rig.poseAt(4000, false);
  const afterSeek = rig.poseAt(2120, false);
  assert.deepEqual(afterSeek, first);
  for (const timeMs of [0, 320, 1180, 1680, 2120, 2560, 3000, 3560, 4600]) {
    const pose = rig.poseAt(timeMs, false);
    assert.ok(Object.values(pose).filter((value) => typeof value === "number").every(Number.isFinite));
  }
  const previous = rig.poseAt(2110, false); const next = rig.poseAt(2130, false);
  assert.ok(Math.abs(next.right_hand_rotation - previous.right_hand_rotation) < 0.1);
  assert.ok(Math.abs(next.right_arm_rotation - previous.right_arm_rotation) < 0.1);
});

test("WAVE_HELLO preserves breathing and RMS mouth composition", () => {
  const rig = new SantaV5Rig(); rig.setSceneDuration(20450); rig.setAnimation("WAVE_HELLO"); rig.setSpeechAmplitude(0.7);
  const speaking = rig.poseAt(2120, true); const paused = rig.poseAt(2120, false);
  assert.ok(speaking.breathing >= 0 && speaking.breathing <= 1);
  assert.ok(speaking.mouth_open > 0);
  assert.equal(paused.mouth_open, 0);
  assert.equal(speaking.right_hand_rotation, paused.right_hand_rotation);
});

test("WAVE_HELLO moves the transformed hand while retaining the landmark hierarchy", () => {
  const rig = new SantaV5Rig(); rig.setSceneDuration(20450); rig.setAnimation("WAVE_HELLO");
  const atRest = buildLayerDrawPlan(SANTA_V5_PACK, 680, 1550, rig.poseAt(0, false), sizes);
  const atWave = buildLayerDrawPlan(SANTA_V5_PACK, 680, 1550, rig.poseAt(2120, false), sizes);
  const restLandmarks = resolveLandmarks(SANTA_V5_ANATOMICAL_LANDMARKS, atRest);
  const waveLandmarks = resolveLandmarks(SANTA_V5_ANATOMICAL_LANDMARKS, atWave);
  const restHand = restLandmarks.find((landmark) => landmark.id === "rightWrist").stage;
  const waveHand = waveLandmarks.find((landmark) => landmark.id === "rightWrist").stage;
  assert.ok(Math.hypot(waveHand.x - restHand.x, waveHand.y - restHand.y) > 20);
  assert.ok(waveLandmarks.every((landmark) => Number.isFinite(landmark.stage.x) && Number.isFinite(landmark.stage.y)));
});
