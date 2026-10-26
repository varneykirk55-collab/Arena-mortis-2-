class_name LightningBeam
extends MeshInstance3D
## Jagged, flickering lightning ribbon between two points (Jupiter's bolt).
## Purely visual; damage is resolved by WeaponManager's ray.

const SHADER := preload("res://resources/shaders/lightning.gdshader")

var start := Vector3.ZERO
var end := Vector3.ZERO
var color := Color(0.55, 0.8, 1.0)
var life := 0.32
var width := 0.09
var _age := 0.0
var _regen := 0.0
var _mat: ShaderMaterial
var _im: ImmediateMesh


static func spawn(context: Node, from: Vector3, to: Vector3, col: Color, w := 0.09) -> LightningBeam:
	var b := LightningBeam.new()
	b.start = from
	b.end = to
	b.color = col
	b.width = w
	var root := context.get_tree().current_scene if context.get_tree().current_scene else context.get_tree().root
	root.add_child(b)
	return b


func _ready() -> void:
	top_level = true
	global_transform = Transform3D.IDENTITY
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_im = ImmediateMesh.new()
	mesh = _im
	_mat = ShaderMaterial.new()
	_mat.shader = SHADER
	_mat.set_shader_parameter("color", color)
	material_override = _mat
	extra_cull_margin = 200.0
	_rebuild()
	# a light that travels along the bolt for a moment
	var l := OmniLight3D.new()
	l.light_color = color
	l.light_energy = 5.0
	l.omni_range = 7.0
	add_child(l)
	l.global_position = start.lerp(end, 0.25)
	var t := create_tween()
	t.tween_property(l, "global_position", end, life * 0.5)
	t.parallel().tween_property(l, "light_energy", 0.0, life)


func _jagged(a: Vector3, b: Vector3, depth: int, amp: float) -> PackedVector3Array:
	var pts := PackedVector3Array([a, b])
	for i in depth:
		var np := PackedVector3Array()
		for k in pts.size() - 1:
			var p0 := pts[k]
			var p1 := pts[k + 1]
			var mid := (p0 + p1) * 0.5
			var d := (p1 - p0)
			var perp := d.cross(Vector3.UP)
			if perp.length() < 0.001:
				perp = d.cross(Vector3.RIGHT)
			perp = perp.normalized().rotated(d.normalized(), randf() * TAU)
			mid += perp * randf_range(-1.0, 1.0) * amp * d.length()
			np.append(p0)
			np.append(mid)
		np.append(pts[pts.size() - 1])
		pts = np
	return pts


func _ribbon(pts: PackedVector3Array, w: float, cam_pos: Vector3) -> void:
	_im.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in pts.size() - 1:
		var a := pts[i]
		var b := pts[i + 1]
		var dir := (b - a).normalized()
		var to_cam := (cam_pos - a).normalized()
		var side := dir.cross(to_cam).normalized() * w * 0.5
		_im.surface_set_uv(Vector2(0, 0)); _im.surface_add_vertex(a - side)
		_im.surface_set_uv(Vector2(0, 1)); _im.surface_add_vertex(a + side)
		_im.surface_set_uv(Vector2(1, 1)); _im.surface_add_vertex(b + side)
		_im.surface_set_uv(Vector2(0, 0)); _im.surface_add_vertex(a - side)
		_im.surface_set_uv(Vector2(1, 1)); _im.surface_add_vertex(b + side)
		_im.surface_set_uv(Vector2(1, 0)); _im.surface_add_vertex(b - side)
	_im.surface_end()


func _rebuild() -> void:
	_im.clear_surfaces()
	var cam := get_viewport().get_camera_3d()
	var cam_pos := cam.global_position if cam else start + Vector3.UP
	var main := _jagged(start, end, 5, 0.18)
	_ribbon(main, width, cam_pos)
	# a few forks
	for f in 3:
		var idx := randi_range(main.size() / 4, main.size() - 2)
		var a := main[idx]
		var dir := (end - start).normalized()
		var off := Vector3(randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)).normalized() * randf_range(0.6, 1.6)
		var fork := _jagged(a, a + dir * randf_range(0.6, 1.5) + off, 3, 0.3)
		_ribbon(fork, width * 0.45, cam_pos)


func _process(delta: float) -> void:
	_age += delta
	_regen -= delta
	if _regen <= 0.0 and _age < life * 0.7:
		_regen = 0.05
		_rebuild()
	_mat.set_shader_parameter("fade", clamp(1.0 - _age / life, 0.0, 1.0))
	if _age >= life:
		queue_free()
