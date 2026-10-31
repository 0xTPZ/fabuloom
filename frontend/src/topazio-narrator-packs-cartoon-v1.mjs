/**
 * Mission 023.4: original cartoon facial bases for Dora and Alex.
 *
 * Each pack uses one generated mouthless identity canvas plus compact,
 * same-canvas mouth/eyelid states.  The state art stays small and follows the
 * face geometry instead of painting a second lower-face plate over it.
 */

import { ANIMATION_READY_PROFILE, CHARACTER_FORMAT, validateCharacterPack } from "./character-pack.mjs";

export const TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1 = Object.freeze({
  format: "fabuloom.narrator-cartoon/0.1",
  source_size: Object.freeze([1254, 1254]),
  orientation: "frontal-bust",
  base_composition: "single-original-mouthless-cartoon-identity-canvas",
  mouth_strategy: "compact-same-canvas-painted-states",
  expression_states: Object.freeze(["closed", "slight", "moderate", "open", "blink"]),
  timing_source: "measured_wav_segments",
  mouth_source: "pcm16_rms_envelope",
  word_phoneme_viseme_timing: "unavailable",
  quality_gate: "AWAITING_ART_APPROVAL",
});

const ROOT = "assets/characters/topazio-narrators-cartoon-v1";
const SOURCE_SIZE = Object.freeze([...TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1.source_size]);
const BASE_SIZE = Object.freeze([0.68, 0.68]);
const BASE_POSITION = Object.freeze([0.5, 0.32]);

function point(value) { return Object.freeze([...value]); }
function asset(character, name) { return `${ROOT}/${character}/${name}`; }

function createPack({ id, name, character, voice_id }) {
  const states = Object.freeze({
    closed: asset(character, "mouth-closed.svg"),
    slight: asset(character, "mouth-slight.svg"),
    moderate: asset(character, "mouth-moderate.svg"),
    open: asset(character, "mouth-open.svg"),
    smile: asset(character, "mouth-closed.svg"),
  });
  const base = asset(character, "head-clean.png");
  const eyelids = asset(character, "eyelids-closed.svg");
  const pack = {
    format: CHARACTER_FORMAT,
    rig_profile: ANIMATION_READY_PROFILE,
    id,
    name,
    character,
    voice_id,
    language: "pt-BR",
    art_status: "character-art-consistency-v1-experimental-awaiting-art-approval",
    art_notes: "Original cartoon identity canvas with compact mouth states; generated bases are preserved as versioned experimental assets. Approval remains pending.",
    visual_contract: TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1.format,
    face_reference: Object.freeze({
      source_size: point(SOURCE_SIZE),
      head_pivot: point([0.5, 0.5]),
      mouth_center: point([0.5, character === "dora" ? 0.52 : 0.53]),
      mouth_scale: point([1, 1]),
    }),
    facial_states: Object.freeze({ mouth: states }),
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
        position: point([0.5, 0.5]),
        size: point([1, 1]),
        source_size: point(SOURCE_SIZE),
        z: 1,
      },
      {
        id: "mouth",
        role: "mouth",
        asset: states.closed,
        parent: "head",
        anchor: point([0.5, 0.5]),
        position: point([0.5, 0.5]),
        size: point([0.9, 0.9]),
        source_size: point(SOURCE_SIZE),
        mouth_motion: "subtle",
        z: 2,
      },
    ],
    expressions: [{ id: "neutral", overrides: {} }, { id: "smile", overrides: { mouth: states.smile } }],
    bindings: { head_rotation: "head", eye_open: "eyelids", mouth_open: "mouth", breathing: "head", hair_sway: "head" },
  };
  return Object.freeze(validateCharacterPack(pack));
}

export const DORA_NARRATOR_PACK_CARTOON_V1 = createPack({
  id: "topazio-narrator-dora-cartoon-v1",
  name: "Dora · cartoon facial V1",
  character: "dora",
  voice_id: "pf_dora",
});

export const ALEX_NARRATOR_PACK_CARTOON_V1 = createPack({
  id: "topazio-narrator-alex-cartoon-v1",
  name: "Alex · cartoon facial V1",
  character: "alex",
  voice_id: "pm_alex",
});

export const TOPAZIO_NARRATOR_PACKS_CARTOON_V1 = Object.freeze({
  dora: DORA_NARRATOR_PACK_CARTOON_V1,
  alex: ALEX_NARRATOR_PACK_CARTOON_V1,
});
