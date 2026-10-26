extends SceneTree
## Loads every GDScript and scene in the project and reports failures.
## godot --headless -s tests/check_scripts.gd

func _initialize() -> void:
	var failures := 0
	var files := _collect("res://", [])
	for f in files:
		if f.ends_with(".gd") and not f.begins_with("res://tests/") and not f.begins_with("res://tools/"):
			var s = load(f)
			if s == null or not (s as Script).can_instantiate():
				print("SCRIPT_FAIL ", f)
				failures += 1
	for f in files:
		if f.ends_with(".tscn"):
			var p = load(f)
			if p == null:
				print("SCENE_FAIL ", f)
				failures += 1
	print("CHECK_DONE failures=", failures)
	quit(1 if failures > 0 else 0)


func _collect(dir: String, out: Array) -> Array:
	var d := DirAccess.open(dir)
	if d == null:
		return out
	d.list_dir_begin()
	var n := d.get_next()
	while n != "":
		if not n.begins_with("."):
			var p := dir.path_join(n)
			if d.current_is_dir():
				_collect(p, out)
			else:
				out.append(p)
		n = d.get_next()
	return out
