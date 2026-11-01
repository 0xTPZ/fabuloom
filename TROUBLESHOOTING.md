# Troubleshooting

## `fabuloom_core` cannot be imported

Use the project-local environment and set `PYTHONPATH` for the test commands:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
```

## Preview says that no manifest is available

The checkout has no private developer exports. The preview requires a compatible local measured manifest and referenced audio under the configured workspace. Do not copy files from `E:\Fabuloom\workspace\exports` into a clean installation.

## FFmpeg is missing

The Studio shell can be inspected without FFmpeg. Export examples cannot run until `ffmpeg` and `ffprobe` are available on `PATH`. Install them using your operating system's normal package method; this project does not install global tools.

## Kokoro is unavailable

Kokoro is optional. The core contracts and browser shell do not imply that model weights are present. Review provider/model licensing and install the optional extra only in a project-local environment.

## Port or path errors

Use another loopback port, for example `--port 8876`. Keep `FABULOOM_EXPORT_ROOT` inside `FABULOOM_WORKSPACE_ROOT`; the server intentionally rejects an export root outside it.
