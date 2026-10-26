extends SceneTree
## Renders a scene from given camera positions (visual QA).
## godot --rendering-driver opengl3 --path . -s tools/preview/scene_shot.gd -- \
##     <res://scene.tscn|glb[,glb2...]> <out_prefix> "px,py,pz>tx,ty,tz" ["..."] ...
## Optional env var SHOT_FOV, SHOT_WAIT (frames), SHOT_W/SHOT_H.

func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var w := int(OS.get_environment("SHOT_W")) if OS.get_environment("SHOT_W") != "" else 1280
	var h := int(OS.get_environment("SHOT_H")) if OS.get_environment("SHOT_H") != "" else 720
	root.size = Vector2i(w, h)
	var world := Node3D.new()
	root.add_child(world)
	var has_env := false
	for p in args[0].split(","):
		var inst: Node = (load(p) as PackedScene).instantiate()
		world.add_child(inst)
		if inst.find_children("*", "WorldEnvironment", true, false).size() > 0 or inst is WorldEnvironment:
			has_env = true
	if not has_env:
		var env := WorldEnvironment.new()
		var e := Environment.new()
		e.background_mode = Environment.BG_COLOR
		e.background_color = Color(0.35, 0.4, 0.5)
		e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		e.ambient_light_color = Color(0.6, 0.6, 0.65)
		e.ambient_light_energy = 0.7
		e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
		env.environment = e
		world.add_child(env)
		var sun := DirectionalLight3D.new()
		sun.rotation_degrees = Vector3(-40, 30, 0)
		sun.shadow_enabled = true
		sun.directional_shadow_max_distance = 200
		world.add_child(sun)
	var cam := Camera3D.new()
	cam.fov = float(OS.get_environment("SHOT_FOV")) if OS.get_environment("SHOT_FOV") != "" else 75.0
	cam.far = 1000
	world.add_child(cam)
	cam.current = true
	var wait := int(OS.get_environment("SHOT_WAIT")) if OS.get_environment("SHOT_WAIT") != "" else 8
	for i in range(2, args.size()):
		var parts := args[i].split(">")
		var a := parts[0].split_floats(",")
		var b := parts[1].split_floats(",")
		cam.position = Vector3(a[0], a[1], a[2])
		cam.look_at(Vector3(b[0], b[1], b[2]), Vector3.UP)
		for f in wait:
			await process_frame
		root.get_texture().get_image().save_png("%s_%d.png" % [args[1], i - 2])
	print("SHOT_OK")
	quit()
