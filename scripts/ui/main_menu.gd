extends Node3D
## Title screen: the Colosseum as a slowly orbiting backdrop with the menu.

const GAME_SCENE := "res://scenes/main/game.tscn"

var _cam: Camera3D
var _t := 0.0
var _main: Control
var _settings_wrap: Control
var _loading: Label


func _ready() -> void:
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	_cam = $Camera3D
	var ui := CanvasLayer.new()
	add_child(ui)
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	ui.add_child(root)
	var shade := TextureRect.new()
	var g := Gradient.new()
	g.set_color(0, Color(0, 0, 0, 0.75))
	g.set_color(1, Color(0, 0, 0, 0.0))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill_from = Vector2(0, 0.5)
	gt.fill_to = Vector2(0.7, 0.5)
	shade.texture = gt
	shade.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(shade)
	_main = VBoxContainer.new()
	_main.add_theme_constant_override("separation", 16)
	_main.position = Vector2(120, 250)
	root.add_child(_main)
	_main.add_child(UIUtil.title("ARENA MORTIS", 110))
	var tag := UIUtil.text("The games never ended. Neither did the dead.", 28, Color(0.9, 0.8, 0.62))
	_main.add_child(tag)
	_main.add_child(Control.new())
	_main.add_child(UIUtil.button("Enter the Arena", _start, 420))
	_main.add_child(UIUtil.button("Settings", _show_settings, 420))
	_main.add_child(UIUtil.button("Quit", func(): get_tree().quit(), 420))
	var help := UIUtil.text("WASD move   Mouse look   LMB fire   RMB aim   R reload   Shift sprint\nSpace jump   E interact   1 / 2 / Q / wheel switch weapon   Esc pause", 20, Color(0.75, 0.7, 0.62))
	help.custom_minimum_size = Vector2(900, 0)
	_main.add_child(help)
	for b in _main.get_children():
		if b is Button:
			b.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	_settings_wrap = UIUtil.centered_panel(root, Vector2(640, 0)).get_parent().get_parent()
	var sp := SettingsPanel.new()
	_settings_wrap.get_child(0).get_child(0).add_child(sp)
	sp.back_pressed.connect(func(): _settings_wrap.visible = false; _main.visible = true)
	_settings_wrap.visible = false
	_loading = UIUtil.title("", 40, Color(0.95, 0.78, 0.38))
	_loading.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_loading.position = Vector2(-300, -120)
	_loading.custom_minimum_size = Vector2(600, 60)
	root.add_child(_loading)
	(_main.get_child(3) as Button).grab_focus()


func _show_settings() -> void:
	_main.visible = false
	_settings_wrap.visible = true


func _start() -> void:
	_main.visible = false
	_loading.text = "Opening the gates..."
	await get_tree().process_frame
	await get_tree().process_frame
	get_tree().change_scene_to_file(GAME_SCENE)


func _process(delta: float) -> void:
	_t += delta * 0.035
	var r := 22.0
	_cam.position = Vector3(cos(_t) * r * 1.2, 7.0 + sin(_t * 0.7) * 1.5, sin(_t) * r * 0.75)
	_cam.look_at(Vector3(0, 9.0, 0), Vector3.UP)
