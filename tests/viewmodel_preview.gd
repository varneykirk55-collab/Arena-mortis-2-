extends Node3D
## Renders each weapon's first-person framing (hip + ADS) for visual QA.
## xvfb-run godot --rendering-driver opengl3 --path . res://tests/viewmodel_preview.tscn -- <out_dir>

var out_dir := "res://tools/preview/out"


func _ready() -> void:
	_run.call_deferred()


func _run() -> void:
	var a := OS.get_cmdline_user_args()
	if a.size() > 0:
		out_dir = a[0]
	get_tree().root.size = Vector2i(1280, 720)
	# light-weight backdrop: environment + a sand floor + a torch light
	var env := WorldEnvironment.new()
	env.environment = load("res://resources/environment_dusk.tres")
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, 150, 0)
	sun.light_color = Color(0.62, 0.7, 0.95)
	sun.light_energy = 1.05
	add_child(sun)
	add_child(load("res://assets/models/colosseum_floor.glb").instantiate())
	var torch := OmniLight3D.new()
	torch.light_color = Color(1.0, 0.58, 0.25)
	torch.light_energy = 2.0
	torch.omni_range = 8
	torch.position = Vector3(-9, 2.5, 1)
	add_child(torch)
	var cam := Camera3D.new()
	cam.near = 0.03
	cam.fov = 80
	add_child(cam)
	cam.position = Vector3(-8, 1.72, 4)
	cam.look_at(Vector3(-12, 1.6, -8))
	cam.current = true
	var wm := WeaponManager.new()
	wm.arms_scene = load("res://assets/models/viewmodel_arms.glb")
	cam.add_child(wm)
	wm.set_physics_process(false)
	for wid in ["pistol", "m4", "jupiter"]:
		wm.give_weapon(load("res://resources/weapons/%s.tres" % wid))
		for i in 30:
			await get_tree().process_frame
		for ads in [0.0, 1.0]:
			wm.ads_amount = ads
			for i in 20:
				await get_tree().process_frame
			await RenderingServer.frame_post_draw
			get_viewport().get_texture().get_image().save_png(out_dir.path_join("vm_%s_%s.png" % [wid, "ads" if ads > 0 else "hip"]))
	print("VM_DONE")
	get_tree().quit()
