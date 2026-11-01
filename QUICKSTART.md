# Quickstart

## First user workflow

1. Install the project-local environment from [INSTALL.md](INSTALL.md).
2. Run `pwsh -File .\scripts\diagnose.ps1` and resolve missing Python/FFmpeg tools.
3. Set `FABULOOM_WORKSPACE_ROOT` and `FABULOOM_EXPORT_ROOT`.
4. Run `python .\frontend\server.py --port 8765` and open `http://127.0.0.1:8765/`.
5. Create a project, save a short script, and import one image per generated scene.
6. Generate **Santa V5** narration in **Áudio**, use **Prévia**, then export from **Exportação**.
7. Reopen the project from **Projetos**; project JSON, scene assets, narration manifest and exports remain under the configured workspace.

## Scope

The supported Alpha workflow is intentionally small: sentence-based scenes, local image import, Santa V5/`pm_santa`, measured audio preview and horizontal H.264/AAC MP4 export. The Python examples and DEV pages are reference tools, not prerequisites for the basic Studio workflow.
