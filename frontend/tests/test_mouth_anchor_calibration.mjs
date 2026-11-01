import assert from "node:assert/strict";
import test from "node:test";
import { buildLayerDrawPlan } from "../src/layered-character.ts";
import {
  ALEX_NARRATOR_PACK_CARTOON_V1,
  DORA_NARRATOR_PACK_CARTOON_V1,
  TOPAZIO_NARRATOR_MOUTH_ANCHOR_CONTRACT_V1,
  validateCartoonFrameProfile,
} from "../src/topazio-narrator-packs-cartoon-v1.mjs";

const pose = {
  breathing: 0.5,
  head_rotation: 0,
  eye_open: 1,
  mouth_open: 0,
  hair_sway: 0,
  brow_raise: 0,
  left_arm: 0,
  right_arm: 0,
};

function byId(plan, id) { return plan.find((entry) => entry.layer.id === id); }

test("mouth anchor plans are deterministic, head-local and character-specific", () => {
  for (const pack of [DORA_NARRATOR_PACK_CARTOON_V1, ALEX_NARRATOR_PACK_CARTOON_V1]) {
    assert.equal(pack.framing.mouth_anchor_contract, TOPAZIO_NARRATOR_MOUTH_ANCHOR_CONTRACT_V1);
    const first = buildLayerDrawPlan(pack, 1080, 1920, pose);
    const second = buildLayerDrawPlan(pack, 1080, 1920, pose);
    assert.deepEqual(first, second);
    const head = byId(first, "head");
    const mouth = byId(first, "mouth");
    assert.equal(mouth.layer.parent, "head");
    assert.deepEqual(mouth.layer.anchor, pack.framing.mouth_anchor);
    assert.deepEqual(mouth.layer.position, [pack.framing.mouth_position[0] + pack.framing.mouth_offset[0], pack.framing.mouth_position[1] + pack.framing.mouth_offset[1]]);
    assert.deepEqual(head.matrix, byId(second, "head").matrix);
    assert.ok(mouth.matrix.f > head.matrix.f);
  }
  const doraMouth = byId(buildLayerDrawPlan(DORA_NARRATOR_PACK_CARTOON_V1, 1080, 1920, pose), "mouth");
  const alexMouth = byId(buildLayerDrawPlan(ALEX_NARRATOR_PACK_CARTOON_V1, 1080, 1920, pose), "mouth");
  assert.notEqual(doraMouth.matrix.f, alexMouth.matrix.f);
});

test("calibrated landmarks remain ordered and all four RMS states stay declared", () => {
  for (const pack of [DORA_NARRATOR_PACK_CARTOON_V1, ALEX_NARRATOR_PACK_CARTOON_V1]) {
    const landmarks = pack.face_reference.landmarks;
    assert.ok(landmarks.nose_center[1] < landmarks.mouth_center[1]);
    assert.ok(landmarks.mouth_center[1] < landmarks.chin_upper_limit[1]);
    assert.ok(landmarks.mouth_left[0] < landmarks.mouth_center[0]);
    assert.ok(landmarks.mouth_center[0] < landmarks.mouth_right[0]);
    assert.deepEqual(Object.keys(pack.facial_states.mouth), ["closed", "slight", "moderate", "open", "smile"]);
  }
});

test("legacy cartoon framing profiles remain valid without optional anchor metadata", () => {
  assert.doesNotThrow(() => validateCartoonFrameProfile({
    base_size: [0.68, 0.3825],
    base_position: [0.5, 0.205],
    mouth_position: [0.5, 0.5],
    mouth_scale: [1, 1],
    eyelids_position: [0.5, 0.5],
    eyelids_scale: [1, 1],
  }));
});
