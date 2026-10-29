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

`SANTA_V5_WAVE_HELLO_CLIP` is the first consumer. It coordinates the right
upper arm, forearm, hand, head and torso through anticipation, elevation,
three small hand reversals and a gradual return. It is selected with:

```js
rig.setAnimation("WAVE_HELLO");
const pose = rig.poseAt(2120, false);
```

The clip is additive over the base rig, so breathing, blinking and RMS mouth
animation remain available. A named clip temporarily owns the body channels
that it animates, preventing the long scene choreography from fighting the
gesture. No IK or mesh deformation is introduced in this version.

The DEV page `/santa-v5-calibration.html` exposes the clip with play, pause,
seek, keyframe inspection, landmark and pivot overlays. The five-pose gallery
and the 5-second technical capture use the same `SantaV5Rig` and
`LayeredCharacterRenderer`.
