class_name Interactable
extends Node3D
## Base class for anything the player can use with the interact key.
## Subclasses override get_prompt() and interact().

@export var prompt_offset := Vector3(0, 1.0, 0)
@export var extra_reach := 0.0
@export var deny_sound: AudioStream


func _ready() -> void:
	add_to_group("interactable")


func is_enabled() -> bool:
	return true


func interaction_point() -> Vector3:
	return global_transform * prompt_offset


func get_prompt(_player: Player) -> String:
	return ""


func interact(_player: Player) -> void:
	pass


func wallet() -> PointsWallet:
	return get_tree().get_first_node_in_group("points_wallet") as PointsWallet


func economy() -> EconomyConfig:
	var w := wallet()
	return w.config if w else null


func deny() -> void:
	if deny_sound:
		Sfx.play_3d(self, deny_sound, interaction_point(), -2.0)
