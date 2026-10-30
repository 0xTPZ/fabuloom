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
- Rig-faithful video export — transparent deterministic browser capture,
  measured RMS mouth motion, per-segment captions and FFmpeg composition
  validated with Santa V2 in Mission 010.2. Multi-scene composition and
  richer camera direction remain future work.
- Santa V3 character scene — full-body joint layers, deterministic continuous
  prop interaction, measured `pm_santa` narration and real-engine MP4 export
  implemented in Mission 011. General scene authoring and final art remain
  future work.
- Santa V4 cartoon refinement — original rounded rig-ready layers, preserved
  V3 compatibility, browser-stage selection and real-engine MP4 comparison
  implemented in Mission 011.1. Final painted art, broader gesture authoring
  and human visual approval remain future work.
- Santa V5 production rig — higher-fidelity original transparent character
  pieces, fine-grained joint hierarchy, Stage selection and deterministic
  H.264/AAC demonstration implemented in Mission 012.1. Human review remains
  necessary for final cinematic polish; phonetic alignment and a general scene
  editor remain future work.
- Visual Inspector V1 — deterministic loopback captures, versioned frame
  evidence, landmark/joint/motion diagnostics, tolerant PNG comparisons and a
  read-only DEV page implemented in Mission 013. Automatic art correction,
  external vision models and final artistic approval remain future work.
- Visual Inspector V1.1 — controlled known-defect fixtures, alpha-footprint
  join checks, side-aware crossing checks, IDLE/WAVE/POINT temporal coverage,
  evidence overlays and separate technical/artistic references implemented in
  Mission 013.1. Full per-pixel joint masks, external vision execution and
  human artistic approval remain future work.
- Visual Inspector V1.2 — historical PNG/MP4 evidence bank, blind real-image
  evaluation, pixel masks/components/contour measurements, isolated historical
  correction replay and provider-neutral multimodal contract implemented in
  Mission 013.2. Opaque-video segmentation remains heuristic; external model
  execution and final artistic approval remain future work.

- Visual QA Gate V1.3 — deterministic smart frame plans, standard evidence
  packages, technical gate status, bounded assisted correction with safe
  rollback, historical Santa V5 replay and a DEV review page implemented in
  Mission 013.3. Multimodal analysis remains explicitly unavailable/offline;
  human artistic approval remains required.
- Santa V5 visual quality recovery — Mission 014 audited the real 1080×1920
  production captures, corrected named-clip composition drift and left-arm
  POINT_AT clipping, added before/after and close-up evidence, and regenerated
  the WAVE_HELLO and bilateral POINT_AT H.264 demos. Artistic approval remains
  human; mesh deformation and a general scene editor remain future work.
- Anatomy-first rig rebuild — Mission 015 added a reversible Santa V5
  reconstructed-assets experiment with independent cuff/hand nodes, alpha
  metrics, boot-scale comparison and same-renderer evidence. Godot/Inochi2D
  mesh deformation remains explicitly unexecuted until a permitted local tool
  is available; the approved V5 pack remains unchanged.
- Mesh Rig Lab V1 — Mission 016 executed the first isolated weighted-mesh proof
  with Godot 4.7.2 Compatibility/OpenGL. The lab uses a copied Santa V5 arm
  texture, a five-bone `Skeleton2D` hierarchy, 96 weighted `Polygon2D` tiles,
  five pose captures, transparent PNG output and a deterministic six-second
  frame sequence. The current Canvas renderer remains production; the mesh
  lab is experimental and requires human visual review before any migration.

## Later

- Animus integration after its public boundary and license are verified.
- Full video compositor.
- Multiplatform export adapters.
- Word and phoneme alignment where the selected provider supports reliable timing.

No roadmap item is considered implemented until its tests and documentation are updated.
