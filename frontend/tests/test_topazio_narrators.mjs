import assert from "node:assert/strict";
import test from "node:test";
import { buildLayerDrawPlan, LayeredCharacterRig } from "../src/layered-character.ts";
import { validateCharacterPack } from "../src/character-pack.mjs";
import { TOPAZIO_NARRATOR_PACKS } from "../src/topazio-narrator-packs.mjs";
import { TOPAZIO_NARRATION_CATALOG, manifestVoiceId, narrationForCharacter, narrationForUrl } from "../src/topazio-narrations.mjs";

test("the three Topazio narrators share a compact validated rig", () => {
  assert.deepEqual(Object.keys(TOPAZIO_NARRATOR_PACKS), ["dora", "santa", "alex"]);
  assert.deepEqual(TOPAZIO_NARRATION_CATALOG.map((item) => item.characterId), ["dora", "santa", "alex"]);
  for (const item of TOPAZIO_NARRATION_CATALOG) {
    assert.equal(narrationForCharacter(item.characterId), item);
    assert.equal(narrationForUrl(item.url), item);
    assert.match(item.url, /kokoro-story-demo-0091-(dora|santa|alex)\.json$/);
  }
  assert.equal(manifestVoiceId({ metadata: { voice_id: "pf_dora" }, segments: [] }), "pf_dora");
  assert.equal(manifestVoiceId({ metadata: {}, segments: [{ voice_id: "pm_santa" }] }), "pm_santa");
  for (const [key, pack] of Object.entries(TOPAZIO_NARRATOR_PACKS)) {
    assert.equal(validateCharacterPack(pack), pack);
    assert.equal(pack.layers.length, 5);
    assert.equal(pack.layers[0].id, "portrait");
    assert.equal(pack.bindings.head_rotation, "portrait");
    assert.equal(pack.bindings.mouth_open, "mouth");
    assert.equal(pack.language, "pt-BR");
    assert.match(pack.voice_id, /^p[fm]_(dora|santa|alex)$/);
    assert.match(pack.layers[0].asset, new RegExp(`topazio-narrators/${key}\\.png$`));
  }
});

test("narrator packs resolve finite compact draw plans and expressions", () => {
  const rig = new LayeredCharacterRig();
  rig.setSpeechAmplitude(0.65);
  rig.update(1200, true);
  for (const pack of Object.values(TOPAZIO_NARRATOR_PACKS)) {
    const plan = buildLayerDrawPlan(pack, 960, 540, rig.pose(), new Map([
      [pack.layers[0].asset, [1145, 1374]],
      ["assets/characters/fantasy-narrator/eyes.svg", [320, 90]],
      ["assets/characters/fantasy-narrator/eyelids.svg", [320, 90]],
      ["assets/characters/fantasy-narrator/brows.svg", [320, 90]],
      ["assets/characters/fantasy-narrator/mouth.svg", [200, 100]],
    ]));
    assert.equal(plan.length, 5);
    assert.equal(plan.at(-1).layer.id, "mouth");
    for (const entry of plan) for (const value of Object.values(entry.matrix)) assert.ok(Number.isFinite(value));
  }
});
