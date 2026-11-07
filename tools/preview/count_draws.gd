extends SceneTree
## Static draw-call budget: counts geometry instances and material surfaces per
## top-level branch of the game scene (upper bound for a view that sees everything).
func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	var game: Node = load("res://scenes/main/game.tscn").instantiate()
	game.set("auto_start", false)
	root.add_child(game)
	await process_frame
	await process_frame
	var tot := 0
	for branch in _branches(game):
		var inst := 0
		var surf := 0
		for g in branch.find_children("*", "GeometryInstance3D", true, false):
			if not (g as GeometryInstance3D).is_visible_in_tree():
				continue
			inst += 1
			var m: Mesh = null
			if g is MeshInstance3D:
				m = g.mesh
			elif g is MultiMeshInstance3D and g.multimesh:
				m = g.multimesh.mesh
			surf += m.get_surface_count() if m else 1
		if inst > 0:
			print("BRANCH %-40s instances=%5d surfaces=%5d" % [game.get_path_to(branch), inst, surf])
			tot += surf
	print("TOTAL_SURFACES ", tot)
	quit()

func _branches(game: Node) -> Array:
	var out := []
	for c in game.get_children():
		if c.get_child_count() > 0 and c.name in ["Colosseum", "Arena", "Level"]:
			for cc in c.get_children():
				out.append(cc)
		else:
			out.append(c)
	return out
