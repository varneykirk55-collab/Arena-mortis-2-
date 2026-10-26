extends Node
## Global player settings (autoload "Settings").
## Owns: input action registration, mouse sensitivity, audio volumes, persistence.

signal changed

const SAVE_PATH := "user://settings.cfg"

var mouse_sensitivity: float = 1.0      ## multiplier; 1.0 == 0.12 degrees per pixel
var invert_y: bool = false
var field_of_view: float = 80.0
var master_volume: float = 0.8
var sfx_volume: float = 1.0
var ambient_volume: float = 0.8
var fullscreen: bool = false


func _enter_tree() -> void:
	InputSetup.register_actions()
	load_settings()
	apply_audio()


func _ready() -> void:
	apply_video()


func apply_video() -> void:
	if DisplayServer.get_name() == "headless":
		return
	var mode := DisplayServer.WINDOW_MODE_FULLSCREEN if fullscreen else DisplayServer.WINDOW_MODE_WINDOWED
	if DisplayServer.window_get_mode() != mode:
		DisplayServer.window_set_mode(mode)


func load_settings() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATH) != OK:
		return
	mouse_sensitivity = cfg.get_value("input", "mouse_sensitivity", mouse_sensitivity)
	invert_y = cfg.get_value("input", "invert_y", invert_y)
	field_of_view = cfg.get_value("video", "fov", field_of_view)
	master_volume = cfg.get_value("audio", "master", master_volume)
	sfx_volume = cfg.get_value("audio", "sfx", sfx_volume)
	ambient_volume = cfg.get_value("audio", "ambient", ambient_volume)
	fullscreen = cfg.get_value("video", "fullscreen", fullscreen)


func save_settings() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("input", "mouse_sensitivity", mouse_sensitivity)
	cfg.set_value("input", "invert_y", invert_y)
	cfg.set_value("video", "fov", field_of_view)
	cfg.set_value("audio", "master", master_volume)
	cfg.set_value("audio", "sfx", sfx_volume)
	cfg.set_value("audio", "ambient", ambient_volume)
	cfg.set_value("video", "fullscreen", fullscreen)
	cfg.save(SAVE_PATH)


func set_value(key: String, value: Variant) -> void:
	set(key, value)
	apply_audio()
	if key == "fullscreen":
		apply_video()
	save_settings()
	changed.emit()


func apply_audio() -> void:
	_set_bus("Master", master_volume)
	_set_bus("SFX", sfx_volume)
	_set_bus("Ambient", ambient_volume)


func _set_bus(bus_name: String, linear: float) -> void:
	var idx := AudioServer.get_bus_index(bus_name)
	if idx >= 0:
		AudioServer.set_bus_volume_db(idx, linear_to_db(max(linear, 0.0001)))
		AudioServer.set_bus_mute(idx, linear <= 0.001)
