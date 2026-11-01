import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { test } from "node:test";
import { buildLayerDrawPlan } from "../src/layered-character.ts";
import { validateCharacterPack } from "../src/character-pack.mjs";
import { SANTA_V5_PACK } from "../src/santa-v5-pack.mjs";
import { SANTA_V5_ANATOMY_EXPERIMENTAL_PACK } from "../src/santa-v5-anatomy-experimental-pack.mjs";
import { decodePng } from "../../tools/visual-inspector/png.mjs";

const root = new URL("../assets/characters/topazio-narrators-v5/experimental-anatomy/", import.meta.url);
const byId = (pack, id) => pack.layers.find((layer) => layer.id === id);

test("official Santa V5 pack remains the production source of truth", () => {
  assert.equal(SANTA_V5_PACK.id, "topazio-narrator-santa-v5");
  assert.equal(SANTA_V5_PACK.art_status, "production-rig-v1");
  assert.equal(byId(SANTA_V5_PACK, "left_upper_arm").asset, "assets/characters/topazio-narrators-v5/santa/upper-arm-left.png");
  assert.equal(byId(SANTA_V5_PACK, "left_hand").parent, "left_forearm");
});

test("experimental pack validates and exposes an explicit anatomy hierarchy", () => {
  assert.equal(validateCharacterPack(SANTA_V5_ANATOMY_EXPERIMENTAL_PACK), SANTA_V5_ANATOMY_EXPERIMENTAL_PACK);
  assert.equal(SANTA_V5_ANATOMY_EXPERIMENTAL_PACK.art_status, "experimental-anatomy-first");
  assert.equal(byId(SANTA_V5_ANATOMY_EXPERIMENTAL_PACK, "left_forearm").parent, "left_upper_arm");
  assert.equal(byId(SANTA_V5_ANATOMY_EXPERIMENTAL_PACK, "left_cuff").parent, "left_forearm");
  assert.equal(byId(SANTA_V5_ANATOMY_EXPERIMENTAL_PACK, "left_hand").parent, "left_forearm");
  assert.equal(byId(SANTA_V5_ANATOMY_EXPERIMENTAL_PACK, "right_cuff").parent, "right_forearm");
  assert.deepEqual(SANTA_V5_ANATOMY_EXPERIMENTAL_PACK.anatomy_segments.filter((part) => part.id.endsWith("-left")).map((part) => part.role), ["shoulder", "upper-arm", "elbow-overlap", "forearm", "wrist-cuff", "hand"]);
});

test("experimental feet are smaller without changing the official pack", () => {
  assert.deepEqual(byId(SANTA_V5_PACK, "left_foot").size, [0.86, 0.30]);
  assert.deepEqual(byId(SANTA_V5_ANATOMY_EXPERIMENTAL_PACK, "left_foot").size, [0.74, 0.26]);
  assert.deepEqual(byId(SANTA_V5_ANATOMY_EXPERIMENTAL_PACK, "right_foot").size, [0.74, 0.26]);
});

test("experimental draw plans are finite and preserve parent-before-child resolution", () => {
  const plans = buildLayerDrawPlan(SANTA_V5_ANATOMY_EXPERIMENTAL_PACK, 1080, 1920, { breathing: 0.5, head_rotation: 0.03, eye_open: 1, mouth_open: 0.4, hair_sway: 0, brow_raise: 0.1, left_arm: 0.1, right_arm: -0.2, left_arm_rotation: 0.1, right_arm_rotation: -0.2, left_forearm_rotation: 0.3, right_forearm_rotation: -0.3, left_hand_rotation: 0.1, right_hand_rotation: -0.1 });
  const indexes = new Map(plans.map((plan, index) => [plan.layer.id, index]));
  assert.ok(indexes.get("left_upper_arm") < indexes.get("left_forearm"));
  assert.ok(indexes.get("left_forearm") < indexes.get("left_cuff"));
  assert.ok(indexes.get("left_cuff") < indexes.get("left_hand"));
  for (const plan of plans) for (const value of Object.values(plan.matrix)) assert.ok(Number.isFinite(value), `${plan.layer.id} matrix must be finite`);
});

test("all generated experimental anatomy bands are valid PNGs", async () => {
  for (const file of ["upper-arm-left-anatomy.png", "upper-arm-right-anatomy.png", "forearm-left-anatomy.png", "forearm-right-anatomy.png", "cuff-left-anatomy.png", "cuff-right-anatomy.png"]) {
    const path = new URL(file, root);
    await access(path);
    const image = decodePng(await readFile(path));
    assert.ok(image.width > 0 && image.height > 0, file);
    assert.equal(image.rgba.length, image.width * image.height * 4, file);
  }
});
