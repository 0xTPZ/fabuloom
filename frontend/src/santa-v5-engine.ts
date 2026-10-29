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
import { SANTA_V5_PACK } from "./santa-v5-pack.mjs";

export const SANTA_V5_ANIMATION_FORMAT = SANTA_V3_ANIMATION_FORMAT;

const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, Number(value) || 0));

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
    { timeMs: 0, easing: "ease-in-out", channels: { right_arm_rotation: 0, right_forearm_rotation: 0, right_hand_rotation: 0, head_rotation: 0, torso_rotation: 0 } },
    { timeMs: 320, easing: "ease-in-out", channels: { right_arm_rotation: -0.055, right_forearm_rotation: -0.045, right_hand_rotation: -0.025, head_rotation: -0.012, torso_rotation: -0.008 } },
    { timeMs: 1180, easing: "ease-out", channels: { right_arm_rotation: 0.92, right_forearm_rotation: 1.08, right_hand_rotation: 0.045, head_rotation: -0.042, torso_rotation: -0.018 } },
    { timeMs: 1680, easing: "ease-in-out", channels: { right_arm_rotation: 1.05, right_forearm_rotation: 1.24, right_hand_rotation: -0.30, head_rotation: -0.035, torso_rotation: -0.016 } },
    { timeMs: 2120, easing: "ease-in-out", channels: { right_arm_rotation: 1.08, right_forearm_rotation: 1.28, right_hand_rotation: 0.28, head_rotation: -0.028, torso_rotation: -0.014 } },
    { timeMs: 2560, easing: "ease-in-out", channels: { right_arm_rotation: 1.04, right_forearm_rotation: 1.25, right_hand_rotation: -0.30, head_rotation: -0.026, torso_rotation: -0.013 } },
    { timeMs: 3000, easing: "ease-in-out", channels: { right_arm_rotation: 0.98, right_forearm_rotation: 1.18, right_hand_rotation: 0.23, head_rotation: -0.022, torso_rotation: -0.010 } },
    { timeMs: 3560, easing: "ease-in", channels: { right_arm_rotation: 0.64, right_forearm_rotation: 0.78, right_hand_rotation: 0.06, head_rotation: -0.012, torso_rotation: -0.006 } },
    { timeMs: 4600, easing: "ease-in-out", channels: { right_arm_rotation: 0, right_forearm_rotation: 0, right_hand_rotation: 0, head_rotation: 0, torso_rotation: 0 } },
  ],
});

const SANTA_V5_ANIMATION_CLIPS = Object.freeze({ WAVE_HELLO: SANTA_V5_WAVE_HELLO_CLIP });

export const SANTA_V5_ANIMATION_LIBRARY = Object.freeze({
  ...SANTA_V3_ANIMATION_LIBRARY,
  WAVE_HELLO: { durationMs: SANTA_V5_WAVE_HELLO_CLIP.durationMs, sample: (timeMs) => sampleAnimationClip(SANTA_V5_WAVE_HELLO_CLIP, timeMs) },
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
  }

  setAnimation(animationId, startTimeMs = 0) {
    if (animationId === null || animationId === undefined || animationId === "") {
      this.activeAnimationId = null;
      this.animationStartMs = 0;
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
    return this;
  }

  animationId() { return this.activeAnimationId; }

  poseAt(timeMs, isPlaying) {
    const pose = super.poseAt(timeMs, isPlaying);
    const safeTime = Math.max(0, Number(timeMs) || 0);
    const seconds = Math.max(0, Number(timeMs) || 0) / 1000;
    const scene = santaV3SceneAt(timeMs, this.sceneDurationMs);
    const activeClip = this.activeAnimationId ? SANTA_V5_ANIMATION_CLIPS[this.activeAnimationId] : null;
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
      pose.torso_y = 0;
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
    if (activeClip?.id === "WAVE_HELLO") {
      limitPoseChannel(pose, "right_arm_rotation", -0.22, 1.12);
      limitPoseChannel(pose, "right_forearm_rotation", -0.18, 1.32);
      limitPoseChannel(pose, "right_hand_rotation", -0.34, 0.34);
      limitPoseChannel(pose, "head_rotation", -0.10, 0.10);
      limitPoseChannel(pose, "torso_rotation", -0.06, 0.06);
    }
    pose.left_hand_rotation += pose.left_forearm_rotation * 0.14;
    pose.right_hand_rotation += pose.right_forearm_rotation * 0.14;
    pose.left_foot_rotation += pose.left_shin_rotation * -0.18;
    pose.right_foot_rotation += pose.right_shin_rotation * -0.18;
    if (activeClip?.id === "WAVE_HELLO") limitPoseChannel(pose, "right_hand_rotation", -0.34, 0.34);
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
}

export const captureSantaV5Frames = captureSantaV3Frames;
