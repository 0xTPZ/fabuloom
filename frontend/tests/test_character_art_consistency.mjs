import assert from "node:assert/strict";
import { existsSync, readFileSync, statSync } from "node:fs";
import test from "node:test";
import {
  ALEX_NARRATOR_PACK_CARTOON_V1,
  DORA_NARRATOR_PACK_CARTOON_V1,
  TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1,
  TOPAZIO_NARRATOR_CARTOON_FRAME_PROFILES,
  TOPAZIO_NARRATOR_MOUTH_ANCHOR_CONTRACT_V1,
  TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS,
  validateCartoonFrameProfile,
} from "../src/topazio-narrator-packs-cartoon-v1.mjs";

const root = new URL("../", import.meta.url);
const local = (asset) => new URL(asset, root).pathname.replace(/^\/+/, "").replaceAll("/", "\\");

test("cartoon narrator packs preserve distinct voices and the shared contract", () => {
  assert.equal(TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1.format, "fabuloom.narrator-cartoon/0.1");
  assert.equal(TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1.source_size[0], 1254);
  assert.equal(DORA_NARRATOR_PACK_CARTOON_V1.voice_id, "pf_dora");
  assert.equal(ALEX_NARRATOR_PACK_CARTOON_V1.voice_id, "pm_alex");
  assert.equal(DORA_NARRATOR_PACK_CARTOON_V1.language, "pt-BR");
  assert.equal(ALEX_NARRATOR_PACK_CARTOON_V1.language, "pt-BR");
  assert.notEqual(DORA_NARRATOR_PACK_CARTOON_V1.layers[0].asset, ALEX_NARRATOR_PACK_CARTOON_V1.layers[0].asset);
});

test("cartoon packs use one identity base and compact explicit mouth states", () => {
  for (const pack of [DORA_NARRATOR_PACK_CARTOON_V1, ALEX_NARRATOR_PACK_CARTOON_V1]) {
    assert.deepEqual(pack.layers.map((layer) => layer.id), ["head", "eyelids", "mouth"]);
    assert.deepEqual(Object.keys(pack.facial_states.mouth), ["closed", "slight", "moderate", "open", "smile"]);
    assert.deepEqual(pack.layers[0].source_size, [1254, 1254]);
    assert.equal(pack.layers[1].parent, "head");
    assert.equal(pack.layers[2].parent, "head");
    assert.equal(pack.layers[2].mouth_motion, "subtle");
    for (const asset of [pack.layers[0].asset, pack.layers[1].asset, ...Object.values(pack.facial_states.mouth)]) {
      const path = local(asset);
      assert.ok(existsSync(path), `missing ${asset}`);
      assert.ok(statSync(path).size > 100, `empty ${asset}`);
    }
    for (const state of Object.values(pack.facial_states.mouth)) {
      const svg = readFileSync(local(state), "utf8");
      assert.match(svg, /viewBox="0 0 1254 1254"/);
      assert.doesNotMatch(svg, /<rect[^>]+width="1254"/);
      assert.match(svg, /stroke=/);
    }
    assert.equal(pack.mouth_polish_status, "v1.1-experimental-awaiting-art-approval");
    assert.ok(existsSync(local(`assets/characters/topazio-narrators-cartoon-v1/${pack.character}/mouth-closed.svg`)), "previous mouth state must remain preserved");
    assert.match(pack.facial_states.mouth.closed, /mouth-polish-closed\.svg$/);
    assert.match(pack.facial_states.mouth.open, /mouth-polish-open\.svg$/);
  }
});

test("cartoon framing profiles preserve square assets and keep facial states in the head frame", () => {
  for (const [character, pack] of [["dora", DORA_NARRATOR_PACK_CARTOON_V1], ["alex", ALEX_NARRATOR_PACK_CARTOON_V1]]) {
    const profile = TOPAZIO_NARRATOR_CARTOON_FRAME_PROFILES[character];
    assert.deepEqual(pack.framing.base_size, profile.base_size);
    assert.deepEqual(pack.framing.base_position, profile.base_position);
    assert.equal(pack.framing.asset_aspect_preserved, true);
    assert.ok(Math.abs(profile.base_size[0] * (1080 / 1920) - profile.base_size[1]) < 1e-9);
    const head = pack.layers.find((layer) => layer.id === "head");
    const mouth = pack.layers.find((layer) => layer.id === "mouth");
    const eyelids = pack.layers.find((layer) => layer.id === "eyelids");
    assert.deepEqual(head.size, profile.base_size);
    assert.deepEqual(head.position, profile.base_position);
    assert.equal(mouth.parent, "head");
    assert.deepEqual(mouth.anchor, profile.mouth_anchor);
    assert.deepEqual(mouth.position, profile.mouth_position.map((value, index) => value + profile.mouth_offset[index]));
    assert.deepEqual(mouth.size, profile.mouth_scale);
    assert.deepEqual(eyelids.position, profile.eyelids_position);
    assert.deepEqual(eyelids.size, profile.eyelids_scale);
  }
  assert.throws(() => validateCartoonFrameProfile({
    base_size: [1.2, 0.3], base_position: [0.5, 0.2], mouth_position: [0.5, 0.5], mouth_scale: [1, 1], eyelids_position: [0.5, 0.5], eyelids_scale: [1, 1],
  }), /cartoon base_size/);
});

test("mouth anchor calibration is versioned and character-specific", () => {
  assert.equal(TOPAZIO_NARRATOR_CARTOON_CONTRACT_V1.mouth_anchor_contract, TOPAZIO_NARRATOR_MOUTH_ANCHOR_CONTRACT_V1);
  for (const [character, pack] of [["dora", DORA_NARRATOR_PACK_CARTOON_V1], ["alex", ALEX_NARRATOR_PACK_CARTOON_V1]]) {
    const calibration = TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS[character];
    const profile = TOPAZIO_NARRATOR_CARTOON_FRAME_PROFILES[character];
    assert.deepEqual(pack.framing.mouth_anchor, calibration.mouth_anchor);
    assert.deepEqual(pack.framing.mouth_offset, calibration.mouth_offset);
    assert.deepEqual(pack.framing.mouth_landmarks, calibration.landmarks);
    assert.deepEqual(pack.face_reference.landmarks, calibration.landmarks);
    assert.deepEqual(pack.layers.find((layer) => layer.id === "mouth").position, [0.5, 0.5 + calibration.mouth_offset[1]]);
    assert.ok(calibration.landmarks.mouth_center[1] > calibration.landmarks.nose_center[1]);
    assert.ok(calibration.landmarks.mouth_center[1] < calibration.landmarks.chin_upper_limit[1]);
    assert.equal(profile.mouth_scale[0], 1);
    assert.equal(profile.mouth_scale[1], 1);
  }
  assert.notDeepEqual(
    TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS.dora.mouth_offset,
    TOPAZIO_NARRATOR_MOUTH_CALIBRATIONS.alex.mouth_offset,
  );
});
