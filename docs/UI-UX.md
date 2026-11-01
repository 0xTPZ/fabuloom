# Studio UI/UX foundation

Mission 006.1 establishes the first reusable interface shell for Fabuloom
Studio without changing the audio player, character rig, or manifest
contracts.

## Visual system

The interface uses a deep blue workspace background, cool blue interaction
states, violet character accents, and restrained gold provider accents. The
tokens are CSS custom properties in `frontend/style.css`; components use the
tokens rather than hard-coded per-panel themes. Panels have a low-contrast
border, compact typography, and clear grouping so the stage remains the focus.

## Component boundaries

- `sidebar`: project context, local-only status, and navigation placeholders;
- `topbar`: breadcrumb, save state, local badge, and profile affordance;
- `stage-panel`: Canvas preview, live state, and character presence;
- `timeline-panel`: ordered manifest segments with measured time ranges;
- `transport-panel`: Play, Pause, Stop, seek, and playback status;
- `inspector-column`: character state, voice metadata, and diagnostics;
- `frontend/src/main.ts`: DOM binding only; audio and character behavior stay
  in their existing modules.

The disabled navigation actions are intentionally presentational in V0.3. No
placeholder action pretends to create or edit project data.

## Responsive behavior

The layout is checked at 1920x1080, 1366x768, 768x1024, 390x844, and
360x800. At desktop widths the stage and inspector share a grid. At tablet
widths the inspector moves below the stage. At mobile widths the inspector
stacks, the sidebar becomes an off-canvas menu, and the timeline rows preserve
their text/time hierarchy without horizontal page overflow.

## Accessibility and local boundary

The document has a Portuguese-Brazilian language declaration, descriptive
landmarks, labels for controls, a real details disclosure for diagnostics,
keyboard-visible focus, an Escape path for the mobile menu, and a reduced
motion preference. Files remain local: the server binds to loopback and the
interface exposes no absolute filesystem paths.

The mouth continues to use real-time RMS amplitude. The interface labels this
as an approximation and never presents it as phonetic, word, or viseme timing.
