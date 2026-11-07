# Arena Mortis 2 — prepared asset handoff (2026-11-06)

Working tree based on `bjorn/am2-asset-prep` at `14d2cf8`. The new assets are alongside-only: real gameplay resource/scene pointers remain unchanged. No gameplay, weapon balance, environment or source-code changes accompany these asset corrections.

## Deliverables

Final GLBs: `assets/models/`. Editable Blender 4.2 sources: `assets/models/blend_sources/` (with `.gdignore` to avoid automatic Blender reimports). All eight GLBs and blends also exist in `/workspace/arena_mortis2/work/out/`. The two copies are hash-checked in `work/fixes/final_hashes.json`. Six GLBs changed in this correction pass; zombie and Jupiter are unchanged.

## Characters

Female samurai = player; Roman legionary = zombie. Both retain 24 bones, including `Head`, `RightWeaponSocket`, and `LeftHandIK`. Socket markers are Skeleton3D bones, not standalone Node3Ds: attach via BoneAttachment3D.

| Asset | Clips (seconds) |
|---|---|
| zombie_legionary_new | Idle 2.4; Walk 1.033333; Run 0.666667; Attack 1.0; Hit 0.333333; Death 1.6; Emerge 1.3 |
| player_samurai | Idle 2.4; Walk 1.0; Run 0.666667; AimIdle 2.0; FireRecoil 0.233333 |

Zombie clips are adapted from the stage1 legionary rig. Gameplay already enables looping for its Idle/Walk/Run. Samurai clips are basic procedural FK, not mocap; no reload, fingers, cloth simulation or weapon-contact IK is claimed.

Samurai now faces Godot **-Z** (180-degree armature yaw). Both horizontal rest foot-to-toe forward dots against -Z are **1.0**. RightWeaponSocket is at the RightHand bone origin rather than its tail; its orientation is baked per frame so mounted weapons point forward. Sampled every 1/30 second across every clip:

| Clip | Maximum wrist/socket distance (m) | Minimum socket forward dot against -Z | Imported loop mode |
|---|---:|---:|---:|
| AimIdle | 0.000000120 | 0.999996603 | 1 (linear) |
| FireRecoil | 0.000000120 | 0.999999762 | 0 (one shot) |
| Idle | 0.000000124 | 0.999999821 | 1 |
| Run | 0.000000152 | 1.000000000 | 1 |
| Walk | 0.000000126 | 1.000000000 | 1 |

Animation names are unchanged. **Include `player_samurai.glb.import` in the handoff**: `_subresources/animations/<clip>/settings/loop_mode=1` stores the four loop decisions. This was verified after Godot 4.7.2 import, not inferred from names. A real BoneAttachment3D with the M4 instantiated under it measured weapon forward dot **1.0**.

## Weapons

M4 and pistol origins are now grip-relative. Their RightHand/LeftHand positions match the old model markers, with both hand markers pitched -14 degrees. Their overall bounding-box sizes match the old models; muzzle positions match the old values exactly to float precision:

| Asset | Size X/Y/Z (m) | Muzzle X/Y/Z (m) | Muzzle forward dot against -Z |
|---|---|---|---:|
| weapon_m4_new | 0.068 / 0.311 / 0.886 | 0 / 0.022 / -0.56 | 1.0 |
| weapon_pistol_new | 0.044 / 0.171 / 0.198 | 0 / 0.037 / -0.14 | 1.0 |
| weapon_rifle_alt | 0.060318 / 0.230493 / 0.840125 | 0 / 0.174089 / -0.42 | 1.0 |

The replacement sculpts have different silhouettes, so matching size and muzzle/grip anchors does not make every bounds coordinate identical. M4 minimum Y is -0.210438 vs old -0.196; pistol -0.114636 vs old -0.107. This is not an interactive first-person framing/art approval.

Real texture-preserving geometry splits (not empty nodes):
- M4: `M4` body 13,639 faces; `Magazine` 1,090; `Bolt` 271.
- Pistol: `Pistol` body 5,826 faces; `Magazine` 1,873; `Slide` 7,300.
- Region-based cuts retain UV/materials but are not bespoke clean mechanical topology; cut edges merit close-up review.

The failing contract is `tests/run_tests.gd:test_weapon_resources` lines 145–147, which checks Muzzle, RightHand, LeftHand and Magazine on all three weapon models. This checkout has **223**, not Rob's separate 273, checks. Bolt and Slide are additionally verified by direct imported-node inspection.

Rifle-alt: geometry and marker positions rotated together, so the real barrel is now on -Z. Muzzle Z=-0.42, LeftHand Z=-0.168, RightHand Z=+0.032436. Both hands import at -14 degrees pitch. Muzzle/right-grip direction dot against -Z is 0.979381561 (vertical rise included); the muzzle's own forward dot is 1.0.

Jupiter remains unchanged in this pass. Its new asset does **not** have a Magazine node; do not switch its resource pointer and assume the weapon contract passes.

## Mystery Box and Emendatio / Pack-a-Punch

The lid and machine moving parts are actual separate MeshInstance3Ds, not just empty markers. Mystery Box has `BoxBody`, `Lid` on a rear hinge, and `BoxInterior`. Emendatio has `MachineBody`, `Disc`, `GearL`, `GearR`, and dark inner hubs. The gear pieces are segmented roller/end rings from the fused sculpt; existing cut-boundary/art-quality caveats still apply.

Per-axis affine scaling matches the **entire old closed mesh bounds**, rather than uniformly scaling only the width:

| Asset | Bounds minimum X/Y/Z (m) | Size X/Y/Z (m) |
|---|---|---|
| mystery_box_new (same as old) | -0.617794 / -0.025 / -0.329625 | 1.235588 / 0.748875 / 0.659250 |
| pack_a_punch_new (same as old) | -1.3 / 0 / -0.95 | 2.6 / 2.472598 / 1.9 |

Box WeaponAnchor Y restored to **0.85 m**, lid pivot now approximately (-0.000173, 0.596039, -0.294208). PaP width restored to **2.6 m**; `WeaponSlot` at old (0,0.75,0.75) is present. Disc/gears keep pivots appropriate to their own sculpt, not the old machine's different geometry: Disc (0.002264,0.423703,0.882923), GearL (-0.618929,0.933537,0.051114), GearR (0.623457,0.933537,0.051114). Prompt/light/audio offsets have not been changed and still merit Rob's visual check.

## Verification and evidence

All evidence below is under `/workspace/arena_mortis2/work/fixes/`.
- `blender.log`, `fix_assets.py`, `changes.json`: export method, source backups in `before/`, measured transformations and split face counts.
- `measure.gd`, `measure.log`: imported bounds, marker positions/axes, loop modes, body forward, every-frame socket sampling, actual attached M4. `FIX_CHECKS failures=0`.
- `validator_summary.json`: all eight GLBs have **0 validator errors**. Warnings remain (generated tangent space and inherited rig hierarchy); zero warnings is not claimed.
- `import.log`: real repo Godot 4.7.2 headless editor import, exit 0, no ERROR/WARNING/SCRIPT ERROR diagnostics.
- `temp_import.log`: temporary swapped-copy import, exit 0, no ERROR/WARNING/SCRIPT ERROR diagnostics.
- `tests_swapped.log`: Rob-scope swapped-copy full suite, **223 passed / 0 failed**, exit 0. Shutdown reports 40 leaked ObjectDB instances and 4 resources still in use.
- `verify_assets.log`: animation motion/finite transforms, zombie clips, lid movement and nonempty machine parts; `ASSET_RUNTIME_CHECKS failures=0`, exit 0; lid center displacement after opening = 0.491474956 m.
- `tests_unswapped.log`: full real-repo suite, **223 passed / 0 failed**, exit 0. Shutdown reports 4 leaked ObjectDB instances and 2 resources still in use; this test shutdown is not described as warning-free.

The temporary copy is `work/fixes/temp_swapped/`; swaps are recorded in `temp_pointer_changes.txt`. It uses the new M4, pistol, legionary, box and PaP; original Jupiter is retained, matching Rob's pointer-swap scope. Samurai is not wired into this older checkout's player code, so its attachment and animation assertions are performed separately in `measure.gd`.

An additional all-new-pointer trial (also switching Jupiter) produced **222 passed / 1 failed**, exit 1: only `jupiter model has Magazine` failed. This is an unchanged Jupiter-asset limitation, not silently fixed here; see `tests_swapped_including_jupiter.log`.

Five Blender review stills are saved beside the logs (`weapon_m4_new.png`, `weapon_pistol_new.png`, `player_samurai.png`, `mystery_box_new.png`, `pack_a_punch_new.png`). These are offline stills, not a gameplay visual sign-off.

No git write commands, commits, pushes or merges were run. Parent owns commit/integration and interactive visual approval.

## Samurai finger rig and gun-hold poses (Nov 6, 2026, EST; base 6c7141d)

- **Finger bones:** 30 added (`{Left,Right}Hand{Thumb,Index,Middle,Ring,Pinky}{1,2,3}`, children of each hand); skeleton is now **54 bones** (24 + RightWeaponSocket/LeftHandIK included in the 24 + 30 fingers). The mesh fingers are fused (mitten-like, ~13 cm hand, no gaps between fingers), so bones were laid along four strips across the knuckle width with Gaussian cross-strip weights and a smooth hand→finger blend at the knuckles (292 right / 205 left hand vertices reweighted). The thumb has no separate lobe; its bones drive the thumb-side edge. Adjacent fingers with different curls shear the fused web; separation is limited by the geometry.
- The old UV-preserving mesh-curl hack and the RightHand→RightWeaponSocket skin redirect were dropped (mesh is the uncurled original); the pistolfix arm-weight cleanup (2,174 vertices) is retained.
- **Clips (all 15):** Idle/Walk/Run/AimIdle/FireRecoil × base(M4)/_Jupiter/_Pistol. Right hand in a handshake grip (fingers across the grip, index extended as trigger finger, thumb opposed); left hand palm-up under the handguard for rifles, cupped over the right hand for the pistol; elbows down. AimIdle/FireRecoil hold the gun ~4 cm further to her right than the ready clips.
- **Socket:** RightWeaponSocket world orientation is unchanged per frame in Idle, AimIdle and FireRecoil (max basis delta 6e-7). Its origin is now keyed to the palm grip point (was the wrist). In **Walk and Run** the socket orientation is locked to Idle frame 0 so the gun no longer tilts with the gait. Rob's 180° roll stays.
- Loop settings, clip names and -Z forward unchanged (`player_samurai.glb.import` byte-identical).
- Measured in Godot (palm grip point to marker, roll applied): right 0.0 mm, left 10–12 mm (deliberate under-rail offset) in every clip; gun up-dot constant 0.9703 in every clip. Wrist-bone-to-marker distances are 5.6–6.0 cm (right) by design.
- Verification: validator 0 errors/2 warnings; Godot import clean; 223/223 tests in the real repo and in an all-new-models copy.
