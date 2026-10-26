class_name InputSetup
extends RefCounted
## Registers the game's input actions in code so the bindings live in one
## readable place (and survive project.godot edits by other tools).

const KEYS := {
	"move_forward": [KEY_W, KEY_UP],
	"move_back": [KEY_S, KEY_DOWN],
	"move_left": [KEY_A, KEY_LEFT],
	"move_right": [KEY_D, KEY_RIGHT],
	"sprint": [KEY_SHIFT],
	"jump": [KEY_SPACE],
	"reload": [KEY_R],
	"interact": [KEY_E],
	"pause": [KEY_ESCAPE],
	"weapon_1": [KEY_1],
	"weapon_2": [KEY_2],
	"weapon_3": [KEY_3],
	"weapon_swap": [KEY_Q],
}
const MOUSE := {
	"fire": [MOUSE_BUTTON_LEFT],
	"aim": [MOUSE_BUTTON_RIGHT],
	"weapon_next": [MOUSE_BUTTON_WHEEL_UP],
	"weapon_prev": [MOUSE_BUTTON_WHEEL_DOWN],
}


static func register_actions() -> void:
	for action in KEYS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key in KEYS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
	for action in MOUSE:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for b in MOUSE[action]:
			var ev := InputEventMouseButton.new()
			ev.button_index = b
			InputMap.action_add_event(action, ev)
