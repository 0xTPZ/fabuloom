# Scene Asset Registry V0.1

The Fabuloom production pipeline can reference reusable local visual plates by
stable ID without putting generated media or machine-specific absolute paths in
the public repository.

The public contract is `assets/scene-registry.json`, with format
`fabuloom.scene-asset-registry/0.1`. `src/fabuloom_core/scene_assets.py` loads
the registry, validates IDs and relative paths, keeps resolution inside the
configured Fabuloom workspace, and optionally verifies the declared SHA-256.

## Official Santa library

`santa-library-topazioverse-v1` is the first registered plate. Its binary is
workspace-only at:

`E:/Fabuloom/workspace/exports/official-scenes/santa-library-topazioverse-v1/library-base.png`

The plate contains only the library environment. Santa V5 is composited by the
existing `NarratorAvatarRenderer` during capture, so the same background can be
reused for host openings, closings, and future episodes without regenerating or
baking the character into the scene.

The current artwork is an original conceptual plate generated locally for
Fabuloom and remains `awaiting_human_artistic_approval`. It is not a new
literary canon asset and is not published by Git.

## Example

```python
from fabuloom_core.scene_assets import SceneAssetRegistry

registry = SceneAssetRegistry.from_json(
    "assets/scene-registry.json",
    workspace_root=r"E:\\Fabuloom",
)
library_png = registry.resolve("santa-library-topazioverse-v1")
```

Episode timelines store the ID and an export-relative image path. They never
store an absolute local path. Missing IDs, missing files, traversal attempts,
and hash mismatches fail clearly before rendering.
