import assert from "node:assert/strict";
import test from "node:test";
import { existsSync, readFileSync } from "node:fs";
import { buildLayerDrawPlan } from "../src/layered-character.ts";
import { validateCharacterPack } from "../src/character-pack.mjs";
import { SANTA_V5_PACK } from "../src/santa-v5-pack.mjs";
import { SantaV5Rig, SANTA_V5_ANIMATION_LIBRARY } from "../src/santa-v5-engine.ts";

test("Santa V5 final rig pack validates its fine-grained local assets", () => {
  assert.equal(validateCharacterPack(SANTA_V5_PACK), SANTA_V5_PACK);
  assert.equal(SANTA_V5_PACK.voice_id, "pm_santa");
  assert.equal(SANTA_V5_PACK.language, "pt-BR");
  assert.equal(SANTA_V5_PACK.art_status, "production-rig-v1");
  const headLayer = SANTA_V5_PACK.layers.find((layer) => layer.id === "head");
  assert.equal(headLayer.asset.endsWith("head-clean.png"), true);
  assert.equal(existsSync(new URL("../assets/characters/topazio-narrators-v5/santa/head-clean.png", import.meta.url)), true);
  assert.ok(SANTA_V5_PACK.expressions.some((expression) => expression.id === "wave" && expression.overrides.right_hand.endsWith("hand-right-wave.png")));
  assert.ok(SANTA_V5_PACK.expressions.some((expression) => expression.id === "point" && expression.overrides.right_hand.endsWith("hand-right-point.png")));
  assert.ok(SANTA_V5_PACK.expressions.some((expression) => expression.id === "point-left" && expression.overrides.left_hand.endsWith("hand-left-point.png")));
  for (const role of ["torso", "pelvis", "neck", "head", "hair_front", "hair_back", "eyes", "eyelids", "brows", "mouth", "upper_arm", "forearm", "hand", "upper_leg", "lower_leg", "foot", "accessory"]) {
    assert.ok(SANTA_V5_PACK.layers.some((layer) => layer.role === role), `missing role ${role}`);
  }
  for (const layer of SANTA_V5_PACK.layers) {
    const path = new URL(`../${layer.asset}`, import.meta.url);
    assert.equal(existsSync(path), true, `missing asset ${layer.asset}`);
    assert.equal(readFileSync(path).subarray(0, 8).toString("hex"), "89504e470d0a1a0a", `not a PNG: ${layer.asset}`);
  }
  const facialLayers = SANTA_V5_PACK.layers.filter((layer) => ["head", "eyes", "eyelids", "brows", "glasses", "beard", "mouth"].includes(layer.id));
  assert.equal(new Set(facialLayers.map((layer) => layer.asset)).size, facialLayers.length, "facial layers must not reuse the same painted asset");
  assert.equal(facialLayers.some((layer) => layer.id !== "head" && layer.asset === headLayer.asset), false, "clean head base must not be reused as a facial overlay");
});

test("Santa V5 wave expression keeps the original hand and adds a valid palm-facing asset", () => {
  const original = new URL("../assets/characters/topazio-narrators-v5/santa/hand-right.png", import.meta.url);
  const wave = new URL("../assets/characters/topazio-narrators-v5/santa/hand-right-wave.png", import.meta.url);
  assert.equal(existsSync(original), true);
  assert.equal(existsSync(wave), true);
  assert.equal(readFileSync(wave).subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  assert.equal(readFileSync(original).subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
});

test("Santa V5 point expression preserves the neutral and wave hand assets", () => {
  const original = new URL("../assets/characters/topazio-narrators-v5/santa/hand-right.png", import.meta.url);
  const wave = new URL("../assets/characters/topazio-narrators-v5/santa/hand-right-wave.png", import.meta.url);
  const point = new URL("../assets/characters/topazio-narrators-v5/santa/hand-right-point.png", import.meta.url);
  const leftPoint = new URL("../assets/characters/topazio-narrators-v5/santa/hand-left-point.png", import.meta.url);
  assert.equal(existsSync(original), true);
  assert.equal(existsSync(wave), true);
  assert.equal(existsSync(point), true);
  assert.equal(existsSync(leftPoint), true);
  assert.equal(readFileSync(point).subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  assert.equal(readFileSync(leftPoint).subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  assert.notEqual(readFileSync(point).length, readFileSync(original).length);
});

test("Santa V5 keeps the independent anatomical hierarchy explicit", () => {
  const parentOf = (id) => SANTA_V5_PACK.layers.find((layer) => layer.id === id)?.parent;
  assert.equal(parentOf("torso"), null);
  assert.equal(parentOf("pelvis"), "torso");
  assert.equal(parentOf("neck"), "torso");
  assert.equal(parentOf("head"), "neck");
  assert.equal(parentOf("left_forearm"), "left_upper_arm");
  assert.equal(parentOf("right_hand"), "right_forearm");
  assert.equal(parentOf("left_shin"), "left_thigh");
  assert.equal(parentOf("right_foot"), "right_shin");
  assert.equal(SANTA_V5_PACK.layers.filter((layer) => layer.parent === "head").length, 7);
});

test("Santa V5 reuses the complete animation catalogue and exposes visible pose channels", () => {
  for (const name of ["idle", "walk", "sit", "stand_up", "talk", "explain", "reach", "hold_object", "drink", "read_book", "blink", "look_left", "look_right", "smile", "talk_mouth", "eyebrow_raise"]) {
    assert.equal(typeof SANTA_V5_ANIMATION_LIBRARY[name]?.sample, "function", name);
  }
  const rig = new SantaV5Rig();
  rig.setSceneDuration(30000);
  rig.setSpeechAmplitude(0.8);
  const walking = rig.poseAt(1800, true);
  const explaining = rig.poseAt(24500, true);
  assert.notEqual(walking.left_thigh_rotation, walking.right_thigh_rotation);
  assert.notEqual(explaining.left_arm_rotation, explaining.right_arm_rotation);
  assert.ok(Math.abs(explaining.right_hand_rotation) > 0);
  assert.equal(rig.poseAt(24500, false).mouth_open, 0);
  assert.ok(rig.poseAt(24500, true).mouth_open > 0);
});

test("Santa V5 head and torso remain independently transformable", () => {
  const rig = new SantaV5Rig();
  rig.setSceneDuration(30000);
  const pose = rig.poseAt(24500, true);
  const still = buildLayerDrawPlan(SANTA_V5_PACK, 680, 1550, pose, new Map());
  const turned = buildLayerDrawPlan(SANTA_V5_PACK, 680, 1550, { ...pose, head_rotation: 0.2 });
  const wristTurned = buildLayerDrawPlan(SANTA_V5_PACK, 680, 1550, { ...pose, right_hand_rotation: pose.right_hand_rotation + 0.4 });
  const entry = (plan, id) => plan.find((item) => item.layer.id === id);
  assert.equal(entry(still, "torso").matrix.b, entry(turned, "torso").matrix.b);
  assert.notEqual(entry(still, "head").matrix.b, entry(turned, "head").matrix.b);
  assert.notEqual(entry(still, "right_hand").matrix.e, entry(wristTurned, "right_hand").matrix.e);
});

test("Santa V5 eyelid overlay is hidden when open and visible only while blinking", () => {
  const open = buildLayerDrawPlan(SANTA_V5_PACK, 680, 1550, { eye_open: 1 });
  const closed = buildLayerDrawPlan(SANTA_V5_PACK, 680, 1550, { eye_open: 0 });
  const partial = buildLayerDrawPlan(SANTA_V5_PACK, 680, 1550, { eye_open: 0.5 });
  const opacity = (plan) => plan.find((entry) => entry.layer.id === "eyelids").opacity;
  assert.equal(opacity(open), 0);
  assert.equal(opacity(closed), 1);
  assert.equal(opacity(partial), 0.5);
});
