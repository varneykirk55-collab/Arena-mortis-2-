# Modern_M4 — v3 refinement report

**Modern M4 (black, no optic).** Refinement of v2, not a rebuild: silhouette, proportions, colours and design kept. No scopes/attachments added. Not integrated into Arena Mortis.

## What changed (v2 → v3)

**Geometry** (only first-person-visible detail, no extra subdivision):
- Bolt-carrier bore + real ejection-port window; bolt carrier group modelled and visible behind the dust cover
- Dust cover lifted 0.1 mm off its recess floor (no z-fighting); hinged on a real pivot
- Barrel-nut lug made flush (no clipping into the upper); QD cups counter-bored into the stock
- Magazine body seam groove above the floorplate; vertical grip + mount moved to sit under the handguard (no clipping)
- MBUS-style folding sights split into rail-clamp base + leaf on a hinge pin
- Lifted blacks (albedo ~0.03-0.065) so nothing reads as pure black; each finish separated by value + roughness + metalness

**PBR:** Predominantly black, parts separated by finish: anodized aluminium receivers/rails, parkerized steel internals, matte & stippled polymer furniture, carbon-fibre handguard, tungsten Cerakote muzzle can, rubber butt pad.
- Macro + micro roughness variation, subtle curvature edge highlight baked into BaseColor, bump detail (stipple/knurl/weave/rubber) baked into the normal map.
- AO baked (25 mm contact/crevice AO) into ORM R. No weathering.

## Files

| File | Notes |
|---|---|
| `Modern_M4.blend` | editable, transforms applied, real metric scale, descriptive part names, procedural materials (source: `scripts/build_*.py` + `scripts/wlib.py`) |
| `Modern_M4.glb` | 40,588 tris, 32 meshes, 3× 4096² PNGs embedded (35.6 MB) (in the chat delivery this is shipped as `full_gltf/Modern_M4.gltf` + `.bin` + `textures/` to stay under 25 MB per file; identical content) |
| `Modern_M4_LOD1.glb` | gameplay LOD, 18,238 tris, 3× 2048² PNGs embedded (10.3 MB) |
| `textures/Modern_M4/` | `Modern_M4_BaseColor.png` (sRGB), `_ORM.png` (R=AO, G=rough, B=metal), `_Normal.png` (tangent, OpenGL/+Y) at 4096, `_LOD1_*` at 2048 |

## Stats

- Tris: v2 35,988 (29 parts) → v3 40,588 (32 parts); LOD1 18,238.
- Single material `M_Modern_M4_baked`, one shared UV atlas, uniform texel density ≈3.65 px/mm at 4K. UV coverage 56% (polygon area) / 55.0% (baked texels).

## Hierarchy, pivots, animation

`Modern_M4` (root empty) → `receiver_lower` → all other parts. Each moving part is a separate object whose origin is its real pivot; motion ranges are stored as custom property `anim` (exported as glTF node extras, 13 nodes).

| Node | World pivot (Blender X fwd, Y left, Z up; m) |
|---|---|
| bolt_catch | (0.0300, 0.0142, 0.0370) |
| stock | (-0.1520, 0.0000, 0.0600) |
| mag_release | (0.0360, -0.0142, 0.0240) |
| magazine | (0.0817, 0.0000, -0.0130) |
| receiver_upper | (0.1120, 0.0000, 0.0420) |
| bolt_carrier | (-0.0940, 0.0000, 0.0635) |
| charging_handle | (-0.1240, 0.0000, 0.0900) |
| dust_cover | (-0.0025, -0.0106, 0.0615) |
| forward_assist | (-0.1135, -0.0112, 0.0750) |
| sight_front_leaf | (0.4215, 0.0000, 0.1085) |
| sight_rear_leaf | (-0.0505, 0.0000, 0.1085) |
| selector | (-0.0360, 0.0000, 0.0360) |
| trigger | (0.0060, 0.0000, 0.0300) |

Animated: bolt_carrier, bolt_catch, charging_handle, dust_cover, forward_assist, mag_release, magazine, receiver_upper, selector, sight_front_leaf, sight_rear_leaf, stock, trigger.

**Motion metadata (`anim` extras, verbatim from the GLB):**

- `bolt_carrier`: `{"anim": "translate", "axis": "X", "range_m": [0.0, -0.075]}`
- `bolt_catch`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, -8]}`
- `charging_handle`: `{"anim": "translate", "axis": "X", "range_m": [0.0, -0.06]}`
- `dust_cover`: `{"anim": "rotate", "axis": "X", "range_deg": [0, 110]}`
- `forward_assist`: `{"anim": "translate", "axis": "X", "range_m": [0.0, 0.003]}`
- `mag_release`: `{"anim": "translate", "axis": "Y", "range_m": [0.0, 0.0025]}`
- `magazine`: `{"anim": "translate", "axis": "mag_axis", "dir": [0.0, 0.0, -1.0], "range_m": [0.0, 0.2]}`
- `receiver_upper`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, -25], "note": "takedown"}`
- `selector`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, 90]}`
- `sight_front_leaf`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, -90], "note": "0 = deployed"}`
- `sight_rear_leaf`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, 90], "note": "0 = deployed"}`
- `stock`: `{"anim": "translate", "axis": "X", "range_m": [0.0, -0.085], "positions": 6}`
- `trigger`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, 12]}`

## Verification (all actually run)

- Blender 4.2.3 re-import of both GLBs (`scripts/verify_glb.py`): index tris == re-imported tris, 1 root, no non-unit scales, UVs present, baked material has baseColor + metallicRoughness + normal + occlusion textures, anim extras present.
- Godot 4.7.2 headless `--import` (temp project `godot_test/`, exit 0) + `check.gd`: GODOT_OK for full and LOD1 (mesh/tri counts match, StandardMaterial3D with albedo/roughness/metallic/normal/AO textures, hierarchy + pivots as above). GLTF_SEPARATE delivery copy also imported: GODOT_OK, 40,588 tris.
- Contact check (`scripts/check_contacts.py`): no floating parts; remaining intersections are intentional seated/hidden joints (barrel into receiver, gas block, muzzle threads, buffer threads, grip top, trigger-guard ears, pins, floorplate) or flush coplanar contacts.
- Bake bug found and fixed in v3b: per-object bake margins were overwriting neighbouring parts' islands (dark stripes on chamfers). Fixed by baking with margin 0 and dilating once over the combined atlas. After fix, procedural vs GLB base-colour render differs by <0.3/255 on average, 0% pixels >40/255; `renders/glb_check/Modern_M4_fps.png` is clean.

## Godot notes

- glTF is Y-up; the muzzle points +X in Godot. Rotate the root −90° about Y to face −Z (Godot forward).
- Import as-is; the ORM texture is wired to AO/roughness/metallic automatically.

## Remaining issues / limits

- UV atlas usage ~51-56% (Blender concave pack with rotation; hidden bores/interiors also take space). Could be raised by re-unwrapping and rebaking; not done (would change the .blend UVs).
- A few UV islands overlap within the same part (same material, mostly hidden faces); negligible visually.
- LOD1 is a single collapse-decimated level (~18k tris); no LOD2/billboard. Small parts (<120 faces) are not decimated.
- Textures are PNG (lossless, large). Convert to Godot VRAM compression on import (default) or to KTX2/WebP if file size matters.
- Not tested inside Arena Mortis (by design).

## Comparisons

- `comparisons/Modern_M4_before_after_grid.png`
- `comparisons/Modern_M4_{left,right,front34,fps}_before_after.png` (v2_before vs v3)
- `renders/v3/`, `renders/v2_before/`, `renders/glb_check/Modern_M4_fps.png`
