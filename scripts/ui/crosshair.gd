class_name Crosshair
extends Control
## Dynamic four-line crosshair with a hitmarker.

var spread := 2.0           ## degrees, drives the gap
var _hit_t := 0.0
var _hit_kill := false
var _hit_head := false


func hitmarker(kill: bool, head: bool) -> void:
	_hit_t = 0.22 if not kill else 0.35
	_hit_kill = kill
	_hit_head = head


func _process(delta: float) -> void:
	_hit_t = max(_hit_t - delta, 0.0)
	queue_redraw()


func _draw() -> void:
	var gap := 6.0 + spread * 7.0
	var len := 11.0
	var col := Color(0.95, 0.92, 0.85, 0.85)
	var sh := Color(0, 0, 0, 0.6)
	for d in [Vector2.UP, Vector2.DOWN, Vector2.LEFT, Vector2.RIGHT]:
		var a: Vector2 = d * gap
		var b: Vector2 = d * (gap + len)
		draw_line(a + Vector2(1, 1), b + Vector2(1, 1), sh, 3.0)
		draw_line(a, b, col, 2.0)
	draw_circle(Vector2.ZERO, 1.5, col)
	if _hit_t > 0.0:
		var hc := Color(1, 1, 1, 1) if not _hit_kill else Color(1.0, 0.15, 0.1, 1)
		if _hit_head and _hit_kill:
			hc = Color(1.0, 0.75, 0.2, 1)
		var s := 9.0 + (5.0 if _hit_kill else 0.0)
		for d in [Vector2(1, 1), Vector2(-1, 1), Vector2(1, -1), Vector2(-1, -1)]:
			draw_line(d * 5.0, d * s, Color(0, 0, 0, 0.6), 4.0)
			draw_line(d * 5.0, d * s, hc, 2.5)
