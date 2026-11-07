@tool
extends EditorScenePostImport
## Preserve supplied geometry/UVs/textures. Normalize +X to -Z, consolidate
## static parts and retain moving assemblies with world-aligned local axes.
var groups: Dictionary
var pivots: Dictionary
var material: Material
var rotation := Transform3D(Basis(Vector3.UP, PI / 2), Vector3.ZERO)

func _post_import(scene: Node) -> Object:
	groups = {}
	pivots = {}
	material = null
	_collect(scene, Transform3D.IDENTITY, "Body")
	var root := Node3D.new()
	var is_mk35 := get_source_file().contains("mk35")
	root.name = "MK35" if is_mk35 else "M4"
	for key in groups:
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		var pivot: Vector3 = pivots.get(key, Vector3.ZERO)
		for entry in groups[key]:
			var transform: Transform3D = entry[1]
			transform.origin -= pivot
			var mesh: Mesh = entry[0]
			for i in mesh.get_surface_count():
				st.append_from(mesh, i, transform)
		st.set_material(material)
		var part := MeshInstance3D.new()
		part.name = key
		part.mesh = st.commit()
		part.position = pivot
		root.add_child(part)
		part.owner = root
	_marker(root, "Muzzle", Vector3(0, 0.06, -0.615 if is_mk35 else -0.4755))
	_marker(root, "RightHand", Vector3(0, -0.025 if is_mk35 else -0.004, 0.05))
	(root.get_node("RightHand") as Node3D).rotation.x = deg_to_rad(-15)
	_marker(root, "LeftHand", Vector3(0, 0.01, -0.28))
	_marker(root, "Sight", Vector3(0, 0.137 if is_mk35 else 0.13, -0.0135 if is_mk35 else 0.0505))
	scene.free()
	return root

func _marker(root: Node, label: String, position: Vector3) -> void:
	var n := Node3D.new()
	n.name = label
	n.position = position
	root.add_child(n)
	n.owner = root

func _collect(node: Node, parent_transform: Transform3D, group: String) -> void:
	var transform := parent_transform
	if node is Node3D:
		transform *= (node as Node3D).transform
	var moving := {"magazine":"Magazine", "bolt_carrier":"Bolt", "charging_handle":"ChargingHandle", "dust_cover":"DustCover"}
	if moving.has(String(node.name)):
		group = moving[String(node.name)]
		pivots[group] = rotation * transform.origin
	if node is MeshInstance3D:
		var mesh := (node as MeshInstance3D).mesh
		if material == null:
			material = mesh.surface_get_material(0)
		if not groups.has(group):
			groups[group] = []
		groups[group].append([mesh, rotation * transform])
	for child in node.get_children():
		_collect(child, transform, group)
