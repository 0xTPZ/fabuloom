# Testing

The V0.1 test suite uses only Python's standard library. It does not require internet access, models, GPU drivers, Kokoro, Piper, FFmpeg, or a virtual environment.

From `E:\Fabuloom\studio`:

```powershell
python -m unittest discover -s tests -v
python .\examples\contract_demo.py
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

The simulated provider intentionally returns a placeholder URI and synthetic word timing. Passing these tests does not validate the quality or timing of a real TTS engine.
