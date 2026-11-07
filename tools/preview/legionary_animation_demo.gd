extends Node
## Actual imported GLB playback, suitable for Godot --write-movie recording.
var player: AnimationPlayer
var timeline := [["Idle",2.4],["Walk",2.08],["Run",2.04],["Attack",1.0],["Hit",0.7],["Death",2.0],["Emerge",1.3]]
var index := -1
var elapsed := 0.0
var label: Label

func _ready() -> void:
	var model: Node3D = load("res://assets/models/zombie_legionary.glb").instantiate()
	add_child(model)
	player = model.find_child("AnimationPlayer",true,false)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.055,0.065,0.075)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.7,0.75,0.85)
	env.environment.ambient_light_energy = 0.45
	add_child(env)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-35,-25,0)
	light.light_energy = 1.3
	add_child(light)
	var camera := Camera3D.new()
	add_child(camera)
	camera.position = Vector3(2,1.6,4)
	camera.look_at(Vector3(0,.9,.1))
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 2.6
	camera.current = true
	var canvas := CanvasLayer.new()
	add_child(canvas)
	label = Label.new()
	canvas.add_child(label)
	label.position = Vector2(30,25)
	label.add_theme_font_size_override("font_size",28)
	next_clip()

func next_clip() -> void:
	index += 1
	if index >= timeline.size():
		print("LEGIONARY_ANIMATION_DEMO_DONE")
		get_tree().quit()
		return
	elapsed = 0
	player.stop()
	# Reset prevents held transforms from a completed death carrying into Emerge.
	var skel := player.get_parent().find_child("Skeleton3D",true,false) as Skeleton3D
	if skel:
		skel.reset_bone_poses()
	var clip: String = timeline[index][0]
	if clip in ["Idle","Walk","Run"]:
		player.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
	player.play(clip,0)
	label.text = "Legionary — " + clip + "\nActual Godot 4.7.2 GLB playback"
	print("DEMO_CLIP ",clip)

func _process(delta: float) -> void:
	if index < 0 or index >= timeline.size():
		return
	elapsed += delta
	if elapsed >= float(timeline[index][1]):
		next_clip()
