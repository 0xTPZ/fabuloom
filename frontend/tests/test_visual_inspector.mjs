import assert from "node:assert/strict";
import { test } from "node:test";

import { buildLayerDrawPlan } from "../src/layered-character.ts";
import { resolveLandmarks } from "../src/character-landmarks.mjs";
import { SANTA_V5_ANATOMICAL_LANDMARKS, SANTA_V5_ALPHA_BOUNDS } from "../src/santa-v5-calibration.mjs";
import { SantaV5Rig } from "../src/santa-v5-engine.ts";
import { SANTA_V5_PACK } from "../src/santa-v5-pack.mjs";
import {
  VISUAL_INSPECTION_FORMAT,
  buildInspectionFrame,
  defaultInspectionConfig,
  diagnoseFrame,
  diagnoseMotion,
  summarizeInspection,
  transformRect,
} from "../src/visual-inspector-core.mjs";
import { annotatePng, comparePngBuffers, decodePng, encodePng } from "../../tools/visual-inspector/png.mjs";
import { createKnownDefectFixtures, correctFaceDuplicateFixture, resolveFixtureRegion } from "../../tools/visual-inspector/fixtures.mjs";

const sizes = new Map([
  ["assets/characters/topazio-narrators-v5/santa/hair-back.png", [1246, 1263]],
  ["assets/characters/topazio-narrators-v5/santa/foot-left.png", [1230, 1278]],
  ["assets/characters/topazio-narrators-v5/santa/foot-right.png", [1199, 1312]],
  ["assets/characters/topazio-narrators-v5/santa/shin-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/shin-right.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/pelvis.png", [1261, 1247]],
  ["assets/characters/topazio-narrators-v5/santa/thigh-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/thigh-right.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/torso.png", [1139, 1381]],
  ["assets/characters/topazio-narrators-v5/santa/upper-arm-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/upper-arm-right.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/forearm-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/forearm-right.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/hand-left.png", [1024, 1536]],
  ["assets/characters/topazio-narrators-v5/santa/hand-right.png", [1151, 1366]],
  ["assets/characters/topazio-narrators-v5/santa/neck.png", [1536, 1024]],
  ["assets/characters/topazio-narrators-v5/santa/head-clean.png", [1316, 1195]],
  ["assets/characters/topazio-narrators-v5/santa/hair-front.png", [1536, 1024]],
  ["assets/characters/topazio-narrators-v5/santa/eyes-open.png", [1774, 887]],
  ["assets/characters/topazio-narrators-v5/santa/eyelids-closed.png", [1851, 850]],
  ["assets/characters/topazio-narrators-v5/santa/brows.png", [1774, 887]],
  ["assets/characters/topazio-narrators-v5/santa/glasses.png", [1316, 1195]],
  ["assets/characters/topazio-narrators-v5/santa/beard.png", [1316, 1195]],
  ["assets/characters/topazio-narrators-v5/santa/mouth-closed.png", [1536, 1024]],
  ["assets/characters/topazio-narrators-v5/santa/mouth-open.png", [1316, 1195]],
]);

function santaFrame({ timeMs = 0, isPlaying = false, pose = null, mutate = null } = {}) {
  const rig = new SantaV5Rig();
  rig.setSceneDuration(20450);
  rig.setSpeechAmplitude(isPlaying ? 0.7 : 0);
  rig.update(timeMs, isPlaying);
  const finalPose = pose || rig.pose();
  const plans = buildLayerDrawPlan(SANTA_V5_PACK, 1080, 1920, finalPose, sizes);
  const landmarks = resolveLandmarks(SANTA_V5_ANATOMICAL_LANDMARKS, plans);
  const frame = buildInspectionFrame({
    characterId: SANTA_V5_PACK.id,
    pack: SANTA_V5_PACK,
    plans,
    resolvedAssets: Object.fromEntries(SANTA_V5_PACK.layers.map((layer) => [layer.id, layer.asset])),
    pose: finalPose,
    timeMs,
    isPlaying,
    animationId: null,
    width: 1080,
    height: 1920,
    alphaBounds: SANTA_V5_ALPHA_BOUNDS,
    landmarks,
  });
  if (mutate) mutate(frame);
  return frame;
}

test("builds a versioned frame with transforms, bounds and resolved landmarks", () => {
  const frame = santaFrame();
  assert.equal(frame.format, VISUAL_INSPECTION_FORMAT);
  assert.equal(frame.layers.length, SANTA_V5_PACK.layers.length);
  assert.equal(frame.landmarks.length, SANTA_V5_ANATOMICAL_LANDMARKS.length);
  assert.ok(frame.layers.every((layer) => layer.transformedAlphaBounds.width > 0));
  assert.ok(frame.landmarks.every((landmark) => Number.isFinite(landmark.stage.x)));
});

test("known-good Santa neutral frame has no verified errors", () => {
  const diagnostics = diagnoseFrame(santaFrame(), defaultInspectionConfig());
  assert.equal(diagnostics.issues.filter((finding) => finding.severity === "error").length, 0, JSON.stringify(diagnostics.issues));
});

test("known-good Santa frame passes the alpha-overlap and silhouette checks", () => {
  const diagnostics = diagnoseFrame(santaFrame(), defaultInspectionConfig());
  assert.equal(diagnostics.issues.some((finding) => ["visible-joint-gap", "anatomical-crossing"].includes(finding.code)), false, JSON.stringify(diagnostics.issues));
});

test("inspection frames are deterministic for the same absolute time", () => {
  assert.deepEqual(santaFrame({ timeMs: 1680, isPlaying: true }), santaFrame({ timeMs: 1680, isPlaying: true }));
});

test("detects an artificial joint gap as an error", () => {
  const frame = santaFrame({ mutate: (value) => { value.landmarks.find((landmark) => landmark.id === "leftWrist").stage.x += 300; } });
  const diagnostics = diagnoseFrame(frame);
  assert.ok(diagnostics.issues.some((finding) => finding.code === "joint-gap" && finding.severity === "error"));
});

test("distinguishes a duplicated facial asset from a painted-face hypothesis", () => {
  const duplicate = santaFrame({ mutate: (value) => {
    value.layers.find((layer) => layer.id === "eyes").asset = value.layers.find((layer) => layer.id === "brows").asset;
  } });
  const duplicateIssues = diagnoseFrame(duplicate).issues;
  assert.ok(duplicateIssues.some((finding) => finding.code === "facial-asset-duplicate" && finding.severity === "error"));

  const painted = santaFrame({ mutate: (value) => {
    value.layers.find((layer) => layer.id === "head").asset = "assets/head.png";
  } });
  const paintedIssues = diagnoseFrame(painted).issues;
  assert.ok(paintedIssues.some((finding) => finding.code === "possible-painted-face-duplication" && finding.severity === "hypothesis"));
});

test("checks blink state without treating a closed eyelid as an error", () => {
  const closed = santaFrame({ pose: { ...santaFrame().pose, eye_open: 0 } });
  assert.equal(diagnoseFrame(closed).issues.some((finding) => finding.code === "blink-closed-state"), false);
  const incorrect = santaFrame({ mutate: (value) => { value.layers.find((layer) => layer.id === "eyelids").opacity = 1; } });
  assert.ok(diagnoseFrame(incorrect).issues.some((finding) => finding.code === "blink-open-state"));
});

test("reports insufficient evidence as a hypothesis", () => {
  const frame = santaFrame({ mutate: (value) => { value.landmarks = []; } });
  const issues = diagnoseFrame(frame).issues;
  assert.ok(issues.some((finding) => finding.code === "insufficient-landmarks" && finding.severity === "hypothesis"));
});

test("detects motion discontinuity and avoids claiming it with one frame", () => {
  const first = santaFrame({ timeMs: 0 });
  const second = santaFrame({ timeMs: 1000, mutate: (value) => { value.landmarks.find((landmark) => landmark.id === "rightWrist").stage.x += 3000; } });
  assert.ok(diagnoseMotion([first, second]).issues.some((finding) => finding.code === "motion-discontinuity"));
  assert.ok(diagnoseMotion([first]).issues.some((finding) => finding.code === "insufficient-motion-evidence" && finding.severity === "hypothesis"));
});

test("the controlled defect bank detects each introduced defect at the expected region", () => {
  const goodFrame = santaFrame();
  const fixtures = createKnownDefectFixtures(goodFrame);
  assert.equal(fixtures.length, 9);
  for (const fixture of fixtures) {
    const diagnostics = fixture.frames ? diagnoseMotion(fixture.frames) : diagnoseFrame(fixture.frame);
    const issues = diagnostics.issues;
    const matched = fixture.expectedCodes.filter((code) => issues.some((finding) => finding.code === code));
    assert.deepEqual(matched, fixture.expectedCodes, `${fixture.id}: ${JSON.stringify(issues)}`);
    assert.ok(resolveFixtureRegion(fixture, fixture.frame), `${fixture.id}: missing evidence region`);
  }
});

test("the preserved painted-face defect has a controlled correction path", () => {
  const goodFrame = santaFrame();
  const fixture = createKnownDefectFixtures(goodFrame).find((candidate) => candidate.id === "face-painted-duplicate");
  assert.ok(diagnoseFrame(fixture.frame).issues.some((finding) => finding.code === "possible-painted-face-duplication"));
  const corrected = correctFaceDuplicateFixture(fixture, goodFrame);
  assert.equal(diagnoseFrame(corrected).issues.some((finding) => finding.code === "possible-painted-face-duplication"), false);
  assert.equal(diagnoseFrame(corrected).issues.filter((finding) => finding.severity === "error").length, 0);
});

test("PNG comparison tolerates small antialiasing differences and emits evidence", () => {
  const base = Buffer.from([
    20, 30, 40, 255, 20, 30, 40, 255,
    20, 30, 40, 255, 20, 30, 40, 255,
  ]);
  const close = Buffer.from(base);
  close[0] += 5;
  const changed = Buffer.from(base);
  changed[0] = 240;
  changed[1] = 180;
  const reference = encodePng({ width: 2, height: 2, rgba: base });
  const tolerant = comparePngBuffers(reference, encodePng({ width: 2, height: 2, rgba: close }));
  assert.equal(tolerant.differingPixels, 0);
  const result = comparePngBuffers(reference, encodePng({ width: 2, height: 2, rgba: changed }));
  assert.equal(result.compatible, true);
  assert.equal(result.differingPixels, 1);
  assert.deepEqual(result.differenceBounds, { left: 0, top: 0, right: 1, bottom: 1, width: 1, height: 1 });
  assert.equal(decodePng(result.diffMaskPng).width, 2);
  assert.equal(decodePng(result.overlayPng).height, 2);
  const mismatch = comparePngBuffers(reference, encodePng({ width: 1, height: 1, rgba: Buffer.from([0, 0, 0, 255]) }));
  assert.equal(mismatch.compatible, false);
  const annotated = decodePng(annotatePng(reference, { regions: [{ left: 0, top: 0, right: 2, bottom: 2 }], color: [255, 0, 0, 255], lineWidth: 1 }));
  assert.deepEqual([...annotated.rgba.subarray(0, 4)], [255, 0, 0, 255]);
});

test("summarizes verified errors separately from review hypotheses", () => {
  const result = summarizeInspection({
    frameDiagnostics: [{ issues: [{ severity: "warning" }, { severity: "hypothesis" }] }],
    motionDiagnostics: [{ issues: [{ severity: "error" }] }],
  });
  assert.deepEqual(result.counts, { error: 1, warning: 1, hypothesis: 1 });
  assert.equal(result.status, "needs-correction");
});

test("transforms rectangles using all four corners", () => {
  const result = transformRect({ a: 0, b: 1, c: -1, d: 0, e: 10, f: 20 }, [0, 0, 2, 1]);
  assert.deepEqual(result, { left: 9, top: 20, right: 10, bottom: 22, width: 1, height: 2 });
});
