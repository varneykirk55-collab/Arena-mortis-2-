class_name Tracer
extends MeshInstance3D
## A short streak travelling from muzzle to hit point.

var _from := Vector3.ZERO
var _to := Vector3.ZERO
var _t := 0.0
var _dur := 0.06
var _im: ImmediateMesh
var _mat: StandardMaterial3D


static func spawn(context: Node, from: Vector3, to: Vector3) -> void:
	var t := Tracer.new()
	t._from = from
	t._to = to
	t._dur = clamp(from.distance_to(to) / 350.0, 0.02, 0.12)
	var root := context.get_tree().current_scene if context.get_tree().current_scene else context.get_tree().root
	root.add_child(t)


func _ready() -> void:
	top_level = true
	global_transform = Transform3D.IDENTITY
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	extra_cull_margin = 200.0
	_im = ImmediateMesh.new()
	mesh = _im
	_mat = StandardMaterial3D.new()
	_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_mat.albedo_color = Color(1.0, 0.8, 0.45, 0.8)
	_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	material_override = _mat


func _process(delta: float) -> void:
	_t += delta
	var u: float = clamp(_t / _dur, 0.0, 1.0)
	var head := _from.lerp(_to, u)
	var tail := _from.lerp(_to, max(u - 0.35, 0.0))
	_im.clear_surfaces()
	var cam := get_viewport().get_camera_3d()
	if cam:
		var dir := (head - tail)
		if dir.length() > 0.01:
			var side := dir.normalized().cross((cam.global_position - head).normalized()).normalized() * 0.012
			_im.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
			_im.surface_add_vertex(tail - side); _im.surface_add_vertex(tail + side); _im.surface_add_vertex(head + side)
			_im.surface_add_vertex(tail - side); _im.surface_add_vertex(head + side); _im.surface_add_vertex(head - side)
			_im.surface_end()
	if _t >= _dur:
		queue_free()
