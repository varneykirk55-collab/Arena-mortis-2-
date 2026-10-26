class_name MysteryBox
extends Interactable
## Pay to open; the lid opens, weapons cycle above the box, one is chosen
## from a weighted pool and offered to the buyer for a limited time.

signal opened
signal weapon_offered(weapon: WeaponData)
signal weapon_taken(weapon: WeaponData)
signal closed

enum State { IDLE, CYCLING, OFFERING, CLOSING }

@export var pool: Array[WeaponData] = []
@export var cycle_time := 3.4
@export var offer_time := 9.0
@export var open_sound: AudioStream
@export var close_sound: AudioStream
@export var reveal_sound: AudioStream

var state := State.IDLE
var selected: WeaponData
var _lid: Node3D
var _anchor: Node3D
var _display: Node3D
var _display_id: StringName
var _light: OmniLight3D
var _timer := 0.0
var _swap_t := 0.0
var _buyer: Player
var _rng := RandomNumberGenerator.new()
var _model_cache := {}


func _ready() -> void:
	super._ready()
	_rng.randomize()
	_lid = find_child("Lid", true, false)
	_anchor = find_child("WeaponAnchor", true, false)
	_light = OmniLight3D.new()
	_light.light_color = Color(1.0, 0.7, 0.3)
	_light.omni_range = 8.0
	_light.light_energy = 1.8
	_light.position = Vector3(0, 1.4, 0.6)
	add_child(_light)


func cost() -> int:
	var e := economy()
	return e.mystery_box_cost if e else 950


## Weighted pick from `pool` using each WeaponData.box_weight.
static func roll(weapons: Array[WeaponData], rng: RandomNumberGenerator) -> WeaponData:
	var total := 0.0
	for w in weapons:
		total += max(w.box_weight, 0.0)
	if total <= 0.0:
		return null
	var r := rng.randf() * total
	for w in weapons:
		r -= max(w.box_weight, 0.0)
		if r <= 0.0:
			return w
	return weapons.back()


func get_prompt(player: Player) -> String:
	match state:
		State.IDLE:
			var w := wallet()
			if w and not w.can_afford(cost()):
				return "Mystery Box  [%d]  -  not enough points" % cost()
			return "Press E for the Mystery Box  [%d]" % cost()
		State.OFFERING:
			if player == _buyer and selected:
				return "Press E to take %s" % selected.display_name
	return ""


func interact(player: Player) -> void:
	match state:
		State.IDLE:
			var w := wallet()
			if w == null or not w.try_spend(cost()):
				deny()
				return
			_buyer = player
			_open()
		State.OFFERING:
			if player == _buyer and selected:
				player.weapons.give_weapon(selected)
				weapon_taken.emit(selected)
				_close()


func _open() -> void:
	state = State.CYCLING
	selected = roll(pool, _rng)
	_timer = cycle_time
	_swap_t = 0.0
	Sfx.play_3d(self, open_sound, global_position + Vector3.UP, 0.0, 0.0)
	var t := create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	if _lid:
		t.tween_property(_lid, "rotation:x", deg_to_rad(-105.0), 0.6)
	t.parallel().tween_property(_light, "light_energy", 4.0, 0.6)
	opened.emit()


func _close() -> void:
	state = State.CLOSING
	_buyer = null
	_clear_display()
	Sfx.play_3d(self, close_sound, global_position + Vector3.UP, -2.0, 0.0)
	var t := create_tween()
	if _lid:
		t.tween_property(_lid, "rotation:x", 0.0, 0.5).set_trans(Tween.TRANS_BOUNCE).set_ease(Tween.EASE_OUT)
	t.parallel().tween_property(_light, "light_energy", 1.8, 0.5)
	t.tween_callback(func(): state = State.IDLE; closed.emit())


func _show_weapon(data: WeaponData) -> void:
	if _display_id == data.id and _display:
		return
	_clear_display()
	_display = data.viewmodel_scene.instantiate()
	_display_id = data.id
	_anchor.add_child(_display)
	_display.scale = Vector3.ONE * 2.2
	_display.rotation = Vector3(0, PI * 0.5, 0)


func _clear_display() -> void:
	if _display:
		_display.queue_free()
	_display = null
	_display_id = &""


func _process(delta: float) -> void:
	match state:
		State.CYCLING:
			_timer -= delta
			_swap_t -= delta
			var progress: float = 1.0 - _timer / cycle_time
			if _swap_t <= 0.0:
				_swap_t = lerp(0.08, 0.38, progress * progress)
				_show_weapon(pool[_rng.randi() % pool.size()])
			if _display:
				_display.position.y = progress * 0.45
				_display.rotate_y(delta * 2.5)
			if _timer <= 0.0:
				_show_weapon(selected)
				_display.position.y = 0.45
				state = State.OFFERING
				_timer = offer_time
				Sfx.play_3d(self, reveal_sound, global_position + Vector3.UP, 0.0, 0.0)
				weapon_offered.emit(selected)
		State.OFFERING:
			_timer -= delta
			if _display:
				_display.rotation.y = PI * 0.5 + sin(Time.get_ticks_msec() * 0.002) * 0.4
				# sink back into the box during the last seconds
				if _timer < 3.0:
					_display.position.y = 0.45 * (_timer / 3.0)
			if _timer <= 0.0:
				_close()
