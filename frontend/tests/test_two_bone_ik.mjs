import assert from "node:assert/strict";
import { test } from "node:test";

import { angleBetweenPoints, angleDelta, solveTwoBoneIK } from "../src/two-bone-ik.mjs";

const shoulder = { x: 0, y: 0 };

test("two-bone IK reaches an attainable target with deterministic angles", () => {
  const input = { shoulder, target: { x: 3, y: 2 }, upperLength: 3, forearmLength: 2.5, elbowPreference: { x: 1, y: 0.5 } };
  const first = solveTwoBoneIK(input); const second = solveTwoBoneIK(input);
  assert.deepEqual(first, second);
  assert.equal(first.reachable, true);
  assert.ok(first.error < 1e-9);
  assert.ok(first.elbow.x > 0);
});

test("two-bone IK clamps unreachable targets without invalid numbers", () => {
  const result = solveTwoBoneIK({ shoulder, target: { x: 20, y: 0 }, upperLength: 3, forearmLength: 2, elbowPreference: { x: 1, y: 0 } });
  assert.equal(result.reachable, false);
  assert.equal(result.clamped, true);
  assert.ok(Math.abs(result.error - 15) < 1e-9);
  assert.ok([result.shoulderAngle, result.elbowAngle, result.wrist.x, result.wrist.y].every(Number.isFinite));
});

test("two-bone IK respects elbow preference and joint limits", () => {
  const outward = solveTwoBoneIK({ shoulder, target: { x: 2, y: -2 }, upperLength: 2.8, forearmLength: 2.2, elbowPreference: { x: 1, y: 1 } });
  assert.ok(outward.elbow.x > 0 && outward.elbow.y > 0);
  const limited = solveTwoBoneIK({ shoulder, target: { x: 2, y: -2 }, upperLength: 2.8, forearmLength: 2.2, elbowPreference: { x: 1, y: 1 }, limits: { shoulder: [-0.2, 1.2], elbow: [-2.8, 0] } });
  assert.ok(limited.shoulderAngle >= -0.2 && limited.shoulderAngle <= 1.2);
  assert.ok(limited.elbowAngle <= 0);
});

test("angle helpers use the documented Canvas coordinate convention", () => {
  assert.equal(angleBetweenPoints({ x: 0, y: 0 }, { x: 0, y: 1 }), Math.PI / 2);
  assert.ok(Math.abs(angleDelta(Math.PI * 1.9, -Math.PI * 1.9)) < 0.7);
});
