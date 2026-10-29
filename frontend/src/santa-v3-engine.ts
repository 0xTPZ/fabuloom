/**
 * Santa V3 animation and deterministic scene renderer.
 *
 * This module is intentionally provider-agnostic: Kokoro only supplies the
 * measured speech envelope to the rig. The body, props and scene are driven
 * by absolute time, so browser playback and offline frame capture share the
 * same animation result.
 */

import { captureLayeredFrames, LayeredCharacterRenderer, frameSchedule } from "./layered-character.ts";
import { SANTA_V3_PACK } from "./santa-v3-pack.mjs";

export const SANTA_V3_ANIMATION_FORMAT = "fabuloom.animation/0.1";
export const SANTA_V3_CLIP_NAMES = Object.freeze([
  "idle", "walk", "sit", "stand_up", "talk", "explain", "reach", "hold_object", "drink", "read_book",
  "blink", "look_left", "look_right", "smile", "talk_mouth", "eyebrow_raise",
]);

const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, Number(value) || 0));
const lerp = (a, b, t) => a + (b - a) * clamp(t);
const smooth = (t) => { const x = clamp(t); return x * x * (3 - 2 * x); };
const pulse = (timeMs, centerMs, widthMs, amount) => Math.exp(-(((timeMs - centerMs) / widthMs) ** 2)) * amount;
const sine = (timeMs, hz, phase = 0) => Math.sin(timeMs / 1000 * Math.PI * 2 * hz + phase);

function segmentProgress(progress, start, end) {
  return smooth((progress - start) / (end - start));
}

/** A clip catalogue with real deterministic samplers, useful to future scene directors. */
export const SANTA_V3_ANIMATION_LIBRARY = Object.freeze({
  idle: { durationMs: 4000, sample: (t) => ({ breathing: (sine(t, 0.18) + 1) / 2 }) },
  walk: { durationMs: 1800, sample: (t) => ({ left_thigh_rotation: sine(t, 0.9) * 0.24, right_thigh_rotation: sine(t, 0.9, Math.PI) * 0.24 }) },
  sit: { durationMs: 1800, sample: (t) => ({ torso_y: smooth(t / 1800) * 0.06, left_thigh_rotation: smooth(t / 1800) * 0.54, right_thigh_rotation: smooth(t / 1800) * -0.54 }) },
  stand_up: { durationMs: 1800, sample: (t) => ({ torso_y: 0.06 * (1 - smooth(t / 1800)), left_thigh_rotation: 0.54 * (1 - smooth(t / 1800)), right_thigh_rotation: -0.54 * (1 - smooth(t / 1800)) }) },
  talk: { durationMs: 4000, sample: () => ({}) },
  explain: { durationMs: 4000, sample: (t) => ({ right_arm_rotation: pulse(t, 1100, 360, -0.30), left_arm_rotation: pulse(t, 2800, 420, 0.24) }) },
  reach: { durationMs: 1800, sample: (t) => ({ right_arm_rotation: -0.55 * smooth(t / 1800), right_forearm_rotation: -0.72 * smooth(t / 1800) }) },
  hold_object: { durationMs: 2000, sample: () => ({ right_arm_rotation: -0.55, right_forearm_rotation: -0.72 }) },
  drink: { durationMs: 2200, sample: (t) => ({ right_arm_rotation: lerp(-0.55, 0.18, smooth(t / 2200)), right_forearm_rotation: lerp(-0.72, -0.38, smooth(t / 2200)) }) },
  read_book: { durationMs: 4000, sample: (t) => ({ head_rotation: sine(t, 0.12) * 0.04, right_arm_rotation: -0.10, left_arm_rotation: 0.10 }) },
  blink: { durationMs: 260, sample: (t) => ({ eye_open: t < 130 ? 1 - t / 130 : (t - 130) / 130 }) },
  look_left: { durationMs: 900, sample: (t) => ({ head_rotation: -0.14 * smooth(t / 900) }) },
  look_right: { durationMs: 900, sample: (t) => ({ head_rotation: 0.14 * smooth(t / 900) }) },
  smile: { durationMs: 1200, sample: () => ({ expression: "smile" }) },
  talk_mouth: { durationMs: 1000, sample: (t) => ({ mouth_open: (sine(t, 4.2) + 1) / 2 }) },
  eyebrow_raise: { durationMs: 900, sample: (t) => ({ brow_raise: 0.6 * Math.sin(Math.PI * clamp(t / 900)) }) },
});

function basePose(timeMs, isPlaying, speechAmplitude) {
  const breathing = (sine(timeMs, 0.18) + 1) / 2;
  const blinkPhase = ((timeMs % 5200) + 5200) % 5200;
  let eyeOpen = 1;
  if (blinkPhase >= 4200 && blinkPhase <= 4460) eyeOpen = blinkPhase < 4330 ? 1 - (blinkPhase - 4200) / 130 : (blinkPhase - 4330) / 130;
  return {
    breathing,
    head_rotation: sine(timeMs, 0.075) * 0.035 + sine(timeMs, 0.033, 1.2) * 0.016,
    eye_open: clamp(eyeOpen),
    mouth_open: isPlaying ? clamp(speechAmplitude) : 0,
    hair_sway: sine(timeMs, 0.11) * 0.012,
    brow_raise: isPlaying ? (sine(timeMs, 0.12) + 1) * 0.10 : 0,
    torso_rotation: sine(timeMs, 0.05) * 0.010,
    torso_y: 0,
    pelvis_y: 0,
    left_arm_rotation: sine(timeMs, 0.08, 0.8) * 0.018,
    right_arm_rotation: sine(timeMs, 0.07, 2.1) * 0.018,
    left_forearm_rotation: 0,
    right_forearm_rotation: 0,
    left_hand_rotation: 0,
    right_hand_rotation: 0,
    left_thigh_rotation: 0,
    right_thigh_rotation: 0,
    left_shin_rotation: 0,
    right_shin_rotation: 0,
    left_foot_rotation: 0,
    right_foot_rotation: 0,
  };
}

/**
 * The sequence is a continuous shot. Percentages make it usable with any
 * measured Kokoro duration while retaining all required actions.
 */
export function santaV3SceneAt(timeMs, durationMs) {
  const duration = Math.max(1, Number(durationMs) || 1);
  const progress = clamp((Number(timeMs) || 0) / duration);
  const walkEnd = 0.16;
  const sitEnd = 0.29;
  const reachEnd = 0.41;
  const drinkEnd = 0.52;
  const returnEnd = 0.60;
  const readEnd = 0.74;
  let action = "idle";
  let seated = 0;
  let cupState = "table";
  let gesture = 0;
  if (progress < walkEnd) action = "walk";
  else if (progress < sitEnd) { action = "sit"; seated = segmentProgress(progress, walkEnd, sitEnd); }
  else if (progress < reachEnd) { action = "reach"; seated = 1; cupState = "reaching"; }
  else if (progress < drinkEnd) { action = "drink"; seated = 1; cupState = "held"; }
  else if (progress < returnEnd) { action = "reach"; seated = 1; cupState = "returning"; }
  else if (progress < readEnd) { action = "read_book"; seated = 1; }
  else { action = "explain"; seated = 1; gesture = Math.sin((progress - readEnd) * Math.PI * 8) * 0.5 + 0.5; }
  const characterX = progress < walkEnd ? lerp(60, 180, progress / walkEnd) : 180;
  const characterY = 560 + seated * 60;
  return { progress, action, seated, cupState, gesture, characterX, characterY };
}

export class SantaV3Rig {
  constructor() {
    this.speechAmplitude = 0;
    this.currentExpression = "neutral";
    this.sceneDurationMs = 1;
    this.currentPose = basePose(0, false, 0);
  }

  setSceneDuration(durationMs) { this.sceneDurationMs = Math.max(1, Number(durationMs) || 1); }
  setSpeechAmplitude(amplitude) { this.speechAmplitude = clamp(amplitude); }
  setExpression(expressionId) { this.currentExpression = expressionId; }

  poseAt(timeMs, isPlaying) {
    const safeTime = Math.max(0, Number(timeMs) || 0);
    const scene = santaV3SceneAt(safeTime, this.sceneDurationMs);
    const sitEnd = 0.29;
    const reachEnd = 0.41;
    const drinkEnd = 0.52;
    const returnEnd = 0.60;
    const pose = basePose(safeTime, isPlaying, this.speechAmplitude);
    pose.torso_y = scene.seated * 0.065;
    pose.pelvis_y = scene.seated * 0.035;
    if (scene.action === "walk") {
      pose.left_thigh_rotation = sine(safeTime, 0.95) * 0.22;
      pose.right_thigh_rotation = sine(safeTime, 0.95, Math.PI) * 0.22;
      pose.left_shin_rotation = Math.max(0, -sine(safeTime, 0.95)) * 0.17;
      pose.right_shin_rotation = Math.max(0, -sine(safeTime, 0.95, Math.PI)) * 0.17;
      pose.left_arm_rotation += sine(safeTime, 0.95, Math.PI) * 0.14;
      pose.right_arm_rotation += sine(safeTime, 0.95) * 0.14;
    }
    if (scene.seated) {
      pose.left_thigh_rotation = lerp(pose.left_thigh_rotation, 0.48, scene.seated);
      pose.right_thigh_rotation = lerp(pose.right_thigh_rotation, -0.48, scene.seated);
      pose.left_shin_rotation = lerp(pose.left_shin_rotation, -0.55, scene.seated);
      pose.right_shin_rotation = lerp(pose.right_shin_rotation, 0.55, scene.seated);
    }
    if (scene.action === "reach" || scene.action === "drink") {
      const reach = scene.action === "reach" ? (scene.cupState === "returning" ? 1 - segmentProgress(scene.progress, drinkEnd, returnEnd) : segmentProgress(scene.progress, sitEnd, reachEnd)) : 1;
      const drink = scene.action === "drink" ? segmentProgress(scene.progress, reachEnd, drinkEnd) : 0;
      // Raise the upper arm and steer the forearm toward the face. The
      // separate channels keep the elbow and wrist independently animatable.
      pose.right_arm_rotation += lerp(0, 1.65, reach) + lerp(0, 0.22, drink);
      pose.right_forearm_rotation += lerp(0, 1.75, reach) + lerp(0, 0.12, drink);
      pose.right_hand_rotation += lerp(0, 0.18, drink);
      pose.left_arm_rotation += lerp(0, 0.12, reach);
    }
    if (scene.action === "read_book") {
      pose.head_rotation += sine(safeTime, 0.12) * 0.04;
      pose.left_arm_rotation += 0.09;
      pose.right_arm_rotation -= 0.10;
      pose.left_forearm_rotation -= 0.16;
      pose.right_forearm_rotation += 0.12;
    }
    if (scene.action === "explain") {
      const t = (safeTime / this.sceneDurationMs - 0.74) / 0.26;
      pose.right_arm_rotation += pulse(t * 10000, 1800, 420, -0.30) + pulse(t * 10000, 5200, 520, 0.22);
      pose.left_arm_rotation += pulse(t * 10000, 3400, 480, 0.28);
      pose.right_forearm_rotation += pulse(t * 10000, 1800, 420, -0.30);
      pose.left_forearm_rotation += pulse(t * 10000, 3400, 480, 0.22);
    }
    return pose;
  }

  update(timeMs, isPlaying) { this.currentPose = this.poseAt(timeMs, isPlaying); }
  pose() { return { ...this.currentPose }; }
}

function drawBackground(ctx, width, height) {
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, "#050c1b"); gradient.addColorStop(0.58, "#102b4f"); gradient.addColorStop(1, "#050913");
  ctx.fillStyle = gradient; ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = "rgba(247,210,122,.16)"; ctx.beginPath(); ctx.arc(width * .78, height * .18, 118, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = "#f7d27a"; ctx.beginPath(); ctx.arc(width * .77, height * .17, 58, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = "rgba(255,255,255,.72)";
  for (let i = 0; i < 22; i += 1) { const x = (i * 173) % width; const y = 90 + ((i * 97) % 720); ctx.fillRect(x, y, i % 3 === 0 ? 5 : 3, i % 3 === 0 ? 5 : 3); }
  ctx.fillStyle = "rgba(247,210,122,.12)"; ctx.fillRect(0, height * .70, width, 4);
}

function drawChair(ctx, x, y) {
  ctx.fillStyle = "#152f55"; ctx.strokeStyle = "#d6a84d"; ctx.lineWidth = 8;
  ctx.beginPath(); ctx.roundRect(x, y - 230, 260, 270, 34); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#0a1429"; ctx.fillRect(x + 28, y + 18, 38, 230); ctx.fillRect(x + 194, y + 18, 38, 230);
}

function drawTable(ctx, x, y) {
  ctx.fillStyle = "#0b172c"; ctx.strokeStyle = "#d6a84d"; ctx.lineWidth = 8;
  ctx.beginPath(); ctx.roundRect(x, y, 510, 56, 20); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#10294e"; ctx.fillRect(x + 34, y + 44, 42, 300); ctx.fillRect(x + 434, y + 44, 42, 300);
}

function drawBook(ctx, x, y) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(-0.05);
  ctx.fillStyle = "#d6a84d"; ctx.strokeStyle = "#f7e2a0"; ctx.lineWidth = 5;
  ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(118, 18); ctx.lineTo(112, 106); ctx.lineTo(4, 88); ctx.closePath(); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#fff2cf"; ctx.beginPath(); ctx.moveTo(118, 18); ctx.lineTo(236, 0); ctx.lineTo(232, 88); ctx.lineTo(112, 106); ctx.closePath(); ctx.fill(); ctx.stroke();
  ctx.strokeStyle = "#8a5b20"; ctx.lineWidth = 3; for (let i = 0; i < 4; i += 1) { ctx.beginPath(); ctx.moveTo(18, 27 + i * 14); ctx.lineTo(98, 38 + i * 12); ctx.stroke(); ctx.beginPath(); ctx.moveTo(136, 28 + i * 14); ctx.lineTo(218, 17 + i * 13); ctx.stroke(); }
  ctx.restore();
}

function drawCup(ctx, x, y, angle = 0) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(angle); ctx.fillStyle = "#f7e2a0"; ctx.strokeStyle = "#8a5b20"; ctx.lineWidth = 6;
  ctx.beginPath(); ctx.roundRect(-28, -62, 56, 68, 12); ctx.fill(); ctx.stroke(); ctx.beginPath(); ctx.arc(32, -28, 21, -Math.PI / 2, Math.PI / 2); ctx.stroke();
  ctx.strokeStyle = "rgba(247,210,122,.58)"; ctx.lineWidth = 5; for (let i = -1; i <= 1; i += 1) { ctx.beginPath(); ctx.moveTo(i * 12, -76); ctx.quadraticCurveTo(i * 8 + 6, -96, i * 12, -116); ctx.stroke(); }
  ctx.restore();
}

function propState(scene, handAnchor = null) {
  const tableCup = { x: 820, y: 1248 };
  const handCup = handAnchor || { x: scene.characterX + 470, y: scene.characterY + 520 };
  const mouthCup = { x: scene.characterX + 350, y: scene.characterY + 380 };
  if (scene.cupState === "table") return { ...tableCup, angle: 0, held: false };
  if (scene.cupState === "reaching") {
    const p = scene.progress < 0.41 ? segmentProgress(scene.progress, 0.29, 0.41) : 1 - segmentProgress(scene.progress, 0.52, 0.60);
    const from = scene.progress < 0.41 ? tableCup : mouthCup; const to = scene.progress < 0.41 ? handCup : tableCup;
    return { x: lerp(from.x, to.x, p), y: lerp(from.y, to.y, p), angle: 0, held: true };
  }
  if (scene.cupState === "held") {
    const p = segmentProgress(scene.progress, 0.41, 0.52);
    return { x: lerp(handCup.x, mouthCup.x, p), y: lerp(handCup.y, mouthCup.y, p), angle: -0.08, held: true };
  }
  return { ...tableCup, angle: 0, held: false };
}

function pointFromMatrix(matrix, x, y) {
  return { x: matrix.a * x + matrix.c * y + matrix.e, y: matrix.b * x + matrix.d * y + matrix.f };
}

export class SantaV3SceneRenderer {
  constructor(canvas, rig = new SantaV3Rig(), options = {}) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.rig = rig;
    this.characterCanvas = document.createElement("canvas");
    this.characterCanvas.width = options.characterWidth || 680;
    this.characterCanvas.height = options.characterHeight || 1550;
    this.characterDrawHeight = options.characterDrawHeight || 1300;
    this.pack = options.pack || SANTA_V3_PACK;
    this.title = options.title || "SANTA V3  ·  TOPAZIOVERSE";
    this.characterRenderer = new LayeredCharacterRenderer(this.characterCanvas, rig, this.pack, {
      assetRoot: options.assetRoot || globalThis.document?.baseURI || "http://127.0.0.1/",
      renderBackground: false,
    });
    this.loaded = false;
  }

  async load() { await this.characterRenderer.load(); this.loaded = true; return this; }

  renderFrame({ timeMs = 0, durationMs = 1, speechAmplitude = 0, isPlaying = true } = {}) {
    this.rig.setSceneDuration(durationMs);
    this.rig.setSpeechAmplitude(speechAmplitude);
    this.characterRenderer.renderFrame({ timeMs, speechAmplitude, isPlaying });
    const ctx = this.context; const width = this.canvas.width; const height = this.canvas.height;
    const scene = santaV3SceneAt(timeMs, durationMs);
    const handPlan = this.characterRenderer.getLayerDrawPlan().find((entry) => entry.layer.id === "right_hand");
    const characterScaleY = this.characterDrawHeight / this.characterCanvas.height;
    const localHand = handPlan
      ? pointFromMatrix(handPlan.matrix, handPlan.intrinsic[0] * 0.5, handPlan.intrinsic[1] * 0.38)
      : null;
    const handAnchor = localHand
      ? { x: scene.characterX + localHand.x, y: scene.characterY + localHand.y * characterScaleY }
      : null;
    const props = propState(scene, handAnchor);
    drawBackground(ctx, width, height);
    drawChair(ctx, 230, 1325); drawTable(ctx, 540, 1320); drawBook(ctx, 700, 1236);
    ctx.drawImage(this.characterCanvas, scene.characterX, scene.characterY, this.characterCanvas.width, this.characterDrawHeight);
    drawCup(ctx, props.x, props.y, props.angle);
    ctx.fillStyle = "rgba(5,9,19,.70)"; ctx.fillRect(54, 62, 972, 94);
    ctx.fillStyle = "#f7d27a"; ctx.font = "700 38px Segoe UI, sans-serif"; ctx.textAlign = "center"; ctx.fillText(this.title, width / 2, 122);
    if (scene.action === "explain") { ctx.fillStyle = "#f7e2a0"; ctx.font = "600 28px Segoe UI, sans-serif"; ctx.fillText("histórias que ganham vida", width / 2, height - 78); }
    return this.canvas;
  }
}

export async function captureSantaV3Frames(renderer, { durationMs, fps = 30, isPlaying = true, amplitudeAt = () => 0, onFrame, signal } = {}) {
  if (!(renderer instanceof SantaV3SceneRenderer)) throw new TypeError("renderer must be a SantaV3SceneRenderer");
  if (typeof onFrame !== "function") throw new TypeError("onFrame callback is required");
  let count = 0;
  for (const frame of frameSchedule(durationMs, fps)) {
    if (signal?.aborted) throw new DOMException("frame capture aborted", "AbortError");
    renderer.renderFrame({ timeMs: frame.timeMs, durationMs, speechAmplitude: amplitudeAt(frame.timeMs), isPlaying });
    const blob = await new Promise((resolve, reject) => renderer.canvas.toBlob((value) => value ? resolve(value) : reject(new Error("scene frame encoding returned no blob")), "image/png"));
    await onFrame({ ...frame, blob }); count += 1;
  }
  return { frameCount: count, durationMs, fps, animation_format: SANTA_V3_ANIMATION_FORMAT };
}
