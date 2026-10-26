class_name WeaponInstance
extends RefCounted
## Runtime state of one carried weapon: ammo, upgrade tier. Pure logic so it
## can be unit-tested without a scene.

signal changed

var data: WeaponData
var upgraded := false
var mag := 0
var reserve := 0


func _init(weapon_data: WeaponData = null) -> void:
	data = weapon_data
	if data:
		mag = data.magazine_size
		reserve = data.reserve_ammo if data.starting_reserve < 0 else data.starting_reserve


func display_name() -> String:
	if upgraded and data.upgraded_name != "":
		return data.upgraded_name
	return data.display_name


func magazine_size() -> int:
	return int(round(data.magazine_size * (data.upgrade_magazine_multiplier if upgraded else 1.0)))


func max_reserve() -> int:
	return int(round(data.reserve_ammo * (data.upgrade_reserve_multiplier if upgraded else 1.0)))


func base_damage() -> float:
	return data.damage * (data.upgrade_damage_multiplier if upgraded else 1.0)


func fire_interval() -> float:
	var rate := data.fire_rate * (data.upgrade_fire_rate_multiplier if upgraded else 1.0)
	return 1.0 / max(rate, 0.01)


## Damage after range falloff (before headshot / player multipliers).
func damage_at(distance: float) -> float:
	var d := base_damage()
	if distance <= data.effective_range:
		return d
	var t: float = clamp((distance - data.effective_range) / max(data.max_range - data.effective_range, 0.01), 0.0, 1.0)
	return d * lerp(1.0, data.min_damage_factor, t)


func can_fire() -> bool:
	return mag > 0


func consume_round() -> bool:
	if mag <= 0:
		return false
	mag -= 1
	changed.emit()
	return true


func can_reload() -> bool:
	return mag < magazine_size() and reserve > 0


## Moves ammunition from reserve into the magazine. Returns rounds loaded.
func finish_reload() -> int:
	var need := magazine_size() - mag
	var take: int = min(need, reserve)
	mag += take
	reserve -= take
	changed.emit()
	return take


func refill() -> void:
	mag = magazine_size()
	reserve = max_reserve()
	changed.emit()


func is_full() -> bool:
	return mag >= magazine_size() and reserve >= max_reserve()


func can_upgrade() -> bool:
	return not upgraded and data != null


## Applies the single Pack-a-Punch tier. Returns false if nothing changed.
func apply_upgrade() -> bool:
	if not can_upgrade():
		return false
	upgraded = true
	refill()
	return true
