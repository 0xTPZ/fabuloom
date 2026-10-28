# Getting started

The repository contains the dependency-free Fabuloom Core V0.1 contracts and
an optional Kokoro PT-BR provider on the Mission 005 integration branch. The
editor, animation engine, and video compositor are not implemented.

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

From `E:\Fabuloom\studio`:

```powershell
python -m unittest discover -s tests -v
python .\examples\contract_demo.py
```

No installation or network access is required for these checks.

The optional Kokoro extra is declared in `pyproject.toml`. Use an existing
local environment with those dependencies and a local model cache for the
offline demonstration; do not add model weights to Git. See
`docs/KOKORO-INTEGRATION.md` for the command and capability limits.

## Future prerequisites

When implementation begins, document exact Python and Node versions, create project-local environments, and verify every dependency license. Do not install anything globally as part of the project.
