import assert from "node:assert/strict";
import test from "node:test";
import { existsSync, readFileSync } from "node:fs";
import { validateCharacterPack } from "../src/character-pack.mjs";
import { SANTA_V5_PACK } from "../src/santa-v5-pack.mjs";

test("Santa V5 production preview pack validates its original local assets", () => {
  assert.equal(validateCharacterPack(SANTA_V5_PACK), SANTA_V5_PACK);
  assert.equal(SANTA_V5_PACK.voice_id, "pm_santa");
  assert.equal(SANTA_V5_PACK.language, "pt-BR");
  assert.equal(SANTA_V5_PACK.art_status, "production-art-preview");
  for (const role of ["torso", "pelvis", "head", "upper_arm", "upper_leg"]) {
    assert.ok(SANTA_V5_PACK.layers.some((layer) => layer.role === role), `missing role ${role}`);
  }
  for (const layer of SANTA_V5_PACK.layers) {
    const path = new URL(`../${layer.asset}`, import.meta.url);
    assert.equal(existsSync(path), true, `missing asset ${layer.asset}`);
    assert.equal(readFileSync(path).subarray(0, 8).toString("hex"), "89504e470d0a1a0a", `not a PNG: ${layer.asset}`);
  }
});

test("Santa V5 preview keeps the production hierarchy explicit", () => {
  const torso = SANTA_V5_PACK.layers.find((layer) => layer.id === "torso");
  const head = SANTA_V5_PACK.layers.find((layer) => layer.id === "head");
  const pelvis = SANTA_V5_PACK.layers.find((layer) => layer.id === "pelvis");
  assert.equal(torso.parent, null);
  assert.equal(head.parent, "torso");
  assert.equal(pelvis.parent, "torso");
  assert.equal(SANTA_V5_PACK.layers.filter((layer) => layer.parent === "torso").length, 4);
});
