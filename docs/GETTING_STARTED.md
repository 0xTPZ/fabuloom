# Getting started

The repository now contains the dependency-free Fabuloom Core V0.1 contracts. There is still no real TTS engine, editor, animation engine, or video compositor.

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

## Future prerequisites

When implementation begins, document exact Python and Node versions, create project-local environments, and verify every dependency license. Do not install anything globally as part of the project.
