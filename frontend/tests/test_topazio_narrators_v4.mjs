import assert from "node:assert/strict";
import test from "node:test";
import { existsSync } from "node:fs";
import { buildLayerDrawPlan, LayeredCharacterRig } from "../src/layered-character.ts";
import { validateCharacterPack } from "../src/character-pack.mjs";
import {
  ALEX_NARRATOR_PACK_V4,
  DORA_NARRATOR_PACK_V4,
  TOPAZIO_NARRATOR_PACKS_V4,
  TOPAZIO_NARRATOR_VISUAL_CONTRACT_V4,
} from "../src/topazio-narrator-packs-v4.mjs";

test("V4 Dora and Alex use the shared frontal visual contract", () => {
  assert.equal(TOPAZIO_NARRATOR_VISUAL_CONTRACT_V4.orientation, "frontal-bust");
  assert.equal(TOPAZIO_NARRATOR_VISUAL_CONTRACT_V4.quality_gate, "AWAITING_ART_APPROVAL");
  for (const [character, pack] of Object.entries(TOPAZIO_NARRATOR_PACKS_V4)) {
    assert.equal(validateCharacterPack(pack), pack);
    assert.equal(pack.language, "pt-BR");
    assert.match(pack.art_status, /art-reforge-v4-experimental-awaiting-art-approval/);
    assert.equal(pack.visual_contract, TOPAZIO_NARRATOR_VISUAL_CONTRACT_V4.format);
    assert.deepEqual(pack.layers.map((layer) => layer.id), ["head", "eyelids", "mouth"]);
    assert.equal(pack.layers.find((layer) => layer.id === "eyelids").parent, "head");
    assert.equal(pack.layers.find((layer) => layer.id === "mouth").parent, "head");
    assert.deepEqual(Object.keys(pack.facial_states.mouth), ["closed", "slight", "moderate", "open", "smile"]);
    const assets = new Set([
      ...pack.layers.map((layer) => layer.asset),
      ...Object.values(pack.facial_states.mouth),
      ...pack.expressions.flatMap((expression) => Object.values(expression.overrides)),
    ]);
    for (const asset of assets) assert.equal(existsSync(new URL(`../${asset}`, import.meta.url)), true, `${character}: ${asset}`);
  }
  assert.equal(DORA_NARRATOR_PACK_V4.voice_id, "pf_dora");
  assert.equal(ALEX_NARRATOR_PACK_V4.voice_id, "pm_alex");
});

test("V4 facial plates use explicit head-local transforms and deterministic poses", () => {
  const rig = new LayeredCharacterRig();
  rig.setSpeechAmplitude(0.72);
  for (const pack of Object.values(TOPAZIO_NARRATOR_PACKS_V4)) {
    rig.update(1700, true);
    const sizes = new Map(pack.layers.map((layer) => [layer.asset, layer.source_size]));
    for (const asset of Object.values(pack.facial_states.mouth)) sizes.set(asset, [...TOPAZIO_NARRATOR_VISUAL_CONTRACT_V4.source_size]);
    const first = buildLayerDrawPlan(pack, 1080, 1920, rig.pose(), sizes);
    const second = buildLayerDrawPlan(pack, 1080, 1920, rig.pose(), sizes);
    assert.deepEqual(first, second);
    const eyelids = first.find((entry) => entry.layer.id === "eyelids");
    const mouth = first.find((entry) => entry.layer.id === "mouth");
    assert.equal(eyelids.opacity, 0);
    assert.ok(mouth.layer.position[1] < 0.5);
    assert.ok(mouth.layer.size[0] < 1);
    rig.update(4330, true);
    const blink = buildLayerDrawPlan(pack, 1080, 1920, rig.pose(), sizes);
    assert.equal(blink.find((entry) => entry.layer.id === "eyelids").opacity, 1);
  }
});
