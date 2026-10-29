import {
  captureSantaV3Frames,
  SANTA_V3_ANIMATION_FORMAT,
  SANTA_V3_ANIMATION_LIBRARY,
  SantaV3Rig,
  SantaV3SceneRenderer,
  santaV3SceneAt,
} from "./santa-v3-engine.ts";
import { SANTA_V5_PACK } from "./santa-v5-pack.mjs";

export const SANTA_V5_ANIMATION_FORMAT = SANTA_V3_ANIMATION_FORMAT;
export const SANTA_V5_ANIMATION_LIBRARY = SANTA_V3_ANIMATION_LIBRARY;

const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, Number(value) || 0));

function limitPoseChannel(pose, channel, min, max) {
  pose[channel] = Math.max(min, Math.min(max, Number(pose[channel]) || 0));
}

/**
 * V5 keeps the proven deterministic V3 choreography and adds only the
 * art-specific finishing behavior. This is deliberately a thin adapter: the
 * Stage and offline capture continue to share one animation implementation.
 */
export class SantaV5Rig extends SantaV3Rig {
  poseAt(timeMs, isPlaying) {
    const pose = super.poseAt(timeMs, isPlaying);
    const seconds = Math.max(0, Number(timeMs) || 0) / 1000;
    const scene = santaV3SceneAt(timeMs, this.sceneDurationMs);
    pose.mouth_open = isPlaying
      ? clamp(this.speechAmplitude * 0.86 + Math.max(0, Math.sin(seconds * Math.PI * 8.4)) * 0.04)
      : 0;

    // V5 uses the V3 choreography, but its painted parts have narrower
    // overlap zones. Keep the approved motions while constraining extremes so
    // sleeves, elbows, knees and hands remain visually connected.
    if (scene.action === "walk") {
      pose.left_thigh_rotation *= 0.82;
      pose.right_thigh_rotation *= 0.82;
      pose.left_shin_rotation *= 0.74;
      pose.right_shin_rotation *= 0.74;
      pose.left_arm_rotation *= 0.84;
      pose.right_arm_rotation *= 0.84;
    }
    if (scene.seated) {
      pose.left_thigh_rotation *= 0.78;
      pose.right_thigh_rotation *= 0.78;
      pose.left_shin_rotation *= 0.78;
      pose.right_shin_rotation *= 0.78;
    }
    if (scene.action === "reach" || scene.action === "drink") {
      limitPoseChannel(pose, "right_arm_rotation", -0.75, 1.02);
      limitPoseChannel(pose, "right_forearm_rotation", -0.82, 0.94);
      limitPoseChannel(pose, "left_arm_rotation", -0.28, 0.28);
    }
    if (scene.action === "explain") {
      limitPoseChannel(pose, "left_arm_rotation", -0.30, 0.34);
      limitPoseChannel(pose, "right_arm_rotation", -0.34, 0.30);
      limitPoseChannel(pose, "left_forearm_rotation", -0.38, 0.38);
      limitPoseChannel(pose, "right_forearm_rotation", -0.38, 0.38);
    }
    pose.left_hand_rotation += pose.left_forearm_rotation * 0.14;
    pose.right_hand_rotation += pose.right_forearm_rotation * 0.14;
    pose.left_foot_rotation += pose.left_shin_rotation * -0.18;
    pose.right_foot_rotation += pose.right_shin_rotation * -0.18;
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
