# Fabuloom Studio — Alpha preparation

Fabuloom Studio is a local-first prototype for turning narrated stories into audiovisual scenes. This branch consolidates the current Studio shell, the Santa V5 Narrator Mode reference, deterministic Canvas rendering, local Kokoro manifests and the existing FFmpeg examples.

## What this Alpha preparation actually includes

- A local browser Studio at `http://127.0.0.1:8765/`.
- Script text editing saved in the browser for the current demo.
- Santa V5 Narrator Mode preview with measured audio timing when local manifests and WAV files exist.
- Scene/profile inspection and links to existing local exports.
- Dependency-free Python core contracts and Node renderer tests.
- Diagnostic tooling and preserved DEV laboratories.
- Project-scoped asynchronous MP4 export with per-scene zoom/pan rendering and controlled music ducking.

## Important limits

This is a preparation branch, not a release. The first project workflow and MP4 export are now implemented, but real Kokoro narration still requires the optional provider and model. New scene authoring is intentionally simple: sentence segmentation, local image association and a small camera vocabulary. Advanced editing, word/phoneme/viseme alignment and broad media support remain outside the Alpha claim.

Santa V5 is the production reference. Dora and Alex remain explicitly gated as `AWAITING_ART_APPROVAL`; experimental narrator packs are not Alpha features.

## Start here

Read [INSTALL.md](INSTALL.md), then [QUICKSTART.md](QUICKSTART.md). The full capability boundary is in [USER_GUIDE.md](USER_GUIDE.md), and known limitations are in [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Project status

This branch is intended for human review as a Draft Alpha preparation. It must not be treated as a published release until a clean-machine acceptance test confirms the complete supported path.
