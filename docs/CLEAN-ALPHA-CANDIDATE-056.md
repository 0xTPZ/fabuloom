# Clean Alpha Candidate 056

Status: `READY_FOR_OWNER_REVIEW` (source-only candidate; not authorized for publication)

## Scope

This candidate is a separate temporary copy of commit `49f7d11`. The Git checkout and `E:\Fabuloom\studio` were not modified. No files were removed from Git and no license was changed.

The candidate contains Fabuloom source, tests, documentation, and the independent `frontend/assets/characters/community-demo-v1` pack (Ponto). It excludes the character directories `topazio-narrators`, `topazio-narrators-cartoon-v1`, `topazio-narrators-recovery-v1`, `topazio-narrators-v2`, `topazio-narrators-v3`, `topazio-narrators-v4`, `topazio-narrators-v5`, `fantasy-narrator`, and `frontend/assets/narrator-mode`. These groups contain Topazioverse identity art or assets whose redistribution authorization is not established by FAB-IP-043. The exclusion applies only to this candidate copy; it does not remove or alter the repository history.

No models, voices, virtual environments, caches, private workspaces, FFmpeg binaries, or other third-party binaries are included.

## Reproducible candidate

- Copy: `C:\Users\User\AppData\Local\Temp\fabuloom-clean-056-f8b5cc9c7ea44f5e9fa062bbf1f6266d`
- File count in the candidate manifest: 530
- Manifest: `CLEAN-CANDIDATE-MANIFEST-056.txt`
- Manifest SHA-256: `26068F8F7928993A36D7ED2084E121C2CD60E0CAEDC0DE4D10EE2061C0F7A1EB`
- Source-only archive (temporary, not committed): `C:\Users\User\AppData\Local\Temp\fabuloom-clean-056-source-only.zip`
- Archive SHA-256: `DC293D63489998E9F07139B77FB008D6FC31D84B484A2F7D12FC04D6B12E1121`

The manifest records a SHA-256 for every included file. The archive was created from the verified clean copy, not from the development checkout.

## Validation

- Clean Python suite: **PASS** — 48 passed, 1 skipped, 22 subtests passed.
- Clean Node suite: **PARTIAL** — 149 passed, 11 failed. The failures are tests whose purpose is to assert the presence of excluded Santa/Dora/Alex/Topazioverse files; the failures are expected after removal from the candidate and are not evidence that Ponto or the source server is broken.
- Clean Studio server: **PASS** — started from the candidate copy on loopback port 18768; `/api/health` returned HTTP 200.
- Ponto persistence E2E: **not independently re-run in this candidate**. The existing quick harness is not distribution-neutral: it hardcodes `fantasy-narrator/torso-core.png` as a fixture, so it stops before opening the clean Studio. This is a test-harness dependency and must be corrected before claiming a clean automated browser gate.
- MP4 export: **BLOCKED in this candidate run**. The source-only copy intentionally contains no Kokoro model/voice and no FFmpeg binary. Installation of those optional external dependencies remains a separate documented setup step; no previous MP4 was reused as evidence.

The candidate therefore starts without Santa V5 and retains the independent Ponto pack, but the current automated harness and some legacy art-presence tests still assume proprietary development assets. This is the smallest documented correction required before a fully automated clean-browser/export claim.

## License boundary

Fabuloom source remains under the repository MIT license. Ponto/community-demo-v1 carries its own independent manifest and license metadata. Topazioverse art is not included in this candidate. Kokoro, model/voice files, FFmpeg and other runtime dependencies are installed separately under their own licenses and are not redistributed here. Nothing in this report revokes, changes, or relicenses any prior asset.

## Decision

`READY_FOR_OWNER_REVIEW`: a clean, hashed source-only candidate exists, starts independently, passes the Python suite, and contains only the independent demo pack among character assets. It is not a public release candidate yet: the clean browser harness must stop relying on `fantasy-narrator`, the legacy proprietary-asset tests should be split or marked as development-only, and a clean export run requires the separately authorized Kokoro/FFmpeg runtime.

No merge, tag, release, or PR publication was performed. PR #33 remains Draft.
