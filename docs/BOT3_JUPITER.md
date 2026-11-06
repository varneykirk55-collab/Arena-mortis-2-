# Bot 3 — Jupiter chain lightning

Dedicated branch: `bot3/jupiter-chain-lightning`. No main merge. No GLB,
skeleton, environment, Mystery Box or Pack-a-Punch implementation changes.
Existing Bot 1 anchor contracts are retained (`Muzzle`, `RightHand`,
`LeftHand`, optional `Core`/`Magazine`, `LeftArmRifle`).

## Mechanics

A zero-spread ray acquires the initial enemy (a miss does not auto-target).
The shot snapshots living zombies, uses per-shot instance identities and a
hard **10 unique enemies including the first** limit. Each next target is
the nearest unvisited living zombie within 9 metres with a clear physics ray
to its torso collision centre. World geometry and intervening living
hurtboxes obstruct jumps. Stop on cap or no valid candidates.

Every hit uses `WeaponManager._apply_hit` -> `Zombie.take_damage` ->
`hit_registered`; existing kill points, electrocution and wave death signals
are preserved. Primary hits retain headshot multipliers; jumps use body
hurtboxes. Damage is resolved atomically on the firing tick; the connecting
beams and impacts reveal every 25 ms, for 225 ms maximum propagation. Beams
use captured endpoints and do not track moving victims after the shot.

## PROVISIONAL balance — pending Kirk approval

- Automatic, 4 shots/second, 100-round magazine, 400 reserve.
- Existing 2,200 damage and 2.8-second reload retained.
- Optimus Maximus: 4,400 damage, 150/600 ammo, 5.2 shots/second,
  2.38-second reload, existing one-tier upgrade/refill path.
- Radius/cadence/damage/economy impact need a human balance review; changing
  these does not change the non-negotiable ten-enemy safety limit.

## Presentation and audio

Blue-white target-to-target flickering beams with decorative forks, delayed
impact sparks/smoke and transient lights; existing zombie electrocution.
White-gold core-to-muzzle idle arcs, a rising/falling energy light pulse,
recoil and a distinct core/magazine recharge pose retain existing anchors.
Idle arc light/branch length is bounded for subtlety. Procedural motion is
not a newly integrated skeletal animation or model.

Original generated mono PCM sounds: `jupiter_charge.wav` (rising electrical
oscillator/noise, 0.16 seconds) and `jupiter_chain.wav` (decaying gated-noise
crackle, 0.24 seconds). Existing discharge, upgraded discharge, electrical
impact and reload sounds are reused. Jupiter firing/reload/chain/impact use
spatial SFX, at most four requests per discharge and eight concurrent voices;
oldest is stopped before replacement. No ten-hit hitmarker sound storm.
Listen/mix on real hardware before declaring the audio final.

## Validation / reproducible demonstration

Godot 4.7.2:

```
godot --headless --path . --editor --import
godot --headless --path . res://tests/run_tests.tscn
# Optional quick focused subset:
godot --headless --path . res://tests/run_tests.tscn -- --jupiter-only
# Render evidence, output directory must already exist:
xvfb-run -a godot --path . --rendering-method gl_compatibility \
  --write-movie /absolute/evidence/jupiter-chain.avi --fixed-fps 30 \
  res://tests/jupiter_chain_demo.tscn -- /absolute/evidence
```

Regressions cover cap/uniqueness across two discharges, nine real connected
jump beams, missed shots, blocked LOS, range/exhaustion, rewards and wave
completion, ammo/reload/upgrades and electrical voice budget. Existing
Mystery Box, Pack-a-Punch, weapons and wave tests are retained.

The demo creates twelve immobilized enemies in the actual arena and records
one shot from an overview camera. It is deterministic software-rendered
evidence, **not** a human playable GPU or performance certification. GPU
Forward+ playtest, sustained automatic-fire performance, first-person
alignment/reload polish, audio mixing and final balance approval remain.
Existing model paths are reused; no new Bot 1 model integration is claimed.


## V: first / third-person camera (follow-up task)

FP remains the default. `camera_toggle` is bound to physical V. A separate
`PlayerPerspective` controller smoothly positions the existing camera over
the right shoulder, tightening with ADS; a 0.22m world sphere sweep prevents
near-plane wall clipping and snaps inward before smoothing back outward.
The same camera controls the reticle in both views. In TP, a reticle ray
chooses the aim point and a muzzle ray resolves the actual hit, preserving
parallax and nearby cover. The player body has no targeting collision.

TP hides FP-only arms/model and instantiates a weapon-only Viewmodel at a
provisional head-relative mount. Fire/reload/equip and inventory/ammo state
remain in the shared framework; toggling mid-reload preserves its timer.

**Asset dependency:** the player scene currently contains no full body.
A neutral capsule `ThirdPersonBody` is a deliberately visible placeholder,
not a Roman or female samurai asset. Bot 1 may supply
`Player.third_person_body_scene` or an existing `ThirdPersonBody` node.
Bot 1 confirmed the **female samurai** rig with a **skeleton bone** `RightWeaponSocket`
(and `LeftHandIK`). Runtime discovers the bone in any nested Skeleton3D and
creates a `BoneAttachment3D` with `bone_name="RightWeaponSocket"`, then parents
weapon presentation there without FP rest offsets; if missing, it uses the
explicit `RightWeaponSocket_PLACEHOLDER` under the head. Bot 1 has prepared `assets/models/player_samurai.glb` on its own branch;
that GLB is rest-pose only and is **not copied or merged into this branch**. Final socket alignment,
left-hand IK and character animations remain with Bot 1. Do not use the Roman zombie rig
as the player body. Camera hides the placeholder when collision pushes the
view inside it. Hardware playtesting and final TP alignment/animation remain.

Additional automated tests cover both reticles for M1911/M4/Jupiter, V action,
FP default, FP arms visibility, TP movement, toggling while reloading,
shoulder ADS distance, wall collision and return to FP.


## Results for this pass

- Godot 4.7.2 headless: **273 checks passed, 0 failed**, exit 0.
- Software OpenGL/llvmpipe rendered demo: **10 hits from 12 living enemies**,
  exit 0; captured successive connecting arcs and impact frames.
- No human GPU/Forward+ playtest or hardware audio/performance sign-off.
- Base is main `2760f1e`; no Bot 2 cinematic dependency.
- Fetched Bot 1 dependency `origin/bjorn/am2-asset-prep` at `6058dfc` only;
  no merge or model copy. GLB metadata confirms `RightWeaponSocket`,
  `RightHand` and `LeftHandIK` are skin joints.
- Current Jupiter/Mystery Box/Pack-a-Punch GLB pointers remain unchanged.
