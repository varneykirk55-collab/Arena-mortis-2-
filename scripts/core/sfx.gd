class_name Sfx
extends RefCounted
## One-shot audio helpers. Players free themselves when finished.


static func play_3d(context: Node, stream: AudioStream, position: Vector3, volume_db := 0.0,
		pitch_variance := 0.05, bus := &"SFX", max_distance := 60.0) -> AudioStreamPlayer3D:
	if stream == null or context == null or not context.is_inside_tree():
		return null
	var p := AudioStreamPlayer3D.new()
	p.stream = stream
	p.volume_db = volume_db
	p.bus = bus
	p.max_distance = max_distance
	p.unit_size = 6.0
	p.pitch_scale = 1.0 + randf_range(-pitch_variance, pitch_variance)
	p.attenuation_filter_cutoff_hz = 12000.0
	var parent := context.get_tree().current_scene if context.get_tree().current_scene else context.get_tree().root
	parent.add_child(p)
	p.global_position = position
	p.finished.connect(p.queue_free)
	p.play()
	return p


static func play_2d(context: Node, stream: AudioStream, volume_db := 0.0, pitch_variance := 0.0,
		bus := &"SFX") -> AudioStreamPlayer:
	if stream == null or context == null or not context.is_inside_tree():
		return null
	var p := AudioStreamPlayer.new()
	p.stream = stream
	p.volume_db = volume_db
	p.bus = bus
	p.pitch_scale = 1.0 + randf_range(-pitch_variance, pitch_variance)
	p.process_mode = Node.PROCESS_MODE_ALWAYS
	context.get_tree().root.add_child(p)
	p.finished.connect(p.queue_free)
	p.play()
	return p


static func pick(streams: Array) -> AudioStream:
	if streams.is_empty():
		return null
	return streams[randi() % streams.size()]
