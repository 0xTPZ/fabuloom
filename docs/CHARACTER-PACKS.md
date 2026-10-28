# Layered Character Packs (V0.1)

Status: contract and optional Canvas renderer integrated on Mission 007A.1 / PR #4.

## Purpose

Fabuloom characters must be independent of Kokoro, the audio clock, the Canvas backend, and the private Animus/Card Game Studio. A character pack is **data**, not executable code. The existing geometric demo rig remains intact as the compatibility baseline.

## Format

`format: "fabuloom.character/0.1"` identifies the schema family. The v0.1 descriptor contains:

- `id`, `name`: stable identity and display name.
- `layers`: ordered sprite nodes with stable IDs, local asset paths, parent IDs or `null`, normalized `anchor` and `position` pairs, and integer `z` order.
- `expressions`: named replacement sprite assets for specific layers.
- `bindings`: semantic animation channels pointing to layer IDs.

All locations and pivots use normalized coordinates in [0, 1]. The renderer
uses each asset's intrinsic pixel frame as the reference for its children:
`position` selects a point in the parent frame, `anchor` selects the asset
point placed there, `size` (when supplied) scales relative to that frame, and
`z` controls stable back-to-front order. A missing `size` uses a deterministic
renderer default. This keeps the data contract independent of Canvas.

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

## Character Stage integration

`frontend/src/layered-character.ts` provides the optional
`LayeredCharacterRenderer` and `LayeredCharacterRig`. It loads only validated
same-origin local assets, resolves parent transforms, pivots and draw order,
and maps the existing stage signals to head rotation, eye openness, mouth
openness, breathing, hair sway, and expression overrides. The geometric
`CharacterRig` remains available and is selectable beside the layered pack.

The first original demo pack is
`frontend/src/fantasy-narrator-pack.mjs`. Its generated portrait and small
vector animation overlays live under
`frontend/assets/characters/fantasy-narrator/`. The pack is intentionally
provider-independent: it does not import Kokoro, Animus, or the audio player.

The base portrait is currently a polished single illustrated layer with
independent vector accents for the first runtime proof. Full production asset
separation (painted body, head, hair, eyes, mouth, clothing and arms as
independently authored art) remains a future character-authoring task; this
demo does not claim that the generated portrait is a final production pack.

## Validation and security

`frontend/src/character-pack.mjs` exports `validateCharacterPack`. It validates a maximum of 128 layers, node uniqueness, acyclic parent references, animation targets, expression overrides, finite normalized coordinates and local sprite paths. External URLs, drive-absolute paths, traversal, backslashes and colon-qualified paths are rejected. SVG assets remain allowed by the descriptor but renderers must apply separate SVG sanitization before loading untrusted packs, or disable SVG imports.

The validator is only a first defense. A future secure importer must enforce archive size/file-count limits, MIME and magic-byte checks, allowed project-local filesystem roots, CSP, asset integrity, image decoding limits, and renderer-specific isolation. Do not assume validation authorizes fetching or executing arbitrary pack content.

## Next implementation steps

1. Expand the original demo into independently authored body, head, hair, eyes, mouth, clothing and arm assets.
2. Add explicit loading progress and asset integrity metadata.
3. Add stronger image decoding limits and a sandboxed importer for untrusted packs.
4. Test playback, seek, reduced motion, mobile screens, loading errors and no-regression.
5. Plan a dedicated character pack editor in Mission 007B.

No private Topazioverse art, proprietary Animus code, model weights or personal data should be included by default. The open format should allow contributors to author their own characters.
