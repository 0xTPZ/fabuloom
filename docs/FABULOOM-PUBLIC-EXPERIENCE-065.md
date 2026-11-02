# Fabuloom Alpha Public Experience Finalization — Mission 065

Status: **PASS_WITH_WARNINGS** for the neutral first-run/public presentation. The audiovisual and visual-parity limitations remain documented; Canvas × FFmpeg remains **PARTIAL**.

## State and interfaces

- Alpha branch: `release/fabuloom-alpha-preparation`
- Alpha technical head: `17d52fd` (Studio first-run fix; report commit follows)
- Launcher target: `http://127.0.0.1:8765/studio.html`
- `frontend/studio.html` is the primary Studio opened by the Windows launcher. `frontend/index.html` is the preserved Character Stage legacy interface.
- `E:\Fabuloom\studio` was not modified.
- PR #33 remains Draft and PR #49 remains Draft; no merge, tag, release or Pages publication was performed.

## Primary Studio first run

The primary Studio now starts a fresh session with the neutral MIT-licensed Ponto community pack on the real canvas. It does not load or synthesize a proprietary narrator automatically, and it clearly shows that Ponto has no voice included. The dashboard copy was changed at runtime to describe the neutral first video path. Existing projects remain authoritative: `loadProject()` restores persisted character-pack references and the missing-pack path reports an error without replacing or deleting the reference. Santa V5 narrator loading remains available when explicitly selected or when a historical project contains it.

The first-run fix is in `frontend/src/studio-shell.mjs`, commit `17d52fd`. The legacy Character Stage default was already neutralized in `08e8e86`; this mission corrected the actual launcher target.

## Real browser evidence

Evidence was captured from the real local Studio using Microsoft Edge and the loopback server, not mockups:

- `C:\Users\User\AppData\Local\Temp\fabuloom-public-065\studio-clean-dashboard.png` — clean candidate dashboard, Ponto on canvas, 1366×768.
- `C:\Users\User\AppData\Local\Temp\fabuloom-public-065\studio-clean-mobile.png` — clean candidate dashboard, 390×844.
- Additional real Studio captures: `studio-scenes.png` and `studio-preview.png` in the same evidence directory.

The public screenshots selected for PR #49 contain only the neutral Ponto experience, local UI and original demonstration text. The Narrators route was not published because it intentionally exposes historical character references and is unsuitable for neutral public presentation.

## Landing page PR #49

Commit `5177aa6` adds a semantic “Real Studio · Ponto demo” section with three responsive images, localized English/PT-BR labels and alt text, lazy loading, and no external dependencies. The earlier bilingual language module remains active, including browser-language default and safe preference persistence. Landing validation passed with `node --check docs/site/app.js`, `git diff --check`, and real Edge captures at 1366×768 and 390×844. The required 1920×1080, 768×1024 and 320×568 matrix remains a documentation warning rather than an unverified PASS claim.

## Clean distribution audit

The 700-file Mission 064 count was not a valid clean distribution: it included Topazio narrator directories, `fantasy-narrator` assets, caches and Playwright `node_modules` because the earlier `robocopy` exclusions were not applied as intended. A fresh 065 copy was rebuilt with absolute directory exclusions and then audited.

- ZIP: `E:\Fabuloom\alpha-testers\fabuloom-alpha-0.1.0-source-only-065.zip`
- Files: 330
- ZIP SHA-256: `6EF3ECEF36EF4A92859CD3EBAB85023AA441B64ABBE3457B41DBB4778D8C0900`
- Manifest: `E:\Fabuloom\alpha-testers\MANIFEST-065.json`
- Manifest SHA-256: `398ADFF647B52EFFDA6EF1843F7612A8A6C1EE7E2CA6C67F6E1C613C4191E19C`
- Clean copy: `C:\Users\User\AppData\Local\Temp\fabuloom-clean-065-i`

The audited candidate contains no Topazio narrator assets, fantasy narrator assets, narrator-mode asset directory, `node_modules`, virtual environment, workspace, cache or Python bytecode. It retains the neutral community pack and the contract module required by the public layered-character tests. The manifest records every relative path, byte count and SHA-256.

## Validation

- Root Python suite: **48 passed, 1 skipped, 22 subtests passed**.
- Clean-copy public Node suite: **128 passed, 0 failed**.
- Clean-copy initial run: real Edge screenshot shows Ponto without proprietary assets.
- Full Kokoro/MP4 export through the clean candidate: **not re-run in this mission** because the clean candidate intentionally has no model/runtime and no new heavy synthesis was authorized; Mission 051.1 remains the last real export evidence.
- Canvas × FFmpeg gate remains **PARTIAL**, without reclassification.

## Decision

**PASS_WITH_WARNINGS** for the integrated public experience and clean source candidate. **GO_WITH_LIMITATIONS for owner review**, not unrestricted publication. Remaining gates are the owner’s approval, external Kokoro/FFmpeg setup, the known visual-parity limitation, and human validation of the native Windows selector. No proprietary assets or production files were published.
