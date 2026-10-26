class_name Layers
extends RefCounted
## Physics layer bit masks (see project.godot [layer_names]).

const WORLD := 1          # layer 1: static level geometry
const PLAYER := 2         # layer 2: player body
const ZOMBIE_BODY := 4    # layer 3: zombie movement capsules
const HURTBOX := 8        # layer 4: zombie damage areas (head/body)
const INTERACTABLE := 16  # layer 5

const BULLET_MASK := WORLD | HURTBOX
