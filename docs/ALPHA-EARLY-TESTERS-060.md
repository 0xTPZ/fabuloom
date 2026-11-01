# Fabuloom Alpha 0.1.0 — early testers

Status: `READY_TO_DISTRIBUTE` for controlled delivery to 3–5 selected participants. This is not a public release and does not authorize a GitHub Release, tag, merge, or broad publication.

## Candidate verification

- Branch: `release/fabuloom-alpha-preparation`
- HEAD: `0f17b35`
- ZIP source: `C:\Users\User\AppData\Local\Temp\fabuloom-clean-057-source-only.zip`
- Prepared copy: `E:\Fabuloom\alpha-testers\fabuloom-alpha-0.1.0-source-only.zip`
- SHA-256: `8CE497B52939D6B4A2FF290BADD852B7995B74D1BE3502FAB093E5C30094B6E2` (confirmed)
- ZIP entries: 348

The archive contains the source-only candidate, documentation, tests, licenses, scripts, and the independent `community-demo-v1` Ponto pack. It contains no Topazioverse art, models, voices, virtual environments, caches, credentials, manuscripts, production workspaces, or private contexts. Optional compatibility source remains in the codebase, but its proprietary assets are absent.

The package was copied from the validated temporary ZIP without modification. The external tester directory contains no runtime dependencies or personal data.

## Prepared materials

`E:\Fabuloom\alpha-testers\` contains:

- `fabuloom-alpha-0.1.0-source-only.zip`
- `SHA256.txt`
- `FIRST-STEPS-WINDOWS.md`
- `INSTALL.md`
- `ALPHA-TESTING-GUIDE.md`
- `KNOWN_LIMITATIONS.md`
- `LICENSES.md`
- `BUG-REPORT-TEMPLATE.md`

The installation guide covers Windows 10/11 extraction, Python/venv setup, local Studio startup, FFmpeg, optional Kokoro, project creation, and export. No administrator permissions or automatic global installation are required.

## Tester checklist

### Experience A — first contact

- Start the Studio and create a project.
- Create two scenes and import two user-owned images.
- Apply camera movements.
- Select Ponto.
- Save, close, reopen, and verify scenes, images, movements, character, and expression.

### Experience B — optional export

- Configure Kokoro and FFmpeg separately if available.
- Generate short narration through the Studio button.
- Export a real MP4 through the interface.
- Reproduce it and check image/audio synchronization.
- Record setup failures without bypassing them; Experience A does not require Kokoro.

## Feedback and safety

The supplied template requests only Windows/Python/runtime versions, non-sensitive hardware context, usability, errors, export results, and suggestions. Testers must not send passwords, tokens, personal projects, manuscripts, private logs, or unredacted paths. No GitHub issues or invitations were created automatically.

## Known limitations

- This is a controlled Alpha, not a stable production release.
- Kokoro, its model/voice, and FFmpeg are external optional dependencies and are not bundled.
- Native Windows directory-dialog validation and the visual parity gate remain documented limitations.
- Topazioverse characters are intentionally absent from the clean package.
- Audiovisual export depends on the tester's separately prepared runtime.

## Recommended distribution

Deliver the ZIP and these instructions only to the selected participants through a channel chosen by the owner. Verify the SHA-256 before extraction. Do not create a public release, tag, download link, or automatic invitation. Collect sanitized feedback using the template and keep the PR #33 Draft.

`E:\Fabuloom\studio` was not modified. No GitHub or external publication was performed in this mission.
