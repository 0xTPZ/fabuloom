# Quickstart

## What can be verified immediately

1. Install the project-local environment from [INSTALL.md](INSTALL.md).
2. Run `pwsh -File .\scripts\diagnose.ps1`.
3. Set `FABULOOM_WORKSPACE_ROOT` and `FABULOOM_EXPORT_ROOT`.
4. Run `python .\frontend\server.py --port 8765`.
5. Open `http://127.0.0.1:8765/`.
6. Open Narradores and confirm that Santa V5 is the production reference.
7. Open Prévia and use the transport controls when a local measured manifest is available.
8. Open Exportação to inspect existing local MP4 links. This screen does not render a new video.

## First video status

The current branch does not guarantee that a new user can create a new project and export a new MP4 from the UI. The reproducible video examples are developer-facing Python pipelines documented under `docs/`, and require their own local audio/assets/FFmpeg inputs. Do not describe the existing demo export as a newly created user project.
