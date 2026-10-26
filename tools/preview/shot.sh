#!/bin/bash
# tools/preview/shot.sh <scene(s)> <out_prefix> "px,py,pz>tx,ty,tz" ...
cd "$(dirname "$0")/../.."
timeout ${SHOT_TIMEOUT:-400} xvfb-run -a -s "-screen 0 ${SHOT_W:-1280}x${SHOT_H:-720}x24" godot --rendering-driver opengl3 --path . -s tools/preview/scene_shot.gd -- "$@" 2>&1 | grep -E "SHOT_OK|ERROR|SCRIPT" | grep -v "ALSA\|audio\|ui_theme" | head -20
