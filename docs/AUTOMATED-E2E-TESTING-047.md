# Automated E2E Testing — Mission 047

## Infrastructure

The permanent harness is in `tools/e2e/`. It uses a local Playwright dependency, an isolated browser context, Microsoft Edge as the existing Chromium-compatible executable, a dedicated loopback port (`18765`), and a disposable workspace supplied through `FABULOOM_WORKSPACE_ROOT`. It produces `result.json`, `report.html`, structured server logs, and screenshots in a run-specific temporary directory.

Run:

```powershell
cd tools/e2e
npm install
npm test
```

No global package, browser, or Windows configuration was changed. The first dependency installation added two packages under `tools/e2e/node_modules` only.

## Latest run

Result: **PARTIAL**.

PASS AUTOMÁTICO:

- Studio started in an isolated workspace.
- Character Library opened.
- `setInputFiles()` selected the complete `community-demo-v1` directory.
- Ponto was imported through the UI, rendered, selected, and changed to the `smile` expression.
- A fresh browser context was created without reusing localStorage/session.
- The managed pack manifest was recovered from the restarted test server.
- Screenshot and structured JSON/HTML evidence were generated under `C:\Users\User\AppData\Local\Temp\fabuloom-e2e-047-YJn0SS` for the latest successful run.

PARTIAL:

- Project creation is prepared through the existing local project endpoint because the current Character Stage shell does not expose the project-creation form used by the Studio workflow.
- The current UI/backend path confirms managed-pack recovery, but the harness does not yet assert the selected expression from a restored project manifest end-to-end.

NOT TESTED:

- Native Windows file-dialog automation. Playwright `setInputFiles()` is explicitly not evidence for the native dialog.
- PNG/JPEG scene import, export MP4, FFprobe/FFmpeg decode in this harness.
- Real Kokoro synthesis; this remains a separate opt-in heavy test.
- Canvas × FFmpeg visual parity. Existing mathematical/unit evidence remains separate and does not become an E2E PASS.

## Failure matrix

The backend regression suite covers active SVG rejection, traversal, undeclared assets, size/file limits, and project reference round-trip. Full browser-facing failure-message assertions for missing/invalid packs remain future work. A missing managed pack is designed to preserve the project reference and report reinstallation, never silently substitute Santa V5.

## Isolation

The harness starts and terminates only its own server process, uses a unique temporary workspace, and does not touch `E:\Fabuloom\studio`, production projects, or other worktrees. Failed evidence is retained by the harness for analysis.

## Regression

- Python: `48 passed, 1 skipped`
- Node: `160 passed`
- E2E: PASS for the listed automated flows; overall classification PARTIAL due to the explicit gaps above.
