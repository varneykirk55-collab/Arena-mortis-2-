"""
Visual overhaul (phase 1) materials: ShaderMaterials using
resources/shaders/stone.gdshader. GLB surfaces with these names are remapped
to these resources at import (tools/import/material_remap.gd).
"""
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "../../resources/materials"
T = "res://assets/textures/"

COMMON = dict(macro="macro_variation", streak="streaks")

MATS = {
    # modelled ashlar blocks (per-block tint comes from vertex colours)
    "lime_block": dict(tex="limestone", scale=0.42, nstr=1.1, rmin=0.62, rmax=1.0, dirt=0.55, streak=0.35, dust=0.5),
    "lime_block_warm": dict(tex="limestone_warm", scale=0.42, nstr=1.1, rmin=0.62, rmax=1.0, dirt=0.55, streak=0.35, dust=0.5),
    # finer architectural trim: columns, cornices, voussoirs, plinths
    "lime_trim": dict(tex="limestone", scale=0.8, nstr=0.9, rmin=0.55, rmax=0.95, dirt=0.45, streak=0.25, dust=0.6,
                      tint=(1.05, 1.03, 1.0)),
    "marble_v2": dict(tex="marble", scale=0.6, nstr=0.6, rmin=0.35, rmax=0.75, dirt=0.5, streak=0.3, dust=0.45,
                      tint=(0.74, 0.71, 0.67)),
    "mortar_v2": dict(tex="mortar", scale=1.4, nstr=1.0, rmin=0.85, rmax=1.0, dirt=0.3, streak=0.1, dust=0.3,
                      tint=(0.8, 0.78, 0.76)),
    "rubble_core": dict(tex="mortar", scale=0.9, nstr=1.4, rmin=0.85, rmax=1.0, dirt=0.4, streak=0.2, dust=0.5),
    "paving": dict(tex="limestone", scale=0.6, nstr=1.2, rmin=0.7, rmax=1.0, dirt=0.25, streak=0.0, dust=0.7,
                   tint=(0.86, 0.83, 0.79)),
    "tunnel_stone": dict(tex="limestone", scale=0.42, nstr=1.1, rmin=0.7, rmax=1.0, dirt=0.5, streak=0.2, dust=0.2,
                         tint=(0.62, 0.58, 0.54)),
    # distant tiers: ashlar course texture through the same weathering shader
    "lime_ashlar": dict(tex="stone_blocks", scale=1 / 2.4, nstr=1.0, rmin=0.65, rmax=1.0, dirt=0.35, streak=0.4, dust=0.45,
                        tint=(0.98, 0.95, 0.9)),
    "lime_seat": dict(tex="limestone", scale=0.55, nstr=1.0, rmin=0.6, rmax=0.95, dirt=0.2, streak=0.0, dust=0.55,
                      tint=(0.95, 0.93, 0.9)),
    # legacy material names (props, statues, obstacles, anything not yet rebuilt)
    # now use the same weathering shader so the whole arena reads consistently
    "stone_blocks": dict(tex="stone_blocks", scale=1 / 2.4, nstr=1.0, rmin=0.65, rmax=1.0, dirt=0.5, streak=0.35, dust=0.45),
    "stone_plain": dict(tex="limestone", scale=0.5, nstr=1.0, rmin=0.6, rmax=1.0, dirt=0.45, streak=0.25, dust=0.5),
    "stone_seat": dict(tex="limestone", scale=0.55, nstr=1.0, rmin=0.6, rmax=0.95, dirt=0.2, streak=0.0, dust=0.55,
                       tint=(0.95, 0.93, 0.9)),
    "stone_dark": dict(tex="limestone", scale=0.45, nstr=1.0, rmin=0.75, rmax=1.0, dirt=0.3, streak=0.2, dust=0.1,
                       tint=(0.42, 0.39, 0.36)),
    "marble": dict(tex="marble", scale=0.9, nstr=0.6, rmin=0.35, rmax=0.75, dirt=0.35, streak=0.15, dust=0.35,
                   tint=(0.76, 0.73, 0.69)),
    "sand": dict(tex="sand_v2", scale=0.28, nstr=1.0, rmin=0.8, rmax=1.0, dirt=0.0, streak=0.0, dust=0.0,
                 macro_a=(1.04, 1.0, 0.94), macro_b=(0.68, 0.62, 0.56), macro_strength=1.0),
    "sand_v2": dict(tex="sand_v2", scale=0.28, nstr=1.0, rmin=0.8, rmax=1.0, dirt=0.0, streak=0.0, dust=0.0,
                    macro_a=(1.06, 1.02, 0.96), macro_b=(0.72, 0.66, 0.60), macro_strength=1.0),
}


def write(name, p):
    ext = []

    def tex(path):
        ext.append(path)
        return f'ExtResource("{len(ext) + 1}")'

    lines = [f'resource_name = "{name}"', 'shader = ExtResource("1")']
    lines.append(f'shader_parameter/albedo_tex = {tex(T + p["tex"] + "_albedo.png")}')
    lines.append(f'shader_parameter/normal_tex = {tex(T + p["tex"] + "_normal.png")}')
    lines.append(f'shader_parameter/rough_tex = {tex(T + p["tex"] + "_rough.png")}')
    lines.append(f'shader_parameter/macro_tex = {tex(T + COMMON["macro"] + ".png")}')
    lines.append(f'shader_parameter/streak_tex = {tex(T + COMMON["streak"] + ".png")}')
    t = p.get("tint", (1.0, 1.0, 1.0))
    lines.append(f"shader_parameter/albedo_color = Color({t[0]}, {t[1]}, {t[2]}, 1)")
    lines.append(f"shader_parameter/tex_scale = {p['scale']}")
    lines.append(f"shader_parameter/normal_strength = {p['nstr']}")
    lines.append(f"shader_parameter/roughness_min = {p['rmin']}")
    lines.append(f"shader_parameter/roughness_max = {p['rmax']}")
    lines.append(f"shader_parameter/dirt_strength = {p['dirt']}")
    lines.append(f"shader_parameter/streak_strength = {p['streak']}")
    lines.append(f"shader_parameter/dust_strength = {p['dust']}")
    if "macro_a" in p:
        a, b = p["macro_a"], p["macro_b"]
        lines.append(f"shader_parameter/macro_tint_a = Color({a[0]}, {a[1]}, {a[2]}, 1)")
        lines.append(f"shader_parameter/macro_tint_b = Color({b[0]}, {b[1]}, {b[2]}, 1)")
        lines.append(f"shader_parameter/macro_strength = {p['macro_strength']}")
    head = f'[gd_resource type="ShaderMaterial" load_steps={len(ext) + 2} format=3]\n\n'
    head += '[ext_resource type="Shader" path="res://resources/shaders/stone.gdshader" id="1"]\n'
    for i, e in enumerate(ext):
        head += f'[ext_resource type="Texture2D" path="{e}" id="{i + 2}"]\n'
    with open(os.path.join(OUT, name + ".tres"), "w") as f:
        f.write(head + "\n[resource]\n" + "\n".join(lines) + "\n")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for k, v in MATS.items():
        write(k, v)
    print(len(MATS), "v2 materials")
