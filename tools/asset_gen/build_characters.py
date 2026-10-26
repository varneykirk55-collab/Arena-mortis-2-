"""
Arena Mortis - humanoid generator: undead legionary / gladiator zombies (skinned,
animated) and marble gladiator statues (static, posed from the same rig).

Rig faces +Z (glTF "front"). Bind pose is a relaxed A-pose.
Animations: Idle, Walk, Run, Attack, Hit, Death (+ Emerge).
"""
import math
import os
import sys

import numpy as np

import meshkit as mk
from meshkit import quat_axis, quat_mul

OUT = sys.argv[1] if len(sys.argv) > 1 else "../../assets/models"

ARM_ANG = math.radians(38)        # A-pose: arm angle from vertical
SA, CA = math.sin(ARM_ANG), math.cos(ARM_ANG)


def build_skeleton(scale=1.0):
    J = []

    def add(name, parent, pos):
        J.append((name, parent, (np.array(pos) * scale).tolist()))
        return len(J) - 1

    hips = add("Hips", -1, (0, 0.98, 0))
    spine = add("Spine", hips, (0, 1.12, 0.0))
    chest = add("Chest", spine, (0, 1.30, 0.0))
    neck = add("Neck", chest, (0, 1.50, 0.0))
    head = add("Head", neck, (0, 1.60, 0.01))
    jaw = add("Jaw", head, (0, 1.625, 0.045))
    bones = {"Hips": hips, "Spine": spine, "Chest": chest, "Neck": neck, "Head": head, "Jaw": jaw}
    for side, sx in (("L", 1), ("R", -1)):
        sh = np.array([sx * 0.185, 1.455, -0.01])
        d = np.array([sx * SA, -CA, 0.0])
        ua = add(f"UpperArm.{side}", chest, sh)
        fa = add(f"Forearm.{side}", ua, sh + d * 0.29)
        hd = add(f"Hand.{side}", fa, sh + d * 0.56)
        th = add(f"Thigh.{side}", hips, (sx * 0.095, 0.94, 0.0))
        sn = add(f"Shin.{side}", th, (sx * 0.1, 0.51, 0.01))
        ft = add(f"Foot.{side}", sn, (sx * 0.105, 0.085, -0.02))
        bones.update({f"UpperArm.{side}": ua, f"Forearm.{side}": fa, f"Hand.{side}": hd,
                      f"Thigh.{side}": th, f"Shin.{side}": sn, f"Foot.{side}": ft})
    return mk.Skeleton(J), bones


SKEL, BONES = build_skeleton()
JPOS = {name: np.array(pos) for (name, parent, pos) in SKEL.joints}


def seg(name, tail=None):
    """Bone segment (head, tail) used for proximity skinning."""
    h = JPOS[name]
    if tail is not None:
        return h, np.array(tail)
    children = [n for (n, p, _) in SKEL.joints if p == BONES[name]]
    # pick the child continuing the chain
    pref = {"Hips": "Spine", "Chest": "Neck"}
    c = pref.get(name, children[0] if children else None)
    return h, JPOS[c]


SEGS = {
    "Hips": seg("Hips", (0, 1.12, 0)),
    "Spine": seg("Spine"),
    "Chest": seg("Chest", (0, 1.47, 0)),
    "Neck": seg("Neck"),
    "Head": seg("Head", (0, 1.82, 0.0)),
    "Jaw": seg("Jaw", (0, 1.58, 0.1)),
}
for s_, sx in (("L", 1), ("R", -1)):
    d = np.array([sx * SA, -CA, 0.0])
    SEGS[f"UpperArm.{s_}"] = seg(f"UpperArm.{s_}")
    SEGS[f"Forearm.{s_}"] = seg(f"Forearm.{s_}")
    SEGS[f"Hand.{s_}"] = (JPOS[f"Hand.{s_}"], JPOS[f"Hand.{s_}"] + d * 0.17)
    SEGS[f"Thigh.{s_}"] = seg(f"Thigh.{s_}")
    SEGS[f"Shin.{s_}"] = seg(f"Shin.{s_}")
    SEGS[f"Foot.{s_}"] = (JPOS[f"Foot.{s_}"], JPOS[f"Foot.{s_}"] + np.array([0, -0.06, 0.2]))


def seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / (ab @ ab + 1e-12), 0, 1)
    c = a + t[:, None] * ab
    return np.linalg.norm(P - c, axis=1)


def auto_weights(candidates, falloff=4.0):
    names = list(candidates)

    def fn(P):
        D = np.stack([seg_dist(P, *SEGS[n]) for n in names], axis=1)
        W = 1.0 / (D ** falloff + 1e-7)
        order = np.argsort(-W, axis=1)[:, :2]
        J = np.zeros((len(P), 4), dtype=np.int64)
        Wt = np.zeros((len(P), 4))
        for k in range(2):
            J[:, k] = [BONES[names[i]] for i in order[:, k]]
            Wt[:, k] = W[np.arange(len(P)), order[:, k]]
        # sharpen: drop small second weights
        Wt[:, 1] = np.where(Wt[:, 1] / (Wt[:, 0] + 1e-12) < 0.08, 0, Wt[:, 1])
        return J, Wt
    return fn


def rigid(bone):
    def fn(P):
        J = np.zeros((len(P), 4), dtype=np.int64)
        J[:, 0] = BONES[bone]
        W = np.zeros((len(P), 4))
        W[:, 0] = 1
        return J, W
    return fn


# ----------------------------------------------------------------------------
# body parts
# ----------------------------------------------------------------------------

def torso(gaunt=1.0, mat="zombie_skin"):
    # (y, half-width x, half-depth z, z-offset)
    secs = [
        (0.86, 0.150, 0.105, 0.0),
        (0.96, 0.165, 0.115, 0.0),
        (1.06, 0.140 * gaunt + 0.01, 0.095, 0.005),
        (1.16, 0.142 * gaunt + 0.01, 0.098, 0.01),
        (1.26, 0.165, 0.112, 0.015),
        (1.36, 0.180, 0.115, 0.01),
        (1.44, 0.185, 0.100, -0.005),
        (1.49, 0.120, 0.075, -0.01),
        (1.52, 0.060, 0.055, 0.0),
    ]
    rings = []
    for (y, rx_, rz_, zo) in secs:
        # flatten the back slightly, chest rounder
        def shape(a, y=y):
            return 1.0 - 0.06 * max(0, -math.sin(a))
        rings.append(mk.ellipse_ring((0, y, zo), rx_, rz_, 20, shape=shape))
    m = mk.loft(rings, mat, cap_start=True, cap_end=False)
    m.skin_fn(auto_weights(["Hips", "Spine", "Chest", "Neck"]))
    return m


def limb(points, radii, mat, bones, n=10, cap_end=True):
    m = mk.tube(points, radii, n, mat, caps=cap_end)
    m.skin_fn(auto_weights(bones))
    return m


def arm(side, mat="zombie_skin", thin=1.0):
    sx = 1 if side == "L" else -1
    sh = JPOS[f"UpperArm.{side}"]
    el = JPOS[f"Forearm.{side}"]
    wr = JPOS[f"Hand.{side}"]
    pts = [sh + (sh - el) * 0.12, sh, (sh + el) / 2, el, (el + wr) / 2, wr]
    rad = [0.05, 0.066 * thin, 0.056 * thin, 0.044, 0.047 * thin, 0.034]
    m = limb(pts, rad, mat, [f"UpperArm.{side}", f"Forearm.{side}", "Chest"], 10)
    m.add(hand(side, mat))
    return m


def hand(side, mat):
    sx = 1 if side == "L" else -1
    wr = JPOS[f"Hand.{side}"]
    d = np.array([sx * SA, -CA, 0.0])
    side_v = np.array([CA * sx, SA, 0]) * 0  # unused
    fwd = np.array([0, 0, 1.0])
    m = mk.Mesh()
    palm = mk.ellipsoid(0.042, 0.05, 0.018, 10, 6, mat)
    # orient palm along d
    B = mk.look_basis(d, up=(0, 0, 1))
    palm.transform(B).translate(*(wr + d * 0.055))
    m.add(palm)
    # claw fingers: curled forward
    lat = np.cross(d, fwd)
    lat /= np.linalg.norm(lat)
    for i, off in enumerate((-0.027, -0.009, 0.009, 0.027)):
        base = wr + d * 0.1 + lat * off
        L = 0.075 - abs(off) * 0.6
        p1 = base + d * L * 0.45 + fwd * 0.012
        p2 = p1 + d * L * 0.3 + fwd * 0.028
        p3 = p2 + d * L * 0.15 + fwd * 0.03
        m.add(mk.tube([base, p1, p2, p3], [0.011, 0.01, 0.008, 0.005], 6, mat))
    th = wr + d * 0.04 + fwd * 0.02
    m.add(mk.tube([th, th + d * 0.03 + fwd * 0.03, th + d * 0.06 + fwd * 0.05], [0.012, 0.01, 0.006], 6, mat))
    m.skin_fn(rigid(f"Hand.{side}"))
    return m


def leg(side, mat="zombie_skin", thin=1.0):
    th = JPOS[f"Thigh.{side}"]
    kn = JPOS[f"Shin.{side}"]
    an = JPOS[f"Foot.{side}"]
    pts = [th + np.array([0, 0.06, 0]), th, th + (kn - th) * 0.45, kn, kn + (an - kn) * 0.35, an + np.array([0, 0.02, 0])]
    rad = [0.092, 0.094 * thin, 0.078 * thin, 0.058, 0.062 * thin, 0.04]
    m = limb(pts, rad, mat, [f"Thigh.{side}", f"Shin.{side}", "Hips"], 10)
    # foot
    sx = 1 if side == "L" else -1
    rings = []
    for (z, w_, h_, y) in ((-0.06, 0.035, 0.04, 0.06), (-0.01, 0.045, 0.045, 0.05), (0.07, 0.05, 0.03, 0.035),
                           (0.14, 0.048, 0.022, 0.025), (0.17, 0.035, 0.015, 0.02)):
        B = mk.look_basis((0, 0, 1), up=(0, 1, 0))
        ring = mk.ellipse_ring((0, 0, 0), w_, h_, 10, basis=B)
        rings.append(ring + np.array([an[0], y, z + an[2]]))
    foot = mk.loft(rings, mat)
    foot.skin_fn(rigid(f"Foot.{side}"))
    m.add(foot)
    return m


def head(mat="zombie_skin", gaunt=True, jaw_open=0.02):
    """Head with brow, sunken eyes, nose cavity, jaw with teeth."""
    m = mk.Mesh()
    hp = JPOS["Head"]
    # cranium: loft of rings along y, front bulge
    secs = [(1.585, 0.055, 0.065, 0.02), (1.62, 0.075, 0.085, 0.015), (1.68, 0.085, 0.098, 0.01),
            (1.74, 0.087, 0.1, 0.0), (1.80, 0.074, 0.088, -0.005), (1.84, 0.045, 0.055, -0.01),
            (1.855, 0.01, 0.012, -0.01)]
    rings = []
    for (y, rx_, rz_, zo) in secs:
        def shape(a, y=y):
            f = 1.0
            if math.sin(a) > 0:   # front (+z): flatter face
                f -= 0.08 * math.sin(a) ** 2
            if gaunt and 1.64 < y < 1.75:
                f -= 0.07 * abs(math.cos(a)) ** 4   # sunken temples/cheeks
            return f
        rings.append(mk.ellipse_ring((0, y, zo), rx_, rz_, 18, shape=shape))
    cran = mk.loft(rings, mat, cap_start=True, cap_end=True)
    m.add(cran)
    # brow ridge
    brow = mk.ellipsoid(0.072, 0.016, 0.03, 12, 6, mat).translate(0, 1.745, 0.075)
    m.add(brow)
    # cheekbones
    for sx in (-1, 1):
        m.add(mk.ellipsoid(0.022, 0.016, 0.03, 8, 5, mat).translate(sx * 0.055, 1.69, 0.07))
    # nose (rotted: short bridge + dark cavity)
    m.add(mk.hull([(-0.012, 1.735, 0.09), (0.012, 1.735, 0.09), (0, 1.73, 0.1), (-0.016, 1.69, 0.098), (0.016, 1.69, 0.098), (0, 1.695, 0.112)], mat))
    m.add(mk.ellipsoid(0.014, 0.008, 0.006, 8, 4, "zombie_mouth").translate(0, 1.684, 0.1))
    # eye sockets (dark) + glowing eyes
    for sx in (-1, 1):
        m.add(mk.ellipsoid(0.023, 0.017, 0.012, 10, 6, "zombie_mouth").translate(sx * 0.034, 1.718, 0.085))
        m.add(mk.sphere(0.009, 8, 6, "zombie_eye").translate(sx * 0.034, 1.716, 0.091))
        # ears
        m.add(mk.ellipsoid(0.01, 0.026, 0.018, 8, 5, mat).translate(sx * 0.086, 1.71, 0.0))
    m.skin_fn(rigid("Head"))
    # jaw (separate bone) with teeth and open mouth cavity
    jaw = mk.Mesh()
    jr = []
    for (y, rx_, rz_, zo) in ((1.645, 0.06, 0.06, 0.03), (1.615, 0.055, 0.058, 0.035), (1.59, 0.04, 0.045, 0.045), (1.575, 0.02, 0.025, 0.05)):
        jr.append(mk.ellipse_ring((0, y, zo), rx_, rz_, 14))
    jaw.add(mk.loft(jr, mat))
    jaw.add(mk.ellipsoid(0.036, 0.014, 0.012, 10, 5, "zombie_mouth").translate(0, 1.652, 0.083))
    for i in range(8):
        x = -0.028 + i * 0.008
        jaw.add(mk.box(0.006, 0.012, 0.005, material="bone").translate(x, 1.646, 0.087 - abs(x) * 0.35))
        jaw.add(mk.box(0.006, 0.011, 0.005, material="bone").translate(x, 1.664, 0.089 - abs(x) * 0.35))
    jaw.skin_fn(rigid("Jaw"))
    m.add(jaw)
    return m


def neck(mat="zombie_skin"):
    m = mk.tube([(0, 1.46, -0.01), (0, 1.54, 0.0), (0, 1.62, 0.01)], [0.06, 0.045, 0.048], 10, mat)
    m.skin_fn(auto_weights(["Chest", "Neck", "Head"]))
    return m


def ribs_wound(mat="bone"):
    """Exposed ribs on the left flank."""
    m = mk.Mesh()
    for i in range(4):
        y = 1.15 + i * 0.05
        pts = [(0.10, y, 0.07), (0.14, y + 0.005, 0.04), (0.155, y + 0.01, 0.0), (0.145, y + 0.012, -0.04)]
        m.add(mk.tube(pts, 0.008, 6, mat))
    m.add(mk.ellipsoid(0.04, 0.11, 0.07, 10, 6, "zombie_mouth").translate(0.115, 1.22, 0.0))
    m.skin_fn(auto_weights(["Spine", "Chest"]))
    return m


# ----------------------------------------------------------------------------
# outfits
# ----------------------------------------------------------------------------

def tattered_skirt(y_top=1.04, y_bot=0.58, r_top=(0.165, 0.12), flare=1.45, mat="zombie_cloth", seed=0):
    r = np.random.default_rng(seed)
    n = 28
    rings = []
    steps = 5
    for i in range(steps + 1):
        u = i / steps
        y = y_top + (y_bot - y_top) * u
        rx_ = r_top[0] * (1 + (flare - 1) * u)
        rz_ = r_top[1] * (1 + (flare - 1) * u * 1.1)
        ring = mk.ellipse_ring((0, y, 0.0), rx_, rz_, n)
        if i == steps:
            ring[:, 1] += (r.random(n) * 0.14) * (np.arange(n) % 2) + r.random(n) * 0.05
        # folds
        ang = 2 * math.pi * np.arange(n) / n
        ring[:, 0] *= 1 + 0.04 * np.sin(ang * 7) * u
        ring[:, 2] *= 1 + 0.04 * np.sin(ang * 7) * u
        rings.append(ring)
    m = mk.loft(rings, mat, cap_start=False, cap_end=False)
    m.add(mk.loft(rings[::-1], mat, cap_start=False, cap_end=False))  # inside faces (double sided)

    def w(P):
        J = np.zeros((len(P), 4), dtype=np.int64)
        W = np.zeros((len(P), 4))
        down = np.clip((y_top - P[:, 1]) / (y_top - y_bot), 0, 1)
        side = np.clip(P[:, 0] / 0.12, -1, 1)
        J[:, 0] = BONES["Hips"]
        J[:, 1] = BONES["Thigh.L"]
        J[:, 2] = BONES["Thigh.R"]
        W[:, 0] = 1 - down * 0.7
        W[:, 1] = down * 0.7 * np.clip(0.5 + side * 0.5, 0, 1)
        W[:, 2] = down * 0.7 * np.clip(0.5 - side * 0.5, 0, 1)
        return J, W
    m.skin_fn(w)
    return m


def pteruges(y_top=1.03, length=0.26, mat="zombie_leather"):
    m = mk.Mesh()
    n = 16
    for i in range(n):
        a = 2 * math.pi * i / n
        x, z = 0.178 * math.cos(a), 0.135 * math.sin(a)
        strip = mk.box(0.045, length, 0.012, bevel=0.003, material=mat)
        strip.translate(0, -length / 2, 0)
        strip.rotate((0, 1, 0), -a + math.pi / 2).translate(x, y_top, z)
        m.add(strip)
        m.add(mk.box(0.03, 0.03, 0.006, material="zombie_metal").rotate((0, 1, 0), -a + math.pi / 2).translate(x * 1.06, y_top - length + 0.03, z * 1.06))
    m.skin_fn(auto_weights(["Hips", "Thigh.L", "Thigh.R"]))
    return m


def belt(y=1.05, mat="zombie_leather"):
    m = mk.Mesh()
    m.add(mk.loft([mk.ellipse_ring((0, y - 0.03, 0), 0.172, 0.125, 24), mk.ellipse_ring((0, y + 0.03, 0), 0.17, 0.123, 24)], mat))
    for i in range(10):
        a = math.pi / 2 + (i - 4.5) * 0.28
        m.add(mk.box(0.035, 0.05, 0.01, material="zombie_metal").rotate((0, 1, 0), -a + math.pi / 2).translate(0.176 * math.cos(a), y, 0.13 * math.sin(a)))
    m.skin_fn(rigid("Hips"))
    return m


def lorica(mat="zombie_metal"):
    """Segmented plate bands over the torso (partially torn away)."""
    m = mk.Mesh()
    for i, (y, rx_, rz_) in enumerate(((1.12, 0.155, 0.112), (1.18, 0.16, 0.116), (1.24, 0.172, 0.122),
                                         (1.30, 0.183, 0.125), (1.36, 0.19, 0.126))):
        if i == 1:
            continue  # missing plate - exposes tunic
        band = mk.loft([mk.ellipse_ring((0, y - 0.028, 0.012), rx_ + 0.012, rz_ + 0.015, 24),
                        mk.ellipse_ring((0, y + 0.028, 0.012), rx_ + 0.008, rz_ + 0.012, 24)], mat, smooth=True)
        if i == 0:
            g = band.groups[mat]
            cut = g["P"][:, 0] > 0.05  # torn on the left - ribs show
            tri_keep = ~np.any(cut[g["I"]], axis=1)
            g["I"] = g["I"][tri_keep]
        m.add(band)
    # shoulder plates (girth): rings around the upper arm, upper/outer half only
    for sx in (-1, 1):
        side = "L" if sx > 0 else "R"
        sh = JPOS[f"UpperArm.{side}"]
        el = JPOS[f"Forearm.{side}"]
        d = (el - sh) / np.linalg.norm(el - sh)
        up_out = np.array([sx * CA, SA, 0.0])
        for k in range(3):
            r = 0.082 - k * 0.004
            plate = mk.lathe([(r - 0.004, -0.026), (r + 0.006, 0.0), (r - 0.002, 0.026)], 18, mat)
            plate.transform(mk.look_basis(d, up=(0, 0, 1)))
            plate.translate(*(sh + d * (0.0 + k * 0.045) - up_out * 0.0))
            g = plate.groups[mat]
            cen = g["P"][g["I"]].mean(axis=1) - (sh + d * (k * 0.045))
            keep = cen @ up_out > -0.01
            g["I"] = g["I"][keep]
            plate.skin_fn(rigid(f"UpperArm.{side}"))
            m.add(plate)
    for sx in (-1, 1):
        strap = mk.tube([(sx * 0.13, 1.47, 0.08), (sx * 0.12, 1.42, 0.125), (sx * 0.05, 1.40, 0.135)], 0.008, 5, "zombie_leather")
        strap.skin_fn(rigid("Chest"))
        m.add(strap)
    m2 = mk.Mesh()
    for k, g in m.groups.items():
        pass
    # skin the bands that are not yet skinned
    bands = mk.Mesh()
    for k, g in list(m.groups.items()):
        pass
    m.skin_fn(lambda P: _mixed_lorica_weights(P))
    return m


def _mixed_lorica_weights(P):
    # shoulder region -> upper arms, torso -> spine/chest
    torso_fn = auto_weights(["Spine", "Chest", "Neck"])
    arm_fn_L = rigid("UpperArm.L")
    arm_fn_R = rigid("UpperArm.R")
    J, W = torso_fn(P)
    is_arm = (np.abs(P[:, 0]) > 0.18) & (P[:, 1] > 1.38)
    jl, wl = arm_fn_L(P)
    jr, wr = arm_fn_R(P)
    left = is_arm & (P[:, 0] > 0)
    right = is_arm & (P[:, 0] < 0)
    J[left], W[left] = jl[left], wl[left]
    J[right], W[right] = jr[right], wr[right]
    return J, W


def galea(mat="zombie_metal", crest=True):
    """Roman legionary helmet with cheek guards, neck guard, brow ridge and crest."""
    m = mk.Mesh()
    dome = []
    for i in range(9):
        a = math.pi / 2 * i / 8
        dome.append((0.098 * math.cos(a) + 0.002, 1.735 + 0.13 * math.sin(a)))
    dome[-1] = (0.004, dome[-1][1])
    bowl = mk.lathe(dome, 22, mat).scale((1.0, 1.0, 1.08)).translate(0, 0, -0.005)
    m.add(bowl)
    # brow band and visor ridge
    m.add(mk.torus(0.1, 0.008, 22, 6, mat).scale((1, 1, 1.08)).translate(0, 1.737, -0.005))
    visor = mk.lathe([(0.1, 1.75), (0.125, 1.745), (0.13, 1.738)], 16, mat, angle0=0.2, angle1=math.pi - 0.2)
    m.add(visor.scale((1, 1, 1.08)))
    # neck guard (flared plate at the back)
    ng = mk.lathe([(0.1, 1.74), (0.12, 1.69), (0.15, 1.665)], 16, mat, angle0=math.pi + 0.35, angle1=2 * math.pi - 0.35)
    m.add(ng.scale((1, 1, 1.1)))
    # cheek guards
    for sx in (-1, 1):
        poly = [(0, 0), (0.05, 0.0), (0.055, -0.06), (0.03, -0.095), (0.0, -0.08)]
        cg = mk.extrude(poly, 0.006, mat).rotate((0, 1, 0), -sx * math.pi / 2 + sx * 0.25)
        cg.translate(sx * 0.095, 1.74, 0.045 - 0.05)
        m.add(cg)
    # crest holder and transverse crest (centurion style, longitudinal for legionary)
    if crest:
        m.add(mk.box(0.012, 0.03, 0.03, material=mat).translate(0, 1.875, 0))
        n = 26
        for i in range(n):
            a = math.pi * (0.1 + 0.8 * i / (n - 1))
            # fan of bristle wedges along the front-back arc
            z = -math.cos(a) * 0.14
            y = 1.88 + math.sin(a) * 0.09
            tuft = mk.tapered_box((0.03, 0.03), (0.022, 0.012), 0.09, material="zombie_crest")
            tuft.translate(0, -0.03, 0).rotate((1, 0, 0), (a - math.pi / 2) * 0.9).translate(0, y - 0.02, z)
            m.add(tuft)
    # rivets
    for i in range(10):
        a = 2 * math.pi * i / 10
        m.add(mk.sphere(0.006, 6, 4, "gold").translate(0.101 * math.cos(a), 1.745, 0.108 * math.sin(a) - 0.005))
    m.skin_fn(rigid("Head"))
    return m


def manica(side="R", mat="zombie_metal"):
    m = mk.Mesh()
    sh = JPOS[f"UpperArm.{side}"]
    wr = JPOS[f"Hand.{side}"]
    for i in range(9):
        u = 0.08 + i * 0.1
        c = sh + (wr - sh) * u
        d = (wr - sh) / np.linalg.norm(wr - sh)
        r = 0.064 - u * 0.022
        ring = mk.lathe([(r, -0.022), (r + 0.006, 0.0), (r, 0.022)], 12, mat)
        ring.transform(mk.look_basis(d)).translate(*c)
        m.add(ring)
    m.skin_fn(auto_weights([f"UpperArm.{side}", f"Forearm.{side}"]))
    return m


def greaves(mat="zombie_metal"):
    m = mk.Mesh()
    for side, sx in (("L", 1), ("R", -1)):
        kn = JPOS[f"Shin.{side}"]
        an = JPOS[f"Foot.{side}"]
        g = mk.lathe([(0.062, 0.0), (0.066, 0.12), (0.058, 0.3), (0.05, 0.38)], 14, mat,
                     angle0=0.15, angle1=math.pi - 0.15)
        g.translate(kn[0], an[1] + 0.06, 0.0)
        g.skin_fn(rigid(f"Shin.{side}"))
        m.add(g)
        knee = mk.ellipsoid(0.055, 0.05, 0.035, 10, 6, mat).translate(kn[0], kn[1] + 0.01, 0.05)
        knee.skin_fn(rigid(f"Shin.{side}"))
        m.add(knee)
    return m


def sandals(mat="zombie_leather"):
    m = mk.Mesh()
    for side, sx in (("L", 1), ("R", -1)):
        an = JPOS[f"Foot.{side}"]
        sole = mk.box(0.11, 0.018, 0.27, bevel=0.006, material=mat).translate(an[0], 0.009, an[2] + 0.06)
        sole.skin_fn(rigid(f"Foot.{side}"))
        m.add(sole)
        for k in range(3):
            st = mk.torus(0.05 - k * 0.004, 0.006, 12, 4, mat).translate(an[0], 0.11 + k * 0.05, an[2] + 0.0)
            st.skin_fn(rigid(f"Shin.{side}"))
            m.add(st)
    return m


def shield_scutum(mat="wood_box"):
    m = mk.Mesh()
    curve = []
    for i in range(9):
        a = -0.6 + 1.2 * i / 8
        curve.append((math.sin(a) * 0.38, math.cos(a) * 0.38 - 0.38))
    # build as extruded curved slab along y
    pts_outer = [(x, z) for x, z in curve]
    pts_inner = [(x * 0.95, z - 0.02) for x, z in curve[::-1]]
    sl = mk.extrude(pts_outer + pts_inner, 1.0, "cloth_red")
    sl.rotate((1, 0, 0), math.pi / 2)
    m.add(sl)
    m.add(mk.sphere(0.07, 12, 8, "gold").scale((1, 1, 0.5)).translate(0, 0, 0.01))
    return m


def parma():
    m = mk.Mesh()
    m.add(mk.lathe([(0.001, 0.05), (0.12, 0.045), (0.26, 0.02), (0.3, 0.0), (0.3, -0.02), (0.001, -0.02)], 24, "wood_box"))
    m.add(mk.sphere(0.06, 12, 8, "gold").scale((1, 0.6, 1)).translate(0, 0.05, 0))
    m.add(mk.torus(0.29, 0.015, 24, 6, "gold"))
    m.rotate((1, 0, 0), math.pi / 2)
    return m


def gladius():
    m = mk.Mesh()
    blade = mk.extrude([(-0.035, 0), (0.035, 0), (0.03, 0.48), (0, 0.6), (-0.03, 0.48)], 0.014, "gun_metal")
    m.add(blade)
    m.add(mk.box(0.11, 0.03, 0.03, bevel=0.008, material="gold").translate(0, -0.01, 0))
    m.add(mk.cylinder(0.016, 0.1, 8, "leather").translate(0, -0.12, 0))
    m.add(mk.sphere(0.03, 10, 6, "gold").translate(0, -0.14, 0))
    return m


# ----------------------------------------------------------------------------
# assembly
# ----------------------------------------------------------------------------

def build_body(variant="legionary", statue=False, seed=0):
    skin = "marble" if statue else "zombie_skin"
    parts = mk.Mesh()
    gaunt = 0.92 if not statue else 1.05
    thin = 0.97 if not statue else 1.12
    parts.add(torso(gaunt, skin))
    parts.add(neck(skin))
    parts.add(head(skin, gaunt=not statue))
    for s in ("L", "R"):
        parts.add(arm(s, skin, thin))
        parts.add(leg(s, skin, thin))
    if not statue:
        parts.add(ribs_wound())
    if variant == "legionary":
        parts.add(tattered_skirt(seed=seed, mat="marble" if statue else "zombie_cloth"))
        parts.add(belt(mat="marble" if statue else "zombie_leather"))
        parts.add(pteruges(mat="marble" if statue else "zombie_leather"))
        parts.add(lorica(mat="marble" if statue else "zombie_metal"))
        parts.add(galea(mat="marble" if statue else "zombie_metal", crest=True))
        parts.add(sandals(mat="marble" if statue else "zombie_leather"))
    else:  # gladiator (murmillo-ish): loincloth, belt, manica, greaves, no helmet
        parts.add(tattered_skirt(1.03, 0.80, (0.168, 0.122), 1.12, "marble" if statue else "zombie_cloth", seed + 5))
        parts.add(belt(1.04, "marble" if statue else "zombie_leather"))
        parts.add(manica("R", "marble" if statue else "zombie_metal"))
        parts.add(greaves("marble" if statue else "zombie_metal"))
        parts.add(sandals("marble" if statue else "zombie_leather"))
        if not statue:
            hair = mk.Mesh()
            r = np.random.default_rng(seed + 9)
            for i in range(40):
                a = r.random() * 2 * math.pi
                yv = 1.76 + r.random() * 0.08
                p0 = np.array([0.08 * math.cos(a), yv, 0.088 * math.sin(a) - 0.01])
                if p0[2] > 0.06 and yv < 1.79:
                    continue
                p1 = p0 * np.array([1.1, 1.0, 1.1]) + np.array([0, -0.06 - r.random() * 0.08, 0])
                hair.add(mk.tube([p0, p1], [0.006, 0.002], 4, "zombie_hair", caps=False))
            hair.skin_fn(rigid("Head"))
            parts.add(hair)
    if not statue:
        # baked blood / rot in vertex colours (mouth, hands, chest wound)
        def blood(P, N):
            c = np.ones((len(P), 3))
            def splat(center, radius, strength):
                d = np.linalg.norm(P - np.array(center), axis=1)
                return np.clip(1 - d / radius, 0, 1) * strength
            s = splat((0, 1.63, 0.09), 0.07, 0.8) + splat((0.12, 1.2, 0.05), 0.12, 0.7) + splat((-0.05, 1.35, 0.12), 0.08, 0.5)
            for side, sx in (("L", 1), ("R", -1)):
                s = s + splat(JPOS[f"Hand.{side}"] + np.array([sx * SA, -CA, 0]) * 0.08, 0.1, 0.6)
            noise = mk.value_noise3(P, 30.0, seed)
            s = np.clip(s * (0.6 + 0.8 * noise), 0, 1)
            c[:, 0] = 1 - s * 0.35
            c[:, 1] = 1 - s * 0.85
            c[:, 2] = 1 - s * 0.85
            return c
        for name in ("zombie_skin", "zombie_cloth", "zombie_metal", "zombie_leather"):
            g = parts.groups.get(name)
            if g is not None:
                g["C"][:, :3] *= blood(g["P"], g["N"])
    return parts


# ----------------------------------------------------------------------------
# animation
# ----------------------------------------------------------------------------

def q(x=0.0, y=0.0, z=0.0):
    """Rotation: X then Y then Z, in parent space (radians)."""
    return mk.quat_euler(x, y, z)


def arm_q(side, fwd=0.0, out=0.0, twist=0.0):
    """Upper-arm rotation from the A-pose. out=0 -> arm hangs vertically;
    fwd>0 swings the arm forward (toward +Z)."""
    sx = 1 if side == "L" else -1
    q_down = quat_axis((0, 0, 1), -sx * ARM_ANG + sx * out)
    q_fwd = quat_axis((1, 0, 0), -fwd)
    q_tw = quat_axis((0, 1, 0), twist * sx)
    return quat_mul(q_fwd, quat_mul(q_down, q_tw))


def elbow_q(side, bend):
    """Forearm bend (forward)."""
    return quat_axis((1, 0, 0), -bend)


R = math.radians


class Clip:
    def __init__(self, name, length):
        self.name = name
        self.length = length
        self.keys = {}  # bone -> {"rotation": [(t, q)], "translation": [(t, v)]}

    def rot(self, bone, t, quat):
        self.keys.setdefault(bone, {}).setdefault("rotation", []).append((t, np.asarray(quat)))

    def pos(self, bone, t, off):
        rest = JPOS[bone] - (JPOS[SKEL.joints[BONES[bone]][0]] * 0 if SKEL.joints[BONES[bone]][1] < 0 else JPOS[SKEL.joints[SKEL.joints[BONES[bone]][1]][0]])
        self.keys.setdefault(bone, {}).setdefault("translation", []).append((t, rest + np.asarray(off)))

    def to_anim(self):
        a = mk.Animation(self.name)
        for bone, paths in self.keys.items():
            for path, ks in paths.items():
                ks = sorted(ks, key=lambda k: k[0])
                times = [k[0] for k in ks]
                vals = [k[1] for k in ks]
                if path == "rotation":
                    # keep quaternions in the same hemisphere
                    for i in range(1, len(vals)):
                        if np.dot(vals[i], vals[i - 1]) < 0:
                            vals[i] = -vals[i]
                a.channels.append((bone, path, times, vals))
        return a


def cyc(clip, bone, frames, fn):
    """Sample fn(phase 0..1) into rotation keys over the clip length (looping)."""
    for i in range(frames + 1):
        u = i / frames
        clip.rot(bone, u * clip.length, fn(u))


def cyc_pos(clip, bone, frames, fn):
    for i in range(frames + 1):
        u = i / frames
        clip.pos(bone, u * clip.length, fn(u))


def anim_idle():
    c = Clip("Idle", 2.4)
    F = 12
    s = lambda u, k=1, ph=0.0: math.sin(2 * math.pi * (u * k + ph))
    cyc(c, "Hips", F, lambda u: q(R(4), R(3) * s(u), R(2) * s(u, 1, 0.25)))
    cyc(c, "Spine", F, lambda u: q(R(10) + R(2) * s(u), 0, R(-2) * s(u)))
    cyc(c, "Chest", F, lambda u: q(R(8) + R(2) * s(u, 1, 0.1), R(4) * s(u, 1, 0.3), 0))
    cyc(c, "Neck", F, lambda u: q(R(10), R(6) * s(u, 1, 0.5), R(8)))
    cyc(c, "Head", F, lambda u: q(R(-6) + R(3) * s(u, 2), R(-4) * s(u), R(12) + R(4) * s(u, 1, 0.2)))
    cyc(c, "Jaw", F, lambda u: q(R(14) + R(6) * s(u, 3), 0, 0))
    for side, sx in (("L", 1), ("R", -1)):
        cyc(c, f"UpperArm.{side}", F, lambda u, side=side, sx=sx: arm_q(side, R(10) + R(4) * s(u, 1, 0.2 * sx), R(6), R(-10)))
        cyc(c, f"Forearm.{side}", F, lambda u, side=side: elbow_q(side, R(25) + R(5) * s(u, 1, 0.4)))
        cyc(c, f"Hand.{side}", F, lambda u: q(R(10), 0, 0))
        cyc(c, f"Thigh.{side}", F, lambda u, sx=sx: q(R(-6 if sx > 0 else 4), 0, R(sx * 3)))
        cyc(c, f"Shin.{side}", F, lambda u, sx=sx: q(R(10 if sx > 0 else 4), 0, 0))
        cyc(c, f"Foot.{side}", F, lambda u, sx=sx: q(R(-4 if sx > 0 else -2), 0, 0))
    cyc_pos(c, "Hips", F, lambda u: (0, -0.03 + 0.008 * s(u), 0))
    return c


def anim_walk(name="Walk", length=1.3, stride=R(26), lean=R(16), arms_up=R(75), limp=0.35):
    """Classic shamble: arms reaching forward, dragging limp on the right leg."""
    c = Clip(name, length)
    F = 16
    s = lambda u, ph=0.0: math.sin(2 * math.pi * (u + ph))
    cs = lambda u, ph=0.0: math.cos(2 * math.pi * (u + ph))
    cyc(c, "Hips", F, lambda u: q(lean * 0.3, R(8) * s(u), R(5) * s(u, 0.25)))
    cyc(c, "Spine", F, lambda u: q(lean * 0.4, R(-5) * s(u), R(-3) * s(u, 0.25)))
    cyc(c, "Chest", F, lambda u: q(lean * 0.5, R(-6) * s(u), R(4) * s(u, 0.1)))
    cyc(c, "Neck", F, lambda u: q(R(-6), R(6) * s(u, 0.3), R(10)))
    cyc(c, "Head", F, lambda u: q(R(-8) + R(4) * s(u, 0.5) * 2, R(5) * s(u), R(10)))
    cyc(c, "Jaw", F, lambda u: q(R(18) + R(8) * s(u, 0.2) * 2, 0, 0))
    for side, sx, ph in (("L", 1, 0.0), ("R", -1, 0.5)):
        amp = stride * (1 - limp * (sx < 0))
        # thigh: forward swing on phase
        cyc(c, f"Thigh.{side}", F, lambda u, ph=ph, amp=amp, sx=sx: q(-amp * s(u, ph), 0, R(sx * 3)))
        # knee bends most during swing (when thigh moving forward)
        cyc(c, f"Shin.{side}", F, lambda u, ph=ph, sx=sx: q(R(12) + R(38 if sx > 0 else 22) * max(0.0, cs(u, ph)) ** 1.5, 0, 0))
        cyc(c, f"Foot.{side}", F, lambda u, ph=ph: q(R(-8) + R(14) * s(u, ph + 0.1), 0, 0))
        # reaching arms with asymmetric sway
        cyc(c, f"UpperArm.{side}", F, lambda u, side=side, ph=ph, sx=sx: arm_q(side, arms_up + R(8) * s(u, ph + 0.5) - (R(20) if sx < 0 else 0), R(14), R(-25)))
        cyc(c, f"Forearm.{side}", F, lambda u, side=side, ph=ph: elbow_q(side, R(18) + R(10) * s(u, ph)))
        cyc(c, f"Hand.{side}", F, lambda u, ph=ph: q(R(-15) + R(10) * s(u, ph), 0, 0))
    cyc_pos(c, "Hips", F, lambda u: (0, -0.04 + 0.025 * abs(s(u)) - 0.02, 0))
    return c


def anim_run():
    c = Clip("Run", 0.66)
    F = 12
    s = lambda u, ph=0.0: math.sin(2 * math.pi * (u + ph))
    cs = lambda u, ph=0.0: math.cos(2 * math.pi * (u + ph))
    cyc(c, "Hips", F, lambda u: q(R(14), R(10) * s(u), 0))
    cyc(c, "Spine", F, lambda u: q(R(12), R(-8) * s(u), 0))
    cyc(c, "Chest", F, lambda u: q(R(10), R(-10) * s(u), 0))
    cyc(c, "Neck", F, lambda u: q(R(-12), 0, 0))
    cyc(c, "Head", F, lambda u: q(R(-10), R(4) * s(u), R(6)))
    cyc(c, "Jaw", F, lambda u: q(R(28), 0, 0))
    for side, sx, ph in (("L", 1, 0.0), ("R", -1, 0.5)):
        cyc(c, f"Thigh.{side}", F, lambda u, ph=ph, sx=sx: q(-R(42) * s(u, ph) - R(12), 0, R(sx * 2)))
        cyc(c, f"Shin.{side}", F, lambda u, ph=ph: q(R(25) + R(70) * max(0.0, cs(u, ph + 0.05)) ** 1.2, 0, 0))
        cyc(c, f"Foot.{side}", F, lambda u, ph=ph: q(R(-10) + R(20) * s(u, ph + 0.15), 0, 0))
        cyc(c, f"UpperArm.{side}", F, lambda u, side=side, ph=ph: arm_q(side, R(55) + R(35) * s(u, ph + 0.5), R(12), R(-20)))
        cyc(c, f"Forearm.{side}", F, lambda u, side=side, ph=ph: elbow_q(side, R(45) + R(20) * s(u, ph + 0.5)))
        cyc(c, f"Hand.{side}", F, lambda u: q(R(-20), 0, 0))
    cyc_pos(c, "Hips", F, lambda u: (0, -0.07 + 0.05 * abs(s(u)), 0))
    return c


def keyed(c, bone, keys, kind="rot"):
    for t, v in keys:
        if kind == "rot":
            c.rot(bone, t, v)
        else:
            c.pos(bone, t, v)


def anim_attack():
    c = Clip("Attack", 1.0)
    T = [0.0, 0.3, 0.5, 0.62, 1.0]
    keyed(c, "Hips", [(0, q(R(8))), (0.3, q(R(-4))), (0.5, q(R(18))), (0.62, q(R(20))), (1.0, q(R(8)))])
    keyed(c, "Spine", [(0, q(R(8))), (0.3, q(R(-10), R(8))), (0.5, q(R(20), R(-10))), (0.62, q(R(22), R(-8))), (1.0, q(R(8)))])
    keyed(c, "Chest", [(0, q(R(8))), (0.3, q(R(-12), R(10))), (0.5, q(R(18), R(-14))), (0.62, q(R(18), R(-10))), (1.0, q(R(8)))])
    keyed(c, "Neck", [(0, q(R(-4))), (0.3, q(R(-18))), (0.5, q(R(6))), (1.0, q(R(-4)))])
    keyed(c, "Head", [(0, q(R(-6))), (0.3, q(R(-20))), (0.5, q(R(10))), (1.0, q(R(-6)))])
    keyed(c, "Jaw", [(0, q(R(10))), (0.3, q(R(40))), (0.5, q(R(35))), (0.7, q(R(15))), (1.0, q(R(10)))])
    for side, sx in (("L", 1), ("R", -1)):
        keyed(c, f"UpperArm.{side}", [(0, arm_q(side, R(70), R(14), R(-20))), (0.3, arm_q(side, R(150), R(30), R(-10))),
                                      (0.5, arm_q(side, R(60), R(-5), R(-30))), (0.62, arm_q(side, R(35), R(-10), R(-30))),
                                      (1.0, arm_q(side, R(70), R(14), R(-20)))])
        keyed(c, f"Forearm.{side}", [(0, elbow_q(side, R(20))), (0.3, elbow_q(side, R(60))), (0.5, elbow_q(side, R(10))),
                                     (0.62, elbow_q(side, R(20))), (1.0, elbow_q(side, R(20)))])
        keyed(c, f"Hand.{side}", [(0, q(R(-15))), (0.3, q(R(-40))), (0.5, q(R(20))), (1.0, q(R(-15)))])
        keyed(c, f"Thigh.{side}", [(0, q(R(-4 * sx), 0, R(sx * 3))), (0.5, q(R(-25 if sx > 0 else 15), 0, R(sx * 4))), (1.0, q(R(-4 * sx), 0, R(sx * 3)))])
        keyed(c, f"Shin.{side}", [(0, q(R(12))), (0.5, q(R(25 if sx > 0 else 10))), (1.0, q(R(12)))])
    keyed(c, "Hips", [(0, (0, -0.04, 0)), (0.5, (0, -0.08, 0.06)), (1.0, (0, -0.04, 0))], "pos")
    return c


def anim_hit():
    c = Clip("Hit", 0.45)
    keyed(c, "Hips", [(0, q(R(6))), (0.12, q(R(-6), R(6))), (0.45, q(R(6)))])
    keyed(c, "Spine", [(0, q(R(8))), (0.12, q(R(-16), R(-6))), (0.45, q(R(8)))])
    keyed(c, "Chest", [(0, q(R(8))), (0.12, q(R(-14), R(8), R(6))), (0.45, q(R(8)))])
    keyed(c, "Head", [(0, q(R(-6))), (0.1, q(R(-28), R(-10), R(-12))), (0.45, q(R(-6)))])
    keyed(c, "Jaw", [(0, q(R(10))), (0.1, q(R(35))), (0.45, q(R(12)))])
    for side, sx in (("L", 1), ("R", -1)):
        keyed(c, f"UpperArm.{side}", [(0, arm_q(side, R(60), R(14), R(-20))), (0.12, arm_q(side, R(20), R(40), R(-20))), (0.45, arm_q(side, R(60), R(14), R(-20)))])
        keyed(c, f"Forearm.{side}", [(0, elbow_q(side, R(20))), (0.12, elbow_q(side, R(45))), (0.45, elbow_q(side, R(20)))])
        keyed(c, f"Thigh.{side}", [(0, q(0, 0, R(sx * 3))), (0.45, q(0, 0, R(sx * 3)))])
    keyed(c, "Hips", [(0, (0, -0.04, 0)), (0.12, (0, -0.06, -0.08)), (0.45, (0, -0.04, 0))], "pos")
    return c


def anim_death():
    c = Clip("Death", 1.5)
    keyed(c, "Hips", [(0, q(R(6))), (0.25, q(R(-10), R(10))), (0.7, q(R(-55), R(20))), (1.0, q(R(-88), R(25), R(6))), (1.5, q(R(-90), R(25), R(6)))])
    keyed(c, "Hips", [(0, (0, -0.04, 0)), (0.25, (0, -0.1, -0.05)), (0.7, (0, -0.45, -0.25)), (1.0, (0, -0.83, -0.42)), (1.5, (0, -0.84, -0.42))], "pos")
    keyed(c, "Spine", [(0, q(R(8))), (0.25, q(R(-15))), (1.0, q(R(-6))), (1.5, q(R(-4)))])
    keyed(c, "Chest", [(0, q(R(8))), (0.25, q(R(-20), R(10))), (1.0, q(R(-4))), (1.5, q(R(-2)))])
    keyed(c, "Neck", [(0, q(0)), (0.7, q(R(25))), (1.0, q(R(-20))), (1.5, q(R(-12), R(30)))])
    keyed(c, "Head", [(0, q(R(-6))), (0.25, q(R(-30))), (0.9, q(R(20))), (1.05, q(R(-10), R(25))), (1.5, q(R(-5), R(40)))])
    keyed(c, "Jaw", [(0, q(R(10))), (0.25, q(R(40))), (1.5, q(R(32)))])
    for side, sx in (("L", 1), ("R", -1)):
        keyed(c, f"UpperArm.{side}", [(0, arm_q(side, R(60), R(14), R(-20))), (0.25, arm_q(side, R(100), R(40), R(-10))),
                                      (0.7, arm_q(side, R(60), R(70), R(0))), (1.0, arm_q(side, R(20), R(85 if sx > 0 else 60), R(10))),
                                      (1.5, arm_q(side, R(15), R(85 if sx > 0 else 60), R(10)))])
        keyed(c, f"Forearm.{side}", [(0, elbow_q(side, R(20))), (0.7, elbow_q(side, R(40))), (1.0, elbow_q(side, R(25 if sx > 0 else 70))), (1.5, elbow_q(side, R(25 if sx > 0 else 70)))])
        keyed(c, f"Thigh.{side}", [(0, q(0, 0, R(sx * 3))), (0.25, q(R(-20 if sx > 0 else 10), 0, R(sx * 3))), (0.7, q(R(-50 if sx > 0 else -10), 0, R(sx * 8))),
                                   (1.0, q(R(-15 if sx > 0 else -35), 0, R(sx * 12))), (1.5, q(R(-15 if sx > 0 else -35), 0, R(sx * 12)))])
        keyed(c, f"Shin.{side}", [(0, q(R(10))), (0.25, q(R(30 if sx > 0 else 10))), (0.7, q(R(50))), (1.0, q(R(10 if sx > 0 else 55))), (1.5, q(R(10 if sx > 0 else 55)))])
        keyed(c, f"Foot.{side}", [(0, q(0)), (1.0, q(R(30))), (1.5, q(R(30)))])
    return c


def anim_emerge():
    """Clawing up from a crouch (used when a zombie leaves its spawn)."""
    c = Clip("Emerge", 1.4)
    keyed(c, "Hips", [(0, q(R(55))), (0.7, q(R(35))), (1.4, q(R(8)))])
    keyed(c, "Hips", [(0, (0, -0.55, 0.1)), (0.7, (0, -0.35, 0.05)), (1.4, (0, -0.04, 0))], "pos")
    keyed(c, "Spine", [(0, q(R(25))), (1.4, q(R(10)))])
    keyed(c, "Head", [(0, q(R(-40))), (0.7, q(R(-25), R(15))), (1.4, q(R(-6)))])
    keyed(c, "Jaw", [(0, q(R(30))), (0.7, q(R(40))), (1.4, q(R(12)))])
    for side, sx in (("L", 1), ("R", -1)):
        keyed(c, f"Thigh.{side}", [(0, q(R(-95), 0, R(sx * 10))), (0.7, q(R(-60), 0, R(sx * 6))), (1.4, q(0, 0, R(sx * 3)))])
        keyed(c, f"Shin.{side}", [(0, q(R(120))), (0.7, q(R(80))), (1.4, q(R(10)))])
        keyed(c, f"Foot.{side}", [(0, q(R(-20))), (1.4, q(0))])
        keyed(c, f"UpperArm.{side}", [(0, arm_q(side, R(60), R(20))), (0.35, arm_q(side, R(110 if sx > 0 else 40), R(20))),
                                      (0.7, arm_q(side, R(40 if sx > 0 else 120), R(20))), (1.4, arm_q(side, R(65), R(14), R(-20)))])
        keyed(c, f"Forearm.{side}", [(0, elbow_q(side, R(50))), (0.7, elbow_q(side, R(30))), (1.4, elbow_q(side, R(20)))])
    return c


ANIMS = [anim_idle, anim_walk, anim_run, anim_attack, anim_hit, anim_death, anim_emerge]


# ----------------------------------------------------------------------------
# linear-blend skinning in Python (for posed static statues)
# ----------------------------------------------------------------------------

def pose_matrices(pose):
    """pose: bone -> quat (local). Returns skinning matrices bone -> 4x4."""
    world = {}
    for (name, parent, head) in SKEL.joints:
        local = np.eye(4)
        hp = np.array(head)
        pp = np.zeros(3) if parent < 0 else np.array(SKEL.joints[parent][2])
        local[:3, 3] = hp - pp
        if name in pose:
            local = local @ mk.mat_from_quat(pose[name])
        world[name] = local if parent < 0 else world[SKEL.joints[parent][0]] @ local
    skin = {}
    for (name, parent, head) in SKEL.joints:
        ibm = np.eye(4)
        ibm[:3, 3] = -np.array(head)
        skin[BONES[name]] = world[name] @ ibm
    return skin


def apply_pose(mesh, pose):
    M = pose_matrices(pose)
    out = mesh.copy()
    for g in out.groups.values():
        P = np.c_[g["P"], np.ones(len(g["P"]))]
        acc = np.zeros((len(P), 4))
        accn = np.zeros((len(P), 3))
        for k in range(4):
            w = g["W"][:, k]
            if not np.any(w > 0):
                continue
            for j in np.unique(g["J"][:, k]):
                sel = (g["J"][:, k] == j) & (w > 0)
                if not np.any(sel):
                    continue
                acc[sel] += (P[sel] @ M[j].T) * w[sel, None]
                accn[sel] += (g["N"][sel] @ M[j][:3, :3].T) * w[sel, None]
        g["P"] = acc[:, :3]
        ln = np.linalg.norm(accn, axis=1, keepdims=True)
        ln[ln == 0] = 1
        g["N"] = accn / ln
    return out


# ----------------------------------------------------------------------------
# writers
# ----------------------------------------------------------------------------

def write_zombie(name, variant, seed):
    body = build_body(variant, False, seed)
    s = mk.Scene()
    s.skeleton = SKEL
    s.add(mk.Node("Body", body, skinned=True))
    for fn in ANIMS:
        s.animations.append(fn().to_anim())
    size = s.write_glb(os.path.join(OUT, name + ".glb"))
    print(name, f"{size / 1e6:.2f} MB", body.tri_count(), "tris")


def write_statue(name, variant, pose, props):
    body = build_body(variant, True)
    posed = apply_pose(body, pose)
    posed.material("marble")
    for p in props:
        posed.add(p.material("marble"))
    # plinth
    pl = mk.Mesh()
    pl.add(mk.box(0.9, 0.12, 0.7, bevel=0.03, material="stone_plain").translate(0, -0.06, 0))
    posed.translate(0, 0.0, 0)
    posed.add(pl)
    posed.color_fn(lambda P, N: 0.75 + 0.25 * np.clip(P[:, 1] / 1.8, 0, 1))
    posed.jitter(0.002, 3)
    s = mk.Scene()
    s.add(mk.Node("Statue", posed.scale(1.25)))
    size = s.write_glb(os.path.join(OUT, name + ".glb"))
    print(name, f"{size / 1e6:.2f} MB", posed.tri_count(), "tris")


def hand_world(pose, side):
    M = pose_matrices(pose)
    j = BONES[f"Hand.{side}"]
    head = JPOS[f"Hand.{side}"]
    return M[j] @ mk.mat_translate(head)


def main():
    os.makedirs(OUT, exist_ok=True)
    write_zombie("zombie_legionary", "legionary", 1)
    write_zombie("zombie_gladiator", "gladiator", 2)
    # statue 1: legionary saluting with raised gladius
    pose1 = {
        "UpperArm.R": arm_q("R", R(150), R(25), R(0)),
        "Forearm.R": elbow_q("R", R(15)),
        "UpperArm.L": arm_q("L", R(35), R(10), R(-30)),
        "Forearm.L": elbow_q("L", R(70)),
        "Head": q(R(-8), R(-15), 0),
        "Thigh.L": q(R(-10), 0, R(4)),
        "Shin.L": q(R(8)),
        "Thigh.R": q(R(6), 0, R(-3)),
    }
    sword = gladius()
    Mh = hand_world(pose1, "R")
    d = Mh[:3, :3] @ np.array([-SA, -CA, 0])
    sword_m = sword.copy().transform(mk.look_basis(d))
    sword_m.translate(*(Mh[:3, 3] + d * 0.09))
    shield = parma()
    ML = hand_world(pose1, "L")
    shield.rotate((0, 1, 0), 0.9).translate(*(ML[:3, 3] + np.array([0.12, 0.02, 0.05])))
    write_statue("statue_legionary", "legionary", pose1, [sword_m, shield])
    # statue 2: gladiator victorious, sword pointed down
    pose2 = {
        "UpperArm.R": arm_q("R", R(40), R(20), R(0)),
        "Forearm.R": elbow_q("R", R(45)),
        "UpperArm.L": arm_q("L", R(120), R(60), R(0)),
        "Forearm.L": elbow_q("L", R(30)),
        "Head": q(R(-15), R(20), 0),
        "Chest": q(R(-5), R(-10), 0),
        "Thigh.R": q(R(-25), 0, R(-6)),
        "Shin.R": q(R(30)),
    }
    Mh = hand_world(pose2, "R")
    d = Mh[:3, :3] @ np.array([-SA, -CA, 0])
    s2 = gladius().transform(mk.look_basis(d)).translate(*(Mh[:3, 3] + d * 0.09))
    write_statue("statue_gladiator", "gladiator", pose2, [s2])


if __name__ == "__main__":
    main()
