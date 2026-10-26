class_name WeaponManager
extends Node3D
## Owns the player's carried weapons (slots), firing, reloading, switching,
## ADS and viewmodel motion. Child of the player's Camera3D.
##
## Communication: emits signals; never touches HUD/economy directly.

signal weapon_changed(weapon: WeaponInstance)
signal ammo_changed(weapon: WeaponInstance)
signal fired(weapon: WeaponInstance)
signal hit_registered(result: Dictionary)   ## from Zombie.take_damage + "weapon"
signal reload_started(weapon: WeaponInstance, duration: float)
signal reload_finished(weapon: WeaponInstance)
signal dry_fired(weapon: WeaponInstance)

enum State { READY, RELOADING, SWITCHING, BUSY }

@export var max_slots := 2
@export var starting_weapon: WeaponData
@export var arms_scene: PackedScene
@export var switch_sound: AudioStream
@export var hitmarker_sound: AudioStream

var slots: Array[WeaponInstance] = []
var current_index := -1
var state := State.READY
var ads_amount := 0.0
var player: Node            ## set by Player
var camera: Camera3D

var _viewmodels: Dictionary = {}     ## WeaponInstance -> Viewmodel
var _cooldown := 0.0
var _state_timer := 0.0
var _pending_index := -1
var _trigger_was_down := false
var _bob_t := 0.0
var _sway := Vector2.ZERO
var _pivot: Node3D
var _audio: AudioStreamPlayer
var _spread_bloom := 0.0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	camera = get_parent() as Camera3D
	_pivot = Node3D.new()
	_pivot.name = "Pivot"
	add_child(_pivot)
	_audio = AudioStreamPlayer.new()
	_audio.bus = &"SFX"
	add_child(_audio)
	if starting_weapon:
		give_weapon(starting_weapon)


# ------------------------------------------------------------------ queries

func current() -> WeaponInstance:
	if current_index < 0 or current_index >= slots.size():
		return null
	return slots[current_index]


func current_viewmodel() -> Viewmodel:
	var w := current()
	return _viewmodels.get(w) if w else null


func has_weapon(id: StringName) -> bool:
	return find_weapon(id) != null


func find_weapon(id: StringName) -> WeaponInstance:
	for w in slots:
		if w.data.id == id:
			return w
	return null


func is_reloading() -> bool:
	return state == State.RELOADING


func is_aiming() -> bool:
	return ads_amount > 0.5


# ------------------------------------------------------------------ inventory

## Gives a weapon: refills if already carried, fills an empty slot, or
## replaces the current weapon when all slots are full.
func give_weapon(data: WeaponData) -> WeaponInstance:
	var existing := find_weapon(data.id)
	if existing:
		existing.refill()
		switch_to(slots.find(existing))
		ammo_changed.emit(existing)
		return existing
	var inst := WeaponInstance.new(data)
	inst.changed.connect(func(): ammo_changed.emit(inst))
	if slots.size() < max_slots:
		slots.append(inst)
		_make_viewmodel(inst)
		switch_to(slots.size() - 1, true)
	else:
		var old := slots[current_index]
		_free_viewmodel(old)
		slots[current_index] = inst
		_make_viewmodel(inst)
		switch_to(current_index, true)
	return inst


func _make_viewmodel(inst: WeaponInstance) -> void:
	var vm := Viewmodel.new()
	_pivot.add_child(vm)
	vm.setup(inst.data, arms_scene)
	vm.visible = false
	_viewmodels[inst] = vm


func _free_viewmodel(inst: WeaponInstance) -> void:
	if _viewmodels.has(inst):
		_viewmodels[inst].queue_free()
		_viewmodels.erase(inst)


func switch_to(index: int, force := false) -> void:
	if index < 0 or index >= slots.size():
		return
	if index == current_index and not force:
		return
	if state == State.BUSY:
		return
	var old := current_viewmodel()
	if old:
		old.cancel_animation()
		old.visible = false
	current_index = index
	var vm := current_viewmodel()
	vm.visible = true
	vm.set_upgraded(current().upgraded)
	var t := current().data.equip_time
	vm.play_equip(t)
	state = State.SWITCHING
	_state_timer = t
	_play(switch_sound, -6.0)
	weapon_changed.emit(current())
	ammo_changed.emit(current())


func cycle(dir: int) -> void:
	if slots.size() > 1:
		switch_to(posmod(current_index + dir, slots.size()))


func refill_all() -> void:
	for w in slots:
		w.refill()
	if current():
		ammo_changed.emit(current())


## Applies Pack-a-Punch to the current weapon. Returns false if not possible.
func upgrade_current() -> bool:
	var w := current()
	if w == null or not w.apply_upgrade():
		return false
	current_viewmodel().set_upgraded(true)
	weapon_changed.emit(w)
	ammo_changed.emit(w)
	return true


## Lowers the weapon and blocks input (Pack-a-Punch, menus).
func set_busy(busy: bool) -> void:
	var vm := current_viewmodel()
	if busy:
		if state == State.RELOADING and vm:
			vm.cancel_animation()
		state = State.BUSY
		if vm:
			vm.play_lower(0.3)
	else:
		state = State.SWITCHING
		_state_timer = 0.4
		if vm:
			vm.play_equip(0.4)


# ------------------------------------------------------------------ input

func _can_act() -> bool:
	return player != null and player.can_act()


func _unhandled_input(event: InputEvent) -> void:
	if not _can_act():
		return
	if event.is_action_pressed("reload"):
		reload()
	elif event.is_action_pressed("weapon_next") or event.is_action_pressed("weapon_swap"):
		cycle(1)
	elif event.is_action_pressed("weapon_prev"):
		cycle(-1)
	elif event.is_action_pressed("weapon_1"):
		switch_to(0)
	elif event.is_action_pressed("weapon_2"):
		switch_to(1)


func reload() -> void:
	var w := current()
	if w == null or state != State.READY or not w.can_reload():
		return
	state = State.RELOADING
	var dur := w.data.reload_time * (0.85 if w.upgraded else 1.0)
	_state_timer = dur
	current_viewmodel().play_reload(dur)
	_play(w.data.reload_sound, -2.0)
	reload_started.emit(w, dur)


func _physics_process(delta: float) -> void:
	_cooldown = max(_cooldown - delta, 0.0)
	_spread_bloom = move_toward(_spread_bloom, 0.0, delta * 4.0)
	var w := current()
	if state == State.RELOADING or state == State.SWITCHING:
		_state_timer -= delta
		if _state_timer <= 0.0:
			if state == State.RELOADING and w:
				w.finish_reload()
				reload_finished.emit(w)
			state = State.READY
	var acting := _can_act()
	var trigger := acting and Input.is_action_pressed("fire")
	var want_ads := acting and Input.is_action_pressed("aim") and state != State.BUSY
	if w:
		var target := 1.0 if want_ads else 0.0
		ads_amount = move_toward(ads_amount, target, delta / max(w.data.ads_time, 0.01))
	if trigger and w and state == State.READY and _cooldown <= 0.0:
		var auto := w.data.fire_mode == WeaponData.FireMode.AUTO
		if auto or not _trigger_was_down:
			if w.can_fire():
				_fire(w)
			elif not _trigger_was_down:
				_play(w.data.dry_sound, -4.0)
				dry_fired.emit(w)
				_cooldown = 0.25
				if w.reserve > 0:
					reload()
	_trigger_was_down = trigger
	# auto reload when empty
	if w and acting and state == State.READY and w.mag == 0 and w.reserve > 0 and not trigger:
		reload()


# ------------------------------------------------------------------ firing

func current_spread_deg() -> float:
	var w := current()
	if w == null:
		return 0.0
	var moving := 0.0
	if player and player.has_method("horizontal_speed"):
		moving = clamp(player.horizontal_speed() / 5.0, 0.0, 1.0)
	var hip := w.data.hip_spread_deg + w.data.move_spread_deg * moving
	return lerp(hip, w.data.ads_spread_deg, ads_amount) + _spread_bloom


func _fire(w: WeaponInstance) -> void:
	if not w.consume_round():
		return
	_cooldown = w.fire_interval()
	var vm := current_viewmodel()
	vm.play_fire()
	var snd := w.data.upgraded_fire_sound if (w.upgraded and w.data.upgraded_fire_sound) else w.data.fire_sound
	Sfx.play_2d(self, snd, -3.0, 0.04)
	if w.data.projectile == WeaponData.Projectile.LIGHTNING:
		_fire_lightning(w)
	else:
		for i in w.data.pellets:
			_fire_hitscan(w)
		_spread_bloom = minf(_spread_bloom + w.data.hip_spread_deg * 0.25, 3.0)
	# recoil is applied after the shot so it affects the *next* round, not this one
	var pitch := w.data.recoil_pitch_deg * (1.0 - 0.4 * ads_amount)
	var yaw := w.data.recoil_yaw_deg * _rng.randf_range(-1.0, 1.0)
	if player and player.has_method("apply_recoil"):
		player.apply_recoil(pitch, yaw)
	fired.emit(w)


func _aim_ray(spread_deg: float) -> Array:
	var from := camera.global_position
	var fwd := -camera.global_basis.z
	if spread_deg > 0.0:
		var ang := deg_to_rad(spread_deg) * sqrt(_rng.randf())
		var rot := _rng.randf() * TAU
		var right := camera.global_basis.x
		var up := camera.global_basis.y
		fwd = (fwd + (right * cos(rot) + up * sin(rot)) * tan(ang)).normalized()
	return [from, fwd]


func _raycast(from: Vector3, dir: Vector3, dist: float, exclude: Array[RID]) -> Dictionary:
	var q := PhysicsRayQueryParameters3D.create(from, from + dir * dist, Layers.BULLET_MASK, exclude)
	q.collide_with_areas = true
	q.collide_with_bodies = true
	return get_world_3d().direct_space_state.intersect_ray(q)


func _fire_hitscan(w: WeaponInstance) -> void:
	var ray := _aim_ray(current_spread_deg())
	var from: Vector3 = ray[0]
	var dir: Vector3 = ray[1]
	var exclude: Array[RID] = []
	if player is CollisionObject3D:
		exclude.append((player as CollisionObject3D).get_rid())
	var remaining_targets := 1 + w.data.penetration
	var end_point := from + dir * w.data.max_range
	var hit_zombies := {}
	for i in 6:
		var hit := _raycast(from, dir, w.data.max_range, exclude)
		if hit.is_empty():
			break
		var col: Object = hit.collider
		if col is Hurtbox:
			var hb := col as Hurtbox
			exclude.append(hb.get_rid())
			if hb.zombie == null or hit_zombies.has(hb.zombie) or not hb.zombie.is_alive():
				continue
			hit_zombies[hb.zombie] = true
			var dist := from.distance_to(hit.position)
			_apply_hit(w, hb, hit.position, dir, dist, false)
			remaining_targets -= 1
			if remaining_targets <= 0:
				end_point = hit.position
				break
		else:
			end_point = hit.position
			ImpactFX.world_hit(self, hit.position, hit.normal)
			break
	if w.data.tracer and current_viewmodel():
		Tracer.spawn(self, current_viewmodel().muzzle_position(), end_point)


func _fire_lightning(w: WeaponInstance) -> void:
	# No spread, no auto-aim, no chaining: the bolt strikes exactly where aimed.
	var ray := _aim_ray(0.0)
	var from: Vector3 = ray[0]
	var dir: Vector3 = ray[1]
	var exclude: Array[RID] = []
	if player is CollisionObject3D:
		exclude.append((player as CollisionObject3D).get_rid())
	var end_point := from + dir * w.data.max_range
	var normal := -dir
	for i in 4:
		var hit := _raycast(from, dir, w.data.max_range, exclude)
		if hit.is_empty():
			break
		if hit.collider is Hurtbox:
			var hb := hit.collider as Hurtbox
			if hb.zombie == null or not hb.zombie.is_alive():
				exclude.append(hb.get_rid())
				continue
			end_point = hit.position
			_apply_hit(w, hb, hit.position, dir, from.distance_to(hit.position), true)
			break
		end_point = hit.position
		normal = hit.normal
		break
	var vm := current_viewmodel()
	var start := vm.muzzle_position() if vm else from
	LightningBeam.spawn(self, start, end_point, w.data.bolt_color, 0.1 if not w.upgraded else 0.14)
	ImpactFX.lightning_hit(self, end_point, normal, w.data.bolt_color)


func _apply_hit(w: WeaponInstance, hb: Hurtbox, pos: Vector3, dir: Vector3, dist: float, lightning: bool) -> void:
	var dmg := w.damage_at(dist) * hb.damage_multiplier
	if hb.is_head:
		dmg *= w.data.headshot_multiplier
	if player and "damage_multiplier" in player:
		dmg *= player.damage_multiplier
	var result: Dictionary = hb.zombie.take_damage(dmg, {
		"is_head": hb.is_head, "position": pos, "direction": dir, "lightning": lightning, "weapon": w.data.id,
	})
	result["weapon"] = w
	if not lightning:
		ImpactFX.flesh_hit(self, pos, dir)
	_play(hitmarker_sound, -8.0 if not result.get("killed", false) else -4.0)
	hit_registered.emit(result)


# ------------------------------------------------------------------ motion

func add_look_sway(delta_px: Vector2) -> void:
	_sway += delta_px * 0.00012


func _process(delta: float) -> void:
	var w := current()
	var vm := current_viewmodel()
	if w == null or vm == null:
		return
	var speed := 0.0
	var grounded := true
	var sprinting := false
	if player:
		speed = player.horizontal_speed()
		grounded = player.is_on_floor()
		sprinting = player.is_sprinting()
	_bob_t += delta * speed * 1.6
	var bob_amt: float = clamp(speed / 5.0, 0.0, 1.4) * (1.0 - 0.85 * ads_amount) * (1.0 if grounded else 0.3)
	var bob := Vector3(sin(_bob_t) * 0.012, -abs(cos(_bob_t)) * 0.014, 0.0) * bob_amt
	_sway = _sway.lerp(Vector2.ZERO, min(delta * 8.0, 1.0))
	var sway := Vector3(-_sway.x, _sway.y, 0.0) * (1.0 - 0.7 * ads_amount)
	var ads_off := w.data.ads_offset
	var base := w.data.hip_offset.lerp(ads_off, ease(ads_amount, -1.6))
	var sprint_pose := 1.0 if (sprinting and state == State.READY) else 0.0
	var kick := vm.kick_amount()
	var pos := base + bob + sway + vm.anim_offset + Vector3(0, -0.04, 0.05) * sprint_pose + Vector3(0, 0, w.data.recoil_kick * kick)
	var rot := vm.anim_rotation + Vector3(-0.35, 0.5, 0.15) * sprint_pose + Vector3(0.06 * kick * (1.0 - 0.6 * ads_amount), 0, 0)
	rot += Vector3(_sway.y * 2.0, -_sway.x * 2.0, -_sway.x * 1.5)
	_pivot.position = _pivot.position.lerp(Vector3.ZERO, 1.0)
	vm.position = vm.position.lerp(pos, min(delta * 18.0, 1.0))
	vm.rotation = vm.rotation.lerp(rot, min(delta * 14.0, 1.0))
	if camera:
		var fov_target: float = lerp(Settings.field_of_view, w.data.ads_fov, ease(ads_amount, -1.6))
		camera.fov = lerp(camera.fov, fov_target, min(delta * 20.0, 1.0))


func _play(stream: AudioStream, vol := 0.0) -> void:
	if stream:
		Sfx.play_2d(self, stream, vol, 0.03)
