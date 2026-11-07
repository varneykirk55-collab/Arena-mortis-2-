extends SceneTree
## Asset preview renderer (used for visual QA of generated models).
## Usage (needs a display, e.g. xvfb-run):
##   godot --rendering-driver opengl3 --path . -s tools/preview/preview.gd -- \
##       <res://model.glb|tscn> <out_prefix> [yaw1,yaw2,...] [pitch] [zoom] [anim_name] [anim_time]
## Writes <out_prefix>_<yaw>.png for each yaw.

var _args: PackedStringArray


func _initialize() -> void:
	_args = OS.get_cmdline_user_args()
	_run.call_deferred()


func _run() -> void:
	var path := _args[0]
	var out := _args[1]
	var yaws := [35.0]
	if _args.size() > 2:
		yaws = Array(_args[2].split(",")).map(func(s): return float(s))
	var pitch := -18.0 if _args.size() <= 3 else float(_args[3])
	var zoom := 1.0 if _args.size() <= 4 else float(_args[4])
	var anim_name := "" if _args.size() <= 5 else _args[5]
	var anim_time := 0.0 if _args.size() <= 6 else float(_args[6])

	root.size = Vector2i(1280, 720)
	var world := Node3D.new()
	root.add_child(world)
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.32, 0.33, 0.36)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.55, 0.55, 0.6)
	e.ambient_light_energy = 0.6
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.environment = e
	world.add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 40, 0)
	sun.light_energy = 1.4
	sun.shadow_enabled = OS.get_environment("PREVIEW_NOSHADOW") == ""
	world.add_child(sun)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-20, 220, 0)
	fill.light_energy = 0.4
	world.add_child(fill)

	var res: Resource = load(path)
	var inst: Node3D = (res as PackedScene).instantiate()
	world.add_child(inst)
	if anim_name != "":
		var ap: AnimationPlayer = inst.find_child("AnimationPlayer", true, false)
		if ap:
			ap.play(anim_name)
			ap.seek(anim_time, true)
			ap.pause()
	await process_frame
	var aabb := _aabb(inst, Transform3D.IDENTITY)
	var center := aabb.get_center()
	var radius := aabb.size.length() * 0.5 / zoom
	var cam := Camera3D.new()
	cam.fov = 40
	world.add_child(cam)
	cam.current = true
	for yaw in yaws:
		var dir := Vector3.FORWARD.rotated(Vector3.RIGHT, deg_to_rad(pitch)).rotated(Vector3.UP, deg_to_rad(yaw))
		cam.position = center - dir * radius / tan(deg_to_rad(cam.fov * 0.5)) * 1.05
		cam.look_at(center, Vector3.UP)
		cam.near = 0.01
		cam.far = radius * 20 + 100
		for i in 4:
			await process_frame
		var img := root.get_texture().get_image()
		img.save_png("%s_%d.png" % [out, int(yaw)])
	print("PREVIEW_OK ", aabb)
	quit()


func _aabb(n: Node, xf: Transform3D) -> AABB:
	var out := AABB()
	var first := true
	var t := xf
	if n is Node3D:
		t = xf * (n as Node3D).transform
	if n is VisualInstance3D:
		var a := t * (n as VisualInstance3D).get_aabb()
		out = a
		first = false
	for c in n.get_children():
		var ca := _aabb(c, t)
		if ca.size != Vector3.ZERO:
			out = ca if first else out.merge(ca)
			first = false
	return out
