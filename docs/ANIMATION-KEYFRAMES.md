# Animation keyframes V0.1

`frontend/src/animation-keyframes.mjs` defines the provider- and
character-independent numeric clip format `fabuloom.animation-keyframes/0.1`.

Each clip contains an identifier, a positive integer duration, an ordered list
of keyframes beginning at `0 ms`, and numeric channel deltas. Sampling clamps to
the clip duration and uses the configured easing curve between adjacent
keyframes. The result depends only on the requested time; it does not depend on
previous frames, playback order or a browser clock.

Supported curves are `linear`, `smoothstep`, `ease-in`, `ease-out` and
`ease-in-out`. `blendAnimationChannels` and `composeAnimationChannels` combine
compatible numeric overlays additively. Character adapters remain responsible
for channel limits and for mapping channels to their own hierarchy.

## Santa V5 example

`SANTA_V5_WAVE_HELLO_CLIP` is the first consumer. It coordinates a normalized
right-hand target, IK weight, wrist oscillation and head motion through
anticipation, elevation, three small hand reversals and a gradual return. It
is selected with:

```js
rig.setAnimation("WAVE_HELLO");
const pose = rig.poseAt(2120, false);
```

The clip is additive over the base rig, so blinking and RMS mouth animation
remain available. During WAVE_HELLO, the calibrated torso scale is held at its
neutral value so the target remains deterministic. `SantaV5Rig` first solves a
provider-independent two-bone IK request and then applies a small deterministic
forward-model refinement for the pack's non-uniform painted-layer scales. This
keeps the real rendered hand pivot, rather than only the analytic angles,
within the measured target error. No mesh deformation or physics is used.

The DEV page `/santa-v5-calibration.html` exposes the clip with play, pause,
seek, keyframe inspection, landmark and pivot overlays. The five-pose gallery
and the 5-second technical capture use the same `SantaV5Rig` and
`LayeredCharacterRenderer`; the wave expression swaps only the right-hand
asset for the palm-facing `hand-right-wave.png` variant and preserves the
original `hand-right.png` asset.
