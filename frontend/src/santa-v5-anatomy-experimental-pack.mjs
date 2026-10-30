import { SANTA_V5_PACK } from "./santa-v5-pack.mjs";

const EXPERIMENTAL_ROOT = "assets/characters/topazio-narrators-v5/experimental-anatomy";
const asset = (file) => `${EXPERIMENTAL_ROOT}/${file}`;

const replacements = Object.freeze({
  left_upper_arm: asset("upper-arm-left-anatomy.png"),
  right_upper_arm: asset("upper-arm-right-anatomy.png"),
  left_forearm: asset("forearm-left-anatomy.png"),
  right_forearm: asset("forearm-right-anatomy.png"),
});

const baseLayers = SANTA_V5_PACK.layers.map((layer) => ({
  ...layer,
  asset: replacements[layer.id] || layer.asset,
  // Mission 015 keeps this foot adjustment experimental and isolated.  The
  // walking choreography and official V5 pack remain untouched.
  size: layer.id === "left_foot" || layer.id === "right_foot"
    ? [0.74, 0.26]
    : layer.size,
}));

const leftForearm = baseLayers.find((layer) => layer.id === "left_forearm");
const rightForearm = baseLayers.find((layer) => layer.id === "right_forearm");
const leftHand = baseLayers.find((layer) => layer.id === "left_hand");
const rightHand = baseLayers.find((layer) => layer.id === "right_hand");

export const SANTA_V5_ANATOMY_EXPERIMENTAL_PACK = {
  ...SANTA_V5_PACK,
  id: "topazio-narrator-santa-v5-anatomy-experimental",
  name: "Santa, narrador oficial · V5 anatomy-first experimental",
  art_status: "experimental-anatomy-first",
  anatomy_segments: [
    { id: "shoulder-cap-left", source: "upper-arm-left.png", role: "shoulder" },
    { id: "upper-arm-left", source: "upper-arm-left-anatomy.png", role: "upper-arm" },
    { id: "elbow-left", source: "forearm-left-anatomy.png", role: "elbow-overlap" },
    { id: "forearm-left", source: "forearm-left-anatomy.png", role: "forearm" },
    { id: "cuff-left", source: "cuff-left-anatomy.png", role: "wrist-cuff" },
    { id: "hand-left", source: "hand-left.png", role: "hand" },
    { id: "shoulder-cap-right", source: "upper-arm-right.png", role: "shoulder" },
    { id: "upper-arm-right", source: "upper-arm-right-anatomy.png", role: "upper-arm" },
    { id: "elbow-right", source: "forearm-right-anatomy.png", role: "elbow-overlap" },
    { id: "forearm-right", source: "forearm-right-anatomy.png", role: "forearm" },
    { id: "cuff-right", source: "cuff-right-anatomy.png", role: "wrist-cuff" },
    { id: "hand-right", source: "hand-right.png", role: "hand" },
  ],
  anatomy_experiments: {
    arm: "masked anatomical bands derived from approved V5 layers; cuff and hand are independent nodes",
    feet: "experimental 0.74 x 0.26 rendered foot scale; no walk timing or foot pivots changed",
    mesh_deformation: "not-executed: Godot and Inochi2D executables were unavailable locally",
  },
  layers: [
    ...baseLayers.filter((layer) => layer.id !== "left_hand" && layer.id !== "right_hand"),
    {
      ...leftForearm,
      id: "left_cuff",
      role: "accessory",
      asset: asset("cuff-left-anatomy.png"),
      parent: "left_forearm",
      position: [0.52, 0.76],
      size: [0.82, 0.36],
      z: 3,
    },
    {
      ...rightForearm,
      id: "right_cuff",
      role: "accessory",
      asset: asset("cuff-right-anatomy.png"),
      parent: "right_forearm",
      position: [0.48, 0.76],
      size: [0.82, 0.36],
      z: 3,
    },
    {
      ...leftHand,
      parent: "left_forearm",
      position: [0.54, 0.76],
      size: [0.88, 0.46],
      z: 4,
    },
    {
      ...rightHand,
      parent: "right_forearm",
      position: [0.47, 0.72],
      size: [0.88, 0.46],
      z: 4,
    },
  ],
};
