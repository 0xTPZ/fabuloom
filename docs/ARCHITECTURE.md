# Architecture

## Boundary

Fabuloom Studio is a new project. TopazioReader and Card Game Studio may inform requirements, but they are not runtime dependencies and are not modified by this project.

## Proposed layers

```text
Project / Script
        |
        v
  Scene Director ---- Character Engine
        |                    |
        v                    v
  Audio Timeline <------ TTS Providers
        |
        v
  Video Compositor
        |
        v
  Export Adapters
```

## V0.1 implementation

The first implementation lives in `src/fabuloom_core` and is intentionally independent of all external engines. Domain models use stable IDs and `format_version: "0.1.0"`. JSON serialization is explicit and rejects unsupported minor versions.

`TTSProvider` is a provider-neutral protocol. `SimulatedTTSProvider` remains the dependency-free provider for tests. The optional `KokoroTTSProvider` is lazy, loads one PT-BR pipeline on demand, reuses it, writes measured WAV output, and releases it through `close()`.

Narration preparation is separated from the provider. `segment_text` creates
stable ordered source segments from paragraphs and sentence punctuation, with
explicit pause policy. `synthesize_narration` turns each segment into a WAV
and composes the existing `AudioManifest`; timeline durations come from the
measured files, while word/phoneme/viseme timestamps remain empty when the
provider does not supply them.

### Character stage V0.3

The local `frontend` stage separates `AudioTimelinePlayer`, `PlaybackClock`,
RMS analysis, `CharacterRig`, Canvas rendering, manifest loading, and UI
controls. The rig consumes a normalized speech amplitude signal and does not
import Kokoro or Animus. Pauses produce zero speech amplitude while breathing,
blinking, and subtle head motion continue. The amplitude path is explicitly a
visual approximation, not phonetic alignment.

The synchronization layer stores integer milliseconds. Audio segments cannot overlap on the same track. Animation overlap is policy-based: gestures, expressions, and visemes may overlap; structural events such as page changes and camera cuts may not overlap on the same track.

### Layered character engine 007A.2

`LayeredCharacterRenderer` is an optional Canvas backend for the data-only
`fabuloom.character/0.1` pack contract. It resolves parent transforms in the
parent asset's intrinsic frame, applies normalized pivots and sizes, sorts
layers by `z`, and uses same-origin local image resources only. Expressions
replace a layer asset without changing the pack identity.

`LayeredCharacterRig` consumes the same provider-independent pose boundary as
the geometric rig. Head rotation, hair sway, blinking, brow motion, mouth
openness, breathing, arm gestures, and expression selection are mapped to
pack bindings. The head is a child of the torso but is the rotation target;
therefore facial descendants move with the head without rotating the torso.
The existing geometric renderer remains the default and is selectable at
runtime; audio clocking, Kokoro, and the manifest are not coupled to either
character backend.

Ari's refined pack contains separate original torso/head bitmaps and explicit
anatomical nodes for hair, face, arms, hands and accessories. The arm sleeve
assets currently use controlled crops from the original costume source and
the smaller expressive accents are vector layers. This is suitable for the
runtime proof and future migration, but the remaining painted layer authoring
is deliberately tracked as an art-quality follow-up.

### Official narrator trio 009

The current Character Stage demonstrator defaults to three small, validated
layered packs: Dora (`pf_dora`), Santa (`pm_santa`), and Alex (`pm_alex`). Each
uses a portrait root plus independent eyes, eyelids, brows, and mouth layers,
with the same provider-independent rig channels for head motion, breathing,
blinking, brow motion, expression, and RMS mouth response. The portraits are
original generated assets with a shared navy, pale-blue, and gold narrator
uniform language; no private Topazioverse artwork or model assets are included.

The voice IDs are metadata only: the character engine does not call Kokoro and
remains usable with any narration manifest. Ari and Lia remain selectable
technical references. A full character editor and external pack importer are
explicitly deferred to a later mission.

Mission 009.1 adds a local narration catalog in
`frontend/src/topazio-narrations.mjs`. Each official narrator maps to one
pre-generated manifest and its expected Kokoro `voice_id`. The stage validates
the loaded manifest against that expected voice, displays the actual loaded
voice, disposes the prior `AudioTimelinePlayer` before switching, and reuses
existing WAVs instead of synthesizing during selection. Playback controls,
seek, timeline rendering and RMS analysis remain shared.

### Animation-ready narrator pipeline 010.1

The original Mission 010 export is intentionally diagnosed as a portrait
composition: its Python path places Dora's full image on the stage and adds
small audio-reactive overlays. That path proves MP4 delivery but cannot move
the head, torso, arms, hands, hair and facial parts independently.

Mission 010.1 keeps the existing V1 packs for compatibility and makes the
`animation-ready/0.1` V2 packs the default official narrator assets. Their
parent graph is consumed by the same `LayeredCharacterRig` and
`LayeredCharacterRenderer` used by the interactive Stage. The V2 pack has
separate anatomical layers and explicit pivots; the torso is the breathing
root, the head is the rotation target, and facial descendants inherit only the
head transform.

`frameSchedule`, `renderFrame`, and `captureLayeredFrames` are the first
export boundary. They render deterministic Canvas frames from the real rig,
with the same time, RMS amplitude, expression and playing state as the Stage,
and stream one PNG blob at a time through a callback. A future local bridge can
forward those frames to FFmpeg and mux the measured WAV without retaining a
complete video in browser memory. The current portrait exporter remains
unchanged until that bridge is connected and validated.

### First video pipeline 010

`examples/first_video_demo.py` is the first deterministic text-to-MP4 path. It
uses the provider-neutral narration service to create or reuse a measured
Kokoro manifest, composes the ordered WAV segments with their real millisecond
positions, derives a per-frame RMS envelope for the visual mouth response, and
passes the resulting layers to FFmpeg. The export contains the original Dora
portrait, a reusable background, segment-level SRT captions, and a short
identity outro. Word, phoneme, and viseme timestamps remain unavailable and are
never synthesized. Generated audio, manifests, sprites, previews, and MP4s are
workspace artifacts and remain outside Git.

### Rig-faithful video capture 010.2

`examples/character_engine_video_demo.py` is the first exporter that uses the
real layered engine end to end. A loopback-only `capture-character.html` page
loads the Santa V2 pack and the same `LayeredCharacterRig` /
`LayeredCharacterRenderer` used by Character Stage. `renderBackground: false`
clears the Canvas before each frame, so the PNG sequence contains only the
transparent character. The browser computes the mouth signal from the PCM-16
WAV RMS envelope and posts one frame at a time to the local capture endpoint.

The Python compositor validates the contiguous frame sequence, then FFmpeg
overlays it on the vertical background and draws per-segment captions from
the measured `start_ms` / `end_ms` boundaries. No second animation
implementation exists in FFmpeg. The rig's `poseAt()` is clock-pure, making
the same pose reproducible after seek or an out-of-order capture request.
Word, phoneme and viseme timing remain unavailable and are not synthesized.

### Santa V3 continuous scene 011

`SantaV3Rig` and `SantaV3SceneRenderer` extend the same deterministic capture
boundary for a full-body character. The rig owns absolute-time pose channels
for the torso, pelvis, head, arms, forearms, hands, legs, blink, brow, mouth
and breathing. A small scene director maps the measured narration duration to
one uninterrupted sequence: walk, sit, reach, drink, return the cup, read and
explain. Chair, table, book and cup are scene primitives; the cup position is
derived from the same scene state as the hand gesture, so FFmpeg only encodes
already-rendered frames and audio.

The browser capture uses an offscreen transparent character canvas composited
onto the scene canvas. This prevents an opaque character background from
leaking into the exported video and keeps Stage/export pose behavior aligned.
The renderer remains independent of Kokoro and can receive another measured
audio envelope or a future phoneme/viseme signal without changing the pack.

### Santa V4 art refinement 011.1

Santa V4 is a pack-level visual refinement, not a second animation engine.
`SantaV4Rig` subclasses the existing deterministic Santa rig and
`SantaV4SceneRenderer` supplies `SANTA_V4_PACK` to the V3 scene renderer through
an explicit pack/title option. This keeps browser playback and offline capture
on one pose implementation while preserving the V3 pack for comparison and
compatibility. The new SVG layers are original and local; the runtime does not
load the generated concept reference.

### Santa V5 rig finalization 012.1

Santa V5 continues the same single-engine rule. `SantaV5Rig` subclasses the
deterministic Santa rig and `SantaV5SceneRenderer` supplies the V5 pack to the
existing scene renderer. The pack is more granular than the V5 art preview:
head, neck, hair, facial overlays, upper/lower limb segments, hands and feet
each have their own parent and pivot. The head is a child of the neck, while
the neck is a child of the torso, so head rotation cannot rotate the torso.

`LayeredCharacterRenderer.getLayerDrawPlan()` exposes the exact resolved
matrices already used for drawing. Scene props use this read-only plan to
anchor the cup to the transformed `right_hand` layer, avoiding a second,
divergent hand trajectory. The fallback remains for older packs without an
explicit hand. Browser Stage and offline capture therefore share the same
rig, asset transforms, RMS mouth signal and deterministic frame schedule.

`frontend/capture-santa-v5.html` is loopback-only through the existing local
server. `examples/santa_v5_video_demo.py` reuses measured audio, captures PNG
frames in the browser, and lets FFmpeg encode the final H.264/AAC file. No
weights or generated media are committed to the public repository.

### Santa V5 calibration boundary

Santa V5 calibration follows the same single-engine boundary. `SantaV5Rig`
performs only asset-specific amplitude limits after the shared V3 scene sampler;
the browser stage, the calibration tool and the offline calibration capture all
consume `LayeredCharacterRenderer`. Diagnostic overlays are development-only
and are not part of exported character frames. FFmpeg receives deterministic
PNG frames only after the browser rig has resolved parent transforms.

Landmark calibration is intentionally downstream of pack validation and
upstream of visual QA. It consumes resolved layer plans but never changes a
source image or invents hidden-joint precision. V5 gait and seated corrections
are deterministic pose-channel adjustments; no physics system or second
renderer was introduced.

### Santa V5 arm IK boundary 012.6

`frontend/src/two-bone-ik.mjs` is independent of Santa, TTS and the browser.
It uses Canvas coordinates (+X right, +Y down, clockwise angles), supports
reach clamping, elbow preference and joint limits, and returns analytic angles,
joint positions and residual error. The Santa adapter consumes the existing
landmarks and pack hierarchy rather than introducing a second skeleton.

Because the painted arm layers use non-uniform X/Y scales, the Santa adapter
also applies a deterministic forward-model refinement to the analytic result.
The refinement models the actual upper-arm and forearm affine scales used by
`LayeredCharacterRenderer`; it is not physics and does not replace the shared
renderer. At full WAVE_HELLO poses the rendered hand pivot is verified against
the requested target, while the clip's `weight` intentionally produces smooth
rest/target blending during approach and return.

The `wave` expression changes only the right-hand asset to the palm-facing
variant. `SantaV5SceneRenderer`, the technical capture and the DEV calibration
page all select the same expression and rig path. The calibration page exposes
the target and elbow preference for diagnostics, including a pointer-drag
override; these controls are development-only and are not a general character
editor.

### Presenter targeting and POINT_AT 012.7

`frontend/src/presentation-targets.mjs` defines the provider- and character-
independent `fabuloom.presentation-target/0.1` boundary. A target can be a
normalized stage point, a stage-pixel point, or the center of a registered
scene object. Resolution is deterministic and never executes target content.

`frontend/src/presenter-targeting.mjs` owns the reusable `POINT_AT` clip and
the planning step that keeps the wrist short of the target by a measured
clearance. The target's actual direction is retained for the pointing finger;
out-of-reach targets are clamped safely and reported as such instead of being
silently treated as precise contact. `SantaV5Rig` selects the calibrated right
or left arm, runs the same two-bone IK and affine forward refinement, and
applies subtle head/torso follow. The painted `point` and `point-left`
expressions are only asset overrides; the animation remains provider-neutral.

The clip is sampled from absolute time, so seek, reverse-order capture and
frame-by-frame export are deterministic. `santa-v5-calibration.html` exposes
target presets, left/right selection, pointer dragging, timing/hold controls,
reach diagnostics, and the resolved pointing direction. Stage and capture
must continue to use this same rig path; FFmpeg receives only the resulting
frames and does not reimplement the gesture.

### Studio UI foundation 006.1

The frontend shell is organized into independent visual responsibilities:

```text
App shell
  ├─ Sidebar / project context
  ├─ Topbar / local status
  └─ Studio workspace
       ├─ Stage preview + transport
       ├─ Timeline rows from the audio manifest
       └─ Inspector (character, voice, diagnostics)
```

The UI reads the existing manifest and player contracts; it does not call
Kokoro, Animus, or any private project directly. Design tokens live in
`frontend/style.css`, and the shell uses CSS grid with responsive breakpoints
for desktop, tablet, and narrow mobile screens. `frontend/assets/logo.svg` and
`frontend/assets/favicon.svg` are original, lightweight vector assets.

The sidebar collapses behind an accessible mobile menu below 920px. Transport
buttons, the narration select, the seek slider, diagnostics disclosure, and
navigation affordances retain labels and visible keyboard focus. The UI keeps
the audio caveat explicit: RMS amplitude drives a visual mouth approximation;
it is not word, phoneme, or viseme alignment.

### Script editor

The editor will represent books, chapters, scenes, speakers, narration, direction notes, and reusable character references. The first data model should be serializable and versioned before a rich UI is built.

### TTS providers

The provider contract isolates text normalization, voice selection, synthesis, duration metadata, and errors. Kokoro is the first integrated provider and Piper remains an offline fallback candidate. The Kokoro adapter currently supports PT-BR voices `pf_dora`, `pm_alex`, and `pm_santa`, plus speed. It rejects unsupported pitch/volume/extras rather than silently ignoring them. Provider-specific models and environments stay outside the public repository.

### Character engine

Characters should be described by stable identities and backend-neutral actions. A future Animus adapter may implement one backend, but Fabuloom must not import Animus internals directly.

### Synchronization

Audio segments should produce a manifest containing stable IDs, source text, voice ID, audio path, duration, and optional word/phoneme timing. Timing must be generated from actual media, not estimated only from character count.

### Composition and export

The compositor should combine voice, music, ambience, SFX, and animation through an explicit timeline. FFmpeg is the initial export boundary. The Mission 010 demo is a deliberately small first exporter, not the complete editor/compositor. Exporters should be deterministic and keep source assets unchanged.

## Storage

SQLite is the planned local index for projects and metadata. Large media and model files should be stored in project-local managed locations under the isolated Fabuloom workspace, with manifests and checksums rather than binary assets in Git.

## License boundary

Only original Fabuloom code is covered by the project MIT license. Kokoro model/package, runtime dependencies, voices, and generated media remain subject to their own licenses. Every external integration needs a license/provenance record before distribution; see `docs/KOKORO-INTEGRATION.md`.

## Deterministic keyframe overlays

`frontend/src/animation-keyframes.mjs` provides the independent
`fabuloom.animation-keyframes/0.1` numeric clip format. It validates ordered
keyframes, samples them by absolute time with easing, and composes additive
channel layers without retaining playback state. Character adapters enforce
their own limits and map channels to the layered hierarchy.

Santa V5 consumes this boundary for `WAVE_HELLO`. The clip owns only the body
channels it animates; breathing, blinking and RMS mouth motion remain in the
base rig. This keeps Character Stage and frame capture on one source of truth
and avoids a second animation implementation in FFmpeg.

### Visual integrity research and engine boundary

Mission 012.8 audited the rendered Canvas plan before considering a backend
migration. The current `LayeredCharacterRenderer` is a rigid cut-out renderer:
each transparent PNG has a local pivot, parent transform and draw order; it
is deterministic for seek and out-of-order frame capture and is already shared
by the Stage and the FFmpeg bridge. It does not perform mesh deformation,
weight painting or phonetic facial alignment.

The research comparison is recorded in
`docs/ANIMATION-TOOLS-RESEARCH.md`. The conclusion is to keep Canvas as the
runtime/export boundary for the current V5 packs. Godot is the strongest later
candidate if mesh deformation and an engine-owned 2D skeleton become necessary;
Inochi2D is promising for specialist 2D deformation but would require a format
bridge and a separate runtime; Blender is best treated as an offline authoring
and render option because its armature/Grease Pencil pipeline is heavier than
the local Stage. None of these tools was installed or used in this mission.
