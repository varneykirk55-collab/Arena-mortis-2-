class_name FireFX
extends Node3D
## Self-building flame: billboard flame + ember + smoke particles and a
## flickering warm light. Used by braziers and torches.

const GLOW := preload("res://assets/textures/glow_particle.png")
const SMOKE := preload("res://assets/textures/smoke_particle.png")

@export var size := 1.0
@export var light_energy := 2.2
@export var light_range := 9.0
@export var cast_shadows := false
@export var with_smoke := true
@export var crackle: AudioStream

var _light: OmniLight3D
var _t := randf() * 10.0


func _ready() -> void:
	_add_flames()
	if with_smoke:
		_add_smoke()
	_light = OmniLight3D.new()
	_light.light_color = Color(1.0, 0.58, 0.25)
	_light.light_energy = light_energy
	_light.omni_range = light_range
	_light.omni_attenuation = 1.4
	_light.shadow_enabled = cast_shadows
	_light.light_size = 0.15
	_light.position = Vector3(0, 0.35 * size, 0)
	_light.distance_fade_enabled = true
	_light.distance_fade_begin = 45.0
	_light.distance_fade_length = 15.0
	add_child(_light)
	if crackle:
		var a := AudioStreamPlayer3D.new()
		a.stream = crackle
		a.bus = &"Ambient"
		a.volume_db = -14.0
		a.unit_size = 2.0
		a.max_distance = 18.0
		a.autoplay = true
		add_child(a)


func _particle_material(tex: Texture2D, additive: bool) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD if additive else BaseMaterial3D.BLEND_MODE_MIX
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.billboard_keep_scale = true
	m.vertex_color_use_as_albedo = true
	m.albedo_texture = tex
	m.disable_receive_shadows = true
	return m


func _add_flames() -> void:
	var p := GPUParticles3D.new()
	p.amount = 28
	p.lifetime = 0.7
	p.local_coords = false
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	pm.emission_sphere_radius = 0.16 * size
	pm.direction = Vector3.UP
	pm.spread = 12.0
	pm.initial_velocity_min = 0.6 * size
	pm.initial_velocity_max = 1.2 * size
	pm.gravity = Vector3(0, 1.2, 0)
	pm.scale_min = 0.6
	pm.scale_max = 1.1
	var sc := Curve.new()
	sc.add_point(Vector2(0, 0.6))
	sc.add_point(Vector2(0.3, 1.0))
	sc.add_point(Vector2(1, 0.1))
	var sct := CurveTexture.new()
	sct.curve = sc
	pm.scale_curve = sct
	var grad := Gradient.new()
	grad.set_color(0, Color(1.0, 0.85, 0.45, 1.0))
	grad.set_color(1, Color(0.6, 0.08, 0.02, 0.0))
	grad.add_point(0.4, Color(1.0, 0.45, 0.1, 0.9))
	var gt := GradientTexture1D.new()
	gt.gradient = grad
	pm.color_ramp = gt
	pm.angle_min = -180.0
	pm.angle_max = 180.0
	p.process_material = pm
	var q := QuadMesh.new()
	q.size = Vector2(0.55, 0.7) * size
	q.material = _particle_material(GLOW, true)
	p.draw_pass_1 = q
	add_child(p)
	# embers
	var e := GPUParticles3D.new()
	e.amount = 10
	e.lifetime = 1.6
	e.local_coords = false
	var em := ParticleProcessMaterial.new()
	em.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	em.emission_sphere_radius = 0.2 * size
	em.direction = Vector3.UP
	em.spread = 30.0
	em.initial_velocity_min = 0.8
	em.initial_velocity_max = 2.0
	em.gravity = Vector3(0, 0.4, 0)
	em.turbulence_enabled = true
	em.turbulence_noise_strength = 1.5
	em.scale_min = 0.03
	em.scale_max = 0.06
	var eg := Gradient.new()
	eg.set_color(0, Color(1, 0.7, 0.3, 1))
	eg.set_color(1, Color(1, 0.3, 0.05, 0))
	var egt := GradientTexture1D.new()
	egt.gradient = eg
	em.color_ramp = egt
	e.process_material = em
	var eq := QuadMesh.new()
	eq.size = Vector2(1, 1)
	eq.material = _particle_material(GLOW, true)
	e.draw_pass_1 = eq
	add_child(e)


func _add_smoke() -> void:
	var s := GPUParticles3D.new()
	s.amount = 10
	s.lifetime = 3.5
	s.local_coords = false
	s.position = Vector3(0, 0.5 * size, 0)
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3.UP
	pm.spread = 10.0
	pm.initial_velocity_min = 0.5
	pm.initial_velocity_max = 0.9
	pm.gravity = Vector3(0.15, 0.25, 0)
	pm.scale_min = 0.8
	pm.scale_max = 1.4
	var sc := Curve.new()
	sc.add_point(Vector2(0, 0.4))
	sc.add_point(Vector2(1, 1.6))
	var sct := CurveTexture.new()
	sct.curve = sc
	pm.scale_curve = sct
	var grad := Gradient.new()
	grad.set_color(0, Color(0.15, 0.13, 0.12, 0.0))
	grad.set_color(1, Color(0.1, 0.1, 0.1, 0.0))
	grad.add_point(0.25, Color(0.16, 0.14, 0.13, 0.35))
	var gt := GradientTexture1D.new()
	gt.gradient = grad
	pm.color_ramp = gt
	s.process_material = pm
	var q := QuadMesh.new()
	q.size = Vector2(0.8, 0.8) * size
	var m := _particle_material(SMOKE, false)
	q.material = m
	s.draw_pass_1 = q
	add_child(s)


func _process(delta: float) -> void:
	_t += delta
	if _light:
		_light.light_energy = light_energy * (0.85 + 0.1 * sin(_t * 11.0) + 0.07 * sin(_t * 23.7) + 0.05 * sin(_t * 5.3))
