import assert from "node:assert/strict";
import test from "node:test";
import { existsSync, readFileSync } from "node:fs";
import { buildLayerDrawPlan } from "../src/layered-character.ts";
import { validateCharacterPack } from "../src/character-pack.mjs";
import { SANTA_V3_PACK } from "../src/santa-v3-pack.mjs";
import { SANTA_V3_ANIMATION_FORMAT, SANTA_V3_ANIMATION_LIBRARY, SantaV3Rig, santaV3SceneAt } from "../src/santa-v3-engine.ts";

test("Santa V3 is a validated full-body pack with independent joints", () => {
  assert.equal(validateCharacterPack(SANTA_V3_PACK), SANTA_V3_PACK);
  assert.equal(SANTA_V3_PACK.format, "fabuloom.character/0.1");
  assert.equal(SANTA_V3_PACK.voice_id, "pm_santa");
  for (const role of ["torso", "pelvis", "neck", "head", "hair_front", "hair_back", "eyes", "eyelids", "brows", "mouth", "upper_arm", "forearm", "hand", "upper_leg", "lower_leg", "foot"]) {
    assert.ok(SANTA_V3_PACK.layers.some((layer) => layer.role === role), `missing role ${role}`);
  }
  assert.ok(SANTA_V3_PACK.layers.some((layer) => layer.id === "head" && layer.parent === "neck"));
  assert.ok(SANTA_V3_PACK.layers.some((layer) => layer.id === "neck" && layer.parent === "torso"));
  for (const layer of SANTA_V3_PACK.layers) {
    const path = new URL(`../${layer.asset}`, import.meta.url);
    assert.equal(existsSync(path), true, `missing asset ${layer.asset}`);
    assert.match(readFileSync(path, "utf8"), /^<svg\s/);
  }
});

test("Santa V3 clip library contains the required actions and facial clips", () => {
  for (const name of ["idle", "walk", "sit", "stand_up", "talk", "explain", "reach", "hold_object", "drink", "read_book", "blink", "look_left", "look_right", "smile", "talk_mouth", "eyebrow_raise"]) {
    assert.equal(typeof SANTA_V3_ANIMATION_LIBRARY[name]?.sample, "function", name);
    assert.ok(SANTA_V3_ANIMATION_LIBRARY[name].durationMs > 0);
  }
  assert.equal(SANTA_V3_ANIMATION_FORMAT, "fabuloom.animation/0.1");
});

test("Santa V3 scene is one deterministic continuous shot", () => {
  const duration = 30000;
  const actions = [0, 5000, 9000, 13000, 19000, 22000, 29000].map((time) => santaV3SceneAt(time, duration).action);
  assert.deepEqual(actions, ["walk", "sit", "reach", "drink", "read_book", "read_book", "explain"]);
  assert.equal(santaV3SceneAt(0, duration).characterX < santaV3SceneAt(6000, duration).characterX, true);
  assert.equal(santaV3SceneAt(14000, duration).cupState, "held");
  assert.equal(santaV3SceneAt(28000, duration).action, "explain");
});

test("Santa V3 keeps head independent from torso and exposes visible arm gestures", () => {
  const rig = new SantaV3Rig();
  rig.setSceneDuration(30000);
  rig.setSpeechAmplitude(0.7);
  const walk = rig.poseAt(2000, true);
  const explainA = rig.poseAt(23000, true);
  const explainB = rig.poseAt(25000, true);
  assert.notEqual(walk.left_thigh_rotation, walk.right_thigh_rotation);
  assert.notEqual(explainA.right_arm_rotation, explainB.right_arm_rotation);
  assert.notEqual(explainA.left_arm_rotation, explainB.left_arm_rotation);
  assert.equal(rig.poseAt(23000, false).mouth_open, 0);
  assert.equal(rig.poseAt(23000, true).mouth_open, 0.7);
  const stillPose = rig.poseAt(23000, true);
  const still = buildLayerDrawPlan(SANTA_V3_PACK, 680, 1140, stillPose, new Map());
  const turned = buildLayerDrawPlan(SANTA_V3_PACK, 680, 1140, { ...stillPose, head_rotation: 0.2 });
  const torso = (plan) => plan.find((entry) => entry.layer.id === "torso");
  const head = (plan) => plan.find((entry) => entry.layer.id === "head");
  assert.equal(torso(still).matrix.b, torso(turned).matrix.b);
  assert.notEqual(head(still).matrix.b, head(turned).matrix.b);
});
