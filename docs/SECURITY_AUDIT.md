# Security and portability review

## Reviewed boundaries

- The local server accepts loopback requests only.
- Export paths are checked to remain inside `FABULOOM_WORKSPACE_ROOT`.
- Frontend asset contracts reject traversal/remote asset forms in the tested renderer paths.
- No credentials, model weights, private context, personal audio or production exports were added.
- No global package or Windows configuration was changed.

## Remaining review items

- Review every third-party provider/model license before publishing an Alpha.
- Keep the server and media pipeline local-only unless a future design adds explicit authentication and threat modelling.
- Add a clean-machine test proving that missing manifests produce an actionable empty state rather than a developer-path lookup.
- Audit large files and Git history before publishing the Draft PR.
