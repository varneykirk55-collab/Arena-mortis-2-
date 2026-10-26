# Test results — foundation build 0.1.0

Environment: Linux cloud container, Godot 4.7.2 stable, no GPU. Every run was
headless or used software rendering (Mesa llvmpipe through Xvfb). That shapes
what could be checked, so read the **Limitations** section.

## 1. Automated suite: `tests/run_tests.tscn`, **223 checks passed, 0 failed**

```
PASS  test_weapon_resources        3 weapons load, sane stats, audio, model markers (Muzzle/hands/Magazine)
PASS  test_weapon_instance_logic   firing consumes ammo, reload math, empty-reserve, one-tier upgrade, upgraded name
PASS  test_damage_falloff          full damage in range, falloff floor
PASS  test_wallet                  start balance, cannot overspend, exact deduction
PASS  test_shop_items              health/ammo/damage items, escalating cost, purchase cap
PASS  test_wave_config             rounds 1-20 strictly more zombies and more health; runners later; active cap set
PASS  test_mystery_box_roll        20,000 rolls: Jupiter 12.4 %, M4 87.6 %, pistol never
PASS  test_model_imports           GLBs import; zombies have skeleton + Idle/Walk/Run/Attack/Hit/Death/Emerge;
                                   arena collision generated; materials remapped
PASS  test_scenes_instantiate      main menu, player, zombie, machines, colosseum, game
PASS  test_navigation_baked        navmesh baked; nav path from each of the 6 gates to the arena centre
PASS  test_shoot_and_kill_zombie   pistol kills a 150 HP zombie; exact points (+10/hit, +60 kill); ammo;
                                   removed from tracking; corpse freed after sinking
PASS  test_headshot_bonus          one-shot headshot kill, +100 headshot bonus, headshot counted
PASS  test_jupiter_precision       a missed bolt hurts nobody; a direct bolt hits hard; no chaining to a zombie 2 m away;
                                   ammo is limited
PASS  test_reload                  reload starts and refills the magazine
PASS  test_mystery_box_flow        prompt on approach; refused without points (no charge); charges 950; cycles;
                                   offers; player receives and equips the weapon; box closes
PASS  test_pack_a_punch_flow       refused without points (no charge); nothing charged mid-process; upgrade applied
                                   (more damage); exactly 5000 deducted once; weapon returned; second upgrade refused free
PASS  test_shop_purchases          shop pauses game; +25 max health; ammo refill refused when full (free) and
                                   works when needed; +15 % damage; unaffordable refused; leaving starts next round
PASS  test_zombie_attacks_player   zombie navigates to the player and damages them
PASS  test_wave_progression        round ends only when all zombies are dead; round 2 is bigger; active cap is never exceeded;
                                   late-round zombies are tougher
PASS  test_death_and_restart       death -> game-over screen -> restart: no leftover zombies, points/health/upgrades/
                                   weapons reset, round 1 again
```

The suite found and fixed one real bug: recoil used to be applied *before*
the shot ray, so Jupiter's heavy kick sent a correctly aimed bolt over the
zombie's head. Recoil now applies after the shot.

Also run: `tests/check_scripts.gd` (every script and scene parses and loads)
and a headless smoke run of the game scene with zero script errors.

## 2. Bot playtest: `tests/bot_playtest.tscn`

A scripted bot played the real game loop at 3× speed. It aims, fires, reloads,
backs away, uses the Mystery Box and shops between rounds.

```
round 1: 6 zombies (150 HP)  cleared at 20 s
round 2: 9 zombies (250 HP)  bot opened the Mystery Box and took the M4, cleared at 59 s
round 3: 11 zombies (350 HP) cleared at 96 s, bought +25 health
round 4: 15 zombies (450 HP) cleared at 241 s, bought health + ammo
round 5: 18 zombies (550 HP) 16 of 18 killed before the 12-minute session limit
57 kills, no script errors, no stuck zombies
```

An earlier bot run that had only the pistol ran out of ammo in round 3 and
was chased down by the last zombie. Per-zombie position logs confirmed the
zombies kept navigating and nothing was stuck. After that run the pistol's
reserve went from 80 to 96, and jogging and sprinting zombies were moved back a
round (jog from round 3, sprint from round 5).

## 3. Visual checks (screenshots, Compatibility renderer under Xvfb)

Rendered and inspected:

* the Colosseum from the arena floor and from above
* the Mystery Box: approach prompt, lid open with weapons cycling, offer
* hip-fire and ADS framing for the pistol, M4 and Jupiter, plus the gloved arms
* Pack-a-Punch: idle, working (weapon lowered), prompt
* HUD: round numeral, points, health, weapon/ammo, prompts, banners
* the shop, the pause menu, and the death camera with the red vignette
* zombie and statue models, and every animation pose
* weapons, machines and props on their own

Screenshots live in `tools/preview/out/` locally. They are git-ignored, so
regenerate them with the commands in the README.

## Limitations (not verified)

* **No real GPU, no live play.** Nobody played the game interactively with
  mouse and keyboard. Controls, game feel, difficulty and fun still need
  your playtest. Input was exercised through Godot's input actions and direct
  calls.
* **The Forward+ look was never seen.** Screenshots came from the
  Compatibility (OpenGL) renderer. Volumetric fog, SSAO and Forward+ glow
  never rendered here, and lighting and fog density may need tuning on a real
  GPU.
* **No performance numbers.** Software rendering ran at a few frames per
  second, which says nothing about a gaming PC. Budget: Colosseum about
  300 k triangles with auto-LODs, about 33 dynamic lights (most shadowless),
  zombies capped at 24 at once.
* **Windows build not launched.** `build/windows/ArenaMortis.exe` exported
  cleanly with the official 4.7.2 templates, but this environment can't run
  Windows binaries. It hasn't been run anywhere yet.
* **Audio unheard.** Sounds are synthesised and their waveforms were checked
  visually, but nobody has listened to them yet.
* **Blender not used** (unavailable here). See `docs/ASSET_SOURCES.md`.
