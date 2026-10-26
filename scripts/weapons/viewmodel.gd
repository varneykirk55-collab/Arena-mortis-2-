class_name Viewmodel
extends Node3D
## First-person presentation of one weapon: the model, gloved arms, muzzle
## flash and procedural fire / reload / equip animations.
## Created by WeaponManager; it never changes gameplay state itself.

const FLASH_TEX := preload("res://assets/textures/muzzle_flash.png")
const CAMO_SHADER := preload("res://resources/shaders/upgrade_camo.gdshader")

var data: WeaponData
var model: Node3D
var muzzle: Node3D
var slide: Node3D
var magazine: Node3D
var core: Node3D
var sight: Node3D

var _slide_rest := Vector3.ZERO
var _mag_rest := Vector3.ZERO
var _flash: MeshInstance3D
var _flash_light: OmniLight3D
var _flash_time := 0.0
var _kick := 0.0               ## 0..1 recoil pose, decays
var _anim_tween: Tween
var _camo: ShaderMaterial
var _core_time := 0.0

## procedural pose offsets read by WeaponManager
var anim_offset := Vector3.ZERO
var anim_rotation := Vector3.ZERO


func setup(weapon: WeaponData, arms_scene: PackedScene) -> void:
	data = weapon
	name = "Viewmodel_%s" % weapon.id
	model = weapon.viewmodel_scene.instantiate()
	add_child(model)
	muzzle = model.find_child("Muzzle", true, false)
	slide = model.find_child("Slide", true, false)
	if slide == null:
		slide = model.find_child("Bolt", true, false)
	magazine = model.find_child("Magazine", true, false)
	core = model.find_child("Core", true, false)
	sight = model.find_child("Sight", true, false)
	if slide:
		_slide_rest = slide.position
	if magazine:
		_mag_rest = magazine.position
	if arms_scene:
		_attach_arms(arms_scene.instantiate())
	_build_flash()
	_disable_shadows(self)


func _attach_arms(arms: Node) -> void:
	var right := arms.find_child("RightArm", true, false) as Node3D
	var left := arms.find_child(String(data.left_arm), true, false) as Node3D
	var rh := model.find_child("RightHand", true, false) as Node3D
	var lh := model.find_child("LeftHand", true, false) as Node3D
	for pair in [[right, rh], [left, lh]]:
		var arm: Node3D = pair[0]
		var anchor: Node3D = pair[1]
		if arm == null or anchor == null:
			continue
		arm.owner = null
		arm.get_parent().remove_child(arm)
		anchor.add_child(arm)
		arm.transform = Transform3D.IDENTITY
	arms.queue_free()


func _build_flash() -> void:
	if muzzle == null:
		return
	_flash = MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(0.22, 0.22) * data.muzzle_flash_scale
	_flash.mesh = q
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.albedo_texture = FLASH_TEX
	mat.albedo_color = data.muzzle_flash_color
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	mat.no_depth_test = true
	_flash.material_override = mat
	_flash.visible = false
	muzzle.add_child(_flash)
	_flash.position = Vector3(0, 0, -0.04)
	_flash_light = OmniLight3D.new()
	_flash_light.light_color = data.muzzle_flash_color
	_flash_light.omni_range = 6.0
	_flash_light.light_energy = 0.0
	_flash_light.shadow_enabled = false
	muzzle.add_child(_flash_light)


func _disable_shadows(n: Node) -> void:
	if n is GeometryInstance3D:
		(n as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		(n as GeometryInstance3D).extra_cull_margin = 2.0
	for c in n.get_children():
		_disable_shadows(c)


func muzzle_position() -> Vector3:
	return muzzle.global_position if muzzle else global_position


# ---------------------------------------------------------------- animations

func play_fire() -> void:
	_kick = 1.0
	_flash_time = 0.05
	if _flash:
		_flash.visible = true
		_flash.rotation.z = randf() * TAU
		var s := randf_range(0.8, 1.25)
		_flash.scale = Vector3(s, s, s)
		_flash_light.light_energy = 2.5
	if slide:
		slide.position = _slide_rest + Vector3(0, 0, 0.035 if data.fire_mode == WeaponData.FireMode.SEMI else 0.02)


func play_reload(duration: float) -> void:
	_kill_tween()
	_anim_tween = create_tween()
	var t := duration
	# tilt the weapon, drop the magazine, insert a new one, rack
	_anim_tween.tween_property(self, "anim_rotation", Vector3(0.25, 0.2, 0.55), t * 0.18).set_trans(Tween.TRANS_SINE)
	_anim_tween.parallel().tween_property(self, "anim_offset", Vector3(-0.03, -0.04, 0.02), t * 0.18)
	if magazine:
		_anim_tween.tween_property(magazine, "position", _mag_rest + Vector3(0, -0.35, 0.05), t * 0.17).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		_anim_tween.tween_callback(func(): magazine.visible = false)
		_anim_tween.tween_interval(t * 0.12)
		_anim_tween.tween_callback(func(): magazine.visible = true; magazine.position = _mag_rest + Vector3(0, -0.25, 0.05))
		_anim_tween.tween_property(magazine, "position", _mag_rest, t * 0.2).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	else:
		_anim_tween.tween_interval(t * 0.5)
	_anim_tween.tween_property(self, "anim_rotation", Vector3(0.1, -0.05, 0.2), t * 0.12)
	if slide:
		_anim_tween.tween_property(slide, "position", _slide_rest + Vector3(0, 0, 0.04), t * 0.05)
		_anim_tween.tween_property(slide, "position", _slide_rest, t * 0.04)
	_anim_tween.tween_property(self, "anim_rotation", Vector3.ZERO, t * 0.1).set_trans(Tween.TRANS_SINE)
	_anim_tween.parallel().tween_property(self, "anim_offset", Vector3.ZERO, t * 0.1)


func play_equip(duration: float) -> void:
	_kill_tween()
	anim_offset = Vector3(0, -0.3, 0.05)
	anim_rotation = Vector3(-0.6, 0.3, 0)
	_anim_tween = create_tween().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_anim_tween.tween_property(self, "anim_offset", Vector3.ZERO, duration)
	_anim_tween.parallel().tween_property(self, "anim_rotation", Vector3.ZERO, duration)


func play_lower(duration: float) -> void:
	_kill_tween()
	_anim_tween = create_tween().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	_anim_tween.tween_property(self, "anim_offset", Vector3(0, -0.35, 0.05), duration)
	_anim_tween.parallel().tween_property(self, "anim_rotation", Vector3(-0.7, 0.2, 0), duration)


func cancel_animation() -> void:
	_kill_tween()
	anim_offset = Vector3.ZERO
	anim_rotation = Vector3.ZERO
	if magazine:
		magazine.visible = true
		magazine.position = _mag_rest
	if slide:
		slide.position = _slide_rest


func _kill_tween() -> void:
	if _anim_tween and _anim_tween.is_valid():
		_anim_tween.kill()
	if magazine:
		magazine.visible = true
		magazine.position = _mag_rest


func set_upgraded(on: bool) -> void:
	if not on:
		_apply_overlay(self, null)
		return
	if _camo == null:
		_camo = ShaderMaterial.new()
		_camo.shader = CAMO_SHADER
		_camo.set_shader_parameter("tint", data.upgrade_tint)
	_apply_overlay(model, _camo)


func _apply_overlay(n: Node, mat: Material) -> void:
	if n is MeshInstance3D and not (n == _flash):
		# keep the gloves un-tinted
		if not String(n.name).contains("Arm"):
			(n as MeshInstance3D).material_overlay = mat
	for c in n.get_children():
		_apply_overlay(c, mat)


func kick_amount() -> float:
	return _kick


func _process(delta: float) -> void:
	_kick = move_toward(_kick, 0.0, delta * 9.0)
	if slide:
		slide.position = slide.position.lerp(_slide_rest, min(delta * 25.0, 1.0)) if _anim_tween == null or not _anim_tween.is_running() else slide.position
	if _flash_time > 0.0:
		_flash_time -= delta
		if _flash_time <= 0.0 and _flash:
			_flash.visible = false
			_flash_light.light_energy = 0.0
	if core:
		_core_time += delta
		var s := 1.0 + 0.04 * sin(_core_time * 23.0) + 0.03 * sin(_core_time * 61.0)
		core.scale = Vector3(s, s, 1.0)
