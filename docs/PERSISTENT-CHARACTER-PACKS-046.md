# Persistent Character Packs — Mission 046

## Storage model

Installed packs are copied, after explicit UI import, into:

`workspace/packs/<pack-id>/<pack-version>/manifest.json`

and validated image resources below the same directory. The server accepts only PNG, WEBP, and SVG image files, limits a pack to 128 files and 25 MB, rejects traversal/absolute paths, duplicate resources, active SVG markers (`script`, event handlers, `javascript:`, and `foreignObject`), and never executes pack code.

## Project contract

Projects now have an optional `character_pack` reference containing the stable pack ID, pack version, contract version, character ID, selected expression, managed asset reference, license, and author. It contains no absolute user path and no browser permission/token. Legacy projects without this field retain their existing narrator behavior.

On reopen, the Studio reads the project reference, fetches the managed manifest/assets, validates them, and restores the character/expression. If the pack is absent, the reference remains intact and the UI reports that reinstallation is required; it does not substitute Santa V5.

## API boundary

- `POST /api/packs/install`: validates and copies an explicitly selected pack into managed workspace storage.
- `GET /api/packs/<id>/<version>`: returns the persisted manifest.
- `GET /api/packs/<id>/<version>/asset/<relative-path>`: serves only contained installed assets.
- `POST /api/projects/<id>/character-pack`: stores the project reference.

The code license remains separate from each pack's declared art license/provenance.

## Compatibility and limitation

Santa V5, Dora, Alex, their rigs, and existing projects were not moved or relicensed. The real browser session after server restart opened the Studio and preserved the existing interface. The current computer-use connector could not attach a directory to the hidden file input because it does not expose a file chooser `setFiles` operation for this control; backend installation/security tests cover the same file validation path, but a complete native folder-selection capture remains pending.
