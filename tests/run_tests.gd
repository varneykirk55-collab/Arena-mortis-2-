extends Node
## Arena Mortis automated test suite.
##   godot --headless --path . res://tests/run_tests.tscn
## Runs unit tests on the data/logic classes and integration tests that drive
## the real game scene (shooting, zombies, waves, economy, machines, shop,
## death + restart). Exit code 0 = all passed.

var _passed := 0
var _failed := 0
var _current := ""
var _log: PackedStringArray = []
var game: Game


func _ready() -> void:
	Player.require_mouse_capture = false
	_run_all.call_deferred()


func check(cond: bool, msg: String) -> void:
	if cond:
		_passed += 1
	else:
		_failed += 1
		var line := "  FAIL [%s] %s" % [_current, msg]
		_log.append(line)
		print(line)


func _run_all() -> void:
	var tests := [
		"test_weapon_resources", "test_weapon_instance_logic", "test_damage_falloff", "test_wallet",
		"test_shop_items", "test_wave_config", "test_mystery_box_roll", "test_model_imports",
		"test_scenes_instantiate", "test_navigation_baked", "test_shoot_and_kill_zombie", "test_headshot_bonus",
		"test_jupiter_precision", "test_reload", "test_mystery_box_flow", "test_pack_a_punch_flow",
		"test_shop_purchases", "test_zombie_attacks_player", "test_wave_progression", "test_death_and_restart",
	]
	for t in tests:
		_current = t
		var before := _failed
		var t0 := Time.get_ticks_msec()
		await call(t)
		var status := "PASS" if _failed == before else "FAIL"
		var line := "%s  %s  (%d ms)" % [status, t, Time.get_ticks_msec() - t0]
		_log.append(line)
		print(line)
	await _teardown_game()
	var summary := "TESTS DONE: %d checks passed, %d failed" % [_passed, _failed]
	_log.append(summary)
	print(summary)
	var f := FileAccess.open("user://test_results.txt", FileAccess.WRITE)
	if f:
		f.store_string("\n".join(_log))
	get_tree().quit(0 if _failed == 0 else 1)


# ------------------------------------------------------------------ helpers

func _frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _secs(s: float) -> void:
	await get_tree().create_timer(s, true, false, true).timeout


## Waits `s` seconds of *game* time (physics ticks), robust to slow frames.
func _game_secs(s: float) -> void:
	await _frames(int(ceil(s * Engine.physics_ticks_per_second / max(Engine.time_scale, 0.01))))


func _process_frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func _new_game() -> Game:
	await _teardown_game()
	Engine.time_scale = 1.0
	game = load("res://scenes/main/game.tscn").instantiate()
	game.start_round = 1
	game.auto_start = false
	get_tree().root.add_child(game)
	get_tree().current_scene = game
	await _frames(3)
	game.waves.stop()            # tests control spawning explicitly
	return game


func _teardown_game() -> void:
	get_tree().paused = false
	Engine.time_scale = 1.0
	if game and is_instance_valid(game):
		game.queue_free()
		await _frames(2)
	game = null


func _spawn_zombie(pos: Vector3, hp := 150.0, speed := 0.0) -> Zombie:
	var z: Zombie = game.waves.zombie_scene.instantiate()
	z.configure(hp, speed, 35.0, false)
	game.get_node("Zombies").add_child(z)
	z.global_position = pos
	z.died.connect(game.waves._on_zombie_died)
	game.waves.alive.append(z)
	return z


func _aim_at(target: Vector3) -> void:
	var p := game.player
	var d := target - p.camera.global_position
	p.rotation.y = atan2(-d.x, -d.z)
	var pitch := rad_to_deg(atan2(d.y, Vector2(d.x, d.z).length()))
	p._pitch = pitch
	p.head.rotation_degrees.x = pitch
	p._recoil = Vector2.ZERO


func _place_player(pos: Vector3) -> void:
	game.player.global_position = pos
	game.player.velocity = Vector3.ZERO


func _fire_once() -> void:
	var wm := game.player.weapons
	wm._cooldown = 0.0
	wm.state = WeaponManager.State.READY
	wm._fire(wm.current())


func _load_weapon(id: String) -> WeaponData:
	return load("res://resources/weapons/%s.tres" % id)


# ------------------------------------------------------------------ unit tests

func test_weapon_resources() -> void:
	for id in ["pistol", "m4", "jupiter", "mk35"]:
		var w := _load_weapon(id)
		check(w != null, "%s loads" % id)
		check(w.damage > 0 and w.fire_rate > 0 and w.magazine_size > 0 and w.reserve_ammo > 0, "%s has sane stats" % id)
		check(w.reload_time > 0 and w.effective_range > 0, "%s reload/range" % id)
		check(w.fire_sound != null and w.reload_sound != null, "%s has audio" % id)
		var vm: Node = w.viewmodel_scene.instantiate()
		for n in ["Muzzle", "RightHand", "LeftHand", "Magazine"]:
			check(vm.find_child(n, true, false) != null, "%s model has %s" % [id, n])
		vm.free()
	var j := _load_weapon("jupiter")
	check(j.projectile == WeaponData.Projectile.LIGHTNING, "Jupiter fires lightning")
	check(j.hip_spread_deg == 0.0 and j.ads_spread_deg == 0.0, "Jupiter has no spread (precision)")
	check(j.magazine_size <= 5 and j.reserve_ammo <= 20, "Jupiter ammo is limited")
	check(j.fire_rate <= 1.0, "Jupiter has a deliberate cadence")


func test_weapon_instance_logic() -> void:
	var w := WeaponInstance.new(_load_weapon("pistol"))
	check(w.mag == 8 and w.reserve == w.data.reserve_ammo, "starts with full mag + reserve")
	for i in 3:
		w.consume_round()
	check(w.mag == 5, "firing consumes rounds")
	check(w.can_reload(), "can reload a partial mag")
	var loaded := w.finish_reload()
	check(loaded == 3 and w.mag == 8 and w.reserve == w.data.reserve_ammo - 3, "reload moves exactly the missing rounds")
	w.reserve = 2
	w.mag = 0
	w.finish_reload()
	check(w.mag == 2 and w.reserve == 0, "reload limited by reserve")
	check(not w.can_reload(), "cannot reload with empty reserve")
	w.mag = 0
	check(not w.consume_round(), "cannot fire an empty magazine")
	var base_dmg := w.base_damage()
	var base_mag := w.magazine_size()
	check(w.apply_upgrade(), "first upgrade applies")
	check(w.upgraded and w.base_damage() > base_dmg and w.magazine_size() > base_mag, "upgrade changes damage and capacity")
	check(w.mag == w.magazine_size() and w.reserve == w.max_reserve(), "upgrade refills ammo")
	check(not w.apply_upgrade(), "only one upgrade tier")
	check(w.display_name() == "Mars Ultor", "upgraded name")


func test_damage_falloff() -> void:
	var w := WeaponInstance.new(_load_weapon("m4"))
	check(is_equal_approx(w.damage_at(5.0), w.base_damage()), "full damage in effective range")
	check(w.damage_at(w.data.max_range) < w.base_damage(), "falloff at max range")
	check(w.damage_at(w.data.max_range) >= w.base_damage() * w.data.min_damage_factor - 0.01, "falloff floor respected")


func test_wallet() -> void:
	var cfg: EconomyConfig = load("res://resources/economy/economy_config.tres")
	var wal := PointsWallet.new()
	wal.config = cfg
	add_child(wal)
	check(wal.points == cfg.starting_points, "starting points from config")
	check(not wal.try_spend(cfg.starting_points + 1), "cannot overspend")
	check(wal.points == cfg.starting_points, "failed purchase leaves balance untouched")
	check(wal.try_spend(200), "affordable purchase succeeds")
	check(wal.points == cfg.starting_points - 200, "purchase deducts exact cost")
	wal.add(90)
	check(wal.points == cfg.starting_points - 110, "points added")
	check(not wal.try_spend(-5) or wal.points >= 0, "negative cost rejected")
	wal.queue_free()


func test_shop_items() -> void:
	var cfg: EconomyConfig = load("res://resources/economy/economy_config.tres")
	check(cfg.shop_items.size() == 3, "three shop items configured")
	var effects := {}
	for it in cfg.shop_items:
		effects[it.effect] = it
	check(effects.has(ShopItem.Effect.MAX_HEALTH) and effects.has(ShopItem.Effect.AMMO_REFILL) and effects.has(ShopItem.Effect.DAMAGE), "health, ammo and damage items exist")
	var hp: ShopItem = effects[ShopItem.Effect.MAX_HEALTH]
	check(hp.cost_for(1) == hp.base_cost + hp.cost_step, "cost escalates")
	check(hp.is_maxed(hp.max_purchases), "max purchases enforced")


func test_wave_config() -> void:
	var c: WaveConfig = load("res://resources/waves/wave_config.tres")
	var prev_n := 0
	var prev_h := 0.0
	for r in range(1, 21):
		var n := c.zombies_for_round(r)
		var h := c.health_for_round(r)
		check(n > prev_n, "round %d has more zombies (%d)" % [r, n])
		check(h > prev_h, "round %d zombies are tougher (%.0f)" % [r, h])
		prev_n = n
		prev_h = h
	check(c.run_chance(1) == 0.0 and c.run_chance(8) > 0.3, "runners appear in later rounds")
	check(c.spawn_interval(40) >= c.spawn_interval_min, "spawn interval clamped")
	check(c.max_active > 0 and c.max_active < 40, "active-enemy cap set")


func test_mystery_box_roll() -> void:
	var pool: Array[WeaponData] = [_load_weapon("m4"), _load_weapon("jupiter")]
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var counts := {"m4": 0, "jupiter": 0}
	var n := 20000
	for i in n:
		var w := MysteryBox.roll(pool, rng)
		counts[String(w.id)] += 1
	var jr := float(counts["jupiter"]) / n
	print("    box roll: jupiter %.1f%%, m4 %.1f%%" % [jr * 100.0, 100.0 - jr * 100.0])
	check(jr > 0.08 and jr < 0.17, "Jupiter is rare (%.1f%%)" % (jr * 100.0))
	check(counts["m4"] > counts["jupiter"] * 4, "ordinary weapons far more common")


func test_model_imports() -> void:
	for z in ["zombie_legionary", "zombie_gladiator"]:
		var inst: Node = load("res://assets/models/%s.glb" % z).instantiate()
		var ap: AnimationPlayer = inst.find_child("AnimationPlayer", true, false)
		check(ap != null, "%s has AnimationPlayer" % z)
		if ap:
			for a in ["Idle", "Walk", "Run", "Attack", "Hit", "Death", "Emerge"]:
				check(ap.has_animation(a), "%s has %s animation" % [z, a])
		var sk: Skeleton3D = inst.find_child("Skeleton3D", true, false)
		check(sk != null and sk.find_bone("Head") >= 0, "%s has a skeleton with a Head bone" % z)
		inst.free()
	for m in ["colosseum_floor", "colosseum_podium", "colosseum_obstacles"]:
		var inst: Node = load("res://assets/models/%s.glb" % m).instantiate()
		check(inst.find_children("*", "StaticBody3D", true, false).size() > 0, "%s generates collision" % m)
		inst.free()
	for m in ["colosseum_cavea", "mystery_box", "pack_a_punch", "brazier_tall", "torch_sconce", "banner",
			"statue_legionary", "statue_gladiator", "weapon_pistol", "weapon_m4", "weapon_jupiter", "viewmodel_arms"]:
		var inst: Node = load("res://assets/models/%s.glb" % m).instantiate()
		var meshes := inst.find_children("*", "MeshInstance3D", true, false)
		check(meshes.size() > 0, "%s imports with meshes" % m)
		var remapped := false
		for mi in meshes:
			var mesh: Mesh = (mi as MeshInstance3D).mesh
			if mesh and mesh.get_surface_count() > 0 and mesh.surface_get_material(0) and mesh.surface_get_material(0).resource_path.begins_with("res://resources/materials/"):
				remapped = true
			if m == "weapon_m4" and mesh:
				var mat := mesh.surface_get_material(0) as StandardMaterial3D
				remapped = mat != null and mat.albedo_texture != null and mat.normal_texture != null and mat.roughness_texture != null and mat.metallic_texture != null
		check(remapped, "%s materials remapped to project materials" % m)
		inst.free()
	var mb: Node = load("res://assets/models/mystery_box.glb").instantiate()
	check(mb.find_child("Lid", true, false) != null, "Mystery Box has an animated Lid node")
	mb.free()


func test_scenes_instantiate() -> void:
	for s in ["res://scenes/ui/main_menu.tscn", "res://scenes/player/player.tscn", "res://scenes/zombies/zombie.tscn",
			"res://scenes/interactables/mystery_box.tscn", "res://scenes/interactables/pack_a_punch.tscn",
			"res://scenes/colosseum/colosseum.tscn", "res://scenes/main/game.tscn"]:
		var ps: PackedScene = load(s)
		check(ps != null and ps.can_instantiate(), "%s can be instantiated" % s)


func test_navigation_baked() -> void:
	await _new_game()
	var nm := game.colosseum.nav_region.navigation_mesh
	check(nm != null and nm.get_polygon_count() > 20, "navigation mesh baked (%d polys)" % (nm.get_polygon_count() if nm else 0))
	await _frames(4)
	var map := game.get_world_3d().navigation_map
	var gates := get_tree().get_nodes_in_group("zombie_spawn")
	check(gates.size() == 6, "six zombie spawn gates")
	for g in gates:
		var path := NavigationServer3D.map_get_path(map, (g as Node3D).global_position, Vector3(0, 0, 6), true)
		check(path.size() > 1 and path[path.size() - 1].distance_to(Vector3(0, 0, 6)) < 1.5, "path from %s to the arena centre" % g.name)


# ------------------------------------------------------------------ integration

func test_shoot_and_kill_zombie() -> void:
	await _new_game()
	_place_player(Vector3(0, 0.1, 10))
	var z := _spawn_zombie(Vector3(0, 0.05, 4), 150.0)
	await _frames(70)            # emerge + physics registration
	var pts0 := game.wallet.points
	Input.action_press("aim")
	await _frames(20)
	var shots := 0
	while z.is_alive() and shots < 12:
		_aim_at(z.global_position + Vector3(0, 1.0, 0))
		await _frames(2)
		_fire_once()
		shots += 1
		await _frames(3)
	Input.action_release("aim")
	check(not z.is_alive(), "zombie killed by pistol fire (%d shots)" % shots)
	check(shots >= 3, "150 HP zombie needs several 45-damage body shots (%d)" % shots)
	var cfg := game.wallet.config
	var expected := pts0 + shots * cfg.points_per_hit + cfg.points_per_kill
	check(game.wallet.points == expected, "points: %d expected %d" % [game.wallet.points, expected])
	check(game.player.weapons.current().mag == 8 - shots, "ammo consumed")
	check(game.waves.alive.is_empty(), "dead zombie removed from tracking")
	await _secs(6.5)
	check(not is_instance_valid(z), "corpse removed from the scene after sinking")


func test_headshot_bonus() -> void:
	await _new_game()
	_place_player(Vector3(0, 0.1, 10))
	var z := _spawn_zombie(Vector3(0, 0.05, 6), 100.0)
	await _frames(70)
	var pts0 := game.wallet.points
	Input.action_press("aim")
	await _frames(20)
	var head := z.find_child("HeadHurtbox", true, false) as Node3D
	_aim_at(head.global_position)
	await _frames(2)
	_fire_once()
	await _frames(3)
	Input.action_release("aim")
	check(not z.is_alive(), "single pistol headshot kills a 100 HP zombie (45 x 2.5)")
	check(game.wallet.points == pts0 + game.wallet.config.points_per_hit + game.wallet.config.points_per_headshot_kill, "headshot kill bonus awarded")
	check(game.headshots == 1, "headshot counted")


func test_jupiter_precision() -> void:
	await _new_game()
	_place_player(Vector3(0, 0.1, 12))
	game.player.weapons.give_weapon(_load_weapon("jupiter"))
	await _frames(50)
	var a := _spawn_zombie(Vector3(-1.0, 0.05, 2), 5000.0)
	var b := _spawn_zombie(Vector3(1.0, 0.05, 2), 5000.0)
	await _frames(70)
	# miss: aim 1.5 m beside zombie A -> nobody is hurt (no auto-aim, no splash)
	_aim_at(a.global_position + Vector3(-2.2, 1.0, 0))
	await _frames(2)
	_fire_once()
	await _frames(3)
	check(a.health == 5000.0 and b.health == 5000.0, "a missed bolt hurts nobody")
	# direct hit on A must not chain to B
	_aim_at(a.global_position + Vector3(0, 1.0, 0))
	await _frames(2)
	_fire_once()
	await _frames(3)
	check(a.health < 5000.0, "a direct bolt damages its target")
	check(a.health <= 5000.0 - 2000.0, "Jupiter hits hard (%.0f left)" % a.health)
	check(b.health == 5000.0, "the bolt does not chain to the neighbour")
	check(game.player.weapons.current().mag == 1, "limited Jupiter ammo consumed")


func test_reload() -> void:
	await _new_game()
	var wm := game.player.weapons
	var w := wm.current()
	w.mag = 2
	wm.state = WeaponManager.State.READY
	wm.reload()
	check(wm.state == WeaponManager.State.RELOADING, "reload starts")
	await _game_secs(w.data.reload_time + 0.3)
	check(w.mag == w.magazine_size() and wm.state == WeaponManager.State.READY, "reload completes and refills magazine")


func test_mystery_box_flow() -> void:
	await _new_game()
	var box: MysteryBox = game.colosseum.get_node("NavigationRegion3D/MysteryBox")
	check(box != null, "Mystery Box placed in the Colosseum")
	_place_player(box.global_position + box.global_basis.z * 2.0)
	_aim_at(box.global_position + Vector3(0, 0.6, 0))
	await _process_frames(4)
	check(game.player.interactor.focused == box, "box is focused when approached")
	check(box.get_prompt(game.player).contains("not enough points"), "prompt explains missing points")
	var pts := game.wallet.points
	box.interact(game.player)
	check(box.state == MysteryBox.State.IDLE and game.wallet.points == pts, "box refuses without enough points and charges nothing")
	game.wallet.add(2000)
	pts = game.wallet.points
	box.interact(game.player)
	check(game.wallet.points == pts - box.cost(), "box charges its cost")
	check(box.state == MysteryBox.State.CYCLING, "box opens and cycles")
	await _game_secs(box.cycle_time + 0.4)
	await _process_frames(3)
	check(box.state == MysteryBox.State.OFFERING and box.selected != null, "box offers a weapon")
	var offered := box.selected
	check(box.get_prompt(game.player).contains(offered.display_name), "prompt names the offered weapon")
	box.interact(game.player)
	check(game.player.weapons.has_weapon(offered.id), "player receives the offered weapon")
	check(game.player.weapons.current().data == offered, "new weapon is equipped")
	await _secs(1.0)
	check(box.state == MysteryBox.State.IDLE, "box closes after the weapon is taken")


func test_pack_a_punch_flow() -> void:
	await _new_game()
	var pap: PackAPunch = game.colosseum.get_node("NavigationRegion3D/PackAPunch")
	check(pap != null, "Pack-a-Punch placed in the Colosseum")
	var w := game.player.weapons.current()
	var pts := game.wallet.points
	pap.interact(game.player)
	check(pap.state == PackAPunch.State.IDLE and not w.upgraded and game.wallet.points == pts, "no upgrade and no charge without points")
	game.wallet.add(6000)
	pts = game.wallet.points
	var dmg0 := w.base_damage()
	pap.interact(game.player)
	check(pap.state == PackAPunch.State.WORKING, "machine starts working")
	check(game.wallet.points == pts, "nothing charged before the upgrade is applied")
	await _game_secs(pap.process_time + 0.5)
	await _process_frames(3)
	check(w.upgraded and w.base_damage() > dmg0, "weapon upgraded with more damage")
	check(game.wallet.points == pts - pap.cost(), "exact upgrade cost deducted once")
	check(game.player.weapons.state != WeaponManager.State.BUSY, "weapon returned to the player")
	pts = game.wallet.points
	pap.interact(game.player)
	check(pap.state == PackAPunch.State.IDLE and game.wallet.points == pts, "already-upgraded weapon is refused without charge")


func test_shop_purchases() -> void:
	await _new_game()
	var shop := game.shop
	game.wallet.add(20000)
	game.open_shop(1)
	await _frames(2)
	check(get_tree().paused and shop.visible, "shop opens and pauses gameplay")
	var items := {}
	for it in game.wallet.config.shop_items:
		items[it.effect] = it
	var pts := game.wallet.points
	check(shop.buy(items[ShopItem.Effect.MAX_HEALTH]), "buy max health")
	check(game.player.max_health == 125.0 and game.player.health == 125.0, "max health increased to 125")
	check(game.wallet.points == pts - items[ShopItem.Effect.MAX_HEALTH].base_cost, "health cost deducted")
	pts = game.wallet.points
	check(not shop.buy(items[ShopItem.Effect.AMMO_REFILL]), "ammo refill refused when already full")
	check(game.wallet.points == pts, "refused refill costs nothing")
	game.player.weapons.current().mag = 1
	game.player.weapons.current().reserve = 3
	check(shop.buy(items[ShopItem.Effect.AMMO_REFILL]), "ammo refill bought when needed")
	check(game.player.weapons.current().is_full(), "ammo refilled")
	check(shop.buy(items[ShopItem.Effect.DAMAGE]), "buy damage upgrade")
	check(is_equal_approx(game.player.damage_multiplier, 1.15), "damage multiplier increased")
	game.wallet.try_spend(game.wallet.points)
	pts = game.wallet.points
	check(not shop.buy(items[ShopItem.Effect.DAMAGE]) and game.wallet.points == pts, "unaffordable item refused")
	var r0 := game.waves.round_number
	shop._on_continue()
	await _frames(3)
	check(not get_tree().paused and game.waves.round_number == r0 + 1 and game.waves.running, "leaving the shop starts the next round")


func test_zombie_attacks_player() -> void:
	await _new_game()
	_place_player(Vector3(0, 0.1, 10))
	var z := _spawn_zombie(Vector3(0, 0.05, 7.0), 500.0, 1.5)
	await _game_secs(6.0)
	check(z.global_position.distance_to(game.player.global_position) < 2.5, "zombie navigated to the player")
	check(game.player.health < game.player.max_health, "zombie damaged the player (hp %.0f)" % game.player.health)


func test_wave_progression() -> void:
	await _new_game()
	Engine.time_scale = 4.0
	var completed := []
	game.waves.round_completed.connect(func(r): completed.append(r))
	game.waves.start_round(1)
	var n1 := game.waves.remaining()
	var max_alive := 0
	var t := 0.0
	while completed.is_empty() and t < 40.0:
		await _frames(10)
		t += 10.0 / 60.0
		max_alive = max(max_alive, game.waves.alive.size())
		for z in game.waves.alive.duplicate():
			if z.state != Zombie.State.EMERGE:
				z.take_damage(99999.0, {})
	check(completed == [1], "round 1 completes when every zombie is dead")
	check(max_alive <= game.waves.config.max_active, "active cap respected")
	game.waves.start_round(2)
	check(game.waves.remaining() > n1, "round 2 schedules more zombies (%d > %d)" % [game.waves.remaining(), n1])
	# cap: spawn round 12 instantly and check concurrency
	game.waves.start_round(12)
	for i in 60:
		game.waves.spawn_one() if game.waves.alive.size() < game.waves.config.max_active else null
	check(game.waves.alive.size() <= game.waves.config.max_active, "never more than max_active zombies at once")
	check(game.waves.alive[0].max_health > 900.0, "late-round zombies are tougher")
	Engine.time_scale = 1.0


func test_death_and_restart() -> void:
	await _new_game()
	game.wallet.add(5000)
	game.player.weapons.give_weapon(_load_weapon("m4"))
	game.player.damage_multiplier = 1.6
	game.waves.start_round(3)
	await _secs(3.0)
	for i in 3:
		_spawn_zombie(Vector3(i * 2.0 - 2.0, 0.05, -5), 200.0)
	game.player.take_damage(500.0)
	check(not game.player.is_alive(), "player dies")
	await _secs(3.0)
	check(game.phase == Game.Phase.GAME_OVER and game.game_over.visible, "game-over screen shown")
	var old := game
	game.restart()
	await _frames(5)
	game = get_tree().current_scene as Game
	check(game != null and game != old, "scene reloaded")
	check(get_tree().get_nodes_in_group("zombies").size() == 0, "no leftover zombies after restart")
	check(game.wallet.points == game.wallet.config.starting_points, "points reset")
	check(game.player.health == 100.0 and game.player.max_health == 100.0, "health reset")
	check(game.player.damage_multiplier == 1.0, "temporary upgrades cleared")
	check(game.player.weapons.slots.size() == 1 and game.player.weapons.current().data.id == &"pistol", "back to the starting pistol")
	await _secs(1.5)
	check(game.waves.round_number == 1, "run restarts at round 1")
