extends SceneTree

const POSES := ["rest", "elbow_45", "elbow_90", "hand_raised", "pointing"]
const ARM_TEXTURE_PATH := "res://assets/santa-v5-arm-right-source.png"

var output_dir := "E:/Fabuloom/workspace/exports/mesh-rig-lab/poses"
var canvas: Node2D
var arm: SantaMeshRigArm
var evidence := {}

func _init() -> void:
    _read_output_arg()
    call_deferred("_capture")

func _read_output_arg() -> void:
    var args := OS.get_cmdline_user_args()
    for index in args.size():
        if args[index] == "--output" and index + 1 < args.size():
            output_dir = args[index + 1]

func _capture() -> void:
    DirAccess.make_dir_recursive_absolute(output_dir)
    canvas = Node2D.new()
    canvas.name = "MeshCaptureCanvas"
    get_root().add_child(canvas)
    arm = SantaMeshRigArm.new()
    arm.name = "SantaV5MeshArm"
    arm.position = Vector2(480, 120)
    arm.scale = Vector2(0.50, 0.50)
    canvas.add_child(arm)
    arm.build(load(ARM_TEXTURE_PATH))
    await process_frame
    arm.capture_rest_reference()
    evidence = {"mission": "016", "tool": "Godot 4.7.2 Skeleton2D/Polygon2D", "texture": "Santa V5 arm-right copied into isolated lab", "poses": [], "transparent_export": true}
    for pose_name in POSES:
        arm.set_pose(pose_name)
        await process_frame
        await process_frame
        var image := get_root().get_viewport().get_texture().get_image()
        var file_path := output_dir.path_join("santa-v5-mesh-%s.png" % pose_name)
        image.save_png(file_path)
        evidence["poses"].append(arm.get_pose_trace())
    evidence["rig"] = arm.get_rig_evidence()
    var evidence_file := FileAccess.open(output_dir.path_join("mesh-rig-evidence.json"), FileAccess.WRITE)
    evidence_file.store_string(JSON.stringify(evidence, "  "))
    evidence_file.close()
    quit()
