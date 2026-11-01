# Fabuloom E2E 047

This isolated Playwright harness starts `frontend/server.py` on port 18765 with a disposable `FABULOOM_WORKSPACE_ROOT`, uses a fresh browser context, captures screenshots, and writes `result.json` under a temporary evidence directory. It prefers the locally installed Microsoft Edge executable and does not change global browser installations.

Run from this directory:

```powershell
npm install
npm test
npm run test:e2e:export
```

`test:e2e:export` runs the heavier real-audio/MP4 gate separately; it is not part of the quick interface regression.

The harness is intentionally honest about current limits: project creation is still prepared through the existing local API because the Character Stage page does not expose the project-creation shell, and native Windows file-dialog behavior is not the same as Playwright `setInputFiles()`.
