class_name HUD
extends CanvasLayer
## In-game heads-up display. Built in code; bind() connects it to the
## gameplay systems' signals. It only displays state, never changes it.

const CINZEL := preload("res://assets/fonts/Cinzel-Variable.ttf")
const OSWALD := preload("res://assets/fonts/Oswald-Variable.ttf")
const GOLD := Color(0.95, 0.78, 0.38)
const BLOOD := Color(0.72, 0.06, 0.04)
const BONE := Color(0.93, 0.88, 0.78)

var crosshair: Crosshair
var round_label: Label
var remaining_label: Label
var points_label: Label
var health_bar: ProgressBar
var health_label: Label
var weapon_label: Label
var ammo_label: Label
var reserve_label: Label
var upgrade_label: Label
var prompt_label: Label
var prompt_panel: PanelContainer
var message_label: Label
var sub_message_label: Label
var hint_label: Label
var vignette: TextureRect
var _popups: Control
var _root: Control

var _player: Player
var _weapons: WeaponManager
var _vignette_alpha := 0.0
var _msg_tween: Tween


func _ready() -> void:
	layer = 5
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)
	_build_vignette()
	_build_crosshair()
	_build_round()
	_build_points_health()
	_build_weapon()
	_build_prompt_and_messages()


# ------------------------------------------------------------------ building

func _label(text: String, font: Font, size: int, color: Color, align := HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.85))
	l.add_theme_constant_override("shadow_offset_x", 2)
	l.add_theme_constant_override("shadow_offset_y", 3)
	l.add_theme_constant_override("outline_size", 4)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.6))
	l.horizontal_alignment = align
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


## Anchors `c` to a point of the screen (0..1) and places it at a pixel offset
## from that anchor with the given size.
func _place(c: Control, anchor: Vector2, offset: Vector2, size: Vector2) -> void:
	_root.add_child(c)
	c.anchor_left = anchor.x
	c.anchor_right = anchor.x
	c.anchor_top = anchor.y
	c.anchor_bottom = anchor.y
	c.offset_left = offset.x
	c.offset_top = offset.y
	c.offset_right = offset.x + size.x
	c.offset_bottom = offset.y + size.y


func _build_vignette() -> void:
	vignette = TextureRect.new()
	var g := Gradient.new()
	g.set_color(0, Color(0.5, 0, 0, 0))
	g.set_color(1, Color(0.55, 0.0, 0.0, 0.85))
	g.add_point(0.55, Color(0.5, 0, 0, 0))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(1.0, 1.0)
	gt.width = 256
	gt.height = 256
	vignette.texture = gt
	vignette.stretch_mode = TextureRect.STRETCH_SCALE
	vignette.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	vignette.set_anchors_preset(Control.PRESET_FULL_RECT)
	vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	vignette.modulate.a = 0.0
	_root.add_child(vignette)


func _build_crosshair() -> void:
	crosshair = Crosshair.new()
	crosshair.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_place(crosshair, Vector2(0.5, 0.5), Vector2.ZERO, Vector2.ZERO)
	hint_label = _label("", OSWALD, 22, GOLD, HORIZONTAL_ALIGNMENT_CENTER)
	_place(hint_label, Vector2(0.5, 0.5), Vector2(-200, 46), Vector2(400, 32))


func _build_round() -> void:
	round_label = _label("", CINZEL, 104, BLOOD)
	round_label.add_theme_constant_override("outline_size", 10)
	round_label.add_theme_color_override("font_outline_color", Color(0.08, 0.0, 0.0, 0.9))
	_place(round_label, Vector2(0, 0), Vector2(46, 14), Vector2(600, 130))
	remaining_label = _label("", OSWALD, 26, BONE, HORIZONTAL_ALIGNMENT_RIGHT)
	_place(remaining_label, Vector2(1, 0), Vector2(-420, 34), Vector2(374, 40))


func _build_points_health() -> void:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 6)
	box.custom_minimum_size = Vector2(340, 0)
	points_label = _label("0", CINZEL, 46, GOLD)
	box.add_child(points_label)
	health_bar = ProgressBar.new()
	health_bar.custom_minimum_size = Vector2(300, 16)
	health_bar.show_percentage = false
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0.05, 0.02, 0.02, 0.75)
	bg.border_color = Color(0.45, 0.32, 0.15)
	bg.set_border_width_all(2)
	var fg := StyleBoxFlat.new()
	fg.bg_color = Color(0.68, 0.08, 0.05)
	health_bar.add_theme_stylebox_override("background", bg)
	health_bar.add_theme_stylebox_override("fill", fg)
	box.add_child(health_bar)
	health_label = _label("100 / 100", OSWALD, 20, BONE)
	box.add_child(health_label)
	box.alignment = BoxContainer.ALIGNMENT_END
	_place(box, Vector2(0, 1), Vector2(46, -190), Vector2(340, 150))
	_popups = Control.new()
	_popups.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_place(_popups, Vector2(0, 1), Vector2(270, -190), Vector2(10, 10))


func _build_weapon() -> void:
	var box := VBoxContainer.new()
	box.alignment = BoxContainer.ALIGNMENT_END
	box.custom_minimum_size = Vector2(460, 0)
	upgrade_label = _label("", OSWALD, 18, Color(0.85, 0.55, 1.0), HORIZONTAL_ALIGNMENT_RIGHT)
	box.add_child(upgrade_label)
	weapon_label = _label("", CINZEL, 30, BONE, HORIZONTAL_ALIGNMENT_RIGHT)
	box.add_child(weapon_label)
	var ammo_row := HBoxContainer.new()
	ammo_row.alignment = BoxContainer.ALIGNMENT_END
	ammo_label = _label("0", OSWALD, 58, BONE, HORIZONTAL_ALIGNMENT_RIGHT)
	reserve_label = _label(" / 0", OSWALD, 30, Color(0.75, 0.7, 0.62), HORIZONTAL_ALIGNMENT_LEFT)
	reserve_label.size_flags_vertical = Control.SIZE_SHRINK_END
	ammo_row.add_child(ammo_label)
	ammo_row.add_child(reserve_label)
	box.add_child(ammo_row)
	_place(box, Vector2(1, 1), Vector2(-506, -200), Vector2(460, 160))


func _build_prompt_and_messages() -> void:
	prompt_panel = PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0, 0, 0, 0.55)
	sb.content_margin_left = 16
	sb.content_margin_right = 16
	sb.content_margin_top = 6
	sb.content_margin_bottom = 6
	prompt_panel.add_theme_stylebox_override("panel", sb)
	prompt_label = _label("", OSWALD, 26, BONE, HORIZONTAL_ALIGNMENT_CENTER)
	prompt_panel.add_child(prompt_label)
	prompt_panel.visible = false
	prompt_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(prompt_panel)
	message_label = _label("", CINZEL, 64, BLOOD, HORIZONTAL_ALIGNMENT_CENTER)
	message_label.add_theme_constant_override("outline_size", 8)
	_place(message_label, Vector2(0.5, 0), Vector2(-700, 170), Vector2(1400, 90))
	sub_message_label = _label("", OSWALD, 28, BONE, HORIZONTAL_ALIGNMENT_CENTER)
	_place(sub_message_label, Vector2(0.5, 0), Vector2(-700, 262), Vector2(1400, 44))
	message_label.modulate.a = 0.0
	sub_message_label.modulate.a = 0.0


# ------------------------------------------------------------------ binding

func bind(player: Player, wallet: PointsWallet, waves: WaveManager) -> void:
	_player = player
	_weapons = player.weapons
	player.health_changed.connect(_on_health)
	player.damaged.connect(_on_damaged)
	player.interactor.prompt_changed.connect(_on_prompt)
	_weapons.weapon_changed.connect(_on_weapon)
	_weapons.ammo_changed.connect(_on_ammo)
	_weapons.hit_registered.connect(_on_hit)
	wallet.points_changed.connect(_on_points)
	waves.round_started.connect(_on_round_started)
	waves.remaining_changed.connect(_on_remaining)
	_on_health(player.health, player.max_health)
	_on_points(wallet.points, 0)
	if _weapons.current():
		_on_weapon(_weapons.current())


func _on_health(cur: float, mx: float) -> void:
	health_bar.max_value = mx
	health_bar.value = cur
	health_label.text = "%d / %d" % [ceil(cur), mx]


func _on_damaged(amount: float, _src: Vector3) -> void:
	_vignette_alpha = clamp(_vignette_alpha + amount / 45.0, 0.0, 1.0)


func _on_prompt(text: String) -> void:
	prompt_label.text = text
	prompt_panel.visible = text != ""
	prompt_panel.reset_size()
	var vp := _root.size
	prompt_panel.position = Vector2((vp.x - prompt_panel.size.x) * 0.5, vp.y * 0.64)


func _on_weapon(w: WeaponInstance) -> void:
	weapon_label.text = w.display_name()
	upgrade_label.text = "UPGRADED" if w.upgraded else ""
	_on_ammo(w)


func _on_ammo(w: WeaponInstance) -> void:
	if _weapons and w != _weapons.current():
		return
	ammo_label.text = str(w.mag)
	reserve_label.text = " / %d" % w.reserve
	var low: bool = w.mag <= maxi(1, int(w.magazine_size() * 0.25))
	ammo_label.add_theme_color_override("font_color", BLOOD if low else BONE)


func _on_points(points: int, delta: int) -> void:
	points_label.text = _fmt(points)
	if delta != 0:
		var l := _label(("+%d" if delta > 0 else "%d") % delta, OSWALD, 26 if abs(delta) < 100 else 32,
				GOLD if delta > 0 else BLOOD)
		_popups.add_child(l)
		l.position = Vector2(randf_range(0, 40), randf_range(-10, 10))
		var t := l.create_tween()
		t.tween_property(l, "position", l.position + Vector2(80, -40), 0.9)
		t.parallel().tween_property(l, "modulate:a", 0.0, 0.9)
		t.tween_callback(l.queue_free)


func _on_hit(result: Dictionary) -> void:
	crosshair.hitmarker(result.get("killed", false), result.get("is_head", false))


func _on_round_started(r: int, _total: int) -> void:
	round_label.text = Roman.to_roman(r)
	round_label.modulate = Color(3, 3, 3)
	var t := create_tween()
	t.tween_property(round_label, "modulate", Color.WHITE, 1.2)


func _on_remaining(n: int) -> void:
	remaining_label.text = "UNDEAD REMAINING  %d" % n


func show_message(title: String, subtitle := "", hold := 2.2) -> void:
	message_label.text = title
	sub_message_label.text = subtitle
	if _msg_tween and _msg_tween.is_valid():
		_msg_tween.kill()
	_msg_tween = create_tween()
	_msg_tween.tween_property(message_label, "modulate:a", 1.0, 0.3)
	_msg_tween.parallel().tween_property(sub_message_label, "modulate:a", 1.0, 0.3)
	_msg_tween.tween_interval(hold)
	_msg_tween.tween_property(message_label, "modulate:a", 0.0, 0.6)
	_msg_tween.parallel().tween_property(sub_message_label, "modulate:a", 0.0, 0.6)


static func _fmt(n: int) -> String:
	var s := str(abs(n))
	var out := ""
	while s.length() > 3:
		out = "," + s.substr(s.length() - 3) + out
		s = s.substr(0, s.length() - 3)
	return ("-" if n < 0 else "") + s + out


func _process(delta: float) -> void:
	_vignette_alpha = move_toward(_vignette_alpha, 0.0, delta * 0.5)
	var low_health := 0.0
	if _player:
		low_health = clamp(1.0 - _player.health / _player.max_health, 0.0, 1.0)
		if not _player.is_alive():
			low_health = 1.0
	vignette.modulate.a = max(_vignette_alpha, low_health * 0.75)
	if _weapons and _weapons.current():
		var w := _weapons.current()
		crosshair.spread = _weapons.current_spread_deg()
		crosshair.visible = not _weapons.is_aiming() and _player.is_alive()
		if _weapons.is_reloading():
			hint_label.text = "RELOADING"
		elif w.mag == 0 and w.reserve == 0:
			hint_label.text = "NO AMMO"
		elif w.mag <= max(1, int(w.magazine_size() * 0.25)) and w.reserve > 0:
			hint_label.text = "RELOAD  [R]"
		else:
			hint_label.text = ""
