class_name PlayerPerspective
extends Node
## Camera-only perspective controller. Does not own movement/combat/inventory.
## Bot1 contract: female samurai, skeleton bone RightWeaponSocket.
## TODO(Bot1): body scene integration and non-rest-pose character animation.
## The neutral capsule and head-relative weapon mount are explicit placeholders,
## NOT a Roman body or a claim of final samurai animation integration.
const SHOULDER := Vector3(0.65, 0.16, 2.7)
const SHOULDER_ADS := Vector3(0.4, 0.08, 1.5)
var player: Player
var body: Node3D
var weapon_mount: Node3D
var placeholder_body := false
var has_weapon_socket := false

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


func _disable_visual_collisions(node: Node) -> void:
	# Body is presentation only. Keep the existing CharacterBody3D collider,
	# never let imported model colliders intercept reticle rays/camera sweeps.
	if node is CollisionObject3D:
		node.collision_layer = 0
		node.collision_mask = 0
	for child in node.get_children():
		_disable_visual_collisions(child)
