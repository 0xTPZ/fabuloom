/**
 * Small, provider-independent landmark helpers for layered character packs.
 *
 * Landmark coordinates are normalized to the intrinsic image of their layer.
 * They are estimates when the joint is hidden by clothing; callers should keep
 * the confidence and note fields when exporting calibration data.
 */
export const CHARACTER_LANDMARK_IDS = Object.freeze([
  "neck", "leftShoulder", "rightShoulder", "leftElbow", "rightElbow",
  "leftWrist", "rightWrist", "hip", "leftKnee", "rightKnee",
  "leftAnkle", "rightAnkle",
]);

export const CHARACTER_LANDMARK_CONNECTIONS = Object.freeze([
  ["neck", "leftShoulder"], ["neck", "rightShoulder"],
  ["leftShoulder", "leftElbow"], ["leftElbow", "leftWrist"],
  ["rightShoulder", "rightElbow"], ["rightElbow", "rightWrist"],
  ["hip", "leftKnee"], ["leftKnee", "leftAnkle"],
  ["hip", "rightKnee"], ["rightKnee", "rightAnkle"],
]);

const finiteUnit = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;

export function validateLandmarks(landmarks, layerIds = new Set()) {
  const errors = [];
  const ids = new Set();
  for (const landmark of landmarks || []) {
    if (!landmark || typeof landmark.id !== "string" || ids.has(landmark.id)) errors.push("landmark id must be unique");
    else ids.add(landmark.id);
    if (!Array.isArray(landmark.local) || landmark.local.length !== 2 || landmark.local.some((value) => !finiteUnit(value))) errors.push(`${landmark.id || "unknown"}: local coordinate must be normalized`);
    if (landmark.layer && layerIds.size && !layerIds.has(landmark.layer)) errors.push(`${landmark.id || "unknown"}: unknown layer ${landmark.layer}`);
    if (!["high", "medium", "low"].includes(landmark.confidence)) errors.push(`${landmark.id || "unknown"}: confidence must be high, medium or low`);
  }
  return { errors, ok: errors.length === 0 };
}

export function transformPoint(matrix, x, y) {
  return { x: matrix.a * x + matrix.c * y + matrix.e, y: matrix.b * x + matrix.d * y + matrix.f };
}

export function landmarkToStagePoint(landmark, plans) {
  const plan = Array.isArray(plans) ? plans.find((entry) => entry.layer.id === landmark.layer) : plans.get(landmark.layer);
  if (!plan) throw new Error(`landmark layer is not present in draw plan: ${landmark.layer}`);
  return transformPoint(plan.matrix, landmark.local[0] * plan.intrinsic[0], landmark.local[1] * plan.intrinsic[1]);
}

export function resolveLandmarks(landmarks, plans) {
  return landmarks.map((landmark) => ({ ...landmark, stage: landmarkToStagePoint(landmark, plans) }));
}

export function landmarkConnectionSegments(landmarks, plans) {
  const resolved = resolveLandmarks(landmarks, plans);
  const byId = new Map(resolved.map((landmark) => [landmark.id, landmark]));
  return CHARACTER_LANDMARK_CONNECTIONS.flatMap(([from, to]) => byId.has(from) && byId.has(to) ? [{ from, to, a: byId.get(from).stage, b: byId.get(to).stage }] : []);
}

export function distanceBetweenLandmarks(first, second, plans) {
  const a = landmarkToStagePoint(first, plans); const b = landmarkToStagePoint(second, plans);
  return Math.hypot(a.x - b.x, a.y - b.y);
}
