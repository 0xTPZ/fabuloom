# Clean Alpha Stabilization 057

Status: `READY_FOR_RELEASE_APPROVAL` for owner review of the source-only candidate. This is not publication authorization.

## State and provenance

The local HEAD before changes was `5665108`, matching the mission reference. The remote branch remained at `49f7d11`; the local branch was ahead by one commit. No remote write was attempted. `E:\Fabuloom\studio` was not modified.

The clean candidate was rebuilt in a separate temporary directory from the development checkout, excluding `.git`, `.venv`, `workspace`, private data, caches, proprietary character directories, and `frontend/assets/narrator-mode`.

Candidate: `C:\Users\User\AppData\Local\Temp\fabuloom-clean-056-f8b5cc9c7ea44f5e9fa062bbf1f6266d`

Excluded character groups: `topazio-narrators`, `topazio-narrators-cartoon-v1`, `topazio-narrators-recovery-v1`, `topazio-narrators-v2`, `topazio-narrators-v3`, `topazio-narrators-v4`, `topazio-narrators-v5`, and `fantasy-narrator`. The independent `community-demo-v1` Ponto pack remains included.

## 11 failures from Mission 056

All 11 failures were missing-file assertions in tests for proprietary or development-only art:

`test_character_art_consistency.mjs`, `test_facial_recovery.mjs`, `test_santa_v3.mjs`, `test_santa_v4.mjs`, `test_santa_v5_anatomy_experimental.mjs`, `test_santa_v5_art.mjs` (three failures), `test_topazio_narrators.mjs`, `test_topazio_narrators_v3.mjs`, and `test_topazio_narrators_v4.mjs`.

They are compatibility/asset-presence tests, not public-core implementation failures. They remain in the repository for authorized development/compatibility validation; they are excluded from the new explicit `tools/e2e/public-tests.mjs` suite rather than silently disabled. The public suite excludes exactly the nine named proprietary test files and no other tests.

## Corrections

- `tools/e2e/run.mjs` no longer uses `fantasy-narrator` as a scene fixture. It generates a tiny neutral PNG in memory, so the public browser test contains no proprietary asset dependency.
- The harness prefers `.venv` when present and falls back to the independently prepared `python` command in a source-only checkout.
- Added `npm run test:public` to run the public-compatible Node suite separately from proprietary compatibility tests.

## Clean candidate validation

- Python: **PASS** — 48 passed, 1 skipped, 22 subtests passed.
- Public Node suite: **PASS** — 128 passed, 0 failed.
- Playwright quick flow: **PASS** for all five flows: project/script/scene/image/movement, Ponto selection and expression, new browser context, Ponto restoration, and backend project-pack reference.
- Real Studio export from clean extraction: **PASS**, using only the neutral in-memory scene image and Ponto. The optional runtime was prepared separately: Python 3.12.10 and Kokoro from the existing validated local virtual environment, cached Kokoro-82M model, and FFmpeg/FFprobe 9.0.1. None of these runtime files are in the ZIP.
- MP4: `C:\Users\User\AppData\Local\Temp\fabuloom-e2e-047-0ClFsH\workspace\workspace\exports\projects\project-88ba551c0567\project-88ba551c0567-1080p.mp4`
- FFprobe: **PASS** — H.264 High, 1920x1080, 30 FPS, AAC-LC mono 48 kHz, 2.900 s.
- FFmpeg full decode: **PASS**. Start/middle/end frames extracted successfully. Ponto selection and project persistence remained PASS after export.

The export used the authorized local runtime as an external dependency; it was not treated as part of the source-only distribution.

## Distribution package

- ZIP: `C:\Users\User\AppData\Local\Temp\fabuloom-clean-057-source-only.zip`
- Included file count: 531
- Manifest: `CLEAN-CANDIDATE-MANIFEST-056.txt`
- Manifest SHA-256: `0E4CB5A11CF582E2553A929FD6265D8D4DCB9963BD26C06BC61ADA0506FA159A`
- ZIP SHA-256: `DBCC998F23F67DEE0AD4496FEF30A2A7926C898D29948E532992F7B3D860EE3F`

The package contains source, public-compatible tests, documentation, scripts, license notices, and the independent Ponto pack. It contains no Santa V5, Dora, Alex, Topazioverse art, manuscripts, production files, credentials, models, voices, FFmpeg binaries, caches, or virtual environments.

## Licensing and remaining limits

Fabuloom code remains MIT. Ponto retains its independently declared pack license and provenance. Kokoro, its model/voice, and FFmpeg remain separately installed dependencies under their own licenses. Excluding files from this ZIP does not remove them from the repository's public history or change their rights status.

The full proprietary compatibility suite still requires an authorized checkout containing those assets. The public UI may log expected 404s for Santa/Dora/Alex preview resources when those optional packs are absent; the basic Studio and Ponto workflow does not depend on them. Native Windows directory-dialog validation remains outside this automated gate.

## Recommendation

`READY_FOR_RELEASE_APPROVAL`: the clean candidate starts without Topazioverse assets, its public suite passes, the browser workflow passes, and a real neutral/Ponto MP4 was exported and decoded using separately prepared optional dependencies. Owner approval and any remaining distribution/legal review are still required. No merge, tag, release, or remote update was performed.
