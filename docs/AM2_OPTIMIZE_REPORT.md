# Arena Mortis 2 staged asset optimization

MB = decimal 1,000,000 bytes. Git cost includes GLB + embedded images extracted on Godot import.

| Asset | Before MB | After MB | Git cost MB | Tris before → after | Errors |
|---|---:|---:|---:|---:|---:|
| emendatio_mortis.glb | 57.43 | 4.40 | 8.08 | 50,006 → 15,000 | 0 |
| jupiter_rifle.glb | 45.67 | 3.55 | 6.53 | 50,004 → 14,999 | 0 |
| mystery_box.glb | 46.75 | 3.35 | 6.06 | 50,000 → 15,000 | 0 |
| pistol_red.glb | 26.55 | 1.83 | 3.12 | 50,008 → 14,999 | 0 |
| pistol_red_alt.glb | 28.27 | 1.90 | 3.24 | 49,998 → 15,000 | 0 |
| rifle_alt_a.glb | 32.78 | 2.63 | 4.69 | 50,000 → 15,000 | 0 |
| rifle_alt_b.glb | 31.27 | 2.53 | 4.48 | 50,000 → 14,999 | 0 |
| rifle_m4.glb | 27.54 | 2.23 | 3.87 | 50,000 → 15,000 | 0 |
| player_samurai_rigged.glb | 35.58 | 3.35 | 5.42 | 49,636 → 19,999 | 0 |
| zombie_legionary_rigged.glb | 38.27 | 3.53 | 5.87 | 50,072 → 19,998 | 0 |

## Method and verification
- Serialized Blender 4.2 decimation: 20k character tris; 15k guns/props. Skin weights retained, all source node and joint names checked for preservation.
- Albedo: 2K JPEG quality 90 (1K on pistols); normals and ORM: 1K lossless PNG.
- All GLBs revalidated using Khronos glTF Validator. Missing-node and missing-joint checks are in optimized/optimization_stats.json.
- No source downloads, marked originals or .blend files modified.
- Character validators also warn NODE_SKINNED_MESH_NON_ROOT; animated transform/deformation testing is still required.
- `RightWeaponSocket` is a Skeleton3D bone, not a Node3D. Attach third-person weapons via BoneAttachment3D with bone_name `RightWeaponSocket`; do not use a node-path lookup for it.
- No animations exist in these optimized exports (rest pose only).
- Validator tangent-space warnings: normals require runtime-generated tangent space. Godot imports calculate it; this is not a validation error.
- Marker locations remain provisional. Mystery Box lid and Emendatio machine gears remain fused; marker nodes do not separate the mesh.
- Visual silhouette/texture approval and animated deformation/playtesting are still required.

Godot isolated import exit code: 0; staged load/marker/skin verification exit code: 0.

## Repository handoff blocker
The required CloudAgent tool is absent in this executor tool catalog. Repository-content edits and commits require that tool per code-changes/source-control instructions. No branch, commit, model copies, gameplay pointers or environment files changed by this executor. Repository remains main @ 2760f1e.

Existing gameplay tests on unchanged checkout: 223 checks passed, 0 failed, process exit 0. Shutdown reports 40 ObjectDB instances leaked and 4 resources still in use. See optimized/logs/existing_game_tests.log. This is not a new-asset gameplay test.
