# Fabuloom Character Stage V0.3

This is a local-only Canvas 2D prototype. It loads the real narration
manifest from `E:\Fabuloom\workspace\exports`, decodes its WAV segments with
Web Audio, and drives a reusable character rig from live RMS amplitude.

The visual rig does not import Kokoro or Animus. Its mouth signal is amplitude
based and intentionally not phonetic alignment. Blinking, breathing, and head
motion continue during pauses and do not depend on audio amplitude.

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
