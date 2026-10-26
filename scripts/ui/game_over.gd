class_name GameOverScreen
extends CanvasLayer
## Shown after death with run statistics and restart options.

signal restart_requested
signal quit_requested

var _stats: Label
var _root: Control


func _ready() -> void:
	layer = 25
	process_mode = Node.PROCESS_MODE_ALWAYS
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_root)
	var bg := UIUtil.dim_background()
	bg.color = Color(0.12, 0.0, 0.0, 0.78)
	_root.add_child(bg)
	var v := UIUtil.centered_panel(_root, Vector2(640, 0))
	v.add_child(UIUtil.title("YOU HAVE FALLEN", 64))
	_stats = UIUtil.text("", 26)
	_stats.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(_stats)
	var b := UIUtil.button("Restart", func(): restart_requested.emit())
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(b)
	var q := UIUtil.button("Main Menu", func(): quit_requested.emit())
	q.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(q)
	visible = false


func open(round_reached: int, kills: int, headshots: int, points_earned: int) -> void:
	_stats.text = "You survived until round %s\n\nKills  %d     Headshots  %d\nPoints earned  %s" % [
		Roman.to_roman(round_reached), kills, headshots, HUD._fmt(points_earned)]
	visible = true
	_root.modulate.a = 0.0
	var t := create_tween()
	t.tween_property(_root, "modulate:a", 1.0, 1.2)
