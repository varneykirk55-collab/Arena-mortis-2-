extends Node
var folder: String
var scene: Node3D
var camera: Camera3D

func _ready() -> void:
	_run.call_deferred()

func frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame

func shot(label: String) -> void:
	await frames(2)
	await RenderingServer.frame_post_draw
	var path := folder.path_join(label + ".png")
	assert(get_viewport().get_texture().get_image().save_png(path) == OK)
	print("LEGIONARY_CAPTURE ", path)

func _run() -> void:
	var args := OS.get_cmdline_user_args()
	folder = args[0] if args.size() else "res://docs/legionary_stage1/after"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(folder))
	get_tree().root.size = Vector2i(1000, 1000)
	var packed: PackedScene = load("res://assets/models/zombie_legionary.glb")
	if args.size() > 1 and args[1] == "original":
		var doc := GLTFDocument.new()
		var state := GLTFState.new()
		assert(doc.append_from_file(ProjectSettings.globalize_path("res://assets/sources/legionary_stage1/original_legionary.glb"),state) == OK)
		var original := doc.generate_scene(state)
		for mi: MeshInstance3D in original.find_children("*","MeshInstance3D",true,false):
			for i in mi.mesh.get_surface_count():
				var mat := mi.mesh.surface_get_material(i)
				var path := "res://resources/materials/" + mat.resource_name + ".tres"
				if ResourceLoader.exists(path):
					mi.mesh.surface_set_material(i,load(path))
		packed = PackedScene.new()
		assert(packed.pack(original) == OK)
		original.free()
	scene = packed.instantiate()
	add_child(scene)
	var anim := scene.find_child("AnimationPlayer", true, false) as AnimationPlayer
	anim.play("Idle")
	anim.seek(0.4, true)
	anim.pause()
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.065, 0.075, 0.09)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.7, 0.75, 0.85)
	env.environment.ambient_light_energy = 0.55
	add_child(env)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-25,-30,0)
	key.light_energy = 1.6
	add_child(key)
	camera = Camera3D.new()
	add_child(camera)
	camera.current = true
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 2.15
	for pair in [["front",Vector3(0,1.1,4)],["back",Vector3(0,1.1,-4)],["three_quarter",Vector3(2.7,1.35,3.4)]]:
		camera.position = pair[1]
		camera.look_at(Vector3(0,0.95,0))
		await shot(pair[0])
	camera.size = 0.52
	camera.position = Vector3(0.25,1.72,1.2)
	camera.look_at(Vector3(0,1.69,0))
	await shot("face_helmet")
	scene.queue_free()
	env.queue_free()
	key.queue_free()
	camera.queue_free()
	await frames(2)
	get_tree().root.size = Vector2i(1280,720)
	Player.require_mouse_capture = false
	var game: Game = load("res://scenes/main/game.tscn").instantiate()
	game.auto_start = false
	add_child(game)
	game.waves.stop()
	game.player.set_physics_process(false)
	game.player.weapons.set_physics_process(false)
	game.player.weapons.set_process(false)
	game.player.weapons._pivot.visible = false
	var zombie: Zombie = load("res://scenes/zombies/zombie.tscn").instantiate()
	zombie.model_scenes = [packed]
	zombie.configure(150,1.25,35,false)
	game.get_node("Zombies").add_child(zombie)
	zombie.set_physics_process(false)
	zombie.position = Vector3(-8,0.05,6)
	zombie.get_node("Model").scale = Vector3.ONE
	zombie._anim.play("Walk")
	zombie._anim.seek(0.25,true)
	zombie._anim.pause()
	game.player.global_position = Vector3(-8,0.1,11)
	game.player.rotation = Vector3.ZERO
	game.player.camera.global_position = Vector3(-8,1.65,11)
	game.player.camera.look_at(Vector3(-8,1.05,6))
	await shot("combat_distance")
	game.player.camera.global_position = Vector3(-7.3,1.6,8.8)
	game.player.camera.look_at(Vector3(-8,1.05,6))
	await shot("colosseum_lighting")
	print("LEGIONARY_CAPTURE_DONE")
	game.queue_free()
	await frames(2)
	get_tree().quit()
