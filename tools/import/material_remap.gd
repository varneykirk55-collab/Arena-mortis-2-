@tool
extends EditorScenePostImport
## Post-import hook for every GLB produced by tools/asset_gen.
## glTF materials are matched by name to res://resources/materials/<name>.tres
## so all look-development (textures, triplanar mapping, shaders) lives in Godot
## resources while the geometry stays generated.

const MATERIAL_DIR := "res://resources/materials/"


func _post_import(scene: Node) -> Object:
	_remap(scene)
	return scene


func _remap(node: Node) -> void:
	if node is MeshInstance3D:
		var mi := node as MeshInstance3D
		var mesh := mi.mesh
		if mesh:
			for i in mesh.get_surface_count():
				var mat := mesh.surface_get_material(i)
				if mat == null:
					continue
				var path := MATERIAL_DIR + mat.resource_name + ".tres"
				if ResourceLoader.exists(path):
					mesh.surface_set_material(i, load(path))
	for child in node.get_children():
		_remap(child)
