class_name SantaMeshRigArm
extends Node2D

## Mission 016 proof: a textured grid of Polygon2D tiles with real bone weights.
## The official Santa V5 arm is copied into this lab as a texture only; the
## production assets are never edited.

const TEXTURE_SIZE := Vector2(1024.0, 1536.0)
const GRID_COLUMNS := 8
const GRID_ROWS := 12
const BONE_CENTERS := [120.0, 570.0, 1000.0, 1300.0, 1500.0]
const BONE_NAMES := ["Shoulder", "UpperArm", "Elbow", "Forearm", "WristHand"]

var skeleton: Skeleton2D
var bones: Array[Bone2D] = []
var tiles: Array[Polygon2D] = []
var texture: Texture2D
var rest_local_transforms: Array[Transform2D] = []
var current_pose := "rest"

func build(source_texture: Texture2D) -> void:
    texture = source_texture
    skeleton = Skeleton2D.new()
    skeleton.name = "Skeleton2D"
    add_child(skeleton)
    _build_bone_chain()
    _build_weighted_grid()

func _build_bone_chain() -> void:
    var positions := [
        Vector2(455.0, 120.0),
        Vector2(85.0, 440.0),
        Vector2(88.0, 440.0),
        Vector2(48.0, 305.0),
        Vector2(22.0, 250.0),
    ]
    var chain: Array[Bone2D] = []
    for index in BONE_NAMES.size():
        var bone := Bone2D.new()
        bone.name = BONE_NAMES[index]
        bone.position = positions[index]
        bone.length = max(24.0, positions[index].length())
        chain.append(bone)
    for index in range(1, chain.size()):
        chain[index - 1].add_child(chain[index])
    var hand_tip := Bone2D.new()
    hand_tip.name = "HandTip"
    hand_tip.position = Vector2(16.0, 0.0)
    hand_tip.length = 16.0
    hand_tip.rest = hand_tip.transform
    chain[4].add_child(hand_tip)
    skeleton.add_child(chain[0])
    bones = chain
    # In code, the editor's “Overwrite Rest Pose” action is explicit.
    for bone in bones:
        bone.rest = bone.transform

func _build_weighted_grid() -> void:
    for row in GRID_ROWS:
        for column in GRID_COLUMNS:
            var x0 := TEXTURE_SIZE.x * float(column) / float(GRID_COLUMNS)
            var x1 := TEXTURE_SIZE.x * float(column + 1) / float(GRID_COLUMNS)
            var y0 := TEXTURE_SIZE.y * float(row) / float(GRID_ROWS)
            var y1 := TEXTURE_SIZE.y * float(row + 1) / float(GRID_ROWS)
            var vertices := PackedVector2Array([
                Vector2(x0, y0), Vector2(x1, y0), Vector2(x1, y1), Vector2(x0, y1)
            ])
            var uvs := PackedVector2Array([
                Vector2(x0, y0), Vector2(x1, y0), Vector2(x1, y1), Vector2(x0, y1)
            ])
            var tile := Polygon2D.new()
            tile.name = "WeightedTile_%02d_%02d" % [row, column]
            tile.polygon = vertices
            tile.uv = uvs
            tile.texture = texture
            add_child(tile)
            # Resolve paths only after the tile is inside the same scene tree.
            tile.skeleton = tile.get_path_to(skeleton)
            for bone_index in bones.size():
                var weights := PackedFloat32Array()
                for vertex in vertices:
                    weights.append(_weight_for_bone(vertex.y, bone_index))
                tile.add_bone(tile.get_path_to(bones[bone_index]), weights)
            tiles.append(tile)

func _weight_for_bone(y: float, bone_index: int) -> float:
    var center: float = BONE_CENTERS[bone_index]
    var radius: float = 270.0 if bone_index in [0, 4] else 245.0
    var value: float = max(0.0, 1.0 - abs(y - center) / radius)
    var total: float = 0.0
    for candidate in BONE_CENTERS:
        var candidate_radius: float = 270.0 if candidate in [BONE_CENTERS[0], BONE_CENTERS[4]] else 245.0
        total += max(0.0, 1.0 - abs(y - float(candidate)) / candidate_radius)
    if total <= 0.0001:
        return 1.0 if bone_index == _nearest_bone(y) else 0.0
    return value / total

func _nearest_bone(y: float) -> int:
    var nearest := 0
    var distance := INF
    for index in BONE_CENTERS.size():
        var candidate_distance: float = abs(y - float(BONE_CENTERS[index]))
        if candidate_distance < distance:
            nearest = index
            distance = candidate_distance
    return nearest

func capture_rest_reference() -> void:
    rest_local_transforms.clear()
    for bone in bones:
        rest_local_transforms.append(_arm_local_transform(bone))

func set_pose(pose_name: String) -> void:
    current_pose = pose_name
    match pose_name:
        "rest":
            set_pose_values(0.0, 0.0, 0.0, 0.0)
        "elbow_45":
            set_pose_values(-0.04, 0.34, -0.12, 0.0)
        "elbow_90":
            set_pose_values(-0.08, 0.95, -0.24, 0.02)
        "hand_raised":
            set_pose_values(-0.62, 0.42, -0.18, -0.06)
        "pointing":
            set_pose_values(-0.30, 0.70, -0.16, -0.04)
        _:
            set_pose_values(0.0, 0.0, 0.0, 0.0)

func set_pose_values(shoulder_angle: float, elbow_angle: float, forearm_angle: float, hand_angle: float) -> void:
    if bones.size() < 5:
        return
    bones[0].rotation = shoulder_angle
    bones[1].rotation = 0.0
    bones[2].rotation = elbow_angle
    bones[3].rotation = forearm_angle
    bones[4].rotation = hand_angle

func set_pose_at_time(seconds: float) -> String:
    var t := fmod(max(seconds, 0.0), 6.0)
    if t < 1.0:
        set_pose_values(0.0, 0.0, 0.0, 0.0)
        current_pose = "rest"
    elif t < 2.0:
        var amount := smoothstep(0.0, 1.0, t - 1.0)
        set_pose_values(lerp(0.0, -0.04, amount), lerp(0.0, 0.95, amount), lerp(0.0, -0.24, amount), lerp(0.0, 0.02, amount))
        current_pose = "elbow_90"
    elif t < 3.0:
        var amount := smoothstep(0.0, 1.0, t - 2.0)
        set_pose_values(lerp(-0.04, -0.62, amount), lerp(0.95, 0.42, amount), lerp(-0.24, -0.18, amount), lerp(0.02, -0.06, amount))
        current_pose = "hand_raised"
    elif t < 4.0:
        var amount := smoothstep(0.0, 1.0, t - 3.0)
        set_pose_values(lerp(-0.62, -0.30, amount), lerp(0.42, 0.70, amount), lerp(-0.18, -0.16, amount), lerp(-0.06, -0.04, amount))
        current_pose = "pointing"
    else:
        var amount := smoothstep(0.0, 1.0, t - 4.0)
        set_pose_values(lerp(-0.30, 0.0, amount), lerp(0.70, 0.0, amount), lerp(-0.16, 0.0, amount), lerp(-0.04, 0.0, amount))
        current_pose = "rest"
    return current_pose

func _arm_local_transform(bone: Bone2D) -> Transform2D:
    return global_transform.affine_inverse() * bone.global_transform

func _skin_vertex(vertex: Vector2) -> Vector2:
    var result := Vector2.ZERO
    for index in bones.size():
        var current_local := _arm_local_transform(bones[index])
        var delta := current_local * rest_local_transforms[index].affine_inverse()
        result += (delta * vertex) * _weight_for_bone(vertex.y, index)
    return result

func get_pose_trace() -> Dictionary:
    var samples := [Vector2(470.0, 280.0), Vector2(530.0, 620.0), Vector2(620.0, 960.0), Vector2(700.0, 1280.0)]
    var max_displacement := 0.0
    var records: Array[Dictionary] = []
    for sample in samples:
        var deformed := _skin_vertex(sample)
        var displacement: float = sample.distance_to(deformed)
        max_displacement = max(max_displacement, displacement)
        records.append({"rest": {"x": sample.x, "y": sample.y}, "deformed": {"x": deformed.x, "y": deformed.y}, "displacement": displacement})
    return {"pose": current_pose, "max_displacement": max_displacement, "samples": records}

func get_rig_evidence() -> Dictionary:
    var weight_sums: Array[float] = []
    for sample_y in [120.0, 570.0, 1000.0, 1300.0, 1500.0]:
        var sum := 0.0
        for bone_index in bones.size():
            sum += _weight_for_bone(sample_y, bone_index)
        weight_sums.append(sum)
    return {
        "bone_hierarchy": BONE_NAMES,
        "bone_count": bones.size(),
        "polygon_tile_count": tiles.size(),
        "grid": {"columns": GRID_COLUMNS, "rows": GRID_ROWS, "vertices_per_tile": 4},
        "weight_normalization_samples": weight_sums,
        "weighted_bones_per_tile": 5,
        "texture_size": {"width": TEXTURE_SIZE.x, "height": TEXTURE_SIZE.y}
    }
