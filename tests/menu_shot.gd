extends Node
## Captures the main menu (visual QA).
func _ready() -> void:
	get_tree().root.size = Vector2i(960, 540)
	var m := load("res://scenes/ui/main_menu.tscn").instantiate()
	get_tree().root.add_child.call_deferred(m)
	await get_tree().create_timer(1.0).timeout
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("res://tools/preview/out/menu.png")
	print("MENU_DONE")
	get_tree().quit()
