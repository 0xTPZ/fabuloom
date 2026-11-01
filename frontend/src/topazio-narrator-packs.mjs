import { ANIMATION_READY_PROFILE } from "./character-pack.mjs";

/**
 * Three intentionally simple narrator packs for the current Character Stage.
 * They share one visual language and the same low-complexity animation rig.
 */
const COMMON_EYES = "assets/characters/fantasy-narrator/eyes.svg";
const COMMON_EYELIDS = "assets/characters/fantasy-narrator/eyelids.svg";
const COMMON_BROWS = "assets/characters/fantasy-narrator/brows.svg";
const COMMON_MOUTH = "assets/characters/fantasy-narrator/mouth.svg";
const COMMON_SMILE = "assets/characters/fantasy-narrator/mouth-smile.svg";

function createNarratorPack({ id, name, voice_id, portrait }) {
  return {
    format: "fabuloom.character/0.1",
    id,
    name,
    voice_id,
    language: "pt-BR",
    layers: [
      {
        id: "portrait",
        asset: `assets/characters/topazio-narrators/${portrait}`,
        parent: null,
        anchor: [0.5, 0.5],
        position: [0.5, 0.6],
        size: [0.48, 0.96],
        z: 0,
      },
      {
        id: "eyes",
        asset: COMMON_EYES,
        parent: "portrait",
        anchor: [0.5, 0.5],
        position: [0.48, 0.2],
        size: [0.22, 0.055],
        z: 2,
      },
      {
        id: "eyelids",
        asset: COMMON_EYELIDS,
        parent: "portrait",
        anchor: [0.5, 0.5],
        position: [0.48, 0.205],
        size: [0.22, 0.055],
        z: 3,
      },
      {
        id: "brows",
        asset: COMMON_BROWS,
        parent: "portrait",
        anchor: [0.5, 0.5],
        position: [0.48, 0.14],
        size: [0.23, 0.06],
        z: 4,
      },
      {
        id: "mouth",
        asset: COMMON_MOUTH,
        parent: "portrait",
        anchor: [0.5, 0.5],
        position: [0.48, 0.33],
        size: [0.14, 0.05],
        z: 5,
      },
    ],
    expressions: [
      { id: "neutral", overrides: {} },
      { id: "smile", overrides: { mouth: COMMON_SMILE } },
    ],
    bindings: {
      head_rotation: "portrait",
      eye_open: "eyelids",
      mouth_open: "mouth",
      breathing: "portrait",
      brow_raise: "brows",
      expression: "mouth",
    },
  };
}

export const DORA_NARRATOR_PACK = createNarratorPack({
  id: "topazio-narrator-dora",
  name: "Dora, voz acolhedora",
  voice_id: "pf_dora",
  portrait: "dora.png",
});

export const SANTA_NARRATOR_PACK = createNarratorPack({
  id: "topazio-narrator-santa",
  name: "Santa, voz sábia",
  voice_id: "pm_santa",
  portrait: "santa.png",
});

export const ALEX_NARRATOR_PACK = createNarratorPack({
  id: "topazio-narrator-alex",
  name: "Alex, voz confiante",
  voice_id: "pm_alex",
  portrait: "alex.png",
});

export const TOPAZIO_NARRATOR_PACKS_V1 = {
  dora: DORA_NARRATOR_PACK,
  santa: SANTA_NARRATOR_PACK,
  alex: ALEX_NARRATOR_PACK,
};

const V2_SHARED = "assets/characters/topazio-narrators-v2/shared";

function createAnimationReadyPack({ id, name, voice_id, character, head, hairBack, hairFront, brows, mouth }) {
  const asset = (file) => `assets/characters/topazio-narrators-v2/${character}/${file}`;
  return {
    format: "fabuloom.character/0.1",
    rig_profile: ANIMATION_READY_PROFILE,
    id,
    name,
    voice_id,
    language: "pt-BR",
    layers: [
      { id: "torso", role: "torso", asset: `${V2_SHARED}/torso.svg`, parent: null, anchor: [0.5, 0.5], position: [0.5, 0.56], size: [0.48, 0.95], z: 0 },
      { id: "hair_back", role: "hair_back", asset: asset(hairBack), parent: "torso", anchor: [0.5, 0.34], position: [0.5, 0.24], size: [0.48, 0.46], z: -1 },
      { id: "left_upper_arm", role: "upper_arm", asset: `${V2_SHARED}/upper-arm-left.svg`, parent: "torso", anchor: [0.5, 0.1], position: [0.18, 0.38], size: [0.34, 0.56], z: 1 },
      { id: "right_upper_arm", role: "upper_arm", asset: `${V2_SHARED}/upper-arm-right.svg`, parent: "torso", anchor: [0.5, 0.1], position: [0.82, 0.38], size: [0.34, 0.56], z: 1 },
      { id: "left_forearm", role: "forearm", asset: `${V2_SHARED}/forearm-left.svg`, parent: "left_upper_arm", anchor: [0.5, 0.1], position: [0.56, 0.78], size: [0.96, 0.82], z: 2 },
      { id: "right_forearm", role: "forearm", asset: `${V2_SHARED}/forearm-right.svg`, parent: "right_upper_arm", anchor: [0.5, 0.1], position: [0.44, 0.78], size: [0.96, 0.82], z: 2 },
      { id: "left_hand", role: "hand", asset: `${V2_SHARED}/hand-left.svg`, parent: "left_forearm", anchor: [0.5, 0.1], position: [0.54, 0.82], size: [0.82, 0.46], z: 3 },
      { id: "right_hand", role: "hand", asset: `${V2_SHARED}/hand-right.svg`, parent: "right_forearm", anchor: [0.5, 0.1], position: [0.46, 0.82], size: [0.82, 0.46], z: 3 },
      { id: "neck", role: "neck", asset: `${V2_SHARED}/neck.svg`, parent: "torso", anchor: [0.5, 0.55], position: [0.5, 0.25], size: [0.50, 0.44], z: 4 },
      { id: "head", role: "head", asset: asset(head), parent: "neck", anchor: [0.5, 0.52], position: [0.5, 0.16], size: [0.92, 0.68], z: 6 },
      { id: "hair_front", role: "hair_front", asset: asset(hairFront), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.46], size: [0.92, 0.80], z: 7 },
      { id: "eyes", role: "eyes", asset: `${V2_SHARED}/eyes.svg`, parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.55], size: [0.78, 0.35], z: 8 },
      { id: "eyelids", role: "eyelids", asset: `${V2_SHARED}/eyelids.svg`, parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.55], size: [0.78, 0.35], z: 9 },
      { id: "brows", role: "brows", asset: asset(brows), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.39], size: [0.78, 0.28], z: 10 },
      { id: "mouth", role: "mouth", asset: asset(mouth), parent: "head", anchor: [0.5, 0.5], position: [0.5, 0.75], size: [0.38, 0.22], z: 11 },
      { id: "accessory", role: "accessory", asset: `${V2_SHARED}/accessory.svg`, parent: "torso", anchor: [0.5, 0.14], position: [0.5, 0.52], size: [0.18, 0.28], z: 12 },
    ],
    expressions: [
      { id: "neutral", overrides: {} },
      { id: "smile", overrides: { mouth: `${V2_SHARED}/mouth-smile.svg` } },
    ],
    bindings: {
      head_rotation: "head",
      eye_open: "eyelids",
      mouth_open: "mouth",
      breathing: "torso",
      left_arm: "left_upper_arm",
      right_arm: "right_upper_arm",
      hair_sway: "hair_front",
      brow_raise: "brows",
      expression: "mouth",
    },
  };
}

export const DORA_NARRATOR_PACK_V2 = createAnimationReadyPack({
  id: "topazio-narrator-dora-v2", name: "Dora, voz acolhedora · V2 animável", voice_id: "pf_dora", character: "dora", head: "head.svg", hairBack: "hair-back.svg", hairFront: "hair-front.svg", brows: "brows.svg", mouth: "mouth.svg",
});
export const SANTA_NARRATOR_PACK_V2 = createAnimationReadyPack({
  id: "topazio-narrator-santa-v2", name: "Santa, voz sábia · V2 animável", voice_id: "pm_santa", character: "santa", head: "head.svg", hairBack: "hair-back.svg", hairFront: "hair-front.svg", brows: "brows.svg", mouth: "mouth.svg",
});
export const ALEX_NARRATOR_PACK_V2 = createAnimationReadyPack({
  id: "topazio-narrator-alex-v2", name: "Alex, voz confiante · V2 animável", voice_id: "pm_alex", character: "alex", head: "head.svg", hairBack: "hair-back.svg", hairFront: "hair-front.svg", brows: "brows.svg", mouth: "mouth.svg",
});

export const TOPAZIO_NARRATOR_PACKS_V2 = {
  dora: DORA_NARRATOR_PACK_V2,
  santa: SANTA_NARRATOR_PACK_V2,
  alex: ALEX_NARRATOR_PACK_V2,
};

export const TOPAZIO_NARRATOR_PACKS = TOPAZIO_NARRATOR_PACKS_V2;
