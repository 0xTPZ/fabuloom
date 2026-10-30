# Animation engine research — Mission 012.8

This is a bounded research record for the Santa V5 visual-integrity audit. No
external runtime was installed, no private project was copied, and no asset
was uploaded.

## Evidence and comparison

| Option | What it offers | Fabuloom fit now | Main cost/risk | License checked |
| --- | --- | --- | --- | --- |
| Current Canvas `LayeredCharacterRenderer` | Deterministic PNG cut-out layers, explicit pivots/parents/z-order, browser Stage and frame capture share one plan | Best fit for the existing V5 assets and FFmpeg boundary | Rigid pieces; no mesh deformation or weight painting | Fabuloom code boundary |
| [Godot 2D skeletons](https://docs.godotengine.org/en/stable/tutorials/animation/2d_skeletons.html) | `Skeleton2D`/`Bone2D` with `Polygon2D`/UV mapping and engine-side animation; official docs describe built-in skeletal deformation and performance benefits | Promising future runtime if V5 evolves to weighted meshes or a Godot-native creator | New project/runtime boundary, asset import and browser/export integration; Godot is not installed on this machine | [Godot MIT license](https://raw.githubusercontent.com/godotengine/godot/master/LICENSE.txt) |
| [Inochi2D SDK](https://github.com/Inochi2D/inochi2d) + [Inochi Creator](https://github.com/Inochi2D/inochi-creator) | Specialist 2D character rigging/deformation workflow and a dedicated SDK/application | Promising authoring PoC for expressive 2D faces and mesh deformation | Requires a pack/format bridge, runtime embedding or offline export, and an asset provenance policy; neither executable is installed | [SDK BSD-2-Clause](https://raw.githubusercontent.com/Inochi2D/inochi2d/main/LICENSE), [Creator BSD-2-Clause](https://raw.githubusercontent.com/Inochi2D/inochi-creator/main/LICENSE) |
| [Blender Grease Pencil](https://docs.blender.org/manual/en/latest/grease_pencil/) + [armature modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/armature.html) | 2D strokes, cut-out/deformation workflows, armatures and scripted offline rendering; the manual documents armature-driven deformation | Useful offline authoring/render fallback for a later production pipeline | Heavy dependency and a new scene/export path; GPL obligations for Blender/scripts need deliberate distribution review; Blender is not installed | [Blender license](https://www.blender.org/about/license/) |

### Recommendation

Keep the current Canvas renderer for the Stage and deterministic exporter while
the art is still transparent, rigid, and pivot-based. The immediate defect was
asset composition and eyelid opacity, and both are now fixed at the existing
boundary. Evaluate Godot first if the product requires a browser/runtime with
weighted 2D bones; evaluate Inochi2D first if the priority becomes specialist
2D rig authoring; reserve Blender for offline production when the team accepts
the larger toolchain and license review. A migration should be driven by a
measured need for deformation, not by the facial duplication bug.

### Machine check and PoC status

Read-only executable discovery on 2026-10-30 found no `blender`, `godot`,
`inochi-creator` or `inochi2d` command on `PATH`. Therefore no external-tool
PoC was run. The in-repository QA page and renderer plan use only copied/local
Fabuloom assets and provide the reproducible evidence needed before choosing a
new runtime. A future PoC must stay under `E:\Fabuloom`, use a copied asset
set, export transparent frames, and compare the same pose samples against the
Canvas reference.

### Metrics used for this decision

The current path was checked on the actual V5 pack at 1080×1920: the face
layers are unique and ordered, the open/blink opacity states are deterministic,
the wrist pivots stay attached to their forearm chains, the foot pivots remain
below their shin joins, and repeated out-of-order samples produce identical
plans. This is enough for the current rigid-layer requirement; it is not a
claim of mesh-deformation quality.
