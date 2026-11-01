import assert from "node:assert/strict";
import test from "node:test";
import { resolveCinematicTransform } from "../src/cinematic-composition.mjs";

const base = { width: 1920, height: 1080, imageWidth: 1920, imageHeight: 1080 };
test("static keeps the image centered without motion", () => {
  assert.deepEqual(resolveCinematicTransform({ ...base, camera: "static", progress: 0.5 }), { scale: 1, offsetX: 0, offsetY: 0 });
});
test("static uses contain framing for portrait and square assets", () => {
  const portrait = resolveCinematicTransform({ camera: "static", width: 1920, height: 1080, imageWidth: 900, imageHeight: 1600 });
  assert.equal(portrait.scale, 0.675);
  assert.equal(portrait.offsetX, 656.25);
  assert.equal(portrait.offsetY, 0);
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
test("pan timing follows FFmpeg's twenty-second trajectory", () => {
  const early = resolveCinematicTransform({ ...base, camera: "pan-horizontal", progress: 1, localMs: 3000 });
  const full = resolveCinematicTransform({ ...base, camera: "pan-horizontal", progress: 1, localMs: 20000 });
  const overflow = 1920 * 1.08 - 1920;
  assert.ok(Math.abs(early.offsetX) < overflow * 0.2);
  assert.equal(full.offsetX, -overflow);
});
