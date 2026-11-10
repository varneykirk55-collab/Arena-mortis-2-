class_name PlayerPerspective
extends Node
## Camera-only perspective controller. Does not own movement/combat/inventory.
## Bot1 contract: female samurai, skeleton bone RightWeaponSocket.
## TODO(Bot1): body scene integration and non-rest-pose character animation.
## The neutral capsule and head-relative weapon mount are explicit placeholders,
## NOT a Roman body or a claim of final samurai animation integration.
const SHOULDER := Vector3(0.85, 0.2, 2.45)
const SHOULDER_ADS := Vector3(0.6, 0.12, 1.5)
var player: Player
var body: Node3D
var weapon_mount: Node3D
var placeholder_body := false
var has_weapon_socket := false
var body_anim: AnimationPlayer
var _recoil_t := 0.0
var _fired_hooked := false

func setup(p: Player, scene: PackedScene) -> void:
	player = p
	body = player.get_node_or_null("ThirdPersonBody") as Node3D
	if body == null:
		body = scene.instantiate() as Node3D if scene else MeshInstance3D.new()
		body.name = "ThirdPersonBody"
		player.add_child(body)
		if scene == null:
			placeholder_body = true
			var capsule := CapsuleMesh.new()
			capsule.radius = 0.3
			capsule.height = 1.75
			(body as MeshInstance3D).mesh = capsule
			body.position.y = 0.9
			var mat := StandardMaterial3D.new()
			mat.albedo_color = Color(0.28, 0.32, 0.36)
			(body as MeshInstance3D).material_override = mat
	_disable_visual_collisions(body)
	# Samurai asset contract (PLAYER_SAMURAI_HANDS.md): node_0 is the complete
	# 23,583-tri TP body (including arms/sleeves/hands); FP_Arms is a 4,600-tri
	# forearm/hand duplicate for FP only and must be hidden in TP to prevent z-fighting.
	var fp_arms := body.find_child("FP_Arms", true, false) as Node3D
	if fp_arms:
		fp_arms.visible = false
	var tp_body_mesh := body.find_child("node_0", true, false) as Node3D
	if tp_body_mesh:
		tp_body_mesh.visible = true
	body_anim = body.find_child("AnimationPlayer", true, false) as AnimationPlayer
	body.visible = false
	weapon_mount = Node3D.new()
	var socket: Node3D
	# Bot1 confirmed this is a SKELETON BONE, not a free marker node.
	# Do not edit the skeleton or assume RightHand transforms; attach through
	# Godot's BoneAttachment3D to follow the authored socket bone.
	var skeletons := body.find_children("*", "Skeleton3D", true, false)
	if body is Skeleton3D:
		skeletons.append(body)
	for node in skeletons:
		var skeleton := node as Skeleton3D
		if skeleton.find_bone("RightWeaponSocket") >= 0:
			var attachment := BoneAttachment3D.new()
			attachment.name = "RightWeaponSocketAttachment"
			attachment.bone_name = "RightWeaponSocket"
			skeleton.add_child(attachment)
			socket = attachment
			break
	if socket == null:
		# Retain compatibility with an explicitly supplied scene-level marker.
		socket = body.find_child("RightWeaponSocket", true, false) as Node3D
	has_weapon_socket = socket != null
	if socket:
		weapon_mount.name = "WeaponPresentation"
		socket.add_child(weapon_mount)
		# Bot1's RightWeaponSocket pose leaves weapon -Z forward but rolled 180
		# degrees (weapon +Y points down). Kirk approved a code-side correction:
		# roll the presentation mount 180 degrees about the barrel (-Z) axis.
		weapon_mount.transform = Transform3D(Basis(Vector3.FORWARD, PI), Vector3.ZERO)
	else:
		weapon_mount.name = "RightWeaponSocket_PLACEHOLDER"
		player.head.add_child(weapon_mount)
		weapon_mount.position = Vector3(0.18, -0.25, -0.1)

func update_camera(delta: float) -> void:
	var camera := player.camera
	var anchor := player.head.global_position
	var offset := Vector3.ZERO
	if player.third_person:
		offset = SHOULDER.lerp(SHOULDER_ADS, player.weapons.ads_amount)
	var desired := player.head.to_global(offset)
	var candidate := camera.global_position.lerp(desired, 1.0 - exp(-12.0 * delta))
	# A sphere sweep prevents near-plane corners clipping, including during
	# shoulder transitions. Collision always snaps inward; outward motion smooths.
	var query := PhysicsShapeQueryParameters3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.22
	query.shape = sphere
	query.collision_mask = Layers.WORLD
	query.exclude = [player.get_rid()]
	query.transform = Transform3D(Basis.IDENTITY, anchor)
	query.motion = candidate - anchor
	var fractions := player.get_world_3d().direct_space_state.cast_motion(query)
	var fraction := maxf(0.0, fractions[0] - 0.015) if fractions[0] < 1.0 else 1.0
	var safe := anchor + query.motion * fraction
	camera.global_position = safe
	camera.near = 0.08 if player.third_person else 0.03
	# Fade-out surrogate: hide when collision pulls the camera inside the body.
	# Body has no physics, and cannot intercept bullets or the reticle.
	body.visible = player.third_person and camera.global_position.distance_to(anchor) > 0.8

	if player.third_person:
		var weapon := player.weapons.current_viewmodel()
		if weapon:
			weapon.visible = body.visible
	update_body_animation(delta)


## Bot1 clip sets: base clips are posed for the M4/rifles; `_Pistol` and
## `_Jupiter` variants place the left hand on that weapon's support grip.
func clip_suffix() -> String:
	var w = player.weapons.current() if player.weapons else null
	if w == null:
		return ""
	match String(w.data.id):
		"pistol":
			return "_Pistol"
		"jupiter":
			return "_Jupiter"
	return ""


func body_clip(base: String) -> String:
	if body_anim == null:
		return ""
	var variant := base + clip_suffix()
	return variant if body_anim.has_animation(variant) else base


func update_body_animation(delta: float) -> void:
	if body_anim == null or not player.third_person:
		return
	if not _fired_hooked and player.weapons:
		player.weapons.fired.connect(_on_weapon_fired)
		_fired_hooked = true
	_recoil_t = maxf(_recoil_t - delta, 0.0)
	var base := "AimIdle"
	var speed := player.horizontal_speed()
	if _recoil_t > 0.0:
		base = "FireRecoil"
	elif speed > 4.5 and not player.weapons.is_aiming():
		base = "Run"
	elif speed > 0.5:
		base = "Walk"
	var clip := body_clip(base)
	if clip == "" or not body_anim.has_animation(clip):
		return
	if body_anim.current_animation != clip:
		body_anim.play(clip, 0.0 if base == "FireRecoil" else 0.15)


func _disable_visual_collisions(node: Node) -> void:
	# Body is presentation only. Keep the existing CharacterBody3D collider,
	# never let imported model colliders intercept reticle rays/camera sweeps.
	if node is CollisionObject3D:
		node.collision_layer = 0
		node.collision_mask = 0
	for child in node.get_children():
		_disable_visual_collisions(child)


func _on_weapon_fired(_w) -> void:
	_recoil_t = 0.24
	if body_anim and player.third_person and body_anim.current_animation.begins_with("FireRecoil"):
		body_anim.seek(0.0, true)
