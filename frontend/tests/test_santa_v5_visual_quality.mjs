import test from "node:test";
import assert from "node:assert/strict";

import { SantaV5SceneRenderer } from "../src/santa-v5-engine.ts";
import { SANTA_V5_POINT_AT_CLIP, SANTA_V5_WAVE_HELLO_CLIP } from "../src/santa-v5-engine.ts";
import { buildSantaV5QaPlan } from "../../tools/visual-inspector/qa-plan.mjs";

test("V5 named presenter clips remain anchored instead of inheriting V3 walk-in drift", () => {
  const animated = Object.create(SantaV5SceneRenderer.prototype);
  animated.rig = { animationId: () => "WAVE_HELLO" };
  const waveScene = animated.sceneAt(1680, SANTA_V5_WAVE_HELLO_CLIP.durationMs);
  assert.equal(waveScene.characterX, 60);
  assert.equal(waveScene.action, "idle");
  assert.equal(waveScene.seated, 0);

  const point = Object.create(SantaV5SceneRenderer.prototype);
  point.rig = { animationId: () => "POINT_AT", presentationTargetInfo: () => ({ arm: "right" }) };
  const pointScene = point.sceneAt(5200, SANTA_V5_POINT_AT_CLIP.durationMs);
  assert.equal(pointScene.characterX, 60);
  assert.equal(pointScene.action, "idle");

  const pointLeft = Object.create(SantaV5SceneRenderer.prototype);
  pointLeft.rig = { animationId: () => "POINT_AT", presentationTargetInfo: () => ({ arm: "left" }) };
  assert.equal(pointLeft.sceneAt(5200, SANTA_V5_POINT_AT_CLIP.durationMs).characterX, 180);

  const compatibility = Object.create(SantaV5SceneRenderer.prototype);
  compatibility.rig = { animationId: () => null };
  assert.equal(compatibility.sceneAt(1680, SANTA_V5_WAVE_HELLO_CLIP.durationMs).characterX, 180);
});

test("visual QA plan covers both POINT_AT arms", () => {
  const plan = buildSantaV5QaPlan({ waveClip: SANTA_V5_WAVE_HELLO_CLIP, pointClip: SANTA_V5_POINT_AT_CLIP });
  assert.ok(plan.captures.some((capture) => capture.name === "point-hold" && capture.mode === "point"));
  assert.ok(plan.captures.some((capture) => capture.name === "point-left-hold" && capture.mode === "point-left"));
  assert.ok(plan.captures.filter((capture) => capture.sequence === "POINT_AT").length >= 2 * SANTA_V5_POINT_AT_CLIP.keyframes.length);
});
