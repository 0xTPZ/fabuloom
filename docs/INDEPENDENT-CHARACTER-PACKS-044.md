# Independent Character Packs — Mission 044

Fabuloom now exposes a versioned, data-only local-pack boundary while preserving the existing Santa V5, Dora, and Alex modules.

## Contract

`frontend/src/character-pack.mjs` continues to validate `fabuloom.character/0.1` and now accepts optional independent metadata: `version`, `author`, `license`, `source`, `compatibility`, and suggested `voice`. Asset licensing is metadata; it is not inherited from the MIT code license. A pack contains only declarative layers, expressions, bindings, and relative asset paths.

## Local loader

`frontend/src/character-pack-loader.mjs` validates a manifest, resolves resources beneath the selected local directory, rejects traversal/absolute/remote paths, reads JSON only, and never imports or executes pack code. Browser discovery uses the File System Access API when available. Missing or malformed manifests are rejected with explicit errors.

## Demonstration

`frontend/assets/characters/community-demo-v1/` is an original geometric pack with MIT metadata and no voice/model. It contains no Topazioverse material. The pack uses the existing `LayeredCharacterRenderer` contract; no second renderer was introduced.

## Compatibility and limits

The implementation is additive. Existing Santa V5 files and identifiers were not moved, copied, relicensed, or modified. This mission adds the loader/contract seam and security tests; it does not yet replace the Studio's hard-coded narrator selector with a complete user-facing pack picker. Browser evidence for a native folder picker therefore remains a limitation of this increment.

Run the Node suite with `node --test frontend/tests/*.mjs`; the Python suite remains unchanged.
