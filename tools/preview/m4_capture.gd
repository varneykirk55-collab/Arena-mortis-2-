extends Node
## Fixed-camera captures through the real game and its actual WeaponManager.
## DISPLAY=:99 godot --rendering-method gl_compatibility --rendering-driver opengl3
##   --path . res://tools/preview/m4_capture.tscn -- res://docs/m4_stage1/before

var game: Game

func _ready() -> void:
	_run.call_deferred()

func _frames(count: int) -> void:
	for i in count:
		await get_tree().process_frame

func _shot(folder: String, label: String) -> void:
	await _frames(3)
	await RenderingServer.frame_post_draw
	var path := folder.path_join(label + ".png")
	var err := get_viewport().get_texture().get_image().save_png(path)
	assert(err == OK, "Could not save " + path)
	print("M4_CAPTURE ", path)
	print("M4_RENDER_STATS ", label, " draws=", Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), " triangles=", Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))

func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var folder := args[0] if args.size() else "res://tools/preview/out/m4"
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
	wm.give_weapon(load("res://resources/weapons/m4.tres"))
	wm.set_physics_process(false)
	wm.set_process(false)
	var vm := wm.current_viewmodel()
	vm.cancel_animation()
	# Deterministic framing; identical gameplay data offsets before and after.
	vm.position = wm.current().data.hip_offset
	vm.rotation = Vector3.ZERO
	game.player.camera.fov = 80.0
	await _shot(folder, "hip")
	vm.position = wm.current().data.ads_offset
	game.player.camera.fov = wm.current().data.ads_fov
	await _shot(folder, "ads")
	vm.position = wm.current().data.hip_offset + Vector3(-0.03, -0.04, 0.02)
	vm.rotation = Vector3(0.25, 0.2, 0.55)
	game.player.camera.fov = 80.0
	await _shot(folder, "reload_pose")
	vm.rotation = Vector3.ZERO
	vm.position = wm.current().data.hip_offset
	vm.set_upgraded(true)
	await _shot(folder, "pack_a_punch")
	# Clean side view of the imported GLB, still rendered by Godot.
	game.queue_free()
	await _frames(2)
	var studio := Node3D.new()
	add_child(studio)
	var rifle: Node3D = load("res://assets/models/weapon_m4.glb").instantiate()
	studio.add_child(rifle)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.055, 0.065, 0.08)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.66, 0.76)
	env.environment.ambient_light_energy = 0.65
	studio.add_child(env)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-35, -30, 0)
	key.light_energy = 1.5
	studio.add_child(key)
	var cam := Camera3D.new()
	cam.position = Vector3(0.85, 0.32, 0.1)
	studio.add_child(cam)
	cam.look_at(Vector3(0, -0.015, -0.19))
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 0.58
	cam.current = true
	await _shot(folder, "profile")
	print("M4_CAPTURE_DONE")
	get_tree().quit()
