extends SceneTree
## Independently load all supplied full-detail/LOD exports, including external maps.
func _initialize() -> void:
	var failures := 0
	for folder in ["Modern_M4", "MK35_ISR_BO7"]:
		for detail in ["full", "LOD1"]:
			var path: String = "res://assets/sources/grok/original/" + folder + "/"
			path += "full_gltf/" + folder + ".gltf" if detail == "full" else folder + "_LOD1.glb"
			var doc := GLTFDocument.new()
			var state := GLTFState.new()
			if doc.append_from_file(ProjectSettings.globalize_path(path), state) != OK:
				failures += 1
				continue
			var scene := doc.generate_scene(state)
			var triangles := 0
			for node: MeshInstance3D in scene.find_children("*", "MeshInstance3D", true, false):
				for i in node.mesh.get_surface_count():
					triangles += node.mesh.surface_get_array_index_len(i) / 3
					var mat := node.mesh.surface_get_material(i) as StandardMaterial3D
					if mat == null or mat.albedo_texture == null or mat.normal_texture == null or mat.roughness_texture == null or mat.metallic_texture == null or mat.ao_texture == null:
						failures += 1
			var expected := (40588 if folder == "Modern_M4" else 48014) if detail == "full" else (18238 if folder == "Modern_M4" else 18322)
			if triangles != expected:
				failures += 1
			print("EXPORT_CHECK ", folder, " ", detail, " triangles=", triangles, " expected=", expected)
			scene.free()
	print("EXPORT_CHECK_DONE failures=", failures)
	quit(0 if failures == 0 else 1)
