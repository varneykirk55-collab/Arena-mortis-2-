# MK35_ISR_BO7 — v3 refinement report

**MK35 ISR (BO7-style, tan/black).** Refinement of v2, not a rebuild: silhouette, proportions, colours and design kept. No scopes/attachments added. Not integrated into Arena Mortis.

## What changed (v2 → v3)

**Geometry** (only first-person-visible detail, no extra subdivision):
- Bolt carrier group added on its own axis, visible through the port with the dust cover open
- Dust cover 0.1 mm off its recess; bolt-release lever seated on the boss face (was buried); one zero-area sliver removed
- Handguard moved 0.5 mm ahead of the upper face (was 2 mm inside it); side panels seated on the wall surface (were 1.2 mm inside)
- Magwell bore clears the magazine top; lower notched under the handguard; full pin rods through the trigger slot
- Magazine side ribs start below the magwell lip; body/floorplate seam groove
- Castle nut + end plate moved behind the lower's tower (were buried) and bored for the buffer tube; stock tube bore + lever slot
- MBUS-style folding sights split into rail-clamp base + leaf on a hinge pin

**PBR:** Tan FDE Cerakote upper/handguard/rails/charging handle (dielectric ceramic coat), black anodized lower and sights, black-nitride steel internals and muzzle brake, matte black polymer panels/stock, stippled grip, rubber butt pad.
- Macro + micro roughness variation, subtle curvature edge highlight baked into BaseColor, bump detail (stipple/knurl/weave/rubber) baked into the normal map.
- AO baked (25 mm contact/crevice AO) into ORM R. No weathering.

## Files

| File | Notes |
|---|---|
| `MK35_ISR_BO7.blend` | editable, transforms applied, real metric scale, descriptive part names, procedural materials (source: `scripts/build_*.py` + `scripts/wlib.py`) |
| `MK35_ISR_BO7.glb` | 48,014 tris, 33 meshes, 3× 4096² PNGs embedded (34.8 MB) (in the chat delivery this is shipped as `full_gltf/MK35_ISR_BO7.gltf` + `.bin` + `textures/` to stay under 25 MB per file; identical content) |
| `MK35_ISR_BO7_LOD1.glb` | gameplay LOD, 18,322 tris, 3× 2048² PNGs embedded (10.0 MB) |
| `textures/MK35_ISR_BO7/` | `MK35_ISR_BO7_BaseColor.png` (sRGB), `_ORM.png` (R=AO, G=rough, B=metal), `_Normal.png` (tangent, OpenGL/+Y) at 4096, `_LOD1_*` at 2048 |

## Stats

- Tris: v2 43,504 (30 parts) → v3 48,014 (33 parts); LOD1 18,322.
- Single material `M_MK35_ISR_BO7_baked`, one shared UV atlas, uniform texel density ≈3.65 px/mm at 4K. UV coverage 52% (polygon area) / 50.6% (baked texels).

## Hierarchy, pivots, animation

`MK35_ISR_BO7` (root empty) → `receiver_lower` → all other parts. Each moving part is a separate object whose origin is its real pivot; motion ranges are stored as custom property `anim` (exported as glTF node extras, 14 nodes).

| Node | World pivot (Blender X fwd, Y left, Z up; m) |
|---|---|
| bolt_catch | (0.0080, 0.0118, 0.0200) |
| stock | (-0.1060, 0.0000, 0.0600) |
| mag_release | (0.0360, -0.0147, 0.0000) |
| magazine | (0.0829, 0.0000, -0.0560) |
| receiver_upper | (0.1120, 0.0000, 0.0140) |
| bolt_carrier | (-0.0760, 0.0000, 0.0660) |
| bolt_release_lever | (0.0100, 0.0186, 0.0660) |
| charging_handle | (-0.0980, 0.0000, 0.0940) |
| dust_cover | (0.0010, -0.0115, 0.0560) |
| forward_assist | (-0.0740, -0.0180, 0.0740) |
| sight_front_leaf | (0.3915, 0.0000, 0.1145) |
| sight_rear_leaf | (0.0135, 0.0000, 0.1145) |
| selector | (-0.0400, 0.0000, 0.0110) |
| trigger | (0.0060, 0.0000, 0.0060) |

Animated: bolt_carrier, bolt_catch, bolt_release_lever, charging_handle, dust_cover, forward_assist, mag_release, magazine, receiver_upper, selector, sight_front_leaf, sight_rear_leaf, stock, trigger.

**Motion metadata (`anim` extras, verbatim from the GLB):**

- `bolt_carrier`: `{"anim": "translate", "axis": "X", "range_m": [0.0, -0.075]}`
- `bolt_catch`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, -8]}`
- `bolt_release_lever`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, 6]}`
- `charging_handle`: `{"anim": "translate", "axis": "X", "range_m": [0.0, -0.06]}`
- `dust_cover`: `{"anim": "rotate", "axis": "X", "range_deg": [0, 110]}`
- `forward_assist`: `{"anim": "translate", "axis": "X", "range_m": [0.0, 0.003]}`
- `mag_release`: `{"anim": "translate", "axis": "Y", "range_m": [0.0, 0.0025]}`
- `magazine`: `{"anim": "translate", "axis": "mag_axis", "dir": [0.0, 0.0, -1.0], "range_m": [0.0, 0.22]}`
- `receiver_upper`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, -25], "note": "takedown"}`
- `selector`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, 90]}`
- `sight_front_leaf`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, -90], "note": "0 = deployed"}`
- `sight_rear_leaf`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, 90], "note": "0 = deployed"}`
- `stock`: `{"anim": "translate", "axis": "X", "range_m": [0.0, -0.08], "positions": 6}`
- `trigger`: `{"anim": "rotate", "axis": "Y", "range_deg": [0, 12]}`

## Verification (all actually run)

- Blender 4.2.3 re-import of both GLBs (`scripts/verify_glb.py`): index tris == re-imported tris, 1 root, no non-unit scales, UVs present, baked material has baseColor + metallicRoughness + normal + occlusion textures, anim extras present.
- Godot 4.7.2 headless `--import` (temp project `godot_test/`, exit 0) + `check.gd`: GODOT_OK for full and LOD1 (mesh/tri counts match, StandardMaterial3D with albedo/roughness/metallic/normal/AO textures, hierarchy + pivots as above). GLTF_SEPARATE delivery copy also imported: GODOT_OK, 48,014 tris.
- Contact check (`scripts/check_contacts.py`): no floating parts; remaining intersections are intentional seated/hidden joints (barrel into receiver, gas block, muzzle threads, buffer threads, grip top, trigger-guard ears, pins, floorplate) or flush coplanar contacts.
- Bake bug found and fixed in v3b: per-object bake margins were overwriting neighbouring parts' islands (dark stripes on chamfers). Fixed by baking with margin 0 and dilating once over the combined atlas. After fix, procedural vs GLB base-colour render differs by <0.3/255 on average, 0% pixels >40/255; `renders/glb_check/MK35_ISR_BO7_fps.png` is clean.

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

- `comparisons/MK35_ISR_BO7_before_after_grid.png`
- `comparisons/MK35_ISR_BO7_{left,right,front34,fps}_before_after.png` (v2_before vs v3)
- `renders/v3/`, `renders/v2_before/`, `renders/glb_check/MK35_ISR_BO7_fps.png`
