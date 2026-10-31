/**
 * Mission 023.3 facial recovery packs.
 *
 * The V4 head and eyelid PNGs remain preserved. Only the unreliable generated
 * mouth plates are replaced by explicit same-canvas vector states. This keeps
 * state selection deterministic and makes a missing mouth asset observable in
 * tests instead of silently erasing the lower face.
 */

import { ANIMATION_READY_PROFILE, CHARACTER_FORMAT, validateCharacterPack } from "./character-pack.mjs";

export const TOPAZIO_NARRATOR_FACIAL_RECOVERY_CONTRACT = Object.freeze({
  format: "fabuloom.narrator-facial-recovery/0.1",
  source_size: Object.freeze([1145, 1374]),
  orientation: "frontal-bust",
  strategy: "same-canvas-explicit-vector-mouth-states",
  base_policy: "preserve-v4-head-and-use-closed-state-as-mouth-base",
  expression_states: Object.freeze(["closed", "slight", "moderate", "open", "smile", "blink"]),
  timing_source: "measured_wav_segments",
  mouth_source: "pcm16_rms_envelope",
  word_phoneme_viseme_timing: "unavailable",
  quality_gate: "AWAITING_ART_APPROVAL",
});

const ROOT = "assets/characters/topazio-narrators-recovery-v1";
const V4_ROOT = "assets/characters/topazio-narrators-v4";
const SOURCE_SIZE = Object.freeze([...TOPAZIO_NARRATOR_FACIAL_RECOVERY_CONTRACT.source_size]);
const BASE_SIZE = Object.freeze([0.82, 0.553]);
const BASE_POSITION = Object.freeze([0.5, 0.34]);

function point(value) { return Object.freeze([...value]); }
function mouthAsset(character, state) { return `${ROOT}/${character}/mouth-${state}.svg`; }
function baseAsset(character) { return `${V4_ROOT}/${character}/head-clean.png`; }
function eyelidAsset(character) { return `${V4_ROOT}/${character}/eyelids-closed-v4.png`; }

function createPack({ id, name, character, voice_id, mouthY }) {
  const states = Object.freeze({
    closed: mouthAsset(character, "closed"),
    slight: mouthAsset(character, "slight"),
    moderate: mouthAsset(character, "moderate"),
    open: mouthAsset(character, "open"),
    smile: mouthAsset(character, "smile"),
  });
  const pack = {
    format: CHARACTER_FORMAT,
    rig_profile: ANIMATION_READY_PROFILE,
    id,
    name,
    character,
    voice_id,
    language: "pt-BR",
    art_status: "facial-system-recovery-v1-experimental-awaiting-art-approval",
    art_notes: "V4 head identity preserved; photorealistic mouth plates replaced by explicit same-canvas vector states. Facial approval remains pending.",
    visual_contract: TOPAZIO_NARRATOR_FACIAL_RECOVERY_CONTRACT.format,
    face_reference: Object.freeze({
      source_size: point(SOURCE_SIZE),
      head_pivot: point([0.5, 0.5]),
      mouth_center: point([0.5, mouthY]),
      mouth_scale: point([1, 1]),
    }),
    facial_states: Object.freeze({ mouth: states }),
    layers: [
      { id: "head", role: "head", asset: baseAsset(character), parent: null, anchor: point([0.5, 0.5]), position: point(BASE_POSITION), size: point(BASE_SIZE), source_size: point(SOURCE_SIZE), z: 0 },
      { id: "eyelids", role: "eyelids", asset: eyelidAsset(character), parent: "head", anchor: point([0.5, 0.5]), position: point(character === "dora" ? [0.5, 0.30] : [0.5, 0.28]), size: point(character === "dora" ? [0.55, 0.55] : [0.45, 0.45]), source_size: point(SOURCE_SIZE), z: 1 },
      { id: "mouth", role: "mouth", asset: states.closed, parent: "head", anchor: point([0.5, 0.5]), position: point([0.5, 0.5]), size: point([1, 1]), source_size: point(SOURCE_SIZE), mouth_motion: "subtle", z: 2 },
    ],
    expressions: [{ id: "neutral", overrides: {} }, { id: "smile", overrides: { mouth: states.smile } }],
    bindings: { head_rotation: "head", eye_open: "eyelids", mouth_open: "mouth", breathing: "head", hair_sway: "head" },
  };
  return Object.freeze(validateCharacterPack(pack));
}

export const DORA_NARRATOR_PACK_RECOVERY_V1 = createPack({ id: "topazio-narrator-dora-facial-recovery-v1", name: "Dora · recuperação facial 023.3", character: "dora", voice_id: "pf_dora", mouthY: 0.32 });
export const ALEX_NARRATOR_PACK_RECOVERY_V1 = createPack({ id: "topazio-narrator-alex-facial-recovery-v1", name: "Alex · recuperação facial 023.3", character: "alex", voice_id: "pm_alex", mouthY: 0.34 });

export const TOPAZIO_NARRATOR_PACKS_RECOVERY_V1 = Object.freeze({
  dora: DORA_NARRATOR_PACK_RECOVERY_V1,
  alex: ALEX_NARRATOR_PACK_RECOVERY_V1,
});
