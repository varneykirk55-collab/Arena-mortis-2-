shader_type sky;
// Dusk sky over the Colosseum: warm horizon, deep blue zenith, stars, moon.

uniform vec3 zenith : source_color = vec3(0.025, 0.035, 0.085);
uniform vec3 mid_sky : source_color = vec3(0.11, 0.09, 0.17);
uniform vec3 horizon : source_color = vec3(0.62, 0.26, 0.12);
uniform vec3 ground : source_color = vec3(0.04, 0.03, 0.03);
uniform vec3 sunset_dir = vec3(-0.8, 0.0, 0.6);
uniform sampler2D stars : source_color, filter_linear, repeat_enable;
uniform float star_strength = 1.6;
uniform vec3 moon_color : source_color = vec3(0.85, 0.9, 1.0);
uniform float moon_size = 0.03;

void sky() {
	vec3 d = EYEDIR;
	float h = d.y;
	vec3 col;
	if (h >= 0.0) {
		col = mix(horizon, mid_sky, smoothstep(0.0, 0.22, h));
		col = mix(col, zenith, smoothstep(0.18, 0.75, h));
		float s = pow(max(dot(normalize(vec3(d.x, 0.0, d.z)), normalize(sunset_dir)), 0.0), 4.0);
		col += vec3(0.55, 0.2, 0.06) * s * (1.0 - smoothstep(0.0, 0.3, h));
		vec2 uv = vec2(atan(d.x, d.z) / 6.2831853 + 0.5, acos(clamp(d.y, -1.0, 1.0)) / 3.14159265);
		col += texture(stars, uv).rgb * star_strength * smoothstep(0.12, 0.55, h);
	} else {
		col = mix(horizon * 0.35, ground, smoothstep(0.0, -0.15, h));
	}
	if (LIGHT0_ENABLED) {
		float md = dot(d, LIGHT0_DIRECTION);
		float disc = smoothstep(cos(moon_size), cos(moon_size * 0.9), md);
		col += moon_color * disc * 4.0;
		col += moon_color * (pow(max(md, 0.0), 300.0) * 0.5 + pow(max(md, 0.0), 14.0) * 0.07);
	}
	COLOR = col;
}
