# Roadmap

## Foundation — completed

- Establish the isolated project layout.
- Document the architecture and project boundaries.
- Define public contribution and security rules.
- Define private recovery and continuity records.

## Version 0.1 — completed in Mission 004

- Versioned script and scene data model — complete.
- Python provider-neutral TTS boundary — complete.
- Deterministic simulated TTS provider — complete.
- Audio segment and synchronization manifest — complete.
- Automated offline tests and executable example — complete.

Deferred from V0.1: TypeScript shell and SQLite index.

## Version 0.2 — in progress

- Kokoro local provider — implemented in the Mission 005 integration branch;
  pending review.
- Piper offline provider.
- Chapter/scene preparation.
- WAV export and duration inspection.
- Initial character identity model.

## Version 0.3 — in progress

- Timeline editor — deferred.
- Character animation adapter boundary — demonstrator implemented in the local stage.
- Audio-to-animation synchronization — amplitude-driven preview implemented; phonetic alignment deferred.
- Preview composition — local Canvas stage implemented; first deterministic
  FFmpeg text-to-MP4 proof implemented in Mission 010; full compositor deferred.
- First video proof — Dora / `pf_dora`, measured segment captions, and RMS
  mouth response implemented; production editor and richer export controls
  remain deferred.
- Animation-ready narrator packs — V2 Dora, Santa and Alex with independent
  anatomical layers and shared Stage rig implemented in Mission 010.1.
- Rig-faithful video export — frame capture boundary implemented; FFmpeg bridge
  and end-to-end validation remain the next export step.

## Later

- Animus integration after its public boundary and license are verified.
- Full video compositor.
- Multiplatform export adapters.
- Word and phoneme alignment where the selected provider supports reliable timing.

No roadmap item is considered implemented until its tests and documentation are updated.
