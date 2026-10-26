class_name WaveConfig
extends Resource
## Round difficulty curve (resources/waves/wave_config.tres).

@export_group("Count")
@export var base_count := 6
@export var count_linear := 2.4
@export var count_quadratic := 0.15
@export var max_active := 24              ## simultaneous living zombies cap

@export_group("Spawning")
@export var spawn_interval_start := 2.0
@export var spawn_interval_decay := 0.94  ## multiplied per round
@export var spawn_interval_min := 0.45
@export var first_spawn_delay := 2.0
@export var min_spawn_distance := 7.0

@export_group("Health")
@export var health_base := 150.0
@export var health_per_round := 100.0     ## linear until health_linear_rounds
@export var health_linear_rounds := 9
@export var health_growth := 1.1          ## multiplicative after that

@export_group("Speed")
@export var walk_speed_min := 1.1
@export var walk_speed_max := 1.6
@export var jog_speed := 2.4
@export var run_speed_min := 3.6
@export var run_speed_max := 4.3
@export var jog_from_round := 2
@export var run_from_round := 4
@export var run_chance_per_round := 0.12
@export var run_chance_max := 0.85

@export_group("Attack")
@export var damage := 35.0


func zombies_for_round(r: int) -> int:
	var k: float = max(r - 1, 0)
	return int(round(base_count + count_linear * k + count_quadratic * k * k))


func health_for_round(r: int) -> float:
	if r <= health_linear_rounds:
		return health_base + health_per_round * (r - 1)
	var h := health_base + health_per_round * (health_linear_rounds - 1)
	return h * pow(health_growth, r - health_linear_rounds)


func spawn_interval(r: int) -> float:
	return max(spawn_interval_start * pow(spawn_interval_decay, r - 1), spawn_interval_min)


func run_chance(r: int) -> float:
	if r < run_from_round:
		return 0.0
	return min(run_chance_per_round * (r - run_from_round + 1), run_chance_max)


## Returns [speed, is_runner] for a new zombie.
func roll_speed(r: int, rng: RandomNumberGenerator) -> Array:
	if rng.randf() < run_chance(r):
		return [rng.randf_range(run_speed_min, run_speed_max), true]
	if r >= jog_from_round and rng.randf() < 0.35:
		return [jog_speed * rng.randf_range(0.9, 1.1), false]
	return [rng.randf_range(walk_speed_min, walk_speed_max), false]
