# Mesh Rig Lab V1 — Mission 016

Mission 016 is an isolated proof of concept for anatomical 2D deformation. It does not replace the production Canvas renderer and it does not modify the official Santa V5 pack.

## Scope

The lab uses a copy of the approved Santa V5 right-arm composite as a texture. The copied texture is subdivided into an 8×12 grid (96 `Polygon2D` tiles). Every tile stores four UV-mapped vertices and five normalized bone-weight arrays. The runtime hierarchy is:

`Shoulder → UpperArm → Elbow → Forearm → WristHand`

The mesh is driven by Godot `Skeleton2D`/`Bone2D` transforms. The source image is not rotated as one rigid sprite. The same weighted mesh is used by the interactive lab, pose captures and the video-frame sequence.

## Reproducible outputs

Generated files stay outside Git under `E:\Fabuloom\workspace\exports\mesh-rig-lab`:

- `poses\santa-v5-mesh-rest.png`
- `poses\santa-v5-mesh-elbow_45.png`
- `poses\santa-v5-mesh-elbow_90.png`
- `poses\santa-v5-mesh-hand_raised.png`
- `poses\santa-v5-mesh-pointing.png`
- `poses\mesh-rig-evidence.json`
- `comparison-board.png`
- `mesh-pose-board.png`
- `santa-v5-mesh-transparent.png`
- `fabuloom-santa-v5-mesh-rig-lab.mp4`

The evidence JSON records the five poses, sampled rest/deformed vertices, maximum displacement, bone hierarchy, grid dimensions, tile count and weight normalization. `rest` is expected to have zero displacement; all four posed states must have non-zero displacement.

## Execution boundary

Godot 4.7.2 stable was downloaded from the official Windows download endpoint and extracted under `E:\Fabuloom\workspace\tools\godot-4.7.2`. It was not installed globally, placed on PATH, or committed. Compatibility/OpenGL was used because the current machine exposes an OpenGL 3.3 Radeon RX 580 path. The official Godot download instructions describe the Windows build as self-contained and runnable after extraction.

The headless dummy driver is retained for syntax/editor validation, but it cannot expose a render-target texture here. Real captures therefore run with the isolated portable executable and the Compatibility renderer. This is an environment limitation, not a simulated render.

## Comparison interpretation

- **A — official rigid:** the approved composite rendered as one rigid sprite.
- **B — reconstructed assets:** copied upper-arm, forearm and hand assets rendered as separate rigid pieces; this remains the Mission 015 raster baseline.
- **C — weighted mesh:** the new Godot proof with vertex deformation and texture-following.

The official production pack and the Mission 015 experiment remain preserved. This lab is experimental and is not an artistic approval of the final Santa V5.

## Alternatives

Godot was selected for the first executable proof because its built-in 2D skeleton workflow directly supports `Skeleton2D`, `Bone2D`, `Polygon2D`, UVs and painted weights. Inochi2D remains an alternative for a future specialist authoring pipeline; it was investigated but not executed in this mission. No Inochi Creator binary or SDK was installed.

## Tests

From `E:\Fabuloom\studio`:

```powershell
node --test frontend/tests/*.mjs
python -m pytest -q
```

The mesh-specific Node test checks the committed lab contract and, when the local evidence exists, verifies the measured non-rigid displacement. The Godot commands are documented in `labs/mesh-rig/README.md`.
