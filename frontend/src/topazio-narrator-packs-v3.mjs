/**
 * Topazioverse official narrator art reforge, V3.
 *
 * Dora and Alex use the same polished bust reference as their visual base,
 * with aligned, transparent eyelid and mouth plates layered through the
 * existing NarratorAvatarRenderer.  The base is deliberately an art asset,
 * not a second animation engine: time, RMS and expression selection remain
 * owned by the shared facial rig.
 */

import { ANIMATION_READY_PROFILE, CHARACTER_FORMAT, validateCharacterPack } from "./character-pack.mjs";

const ROOT = "assets/characters/topazio-narrators-v3";
const SOURCE_SIZE = Object.freeze([1145, 1374]);
const BASE_SIZE = Object.freeze([0.82, 0.553]);
const BASE_POSITION = Object.freeze([0.5, 0.34]);

function asset(character, name) {
  return `${ROOT}/${character}/${name}`;
}

function createReforgedPack({ id, name, character, voice_id }) {
  const base = asset(character, "head-clean.png");
  // The V3 suffix is intentional: narrator-mode's Santa V5 alpha alignment
  // table must not reinterpret these full-canvas overlays as Santa plates.
  const eyelids = asset(character, "eyelids-closed-v3.png");
  const mouthClosed = asset(character, "mouth-closed-v3.png");
  const mouthOpen = asset(character, "mouth-open-v3c.png");
  const pack = {
    format: CHARACTER_FORMAT,
    rig_profile: ANIMATION_READY_PROFILE,
    id,
    name,
    character,
    voice_id,
    language: "pt-BR",
    art_status: "art-reforge-v3-experimental-awaiting-art-approval",
    art_notes: "Cinematic bust base with aligned transparent eyelid and mouth plates; full-body independent layers remain outside this mission.",
    layers: [
      {
        id: "head",
        role: "head",
        asset: base,
        parent: null,
        anchor: [0.5, 0.5],
        position: [...BASE_POSITION],
        size: [...BASE_SIZE],
        source_size: [...SOURCE_SIZE],
        z: 0,
      },
      {
        id: "eyelids",
        role: "eyelids",
        asset: eyelids,
        parent: "head",
        anchor: [0.5, 0.5],
        position: [0.5, 0.5],
        size: [1, 1],
        source_size: [...SOURCE_SIZE],
        z: 1,
      },
      {
        id: "mouth",
        role: "mouth",
        asset: mouthClosed,
        parent: "head",
        anchor: [0.5, 0.5],
        position: [0.5, 0.5],
        size: [1, 1],
        source_size: [...SOURCE_SIZE],
        mouth_motion: "subtle",
        z: 2,
      },
    ],
    expressions: [
      { id: "neutral", overrides: {} },
      { id: "smile", overrides: { mouth: mouthOpen } },
    ],
    bindings: {
      head_rotation: "head",
      eye_open: "eyelids",
      mouth_open: "mouth",
      breathing: "head",
      hair_sway: "head",
    },
  };
  return Object.freeze(validateCharacterPack(pack));
}

export const DORA_NARRATOR_PACK_V3 = createReforgedPack({
  id: "topazio-narrator-dora-v3",
  name: "Dora · narradora oficial V3",
  character: "dora",
  voice_id: "pf_dora",
});

export const ALEX_NARRATOR_PACK_V3 = createReforgedPack({
  id: "topazio-narrator-alex-v3",
  name: "Alex · narrador oficial V3",
  character: "alex",
  voice_id: "pm_alex",
});

export const TOPAZIO_NARRATOR_PACKS_V3 = Object.freeze({
  dora: DORA_NARRATOR_PACK_V3,
  alex: ALEX_NARRATOR_PACK_V3,
});
