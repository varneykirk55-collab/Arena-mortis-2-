# Visual overhaul, phase 1: report

Branch `visual-overhaul-phase1`; safety tag `pre-visual-overhaul-phase1`
(Gemini's SSAO/lighting fix, commit 2760f1e) marks the starting point.

## 1. Tool verification

| Tool | Result |
|---|---|
| Blender | **Not available, not used.** No `blender` binary; `bpy` has no installable distribution here; download.blender.org returns HTTP 403 through the sandbox proxy. Re-checked at the start and end of this pass. |
| Python generation | Yes. numpy modelling kit in `tools/asset_gen/` (`meshkit.py`, new `arch_kit.py`, `build_arena_v2.py`). |
| GLB export | Yes. Hand-written glTF 2.0 binary writer (`meshkit.write_glb`). |
| Godot 4.7.2 import | Yes. `godot --headless --import` imports every regenerated GLB with no errors (a clean checkout needs two import passes; see README). |
| Runtime | Yes. In-game renders from the real `game.tscn`, the automated suite and the smoke run all load the new assets. |

## 2. What changed visually

**Stage A (north span, bays 20–25)** was built first, compared with matching
before shots (`docs/visual_pass/stageA_before_after.png`), then extended in
**Stage B** to the whole arena.

* **Podium wall.** Rebuilt from one swept mesh into modular bays made of
  individual ashlar blocks. The blocks have chamfered, chipped edges, per-block
  colour variation and recessed mortar joints. There are six module types
  (three panel variants, statue niche, gate, column) plus mirroring, so
  neighbouring bays do not repeat.
* **Arches.** Real voussoir rings with keystones over gates and niches. The
  masonry is clipped around each arch instead of being a flat cut-out.
* **Columns and trim.** Fluted engaged columns with moulded bases and
  capitals; a profiled cornice, parapet and base course.
* **Gates and tunnels.** Gates now have ashlar side walls, a vaulted
  voussoir ceiling, flagstone floors, rubble and a portcullis.
* **Floor-to-wall transition.** Sand drifts and scattered rubble along the
  wall foot, plus shader grime that fades with height.
* **Seating.** Individual seat slabs with slight settling and tilt and a few
  missing stones, trimmed cleanly at the stair aisles.
* **Upper tiers.** Arcade bays with real arches and columns, including damaged
  variants. The attic has windows, mast sockets and broken sections.
* **Arena ruins.** Fluted fallen and broken columns, ashlar ruin walls with a
  rubble core and a half-collapsed arch, and a flagstone altar.
* **Materials.** New procedural limestone, warm sandstone, marble, mortar and
  sand textures (albedo, normal, roughness). They use a world-triplanar
  weathering shader with two-scale macro variation (no visible tiling), ground
  grime, rain streaks and sand dust on ledges. Legacy material names were
  moved onto the same shader so props and statues match.
* **Lighting.** The moon was lowered from 1.45 to 0.95 energy and made cooler.
  The warm fill went from 0.45 to 0.16. Ambient, fog and sky were retuned
  toward a blue night with warm torch pools; contrast was raised slightly and
  saturation lowered. **SSAO stays disabled**, so Gemini's fix for the black
  corruption is intact.
* **Zombies and weapons.** Inspected only; no changes were needed. In the
  combat readability shot (`after_Z1_zombies_combat.png`) both stay clear
  against the floor and walls.

## 3. What did not change

Gameplay code, weapon and zombie data, the round system, the Mystery Box,
Pack-a-Punch, the economy, player movement and the Three.js repository were
not touched.

The arena layout is the same: the comparison of `colosseum_layout.json`
against the tag is identical for gates, panels, obstacles, torches, banners,
tiers and grates. Only statue heights in the niches changed, plus new keys
for the modules.

Collision meshes and the navigation source are unchanged, and the navmesh
still bakes to 185 polygons. Zombies spawn and path normally in the smoke run.

## 4. Verification

* `tests/run_tests.tscn`: **223 checks passed, 0 failed.**
* `tests/smoke_run.tscn`: round 1 spawns and runs normally; nav polygons 185.
* `tests/beauty_shots.tscn`: ten fixed cameras rendered through the real game
  scene, before and after. Images are in `docs/visual_pass/before|after/`, and
  side-by-side sheets are `docs/visual_pass/compare_*.png` and
  `stageB_before_after.png`.
* The renders were inspected by eye, not just generated. Passing tests are
  **not** treated as proof that the graphics look good.

## 5. Performance

PERF_TABLE

* Unique geometry in the scene is PERF_SURFACES. The podium uses 30 bay
  instances that share 6 meshes. Upper tiers are 10 MultiMeshes, one per
  module (about 280 instances).
* Triangle budgets per module:

  | Module | Triangles |
  |---|---|
  | Panel A | 3.3 k |
  | Panel B | 6.4 k |
  | Panel C | 4.4 k |
  | Niche | 5.7 k |
  | Gate | 18.2 k |
  | Column | 1.4 k |
  | Arcade bay | 0.56–0.62 k |
  | Attic bay | 0.06–0.24 k |

  Seating is 121 k triangles in 24 culled sectors.
* **Auto-LOD.** Disabled for block-built meshes, because Godot's simplifier
  collapses separate blocks into slivers. Distant tiers use purpose-built
  low-poly modules instead. The floor keeps auto-LOD.
* **Draw calls.** The draw-call numbers come from the Compatibility (OpenGL)
  renderer, which draws an object once more for every extra light that
  touches it. Forward+ uses clustered lighting and should come in lower, but
  that was not measured here. The renders used software GL, so frame times
  say nothing about a real GPU.

## 6. Unresolved issues

* **Forward+ never seen.** All screenshots use the Compatibility renderer
  (llvmpipe, no GPU here). Fog, glow and shadow softness may need retuning
  on a real GPU.
* **Draw calls.** Visible draw calls are higher than before in wide views
  (see table). If it matters on target hardware, the next step is to merge
  podium bays per quadrant into MultiMeshes and drop a material surface (sand
  drifts) into a shared mesh.
* **Panel C damage patch.** The damaged panel's exposed rubble core reads as a
  dark rectangle from some angles (left of the banner in A3, behind
  Pack-a-Punch in G4). It needs a rougher outline and lighter core.
* **Ruin walls.** The free-standing ruin walls read greyer and noisier than
  the podium. The legacy `stone_blocks` texture is still on their faces.
* **Mystery Box corner.** It remains on the dark side; a small warm fill
  light near it would help readability.
* **Windows build.** Exported but not launched; this environment cannot run
  Windows binaries.
