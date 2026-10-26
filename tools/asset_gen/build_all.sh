#!/bin/bash
# Regenerates every procedural asset (textures, materials, models, audio).
set -e
cd "$(dirname "$0")"
python3 textures.py ../../assets/textures
python3 gen_materials.py ../../resources/materials
python3 build_colosseum.py ../../assets/models ../../resources/colosseum_layout.json
python3 build_characters.py ../../assets/models
python3 build_weapons.py ../../assets/models
python3 build_props.py ../../assets/models
python3 audio.py ../../assets/audio
echo "All assets regenerated. Run 'godot --headless --import' to reimport."
