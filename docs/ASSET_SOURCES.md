# Asset sources and licences

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

## Third-party assets

| Asset | Source | Licence |
|---|---|---|
| Cinzel font (`assets/fonts/Cinzel-Variable.ttf`) | Google Fonts repository (github.com/google/fonts, `ofl/cinzel`) | SIL Open Font License 1.1 — `assets/fonts/Cinzel-OFL.txt` |
| Oswald font (`assets/fonts/Oswald-Variable.ttf`) | Google Fonts repository (github.com/google/fonts, `ofl/oswald`) | SIL Open Font License 1.1 — `assets/fonts/Oswald-OFL.txt` |
| Godot Engine 4.7.2 | godotengine.org | MIT |

"SPQR" and the laurel/eagle motifs on the banners are historical Roman symbols
drawn procedurally.
