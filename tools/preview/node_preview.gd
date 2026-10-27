extends SceneTree
## Renders one named node of a GLB (all nodes if none given) for QA.
## -- <res://file.glb> <out_prefix> <node_name|*> [yaw,...] [pitch]
func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	var a := OS.get_cmdline_user_args()
	root.size = Vector2i(1280, 720)
	var world := Node3D.new()
	root.add_child(world)
	var env := WorldEnvironment.new()
	env.environment = load("res://resources/environment_dusk.tres")
	world.add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-35, 30, 0)
	sun.light_energy = 1.2
	sun.light_color = Color(1.0, 0.9, 0.8)
	sun.shadow_enabled = true
	world.add_child(sun)
	var inst: Node3D = (load(a[0]) as PackedScene).instantiate()
	world.add_child(inst)
	if a[2] != "*":
		for c in inst.get_children():
			if c is Node3D and String(c.name) != a[2]:
				(c as Node3D).visible = false
	await process_frame
	var aabb := AABB()
	var first := true
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		if not (mi as Node3D).is_visible_in_tree():
			continue
		var bb: AABB = (mi as MeshInstance3D).global_transform * (mi as MeshInstance3D).get_aabb()
		aabb = bb if first else aabb.merge(bb)
		first = false
	var yaws := [30.0]
	if a.size() > 3:
		yaws = Array(a[3].split(",")).map(func(s): return float(s))
	var pitch := -15.0 if a.size() <= 4 else float(a[4])
	var cam := Camera3D.new()
	cam.fov = 45
	cam.near = 0.05
	world.add_child(cam)
	cam.current = true
	var c := aabb.get_center()
	var rad := aabb.size.length() * 0.5
	for yaw in yaws:
		var dir := Vector3.FORWARD.rotated(Vector3.RIGHT, deg_to_rad(pitch)).rotated(Vector3.UP, deg_to_rad(yaw))
		cam.position = c - dir * rad / tan(deg_to_rad(22.5)) * 1.05
		cam.look_at(c)
		cam.far = rad * 10 + 50
		for i in 4:
			await process_frame
		root.get_texture().get_image().save_png("%s_%d.png" % [a[1], int(yaw)])
	print("NODE_PREVIEW_OK")
	quit()
