# Samurai anatomical hand rebuild — local working tree

Generated 2026-11-06 23:00 EST. No commit or push made by the executor.

## Geometry and provenance

- Replaced both generated mitten regions with MakeHuman hm08 CC0 hand geometry, using the female/young macro, muscle 0.45, weight 0.45. Source: `/workspace/ic_proto/pipeline/assets/mh/base.obj`, female target files, and native skin weights. The OBJ header explicitly dedicates these assets to CC0 (September 2020). Existing body/weapon licences are unchanged.
- Hand skin albedo: CC0 MakeHuman system-assets `skin_middleage_caucasian_male.png`; only the UV hand regions are used, packed in the Blender source and embedded in the GLB. Geometry uses female proportions; the texture name does not describe the mesh.
- Each editable hand: 1,621 vertices / 1,607 quads; budgeted surface: 1,074 geometric vertices / 2,120 triangles. Distinct tapered fingers, opposed thumb, anatomical palm pads, knuckle contours and native nail/nail-bed detail. No fused strips remain.
- Wrist-to-middle-fingertip bone landmark: 176.59 mm on each hand. The 206.65 mm mesh piece includes a 29.92 mm forearm overlap hidden under the cuff. The join is overlapped, not welded; the original generated sleeve cuff remains angular.
- Existing 54 bones retained; the existing 30 finger bind bones were repositioned onto actual anatomical joints and weighted from the CC0 skin weights. No bones or clips added/deleted. Four-influence export weights.
- Updated only hand/arm contact in all 15 existing clips. No Reload, Hit or Death additions, no clip unification, no socket orientation/14-degree tilt correction. Keep the existing integration roll180.
- Total triangles: 23,583 versus 19,967 before (+3,616). The GLB is 7,910,380 bytes versus 4,064,872 before; the extra packed CC0 skin image is not cropped/atlased yet.

## FP_Arms partition

- Export contains `FP_Arms` (arms, sleeves, both hands; 7,509 triangles) and `node_0` (remaining body; 16,074 triangles), both referencing glTF skin 0 / the same 54-bone skeleton and 15 clips.
- 3,269 original arm/sleeve triangles were moved from body into FP_Arms. All 19,343 non-hand body triangles were retained across the two mesh nodes, with no missing/extra triangles; maximum bind-position difference from export float conversion: 4.22e-8 m. Hide `node_0`, keep `FP_Arms` visible for first-person.
- The .blend retains separate editable quad hand templates and the unsplit non-hand body; `export_samurai_hands.py` applies the hand budget, limits skin weights, and creates FP_Arms non-destructively at export. Use that helper instead of a plain manual export.

## Why the previous 0 mm measurements were wrong

The previous tools aligned the gun with `socket * roll180 * inverse(full RightHand marker transform)`. The game aligns the RightHand marker POSITION, but does not invert its -14-degree rotation. The correct mount is:

```text
gun_world = socket_world * roll180 * Translation(-gun_RightHand.origin)
left_palm_world = mean(world LeftHand, LeftHandIndex1, LeftHandPinky1 origins)
```

Using that mount on the actual old GLB in Godot reproduces Rob: approximately 76.147 mm M4, 33.107 mm Jupiter, and 8.416 mm pistol. The left-arm contacts were re-solved against this position-only mount in every clip. Do not reinstate full-marker inversion in the test harness. If Rob later changes the gun mount basis for his tilt fix, hand contacts must be retargeted to that new basis.

## Pistol marker

- RightHand translation (native glTF / Godot model coordinates): `(0, 0.004, 0.024)` -> `(0, -0.032, 0.045)`, moved off the rear slide onto the upper handle/web region. Blender source translation: `(0, -0.045, -0.032)`.
- Marker rotation unchanged; Muzzle and LeftHand markers unchanged. The pistol GLB BIN chunk is byte-identical before/after: no gun geometry changed. M4/Jupiter/other gun GLBs untouched.
- Right thumb/index contact was refitted against the actual position-only mount; support-hand orientation cups the grip. This improves placement, but remaining skin intersections below mean it is NOT a final no-clipping grip.

## Actual Godot measurements, every 30 fps sample in all clips

Distances below use Skeleton3D global bone poses, not Blender-only data. Left = Rob's exact three-origin average. Right uses the explicit grip-cylinder reference stored as `right_grip_reference_hand_local_m` on the rig (M4 `(0.035,0.05,-0.025)`, pistol `(0.03,0.05,0.005)`, Jupiter `(0.045,0.05,-0.04)`). These are internal grip references, not a promise that the whole skin surface avoids the gun.

| Clip | Old left mm | New left mm | Right reference mm | Loop |
|---|---:|---:|---:|---:|
| AimIdle | 76.146528 | 0.001830 | 0.000370 | 1 |
| AimIdle_Jupiter | 33.106927 | 0.001570 | 0.000170 | 1 |
| AimIdle_Pistol | 8.415489 | 0.001470 | 0.000270 | 1 |
| FireRecoil | 76.146521 | 0.000960 | 0.000250 | 0 |
| FireRecoil_Jupiter | 33.106674 | 0.001230 | 0.000150 | 0 |
| FireRecoil_Pistol | 8.415455 | 0.001090 | 0.000250 | 0 |
| Idle | 76.147228 | 0.002070 | 0.000280 | 1 |
| Idle_Jupiter | 33.107162 | 0.002040 | 0.000150 | 1 |
| Idle_Pistol | 8.415539 | 0.002390 | 0.000120 | 1 |
| Run | 76.146632 | 0.001330 | 0.000260 | 1 |
| Run_Jupiter | 33.106923 | 0.002180 | 0.000140 | 1 |
| Run_Pistol | 8.415685 | 0.002030 | 0.000150 | 1 |
| Walk | 76.146401 | 0.001270 | 0.000140 | 1 |
| Walk_Jupiter | 33.106104 | 0.002050 | 0.000140 | 1 |
| Walk_Pistol | 8.415527 | 0.001930 | 0.000140 | 1 |

Maximum new left distance: 0.002390 mm; maximum right reference distance: 0.000368 mm. Maximum socket world-matrix element/axis comparison delta versus baseline: 1.36e-6 with identical Godot importer parameters. Unit bone-scale error <=5.1e-6 (float precision). `.import` is byte-identical; FireRecoil variants remain non-looping and the other 12 clips loop.

## Remaining release blocker: skin penetration

**The hand geometry and palm-reference constraints are improved, but the low-penetration requirement is NOT met. Do not describe this as a finished, no-clipping grip.** Natural-sized fingers/pads still pass through some grip/trigger/ornament surfaces. Jupiter is worst. The old tiny mitten mesh is not a comparable vertex sampling density.

Sampled every five source frames plus clip endpoints. Three non-axis ray-parity votes estimate whether each evaluated hand vertex is enclosed; depth is nearest gun-surface distance. The gun meshes contain cut/open/overlapping pieces, so these are approximate diagnostics, not exact intersection volumes. Vertex tests can also miss edge-only intersections.

| Gun | Hand | Old enclosed % / depth mm | New enclosed % / depth mm |
|---|---|---:|---:|
| m4 | Right | 9.64% / 17.23 | 25.51% / 12.88 |
| m4 | Left | 17.16% / 7.53 | 15.83% / 13.08 |
| pistol | Right | 0.00% / 0.00 | 11.73% / 12.82 |
| pistol | Left | 1.87% / 0.83 | 12.10% / 12.65 |
| jupiter | Right | 58.07% / 33.30 | 23.46% / 31.54 |
| jupiter | Left | 45.90% / 14.84 | 25.42% / 25.05 |

The corrected numeric palm point alone is insufficient to establish visible contact quality. Close-up review and more surface-aware grip shaping are still required. No collision corrective morphs or collision-only meshes were exported to hide this failure.

## Verification and evidence

- glTF validator: 0 errors on samurai (4 warnings) and pistol (3 warnings); warnings are tangent-space / skinned-parent diagnostics.
- Godot imports: no ERROR/WARNING diagnostics in final import logs.
- Final real repo tests: 223 checks passed, 0 failed; final resource-pointer-swapped copy tests: 223 checks passed, 0 failed. Test cleanup still logs ObjectDB/resource-in-use warnings at process exit. The temp copy swaps six actual gameplay resource pointers; the legacy model import assertions continue to inspect legacy files.
- An earlier hard binary replacement experiment failed five legacy material-remapping assertions; an overloaded early real run had six navigation timing failures. Final serial capped-frame runs above pass without changing tests.
- Working evidence: `/workspace/arena_mortis2/work/humanhands/`: `godot_check.gd`, `godot_check.log`, `godot_pointmount_before_fix.log`, `final_metrics.json`, `measure_parity_*.json`, `body_partition_proof.json`, validator/import/test logs, and build scripts.
- Before/after previews: `/workspace/arena_mortis2/work/previews/hands_{rest,pistol,m4,jupiter}_{before,after}_{right,left}.png`; contact sheet `hands_contact_sheet.png`.

## Local files to review / commit

- `assets/models/player_samurai.glb`
- `assets/models/blend_sources/player_samurai.blend`
- `assets/models/weapon_pistol_new.glb`
- `assets/models/blend_sources/weapon_pistol_new.blend`
- `assets/models/blend_sources/export_samurai_hands.py`
- This note and `player_samurai_hands_metrics.json`.

Working tree only. Parent owns commit/push. The visible-clipping release blocker remains open.
