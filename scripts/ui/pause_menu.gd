class_name PauseMenu
extends CanvasLayer
## Escape menu: resume, settings, restart, quit to main menu.

signal resume_requested
signal restart_requested
signal quit_requested

var _main: VBoxContainer
var _settings: SettingsPanel
var _root: Control


func _ready() -> void:
	layer = 20
	process_mode = Node.PROCESS_MODE_ALWAYS
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_root)
	_root.add_child(UIUtil.dim_background())
	_main = UIUtil.centered_panel(_root)
	_main.add_child(UIUtil.title("PAUSED", 64))
	_main.add_child(UIUtil.button("Resume", func(): resume_requested.emit()))
	_main.add_child(UIUtil.button("Settings", _show_settings))
	_main.add_child(UIUtil.button("Restart", func(): restart_requested.emit()))
	_main.add_child(UIUtil.button("Quit to Main Menu", func(): quit_requested.emit()))
	var controls := UIUtil.text("WASD move  -  Mouse look  -  LMB fire  -  RMB aim  -  R reload\nShift sprint  -  Space jump  -  E interact  -  1/2/Q/Wheel switch weapon", 18, Color(0.7, 0.65, 0.58))
	controls.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_main.add_child(controls)
	var sp := UIUtil.centered_panel(_root, Vector2(640, 0))
	_settings = SettingsPanel.new()
	sp.add_child(_settings)
	_settings.back_pressed.connect(_show_main)
	sp.get_parent().get_parent().visible = false
	visible = false


func open() -> void:
	visible = true
	_show_main()


func close() -> void:
	visible = false


func _show_settings() -> void:
	_main.get_parent().get_parent().visible = false
	_settings.get_parent().get_parent().get_parent().visible = true


func _show_main() -> void:
	_main.get_parent().get_parent().visible = true
	_settings.get_parent().get_parent().get_parent().visible = false
