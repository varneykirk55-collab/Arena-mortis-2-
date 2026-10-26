class_name Zombie
extends CharacterBody3D
## Undead enemy: emerges at a spawn point, navigates to the player, attacks at
## close range, reacts to hits and dies. Stats are pushed in by WaveManager
## via configure(). Emits `died` once; frees itself after the corpse sinks.

signal died(zombie: Zombie, info: Dictionary)

enum State { EMERGE, CHASE, ATTACK, STAGGER, DEAD }

@export var model_scenes: Array[PackedScene] = []
@export var groan_sounds: Array[AudioStream] = []
@export var attack_sounds: Array[AudioStream] = []
@export var death_sounds: Array[AudioStream] = []
@export var attack_range := 1.55
@export var attack_hit_range := 2.05
@export var attack_windup := 0.45
@export var attack_duration := 1.0
@export var turn_speed := 7.0
@export var gravity := 18.0

var max_health := 150.0
var health := 150.0
var move_speed := 1.4
var damage := 35.0
var is_runner := false
var state := State.EMERGE
var target: Node3D

var _anim: AnimationPlayer
var _model: Node3D
var _agent: NavigationAgent3D
var _voice: AudioStreamPlayer3D
var _state_t := 0.0
var _attack_applied := false
var _repath_t := 0.0
var _groan_t := 0.0
var _desired := Vector3.ZERO
var _hurtboxes: Array[Hurtbox] = []
var _last_hit_info := {}
var _sink_started := false


func _ready() -> void:
	add_to_group("zombies")
	collision_layer = Layers.ZOMBIE_BODY
	collision_mask = Layers.WORLD | Layers.PLAYER | Layers.ZOMBIE_BODY
	_agent = $NavigationAgent3D
	_agent.velocity_computed.connect(_on_velocity_computed)
	_voice = $Voice
	_spawn_model()
	_groan_t = randf_range(1.0, 5.0)
	_repath_t = randf() * 0.3
	if target == null:
		target = get_tree().get_first_node_in_group("player")
	_play("Emerge", 0.0)
	_state_t = 1.3


## Called by WaveManager before adding to the tree (or right after).
func configure(hp: float, speed: float, dmg: float, runner: bool) -> void:
	max_health = hp
	health = hp
	move_speed = speed
	damage = dmg
	is_runner = runner


func is_alive() -> bool:
	return state != State.DEAD


func _spawn_model() -> void:
	if model_scenes.is_empty():
		return
	_model = model_scenes[randi() % model_scenes.size()].instantiate()
	$Model.add_child(_model)
	var s := randf_range(0.94, 1.07)
	$Model.scale = Vector3(s, s, s)
	_anim = _model.find_child("AnimationPlayer", true, false)
	if _anim:
		for n in ["Idle", "Walk", "Run"]:
			if _anim.has_animation(n):
				_anim.get_animation(n).loop_mode = Animation.LOOP_LINEAR
	# hurtboxes: torso is static on the body, head follows the Head bone
	var body_hb: Hurtbox = $BodyHurtbox
	body_hb.zombie = self
	_hurtboxes.append(body_hb)
	var skel: Skeleton3D = _model.find_child("Skeleton3D", true, false)
	var head_hb := Hurtbox.new()
	head_hb.name = "HeadHurtbox"
	head_hb.is_head = true
	head_hb.zombie = self
	var shape := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.15
	shape.shape = sph
	head_hb.add_child(shape)
	if skel:
		var att := BoneAttachment3D.new()
		att.bone_name = "Head"
		skel.add_child(att)
		att.add_child(head_hb)
		head_hb.position = Vector3(0, 0.11, 0.02)
	else:
		add_child(head_hb)
		head_hb.position = Vector3(0, 1.72, 0)
	_hurtboxes.append(head_hb)


func _play(anim_name: String, blend := 0.2, speed := 1.0) -> void:
	if _anim and _anim.has_animation(anim_name):
		if _anim.current_animation == anim_name and _anim.is_playing():
			_anim.speed_scale = speed
			return
		_anim.play(anim_name, blend)
		_anim.speed_scale = speed


# ------------------------------------------------------------------ damage

## Applies damage. Returns {"killed", "is_head", "damage", "zombie"}.
func take_damage(amount: float, info := {}) -> Dictionary:
	var result := {"killed": false, "is_head": info.get("is_head", false), "damage": 0.0, "zombie": self}
	if state == State.DEAD:
		return result
	var applied: float = min(amount, health)
	health -= amount
	result.damage = applied
	_last_hit_info = info
	if health <= 0.0:
		result.killed = true
		_die(info)
	else:
		# hit reaction: short stagger, more likely for big hits
		if state != State.ATTACK and state != State.EMERGE and (amount >= max_health * 0.2 or randf() < 0.35):
			state = State.STAGGER
			_state_t = 0.35
			_play("Hit", 0.05)
	return result


func _die(info: Dictionary) -> void:
	state = State.DEAD
	remove_from_group("zombies")
	collision_layer = 0
	collision_mask = Layers.WORLD
	$CollisionShape3D.set_deferred("disabled", true)
	velocity = Vector3.ZERO
	_agent.avoidance_enabled = false
	for hb in _hurtboxes:
		hb.disable()
	if info.get("lightning", false):
		_electrocute()
	else:
		_play("Death", 0.1)
	if not death_sounds.is_empty():
		_voice.stream = Sfx.pick(death_sounds)
		_voice.play()
	ImpactFX.blood_pool(self, global_position + Vector3(0, 0.05, 0) - global_basis.z * 0.6, randf_range(1.0, 1.6))
	died.emit(self, info)
	var t := create_tween()
	t.tween_interval(4.0)
	t.tween_callback(func(): _sink_started = true)
	t.tween_property(self, "position:y", position.y - 1.6, 2.0)
	t.tween_callback(queue_free)


func _electrocute() -> void:
	# glow blue, twitch, then fall
	_play("Hit", 0.0, 2.5)
	var flash := ShaderMaterial.new()
	flash.shader = preload("res://resources/shaders/upgrade_camo.gdshader")
	flash.set_shader_parameter("tint", Color(0.5, 0.8, 1.0))
	flash.set_shader_parameter("strength", 1.6)
	_set_overlay(_model, flash)
	var t := create_tween()
	t.tween_interval(0.45)
	t.tween_callback(func(): _play("Death", 0.1, 1.3))
	t.tween_interval(0.8)
	t.tween_callback(func(): _set_overlay(_model, null))


func _set_overlay(n: Node, mat: Material) -> void:
	if n == null:
		return
	if n is MeshInstance3D:
		(n as MeshInstance3D).material_overlay = mat
	for c in n.get_children():
		_set_overlay(c, mat)


# ------------------------------------------------------------------ behaviour

func _physics_process(delta: float) -> void:
	if state == State.DEAD:
		if not _sink_started and not is_on_floor():
			velocity.y -= gravity * delta
			move_and_slide()
		return
	if not is_on_floor():
		velocity.y -= gravity * delta
	else:
		velocity.y = -0.5
	_state_t -= delta
	_groan_t -= delta
	if _groan_t <= 0.0:
		_groan_t = randf_range(3.0, 8.0)
		if not groan_sounds.is_empty() and not _voice.playing:
			_voice.stream = Sfx.pick(groan_sounds)
			_voice.pitch_scale = randf_range(0.85, 1.15)
			_voice.play()
	if target == null or not is_instance_valid(target):
		target = get_tree().get_first_node_in_group("player")
	var target_alive: bool = target != null and (not target.has_method("is_alive") or target.is_alive())
	match state:
		State.EMERGE:
			_stop(delta)
			if _state_t <= 0.0:
				state = State.CHASE
		State.STAGGER:
			_stop(delta)
			if _state_t <= 0.0:
				state = State.CHASE
		State.ATTACK:
			_stop(delta)
			if target_alive:
				_face(target.global_position, delta)
			if not _attack_applied and _state_t <= attack_duration - attack_windup:
				_attack_applied = true
				if target_alive and _flat_dist(target.global_position) <= attack_hit_range and target.has_method("take_damage"):
					target.take_damage(damage, global_position)
			if _state_t <= 0.0:
				state = State.CHASE
		State.CHASE:
			if not target_alive:
				_stop(delta)
				_play("Idle", 0.3)
				return
			var dist := _flat_dist(target.global_position)
			if dist <= attack_range and abs(target.global_position.y - global_position.y) < 1.6:
				_start_attack()
				return
			_repath_t -= delta
			if _repath_t <= 0.0:
				_repath_t = 0.25 if dist < 12.0 else 0.6
				_agent.target_position = target.global_position
			var next := _agent.get_next_path_position()
			var to := next - global_position
			to.y = 0.0
			if to.length() < 0.05:
				to = target.global_position - global_position
				to.y = 0.0
			var dir := to.normalized()
			_desired = dir * move_speed
			if _agent.avoidance_enabled:
				_agent.velocity = _desired
			else:
				_on_velocity_computed(_desired)
			_face(global_position + (velocity if Vector2(velocity.x, velocity.z).length() > 0.2 else dir), delta)
			if is_runner:
				_play("Run", 0.25, move_speed / 3.9)
			else:
				_play("Walk", 0.25, move_speed / 1.25)
	move_and_slide()


func _on_velocity_computed(safe: Vector3) -> void:
	if state != State.CHASE:
		return
	velocity.x = safe.x
	velocity.z = safe.z


func _stop(delta: float) -> void:
	velocity.x = move_toward(velocity.x, 0.0, delta * 12.0)
	velocity.z = move_toward(velocity.z, 0.0, delta * 12.0)
	if _agent.avoidance_enabled:
		_agent.velocity = Vector3.ZERO


func _start_attack() -> void:
	state = State.ATTACK
	_state_t = attack_duration
	_attack_applied = false
	_play("Attack", 0.1)
	if not attack_sounds.is_empty():
		_voice.stream = Sfx.pick(attack_sounds)
		_voice.pitch_scale = randf_range(0.9, 1.1)
		_voice.play()


func _face(point: Vector3, delta: float) -> void:
	var d := point - global_position
	d.y = 0.0
	if d.length() < 0.01:
		return
	var yaw := atan2(d.x, d.z)    # model front is +Z
	rotation.y = lerp_angle(rotation.y, yaw, min(delta * turn_speed, 1.0))


func _flat_dist(p: Vector3) -> float:
	return Vector2(p.x - global_position.x, p.z - global_position.z).length()
