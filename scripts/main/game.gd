class_name Game
extends Node3D
## Top-level orchestrator for one run. Wires gameplay systems together via
## signals and owns the run state machine:
##   PLAYING -> (round cleared) -> SHOP -> PLAYING ... -> (player died) -> GAME_OVER
## Restart reloads this scene, which guarantees a clean slate.

enum Phase { INTRO, PLAYING, INTERMISSION, SHOP, GAME_OVER }

const MAIN_MENU := "res://scenes/ui/main_menu.tscn"

@export var round_start_sound: AudioStream
@export var round_end_sound: AudioStream
@export var purchase_sound: AudioStream
@export var deny_sound: AudioStream
@export var ambient_music: AudioStream
@export var intermission_delay := 3.0
@export var start_round := 1
@export var auto_start := true          ## tests disable this to drive rounds manually

var phase := Phase.INTRO
var kills := 0
var headshots := 0
var points_earned := 0

@onready var colosseum: Colosseum = $Colosseum
@onready var player: Player = $Player
@onready var wallet: PointsWallet = $PointsWallet
@onready var waves: WaveManager = $WaveManager
@onready var hud: HUD = $HUD
@onready var pause_menu: PauseMenu = $PauseMenu
@onready var shop: ShopMenu = $ShopMenu
@onready var game_over: GameOverScreen = $GameOverScreen


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for c in [colosseum, player, waves, wallet]:
		c.process_mode = Node.PROCESS_MODE_PAUSABLE
	wallet.add_to_group("points_wallet")
	get_tree().paused = false
	# place the player
	var spawn := colosseum.get_node_or_null("Markers/PlayerSpawn") as Node3D
	if spawn:
		player.global_transform = spawn.global_transform
	# wiring
	hud.bind(player, wallet, waves)
	shop.setup(wallet, player, purchase_sound, deny_sound)
	player.weapons.hit_registered.connect(_on_hit)
	player.died.connect(_on_player_died)
	waves.round_completed.connect(_on_round_completed)
	waves.zombie_killed.connect(_on_zombie_killed)
	wallet.points_changed.connect(_on_points_changed)
	shop.closed.connect(_on_shop_closed)
	pause_menu.resume_requested.connect(resume)
	pause_menu.restart_requested.connect(restart)
	pause_menu.quit_requested.connect(quit_to_menu)
	game_over.restart_requested.connect(restart)
	game_over.quit_requested.connect(quit_to_menu)
	points_earned = 0
	if ambient_music:
		var a := AudioStreamPlayer.new()
		a.stream = ambient_music
		a.bus = &"Ambient"
		a.volume_db = -6.0
		a.autoplay = true
		add_child(a)
	_capture_mouse(true)
	if auto_start:
		_begin.call_deferred()


func _begin() -> void:
	await get_tree().create_timer(1.0).timeout
	_start_round(start_round)


func _start_round(r: int) -> void:
	phase = Phase.PLAYING
	hud.show_message("ROUND %s" % Roman.to_roman(r), "The dead rise from the gates" if r == 1 else "")
	Sfx.play_2d(self, round_start_sound, -2.0)
	waves.start_round(r)


# ------------------------------------------------------------------ scoring

func _on_points_changed(_points: int, delta: int) -> void:
	if delta > 0:
		points_earned += delta


func _on_hit(result: Dictionary) -> void:
	if result.get("damage", 0.0) <= 0.0:
		return
	var cfg := wallet.config
	wallet.add(cfg.points_per_hit)
	if result.get("killed", false):
		wallet.add(cfg.points_per_headshot_kill if result.get("is_head", false) else cfg.points_per_kill)


func _on_zombie_killed(_z: Zombie, info: Dictionary) -> void:
	kills += 1
	if info.get("is_head", false):
		headshots += 1


# ------------------------------------------------------------------ flow

func _on_round_completed(r: int) -> void:
	if phase == Phase.GAME_OVER:
		return
	phase = Phase.INTERMISSION
	wallet.add(wallet.config.round_bonus_per_round * r)
	Sfx.play_2d(self, round_end_sound, -1.0)
	hud.show_message("ROUND %s SURVIVED" % Roman.to_roman(r), "+%d bonus" % (wallet.config.round_bonus_per_round * r), 1.8)
	await get_tree().create_timer(intermission_delay).timeout
	if phase != Phase.INTERMISSION or not player.is_alive():
		return
	open_shop(r)


func open_shop(completed_round: int) -> void:
	phase = Phase.SHOP
	get_tree().paused = true
	_capture_mouse(false)
	shop.open(completed_round)


func _on_shop_closed() -> void:
	get_tree().paused = false
	_capture_mouse(true)
	player.heal_full()
	_start_round(waves.round_number + 1)


func _on_player_died() -> void:
	phase = Phase.GAME_OVER
	waves.stop()
	await get_tree().create_timer(2.5).timeout
	_capture_mouse(false)
	game_over.open(waves.round_number, kills, headshots, points_earned)


# ------------------------------------------------------------------ pause

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		if phase == Phase.SHOP or phase == Phase.GAME_OVER:
			return
		if get_tree().paused:
			resume()
		else:
			pause()
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.pressed and not get_tree().paused \
			and phase != Phase.GAME_OVER and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		_capture_mouse(true)


func pause() -> void:
	get_tree().paused = true
	_capture_mouse(false)
	pause_menu.open()


func resume() -> void:
	pause_menu.close()
	get_tree().paused = false
	_capture_mouse(true)


func restart() -> void:
	get_tree().paused = false
	get_tree().reload_current_scene()


func quit_to_menu() -> void:
	get_tree().paused = false
	get_tree().change_scene_to_file(MAIN_MENU)


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT and phase == Phase.PLAYING and not get_tree().paused:
		pause()


func _capture_mouse(on: bool) -> void:
	if DisplayServer.get_name() == "headless":
		return
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if on else Input.MOUSE_MODE_VISIBLE
