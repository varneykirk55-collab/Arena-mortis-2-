extends Node

func _ready() -> void:
	_run.call_deferred()

func _run() -> void:
	Player.require_mouse_capture = false
	var game: Game = load("res://scenes/main/game.tscn").instantiate()
	get_tree().root.add_child(game)
	get_tree().current_scene = game
	await get_tree().create_timer(1.5).timeout
	var pap: PackAPunch = game.colosseum.get_node("NavigationRegion3D/PackAPunch")
	game.wallet.add(10000)
	print("before pts=", game.wallet.points, " cur=", game.player.weapons.current().display_name())
	pap.interact(game.player)
	print("pap state=", pap.state, " weapons state=", game.player.weapons.state)
	await get_tree().create_timer(4.0).timeout
	print("after pap state=", pap.state, " upgraded=", game.player.weapons.current().upgraded, " pts=", game.wallet.points, " wstate=", game.player.weapons.state)
	for i in 10:
		await get_tree().create_timer(2.0).timeout
		var s := ""
		for z in game.waves.alive:
			s += "[%s st=%d v=%.1f d=%.1f] " % [str(z.global_position.snapped(Vector3.ONE * 0.1)), z.state, Vector2(z.velocity.x, z.velocity.z).length(), z.global_position.distance_to(game.player.global_position)]
		print("t=", i * 2, " alive=", game.waves.alive.size(), " group=", get_tree().get_nodes_in_group("zombies").size(), " hp=", game.player.health, " ", s)
	game.player.take_damage(1000.0)
	await get_tree().create_timer(3.5).timeout
	print("phase=", game.phase, " game_over.visible=", game.game_over.visible)
	get_tree().quit()
