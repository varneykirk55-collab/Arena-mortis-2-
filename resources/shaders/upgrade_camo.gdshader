shader_type spatial;
// Pack-a-Punch overlay: animated, additive energy pattern over the weapon.
render_mode blend_add, unshaded, cull_back, depth_draw_never;

uniform vec4 tint : source_color = vec4(0.75, 0.25, 1.0, 1.0);
uniform float strength = 0.55;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}

varying vec3 obj_pos;
void vertex() { obj_pos = VERTEX; }

void fragment() {
	vec2 p = obj_pos.zy * 28.0 + obj_pos.x * 9.0;
	float t = TIME * 0.9;
	float n = noise(p + vec2(t, -t * 0.7)) * 0.6 + noise(p * 2.3 - vec2(t * 1.3, t)) * 0.4;
	float bands = smoothstep(0.55, 0.85, n);
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 2.0);
	ALBEDO = tint.rgb * (bands * strength + fres * 0.35);
}
