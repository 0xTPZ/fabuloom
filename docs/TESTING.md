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
