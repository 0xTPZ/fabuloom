import { boundsForLayers, pointBounds } from "../../frontend/src/visual-inspector-core.mjs";

export const DEFECT_FIXTURE_FORMAT = "fabuloom.visual-inspection-fixture/0.1";

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function layer(frame, id) {
  return frame.layers.find((candidate) => candidate.id === id);
}

function landmark(frame, id) {
  return frame.landmarks.find((candidate) => candidate.id === id);
}

function offsetBounds(bounds, dx = 0, dy = 0) {
  return { ...bounds, left: bounds.left + dx, top: bounds.top + dy, right: bounds.right + dx, bottom: bounds.bottom + dy };
}

function shrinkBounds(bounds, width, height = bounds.height) {
  const centerX = (bounds.left + bounds.right) / 2;
  const centerY = (bounds.top + bounds.bottom) / 2;
  return { left: centerX - width / 2, top: centerY - height / 2, right: centerX + width / 2, bottom: centerY + height / 2, width, height };
}

function mutateLayerBounds(frame, id, mutate) {
  const target = layer(frame, id);
  target.transformedAlphaBounds = mutate(target.transformedAlphaBounds);
  return frame;
}

function baseFixture({ id, label, defect, expectedCodes, expectedSeverity = "error", regionSpec, frame, notes = "" }) {
  return { format: DEFECT_FIXTURE_FORMAT, id, label, defect, expectedCodes, expectedSeverity, regionSpec, frame, notes };
}

/**
 * Construct controlled mutations from a known-good frame. Official PNGs and
 * pack descriptors remain untouched; every mutation lives in the returned
 * JSON fixture only.
 */
export function createKnownDefectFixtures(goodFrame) {
  const faceDuplicate = clone(goodFrame);
  const head = layer(faceDuplicate, "head");
  head.asset = head.asset.replace("head-clean.png", "head.png");
  head.assetName = "head.png";

  const eyesClosed = clone(goodFrame);
  eyesClosed.pose.eye_open = 1;
  layer(eyesClosed, "eyelids").opacity = 1;

  const handDisplaced = clone(goodFrame);
  mutateLayerBounds(handDisplaced, "right_hand", (bounds) => offsetBounds(bounds, 180, 0));

  const handSmall = clone(goodFrame);
  mutateLayerBounds(handSmall, "left_hand", (bounds) => shrinkBounds(bounds, 8, 8));

  const footDisplaced = clone(goodFrame);
  mutateLayerBounds(footDisplaced, "right_foot", (bounds) => offsetBounds(bounds, 0, 190));

  const shoulderDisconnected = clone(goodFrame);
  mutateLayerBounds(shoulderDisconnected, "left_upper_arm", (bounds) => offsetBounds(bounds, -180, 0));

  const forearmCrossing = clone(goodFrame);
  mutateLayerBounds(forearmCrossing, "right_forearm", (bounds) => offsetBounds(bounds, -400, 0));

  const proportionsAltered = clone(goodFrame);
  mutateLayerBounds(proportionsAltered, "head", (bounds) => shrinkBounds(bounds, 40, 80));

  const firstMotion = clone(goodFrame);
  const secondMotion = clone(goodFrame);
  firstMotion.timeMs = 0;
  secondMotion.timeMs = 1000;
  landmark(secondMotion, "rightWrist").stage.x += 3000;

  return [
    baseFixture({
      id: "face-painted-duplicate",
      label: "Cabeça com elementos faciais duplicados",
      defect: "painted-face-duplication",
      expectedCodes: ["possible-painted-face-duplication"],
      expectedSeverity: "hypothesis",
      regionSpec: { kind: "layers", layers: ["head", "eyes", "brows", "glasses", "beard", "mouth"] },
      frame: faceDuplicate,
      notes: "Reutiliza o head.png preservado como referência histórica; não altera o head-clean.png oficial.",
    }),
    baseFixture({
      id: "eyes-permanently-closed",
      label: "Olhos permanentemente fechados",
      defect: "blink-open-state",
      expectedCodes: ["blink-open-state"],
      regionSpec: { kind: "layers", layers: ["eyes", "eyelids"] },
      frame: eyesClosed,
      notes: "O frame declara eye_open=1, mas a camada fechada permanece opaca.",
    }),
    baseFixture({
      id: "hand-disconnected",
      label: "Mão deslocada do punho",
      defect: "visible-wrist-gap",
      expectedCodes: ["visible-joint-gap"],
      regionSpec: { kind: "layers", layers: ["right_forearm", "right_hand"] },
      frame: handDisplaced,
    }),
    baseFixture({
      id: "hand-too-small",
      label: "Mão com escala exageradamente pequena",
      defect: "hand-proportion",
      expectedCodes: ["proportion-outlier", "side-asymmetry"],
      expectedSeverity: "warning",
      regionSpec: { kind: "layers", layers: ["left_hand", "head"] },
      frame: handSmall,
    }),
    baseFixture({
      id: "foot-disconnected",
      label: "Pé deslocado da perna",
      defect: "visible-ankle-gap",
      expectedCodes: ["visible-joint-gap"],
      regionSpec: { kind: "layers", layers: ["right_shin", "right_foot"] },
      frame: footDisplaced,
    }),
    baseFixture({
      id: "shoulder-disconnected",
      label: "Ombro visualmente desconectado",
      defect: "visible-shoulder-gap",
      expectedCodes: ["visible-joint-gap"],
      regionSpec: { kind: "layers", layers: ["torso", "left_upper_arm"] },
      frame: shoulderDisconnected,
    }),
    baseFixture({
      id: "forearm-crosses-torso",
      label: "Antebraço atravessando o torso",
      defect: "anatomical-crossing",
      expectedCodes: ["anatomical-crossing", "visible-joint-gap"],
      regionSpec: { kind: "layers", layers: ["torso", "right_forearm"] },
      frame: forearmCrossing,
      notes: "A travessia é avaliada pelo lado do centro visível em relação ao torso; o overlap da articulação também é verificado.",
    }),
    baseFixture({
      id: "body-proportions-altered",
      label: "Proporções corporais alteradas",
      defect: "head-proportion",
      expectedCodes: ["proportion-outlier", "facial-region-outlier"],
      expectedSeverity: "warning",
      regionSpec: { kind: "layers", layers: ["head", "torso"] },
      frame: proportionsAltered,
    }),
    {
      format: DEFECT_FIXTURE_FORMAT,
      id: "motion-jump",
      label: "Salto repentino de articulação entre quadros",
      defect: "motion-discontinuity",
      expectedCodes: ["motion-discontinuity"],
      expectedSeverity: "error",
      regionSpec: { kind: "landmarks", landmarks: ["rightWrist"] },
      frames: [firstMotion, secondMotion],
      frame: secondMotion,
      notes: "A mudança ocorre entre 0 ms e 1000 ms; a sequência precisa ser analisada, não apenas o frame final.",
    },
  ];
}

export function resolveFixtureRegion(fixture, frame = fixture.frame) {
  const spec = fixture.regionSpec || {};
  if (spec.kind === "layers") return boundsForLayers(frame, spec.layers);
  if (spec.kind === "landmarks") {
    const points = (frame.landmarks || [])
      .filter((candidate) => spec.landmarks.includes(candidate.id))
      .map((candidate) => candidate.stage);
    return pointBounds(points);
  }
  return null;
}

export function correctFaceDuplicateFixture(fixture, goodFrame) {
  const corrected = clone(fixture.frame);
  const correctedHead = layer(corrected, "head");
  const goodHead = layer(goodFrame, "head");
  correctedHead.asset = goodHead.asset;
  correctedHead.assetName = goodHead.assetName;
  correctedHead.alphaBounds = [...goodHead.alphaBounds];
  correctedHead.transformedAlphaBounds = { ...goodHead.transformedAlphaBounds };
  return corrected;
}
