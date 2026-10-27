extends Node
## Fixed-camera beauty shots of the real game scene (HUD hidden, no zombies).
## xvfb-run godot --rendering-driver opengl3 --path . res://tests/beauty_shots.tscn -- <out_dir> <prefix> [shot_names,comma]
## Also prints render statistics (draw calls, primitives) for each shot.

const SHOTS := {
	"A1_north_wall": [Vector3(0, 1.7, -7), Vector3(0, 3.2, -20)],
	"A2_north_oblique": [Vector3(-6, 1.7, -9), Vector3(9, 3.0, -19)],
	"A3_wall_closeup": [Vector3(5.5, 1.7, -13.5), Vector3(8.5, 2.6, -19.5)],
	"A4_north_gate": [Vector3(-9, 1.7, -11), Vector3(-13.5, 2.5, -18)],
	"G1_spawn": [Vector3(0, 1.72, 6), Vector3(0, 2.5, -10)],
	"G2_overview": [Vector3(-22, 1.7, 6), Vector3(10, 8, -6)],
	"G3_high": [Vector3(0, 26, 30), Vector3(0, 4, -4)],
	"G4_south_pap": [Vector3(4, 1.7, 9), Vector3(-1, 2.5, 19)],
	"G5_stands": [Vector3(10, 1.7, -4), Vector3(-6, 14, -30)],
}

func _ready() -> void:
	_run.call_deferred()

func _run() -> void:
	var a := OS.get_cmdline_user_args()
	var out_dir: String = a[0] if a.size() > 0 else "res://tools/preview/out"
	var prefix: String = a[1] if a.size() > 1 else "shot"
	var only: PackedStringArray = a[2].split(",") if a.size() > 2 else PackedStringArray()
	Player.require_mouse_capture = false
	get_tree().root.size = Vector2i(1280, 720)
	var game: Game = load("res://scenes/main/game.tscn").instantiate()
	game.auto_start = false
	get_tree().root.add_child(game)
	get_tree().current_scene = game
	await get_tree().process_frame
	game.hud.visible = false
	game.player.weapons.visible = false
	game.player.set_physics_process(false)
	game.player.interactor.set_process(false)
	var cam := game.player.camera
	for key in SHOTS:
		if only.size() > 0 and not only.has(key):
			continue
		var s: Array = SHOTS[key]
		cam.global_position = s[0]
		cam.look_at(s[1], Vector3.UP)
		cam.fov = 75.0
		for i in 5:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		img.save_png(out_dir.path_join("%s_%s.png" % [prefix, key]))
		var vp := get_viewport().get_viewport_rid()
		print("STAT %s draw_calls=%d primitives=%d objects=%d" % [key,
			RenderingServer.viewport_get_render_info(vp, RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_DRAW_CALLS_IN_FRAME),
			RenderingServer.viewport_get_render_info(vp, RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_PRIMITIVES_IN_FRAME),
			RenderingServer.viewport_get_render_info(vp, RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_OBJECTS_IN_FRAME)])
	print("VIDEO_MEM_MB ", RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_VIDEO_MEM_USED) / 1048576.0)
	print("SHOTS_DONE")
	get_tree().quit()
