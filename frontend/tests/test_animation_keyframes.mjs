import assert from "node:assert/strict";
import { test } from "node:test";

import {
  FABULOOM_KEYFRAME_FORMAT,
  blendAnimationChannels,
  composeAnimationChannels,
  sampleAnimationClip,
  validateAnimationClip,
} from "../src/animation-keyframes.mjs";

const clip = {
  format: FABULOOM_KEYFRAME_FORMAT,
  id: "WAVE_HELLO",
  durationMs: 1000,
  easing: "smoothstep",
  keyframes: [
    { timeMs: 0, channels: { arm: 0, hand: 0 } },
    { timeMs: 500, easing: "linear", channels: { arm: 1, hand: -1 } },
    { timeMs: 1000, easing: "ease-in-out", channels: { arm: 0, hand: 0 } },
  ],
};

test("keyframe clips validate duration, order and finite numeric channels", () => {
  assert.equal(validateAnimationClip(clip), clip);
  assert.throws(() => validateAnimationClip({ ...clip, durationMs: 0 }), /positive integer/);
  assert.throws(() => validateAnimationClip({ ...clip, keyframes: [{ timeMs: 10, channels: {} }] }), /start at time 0/);
  assert.throws(() => validateAnimationClip({ ...clip, keyframes: [{ timeMs: 0, channels: { arm: NaN } }] }), /finite number/);
  assert.throws(() => validateAnimationClip({ ...clip, keyframes: [{ timeMs: 0, channels: { arm: true } }] }), /finite number/);
});

test("keyframe sampling is deterministic and clamps outside the clip", () => {
  assert.deepEqual(sampleAnimationClip(clip, -50), { arm: 0, hand: 0 });
  assert.deepEqual(sampleAnimationClip(clip, 1500), { arm: 0, hand: 0 });
  assert.deepEqual(sampleAnimationClip(clip, 250), { arm: 0.5, hand: -0.5 });
  assert.deepEqual(sampleAnimationClip(clip, 250), sampleAnimationClip(clip, 250));
});

test("compatible channels blend additively without temporal state", () => {
  assert.deepEqual(blendAnimationChannels({ arm: 0.2 }, { arm: 0.4, head: -0.1 }, 0.5), { arm: 0.4, head: -0.05 });
  assert.ok(Math.abs(composeAnimationChannels({ arm: 0.2 }, { arm: 0.4 }, { arm: -0.1 }).arm - 0.5) < 1e-12);
  assert.throws(() => blendAnimationChannels({ arm: 0 }, { arm: Infinity }), /finite number/);
});
