extends SceneTree

const OUTPUT := "E:/Fabuloom/workspace/exports/mesh-rig-lab/santa-v5-mesh-transparent.png"

func _init() -> void:
    call_deferred("_run")

func _run() -> void:
    get_root().transparent_bg = true
    RenderingServer.set_default_clear_color(Color(0, 0, 0, 0))
    var canvas := Node2D.new()
    get_root().add_child(canvas)
    var arm := SantaMeshRigArm.new()
    arm.position = Vector2(350, 100)
    arm.scale = Vector2(0.50, 0.50)
    canvas.add_child(arm)
    arm.build(load("res://assets/santa-v5-arm-right-source.png"))
    await process_frame
    arm.capture_rest_reference()
    arm.set_pose("elbow_90")
    await process_frame
    var image := get_root().get_viewport().get_texture().get_image()
    image.save_png(OUTPUT)
    quit()
