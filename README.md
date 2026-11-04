# Fabuloom Studio

Fabuloom Studio is an open-source foundation for turning stories and scripts into narrated videos with animated characters.

The product is designed as one local application with a shared engine:
Desktop, headless CLI, loopback API, browser views and the local MCP adapter use
the same projects, asset catalog, timelines and jobs. Private creative
libraries remain configurable external roots and are never bundled into the
public source tree.

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
Mission 007A.1 adds an optional validated layered-character renderer and an
original adult fantasy narrator pack while preserving the geometric rig.
Mission 007A.2 refines Ari into a 16-node anatomical rig with independent
head, face, hair, arms, hands and accessory transforms; the torso remains the
breathing root and is not rotated by head motion.
Mission 009 adds three official demonstrator narrators — Dora (`pf_dora`),
Santa (`pm_santa`), and Alex (`pm_alex`) — using a shared original
Topazioverse-inspired navy, pale-blue, and gold uniform language. They are
simple, reusable layered packs for the current Character Stage, not final art;
the character editor and external pack import remain deferred.
Mission 010 now adds the first deterministic local text-to-MP4 demonstration:
the original story *A Última Luz* is narrated by Dora with real Kokoro
`pf_dora` audio, measured segment captions, an RMS-driven mouth approximation,
and a 1080x1920 H.264/AAC export. This is a reusable proof-of-pipeline, not
the final editor, compositor, or cinematic animation system. Piper, Animus,
the full editor, word/phoneme alignment, and production export tooling remain
future work.
Mission 010.1 corrects the visual direction for future exports: the official
Dora, Santa and Alex V2 packs now use an animation-ready 16-node hierarchy with
independent body, head, face, hair, arm, hand and accessory layers. The Stage
and the video exporter share the same rig. Mission 010.2 validates the bridge
with Santa V2, real Kokoro `pm_santa` audio, transparent deterministic Canvas
frames, measured segment captions, and a 1080x1920 H.264/AAC MP4. The original
portrait export remains preserved as a compatibility reference.
Mission 011 adds Santa V3, a full-body original technical character pack with
independent pelvis, head, arms, hands, legs and feet. `SantaV3Rig` drives a
continuous walk/sit/reach/drink/read/explain sequence, while
`SantaV3SceneRenderer` reuses the layered renderer for deterministic 1080x1920
browser capture. A real Kokoro `pm_santa` narration, RMS mouth response and
the same rig produce `workspace\\exports\\videos\\fabuloom-santa-v3.mp4`.
The result is a reusable animation demonstrator; final painted art, phonetic
alignment and a general scene editor remain future work.
Mission 011.1 adds Santa V4 as an independent cartoon-art pack. It preserves
Santa V3 and reuses its deterministic skeleton, scene choreography, Kokoro
`pm_santa` manifest, RMS mouth signal and FFmpeg export boundary. V4 replaces
the geometric-looking layer artwork with original rounded SVG layers for the
head, gray hair, glasses, beard, uniform, limbs and hands. The V4 demonstration
is generated by `examples/santa_v4_video_demo.py`; it reuses the measured V3
audio and does not publish model weights or personal media.
Mission 012 begins Santa V5 art production with an original, higher-fidelity
cartoon direction based on the approved identity reference. Mission 012.1
finishes the first rig pass without creating a new animation engine: neck,
head, hair, facial overlays, upper/lower limbs, hands and feet are separate
local PNG layers under `frontend/assets/characters/topazio-narrators-v5/santa/`.
`SantaV5Rig` and `SantaV5SceneRenderer` reuse the deterministic V3 scene and
the same browser capture boundary. The resulting measured `pm_santa` demo is
exported to `workspace\\exports\\videos\\fabuloom-santa-v5.mp4`; generated
media stays outside Git. RMS still drives an expressive mouth approximation,
not phonetic or viseme alignment.

Mission 016 adds an isolated executable mesh-rig lab for the Santa V5 right arm.
It uses a copied production texture, a Godot `Skeleton2D`/`Bone2D` hierarchy,
96 weighted `Polygon2D` tiles and deterministic pose captures. The proof
produces rest, elbow, raised-hand and pointing frames plus a six-second MP4 from
the same weighted mesh. The production Canvas renderer and official Santa V5
assets remain unchanged; this is a measured deformation alternative, not a
merge or an artistic final approval. See `docs/MESH-RIG-LAB.md`.

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

Mission 017 adds Narrator Mode V1: a separate horizontal storyteller scene
with an original fantasy archive SVG, a circular Santa V5 facial avatar, real
Kokoro `pm_santa` audio, segment captions and deterministic 1920x1080 H.264/AAC
export. The mode reuses facial layers and RMS timing without loading the
full-body Stage or inventing phonetic timestamps. See `docs/NARRATOR-MODE.md`.

Mission 017.1 corrects the Narrator Mode facial composition without changing
the approved Santa V5 assets. Inspection showed that the existing mouth PNGs
already included beard and moustache, so the corrected experimental pack uses a
single lower-face plate, explicit RMS mouth states, a shared `NarratorFacialRig`
draw path, and a tighter circular crop. It adds the browser close-up lab at
`frontend/narrator-face-lab.html`, a reusable no-synthesis correction exporter,
and real before/after visual evidence. Artistic approval remains human and the
official pack remains preserved.

Core contract details and invariants are documented in `docs/CONTRACTS.md`. Test instructions are in `docs/TESTING.md`.

Mission 017.2 finalizes the Narrator Mode avatar framing. Real alpha-bound
measurement replaced the clipped V1.1 source window with a bounded 590×590
crop at `{ x: 245, y: 35 }` and an explicit normalized face safe area. The
browser lab exposes offset, zoom, safe-area and reset controls through the same
renderer used by export. The no-synthesis V1.2 MP4 and visual evidence remain
outside Git under `workspace\exports\videos`; artistic approval remains human.

Mission 017.3 aligns the Narrator Mode face in a measured `head-local-v1`
coordinate system. The derived pack records facial landmarks and maps the real
alpha bounds of the official eyes, brows, glasses, hair and lower-face PNGs to
explicit targets instead of positioning full transparent bitmap rectangles.
The lab now shows grid, landmarks, alpha targets, pivots, static reference and
layer toggles through the shared renderer. The no-synthesis V1.3 MP4 and
before/after evidence remain outside Git under `workspace\exports\videos`;
technical checks do not constitute artistic approval.

Mission 017.4 proves and corrects the lower-face anatomy boundary. `neck.png`
and `head-clean.png` both paint a neck/collar assembly; the derived Narrator
Mode pack now preserves the structural neck node but hides only its redundant
pixels, leaving the visible collar owned by `head-clean.png`. The official
Santa V5 assets and V1.3 facial alignment remain unchanged. The no-synthesis
V1.4 MP4 and before/after, enlarged transition, asset and color-map evidence
are generated under `workspace\exports\videos`; artistic approval remains
human.

Mission 018 adds the reproducible Cinematic Story Test V1. It reuses the
Narrator Mode V1.4 avatar, real Kokoro `pm_santa` audio, measured segment
timing, three original scene backgrounds, deterministic Canvas camera effects,
and FFmpeg export. Generated media remains outside Git under
`workspace\exports`; see `docs/CINEMATIC-STORY-TEST.md` for reproduction and
the FilmCraft/EffectCraft audit boundary.

Mission 018.1 fixes the cinematic lip-sync regression: the capture now passes
the measured WAV sample rate into the absolute-time RMS reader. The corrected
pipeline records real RMS/mouth-state diagnostics, generates a V1/V1.1 facial
comparison and reuses the Mission 018 audio without synthesis. See
`docs/CINEMATIC-STORY-TEST.md` for the evidence command.

Mission 019 adds a reusable vertical cinematic-story profile and export path.
It uses original five-scene 9:16 artwork, real Kokoro `pm_santa` narration,
an original deterministic local instrumental bed, measured segment captions,
the Narrator Mode V1.4 avatar and the existing FFmpeg boundary. The reference
export is `fabuloom-vertical-story-test-v1.mp4` under the workspace exports;
generated media remains outside Git. See
`docs/VERTICAL-CINEMATIC-STORY.md` for reproduction and Visual Inspector
evidence. The profile explicitly records that word/phoneme/viseme timing is not
available and that final artistic review remains human.

Mission 020 adds the first official Fabuloom Studio promo pipeline. It uses the
real local Character Stage capture, Kokoro `pm_santa`, six measured scenes,
original procedural music/SFX and two vertical exports: a main version with
music and a TikTok-ready version without music. The generated MP4s and
evidence remain outside Git under `workspace\exports`. See
`docs/OFFICIAL-PROMO.md` for reproduction, claims, licensing boundaries and
the evidence-only inspection command.

Mission 021 adds the official Fabuloom Studio UI shell. The loopback server now
opens a local-first Dashboard with project, script, scenes, narrator, audio,
preview and export views. Santa V5 Narrator Mode V1.4 is the main narrator
reference, while the historical Character Stage and diagnostic laboratories
remain available under an explicit DEV area. See `docs/UI-REFORGE.md` for the
audit matrix, compatibility boundary, captures and known limits.

Mission 022 audits the user journey and clean installation. It records that
the default `main` branch is still the Core foundation, while the UI shell is
on `mission-021-ui-reforge`; it also documents the missing project/editor/job
workflow, the current Dora/Alex integration boundary, and the roadmap for
Narrator Characters, Character Creator V2 and Production Studio. The loopback
server now supports explicit portable `FABULOOM_WORKSPACE_ROOT` and
`FABULOOM_EXPORT_ROOT` values. See `docs/AUDITORIA_GERAL.md` and the linked
mission reports before treating the project as installable.

Mission 023 connects the official narrator trio to the same visual and audio
selection path in Studio. Santa V5 remains the approved production reference;
Dora (`pf_dora`) and Alex (`pm_alex`) now load their own V2 technical facial
packs rather than reusing Santa's face. The selection is validated against the
measured local manifest and the renderer reports `AWAITING_ART_APPROVAL` until
the owner approves the new art. See `docs/OFFICIAL-NARRATORS-V1.md` and
`frontend/official-narrators-board.html`.

Mission 027 produces the Chapter 2 cinematic episode from the exact DOCX
boundary `Capítulo 2 — O minotauro e a cicatriz` (paragraphs 25–46). It uses
real Kokoro `pm_santa` timing, 16 environment-only story plans, the official
`santa-library-topazioverse-v1` scene registry, and the approved Santa V5
medallion in every scene. Character Registry approval is enforced at runtime;
the seven guardian concepts remain `DRAFT` and cannot enter production. The
MP4 and evidence remain outside Git under
`workspace\exports\topazio-book1-capitulo2-cronicas`; see
`docs/CRONICAS-DE-TOPAZIO-027.md`.

Mission 028 produces the Chapter 3 cinematic episode from the exact DOCX
boundary `Capítulo 3 — Sete caminhos para Gaia` (paragraphs 48–105; separator
106; next chapter heading 107). It uses real Kokoro `pm_santa` timing, 20
environment-only story plans, the official `santa-library-topazioverse-v1`
scene registry and the approved Santa V5 medallion. The seven guardian concepts
remain `DRAFT` and are blocked by the runtime policy. The MP4, plates and
reports remain outside Git under
`workspace\exports\topazio-book1-capitulo3-cronicas`; see
`docs/CRONICAS-DE-TOPAZIO-028.md`.

Mission 029 produces the Chapter 4 cinematic episode from the exact DOCX
boundary `Capítulo 4 — O círculo dos ausentes` (title paragraph 107; narrative
paragraphs 108–178; separator 179; next chapter heading 180). It uses 153
measured Kokoro `pm_santa` segments, 20 environment-only story plans, the
official `santa-library-topazioverse-v1` scene registry and the approved Santa
V5 medallion. Draft character identities remain blocked by policy. The MP4,
environment plates and reports remain outside Git under
`workspace\exports\topazio-book1-capitulo4-cronicas`; see
`docs/CRONICAS-DE-TOPAZIO-029.md`.

Mission 030 produces CB-001, `O Quarto Eco`, the first vertical pilot of
`Lendas e Segredos de Topázio`. It uses the exact proposed editorial text,
real Kokoro `pm_santa` timing, Santa V5 through `NarratorAvatarRenderer`,
environment-only cave/crystal plates, the original provided music with voice
ducking and a short fourth-echo reduction, measured captions, and a
deterministic 1080x1920 FFmpeg export. The story remains proposed folklore,
Draft characters are blocked, Suno commercial rights remain pending, and the
MP4/evidence stay outside Git under
`workspace\exports\cronicas-breves\cb-001-o-quarto-eco`; see
`docs/CRONICAS-BREVES-CB001.md`.

Mission 031 adds independent pipelines for CB-002, `A Sombra que Olhava para
o Sol`, and CB-003, `A Luz do Último Viajante`. Both use their exact proposed
editorial text, Kokoro `pm_santa`, Santa V5, `NarratorAvatarRenderer`,
environment-only plates, measured captions and the vertical 1080x1920 profile.
CB-002 is intentionally blocked because its required owner-provided music is
missing; no CB-001 music is substituted. CB-003 has a 52-second H.264/AAC
export with the required music, voice ducking and deterministic Canvas capture.
Both remain proposed and pending human artistic review and music-rights
confirmation. See `docs/CRONICAS-BREVES-031.md`.

Mission 032 adds an isolated Santa expressive-direction laboratory. It audits
the current Kokoro boundary, preserves `pm_santa`/`pt-BR`, and produces three
comparison profiles—neutral, curious and suspense—for the two CB-002 questions.
Only supported speed, punctuation and segmentation controls are used; pitch,
volume, SSML, emotion tags and word/phoneme/viseme timing remain unavailable.
The six WAV samples and manifests stay outside Git under
`workspace\exports\voice-lab\mission-032-santa-expressive-v1`; no approved
episode is changed. See `docs/SANTA-EXPRESSIVE-032.md`.

Mission 033 finalizes CB-002 using the existing owner-provided track
`A Sombra que Olhava para o Sol.mp3`, preserving the measured `pm_santa`
narration and concentrating the voice improvement on ducking and mix
intelligibility. The vertical MP4, SRT, manifest, storyboard, music-selection
report and voice-direction report remain outside Git pending human artistic
review and commercial-rights confirmation. See `docs/CRONICAS-BREVES-033.md`.

Mission 034 adds BT-001, `Por Trás das Crônicas de Topázio`, as a horizontal
behind-the-scenes pilot. It uses the approved editorial script, measured
Kokoro `pm_santa` narration, real Atlas Literário captures, authentic Fabuloom
Studio captures, approved CB-001/002/003 material, the official Santa V5
renderer and the owner-supplied Topázio theme with voice-priority ducking.
The 1920x1080 H.264/AAC export, SRT, manifest, storyboard and reports remain
outside Git under `workspace\exports\bastidores\bt-001-por-tras-das-cronicas`.
Commercial music rights and final human artistic approval remain pending. See
`docs/BASTIDORES-BT-001.md`.

Mission 035 adds Music Studio V1 to the main `frontend/studio.html` shell.
It catalogs owner-supplied local MP3/WAV files with FFprobe, derives a real
PCM/RMS waveform without claiming BPM or beat timing, and saves the versioned
`fabuloom.music-studio-project/0.1` contract. The shared environmental Canvas
renderer produces a full 1920x1080 video at the source duration and an
independently framed 1080x1920 Short of 15–30 seconds. This mode intentionally
contains no Santa V5, narrator, captions, lip-sync or Draft characters. Outputs
and evidence remain outside Git under `workspace\\exports\\music-studio`; see
`docs/FABULOOM-MUSIC-STUDIO-V1.md`. Commercial rights for Suno-origin music
must be confirmed before publication.

Mission 036 adds the V1.1 ambient refinement and sequential Book 1 batch runner.
It removes the artificial purple footer and repeated geometric decoration, derives
titles from each real source filename, selects a heuristic RMS short range, and
produces resumable full/vertical pairs under
`workspace\\exports\\music-studio\\book1-v11`. See
`docs/FABULOOM-MUSIC-STUDIO-V1.1.md` and the generated `INDEX.json`/`BATCH-REPORT.md`.
