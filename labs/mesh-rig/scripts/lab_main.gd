extends Node2D

const ARM_TEXTURE_PATH := "res://assets/santa-v5-arm-right-source.png"
const UPPER_TEXTURE_PATH := "res://assets/santa-v5-upper-arm-right-source.png"
const FOREARM_TEXTURE_PATH := "res://assets/santa-v5-forearm-right-source.png"
const HAND_TEXTURE_PATH := "res://assets/santa-v5-hand-right-source.png"

var mesh_arm: SantaMeshRigArm
var reconstructed: Node2D
var current_pose := "rest"

func _ready() -> void:
    queue_redraw()
    _build_comparison_panels()

func _draw() -> void:
    draw_rect(Rect2(0, 0, 1600, 1000), Color("080b17"))
    draw_rect(Rect2(35, 78, 480, 850), Color("11182b"), true)
    draw_rect(Rect2(560, 78, 480, 850), Color("11182b"), true)
    draw_rect(Rect2(1085, 78, 480, 850), Color("11182b"), true)
    draw_line(Vector2(35, 78), Vector2(1565, 78), Color("d9a441"), 2.0)
    draw_string(ThemeDB.fallback_font, Vector2(50, 48), "FABULOOM MESH RIG LAB V1", HORIZONTAL_ALIGNMENT_LEFT, -1, 30, Color("f2d58a"))
    draw_string(ThemeDB.fallback_font, Vector2(50, 115), "A  Rígido oficial", HORIZONTAL_ALIGNMENT_LEFT, -1, 24, Color("d9e4ff"))
    draw_string(ThemeDB.fallback_font, Vector2(575, 115), "B  Assets reconstruídos", HORIZONTAL_ALIGNMENT_LEFT, -1, 24, Color("d9e4ff"))
    draw_string(ThemeDB.fallback_font, Vector2(1100, 115), "C  Mesh ponderado", HORIZONTAL_ALIGNMENT_LEFT, -1, 24, Color("f2d58a"))
    draw_string(ThemeDB.fallback_font, Vector2(50, 965), "Teclas 1–5: repouso / cotovelo 45° / cotovelo 90° / mão elevada / apontando", HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color("9caaca"))
    draw_string(ThemeDB.fallback_font, Vector2(1100, 965), "Skeleton2D + Polygon2D + pesos por vértice", HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color("9caaca"))

func _build_comparison_panels() -> void:
    var official_texture: Texture2D = load(ARM_TEXTURE_PATH)
    var upper_texture: Texture2D = load(UPPER_TEXTURE_PATH)
    var forearm_texture: Texture2D = load(FOREARM_TEXTURE_PATH)
    var hand_texture: Texture2D = load(HAND_TEXTURE_PATH)
    _add_sprite(official_texture, Vector2(145, 175), 0.25, "OfficialRigid")
    reconstructed = Node2D.new()
    reconstructed.name = "ReconstructedRigidAssets"
    reconstructed.position = Vector2(670, 175)
    reconstructed.scale = Vector2(0.25, 0.25)
    add_child(reconstructed)
    _add_sprite_to(reconstructed, upper_texture, Vector2.ZERO, "UpperArm")
    _add_sprite_to(reconstructed, forearm_texture, Vector2.ZERO, "Forearm")
    _add_sprite_to(reconstructed, hand_texture, Vector2.ZERO, "Hand")
    mesh_arm = SantaMeshRigArm.new()
    mesh_arm.name = "WeightedMeshRig"
    mesh_arm.position = Vector2(1125, 175)
    mesh_arm.scale = Vector2(0.25, 0.25)
    add_child(mesh_arm)
    mesh_arm.build(official_texture)
    mesh_arm.capture_rest_reference()

func _add_sprite(texture: Texture2D, position_value: Vector2, scale_value: float, node_name: String) -> void:
    var sprite := Sprite2D.new()
    sprite.name = node_name
    sprite.texture = texture
    sprite.centered = false
    sprite.position = position_value
    sprite.scale = Vector2(scale_value, scale_value)
    add_child(sprite)

func _add_sprite_to(parent: Node2D, texture: Texture2D, position_value: Vector2, node_name: String) -> void:
    var sprite := Sprite2D.new()
    sprite.name = node_name
    sprite.texture = texture
    sprite.centered = false
    sprite.position = position_value
    parent.add_child(sprite)

func _unhandled_key_input(event: InputEvent) -> void:
    if not event is InputEventKey or not event.pressed:
        return
    var key := event as InputEventKey
    var pose_map := {KEY_1: "rest", KEY_2: "elbow_45", KEY_3: "elbow_90", KEY_4: "hand_raised", KEY_5: "pointing"}
    if pose_map.has(key.keycode):
        current_pose = pose_map[key.keycode]
        mesh_arm.set_pose(current_pose)
