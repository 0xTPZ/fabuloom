/** Optional 2.5D layered character renderer. It consumes data-only packs. */

import { validateCharacterPack } from "./character-pack.mjs";

const IDENTITY = { a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 };

function multiply(left, right) {
  return {
    a: left.a * right.a + left.c * right.b,
    b: left.b * right.a + left.d * right.b,
    c: left.a * right.c + left.c * right.d,
    d: left.b * right.c + left.d * right.d,
    e: left.a * right.e + left.c * right.f + left.e,
    f: left.b * right.e + left.d * right.f + left.f,
  };
}

function translate(x, y) { return { a: 1, b: 0, c: 0, d: 1, e: x, f: y }; }
function rotate(angle) { const cos = Math.cos(angle); const sin = Math.sin(angle); return { a: cos, b: sin, c: -sin, d: cos, e: 0, f: 0 }; }
function scale(x, y) { return { a: x, b: 0, c: 0, d: y, e: 0, f: 0 }; }
function clamp(value, min = 0, max = 1) { return Math.max(min, Math.min(max, Number(value) || 0)); }

export function* frameSchedule(durationMs, fps = 30) {
  if (!Number.isFinite(durationMs) || durationMs < 0) throw new TypeError("durationMs must be finite and non-negative");
  if (!Number.isInteger(fps) || fps <= 0 || fps > 120) throw new TypeError("fps must be an integer in [1,120]");
  const frameCount = Math.ceil(durationMs / 1000 * fps);
  for (let index = 0; index < frameCount; index += 1) {
    yield { index, timeMs: Math.round(index * 1000 / fps) };
  }
}

function sourceSizeFor(layer, assetSizes) {
  return assetSizes.get(layer.asset) || layer.source_size || [1024, 1024];
}

function layerRotation(layer, pack, pose) {
  let rotation = 0;
  if (pack.bindings.head_rotation === layer.id) rotation += pose.head_rotation;
  if (pack.bindings.hair_sway === layer.id) rotation += pose.hair_sway;
  if (pack.bindings.left_arm === layer.id) rotation += pose.left_arm;
  if (pack.bindings.right_arm === layer.id) rotation += pose.right_arm;
  for (const [channel, target] of Object.entries(pack.bindings)) {
    if (target === layer.id && channel.endsWith("_rotation") && channel !== "head_rotation") {
      rotation += Number(pose[channel]) || 0;
    }
  }
  return rotation;
}

function layerTranslation(layer, pack, pose, frameWidth, frameHeight) {
  let x = 0;
  let y = 0;
  for (const [channel, target] of Object.entries(pack.bindings)) {
    if (target !== layer.id) continue;
    const value = Number(pose[channel]) || 0;
    if (channel.endsWith("_x")) x += value * frameWidth;
    if (channel.endsWith("_y")) y += value * frameHeight;
  }
  return [x, y];
}

/**
 * Resolve normalized pack coordinates into deterministic Canvas transforms.
 * Parent coordinates are expressed in the parent's rendered frame.
 */
export function buildLayerDrawPlan(pack, width, height, pose, assetSizes = new Map()) {
  const plans = new Map();
  const layers = [...pack.layers].sort((left, right) => left.z - right.z);

  const resolve = (layer) => {
    if (plans.has(layer.id)) return plans.get(layer.id);
    const parent = layer.parent === null ? null : resolve(pack.layers.find((candidate) => candidate.id === layer.parent));
    const intrinsic = sourceSizeFor(layer, assetSizes);
    const frameWidth = parent ? parent.intrinsic[0] : width;
    const frameHeight = parent ? parent.intrinsic[1] : height;
    const requestedSize = Array.isArray(layer.size) ? layer.size : parent ? [1, 1] : [0.7, 0.9];
    const drawWidth = frameWidth * requestedSize[0];
    const drawHeight = frameHeight * requestedSize[1];
    const position = layer.position || [0.5, 0.5];
    const anchor = layer.anchor || [0.5, 0.5];

    let local = IDENTITY;
    local = multiply(local, translate(frameWidth * position[0], frameHeight * position[1]));
    const [offsetX, offsetY] = layerTranslation(layer, pack, pose, frameWidth, frameHeight);
    if (offsetX || offsetY) local = multiply(local, translate(offsetX, offsetY));
    local = multiply(local, rotate(layerRotation(layer, pack, pose)));
    let animatedY = 1;
    let animatedOpacity = layer.opacity === undefined ? 1 : clamp(layer.opacity);
    if (pack.bindings.eye_open === layer.id) {
      // Eyelids are authored as a closed-state overlay.  They must disappear
      // in the open state; scaling the bitmap alone leaves closed eyes visible
      // in every neutral frame and can also distort the eyelid artwork.
      const eyeOpen = clamp(pose.eye_open);
      animatedOpacity *= 1 - eyeOpen;
    }
    if (pack.bindings.mouth_open === layer.id) {
      // Facial packs may use a combined lower-face plate (beard + lips). In
      // that case switching the plate is safer than stretching the beard.
      // Legacy packs keep the original expressive Y scale by default.
      animatedY = layer.mouth_motion === "subtle"
        ? 0.96 + clamp(pose.mouth_open) * 0.08
        : 0.58 + clamp(pose.mouth_open) * 0.95;
    }
    if (pack.bindings.breathing === layer.id) {
      local = multiply(local, translate(0, (pose.breathing - 0.5) * frameHeight * 0.012));
    }
    if (pack.bindings.brow_raise === layer.id) {
      local = multiply(local, translate(0, -clamp(pose.brow_raise) * frameHeight * 0.018));
    }
    const breathingScale = pack.bindings.breathing === layer.id
      ? 1 + (clamp(pose.breathing) - 0.5) * 0.018
      : 1;
    local = multiply(local, scale(drawWidth / intrinsic[0], (drawHeight / intrinsic[1]) * animatedY * breathingScale));
    local = multiply(local, translate(-anchor[0] * intrinsic[0], -anchor[1] * intrinsic[1]));

    const plan = {
      layer,
      matrix: parent ? multiply(parent.matrix, local) : local,
      drawWidth,
      drawHeight,
      intrinsic,
      opacity: animatedOpacity,
    };
    plans.set(layer.id, plan);
    return plan;
  };

  return layers.map(resolve);
}

export class LayeredCharacterRig {
  constructor() {
    this.speechAmplitude = 0;
    this.currentExpression = "neutral";
    this.currentPose = {
      breathing: 0,
      head_rotation: 0,
      eye_open: 1,
      mouth_open: 0,
      hair_sway: 0,
      brow_raise: 0,
      left_arm: 0,
      right_arm: 0,
    };
  }

  setSpeechAmplitude(amplitude) { this.speechAmplitude = clamp(amplitude); }
  setExpression(expressionId) { this.currentExpression = expressionId; }

  /**
   * Resolve a pose from absolute time only. Keeping this function pure with
   * respect to the clock makes seek and out-of-order frame capture repeatable.
   */
  poseAt(timeMs, isPlaying) {
    const safeTimeMs = Number.isFinite(timeMs) ? Math.max(0, timeMs) : 0;
    const seconds = safeTimeMs / 1000;
    const breathing = (Math.sin(seconds * Math.PI * 1.8) + 1) / 2;
    const headRotation = Math.sin(seconds * 0.48) * 0.038 + Math.sin(seconds * 0.21) * 0.016;
    const hairSway = Math.sin(seconds * 0.67) * 0.009;
    const pulse = (center, width, amount) => {
      const phase = ((safeTimeMs / 1000) % 8 + 8) % 8;
      return Math.exp(-(((phase - center) / width) ** 2)) * amount;
    };
    // Two repeatable presenter gestures are deliberately larger than idle
    // sway, while remaining small enough to look natural over long narration.
    const leftArm = Math.sin(seconds * 0.42 + 0.8) * 0.018
      + pulse(1.8, 0.42, 0.20)
      + pulse(6.8, 0.48, -0.075);
    const rightArm = Math.sin(seconds * 0.39 + 2.1) * 0.014
      + pulse(4.6, 0.46, -0.22)
      + pulse(7.5, 0.42, 0.09);
    const browRaise = isPlaying ? (Math.sin(seconds * 0.9) + 1) * 0.12 : 0;
    let eyeOpen = 1;
    const blinkPhase = safeTimeMs % 5200;
    if (blinkPhase >= 4200 && blinkPhase <= 4460) {
      const elapsed = blinkPhase - 4200;
      if (elapsed <= 130) eyeOpen = 1 - elapsed / 130;
      else eyeOpen = (elapsed - 130) / 130;
    }
    return {
      breathing,
      head_rotation: headRotation,
      eye_open: eyeOpen,
      mouth_open: isPlaying ? this.speechAmplitude : 0,
      hair_sway: hairSway,
      brow_raise: browRaise,
      left_arm: leftArm,
      right_arm: rightArm,
    };
  }

  update(timeMs, isPlaying) {
    this.currentPose = this.poseAt(timeMs, isPlaying);
  }

  pose() { return { ...this.currentPose }; }
}

function drawStageBackground(ctx, width, height) {
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, "#182b49");
  gradient.addColorStop(1, "#080f1d");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = "rgba(109, 160, 255, 0.10)";
  ctx.beginPath();
  ctx.ellipse(width * 0.5, height * 0.89, width * 0.31, height * 0.075, 0, 0, Math.PI * 2);
  ctx.fill();
}

export class LayeredCharacterRenderer {
  constructor(canvas, rig, pack, options = {}) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.rig = rig;
    this.pack = validateCharacterPack(pack);
    this.assetRoot = options.assetRoot || globalThis.document?.baseURI || "http://127.0.0.1/";
    this.renderBackground = options.renderBackground !== false;
    this.images = new Map();
    this.loaded = false;
    this.expression = "neutral";
    this.assetResolver = options.assetResolver || null;
    this.layerVisibility = options.layerVisibility || null;
  }

  async load() {
    const assets = new Set(this.pack.layers.map((layer) => layer.asset));
    for (const expression of this.pack.expressions) {
      for (const asset of Object.values(expression.overrides)) assets.add(asset);
    }
    await Promise.all([...assets].map((asset) => this.loadImage(asset)));
    this.loaded = true;
    return this;
  }

  loadImage(asset) {
    if (this.images.has(asset)) return this.images.get(asset).promise;
    const record = { image: null, size: [0, 0], promise: null };
    this.images.set(asset, record);
    const promise = new Promise((resolve, reject) => {
      const image = new Image();
      record.image = image;
      image.onload = () => { record.size = [image.naturalWidth || image.width, image.naturalHeight || image.height]; resolve(image); };
      image.onerror = () => reject(new Error(`could not load character asset: ${asset}`));
      image.src = new URL(asset, this.assetRoot).href;
    });
    record.promise = promise;
    return promise;
  }

  setExpression(expressionId) {
    if (!this.pack.expressions.some((expression) => expression.id === expressionId)) throw new Error(`Unknown character expression: ${expressionId}`);
    this.expression = expressionId;
    this.rig.setExpression(expressionId);
  }

  setAssetResolver(resolver) {
    if (resolver !== null && typeof resolver !== "function") throw new TypeError("asset resolver must be a function or null");
    this.assetResolver = resolver;
  }

  setLayerVisibility(visibility) {
    if (visibility !== null && typeof visibility !== "function") throw new TypeError("layer visibility must be a function or null");
    this.layerVisibility = visibility;
  }

  /**
   * Render one deterministic frame through the same rig used by Character Stage.
   * This is the boundary consumed by a future local frame encoder.
   */
  renderFrame({ timeMs = 0, speechAmplitude = 0, isPlaying = true } = {}) {
    this.rig.setSpeechAmplitude(speechAmplitude);
    this.rig.update(timeMs, isPlaying);
    this.render();
    return this.canvas;
  }

  /**
   * Expose the resolved plan used by render(). Scene composition can anchor a
   * prop to the same transformed hand or other layer without recreating the
   * hierarchy with a second set of coordinates.
   */
  getLayerDrawPlan() {
    if (!this.loaded) return [];
    const assetSizes = new Map([...this.images.entries()].map(([asset, record]) => [asset, record.size]));
    return buildLayerDrawPlan(this.pack, this.canvas.width, this.canvas.height, this.rig.pose(), assetSizes);
  }

  resolvedAsset(layer) {
    const expression = this.pack.expressions.find((candidate) => candidate.id === this.expression);
    const expressionAsset = expression?.overrides?.[layer.id] || layer.asset;
    return this.assetResolver?.(layer, this.rig.pose(), expressionAsset) || expressionAsset;
  }

  render() {
    const ctx = this.context;
    const width = this.canvas.width;
    const height = this.canvas.height;
    if (this.renderBackground) {
      drawStageBackground(ctx, width, height);
    } else {
      ctx.clearRect(0, 0, width, height);
    }
    if (!this.loaded) return;
    const plans = this.getLayerDrawPlan();
    for (const plan of plans) {
      if (this.layerVisibility && !this.layerVisibility(plan.layer, this.rig.pose())) continue;
      const asset = this.resolvedAsset(plan.layer);
      const record = this.images.get(asset);
      if (!record?.image) continue;
      ctx.save();
      const matrix = plan.matrix;
      ctx.transform(matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f);
      ctx.globalAlpha = plan.opacity;
      ctx.drawImage(record.image, 0, 0, plan.intrinsic[0], plan.intrinsic[1]);
      ctx.restore();
    }
  }
}

function canvasBlob(canvas, type = "image/png") {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("canvas frame encoding returned no blob")), type);
  });
}

/**
 * Stream frames without retaining the complete video in browser memory.
 * `onFrame` can forward each PNG to a local encoder or persist a short preview.
 */
export async function captureLayeredFrames(renderer, {
  durationMs,
  fps = 30,
  isPlaying = true,
  amplitudeAt = () => 0,
  onFrame,
  signal,
} = {}) {
  if (!(renderer instanceof LayeredCharacterRenderer)) throw new TypeError("renderer must be a LayeredCharacterRenderer");
  if (typeof onFrame !== "function") throw new TypeError("onFrame callback is required");
  let count = 0;
  for (const frame of frameSchedule(durationMs, fps)) {
    if (signal?.aborted) throw new DOMException("frame capture aborted", "AbortError");
    renderer.renderFrame({ timeMs: frame.timeMs, speechAmplitude: amplitudeAt(frame.timeMs), isPlaying });
    const blob = await canvasBlob(renderer.canvas);
    await onFrame({ ...frame, blob });
    count += 1;
  }
  return { frameCount: count, durationMs, fps };
}
