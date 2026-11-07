# Samurai anatomical hands — FP/TP follow-up to 454307f

Generated 2026-11-07 00:59 EST. Working tree only; no Git commands, commit or push by executor.

## Current asset and integration contract

- `node_0` is now the **complete TP body**, including the original full arms/sleeves and both anatomical hands: **23,583 triangles**. It equals the previous `node_0` + `FP_Arms` triangle union exactly in bind space (0 missing, 0 extra; 1e-6 m tolerance, measured max position difference 0). No other body geometry changed.
- `FP_Arms` is a **separate duplicate**, forearms/hands/cuffs only: **4,600 triangles**, down from 7,509 (-2,909). All its triangles are also in the complete body. Both meshes use skin 0 / the same 54-bone skeleton.
- Non-skin FP faces require every vertex at least 15% down the forearm from the elbow, average forearm/hand weight >0.35, and every vertex within 75 mm of the forearm axis. Actual minimum t=0.153261 and maximum radius=57.759 mm. No shoulder armour or upper sleeve remains.
- **TP must show `node_0` and hide `FP_Arms`; FP must do the reverse.** Rob's existing TP loop explicitly shows all meshes and must be updated. Showing both now duplicates 4,600 triangles and will z-fight. The preview harness applies correct visibility; Rob's original checkout was not modified.
- Total stored geometry is 28,183 triangles because FP is intentionally duplicated; active TP is 23,583 and active FP is 4,600. Active TP remains +3,616 over the original mitten asset (19,967). GLB: 8,005,196 bytes.

## Hands, contacts and unchanged items

- Retained the CC0 MakeHuman hm08 female/young hand rebuild: 176.59 mm wrist-to-middle-tip, 1,621 editable vertices / 1,607 quads per hand; exported budget 1,074 geometric vertices / 2,120 triangles each. Separate tapered fingers, palm pads, knuckle and nail detail. Existing 30 finger bones and all 54 names remain.
- CC0 source: `/workspace/ic_proto/pipeline/assets/mh/base.obj`, female macro targets and native weights; header explicitly dedicates it to CC0 (September 2020). Packed hand-region skin image is MakeHuman CC0 `skin_middleage_caucasian_male.png`; female geometry is independent of that texture name.
- Fixed a UV-layer join bug: hand and body UV layer names are unified before joining, preserving hand skin/nail UVs instead of losing them. The editable source keeps separate hand templates; use `export_samurai_hands.py`, not a plain manual export.
- M4 support fingers now follow a handguard ellipse, with opposed thumb; MCP origins are retained so the left-palm metric is preserved. Opposite-side/top previews show the wrap; near-side views necessarily hide fingers behind the handguard. M4 right middle/ring/pinky fingers were also wrapped around the grip surface.
- Right hand/forearm contact moved inward by 12/10/15 mm for pistol/M4/Jupiter, respectively, with right thumb/index refitted. Existing socket **world** transform was preserved, not a new gun tilt.
- The 15 clip names, durations, 162 channels per clip and loop settings are unchanged. Only requested existing arm/hand contact keys changed. No Reload/Hit/Death additions, no clip unification, no 14-degree correction. No gun GLB or gun source was edited in this revision.
- Pistol's marker already remains at native glTF `(0,-0.032,0.045)` from the prior revision (historically moved from `(0,0.004,0.024)`); its rotation is unchanged. Socket orientation is unchanged within float tolerance.
- The wrist stub extends 29.92 mm under the original cuff. This is an overlap, **not a weld**; original generated cuffs remain angular. TP previews render the full body alone, with no missing-arm seam or duplicate FP surfaces.

## Exact Godot palm measurements

Mount matches the game, not full-marker inversion:

```text
gun_world = socket_world * roll_Z_180 * Translation(-gun_RightHand.origin)
palm = mean(world origins of Hand, HandIndex1, HandPinky1)
```

Both right and left below use that exact three-origin mean. The old right-reference 0 mm numbers were a different internal grip landmark and must not be presented as this metric. Sampled every 1/30 second including endpoints in all 15 clips, using Godot Skeleton3D poses and identical importer settings for the 454307f baseline.

| Clip | Before right mm | After right mm | After left mm | Loop |
|---|---:|---:|---:|---:|
| AimIdle | 48.7245 | 40.3378 | 0.002180 | 1 |
| AimIdle_Jupiter | 65.3277 | 54.0583 | 0.001582 | 1 |
| AimIdle_Pistol | 37.8454 | 26.0760 | 0.002028 | 1 |
| FireRecoil | 48.7246 | 40.3380 | 0.001207 | 0 |
| FireRecoil_Jupiter | 65.3277 | 54.0585 | 0.001324 | 0 |
| FireRecoil_Pistol | 37.8454 | 26.0759 | 0.001325 | 0 |
| Idle | 48.7245 | 40.3382 | 0.002058 | 1 |
| Idle_Jupiter | 65.3277 | 54.0584 | 0.001683 | 1 |
| Idle_Pistol | 37.8453 | 26.0759 | 0.002390 | 1 |
| Run | 48.7245 | 40.3380 | 0.001437 | 1 |
| Run_Jupiter | 65.3276 | 54.0584 | 0.002275 | 1 |
| Run_Pistol | 37.8453 | 26.0760 | 0.002153 | 1 |
| Walk | 48.7247 | 40.3381 | 0.001080 | 1 |
| Walk_Jupiter | 65.3277 | 54.0585 | 0.001915 | 1 |
| Walk_Pistol | 37.8453 | 26.0759 | 0.002049 | 1 |

Maximum left error: **0.002390 mm**. Right max by gun: pistol 26.0760, M4 40.3382, Jupiter 54.0585 mm; deliberately not claimed to be 0. The marker is a web/grip landmark, not the bone-centroid surface. Maximum socket origin delta versus baseline: 0.000622 mm; maximum basis-axis vector delta 1.18e-06. Bone-scale error <= 5.07e-06. `.import` is byte-identical. FireRecoil variants do not loop; other 12 clips do.

## Remaining skin-intersection limitation

**Not a no-clipping release.** Fingers/pads still intersect some gun surfaces; Jupiter support fingers are the worst and can look cut off by occluding metal. Do not hide this caveat behind the near-zero left-palm result. Right centroid gaps were reduced; they were not forced to zero at the cost of pushing the whole palm into the gun.

Diagnostics below use fixed rest-decimated export geometry, 4 normalized weights, 1,074 vertices/hand, at start/middle/end of each clip. Three non-axis ray-parity votes estimate enclosure; depth is nearest surface for enclosed vertices. These guns have open/overlapping pieces, so this is approximate, not a solid intersection-volume test, and vertex tests can miss edge intersections. Values are maxima over all five clips per gun (not only AimIdle).

| Gun | Hand | Before enclosed % / depth mm | After enclosed % / depth mm |
|---|---|---:|---:|
| pistol | Right | 11.73% / 12.82 | 13.69% / 13.16 |
| pistol | Left | 12.10% / 12.65 | 12.10% / 12.65 |
| m4 | Right | 25.51% / 12.88 | 26.26% / 13.48 |
| m4 | Left | 15.83% / 21.32 | 4.00% / 14.36 |
| jupiter | Right | 23.37% / 31.54 | 18.06% / 27.48 |
| jupiter | Left | 25.33% / 25.05 | 25.33% / 25.05 |

M4 support enclosure is substantially reduced, but residual intersections remain. M4/pistol right maximum depth is about 0.60/0.34 mm higher than baseline; Jupiter right depth is reduced. No corrective morphs or collision-only geometry conceal the issue.

## Verification and evidence

- glTF validator: **0 errors, 4 warnings** (generated tangent-space / skinned-parent warnings).
- Final Godot 4.7.2 real, swapped-temp and preview imports: 0 ERROR / 0 WARNING diagnostics. Renderer-only compatibility/VSync/fog warnings in screenshot logs are unrelated to import.
- Final real-repo tests: **223 passed, 0 failed**. Final temp copy: **223 passed, 0 failed**, with three `_new` weapon resource pointers and the actual new samurai instantiated through the full suite. Assertions unchanged; legacy material-remap assertions still inspect legacy files. Actual new character additionally exercised by all-clip measurement and Rob's integrated game previews. Exit cleanup is not clean despite exit 0: real suite reports 4 ObjectDB instances / 2 resources still in use; the temp suite with the added samurai fixture reports 40 / 4. No test assertions fail.
- Actual player eye camera (~1.6216 m) AimIdle hip/ADS previews for pistol/M4/Jupiter, before and after, show removal of the large upper-sleeve/shoulder occluders. Same Rob game/poses, 1024x576 Compatibility renderer; preview-only shadows disabled, far=30 m to keep software rendering practical. TP previews hide FP_Arms for the final asset; baseline correctly shows the former two disjoint meshes.
- Previews: `/workspace/arena_mortis2/work/previews/hands_fpfix_*_{before,after}.png`. Main contact sheet: `hands_fpfix_contact_sheet.png`; hip and TP sheets: `hands_fpfix_hip_contact_sheet.png`, `hands_fpfix_tp_contact_sheet.png`. Includes M4 support opposite-side/top and each right grip.
- Audit scripts/logs/JSON: `/workspace/arena_mortis2/work/fpfix/` (`contact_metrics.json`, `mesh_proof.json`, `measure_parity_*.json`, validator/import/test logs, actual-camera harness in `rob_preview/tests/_asset_review.gd`).

## Files changed in this follow-up

- `assets/models/player_samurai.glb`
- `assets/models/blend_sources/player_samurai.blend`
- `assets/models/blend_sources/export_samurai_hands.py`
- This note and `player_samurai_hands_metrics.json`.

No gun changes or game-code changes in this follow-up. Parent owns commit. Rob must apply the TP visibility rule above; residual skin clipping remains open.
