import test from "node:test";
import assert from "node:assert/strict";

import {
  analyzeRenderedPixels,
  combineVisualDiagnostics,
  compareRenderedPixels,
  diagnoseRenderedImage,
} from "../src/real-image-inspector.mjs";
import {
  createUnavailableVisualAnalysisProvider,
  createVisualAnalysisRequest,
  validateVisualAnalysisProvider,
} from "../src/visual-analysis-provider.mjs";

function image(width, height, fill = [8, 16, 28, 255]) {
  const rgba = new Uint8ClampedArray(width * height * 4);
  for (let index = 0; index < rgba.length; index += 4) rgba.set(fill, index);
  return { width, height, rgba };
}

function paint(target, left, top, right, bottom, color = [240, 210, 90, 255]) {
  for (let y = top; y < bottom; y += 1) for (let x = left; x < right; x += 1) target.rgba.set(color, (y * target.width + x) * 4);
}

test("pixel analyzer measures alpha, foreground bounds and components", () => {
  const current = image(48, 48);
  paint(current, 12, 10, 30, 36);
  const metrics = analyzeRenderedPixels(current, { region: { left: 0, top: 0, right: 48, bottom: 48 }, minComponentArea: 4 });
  assert.equal(metrics.dimensions.width, 48);
  assert.equal(metrics.alpha.hasTransparency, false);
  assert.equal(metrics.foreground.componentCount, 1);
  assert.deepEqual(metrics.foreground.bounds, { left: 12, top: 10, right: 30, bottom: 36, width: 18, height: 26 });
});

test("pixel comparison reports broad-region changes without inventing landmarks", () => {
  const reference = image(48, 48); const current = image(48, 48); paint(current, 12, 10, 30, 36);
  const result = compareRenderedPixels(reference, current, { region: { left: 0, top: 0, right: 48, bottom: 48 } });
  assert.equal(result.compatible, true);
  assert.ok(result.regions.full.differenceRatio > 0);
  assert.ok(result.regions.face.differenceRatio > 0);
});

test("detached pixel components remain a low-confidence visual hypothesis", () => {
  const current = image(64, 64);
  paint(current, 10, 10, 30, 42);
  paint(current, 44, 22, 52, 30);
  const diagnosis = diagnoseRenderedImage(current, { options: { region: { left: 0, top: 0, right: 64, bottom: 64 }, minComponentArea: 4 } });
  assert.ok(diagnosis.issues.some((finding) => finding.code === "disconnected-component"));
  assert.ok(diagnosis.issues.every((finding) => finding.severity === "hypothesis"));
});

test("reference difference becomes a low-confidence visual hypothesis", () => {
  const reference = image(48, 48); const current = image(48, 48); paint(current, 12, 10, 30, 36);
  const diagnosis = diagnoseRenderedImage(current, { reference, referenceMetrics: analyzeRenderedPixels(reference), options: { faceDifferenceThreshold: .01 } });
  assert.ok(diagnosis.issues.some((finding) => finding.code === "facial-region-difference"));
  assert.ok(diagnosis.issues.every((finding) => finding.origin === "visual-pixels"));
  assert.equal(diagnosis.review.required, true);
});

test("diagnostic combiner preserves source provenance and review state", () => {
  const combined = combineVisualDiagnostics({ geometry: [{ code: "joint-gap", severity: "error", confidence: "high" }], visual: [{ code: "facial-region-difference", severity: "hypothesis", confidence: "low" }] });
  assert.equal(combined.summary.confirmed, 1);
  assert.deepEqual(combined.issues.map((finding) => finding.origin), ["geometry", "visual-pixels"]);
  assert.equal(combined.review.required, true);
});

test("unavailable multimodal provider is explicit and offline", async () => {
  const provider = validateVisualAnalysisProvider(createUnavailableVisualAnalysisProvider());
  assert.equal(provider.capabilities().image, false);
  const request = createVisualAnalysisRequest({ image: { id: "local" } });
  const imageResult = await provider.analyzeImage(request);
  const sequenceResult = await provider.analyzeSequence(request);
  assert.equal(imageResult.status, "not-executed");
  assert.equal(sequenceResult.status, "not-executed");
  assert.equal(imageResult.humanReviewRequired, true);
});
