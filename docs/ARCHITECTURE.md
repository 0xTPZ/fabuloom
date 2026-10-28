# Architecture

## Boundary

Fabuloom Studio is a new project. TopazioReader and Card Game Studio may inform requirements, but they are not runtime dependencies and are not modified by this project.

## Proposed layers

```text
Project / Script
        |
        v
  Scene Director ---- Character Engine
        |                    |
        v                    v
  Audio Timeline <------ TTS Providers
        |
        v
  Video Compositor
        |
        v
  Export Adapters
```

## V0.1 implementation

The first implementation lives in `src/fabuloom_core` and is intentionally independent of all external engines. Domain models use stable IDs and `format_version: "0.1.0"`. JSON serialization is explicit and rejects unsupported minor versions.

`TTSProvider` is a provider-neutral protocol. `SimulatedTTSProvider` remains the dependency-free provider for tests. The optional `KokoroTTSProvider` is lazy, loads one PT-BR pipeline on demand, reuses it, writes measured WAV output, and releases it through `close()`.

Narration preparation is separated from the provider. `segment_text` creates
stable ordered source segments from paragraphs and sentence punctuation, with
explicit pause policy. `synthesize_narration` turns each segment into a WAV
and composes the existing `AudioManifest`; timeline durations come from the
measured files, while word/phoneme/viseme timestamps remain empty when the
provider does not supply them.

### Character stage V0.3

The local `frontend` stage separates `AudioTimelinePlayer`, `PlaybackClock`,
RMS analysis, `CharacterRig`, Canvas rendering, manifest loading, and UI
controls. The rig consumes a normalized speech amplitude signal and does not
import Kokoro or Animus. Pauses produce zero speech amplitude while breathing,
blinking, and subtle head motion continue. The amplitude path is explicitly a
visual approximation, not phonetic alignment.

The synchronization layer stores integer milliseconds. Audio segments cannot overlap on the same track. Animation overlap is policy-based: gestures, expressions, and visemes may overlap; structural events such as page changes and camera cuts may not overlap on the same track.

### Studio UI foundation 006.1

The frontend shell is organized into independent visual responsibilities:

```text
App shell
  ├─ Sidebar / project context
  ├─ Topbar / local status
  └─ Studio workspace
       ├─ Stage preview + transport
       ├─ Timeline rows from the audio manifest
       └─ Inspector (character, voice, diagnostics)
```

The UI reads the existing manifest and player contracts; it does not call
Kokoro, Animus, or any private project directly. Design tokens live in
`frontend/style.css`, and the shell uses CSS grid with responsive breakpoints
for desktop, tablet, and narrow mobile screens. `frontend/assets/logo.svg` and
`frontend/assets/favicon.svg` are original, lightweight vector assets.

The sidebar collapses behind an accessible mobile menu below 920px. Transport
buttons, the narration select, the seek slider, diagnostics disclosure, and
navigation affordances retain labels and visible keyboard focus. The UI keeps
the audio caveat explicit: RMS amplitude drives a visual mouth approximation;
it is not word, phoneme, or viseme alignment.

### Script editor

The editor will represent books, chapters, scenes, speakers, narration, direction notes, and reusable character references. The first data model should be serializable and versioned before a rich UI is built.

### TTS providers

The provider contract isolates text normalization, voice selection, synthesis, duration metadata, and errors. Kokoro is the first integrated provider and Piper remains an offline fallback candidate. The Kokoro adapter currently supports PT-BR voices `pf_dora`, `pm_alex`, and `pm_santa`, plus speed. It rejects unsupported pitch/volume/extras rather than silently ignoring them. Provider-specific models and environments stay outside the public repository.

### Character engine

Characters should be described by stable identities and backend-neutral actions. A future Animus adapter may implement one backend, but Fabuloom must not import Animus internals directly.

### Synchronization

Audio segments should produce a manifest containing stable IDs, source text, voice ID, audio path, duration, and optional word/phoneme timing. Timing must be generated from actual media, not estimated only from character count.

### Composition and export

The compositor should combine voice, music, ambience, SFX, and animation through an explicit timeline. FFmpeg is the initial export boundary. Exporters should be deterministic and keep source assets unchanged.

## Storage

SQLite is the planned local index for projects and metadata. Large media and model files should be stored in project-local managed locations under the isolated Fabuloom workspace, with manifests and checksums rather than binary assets in Git.

## License boundary

Only original Fabuloom code is covered by the project MIT license. Kokoro model/package, runtime dependencies, voices, and generated media remain subject to their own licenses. Every external integration needs a license/provenance record before distribution; see `docs/KOKORO-INTEGRATION.md`.
