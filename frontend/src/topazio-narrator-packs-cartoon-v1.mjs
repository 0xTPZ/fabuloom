/**
 * Mission 023.4/023.4.2: original cartoon facial bases and polished mouth
 * states for Dora and Alex.
 *
 * Each pack uses one generated mouthless identity canvas plus compact,
 * same-canvas mouth/eyelid states.  The state art stays small and follows the
 * face geometry instead of painting a second lower-face plate over it.
 */

import { ANIMATION_READY_PROFILE, CHARACTER_FORMAT, validateCharacterPack } from "./character-pack.mjs";

export const TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1 = Object.freeze({
  format: "fabuloom.narrator-cartoon/0.1",
  mouth_anchor_contract: "fabuloom.narrator-mouth-anchor/0.1",
  source_size: Object.freeze([1254, 1254]),
  orientation: "frontal-bust",
  base_composition: "single-original-mouthless-cartoon-identity-canvas",
  mouth_strategy: "compact-same-canvas-painted-states",
  mouth_polish: "small-soft-outline-progressive-states-v1",
  expression_states: Object.freeze(["closed", "slight", "moderate", "open", "blink"]),
  timing_source: "measured_wav_segments",
  mouth_source: "pcm16_rms_envelope",
  word_phoneme_viseme_timing: "unavailable",
  quality_gate: "AWAITING_ART_APPROVAL",
});

const ROOT = "assets/characters/topazio-narrators-cartoon-v1";
const SOURCE_SIZE = Object.freeze([...TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1.source_size]);
export const TOPAZIO_NARRATOR_CARTOON_SOURCE_CANVAS = Object.freeze([1080, 1920]);
export const TOPAZIO_NARRATOR_MOUTH_ANCHOR_CONTRACT_V1 = "fabuloom.narrator-mouth-anchor/0.1";

// Head-local calibration landmarks measured against each identity canvas.
// The previous pack used only the geometric canvas centre for both narrators,
// which placed the compact mouth art too close to the nose in the avatar.
export const TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS = Object.freeze({
  dora: Object.freeze({
    mouth_anchor: Object.freeze([0.5, 0.5]),
    mouth_position: Object.freeze([0.5, 0.5]),
    mouth_offset: Object.freeze([0, 0.04]),
    mouth_scale: Object.freeze([1, 1]),
    landmarks: Object.freeze({
      head_center: Object.freeze([627, 627]),
      nose_center: Object.freeze([627, 565]),
      mouth_center: Object.freeze([627, 665]),
      mouth_left: Object.freeze([552, 665]),
      mouth_right: Object.freeze([702, 665]),
      chin_upper_limit: Object.freeze([627, 775]),
    }),
  }),
  alex: Object.freeze({
    mouth_anchor: Object.freeze([0.5, 0.5]),
    mouth_position: Object.freeze([0.5, 0.5]),
    mouth_offset: Object.freeze([0, 0.036]),
    mouth_scale: Object.freeze([1, 1]),
    landmarks: Object.freeze({
      head_center: Object.freeze([627, 627]),
      nose_center: Object.freeze([627, 580]),
      mouth_center: Object.freeze([627, 666]),
      mouth_left: Object.freeze([548, 666]),
      mouth_right: Object.freeze([706, 666]),
      chin_upper_limit: Object.freeze([627, 810]),
    }),
  }),
});

// The narrator source canvas is 1080x1920 while the cartoon head assets are
// square.  A single normalized value for both axes stretched the face
// vertically before it reached the circular crop.  These profiles keep the
// rendered square square and are deliberately pack-local: the shared
// renderer and Santa V5 framing remain unchanged.
export const TOPAZIO_NARRATOR_CARTOON_FRAME_PROFILES = Object.freeze({
  dora: Object.freeze({
    base_size: Object.freeze([0.68, 0.3825]),
    base_position: Object.freeze([0.5, 0.205]),
    mouth_anchor: TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS.dora.mouth_anchor,
    mouth_position: TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS.dora.mouth_position,
    mouth_offset: TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS.dora.mouth_offset,
    mouth_scale: TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS.dora.mouth_scale,
    mouth_landmarks: TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS.dora.landmarks,
    eyelids_position: Object.freeze([0.5, 0.5]),
    eyelids_scale: Object.freeze([1, 1]),
  }),
  alex: Object.freeze({
    base_size: Object.freeze([0.68, 0.3825]),
    base_position: Object.freeze([0.5, 0.205]),
    mouth_anchor: TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS.alex.mouth_anchor,
    mouth_position: TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS.alex.mouth_position,
    mouth_offset: TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS.alex.mouth_offset,
    mouth_scale: TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS.alex.mouth_scale,
    mouth_landmarks: TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS.alex.landmarks,
    eyelids_position: Object.freeze([0.5, 0.5]),
    eyelids_scale: Object.freeze([1, 1]),
  }),
});

function unit(value, label) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 1) {
    throw new TypeError(`${label} must be in [0,1]`);
  }
}

function normalizedPoint(value, label) {
  if (!Array.isArray(value) || value.length !== 2) throw new TypeError(`${label} must be a 2D point`);
  value.forEach((item) => unit(item, label));
  return Object.freeze([...value]);
}

function signedPoint(value, label) {
  if (!Array.isArray(value) || value.length !== 2) throw new TypeError(`${label} must be a 2D offset`);
  value.forEach((item) => {
    if (typeof item !== "number" || !Number.isFinite(item) || item < -0.5 || item > 0.5) {
      throw new TypeError(`${label} must contain finite offsets in [-0.5,0.5]`);
    }
  });
  return Object.freeze([...value]);
}

function pixelPoint(value, label) {
  if (!Array.isArray(value) || value.length !== 2) throw new TypeError(`${label} must be a 2D pixel point`);
  value.forEach((item, index) => {
    if (typeof item !== "number" || !Number.isFinite(item) || item < 0 || item > SOURCE_SIZE[index]) {
      throw new RangeError(`${label} is outside source canvas`);
    }
  });
  return Object.freeze([...value]);
}

function mouthLandmarks(value, label) {
  if (!value || typeof value !== "object") throw new TypeError(`${label} must be an object`);
  return Object.freeze(Object.fromEntries([
    ["head_center", pixelPoint(value.head_center, `${label}.head_center`)],
    ["nose_center", pixelPoint(value.nose_center, `${label}.nose_center`)],
    ["mouth_center", pixelPoint(value.mouth_center, `${label}.mouth_center`)],
    ["mouth_left", pixelPoint(value.mouth_left, `${label}.mouth_left`)],
    ["mouth_right", pixelPoint(value.mouth_right, `${label}.mouth_right`)],
    ["chin_upper_limit", pixelPoint(value.chin_upper_limit, `${label}.chin_upper_limit`)],
  ]));
}

function positivePoint(value, label) {
  const result = normalizedPoint(value, label);
  if (result.some((item) => item <= 0)) throw new TypeError(`${label} must be positive`);
  return result;
}

export function validateCartoonFrameProfile(profile) {
  if (!profile || typeof profile !== "object") throw new TypeError("cartoon frame profile must be an object");
  const baseSize = positivePoint(profile.base_size, "cartoon base_size");
  const expectedHeight = baseSize[0] * TOPAZIO_NARRATOR_CARTOON_SOURCE_CANVAS[0] / TOPAZIO_NARRATOR_CARTOON_SOURCE_CANVAS[1];
  if (Math.abs(expectedHeight - baseSize[1]) > 0.005) throw new RangeError("cartoon base_size must preserve the square asset aspect");
  const mouthAnchor = normalizedPoint(profile.mouth_anchor || [0.5, 0.5], "cartoon mouth_anchor");
  const mouthPosition = normalizedPoint(profile.mouth_position, "cartoon mouth_position");
  const mouthOffset = signedPoint(profile.mouth_offset || [0, 0], "cartoon mouth_offset");
  const effectiveMouthPosition = mouthPosition.map((value, index) => value + mouthOffset[index]);
  if (effectiveMouthPosition.some((value) => value < 0 || value > 1)) throw new RangeError("cartoon mouth position plus offset must stay in [0,1]");
  const landmarks = profile.mouth_landmarks === undefined
    ? null
    : mouthLandmarks(profile.mouth_landmarks, "cartoon mouth_landmarks");
  return Object.freeze({
    base_size: baseSize,
    base_position: normalizedPoint(profile.base_position, "cartoon base_position"),
    mouth_anchor: mouthAnchor,
    mouth_position: mouthPosition,
    mouth_offset: mouthOffset,
    mouth_scale: positivePoint(profile.mouth_scale, "cartoon mouth_scale"),
    mouth_landmarks: landmarks,
    eyelids_position: normalizedPoint(profile.eyelids_position, "cartoon eyelids_position"),
    eyelids_scale: positivePoint(profile.eyelids_scale, "cartoon eyelids_scale"),
  });
}

for (const profile of Object.values(TOPAZIO_NARRATOR_CARTOON_FRAME_PROFILES)) validateCartoonFrameProfile(profile);

function point(value) { return Object.freeze([...value]); }
function asset(character, name) { return `${ROOT}/${character}/${name}`; }

function createPack({ id, name, character, voice_id }) {
  const frame = validateCartoonFrameProfile(TOPAZIO_NARRATOR_CARTOON_FRAME_PROFILES[character]);
  const states = Object.freeze({
    closed: asset(character, "mouth-polish-closed.svg"),
    slight: asset(character, "mouth-polish-slight.svg"),
    moderate: asset(character, "mouth-polish-moderate.svg"),
    open: asset(character, "mouth-polish-open.svg"),
    smile: asset(character, "mouth-polish-closed.svg"),
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
    art_notes: "Original cartoon identity canvas with compact polished mouth states; previous mouth assets remain preserved as versioned experimental assets. Approval remains pending.",
    mouth_polish_status: "v1.1-experimental-awaiting-art-approval",
    visual_contract: TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1.format,
    face_reference: Object.freeze({
      source_size: point(SOURCE_SIZE),
      head_pivot: point([0.5, 0.5]),
      mouth_anchor_contract: TOPAZIO_NARRATOR_MOUTH_ANCHOR_CONTRACT_V1,
      mouth_anchor: point(frame.mouth_anchor),
      mouth_position: point(frame.mouth_position),
      mouth_offset: point(frame.mouth_offset),
      mouth_center: point([frame.mouth_landmarks.mouth_center[0] / SOURCE_SIZE[0], frame.mouth_landmarks.mouth_center[1] / SOURCE_SIZE[1]]),
      landmarks: frame.mouth_landmarks,
      mouth_scale: point(frame.mouth_scale),
      mouth_polish: "small-soft-outline-progressive-states-v1",
    }),
    framing: Object.freeze({
      format: "fabuloom.narrator-cartoon-framing/0.1",
      source_canvas: TOPAZIO_NARRATOR_CARTOON_SOURCE_CANVAS,
      asset_aspect_preserved: true,
      base_size: frame.base_size,
      base_position: frame.base_position,
      head_pivot: point([0.5, 0.5]),
      mouth_anchor_contract: TOPAZIO_NARRATOR_MOUTH_ANCHOR_CONTRACT_V1,
      mouth_anchor: frame.mouth_anchor,
      mouth_position: frame.mouth_position,
      mouth_offset: frame.mouth_offset,
      mouth_scale: frame.mouth_scale,
      mouth_landmarks: frame.mouth_landmarks,
      eyelids_position: frame.eyelids_position,
      eyelids_scale: frame.eyelids_scale,
      visible_frame: "NARRATOR_FACE_CROP",
    }),
    facial_states: Object.freeze({ mouth: states }),
    layers: [
      {
        id: "head",
        role: "head",
        asset: base,
        parent: null,
        anchor: point([0.5, 0.5]),
        position: frame.base_position,
        size: frame.base_size,
        source_size: point(SOURCE_SIZE),
        z: 0,
      },
      {
        id: "eyelids",
        role: "eyelids",
        asset: eyelids,
        parent: "head",
        anchor: point([0.5, 0.5]),
        position: frame.eyelids_position,
        size: frame.eyelids_scale,
        source_size: point(SOURCE_SIZE),
        z: 1,
      },
      {
        id: "mouth",
        role: "mouth",
        asset: states.closed,
        parent: "head",
        anchor: point(frame.mouth_anchor),
        position: point(frame.mouth_position.map((value, index) => value + frame.mouth_offset[index])),
        size: frame.mouth_scale,
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
