#!/bin/bash
cd "$(dirname "$0")/../.."
timeout 600 xvfb-run -a -s "-screen 0 1280x720x24" godot --rendering-driver opengl3 --path . -s tools/preview/node_preview.gd -- "$@" 2>&1 | grep -E "NODE_PREVIEW_OK|SCRIPT ERROR"
