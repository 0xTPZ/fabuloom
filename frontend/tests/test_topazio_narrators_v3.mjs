import assert from "node:assert/strict";
import test from "node:test";
import { existsSync } from "node:fs";
import { buildLayerDrawPlan, LayeredCharacterRig } from "../src/layered-character.ts";
import { validateCharacterPack } from "../src/character-pack.mjs";
import { TOPAZIO_NARRATOR_PACKS_V3 } from "../src/topazio-narrator-packs-v3.mjs";

test("V3 Dora and Alex packs are validated cinematic facial packs", () => {
  for (const [character, pack] of Object.entries(TOPAZIO_NARRATOR_PACKS_V3)) {
    assert.equal(validateCharacterPack(pack), pack);
    assert.equal(pack.language, "pt-BR");
    assert.match(pack.art_status, /art-reforge-v3/);
    assert.deepEqual(pack.layers.map((layer) => layer.id), ["head", "eyelids", "mouth"]);
    assert.equal(pack.layers.find((layer) => layer.id === "eyelids").parent, "head");
    assert.equal(pack.layers.find((layer) => layer.id === "mouth").parent, "head");
    const assets = new Set([
      ...pack.layers.map((layer) => layer.asset),
      ...pack.expressions.flatMap((expression) => Object.values(expression.overrides)),
    ]);
    for (const asset of assets) assert.equal(existsSync(new URL(`../${asset}`, import.meta.url)), true, `${character}: ${asset}`);
  }
});

test("V3 overlays stay aligned to the same head-local frame and preserve deterministic motion", () => {
  const rig = new LayeredCharacterRig();
  rig.setSpeechAmplitude(0.72);
  for (const pack of Object.values(TOPAZIO_NARRATOR_PACKS_V3)) {
    rig.update(1700, true);
    const sizes = new Map(pack.layers.map((layer) => [layer.asset, layer.source_size]));
    for (const expression of pack.expressions) {
      for (const asset of Object.values(expression.overrides)) sizes.set(asset, [1145, 1374]);
    }
    const first = buildLayerDrawPlan(pack, 1080, 1920, rig.pose(), sizes);
    const second = buildLayerDrawPlan(pack, 1080, 1920, rig.pose(), sizes);
    assert.deepEqual(first, second);
    assert.equal(first.find((entry) => entry.layer.id === "eyelids").opacity, 0);
    rig.update(4330, true);
    const blink = buildLayerDrawPlan(pack, 1080, 1920, rig.pose(), sizes);
    assert.equal(blink.find((entry) => entry.layer.id === "eyelids").opacity, 1);
    assert.ok(first.find((entry) => entry.layer.id === "mouth").drawHeight > 0);
  }
});
