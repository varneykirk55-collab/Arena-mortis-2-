class_name Player
extends CharacterBody3D
## First-person player: movement, mouse look, health/regeneration, recoil and
## death. Weapons live in $Head/Camera3D/WeaponManager; interaction in $Interactor.

signal health_changed(current: float, maximum: float)
signal damaged(amount: float, source_position: Vector3)
signal died

@export_group("Movement")
@export var walk_speed := 4.6
@export var sprint_speed := 7.0
@export var ads_speed_multiplier := 0.6
@export var acceleration := 14.0
@export var air_acceleration := 3.5
@export var friction := 12.0
@export var jump_velocity := 4.8
@export var gravity := 15.0

@export_group("Health")
@export var max_health := 100.0
@export var regen_delay := 4.0
@export var regen_rate := 30.0

@export_group("Audio")
@export var hurt_sounds: Array[AudioStream] = []
@export var death_sound: AudioStream
@export var footstep_sounds: Array[AudioStream] = []

const BASE_SENSITIVITY := 0.12     ## degrees per pixel at sensitivity 1.0

## Automated tests / bots turn this off so the player can act without a captured mouse.
static var require_mouse_capture := true

var health := 100.0
var damage_multiplier := 1.0       ## shop "weapon damage" upgrade
var input_enabled := true
var alive := true

var _pitch := 0.0
var _recoil := Vector2.ZERO        ## accumulated (pitch, yaw) degrees to recover
var _since_damage := 99.0
var _sprinting := false
var _step_dist := 0.0

@onready var head: Node3D = $Head
@onready var camera: Camera3D = $Head/Camera3D
@onready var weapons: WeaponManager = $Head/Camera3D/WeaponManager
@onready var interactor: Interactor = $Interactor


func _ready() -> void:
	add_to_group("player")
	collision_layer = Layers.PLAYER
	collision_mask = Layers.WORLD | Layers.ZOMBIE_BODY
	health = max_health
	weapons.player = self
	camera.fov = Settings.field_of_view
	health_changed.emit(health, max_health)


func is_alive() -> bool:
	return alive


func can_act() -> bool:
	var captured := Input.mouse_mode == Input.MOUSE_MODE_CAPTURED or not require_mouse_capture
	return alive and input_enabled and captured and not get_tree().paused


func is_sprinting() -> bool:
	return _sprinting


func horizontal_speed() -> float:
	return Vector2(velocity.x, velocity.z).length()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and can_act():
		var sens := BASE_SENSITIVITY * Settings.mouse_sensitivity
		if weapons.is_aiming():
			sens *= 0.65
		var rel: Vector2 = event.relative
		rotate_y(deg_to_rad(-rel.x * sens))
		_pitch -= rel.y * sens * (-1.0 if Settings.invert_y else 1.0)
		_pitch = clamp(_pitch, -88.0, 88.0)
		head.rotation_degrees.x = _pitch
		weapons.add_look_sway(rel)


func apply_recoil(pitch_deg: float, yaw_deg: float) -> void:
	_pitch = clamp(_pitch + pitch_deg, -88.0, 88.0)
	rotate_y(deg_to_rad(yaw_deg))
	head.rotation_degrees.x = _pitch
	_recoil += Vector2(pitch_deg, yaw_deg)


func _physics_process(delta: float) -> void:
	var on_floor := is_on_floor()
	if not on_floor:
		velocity.y -= gravity * delta
	var wish := Vector3.ZERO
	var acting := can_act()
	if acting:
		var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
		wish = (global_basis * Vector3(input.x, 0, input.y))
		wish.y = 0
		wish = wish.normalized() * min(input.length(), 1.0)
		_sprinting = Input.is_action_pressed("sprint") and input.y < -0.2 and not weapons.is_aiming() \
				and not Input.is_action_pressed("fire") and on_floor
		if Input.is_action_just_pressed("jump") and on_floor:
			velocity.y = jump_velocity
	else:
		_sprinting = false
	var speed := sprint_speed if _sprinting else walk_speed
	var w := weapons.current()
	if w:
		speed *= w.data.move_speed_multiplier
	speed *= lerp(1.0, ads_speed_multiplier, weapons.ads_amount)
	var target := wish * speed
	var accel := acceleration if on_floor else air_acceleration
	if wish.length() < 0.01 and on_floor:
		accel = friction
	var horiz := Vector3(velocity.x, 0, velocity.z).move_toward(target, accel * max(speed, 1.0) * delta)
	velocity.x = horiz.x
	velocity.z = horiz.z
	move_and_slide()
	_update_recoil(delta)
	_update_regen(delta)
	_footsteps(delta, on_floor)


func _update_recoil(delta: float) -> void:
	if _recoil.length() < 0.001:
		return
	var rec: Vector2 = _recoil * minf(delta * 7.0, 1.0)
	_recoil -= rec
	_pitch = clamp(_pitch - rec.x * 0.85, -88.0, 88.0)
	head.rotation_degrees.x = _pitch


func _update_regen(delta: float) -> void:
	if not alive:
		return
	_since_damage += delta
	if _since_damage >= regen_delay and health < max_health:
		health = min(health + regen_rate * delta, max_health)
		health_changed.emit(health, max_health)


func _footsteps(delta: float, on_floor: bool) -> void:
	if not on_floor or footstep_sounds.is_empty():
		return
	_step_dist += horizontal_speed() * delta
	var stride := 2.2 if _sprinting else 1.7
	if _step_dist >= stride:
		_step_dist = 0.0
		Sfx.play_2d(self, Sfx.pick(footstep_sounds), -16.0 if not _sprinting else -12.0, 0.1)


func take_damage(amount: float, source_position := Vector3.ZERO) -> void:
	if not alive or amount <= 0.0:
		return
	health = max(health - amount, 0.0)
	_since_damage = 0.0
	health_changed.emit(health, max_health)
	damaged.emit(amount, source_position)
	if health <= 0.0:
		_die()
	else:
		Sfx.play_2d(self, Sfx.pick(hurt_sounds), -2.0, 0.08)
		# camera punch
		var t := create_tween()
		t.tween_property(camera, "rotation_degrees:z", randf_range(-4.0, 4.0), 0.06)
		t.tween_property(camera, "rotation_degrees:z", 0.0, 0.25)


func heal_full() -> void:
	health = max_health
	health_changed.emit(health, max_health)


func add_max_health(amount: float) -> void:
	max_health += amount
	health = max_health
	health_changed.emit(health, max_health)


func _die() -> void:
	alive = false
	_sprinting = false
	Sfx.play_2d(self, death_sound, 0.0)
	weapons.set_busy(true)
	# fall to the ground
	var t := create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	t.tween_property(head, "position:y", 0.25, 0.9)
	t.parallel().tween_property(camera, "rotation_degrees:z", 70.0, 0.9)
	t.parallel().tween_callback(func(): weapons.visible = false).set_delay(0.3)
	died.emit()
