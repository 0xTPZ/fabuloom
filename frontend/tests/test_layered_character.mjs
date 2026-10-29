import assert from "node:assert/strict";
import test from "node:test";
import { FANTASY_NARRATOR_PACK } from "../src/fantasy-narrator-pack.mjs";
import { validateCharacterPack } from "../src/character-pack.mjs";
import { buildLayerDrawPlan, frameSchedule, LayeredCharacterRig } from "../src/layered-character.ts";

test("fantasy narrator pack validates and resolves layered transforms", () => {
  validateCharacterPack(FANTASY_NARRATOR_PACK);
  const rig = new LayeredCharacterRig();
  rig.update(1000, false);
  const sizes = new Map([
    ["assets/characters/fantasy-narrator/torso-core.png", [1145, 1374]],
    ["assets/characters/fantasy-narrator/head.png", [1145, 1374]],
    ["assets/characters/fantasy-narrator/eyes.svg", [320, 90]],
    ["assets/characters/fantasy-narrator/eyelids.svg", [320, 90]],
    ["assets/characters/fantasy-narrator/brows.svg", [320, 90]],
    ["assets/characters/fantasy-narrator/mouth.svg", [200, 100]],
  ]);
  const plan = buildLayerDrawPlan(FANTASY_NARRATOR_PACK, 960, 540, rig.pose(), sizes);
  assert.equal(plan.length, 16);
  assert.deepEqual(plan.map((entry) => entry.layer.id), [
    "torso", "neck", "left_upper_arm", "right_upper_arm", "left_forearm", "right_forearm",
    "left_hand", "right_hand", "hair_back", "head", "eyes", "eyelids", "brows", "mouth",
    "hair_front", "accessory_pendant",
  ]);
  for (const entry of plan) {
    for (const value of Object.values(entry.matrix)) assert.ok(Number.isFinite(value));
  }
});

test("head rotation is isolated from the torso and inherited by facial parts", () => {
  const rig = new LayeredCharacterRig();
  const still = buildLayerDrawPlan(FANTASY_NARRATOR_PACK, 960, 540, {
    breathing: 0.5, head_rotation: 0, eye_open: 1, mouth_open: 0, hair_sway: 0,
    brow_raise: 0, left_arm: 0, right_arm: 0,
  });
  const turned = buildLayerDrawPlan(FANTASY_NARRATOR_PACK, 960, 540, {
    breathing: 0.5, head_rotation: 0.12, eye_open: 1, mouth_open: 0, hair_sway: 0,
    brow_raise: 0, left_arm: 0, right_arm: 0,
  });
  const find = (plans, id) => plans.find((entry) => entry.layer.id === id);
  assert.equal(find(still, "torso").matrix.b, 0);
  assert.equal(find(still, "torso").matrix.c, 0);
  assert.equal(find(turned, "torso").matrix.b, 0);
  assert.equal(find(turned, "torso").matrix.c, 0);
  assert.notEqual(find(still, "head").matrix.b, find(turned, "head").matrix.b);
  assert.notEqual(find(still, "mouth").matrix.b, find(turned, "mouth").matrix.b);
});

test("anatomical rig exposes independent arm, hair and brow bindings", () => {
  const ids = new Set(FANTASY_NARRATOR_PACK.layers.map((layer) => layer.id));
  for (const id of ["left_upper_arm", "left_forearm", "left_hand", "right_upper_arm", "right_forearm", "right_hand", "hair_back", "hair_front", "brows", "neck"]) {
    assert.ok(ids.has(id), `missing anatomical layer ${id}`);
  }
  assert.equal(FANTASY_NARRATOR_PACK.bindings.head_rotation, "head");
  assert.equal(FANTASY_NARRATOR_PACK.bindings.breathing, "torso");
  assert.equal(FANTASY_NARRATOR_PACK.bindings.hair_sway, "hair_front");
  assert.equal(FANTASY_NARRATOR_PACK.bindings.brow_raise, "brows");
  assert.equal(FANTASY_NARRATOR_PACK.layers.find((layer) => layer.id === "head").parent, "neck");
  assert.equal(FANTASY_NARRATOR_PACK.layers.find((layer) => layer.id === "hair_back").parent, "head");
});

test("layered rig keeps speech amplitude independent from provider", () => {
  const rig = new LayeredCharacterRig();
  rig.setSpeechAmplitude(0.72);
  rig.update(1000, true);
  assert.equal(rig.pose().mouth_open, 0.72);
  rig.update(1000, false);
  assert.equal(rig.pose().mouth_open, 0);
});

test("layered rig produces a blink and subtle secondary motion", () => {
  const rig = new LayeredCharacterRig();
  rig.update(4300, false);
  rig.update(4380, false);
  assert.ok(rig.pose().eye_open < 1);
  assert.notEqual(rig.pose().hair_sway, 0);
});

test("frame schedule is deterministic and bounded", () => {
  assert.deepEqual([...frameSchedule(1000, 10)], [
    { index: 0, timeMs: 0 },
    { index: 1, timeMs: 100 },
    { index: 2, timeMs: 200 },
    { index: 3, timeMs: 300 },
    { index: 4, timeMs: 400 },
    { index: 5, timeMs: 500 },
    { index: 6, timeMs: 600 },
    { index: 7, timeMs: 700 },
    { index: 8, timeMs: 800 },
    { index: 9, timeMs: 900 },
  ]);
  assert.throws(() => [...frameSchedule(-1, 30)], /non-negative/);
  assert.throws(() => [...frameSchedule(1000, 0)], /\[1,120\]/);
});
