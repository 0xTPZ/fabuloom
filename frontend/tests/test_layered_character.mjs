import assert from "node:assert/strict";
import test from "node:test";
import { FANTASY_NARRATOR_PACK } from "../src/fantasy-narrator-pack.mjs";
import { validateCharacterPack } from "../src/character-pack.mjs";
import { buildLayerDrawPlan, LayeredCharacterRig } from "../src/layered-character.ts";

test("fantasy narrator pack validates and resolves layered transforms", () => {
  validateCharacterPack(FANTASY_NARRATOR_PACK);
  const rig = new LayeredCharacterRig();
  rig.update(1000, false);
  const sizes = new Map([
    ["assets/characters/fantasy-narrator/portrait.png", [1145, 1374]],
    ["assets/characters/fantasy-narrator/eyes.svg", [320, 90]],
    ["assets/characters/fantasy-narrator/mouth.svg", [200, 100]],
    ["assets/characters/fantasy-narrator/breath.svg", [420, 260]],
  ]);
  const plan = buildLayerDrawPlan(FANTASY_NARRATOR_PACK, 960, 540, rig.pose(), sizes);
  assert.equal(plan.length, 4);
  assert.deepEqual(plan.map((entry) => entry.layer.id), ["portrait", "eyes", "mouth", "breath"]);
  for (const entry of plan) {
    for (const value of Object.values(entry.matrix)) assert.ok(Number.isFinite(value));
  }
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
