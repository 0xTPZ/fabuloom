import test from "node:test";
import assert from "node:assert/strict";

import { SANTA_V5_POINT_AT_CLIP, SANTA_V5_WAVE_HELLO_CLIP } from "../src/santa-v5-engine.ts";
import { executeCorrectionAttempt, createCorrectionAttempt } from "../../tools/visual-inspector/assisted-correction.mjs";
import { buildSantaV5QaPlan } from "../../tools/visual-inspector/qa-plan.mjs";
import { assertWorkspacePath, buildEvidencePackage, validateEvidencePackage } from "../../tools/visual-inspector/qa-report.mjs";

test("QA plan is deterministic and covers required visual states", () => {
  const first = buildSantaV5QaPlan({ waveClip: SANTA_V5_WAVE_HELLO_CLIP, pointClip: SANTA_V5_POINT_AT_CLIP });
  const second = buildSantaV5QaPlan({ waveClip: SANTA_V5_WAVE_HELLO_CLIP, pointClip: SANTA_V5_POINT_AT_CLIP });
  assert.deepEqual(first, second);
  const names = new Set(first.captures.map((capture) => capture.name));
  for (const required of ["neutral", "idle-mid", "blink", "mouth-open", "wave-raised", "point-hold", "feet-neutral"]) assert.ok(names.has(required), required);
  assert.ok(first.captures.some((capture) => capture.name.startsWith("wave-kf-")));
  assert.ok(first.captures.some((capture) => capture.name.startsWith("wave-mid-")));
  assert.ok(first.captures.every((capture) => typeof capture.reason === "string" && capture.reason.length > 10));
});

test("assisted correction accepts a validated isolated change", async () => {
  const state = createCorrectionAttempt({ id: "accept", scope: "test", maxAttempts: 1 });
  let rollbackCount = 0;
  const result = await executeCorrectionAttempt({
    state,
    snapshot: async () => ({ variant: "before" }),
    apply: async () => ({ variant: "after" }),
    validate: async ({ after }) => ({ accepted: after.variant === "after" }),
    rollback: async () => { rollbackCount += 1; },
  });
  assert.equal(result.status, "accepted");
  assert.equal(result.attempts, 1);
  assert.equal(rollbackCount, 0);
});

test("assisted correction reverts rejected changes and enforces attempt limit", async () => {
  const state = createCorrectionAttempt({ id: "reject", scope: "test", maxAttempts: 1 });
  let rollbackCount = 0;
  const run = () => executeCorrectionAttempt({
    state,
    snapshot: async () => ({ officialAssetsChanged: false }),
    apply: async () => ({ officialAssetsChanged: true }),
    validate: async () => ({ accepted: false, reason: "test rejection" }),
    rollback: async () => { rollbackCount += 1; },
  });
  const reverted = await run();
  assert.equal(reverted.status, "reverted");
  assert.equal(rollbackCount, 1);
  const limitResult = await executeCorrectionAttempt({
    state: { ...reverted, attempts: 1 },
    snapshot: async () => ({}), apply: async () => ({}), validate: async () => ({ accepted: true }), rollback: async () => undefined,
  });
  assert.equal(limitResult.status, "attempt-limit");
});

test("evidence package validates workspace containment", () => {
  assert.throws(() => assertWorkspacePath("C:/outside/secret.png"), /outside workspace/);
  const evidence = buildEvidencePackage({
    generatedAt: "2026-10-30T00:00:00.000Z",
    plan: { format: "fabuloom.visual-qa-plan/0.1", captures: [{ name: "neutral", mode: "neutral", timeMs: 0, reason: "test" }] },
    executions: [{ id: "production", variant: "production-v5", output: "E:/Fabuloom/workspace/exports/visual-qa/test", report: { captures: [{ name: "neutral", reason: "test", screenshot: "neutral.png" }] }, reportPath: "E:/Fabuloom/workspace/exports/visual-qa/test/report.json", exitCode: 0, status: "completed" }],
    comparisons: [],
  });
  assert.equal(validateEvidencePackage(evidence), true);
  assert.equal(evidence.images[0].url, "/exports/visual-qa/test/neutral.png");
});
