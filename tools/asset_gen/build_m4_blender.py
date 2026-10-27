"""Stage 1 M4 source. Run with Blender, not system Python.

blender --background --factory-startup --python tools/asset_gen/build_m4_blender.py
Only writes weapon_m4.glb and its editable .blend source. No arena/other assets.
Design coordinates match the old GLB: X right, Y up, -Z muzzle; metres.
Godot material_remap.gd resolves the m4_* material names to .tres resources.
"""
import math
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else ROOT/'assets/models'
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
MATERIALS = {}
GROUPS = {"Body": [], "Magazine": [], "Bolt": []}
GROUP = "Body"


def xyz(p):
    return Vector((p[0], -p[2], p[1]))


def mat(name, color, metallic, rough):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = rough
    MATERIALS[name] = m


mat('m4_receiver', (0.36, 0.39, 0.42), 0.5, 0.58)
mat('m4_rail', (0.23, 0.25, 0.28), 0.45, 0.63)
mat('m4_polymer', (0.25, 0.265, 0.22), 0.0, 0.95)
mat('m4_steel', (0.34, 0.36, 0.39), 0.65, 0.5)
mat('m4_magazine', (0.43, 0.44, 0.39), 0.55, 0.68)
mat('m4_recess', (0.025, 0.029, 0.033), 0.05, 0.75)
mat('m4_markings', (0.68, 0.69, 0.60), 0.15, 0.6)
mat('gun_lens', (0.22, 0.48, 0.48), 0.0, 0.08)
mat('glow_red', (1.0, 0.03, 0.008), 0.0, 0.3)


def finish(obj, name, material, bevel=0.0, smooth=False):
    obj.name = name
    obj.data.materials.append(MATERIALS[material])
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new('Machined edge radius', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    mod = obj.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    mod.keep_sharp = True
    mod.weight = 50
    bpy.ops.object.modifier_apply(modifier=mod.name)
    GROUPS[GROUP].append(obj)
    return obj


def box(name, center, size, material, bevel=0.001):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz(center))
    obj = bpy.context.object
    obj.dimensions = (size[0], size[2], size[1])
    return finish(obj, name, material, bevel)


def profile(name, zy, width, material, bevel=0.001, x=0):
    verts = [xyz((x + sx * width / 2, y, z)) for sx in (-1, 1) for z, y in zy]
    n = len(zy)
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    return finish(obj, name, material, bevel)


def cylinder(name, a, b, radius, material, vertices=24, bevel=0.0005):
    a, b = xyz(a), xyz(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=(b - a).length, location=(a + b) / 2)
    obj = bpy.context.object
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = (b - a).to_track_quat('Z', 'Y')
    return finish(obj, name, material, bevel, True)


def ring(name, center, outer, inner, depth, material, segments=32):
    # True hollow cylinder: the flash hider and optic do not end in solid caps.
    x, y, z = center
    verts = []
    for zz, rr in ((z-depth/2, outer), (z-depth/2, inner), (z+depth/2, outer), (z+depth/2, inner)):
        verts += [xyz((x+rr*math.cos(i*math.tau/segments), y+rr*math.sin(i*math.tau/segments), zz)) for i in range(segments)]
    faces = []
    for a, b in ((0,1),(2,0),(1,3),(3,2)):
        for i in range(segments):
            j = (i+1) % segments
            faces.append((a*segments+i,a*segments+j,b*segments+j,b*segments+i))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
    return finish(obj, name, material, 0.00035, True)


# Forged receiver silhouette: raised upper, forward magwell and separate grip.
profile('Forged upper', [(0.085,0.012),(0.085,0.037),(0.067,0.049),(-0.135,0.049),(-0.159,0.038),(-0.159,0.009),(-0.075,0.005)], .038, 'm4_receiver', .002)
profile('Lower receiver', [(0.072,.012),(-.128,.012),(-.14,-.024),(-.126,-.045),(-.065,-.045),(-.058,-.018),(.05,-.018),(.072,-.008)], .034, 'm4_receiver', .0018)
profile('Magazine well lip', [(-.064,-.031),(-.134,-.031),(-.14,-.044),(-.065,-.047)], .039, 'm4_receiver', .001)
profile('Angled pistol grip', [(.043,-.012),(.007,-.013),(.025,-.09),(.05,-.112),(.079,-.103),(.066,-.061)], .03, 'm4_polymer', .003)
for i in range(6):
    for sx in (-1, 1):
        box('Grip traction', (sx*.0156,-.048-i*.008,.04+i*.0026), (.0018,.0018,.022), 'm4_recess', .0003)
# Open trigger guard (separate rails instead of a filled slab).
profile('Trigger guard', [(.014,-.018),(.014,-.041),(.001,-.052),(-.048,-.052),(-.062,-.035),(-.058,-.028),(-.05,-.044),(.001,-.044),(.006,-.037),(.006,-.018)], .009, 'm4_receiver', .001)
profile('Curved trigger', [(-.008,-.017),(-.018,-.018),(-.027,-.031),(-.023,-.039),(-.018,-.038),(-.021,-.031)], .005, 'm4_steel', .0007)
# Rear buffer, castle nut, telescoping stock with a real open triangular strut.
cylinder('Buffer tube', (0,.025,.07),(0,.025,.285),.014,'m4_steel')
ring('Castle nut',(0,.025,.105),.018,.014,.012,'m4_rail',24)
profile('Stock cheek rest', [(.15,.043),(.292,.043),(.31,.029),(.31,-.002),(.15,-.002)], .042, 'm4_polymer', .003)
profile('Stock lower strut', [(.16,-.005),(.18,-.022),(.286,-.066),(.307,-.065),(.307,-.052),(.19,-.012)], .025, 'm4_polymer', .002)
box('Stock butt',(0,-.018,.31),(.044,.12,.018),'m4_polymer',.003)
box('Rubber butt pad',(0,-.018,.323),(.045,.119,.01),'m4_recess',.002)
for i in range(9):
    box('Butt pad rib',(0,-.068+i*.012,.329),(.037,.003,.002),'m4_polymer',.0005)
box('Stock adjustment latch',(0,-.029,.185),(.025,.009,.051),'m4_rail',.001)
# Barrel and barrel nut, with stepped diameters and gas tube.
cylinder('Barrel',(0,.022,-.145),(0,.022,-.532),.0085,'m4_steel',32)
ring('Barrel nut',(0,.022,-.156),.026,.012,.018,'m4_rail')
cylinder('Gas tube',(0,.043,-.17),(0,.043,-.434),.002,'m4_steel',12)
cylinder('Gas block',(0,.022,-.429),(0,.022,-.448),.012,'m4_rail')
ring('Muzzle shoulder',(0,.022,-.506),.0115,.007,.011,'m4_steel')
ring('Flash hider',(0,.022,-.535),.012,.007,.045,'m4_rail')
for i in range(5):
    a=i*math.tau/5
    cylinder('Flash hider slot',(math.cos(a)*.0122,.022+math.sin(a)*.0122,-.522),(math.cos(a)*.0122,.022+math.sin(a)*.0122,-.547),.0021,'m4_recess',8,0)
# Slim free-float quad rail; contrasting flat panels, recessed vents and bolts.
box('Handguard core',(0,.022,-.285),(.046,.046,.238),'m4_rail',.004)
for sx in (-1,1):
    box('Rail backing',(sx*.025,.022,-.282),(.006,.031,.224),'m4_receiver',.001)
    for i in range(13):
        z=-.184-i*.016
        box('Side rail tooth',(sx*.029,.022,z),(.006,.036,.006),'m4_rail',.0006)
    # Ribbed insulating panels over the central rail, narrower than old blocks.
    box('Heat shield',(sx*.033,.022,-.29),(.008,.026,.122),'m4_polymer',.002)
    for i in range(11):
        box('Heat shield rib',(sx*.0375,.022,-.238-i*.01),(.002,.025,.003),'m4_polymer',.0005)
    for z in (-.185,-.384):
        cylinder('Rail fastener',(sx*.027,.022,z),(sx*.032,.022,z),.003,'m4_steel',12)
for z in [-.18-i*.014 for i in range(16)]:
    box('Lower rail tooth',(0,-.006,z),(.028,.006,.006),'m4_rail',.0006)
# Continuous top rail, thin dovetail teeth and relief channel.
box('Top rail bed',(0,.05,-.15),(.024,.009,.48),'m4_rail',.001)
for i in range(32):
    box('Picatinny lug',(0,.057,.079-i*.0148),(.031,.006,.007),'m4_receiver',.0007)
box('Rail center channel',(0,.0603,-.16),(.006,.0006,.47),'m4_recess',.0001)
# Ejection port recessed bed, visible silver bolt carrier and hinged cover.
box('Port cavity',(.0198,.029,-.029),(.001,.018,.066),'m4_recess',.001)
box('Port carrier',(.0205,.03,-.026),(.001,.009,.045),'m4_steel',.0005)
box('Dust cover',(.023,.012,-.03),(.003,.012,.065),'m4_receiver',.001)
cylinder('Cover hinge',(.023,.019,.006),(.023,.019,-.066),.002,'m4_steel',12)
cylinder('Forward assist',(.019,.034,.046),(.039,.043,.067),.006,'m4_receiver',20)
cylinder('Assist serrated cap',(.037,.042,.065),(.041,.044,.069),.007,'m4_rail',20)
box('Case deflector',(.023,.031,.015),(.012,.019,.013),'m4_receiver',.002)
box('Charging handle',(0,.046,.087),(.061,.009,.014),'m4_rail',.001)
for sx in (-1,1):
    for z,y in ((.052,.003),(-.126,-.012)):
        cylinder('Receiver pin',(sx*.017,y,z),(sx*.019,y,z),.003,'m4_steel',16)
    cylinder('Selector pivot',(sx*.017,-.005,.028),(sx*.021,-.005,.028),.004,'m4_steel',16)
    box('Selector lever',(sx*.021,-.009,.019),(.003,.005,.023),'m4_rail',.0008)
    # Restrained witness markings; no faux logos.
    for z in (.012,.028,.044):
        box('Selector index',(sx*.018,-.016,z),(.0007,.0015,.003),'m4_markings',.0001)
    for i in range(3):
        box('Receiver engraving',(sx*.0177,-.003-i*.004,-.086),(.0006,.001,.023-i*.004),'m4_markings',.0001)
# Low-profile reflex sight: open, chamfered hood; clear sightline at Y=.091.
box('Optic mounting shoe',(0,.064,.025),(.034,.009,.052),'m4_rail',.001)
box('Optic chassis',(0,.071,.021),(.041,.009,.05),'m4_receiver',.001)
for sx in (-1,1):
    profile('Optic hood cheek', [(.039,.074),(.039,.11),(.034,.12),(.019,.12),(.014,.111),(.014,.074)], .0045, 'm4_receiver', .001, sx*.022)
box('Optic hood bridge',(0,.121,.027),(.043,.0045,.025),'m4_receiver',.001)
box('Glass',(0,.094,.015),(.037,.037,.0006),'gun_lens',0)
box('Reticle',(0,.091,.0143),(.0011,.0011,.0003),'glow_red',.0001)
cylinder('Brightness dial',(.021,.083,.024),(.03,.083,.024),.008,'m4_rail',24)
for sx in (-1,1):
    cylinder('Mount clamp bolt',(sx*.018,.064,.025),(sx*.022,.064,.025),.003,'m4_steel',12)
# Folded front backup sight avoids obscuring the red dot.
box('Folded sight base',(0,.065,-.386),(.029,.01,.035),'m4_rail',.001)
box('Folded sight leaf',(0,.071,-.385),(.016,.004,.026),'m4_steel',.0007)

# Separate curved stamped STANAG, retained as the procedural reload target.
GROUP = 'Magazine'
profile('Curved STANAG', [(-.067,-.027),(-.128,-.027),(-.132,-.095),(-.155,-.178),(-.148,-.19),(-.094,-.181),(-.078,-.105)], .025, 'm4_magazine', .0017)
profile('Magazine base plate',[(-.096,-.177),(-.151,-.186),(-.157,-.18),(-.16,-.191),(-.098,-.194),(-.091,-.187)], .03, 'm4_rail', .001)
for sx in (-1,1):
    for i in range(3):
        z=-.085-i*.014
        profile('Pressed magazine flute', [(z,-.054),(z-.004,-.055),(z-.01,-.11),(z-.026,-.167),(z-.022,-.168),(z-.006,-.111)], .0015, 'm4_rail', .0004, sx*.0128)
GROUP = 'Bolt'
box('Moving bolt handle',(.021,.03,-.01),(.004,.009,.024),'m4_steel',.001)

# Consolidate static parts by material to keep draw count bounded.
root = bpy.data.objects.new('M4', None)
bpy.context.collection.objects.link(root)
for group, objects in GROUPS.items():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = 'M4_Body' if group == 'Body' else group
    bpy.context.scene.cursor.location = (0,0,0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    # Joining preserves duplicate slots; collapse them before glTF export.
    slots = list(obj.data.materials)
    unique = list(dict.fromkeys(slots))
    remap = {i:unique.index(m) for i,m in enumerate(slots)}
    indices = [remap[p.material_index] for p in obj.data.polygons]
    obj.data.materials.clear()
    for m in unique: obj.data.materials.append(m)
    for p,i in zip(obj.data.polygons,indices): p.material_index=i
    obj.parent = root

for name, pos in [('Muzzle',(0,.022,-.56)), ('RightHand',(0,-.016,.022)), ('LeftHand',(0,.022,-.29)), ('Sight',(0,.092,.03))]:
    obj=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(obj)
    obj.location=xyz(pos)
    if name=='RightHand': obj.rotation_euler.x=math.radians(-15)
    obj.parent=root

bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1
# A subtle shared microfinish controls roughness, rather than painting bright
# noise into the metal. This is a generated texture, not downloaded artwork.
rng = np.random.default_rng(404)
grain = np.clip(rng.normal(.83,.035,(256,256)),.70,.96).astype(np.float32)
pixels = np.ones((256,256,4),dtype=np.float32)
pixels[:,:,:3] = grain[:,:,None]
finish_image = bpy.data.images.new('M4 microfinish',width=256,height=256)
finish_image.colorspace_settings.name='Non-Color'
finish_image.pixels.foreach_set(pixels.ravel())
finish_image.filepath_raw=str(ROOT/'assets/textures/m4_finish.png')
finish_image.file_format='PNG'
finish_image.save()
for name,m in MATERIALS.items():
    if not name.startswith('m4_'): continue
    c=m.diffuse_color
    bsdf=m.node_tree.nodes.get('Principled BSDF')
    metal=bsdf.inputs['Metallic'].default_value
    rough=bsdf.inputs['Roughness'].default_value
    use_finish=name not in ('m4_recess','m4_markings')
    text='[gd_resource type="StandardMaterial3D" load_steps=%d format=3]\n\n' % (2 if use_finish else 1)
    if use_finish: text+='[ext_resource type="Texture2D" path="res://assets/textures/m4_finish.png" id="1"]\n\n'
    text+='[resource]\nresource_name = "%s"\nalbedo_color = Color(%s, %s, %s, 1)\nmetallic = %s\nroughness = %s\n' % (name,c[0],c[1],c[2],metal,rough)
    if use_finish: text+='roughness_texture = ExtResource("1")\nroughness_texture_channel = 0\nuv1_triplanar = true\nuv1_scale = Vector3(16, 16, 16)\ntexture_filter = 5\n'
    (ROOT/'resources/materials'/f'{name}.tres').write_text(text)
source=ROOT/'assets'/'sources'/'m4_stage1.blend'
source.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(source))
bpy.ops.export_scene.gltf(filepath=str(OUT/'weapon_m4.glb'), export_format='GLB', export_animations=False, export_cameras=False, export_lights=False, export_yup=True)
triangles=sum(len(p.vertices)-2 for o in GROUPS for ob in bpy.data.objects if ob.type=='MESH' and ob.name==('M4_Body' if o=='Body' else o) for p in ob.data.polygons)
print('M4_BUILD_DONE triangles=',triangles,' Blender=',bpy.app.version_string)
