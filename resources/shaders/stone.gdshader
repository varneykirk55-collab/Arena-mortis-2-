shader_type spatial;
// Arena Mortis weathered-surface shader (visual overhaul, phase 1).
// World-space triplanar albedo/normal/roughness, plus:
//   * macro colour variation (breaks up texture tiling across a wall)
//   * per-block tint and baked AO from vertex colours
//   * ground grime that fades with height (wall/floor transition)
//   * vertical rain/soot streaks on walls
//   * sand dust settling on upward-facing ledges
// Works in Forward+ and Compatibility. No screen-space effects.
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rough_tex : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D macro_tex : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform sampler2D streak_tex : hint_default_black, filter_linear_mipmap, repeat_enable;

uniform vec4 albedo_color : source_color = vec4(1.0);
uniform float tex_scale = 0.5;            // texture repeats per metre
uniform float normal_strength = 1.0;
uniform float roughness_min = 0.65;
uniform float roughness_max = 1.0;
uniform float blend_sharpness = 6.0;
uniform bool use_vertex_color = true;

uniform float macro_scale = 0.045;
uniform vec4 macro_tint_a : source_color = vec4(1.04, 1.0, 0.94, 1.0);
uniform vec4 macro_tint_b : source_color = vec4(0.82, 0.80, 0.78, 1.0);
uniform float macro_strength = 0.85;

uniform vec4 dirt_color : source_color = vec4(0.42, 0.36, 0.30, 1.0);
uniform float dirt_height = 1.4;          // metres above dirt_base where grime fades out
uniform float dirt_base = 0.0;
uniform float dirt_strength = 0.6;

uniform float streak_strength = 0.35;
uniform float streak_scale = 0.35;

uniform vec4 dust_color : source_color = vec4(0.62, 0.52, 0.40, 1.0);
uniform float dust_strength = 0.55;

varying vec3 w_pos;
varying vec3 w_nrm;

void vertex() {
	w_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	w_nrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

vec3 unpack_n(vec4 t) {
	// reconstruct z so this works whether or not the texture was imported as RGTC normal map
	vec2 xy = t.xy * 2.0 - 1.0;
	vec3 n = vec3(xy, sqrt(max(1.0 - dot(xy, xy), 0.0)));
	n.xy *= normal_strength;
	return n;
}

void fragment() {
	vec3 N = normalize(w_nrm);
	vec3 w = pow(abs(N), vec3(blend_sharpness));
	w /= (w.x + w.y + w.z + 1e-5);
	vec3 p = w_pos * tex_scale;
	vec2 uvx = p.zy;
	vec2 uvy = p.xz;
	vec2 uvz = p.xy;

	vec3 alb = texture(albedo_tex, uvx).rgb * w.x + texture(albedo_tex, uvy).rgb * w.y + texture(albedo_tex, uvz).rgb * w.z;
	float rgh = texture(rough_tex, uvx).r * w.x + texture(rough_tex, uvy).r * w.y + texture(rough_tex, uvz).r * w.z;

	// triplanar normal mapping (whiteout blend)
	vec3 tx = unpack_n(texture(normal_tex, uvx));
	vec3 ty = unpack_n(texture(normal_tex, uvy));
	vec3 tz = unpack_n(texture(normal_tex, uvz));
	tx = vec3(tx.xy + N.zy, abs(tx.z) * N.x);
	ty = vec3(ty.xy + N.xz, abs(ty.z) * N.y);
	tz = vec3(tz.xy + N.xy, abs(tz.z) * N.z);
	vec3 wn = normalize(tx.zyx * w.x + ty.xzy * w.y + tz.xyz * w.z);

	// macro variation: two scales so repetition across a wall disappears
	vec3 m1 = texture(macro_tex, w_pos.xz * macro_scale + w_pos.y * 0.013).rgb;
	vec3 m2 = texture(macro_tex, (w_pos.zx + vec2(w_pos.y * 0.7)) * macro_scale * 3.1).rgb;
	float mv = clamp(m1.r * 0.65 + m2.g * 0.35, 0.0, 1.0);
	alb *= mix(vec3(1.0), mix(macro_tint_b.rgb, macro_tint_a.rgb, mv), macro_strength);

	if (use_vertex_color) {
		alb *= COLOR.rgb;
	}
	alb *= albedo_color.rgb;

	// vertical streaks on walls (stronger just below ledges -> faked by height noise)
	float wall = 1.0 - abs(N.y);
	float sk = texture(streak_tex, vec2((w_pos.x + w_pos.z) * streak_scale, w_pos.y * 0.04)).r;
	sk *= (0.5 + 0.5 * m1.b);
	alb *= 1.0 - sk * streak_strength * wall;

	// grime near the ground
	float g = 1.0 - smoothstep(dirt_base, dirt_base + dirt_height, w_pos.y + (m2.r - 0.5) * 0.6);
	alb = mix(alb, alb * dirt_color.rgb * 1.6, g * dirt_strength);

	// sand dust on upward-facing surfaces
	float up = smoothstep(0.55, 0.9, wn.y);
	float dn = smoothstep(0.35, 0.75, m1.g + m2.b * 0.3);
	alb = mix(alb, dust_color.rgb * (0.85 + 0.3 * m2.r), up * dn * dust_strength);

	ALBEDO = alb;
	ROUGHNESS = clamp(mix(roughness_min, roughness_max, rgh) + up * dn * 0.08, 0.0, 1.0);
	SPECULAR = 0.35;
	NORMAL = normalize((VIEW_MATRIX * vec4(wn, 0.0)).xyz);
}
