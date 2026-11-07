extends "res://tests/run_tests.gd"
## Includes actual clip sampling and game-state integration, not just names.
var legionary: PackedScene = load("res://assets/models/zombie_legionary.glb")

func _run_all() -> void:
	for test in ["test_character_asset", "test_character_playback", "test_legionary_gameplay", "test_gladiator_compatibility"]:
		_current = test
		await call(test)
	await _teardown_game()
	print("LEGIONARY_TESTS_DONE: %d passed, %d failed" % [_passed,_failed])
	get_tree().quit(0 if _failed == 0 else 1)

func test_character_asset() -> void:
	var model := legionary.instantiate()
	var skel := model.find_child("Skeleton3D",true,false) as Skeleton3D
	check(skel != null and skel.get_bone_count() >= 50, "named humanoid with articulated fingers")
	for name in ["Head","Hips","Chest","Forearm.L","Shin.R","Finger1_3.L","Thumb3.R"]:
		check(skel.find_bone(name) >= 0, "bone " + name)
	var meshes := model.find_children("*","MeshInstance3D",true,false)
	var triangles := 0
	var surfaces := 0
	var unique := {}
	for mi: MeshInstance3D in meshes:
		check(mi.skin != null, "skin binding on " + mi.name)
		for i in mi.mesh.get_surface_count():
			var mat := mi.mesh.surface_get_material(i) as StandardMaterial3D
			check(mat != null and mat.albedo_texture != null and mat.normal_texture != null and mat.roughness_texture != null, "PBR maps on " + mi.name)
			unique[mat.get_instance_id()] = true
			triangles += mi.mesh.surface_get_array_index_len(i) / 3
			surfaces += 1
			var arrays := mi.mesh.surface_get_arrays(i)
			var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
			var good := not weights.is_empty()
			for j in range(0,weights.size(),4):
				good = good and abs(weights[j]+weights[j+1]+weights[j+2]+weights[j+3]-1.0) < 0.002
			check(good, "normalized four-influence weights on " + mi.name)
	print("CHARACTER_BUDGET triangles=",triangles," surfaces=",surfaces," materials=",unique.size())
	check(triangles < 45000 and surfaces == 4 and unique.size() == 1, "real-time character budget")
	model.free()

func test_character_playback() -> void:
	var model := legionary.instantiate()
	add_child(model)
	var anim := model.find_child("AnimationPlayer",true,false) as AnimationPlayer
	var skel := model.find_child("Skeleton3D",true,false) as Skeleton3D
	for clip in ["Idle","Walk","Run","Attack","Hit","Death","Emerge"]:
		check(anim.has_animation(clip), "clip exists: " + clip)
		var index := skel.find_bone("Thigh.L" if clip in ["Walk","Run"] else ("UpperArm.L" if clip == "Attack" else ("Chest" if clip == "Hit" else ("Head" if clip == "Idle" else "Hips"))))
		anim.play(clip,0)
		anim.seek(0.02,true)
		skel.force_update_all_bone_transforms()
		var before := skel.get_bone_global_pose(index)
		anim.seek(anim.get_animation(clip).length * 0.43,true)
		skel.force_update_all_bone_transforms()
		var after := skel.get_bone_global_pose(index)
		check(not before.is_equal_approx(after), "actual bone playback changes: " + clip)
		check(anim.get_animation(clip).get_track_count() > 10, "exported animation tracks: " + clip)
	anim.play("Walk",0)
	await _secs(0.15)
	var t := anim.current_animation_position
	await _secs(0.15)
	check(anim.current_animation_position > t, "AnimationPlayer advances during actual frames")
	model.queue_free()
	await _process_frames(2)

func spawn_character(scene: PackedScene, pos: Vector3, speed := 1.25, runner := false) -> Zombie:
	var z: Zombie = game.waves.zombie_scene.instantiate()
	z.model_scenes = [scene]
	z.configure(500,speed,35,runner)
	game.get_node("Zombies").add_child(z)
	z.global_position = pos
	z.died.connect(game.waves._on_zombie_died)
	return z

func test_legionary_gameplay() -> void:
	await _new_game()
	_place_player(Vector3(0,0.1,10))
	var z := spawn_character(legionary,Vector3(0,0.05,5))
	check(z._anim.current_animation == "Emerge", "legionary emerges through existing controller")
	await _game_secs(2)
	check(z.state == Zombie.State.CHASE and z._anim.current_animation == "Walk", "normal navigation drives Walk")
	var distance := z.global_position.distance_to(game.player.global_position)
	await _game_secs(2)
	check(z.global_position.distance_to(game.player.global_position) < distance, "navigates toward player")
	z.take_damage(110)
	check(z.state == Zombie.State.STAGGER and z._anim.current_animation == "Hit", "damage drives Hit clip")
	var attack_seen := false
	for i in 300:
		await _frames(1)
		attack_seen = attack_seen or z._anim.current_animation == "Attack"
	check(game.player.health < game.player.max_health, "unchanged melee contact damages player")
	check(attack_seen, "existing attack uses Attack clip during pursuit")
	z.take_damage(9999)
	check(z.state == Zombie.State.DEAD and z._anim.current_animation == "Death", "death drives Death clip")
	await _secs(6.5)
	check(not is_instance_valid(z), "corpse removed after existing sink timer")
	await _new_game()
	_place_player(Vector3(0,0.1,10))
	var runner := spawn_character(legionary,Vector3(0,0.05,-6),3.9,true)
	await _game_secs(1.7)
	check(runner._anim.current_animation == "Run", "runner drives Run clip")
	runner.queue_free()
	# Each current rifle must hit the new bone-following head hurtbox.
	for id in ["m4","mk35"]:
		game.player.weapons.give_weapon(_load_weapon(id))
		var target := spawn_character(legionary,Vector3(0,0.05,5),0)
		await _frames(80)
		var head := target.find_child("HeadHurtbox",true,false) as Node3D
		Input.action_press("aim")
		await _frames(20)
		_aim_at(head.global_position)
		await _frames(2)
		_fire_once()
		check(target.health < target.max_health, id + " hits new animated skeleton/hurtbox")
		Input.action_release("aim")
		target.queue_free()
		await _frames(3)

func test_gladiator_compatibility() -> void:
	await _new_game()
	_place_player(Vector3(0,0.1,10))
	var gladiator := spawn_character(load("res://assets/models/zombie_gladiator.glb"),Vector3(0,0.05,7))
	await _game_secs(6)
	check(gladiator._anim.has_animation("Attack") and game.player.health < game.player.max_health, "unchanged gladiator still navigates and attacks")
