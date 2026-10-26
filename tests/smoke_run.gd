extends Node
## Boots the game scene and runs it for a while, reporting state each second.
## godot --headless --path . res://tests/smoke_run.tscn -- [seconds]


func _ready() -> void:
	_run.call_deferred()


func _run() -> void:
	var secs := 12.0
	var a := OS.get_cmdline_user_args()
	if a.size() > 0:
		secs = float(a[0])
	Player.require_mouse_capture = false
	var t0 := Time.get_ticks_msec()
	var game: Game = load("res://scenes/main/game.tscn").instantiate()
	get_tree().root.add_child(game)
	get_tree().current_scene = game
	await get_tree().process_frame
	print("SMOKE scene loaded in %d ms" % (Time.get_ticks_msec() - t0))
	var elapsed := 0.0
	while elapsed < secs:
		await get_tree().create_timer(1.0).timeout
		elapsed += 1.0
		print("SMOKE t=%d round=%d alive=%d to_spawn=%d points=%d hp=%.0f nav_polys=%d" % [
			elapsed, game.waves.round_number, game.waves.alive.size(), game.waves.to_spawn,
			game.wallet.points, game.player.health,
			game.colosseum.nav_region.navigation_mesh.get_polygon_count() if game.colosseum.nav_region.navigation_mesh else -1])
	print("SMOKE_DONE")
	get_tree().quit()
