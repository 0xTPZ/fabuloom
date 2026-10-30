import assert from "node:assert/strict";
import test from "node:test";

import { buildLayerDrawPlan } from "../src/layered-character.ts";
import { transformPoint } from "../src/character-landmarks.mjs";
import { SANTA_V5_PACK } from "../src/santa-v5-pack.mjs";
import { SantaV5Rig } from "../src/santa-v5-engine.ts";

const sizes = new Map([
  ["assets/characters/topazio-narrators-v5/santa/head-clean.png", [1316, 1195]],
  ["assets/characters/topazio-narrators-v5/santa/torso.png", [1139, 1381]],
  ["assets/characters/topazio-narrators-v5/santa/pelvis.png", [1261, 1247]],
  ["assets/characters/topazio-narrators-v5/santa/thigh-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/thigh-right.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/shin-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/shin-right.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/foot-left.png", [1230, 1278]],
  ["assets/characters/topazio-narrators-v5/santa/foot-right.png", [1199, 1312]],
  ["assets/characters/topazio-narrators-v5/santa/upper-arm-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/upper-arm-right.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/forearm-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/forearm-right.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/hand-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/hand-right.png", [1151, 1366]],
]);

function planAt(timeMs = 0) {
  const rig = new SantaV5Rig();
  rig.setSceneDuration(20450);
  rig.update(timeMs, false);
  return buildLayerDrawPlan(SANTA_V5_PACK, 1080, 1920, rig.pose(), sizes);
}

function pivot(plan, id) {
  const entry = plan.find((candidate) => candidate.layer.id === id);
  return transformPoint(entry.matrix, entry.layer.anchor[0] * entry.intrinsic[0], entry.layer.anchor[1] * entry.intrinsic[1]);
}

test("Santa V5 visual plan has a clean base and ordered independent facial overlays", () => {
  const face = SANTA_V5_PACK.layers
    .filter((layer) => ["head", "eyes", "eyelids", "brows", "glasses", "beard", "mouth"].includes(layer.id))
    .sort((left, right) => left.z - right.z);
  assert.equal(face[0].asset.endsWith("head-clean.png"), true);
  assert.deepEqual(face.map((layer) => layer.id), ["head", "eyes", "eyelids", "brows", "glasses", "beard", "mouth"]);
  assert.equal(new Set(face.map((layer) => layer.asset)).size, face.length);
});

test("Santa V5 hand chains preserve measured wrist joins in the draw plan", () => {
  const plan = planAt();
  const leftElbow = pivot(plan, "left_forearm");
  const leftWrist = pivot(plan, "left_hand");
  const rightElbow = pivot(plan, "right_forearm");
  const rightWrist = pivot(plan, "right_hand");
  assert.ok(leftWrist.y > leftElbow.y && rightWrist.y > rightElbow.y);
  assert.ok(leftWrist.x < rightWrist.x);
  assert.ok(Math.abs(leftWrist.y - rightWrist.y) < 40);
  assert.ok([leftWrist, rightWrist].every(({ x, y }) => Number.isFinite(x) && Number.isFinite(y)));
});

test("Santa V5 foot pivots are symmetric and remain below the shin joins", () => {
  const plan = planAt();
  const leftAnkle = pivot(plan, "left_shin");
  const rightAnkle = pivot(plan, "right_shin");
  const leftFoot = pivot(plan, "left_foot");
  const rightFoot = pivot(plan, "right_foot");
  assert.ok(leftFoot.y > leftAnkle.y && rightFoot.y > rightAnkle.y);
  assert.ok(Math.abs(leftFoot.y - rightFoot.y) < 20);
  assert.ok(Math.abs((leftFoot.x + rightFoot.x) - 1080) < 20);
  assert.ok([leftFoot, rightFoot].every(({ x, y }) => Number.isFinite(x) && Number.isFinite(y)));
});

test("Santa V5 plan remains deterministic when sampled out of chronological order", () => {
  const a = planAt(12000);
  const b = planAt(1400);
  const c = planAt(12000);
  assert.deepEqual(a, c);
  assert.notDeepEqual(a, b);
});
