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
