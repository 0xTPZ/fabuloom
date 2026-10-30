# Fabuloom Narrator Mode V1

Narrator Mode is a horizontal, facial-presenter export mode for stories that
do not need the full-body Character Stage. It reuses the existing Kokoro
manifest, `LayeredCharacterRenderer`, Canvas capture boundary and FFmpeg mux,
but composes a separate cinematic scene with a circular Santa V5 facial
avatar.

## Pipeline

```text
texto original → Kokoro pm_santa → WAVs medidos → manifesto de segmentos
       → RMS PCM-16 → avatar facial circular + cenário SVG → PNGs determinísticos
       → FFmpeg H.264/yuv420p + AAC → MP4 horizontal
```

Generate the demo with:

```powershell
E:\Fabuloom\workspace\.venv\Scripts\python.exe `
  E:\Fabuloom\studio\examples\narrator_mode_demo.py --overwrite
```

Outputs stay outside Git under `E:\Fabuloom\workspace\exports`. The demo
uses the exact V1 text, `pm_santa`, `pt-BR`, a 1920×1080 canvas and 30 fps.
Kokoro model weights are not part of this repository.

## Architecture boundary

- `NarratorAvatarRenderer` filters the approved Santa V5 pack to neck, head,
  hair and facial layers. It clips the result to a configurable gold/blue
  circle; limbs, body and IK are not loaded.
- `NarratorSceneRenderer` owns the original storyteller-office SVG, ambient
  glow, title, avatar placement and safe subtitle area.
- `createNarratorTimeline()` preserves measured `[start_ms, end_ms)` segment
  intervals and marks word, phoneme and viseme timing as unavailable.
- `SubtitleRenderer` renders segment captions only.
- `capture-narrator-mode.html` uses real WAV samples to calculate the mouth
  RMS envelope and streams deterministic PNG frames to the loopback server.
- `narrator_mode_demo.py` invokes capture and FFmpeg; FFmpeg does not
  implement a second animation rig.

## DEV area

Open `/narrator-mode.html` through `frontend/server.py`. The page provides the
script text, voice and scene selectors, a Canvas preview, local WAV
Play/Pause/Stop controls and a loopback-only “Gerar vídeo” action. The action
starts the known `narrator_mode_demo.py` job; it does not accept shell
commands, paths or executable names from the browser.

## Visual QA

Inspect actual rendered PNG samples with:

```powershell
node E:\Fabuloom\studio\tools\visual-inspector\narrator-mode-report.mjs
```

The report checks canvas dimensions, opaque/non-empty samples, deterministic
differences between timestamps, circular avatar layout and the subtitle safe
area. It is evidence for human review, not automatic artistic approval.

## Known limits

- Mouth motion is an RMS intensity approximation, not phoneme or viseme
  alignment.
- Captions are synchronized to measured audio segments, not individual words.
- The office scenario is an original SVG composition and intentionally simple.
- The facial pack is a controlled crop of Santa V5, not a mesh-deformed head.
- MP4 and WAV files are generated artifacts and must stay in the workspace
  export directory.

