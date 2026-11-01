# Cinematic Story Test V1

Mission 018 reuses the existing Narrator Mode V1.4 and deterministic Canvas →
PNG → FFmpeg pipeline. It is a composition test, not a new editor.

## Story and measured timeline

The original Portuguese narration is synthesized with Kokoro `pm_santa` and
`pt-BR`. The source text is separated into three paragraphs so the measured
audio can drive three semantic scenes. The third paragraph contains two
sentences; the narration contract keeps those as two measured audio segments
inside the third scene. Scene boundaries are calculated only after the WAV
durations are known. Punctuation/paragraph pauses are preserved as timeline
gaps.

The exported timeline is a workspace artifact:

`E:\Fabuloom\workspace\exports\cinematic-story-test-v1\fabuloom-cinematic-story-test-v1-timeline.json`

Word, phoneme and viseme timings remain unavailable. Captions use measured
segment ranges only.

## Scene assets and camera treatment

Three original generated raster backgrounds are kept outside Git under:

`E:\Fabuloom\workspace\exports\cinematic-story-test-v1\scenes`

The capture page uses the same `NarratorAvatarRenderer` as Narrator Mode V1.4
and places Santa in the lower-left. Scene effects are deterministic Canvas
operations:

- Arenhast: progressive zoom.
- Temple/crystal: progressive approach plus a restrained sinusoidal blue glow.
- Silhouette/crystal: lateral pan plus deterministic darkening.
- Scene boundaries: 700 ms crossfades.

FilmCraft 0.14.0 and EffectCraft 0.18.0 were audited in
`E:\TopazioCreativeLab`. Their previously verified operations include FilmCraft
timeline/import/export/render/keyframes/transitions and EffectCraft
composition/render-frame. The two engines are not silently treated as an
integrated dependency here; Fabuloom uses its already validated Canvas and
FFmpeg path.

## Reproduction

```powershell
$env:PYTHONPATH = "E:\Fabuloom\studio\src"
E:\Fabuloom\workspace\.venv\Scripts\python.exe `
  E:\Fabuloom\studio\examples\cinematic_story_test_demo.py --overwrite
```

The output video is:

`E:\Fabuloom\workspace\exports\videos\fabuloom-cinematic-story-test-v1.mp4`

The MP4, WAVs, generated scenes, frame sequence, timeline, SRT, frame board
and report are workspace artifacts and must not be committed to the public
repository. Artistic approval remains a human review step.

## Mission 018.1 — lip-sync regression fix

The first cinematic capture had a regression in its inline RMS path: it called
the reader without the measured WAV sample rate. The resulting absolute-time
window became `NaN`, so the reader returned zero for every frame even though the
Kokoro audio was valid. Mission 017.4 passed this argument correctly.

The fix extracts strict mono PCM-16 decoding, absolute-time segment composition
and the RMS reader into `frontend/src/cinematic-audio.mjs`. The capture page now
passes the actual sample rate and records RMS, mouth state and selected asset
diagnostics in `complete.json`. The official Santa V5 assets and scene images
are unchanged.

Reproduce the corrected video without synthesis:

```powershell
$env:PYTHONPATH = "E:\Fabuloom\studio\src"
E:\Fabuloom\workspace\.venv\Scripts\python.exe `
  E:\Fabuloom\studio\examples\cinematic_story_lipsync_demo.py --overwrite
```

The corrected output, mouth-state board, V1/V1.1 comparison, difference crop
and RMS report are under `E:\Fabuloom\workspace\exports\videos`. The final
MP4 reuses the Mission 018 WAV and manifest, remains 1920×1080 H.264/AAC and
has no word, phoneme or viseme timestamps. Human visual review remains
required.
