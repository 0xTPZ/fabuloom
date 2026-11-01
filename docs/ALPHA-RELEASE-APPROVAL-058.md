# Alpha Release Approval Review 058

Status: `READY_FOR_OWNER_APPROVAL` — source-only candidate prepared; owner authorization is still required. No release, tag, merge, or GitHub Release was created.

## Git and PR

- Branch: `release/fabuloom-alpha-preparation`
- Local HEAD: `1de890c`
- Remote HEAD before synchronization: `49f7d11`
- Local commits pending: `5665108`, `1de890c`
- Working tree before this report: clean
- PR: #33, Draft

The two pending commits contain only the Mission 056 report, Mission 057 report, the public E2E test selector, and the neutral-fixture/Python-discovery harness correction. No private context, production asset, model, credential, or Topazioverse art was added. The branch is intentionally ahead of remote by two commits; synchronization is authorized by this mission and will be a normal push, never a force push.

## Final source-only candidate

The earlier ZIP hash from Mission 057 was reproducible but its audit revealed that it included `tools/e2e/node_modules` and `.pytest_cache`. Those are not distribution content. The ZIP was rebuilt from a fresh isolated copy with those caches excluded; the path is unchanged for handoff.

- ZIP: `C:\Users\User\AppData\Local\Temp\fabuloom-clean-057-source-only.zip`
- Final ZIP SHA-256: `8CE497B52939D6B4A2FF290BADD852B7995B74D1BE3502FAB093E5C30094B6E2`
- Manifest: `CLEAN-CANDIDATE-MANIFEST-058.txt`
- Manifest SHA-256: `8FEEAC8285812E849010DBF2BF1328E9BDD93061319C3AE24D362AA604D8FE48`
- Included files: 346
- Reproduction copy: `C:\Users\User\AppData\Local\Temp\fabuloom-clean-058-1c95805a30284ba3b95c8ad743072ab3`

The expected Mission 057 ZIP hash (`DBCC998F...`) therefore does not match the corrected package; the mismatch is intentional and documented, caused by removing dependency/cache content found during this review.

The package contains source, documentation, licenses, scripts, tests, and `community-demo-v1`/Ponto only. It excludes all Topazioverse character directories, `frontend/assets/narrator-mode`, models, voices, binaries, caches, virtual environments, credentials, manuscripts, production workspaces, and private contexts. The source code for optional compatibility remains, but no proprietary artwork is distributed. Exclusion from the ZIP does not erase files from public Git history or alter their licensing status.

## Validation

- Python clean suite: **PASS** — 48 passed, 1 skipped, 22 subtests passed.
- Public Node suite: **PASS** — 128 passed, 0 failed using `npm run test:public`.
- Playwright quick flow: **PASS** — project creation, neutral image import, Ponto selection, expression, new browser context, restoration, and backend pack reference.
- Automated export: **PASS** from the clean extraction using the separately prepared authorized runtime. The Kokoro model was reused from local cache; no model was downloaded or copied into the package.
- MP4: `C:\Users\User\AppData\Local\Temp\fabuloom-e2e-047-0ClFsH\workspace\workspace\exports\projects\project-88ba551c0567\project-88ba551c0567-1080p.mp4`
- FFprobe: H.264 High, 1920x1080, 30 FPS, AAC-LC mono 48 kHz, 2.900 seconds.
- FFmpeg full decode and start/middle/end frame extraction: **PASS**.
- Ponto persistence after export: **PASS**.

The browser/export evidence used the clean source tree plus separately prepared Python/Kokoro/FFmpeg runtime. Those dependencies are not part of the source-only ZIP and must be installed independently according to `INSTALL.md` and the third-party license inventory.

## Visual and legal gates

The visual parity gate remains `PARTIAL`, unchanged from Mission 054; it is not being upgraded artificially. The source-only boundary remains: Fabuloom code under MIT, Ponto under its own declared independent license, and Kokoro/model/FFmpeg under their respective external licenses. Owner-controlled Topazioverse art is not included.

Known limitations remain the optional Santa/Dora/Alex compatibility resources, native Windows directory-dialog validation, and the requirement for separately installed narration/export dependencies.

## Installation procedure

1. Extract the ZIP to a user-controlled directory.
2. Install Python 3.11+ locally and create a project virtual environment.
3. Install the documented Python dependencies; install Kokoro/model/voice separately if narration is required.
4. Install FFmpeg/FFprobe separately and review their licenses.
5. Run `python frontend/server.py --port 18765` and open `http://127.0.0.1:18765/studio.html`.
6. Use the public Ponto pack or import an independently licensed pack. Do not expect proprietary Santa/Dora/Alex artwork in this package.

## Recommendation

`READY_FOR_OWNER_APPROVAL`. The corrected source-only candidate is reproducible, excludes proprietary art and caches, passes the applicable public tests, and has a real neutral/Ponto export validated through the interface. Publication remains blocked until the owner explicitly approves the package, licenses, and remaining documented limitations.
