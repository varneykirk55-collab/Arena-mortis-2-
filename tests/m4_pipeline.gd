extends Node
## Integration regression for the imported replacement, actual fire/reload,
## attachment transforms and Pack-a-Punch presentation. No gameplay overrides.
var passed := 0
var failed := 0

func _ready() -> void:
	_run.call_deferred()

func check(value: bool, message: String) -> void:
	if value:
		passed += 1
	else:
		failed += 1
	print("PASS " if value else "FAIL ", message)

func _run() -> void:
	Player.require_mouse_capture = false
	var game: Game = load("res://scenes/main/game.tscn").instantiate()
	game.auto_start = false
	add_child(game)
	await get_tree().physics_frame
	game.player.weapons.give_weapon(load("res://resources/weapons/m4.tres"))
	var wm := game.player.weapons
	await get_tree().create_timer(0.7).timeout
	var w := wm.current()
	var vm := wm.current_viewmodel()
	check(w.data.id == &"m4" and wm.state == WeaponManager.State.READY, "real WeaponManager equips M4")
	check(vm.muzzle.position.is_equal_approx(Vector3(0, 0.06, -0.4755)), "muzzle at Grok suppressor tip")
	check(vm.sight.position.is_equal_approx(Vector3(0, 0.13, 0.0505)), "sight matches Grok iron sights")
	var rh := vm.model.find_child("RightHand", true, false) as Node3D
	var lh := vm.model.find_child("LeftHand", true, false) as Node3D
	check(rh.position.is_equal_approx(Vector3(0, -0.004, 0.05)), "right hand at Grok grip")
	check(is_equal_approx(rh.rotation.x, deg_to_rad(-15)), "right hand rotation preserved")
	check(lh.position.is_equal_approx(Vector3(0, 0.01, -0.28)), "left hand at Grok handguard")
	check(rh.find_child("RightArm",true,false) != null and lh.find_child("LeftArmRifle",true,false) != null, "existing arms attach")
	var bolt_rest := vm.slide.position
	var mag_rest := vm.magazine.position
	wm._fire(w)
	check(w.mag == 29, "actual firing consumes one M4 round")
	check(vm.slide.position.z > bolt_rest.z, "firing moves imported Bolt")
	check(vm._flash.visible, "firing shows existing muzzle flash")
	wm.reload()
	check(wm.state == WeaponManager.State.RELOADING, "actual reload starts")
	await get_tree().create_timer(0.7).timeout
	check(vm.magazine.position.y < mag_rest.y - 0.02 or not vm.magazine.visible, "imported Magazine detaches during reload")
	await get_tree().create_timer(2.2).timeout
	check(w.mag == 30 and w.reserve == 209, "reload preserves original ammo transfer")
	check(vm.magazine.visible and vm.magazine.position.is_equal_approx(mag_rest), "magazine returns to its imported rest pose")
	check(vm.slide.position.is_equal_approx(bolt_rest), "bolt returns to rest")
	check(wm.upgrade_current(), "existing upgrade applies")
	check(w.upgraded and w.magazine_size() == 40, "Pack-a-Punch data unchanged")
	var meshes := vm.model.find_children("*", "MeshInstance3D", true, false)
	var surfaces := 0
	var triangles := 0
	for mesh: MeshInstance3D in meshes:
		if String(mesh.name).contains("Arm") or mesh == vm._flash:
			continue
		check(mesh.material_overlay != null and mesh.material_overlay.shader == Viewmodel.CAMO_SHADER, "animated camo retained on " + String(mesh.name))
		for i in mesh.mesh.get_surface_count():
			var material := mesh.mesh.surface_get_material(i)
			var pbr := material as StandardMaterial3D
			check(pbr != null and pbr.albedo_texture != null and pbr.normal_texture != null and pbr.roughness_texture != null and pbr.metallic_texture != null, "Grok PBR textures on " + String(mesh.name) + ":" + str(i))
			surfaces += 1
			triangles += mesh.mesh.surface_get_array_index_len(i) / 3
	check(surfaces <= 12 and triangles <= 30000, "first-person asset budget: %d surfaces, %d triangles" % [surfaces,triangles])
	print("M4_PIPELINE_DONE: %d passed, %d failed" % [passed,failed])
	game.queue_free()
	await get_tree().process_frame
	get_tree().quit(0 if failed == 0 else 1)
