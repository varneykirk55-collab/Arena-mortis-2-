# Legionary Zombie — reusable source

Original character created with Blender 4.3.2 Python mesh modelling, armature
tools, vertex groups and keyed actions. The editable `Legionary_Zombie.blend`
contains the rig, four named meshes and packed original procedural PBR images.
The generation source is `tools/asset_gen/build_legionary_blender.py` in the
project; no third-party character models, animation clips or concept images
were used. The preserved `original_legionary.glb` is the project's old model,
included for comparison only.

## Coordinates and structure

- Metres, unit scale 1. Character approximately 1.83 m to helmet crown.
- Blender: Z up, -Y forward, X right. Exported glTF/Godot: Y up, +Z forward.
- Origin at the ground between the feet. Root object `Legionary_Rig` is static;
  `Hips` is the animation root. Locomotion is in-place.
- Armature `Legionary_Humanoid`: 52 named bones. Hips → Spine → Chest → Neck →
  Head; Jaw, clavicles, upper/lower limbs, feet/toes and three joints per digit.
- `Skin_Anatomy`, `Lorica_Helmet`, `Tunic_Cloth`, `Leather_Equipment`: four
  skinned meshes, one shared `legionary_atlas` material. Armor vertices are
  rigidly assigned to a single bone; skin blends across limb joints.
- 37,168 triangles at full detail, normalized weights with at most four
  exported influences. The generator uses one or two influences per vertex.

## Textures

2048×1024 atlas, with eight finish regions: skin, oxidized iron, leather, red
cloth, wound, bronze, eye and dark details. Original procedural images are
packed in the Blender source and embedded in the GLB.

- `BaseColor.png`: sRGB.
- `Normal.png`: tangent-space OpenGL/+Y microdetail, non-color data.
- `ORM.png`: R = ambient occlusion factor, G = roughness, B = metallic.
  AO is a neutral procedural factor, not a baked contact-occlusion solution.

The Godot project remaps the atlas material through its existing import hook.
`resources/materials/legionary_atlas.tres` uses an asset-only albedo gain of 2
and metallic factor 0.6 to keep oxidized armor readable in the existing night
environment. Arena lighting and SSAO settings are unchanged. The standalone
GLB and packed Blender material retain neutral PBR values for other scenes.

## Animation clips

Keyed at 30 FPS, exported from frame zero with sampled bone transforms.
Actual clip lengths: Idle 2.4 s, Walk 1.0333 s, Run 0.6667 s, Attack 1 s,
Hit 0.3333 s, Death 1.6 s, Emerge 1.3 s.

| Clip | Intended use | Loop |
|---|---|---|
| Idle | subtle breathing, jaw/head motion | yes |
| Walk | opposite limb swing, knee/ankle flex, hip weight shift | yes |
| Run | faster pursuit gait and bent elbows | yes |
| Attack | wind-up/reach, strike around 0.45 s, recovery | no |
| Hit | short torso/head recoil | no |
| Death | forward collapse, held corpse pose | no |
| Emerge | rise from below ground | no |

Looping is a consumer setting because glTF has no standard playback-loop flag.
The start/end poses of Idle/Walk/Run match. The existing game controller enables
their loops and blends between states. Emerge and Death include local Hips
translation; there is no game logic, AI, collision or damage code in the asset.

## Export / reuse

The build uses GLB, selected rig + four meshes, Y-up conversion, skin export,
all action clips, forced animation sampling and up to four influences. Preview
lights/camera are not exported. In Blender, select the rig and meshes, then
export glTF 2.0 with animation/actions and skinning enabled.

Godot can import the GLB directly without Arena Mortis. Unity/Unreal require
their usual glTF import/retarget setup, possible forward-axis conversion and
normal-map/channel configuration. Unity materials may need ORM repacking for
metallic/smoothness conventions. The `.blend` remains the editable master.
In the standalone ZIP the Blender master is under `Sources/`, which has a
`.gdignore` file so a clean Godot installation imports only the ready GLB.
Open its `project.godot` and press F5 for a self-contained animation showcase.

## Quality limits

Facial anatomy, scarring and hand detail are procedurally constructed and
simplified. Gaits have approximate foot planting; armor/cloth contacts can
intersect during some poses. There is no foot IK or cloth simulation. Human
art/animation review remains necessary before calling this a polished library
character. Actual playback and gameplay integration are separately verified.
