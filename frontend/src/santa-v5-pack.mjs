import { ANIMATION_READY_PROFILE } from "./character-pack.mjs";

const ROOT = "assets/characters/topazio-narrators-v5/santa";
const asset = (file) => `${ROOT}/${file}`;

/**
 * Santa V5 art-production preview.
 *
 * This is deliberately not the final animation-ready contract: the generated
 * production pieces currently combine some adjacent joints (arm+hand and
 * thigh+boot). It exists to validate scale, silhouette and basic transforms
 * before the art is approved for fine-grained facial and limb rigging.
 */
export const SANTA_V5_PACK = {
  format: "fabuloom.character/0.1",
  rig_profile: ANIMATION_READY_PROFILE,
  id: "topazio-narrator-santa-v5-preview",
  name: "Santa, arte de produção · V5 preview",
  voice_id: "pm_santa",
  language: "pt-BR",
  art_status: "production-art-preview",
  layers: [
    { id: "left_leg", role: "upper_leg", asset: asset("leg-left.png"), parent: "pelvis", anchor: [0.5, 0.08], position: [0.34, 0.56], size: [0.30, 0.62], z: -3 },
    { id: "right_leg", role: "upper_leg", asset: asset("leg-right.png"), parent: "pelvis", anchor: [0.5, 0.08], position: [0.66, 0.56], size: [0.30, 0.62], z: -3 },
    { id: "pelvis", role: "pelvis", asset: asset("pelvis.png"), parent: "torso", anchor: [0.5, 0.42], position: [0.5, 0.72], size: [0.70, 0.38], z: -2 },
    { id: "torso", role: "torso", asset: asset("torso.png"), parent: null, anchor: [0.5, 0.48], position: [0.5, 0.45], size: [0.66, 0.62], z: 0 },
    { id: "left_arm", role: "upper_arm", asset: asset("arm-left.png"), parent: "torso", anchor: [0.5, 0.08], position: [0.14, 0.37], size: [0.30, 0.48], z: 2 },
    { id: "right_arm", role: "upper_arm", asset: asset("arm-right.png"), parent: "torso", anchor: [0.5, 0.08], position: [0.86, 0.37], size: [0.30, 0.48], z: 2 },
    { id: "head", role: "head", asset: asset("head.png"), parent: "torso", anchor: [0.5, 0.58], position: [0.5, 0.14], size: [0.46, 0.40], z: 6 },
  ],
  expressions: [{ id: "neutral", overrides: {} }],
  bindings: {
    head_rotation: "head",
    breathing: "torso",
    torso_rotation: "torso",
    torso_y: "torso",
    pelvis_y: "pelvis",
    left_arm_rotation: "left_arm",
    right_arm_rotation: "right_arm",
    left_thigh_rotation: "left_leg",
    right_thigh_rotation: "right_leg",
  },
};
