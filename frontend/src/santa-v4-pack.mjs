import { ANIMATION_READY_PROFILE } from "./character-pack.mjs";

const ROOT = "assets/characters/topazio-narrators-v4/santa";
const V2 = "assets/characters/topazio-narrators-v2";
const shared = (file) => `${V2}/shared/${file}`;
const santa = (file) => `${ROOT}/${file}`;

/** Santa V4: same public descriptor and hierarchy as V3, with a softer,
 * more expressive illustrated layer set and separate glasses/beard accents. */
export const SANTA_V4_PACK = {
  format: "fabuloom.character/0.1",
  rig_profile: ANIMATION_READY_PROFILE,
  id: "topazio-narrator-santa-v4",
  name: "Santa, narrador oficial · V4 cartoon",
  voice_id: "pm_santa",
  language: "pt-BR",
  layers: [
    { id: "hair_back", role: "hair_back", asset: santa("hair-back.svg"), parent: "torso", anchor: [0.5, 0.34], position: [0.5, 0.18], size: [0.64, 0.40], z: -6 },
    { id: "left_shoe", role: "foot", asset: santa("shoe-left.svg"), parent: "left_shin", anchor: [0.5, 0.18], position: [0.48, 0.55], size: [0.72, 0.35], z: -5 },
    { id: "right_shoe", role: "foot", asset: santa("shoe-right.svg"), parent: "right_shin", anchor: [0.5, 0.18], position: [0.52, 0.55], size: [0.72, 0.35], z: -5 },
    { id: "left_shin", role: "lower_leg", asset: santa("shin-left.svg"), parent: "left_thigh", anchor: [0.5, 0.08], position: [0.5, 0.55], size: [0.62, 0.65], z: -4 },
    { id: "right_shin", role: "lower_leg", asset: santa("shin-right.svg"), parent: "right_thigh", anchor: [0.5, 0.08], position: [0.5, 0.55], size: [0.62, 0.65], z: -4 },
    { id: "pelvis", role: "pelvis", asset: santa("pelvis.svg"), parent: "torso", anchor: [0.5, 0.44], position: [0.5, 0.65], size: [0.72, 0.40], z: -3 },
    { id: "left_thigh", role: "upper_leg", asset: santa("thigh-left.svg"), parent: "pelvis", anchor: [0.5, 0.08], position: [0.32, 0.32], size: [0.62, 0.70], z: -2 },
    { id: "right_thigh", role: "upper_leg", asset: santa("thigh-right.svg"), parent: "pelvis", anchor: [0.5, 0.08], position: [0.68, 0.32], size: [0.62, 0.70], z: -2 },
    { id: "torso", role: "torso", asset: santa("torso.svg"), parent: null, anchor: [0.5, 0.5], position: [0.5, 0.48], size: [0.58, 0.62], z: 0 },
    { id: "left_upper_arm", role: "upper_arm", asset: santa("upper-arm-left.svg"), parent: "torso", anchor: [0.5, 0.08], position: [0.14, 0.34], size: [0.30, 0.42], z: 1 },
    { id: "right_upper_arm", role: "upper_arm", asset: santa("upper-arm-right.svg"), parent: "torso", anchor: [0.5, 0.08], position: [0.86, 0.34], size: [0.30, 0.42], z: 1 },
    { id: "left_forearm", role: "forearm", asset: santa("forearm-left.svg"), parent: "left_upper_arm", anchor: [0.5, 0.08], position: [0.56, 0.55], size: [0.70, 0.50], z: 2 },
    { id: "right_forearm", role: "forearm", asset: santa("forearm-right.svg"), parent: "right_upper_arm", anchor: [0.5, 0.08], position: [0.44, 0.55], size: [0.70, 0.50], z: 2 },
    { id: "left_hand", role: "hand", asset: santa("hand-left.svg"), parent: "left_forearm", anchor: [0.5, 0.10], position: [0.54, 0.72], size: [0.38, 0.25], z: 3 },
    { id: "right_hand", role: "hand", asset: santa("hand-right.svg"), parent: "right_forearm", anchor: [0.5, 0.10], position: [0.46, 0.72], size: [0.38, 0.25], z: 3 },
    { id: "neck", role: "neck", asset: shared("neck.svg"), parent: "torso", anchor: [0.5, 0.55], position: [0.5, 0.23], size: [0.44, 0.38], z: 4 },
    { id: "head", role: "head", asset: santa("head.svg"), parent: "neck", anchor: [0.5, 0.52], position: [0.5, 0.13], size: [0.58, 0.64], z: 6 },
    { id: "hair_front", role: "hair_front", asset: santa("hair-front.svg"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.40], size: [0.84, 0.70], z: 7 },
    { id: "eyes", role: "eyes", asset: shared("eyes.svg"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.53], size: [0.70, 0.32], z: 8 },
    { id: "eyelids", role: "eyelids", asset: shared("eyelids.svg"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.53], size: [0.70, 0.32], z: 9 },
    { id: "brows", role: "brows", asset: santa("brows.svg"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.36], size: [0.72, 0.24], z: 10 },
    { id: "glasses", role: "accessory", asset: santa("glasses.svg"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.53], size: [0.80, 0.36], z: 11 },
    { id: "beard", role: "accessory", asset: santa("beard.svg"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.77], size: [0.70, 0.48], z: 12 },
    { id: "mouth", role: "mouth", asset: santa("mouth.svg"), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.74], size: [0.28, 0.17], z: 13 },
  ],
  expressions: [
    { id: "neutral", overrides: {} },
    { id: "smile", overrides: { mouth: shared("mouth-smile.svg") } },
  ],
  bindings: {
    head_rotation: "head", eye_open: "eyelids", mouth_open: "mouth", breathing: "torso", brow_raise: "brows",
    hair_sway: "hair_front", torso_rotation: "torso", torso_y: "torso", pelvis_y: "pelvis",
    left_arm_rotation: "left_upper_arm", right_arm_rotation: "right_upper_arm",
    left_forearm_rotation: "left_forearm", right_forearm_rotation: "right_forearm",
    left_hand_rotation: "left_hand", right_hand_rotation: "right_hand",
    left_thigh_rotation: "left_thigh", right_thigh_rotation: "right_thigh",
    left_shin_rotation: "left_shin", right_shin_rotation: "right_shin",
    left_foot_rotation: "left_shoe", right_foot_rotation: "right_shoe",
    expression: "mouth",
  },
};
