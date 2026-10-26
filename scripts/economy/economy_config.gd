class_name EconomyConfig
extends Resource
## Every cost and reward in the game lives here (resources/economy/economy_config.tres).

@export_group("Rewards")
@export var starting_points := 500
@export var points_per_hit := 10
@export var points_per_kill := 60
@export var points_per_headshot_kill := 100
@export var round_bonus_per_round := 50   ## awarded on round completion: bonus * round

@export_group("Costs")
@export var mystery_box_cost := 950
@export var pack_a_punch_cost := 5000

@export_group("Shop")
@export var shop_items: Array[ShopItem] = []
