extends "res://tools/preview/m4_capture.gd"

func _run() -> void:
	var folder := "res://docs/grok_integration/screenshots"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(folder))
	get_tree().root.size = Vector2i(1280, 720)
	Player.require_mouse_capture = false
	game = load("res://scenes/main/game.tscn").instantiate()
	game.auto_start = false
	add_child(game)
	await _frames(2)
	game.waves.stop()
	game.player.set_physics_process(false)
	game.player.global_position = Vector3(0, 0.1, 6)
	game.player.rotation = Vector3.ZERO
	game.player.head.rotation = Vector3.ZERO
	var wm := game.player.weapons
	for id in ["m4", "mk35"]:
		wm.give_weapon(load("res://resources/weapons/%s.tres" % id))
		wm.set_physics_process(false)
		wm.set_process(false)
		var vm := wm.current_viewmodel()
		vm.cancel_animation()
		vm.position = wm.current().data.hip_offset
		vm.rotation = Vector3.ZERO
		game.player.camera.fov = 80
		await _shot(folder, id + "_hip")
		vm.position = wm.current().data.ads_offset
		game.player.camera.fov = wm.current().data.ads_fov
		await _shot(folder, id + "_ads")
		vm.position = wm.current().data.hip_offset
		game.player.camera.fov = 80
		vm.play_reload(wm.current().data.reload_time)
		vm._anim_tween.pause()
		vm._anim_tween.custom_step(wm.current().data.reload_time * 0.30)
		vm.rotation = vm.anim_rotation
		vm.position += vm.anim_offset
		await _shot(folder, id + "_reload")
		vm.cancel_animation()
		vm.rotation = Vector3.ZERO
		vm.position = wm.current().data.hip_offset
		wm.upgrade_current()
		await _shot(folder, id + "_upgraded")
	print("GROK_CAPTURE_DONE")
	game.queue_free()
	await _frames(2)
	get_tree().quit()
