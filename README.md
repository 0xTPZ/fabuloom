# Fabuloom Studio

Fabuloom Studio is an open-source, local-first storytelling studio for turning scripts into narrated videos with characters, camera motion, and FFmpeg export.

The project is real and functional beyond the planning stage, but the Alpha is still being prepared:

> **Fabuloom Studio 0.1.0-alpha — in preparation, not officially released.**

The active development is on [`release/fabuloom-alpha-preparation`](https://github.com/0xTPZ/fabuloom/tree/release/fabuloom-alpha-preparation), tracked in [PR #33](https://github.com/0xTPZ/fabuloom/pull/33). Features from that branch are not claimed to be available on `main` until reviewed and merged.

[Leia em português (Brasil)](README.pt-BR.md)

## What the Alpha is building

The development branch supports the core local workflow:

- Project creation and persistence.
- Script and scene editing.
- Image import and camera movements.
- Cinematic preview and MP4 export through FFmpeg.
- Optional Kokoro narration.
- A character library with independently installed packs.
- The neutral `community-demo-v1` character pack, Ponto.
- Python, Node, and Playwright tests for the public workflow.

Fabuloom is intended for writers, content creators, artists, independent producers, and developers who want an editable path from story to audiovisual production. It is not presented as a replacement for Premiere, CapCut, or another professional editor.

## Technology

Python powers the local server and audio integration. The Studio uses browser technologies for the interface and preview, Kokoro is an optional narration provider, and FFmpeg is an external export dependency.

## Follow the development

The Alpha is not a public release or download. When access is authorized, use the development branch and read:

- [Installation guide](https://github.com/0xTPZ/fabuloom/blob/release/fabuloom-alpha-preparation/INSTALL.md)
- [Alpha testing guide](https://github.com/0xTPZ/fabuloom/blob/release/fabuloom-alpha-preparation/ALPHA-TESTING-GUIDE.md)
- [Known limitations](https://github.com/0xTPZ/fabuloom/blob/release/fabuloom-alpha-preparation/KNOWN_LIMITATIONS.md)
- [License boundary](https://github.com/0xTPZ/fabuloom/blob/release/fabuloom-alpha-preparation/LICENSES.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

No test ZIP, model, voice, private environment, manuscript, or uncleared Topazioverse artwork is offered as a public download here. Independent packs remain subject to their own licenses and provenance.

## License

Original Fabuloom code is MIT-licensed. Third-party code, models, voices, images, character packs, and media remain subject to their respective licenses and permissions.
