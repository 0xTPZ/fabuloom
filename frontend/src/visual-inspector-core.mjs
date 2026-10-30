/**
 * Fabuloom Visual Inspector V1, browser-safe analysis primitives.
 *
 * This module intentionally consumes resolved draw-plan data instead of a
 * Santa-specific renderer. A capture adapter may provide any character pack
 * that exposes the same layer/pivot/landmark concepts.
 */

export const VISUAL_INSPECTION_FORMAT = "fabuloom.visual-inspection/0.1";

const FACE_LAYER_IDS = new Set(["head", "eyes", "eyelids", "brows", "glasses", "beard", "mouth"]);
const FACE_OVERLAY_IDS = new Set(["eyes", "eyelids", "brows", "glasses", "beard", "mouth"]);

const finite = (value) => typeof value === "number" && Number.isFinite(value);
const basename = (asset) => String(asset || "").split(/[\\/]/).pop() || "";
const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, Number(value) || 0));

export function transformPoint(matrix, x, y) {
  return {
    x: matrix.a * x + matrix.c * y + matrix.e,
    y: matrix.b * x + matrix.d * y + matrix.f,
  };
}

export function transformRect(matrix, rect) {
  const [left, top, right, bottom] = rect;
  const points = [
    transformPoint(matrix, left, top),
    transformPoint(matrix, right, top),
    transformPoint(matrix, right, bottom),
    transformPoint(matrix, left, bottom),
  ];
  const minX = Math.min(...points.map((point) => point.x));
  const minY = Math.min(...points.map((point) => point.y));
  const maxX = Math.max(...points.map((point) => point.x));
  const maxY = Math.max(...points.map((point) => point.y));
  return { left: minX, top: minY, right: maxX, bottom: maxY, width: maxX - minX, height: maxY - minY };
}

export function defaultInspectionConfig() {
  return {
    jointChecks: [
      { id: "left-shoulder", landmark: "leftShoulder", pivotLayer: "left_upper_arm", maxDistancePx: 100, label: "ombro esquerdo → braço" },
      { id: "right-shoulder", landmark: "rightShoulder", pivotLayer: "right_upper_arm", maxDistancePx: 100, label: "ombro direito → braço" },
      { id: "left-elbow", landmark: "leftElbow", pivotLayer: "left_forearm", maxDistancePx: 100, label: "cotovelo esquerdo → antebraço" },
      { id: "right-elbow", landmark: "rightElbow", pivotLayer: "right_forearm", maxDistancePx: 100, label: "cotovelo direito → antebraço" },
      { id: "left-wrist", landmark: "leftWrist", pivotLayer: "left_hand", maxDistancePx: 100, label: "punho esquerdo → mão" },
      { id: "right-wrist", landmark: "rightWrist", pivotLayer: "right_hand", maxDistancePx: 100, label: "punho direito → mão" },
      { id: "left-ankle", landmark: "leftAnkle", pivotLayer: "left_foot", maxDistancePx: 125, label: "tornozelo esquerdo → pé" },
      { id: "right-ankle", landmark: "rightAnkle", pivotLayer: "right_foot", maxDistancePx: 125, label: "tornozelo direito → pé" },
    ],
    proportionChecks: [
      { id: "head-torso", numerator: "head", denominator: "torso", metric: "width", min: 0.25, max: 1.8, label: "largura da cabeça / tronco" },
      { id: "hands-head", numerator: "left_hand", denominator: "head", metric: "width", min: 0.05, max: 1.0, label: "largura da mão / cabeça" },
      { id: "feet-torso", numerator: "left_foot", denominator: "torso", metric: "width", min: 0.05, max: 1.0, label: "largura do pé / tronco" },
    ],
    symmetryChecks: [
      { id: "hands-symmetry", left: "left_hand", right: "right_hand", metric: "width", minRatio: 0.55, label: "simetria de mãos" },
      { id: "feet-symmetry", left: "left_foot", right: "right_foot", metric: "width", minRatio: 0.55, label: "simetria de pés" },
    ],
    maxLandmarkSpeedPxPerSecond: 1800,
  };
}

function issue({ code, severity, confidence, message, evidence = {}, relatedLayers = [] }) {
  return { code, severity, confidence, message, evidence, relatedLayers };
}

function layerCenter(layer) {
  const bounds = layer?.transformedAlphaBounds;
  return bounds ? { x: (bounds.left + bounds.right) / 2, y: (bounds.top + bounds.bottom) / 2 } : null;
}

function ratioFor(left, right, metric) {
  const a = Number(left?.transformedAlphaBounds?.[metric]);
  const b = Number(right?.transformedAlphaBounds?.[metric]);
  if (!finite(a) || !finite(b) || b <= 0) return null;
  return a / b;
}

export function buildInspectionFrame({
  characterId,
  pack,
  plans,
  resolvedAssets = {},
  pose = {},
  timeMs = 0,
  isPlaying = false,
  animationId = null,
  expression = "neutral",
  width,
  height,
  alphaBounds = {},
  landmarks = [],
  resourceErrors = [],
  consoleErrors = [],
  view = "full",
} = {}) {
  const layers = plans.map((plan) => {
    const asset = resolvedAssets[plan.layer.id] || plan.layer.asset;
    const alpha = alphaBounds[basename(asset)] || [0, 0, plan.intrinsic[0], plan.intrinsic[1]];
    const pivot = transformPoint(plan.matrix, plan.layer.anchor[0] * plan.intrinsic[0], plan.layer.anchor[1] * plan.intrinsic[1]);
    return {
      id: plan.layer.id,
      role: plan.layer.role || null,
      parent: plan.layer.parent,
      z: plan.layer.z,
      asset,
      assetName: basename(asset),
      intrinsicSize: { width: plan.intrinsic[0], height: plan.intrinsic[1] },
      drawSize: { width: plan.drawWidth, height: plan.drawHeight },
      anchor: [...plan.layer.anchor],
      position: [...plan.layer.position],
      matrix: { ...plan.matrix },
      opacity: plan.opacity,
      alphaBounds: [...alpha],
      pivot,
      transformedAlphaBounds: transformRect(plan.matrix, alpha),
    };
  });
  return {
    format: VISUAL_INSPECTION_FORMAT,
    characterId: characterId || pack?.id || null,
    characterFormat: pack?.format || null,
    timeMs: Math.max(0, Math.round(Number(timeMs) || 0)),
    isPlaying: Boolean(isPlaying),
    animationId,
    expression,
    canvas: { width, height },
    pose: Object.fromEntries(Object.entries(pose).filter(([, value]) => finite(value))),
    layers,
    landmarks: landmarks.map((landmark) => ({
      id: landmark.id,
      layer: landmark.layer,
      local: landmark.local ? [...landmark.local] : null,
      confidence: landmark.confidence || "unknown",
      stage: landmark.stage ? { x: landmark.stage.x, y: landmark.stage.y } : null,
    })),
    resourceErrors: [...resourceErrors],
    consoleErrors: [...consoleErrors],
    view,
  };
}

export function diagnoseFrame(frame, config = {}) {
  const defaults = defaultInspectionConfig();
  const options = {
    ...defaults,
    ...config,
    jointChecks: config.jointChecks || defaults.jointChecks,
    proportionChecks: config.proportionChecks || defaults.proportionChecks,
    symmetryChecks: config.symmetryChecks || defaults.symmetryChecks,
  };
  const issues = [];
  const layerMap = new Map((frame.layers || []).map((layer) => [layer.id, layer]));
  const landmarkMap = new Map((frame.landmarks || []).map((landmark) => [landmark.id, landmark]));
  const scale = Math.max(0.1, Number(frame.canvas?.width || 1080) / 1080);
  const add = (data) => issues.push(data);

  if (!frame.layers?.length) {
    add(issue({ code: "missing-layers", severity: "error", confidence: "high", message: "O quadro não contém camadas resolvidas." }));
  }
  for (const error of frame.resourceErrors || []) {
    add(issue({ code: "resource-load", severity: "error", confidence: "high", message: `Recurso não carregado: ${error}`, evidence: { resource: error } }));
  }
  for (const error of frame.consoleErrors || []) {
    add(issue({ code: "console-error", severity: "warning", confidence: "high", message: `Erro de console durante a captura: ${error}`, evidence: { console: error } }));
  }

  const facial = (frame.layers || []).filter((layer) => FACE_LAYER_IDS.has(layer.id));
  const facialAssets = new Map();
  for (const layer of facial) {
    const previous = facialAssets.get(layer.asset);
    if (previous) {
      add(issue({
        code: "facial-asset-duplicate",
        severity: "error",
        confidence: "high",
        message: `Camadas faciais reutilizam o mesmo asset: ${previous.id} e ${layer.id}.`,
        evidence: { asset: layer.asset, layers: [previous.id, layer.id] },
        relatedLayers: [previous.id, layer.id],
      }));
    } else facialAssets.set(layer.asset, layer);
  }
  const head = layerMap.get("head");
  if (head && basename(head.asset) === "head.png" && facial.some((layer) => FACE_OVERLAY_IDS.has(layer.id))) {
    add(issue({
      code: "possible-painted-face-duplication",
      severity: "hypothesis",
      confidence: "medium",
      message: "A cabeça usa head.png junto com overlays faciais; o asset pode já conter elementos duplicados.",
      evidence: { headAsset: head.asset, overlays: facial.filter((layer) => FACE_OVERLAY_IDS.has(layer.id)).map((layer) => layer.id) },
      relatedLayers: ["head", ...facial.filter((layer) => FACE_OVERLAY_IDS.has(layer.id)).map((layer) => layer.id)],
    }));
  }

  const eyeOpen = Number(frame.pose?.eye_open);
  const eyelids = layerMap.get("eyelids");
  if (eyelids && finite(eyeOpen)) {
    if (eyeOpen > 0.95 && eyelids.opacity > 0.05) {
      add(issue({ code: "blink-open-state", severity: "error", confidence: "high", message: "A camada de pálpebras aparece no estado de olhos abertos.", evidence: { eyeOpen, eyelidOpacity: eyelids.opacity }, relatedLayers: ["eyelids"] }));
    } else if (eyeOpen < 0.05 && eyelids.opacity < 0.9) {
      add(issue({ code: "blink-closed-state", severity: "warning", confidence: "medium", message: "A piscada declarada não torna a camada de pálpebras suficientemente visível.", evidence: { eyeOpen, eyelidOpacity: eyelids.opacity }, relatedLayers: ["eyelids"] }));
    }
  }

  if (head?.transformedAlphaBounds) {
    const bounds = head.transformedAlphaBounds;
    const marginX = bounds.width * 0.35;
    const marginY = bounds.height * 0.35;
    for (const layer of facial.filter((candidate) => FACE_OVERLAY_IDS.has(candidate.id))) {
      const center = layerCenter(layer);
      const inside = center && center.x >= bounds.left - marginX && center.x <= bounds.right + marginX
        && center.y >= bounds.top - marginY && center.y <= bounds.bottom + marginY;
      if (!inside) {
        add(issue({ code: "facial-region-outlier", severity: "warning", confidence: "medium", message: `A camada facial ${layer.id} está fora da região esperada da cabeça.`, evidence: { layer: layer.id, center, headBounds: bounds }, relatedLayers: ["head", layer.id] }));
      }
    }
  }

  for (const check of options.jointChecks) {
    const landmark = landmarkMap.get(check.landmark);
    const layer = layerMap.get(check.pivotLayer);
    if (!landmark?.stage || !layer?.pivot) {
      add(issue({ code: "insufficient-joint-evidence", severity: "hypothesis", confidence: "low", message: `Evidência insuficiente para ${check.label || check.id}.`, evidence: { landmark: check.landmark, pivotLayer: check.pivotLayer }, relatedLayers: [check.pivotLayer] }));
      continue;
    }
    const distance = Math.hypot(landmark.stage.x - layer.pivot.x, landmark.stage.y - layer.pivot.y);
    const threshold = check.maxDistancePx * scale;
    if (distance > threshold) {
      add(issue({ code: "joint-gap", severity: "error", confidence: "high", message: `${check.label || check.id} está separado por ${distance.toFixed(1)} px.`, evidence: { distancePx: distance, thresholdPx: threshold, landmark: landmark.stage, pivot: layer.pivot }, relatedLayers: [check.pivotLayer] }));
    }
  }

  for (const check of options.proportionChecks) {
    const numerator = layerMap.get(check.numerator);
    const denominator = layerMap.get(check.denominator);
    const ratio = ratioFor(numerator, denominator, check.metric || "width");
    if (ratio === null) {
      add(issue({ code: "insufficient-proportion-evidence", severity: "hypothesis", confidence: "low", message: `Evidência insuficiente para ${check.label || check.id}.`, evidence: { numerator: check.numerator, denominator: check.denominator } }));
    } else if (ratio < check.min || ratio > check.max) {
      add(issue({ code: "proportion-outlier", severity: "warning", confidence: "medium", message: `${check.label || check.id} resultou em razão ${ratio.toFixed(3)} fora do intervalo configurado.`, evidence: { ratio, min: check.min, max: check.max }, relatedLayers: [check.numerator, check.denominator] }));
    }
  }

  for (const check of options.symmetryChecks) {
    const left = layerMap.get(check.left);
    const right = layerMap.get(check.right);
    const leftValue = Number(left?.transformedAlphaBounds?.[check.metric || "width"]);
    const rightValue = Number(right?.transformedAlphaBounds?.[check.metric || "width"]);
    if (!finite(leftValue) || !finite(rightValue) || Math.max(leftValue, rightValue) <= 0) continue;
    const ratio = Math.min(leftValue, rightValue) / Math.max(leftValue, rightValue);
    if (ratio < check.minRatio) {
      add(issue({ code: "side-asymmetry", severity: "warning", confidence: "medium", message: `${check.label || check.id} tem razão esquerda/direita ${ratio.toFixed(3)} abaixo do limite configurado.`, evidence: { ratio, minRatio: check.minRatio, left: leftValue, right: rightValue }, relatedLayers: [check.left, check.right] }));
    }
  }

  if (!(frame.landmarks || []).some((landmark) => landmark.stage)) {
    add(issue({ code: "insufficient-landmarks", severity: "hypothesis", confidence: "low", message: "O quadro não possui landmarks resolvidos; diagnósticos anatômicos não podem ser confirmados." }));
  }
  return { frameTimeMs: frame.timeMs, issues };
}

export function diagnoseMotion(frames, config = {}) {
  const maxSpeed = Number(config.maxLandmarkSpeedPxPerSecond || defaultInspectionConfig().maxLandmarkSpeedPxPerSecond);
  const ordered = [...frames].filter((frame) => Array.isArray(frame.landmarks)).sort((a, b) => a.timeMs - b.timeMs);
  const issues = [];
  if (ordered.length < 2) {
    return { issues: [issue({ code: "insufficient-motion-evidence", severity: "hypothesis", confidence: "low", message: "São necessários pelo menos dois quadros da mesma sequência para avaliar continuidade.", evidence: { frameCount: ordered.length } })] };
  }
  for (let index = 1; index < ordered.length; index += 1) {
    const previous = ordered[index - 1];
    const current = ordered[index];
    const dt = (current.timeMs - previous.timeMs) / 1000;
    if (!(dt > 0)) continue;
    const previousLandmarks = new Map(previous.landmarks.filter((landmark) => landmark.stage).map((landmark) => [landmark.id, landmark.stage]));
    for (const landmark of current.landmarks.filter((candidate) => candidate.stage)) {
      const old = previousLandmarks.get(landmark.id);
      if (!old) continue;
      const distance = Math.hypot(landmark.stage.x - old.x, landmark.stage.y - old.y);
      const speed = distance / dt;
      if (speed > maxSpeed) {
        issues.push(issue({ code: "motion-discontinuity", severity: "error", confidence: "high", message: `O landmark ${landmark.id} saltou a ${speed.toFixed(1)} px/s.`, evidence: { fromMs: previous.timeMs, toMs: current.timeMs, distancePx: distance, speedPxPerSecond: speed, maxSpeedPxPerSecond: maxSpeed } }));
      }
    }
  }
  return { issues };
}

export function summarizeInspection({ frameDiagnostics = [], motionDiagnostics = [], captureErrors = [] } = {}) {
  const issues = [...frameDiagnostics.flatMap((entry) => entry.issues || []), ...motionDiagnostics.flatMap((entry) => entry.issues || [])];
  const counts = { error: 0, warning: 0, hypothesis: 0 };
  for (const finding of issues) if (counts[finding.severity] !== undefined) counts[finding.severity] += 1;
  const status = captureErrors.length || counts.error ? "needs-correction" : counts.warning || counts.hypothesis ? "needs-review" : "no-verified-errors";
  return { status, counts, total: issues.length, captureErrors: [...captureErrors] };
}
