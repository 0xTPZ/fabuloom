import assert from "node:assert/strict";
import { test } from "node:test";

import { buildLayerDrawPlan } from "../src/layered-character.ts";
import { resolveLandmarks, transformPoint, validateLandmarks } from "../src/character-landmarks.mjs";
import { diagnoseSantaV5Calibration, SANTA_V5_ANATOMICAL_LANDMARKS } from "../src/santa-v5-calibration.mjs";
import { SantaV5Rig } from "../src/santa-v5-engine.ts";
import { SANTA_V5_PACK } from "../src/santa-v5-pack.mjs";

const sizes = new Map([
  ["assets/characters/topazio-narrators-v5/santa/hair-back.png", [1246, 1263]],
  ["assets/characters/topazio-narrators-v5/santa/foot-left.png", [1230, 1278]],
  ["assets/characters/topazio-narrators-v5/santa/foot-right.png", [1199, 1312]],
  ["assets/characters/topazio-narrators-v5/santa/shin-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/shin-right.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/pelvis.png", [1261, 1247]],
  ["assets/characters/topazio-narrators-v5/santa/thigh-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/thigh-right.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/torso.png", [1139, 1381]],
  ["assets/characters/topazio-narrators-v5/santa/upper-arm-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/upper-arm-right.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/forearm-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/forearm-right.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/hand-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/hand-right.png", [1151, 1366]],
  ["assets/characters/topazio-narrators-v5/santa/neck.png", [1536, 1024]],
  ["assets/characters/topazio-narrators-v5/santa/head.png", [1316, 1195]],
  ["assets/characters/topazio-narrators-v5/santa/hair-front.png", [1536, 1024]],
  ["assets/characters/topazio-narrators-v5/santa/eyes-open.png", [1774, 887]],
  ["assets/characters/topazio-narrators-v5/santa/eyelids-closed.png", [1851, 850]],
  ["assets/characters/topazio-narrators-v5/santa/brows.png", [1774, 887]],
  ["assets/characters/topazio-narrators-v5/santa/glasses.png", [1316, 1195]],
  ["assets/characters/topazio-narrators-v5/santa/beard.png", [1316, 1195]],
  ["assets/characters/topazio-narrators-v5/santa/mouth-closed.png", [1536, 1024]],
  ["assets/characters/topazio-narrators-v5/santa/mouth-open.png", [1316, 1195]],
]);

const durationMs = 20450;

test("Santa V5 pack passes calibration invariants", () => {
  const report = diagnoseSantaV5Calibration(SANTA_V5_PACK, sizes);
  assert.equal(report.ok, true, report.errors.join("; "));
  const landmarks = validateLandmarks(SANTA_V5_ANATOMICAL_LANDMARKS, new Set(SANTA_V5_PACK.layers.map((layer) => layer.id)));
  assert.equal(landmarks.ok, true, landmarks.errors.join("; "));
});

test("anatomical landmarks convert from intrinsic layer space to stage space", () => {
  const rig = new SantaV5Rig(); rig.setSceneDuration(durationMs); rig.update(0, false);
  const plans = buildLayerDrawPlan(SANTA_V5_PACK, 1080, 1920, rig.pose(), sizes);
  const resolved = resolveLandmarks(SANTA_V5_ANATOMICAL_LANDMARKS, plans);
  assert.equal(resolved.length, 12);
  assert.ok(resolved.every((landmark) => Number.isFinite(landmark.stage.x) && Number.isFinite(landmark.stage.y)));
  const leftShoulder = resolved.find((landmark) => landmark.id === "leftShoulder").stage;
  const rightShoulder = resolved.find((landmark) => landmark.id === "rightShoulder").stage;
  assert.ok(leftShoulder.x < rightShoulder.x);
  assert.ok(leftShoulder.y > 0 && rightShoulder.y < 1920);
  const pivotLayer = { leftShoulder: "left_upper_arm", rightShoulder: "right_upper_arm", leftElbow: "left_forearm", rightElbow: "right_forearm", leftWrist: "left_hand", rightWrist: "right_hand", leftKnee: "left_shin", rightKnee: "right_shin", leftAnkle: "left_foot", rightAnkle: "right_foot" };
  for (const landmark of resolved) {
    const layerId = pivotLayer[landmark.id]; if (!layerId) continue;
    const plan = plans.find((entry) => entry.layer.id === layerId);
    const pivot = transformPoint(plan.matrix, plan.layer.anchor[0] * plan.intrinsic[0], plan.layer.anchor[1] * plan.intrinsic[1]);
    assert.ok(Math.hypot(pivot.x - landmark.stage.x, pivot.y - landmark.stage.y) < 80, `${landmark.id} pivot is too far from its landmark`);
  }
});

test("Santa V5 constrains painted-rig extremes by action", () => {
  const rig = new SantaV5Rig();
  rig.setSceneDuration(durationMs);
  const poses = [0, 1800, 5000, 7200, 9600, 15000, 18000].map((timeMs) => ({ timeMs, pose: rig.poseAt(timeMs, true) }));
  const walk = poses.find(({ timeMs }) => timeMs === 1800).pose;
  const reach = poses.find(({ timeMs }) => timeMs === 7200).pose;
  const explain = poses.find(({ timeMs }) => timeMs === 18000).pose;
  assert.ok(Math.abs(walk.left_thigh_rotation) <= 0.19);
  assert.ok(Math.abs(walk.left_shin_rotation) <= 0.14);
  assert.ok(Math.abs(reach.right_arm_rotation) <= 1.02);
  assert.ok(Math.abs(reach.right_forearm_rotation) <= 0.94);
  assert.ok(Math.abs(explain.left_arm_rotation) <= 0.34);
  assert.ok(Math.abs(explain.right_arm_rotation) <= 0.34);
  assert.ok(Math.abs(poses.find(({ timeMs }) => timeMs === 1800).pose.pelvis_x) <= 0.012);
  assert.ok(Math.abs(poses.find(({ timeMs }) => timeMs === 1800).pose.left_foot_x) <= 0.006);
  assert.ok(Math.abs(poses.find(({ timeMs }) => timeMs === 5000).pose.left_thigh_rotation) <= 0.36);
});

test("Santa V5 transitions remain bounded around walk and seated boundaries", () => {
  const rig = new SantaV5Rig(); rig.setSceneDuration(durationMs);
  const samples = [3200, 3300, 5850, 6000].map((timeMs) => rig.poseAt(timeMs, true));
  assert.ok(Math.abs(samples[1].left_thigh_rotation - samples[0].left_thigh_rotation) < 0.5);
  assert.ok(Math.abs(samples[1].left_shin_rotation - samples[0].left_shin_rotation) < 0.6);
  assert.ok(Math.abs(samples[3].left_thigh_rotation - samples[2].left_thigh_rotation) < 0.5);
  assert.ok(samples.every((pose) => Object.values(pose).filter((value) => typeof value === "number").every(Number.isFinite)));
});

test("Santa V5 draw plans are deterministic and preserve independent joints", () => {
  const rig = new SantaV5Rig();
  rig.setSceneDuration(durationMs);
  rig.setSpeechAmplitude(0.6);
  rig.update(7200, true);
  const first = buildLayerDrawPlan(SANTA_V5_PACK, 1080, 1920, rig.pose(), sizes);
  rig.update(7200, true);
  const second = buildLayerDrawPlan(SANTA_V5_PACK, 1080, 1920, rig.pose(), sizes);
  assert.deepEqual(first, second);
  const head = first.find((entry) => entry.layer.id === "head");
  const torso = first.find((entry) => entry.layer.id === "torso");
  const hand = first.find((entry) => entry.layer.id === "right_hand");
  assert.notDeepEqual(head.matrix, torso.matrix);
  assert.notDeepEqual(hand.matrix, torso.matrix);
  assert.ok(first.every((entry) => Object.values(entry.matrix).every(Number.isFinite)));
});
