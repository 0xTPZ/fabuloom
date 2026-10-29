import {
  captureSantaV3Frames,
  SANTA_V3_ANIMATION_FORMAT,
  SANTA_V3_ANIMATION_LIBRARY,
  SantaV3Rig,
  SantaV3SceneRenderer,
  santaV3SceneAt,
} from "./santa-v3-engine.ts";
import {
  FABULOOM_KEYFRAME_FORMAT,
  sampleAnimationClip,
  validateAnimationClip,
} from "./animation-keyframes.mjs";
import { angleDelta, solveTwoBoneIK } from "./two-bone-ik.mjs";
import { createPresentationTarget, validatePresentationTarget } from "./presentation-targets.mjs";
import { createPointAtClip, planPointAtTarget, pointerRotationForIK } from "./presenter-targeting.mjs";
import {
  SANTA_V5_RIGHT_ARM_IK_CALIBRATION,
  SANTA_V5_RIGHT_ARM_RENDER_GEOMETRY,
  SANTA_V5_LEFT_ARM_IK_CALIBRATION,
  SANTA_V5_LEFT_ARM_RENDER_GEOMETRY,
} from "./santa-v5-calibration.mjs";
import { SANTA_V5_PACK, SANTA_V5_POINTING_HAND, SANTA_V5_POINTING_HAND_LEFT } from "./santa-v5-pack.mjs";

export const SANTA_V5_ANIMATION_FORMAT = SANTA_V3_ANIMATION_FORMAT;

const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, Number(value) || 0));

const rotateVector = (vector, angle) => ({
  x: Math.cos(angle) * vector.x - Math.sin(angle) * vector.y,
  y: Math.sin(angle) * vector.x + Math.cos(angle) * vector.y,
});
const scaleVector = (vector, scale) => ({ x: vector.x * scale.x, y: vector.y * scale.y });
const addVectors = (left, right) => ({ x: left.x + right.x, y: left.y + right.y });
const distanceBetween = (left, right) => Math.hypot(right.x - left.x, right.y - left.y);

/** Forward model for either calibrated painted arm. */
function renderedArmAt(calibration, geometry, upperRotation, forearmRotation, rootRotation = 0) {
  const upper = rotateVector(scaleVector(geometry.upperOffset, geometry.upperScale), upperRotation);
  const forearmLocal = rotateVector(scaleVector(geometry.forearmOffset, geometry.forearmScale), forearmRotation);
  const forearm = rotateVector(scaleVector(forearmLocal, geometry.upperScale), upperRotation);
  const localElbow = addVectors(calibration.shoulder, scaleVector(upper, geometry.rootScale));
  const localWrist = addVectors(calibration.shoulder, scaleVector(addVectors(upper, forearm), geometry.rootScale));
  if (!rootRotation) return { elbow: localElbow, wrist: localWrist };
  const rotateAroundRoot = (point) => {
    const relative = { x: point.x - calibration.rootPivot.x, y: point.y - calibration.rootPivot.y };
    const rotated = rotateVector(relative, rootRotation);
    return { x: calibration.rootPivot.x + rotated.x, y: calibration.rootPivot.y + rotated.y };
  };
  const elbow = rotateAroundRoot(localElbow);
  const wrist = rotateAroundRoot(localWrist);
  return { elbow, wrist };
}

function refineRenderedArm(analytic, target, calibration, geometry, rootRotation = 0) {
  let upperRotation = angleDelta(calibration.baseShoulderAngle, analytic.shoulderAngle);
  let forearmRotation = angleDelta(calibration.baseElbowAngle, analytic.elbowAngle);
  const epsilon = 1e-4;
  for (let iteration = 0; iteration < 16; iteration += 1) {
    const current = renderedArmAt(calibration, geometry, upperRotation, forearmRotation, rootRotation).wrist;
    const error = { x: target.x - current.x, y: target.y - current.y };
    if (Math.hypot(error.x, error.y) < 0.01) break;
    const nextUpper = renderedArmAt(calibration, geometry, upperRotation + epsilon, forearmRotation, rootRotation).wrist;
    const nextForearm = renderedArmAt(calibration, geometry, upperRotation, forearmRotation + epsilon, rootRotation).wrist;
    const upperJacobian = { x: (nextUpper.x - current.x) / epsilon, y: (nextUpper.y - current.y) / epsilon };
    const forearmJacobian = { x: (nextForearm.x - current.x) / epsilon, y: (nextForearm.y - current.y) / epsilon };
    const determinant = upperJacobian.x * forearmJacobian.y - forearmJacobian.x * upperJacobian.y;
    if (Math.abs(determinant) < 1e-8) break;
    const upperStep = (error.x * forearmJacobian.y - error.y * forearmJacobian.x) / determinant;
    const forearmStep = (upperJacobian.x * error.y - upperJacobian.y * error.x) / determinant;
    const stepScale = Math.max(1, Math.max(Math.abs(upperStep), Math.abs(forearmStep)) / 0.45);
    upperRotation += upperStep / stepScale;
    forearmRotation += forearmStep / stepScale;
  }
  const rendered = renderedArmAt(calibration, geometry, upperRotation, forearmRotation, rootRotation);
  return { upperRotation, forearmRotation, ...rendered, error: distanceBetween(rendered.wrist, target) };
}

function renderedRightArmAt(upperRotation, forearmRotation) { return renderedArmAt(SANTA_V5_RIGHT_ARM_IK_CALIBRATION, SANTA_V5_RIGHT_ARM_RENDER_GEOMETRY, upperRotation, forearmRotation); }
function renderedLeftArmAt(upperRotation, forearmRotation) { return renderedArmAt(SANTA_V5_LEFT_ARM_IK_CALIBRATION, SANTA_V5_LEFT_ARM_RENDER_GEOMETRY, upperRotation, forearmRotation); }
function refineRenderedRightArm(analytic, target) { return refineRenderedArm(analytic, target, SANTA_V5_RIGHT_ARM_IK_CALIBRATION, SANTA_V5_RIGHT_ARM_RENDER_GEOMETRY); }
function refineRenderedLeftArm(analytic, target) { return refineRenderedArm(analytic, target, SANTA_V5_LEFT_ARM_IK_CALIBRATION, SANTA_V5_LEFT_ARM_RENDER_GEOMETRY); }

function limitPoseChannel(pose, channel, min, max) {
  pose[channel] = Math.max(min, Math.min(max, Number(pose[channel]) || 0));
}

/**
 * One deliberately small, additive clip. The values are pose deltas, so
 * breathing, blinking, RMS mouth motion and the existing neutral pose remain
 * owned by the rig instead of being duplicated in the clip.
 */
export const SANTA_V5_WAVE_HELLO_CLIP = validateAnimationClip({
  format: FABULOOM_KEYFRAME_FORMAT,
  id: "WAVE_HELLO",
  durationMs: 4600,
  easing: "ease-in-out",
  keyframes: [
    { timeMs: 0, easing: "ease-in-out", channels: { right_hand_target_x: 0.71044232, right_hand_target_y: 0.43846624, right_arm_ik_weight: 0, right_hand_rotation: 0, head_rotation: 0, torso_rotation: 0 } },
    { timeMs: 320, easing: "ease-in-out", channels: { right_hand_target_x: 0.739, right_hand_target_y: 0.454, right_arm_ik_weight: 0.12, right_hand_rotation: -0.025, head_rotation: -0.012, torso_rotation: 0 } },
    { timeMs: 1180, easing: "ease-out", channels: { right_hand_target_x: 0.768, right_hand_target_y: 0.205, right_arm_ik_weight: 0.84, right_hand_rotation: 0.045, head_rotation: -0.042, torso_rotation: 0 } },
    { timeMs: 1680, easing: "ease-in-out", channels: { right_hand_target_x: 0.778, right_hand_target_y: 0.156, right_arm_ik_weight: 1, right_hand_rotation: -0.16, head_rotation: -0.035, torso_rotation: 0 } },
    { timeMs: 2120, easing: "ease-in-out", channels: { right_hand_target_x: 0.781, right_hand_target_y: 0.154, right_arm_ik_weight: 1, right_hand_rotation: 0.18, head_rotation: -0.028, torso_rotation: 0 } },
    { timeMs: 2560, easing: "ease-in-out", channels: { right_hand_target_x: 0.778, right_hand_target_y: 0.156, right_arm_ik_weight: 1, right_hand_rotation: -0.16, head_rotation: -0.026, torso_rotation: 0 } },
    { timeMs: 3000, easing: "ease-in-out", channels: { right_hand_target_x: 0.774, right_hand_target_y: 0.178, right_arm_ik_weight: 0.96, right_hand_rotation: 0.14, head_rotation: -0.022, torso_rotation: 0 } },
    { timeMs: 3560, easing: "ease-in", channels: { right_hand_target_x: 0.754, right_hand_target_y: 0.300, right_arm_ik_weight: 0.64, right_hand_rotation: 0.06, head_rotation: -0.012, torso_rotation: 0 } },
    { timeMs: 4600, easing: "ease-in-out", channels: { right_hand_target_x: 0.71044232, right_hand_target_y: 0.43846624, right_arm_ik_weight: 0, right_hand_rotation: 0, head_rotation: 0, torso_rotation: 0 } },
  ],
});

export const SANTA_V5_POINT_AT_CLIP = createPointAtClip({ durationMs: 8000, holdMs: 4100 });

export const SANTA_V5_DEFAULT_POINT_TARGET = createPresentationTarget({
  id: "default-point-target",
  position: { x: 0.90, y: 0.15 },
  coordinateSpace: "normalized-stage",
  label: "alvo padrão",
});

const SANTA_V5_ANIMATION_CLIPS = Object.freeze({
  WAVE_HELLO: SANTA_V5_WAVE_HELLO_CLIP,
  POINT_AT: SANTA_V5_POINT_AT_CLIP,
});

export const SANTA_V5_ANIMATION_LIBRARY = Object.freeze({
  ...SANTA_V3_ANIMATION_LIBRARY,
  WAVE_HELLO: { durationMs: SANTA_V5_WAVE_HELLO_CLIP.durationMs, sample: (timeMs) => sampleAnimationClip(SANTA_V5_WAVE_HELLO_CLIP, timeMs) },
  POINT_AT: { durationMs: SANTA_V5_POINT_AT_CLIP.durationMs, sample: (timeMs) => sampleAnimationClip(SANTA_V5_POINT_AT_CLIP, timeMs) },
});

/**
 * V5 keeps the proven deterministic V3 choreography and adds only the
 * art-specific finishing behavior. This is deliberately a thin adapter: the
 * Stage and offline capture continue to share one animation implementation.
 */
export class SantaV5Rig extends SantaV3Rig {
  constructor() {
    super();
    this.activeAnimationId = null;
    this.animationStartMs = 0;
    this.rightHandTarget = null;
    this.lastIKResult = null;
    this.presentationTarget = null;
    this.pointAtPlan = null;
    this.pointAtClip = SANTA_V5_POINT_AT_CLIP;
  }

  setAnimation(animationId, startTimeMs = 0) {
    if (animationId === null || animationId === undefined || animationId === "") {
      this.activeAnimationId = null;
      this.animationStartMs = 0;
      this.lastIKResult = null;
      return this;
    }
    if (!SANTA_V5_ANIMATION_CLIPS[animationId]) throw new RangeError(`Unknown Santa V5 animation: ${animationId}`);
    if (!Number.isFinite(startTimeMs) || startTimeMs < 0) throw new TypeError("Animation start time must be a non-negative finite number");
    this.activeAnimationId = animationId;
    this.animationStartMs = startTimeMs;
    return this;
  }

  clearAnimation() {
    this.activeAnimationId = null;
    this.animationStartMs = 0;
    this.lastIKResult = null;
    return this;
  }

  animationId() { return this.activeAnimationId; }

  pointAtClipDefinition() { return this.pointAtClip; }

  setPointAtTiming(options = {}) {
    this.pointAtClip = createPointAtClip(options);
    if (this.activeAnimationId === "POINT_AT") this.animationStartMs = 0;
    return this;
  }

  /** Configure the provider-independent target used by POINT_AT. */
  setPresentationTarget(target, options = {}) {
    const validated = validatePresentationTarget(target);
    const arm = options.arm || (validated.coordinateSpace === "normalized-stage" ? (validated.position.x < 0.5 ? "left" : "right") : "right");
    const left = arm === "left";
    this.presentationTarget = validated;
    this.pointAtPlan = planPointAtTarget(validated, {
      calibration: left ? SANTA_V5_LEFT_ARM_IK_CALIBRATION : SANTA_V5_RIGHT_ARM_IK_CALIBRATION,
      pointerLocalAngle: options.pointerLocalAngle ?? (left ? SANTA_V5_POINTING_HAND_LEFT.localAngle : SANTA_V5_POINTING_HAND.localAngle),
      wristClearancePx: options.wristClearancePx ?? 86,
      objects: options.objects,
      width: options.width ?? (left ? SANTA_V5_LEFT_ARM_IK_CALIBRATION.frameWidth : SANTA_V5_RIGHT_ARM_IK_CALIBRATION.frameWidth),
      height: options.height ?? (left ? SANTA_V5_LEFT_ARM_IK_CALIBRATION.frameHeight : SANTA_V5_RIGHT_ARM_IK_CALIBRATION.frameHeight),
      elbowPreference: options.elbowPreference,
      arm,
    });
    this.lastIKResult = null;
    return this;
  }

  clearPresentationTarget() {
    this.presentationTarget = null;
    this.pointAtPlan = null;
    this.lastIKResult = null;
    return this;
  }

  presentationTargetInfo() {
    if (!this.pointAtPlan) return null;
    return {
      id: this.pointAtPlan.target.target.id,
      label: this.pointAtPlan.target.label,
      point: { ...this.pointAtPlan.target.point },
      normalized: { ...this.pointAtPlan.target.normalized },
      wristTarget: { ...this.pointAtPlan.wristTarget },
      normalizedWrist: { ...this.pointAtPlan.normalizedWrist },
      pointerDirection: this.pointAtPlan.pointerDirection,
      headRotation: this.pointAtPlan.headRotation,
      torsoRotation: this.pointAtPlan.torsoRotation,
      reachable: this.pointAtPlan.reachable,
      clamped: this.pointAtPlan.clamped,
      coordinateSpace: this.pointAtPlan.target.coordinateSpace,
      arm: this.pointAtPlan.arm,
    };
  }

  /**
   * Set an optional normalized [0,1] hand target for the active IK clip.
   * Coordinates are stage-relative; the solver itself works in the calibrated
   * 1080x1920 Canvas space. `elbowPreference` is a direction from the shoulder.
   */
  setRightHandTarget({ x, y, weight = 1, elbowPreference, wristRotation = 0 } = {}) {
    if (![x, y, weight, wristRotation].every(Number.isFinite)) throw new TypeError("Right-hand IK target values must be finite");
    if (x < 0 || x > 1 || y < 0 || y > 1) throw new RangeError("Right-hand IK target coordinates must be normalized to [0,1]");
    const preference = elbowPreference || SANTA_V5_RIGHT_ARM_IK_CALIBRATION.elbowPreference;
    if (!preference || !Number.isFinite(preference.x) || !Number.isFinite(preference.y) || Math.hypot(preference.x, preference.y) < 1e-9) throw new RangeError("Right-hand elbow preference must be a non-zero finite vector");
    this.rightHandTarget = { x, y, weight: clamp(weight), elbowPreference: { x: preference.x, y: preference.y }, wristRotation };
    return this;
  }

  clearRightHandTarget() { this.rightHandTarget = null; return this; }
  rightHandIK() { return this.lastIKResult ? { ...this.lastIKResult } : null; }

  solveArmIK(side, sample) {
    const left = side === "left";
    const calibration = left ? SANTA_V5_LEFT_ARM_IK_CALIBRATION : SANTA_V5_RIGHT_ARM_IK_CALIBRATION;
    const geometry = left ? SANTA_V5_LEFT_ARM_RENDER_GEOMETRY : SANTA_V5_RIGHT_ARM_RENDER_GEOMETRY;
    const x = sample[`${side}_hand_target_x`];
    const y = sample[`${side}_hand_target_y`];
    const target = {
      x: clamp(x, 0, 1) * calibration.frameWidth,
      y: clamp(y, 0, 1) * calibration.frameHeight,
    };
    const analytic = solveTwoBoneIK({
      shoulder: calibration.shoulder,
      target,
      upperLength: calibration.upperLength,
      forearmLength: calibration.forearmLength,
      elbowPreference: sample.elbowPreference || calibration.elbowPreference,
      limits: { shoulder: [-2.35, 2.15], elbow: [-3.12, 3.12] },
    });
    const refined = refineRenderedArm(analytic, target, calibration, geometry, Number(sample.rootRotation) || 0);
    return { ...analytic, arm: side, shoulderRotation: refined.upperRotation, elbowRotation: refined.forearmRotation, renderedElbow: refined.elbow, renderedWrist: refined.wrist, renderedError: refined.error };
  }

  solveRightHandIK(sample) { return this.solveArmIK("right", sample); }
  solveLeftHandIK(sample) { return this.solveArmIK("left", sample); }
  activeArmIK() { return this.lastIKResult ? { ...this.lastIKResult } : null; }

  poseAt(timeMs, isPlaying) {
    const pose = super.poseAt(timeMs, isPlaying);
    const safeTime = Math.max(0, Number(timeMs) || 0);
    const seconds = Math.max(0, Number(timeMs) || 0) / 1000;
    const scene = santaV3SceneAt(timeMs, this.sceneDurationMs);
    const activeClip = this.activeAnimationId === "POINT_AT"
      ? this.pointAtClip
      : this.activeAnimationId ? SANTA_V5_ANIMATION_CLIPS[this.activeAnimationId] : null;
    const clipTime = Math.max(0, safeTime - this.animationStartMs);
    pose.mouth_open = isPlaying
      ? clamp(this.speechAmplitude * 0.86 + Math.max(0, Math.sin(seconds * Math.PI * 8.4)) * 0.04)
      : 0;
    pose.pelvis_x = 0;
    pose.pelvis_rotation = 0;
    pose.left_foot_x = 0;
    pose.right_foot_x = 0;

    // A named clip temporarily owns the body channels while the neutral
    // breathing/facial channels from the base rig continue underneath it.
    // This keeps WAVE_HELLO composable without letting the long scene
    // choreography introduce an unrelated walk/sit transition.
    if (activeClip) {
      if (activeClip.id === "WAVE_HELLO" || activeClip.id === "POINT_AT") pose.breathing = 0.5;
      pose.torso_y = 0;
      pose.torso_rotation = 0;
      pose.pelvis_y = 0;
      pose.pelvis_x = 0;
      pose.pelvis_rotation = 0;
      pose.left_arm_rotation = 0;
      pose.right_arm_rotation = 0;
      pose.left_forearm_rotation = 0;
      pose.right_forearm_rotation = 0;
      pose.left_hand_rotation = 0;
      pose.right_hand_rotation = 0;
      pose.left_thigh_rotation = 0;
      pose.right_thigh_rotation = 0;
      pose.left_shin_rotation = 0;
      pose.right_shin_rotation = 0;
      pose.left_foot_rotation = 0;
      pose.right_foot_rotation = 0;
      const delta = sampleAnimationClip(activeClip, clipTime);
      for (const [channel, value] of Object.entries(delta)) pose[channel] = (pose[channel] || 0) + value;
      if (activeClip.id === "WAVE_HELLO") {
        const target = this.rightHandTarget || {
          x: delta.right_hand_target_x,
          y: delta.right_hand_target_y,
          weight: delta.right_arm_ik_weight,
          elbowPreference: SANTA_V5_RIGHT_ARM_IK_CALIBRATION.elbowPreference,
          wristRotation: 0,
        };
        const ik = this.solveRightHandIK({
          right_hand_target_x: target.x,
          right_hand_target_y: target.y,
          elbowPreference: target.elbowPreference,
        });
        const weight = clamp(target.weight ?? delta.right_arm_ik_weight);
        pose.right_hand_target_x = target.x;
        pose.right_hand_target_y = target.y;
        pose.right_arm_ik_weight = weight;
        pose.right_arm_rotation = ik.shoulderRotation * weight;
        pose.right_forearm_rotation = ik.elbowRotation * weight;
        pose.right_hand_rotation = Number(delta.right_hand_rotation) || 0;
        if (Number.isFinite(target.wristRotation)) pose.right_hand_rotation += target.wristRotation;
        this.lastIKResult = Object.freeze({
          ...ik,
          weight,
          normalizedTarget: { x: target.x, y: target.y },
          wristRotation: Number(target.wristRotation) || 0,
          appliedRenderedWrist: renderedRightArmAt(ik.shoulderRotation * weight, ik.elbowRotation * weight).wrist,
          appliedRenderedError: distanceBetween(
            renderedRightArmAt(ik.shoulderRotation * weight, ik.elbowRotation * weight).wrist,
            ik.requestedTarget,
          ),
        });
      }
      if (activeClip.id === "POINT_AT") {
        const plan = this.pointAtPlan || planPointAtTarget(SANTA_V5_DEFAULT_POINT_TARGET, { calibration: SANTA_V5_RIGHT_ARM_IK_CALIBRATION, pointerLocalAngle: SANTA_V5_POINTING_HAND.localAngle });
        const left = plan.arm === "left";
        const side = left ? "left" : "right";
        const calibration = left ? SANTA_V5_LEFT_ARM_IK_CALIBRATION : SANTA_V5_RIGHT_ARM_IK_CALIBRATION;
        const geometry = left ? SANTA_V5_LEFT_ARM_RENDER_GEOMETRY : SANTA_V5_RIGHT_ARM_RENDER_GEOMETRY;
        const weight = clamp(delta.point_at_weight);
        const headWeight = clamp(delta.point_head_weight);
        const torsoWeight = clamp(delta.point_torso_weight);
        const rootRotation = plan.torsoRotation * torsoWeight;
        const ik = left
          ? this.solveLeftHandIK({
            left_hand_target_x: plan.normalizedWrist.x,
            left_hand_target_y: plan.normalizedWrist.y,
            elbowPreference: plan.elbowPreference,
            rootRotation,
          })
          : this.solveRightHandIK({
            right_hand_target_x: plan.normalizedWrist.x,
            right_hand_target_y: plan.normalizedWrist.y,
            elbowPreference: plan.elbowPreference,
            rootRotation,
          });
        const pointerRotation = pointerRotationForIK(ik, plan, calibration);
        pose[`${side}_hand_target_x`] = plan.normalizedWrist.x;
        pose[`${side}_hand_target_y`] = plan.normalizedWrist.y;
        pose[`${side}_arm_ik_weight`] = weight;
        pose[`${side}_arm_rotation`] = ik.shoulderRotation * weight;
        pose[`${side}_forearm_rotation`] = ik.elbowRotation * weight;
        pose[`${side}_hand_rotation`] = (pointerRotation + (Number(delta.point_hand_rotation) || 0)) * weight;
        pose.head_rotation += plan.headRotation * headWeight;
        pose.torso_rotation += rootRotation;
        const applied = renderedArmAt(calibration, geometry, ik.shoulderRotation * weight, ik.elbowRotation * weight, rootRotation);
        this.lastIKResult = Object.freeze({
          ...ik,
          arm: side,
          weight,
          normalizedTarget: { ...plan.normalizedWrist },
          presentationTarget: { ...plan.target.point },
          presentationTargetId: plan.target.target.id,
          presentationTargetLabel: plan.target.label,
          pointerDirection: plan.pointerDirection,
          pointerRotation,
          targetReachable: plan.reachable,
          targetClamped: plan.clamped,
          targetOutOfReach: plan.targetOutOfReach,
          wristClearancePx: plan.wristClearancePx,
          appliedRenderedWrist: applied.wrist,
          appliedRenderedError: distanceBetween(applied.wrist, ik.requestedTarget),
        });
        /*
         * POINT_AT owns the selected arm only. The other arm remains at its
         * neutral channel values so changing targets never leaves a stale
         * right-arm pose behind when attention moves to the left side.
         */
        if (left) {
          pose.right_hand_target_x = 0;
          pose.right_hand_target_y = 0;
          pose.right_arm_ik_weight = 0;
        } else {
          pose.left_hand_target_x = 0;
          pose.left_hand_target_y = 0;
          pose.left_arm_ik_weight = 0;
        }
      }
    }

    // V5 uses the V3 choreography, but its painted parts have narrower
    // overlap zones. Keep the approved motions while constraining extremes so
    // sleeves, elbows, knees and hands remain visually connected.
    if (!activeClip && scene.action === "walk") {
      const gait = Math.sin(seconds * Math.PI * 2 * 0.95);
      pose.left_thigh_rotation = gait * 0.11;
      pose.right_thigh_rotation = -gait * 0.11;
      pose.left_shin_rotation = Math.max(0, -gait) * 0.08;
      pose.right_shin_rotation = Math.max(0, gait) * 0.08;
      pose.pelvis_x = gait * 0.012;
      pose.pelvis_y -= Math.abs(gait) * 0.012;
      pose.pelvis_rotation = gait * 0.018;
      pose.left_foot_x = gait * 0.006;
      pose.right_foot_x = -gait * 0.006;
      pose.left_arm_rotation *= 0.84;
      pose.right_arm_rotation *= 0.84;
    }
    if (!activeClip && scene.seated) {
      const seated = scene.seated;
      pose.torso_y = seated * 0.045;
      pose.torso_rotation += seated * 0.028;
      pose.pelvis_y = seated * 0.060;
      pose.pelvis_rotation = -seated * 0.024;
      pose.left_thigh_rotation = seated * 0.36;
      pose.right_thigh_rotation = -seated * 0.36;
      pose.left_shin_rotation = -seated * 0.43;
      pose.right_shin_rotation = seated * 0.43;
      pose.left_foot_x = -seated * 0.010;
      pose.right_foot_x = seated * 0.010;
    }
    if (!activeClip && (scene.action === "reach" || scene.action === "drink")) {
      limitPoseChannel(pose, "right_arm_rotation", -0.75, 1.02);
      limitPoseChannel(pose, "right_forearm_rotation", -0.82, 0.94);
      limitPoseChannel(pose, "left_arm_rotation", -0.28, 0.28);
    }
    if (!activeClip && scene.action === "explain") {
      limitPoseChannel(pose, "left_arm_rotation", -0.30, 0.34);
      limitPoseChannel(pose, "right_arm_rotation", -0.34, 0.30);
      limitPoseChannel(pose, "left_forearm_rotation", -0.38, 0.38);
      limitPoseChannel(pose, "right_forearm_rotation", -0.38, 0.38);
    }
    if (activeClip?.id === "WAVE_HELLO" || activeClip?.id === "POINT_AT") {
      const pointLeft = activeClip.id === "POINT_AT" && this.pointAtPlan?.arm === "left";
      const side = pointLeft ? "left" : "right";
      limitPoseChannel(pose, `${side}_arm_rotation`, -2.35, 2.15);
      limitPoseChannel(pose, `${side}_forearm_rotation`, -3.12, 3.12);
      limitPoseChannel(pose, `${side}_hand_rotation`, -0.34, 0.34);
      limitPoseChannel(pose, "head_rotation", -0.10, 0.10);
      limitPoseChannel(pose, "torso_rotation", -0.06, 0.06);
    }
    if (activeClip?.id !== "POINT_AT") pose.left_hand_rotation += pose.left_forearm_rotation * 0.14;
    if (activeClip?.id !== "WAVE_HELLO" && activeClip?.id !== "POINT_AT") pose.right_hand_rotation += pose.right_forearm_rotation * 0.14;
    pose.left_foot_rotation += pose.left_shin_rotation * -0.18;
    pose.right_foot_rotation += pose.right_shin_rotation * -0.18;
    if (activeClip?.id === "WAVE_HELLO") limitPoseChannel(pose, "right_hand_rotation", -0.34, 0.34);
    if (activeClip?.id === "POINT_AT") {
      const side = this.pointAtPlan?.arm === "left" ? "left" : "right";
      limitPoseChannel(pose, `${side}_hand_rotation`, -Math.PI, Math.PI);
    }
    return pose;
  }
}

export class SantaV5SceneRenderer extends SantaV3SceneRenderer {
  constructor(canvas, rig = new SantaV5Rig(), options = {}) {
    super(canvas, rig, {
      ...options,
      pack: SANTA_V5_PACK,
      title: options.title || "SANTA V5  ·  TOPAZIOVERSE",
    });
  }

  renderFrame(options = {}) {
    const animationId = this.rig.animationId?.();
    const expression = animationId === "WAVE_HELLO"
      ? "wave"
      : animationId === "POINT_AT"
        ? (this.rig.presentationTargetInfo?.()?.arm === "left" ? "point-left" : "point")
        : "neutral";
    if (this.characterRenderer.expression !== expression) this.characterRenderer.setExpression(expression);
    return super.renderFrame(options);
  }
}

export const captureSantaV5Frames = captureSantaV3Frames;
