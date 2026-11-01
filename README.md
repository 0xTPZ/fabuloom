# Fabuloom Studio

Fabuloom Studio is a local-first, open-source application for turning written stories into narrated audiovisual productions.

The project has moved beyond the planning stage. The functional Alpha is being prepared on the [`release/fabuloom-alpha-preparation`](https://github.com/0xTPZ/fabuloom/tree/release/fabuloom-alpha-preparation) branch and tracked in [PR #33](https://github.com/0xTPZ/fabuloom/pull/33).

> **Fabuloom Studio 0.1.0-alpha — in preparation, not officially released.**
>
> The features below describe the development branch. They are not claimed to be available on `main` until the work is reviewed and merged.

## What the Alpha can do

The current development build supports:

- Creating and persisting local projects.
- Writing and editing scripts.
- Organizing scenes and importing images.
- Camera movements and cinematic preview.
- Narration through an optional Kokoro setup.
- A character library with locally installed character packs.
- The independent `community-demo-v1` character pack, Ponto.
- MP4 export through FFmpeg.
- Automated Python, Node, and Playwright coverage for the public workflow.

The application is designed for writers, independent creators, artists, producers, and developers who want an editable local workflow from story to narrated video. It is not presented as a replacement for Premiere, CapCut, or other professional editors.

## Project model

- **Product:** Fabuloom Studio
- **Development version:** 0.1.0-alpha
- **Approach:** open source and local-first
- **Proposal:** transform written stories into editable narrated audiovisual productions
- **Code license:** MIT for original Fabuloom code
- **Assets and dependencies:** governed by their own licenses and provenance

The public source-only candidate does not bundle models, voices, FFmpeg, private environments, or uncleared Topazioverse artwork. Independent character packs can be installed separately when their licenses and provenance are documented.

## Try the development branch

The Alpha is not yet a public release. When access is authorized, start with the development branch and follow its installation guide:

1. Check out [`release/fabuloom-alpha-preparation`](https://github.com/0xTPZ/fabuloom/tree/release/fabuloom-alpha-preparation).
2. Read [`INSTALL.md`](https://github.com/0xTPZ/fabuloom/blob/release/fabuloom-alpha-preparation/INSTALL.md) and [`ALPHA-TESTING-GUIDE.md`](https://github.com/0xTPZ/fabuloom/blob/release/fabuloom-alpha-preparation/ALPHA-TESTING-GUIDE.md).
3. Review [`KNOWN_LIMITATIONS.md`](https://github.com/0xTPZ/fabuloom/blob/release/fabuloom-alpha-preparation/KNOWN_LIMITATIONS.md) before running the Studio.

The branch is still under owner review. Do not treat the local test ZIPs as public downloads.

## Documentation

- [Installation (Alpha branch)](https://github.com/0xTPZ/fabuloom/blob/release/fabuloom-alpha-preparation/INSTALL.md)
- [Alpha testing guide](https://github.com/0xTPZ/fabuloom/blob/release/fabuloom-alpha-preparation/ALPHA-TESTING-GUIDE.md)
- [Known limitations](https://github.com/0xTPZ/fabuloom/blob/release/fabuloom-alpha-preparation/KNOWN_LIMITATIONS.md)
- [License boundary and notices](https://github.com/0xTPZ/fabuloom/blob/release/fabuloom-alpha-preparation/LICENSES.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Alpha development PR #33](https://github.com/0xTPZ/fabuloom/pull/33)

## Scope and privacy

Fabuloom is developed independently from TopazioReader and Card Game Studio. Those projects are not dependencies. Private production environments, manuscripts, personal audio, models, generated media, and private continuity context are not part of this public presentation.

## License

Original Fabuloom Studio code is available under the [MIT License](LICENSE). This applies only to original project code. Third-party code, models, voices, images, character packs, and media remain subject to their respective licenses and permissions.
