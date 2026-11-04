# Getting started

Fabuloom Studio is one local application with a shared engine. The native
Desktop shell, headless CLI, loopback HTTP API, existing browser Stage and
local MCP adapter all operate on the same projects, catalog, timelines and
jobs. The current foundation is dependency-light and does not install a
second editor or duplicate the rendering/TTS boundary.

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
python -B -m fabuloom_core.cli status
python -B -m fabuloom_core.cli project list
```

No installation or network access is required for these checks. The CLI also
supports `project create`, `project update`, `job create`, `job show`,
`job cancel`, and `catalog scan`. Jobs persist under the configured workspace,
report progress, and recover stale queued/running records as interrupted.

## Start the application surfaces

The Desktop shell is a thin Tkinter surface over `EngineService`. It starts a
loopback-only API on port 8790 and can launch the existing browser Stage on
port 8765. For automation, prefer the structured CLI/API contracts rather
than browser coordinates:

```powershell
python .\desktop\fabuloom_desktop.py --check
python .\desktop\fabuloom_desktop.py
python -B -m fabuloom_core.cli api --port 8790
```

The API is deliberately bound to loopback. A local stdio MCP adapter is also
available for agents and translates tool calls to the same engine services:

```powershell
python -B -m fabuloom_core.mcp --root E:\Fabuloom
```

The adapter speaks newline-delimited JSON-RPC on stdin/stdout; it does not
contain a second project, catalog, render or TTS implementation.

Set `FABULOOM_ROOT` when the private library/workspace lives outside the
repository. The default discovery prefers the nearest Fabuloom umbrella
containing both `studio` and `workspace`, while generated data remains outside
the public source tree.

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

## Shared production job

The first end-to-end acceptance production is deliberately generic and uses
only a generated SVG plus deterministic synthetic audio when Kokoro is not
available. It still exercises the shared manifest, timeline, Canvas capture,
captions, checkpoint and FFmpeg export:

```powershell
python -B -m fabuloom_core.cli --root E:\Fabuloom render demo --output-id local-demo
```

The same operation is available as `POST /api/v1/render` and the MCP tool
`fabuloom_render_demo`. To add local music without copying or changing the
source, pass `--music-path` under the configured root; the shared service
applies voice-priority sidechain ducking, fades and a limiter. Human listening
and artistic review remain required.

## Browser Stage and local workspace

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

When adding providers or export plugins, document exact Python and Node
versions, create project-local environments, and verify every dependency and
model license. Do not install anything globally as part of the project.
