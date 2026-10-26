#!/bin/bash
# tools/preview/preview.sh <res://path> <out_prefix> [yaws] [pitch] [zoom] [anim] [time]
cd "$(dirname "$0")/../.."
timeout 300 xvfb-run -a -s "-screen 0 1280x720x24" godot --rendering-driver opengl3 --path . -s tools/preview/preview.gd -- "$@" 2>&1 | grep -E "PREVIEW_OK|ERROR|SCRIPT ERROR" | grep -v "ALSA\|audio" | head -20
