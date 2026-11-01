/**
 * Topazioverse official narrator art reforge, V4.
 *
 * Dora and Alex V4 are authored as frontal stylized storybook busts.  Their
 * mouth and eyelid plates use the same 1145x1374 source canvas, but explicit
 * local transforms keep the generated facial plates aligned with the clean
 * head base.  Time, RMS and expression selection remain owned by the shared
 * NarratorAvatarRenderer.
 */

import { ANIMATION_READY_PROFILE, CHARACTER_FORMAT, validateCharacterPack } from "./character-pack.mjs";

export const TOPAZIO_NARRATOR_VISUAL_CONTRACT_V4 = Object.freeze({
  format: "fabuloom.narrator-visual-contract/0.1",
  source_size: Object.freeze([1145, 1374]),
  orientation: "frontal-bust",
  base_composition: "mouthless-head-with-transparent-expression-plates",
  avatar_frame: "circular-gold-blue",
  safe_area: Object.freeze({ left: 0.06, top: 0.035, right: 0.94, bottom: 0.965 }),
  face_scale: "shared-narrator-crop-v1",
  expression_states: Object.freeze(["neutral", "smile", "mouth_closed", "mouth_slight", "mouth_open", "blink"]),
  timing_source: "measured_wav_segments",
  mouth_source: "pcm16_rms_envelope",
  word_phoneme_viseme_timing: "unavailable",
  quality_gate: "AWAITING_ART_APPROVAL",
});

const ROOT = "assets/characters/topazio-narrators-v4";
const SOURCE_SIZE = Object.freeze([...TOPAZIO_NARRATOR_VISUAL_CONTRACT_V4.source_size]);
const BASE_SIZE = Object.freeze([0.82, 0.553]);
const BASE_POSITION = Object.freeze([0.5, 0.34]);

function asset(character, name) {
  return `${ROOT}/${character}/${name}`;
}

function point(value) { return Object.freeze([...value]); }

function createReforgedPack({ id, name, character, voice_id, mouthPosition, eyelidPosition, mouthScale, eyelidScale }) {
  const base = asset(character, "head-clean.png");
  const eyelids = asset(character, "eyelids-closed-v4.png");
  const mouthStates = Object.freeze({
    closed: asset(character, "mouth-closed-v4.png"),
    slight: asset(character, "mouth-slight-v4.png"),
    moderate: asset(character, "mouth-open-v4.png"),
    open: asset(character, "mouth-open-v4.png"),
    smile: asset(character, "mouth-smile-v4.png"),
  });
  const pack = {
    format: CHARACTER_FORMAT,
    rig_profile: ANIMATION_READY_PROFILE,
    id,
    name,
    character,
    voice_id,
    language: "pt-BR",
    art_status: "art-reforge-v4-experimental-awaiting-art-approval",
    art_notes: "Frontal stylized storybook bust with a mouthless base and aligned V4 facial plates. Santa V5 is the style reference only; physical identity remains distinct.",
    visual_contract: TOPAZIO_NARRATOR_VISUAL_CONTRACT_V4.format,
    face_reference: Object.freeze({
      source_size: point(SOURCE_SIZE),
      head_pivot: point([0.5, 0.5]),
      mouth_center: point([0.5, mouthPosition[1]]),
      eyelid_center: point([0.5, eyelidPosition[1]]),
      mouth_scale: point(mouthScale),
      eyelid_scale: point(eyelidScale),
    }),
    facial_states: Object.freeze({ mouth: mouthStates }),
    layers: [
      {
        id: "head",
        role: "head",
        asset: base,
        parent: null,
        anchor: point([0.5, 0.5]),
        position: point(BASE_POSITION),
        size: point(BASE_SIZE),
        source_size: point(SOURCE_SIZE),
        z: 0,
      },
      {
        id: "eyelids",
        role: "eyelids",
        asset: eyelids,
        parent: "head",
        anchor: point([0.5, 0.5]),
        position: point(eyelidPosition),
        size: point(eyelidScale),
        source_size: point(SOURCE_SIZE),
        z: 1,
      },
      {
        id: "mouth",
        role: "mouth",
        asset: mouthStates.closed,
        parent: "head",
        anchor: point([0.5, 0.5]),
        position: point(mouthPosition),
        size: point(mouthScale),
        source_size: point(SOURCE_SIZE),
        mouth_motion: "subtle",
        z: 2,
      },
    ],
    expressions: [
      { id: "neutral", overrides: {} },
      { id: "smile", overrides: { mouth: mouthStates.smile } },
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

export const DORA_NARRATOR_PACK_V4 = createReforgedPack({
  id: "topazio-narrator-dora-v4",
  name: "Dora · narradora oficial V4",
  character: "dora",
  voice_id: "pf_dora",
  mouthPosition: [0.5, 0.36],
  eyelidPosition: [0.5, 0.30],
  mouthScale: [0.38, 0.38],
  eyelidScale: [0.55, 0.55],
});

export const ALEX_NARRATOR_PACK_V4 = createReforgedPack({
  id: "topazio-narrator-alex-v4",
  name: "Alex · narrador oficial V4",
  character: "alex",
  voice_id: "pm_alex",
  mouthPosition: [0.5, 0.37],
  eyelidPosition: [0.5, 0.28],
  mouthScale: [0.5, 0.5],
  eyelidScale: [0.45, 0.45],
});

export const TOPAZIO_NARRATOR_PACKS_V4 = Object.freeze({
  dora: DORA_NARRATOR_PACK_V4,
  alex: ALEX_NARRATOR_PACK_V4,
});
