extends "res://tests/run_tests.gd"
## End-to-end coverage through existing game systems, not a parallel weapon API.

func _run_all() -> void:
	for test in ["test_weapon_resources", "test_model_imports", "test_grok_imports", "test_rifles_combat", "test_box_acquisition_and_upgrade", "test_switching_and_empty"]:
		_current = test
		await call(test)
	await _teardown_game()
	print("GROK_TESTS_DONE: %d passed, %d failed" % [_passed, _failed])
	get_tree().quit(0 if _failed == 0 else 1)

func test_grok_imports() -> void:
	for id in ["m4", "mk35"]:
		var scene := _load_weapon(id).viewmodel_scene.instantiate()
		var meshes := scene.find_children("*", "MeshInstance3D", true, false)
		var triangles := 0
		check(meshes.size() == 5, id + " static consolidation + four moving parts")
		for node: MeshInstance3D in meshes:
			var mat := node.mesh.surface_get_material(0) as StandardMaterial3D
			check(mat != null and mat.albedo_texture != null and mat.normal_texture != null and mat.roughness_texture != null and mat.metallic_texture != null and mat.ao_texture != null, id + "/" + node.name + " all PBR maps load")
			triangles += node.mesh.surface_get_array_index_len(0) / 3
		check(triangles == (18238 if id == "m4" else 18322), id + " supplied LOD triangle count preserved")
		check((scene.get_node("Muzzle") as Node3D).position.z < -0.45, id + " barrel faces Godot forward")
		scene.free()
	var m4 := _load_weapon("m4")
	check(m4.damage == 42 and m4.magazine_size == 30 and m4.reserve_ammo == 210 and m4.fire_rate == 12.5 and m4.reload_time == 2.3, "M4 existing ballistics/ammo/cadence/reload unchanged")

func test_rifles_combat() -> void:
	for id in ["m4", "mk35"]:
		await _new_game()
		_place_player(Vector3(0, 0.1, 10))
		var wm := game.player.weapons
		wm.give_weapon(_load_weapon(id))
		await _secs(0.8)
		var w := wm.current()
		var zombie := _spawn_zombie(Vector3(0, 0.05, 5), 5000.0)
		await _frames(75)
		_aim_at(zombie.global_position + Vector3(0, 1, 0))
		var health := zombie.health
		_fire_once()
		check(zombie.health < health, id + " hits and damages real zombie")
		check(game.wallet.points > game.wallet.config.starting_points, id + " hit rewards existing points")
		check(w.mag == w.magazine_size() - 1, id + " shot consumes ammo")
		var vm := wm.current_viewmodel()
		check(vm._flash.visible and vm.slide.position.z > vm._slide_rest.z, id + " flash and moving bolt")
		var head := zombie.find_child("HeadHurtbox", true, false) as Node3D
		Input.action_press("aim")
		await _frames(20)
		_aim_at(head.global_position)
		await _frames(2)
		health = zombie.health
		_fire_once()
		check(health - zombie.health > w.base_damage() * 1.5, id + " headshot multiplier via real hit detection")
		Input.action_release("aim")
		wm.reload()
		await _secs(w.data.reload_time * 0.4)
		check(not vm.magazine.visible or vm.magazine.position.y < vm._mag_rest.y - 0.02, id + " supplied magazine removes during reload")
		await _secs(w.data.reload_time * 0.65)
		check(w.mag == w.magazine_size() and vm.magazine.visible and vm.magazine.position.is_equal_approx(vm._mag_rest), id + " magazine inserts and ammo restores")
		check(vm.charging_handle.position.is_equal_approx(vm._charging_rest), id + " supplied charging handle returns")
		check(game.hud.weapon_label.text == w.data.display_name, id + " HUD weapon name")
		check(game.hud.ammo_label.text == str(w.mag), id + " HUD ammo updates")

func test_box_acquisition_and_upgrade() -> void:
	await _new_game()
	var box: MysteryBox = game.colosseum.get_node("NavigationRegion3D/MysteryBox")
	var counts := {"m4":0, "mk35":0, "jupiter":0}
	var rng := RandomNumberGenerator.new()
	rng.seed = 3507
	for i in 20000:
		var selected := MysteryBox.roll(box.pool, rng)
		check(counts.has(String(selected.id)), "box pool valid") if i == 0 else null
		counts[String(selected.id)] += 1
	check(counts["mk35"] > 4500 and counts["mk35"] < 7000, "MK35 available through normal weighted box pool: " + str(counts))
	# Use deterministic roll seeds, retaining the unmodified real three-weapon pool.
	for id in ["m4", "mk35"]:
		var seed_value := 0
		while true:
			box._rng.seed = seed_value
			if MysteryBox.roll(box.pool, box._rng).id == StringName(id):
				break
			seed_value += 1
		box._rng.seed = seed_value
		game.wallet.add(20000)
		box.interact(game.player)
		check(box.selected.id == StringName(id), id + " selected by real box")
		await _secs(box.cycle_time + 0.2)
		print("BOX_DIAG ", id, " state=", box.state, " selected=", box.selected.id, " timer=", box._timer)
		while box.state == MysteryBox.State.CYCLING:
			await _process_frames(1)
		check(box.state == MysteryBox.State.OFFERING, id + " box reaches offer state")
		box.interact(game.player)
		await _secs(0.8)
		check(game.player.weapons.current().data.id == StringName(id), id + " acquired and equipped through box")
		var pap: PackAPunch = game.colosseum.get_node("NavigationRegion3D/PackAPunch")
		var points := game.wallet.points
		pap.interact(game.player)
		await _secs(pap.process_time + 0.7)
		var w := game.player.weapons.current()
		check(w.upgraded and game.wallet.points == points - pap.cost(), id + " actual Pack-a-Punch charges once and upgrades")
		var vm := game.player.weapons.current_viewmodel()
		check((vm.model.get_node("Body") as MeshInstance3D).material_overlay.shader == Viewmodel.CAMO_SHADER, id + " original animated camo attached")
		check(game.hud.weapon_label.text == w.display_name(), id + " upgraded HUD name")

func test_switching_and_empty() -> void:
	await _new_game()
	var wm := game.player.weapons
	var pistol := wm.current()
	var rifle := wm.give_weapon(_load_weapon("mk35"))
	await _secs(0.8)
	wm.switch_to(0)
	await _secs(0.8)
	check(wm.current() == pistol, "switch back to M1911")
	wm.cycle(1)
	await _secs(0.8)
	check(wm.current() == rifle, "cycle to MK35")
	rifle.mag = 2
	rifle.reserve = 0
	Input.action_press("fire")
	await _secs(0.5)
	Input.action_release("fire")
	check(rifle.mag == 0 and rifle.reserve == 0, "automatic firing stops at zero ammo, no negatives")
	wm.reload()
	check(wm.state != WeaponManager.State.RELOADING, "cannot reload without reserve")
	rifle.reserve = 7
	await _secs(rifle.data.reload_time + 0.3)
	check(rifle.mag == 7 and rifle.reserve == 0, "empty-mag auto-reload limited by reserve")
	wm.give_weapon(_load_weapon("mk35"))
	check(wm.slots.size() == 2 and wm.current() == rifle and rifle.mag == 30, "duplicate acquisition refills without extra slot")
	wm.give_weapon(_load_weapon("m4"))
	check(wm.slots.size() == 2 and wm.find_weapon(&"mk35") == null, "full inventory replacement uses existing two-slot rules")
