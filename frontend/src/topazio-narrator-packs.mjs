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

export const TOPAZIO_NARRATOR_PACKS = {
  dora: DORA_NARRATOR_PACK,
  santa: SANTA_NARRATOR_PACK,
  alex: ALEX_NARRATOR_PACK,
};
