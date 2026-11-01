extends SceneTree

const OUTPUT := "E:/Fabuloom/workspace/exports/mesh-rig-lab/comparison-board.png"

func _init() -> void:
    call_deferred("_run")

func _run() -> void:
    var scene: Node = load("res://main.tscn").instantiate()
    get_root().add_child(scene)
    await process_frame
    await process_frame
    var image := get_root().get_viewport().get_texture().get_image()
    image.save_png(OUTPUT)
    quit()
