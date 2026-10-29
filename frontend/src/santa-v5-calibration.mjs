/**
 * Calibration metadata for the approved Santa V5 PNG layers.
 *
 * Bounds are measured from the decoded RGBA alpha channel. They are diagnostic
 * data only: the source images remain untouched and the runtime still uses
 * each image's intrinsic dimensions for deterministic Canvas rendering.
 */
export const SANTA_V5_ALPHA_BOUNDS = Object.freeze({
  "hair-back.png": [131, 159, 1117, 1026],
  "foot-left.png": [126, 244, 1133, 1158],
  "foot-right.png": [185, 106, 1066, 1224],
  "shin-left.png": [316, 0, 743, 1344],
  "shin-right.png": [300, 25, 730, 1392],
  "pelvis.png": [31, 45, 1230, 1168],
  "thigh-left.png": [207, 75, 884, 1444],
  "thigh-right.png": [263, 75, 782, 1469],
  "torso.png": [20, 4, 1121, 1334],
  "upper-arm-left.png": [90, 129, 969, 1396],
  "upper-arm-right.png": [113, 123, 949, 1411],
  "forearm-left.png": [71, 52, 993, 1476],
  "forearm-right.png": [135, 91, 972, 1482],
  "hand-left.png": [92, 205, 933, 1311],
  "hand-right.png": [101, 75, 982, 1244],
  "neck.png": [259, 209, 1280, 848],
  "head.png": [173, 41, 1112, 1152],
  "hair-front.png": [111, 78, 1425, 922],
  "eyes-open.png": [196, 278, 1579, 627],
  "eyelids-closed.png": [243, 290, 1609, 673],
  "brows.png": [133, 309, 1643, 612],
  "glasses.png": [51, 444, 1270, 782],
  "beard.png": [137, 415, 1198, 1093],
  "mouth-closed.png": [270, 255, 1264, 884],
});

export const SANTA_V5_EXPECTED_PIVOTS = Object.freeze({
  torso: [0.5, 0.5],
  pelvis: [0.5, 0.42],
  neck: [0.5, 0.55],
  head: [0.5, 0.54],
  left_upper_arm: [0.5, 0.08],
  right_upper_arm: [0.5, 0.08],
  left_forearm: [0.5, 0.08],
  right_forearm: [0.5, 0.08],
  left_hand: [0.5, 0.1],
  right_hand: [0.5, 0.1],
  left_thigh: [0.5, 0.08],
  right_thigh: [0.5, 0.08],
  left_shin: [0.5, 0.08],
  right_shin: [0.5, 0.08],
  left_foot: [0.5, 0.16],
  right_foot: [0.5, 0.16],
});

/**
 * Anatomical landmarks are normalized in the local intrinsic image of their
 * associated layer. Medium/low confidence marks joints hidden by the uniform
 * or inferred from adjacent pieces; they are not claimed as measurements.
 */
export const SANTA_V5_ANATOMICAL_LANDMARKS = Object.freeze([
  { id: "neck", layer: "neck", local: [0.5, 0.56], confidence: "medium", note: "centro estimado da gola visível" },
  { id: "leftShoulder", layer: "torso", local: [0.16, 0.15], confidence: "medium", note: "junção sob a ombreira esquerda; parcialmente oculta" },
  { id: "rightShoulder", layer: "torso", local: [0.84, 0.15], confidence: "medium", note: "junção sob a ombreira direita; parcialmente oculta" },
  { id: "leftElbow", layer: "left_upper_arm", local: [0.54, 0.53], confidence: "low", note: "inferido pela dobra da manga e pela posição do antebraço" },
  { id: "rightElbow", layer: "right_upper_arm", local: [0.46, 0.53], confidence: "low", note: "inferido pela dobra da manga e pela posição do antebraço" },
  { id: "leftWrist", layer: "left_forearm", local: [0.53, 0.72], confidence: "medium", note: "transição visível entre punho e mão" },
  { id: "rightWrist", layer: "right_forearm", local: [0.47, 0.72], confidence: "medium", note: "transição visível entre punho e mão" },
  { id: "hip", layer: "pelvis", local: [0.5, 0.42], confidence: "medium", note: "centro estimado do cós sob o casaco" },
  { id: "leftKnee", layer: "left_thigh", local: [0.5, 0.58], confidence: "low", note: "inferido pela continuidade entre coxa e canela" },
  { id: "rightKnee", layer: "right_thigh", local: [0.5, 0.58], confidence: "low", note: "inferido pela continuidade entre coxa e canela" },
  { id: "leftAnkle", layer: "left_shin", local: [0.5, 0.72], confidence: "medium", note: "ponto de encontro estimado com o cano da bota" },
  { id: "rightAnkle", layer: "right_shin", local: [0.5, 0.72], confidence: "medium", note: "ponto de encontro estimado com o cano da bota" },
]);

/**
 * Effective right-arm chain measured from the rendered neutral pack at
 * 1080x1920. The layer pivots are calibrated to the anatomical landmarks, so
 * an IK target controls the actual hand attachment point rather than a visual
 * approximation inside the painted asset. Angles use the Canvas convention
 * documented by `two-bone-ik.mjs`.
 */
export const SANTA_V5_RIGHT_ARM_IK_CALIBRATION = Object.freeze({
  frameWidth: 1080,
  frameHeight: 1920,
  shoulder: Object.freeze({ x: 782.352, y: 399.36 }),
  elbow: Object.freeze({ x: 772.65792, y: 666.8544 }),
  wrist: Object.freeze({ x: 767.2777056, y: 841.8551808 }),
  handTarget: Object.freeze({ x: 767.2777056, y: 841.8551808 }),
  upperLength: 267.6700005947742,
  forearmLength: 175.08346577446878,
  baseShoulderAngle: 1.60702078383754,
  baseElbowAngle: -0.005490192729581844,
  elbowPreference: Object.freeze({ x: 1, y: 0.55 }),
  restTarget: Object.freeze({ x: 767.2777056, y: 841.8551808 }),
  waveTarget: Object.freeze({ x: 840, y: 300 }),
});

/**
 * Affine geometry used by the real layered renderer for the right-arm chain.
 * The non-uniform scales are intentional: the painted arm pieces fit their
 * source boxes differently on X and Y. The IK adapter uses this metadata to
 * refine the analytic two-bone solution against the actual rendered endpoint.
 */
export const SANTA_V5_RIGHT_ARM_RENDER_GEOMETRY = Object.freeze({
  rootScale: Object.freeze({ x: 0.6258121158911326, y: 1.0010137581462708 }),
  upperScale: Object.freeze({ x: 0.37818359375, y: 0.3866080729166667 }),
  forearmScale: Object.freeze({ x: 0.74, y: 0.46 }),
  upperOffset: Object.freeze({ x: -40.96, y: 691.2 }),
  forearmOffset: Object.freeze({ x: -30.72, y: 983.04 }),
});

const finiteUnit = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;

/**
 * Check pack-level calibration invariants without decoding or mutating assets.
 * `errors` are contract failures. `warnings` are visual calibration hints and
 * are intentionally advisory because generated art may have soft margins.
 */
export function diagnoseSantaV5Calibration(pack, assetSizes = new Map()) {
  const errors = [];
  const warnings = [];
  const layerIds = new Set(pack.layers.map((layer) => layer.id));
  for (const layer of pack.layers) {
    if (!Array.isArray(layer.anchor) || layer.anchor.some((value) => !finiteUnit(value))) errors.push(`${layer.id}: invalid pivot`);
    if (!Array.isArray(layer.position) || layer.position.some((value) => !finiteUnit(value))) errors.push(`${layer.id}: invalid position`);
    if (!Array.isArray(layer.size) || layer.size.some((value) => !finiteUnit(value) || value === 0)) errors.push(`${layer.id}: invalid scale`);
    if (layer.parent !== null && !layerIds.has(layer.parent)) errors.push(`${layer.id}: missing parent ${layer.parent}`);
    const expected = SANTA_V5_EXPECTED_PIVOTS[layer.id];
    if (expected && layer.anchor.some((value, index) => Math.abs(value - expected[index]) > 0.24)) warnings.push(`${layer.id}: pivot is far from the expected joint region`);
    const size = assetSizes.get(layer.asset);
    const bounds = SANTA_V5_ALPHA_BOUNDS[layer.asset.split("/").pop()];
    if (size && bounds) {
      const [left, top, right, bottom] = bounds;
      const [width, height] = size;
      const margin = Math.min(left / width, top / height, (width - right) / width, (height - bottom) / height);
      if (margin > 0.22) warnings.push(`${layer.id}: large transparent margin may affect visual alignment`);
    }
  }
  return { errors, warnings, ok: errors.length === 0 };
}
