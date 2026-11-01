# Alpha 0.1.0 — Third-Party License and Provenance Inventory

Audit date: 2026-11-01  
Scope: components used by the local Studio and the real `pm_santa` validation. No third-party weights, voices, caches or media are committed.

| Component | Version observed | Official origin | License / obligation | Included in public Git? | Gate |
|---|---:|---|---|---|---|
| Fabuloom original code | 0.1.0 | this repository | MIT; retain notice | Yes | PASS |
| Kokoro Python package | 0.9.4 | `github.com/hexgrad/kokoro` / PyPI | Apache-2.0 according to package metadata; retain notices | No, optional install | PASS conditioned on notice bundle |
| Kokoro-82M model | public model revision in HF cache | `huggingface.co/hexgrad/Kokoro-82M` | Apache-2.0 shown by official model card; do not bundle without attribution/terms | No | PASS for local download; redistribution requires record |
| Kokoro voices (`pm_santa`, `pf_dora`, `pm_alex`) | shipped through Kokoro model/package | Kokoro package/model distribution | voice provenance is coupled to Kokoro terms; no separate voice notice was found in this checkout | No | BLOCKED for bundling until provenance is recorded |
| PyTorch | 2.15.0 observed in audit venv | `pytorch.org` / PyPI | BSD-style license and notices | No, installed dependency | PARTIAL — exact notice bundle not committed |
| NumPy | 2.5.4 | `numpy.org` / PyPI | BSD-3-Clause | No | PASS conditioned on dependency notices |
| SoundFile | 0.14.0 | `github.com/bastibe/python-soundfile` / PyPI | BSD-3-Clause | No | PASS conditioned on dependency notices |
| Misaki | 0.9.4 | Kokoro dependency metadata | verify transitive notices before bundling | No | PARTIAL |
| espeakng-loader / phonemizer-fork | 0.2.4 / 3.3.2 observed | PyPI projects | dependency-specific licenses must be preserved; eSpeak-ng commonly carries GPL-3.0-or-later obligations | No | BLOCKED for a bundled redistributable runtime until exact notices are captured |
| FFmpeg | 9.0.1 host runtime | `ffmpeg.org` / build vendor | build-specific LGPL/GPL configuration and notices; this branch does not bundle the binary | No | PARTIAL — publish exact build provenance if distributing binary |
| Segoe UI / system fonts | Windows host | Microsoft system font | not redistributed by Fabuloom; local FFmpeg examples reference installed font path | No | PASS if not bundled; do not package font |
| Fabuloom SVG/PNG test assets | mission-local originals | generated for audit / repository assets | original or repository-owned; retain project MIT boundary | Some repository assets | PASS for test use |
| Music/SFX in Studio Alpha core | none in the final 037/038 Studio export | n/a | no demonstrative third-party track is distributed | No | PASS |

## Decision boundary

The public repository can be shared as source under MIT with optional local setup. It is not yet a self-contained redistributable installer containing Kokoro, PyTorch, eSpeak-ng, FFmpeg, model weights or voices. Before any packaged Alpha, attach exact package lock/provenance and third-party notices, and resolve the voice/eSpeak-ng redistribution boundary.

Sources checked: project `LICENSE`, `LICENSES.md`, `docs/KOKORO-INTEGRATION.md`, installed package metadata, the official Kokoro repository, the official `hexgrad/Kokoro-82M` model card, and the FFmpeg build information from the validation host.
