class_name WeaponData
extends Resource
## Data-driven weapon definition. One .tres per weapon in resources/weapons/.
## Runtime state (ammo, upgrade) lives in WeaponInstance.

enum FireMode { SEMI, AUTO }
enum Projectile { HITSCAN, LIGHTNING }

@export var id: StringName
@export var display_name := ""
@export var viewmodel_scene: PackedScene
@export var left_arm := &"LeftArmPistol"   ## node name in viewmodel_arms.glb

@export_group("Ballistics")
@export var projectile: Projectile = Projectile.HITSCAN
@export var fire_mode: FireMode = FireMode.SEMI
@export var damage := 40.0
@export var headshot_multiplier := 2.5
@export var fire_rate := 6.0                 ## shots per second
@export var effective_range := 30.0          ## full damage up to here
@export var max_range := 120.0
@export var min_damage_factor := 0.55        ## damage at max_range
@export var pellets := 1
@export var penetration := 0                 ## extra zombies a bullet passes through

@export_group("Ammunition")
@export var magazine_size := 8
@export var reserve_ammo := 80               ## maximum reserve
@export var reload_time := 1.6
@export var starting_reserve := -1           ## -1 = full reserve

@export_group("Handling")
@export var hip_spread_deg := 2.0
@export var ads_spread_deg := 0.3
@export var move_spread_deg := 2.0
@export var recoil_pitch_deg := 1.6
@export var recoil_yaw_deg := 0.5
@export var recoil_kick := 0.05              ## viewmodel z kick (m)
@export var ads_fov := 55.0
@export var ads_time := 0.18
@export var hip_offset := Vector3(0.17, -0.19, -0.36)
@export var ads_offset := Vector3(0.0, -0.06, -0.24)
@export var equip_time := 0.45
@export var move_speed_multiplier := 1.0

@export_group("Upgrade (Pack-a-Punch)")
@export var upgraded_name := ""
@export var upgrade_damage_multiplier := 2.0
@export var upgrade_magazine_multiplier := 1.5
@export var upgrade_reserve_multiplier := 1.5
@export var upgrade_fire_rate_multiplier := 1.15
@export var upgrade_tint := Color(0.75, 0.25, 1.0)

@export_group("Effects")
@export var fire_sound: AudioStream
@export var upgraded_fire_sound: AudioStream
@export var reload_sound: AudioStream
@export var dry_sound: AudioStream
@export var muzzle_flash_color := Color(1.0, 0.75, 0.4)
@export var muzzle_flash_scale := 1.0
@export var tracer := true
@export var bolt_color := Color(0.55, 0.8, 1.0)  ## lightning colour (Jupiter)

@export_group("Mystery Box")
@export var box_weight := 10.0               ## relative chance in the box pool
