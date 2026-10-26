class_name WaveManager
extends Node
## Runs rounds: schedules zombie spawns with pacing and an active cap, tracks
## the living, and reports when a round is cleared.

signal round_started(round_number: int, total: int)
signal round_completed(round_number: int)
signal remaining_changed(remaining: int)
signal zombie_spawned(zombie: Zombie)
signal zombie_killed(zombie: Zombie, info: Dictionary)

@export var config: WaveConfig
@export var zombie_scene: PackedScene
@export var container_path: NodePath
@export var spawn_group := &"zombie_spawn"

var round_number := 0
var to_spawn := 0          ## scheduled but not yet spawned this round
var alive: Array[Zombie] = []
var running := false
var _timer := 0.0
var _rng := RandomNumberGenerator.new()
var _container: Node


func _ready() -> void:
	_container = get_node_or_null(container_path)
	if _container == null:
		_container = self


func remaining() -> int:
	return to_spawn + alive.size()


func start_round(r: int) -> void:
	round_number = r
	to_spawn = config.zombies_for_round(r)
	running = true
	_timer = config.first_spawn_delay
	round_started.emit(r, to_spawn)
	remaining_changed.emit(remaining())


func stop() -> void:
	running = false


## Removes every zombie immediately (used by tests and restarts).
func clear_all() -> void:
	for z in alive:
		if is_instance_valid(z):
			z.queue_free()
	alive.clear()
	to_spawn = 0
	running = false


func _process(delta: float) -> void:
	if not running:
		return
	if to_spawn > 0:
		_timer -= delta
		if _timer <= 0.0 and alive.size() < config.max_active:
			if spawn_one() != null:
				_timer = config.spawn_interval(round_number) * _rng.randf_range(0.7, 1.3)
			else:
				_timer = 0.5


func spawn_one() -> Zombie:
	var point := _pick_spawn_point()
	if point == null:
		return null
	var z: Zombie = zombie_scene.instantiate()
	var spd: Array = config.roll_speed(round_number, _rng)
	z.configure(config.health_for_round(round_number), spd[0], config.damage, spd[1])
	_container.add_child(z)
	z.global_position = point.global_position + Vector3(_rng.randf_range(-0.6, 0.6), 0.05, _rng.randf_range(-0.6, 0.6))
	z.rotation.y = point.global_rotation.y
	z.died.connect(_on_zombie_died)
	alive.append(z)
	to_spawn -= 1
	zombie_spawned.emit(z)
	return z


func _pick_spawn_point() -> Node3D:
	var points := get_tree().get_nodes_in_group(spawn_group)
	if points.is_empty():
		return null
	var player := get_tree().get_first_node_in_group("player") as Node3D
	var weights: Array[float] = []
	var total := 0.0
	for p in points:
		var w := 1.0
		if player:
			var d: float = (p as Node3D).global_position.distance_to(player.global_position)
			w = 0.05 if d < config.min_spawn_distance else 1.0 / (1.0 + d / 18.0)
		weights.append(w)
		total += w
	var r := _rng.randf() * total
	for i in points.size():
		r -= weights[i]
		if r <= 0.0:
			return points[i]
	return points.back()


func _on_zombie_died(z: Zombie, info: Dictionary) -> void:
	alive.erase(z)
	zombie_killed.emit(z, info)
	remaining_changed.emit(remaining())
	if running and to_spawn == 0 and alive.is_empty():
		running = false
		round_completed.emit(round_number)
