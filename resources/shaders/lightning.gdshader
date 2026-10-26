shader_type spatial;
// Bright additive lightning ribbon (Jupiter bolt).
render_mode blend_add, unshaded, cull_disabled, depth_draw_never, shadows_disabled;

uniform vec4 color : source_color = vec4(0.55, 0.8, 1.0, 1.0);
uniform float energy = 4.0;
uniform float fade = 1.0;

void fragment() {
	// UV.y runs across the ribbon: bright core, soft edges
	float d = abs(UV.y - 0.5) * 2.0;
	float core = smoothstep(0.35, 0.0, d);
	float glow = smoothstep(1.0, 0.0, d) * 0.35;
	ALBEDO = (color.rgb * glow + vec3(1.0) * core) * energy * fade;
}
