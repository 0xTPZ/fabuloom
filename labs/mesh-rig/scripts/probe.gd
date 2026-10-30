extends SceneTree

func _init() -> void:
    for class_name_value in ["Polygon2D", "Skeleton2D", "Bone2D", "MeshInstance2D"]:
        print("CLASS ", class_name_value)
        for item in ClassDB.class_get_property_list(class_name_value):
            var name_value: String = String(item.get("name", ""))
            if class_name_value == "Polygon2D" or name_value in ["mesh", "texture", "position", "rotation", "rest", "length"]:
                print("  ", name_value, " type=", item.get("type"), " hint=", item.get("hint"))
    quit()
