# Unified Studio Character Library — Mission 049

## Architecture

`studio.html` is now the recommended user entry point. The library is injected into its existing Narrators route by `studio-shell.mjs`; `index.html` remains the preserved Character Stage/DEV compatibility surface. Both surfaces reuse `character-pack.mjs`, `character-pack-loader.mjs`, `LayeredCharacterRenderer`, managed pack APIs, and the project `character_pack` reference.

## User flow

With a project open, the user opens Narrators, selects Ponto, chooses `neutral` or `smile`, and the Studio installs/uses the managed community pack. The visual preview uses the existing layered renderer in a `character` preview mode. The project voice is not changed. Local pack import uses the existing directory input and managed installation endpoint; scripts, traversal, undeclared assets, and active SVG content remain rejected by the existing security boundary.

## Persistence and recovery

The project stores pack ID, version, contract, character ID, expression, managed asset reference, license, and author in `project.json`. No absolute path or browser permission is stored. On reopen, the Studio resolves the managed pack and restores the expression. If the pack is missing, the reference remains and the UI reports that reinstall is required; it does not select Santa V5 silently.

## Evidence

The expanded Playwright harness in `tools/e2e/run.mjs` completed the real Studio flow in the latest run:

- create project, script, scene, PNG, movement and save: PASS;
- select Ponto, select `smile`, persist association: PASS;
- restart isolated server and open a fresh browser context: PASS;
- restore Ponto, `smile`, scene, image and `character_pack` backend reference: PASS.

Latest evidence directory: `C:\Users\User\AppData\Local\Temp\fabuloom-e2e-047-KOEP5P`.

Overall mission classification remains **PARTIAL** because MP4/FFprobe, native Windows dialog, and Canvas × FFmpeg visual parity are separate gates and were not artificially marked PASS here.

## Compatibility

Santa V5, Dora, Alex, Narrator Mode, Kokoro integration, cinematic preview, and existing assets were not removed, moved, relicensed, or structurally rewritten. The project voice remains independent from visual pack selection.
