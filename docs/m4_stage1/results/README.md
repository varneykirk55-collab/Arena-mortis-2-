# Stage 1 validation

- Godot 4.7.2 standard Linux build; Blender 4.3.2 actually executed.
- `tests/run_tests.tscn`: **223 passed, 0 failed**, exit 0.
- `tests/m4_pipeline.tscn`: **32 passed, 0 failed**, exit 0.
- Both capture runs finished with `M4_CAPTURE_DONE`, exit 0. Five PNGs per run.
- Full M4 rebuild via `build_weapons.py` into an external output directory
  reproduced an identical GLB: SHA-256
  `2b08bbdc458b82a3c7ec19426f69df018e679a61419cdea447b6e73d37ab3b93`.
- `git diff --check` passed. Gameplay scripts/data, scenes, project settings,
  SSAO shader/environment settings and arena files match the starting branch.
- No changes to the pistol, Jupiter, arms or zombie models.

| Godot view | Draw calls before | Draw calls after |
|---|---:|---:|
| Hip | 1575 | 1578 |
| ADS | 898 | 901 |
| Fixed reload pose | 1586 | 1592 |
| Pack-a-Punch | 1583 | 1589 |
| Studio profile | 8 | 11 |

GLB LOD0: 2,240 → 26,200 triangles; 8 → 11 surfaces; 331,476 → 1,558,688 bytes.
Automatic LOD may reduce the triangles drawn in the profile capture.

The captures used software OpenGL; these counts are not a GPU performance
benchmark. Compatibility reports expected warnings for unavailable screen-space
AA and volumetric fog. Forward+ and target-hardware performance remain untested.

Logs retain the actual runner output. The first development version of the new
M4 test accidentally included the runtime flash QuadMesh in its imported-mesh
audit; the corrected final test excludes it and passed all 32 checks. No
production code was changed to make a test pass.
