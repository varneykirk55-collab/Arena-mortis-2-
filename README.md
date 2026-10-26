# Arena Mortis (Godot 4)

Round-based, single-player, first-person zombie survival inside an ancient
Roman Colosseum. Survive escalating waves of undead legionaries and gladiators
with modern firearms, the Mystery Box, Pack-a-Punch, a between-round shop and
Jupiter, a lightning wonder weapon that rewards precise aim.

This is the **playable foundation** built from scratch in Godot. The original
Three.js version of Arena Mortis is a separate project and was not touched.

## Requirements

* **Godot 4.7.x (stable)** with the standard (non-.NET) build. Developed and
  tested with 4.7.2.
* Windows PC with a Vulkan-capable GPU (the project uses the Forward+ renderer).
* Optional, only to regenerate assets: Python 3.10+ with `numpy`, `scipy`, `Pillow`.

## Running

1. Open Godot → **Import** → select `project.godot`.
2. First open imports every asset (about a minute).
3. Press **F5** (main scene is the main menu).

Or from a terminal: `godot --path .`

A Windows build is produced with `godot --headless --export-release "Windows Desktop" build/windows/ArenaMortis.exe`
(export templates for 4.7.2 must be installed).

## Controls

| Action | Key |
|---|---|
| Move | W A S D |
| Look | Mouse |
| Fire | Left mouse |
| Aim down sights | Right mouse (hold) |
| Reload | R |
| Sprint | Shift (forward only, not while aiming/firing) |
| Jump | Space |
| Interact (Mystery Box, Pack-a-Punch) | E |
| Switch weapon | 1 / 2, Q, or mouse wheel |
| Pause / unpause | Esc |

Mouse sensitivity, FOV, invert-Y and volumes are in **Settings** (main menu and
pause menu) and are saved between sessions.

## The loop

* You start in the middle of the arena with an **M1911** and **500 points**.
* Zombies crawl out of the six gate tunnels. Each round has more of them, and
  they get tougher; jogging zombies appear from round 3 and sprinters from round 5.
* Points: **+10** per hit, **+60** per kill, **+100** per headshot kill, plus a
  round bonus (50 × round).
* **Mystery Box** (north wall, 950): random weapon from a weighted pool —
  M4 Carbine (common) or **Jupiter** (about 1 in 8). If you already have the
  weapon, taking it refills it.
* **Pack-a-Punch** (south wall, 5000): one upgrade per weapon — more damage,
  bigger magazine and reserve, faster fire, new name and an animated finish.
* **Between-round shop**: max health (+25), full ammo refill, +15% weapon damage.
* Die and restart from the game-over screen (or the pause menu) for a clean run.

## Project layout

```
scenes/       main (game), colosseum, player, zombies, interactables, ui
scripts/      core, main, player, weapons, zombies, waves, economy, interactables, ui, fx, colosseum
resources/    weapons/*.tres, economy/, waves/, materials/, shaders/, environment
assets/       models (.glb), textures, audio, fonts
tools/        asset_gen (Python generators = asset sources), import (material remap), preview (QA renderers)
tests/        automated tests, bot playtest, screenshot capture
docs/         ARCHITECTURE.md, ASSET_SOURCES.md, TEST_RESULTS.md
```

Tuning lives in data, not code:

* weapons → `resources/weapons/*.tres`
* costs, rewards, shop items → `resources/economy/economy_config.tres`
* round sizes, health, speeds, spawn pacing, active cap → `resources/waves/wave_config.tres`

See **docs/ARCHITECTURE.md** for the scene structure, ownership boundaries and
how to extend the game.

## Running the tests

```
godot --headless --import                                   # once
godot --headless --path . res://tests/run_tests.tscn         # unit + integration (exit code 0 = pass)
godot --headless --path . res://tests/bot_playtest.tscn -- 4 3   # bot plays up to round 4 at 3x speed
```

Screenshot QA (needs a display; on Linux use Xvfb):
`xvfb-run godot --rendering-driver opengl3 --path . res://tests/visual_capture.tscn -- res://tools/preview/out`

Results and known limitations: **docs/TEST_RESULTS.md**.

## Regenerating assets

```
cd tools/asset_gen && ./build_all.sh
cd ../.. && godot --headless --import
```

Blender was not available in the environment this foundation was built in, so
the models were authored with a Python modelling kit instead. See
**docs/ASSET_SOURCES.md**.
