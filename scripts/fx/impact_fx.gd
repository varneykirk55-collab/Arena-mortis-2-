class_name ImpactFX
extends RefCounted
## Spawns short-lived hit effects (dust, blood, sparks) and decals.

const SMOKE := preload("res://assets/textures/smoke_particle.png")
const GLOW := preload("res://assets/textures/glow_particle.png")
const HOLE := preload("res://assets/textures/bullet_hole.png")
const BLOOD_A := preload("res://assets/textures/blood_decal.png")
const BLOOD_B := preload("res://assets/textures/blood_decal_2.png")
const SCORCH := preload("res://assets/textures/scorch_decal.png")

static var _mat_cache := {}


static func _root(context: Node) -> Node:
	return context.get_tree().current_scene if context.get_tree().current_scene else context.get_tree().root


static func _mat(tex: Texture2D, additive: bool) -> StandardMaterial3D:
	var key := "%s_%s" % [tex.resource_path, additive]
	if _mat_cache.has(key):
		return _mat_cache[key]
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD if additive else BaseMaterial3D.BLEND_MODE_MIX
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.vertex_color_use_as_albedo = true
	m.albedo_texture = tex
	_mat_cache[key] = m
	return m


static func _burst(context: Node, pos: Vector3, normal: Vector3, color: Color, count: int, speed: float,
		size: float, life: float, tex: Texture2D, additive: bool, gravity := Vector3(0, -6, 0)) -> void:
	var p := CPUParticles3D.new()
	p.one_shot = true
	p.emitting = false
	p.amount = count
	p.lifetime = life
	p.explosiveness = 0.95
	p.local_coords = false
	p.direction = normal
	p.spread = 35.0
	p.initial_velocity_min = speed * 0.4
	p.initial_velocity_max = speed
	p.gravity = gravity
	p.scale_amount_min = size * 0.5
	p.scale_amount_max = size
	var g := Gradient.new()
	g.set_color(0, color)
	g.set_color(1, Color(color.r, color.g, color.b, 0.0))
	p.color_ramp = g
	var q := QuadMesh.new()
	q.size = Vector2(1, 1)
	q.material = _mat(tex, additive)
	p.mesh = q
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_root(context).add_child(p)
	p.global_position = pos
	p.emitting = true
	p.finished.connect(p.queue_free)


static func decal(context: Node, pos: Vector3, normal: Vector3, tex: Texture2D, size: float, life := 20.0, modulate := Color.WHITE) -> Decal:
	var d := Decal.new()
	d.texture_albedo = tex
	d.size = Vector3(size, 0.4, size)
	d.modulate = modulate
	d.cull_mask = 1
	d.upper_fade = 0.2
	d.lower_fade = 0.2
	_root(context).add_child(d)
	d.global_position = pos
	var up := normal.normalized()
	var ref := Vector3.FORWARD if abs(up.dot(Vector3.FORWARD)) < 0.9 else Vector3.RIGHT
	var x := ref.cross(up).normalized()
	var z := x.cross(up).normalized()
	d.global_basis = Basis(x, up, z).rotated(up, randf() * TAU)
	var t := d.create_tween()
	t.tween_interval(life)
	t.tween_property(d, "modulate:a", 0.0, 2.0)
	t.tween_callback(d.queue_free)
	return d


static func world_hit(context: Node, pos: Vector3, normal: Vector3) -> void:
	_burst(context, pos + normal * 0.03, normal, Color(0.55, 0.48, 0.38, 0.8), 8, 2.5, 0.25, 0.9, SMOKE, false, Vector3(0, -1.0, 0))
	_burst(context, pos + normal * 0.02, normal, Color(1.0, 0.8, 0.5, 1.0), 4, 6.0, 0.04, 0.25, GLOW, true)
	decal(context, pos, normal, HOLE, 0.12, 12.0)


static func flesh_hit(context: Node, pos: Vector3, dir: Vector3) -> void:
	_burst(context, pos, -dir + Vector3(0, 0.3, 0), Color(0.35, 0.02, 0.02, 0.95), 12, 3.0, 0.12, 0.6, SMOKE, false)


static func blood_pool(context: Node, pos: Vector3, size := 1.4) -> void:
	decal(context, pos, Vector3.UP, BLOOD_A if randf() < 0.5 else BLOOD_B, size, 40.0)


static func lightning_hit(context: Node, pos: Vector3, normal: Vector3, color: Color) -> void:
	_burst(context, pos, normal, Color(color.r, color.g, color.b, 1.0), 26, 9.0, 0.08, 0.5, GLOW, true, Vector3(0, -9, 0))
	_burst(context, pos, normal, Color(0.3, 0.32, 0.4, 0.7), 8, 1.5, 0.6, 1.2, SMOKE, false, Vector3(0, 0.5, 0))
	decal(context, pos, normal, SCORCH, 1.0, 25.0)
	var l := OmniLight3D.new()
	l.light_color = color
	l.light_energy = 8.0
	l.omni_range = 9.0
	_root(context).add_child(l)
	l.global_position = pos + normal * 0.4
	var t := l.create_tween()
	t.tween_property(l, "light_energy", 0.0, 0.35)
	t.tween_callback(l.queue_free)
