import assert from "node:assert/strict";
import test from "node:test";
import { existsSync, readFileSync } from "node:fs";
import { buildLayerDrawPlan, LayeredCharacterRig } from "../src/layered-character.ts";
import { validateCharacterPack } from "../src/character-pack.mjs";
import { TOPAZIO_NARRATOR_PACKS, TOPAZIO_NARRATOR_PACKS_V1 } from "../src/topazio-narrator-packs.mjs";
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
    assert.equal(pack.rig_profile, "animation-ready/0.1");
    assert.equal(pack.layers.length, 16);
    assert.equal(pack.layers[0].id, "torso");
    assert.equal(pack.bindings.head_rotation, "head");
    assert.equal(pack.bindings.mouth_open, "mouth");
    assert.equal(pack.language, "pt-BR");
    assert.match(pack.voice_id, /^p[fm]_(dora|santa|alex)$/);
    assert.match(pack.layers[0].asset, /topazio-narrators-v2\/shared\/torso\.svg$/);
    assert.ok(pack.layers.some((layer) => layer.role === "head" && layer.parent === "neck"));
    assert.ok(pack.layers.some((layer) => layer.role === "mouth" && layer.parent === "head"));
    assert.ok(pack.layers.some((layer) => layer.role === "hand"));
    assert.equal(validateCharacterPack(TOPAZIO_NARRATOR_PACKS_V1[key]).layers.length, 5);
  }
});

test("narrator packs resolve finite compact draw plans and expressions", () => {
  const rig = new LayeredCharacterRig();
  rig.setSpeechAmplitude(0.65);
  rig.update(1200, true);
  for (const pack of Object.values(TOPAZIO_NARRATOR_PACKS)) {
    const plan = buildLayerDrawPlan(pack, 960, 540, rig.pose(), new Map([
      ["assets/characters/topazio-narrators-v2/shared/torso.svg", [640, 960]],
      ["assets/characters/topazio-narrators-v2/shared/neck.svg", [1000, 700]],
      ["assets/characters/topazio-narrators-v2/shared/eyes.svg", [600, 200]],
      ["assets/characters/topazio-narrators-v2/shared/eyelids.svg", [600, 200]],
      ["assets/characters/topazio-narrators-v2/shared/brows.svg", [600, 180]],
      ["assets/characters/topazio-narrators-v2/shared/upper-arm-left.svg", [300, 500]],
      ["assets/characters/topazio-narrators-v2/shared/upper-arm-right.svg", [300, 500]],
      ["assets/characters/topazio-narrators-v2/shared/forearm-left.svg", [300, 500]],
      ["assets/characters/topazio-narrators-v2/shared/forearm-right.svg", [300, 500]],
      ["assets/characters/topazio-narrators-v2/shared/hand-left.svg", [240, 260]],
      ["assets/characters/topazio-narrators-v2/shared/hand-right.svg", [240, 260]],
      ["assets/characters/topazio-narrators-v2/shared/accessory.svg", [220, 260]],
      [pack.layers.find((layer) => layer.id === "head").asset, [600, 500]],
      [pack.layers.find((layer) => layer.id === "hair_back").asset, [640, 620]],
      [pack.layers.find((layer) => layer.id === "hair_front").asset, [600, 500]],
      [pack.layers.find((layer) => layer.id === "brows").asset, [600, 180]],
      [pack.layers.find((layer) => layer.id === "mouth").asset, [260, 140]],
      ["assets/characters/topazio-narrators-v2/shared/mouth-smile.svg", [260, 140]],
    ]));
    assert.equal(plan.length, 16);
    assert.equal(plan.at(-1).layer.id, "accessory");
    for (const entry of plan) for (const value of Object.values(entry.matrix)) assert.ok(Number.isFinite(value));
  }
});

test("V2 narrator assets are local SVG layers", () => {
  for (const pack of Object.values(TOPAZIO_NARRATOR_PACKS)) {
    const assets = new Set([
      ...pack.layers.map((layer) => layer.asset),
      ...pack.expressions.flatMap((expression) => Object.values(expression.overrides)),
    ]);
    for (const asset of assets) {
      const url = new URL(`../${asset}`, import.meta.url);
      assert.equal(existsSync(url), true, `missing character asset ${asset}`);
      assert.match(readFileSync(url, "utf8"), /^<svg\s/);
    }
  }
});

test("V2 head rotation leaves the torso transform stable", () => {
  const pack = TOPAZIO_NARRATOR_PACKS.dora;
  const still = buildLayerDrawPlan(pack, 960, 540, { breathing: 0.5, head_rotation: 0, eye_open: 1, mouth_open: 0, hair_sway: 0, brow_raise: 0, left_arm: 0, right_arm: 0 });
  const turned = buildLayerDrawPlan(pack, 960, 540, { breathing: 0.5, head_rotation: 0.16, eye_open: 1, mouth_open: 0, hair_sway: 0, brow_raise: 0, left_arm: 0, right_arm: 0 });
  const torso = (plan) => plan.find((entry) => entry.layer.id === "torso");
  const head = (plan) => plan.find((entry) => entry.layer.id === "head");
  assert.equal(torso(still).matrix.b, torso(turned).matrix.b);
  assert.equal(torso(still).matrix.c, torso(turned).matrix.c);
  assert.notEqual(head(still).matrix.b, head(turned).matrix.b);
});
