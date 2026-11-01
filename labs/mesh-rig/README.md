# Fabuloom Mesh Rig Lab V1

Isolated Mission 016 proof of concept for the Santa V5 right arm. This lab is not the production Character Stage and does not replace the current rigid renderer.

## What is proven

- Godot `Skeleton2D` and a five-bone hierarchy: `Shoulder → UpperArm → Elbow → Forearm → WristHand`.
- A tiled textured mesh made from 96 `Polygon2D` cells, each with four vertices and five normalized bone-weight arrays.
- Real vertex deformation driven by bone transforms; the source image follows the mesh rather than being rotated as a single sprite.
- Five reproducible poses: `rest`, `elbow_45`, `elbow_90`, `hand_raised`, and `pointing`.
- Transparent PNG capture and a deterministic six-second frame sequence for later composition.

The source PNGs under `assets/` are isolated copies of the approved Santa V5 assets. Production assets are not modified. The portable Godot binary is kept outside the repository under `E:\Fabuloom\workspace\tools\godot-4.7.2` and is not committed.

## Run

From `E:\Fabuloom\studio`:

```powershell
$godot = 'E:\Fabuloom\workspace\tools\godot-4.7.2\Godot_v4.7.2-stable_win64_console.exe'
$lab = 'E:\Fabuloom\studio\labs\mesh-rig'
& $godot --rendering-method gl_compatibility --path $lab --editor --quit
& $godot --rendering-method gl_compatibility --path $lab --script res://scripts/capture.gd -- --output 'E:\Fabuloom\workspace\exports\mesh-rig-lab\poses'
& $godot --rendering-method gl_compatibility --path $lab --script res://scripts/capture_board.gd
& $godot --rendering-method gl_compatibility --path $lab --script res://scripts/capture_sequence.gd
& $godot --rendering-method gl_compatibility --path $lab --script res://scripts/capture_transparent.gd
```

The `--headless` driver is useful for syntax checks but cannot provide a render-target texture on this machine. Captures therefore run with the portable executable and Compatibility/OpenGL, using the detected Radeon RX 580.

## Evidence

`mesh-rig-evidence.json` records the hierarchy, grid, weight normalization and measured sample-vertex displacement. Zero displacement is expected in `rest`; the bent poses must be non-zero. No word, phoneme, audio or facial timing is involved in this lab.

The video sequence is made from the same captured mesh frames with FFmpeg; it is not a second animation implementation.

## Alternatives investigated

Godot was selected for the first executable proof because it is self-contained and already provides 2D skeletal deformation. Inochi2D remains an alternative for a later authoring workflow; it was not executed in this mission.
