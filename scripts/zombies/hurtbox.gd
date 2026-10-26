class_name Hurtbox
extends Area3D
## Damage receiver on a zombie (body or head). Bullets ray-test against
## the HURTBOX layer and forward hits to `zombie`.

@export var is_head := false
@export var damage_multiplier := 1.0

var zombie: Zombie


func _init() -> void:
	collision_layer = Layers.HURTBOX
	collision_mask = 0
	monitoring = false
	monitorable = true
	input_ray_pickable = false


func disable() -> void:
	collision_layer = 0
	for c in get_children():
		if c is CollisionShape3D:
			(c as CollisionShape3D).set_deferred("disabled", true)
