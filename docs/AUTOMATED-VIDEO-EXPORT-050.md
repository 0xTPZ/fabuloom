# Automated Video Export Gate — Mission 050

## Harness

The existing Playwright harness was extended; no second infrastructure was created. Use:

```powershell
cd tools/e2e
npm run test:e2e:export
```

The command uses a disposable workspace, dedicated port, isolated server process, fresh browser context, screenshots, structured logs, `result.json`, and `report.html`. It does not touch production workspaces or global Windows settings.

## Flow executed

The real `studio.html` interface successfully performed project creation, original roteiro, scene generation, PNG import, camera movement, Ponto selection, `smile` expression selection, project save, server restart, fresh browser context, project reopen, and character/scenes recovery.

The export mode then clicked the real “Gerar narração Santa” button. The application reported `pm_santa · indisponível` in the isolated test workspace. Because narration is a prerequisite for the current export path, the gate stopped without creating or fabricating an MP4.

## Classification

- Project and character UI flow: **PASS**.
- Project/scene/image/movement recovery: **PASS**.
- Real narration through Studio button: **BLOCKED** — Kokoro/model/voice was not available to the isolated test workspace; no heavy download or synthesis workaround was performed.
- MP4 export through the real button: **NOT TESTED** — correctly not attempted after the prerequisite failed.
- FFprobe, H.264/AAC, FFmpeg decode, audio/video duration comparison: **NOT TESTED** — no output existed to validate.
- Native Windows file dialog: **NOT TESTED**; Playwright `setInputFiles()` only validates the HTML input.
- Canvas × FFmpeg parity: **NOT TESTED** in this export gate.

Overall result: **BLOCKED** for the audiovisual export gate, with the exact blocker exposed by the UI. The quick E2E project/character suite remains separate and passes.

## Evidence

Latest export evidence directory: `C:\Users\User\AppData\Local\Temp\fabuloom-e2e-047-UaADC0`.

The structured result records the blocked narration state and contains no fabricated media path. The prior successful project/character run produced the corresponding screenshots and restoration evidence.

## Remaining work

Provide a documented, independently available Kokoro/model fixture or a supported short WAV narration-import path in the Studio. Then rerun `test:e2e:export` to exercise the real export button and FFprobe/FFmpeg validation. This mission does not change the audiovisual engine or redistribute models/voices.
