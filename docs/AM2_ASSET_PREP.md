# Arena Mortis 2 — prepared asset handoff (2026-11-06)

All files in `staging/optimized/` are staged replacements, NOT gameplay-integrated. See `OPTIMIZE_REPORT.md` and `optimized/optimization_stats.json` for measured costs and verification.

## Intended repository mapping (safe alongside existing models)

| Optimized staged source | Intended `assets/models/` destination |
|---|---|
| zombie_legionary_rigged.glb | zombie_legionary_new.glb |
| player_samurai_rigged.glb | player_samurai.glb |
| jupiter_rifle.glb | weapon_jupiter_new.glb |
| pistol_red.glb | weapon_pistol_new.glb |
| rifle_m4.glb | weapon_m4_new.glb |
| rifle_alt_a.glb | weapon_rifle_alt.glb |
| mystery_box.glb | mystery_box_new.glb |
| emendatio_mortis.glb | pack_a_punch_new.glb |

`pistol_red_alt.glb` and `rifle_alt_b.glb` remain optimized alternates in staging; do not add duplicates unnecessarily. Existing models remain in place: no move to `_old/` is necessary for alongside-only additions. If any destination already exists, preserve it before replacing.

## Characters and markers

Female samurai = player. Roman legionary = zombie. Each has 24 skin joints and retains all source node/joint names, including `Head` and player `RightWeaponSocket`. They are rest-pose rigs with NO animation clips. Retain working gameplay models and animations until a verified animation set is ready.

`Head` and `RightWeaponSocket` are Skeleton3D bones. For weapon mounting create a BoneAttachment3D with bone_name `RightWeaponSocket`; no standalone Node3D socket is imported. Both rigs include this socket bone.

Jupiter: `Muzzle`, `RightHand`, `LeftHand`, `Core`.
Mystery Box: `Lid`, `WeaponAnchor`.
Emendatio: `Disc`, `GearL`, `GearR`.
All source markers retained; marker positions are provisional and require in-game attachment/interaction checks. Box lid and machine gears remain fused into the source mesh: markers alone do not enable their animation.

## Constraints / remaining work

- Do not alter weapon resource pointers, ammunition, damage, chain logic, zombie AI or environment files.
- New assets are not visually approved or interactively playtested.
- Character movement, attacks, hits, deaths, player handling, aim, firing and reload clips are NOT present. Bone deformation still needs animation verification.
- Existing baseline gameplay test suite: 223 checks passed, zero failed, exit 0. Existing shutdown warnings report 40 ObjectDB instances and four resources still in use.
- Proposed branch: `bjorn/am2-asset-prep`; no push or merge permitted.
- This executor has no CloudAgent tool, which is mandatory for repository-content edits/commit by current instructions; repository integration and commit remain pending with the coordinator.
