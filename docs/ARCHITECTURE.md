# Arena Mortis — Architecture

This document explains how the Godot project is put together, who owns what,
and how to extend it without rebuilding anything.

## 1. Runtime scene tree

```
MainMenu (scenes/ui/main_menu.tscn)          ← application entry point
└─ Colosseum (backdrop only: spawn_gameplay = false, build_navigation = false)

Game (scenes/main/game.tscn, scripts/main/game.gd)   ← one run
├─ Colosseum (scenes/colosseum/colosseum.tscn)
│  ├─ WorldEnvironment / Moon light / Ambience
│  ├─ NavigationRegion3D            ← navmesh baked at load from these children
│  │  ├─ Floor, Podium, Obstacles   ← generated GLBs with "-colonly" collision
│  │  ├─ MysteryBox, PackAPunch     ← placed by colosseum.gd from the layout
│  │  └─ tall braziers              ← "-convcol" collision, part of the navmesh
│  ├─ Cavea                         ← seating / galleries (visual only)
│  ├─ Props                         ← torches, tripods, statues, banners, debris, decals
│  └─ Markers                       ← ZombieSpawns/Gate0..5 (group "zombie_spawn"), PlayerSpawn
├─ Zombies (container for spawned Zombie instances)
├─ Player (scenes/player/player.tscn)
│  ├─ Head/Camera3D/WeaponManager   ← weapons, viewmodels, firing
│  └─ Interactor                    ← finds Interactables, forwards "interact"
├─ PointsWallet                     ← points balance (group "points_wallet")
├─ WaveManager                      ← rounds, spawning, active cap
├─ HUD, PauseMenu, ShopMenu, GameOverScreen (CanvasLayers, built in code)
```

`Game` is the only node that knows about everything. It wires signals in
`_ready()` and owns the run state machine:

```
INTRO → PLAYING → (round cleared) → INTERMISSION → SHOP (tree paused) → PLAYING …
                         └──────── (player died) ────────→ GAME_OVER
```

**Restart** calls `get_tree().reload_current_scene()`. Because every piece of
run state (zombies, round, points, upgrades, purchases, weapons) lives inside
the Game scene, a reload is a guaranteed clean slate. Only the `Settings`
autoload (mouse sensitivity, volumes, FOV) persists.

## 2. Ownership boundaries

| System | Script | Owns | Talks to others via |
|---|---|---|---|
| Settings (autoload) | `scripts/core/settings.gd` | input actions, sensitivity, FOV, volumes (saved to `user://settings.cfg`) | `changed` signal |
| Input bindings | `scripts/core/input_setup.gd` | every key/mouse binding, in one table | called by Settings |
| Player | `scripts/player/player.gd` | movement, look, health/regen, recoil, death | `health_changed`, `damaged`, `died` |
| Interaction | `scripts/player/interactor.gd` + `scripts/interactables/interactable.gd` | choosing the focused interactable, prompts | `prompt_changed` |
| Weapons | `scripts/weapons/weapon_manager.gd` | slots, firing, reload, switching, ADS, viewmodel motion | `weapon_changed`, `ammo_changed`, `fired`, `hit_registered`, `reload_*` |
| Weapon data | `scripts/weapons/weapon_data.gd` (Resource) | all per-weapon numbers, sounds, upgrade rules | — |
| Weapon state | `scripts/weapons/weapon_instance.gd` (RefCounted) | ammo + upgrade tier, pure logic (unit-tested) | `changed` |
| Viewmodel | `scripts/weapons/viewmodel.gd` | model, gloves, muzzle flash, procedural fire/reload/equip animation | read by WeaponManager |
| Zombies | `scripts/zombies/zombie.gd`, `hurtbox.gd` | AI states, navigation, attacks, hit reactions, death, cleanup | `died` |
| Waves | `scripts/waves/wave_manager.gd` + `wave_config.gd` | round sizes, spawn pacing, active cap, completion | `round_started`, `round_completed`, `remaining_changed`, `zombie_killed` |
| Economy | `scripts/economy/points_wallet.gd` + `economy_config.gd` + `shop_item.gd` | balance, every cost/reward | `points_changed`, `purchase_failed` |
| Mystery Box | `scripts/interactables/mystery_box.gd` | weighted pool roll, open/cycle/offer/close | `opened`, `weapon_offered`, `weapon_taken`, `closed` |
| Pack-a-Punch | `scripts/interactables/pack_a_punch.gd` | one-tier upgrade, charge-only-on-success | `upgrade_started`, `upgrade_finished` |
| Shop | `scripts/ui/shop_menu.gd` | between-round purchases, purchase counts | `closed` |
| Arena | `scripts/colosseum/colosseum.gd` | dressing from the layout, markers, environment, navmesh bake | — |
| FX | `scripts/fx/*.gd` | fire, impacts/decals, lightning bolt, tracers (fire-and-forget) | — |
| HUD/menus | `scripts/ui/*.gd` | display only; never change game state directly except via Game callbacks | — |

Rules followed throughout:

* **Signals up, calls down.** Children never reach into siblings; `Game` connects them.
* **Data in resources.** Weapons (`resources/weapons/*.tres`), economy and shop
  (`resources/economy/economy_config.tres`), waves (`resources/waves/wave_config.tres`),
  materials (`resources/materials/*.tres`), environment (`resources/environment_dusk.tres`).
* **One autoload** (`Settings`), because settings genuinely outlive scenes.
* **Groups**: `player`, `zombies`, `zombie_spawn`, `interactable`, `points_wallet`.
* **Physics layers** (`scripts/core/layers.gd`): 1 world, 2 player, 3 zombie bodies,
  4 hurtboxes, 5 interactables. Bullets ray-test `WORLD | HURTBOX` only, so the
  zombie movement capsule never eats shots; head/body hurtboxes decide damage.

## 3. Key flows

**Shooting.** `WeaponManager._fire()` consumes a round, plays the viewmodel
kick + sound, then either `_fire_hitscan()` (spread, penetration, tracer,
impacts) or `_fire_lightning()` (Jupiter: zero spread, first collider only, no
splash, no chaining). Hits call `Zombie.take_damage()` which returns
`{killed, is_head, damage}`; the manager emits `hit_registered`, and `Game`
awards points (per hit, plus kill or headshot-kill bonus). Recoil is applied
*after* the ray so it affects the next shot.

**Zombie lifecycle.** `WaveManager.spawn_one()` picks a gate (weighted toward
nearer gates, never closer than `min_spawn_distance`), configures health/speed
from `WaveConfig`, and adds the zombie. The zombie plays `Emerge`, then chases
using `NavigationAgent3D` with RVO avoidance, attacks inside `attack_range`
(damage lands mid-swing only if the player is still within `attack_hit_range`),
staggers on heavy hits, and on death disables collision/hurtboxes, plays
`Death` (or an electrocution flash for Jupiter kills), leaves a blood decal,
sinks, and frees itself.

**Rounds.** A round ends when `to_spawn == 0` and no zombie is alive.
`Game` pays the round bonus, shows the banner, waits, then opens the shop
(tree paused). Leaving the shop heals the player and starts the next round.

**Pack-a-Punch.** Validates weapon + balance up front, lowers the weapon for
`process_time`, then at completion: `try_spend()` → `upgrade_current()`; if the
upgrade could not be applied the cost is refunded. Points are never taken for
an upgrade that did not happen.

## 4. Assets pipeline

All 3D models, textures, materials and sounds are generated by the Python
scripts in `tools/asset_gen/` (see `docs/ASSET_SOURCES.md` for why Blender was
not used and what replaced it). Each generated `.glb` gets a `.import` file
that runs `tools/import/material_remap.gd`, which swaps glTF materials for the
project's `resources/materials/<name>.tres` by name. So:

* change a **shape** → edit the generator, run `tools/asset_gen/build_all.sh`, then `godot --headless --import`;
* change a **look** → edit the material `.tres` (or `gen_materials.py`) — no regeneration of meshes needed.

Special node-name suffixes used in the GLBs (Godot import conventions):
`-colonly` (invisible trimesh collision) for floor/podium/obstacles and
`-convcol` (visible + convex collision) for braziers and machines.

## 5. Extending

* **New weapon:** add a `.glb` with `Muzzle`, `RightHand`, `LeftHand`
  (and optional `Magazine`, `Slide`/`Bolt`, `Sight`, `Core`) nodes, create a
  `WeaponData` `.tres`, give it a `box_weight > 0`, and append it to the
  Mystery Box `pool` in `scenes/interactables/mystery_box.tscn`. No code needed.
* **New zombie look:** add a GLB using the same skeleton/animation names
  (`build_characters.py` → `write_zombie()`), add it to `model_scenes` in
  `scenes/zombies/zombie.tscn`.
* **Difficulty:** edit `resources/waves/wave_config.tres`.
* **Prices/rewards/shop items:** edit `resources/economy/economy_config.tres`
  (new item effects need one `match` branch in `ShopMenu.buy()`).
* **New interactable:** extend `Interactable`, implement `get_prompt()` and
  `interact()`, add it anywhere in the scene. The Interactor finds it via the
  `interactable` group.
* **Arena dressing:** layout points come from `resources/colosseum_layout.json`
  (written by `build_colosseum.py`); placement rules live in `colosseum.gd`.

## 6. Tests

* `tests/run_tests.tscn` — unit + integration suite (headless).
* `tests/bot_playtest.tscn` — scripted bot plays rounds through the normal loop.
* `tests/visual_capture.tscn` / `tests/viewmodel_preview.tscn` — screenshot QA (needs a display; we used Xvfb + the Compatibility renderer).
* `tests/check_scripts.gd` — parses every script.

See `docs/TEST_RESULTS.md` for the latest results and limitations.
