import test from "node:test";
import assert from "node:assert/strict";
import {
  PRESENTATION_TARGET_FORMAT,
  createPresentationTarget,
  resolvePresentationTarget,
  validatePresentationTarget,
} from "../src/presentation-targets.mjs";
import {
  createPointAtClip,
  planPointAtTarget,
} from "../src/presenter-targeting.mjs";
import { SANTA_V5_RIGHT_ARM_IK_CALIBRATION } from "../src/santa-v5-calibration.mjs";

test("presentation targets validate and convert normalized coordinates", () => {
  const target = createPresentationTarget({ id: "book-right", position: { x: 0.84, y: 0.30 }, label: "Livro" });
  assert.equal(target.format, PRESENTATION_TARGET_FORMAT);
  const resolved = resolvePresentationTarget(target, { width: 1080, height: 1920 });
  assert.ok(Math.abs(resolved.point.x - 907.2) < 1e-9);
  assert.equal(resolved.point.y, 576);
});

test("scene-object targets resolve through object position or bounds", () => {
  const target = createPresentationTarget({ id: "symbol", objectId: "topazio-symbol", coordinateSpace: "scene-object", position: { x: 0, y: 0 }, label: "Símbolo" });
  const resolved = resolvePresentationTarget(target, {
    width: 1080,
    height: 1920,
    objects: { "topazio-symbol": { coordinateSpace: "normalized-stage", position: { x: 0.2, y: 0.3 }, bounds: { x: 0.1, y: 0.2, width: 0.2, height: 0.1 } } },
  });
  assert.deepEqual(resolved.point, { x: 216, y: 480 });
  assert.equal(resolved.label, "Símbolo");
});

test("targets reject invalid normalized positions and unsupported spaces", () => {
  assert.throws(() => validatePresentationTarget({ format: PRESENTATION_TARGET_FORMAT, id: "bad-target", position: { x: 1.2, y: 0.4 }, coordinateSpace: "normalized-stage" }));
  assert.throws(() => validatePresentationTarget({ format: PRESENTATION_TARGET_FORMAT, id: "bad-target", position: { x: 1, y: 1 }, coordinateSpace: "unknown" }));
});

test("POINT_AT clip has configurable hold and deterministic phase boundaries", () => {
  const clip = createPointAtClip({ durationMs: 9000, holdMs: 5100 });
  assert.equal(clip.id, "POINT_AT");
  assert.equal(clip.durationMs, 9000);
  assert.equal(clip.keyframes.at(3).channels.point_at_weight, 1);
  assert.equal(clip.keyframes.at(4).timeMs - clip.keyframes.at(3).timeMs, 5100);
  assert.deepEqual(clip.keyframes.at(-1).channels, { point_at_weight: 0, point_head_weight: 0, point_torso_weight: 0, point_hand_rotation: 0 });
  assert.throws(() => createPointAtClip({ durationMs: 3000, holdMs: 1000 }));
});

test("POINT_AT plans a safe wrist short of the target and flags unreachable objects", () => {
  const right = createPresentationTarget({ id: "right", position: { x: 0.90, y: 0.28 } });
  const left = createPresentationTarget({ id: "left", position: { x: 0.20, y: 0.32 } });
  const far = createPresentationTarget({ id: "far", position: { x: 0.99, y: 0.01 } });
  const rightPlan = planPointAtTarget(right, { calibration: SANTA_V5_RIGHT_ARM_IK_CALIBRATION });
  const leftPlan = planPointAtTarget(left, { calibration: SANTA_V5_RIGHT_ARM_IK_CALIBRATION });
  const farPlan = planPointAtTarget(far, { calibration: SANTA_V5_RIGHT_ARM_IK_CALIBRATION, wristClearancePx: 0 });
  assert.ok(rightPlan.wristDistance < rightPlan.requestedDistance);
  assert.ok(Number.isFinite(rightPlan.pointerDirection));
  assert.notDeepEqual(rightPlan.elbowPreference, leftPlan.elbowPreference);
  assert.equal(farPlan.reachable, false);
  assert.equal(farPlan.clamped, true);
});
