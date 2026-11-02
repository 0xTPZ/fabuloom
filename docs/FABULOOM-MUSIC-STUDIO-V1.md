# Fabuloom Music Studio V1

Music Studio V1 is the local-first production surface for owner-supplied instrumental tracks. It is intentionally separate from Kokoro narration and the Character Stage.

## Contracts

Projects use `fabuloom.music-studio-project/0.1`. A project records the source filename, SHA-256, FFprobe metadata, a 240-bar RMS envelope decoded from real PCM, a heuristic list of high-energy windows, a horizontal timeline, and an independent 15–30 second vertical timeline. The project explicitly records that BPM, beats and musical transitions are unavailable unless measured by a future audio-analysis tool.

The source file is copied only into the local export project. It is never retimed, pitch-shifted, or replaced. The final MP4 uses H.264 video and AAC audio; AAC is a container delivery encode, not a claim that the source changed.

## Renderer and UI

`frontend/src/music-studio-renderer.mjs` is shared by the Music Studio browser preview and `frontend/capture-music-studio.html`. The renderer composes environmental stills with slow camera motion, parallax-like layers, mist, crystals and particles. RMS changes the intensity of light and particles discreetly. No Santa V5, narrator medallion, captions, lip-sync or draft character is part of this mode.

The main interface is `frontend/studio.html`, route `#music`. The local server exposes only loopback endpoints for catalog, analysis, project persistence, and export job status. Music input is constrained to `workspace/inputs/music`; projects and outputs remain under `workspace/exports/music-studio`.

## Outputs and review

The full export is 1920×1080 at 30 FPS for the entire measured source duration. The Short is 1080×1920 at 30 FPS and uses its own framing/timeline over the selected source range; it is not a CSS crop of the full video. Each run also writes a small preview, a visual board, `analysis.json`, `project.json`, `reports/progress.json`, and `reports/technical-report.json`.

The selected initial test is `O Chamado do Vazio.mp3` because it is present in the local library. The music briefing associates this concept with a Suno-origin workflow. Commercial-use confirmation remains a release gate and no automatic publication is performed.

## Verification

Use the Python suite and frontend Node tests, then verify each MP4 with FFprobe and an FFmpeg decode. Human review remains required for visual approval and musical suitability; RMS candidate windows are not beat detection.
