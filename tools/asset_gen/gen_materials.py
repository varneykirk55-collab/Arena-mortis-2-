"""
Writes Godot StandardMaterial3D resources (resources/materials/*.tres).
GLB surfaces are matched to these by material name at import time
(see tools/import/material_remap.gd).
"""
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "../../resources/materials"
T = "res://assets/textures/"

# name: dict(props)
MATS = {
    # --- architecture (world triplanar) ---
    "stone_blocks": dict(tex="stone_blocks", tri="world", scale=1 / 2.4, vcol=True, rough_tex=True),
    "stone_plain": dict(tex="stone_plain", tri="world", scale=0.45, vcol=True, rough_tex=True),
    "stone_dark": dict(tex="stone_plain", tri="world", scale=0.45, vcol=True, color=(0.32, 0.29, 0.26), rough_tex=True),
    "stone_seat": dict(tex="stone_plain", tri="world", scale=0.6, vcol=True, color=(0.92, 0.88, 0.82), rough_tex=True),
    "marble": dict(tex="stone_plain", tri="object", scale=0.8, vcol=True, color=(1.05, 1.02, 0.98), roughness=0.55),
    "sand": dict(tex="sand", tri="world", scale=0.25, vcol=True, rough_tex=True, normal_scale=1.2),
    "void": dict(color=(0.015, 0.012, 0.01), roughness=1.0, unshaded=False),
    # --- props / machines ---
    "bronze": dict(tex="bronze", tri="object", scale=1.5, metallic=0.85, rough_tex=True, vcol=True),
    "gold": dict(tex="bronze", tri="object", scale=1.5, metallic=1.0, color=(1.25, 1.05, 0.7), roughness=0.3, vcol=True),
    "iron": dict(tex="iron", tri="object", scale=1.2, metallic=0.6, rough_tex=True, vcol=True),
    "iron_world": dict(tex="iron", tri="world", scale=0.8, metallic=0.6, rough_tex=True, vcol=True),
    "wood_box": dict(tex="wood", tri="object", scale=3.0, rough_tex=True, vcol=True, color=(0.78, 0.66, 0.58)),
    "rope": dict(tex="leather", tri="object", scale=3, color=(1.6, 1.4, 1.0), roughness=0.95),
    "cloth_red": dict(tex="cloth_red", uv=True, scale=1.0, normal="cloth", roughness=0.9, double=True, vcol=True),
    "banner": dict(tex="banner", uv=True, alpha_tex="banner_alpha", roughness=0.9, double=True),
    "leather": dict(tex="leather", tri="object", scale=2.0, roughness=0.75, vcol=True),
    "glow_orange": dict(color=(1.0, 0.55, 0.15), emission=(1.0, 0.45, 0.1), energy=4.0, unshaded=True),
    "glow_ember": dict(color=(0.6, 0.15, 0.02), emission=(1.0, 0.25, 0.04), energy=2.5),
    "glow_question": dict(color=(1.0, 0.75, 0.3), emission=(1.0, 0.62, 0.18), energy=6.0, unshaded=True),
    "glow_blue": dict(color=(0.5, 0.8, 1.0), emission=(0.35, 0.7, 1.0), energy=6.0, unshaded=True),
    "glow_red": dict(color=(1.0, 0.2, 0.1), emission=(1.0, 0.12, 0.05), energy=6.0, unshaded=True),
    "coal": dict(color=(0.22, 0.19, 0.16), roughness=0.95),
    # --- weapons (object triplanar) ---
    "gun_metal": dict(tex="metal", tri="object", scale=4.0, color=(2.6, 2.6, 2.75), metallic=0.45, rough_tex=True, rough_tex_name="metal_rough", normal="metal"),
    "gun_polymer": dict(tex="polymer", tri="object", scale=4.0, color=(3.2, 3.2, 3.4), roughness=0.55, normal="polymer"),
    "gun_wood": dict(tex="wood", tri="object", scale=5.0, rough_tex=True, color=(1.05, 0.9, 0.8)),
    "gun_bronze": dict(tex="bronze", tri="object", scale=4.0, metallic=0.75, color=(1.25, 1.08, 0.82), roughness=0.32),
    "gun_lens": dict(color=(0.35, 0.5, 0.45), roughness=0.05, alpha=0.18),
    "glove": dict(tex="leather", tri="object", scale=6.0, color=(1.1, 0.98, 0.9), roughness=0.6),
    "sleeve": dict(color=(0.32, 0.34, 0.28), normal="cloth", tri="object", scale=6.0, roughness=0.9),
    # --- zombies (mesh UVs; skinned) ---
    "zombie_skin": dict(tex="skin", uv=True, scale=2.0, rough_tex=True, vcol=True, normal_scale=1.1, color=(1.15, 1.18, 1.02), emission=(0.14, 0.15, 0.12), energy=0.35),
    "zombie_cloth": dict(tex="cloth_red", uv=True, scale=2.0, normal="cloth", roughness=0.85, vcol=True, double=True, color=(1.45, 1.25, 1.25), emission=(0.18, 0.04, 0.03), energy=0.3),
    "zombie_leather": dict(tex="leather", uv=True, scale=2.0, roughness=0.65, vcol=True, color=(1.4, 1.3, 1.2), emission=(0.1, 0.07, 0.05), energy=0.25),
    "zombie_metal": dict(tex="bronze", uv=True, scale=2.0, metallic=0.45, rough_tex=True, vcol=True, color=(1.35, 1.22, 1.0), emission=(0.16, 0.13, 0.09), energy=0.3),
    "zombie_iron": dict(tex="iron", uv=True, scale=2.0, metallic=0.4, rough_tex=True, vcol=True, color=(1.5, 1.45, 1.4), emission=(0.12, 0.11, 0.1), energy=0.25),
    "zombie_crest": dict(tex="cloth_red", uv=True, scale=3.0, roughness=0.9, color=(1.6, 1.2, 1.2), emission=(0.25, 0.05, 0.04), energy=0.35),
    "zombie_eye": dict(color=(1.0, 0.85, 0.3), emission=(1.0, 0.7, 0.15), energy=3.5),
    "zombie_mouth": dict(color=(0.18, 0.04, 0.04), roughness=0.4),
    "bone": dict(tex="stone_plain", uv=True, scale=3.0, color=(1.25, 1.18, 1.02), roughness=0.55),
    "zombie_hair": dict(color=(0.12, 0.1, 0.08), roughness=0.85),
}


def write(name, p):
    ext = []

    def tex(path):
        ext.append(path)
        return f'ExtResource("{len(ext)}")'

    lines = [f'resource_name = "{name}"']
    if p.get("vcol"):
        lines.append("vertex_color_use_as_albedo = true")
    col = p.get("color")
    if col:
        lines.append(f"albedo_color = Color({col[0]}, {col[1]}, {col[2]}, 1)")
    if "tex" in p:
        lines.append(f"albedo_texture = {tex(T + p['tex'] + '_albedo.png')}")
    if p.get("alpha_tex"):
        # banner alpha baked separately; use alpha scissor through detail mask is overkill:
        lines.append("transparency = 2")
        lines.append("alpha_scissor_threshold = 0.5")
    if p.get("rough_tex"):
        rn = p.get("rough_tex_name", p["tex"] + "_rough")
        lines.append(f"roughness_texture = {tex(T + rn + '.png')}")
        lines.append("roughness_texture_channel = 4")
        lines.append("roughness = 1.0")
    elif "roughness" in p:
        lines.append(f"roughness = {p['roughness']}")
    if "metallic" in p:
        lines.append(f"metallic = {p['metallic']}")
        lines.append("metallic_specular = 0.5")
    nrm = p.get("normal", p.get("tex"))
    if nrm and os.path.exists(os.path.join(os.path.dirname(OUT), "..", "assets", "textures", nrm + "_normal.png")):
        lines.append("normal_enabled = true")
        lines.append(f"normal_scale = {p.get('normal_scale', 1.0)}")
        lines.append(f"normal_texture = {tex(T + nrm + '_normal.png')}")
    if "emission" in p:
        e = p["emission"]
        lines.append("emission_enabled = true")
        lines.append(f"emission = Color({e[0]}, {e[1]}, {e[2]}, 1)")
        lines.append(f"emission_energy_multiplier = {p.get('energy', 1.0)}")
    if "alpha" in p:
        lines.append("transparency = 1")
        lines[[i for i, l in enumerate(lines) if l.startswith("albedo_color")][0]] = "albedo_color = Color(%s, %s, %s, %s)" % (*p["color"], p["alpha"])
    if p.get("unshaded"):
        lines.append("shading_mode = 0")
    if p.get("double"):
        lines.append("cull_mode = 2")
    tri = p.get("tri")
    s = p.get("scale", 1.0)
    if tri:
        lines.append("uv1_triplanar = true")
        lines.append("uv1_triplanar_sharpness = 4.0")
        if tri == "world":
            lines.append("uv1_world_triplanar = true")
        lines.append(f"uv1_scale = Vector3({s}, {s}, {s})")
    elif p.get("uv") and s != 1.0:
        lines.append(f"uv1_scale = Vector3({s}, {s}, {s})")
    lines.append("texture_filter = 5" if (tri or p.get("uv")) else "texture_filter = 3")

    # alpha texture: combine into albedo alpha at generation? we keep a separate
    # alpha png and pack it into the banner albedo below.
    head = f'[gd_resource type="StandardMaterial3D" load_steps={len(ext) + 1} format=3]\n\n'
    for i, e in enumerate(ext):
        head += f'[ext_resource type="Texture2D" path="{e}" id="{i + 1}"]\n'
    out = head + "\n[resource]\n" + "\n".join(lines) + "\n"
    with open(os.path.join(OUT, name + ".tres"), "w") as f:
        f.write(out)


def pack_banner_alpha():
    from PIL import Image
    tdir = os.path.join(os.path.dirname(OUT), "..", "assets", "textures")
    a = Image.open(os.path.join(tdir, "banner_alpha.png")).convert("L")
    rgb = Image.open(os.path.join(tdir, "banner_albedo.png")).convert("RGB")
    rgba = rgb.copy()
    rgba.putalpha(a)
    rgba.save(os.path.join(tdir, "banner_albedo.png"))
    os.remove(os.path.join(tdir, "banner_alpha.png"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    tdir = os.path.join(os.path.dirname(OUT), "..", "assets", "textures")
    if os.path.exists(os.path.join(tdir, "banner_alpha.png")):
        pack_banner_alpha()
    for k, v in MATS.items():
        write(k, v)
    print(len(MATS), "materials")
