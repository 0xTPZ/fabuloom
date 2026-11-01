import assert from "node:assert/strict";
import test from "node:test";
import { resolveCinematicTransform } from "../src/cinematic-composition.mjs";

const base = { width: 1920, height: 1080, imageWidth: 1920, imageHeight: 1080 };
test("static keeps the image centered without motion", () => {
  assert.deepEqual(resolveCinematicTransform({ ...base, camera: "static", progress: 0.5 }), { scale: 1, offsetX: 0, offsetY: 0 });
});
test("zoom grows monotonically and pans remain bounded", () => {
  const zoomStart = resolveCinematicTransform({ ...base, camera: "zoom", localMs: 0, progress: 0 });
  const zoomEnd = resolveCinematicTransform({ ...base, camera: "zoom", localMs: 3000, progress: 1 });
  assert.ok(zoomEnd.scale > zoomStart.scale);
  const horizontal = resolveCinematicTransform({ ...base, camera: "pan-horizontal", progress: 1 });
  const vertical = resolveCinematicTransform({ ...base, camera: "pan-vertical", progress: 1 });
  assert.equal(horizontal.offsetY, -(1080 * 1.08 - 1080) / 2);
  assert.equal(vertical.offsetX, -(1920 * 1.08 - 1920) / 2);
});
