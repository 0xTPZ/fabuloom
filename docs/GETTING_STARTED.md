# Getting started

This is the documentation-only foundation. There is no editor, TTS runtime, animation engine, or video compositor to run yet.

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

## Future prerequisites

When implementation begins, document exact Python and Node versions, create project-local environments, and verify every dependency license. Do not install anything globally as part of the project.
