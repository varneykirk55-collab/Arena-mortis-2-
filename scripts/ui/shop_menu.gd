class_name ShopMenu
extends CanvasLayer
## Between-round shop. Lists ShopItems from the EconomyConfig, applies their
## effects to the player, and starts the next round when the player leaves.

signal closed

var wallet: PointsWallet
var player: Player
var purchases := {}            ## item id -> times bought (this run)

var _root: Control
var _list: VBoxContainer
var _points: Label
var _header: Label
var _continue: Button
var _rows := {}
var _buy_sound: AudioStream
var _deny_sound: AudioStream


func setup(p_wallet: PointsWallet, p_player: Player, buy_sound: AudioStream, deny_sound: AudioStream) -> void:
	wallet = p_wallet
	player = p_player
	_buy_sound = buy_sound
	_deny_sound = deny_sound
	wallet.points_changed.connect(func(_p, _d): _refresh())


func _ready() -> void:
	layer = 15
	process_mode = Node.PROCESS_MODE_ALWAYS
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_root)
	_root.add_child(UIUtil.dim_background())
	var v := UIUtil.centered_panel(_root, Vector2(820, 0))
	_header = UIUtil.title("ROUND SURVIVED", 56)
	v.add_child(_header)
	var sub := UIUtil.text("The gates are sealed for a moment. Spend your points before the next wave.", 22, Color(0.78, 0.72, 0.64))
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(sub)
	_points = UIUtil.title("0", 40, Color(0.95, 0.78, 0.38))
	v.add_child(_points)
	_list = VBoxContainer.new()
	_list.add_theme_constant_override("separation", 10)
	v.add_child(_list)
	_continue = UIUtil.button("Begin next round", _on_continue, 420)
	_continue.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(_continue)
	visible = false


func open(completed_round: int) -> void:
	_header.text = "ROUND %s SURVIVED" % Roman.to_roman(completed_round)
	_continue.text = "Begin round %s" % Roman.to_roman(completed_round + 1)
	_build_rows()
	_refresh()
	visible = true
	_continue.grab_focus()


func _build_rows() -> void:
	for c in _list.get_children():
		c.queue_free()
	_rows.clear()
	for item in wallet.config.shop_items:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 18)
		var info := VBoxContainer.new()
		info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var name_l := UIUtil.text(item.display_name, 28, Color(0.95, 0.88, 0.75))
		var desc_l := UIUtil.text(item.description, 18, Color(0.7, 0.65, 0.58))
		info.add_child(name_l)
		info.add_child(desc_l)
		row.add_child(info)
		var btn := Button.new()
		btn.custom_minimum_size = Vector2(220, 56)
		btn.pressed.connect(buy.bind(item))
		row.add_child(btn)
		_list.add_child(row)
		_rows[item.id] = {"button": btn, "name": name_l, "item": item}


func times_bought(item: ShopItem) -> int:
	return purchases.get(item.id, 0)


## Returns "" if the item can be bought, otherwise the reason it cannot.
func unavailable_reason(item: ShopItem) -> String:
	if item.is_maxed(times_bought(item)):
		return "MAXED"
	if item.effect == ShopItem.Effect.AMMO_REFILL and _all_full():
		return "AMMO FULL"
	if not wallet.can_afford(item.cost_for(times_bought(item))):
		return "NEED POINTS"
	return ""


func _all_full() -> bool:
	for w in player.weapons.slots:
		if not w.is_full():
			return false
	return true


## Attempts a purchase. Returns true when points were spent and the effect applied.
func buy(item: ShopItem) -> bool:
	if unavailable_reason(item) != "":
		if _deny_sound:
			Sfx.play_2d(self, _deny_sound, -4.0)
		return false
	var cost := item.cost_for(times_bought(item))
	if not wallet.try_spend(cost):
		return false
	match item.effect:
		ShopItem.Effect.MAX_HEALTH:
			player.add_max_health(item.effect_value)
		ShopItem.Effect.AMMO_REFILL:
			player.weapons.refill_all()
		ShopItem.Effect.DAMAGE:
			player.damage_multiplier += item.effect_value
	purchases[item.id] = times_bought(item) + 1
	if _buy_sound:
		Sfx.play_2d(self, _buy_sound, -2.0)
	_refresh()
	return true


func _refresh() -> void:
	if wallet == null or _points == null:
		return
	_points.text = "%s points" % HUD._fmt(wallet.points)
	for id in _rows:
		var r: Dictionary = _rows[id]
		var item: ShopItem = r.item
		var reason := unavailable_reason(item)
		var btn: Button = r.button
		var n := times_bought(item)
		var lvl := (" (%d/%d)" % [n, item.max_purchases]) if item.max_purchases > 0 else ""
		r.name.text = item.display_name + lvl
		if reason == "MAXED" or reason == "AMMO FULL":
			btn.text = reason
			btn.disabled = true
		else:
			btn.text = "Buy  -  %d" % item.cost_for(n)
			btn.disabled = reason != ""


func _on_continue() -> void:
	visible = false
	closed.emit()
