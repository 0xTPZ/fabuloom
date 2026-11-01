# Fabuloom Studio — Alpha preparation

Fabuloom Studio is a local-first prototype for turning narrated stories into audiovisual scenes. This branch consolidates the current Studio shell, the Santa V5 Narrator Mode reference, deterministic Canvas rendering, local Kokoro manifests and the existing FFmpeg examples.

## What this Alpha preparation actually includes

- A local browser Studio at `http://127.0.0.1:8765/`.
- Project-local script editing with persistent projects and sentence-based scene creation.
- Santa V5 Narrator Mode preview with measured audio timing when local manifests and WAV files exist.
- Scene image import, Santa V5 narration generation and project-scoped MP4 export.
- Dependency-free Python core contracts and Node renderer tests.
- Diagnostic tooling and preserved DEV laboratories.
- Project-scoped asynchronous MP4 export with per-scene zoom/pan rendering and controlled music ducking.

## Important limits

This is a Draft Alpha preparation, not a published release. A new user can create a project, save a script, import one image per sentence, generate real Kokoro `pm_santa` narration when the optional runtime and model are available, preview the measured timeline and export a horizontal MP4. New scene authoring is intentionally simple: sentence segmentation, local image association and a small camera vocabulary. Advanced editing, word/phoneme/viseme alignment and broad media support remain outside the Alpha claim.

Santa V5 is the production reference. Dora and Alex remain explicitly gated as `AWAITING_ART_APPROVAL`; experimental narrator packs are not Alpha features.

## Start here

Read [INSTALL.md](INSTALL.md), then [QUICKSTART.md](QUICKSTART.md). The full capability boundary is in [USER_GUIDE.md](USER_GUIDE.md), and known limitations are in [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## First production

1. Install the project-local environment and run `scripts/diagnose.ps1`.
2. Start the loopback Studio and open `http://127.0.0.1:8765/`.
3. Open **Projetos → ＋ Novo projeto**, then write and save a script.
4. Open **Cenas** and import one PNG/JPEG/WebP per scene.
5. Open **Áudio → Gerar narração Santa**, review **Prévia**, then choose **Exportação → Exportar MP4**.

## Project status

This branch is intended for human review as a Draft Alpha preparation. It must not be treated as a published release until a clean-machine acceptance test confirms the complete supported path.
