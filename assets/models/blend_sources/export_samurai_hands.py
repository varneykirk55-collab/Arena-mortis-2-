# Blender export helper: evaluated hand budget, four skin influences, FP_Arms face partition.
import bpy,json,sys,math
from pathlib import Path
R=Path(__file__).resolve().parents[3];W=R/'work/hand_geometry_export';W.mkdir(parents=True,exist_ok=True);src=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else Path(__file__).with_name('player_samurai.blend');bpy.ops.wm.open_mainfile(filepath=str(src));r=bpy.data.objects['Armature'];sc=bpy.context.scene
r['grip_note']='Anatomical CC0 MakeHuman hm08 female hand grafts, independent fingers and nails. Existing 54-bone names retained. Per-gun hand contact clips; world RightWeaponSocket unchanged (keep Rob roll180 and existing tilt). See blend_sources/PLAYER_SAMURAI_HANDS.md.'
r['hand_mesh_source']='MakeHuman hm08 CC0 (2020 dedication in base.obj), female young macro. Separate thumb and four fingers, anatomical pads/knuckles. Original hand mitten vertices removed.'
for s in ['Right','Left']:
 ob=bpy.data.objects[s+'_HumanHand'];ob['source']='MakeHuman hm08 CC0; source detail and limitations in blend_sources/PLAYER_SAMURAI_HANDS.md.'
r.animation_data.action=bpy.data.actions['Idle'];sc.frame_set(0);bpy.context.view_layer.update();bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(R/'assets/models/blend_sources/player_samurai.blend'))
# Evaluate the budget modifier once in bind pose. Preserve editable quads + budget modifier in the saved source.
r.data.pose_position='REST'
for s in ['Right','Left']:
 ob=bpy.data.objects[s+'_HumanHand'];bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier='GameHandBudget')
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.ops.object.mode_set(mode='WEIGHT_PAINT');bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL',limit=4);bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL',lock_active=False);bpy.ops.object.mode_set(mode='OBJECT')
# Partition the original body faces, without changing their positions, weights, UVs or materials.
body=bpy.data.objects['node_0'];bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.context.scene.tool_settings.mesh_select_mode=(False,False,True)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
armids={g.index for g in body.vertex_groups if g.name.startswith(('LeftArm','LeftForeArm','LeftHand','LeftShoulder','RightArm','RightForeArm','RightHand','RightShoulder'))}
aw={v.index:sum(g.weight for g in v.groups if g.group in armids) for v in body.data.vertices}
selected=0
for p in body.data.polygons:
 vals=[aw[i] for i in p.vertices];p.select=sum(vals)/len(vals)>.35
 if p.select:selected+=len(p.vertices)-2
before=set(bpy.context.scene.objects);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.separate(type='SELECTED');bpy.ops.object.mode_set(mode='OBJECT')
parts=[o for o in bpy.context.scene.objects if o not in before];assert len(parts)==1,parts
fp=parts[0];fp.name='FP_Arms';fp.data.name='FP_Arms_Hands_Sleeves';fp['purpose']='Arms, sleeves and anatomical hands, using the same skeleton and 15 clips. Hide node_0 for first-person.'
bpy.ops.object.select_all(action='DESELECT')
for ob in [fp,bpy.data.objects['Right_HumanHand'],bpy.data.objects['Left_HumanHand']]:ob.select_set(True)
bpy.context.view_layer.objects.active=fp;bpy.ops.object.join()
print('FP_ARM_PARTITION_BODY_TRIANGLES',selected)

r.data.pose_position='POSE';bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
for ob in [r,bpy.data.objects['node_0'],bpy.data.objects['FP_Arms']]:ob.select_set(True)
bpy.context.view_layer.objects.active=r
stats={'bones':len(r.data.bones),'clips':[a.name for a in bpy.data.actions],'meshes':{}}
for n in ['node_0','FP_Arms']:
 ob=bpy.data.objects[n];stats['meshes'][n]={'vertices':len(ob.data.vertices),'triangles':sum(len(p.vertices)-2 for p in ob.data.polygons)}
bpy.ops.export_scene.gltf(filepath=str(R/'assets/models/player_samurai.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_nla_strips=True,export_image_format='AUTO',export_materials='EXPORT',export_skins=True,export_yup=True,export_extras=True)
json.dump(stats,open(W/'export_stats.json','w'),indent=2);print('EXPORT_STATS',stats)
