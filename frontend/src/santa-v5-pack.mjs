import { ANIMATION_READY_PROFILE } from "./character-pack.mjs";

const ROOT = "assets/characters/topazio-narrators-v5/santa";
const asset = (file) => `${ROOT}/${file}`;

/**
 * Santa V5's production rig.
 *
 * The V5 artwork remains the approved source of truth, while the pack exposes
 * a fine-grained, deterministic hierarchy for the existing Character Engine.
 * Every joint is a normal layer transform; no provider or model code is
 * coupled to this descriptor.
 */
export const SANTA_V5_PACK = {
  format: "fabuloom.character/0.1",
  rig_profile: ANIMATION_READY_PROFILE,
  id: "topazio-narrator-santa-v5",
  name: "Santa, narrador oficial · V5 articulável",
  voice_id: "pm_santa",
  language: "pt-BR",
  art_status: "production-rig-v1",
  layers: [
    { id: "hair_back", role: "hair_back", asset: asset("hair-back.png"), parent: "torso", anchor: [0.5, 0.52], position: [0.5, 0.18], size: [0.70, 0.46], z: -7 },
    { id: "left_foot", role: "foot", asset: asset("foot-left.png"), parent: "left_shin", anchor: [0.5, 0.16], position: [0.48, 0.80], size: [0.86, 0.30], z: -6 },
    { id: "right_foot", role: "foot", asset: asset("foot-right.png"), parent: "right_shin", anchor: [0.5, 0.16], position: [0.52, 0.80], size: [0.86, 0.30], z: -6 },
    { id: "left_shin", role: "lower_leg", asset: asset("shin-left.png"), parent: "left_thigh", anchor: [0.5, 0.08], position: [0.5, 0.66], size: [0.66, 0.72], z: -5 },
    { id: "right_shin", role: "lower_leg", asset: asset("shin-right.png"), parent: "right_thigh", anchor: [0.5, 0.08], position: [0.5, 0.66], size: [0.66, 0.72], z: -5 },
    { id: "pelvis", role: "pelvis", asset: asset("pelvis.png"), parent: "torso", anchor: [0.5, 0.42], position: [0.5, 0.67], size: [0.78, 0.42], z: -4 },
    { id: "left_thigh", role: "upper_leg", asset: asset("thigh-left.png"), parent: "pelvis", anchor: [0.5, 0.08], position: [0.32, 0.34], size: [0.66, 0.72], z: -3 },
    { id: "right_thigh", role: "upper_leg", asset: asset("thigh-right.png"), parent: "pelvis", anchor: [0.5, 0.08], position: [0.68, 0.34], size: [0.66, 0.72], z: -3 },
    { id: "torso", role: "torso", asset: asset("torso.png"), parent: null, anchor: [0.5, 0.5], position: [0.5, 0.46], size: [0.66, 0.72], z: 0 },
    { id: "left_upper_arm", role: "upper_arm", asset: asset("upper-arm-left.png"), parent: "torso", anchor: [0.5, 0.08], position: [0.11, 0.14], size: [0.34, 0.43], z: 1 },
    { id: "right_upper_arm", role: "upper_arm", asset: asset("upper-arm-right.png"), parent: "torso", anchor: [0.5, 0.08], position: [0.84, 0.15], size: [0.34, 0.43], z: 1 },
    { id: "left_forearm", role: "forearm", asset: asset("forearm-left.png"), parent: "left_upper_arm", anchor: [0.5, 0.08], position: [0.54, 0.57], size: [0.74, 0.46], z: 2 },
    { id: "right_forearm", role: "forearm", asset: asset("forearm-right.png"), parent: "right_upper_arm", anchor: [0.5, 0.08], position: [0.46, 0.53], size: [0.74, 0.46], z: 2 },
    { id: "left_hand", role: "hand", asset: asset("hand-left.png"), parent: "left_forearm", anchor: [0.5, 0.10], position: [0.54, 0.76], size: [0.68, 0.34], z: 3 },
    { id: "right_hand", role: "hand", asset: asset("hand-right.png"), parent: "right_forearm", anchor: [0.5, 0.10], position: [0.47, 0.72], size: [0.68, 0.34], z: 3 },
    { id: "neck", role: "neck", asset: asset("neck.png"), parent: "torso", anchor: [0.5, 0.55], position: [0.5, 0.20], size: [0.46, 0.34], z: 4 },
    { id: "head", role: "head", asset: asset("head.png"), parent: "neck", anchor: [0.5, 0.54], position: [0.5, 0.10], size: [0.84, 0.80], z: 6 },
    { id: "hair_front", role: "hair_front", asset: asset("hair-front.png"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.38], size: [0.94, 0.78], z: 7 },
    { id: "eyes", role: "eyes", asset: asset("eyes-open.png"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.54], size: [0.68, 0.28], z: 8 },
    { id: "eyelids", role: "eyelids", asset: asset("eyelids-closed.png"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.54], size: [0.68, 0.28], z: 9 },
    { id: "brows", role: "brows", asset: asset("brows.png"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.37], size: [0.68, 0.23], z: 10 },
    { id: "glasses", role: "accessory", asset: asset("glasses.png"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.54], size: [0.72, 0.32], z: 11 },
    { id: "beard", role: "accessory", asset: asset("beard.png"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.77], size: [0.66, 0.42], z: 12 },
    { id: "mouth", role: "mouth", asset: asset("mouth-closed.png"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.75], size: [0.34, 0.19], z: 13 },
  ],
  expressions: [
    { id: "neutral", overrides: {} },
    { id: "smile", overrides: { mouth: asset("mouth-open.png") } },
    { id: "wave", overrides: { right_hand: asset("hand-right-wave.png") } },
  ],
  bindings: {
    head_rotation: "head",
    eye_open: "eyelids",
    mouth_open: "mouth",
    breathing: "torso",
    hair_sway: "hair_front",
    brow_raise: "brows",
    torso_rotation: "torso",
    torso_y: "torso",
    pelvis_x: "pelvis",
    pelvis_y: "pelvis",
    pelvis_rotation: "pelvis",
    left_arm_rotation: "left_upper_arm",
    right_arm_rotation: "right_upper_arm",
    left_forearm_rotation: "left_forearm",
    right_forearm_rotation: "right_forearm",
    left_hand_rotation: "left_hand",
    right_hand_rotation: "right_hand",
    left_thigh_rotation: "left_thigh",
    right_thigh_rotation: "right_thigh",
    left_shin_rotation: "left_shin",
    right_shin_rotation: "right_shin",
    left_foot_rotation: "left_foot",
    right_foot_rotation: "right_foot",
    left_foot_x: "left_foot",
    right_foot_x: "right_foot",
  },
};
