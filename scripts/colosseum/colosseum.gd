class_name Colosseum
extends Node3D
## The arena. Static architecture comes from generated GLBs placed in the
## scene; this script dresses it from resources/colosseum_layout.json
## (torches, braziers, statues, banners, debris, mist), creates gameplay
## markers (zombie spawns, Mystery Box, Pack-a-Punch, player spawn), sets up
## the dusk environment and bakes navigation.

const LAYOUT_PATH := "res://resources/colosseum_layout.json"

@export var spawn_gameplay := true        ## markers + interactables (off in the menu backdrop)
@export var build_navigation := true
@export var lights_quality := 1           ## 0 low, 1 normal

@export_group("Scenes")
@export var torch_scene: PackedScene
@export var brazier_scene: PackedScene
@export var tripod_scene: PackedScene
@export var banner_scene: PackedScene
@export var statue_scenes: Array[PackedScene] = []
@export var debris_scene: PackedScene
## Modular architecture (visual overhaul). One mesh per module, reused per bay.
@export var podium_modules_scene: PackedScene
@export var mystery_box_scene: PackedScene
@export var pack_a_punch_scene: PackedScene
@export var fire_crackle: AudioStream

var layout: Dictionary = {}
var A := 30.0
var B := 20.0
var _rng := RandomNumberGenerator.new()

@onready var nav_region: NavigationRegion3D = $NavigationRegion3D
@onready var props: Node3D = $Props
@onready var markers: Node3D = $Markers


func _ready() -> void:
	_rng.seed = 4242
	layout = _load_layout()
	A = layout.get("A", 30.0)
	B = layout.get("B", 20.0)
	_shadow_setup()
	_place_modules()
	_place_lighting_props()
	_place_statues()
	_place_banners()
	_place_debris()
	_add_mist()
	if spawn_gameplay:
		_place_gameplay()
	if build_navigation:
		bake_navigation()


func _load_layout() -> Dictionary:
	var f := FileAccess.open(LAYOUT_PATH, FileAccess.READ)
	if f == null:
		push_error("Colosseum layout missing: %s" % LAYOUT_PATH)
		return {}
	var d = JSON.parse_string(f.get_as_text())
	return d if d is Dictionary else {}


static func basis_from(rows: Array) -> Basis:
	# layout stores the three basis columns (x, y, z)
	return Basis(Vector3(rows[0][0], rows[0][1], rows[0][2]), Vector3(rows[1][0], rows[1][1], rows[1][2]),
			Vector3(rows[2][0], rows[2][1], rows[2][2]))


static func v3(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])


## Point on the offset ellipse (d metres outside the arena edge) at angle t.
func ellipse_point(d: float, t: float, y := 0.0) -> Vector3:
	return Vector3((A + d) * cos(t), y, (B + d) * sin(t))


func inward_basis(d: float, t: float) -> Basis:
	var n := Vector3((B + d) * cos(t), 0, (A + d) * sin(t)).normalized()
	var z := -n
	var x := Vector3.UP.cross(z).normalized()
	return Basis(x, Vector3.UP, z)


func _add(scene: PackedScene, xf: Transform3D, parent: Node = null) -> Node3D:
	if scene == null:
		return null
	var n: Node3D = scene.instantiate()
	(parent if parent else props).add_child(n)
	n.global_transform = xf
	return n


func _add_fire(host: Node3D, size: float, energy: float, rng_: float, shadows: bool) -> void:
	var fp := host.find_child("FirePoint", true, false) as Node3D
	var fire := FireFX.new()
	fire.size = size
	fire.light_energy = energy
	fire.light_range = rng_
	fire.cast_shadows = shadows and lights_quality > 0
	fire.crackle = fire_crackle
	(fp if fp else host).add_child(fire)


# ------------------------------------------------------------------ dressing

func _shadow_setup() -> void:
	# one-sided architecture must cast shadows from both faces
	for n in find_children("*", "GeometryInstance3D", true, false):
		(n as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_DOUBLE_SIDED


func _place_lighting_props() -> void:
	# torches beside every gate
	for t in layout.get("torches", []):
		var xf := Transform3D(basis_from(t.basis), v3(t.pos))
		var torch := _add(torch_scene, xf)
		if torch:
			_add_fire(torch, 0.45, 2.5, 11.0, false)
	# tall braziers in front of the panel bays (not where the machines go)
	var panels: Array = layout.get("panels", [])
	var reserved := _machine_panels()
	var i := 0
	for p in panels:
		if reserved.has(int(p.bay)):
			continue
		i += 1
		if i % 2 == 0:
			continue
		var pos := v3(p.pos)
		pos -= Vector3(pos.x, 0, pos.z).normalized() * 0.4
		var b := _add(brazier_scene, Transform3D(Basis.IDENTITY, pos), nav_region)
		if b:
			_add_fire(b, 1.0, 3.8, 18.0, i % 4 == 1)
	# small tripods along the podium terrace
	var n_tri := 16
	for k in n_tri:
		var t := TAU * (k + 0.5) / n_tri
		var tri := _add(tripod_scene, Transform3D(Basis.IDENTITY, ellipse_point(2.2, t, layout.get("podium_h", 5.0))))
		if tri:
			_add_fire(tri, 0.55, 2.2, 12.0, false)


func _machine_panels() -> Dictionary:
	## Mystery Box on the panel bay furthest north (min z), Pack-a-Punch furthest south.
	var panels: Array = layout.get("panels", [])
	if panels.is_empty():
		return {}
	var north = panels[0]
	var south = panels[0]
	for p in panels:
		if p.pos[2] < north.pos[2]:
			north = p
		if p.pos[2] > south.pos[2]:
			south = p
	return {int(north.bay): north, int(south.bay): south}


## Instantiates the modular podium bays listed in the layout. Each module mesh
## is shared by every bay that uses it (mesh reuse; per-instance culling/LOD).
func _place_modules() -> void:
	if podium_modules_scene == null or not layout.has("podium_modules"):
		return
	var lib: Node = podium_modules_scene.instantiate()
	var meshes := {}
	for mi in lib.find_children("*", "MeshInstance3D", true, false):
		meshes[String(mi.name)] = (mi as MeshInstance3D).mesh
	lib.free()
	var root := Node3D.new()
	root.name = "Architecture"
	add_child(root)
	for e in layout.get("podium_modules", []):
		var mesh: Mesh = meshes.get(String(e.module))
		if mesh == null:
			continue
		var mi := MeshInstance3D.new()
		mi.name = "Bay%02d_%s" % [int(e.bay), e.module]
		mi.mesh = mesh
		var b := basis_from(e.basis)
		if e.get("mirror", false):
			b = b * Basis.from_scale(Vector3(-1, 1, 1))
		root.add_child(mi)
		mi.global_transform = Transform3D(b, v3(e.pos))
	var col_mesh: Mesh = meshes.get("Column")
	if col_mesh:
		var k := 0
		for c in layout.get("podium_columns", []):
			var mi := MeshInstance3D.new()
			mi.name = "Column%02d" % k
			mi.mesh = col_mesh
			root.add_child(mi)
			mi.global_transform = Transform3D(basis_from(c.basis), v3(c.pos))
			k += 1


func _place_statues() -> void:
	var k := 0
	for n in layout.get("niches", []):
		if statue_scenes.is_empty():
			break
		var xf := Transform3D(basis_from(n.basis), v3(n.pos))
		_add(statue_scenes[k % statue_scenes.size()], xf)
		k += 1


func _place_banners() -> void:
	for b in layout.get("banners_low", []):
		var xf := Transform3D(basis_from(b.basis), v3(b.pos))
		_add(banner_scene, xf)
	var k := 0
	for b in layout.get("tier2_bays", []):
		k += 1
		if k % 3 != 0:
			continue
		var xf := Transform3D(basis_from(b.basis).scaled(Vector3(0.8, 0.8, 0.8)), v3(b.pos) + Vector3(0, 0.7, 0))
		_add(banner_scene, xf)
	k = 0
	for b in layout.get("galleryA_bays", []):
		k += 1
		if k % 4 != 0:
			continue
		var xf := Transform3D(basis_from(b.basis).scaled(Vector3(1.3, 1.3, 1.3)), v3(b.pos) + Vector3(0, 1.0, 0))
		_add(banner_scene, xf)


func _place_debris() -> void:
	if debris_scene == null:
		return
	for k in 9:
		var t := _rng.randf() * TAU
		var d := -_rng.randf_range(2.5, 6.0)
		var pos := ellipse_point(d, t, 0.03)
		var near_gate := false
		for g in layout.get("gates", []):
			if pos.distance_to(v3(g.mouth)) < 5.0:
				near_gate = true
		if near_gate:
			continue
		var n: Node3D = debris_scene.instantiate()
		props.add_child(n)
		n.global_position = pos
		n.rotation.y = _rng.randf() * TAU
		# show a random subset of the debris pieces
		for c in n.get_children():
			if c is Node3D and _rng.randf() < 0.35:
				c.visible = false
			elif c is Node3D:
				(c as Node3D).position += Vector3(_rng.randf_range(-1.2, 1.2), 0, _rng.randf_range(-1.2, 1.2))
	# old blood on the sand
	for k in 14:
		var r := sqrt(_rng.randf()) * 0.85
		var t := _rng.randf() * TAU
		var pos := Vector3(A * r * cos(t), 0.0, B * r * sin(t))
		var d := Decal.new()
		d.texture_albedo = ImpactFX.BLOOD_A if k % 2 == 0 else ImpactFX.BLOOD_B
		d.size = Vector3(1, 0.6, 1) * _rng.randf_range(1.5, 3.5)
		d.modulate = Color(0.8, 0.75, 0.75, 0.85)
		d.cull_mask = 1
		props.add_child(d)
		d.position = pos
		d.rotation.y = _rng.randf() * TAU


func _add_mist() -> void:
	var p := GPUParticles3D.new()
	p.name = "GroundMist"
	p.amount = 70
	p.lifetime = 24.0
	p.preprocess = 24.0
	p.visibility_aabb = AABB(Vector3(-40, -2, -30), Vector3(80, 8, 60))
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(A * 0.9, 0.3, B * 0.9)
	pm.direction = Vector3(1, 0, 0.3)
	pm.spread = 40.0
	pm.initial_velocity_min = 0.15
	pm.initial_velocity_max = 0.45
	pm.gravity = Vector3.ZERO
	pm.scale_min = 0.7
	pm.scale_max = 1.3
	var g := Gradient.new()
	g.set_color(0, Color(0.6, 0.58, 0.62, 0.0))
	g.set_color(1, Color(0.6, 0.58, 0.62, 0.0))
	g.add_point(0.3, Color(0.6, 0.58, 0.62, 0.16))
	g.add_point(0.7, Color(0.6, 0.58, 0.62, 0.16))
	var gt := GradientTexture1D.new()
	gt.gradient = g
	pm.color_ramp = gt
	p.process_material = pm
	var q := QuadMesh.new()
	q.size = Vector2(9, 4)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.vertex_color_use_as_albedo = true
	m.albedo_texture = preload("res://assets/textures/smoke_particle.png")
	m.proximity_fade_enabled = true
	m.proximity_fade_distance = 2.0
	m.distance_fade_mode = BaseMaterial3D.DISTANCE_FADE_PIXEL_ALPHA
	m.distance_fade_min_distance = 1.0
	m.distance_fade_max_distance = 6.0
	q.material = m
	p.draw_pass_1 = q
	p.position = Vector3(0, 0.9, 0)
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(p)
	# steam rising from the hypogeum grates
	for gp in layout.get("grates", []):
		var s := GPUParticles3D.new()
		s.amount = 12
		s.lifetime = 5.0
		s.preprocess = 5.0
		var sm := ParticleProcessMaterial.new()
		sm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
		sm.emission_box_extents = Vector3(1.2, 0.05, 0.8)
		sm.direction = Vector3.UP
		sm.spread = 15.0
		sm.initial_velocity_min = 0.3
		sm.initial_velocity_max = 0.7
		sm.gravity = Vector3(0.1, 0.05, 0)
		sm.scale_min = 1.0
		sm.scale_max = 2.2
		var sg := Gradient.new()
		sg.set_color(0, Color(0.55, 0.55, 0.6, 0.0))
		sg.set_color(1, Color(0.55, 0.55, 0.6, 0.0))
		sg.add_point(0.25, Color(0.55, 0.55, 0.6, 0.22))
		var sgt := GradientTexture1D.new()
		sgt.gradient = sg
		sm.color_ramp = sgt
		s.process_material = sm
		var sq := QuadMesh.new()
		sq.size = Vector2(1.6, 1.6)
		sq.material = m
		s.draw_pass_1 = sq
		s.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(s)
		s.position = v3(gp) + Vector3(0, 0.1, 0)


# ------------------------------------------------------------------ gameplay

func _place_gameplay() -> void:
	var spawns := Node3D.new()
	spawns.name = "ZombieSpawns"
	markers.add_child(spawns)
	for g in layout.get("gates", []):
		var m := Marker3D.new()
		m.name = "Gate%d" % int(g.index)
		spawns.add_child(m)
		m.global_transform = Transform3D(basis_from(g.basis), v3(g.spawn))
		m.add_to_group("zombie_spawn")
	var machines := _machine_panels()
	var north_bay := -1
	var south_bay := -1
	for bay in machines:
		var p = machines[bay]
		if north_bay == -1 or p.pos[2] < machines[north_bay].pos[2]:
			north_bay = bay
		if south_bay == -1 or p.pos[2] > machines[south_bay].pos[2]:
			south_bay = bay
	if north_bay >= 0 and mystery_box_scene:
		var p = machines[north_bay]
		var xf := Transform3D(basis_from(p.basis), v3(p.pos))
		xf.origin -= xf.basis.z * 0.3
		var box := _add(mystery_box_scene, xf, nav_region)
		box.name = "MysteryBox"
	if south_bay >= 0 and pack_a_punch_scene:
		var p = machines[south_bay]
		var xf := Transform3D(basis_from(p.basis), v3(p.pos))
		xf.origin += xf.basis.z * 0.2
		var pap := _add(pack_a_punch_scene, xf, nav_region)
		pap.name = "PackAPunch"
	var ps := Marker3D.new()
	ps.name = "PlayerSpawn"
	markers.add_child(ps)
	ps.global_transform = Transform3D(Basis.IDENTITY, Vector3(0, 0.1, 6.0))


func bake_navigation() -> void:
	var nm := NavigationMesh.new()
	nm.agent_radius = 0.5
	nm.agent_height = 2.0
	nm.agent_max_climb = 0.25
	nm.agent_max_slope = 40.0
	nm.cell_size = 0.25
	nm.cell_height = 0.25
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_STATIC_COLLIDERS
	nm.geometry_collision_mask = Layers.WORLD
	nm.geometry_source_geometry_mode = NavigationMesh.SOURCE_GEOMETRY_ROOT_NODE_CHILDREN
	nm.filter_baking_aabb = AABB(Vector3(-A - 12.0, -1.0, -B - 12.0), Vector3((A + 12.0) * 2.0, 3.0, (B + 12.0) * 2.0))
	nm.region_min_size = 4.0
	nav_region.navigation_mesh = nm
	nav_region.bake_navigation_mesh(false)
