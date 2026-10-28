# Fabuloom Studio

Fabuloom Studio is an open-source foundation for turning stories and scripts into narrated videos with animated characters.

The project is being designed as an independent application by 0xTPZ. It is intentionally separate from TopazioReader and Card Game Studio. Those projects are references only; no source code, models, environments, personal audio, or private context is published here.

## Vision

Fabuloom should let a creator move from a written story to an editable scene timeline, with narration, characters, audio synchronization, and export targets that can grow from local desktop workflows to other platforms.

## Initial architecture

1. Script editor — chapters, scenes, dialogue, narration, and structured metadata.
2. TTS providers — Kokoro as the initial primary provider, Piper as an offline alternative, and a provider interface for future engines.
3. Character engine — modular character identities, expressions, poses, and animation backends.
4. Audio/animation synchronization — segment manifests, durations, cues, and alignment metadata.
5. Scene director — camera, staging, voice direction, ambience, and transitions.
6. Video compositor — layered assembly of voice, music, ambience, SFX, and animation.
7. Multiplatform export — local video/audio outputs first, with future platform-specific adapters.

## Current status

Fabuloom Core V0.1 now provides dependency-free, versioned Python contracts for projects, books, chapters, scenes, characters, narrators, dialogue, audio segments, animation events, timelines, and audio manifests. It also includes a provider-neutral TTS interface and a deterministic simulated provider for tests. The V0.2 integration branch adds an optional, lazy Kokoro PT-BR provider; it does not add model weights to this repository.

The V0.3 branch adds a local Canvas character-stage demonstrator with real
manifest-backed playback and amplitude-driven mouth motion. Mission 006.1
adds the responsive Studio UI foundation around that stage: a local-only shell,
timeline, inspector, accessible transport controls, and original SVG branding.
Piper, Animus, full editor, MP4 export, and cinematic animation are not
implemented yet.

## Technology direction

- Python for audio generation and processing.
- Kokoro for the first optional TTS integration.
- Piper for offline fallback.
- TypeScript for the future interface.
- FFmpeg for media export.
- SQLite for local project data.

All dependencies and model licenses must be reviewed before integration. Large models, virtual environments, generated media, private context, and temporary files remain outside this public repository.

## License

Original Fabuloom Studio code is intended to use the MIT License. This choice applies only to original project material; third-party code, models, voices, and media remain subject to their own licenses.

See `docs/KOKORO-INTEGRATION.md` for the optional provider, capability limits, offline demonstration, and third-party licensing notes. See the contribution, security, architecture, and getting-started documents for project boundaries.

Core contract details and invariants are documented in `docs/CONTRACTS.md`. Test instructions are in `docs/TESTING.md`.
