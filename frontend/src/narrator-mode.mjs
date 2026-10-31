/**
 * Fabuloom Narrator Mode V1.
 *
 * The mode intentionally owns a small facial composition instead of reusing
 * the full-body Character Stage. It still consumes the same V5 face assets,
 * layer transforms and RMS envelope, so a browser preview and offline frame
 * capture share one deterministic implementation.
 */

import { LayeredCharacterRenderer, LayeredCharacterRig } from "./layered-character.ts";
import { SANTA_V5_PACK } from "./santa-v5-pack.mjs";
import { validateCharacterPack } from "./character-pack.mjs";

export const NARRATOR_MODE_FORMAT = "fabuloom.narrator-mode/0.1";
export const NARRATOR_SCENE_FORMAT = "fabuloom.narrator-scene/0.1";
export const NARRATOR_FPS = 30;
export const NARRATOR_CANVAS = Object.freeze({ width: 1920, height: 1080 });
export const NARRATOR_AVATAR_DEFAULT = Object.freeze({ x: 74, y: 676, size: 330, borderWidth: 8 });
export const NARRATOR_SOURCE_CANVAS = Object.freeze({ width: 1080, height: 1920 });
export const NARRATOR_FACE_CROP = Object.freeze({ x: 245, y: 35, width: 590, height: 590 });
export const NARRATOR_FACE_SAFE_AREA = Object.freeze({ left: 0.06, top: 0.035, right: 0.94, bottom: 0.965 });
export const NARRATOR_FACE_REFERENCE = Object.freeze({
  width: 1316,
  height: 1195,
  coordinateSystem: "head-local-v1",
  landmarks: Object.freeze({
    headCenter: Object.freeze({ x: 658, y: 598 }),
    leftEye: Object.freeze({ x: 526, y: 540 }),
    rightEye: Object.freeze({ x: 790, y: 540 }),
    nose: Object.freeze({ x: 658, y: 650 }),
    glasses: Object.freeze({ x: 658, y: 540 }),
    brows: Object.freeze({ x: 658, y: 390 }),
    moustache: Object.freeze({ x: 658, y: 710 }),
    mouth: Object.freeze({ x: 658, y: 785 }),
    beardBase: Object.freeze({ x: 658, y: 1035 }),
  }),
});

// Measured alpha bounds in each official facial PNG. These values are used to
// position the painted pixels, not the transparent bitmap rectangles.
export const NARRATOR_FACE_ALPHA_BOUNDS = Object.freeze({
  "hair-front.png": Object.freeze([111, 78, 1425, 921]),
  "eyes-open.png": Object.freeze([196, 279, 1579, 627]),
  "eyelids-closed.png": Object.freeze([243, 291, 1609, 673]),
  "brows.png": Object.freeze([133, 310, 1643, 612]),
  "glasses.png": Object.freeze([51, 444, 1270, 781]),
  "mouth-closed.png": Object.freeze([270, 255, 1263, 884]),
});

export const NARRATOR_FACE_ALPHA_TARGETS = Object.freeze({
  hair_front: Object.freeze([95, 25, 1220, 820]),
  eyes: Object.freeze([400, 460, 930, 620]),
  eyelids: Object.freeze([400, 460, 930, 620]),
  brows: Object.freeze([390, 330, 930, 450]),
  glasses: Object.freeze([360, 430, 960, 650]),
  mouth: Object.freeze([350, 625, 970, 1045]),
});

const FACE_LAYER_IDS = new Set([
  "neck", "hair_back", "head", "hair_front", "eyes", "eyelids", "brows", "glasses", "beard", "mouth",
]);
const FACE_ORDER = ["hair_back", "neck", "head", "hair_front", "eyes", "eyelids", "brows", "glasses", "beard", "mouth"];
const finite = (value) => typeof value === "number" && Number.isFinite(value);
const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, Number(value) || 0));

function assertPositiveInteger(value, label) {
  if (!Number.isInteger(value) || value <= 0) throw new TypeError(`${label} must be a positive integer`);
}

function assertUnitInterval(value, label) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 1) throw new TypeError(`${label} must be in [0,1]`);
}

export function validateNarratorFaceCrop(crop = NARRATOR_FACE_CROP) {
  if (!crop || typeof crop !== "object") throw new TypeError("face crop must be an object");
  const values = [crop.x, crop.y, crop.width, crop.height];
  if (!values.every((value) => Number.isFinite(value))) throw new TypeError("face crop must contain finite values");
  if (crop.width <= 0 || crop.height <= 0 || crop.width !== crop.height) throw new TypeError("face crop must be a positive square");
  if (crop.x < 0 || crop.y < 0 || crop.x + crop.width > NARRATOR_SOURCE_CANVAS.width || crop.y + crop.height > NARRATOR_SOURCE_CANVAS.height) {
    throw new RangeError("face crop must stay inside the narrator source canvas");
  }
  return Object.freeze({ x: crop.x, y: crop.y, width: crop.width, height: crop.height });
}

export function validateNarratorFaceSafeArea(safeArea = NARRATOR_FACE_SAFE_AREA) {
  if (!safeArea || typeof safeArea !== "object") throw new TypeError("face safe area must be an object");
  for (const [key, value] of Object.entries(safeArea)) assertUnitInterval(value, `face safe area ${key}`);
  if (safeArea.left >= safeArea.right || safeArea.top >= safeArea.bottom) throw new TypeError("face safe area must have positive dimensions");
  return Object.freeze({ left: safeArea.left, top: safeArea.top, right: safeArea.right, bottom: safeArea.bottom });
}

export function faceSafeAreaForCrop(crop = NARRATOR_FACE_CROP, safeArea = NARRATOR_FACE_SAFE_AREA) {
  const validCrop = validateNarratorFaceCrop(crop);
  const validSafeArea = validateNarratorFaceSafeArea(safeArea);
  return Object.freeze({
    left: validCrop.x + validCrop.width * validSafeArea.left,
    top: validCrop.y + validCrop.height * validSafeArea.top,
    right: validCrop.x + validCrop.width * validSafeArea.right,
    bottom: validCrop.y + validCrop.height * validSafeArea.bottom,
    width: validCrop.width * (validSafeArea.right - validSafeArea.left),
    height: validCrop.height * (validSafeArea.bottom - validSafeArea.top),
  });
}

export function adjustNarratorFaceCrop(crop = NARRATOR_FACE_CROP, options = {}) {
  const base = validateNarratorFaceCrop(crop);
  const zoom = Number(options.zoom ?? 1);
  const offsetX = Number(options.offsetX ?? 0);
  const offsetY = Number(options.offsetY ?? 0);
  if (![zoom, offsetX, offsetY].every(Number.isFinite) || zoom <= 0) throw new TypeError("face framing values must be finite and zoom must be positive");
  const size = base.width / zoom;
  const centerX = base.x + base.width / 2 + offsetX;
  const centerY = base.y + base.height / 2 + offsetY;
  const x = Math.max(0, Math.min(NARRATOR_SOURCE_CANVAS.width - size, centerX - size / 2));
  const y = Math.max(0, Math.min(NARRATOR_SOURCE_CANVAS.height - size, centerY - size / 2));
  return validateNarratorFaceCrop({ x, y, width: size, height: size });
}

function faceAssetName(asset) {
  return String(asset || "").split(/[\\/]/).pop();
}

function alignLayerAlphaToHead(layer, targetBounds) {
  const assetName = faceAssetName(layer.asset);
  const sourceBounds = NARRATOR_FACE_ALPHA_BOUNDS[assetName];
  if (!sourceBounds || !targetBounds) return layer;
  const [sourceLeft, sourceTop, sourceRight, sourceBottom] = sourceBounds;
  const [targetLeft, targetTop, targetRight, targetBottom] = targetBounds;
  const sourceWidth = sourceRight - sourceLeft;
  const sourceHeight = sourceBottom - sourceTop;
  const targetWidth = targetRight - targetLeft;
  const targetHeight = targetBottom - targetTop;
  const intrinsic = assetName === "eyes-open.png" || assetName === "brows.png"
    ? (assetName === "eyes-open.png" ? [1774, 887] : [1774, 887])
    : assetName === "eyelids-closed.png" ? [1851, 850]
      : assetName === "glasses.png" || assetName === "mouth-open.png" ? [1316, 1195]
        : assetName === "mouth-closed.png" ? [1536, 1024]
          : [1536, 1024];
  const scaleX = targetWidth / sourceWidth;
  const scaleY = targetHeight / sourceHeight;
  const sourceCenterX = (sourceLeft + sourceRight) / 2;
  const sourceCenterY = (sourceTop + sourceBottom) / 2;
  const targetCenterX = (targetLeft + targetRight) / 2;
  const targetCenterY = (targetTop + targetBottom) / 2;
  layer.size = [intrinsic[0] * scaleX / NARRATOR_FACE_REFERENCE.width, intrinsic[1] * scaleY / NARRATOR_FACE_REFERENCE.height];
  layer.position = [
    (targetCenterX + (intrinsic[0] / 2 - sourceCenterX) * scaleX) / NARRATOR_FACE_REFERENCE.width,
    (targetCenterY + (intrinsic[1] / 2 - sourceCenterY) * scaleY) / NARRATOR_FACE_REFERENCE.height,
  ];
  layer.face_coordinate_system = NARRATOR_FACE_REFERENCE.coordinateSystem;
  layer.face_alpha_target = [...targetBounds];
  return layer;
}

export function validateNarratorManifest(manifest) {
  if (!manifest || typeof manifest !== "object") throw new TypeError("narrator manifest must be an object");
  if (!Number.isInteger(manifest.duration_ms) || manifest.duration_ms <= 0) throw new TypeError("manifest duration_ms must be positive");
  if (!Array.isArray(manifest.segments) || manifest.segments.length === 0) throw new TypeError("manifest must contain segments");
  let previousEnd = 0;
  for (const [index, segment] of manifest.segments.entries()) {
    if (!segment || typeof segment.text !== "string" || !segment.text.trim()) throw new TypeError(`segment ${index} text is required`);
    if (!Number.isInteger(segment.start_ms) || !Number.isInteger(segment.end_ms) || segment.start_ms < 0 || segment.end_ms <= segment.start_ms) {
      throw new TypeError(`segment ${index} has an invalid measured range`);
    }
    if (segment.end_ms > manifest.duration_ms || segment.start_ms < previousEnd) throw new TypeError(`segment ${index} is outside ordered timeline`);
    previousEnd = segment.end_ms;
  }
  return manifest;
}

export function createNarratorTimeline(manifest) {
  validateNarratorManifest(manifest);
  return Object.freeze({
    format: NARRATOR_MODE_FORMAT,
    durationMs: manifest.duration_ms,
    segments: manifest.segments.map((segment, index) => Object.freeze({
      id: segment.id || `segment-${index + 1}`,
      index,
      text: segment.text,
      startMs: segment.start_ms,
      endMs: segment.end_ms,
      voiceId: segment.voice_id || manifest.metadata?.voice_id || null,
      audioUri: segment.audio_uri || null,
      timingSource: "measured_wav_segment",
      wordTimings: [],
      phonemeTimings: [],
      visemeTimings: [],
    })),
  });
}

export function segmentAt(timeline, timeMs) {
  const safeTime = Math.max(0, Math.round(Number(timeMs) || 0));
  return timeline.segments.find((segment) => safeTime >= segment.startMs && safeTime < segment.endMs) || null;
}

export function facialPoseAt(timeMs, speechAmplitude = 0, isPlaying = true) {
  const safeTime = Math.max(0, Number(timeMs) || 0);
  const seconds = safeTime / 1000;
  const blinkPhase = safeTime % 5200;
  let eyeOpen = 1;
  if (blinkPhase >= 4200 && blinkPhase <= 4460) {
    const elapsed = blinkPhase - 4200;
    eyeOpen = elapsed <= 130 ? 1 - elapsed / 130 : (elapsed - 130) / 130;
  }
  return Object.freeze({
    head_rotation: Math.sin(seconds * 0.48) * 0.038 + Math.sin(seconds * 0.21) * 0.016,
    eye_open: clamp(eyeOpen),
    mouth_open: isPlaying ? clamp(speechAmplitude) : 0,
    brow_raise: isPlaying ? (Math.sin(seconds * 0.9) + 1) * 0.12 : 0,
    hair_sway: Math.sin(seconds * 0.67) * 0.009,
    breathing: (Math.sin(seconds * Math.PI * 1.8) + 1) / 2,
  });
}

export function mouthStateAt(amplitude = 0, isPlaying = true) {
  const value = isPlaying ? clamp(amplitude) : 0;
  if (value < 0.12) return "closed";
  if (value < 0.34) return "slight";
  if (value < 0.68) return "moderate";
  return "open";
}

/**
 * Narrator Mode's facial clock is intentionally explicit. It delegates the
 * generic channels to the shared rig, then overlays the named facial pose
 * used by this mode. This keeps the pose returned to callers and the pose
 * consumed by the Canvas draw plan on the same deterministic path.
 */
export class NarratorFacialRig extends LayeredCharacterRig {
  poseAt(timeMs, isPlaying) {
    const sharedPose = super.poseAt(timeMs, isPlaying);
    return { ...sharedPose, ...facialPoseAt(timeMs, this.speechAmplitude, isPlaying) };
  }
}

export function avatarCircleBounds(width, height, options = {}) {
  assertPositiveInteger(width, "width");
  assertPositiveInteger(height, "height");
  const x = Number(options.x ?? NARRATOR_AVATAR_DEFAULT.x);
  const y = Number(options.y ?? NARRATOR_AVATAR_DEFAULT.y);
  const size = Number(options.size ?? NARRATOR_AVATAR_DEFAULT.size);
  if (![x, y, size].every(finite) || size <= 0) throw new TypeError("avatar bounds must be finite and positive");
  const bounds = { x, y, size, right: x + size, bottom: y + size, centerX: x + size / 2, centerY: y + size / 2 };
  if (bounds.x < 0 || bounds.y < 0 || bounds.right > width || bounds.bottom > height) throw new RangeError("avatar circle must stay inside the canvas");
  return Object.freeze(bounds);
}

export function createNarratorAvatarPack(sourcePack = SANTA_V5_PACK, options = {}) {
  validateCharacterPack(sourcePack);
  const composition = options.composition || "corrected";
  const layers = sourcePack.layers
    .filter((layer) => FACE_LAYER_IDS.has(layer.id))
    .map((layer) => {
      const copy = { ...layer, position: [...layer.position], size: [...layer.size], anchor: [...layer.anchor] };
      if (copy.id === "neck") { copy.parent = null; copy.position = [0.5, 0.34]; }
      else if (copy.id === "hair_back") { copy.parent = "head"; copy.position = [0.5, 0.32]; copy.size = [0.98, 0.82]; }
      else if (copy.id !== "head") copy.parent = "head";
      if (copy.id === "hair_front" || copy.id === "eyes" || copy.id === "eyelids" || copy.id === "brows" || copy.id === "glasses" || copy.id === "mouth") {
        alignLayerAlphaToHead(copy, NARRATOR_FACE_ALPHA_TARGETS[copy.id]);
      }
      if (composition === "corrected" && copy.id === "beard") copy.opacity = 0;
      if (composition === "corrected" && copy.id === "mouth") {
        // The approved V5 mouth PNGs are complete lower-face plates (they
        // contain the moustache and beard as well as the lips). Use one plate
        // at the beard scale instead of stacking two copies of the beard.
        copy.mouth_motion = "subtle";
      }
      return copy;
    })
    .sort((left, right) => FACE_ORDER.indexOf(left.id) - FACE_ORDER.indexOf(right.id))
    .map((layer, index) => ({ ...layer, z: index }));
  const pack = {
    format: "fabuloom.character/0.1",
    rig_profile: sourcePack.rig_profile,
    id: "topazio-narrator-santa-v5-face",
    name: "Santa V5 · avatar facial do Narrator Mode",
    voice_id: sourcePack.voice_id,
    language: sourcePack.language,
    art_status: composition === "corrected" ? "production-face-aligned-v1.3-experimental-composition" : "production-face-crop-v1",
    layers,
    expressions: sourcePack.expressions.map((expression) => ({
      id: expression.id,
      overrides: Object.fromEntries(Object.entries(expression.overrides).filter(([id]) => FACE_LAYER_IDS.has(id))),
    })),
    bindings: {
      head_rotation: "head",
      eye_open: "eyelids",
      mouth_open: "mouth",
      hair_sway: "hair_front",
      brow_raise: "brows",
    },
  };
  validateCharacterPack(pack);
  return Object.freeze(pack);
}

export class NarratorAvatarRenderer {
  constructor(canvas, options = {}) {
    if (!canvas || typeof canvas.getContext !== "function") throw new TypeError("a target canvas is required");
    this.canvas = canvas;
    this.sourceCanvas = options.sourceCanvas || document.createElement("canvas");
    this.sourceCanvas.width = NARRATOR_SOURCE_CANVAS.width;
    this.sourceCanvas.height = NARRATOR_SOURCE_CANVAS.height;
    this.pack = options.pack || createNarratorAvatarPack();
    this.rig = options.rig || new NarratorFacialRig();
    const mouthOpenAsset = this.pack.expressions.find((expression) => expression.id === "smile")?.overrides?.mouth || null;
    this.renderer = new LayeredCharacterRenderer(this.sourceCanvas, this.rig, this.pack, {
      assetRoot: options.assetRoot || document.baseURI,
      renderBackground: false,
      assetResolver: (layer, pose, expressionAsset) => {
        if (layer.id !== "mouth" || !mouthOpenAsset) return expressionAsset;
        return mouthStateAt(pose.mouth_open, true) === "closed" || mouthStateAt(pose.mouth_open, true) === "slight"
          ? expressionAsset
          : mouthOpenAsset;
      },
    });
    this.crop = validateNarratorFaceCrop(options.crop || NARRATOR_FACE_CROP);
    this.visibleLayers = null;
    this.loaded = false;
  }

  async load() { await this.renderer.load(); this.loaded = true; return this; }

  setLayerVisibility(visibility) {
    this.visibleLayers = visibility;
    this.renderer.setLayerVisibility(visibility);
  }

  renderTo(context, options = {}) {
    if (!this.loaded) throw new Error("narrator avatar assets are not loaded");
    const bounds = avatarCircleBounds(this.canvas.width, this.canvas.height, options);
    const crop = validateNarratorFaceCrop(options.crop || this.crop);
    this.renderer.renderFrame({ timeMs: options.timeMs, speechAmplitude: options.speechAmplitude, isPlaying: options.isPlaying });
    const radius = bounds.size / 2;
    context.save();
    context.beginPath();
    context.arc(bounds.centerX, bounds.centerY, radius, 0, Math.PI * 2);
    context.clip();
    context.fillStyle = "#07172e";
    context.fillRect(bounds.x, bounds.y, bounds.size, bounds.size);
    context.drawImage(this.sourceCanvas, crop.x, crop.y, crop.width, crop.height, bounds.x, bounds.y, bounds.size, bounds.size);
    context.restore();
    context.save();
    context.beginPath();
    context.arc(bounds.centerX, bounds.centerY, radius - 4, 0, Math.PI * 2);
    context.strokeStyle = "#f7d27a";
    context.lineWidth = Number(options.borderWidth || NARRATOR_AVATAR_DEFAULT.borderWidth);
    context.stroke();
    context.beginPath();
    context.arc(bounds.centerX, bounds.centerY, radius - 14, 0, Math.PI * 2);
    context.strokeStyle = "rgba(45, 104, 178, 0.9)";
    context.lineWidth = 3;
    context.stroke();
    context.restore();
    return bounds;
  }
}

function drawWrappedText(context, text, x, y, maxWidth, lineHeight) {
  const words = String(text).split(/\s+/);
  const lines = [];
  let line = "";
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (line && context.measureText(candidate).width > maxWidth) { lines.push(line); line = word; }
    else line = candidate;
  }
  if (line) lines.push(line);
  lines.forEach((value, index) => context.fillText(value, x, y + index * lineHeight));
  return lines.length;
}

export class SubtitleRenderer {
  render(context, segment, options = {}) {
    if (!segment) return;
    const x = options.x ?? 1240;
    const y = options.y ?? 858;
    const width = options.width ?? 1250;
    context.save();
    context.font = "600 34px Segoe UI, sans-serif";
    context.textAlign = "center";
    context.textBaseline = "top";
    const lines = String(segment.text).split(/\s+/);
    const wrapped = [];
    let line = "";
    for (const word of lines) {
      const candidate = line ? `${line} ${word}` : word;
      if (line && context.measureText(candidate).width > width) { wrapped.push(line); line = word; }
      else line = candidate;
    }
    if (line) wrapped.push(line);
    const lineHeight = 48;
    const boxHeight = wrapped.length * lineHeight + 34;
    context.fillStyle = "rgba(3, 12, 28, 0.84)";
    context.fillRect(x - width / 2 - 24, y - 18, width + 48, boxHeight);
    context.strokeStyle = "rgba(247, 210, 122, 0.7)";
    context.lineWidth = 2;
    context.strokeRect(x - width / 2 - 24, y - 18, width + 48, boxHeight);
    context.fillStyle = "#fff7dc";
    wrapped.forEach((value, index) => context.fillText(value, x, y + index * lineHeight));
    context.restore();
  }
}

export class NarratorSceneRenderer {
  constructor(canvas, avatar, options = {}) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.avatar = avatar;
    this.sceneImage = options.sceneImage || null;
    this.timeline = options.timeline || null;
    this.amplitudeAt = options.amplitudeAt || (() => 0);
    this.subtitles = options.subtitles || new SubtitleRenderer();
    this.sceneId = options.sceneId || "topazio-storyteller-office";
  }

  renderFrame({ timeMs = 0, isPlaying = true } = {}) {
    const ctx = this.context;
    const { width, height } = this.canvas;
    ctx.clearRect(0, 0, width, height);
    if (this.sceneImage) ctx.drawImage(this.sceneImage, 0, 0, width, height);
    else { ctx.fillStyle = "#061329"; ctx.fillRect(0, 0, width, height); }
    const glow = (Math.sin((Number(timeMs) || 0) / 1000 * 0.8) + 1) / 2;
    ctx.fillStyle = `rgba(247, 210, 122, ${0.04 + glow * 0.04})`;
    ctx.beginPath(); ctx.arc(1530, 300, 240 + glow * 12, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#f7d27a"; ctx.font = "700 28px Segoe UI, sans-serif"; ctx.textAlign = "left"; ctx.fillText("FABULOOM · NARRATOR MODE", 84, 78);
    ctx.fillStyle = "rgba(255,255,255,0.65)"; ctx.font = "22px Segoe UI, sans-serif"; ctx.fillText("TOPAZIOVERSE ARCHIVES", 84, 112);
    if (this.avatar) this.avatar.renderTo(ctx, { timeMs, isPlaying, speechAmplitude: this.amplitudeAt(timeMs) });
    const segment = this.timeline ? segmentAt(this.timeline, timeMs) : null;
    this.subtitles.render(ctx, segment);
    ctx.fillStyle = "rgba(247,210,122,0.9)"; ctx.font = "22px Segoe UI, sans-serif"; ctx.textAlign = "right"; ctx.fillText("SANTA · pm_santa · pt-BR", width - 84, height - 42);
    return { segment, pose: facialPoseAt(timeMs, this.amplitudeAt(timeMs), isPlaying), sceneId: this.sceneId };
  }
}

export function createNarratorModeDescriptor(manifest, options = {}) {
  const timeline = createNarratorTimeline(manifest);
  const avatar = avatarCircleBounds(NARRATOR_CANVAS.width, NARRATOR_CANVAS.height, options.avatar);
  return {
    format: NARRATOR_MODE_FORMAT,
    voiceId: options.voiceId || manifest.metadata?.voice_id || manifest.segments[0]?.voice_id || "pm_santa",
    language: options.language || "pt-BR",
    sceneId: options.sceneId || "topazio-storyteller-office",
    canvas: NARRATOR_CANVAS,
    fps: NARRATOR_FPS,
    avatar,
    timeline,
    timingSource: "measured_wav_segments",
    wordTiming: "unavailable",
    phonemeTiming: "unavailable",
    visemeTiming: "unavailable",
  };
}

