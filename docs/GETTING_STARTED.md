# Getting started

For the community-facing path, start with the repository-root [INSTALL.md](../INSTALL.md) and [QUICKSTART.md](../QUICKSTART.md). This file retains the developer-level contract details.

This preparation branch contains the dependency-free Fabuloom Core contracts,
the local Studio shell, Santa V5 Narrator Mode and optional Kokoro integration.
The full project/editor workflow and one-click export job are not implemented.

## Layout

- Public source checkout: `E:/Fabuloom/studio`
- Private project context: `E:/Fabuloom/internal`
- Local workspace and future generated artifacts: `E:/Fabuloom/workspace`

## Development principles

- Keep all new work inside `E:/Fabuloom`.
- Keep models, environments, caches, generated media, and temporary files out of Git.
- Treat TopazioReader and Card Game Studio as read-only references.
- Prefer interfaces and manifests before concrete integrations.
- Record decisions and verification results as the project evolves.

## Run the core checks

From the repository root:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m unittest discover -s tests -p 'test_*.py' -v
python .\examples\contract_demo.py
```

No installation or network access is required for these checks.

The optional Kokoro extra is declared in `pyproject.toml`. For an isolated
checkout, create a local environment and install it only if the user has
reviewed the dependency/model licenses:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[kokoro]"
```

The repository does not contain model weights, WAVs, manifestos or caches. See
`docs/KOKORO-INTEGRATION.md` for the command, segmentation/manifest flow and
capability limits. The optional real-model test remains skipped unless the
user explicitly enables it.

## Studio UI and local workspace

The public `main` branch remains the Core foundation. This preparation branch
contains the Studio shell and should be used through the isolated release
worktree or a review checkout.

The frontend has no `package.json` because it intentionally runs without a
bundler. Node is used for the dependency-free `.mjs` test suite. FFmpeg is a
runtime prerequisite only for the offline export examples; verify it with
`ffmpeg -version` and `ffprobe -version`.

For a clean checkout, keep generated data isolated from the repository with
the explicit local roots below:

```powershell
$env:FABULOOM_WORKSPACE_ROOT = (Resolve-Path .).Path
$env:FABULOOM_EXPORT_ROOT = Join-Path $env:FABULOOM_WORKSPACE_ROOT 'workspace\exports'
python .\frontend\server.py --port 8765
```

Open `http://127.0.0.1:8765/`. Existing developer exports are not required for
the server to start, but the preview and export links remain empty until local
manifests, WAVs and production profiles are supplied.

## Future prerequisites

When implementation begins, document exact Python and Node versions, create project-local environments, and verify every dependency license. Do not install anything globally as part of the project.
