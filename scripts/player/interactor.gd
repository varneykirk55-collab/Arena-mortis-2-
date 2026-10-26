class_name Interactor
extends Node3D
## Finds the best Interactable in front of the player and forwards the
## interact action to it. Emits the prompt text for the HUD.

signal prompt_changed(text: String)

@export var reach := 2.6
@export var min_facing := 0.45

var focused: Interactable
var _last_prompt := "__"
@onready var player: Player = get_parent()


func _process(_delta: float) -> void:
	var best: Interactable = null
	var best_score := -INF
	if player.can_act():
		var cam := player.camera
		var fwd := -cam.global_basis.z
		for n in get_tree().get_nodes_in_group("interactable"):
			var it := n as Interactable
			if it == null or not it.is_enabled():
				continue
			var to := it.interaction_point() - cam.global_position
			var d := to.length()
			if d > reach + it.extra_reach:
				continue
			var facing := fwd.dot(to.normalized())
			if facing < min_facing:
				continue
			var score := facing * 2.0 - d * 0.3
			if score > best_score:
				best_score = score
				best = it
	focused = best
	var prompt := best.get_prompt(player) if best else ""
	if prompt != _last_prompt:
		_last_prompt = prompt
		prompt_changed.emit(prompt)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("interact") and focused and player.can_act():
		focused.interact(player)
		_last_prompt = "__"
