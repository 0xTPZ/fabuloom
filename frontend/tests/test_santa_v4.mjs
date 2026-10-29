import assert from "node:assert/strict";
import test from "node:test";
import { existsSync, readFileSync } from "node:fs";
import { buildLayerDrawPlan } from "../src/layered-character.ts";
import { validateCharacterPack } from "../src/character-pack.mjs";
import { SANTA_V4_PACK, SantaV4Rig } from "../src/santa-v4-engine.ts";

test("Santa V4 is a validated cartoon pack with independent illustrated layers", () => {
  assert.equal(validateCharacterPack(SANTA_V4_PACK), SANTA_V4_PACK);
  assert.equal(SANTA_V4_PACK.format, "fabuloom.character/0.1");
  assert.equal(SANTA_V4_PACK.voice_id, "pm_santa");
  assert.equal(SANTA_V4_PACK.language, "pt-BR");
  for (const role of ["torso", "pelvis", "neck", "head", "hair_front", "hair_back", "eyes", "eyelids", "brows", "mouth", "upper_arm", "forearm", "hand", "upper_leg", "lower_leg", "foot", "accessory"]) {
    assert.ok(SANTA_V4_PACK.layers.some((layer) => layer.role === role), `missing role ${role}`);
  }
  assert.ok(SANTA_V4_PACK.layers.some((layer) => layer.id === "head" && layer.parent === "neck"));
  assert.ok(SANTA_V4_PACK.layers.some((layer) => layer.id === "glasses" && layer.parent === "head"));
  assert.ok(SANTA_V4_PACK.layers.some((layer) => layer.id === "beard" && layer.parent === "head"));
  for (const layer of SANTA_V4_PACK.layers) {
    const path = new URL(`../${layer.asset}`, import.meta.url);
    assert.equal(existsSync(path), true, `missing asset ${layer.asset}`);
    assert.match(readFileSync(path, "utf8"), /^<svg\s/);
  }
});

test("Santa V4 keeps head, torso, arms, and hands independently transformable", () => {
  const rig = new SantaV4Rig();
  rig.setSceneDuration(30000);
  rig.setSpeechAmplitude(0.7);
  const base = rig.poseAt(14000, true);
  const gesture = rig.poseAt(15000, true);
  assert.notEqual(base.right_arm_rotation, gesture.right_arm_rotation);
  assert.notEqual(base.left_arm_rotation, gesture.left_arm_rotation);
  assert.notEqual(base.right_hand_rotation, gesture.right_hand_rotation);
  assert.equal(rig.poseAt(23000, false).mouth_open, 0);
  assert.equal(rig.poseAt(23000, true).mouth_open, 0.7);
  const still = buildLayerDrawPlan(SANTA_V4_PACK, 680, 1140, base, new Map());
  const turned = buildLayerDrawPlan(SANTA_V4_PACK, 680, 1140, { ...base, head_rotation: 0.2 });
  const torso = (plan) => plan.find((entry) => entry.layer.id === "torso");
  const head = (plan) => plan.find((entry) => entry.layer.id === "head");
  assert.equal(torso(still).matrix.b, torso(turned).matrix.b);
  assert.notEqual(head(still).matrix.b, head(turned).matrix.b);
});
