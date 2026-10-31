# Fabuloom Studio UI Reforge V1

Mission 021 consolidates the existing Fabuloom production paths behind a
local-first Studio shell. It does not create a new video editor, a second
character renderer or a new export pipeline.

## Audit matrix

| Resource | Current role | Classification | Primary entry |
| --- | --- | --- | --- |
| Santa V5 + Narrator Mode V1.4 | Facial narrator, RMS mouth, measured timeline | Stable for current use | Studio Preview / Narrators |
| Kokoro manifests and WAVs | Local narration playback | Stable for current use | Studio Audio / Preview |
| Canvas + FFmpeg profiles | Deterministic production/export boundary | Stable for current use | Studio Scenes / Export |
| Vertical Story and Official Promo profiles | Reproducible demonstrations | Stable for current use | Studio Projects / Scenes |
| `frontend/index.html` Character Stage | Historical full-body stage | Legacy reference | Area DEV |
| Face lab, Santa galleries, Visual Inspector and QA | Calibration and evidence | Experimental / diagnostic | Area DEV |
| Roteiro and Cenas editing | Local draft and profile inspection | Experimental | Studio Roteiro / Cenas |
| New project creation and full editor | Not implemented in this mission | Incomplete | Intentionally disabled |

The audit found that the old root page mixed Lia, Ari, Santa V3, Santa V4,
Santa V5 and narrator packs in one experimental selector. Narrator Mode was
the more current facial composition, but it was only reachable as a separate
page. The new shell makes Santa V5 the main reference and moves legacy pages
behind an explicit DEV boundary.

## Official shell

The loopback server now opens `studio.html` at `/`. The shell is implemented by
`frontend/studio.html`, `frontend/studio.css` and `frontend/src/studio-shell.mjs`.
It provides:

- Dashboard with project state and local component health;
- project and export views that link to files actually present in the
  workspace;
- a local script draft saved in browser storage, clearly marked experimental;
- profile-backed scene inspection using the real Official Promo and Vertical
  Story JSON files;
- official narrator selection with Santa V5 as the primary reference;
- audio status showing Kokoro voice identity, measured timing and the explicit
  absence of phoneme/viseme timing;
- persistent preview using `NarratorAvatarRenderer`,
  `NarratorSceneRenderer` and `AudioTimelinePlayer`;
- export links for existing verified MP4 files, without pretending to start a
  render job that the UI does not yet expose;
- a DEV area linking the preserved Character Stage, Narrator Mode, face lab,
  Visual Inspector and Visual QA pages.

The preview is intentionally honest about its boundary: it shares the current
Narrator Mode renderer and audio clock, but it does not claim to be a complete
real-time replacement for offline FFmpeg export. The current browser preview
uses the available `pm_santa` demonstration manifest by default and can switch
to the catalogued Dora and Alex manifests when present locally.

## Compatibility and preservation

The change is additive. Existing capture pages, profile contracts, Santa V5
assets, Kokoro adapters, export examples and diagnostic pages remain intact.
The old Character Stage remains available at `/index.html` and is labelled as a
legacy reference in the new Area DEV. No external project, model weight,
credential or generated production media is copied into the public repository.

The new `fabuloom.studio-ui/0.1` metadata contract contains only navigation,
narrator, profile and export catalog information. It does not replace the
versioned audio, character, timeline or production-profile contracts.

## Validation

The UI was inspected in a real loopback browser at desktop resolution. The
Dashboard loaded the local `pm_santa` manifest with 11 segments and 1:02 of
measured audio. The Narrators view showed Santa V5 as the production reference;
the Scenes view read six Official Promo scenes and five Vertical Story scenes;
the DEV view exposed the preserved experimental pages.

The desktop and responsive evidence captures are stored outside Git:

- `E:\Fabuloom\workspace\exports\ui-reforge-v1\evidence\studio-dashboard-desktop.png`;
- `E:\Fabuloom\workspace\exports\ui-reforge-v1\evidence\studio-dashboard-mobile.png`.

The mobile breakpoint uses a single-column layout, fixed overflow containment,
and a collapsible navigation. Browser/headless captures can show an interim
loading state while local audio is decoding; the functional browser check waits
for the manifest and confirms the populated timeline before review.

Automated coverage includes the new Studio UI metadata contract and all
previous frontend/Python suites. Human visual review remains required for the
final artistic judgment.

## Known limits and next priorities

- The shell does not yet create or rename project files.
- Roteiro edits are local browser drafts, not persisted project contracts.
- Scene editing and export-job controls remain read-only views of existing
  capabilities.
- Narrator Mode currently has one primary facial composition; full-body
  Character Stage variants remain DEV references.
- Real-time preview and offline export share the narrator renderer, but the
  complete multi-scene compositor is still an offline profile/FFmpeg path.

Next priorities are to persist the existing project contract behind the shell,
add safe profile selection, expose a real export-job status endpoint, and only
then consider deeper scene editing.
