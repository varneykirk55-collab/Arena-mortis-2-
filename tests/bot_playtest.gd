extends Node
## Automated play session: a simple bot drives the real player through the
## normal game loop (aim, shoot, reload, kite, shop between rounds) to check
## that rounds progress and nothing breaks over a longer session.
##   godot --headless --path . res://tests/bot_playtest.tscn -- [max_rounds] [time_scale]
## This is a stability/flow test, not a balance or "fun" test.

var game: Game
var max_rounds := 5
var time_scale := 3.0
var _toggle := false
var _errors_at_start := 0
var _t := 0.0
var _round_times := {}
var _last_round := 0
var _report: PackedStringArray = []


func _ready() -> void:
	Player.require_mouse_capture = false
	var a := OS.get_cmdline_user_args()
	if a.size() > 0:
		max_rounds = int(a[0])
	if a.size() > 1:
		time_scale = float(a[1])
	_start.call_deferred()


func _start() -> void:
	game = load("res://scenes/main/game.tscn").instantiate()
	get_tree().root.add_child(game)
	get_tree().current_scene = game
	await get_tree().process_frame
	game.wallet.add(0)
	Engine.time_scale = time_scale
	game.waves.round_started.connect(func(r, n): _log("round %d started: %d zombies, hp %.0f" % [r, n, game.waves.config.health_for_round(r)]))
	game.waves.round_completed.connect(func(r): _log("round %d cleared at t=%.0fs  points=%d hp=%.0f kills=%d" % [r, _t, game.wallet.points, game.player.health, game.kills]))
	game.player.died.connect(func(): _log("player died in round %d at t=%.0fs (kills %d)" % [game.waves.round_number, _t, game.kills]))


func _log(s: String) -> void:
	print("BOT ", s)
	_report.append(s)


func _physics_process(delta: float) -> void:
	if game == null or not is_instance_valid(game):
		return
	_t += delta
	var p := game.player
	# shop: buy what we can, then continue
	if game.shop.visible:
		for it in game.wallet.config.shop_items:
			var cost: int = it.cost_for(game.shop.times_bought(it))
			var saving_for_box: bool = game.player.weapons.slots.size() < 2 and game.wallet.points - cost < 1000
			var needs_ammo: bool = it.effect == ShopItem.Effect.AMMO_REFILL and game.player.weapons.current().reserve < 30
			if game.shop.unavailable_reason(it) == "" and (not saving_for_box or needs_ammo):
				game.shop.buy(it)
				_log("  bought %s" % it.display_name)
		if game.waves.round_number >= max_rounds:
			_finish("reached round limit")
			return
		game.shop._on_continue()
		return
	if game.phase == Game.Phase.GAME_OVER:
		_finish("game over")
		return
	if _t > 60.0 * 12.0:
		_finish("time limit")
		return
	if int(_t / 20.0) != int((_t - delta) / 20.0):
		var info := ""
		for z in game.waves.alive:
			if is_instance_valid(z):
				info += "[%s st=%d v=%.1f hp=%.0f] " % [str(z.global_position.snapped(Vector3.ONE * 0.1)), z.state, Vector2(z.velocity.x, z.velocity.z).length(), z.health]
		_log("t=%.0f player=%s alive=%d to_spawn=%d %s" % [_t, str(p.global_position.snapped(Vector3.ONE * 0.1)), game.waves.alive.size(), game.waves.to_spawn, info])
	if not p.is_alive():
		_release_all()
		return
	# Mystery Box: use it once when affordable, while the arena is empty
	var box: MysteryBox = game.colosseum.get_node("NavigationRegion3D/MysteryBox")
	if box.state != MysteryBox.State.IDLE and box._buyer == p:
		_use_box()
		return
	if p.weapons.slots.size() < 2 and game.wallet.points >= 950 and game.waves.alive.size() == 0 and game.phase == Game.Phase.PLAYING:
		_use_box()
		return
	var target := _pick_target()
	if target == null:
		_release_all()
		_wander()
		return
	var dist := p.global_position.distance_to(target.global_position)
	var ads := dist > 3.5 and dist < 26.0
	if ads:
		Input.action_press("aim")
	else:
		Input.action_release("aim")
	var head := target.find_child("HeadHurtbox", true, false) as Node3D
	var aim_point := head.global_position if (ads and head and p.weapons.ads_amount > 0.8) else target.global_position + Vector3(0, 1.15, 0)
	_aim(aim_point)
	# kite: back away when a zombie is close, strafe a little
	Input.action_release("move_forward")
	if dist < 5.0:
		Input.action_press("move_back")
		Input.action_press("move_left" if fmod(_t, 6.0) < 3.0 else "move_right")
	else:
		Input.action_release("move_back")
		Input.action_release("move_left")
		Input.action_release("move_right")
	_avoid_walls()
	var w := p.weapons.current()
	if w.mag == 0:
		Input.action_release("fire")
		if w.reserve == 0 and p.weapons.slots.size() > 1:
			p.weapons.cycle(1)
		return
	if dist < 28.0:
		if w.data.fire_mode == WeaponData.FireMode.AUTO:
			Input.action_press("fire")
		else:
			_toggle = not _toggle
			if _toggle:
				Input.action_press("fire")
			else:
				Input.action_release("fire")
	else:
		Input.action_release("fire")


func _pick_target() -> Zombie:
	var best: Zombie = null
	var best_d := INF
	var space := game.get_world_3d().direct_space_state
	for z in game.waves.alive:
		if not is_instance_valid(z) or not z.is_alive() or z.state == Zombie.State.EMERGE:
			continue
		var d := z.global_position.distance_to(game.player.global_position)
		if d >= best_d:
			continue
		var q := PhysicsRayQueryParameters3D.create(game.player.camera.global_position, z.global_position + Vector3(0, 1.1, 0), Layers.WORLD)
		if space.intersect_ray(q).is_empty():
			best = z
			best_d = d
	return best


func _aim(point: Vector3) -> void:
	var p := game.player
	var d := point - p.camera.global_position
	p.rotation.y = atan2(-d.x, -d.z)
	var pitch := rad_to_deg(atan2(d.y, Vector2(d.x, d.z).length()))
	p._pitch = pitch
	p.head.rotation_degrees.x = pitch


func _avoid_walls() -> void:
	var pos := game.player.global_position
	var e := Vector2(pos.x / 27.0, pos.z / 17.0).length()
	if e > 1.0:
		# too close to the podium wall: walk back toward the middle
		_aim(Vector3(0, 1.5, 0))
		Input.action_release("move_back")
		Input.action_press("move_forward")


func _wander() -> void:
	var pos := game.player.global_position
	if pos.distance_to(Vector3(0, 0, 6)) > 3.0:
		_aim(Vector3(0, 1.6, 6))
		Input.action_press("move_forward")
	else:
		Input.action_release("move_forward")


func _use_box() -> void:
	_release_all()
	var box: MysteryBox = game.colosseum.get_node("NavigationRegion3D/MysteryBox")
	if box.state == MysteryBox.State.IDLE:
		game.player.global_position = box.global_position + box.global_basis.z * 2.0
		_aim(box.global_position + Vector3(0, 0.6, 0))
		box.interact(game.player)
		_log("  opened the Mystery Box (points now %d)" % game.wallet.points)
	elif box.state == MysteryBox.State.OFFERING:
		box.interact(game.player)
		_log("  took %s from the box" % game.player.weapons.current().display_name())


func _release_all() -> void:
	for a in ["fire", "aim", "move_forward", "move_back", "move_left", "move_right", "sprint"]:
		Input.action_release(a)


func _finish(reason: String) -> void:
	_release_all()
	_log("session end (%s): reached round %d, kills %d, headshots %d, points earned %d, game time %.0fs" % [
		reason, game.waves.round_number, game.kills, game.headshots, game.points_earned, _t])
	var f := FileAccess.open("user://bot_playtest.txt", FileAccess.WRITE)
	if f:
		f.store_string("\n".join(_report))
	set_physics_process(false)
	Engine.time_scale = 1.0
	get_tree().paused = false
	print("BOT_DONE")
	get_tree().quit()
