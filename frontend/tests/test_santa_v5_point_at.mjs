import test from "node:test";
import assert from "node:assert/strict";
import {
  SANTA_V5_ANIMATION_LIBRARY,
  SANTA_V5_POINT_AT_CLIP,
  SANTA_V5_WAVE_HELLO_CLIP,
  SantaV5Rig,
} from "../src/santa-v5-engine.ts";
import { createPresentationTarget } from "../src/presentation-targets.mjs";
import { buildLayerDrawPlan } from "../src/layered-character.ts";
import { transformPoint } from "../src/character-landmarks.mjs";
import { SANTA_V5_PACK } from "../src/santa-v5-pack.mjs";

const sizes = new Map([
  ["assets/characters/topazio-narrators-v5/santa/torso.png", [1139, 1381]],
  ["assets/characters/topazio-narrators-v5/santa/upper-arm-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/forearm-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/hand-left.png", [1024, 1536]],
]);

const rightTarget = createPresentationTarget({ id: "book-right", position: { x: 0.88, y: 0.30 }, label: "Livro à direita" });
const leftTarget = createPresentationTarget({ id: "symbol-left", position: { x: 0.30, y: 0.34 }, label: "Símbolo à esquerda" });

test("Santa V5 exposes POINT_AT without changing WAVE_HELLO", () => {
  assert.equal(SANTA_V5_POINT_AT_CLIP.id, "POINT_AT");
  assert.equal(SANTA_V5_ANIMATION_LIBRARY.POINT_AT.durationMs, 8000);
  assert.equal(SANTA_V5_WAVE_HELLO_CLIP.id, "WAVE_HELLO");
});

test("POINT_AT keeps the arm chain connected while head and torso follow", () => {
  const rig = new SantaV5Rig();
  rig.setSceneDuration(8000); rig.setPresentationTarget(rightTarget).setAnimation("POINT_AT");
  rig.update(0, false);
  const rest = rig.pose();
  rig.update(2800, false);
  const raised = rig.pose();
  const info = rig.presentationTargetInfo();
  const ik = rig.rightHandIK();
  assert.equal(info.id, "book-right");
  assert.equal(ik.presentationTargetId, "book-right");
  assert.ok(Math.abs(raised.right_arm_rotation) > 0.1);
  assert.ok(Math.abs(raised.head_rotation - rest.head_rotation) > 0.005);
  assert.ok(Math.abs(raised.torso_rotation - rest.torso_rotation) > 0.005);
  assert.ok(ik.appliedRenderedWrist && Number.isFinite(ik.appliedRenderedWrist.x));
  assert.ok(Number.isFinite(ik.pointerRotation));
});

test("POINT_AT supports a left target, out-of-order seek and deterministic repetition", () => {
  const first = new SantaV5Rig();
  first.setSceneDuration(8000); first.setPresentationTarget(leftTarget).setAnimation("POINT_AT");
  first.update(6500, false); const hold = first.pose(); const holdIK = first.activeArmIK();
  first.update(300, false); const early = first.pose();
  first.update(6500, false); const repeated = first.pose();
  assert.equal(holdIK.arm, "left");
  assert.ok(Math.abs(hold.left_arm_rotation) > 0.1);
  assert.equal(hold.right_arm_rotation, 0);
  assert.ok(holdIK.presentationTarget.x < 540);
  assert.notDeepEqual(early, hold);
  assert.deepEqual(repeated, hold);
});

test("POINT_AT target can change without rewriting the clip", () => {
  const rig = new SantaV5Rig();
  rig.setSceneDuration(8000); rig.setAnimation("POINT_AT").setPresentationTarget(rightTarget);
  rig.update(3000, false); const right = rig.rightHandIK();
  rig.setPresentationTarget(leftTarget); rig.update(3000, false); const left = rig.rightHandIK();
  assert.equal(right.presentationTargetId, "book-right");
  assert.equal(left.presentationTargetId, "symbol-left");
  assert.equal(right.arm, "right");
  assert.equal(left.arm, "left");
  assert.notEqual(right.pointerDirection, left.pointerDirection);
});

test("POINT_AT left arm reaches the real rendered hand pivot", () => {
  const rig = new SantaV5Rig();
  rig.setPresentationTarget(leftTarget).setAnimation("POINT_AT");
  rig.update(2800, false);
  const ik = rig.activeArmIK();
  const plan = buildLayerDrawPlan(SANTA_V5_PACK, 1080, 1920, rig.pose(), sizes);
  const hand = plan.find((entry) => entry.layer.id === "left_hand");
  const handPoint = transformPoint(hand.matrix, hand.layer.anchor[0] * hand.intrinsic[0], hand.layer.anchor[1] * hand.intrinsic[1]);
  assert.equal(ik.arm, "left");
  assert.ok(Math.hypot(handPoint.x - ik.requestedTarget.x, handPoint.y - ik.requestedTarget.y) < 3);
  assert.ok(ik.appliedRenderedError < 1);
});
