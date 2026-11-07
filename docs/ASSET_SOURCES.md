# Asset sources and licences

## M4 Stage 1 update

The M4 now uses Blender 4.3.2, executed in this cloud environment. Its original
model source is `tools/asset_gen/build_m4_blender.py`, with editable output
`assets/sources/m4_stage1.blend`. The script generates the GLB, M4-only Godot
materials and a seeded microfinish roughness texture. It uses no third-party
models or texture assets. See [the M4 review](m4_stage1/README.md) for actual
Godot comparisons and validation. The historical pipeline below still applies
to the other weapons and arms.

Every model, texture, material and sound in this project is **original** and was
generated for Arena Mortis by the scripts in `tools/asset_gen/`. No assets were
ripped from Call of Duty or any other game, and the reference sheet was used only
as visual direction (it is not included in the project or used as a texture).

## Tooling note: Blender was not available

The specification asks for Blender. The build environment only allowed network
access to GitHub; blender.org, PyPI (`bpy`), Ubuntu apt mirrors and the usual
Blender mirrors were all blocked, so Blender could not be installed. **No asset
was made in Blender, and none of the files claim otherwise.**

The practical alternative used instead:

| Need | What was used |
|---|---|
| Modelling | `tools/asset_gen/meshkit.py`, a small Python/numpy modelling kit: chamfered boxes and convex hulls, lathes, lofts, profile extrusion with ear-clipping, sweeps along paths, ring sweeps around the arena ellipse, weathering jitter and baked vertex-colour grime/AO. |
| Rigging / animation | The same kit writes skeletons (joints + inverse bind matrices), proximity-based skin weights and keyframed rotation/translation clips. |
| Export | Hand-written, spec-compliant binary glTF 2.0 (`.glb`) writer. Godot imports these like any Blender export. |
| Source files | The Python generators **are** the editable sources (the equivalent of `.blend` files). Run `tools/asset_gen/build_all.sh` to regenerate everything. |

If Blender becomes available later, any `.glb` can be opened in Blender
(File → Import → glTF 2.0), refined there, and re-exported over the same path —
the Godot import settings (material remap script) still apply.

## Generated assets

| Asset | Generator | Notes |
|---|---|---|
| Colosseum floor, podium wall + 6 gates/tunnels, statue niches, terrace, seating tiers with stair aisles, arcaded galleries, attic with velarium masts, arena ruins | `build_colosseum.py` | Plus collision meshes and `resources/colosseum_layout.json` |
| Undead legionary + undead gladiator (skinned, 7 animations: Idle, Walk, Run, Attack, Hit, Death, Emerge) | `build_characters.py` | Shared 18-bone skeleton |
| Marble statues (legionary, gladiator) | `build_characters.py` | Same rig, posed in Python and baked |
| M1911 pistol, M4 carbine, Jupiter wonder weapon, first-person gloves/sleeves | `build_weapons.py` | Original models guided by the reference sheet's proportions |
| Mystery Box, Pack-a-Punch machine, tall + tripod braziers, wall torch, banner, floor debris (helmet, shield, sword, bones) | `build_props.py` | |
| All textures (travertine masonry, weathered stone, sand, gun metal, polymer, wood, bronze, iron, zombie skin, cloth, leather, blood/scorch/bullet-hole decals, particles, banner art, star field, icon) | `textures.py` | Seeded spectral noise / Worley noise; tileable |
| Godot materials | `gen_materials.py` | Mapped onto GLB surfaces by name at import |
| All sound effects and ambience (gunshots, Jupiter thunder, reloads, zombie groans/attacks/deaths, player hurt/death, footsteps, Mystery Box music-box tune, Pack-a-Punch forge, round horns, ambience, fire loop) | `audio.py` | Synthesised from oscillators, filtered noise and convolution reverb. The Mystery Box tune is an original melody. |

Licence for all of the above: original work created for this project; the
project owner may license it however they choose.

## Visual overhaul, phase 1 (October 2026)

Blender was checked again before this pass: no `blender` binary, `bpy` is not
installable from PyPI here, and download.blender.org returns 403 through the
sandbox proxy. **Blender was not used for this pass either.** All new
architecture was modelled with the same Python kit and exported with the same
GLB writer; Godot 4.7.2 imported every file (verified with `godot --import`
and in-engine renders).

| Asset | Generator | Notes |
|---|---|---|
| Modular podium bays (PanelA/B/C, Niche, Gate, Column): individual ashlar blocks with chipped edges and per-block tint, recessed mortar, voussoir arches with keystones, fluted engaged columns with bases and capitals, moulded cornice, parapet, base course, sand drifts, rubble, flagstones, damaged variant | `arch_kit.py`, `build_arena_v2.py` → `podium_modules.glb` | Placed per bay by `scripts/colosseum/colosseum.gd`, all instances share one mesh per module |
| Cavea: individual seat slabs (trimmed at stair aisles), arcade bays for tier 2 and galleries (intact and damaged), attic bays (plain, mast, broken) | `build_arena_v2.py` → `colosseum_cavea.glb`, `cavea_modules.glb` | Distant arcade/attic bays drawn as MultiMesh |
| Rebuilt arena ruins: fluted column drums, ashlar ruin walls with rubble core and half-fallen arch, flagstone altar | `build_colosseum.py` → `colosseum_obstacles.glb` | Collision shapes unchanged |
| Textures: limestone, warm sandstone, marble, mortar, sand v2, macro variation, rain streaks (albedo / normal / roughness) | `textures_v2.py` | Procedural, seeded, tileable |
| Weathered-stone shader (world triplanar PBR + macro variation + ground grime + streaks + ledge dust) | `resources/shaders/stone.gdshader` | Original |
| Materials `lime_*`, `marble_v2`, `mortar_v2`, `rubble_core`, `paving`, `tunnel_stone`, `sand_v2`, and shader overrides of the legacy `stone_*`, `marble`, `sand` | `gen_materials_v2.py` | Original |

No third-party textures, scans or models were added in this pass.

## Third-party assets

| Asset | Source | Licence |
|---|---|---|
| Cinzel font (`assets/fonts/Cinzel-Variable.ttf`) | Google Fonts repository (github.com/google/fonts, `ofl/cinzel`) | SIL Open Font License 1.1 — `assets/fonts/Cinzel-OFL.txt` |
| Oswald font (`assets/fonts/Oswald-Variable.ttf`) | Google Fonts repository (github.com/google/fonts, `ofl/oswald`) | SIL Open Font License 1.1 — `assets/fonts/Oswald-OFL.txt` |
| Godot Engine 4.7.2 | godotengine.org | MIT |

"SPQR" and the laurel/eagle motifs on the banners are historical Roman symbols
drawn procedurally.
