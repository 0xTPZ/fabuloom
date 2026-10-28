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
warning logs.
