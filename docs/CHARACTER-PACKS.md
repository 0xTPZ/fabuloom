# Layered Character Packs (V0.1)

Status: contract and optional Canvas renderer refined on Mission 007A.2 / PR #4.

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

The current list of animation channels is `head_rotation`, `eye_open`, `mouth_open`, `breathing`, `left_arm`, `right_arm`, `hair_sway`, `brow_raise`, and `expression`.

The channel target is a layer ID, not a global character transform. For example,
`head_rotation` targets `head`, so the torso remains fixed while child facial
layers inherit the head pivot. `left_arm` and `right_arm` target the upper-arm
nodes; forearms and hands inherit those transforms through the parent chain.

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

The original demo pack is `frontend/src/fantasy-narrator-pack.mjs`. Its
illustrated torso and head assets plus local vector layer assets live under
`frontend/assets/characters/fantasy-narrator/`. The pack is intentionally
provider-independent: it does not import Kokoro, Animus, or the audio player.

Mission 007A.2 adds an explicit anatomical hierarchy: torso, neck, head,
back/front hair, eyes, eyelids, brows, mouth, upper arms, forearms, hands and
an accessory. Ari's torso and head are separate original generated assets;
the arm sleeves are isolated local crops of the same original costume source,
while facial accents, hair motion and hands are independent SVG layers. This
is a functional runtime rig and an asset-authoring bridge, not a claim that
every painted pixel is production-ready for a final long-form character pack.

### Official narrator trio

Mission 009 adds three intentionally simple official demonstrators:

| Pack | Kokoro voice metadata | Role |
| --- | --- | --- |
| Dora | `pf_dora` | welcoming, serene narrator |
| Santa | `pm_santa` | mature, wise narrator |
| Alex | `pm_alex` | young, confident narrator |

The packs live in `frontend/src/topazio-narrator-packs.mjs` and reuse the
provider-neutral v0.1 contract. Their original transparent portraits are in
`frontend/assets/characters/topazio-narrators/`; they share a navy, pale-blue,
and gold uniform language with a subtle gem ornament. The three character
choices are the primary stage demonstrators, while Ari and Lia remain
references for the richer and geometric rigs.

These assets are a maintainable visual foundation, not final production art.
The editor and external character-pack import remain outside this mission.

## Validation and security

`frontend/src/character-pack.mjs` exports `validateCharacterPack`. It validates a maximum of 128 layers, node uniqueness, acyclic parent references, animation targets, expression overrides, finite normalized coordinates and local sprite paths. External URLs, drive-absolute paths, traversal, backslashes and colon-qualified paths are rejected. SVG assets remain allowed by the descriptor but renderers must apply separate SVG sanitization before loading untrusted packs, or disable SVG imports.

The validator is only a first defense. A future secure importer must enforce archive size/file-count limits, MIME and magic-byte checks, allowed project-local filesystem roots, CSP, asset integrity, image decoding limits, and renderer-specific isolation. Do not assume validation authorizes fetching or executing arbitrary pack content.

## Next implementation steps

1. Replace the arm crop bridge and vector facial accents with independently authored painted layers when the art pipeline is ready.
2. Add explicit loading progress and asset integrity metadata.
3. Add stronger image decoding limits and a sandboxed importer for untrusted packs.
4. Test playback, seek, reduced motion, mobile screens, loading errors and no-regression.
5. Plan a dedicated character pack editor in Mission 007B.

No private Topazioverse art, proprietary Animus code, model weights or personal data should be included by default. The open format should allow contributors to author their own characters.
