extends SceneTree

const FPS := 30
const DURATION := 6.0
const OUTPUT_DIR := "E:/Fabuloom/workspace/exports/mesh-rig-lab/sequence"
const ARM_TEXTURE_PATH := "res://assets/santa-v5-arm-right-source.png"

var canvas: Node2D
var arm: SantaMeshRigArm
var manifest := {"fps": FPS, "duration_seconds": DURATION, "frames": [], "source": "same weighted Polygon2D rig as interactive lab"}

func _init() -> void:
    call_deferred("_run")

func _run() -> void:
    DirAccess.make_dir_recursive_absolute(OUTPUT_DIR)
    canvas = Node2D.new()
    get_root().add_child(canvas)
    arm = SantaMeshRigArm.new()
    arm.position = Vector2(440, 110)
    arm.scale = Vector2(0.50, 0.50)
    canvas.add_child(arm)
    arm.build(load(ARM_TEXTURE_PATH))
    await process_frame
    arm.capture_rest_reference()
    for frame in int(DURATION * FPS):
        var seconds := float(frame) / float(FPS)
        var pose_name := arm.set_pose_at_time(seconds)
        await process_frame
        var image := get_root().get_viewport().get_texture().get_image()
        image.save_png(OUTPUT_DIR.path_join("frame_%04d.png" % frame))
        manifest["frames"].append({"frame": frame, "time_seconds": seconds, "pose": pose_name, "trace": arm.get_pose_trace()})
    var file := FileAccess.open(OUTPUT_DIR.path_join("sequence.json"), FileAccess.WRITE)
    file.store_string(JSON.stringify(manifest, "  "))
    file.close()
    quit()
