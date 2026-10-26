class_name PointsWallet
extends Node
## The player's points balance. Every transaction goes through try_spend()
## so balance checks cannot be skipped.

signal points_changed(points: int, delta: int)
signal purchase_failed(cost: int)

@export var config: EconomyConfig

var points := 0


func _ready() -> void:
	reset()


func reset() -> void:
	points = config.starting_points if config else 0
	points_changed.emit(points, 0)


func add(amount: int) -> void:
	if amount <= 0:
		return
	points += amount
	points_changed.emit(points, amount)


func can_afford(cost: int) -> bool:
	return cost >= 0 and points >= cost


## Deducts `cost` if affordable. Returns true on success.
func try_spend(cost: int) -> bool:
	if not can_afford(cost):
		purchase_failed.emit(cost)
		return false
	points -= cost
	points_changed.emit(points, -cost)
	return true


## Refund helper for transactions that could not be completed after paying.
func refund(cost: int) -> void:
	add(cost)
