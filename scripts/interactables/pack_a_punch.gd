class_name PackAPunch
extends Interactable
## Upgrades the player's current weapon (one tier). Points are only taken when
## the upgrade is actually applied; failed upgrades are refunded.

signal upgrade_started(weapon: WeaponInstance)
signal upgrade_finished(weapon: WeaponInstance, success: bool)

enum State { IDLE, WORKING }

@export var process_time := 3.2
@export var work_sound: AudioStream
@export var done_sound: AudioStream

var state := State.IDLE
var _disc: Node3D
var _gears: Array[Node3D] = []
var _light: OmniLight3D
var _spin := 0.4
var _player: Player
var _weapon: WeaponInstance
var _timer := 0.0


func _ready() -> void:
	super._ready()
	_disc = find_child("Disc", true, false)
	for n in ["GearL", "GearR"]:
		var g := find_child(n, true, false)
		if g:
			_gears.append(g)
	_light = OmniLight3D.new()
	_light.light_color = Color(1.0, 0.5, 0.15)
	_light.omni_range = 7.0
	_light.light_energy = 1.5
	_light.position = Vector3(0, 1.2, 1.2)
	add_child(_light)


func cost() -> int:
	var e := economy()
	return e.pack_a_punch_cost if e else 5000


func get_prompt(player: Player) -> String:
	if state == State.WORKING:
		return ""
	var w := player.weapons.current()
	if w == null:
		return ""
	if not w.can_upgrade():
		return "%s is already upgraded" % w.display_name()
	var wal := wallet()
	if wal and not wal.can_afford(cost()):
		return "Pack-a-Punch  [%d]  -  not enough points" % cost()
	return "Press E to Pack-a-Punch %s  [%d]" % [w.display_name(), cost()]


func interact(player: Player) -> void:
	if state != State.IDLE:
		return
	var w := player.weapons.current()
	var wal := wallet()
	if w == null or not w.can_upgrade() or wal == null or not wal.can_afford(cost()):
		deny()
		return
	state = State.WORKING
	_player = player
	_weapon = w
	_timer = process_time
	player.weapons.set_busy(true)
	Sfx.play_3d(self, work_sound, global_position + Vector3(0, 1.2, 0.8), 0.0, 0.0)
	upgrade_started.emit(w)


func _finish() -> void:
	var success := false
	var wal := wallet()
	if _player and _player.is_alive() and _player.weapons.current() == _weapon and wal:
		if wal.try_spend(cost()):
			success = _player.weapons.upgrade_current()
			if not success:
				wal.refund(cost())
	if _player:
		_player.weapons.set_busy(false)
	if success:
		Sfx.play_3d(self, done_sound, global_position + Vector3(0, 1.2, 0.8), 2.0, 0.0)
		var t := create_tween()
		t.tween_property(_light, "light_energy", 12.0, 0.08)
		t.tween_property(_light, "light_energy", 1.5, 0.6)
	upgrade_finished.emit(_weapon, success)
	state = State.IDLE
	_player = null
	_weapon = null


func _process(delta: float) -> void:
	var target_spin := 6.0 if state == State.WORKING else 0.4
	_spin = lerp(_spin, target_spin, min(delta * 2.0, 1.0))
	if _disc:
		_disc.rotate_object_local(Vector3.FORWARD, delta * _spin)
	for i in _gears.size():
		_gears[i].rotate_object_local(Vector3.RIGHT, delta * _spin * (1.0 if i == 0 else -1.3))
	if state == State.WORKING:
		_light.light_energy = 3.0 + sin(Time.get_ticks_msec() * 0.03) * 1.5
		_timer -= delta
		if _player and not _player.is_alive():
			_timer = 0.0
		if _timer <= 0.0:
			_finish()
