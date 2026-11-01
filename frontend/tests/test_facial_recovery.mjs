import assert from "node:assert/strict";
import test from "node:test";
import { existsSync } from "node:fs";
import { buildLayerDrawPlan, collectCharacterAssetPaths, LayeredCharacterRig } from "../src/layered-character.ts";
import { validateCharacterPack } from "../src/character-pack.mjs";
import { MOUTH_RECOVERY_LAB_PACK, MOUTH_RECOVERY_STATES } from "../src/mouth-recovery-lab.mjs";
import {
  ALEX_NARRATOR_PACK_RECOVERY_V1,
  DORA_NARRATOR_PACK_RECOVERY_V1,
  TOPAZIO_NARRATOR_FACIAL_RECOVERY_CONTRACT,
  TOPAZIO_NARRATOR_PACKS_RECOVERY_V1,
} from "../src/topazio-narrator-packs-recovery-v1.mjs";

test("facial recovery packs use explicit same-canvas vector mouth states", () => {
  assert.equal(TOPAZIO_NARRATOR_FACIAL_RECOVERY_CONTRACT.strategy, "same-canvas-explicit-vector-mouth-states");
  for (const [character, pack] of Object.entries(TOPAZIO_NARRATOR_PACKS_RECOVERY_V1)) {
    assert.equal(validateCharacterPack(pack), pack);
    assert.match(pack.art_status, /facial-system-recovery-v1-experimental-awaiting-art-approval/);
    assert.equal(pack.language, "pt-BR");
    assert.deepEqual(Object.keys(pack.facial_states.mouth), ["closed", "slight", "moderate", "open", "smile"]);
    const mouth = pack.layers.find((layer) => layer.id === "mouth");
    assert.deepEqual(mouth.position, [0.5, 0.5]);
    assert.deepEqual(mouth.size, [1, 1]);
    for (const asset of collectCharacterAssetPaths(pack)) {
      assert.equal(existsSync(new URL(`../${asset}`, import.meta.url)), true, `${character}: ${asset}`);
    }
  }
  assert.equal(DORA_NARRATOR_PACK_RECOVERY_V1.voice_id, "pf_dora");
  assert.equal(ALEX_NARRATOR_PACK_RECOVERY_V1.voice_id, "pm_alex");
});

test("recovery and prototype state maps are complete and deterministic", () => {
  assert.deepEqual(MOUTH_RECOVERY_STATES, ["closed", "slight", "moderate", "open", "smile"]);
  assert.equal(validateCharacterPack(MOUTH_RECOVERY_LAB_PACK), MOUTH_RECOVERY_LAB_PACK);
  const rig = new LayeredCharacterRig();
  rig.setSpeechAmplitude(0.72);
  rig.update(1700, true);
  const sizes = new Map(MOUTH_RECOVERY_LAB_PACK.layers.map((layer) => [layer.asset, layer.source_size]));
  for (const asset of Object.values(MOUTH_RECOVERY_LAB_PACK.facial_states.mouth)) sizes.set(asset, [640, 720]);
  const first = buildLayerDrawPlan(MOUTH_RECOVERY_LAB_PACK, 640, 720, rig.pose(), sizes);
  const second = buildLayerDrawPlan(MOUTH_RECOVERY_LAB_PACK, 640, 720, rig.pose(), sizes);
  assert.deepEqual(first, second);
  assert.deepEqual(first.find((entry) => entry.layer.id === "mouth").layer.size, [1, 1]);
});
