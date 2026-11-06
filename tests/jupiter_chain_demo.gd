extends Node
## Deterministic rendered evidence, NOT a substitute for a human GPU playtest.
## godot --path . res://tests/jupiter_chain_demo.tscn -- /absolute/evidence/directory
var game: Game
var hits := 0

func _ready() -> void:
	_run.call_deferred()

func _run() -> void:
	get_tree().root.scaling_3d_scale = 0.5
	Player.require_mouse_capture = false
	game = load("res://scenes/main/game.tscn").instantiate()
	game.auto_start = false
	get_tree().root.add_child(game)
	get_tree().current_scene = game
	game.player.global_position = Vector3(0, 0.1, 14)
	game.player.weapons.give_weapon(load("res://resources/weapons/jupiter.tres"))
	var targets: Array[Zombie] = []
	for i in 12:
		var z: Zombie = game.waves.zombie_scene.instantiate()
		z.configure(50000, 0, 35, false)
		game.get_node("Zombies").add_child(z)
		z.global_position = Vector3(-3 + (i % 3) * 3, 0.05, 3 - floori(i / 3.0) * 3)
		z.set_physics_process(false)
		targets.append(z)
	game.player.weapons.hit_registered.connect(func(_r): hits += 1)
	for i in 45:
		await get_tree().physics_frame
	var dir: Vector3 = targets[1].get_node("BodyHurtbox/CollisionShape3D").global_position - game.player.camera.global_position
	game.player.rotation.y = atan2(-dir.x, -dir.z)
	game.player.head.rotation.x = atan2(dir.y, Vector2(dir.x, dir.z).length())
	# Overview allows actual enemy-to-enemy links to be inspected unobscured.
	var overview := Camera3D.new()
	game.add_child(overview)
	overview.global_position = Vector3(8, 8, 12)
	overview.look_at(Vector3(0, 1, -1))
	overview.current = true
	var args := OS.get_cmdline_user_args()
	var output := args[0] if not args.is_empty() else "user://"
	for frame in 40:
		if frame == 8:
			game.player.weapons._fire(game.player.weapons.current())
			game.hud.show_message("JUPITER — DIVINE CHAIN", "%d / 12 enemies struck; cap 10" % hits, 4.0)
			print("DEMO: %d unique hit events (12 living candidates)" % hits)
		await get_tree().process_frame
		if frame in [10, 13, 16] and DisplayServer.get_name() != "headless":
			await RenderingServer.frame_post_draw
			get_viewport().get_texture().get_image().save_png(output.path_join("jupiter_chain_%02d.png" % frame))
	game.queue_free()
	await get_tree().process_frame
	await get_tree().process_frame
	get_tree().quit(0 if hits == 10 else 1)
