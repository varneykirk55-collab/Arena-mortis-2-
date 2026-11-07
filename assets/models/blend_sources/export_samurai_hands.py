# Blender export helper: complete TP body plus independent forearm/hands/cuffs-only FP duplicate.
import bpy,json,sys,math
from pathlib import Path
R=Path(__file__).resolve().parents[3];W=R/'work/hand_geometry_export';W.mkdir(parents=True,exist_ok=True);src=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else Path(__file__).with_name('player_samurai.blend');bpy.ops.wm.open_mainfile(filepath=str(src));r=bpy.data.objects['Armature'];sc=bpy.context.scene
r['grip_note']='Complete TP body plus forearms-only FP mesh; anatomical CC0 MakeHuman hm08 female hands. Existing 54-bone names retained. Per-gun hand contact clips; world RightWeaponSocket unchanged (keep Rob roll180 and existing tilt). See blend_sources/PLAYER_SAMURAI_HANDS.md.'
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
# A complete TP body is authoritative. FP geometry is a separate duplicate, never required in TP.
body=bpy.data.objects['node_0']
uv_name=body.data.uv_layers.active.name
for side in ['Right','Left']:
 ob=bpy.data.objects[side+'_HumanHand'];ob.data.uv_layers.active.name=uv_name
bpy.ops.object.select_all(action='DESELECT')
for ob in [body,bpy.data.objects['Right_HumanHand'],bpy.data.objects['Left_HumanHand']]:ob.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join();body.data.name='Samurai_Complete_TP_Body';body['purpose']='Complete third-person body including arms, sleeves and anatomical hands. Show this alone in TP; hide FP_Arms.'
fp=body.copy();fp.data=body.data.copy();bpy.context.scene.collection.objects.link(fp);fp.name='FP_Arms';fp.data.name='FP_Forearms_Hands_Cuffs';fp['purpose']='First-person only: forearms, hands and cuffs. No upper sleeve or shoulder armour. Hide in third-person to avoid duplicate-surface z fighting.';fp['render_mode']='first_person_only'
# Strict bind-space forearm cylinder: begins 15% distal to the elbow. Upper sleeves/shoulders cannot enter it.
fore={}
for side in ['Left','Right']:
 bone=r.data.bones[side+'ForeArm'];axis=(bone.tail_local-bone.head_local).normalized();groups={g.index for g in fp.vertex_groups if g.name.startswith((side+'ForeArm',side+'Hand'))};fore[side]=(bone.head_local.copy(),axis,bone.length,groups)
keep=[];ts=[];rs=[]
for p in fp.data.polygons:
 skin=fp.data.materials[p.material_index].name.startswith('Samurai_Hands_Skin')
 ok=skin
 if not skin:
  for side,(head,axis,L,groups) in fore.items():
   P=[fp.data.vertices[i] for i in p.vertices];wt=sum(sum(g.weight for g in v.groups if g.group in groups) for v in P)/len(P);T=[(v.co-head).dot(axis)/L for v in P];D=[((v.co-head)-axis*(t*L)).length for v,t in zip(P,T)]
   if wt>.35 and min(T)>=.15 and max(D)<=.075:
    ok=True;ts+=T;rs+=D;break
 keep.append(ok)
bpy.ops.object.select_all(action='DESELECT');fp.select_set(True);bpy.context.view_layer.objects.active=fp;bpy.context.scene.tool_settings.mesh_select_mode=(False,False,True)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
for p,ok in zip(fp.data.polygons,keep):p.select=not ok
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.delete(type='FACE');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.delete_loose(use_verts=True,use_edges=True,use_faces=False);bpy.ops.object.mode_set(mode='OBJECT')
fp['proximal_cut_forearm_fraction']=.15
print('FP_FOREARM_LIMITS',min(ts) if ts else None,max(rs) if rs else None)

r.data.pose_position='POSE';bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
for ob in [r,bpy.data.objects['node_0'],bpy.data.objects['FP_Arms']]:ob.select_set(True)
bpy.context.view_layer.objects.active=r
stats={'bones':len(r.data.bones),'clips':[a.name for a in bpy.data.actions],'meshes':{}}
for n in ['node_0','FP_Arms']:
 ob=bpy.data.objects[n];stats['meshes'][n]={'vertices':len(ob.data.vertices),'triangles':sum(len(p.vertices)-2 for p in ob.data.polygons)}
bpy.ops.export_scene.gltf(filepath=str(R/'assets/models/player_samurai.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_nla_strips=True,export_image_format='AUTO',export_materials='EXPORT',export_skins=True,export_yup=True,export_extras=True)
json.dump(stats,open(W/'export_stats.json','w'),indent=2);print('EXPORT_STATS',stats)
