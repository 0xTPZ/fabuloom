# Fabuloom Public Experience 2.0 — Mission 064

Status: **PASS_WITH_WARNINGS** for the public-experience work; **PARTIAL** for the overall Alpha because the visual Canvas × FFmpeg gate remains PARTIAL and owner review is still required.

## Scope and preservation

- Alpha branch: `release/fabuloom-alpha-preparation`
- Alpha technical head: `08e8e86`
- PR #33 remains Draft and was not merged.
- PR #49 remains Draft and was not merged; its head is `20b205f`.
- PR #47 was already merged conventionally in Mission 063; no merge was performed in this mission.
- `E:\Fabuloom\studio` was not modified.
- No release, tag, GitHub Pages publication, global installation, or proprietary asset publication was performed.

## Public landing experience

PR #49 now has a separate `docs/site/app.js` translation module. The landing page supports complete English and Brazilian Portuguese text for navigation, hero, workflow, open-source boundary, CTA, footer, document title, description and Open Graph metadata. Language preference is stored defensively in `localStorage`; browser language is used only when no preference exists. The page has semantic sections, visible keyboard focus, 44px interactive controls, responsive layout and reduced-motion rules. No external fonts, trackers, remote assets or backend are required.

Real screenshots were captured outside the repository at:

- `C:\Users\User\AppData\Local\Temp\fabuloom-public-064\landing-en.png`
- `C:\Users\User\AppData\Local\Temp\fabuloom-public-064\landing-mobile.png`

`node --check docs/site/app.js` and `git diff --check` passed. The public page uses abstract CSS artwork rather than a product screenshot, avoiding accidental publication of proprietary characters.

## First-run neutrality

The legacy Character Stage previously selected Dora whenever her assets loaded. Fresh sessions now select the neutral MIT-licensed community demo pack (Ponto) when available. Existing project-aware Studio restoration remains authoritative and was not changed; Santa V5 and existing narrator compatibility remain available. This is a minimal default-selection change in `frontend/src/main.ts` (`08e8e86`).

## Clean candidate 064

Created separately from the Alpha checkout:

- ZIP: `E:\Fabuloom\alpha-testers\fabuloom-alpha-0.1.0-source-only-064.zip`
- Clean validation copy: `C:\Users\User\AppData\Local\Temp\fabuloom-clean-064-new`
- ZIP SHA-256: `96197D6477ADBDE6E83F10543EDBBBFD377DB4D500644A343B3E67E87490C9BD`
- Clean-copy file count: 700

The copy excludes Git metadata, virtual environments, workspace data, caches, E2E dependencies and Topazioverse/narrator asset directories. It retains public code, documentation, launcher, tests and the neutral community pack. Earlier candidates were not overwritten.

## Validation

- Public Node suite: **128 passed, 0 failed** in the repository and clean copy.
- Root Python suite: **48 passed, 1 skipped, 22 subtests passed**. The E2E directory itself contains no Python tests (`no tests ran`), so that command was not treated as a passing Python suite.
- Landing JavaScript syntax and whitespace checks: **PASS**.
- Responsive captures: desktop and mobile evidence generated; the complete 1920/1366/768/390/320 matrix remains a warning if owner review requires every size archived.
- Real audiovisual export: previously approved in Mission 051.1; no new heavy Kokoro synthesis was performed.
- Canvas × FFmpeg visual gate: remains **PARTIAL**, as required by prior evidence; it was not reclassified artificially.

## Licensing and security boundary

The candidate is source-only. Fabuloom code remains MIT. The neutral Ponto pack declares its own provenance/license. Kokoro, voices, models and FFmpeg remain external dependencies and are not bundled. Topazioverse artwork is excluded from the clean candidate and no statement is made about its historical presence. Pack loading continues to reject traversal, remote assets, executable pack scripts and unsafe manifests in the public test suite.

## Remaining limitations and recommendation

The Alpha is suitable for a controlled owner/early-tester review with documented limitations, not an unrestricted release. Remaining gates include owner approval, the known visual-parity limitation, external Kokoro/FFmpeg setup, and human validation of the native Windows selector. Recommendation: **GO_WITH_LIMITATIONS for owner review; do not publish until the owner approves the candidate and the remaining gates.**
