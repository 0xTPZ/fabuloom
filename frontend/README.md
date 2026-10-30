# Fabuloom Character Stage V0.3

This is a local-only Canvas 2D prototype. It loads the real narration
manifest from `E:\Fabuloom\workspace\exports`, decodes its WAV segments with
Web Audio, and drives a reusable character rig from live RMS amplitude.

The UI uses a small dark-blue/violet/gold design system defined in
`style.css`. The shell contains a project sidebar, breadcrumb topbar, stage
preview, manifest-backed timeline, character/voice inspector, diagnostics
disclosure, and responsive transport controls. It is designed for desktop,
tablet, and narrow mobile layouts and remains local-only.

The visual rig does not import Kokoro or Animus. Its mouth signal is amplitude
based and intentionally not phonetic alignment. Blinking, breathing, and head
motion continue during pauses and do not depend on audio amplitude.

The Character Stage can switch between the original geometric rig and the
optional layered pack for Ari, an adult fantasy narrator. The pack is validated
before local PNG/SVG assets are loaded; layer transforms, pivots, draw order,
anatomical hierarchy, expressions, blinking, head motion, brow motion, arm
gestures, mouth openness, breathing, and subtle hair sway are handled by
`src/layered-character.ts`.

The primary demonstrators are now the animation-ready V2 narrator trio: Dora
(`pf_dora`), Santa (`pm_santa`), and Alex (`pm_alex`). Their shared original
uniform language uses independent torso, neck, head, hair, facial, arm, hand
and accessory layers. The voice IDs are metadata used to keep visual
identities aligned with narration voices. The earlier portrait-based V1 packs
remain available as compatibility references; Ari and Lia remain technical
references.

The local narration catalog in `src/topazio-narrations.mjs` maps each official
character to a pre-generated manifest in `E:\Fabuloom\workspace\exports`.
The inspector reports the voice actually found in the loaded manifest, and a
character change stops/disposes the previous player before loading the matching
existing WAV set. Synthesis is never triggered by a character selection.

## Run locally

From `E:\Fabuloom\studio`:

```powershell
python .\frontend\server.py
```

Open `http://127.0.0.1:8765/` in a browser. The server binds only to
loopback, serves the frontend directory, and exposes only files beneath
`E:\Fabuloom\workspace\exports` under `/exports/`.

The checked-in `.ts` modules are written in browser-compatible TypeScript
syntax so the local server can run without installing a bundler. The
`frontend/tsconfig.json` documents the strict compiler target for a future
local TypeScript toolchain. Timeline tests can run with Node's built-in
TypeScript stripping:

```powershell
node --experimental-strip-types .\frontend\tests\test_timeline.mjs
```

The original vector brand assets are in `frontend/assets/`. No bundler or
global dependency is required for the local preview.

## Animation-ready capture boundary

`src/layered-character.ts` exposes `frameSchedule`,
`LayeredCharacterRenderer.renderFrame`, and `captureLayeredFrames`. They use
the same rig and Canvas renderer as the Stage, update the pose at deterministic
timestamps, and stream transparent PNG frames through a callback without
accumulating the whole sequence in memory. `capture-character.html` is the
local browser bridge used by `examples/character_engine_video_demo.py`: it
loads Santa V2, computes the PCM-16 RMS envelope from the measured WAV, and
posts frames only to the loopback capture endpoint. FFmpeg composes those
same frames over the background; the original portrait exporter remains a
compatibility reference.

The Santa V5 visual-integrity review is available at
`/santa-v5-visual-integrity.html`. It is a local QA page for the clean facial
base, eyelid open/closed states, RMS mouth state, neutral/raised/pointing hands
and grounded feet. The page uses the same pack and draw-plan implementation as
the Stage; it is not a second renderer.

## Visual Inspector V1

Open `/visual-inspector.html` from the local server for the read-only DEV
inspector. It renders Santa V5 through the same `LayeredCharacterRenderer`,
shows landmarks and evidence-based diagnostics, supports approved PNG
references, exports the current frame JSON and keeps a local session history.
The automated loopback capture and report CLI is documented in
`docs/VISUAL-INSPECTOR.md` and does not modify assets or source files.
V1.1 also reports controlled defect fixtures, separates technical and artistic
references, and states when temporal or human review has not been executed.
V1.2 adds `/visual-inspector-real.html` for local PNG inspection independent
of the active Stage. The offline pixel analyzer records alpha availability,
foreground bounds, connected components, broad evidence regions and reference
differences. Historical evaluation writes blind results before post-hoc human
review; an unavailable multimodal provider is represented explicitly rather
than simulated.
