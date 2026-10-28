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
python .\frontend\server.py
```

The last command serves the stage only on `127.0.0.1`. Browser validation
covers manifest loading, real WAV playback, Play/Pause/Stop, seek, silence
gaps, Canvas rendering, and the amplitude-driven mouth. The visual signal is
not phonetic alignment.
