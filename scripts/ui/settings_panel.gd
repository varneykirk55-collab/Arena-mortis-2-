class_name SettingsPanel
extends VBoxContainer
## Mouse sensitivity, FOV, invert-Y and volume controls bound to Settings.

signal back_pressed


func _ready() -> void:
	add_theme_constant_override("separation", 12)
	add_child(UIUtil.title("SETTINGS", 44, Color(0.95, 0.78, 0.38)))
	_slider("Mouse sensitivity", "mouse_sensitivity", 0.1, 4.0, 0.05)
	_slider("Field of view", "field_of_view", 65.0, 100.0, 1.0)
	_slider("Master volume", "master_volume", 0.0, 1.0, 0.05)
	_slider("Effects volume", "sfx_volume", 0.0, 1.0, 0.05)
	_slider("Ambience volume", "ambient_volume", 0.0, 1.0, 0.05)
	var inv := CheckBox.new()
	inv.text = "Invert mouse Y"
	inv.button_pressed = Settings.invert_y
	inv.toggled.connect(func(on): Settings.set_value("invert_y", on))
	add_child(inv)
	var fs := CheckBox.new()
	fs.text = "Fullscreen"
	fs.button_pressed = Settings.fullscreen
	fs.toggled.connect(func(on): Settings.set_value("fullscreen", on))
	add_child(fs)
	var back := UIUtil.button("Back", func(): back_pressed.emit())
	back.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	add_child(back)


func _slider(label: String, key: String, mn: float, mx: float, step: float) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	var l := UIUtil.text(label, 22)
	l.custom_minimum_size = Vector2(230, 0)
	l.autowrap_mode = TextServer.AUTOWRAP_OFF
	row.add_child(l)
	var s := HSlider.new()
	s.min_value = mn
	s.max_value = mx
	s.step = step
	s.value = Settings.get(key)
	s.custom_minimum_size = Vector2(260, 30)
	s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var val := UIUtil.text(_fmt(s.value, step), 22, Color(0.95, 0.78, 0.38))
	val.custom_minimum_size = Vector2(60, 0)
	val.autowrap_mode = TextServer.AUTOWRAP_OFF
	s.value_changed.connect(func(v):
		Settings.set_value(key, v)
		val.text = _fmt(v, step))
	row.add_child(s)
	row.add_child(val)
	add_child(row)


static func _fmt(v: float, step: float) -> String:
	return str(int(v)) if step >= 1.0 else "%.2f" % v
