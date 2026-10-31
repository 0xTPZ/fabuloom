# Testing

The V0.1 test suite uses only Python's standard library. It does not require internet access, models, GPU drivers, Kokoro, Piper, FFmpeg, or a virtual environment.

From `E:\Fabuloom\studio`:

```powershell
python -m unittest discover -s tests -v
python .\examples\contract_demo.py
```

The Kokoro unit tests use injected fakes and do not load a model. The real
integration test is opt-in and requires an already available local model:

```powershell
$env:FABULOOM_RUN_KOKORO_REAL = "1"
python -m unittest tests.integration.test_kokoro_real -v
```

The demonstration uses offline mode and writes only to
`E:\Fabuloom\workspace\exports`:

```powershell
python .\examples\kokoro_demo.py --text "Uma história em português brasileiro." --voice pf_dora
python .\examples\kokoro_story_demo.py --voice pf_dora
```

The tests cover:

- project validation;
- JSON serialization and deserialization;
- explicit format compatibility;
- deterministic stable IDs;
- duplicate IDs and invalid references;
- negative and out-of-bounds times;
- forbidden audio overlap;
- simultaneous audio on different tracks and half-open touching ranges;
- allowed and forbidden animation overlap;
- nested animation overlap detection;
- audio manifest round-trip;
- simulated TTS determinism and error handling;
- finite, non-boolean speed, volume, and pitch parameters.
- Kokoro PT-BR voice selection, model reuse, output-path protection, WAV
  validation, provider errors, and unavailable timing metadata.
- sentence/paragraph segmentation, long-text limits, punctuation pauses,
  ordered manifest composition, voice consistency, partial failure reporting,
  and explicit overwrite control.

The simulated provider intentionally returns a placeholder URI and synthetic word timing. Passing these tests does not validate the quality or timing of a real TTS engine.

The V0.3 frontend tests are dependency-free Node tests using built-in
TypeScript stripping:

```powershell
node --experimental-strip-types .\frontend\tests\test_timeline.mjs
node --experimental-strip-types .\frontend\tests\test_audio.mjs
node --experimental-strip-types --test .\frontend\tests\test_layered_character.mjs
python .\frontend\server.py
```

The last command serves the stage only on `127.0.0.1`. Browser validation
covers manifest loading, real WAV playback, Play/Pause/Stop, seek, silence
gaps, Canvas rendering, and the amplitude-driven mouth. The visual signal is
not phonetic alignment.

The UI foundation was also checked in a browser at these viewports:

- 1920x1080 and 1366x768: two-column stage plus inspector;
- 768x1024: single-column stage with a two-column inspector;
- 390x844 and 360x800: single-column mobile layout, collapsed sidebar, and no
  horizontal overflow.

The browser check also confirmed keyboard-visible focus styles, the mobile
sidebar open/close behavior, successful Play/Pause/Stop transitions, and no
browser console errors or warnings during the local demo.

Mission 007A.1 additionally validates the layered pack contract with
`node --test .\frontend\tests\test_character_pack.mjs`, and checks the
optional renderer with the dependency-free layered rig tests. Browser checks
cover selection between the geometric and layered characters, expression
switching, local PNG/SVG loading, Play/Pause/Stop while the layered character
is active, desktop composition, mobile no-overflow, and empty console error /
warning logs. Mission 007A.2 additionally covers the 16-node Ari anatomical
hierarchy, head-only rotation isolation, inherited facial transforms, arm /
hair / brow bindings, and the refined original layer assets.

Mission 009 adds the official narrator-pack checks:

```powershell
node --test .\frontend\tests\test_topazio_narrators.mjs
```

The test validates Dora, Santa, and Alex pack metadata, PT-BR Kokoro voice
identifiers, v0.1 contract validation, and finite layered draw plans. Browser
validation should additionally select each narrator, verify the shared stage
layout and inspector metadata, exercise expression and transport controls,
seek through the manifest, and confirm no console errors or warnings.

Mission 009.1 also validates the real local narration set. The generated
manifests must contain exactly one voice each (`pf_dora`, `pm_santa`, or
`pm_alex`), 24 kHz mono PCM-16 WAV segments, and durations matching WAV frame
counts. Browser checks cover automatic manifest selection, voice identity shown
in the inspector, switching during playback, paused-state and seek behavior,
safe stop/disposal, and empty error/warning logs. The audio-player unit test
also verifies that disposal closes the context and clears decoded buffers.

Mission 010.1 adds animation-ready V2 pack coverage. The Character Stage now
loads Dora, Santa and Alex from 16 real layers each, while the V1 portrait
packs remain validated as compatibility references. The tests cover the V2
rig profile, anatomical roles, head-parent isolation, finite draw plans, and
the deterministic frame schedule:

```powershell
node --test .\frontend\tests\test_character_pack.mjs .\frontend\tests\test_layered_character.mjs .\frontend\tests\test_topazio_narrators.mjs
```

The browser capture API is `captureLayeredFrames` in
`frontend/src/layered-character.ts`. It streams one transparent Canvas PNG
blob per frame to a caller-owned callback using deterministic absolute times.
Browser validation should select each V2 narrator, exercise head motion,
blink, RMS mouth, breathing, arm/hand hierarchy and expressions, then confirm
no console errors or warnings. The original portrait exporter remains covered
by the Mission 010 render/probe checks.

Mission 011 adds dependency-free Santa V3 contract and scene tests:

```powershell
node --test .\frontend\tests\test_santa_v3.mjs
```

The real local demonstration reuses the existing offline Kokoro environment
and captures the same `SantaV3Rig` / `SantaV3SceneRenderer` used by the
browser stage:

```powershell
$env:PYTHONPATH = "E:\Fabuloom\studio\src"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:HF_DATASETS_OFFLINE = "1"
python .\examples\santa_v3_video_demo.py `
  --export-dir "E:\Fabuloom\workspace\exports" `
  --reuse-manifest --overwrite
```

The command verifies contiguous PNG frames, measured WAV timing, a 1080x1920
H.264/AAC MP4, a three-frame comparison image and an FFmpeg-readable output.
The scene contains no invented word, phoneme or viseme timestamps. Human
visual review remains required for final animation approval.

## Character Engine video demonstration

The Mission 010.2 exporter uses a local Kokoro runtime and writes the Santa V2
demonstration only under `E:\Fabuloom\workspace\exports`:

```powershell
$env:PYTHONPATH = "E:\Fabuloom\studio\src"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:HF_DATASETS_OFFLINE = "1"
python .\examples\character_engine_video_demo.py `
  --export-dir "E:\Fabuloom\workspace\exports" `
  --background "E:\Fabuloom\workspace\exports\videos\fabuloom-first-video-background.png" `
  --overwrite
```

The command produces `fabuloom-character-engine-santa.mp4`, measured audio,
SRT and per-segment caption sources, a transparent frame sequence, and a
probe report. The capture server is enabled only when `FABULOOM_CAPTURE_DIR`
is set by the script, binds to `127.0.0.1`, rejects paths outside the
workspace and accepts only PNG/JSON payloads. The exporter checks frame
count/order, WAV/video duration, H.264/AAC output, full FFmpeg decode and
black-frame diagnostics. Human review is still required for final visual
approval.

## First video demonstration

The Mission 010 demo uses an already available local Kokoro runtime and does
not install packages or download model weights. It writes generated artifacts
only under the configured workspace export directory:

```powershell
$env:PYTHONPATH = "E:\Fabuloom\studio\src"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:HF_DATASETS_OFFLINE = "1"
python .\examples\first_video_demo.py `
  --export-dir "E:\Fabuloom\workspace\exports" `
  --background "E:\Fabuloom\workspace\exports\videos\fabuloom-first-video-background.png" `
  --overwrite
```

After the first synthesis, `--reuse-manifest` re-renders the same text and
voice without invoking TTS again. The exporter reports the measured segment
manifest duration, the MP4 probe, the RMS mouth source, and the explicit
absence of word/phoneme/viseme timing. Validate the finished file with:

```powershell
ffprobe -v error -show_entries format=duration,size:stream=index,codec_name,codec_type,width,height,pix_fmt,sample_rate,channels -of json .\workspace\exports\videos\fabuloom-first-video-dora.mp4
ffmpeg -hide_banner -loglevel error -i .\workspace\exports\videos\fabuloom-first-video-dora.mp4 -f null -
```

The first reference export is a 1080x1920 H.264/AAC MP4. Its captions are
segment-level captions based on measured audio boundaries; they are not word
alignment.

## Visual Inspector V1

The Inspector unit tests are dependency-free and include frame-schema
serialization, known-good Santa V5 evidence, artificial joint gaps, facial
asset duplication, blink states, insufficient evidence, motion discontinuity,
deterministic rectangle transforms, and tolerant PNG comparison:

```powershell
node --test .\frontend\tests\test_visual_inspector.mjs
```

The first end-to-end inspection uses the same renderer through loopback HTTP:

```powershell
node .\tools\visual-inspector\cli.mjs `
  --output "E:\Fabuloom\workspace\exports\visual-inspector\mission-013"
```

The report is read-only and returns a non-zero correction status only when a
confirmed error or capture failure is present. Warnings and hypotheses remain
review states. The comparison baseline is the neutral frame of the same run
unless an approved PNG is supplied with `--reference`; it is not artistic
ground truth. Review the generated Markdown, JSON, masks, overlays and the
DEV page before accepting a visual change.

Mission 013.1 adds nine controlled known-defect fixtures and checks both
positive detection and the known-good false-positive count. The full report
also samples IDLE, WAVE_HELLO and POINT_AT sequences and emits highlighted
fixture evidence plus `visual-inspection-evidence.json`:

```powershell
node .\tools\visual-inspector\cli.mjs `
  --output "E:\Fabuloom\workspace\exports\visual-inspector\mission-013.1-final"
```

The external `--reference PNG` input is recorded as an artistic reference and
is never substituted for the technical neutral baseline. The current CLI uses
measured alpha bounds and tolerant PNG differences; pixel-perfect or AI-based
artistic judgment remains outside the automated acceptance criterion.

## Visual Inspector V1.2 — imagens históricas reais

The real-image path uses only local PNGs and does not require a model, GPU or
network service. The historical sample bank is created from preserved V3/V4/V5
MP4 frames plus an isolated replay of the preserved V5 `head.png` asset. The
original media is never overwritten:

```powershell
node .\tools\visual-inspector\cli.mjs `
  --output "E:\Fabuloom\workspace\exports\visual-inspector\mission-013.2-real\historical-head-original" `
  --variant historical-head-original

node .\tools\visual-inspector\real-cli.mjs `
  --workspace "E:\Fabuloom" `
  --output "E:\Fabuloom\workspace\exports\visual-inspector\mission-013.2-real\real-run" `
  --review "E:\Fabuloom\workspace\exports\visual-inspector\mission-013.2-real\historical-review.json"
```

The command writes `historical-dataset-manifest.json` with source paths,
times, dimensions and SHA-256 hashes. It first writes `blind-results.json`
without review labels, then optionally computes post-hoc metrics from the
separate review file. `real-visual-inspection-report.md` records the sample
size, confirmed defects, artistic differences, inconclusive cases, evidence
regions and limitations. Results are not comparable to the JSON fixture rate
unless explicitly reported as separate populations.

For a browser-only check, start the local server and open
`/visual-inspector-real.html`. Select a local PNG and, optionally, a reference
PNG. The page does not require an active character and displays pixel evidence,
confidence and the explicit `IA multimodal: não executada` state.

## Santa V4 cartoon refinement

Mission 011.1 adds the dependency-free Santa V4 contract and transform tests:

```powershell
node --test .\frontend\tests\test_santa_v4.mjs .\frontend\tests\test_santa_v3.mjs
```

The refinement demonstration reuses the measured Santa V3 manifest and emits
the V4 MP4, frame comparisons and report under the workspace export directory:

```powershell
$env:PYTHONPATH = "E:\Fabuloom\studio\src"
python .\examples\santa_v4_video_demo.py `
  --export-dir "E:\Fabuloom\workspace\exports" `
  --overwrite
```

The command validates the local V4 pack, contiguous PNG frames, measured WAV
duration, H.264/AAC output and V3/V4 comparison frame. It does not synthesize
new audio. Word, phoneme and viseme timing remain unavailable.

## Santa V5 rig and video capture

Mission 012.1 validates the final V5 layer contract, deterministic transforms,
independent head/torso motion and visible hand channels:

```powershell
node --test .\frontend\tests\test_santa_v5_art.mjs
```

For visual review, start the loopback stage server and open
`/santa-v5-preview.html`. The preview uses the same fine-grained pack as the
Stage. To produce the measured local demonstration and frame comparisons:

```powershell
$env:PYTHONPATH = 'E:\Fabuloom\studio\src'
& 'E:\Fabuloom\workspace\.venv\Scripts\python.exe' .\examples\santa_v5_video_demo.py --overwrite
```

The capture validates a contiguous 30 FPS PNG sequence, 1080x1920 composition,
the real measured `pm_santa` WAV duration, and FFprobe H.264/AAC output. The
comparison artifacts are written under `E:\Fabuloom\workspace\exports\videos`.
RMS mouth motion is intentionally not phoneme or viseme alignment.

Mission 012.3 adds `frontend/tests/test_santa_v5_calibration.mjs`. It checks
the measured alpha metadata, action-specific amplitude limits, deterministic
draw plans and independent head/hand transforms. The visual tools are local
DEV pages; their screenshots and the silent 8-second reel are generated under
the workspace export directory and are not committed.

Mission 012.4 extends those checks with local-to-stage landmark conversion,
landmark/pivot proximity for shoulders, elbows, wrists, knees and ankles,
finite hierarchical transforms, bounded gait channels and continuity checks at
walk/seated phase boundaries. Visual review remains mandatory because the long
coat can conceal some seated knee motion even when the transforms are valid.

Mission 012.5 adds `frontend/tests/test_animation_keyframes.mjs` and
`frontend/tests/test_santa_v5_wave.mjs`. They cover clip validation, finite
numeric parameters, easing/interpolation, additive channel composition,
absolute-time determinism after seek, continuity, RMS/breathing composition,
joint movement and landmark hierarchy checks for `WAVE_HELLO`.

The visual DEV tool is `/santa-v5-calibration.html`; select `WAVE_HELLO` to
inspect keyframes and use play, pause or seek. The five-pose board is
`/santa-v5-wave-gallery.html`. The technical capture is generated with:

```powershell
& 'E:\Fabuloom\workspace\.venv\Scripts\python.exe' .\examples\santa_v5_wave_demo.py --overwrite
```

It produces a silent 5-second H.264 MP4 under
`E:\Fabuloom\workspace\exports\videos\`.

Mission 012.6 adds the dependency-free IK and rendered-endpoint checks:

```powershell
node --test .\frontend\tests\test_two_bone_ik.mjs .\frontend\tests\test_santa_v5_wave.mjs .\frontend\tests\test_santa_v5_art.mjs .\frontend\tests\test_santa_v5_calibration.mjs
```

These tests cover reachable and unreachable targets, elbow preference and
limits, deterministic angle helpers, normalized target overrides, expression
asset preservation, transformed shoulder/elbow/hand pivots, seek stability,
and the measured rendered hand error at a full wave pose. The regenerated
technical MP4 is checked with FFprobe as 150 frames at 30 FPS, 1080x1920,
H.264, silent and 5.000 seconds. The five-pose board and previous-versus-IK
comparison remain workspace-only review artifacts.

Mission 012.7 adds the provider-independent target and presenter tests:

```powershell
node --test .\\frontend\\tests\\test_presentation_targets.mjs .\\frontend\\tests\\test_santa_v5_point_at.mjs .\\frontend\\tests\\test_santa_v5_art.mjs
```

They cover normalized and scene-object target resolution, invalid targets,
configurable POINT_AT phases/hold, safe out-of-reach planning, right/left arm
selection, actual left-hand pivot reach, expression asset preservation, and
out-of-order deterministic seeks. The capture is
`fabuloom-santa-v5-point-at.mp4`; its accompanying report records the target
sequence, frame count and the fact that the video is silent by design. The
pose board is a workspace-only visual review artifact.

Mission 012.8 adds the visual-integrity regression suite and review page:

```powershell
node --test .\frontend\tests\test_santa_v5_visual_integrity.mjs .\frontend\tests\test_santa_v5_art.mjs .\frontend\tests\test_santa_v5_calibration.mjs
```

Open `/santa-v5-visual-integrity.html` on the loopback server to review the
clean facial base, neutral/blink/mouth states, hand neutral/raised/pointing
states and grounded feet. The screenshot
`E:\Fabuloom\workspace\exports\santa-v5-visual-integrity.png` is a local QA
artifact and is not committed.

Mission 013.3 adds deterministic Visual QA plan/evidence/correction tests:

```powershell
node --test .\frontend\tests\test_visual_qa.mjs
```

The full gate is local and uses Edge headless plus the loopback server. It
does not require internet, GPU, a vision model or model weights. Use
`qa-gate.mjs --correction` only for the documented historical replay; the
official production pack remains untouched and artistic approval stays pending
human review.

## Mission 014 — Santa V5 visual quality recovery

The Mission 014 audit runs the same gate at production width and includes both
POINT_AT directions:

```powershell
node .\tools\visual-inspector\qa-gate.mjs `
  --output "E:\Fabuloom\workspace\exports\visual-qa\mission-014\audit-production-1080-final" `
  --port 8873 --variant production-v5
```

The final run passed the technical gate with 60 captures at 1080×1920. Human
inspection verified the corrected WAVE_HELLO anchor, right and left POINT_AT,
face states, hands and grounded feet. The report generator creates the
before/after overlays and close-up evidence:

```powershell
node .\tools\visual-inspector\mission-014-report.mjs
```

The deterministic video checks are:

```powershell
python .\examples\santa_v5_wave_demo.py --export-dir E:\Fabuloom\workspace\exports --overwrite
python .\examples\santa_v5_point_at_demo.py --export-dir E:\Fabuloom\workspace\exports --overwrite
ffmpeg -v error -i E:\Fabuloom\workspace\exports\videos\fabuloom-santa-v5-point-at.mp4 -f null -
```

Both videos were verified with FFprobe as H.264/yuv420p at 1080×1920; WAVE is
5.000 s and POINT_AT is 8.500 s. The demos are silent visual engine proofs;
they do not claim phonetic alignment. Generated frames, videos and boards stay
under `E:\Fabuloom\workspace\exports` and are not committed.

## Mission 015 — anatomy-first evidence

The experimental pack and derived PNG bands are validated without network,
models or GPU dependencies:

```powershell
node --experimental-strip-types --test .\frontend\tests\test_santa_v5_anatomy_experimental.mjs
node .\tools\anatomy-first-rig\generate-experimental-assets.mjs
node .\tools\anatomy-first-rig\generate-report.mjs
```

Serve the local comparison pages with `python .\frontend\server.py --port
8903`, then open `/santa-v5-anatomy-gallery.html`,
`/santa-v5-arm-comparison.html` and `/santa-v5-boots-comparison.html`.
The short motion proof is generated with:

```powershell
python .\examples\santa_v5_anatomy_demo.py --export-dir E:\Fabuloom\workspace\exports --overwrite
```

The proof uses the same `SantaV5Rig` and `LayeredCharacterRenderer` as the
Stage. It is an isolated raster reconstruction, not a mesh-deformation test;
Godot, Inochi2D and Blender were unavailable locally and no installation is
performed by this workflow.

## Mission 017 — Narrator Mode

Pure Narrator Mode contracts are tested without a browser or model:

```powershell
node --test .\frontend\tests\test_narrator_mode.mjs
```

The real local export requires the existing Fabuloom virtual environment,
cached Kokoro assets, Edge and FFmpeg. After export, inspect actual PNG
samples with:

```powershell
node .\tools\visual-inspector\narrator-mode-report.mjs
```

The capture report checks 1920×1080 frames, non-empty opaque samples,
deterministic differences, the circular facial-only avatar and caption safe
area. Human review remains required.

## Mission 017.1 — facial correction

The facial correction adds a renderer-path contract test and a no-synthesis
export that reuses the Mission 017 WAV and measured manifest:

```powershell
node --test .\frontend\tests\test_narrator_mode.mjs .\frontend\tests\test_layered_character.mjs
E:\Fabuloom\workspace\.venv\Scripts\python.exe `
  .\examples\narrator_mode_face_correction_demo.py --overwrite
node .\tools\visual-inspector\narrator-face-correction-report.mjs
node .\tools\visual-inspector\qa-gate.mjs `
  --output "E:\Fabuloom\workspace\exports\visual-qa\mission-017.1" `
  --port 8817 --variant production-v5
```

Open `/narrator-face-lab.html` through the loopback server for enlarged
before/after review, explicit blink and mouth states, head movement and layer
visibility toggles. The face lab and all reports are diagnostic evidence; they
do not perform artistic approval and do not modify official Santa V5 assets.

## Mission 017.2 — final avatar framing

The framing change is covered by crop/safe-area validation, bounded offset and
zoom adjustment, deterministic rendering, facial-state samples and the same
renderer path used by the exporter:

```powershell
node --test .\frontend\tests\*.mjs
$env:PYTHONPATH='E:\Fabuloom\studio\src'
E:\Fabuloom\workspace\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'
E:\Fabuloom\workspace\.venv\Scripts\python.exe `
  .\examples\narrator_mode_framing_demo.py --overwrite --reuse-capture
node .\tools\visual-inspector\narrator-face-framing-report.mjs
ffmpeg -v error -i E:\Fabuloom\workspace\exports\videos\fabuloom-narrator-mode-v1.2-framing.mp4 -f null -
```

The V1.2 evidence includes the equivalent V1.1/V1.2 frame comparison, five
facial states, the safe-area overlay and the JSON/Markdown Visual Inspector
report. The Inspector checks pixels and structure; it does not grant artistic
approval. The audio and manifest are reused, so no Kokoro synthesis is required
for this validation.

## Mission 017.3 — face alignment

The face-alignment change is covered by head-local landmark/alpha-target
contracts and the existing renderer tests:

```powershell
node --test .\frontend\tests\test_narrator_mode.mjs
node --test .\frontend\tests\*.mjs
python -m pytest -q
node .\tools\visual-inspector\narrator-face-alignment-report.mjs
```

The alignment report samples neutral, head motion, blink and open-mouth frames,
compares V1.2 and V1.3 at equivalent timestamps, checks 1920×1080 opaque
frames, and records the `head-local-v1` landmarks and measured alpha bounds.
The browser lab must be opened through `frontend/server.py`; it uses the same
renderer/export path, displays a static `head.png` reference and keeps layer
toggles available. The no-synthesis export reuses the Mission 017 WAV and
manifest. Technical evidence and the optional QA Gate never replace human
artistic review.

## Mission 017.4 — anatomical neck boundary

The V1.4 correction is covered by the Narrator Mode unit tests and by a real
browser capture/export:

```powershell
node --test .\frontend\tests\test_narrator_mode.mjs
node --test .\frontend\tests\*.mjs
python -m pytest -q
python .\examples\narrator_mode_neck_fix_demo.py --overwrite
```

The tests assert that the structural `neck` parent remains in the draw plan,
its corrected opacity is zero, the head transform is unchanged relative to a
source-composition pack, and the visible collar owner is `head-clean.png`.
The demo reuses the measured Mission 017 audio and manifest, probes the output
with FFprobe, and produces before/after and enlarged transition evidence. The
face lab must be opened through `frontend/server.py`; its semantic neck/beard
toggles and color map are diagnostic only. No automated check grants artistic
approval.
