# Core contracts V0.1

The implementation is in `src/fabuloom_core` and uses JSON objects with an explicit `format_version`. V0.1 accepts the `0.1.x` compatibility family; a future minor version must be handled by an explicit migration before deserialization.

## Domain model

The project model is nested as:

```text
Project
  ├─ Character[]
  ├─ Narrator[]
  └─ Book[]
       └─ Chapter[]
            └─ Scene[]
                 └─ Dialogue[]
```

Every entity has a stable `id`. IDs must be unique across a project, not only within one collection. `make_stable_id(namespace, key)` can derive a deterministic ID from a natural key without randomness.

Dialogues are either `dialogue` with a `speaker_id` or `narration` with a `narrator_id`. References are checked during project validation.

## TTS contract

`SynthesisRequest` contains:

- request ID;
- text;
- voice ID;
- language;
- provider-neutral speed, pitch, volume, and extension parameters;
- caller metadata.

`SynthesisResult` returns provider ID, voice ID, language, audio URI, actual duration in milliseconds, optional word timings, optional phoneme/viseme timings, and metadata.

`TTSProvider` is a protocol. The `SimulatedTTSProvider` implements it without models, network access, files, or GPU. Its URI and word timings are explicitly marked `simulated`/`synthetic` and must not be treated as real acoustic measurements.

Synthesis speed and volume must be finite, non-boolean numbers greater than zero. Pitch must be a finite, non-boolean numeric offset; negative pitch is valid. `NaN`, positive/negative infinity, zero or negative speed/volume, and booleans are rejected with stable `TTSError` codes.

## Synchronization contract

All time values are integer milliseconds. An `AudioSegment` stores `start_ms`, `end_ms`, and `duration_ms`; validation requires `duration_ms == end_ms - start_ms`.

Each segment may contain word, phoneme, and viseme timing arrays. Their times are relative to the segment and are optional. When a provider has no phoneme or viseme data, the arrays remain empty; no precision is invented.

`AudioManifest` combines audio segments and animation events for a timeline. Intervals use the half-open convention `[start_ms, end_ms)`: touching ranges such as `[0, 100)` and `[100, 200)` are valid and do not overlap. The validator enforces:

- no negative times;
- no item beyond timeline duration;
- no duplicate IDs in a manifest;
- no overlap between audio segments on the same `track_id`;
- simultaneous segments on different tracks, including voice/music and SFX over other tracks;
- animation events may overlap on separate tracks;
- same-track overlap is allowed only when both events are `gesture`, `expression`, or `viseme`;
- structural events such as `page_change` and `camera` cannot overlap on the same track.

## JSON example

The executable example in `examples/contract_demo.py` creates a project, synthesizes a simulated segment, validates a manifest, serializes it, and deserializes the project. Run it from the repository root with:

```powershell
python .\examples\contract_demo.py
```
