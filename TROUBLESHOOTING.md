# Troubleshooting

## `fabuloom_core` cannot be imported

Use the project-local environment and set `PYTHONPATH` for the test commands:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
```

## Preview says that no manifest is available

Select an existing project or generate narration from **Áudio** first. A clean checkout has no private developer exports and therefore starts with an empty preview. Do not copy files from `E:\Fabuloom\workspace\exports` into a clean installation.

## FFmpeg is missing

The Studio shell can be inspected without FFmpeg. Export examples cannot run until `ffmpeg` and `ffprobe` are available on `PATH`. Install them using your operating system's normal package method; this project does not install global tools.

## Kokoro is unavailable

Kokoro is optional for opening the shell but required for real narration. Install the extra in the project-local environment with `python -m pip install -e ".[kokoro]"`. If the package is installed but generation still fails, check that the public `hexgrad/Kokoro-82M` model can be downloaded or is present in the Hugging Face cache, and that `pm_santa` is available. Never copy private models or generated audio into the repository.

## Port or path errors

Use another loopback port, for example `--port 8876`. Keep `FABULOOM_EXPORT_ROOT` inside `FABULOOM_WORKSPACE_ROOT`; the server intentionally rejects an export root outside it.
