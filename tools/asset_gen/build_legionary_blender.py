"""Reusable original legionary character, authored/rigged/animated with Blender.
Run: blender --background --factory-startup --python tools/asset_gen/build_legionary_blender.py
Metres. Design axes X right / Y up / Z front; Blender X right / -Y front / Z up.
No game code or behavior is embedded in the asset. One atlas; four skinned meshes.
"""
import math
from pathlib import Path
from collections import defaultdict
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'assets/sources/legionary_stage1'
TEX = ROOT/'assets/textures/legionary'
SOURCE.mkdir(parents=True,exist_ok=True)
TEX.mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def xyz(p): return Vector((p[0],-p[2],p[1]))
DATA=defaultdict(lambda:{'v':[],'f':[],'uv':[],'w':[]})
GROUP='Skin_Anatomy'
def add(v,f,uv,tile,w):
    d=DATA[GROUP]; off=len(d['v'])
    # Shorter exposed neck; keep the named Head joint at the gameplay contract.
    cranial=isinstance(w,str) and w in ('Head','Jaw')
    d['v'] += [tuple(xyz(np.array(p)+np.array([0,-.027,0]) if cranial else p)) for p in v]
    d['f'] += [tuple(i+off for i in face) for face in f]
    col,row=tile%4,tile//4
    d['uv'] += [((col+.025+.95*u)/4,(row+.025+.95*v)/2) for u,v in uv]
    d['w'] += [w(p) if callable(w) else {w:1.0} for p in v]

def ellipsoid(center,radius,tile,bone,seg=20,rings=12,deform=None):
    v=[];uv=[];f=[]
    for j in range(rings+1):
        a=-math.pi/2+math.pi*j/rings
        for i in range(seg+1):
            t=i*math.tau/seg
            p=np.array(center)+np.array([radius[0]*math.cos(a)*math.cos(t),radius[1]*math.sin(a),radius[2]*math.cos(a)*math.sin(t)])
            if deform:p=deform(p,t,a)
            v.append(p);uv.append((i/seg,j/rings))
    for j in range(rings):
        for i in range(seg):
            k=j*(seg+1)+i;f.append((k,k+1,k+seg+2,k+seg+1))
    add(v,f,uv,tile,bone)

def loft(points,radii,tile,weights,seg=16,caps=True):
    points=np.array(points,float);v=[];uv=[];f=[]
    for j,p in enumerate(points):
        tangent=points[min(j+1,len(points)-1)]-points[max(0,j-1)]
        tangent/=np.linalg.norm(tangent)
        side=np.cross(tangent,[0,0,1])
        if np.linalg.norm(side)<.01:side=np.cross(tangent,[0,1,0])
        side/=np.linalg.norm(side);front=np.cross(side,tangent);front/=np.linalg.norm(front)
        rx,rz=radii[j] if hasattr(radii[j],'__len__') else (radii[j],radii[j])
        for i in range(seg+1):
            a=i*math.tau/seg
            v.append(p+side*math.cos(a)*rx+front*math.sin(a)*rz);uv.append((i/seg,j/(len(points)-1)))
    for j in range(len(points)-1):
        for i in range(seg):
            k=j*(seg+1)+i;f.append((k,k+1,k+seg+2,k+seg+1))
    if caps:f += [tuple(range(seg-1,-1,-1)),tuple((len(points)-1)*(seg+1)+i for i in range(seg))]
    add(v,f,uv,tile,weights)

def tube(points,r,tile,bone,seg=8):loft(points,[r]*len(points),tile,bone,seg)

def shell(y0,y1,rx,rz,tile,bone,start=0,end=math.tau,seg=48,thick=.003,flare=0):
    v=[];uv=[];f=[]
    # Rounded thickness transition gives the lames real rolled metal edges.
    for y,dr in [(y0,0),(y0+.0015,.001),(y1-.0015,flare+.001),(y1,flare),(y1,flare-thick),(y0,-thick)]:
        for i in range(seg+1):
            a=start+(end-start)*i/seg
            v.append(((rx+dr)*math.cos(a),y,(rz+dr)*math.sin(a)));uv.append((i/seg,(y-y0)/(y1-y0)))
    for j in range(6):
        for i in range(seg):
            a=j*(seg+1)+i;b=((j+1)%6)*(seg+1)+i
            f.append((a,a+1,b+1,b))
    if end-start<6.28:
        for i in (0,seg): f.append(tuple(j*(seg+1)+i for j in range(6)))
    add(v,f,uv,tile,bone)

def ribbon(points,width,tile,bone,thick=.002):
    pts=np.array(points,float);v=[];uv=[];f=[]
    for j,p in enumerate(pts):
        t=pts[min(j+1,len(pts)-1)]-pts[max(0,j-1)]
        side=np.cross(t,[0,0,1]);side/=np.linalg.norm(side)+1e-9
        for dep,sgn in ((0,-1),(0,1),(-thick,-1),(-thick,1)):
            v.append(p+side*width/2*sgn+np.array([0,0,dep]));uv.append((0 if sgn<0 else 1,j/(len(pts)-1)))
    for j in range(len(pts)-1):
        k=j*4
        f += [(k,k+1,k+5,k+4),(k+2,k+6,k+7,k+3),(k,k+4,k+6,k+2),(k+1,k+3,k+7,k+5)]
    f += [(0,2,3,1),tuple(range((len(pts)-1)*4,len(pts)*4))]
    add(v,f,uv,tile,bone)

# Humanoid hierarchy, including articulated jaw, digits and toes.
BONES={}
def bone(name,head,tail,parent=None): BONES[name]=(np.array(head,float),np.array(tail,float),parent)
bone('Hips',(0,.98,0),(0,1.10,0))
bone('Spine',(0,1.10,0),(0,1.29,0),'Hips')
bone('Chest',(0,1.29,0),(0,1.48,0),'Spine')
bone('Neck',(0,1.48,0),(0,1.60,0),'Chest')
bone('Head',(0,1.60,.01),(0,1.82,.01),'Neck')
bone('Jaw',(0,1.65,.025),(0,1.605,.075),'Head')
for s,sign in [('L',1),('R',-1)]:
    shoulder=(sign*.205,1.46,0);elbow=(sign*.32,1.18,.005);wrist=(sign*.385,.92,.045)
    bone('Clavicle.'+s,(0,1.44,0),shoulder,'Chest')
    bone('UpperArm.'+s,shoulder,elbow,'Clavicle.'+s)
    bone('Forearm.'+s,elbow,wrist,'UpperArm.'+s)
    bone('Hand.'+s,wrist,(sign*.399,.84,.059),'Forearm.'+s)
    bone('Thigh.'+s,(sign*.094,.97,0),(sign*.105,.53,.015),'Hips')
    bone('Shin.'+s,(sign*.105,.53,.015),(sign*.105,.115,-.015),'Thigh.'+s)
    bone('Foot.'+s,(sign*.105,.115,-.015),(sign*.105,.05,.16),'Shin.'+s)
    bone('Toe.'+s,(sign*.105,.05,.12),(sign*.105,.045,.22),'Foot.'+s)

def chainweights(names):
    def fn(p):
        p=np.array(p);scores=[]
        for name in names:
            a,b,_=BONES[name];d=b-a;t=np.clip(np.dot(p-a,d)/np.dot(d,d),0,1)
            scores.append((np.linalg.norm(p-a-t*d),name))
        scores.sort();vals=[(n,1/(d+.014)**4) for d,n in scores[:2]];total=sum(v for n,v in vals)
        return {n:v/total for n,v in vals if v/total>.015}
    return fn

# Continuous tapered skin torso and limbs, not disconnected block joints.
loft([(0,.86,0),(0,.96,0),(0,1.07,0),(0,1.20,.0),(0,1.33,0),(0,1.43,0),(0,1.48,0),(0,1.53,0)],
     [(.14,.095),(.156,.105),(.13,.084),(.147,.095),(.182,.108),(.19,.10),(.13,.075),(.052,.048)],0,chainweights(['Hips','Spine','Chest','Neck']),24)
loft([(0,1.47,0),(0,1.54,.002),(0,1.60,.007)],[.053,.046,.05],0,chainweights(['Neck','Head']),20)

for s,sign in [('L',1),('R',-1)]:
    names=['UpperArm.'+s,'Forearm.'+s,'Hand.'+s]
    loft([(sign*.205,1.46,0),(sign*.24,1.39,0),(sign*.292,1.27,.003),(sign*.32,1.19,.005),(sign*.325,1.16,.012),(sign*.35,1.08,.025),(sign*.378,.96,.04),(sign*.385,.92,.045)],
         [(.052,.051),(.051,.048),(.038,.039),(.033,.034),(.034,.035),(.04,.037),(.027,.025),(.024,.022)],0,chainweights(names),16)
    loft([(sign*.385,.935,.045),(sign*.391,.90,.054),(sign*.4,.858,.06),(sign*.402,.835,.062)],[(.024,.019),(.032,.02),(.035,.017),(.029,.015)],0,chainweights(['Forearm.'+s,'Hand.'+s]),16)
    # Four individually modelled, three-joint fingers; slightly unequal lengths.
    for fi,(offset,length) in enumerate([(-.026,.066),(-.009,.08),(.009,.076),(.025,.061)]):
        base=np.array([sign*(.4+offset),.846,.062]);parent='Hand.'+s
        pts=[base,base+np.array([sign*.004,-length*.42,.009]),base+np.array([sign*.004,-length*.75,.022]),base+np.array([sign*.002,-length,.034])]
        ns=[]
        for j in range(3):
            name=f'Finger{fi+1}_{j+1}.{s}';bone(name,pts[j],pts[j+1],parent);ns.append(name);parent=name
        loft(pts,[.008,.0085,.007,.0045],0,chainweights(ns),10)
        ellipsoid(pts[-1]+np.array([0,.004,.003]),(.005,.009,.0015),7,ns[-1],8,6)
    thumb=[(sign*.37,.901,.064),(sign*.351,.878,.083),(sign*.347,.851,.104),(sign*.355,.836,.111)]
    ns=[];parent='Hand.'+s
    for j in range(3):
        name=f'Thumb{j+1}.{s}';bone(name,thumb[j],thumb[j+1],parent);parent=name;ns.append(name)
    loft(thumb,[.012,.011,.009,.006],0,chainweights(ns),10)
    # Thigh-to-calf topology includes extra supporting rings at each knee.
    loft([(sign*.094,.96,0),(sign*.099,.87,0),(sign*.103,.70,.005),(sign*.105,.56,.014),(sign*.105,.525,.018),(sign*.105,.49,.02),(sign*.105,.39,-.005),(sign*.105,.24,-.018),(sign*.105,.12,-.015)],
         [(.073,.078),(.075,.076),(.060,.063),(.043,.046),(.043,.047),(.042,.043),(.047,.052),(.034,.035),(.024,.029)],0,chainweights(['Thigh.'+s,'Shin.'+s,'Foot.'+s]),20)
    loft([(sign*.105,.085,-.07),(sign*.105,.065,-.03),(sign*.105,.056,.065),(sign*.105,.045,.16)],[(.03,.035),(.034,.043),(.044,.031),(.042,.022)],0,'Foot.'+s,16)
    for ti in range(5):
        x=sign*(.07+ti*.017);length=.033-ti*.003
        ellipsoid((x,.043,.17+length/2),(.009,.016,length),0,'Toe.'+s,10,8)
        ellipsoid((x,.057,.183+length/2),(.006,.0015,.009),7,'Toe.'+s,8,6)

# Face sculpt surface: sockets, cheeks, jaw and asymmetrical temporal wasting.
def face(p,t,a):
    x,y,z=p
    if z>0:
        gauss=lambda xx,yy,sx,sy:math.exp(-((x-xx)/sx)**2-((y-yy)/sy)**2)
        z-=.020*(gauss(-.033,1.728,.024,.019)+gauss(.033,1.728,.024,.019))
        z+=.014*(gauss(-.05,1.695,.022,.018)+gauss(.05,1.695,.022,.018))
        z-=.011*gauss(-.049,1.662,.03,.025)
        z+=.010*gauss(.0,1.606,.035,.017)
        x*=1-.18*math.exp(-((y-1.62)/.028)**2)
    return np.array([x,y,z])
ellipsoid((0,1.708,.004),(.077,.115,.083),0,'Head',48,32,face)
# Jaw has an actual hinge bone with lower teeth/lip, for breathing and attack.
ellipsoid((0,1.626,.038),(.057,.031,.05),0,'Jaw',24,12)
for sx in (-1,1):
    # Sunken orbit, milky eye, restrained iris and pupil (no emission).
    ellipsoid((sx*.032,1.727,.061),(.014,.006,.004),7,'Head',20,12)
    ellipsoid((sx*.032,1.728,.064),(.010,.0038,.003),0,'Head',20,12)
    ellipsoid((sx*.032,1.728,.067),(.0026,.0029,.0008),0,'Head',12,8)
    ellipsoid((sx*.032,1.728,.0677),(.0011,.0018,.0004),7,'Head',10,6)
    tube([(sx*.012,1.743,.070),(sx*.03,1.747,.071),(sx*.052,1.741,.061)],.005,0,'Head',10)
    tube([(sx*.02,1.728,.065),(sx*.032,1.734,.066),(sx*.043,1.728,.064)],.0025,0,'Head',8)
    tube([(sx*.02,1.727,.065),(sx*.032,1.723,.066),(sx*.043,1.727,.064)],.002,0,'Head',8)
    # Helix and antihelix of the ears; helmet cheek guards leave the rim visible.
    ear=[(sx*.079,1.694,.0),(sx*.088,1.705,-.006),(sx*.09,1.725,-.005),(sx*.085,1.74,.002),(sx*.078,1.729,.01),(sx*.077,1.706,.009)]
    tube(ear,.005,0,'Head',8)
    tube([(sx*.081,1.706,.004),(sx*.083,1.72,.004),(sx*.079,1.728,.006)],.0025,0,'Head',8)
# Tapered bridge and nostril wings, not a separate spherical nose.
loft([(0,1.754,.069),(0,1.729,.081),(0,1.702,.103),(0,1.691,.104)],[ (.008,.005),(.008,.007),(.012,.009),(.010,.005)],0,'Head',12)
for sx in (-1,1):
    ellipsoid((sx*.012,1.692,.091),(.008,.006,.008),0,'Head',12,8)
    ellipsoid((sx*.012,1.688,.097),(.004,.002,.003),7,'Head',10,6)
mouth=[(-.034,1.651,.074),(-.018,1.65,.085),(0,1.647,.091),(.017,1.651,.084),(.031,1.653,.075)]
tube(mouth,.0018,7,'Head',8)
tube([(x,y-.0035,z+.0005) for x,y,z in mouth],.002,0,'Jaw',8)
for i in range(6):
    ellipsoid((-.02+i*.008,1.649,.085-abs(i-2.5)*.002),(.0025,.0015,.001),0,'Head',8,6)
# Small irregular wound margins: left cheek and one forearm, not gore props.
ellipsoid((-.056,1.67,.067),(.009,.015,.001),4,'Head',17,10)
tube([(-.061,1.681,.066),(-.059,1.674,.069),(-.060,1.663,.068)],.0011,4,'Head',8)
ellipsoid((.355,1.05,.059),(.017,.039,.002),4,'Forearm.L',16,10)

# Tunic with a pleated, irregular hem. Upper garment peeks between lames.
GROUP='Tunic_Cloth'
def tunic():
    v=[];uv=[];f=[];seg=64
    for j,(y,rx,rz) in enumerate([(.79,.205,.133),(.84,.195,.128),(.98,.18,.12),(1.06,.145,.099),(1.27,.172,.107),(1.44,.194,.105)]):
        for i in range(seg+1):
            a=i*math.tau/seg;pleat=.0045*math.cos(a*16)
            yy=y+(.009*math.sin(a*9)+.005*math.cos(a*17) if j==0 else 0)
            v.append(((rx+pleat)*math.cos(a),yy,(rz+pleat)*math.sin(a)));uv.append((i/seg,j/5))
    for j in range(5):
        for i in range(seg):
            k=j*(seg+1)+i;f.append((k,k+1,k+seg+2,k+seg+1))
    def weights(p):
        if p[1]>.97:return chainweights(['Hips','Spine','Chest'])(p)
        thigh='Thigh.L' if p[0]>0 else 'Thigh.R'
        blend=.32*max(0,1-(p[1]-.79)/.18)
        return {'Hips':1-blend,thigh:blend}
    add(v,f,uv,3,weights)
tunic()
for s,sign in [('L',1),('R',-1)]:
    loft([(sign*.2,1.45,0),(sign*.235,1.39,0),(sign*.265,1.33,0)],[.059,.058,.052],3,'UpperArm.'+s,20)
    # Cuff stitching along the tunic sleeve.
    for k in range(8):
        a=k*math.tau/8
        ellipsoid((sign*.265+.048*math.cos(a),1.33,.049*math.sin(a)),(.0018,.004,.0018),2,'UpperArm.'+s,6,4)

GROUP='Lorica_Helmet'
# Lorica segmentata: layered body lames, segmented shoulder guards, metal latches.
for i in range(8):
    y=1.065+i*.042
    rx=.161+(.028*max(0,min(1,(y-1.12)/.24)))
    rz=.105+.015*max(0,(y-1.12)/.24)
    shell(y,y+.048,rx,rz,1,'Spine' if y<1.27 else 'Chest',seg=48)
    if i%2==0:
        for x in (-.052,.052):
            ellipsoid((x,y+.023,rz+.001),(.011,.011,.003),5,'Spine' if y<1.27 else 'Chest',12,8)
            for dx in (-.007,.007):ellipsoid((x+dx,y+.023,rz+.004),(.002,.002,.002),1,'Spine' if y<1.27 else 'Chest',8,6)
# Breast/upper-back plates and armoured shoulders, each rigidly weighted.
shell(1.397,1.47,.177,.113,1,'Chest',seg=48,flare=-.015)
for s,sign in [('L',1),('R',-1)]:
    for j in range(4):
        y=1.485-j*.036;x=sign*(.19+j*.016)
        # Bent saddle plates over the shoulders, real inner/outer surfaces.
        v=[];uv=[];f=[];seg=20
        for depth,dy in ((.0,0),(.003,-.003)):
            for zz in (-.074,.074):
                for i in range(seg+1):
                    a=-1.35+2.7*i/seg
                    v.append((x+sign*(.065-depth)*math.sin(a),y+.027*math.cos(a)+dy,zz));uv.append((i/seg,(zz+.074)/.148))
        for band in (0,2):
            for i in range(seg):f.append((band*(seg+1)+i,band*(seg+1)+i+1,(band+1)*(seg+1)+i+1,(band+1)*(seg+1)+i))
        add(v,f,uv,1,'Chest' if j==0 else 'UpperArm.'+s)
        for z in (-.065,.065):ellipsoid((x,y+.025,z),(.0035,.0035,.0035),5,'Chest' if j==0 else 'UpperArm.'+s,10,6)
# Imperial Gallic helmet dome: tailored profile rather than a hemisphere primitive.
v=[];uv=[];f=[];seg=48
for j,(y,rx,rz) in enumerate([(1.736,.082,.083),(1.766,.088,.089),(1.805,.079,.079),(1.835,.057,.06),(1.85,.025,.026),(1.854,.002,.002)]):
    for i in range(seg+1):
        a=i*math.tau/seg
        v.append((rx*math.cos(a),y,rz*math.sin(a)-.005));uv.append((i/seg,j/5))
for j in range(5):
    for i in range(seg):
        k=j*(seg+1)+i;f.append((k,k+1,k+seg+2,k+seg+1))
add(v,f,uv,1,'Head')
shell(1.744,1.755,.086,.089,5,'Head',seg=48)
# Raised brow reinforcement with rolled trim, ear-side hinges and cheek guards.
tube([(-.077,1.757,.03),(-.062,1.766,.067),(-.03,1.772,.085),(0,1.773,.089),(.03,1.772,.085),(.062,1.766,.067),(.077,1.757,.03)],.006,1,'Head',10)
for sx in (-1,1):
    ribbon([(sx*.075,1.737,.026),(sx*.076,1.709,.035),(sx*.065,1.665,.054),(sx*.047,1.625,.056)],.031,1,'Head',.003)
    tube([(sx*.061,1.73,.044),(sx*.062,1.694,.054),(sx*.048,1.637,.064)],.002,5,'Head',8)
    ellipsoid((sx*.077,1.735,.027),(.008,.006,.004),5,'Head',12,8)
# Sloping neck guard, distinct from the cheek guards.
v=[];uv=[];f=[]
for j,(y,rx,rz) in enumerate([(1.747,.084,.085),(1.725,.099,.12),(1.707,.106,.142)]):
    for i in range(33):
        a=math.pi+math.pi*i/32
        v.append((rx*math.cos(a),y,rz*math.sin(a)-.004));uv.append((i/32,j/2))
for j in range(2):
    for i in range(32):
        k=j*33+i;f.append((k,k+1,k+34,k+33))
add(v,f,uv,1,'Head')
tube([(-.1,1.707,-.02),(-.08,1.707,-.105),(0,1.707,-.146),(.08,1.707,-.105),(.1,1.707,-.02)],.002,5,'Head',8)
# Forged cross reinforcement over the skull.
tube([(0,1.768,.086),(0,1.825,.067),(0,1.856,-.005),(0,1.825,-.074),(0,1.75,-.091)],.0038,1,'Head',10)

GROUP='Leather_Equipment'
shell(1.014,1.057,.161,.113,2,'Hips',seg=48,thick=.006)
for i in range(18):
    a=i*math.tau/18
    ellipsoid((.164*math.cos(a),1.036,.117*math.sin(a)),(.012,.015,.004),5,'Hips',10,6)
for x in [-.061,-.021,.021,.061]:
    ribbon([(x,1.025,.12),(x,.95,.132),(x,.86,.143),(x,.81,.15)],.025,2,'Hips',.004)
    for y in [.995,.955,.915,.875,.83]:ellipsoid((x,y,.145-(y-.81)*.1),(.0035,.0035,.002),5,'Hips',8,6)
for sx in (-1,1):
    ribbon([(sx*.088,1.46,.114),(sx*.073,1.39,.127),(sx*.065,1.32,.126)],.019,2,'Chest',.003)
    for y in (1.445,1.38):
        tube([(sx*.09-.009,y,.127),(sx*.09+.009,y,.127)],.002,5,'Chest',8)
for s,sign in [('L',1),('R',-1)]:
    # Caligae soles, leather lattice straps and calf lacing; toes stay exposed.
    loft([(sign*.105,.025,-.078),(sign*.105,.024,-.02),(sign*.105,.022,.10),(sign*.105,.02,.21)],[(.036,.012),(.04,.012),(.049,.013),(.043,.012)],2,'Foot.'+s,20)
    for z in (.0,.055,.105,.15):
        pts=[(sign*.105-.045,.042,z),(sign*.105-.035,.078,z),(sign*.105,.092,z),(sign*.105+.035,.078,z),(sign*.105+.045,.042,z)]
        ribbon(pts,.012,2,'Foot.'+s,.003)
    for y in (.145,.205,.27):
        pts=[(sign*.105+.029*math.cos(a),y,.03*math.sin(a)-.015) for a in np.linspace(0,math.tau,25)]
        tube(pts,.004,2,'Shin.'+s,6)
    for i in range(5):
        y=.14+i*.028
        tube([(sign*.105-.02,y,.012),(sign*.105+.02,y+.028,.014)],.0025,2,'Shin.'+s,6)

# One original PBR atlas with coherent microfinish; eight 512px regions.
rng=np.random.default_rng(27106);size=512
colors=[(.44,.465,.385),(.29,.31,.30),(.23,.145,.085),(.29,.077,.050),(.17,.065,.05),(.40,.285,.13),(.6,.61,.47),(.10,.075,.053)]
rough=[.83,.64,.85,.94,.72,.58,.45,.86];metal=[0,.78,0,0,0,.64,0,0]
base=np.ones((size*2,size*4,4),np.float32);orm=np.ones_like(base);normal=np.ones_like(base)
for tile,col in enumerate(colors):
    yy,xx=np.mgrid[0:size,0:size];noise=rng.normal(0,1,(size,size))
    broad=np.sin(xx*.037)*np.cos(yy*.027)+.5*np.sin((xx+yy)*.016)
    grain=.014*noise+.026*broad
    if tile==3:grain+=.025*np.sin(xx*math.pi/2)*np.sin(yy*math.pi/2)
    if tile==1:grain+=.012*np.sin(xx*.48+yy*.02)
    rgb=np.clip(np.array(col)[None,None,:]+grain[:,:,None],.02,.95)
    if tile==1:
        rust=np.clip((np.sin(xx*.019)+np.cos(yy*.033)+.5*np.sin((xx-yy)*.027)-1.05)*.35,0,.5)
        rgb=rgb*(1-rust[:,:,None])+np.array([.23,.115,.05])*rust[:,:,None]
    region=(slice((tile//4)*size,(tile//4+1)*size),slice((tile%4)*size,(tile%4+1)*size))
    base[region][:,:,:3]=rgb
    orm[region][:,:,0]=np.clip(.93+.025*broad,.80,1)
    orm[region][:,:,1]=np.clip(rough[tile]+noise*.022+broad*.025,.2,.98)
    orm[region][:,:,2]=metal[tile]
    gx,gy=np.gradient(grain);strength=.65 if tile in (0,2,3) else .32
    normal[region][:,:,0]=.5-gx*strength;normal[region][:,:,1]=.5-gy*strength;normal[region][:,:,2]=1
images={}
for label,pixels in [('BaseColor',base),('ORM',orm),('Normal',normal)]:
    im=bpy.data.images.new('Legionary_'+label,width=size*4,height=size*2)
    im.colorspace_settings.name='sRGB' if label=='BaseColor' else 'Non-Color'
    im.pixels.foreach_set(pixels.ravel());im.filepath_raw=str(TEX/(label+'.png'));im.file_format='PNG';im.save();im.pack();images[label]=im
mat=bpy.data.materials.new('legionary_atlas');mat.use_nodes=True
nodes=mat.node_tree.nodes;links=mat.node_tree.links;bsdf=nodes.get('Principled BSDF')
for label in images:
    n=nodes.new('ShaderNodeTexImage');n.image=images[label];n.label=label
    if label=='BaseColor':links.new(n.outputs['Color'],bsdf.inputs['Base Color'])
    elif label=='Normal':
        nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.5;links.new(n.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bsdf.inputs['Normal'])
    else:
        sep=nodes.new('ShaderNodeSeparateColor');links.new(n.outputs['Color'],sep.inputs[0]);links.new(sep.outputs['Green'],bsdf.inputs['Roughness']);links.new(sep.outputs['Blue'],bsdf.inputs['Metallic'])

# Build actual Blender armature and normalized vertex groups. Armor weights are
# exactly one rigid bone; skin at elbows/knees blends across neighboring bones.
armdata=bpy.data.armatures.new('Legionary_Humanoid')
rig=bpy.data.objects.new('Legionary_Rig',armdata);bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for name,(head,tail,parent) in BONES.items():
    b=armdata.edit_bones.new(name);b.head=xyz(head);b.tail=xyz(tail)
    if parent:b.parent=armdata.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
objects=[]
for name,d in DATA.items():
    mesh=bpy.data.meshes.new(name+'_Topology');mesh.from_pydata(d['v'],[],d['f']);mesh.update()
    uv=mesh.uv_layers.new(name='AtlasUV')
    for face in mesh.polygons:
        face.use_smooth=True
        for li in face.loop_indices:uv.data[li].uv=d['uv'][mesh.loops[li].vertex_index]
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);obj.data.materials.append(mat)
    for bn in BONES:obj.vertex_groups.new(name=bn)
    for i,weights in enumerate(d['w']):
        total=sum(weights.values())
        for bn,w in weights.items():obj.vertex_groups[bn].add([i],w/total,'REPLACE')
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    mod=obj.modifiers.new('Humanoid skin','ARMATURE');mod.object=rig;obj.parent=rig
    objects.append(obj)

def rotation(name,axis,angle):
    pb=rig.pose.bones[name];rest=armdata.bones[name].matrix_local.to_quaternion()
    q=rest.inverted() @ Quaternion(xyz(axis),angle) @ rest
    pb.rotation_mode='QUATERNION';pb.rotation_quaternion=q

def translate(name,delta):
    rig.pose.bones[name].location=armdata.bones[name].matrix_local.to_3x3().inverted() @ xyz(delta)

# Authored keyframes in Blender actions; no game state references or root-motion
# dependencies. Attack peak at .45s matches the existing gameplay contact time.
FPS=30
for name,seconds,loop in [('Idle',2.4,True),('Walk',1.04,True),('Run',.68,True),('Attack',1.0,False),('Hit',.35,False),('Death',1.6,False),('Emerge',1.3,False)]:
    action=bpy.data.actions.new(name);rig.animation_data_create();rig.animation_data.action=action
    n=round(seconds*FPS)
    frames=list(range(0,n+1,2))
    if n not in frames:frames.append(n)
    for frame in frames:
        t=frame/n;p=t*math.tau
        for pb in rig.pose.bones:pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion();pb.location=(0,0,0)
        rotation('Chest',(1,0,0),.09);rotation('Head',(0,1,0),-.07)
        if name in ('Idle','Walk','Run'):
            rotation('Chest',(1,0,0),.09+.013*math.sin(p));rotation('Head',(0,1,0),-.07+.025*math.sin(p))
            rotation('Jaw',(1,0,0),.03+.018*math.sin(p))
            if name!='Idle':
                run=name=='Run';amp=.70 if run else .39
                translate('Hips',(.008*math.sin(p),(.038 if run else .014)*(1-math.cos(2*p)),0))
                for s,phase in [('L',0),('R',math.pi)]:
                    swing=math.sin(p+phase)
                    rotation('Thigh.'+s,(1,0,0),amp*swing)
                    rotation('Shin.'+s,(1,0,0),-(1.12 if run else .62)*max(0,-swing))
                    rotation('Foot.'+s,(1,0,0),-.16*swing+.18*max(0,-swing))
                    rotation('UpperArm.'+s,(1,0,0),-.22-amp*.65*swing)
                    rotation('Forearm.'+s,(1,0,0),-.75 if run else -.22)
                    rotation('Spine',(0,1,0),.045*math.sin(p))
        elif name=='Attack':
            # Reach/wind-up, downward strike at contact, then recoil to idle.
            amount=np.interp(t,[0,.2,.38,.45,.65,1],[0,.8,1,.55,.25,0])
            rotation('Chest',(1,0,0),.09+.18*math.sin(t*math.pi))
            for s,mul in [('L',1),('R',.88)]:
                rotation('UpperArm.'+s,(1,0,0),-1.45*amount*mul)
                rotation('Forearm.'+s,(1,0,0),-.45*amount)
        elif name=='Hit':
            a=math.sin(math.pi*t)*(1-t*.35);rotation('Chest',(1,0,0),-.18*a);rotation('Head',(1,0,0),-.18*a);rotation('Spine',(0,0,1),.08*a)
        elif name=='Death':
            fall=float(np.interp(t,[0,.18,.65,.83,1],[0,.1,1,1.02,1]))
            rotation('Hips',(1,0,0),1.48*fall)
            translate('Hips',(.025*fall,-.76*fall,.12*fall))
            rotation('Head',(0,1,0),.6*fall)
            for s in ('L','R'):
                rotation('UpperArm.'+s,(1,0,0),-.62*fall)
                rotation('Forearm.'+s,(1,0,0),-.25*fall)
        elif name=='Emerge':
            translate('Hips',(0,-.80*(1-t)**2,0))
            rotation('Chest',(1,0,0),.4*(1-t)+.09)
            rotation('UpperArm.L',(1,0,0),-.5*(1-t))
            rotation('UpperArm.R',(1,0,0),-.35*(1-t))
        # Finger curl and mild asymmetry keep hands alive without clenched fists.
        for s in ('L','R'):
            for fi in range(1,5):
                for j in range(1,4):rotation(f'Finger{fi}_{j}.{s}',(1,0,0),-.12*(j/3))
        for pb in rig.pose.bones:
            pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name)
            if pb.name=='Hips':pb.keyframe_insert('location',frame=frame,group=pb.name)
    for fc in action.fcurves:
        for kp in fc.keyframe_points:kp.interpolation='BEZIER'
    action.use_fake_user=True
rig.animation_data.action=bpy.data.actions['Idle']
scene=bpy.context.scene;scene.render.fps=FPS;scene.frame_start=0;scene.frame_end=72;scene.frame_set(0)
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
rig['asset_notes']='Original Roman legionary zombie. Metres; Blender -Y front; glTF +Z front. In-place animation; armor rigidly weighted.'

# Portable .blend source and glTF with actual skin weights and all seven clips.
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'Legionary_Zombie.blend'))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for obj in objects:obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'assets/models/zombie_legionary.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False,export_skins=True,export_all_influences=False,export_yup=True)
triangles=sum(len(p.vertices)-2 for o in objects for p in o.data.polygons)
print('LEGIONARY_BUILD_DONE triangles=',triangles,' materials=1 meshes=',len(objects),' bones=',len(BONES),' clips=',[a.name for a in bpy.data.actions])

# Real Blender studio rendering; source remains free of game-specific code.
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(10)
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=False
scene.render.resolution_x=800;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world.color=(.13,.15,.18)
def area(name,pos,power,size,color):
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size;light.color=color
    o=bpy.data.objects.new(name,light);scene.collection.objects.link(o);o.location=xyz(pos);o.rotation_euler=(xyz((0,1,0))-o.location).to_track_quat('-Z','Y').to_euler()
area('Studio_Key',(2.5,3.6,3.5),450,4,(1,.90,.79))
area('Studio_Fill',(-2,2,2),180,3,(.69,.79,1))
area('Studio_Rim',(0,3,-2),350,2,(.85,.9,1))
camdata=bpy.data.cameras.new('AssetReviewCamera');cam=bpy.data.objects.new('AssetReviewCamera',camdata);scene.collection.objects.link(cam);scene.camera=cam
out=ROOT/'docs/legionary_stage1/blender';out.mkdir(parents=True,exist_ok=True)
for label,pos,target,scale in [('front',(0,1,4),(0,.96,0),2.15),('back',(0,1,-4),(0,.96,0),2.15),('three_quarter',(2.5,1.5,3.4),(0,.96,0),2.15),('face_helmet',(.22,1.73,1.3),(0,1.70,0),.48)]:
    cam.location=xyz(pos);cam.rotation_euler=(xyz(target)-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=scale
    scene.render.filepath=str(out/(label+'.png'));bpy.ops.render.render(write_still=True)
print('LEGIONARY_BLENDER_RENDERS_DONE')
