class_name UIUtil
extends RefCounted
## Small helpers for building menus in code.

const CINZEL := preload("res://assets/fonts/Cinzel-Variable.ttf")
const OSWALD := preload("res://assets/fonts/Oswald-Variable.ttf")


static func title(text: String, size := 72, color := Color(0.75, 0.08, 0.05)) -> Label:
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_override("font", CINZEL)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_constant_override("outline_size", 8)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	return l


static func text(t: String, size := 24, color := Color(0.93, 0.88, 0.78)) -> Label:
	var l := Label.new()
	l.text = t
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l


static func button(t: String, cb: Callable, min_w := 360) -> Button:
	var b := Button.new()
	b.text = t
	b.custom_minimum_size = Vector2(min_w, 54)
	b.pressed.connect(cb)
	return b


static func dim_background() -> ColorRect:
	var c := ColorRect.new()
	c.color = Color(0.02, 0.0, 0.0, 0.72)
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	return c


static func centered_panel(parent: Control, min_size := Vector2(560, 0)) -> VBoxContainer:
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	parent.add_child(center)
	var panel := PanelContainer.new()
	panel.custom_minimum_size = min_size
	center.add_child(panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 14)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	panel.add_child(v)
	return v
