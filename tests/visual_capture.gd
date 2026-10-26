extends Node
## Scripted visual QA: drives the real game scene and saves screenshots.
## Needs a display:  xvfb-run godot --rendering-driver opengl3 --path . res://tests/visual_capture.tscn -- <out_dir>

var out_dir := "res://tools/preview/out"
var game: Game


func _ready() -> void:
	_run.call_deferred()


func _shot(name: String) -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var path := out_dir.path_join("cap_%s.png" % name)
	img.save_png(path)
	print("CAPTURE ", path)


func _wait(sec: float) -> void:
	await get_tree().create_timer(sec, true, false, true).timeout


func _face(target: Vector3) -> void:
	var p := game.player
	var d := target - p.camera.global_position
	p.rotation.y = atan2(-d.x, -d.z)
	var pitch := rad_to_deg(atan2(d.y, Vector2(d.x, d.z).length()))
	p._pitch = pitch
	p.head.rotation_degrees.x = pitch


func _teleport(pos: Vector3, look: Vector3) -> void:
	game.player.global_position = pos
	game.player.velocity = Vector3.ZERO
	_face(look)


func _run() -> void:
	var a := OS.get_cmdline_user_args()
	if a.size() > 0:
		out_dir = a[0]
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out_dir) if out_dir.begins_with("res://") else out_dir)
	Player.require_mouse_capture = false
	get_tree().root.size = Vector2i(1600, 900)
	game = load("res://scenes/main/game.tscn").instantiate()
	get_tree().root.add_child(game)
	get_tree().current_scene = game
	await _wait(2.5)
	await _shot("01_spawn")
	var box := game.colosseum.get_node("NavigationRegion3D/MysteryBox") as Node3D
	var pap := game.colosseum.get_node("NavigationRegion3D/PackAPunch") as Node3D
	# Mystery box
	_teleport(box.global_position + box.global_basis.z * 2.4, box.global_position + Vector3(0, 0.6, 0))
	await _wait(0.4)
	await _shot("02_box_prompt")
	game.wallet.add(20000)
	box.interact(game.player)
	await _wait(1.6)
	await _shot("03_box_cycling")
	await _wait(2.6)
	await _shot("04_box_offer")
	# weapons
	game.player.weapons.give_weapon(load("res://resources/weapons/m4.tres"))
	_teleport(Vector3(0, 0.1, 8), Vector3(-10, 3, -6))
	await _wait(0.8)
	await _shot("05_m4_hip")
	Input.action_press("aim")
	await _wait(0.6)
	await _shot("06_m4_ads")
	Input.action_release("aim")
	game.player.weapons.give_weapon(load("res://resources/weapons/jupiter.tres"))
	await _wait(1.0)
	await _shot("07_jupiter")
	# Pack-a-Punch
	_teleport(pap.global_position + pap.global_basis.z * 3.0, pap.global_position + Vector3(0, 1.0, 0))
	await _wait(0.5)
	await _shot("08_pap")
	pap.interact(game.player)
	await _wait(1.5)
	await _shot("09_pap_working")
	await _wait(2.2)
	await _shot("10_pap_done")
	# zombies: let them come
	_teleport(Vector3(0, 0.1, 9), Vector3(0, 1.2, -10))
	Engine.time_scale = 3.0
	await _wait(12.0)
	Engine.time_scale = 1.0
	var zs := []
	for zz in get_tree().get_nodes_in_group("zombies"):
		var q := (zz as Node3D).global_position
		if Vector2(q.x / 28.0, q.z / 18.0).length() < 0.95:
			zs.append(zz)
	print("ZOMBIES in arena=", zs.size())
	if zs.size() > 0:
		var z: Node3D = zs[0]
		for zz in zs:
			if (zz as Node3D).global_position.distance_to(game.player.global_position) < z.global_position.distance_to(game.player.global_position):
				z = zz
		_teleport(z.global_position + (game.player.global_position - z.global_position).normalized() * 6.0 + Vector3(0, 0.1, 0), z.global_position + Vector3(0, 1.3, 0))
		await _wait(0.3)
		await _shot("11_zombie_close")
		# fire Jupiter at it
		Input.action_press("fire")
		await _wait(0.12)
		await _shot("12_jupiter_fire")
		Input.action_release("fire")
		await _wait(0.5)
		await _shot("13_after_bolt")
	# overview from the floor and from the terrace
	_teleport(Vector3(-22, 0.1, 6), Vector3(10, 8, -6))
	await _wait(0.5)
	await _shot("14_arena_view")
	game.open_shop(1)
	await _wait(0.5)
	await _shot("15_shop")
	game.shop._on_continue()
	await _wait(0.3)
	game.pause()
	await _wait(0.3)
	await _shot("16_pause")
	game.resume()
	game.player.take_damage(1000.0, Vector3.ZERO)
	await _wait(5.0)
	await _shot("17_game_over")
	print("CAPTURE_DONE")
	get_tree().quit()
