class_name ShopItem
extends Resource
## One purchasable between-round upgrade. Effects are applied by ShopMenu via `effect`.

enum Effect { MAX_HEALTH, AMMO_REFILL, DAMAGE }

@export var id: StringName
@export var display_name := ""
@export_multiline var description := ""
@export var effect: Effect = Effect.MAX_HEALTH
@export var base_cost := 1000
@export var cost_step := 0            ## added to the price after each purchase
@export var max_purchases := 0        ## 0 = unlimited
@export var effect_value := 0.0       ## e.g. +25 health, +0.15 damage multiplier


func cost_for(times_bought: int) -> int:
	return base_cost + cost_step * times_bought


func is_maxed(times_bought: int) -> bool:
	return max_purchases > 0 and times_bought >= max_purchases
