# Layered Character Packs (proposal V0.1)

Status: initial contract for Mission 007A, **not yet integrated with the Character Stage renderer**.

## Purpose

Fabuloom characters must be independent of Kokoro, the audio clock, the Canvas backend, and the private Animus/Card Game Studio. A character pack is **data**, not executable code. The existing geometric demo rig remains intact as the compatibility baseline.

## Format

`format: "fabuloom.character/0.1"` identifies the schema family. The v0.1 descriptor contains:

- `id`, `name`: stable identity and display name.
- `layers`: ordered sprite nodes with stable IDs, local asset paths, parent IDs or `null`, normalized `anchor` and `position` pairs, and integer `z` order.
- `expressions`: named replacement sprite assets for specific layers.
- `bindings`: semantic animation channels pointing to layer IDs.

All locations and pivots use normalized coordinates in [0, 1]. This describes **data structure only**; a renderer must explicitly specify transform composition and reference dimensions before rendering production assets.

The current list of animation channels is `head_rotation`, `eye_open`, `mouth_open`, `breathing`, `left_arm`, `right_arm`, `hair_sway`, and `expression`.

### Minimal illustrative descriptor

```json
{
  "format": "fabuloom.character/0.1",
  "id": "narrator-one",
  "name": "Narrator",
  "layers": [
    { "id": "body", "asset": "assets/body.webp", "parent": null, "anchor": [0.5, 0.5], "position": [0.5, 0.75], "z": 0 },
    { "id": "head", "asset": "assets/head.webp", "parent": "body", "anchor": [0.5, 0.8], "position": [0.5, 0.25], "z": 1 },
    { "id": "mouth", "asset": "assets/mouth.png", "parent": "head", "anchor": [0.5, 0.5], "position": [0.5, 0.7], "z": 2 }
  ],
  "expressions": [
    { "id": "neutral", "overrides": {} },
    { "id": "smile", "overrides": { "mouth": "assets/mouth-smile.png" } }
  ],
  "bindings": { "breathing": "body", "head_rotation": "head", "mouth_open": "mouth" }
}
```

## Validation and security

`frontend/src/character-pack.mjs` exports `validateCharacterPack`. It validates a maximum of 128 layers, node uniqueness, acyclic parent references, animation targets, expression overrides, finite normalized coordinates and local sprite paths. External URLs, drive-absolute paths, traversal, backslashes and colon-qualified paths are rejected. SVG assets remain allowed by the descriptor but renderers must apply separate SVG sanitization before loading untrusted packs, or disable SVG imports.

The validator is only a first defense. A future secure importer must enforce archive size/file-count limits, MIME and magic-byte checks, allowed project-local filesystem roots, CSP, asset integrity, image decoding limits, and renderer-specific isolation. Do not assume validation authorizes fetching or executing arbitrary pack content.

## Next implementation steps

1. Confirm the code and node tests run under the project's supported Node version.
2. Specify deterministic transform rules, draw ordering, expression blending and sizes.
3. Implement a separate layered renderer behind an existing Character Stage interface.
4. Supply *licensed, original* layered sprites and a side-by-side toggle against the existing demo rig.
5. Test playback, seek, reduced motion, mobile screens, loading errors and no-regression.
6. Plan a dedicated character pack editor in Mission 007B.

No private Topazioverse art, proprietary Animus code, model weights or personal data should be included by default. The open format should allow contributors to author their own characters.
