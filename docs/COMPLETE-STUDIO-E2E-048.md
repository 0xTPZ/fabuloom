# Complete Studio E2E — Mission 048

## Surfaces

The repository has two browser surfaces: `studio.html` is the production project workflow (`studio-shell.mjs`), while `index.html` is the Character Stage/legacy visual surface used by the Mission 047 pack test. The harness now exercises both boundaries honestly; it does not pretend that Character Stage controls are the production project editor.

## Latest run

Command: `cd tools/e2e; npm test`

Result: **PARTIAL**.

PASS AUTOMÁTICO in the real `studio.html` surface:

- Created `E2E-Ponto` through the visible New Project dialog.
- Entered an original script through the visible editor.
- Saved the script and generated a scene.
- Imported a PNG with Playwright `setInputFiles()` through the scene control.
- Changed the scene camera to Zoom and saved it.
- Closed the browser context, restarted the isolated server, opened a new context, reopened the project, and recovered the scene text and image.
- Generated fresh screenshots, structured logs, `result.json`, and `report.html` in a disposable evidence directory.

PARTIAL / NOT TESTED:

- Ponto library association in `studio.html`: now covered by Mission 049's unified library flow; this document remains the baseline for the pre-integration run.
- Project-level pack and expression restoration: covered by Mission 049's expanded harness.
- MP4 export, FFprobe, and complete FFmpeg decode in this run: not tested because the production flow requires narration/audio and the harness deliberately avoids substituting direct API calls.
- Native Windows file dialog: not tested. Playwright `setInputFiles()` validates the HTML control, not the native dialog.
- Canvas × FFmpeg capture and metrics: not tested in this run; no parity PASS is claimed.
- Real Kokoro synthesis: not run in every regression.

## Evidence and isolation

The latest successful run was stored under `C:\Users\User\AppData\Local\Temp\fabuloom-e2e-047-FgHs1B` during execution. The harness uses a unique temporary workspace, port `18765`, a fresh browser context, and only its own server process. It does not touch `E:\Fabuloom\studio` or production projects.

## Regression

- Python: `48 passed, 1 skipped`.
- Node: `160 passed`.
- Playwright: real Studio project create/save/reopen/image/movement flow PASS; overall mission PARTIAL due the explicit missing character-pack integration and audiovisual/visual gates.

## Remaining work

To reach PASS, expose the character-pack reference/selection in `studio.html`, connect it to the persisted project manifest, then add a fixture-audio export flow and a separate visual Canvas × FFmpeg job. These are product/integration gaps, not reasons to weaken this harness's classifications.
