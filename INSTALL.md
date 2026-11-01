# Installation

## Supported environment for this preparation branch

Validated in the audit environment on Windows with Python 3.12.10, Node 24.19.0/npm 11.17.0 and FFmpeg 9.0.1. These are validation observations, not bundled runtimes. Python 3.11+ is required by `pyproject.toml`. Node is needed for the `.mjs` test suite. FFmpeg/ffprobe are needed by export examples, not by the static Studio shell.

No global installation is required. Do not copy private models, WAVs, caches or production exports into the repository.

## Clean checkout

```powershell
git clone https://github.com/0xTPZ/fabuloom.git
cd fabuloom
git fetch origin release/fabuloom-alpha-preparation
git switch --detach release/fabuloom-alpha-preparation
```

## Project-local Python environment

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e .
```

The core has no mandatory third-party Python dependency. The command above is the supported editable install and works in a clean checkout because the repository declares its setuptools build backend. Kokoro remains optional for opening the shell, but is required for real Santa narration.

## Diagnose prerequisites

```powershell
pwsh -File .\scripts\diagnose.ps1
```

The diagnostic command reports missing tools without changing global configuration.

## Start the local Studio

```powershell
$env:FABULOOM_WORKSPACE_ROOT = (Resolve-Path .).Path
$env:FABULOOM_EXPORT_ROOT = Join-Path $env:FABULOOM_WORKSPACE_ROOT 'workspace\exports'
python .\frontend\server.py --port 8765
```

Open `http://127.0.0.1:8765/`. The server binds to loopback only and limits export paths to the configured workspace. A clean checkout starts, but it will show empty preview/export states until local manifests, audio and profiles are supplied.

## Optional Kokoro provider

```powershell
& .\.venv\Scripts\python.exe -m pip install -e ".[kokoro]"
```

This installs the provider and runtime dependencies in `.venv`; it does not bundle model weights. On first narration, Kokoro downloads the public `hexgrad/Kokoro-82M` model into the user's Hugging Face cache, or uses an existing public cache. Review [LICENSES.md](LICENSES.md) and [docs/KOKORO-INTEGRATION.md](docs/KOKORO-INTEGRATION.md) before enabling it. No global installation is performed.
