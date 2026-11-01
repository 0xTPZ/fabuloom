# Fabuloom Public Experience & Alpha Readiness 063

Status: `PASS_WITH_WARNINGS` for preparation; no Alpha release or GitHub Pages publication performed.

## Initial and GitHub state

- Alpha branch HEAD: `7274bed` (`release/fabuloom-alpha-preparation`).
- PR #33 remains Draft and untouched.
- PR #47 was reviewed as documentation-only, reconciled against current `main`, and merged conventionally as merge commit `bb47a37140ae9549f1e807fdc5dda63aa7ef19dd`.
- Landing page PR #49 is open as Draft: `https://github.com/0xTPZ/fabuloom/pull/49`.
- No tag, GitHub Release, Pages activation, visibility change, or production change was performed.

The public repository description and topics were improved in Mission 062. The bilingual README is now on `main`; the Alpha disclaimer and branch distinction remain explicit.

## Public identity and landing page

The landing page is prepared in PR #49 under `docs/site/` as framework-free HTML/CSS/JavaScript. It is responsive, keyboard-readable, uses no external fonts, trackers, cookies, backend, or required network service, and includes basic description/Open Graph metadata without inventing a canonical URL.

It presents the real workflow: projects, scripts, scenes, characters, optional Kokoro narration, camera movement, preview, and FFmpeg export. The flow is shown as Story → Script → Scenes → Narration → Video. A bilingual language toggle is included.

The hero graphic is explicitly decorative CSS, not a fabricated product screenshot. No Studio screenshot was committed because the real Studio default screen currently displays Santa V5; publishing that image would violate the neutral public-asset boundary. Real isolated evidence remains outside the repository until a neutral, sanitized character-default state is approved.

Local preview was verified with a Python static server and Microsoft Edge at 1366×900. GitHub Pages was not activated.

## Launcher and first-run experience

The Windows launcher from Mission 061 remains in the Alpha branch. It resolves its own path, prefers `.venv`, falls back to local Python, validates the expected Studio page, rejects unknown listeners on port 8765, starts only its own process, opens the browser, and stops its child after Enter. No global settings or automatic installations are used.

The clean extraction smoke test found Python without a venv, started the loopback Studio, opened `http://127.0.0.1:8765/studio.html`, and shut down the child process. The separate-port conflict test rejected a non-Fabuloom HTTP listener safely.

## Clean Alpha candidate 063

- ZIP: `E:\Fabuloom\alpha-testers\fabuloom-alpha-0.1.0-source-only-063.zip`
- Clean extraction: `C:\Users\User\AppData\Local\Temp\fabuloom-clean-063-db4fc3af1e234b00a6fd4b19b1566638`
- Included files: 338
- ZIP SHA-256: `57C425BB9E3D5492721A9F01EAE0F967051608840FACE021CAA5966AABAF3F26`
- Manifest SHA-256: `7EBB149491EDF7D253548902A0941F6D0F75EE20EF827A89633C4388B5BACF9F`

The package includes public source, Ponto, launcher, documentation, licenses, scripts, and applicable tests. It excludes Topazioverse assets, models, voices, FFmpeg, caches, node_modules, virtual environments, manuscripts, credentials, production workspaces, and private context. It is separate from candidates 060 and 061.

## Validation

- Clean Python suite: **PASS** — 48 passed, 1 skipped, 22 subtests.
- Clean public Node suite: **PASS** — 128 passed, 0 failed.
- Launcher clean-copy smoke test: **PASS**.
- Launcher conflicting-port safety test: **PASS**.
- Landing page static preview: **PASS** at 1366×900 in Edge.
- Canvas × FFmpeg visual parity: **PARTIAL**, retained from prior missions.
- Real export with Kokoro/FFmpeg: previously validated in the clean candidate workflow; dependencies remain external and are not included in this package.

## Collaboration and documentation

The Alpha branch already contains installation, first-run, testing, limitations, license, security, contributing, and bug-report guidance. The public landing page links only to real repository/branch URLs. No mass issues, invitations, backlinks, trackers, or external promotion were created.

## Risks and recommendations

1. Keep PR #33 Draft until owner approval.
2. Review and merge PR #49 separately before enabling Pages.
3. Capture neutral Studio screenshots only after removing the proprietary character default from the public demonstration state, or explicitly approve a neutral capture procedure.
4. Keep Kokoro, models, voices, and FFmpeg external with their own notices.
5. Treat visual parity as `PARTIAL`; do not upgrade that gate from documentation alone.
