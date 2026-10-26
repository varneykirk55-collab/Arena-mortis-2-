"""
Arena Mortis - weapons and first-person arms.

Weapon space: forward = -Z, up = +Y, origin = where the right hand grips.
Each weapon GLB contains named nodes the game uses:
  Slide / Bolt   - kicked back on fire
  Magazine       - dropped/raised during reload
  Muzzle         - empty marker at the barrel tip (muzzle flash / tracer start)
  RightHand      - empty marker for the right glove
  LeftHand       - empty marker for the left glove
  Core           - (Jupiter) glowing element animated by script
"""
import math
import os
import sys

import numpy as np

import meshkit as mk

OUT = sys.argv[1] if len(sys.argv) > 1 else "../../assets/models"


def side(poly, thick, mat, x=0.0, bevel=0.0):
    """Extrude a side profile given as (u=forward, v=up) to thickness along X."""
    m = mk.extrude(poly, thick, mat, bevel=bevel)
    m.rotate((0, 1, 0), math.pi / 2)
    return m.translate(x, 0, 0)


def barrel(r, length, mat, z0, y, seg=14, r2=None):
    """Cylinder along -Z starting at z0 going forward by length."""
    c = mk.cylinder(r, length, seg, mat, r2=r2)
    c.rotate((1, 0, 0), -math.pi / 2)  # +Y -> -Z
    return c.translate(0, y, z0)


def boxm(sx, sy, sz, cx, cy, cz, mat, bevel=0.002):
    return mk.box(sx, sy, sz, bevel=bevel, material=mat).translate(cx, cy, cz)


def empty(name, pos, rot=(0, 0, 0, 1)):
    return mk.Node(name, None, tuple(pos), tuple(rot))


# ----------------------------------------------------------------------------
# M1911-style pistol
# ----------------------------------------------------------------------------

def pistol():
    frame = mk.Mesh()
    # frame (dust cover + trigger guard + grip)
    frame.add(side([(-0.035, 0.0), (0.12, 0.0), (0.12, 0.022), (0.02, 0.022), (-0.04, 0.02)], 0.026, "gun_metal", bevel=0.002))
    guard = [(0.0, 0.0), (0.006, -0.004), (0.055, -0.004), (0.06, -0.012), (0.058, -0.04), (0.05, -0.048), (0.0, -0.048),
             (0.0, -0.04), (0.048, -0.04), (0.05, -0.012), (0.004, -0.012)]
    frame.add(side(guard, 0.012, "gun_metal"))
    grip_poly = [(-0.035, 0.012), (0.012, 0.012), (0.004, -0.05), (-0.006, -0.105), (-0.05, -0.105), (-0.052, -0.06), (-0.045, 0.0)]
    frame.add(side(grip_poly, 0.028, "gun_metal", bevel=0.002))
    for sx in (-1, 1):
        panel = [(-0.03, 0.002), (0.003, 0.002), (-0.003, -0.05), (-0.011, -0.095), (-0.044, -0.095), (-0.046, -0.05), (-0.04, -0.005)]
        frame.add(side(panel, 0.006, "gun_wood", x=sx * 0.016, bevel=0.0015))
        for i in range(3):
            frame.add(mk.sphere(0.003, 6, 4, "gold").translate(sx * 0.019, -0.02 - i * 0.03, 0.025))
    frame.add(side([(0.012, -0.005), (0.02, -0.006), (0.026, -0.03), (0.02, -0.032)], 0.006, "gun_metal"))  # trigger
    frame.add(side([(-0.052, 0.02), (-0.04, 0.03), (-0.035, 0.04), (-0.05, 0.045), (-0.06, 0.03)], 0.012, "gun_metal"))  # beavertail
    frame.add(side([(-0.035, 0.03), (-0.028, 0.045), (-0.035, 0.052), (-0.042, 0.04)], 0.008, "gun_metal"))  # hammer

    slide = mk.Mesh()
    slide.add(side([(-0.055, 0.02), (0.13, 0.02), (0.13, 0.05), (0.122, 0.056), (-0.048, 0.056), (-0.055, 0.05)], 0.027, "gun_metal", bevel=0.0025))
    for i in range(9):  # rear serrations
        slide.add(boxm(0.0285, 0.024, 0.0025, 0, 0.038, -(-0.05 + i * 0.006), "gun_metal", 0))
    slide.add(boxm(0.006, 0.008, 0.008, 0, 0.06, -0.12, "gun_metal", 0.001))   # front sight
    slide.add(boxm(0.02, 0.008, 0.008, 0, 0.06, 0.04, "gun_metal", 0.001))     # rear sight
    slide.add(boxm(0.0285, 0.016, 0.03, 0.0, 0.045, -0.02, "gun_polymer", 0.0005))  # ejection port shadow
    slide.add(barrel(0.0075, 0.006, "gun_metal", -0.13, 0.037))
    slide.add(barrel(0.0055, 0.004, "coal", -0.134, 0.037))

    mag = mk.Mesh()
    mag.add(boxm(0.022, 0.1, 0.03, 0, -0.05, 0.022, "gun_metal", 0.002))
    mag.add(boxm(0.026, 0.008, 0.036, 0, -0.103, 0.022, "gun_polymer", 0.002))

    s = mk.Scene()
    root = mk.Node("Pistol", frame)
    root.children.append(mk.Node("Slide", slide))
    root.children.append(mk.Node("Magazine", mag))
    root.children.append(empty("Muzzle", (0, 0.037, -0.14)))
    root.children.append(empty("RightHand", (0, 0.004, 0.024), mk.quat_axis((1, 0, 0), math.radians(-14))))
    root.children.append(empty("LeftHand", (-0.012, -0.03, 0.03), mk.quat_axis((1, 0, 0), math.radians(-14))))
    s.add(root)
    return s


def _flip_side_parts(mesh):
    """side() builds with forward = +Z after rotation; boxes were placed with
    explicit -Z coordinates. Normalise: anything built via side() is mirrored."""
    # side() maps u -> -z already (rotation about Y by +90 maps x->-z), so no-op.
    return mesh


# ----------------------------------------------------------------------------
# M4 carbine
# ----------------------------------------------------------------------------

def m4():
    body = mk.Mesh()
    # upper receiver
    body.add(side([(-0.08, 0.0), (0.16, 0.0), (0.16, 0.045), (-0.08, 0.045)], 0.034, "gun_metal", bevel=0.003))
    # picatinny rail on top of upper
    body.add(boxm(0.022, 0.008, 0.24, 0, 0.049, -0.04, "gun_metal", 0.001))
    for i in range(16):
        body.add(boxm(0.024, 0.004, 0.006, 0, 0.055, 0.075 - i * 0.015, "gun_metal", 0))
    # forward assist + ejection port + charging handle
    body.add(barrel(0.007, 0.03, "gun_metal", 0.0, 0.03).rotate((0, 1, 0), 0.0).translate(0.02, 0, 0.0))
    body.add(boxm(0.002, 0.02, 0.05, 0.0175, 0.025, -0.02, "gun_polymer", 0))
    body.add(boxm(0.03, 0.01, 0.025, 0, 0.05, 0.09, "gun_metal", 0.002))
    # lower receiver + mag well + trigger guard
    body.add(side([(-0.07, 0.0), (0.06, 0.0), (0.075, -0.02), (0.075, -0.045), (0.035, -0.045), (0.03, -0.02), (-0.04, -0.02), (-0.07, -0.015)],
                  0.032, "gun_metal", bevel=0.003))
    body.add(side([(-0.035, -0.02), (0.03, -0.02), (0.032, -0.03), (-0.033, -0.03)], 0.012, "gun_metal"))
    body.add(side([(-0.02, -0.022), (-0.012, -0.022), (-0.008, -0.045), (-0.015, -0.046)], 0.006, "gun_metal"))  # trigger
    # pistol grip (polymer, angled)
    body.add(side([(-0.04, -0.015), (-0.005, -0.015), (-0.03, -0.11), (-0.065, -0.11), (-0.06, -0.06)], 0.03, "gun_polymer", bevel=0.004))
    # handguard (quad rail)
    hg = mk.Mesh()
    hg.add(boxm(0.05, 0.05, 0.25, 0, 0.022, -0.29, "gun_polymer", 0.006))
    for (cx, cy, sx, sy) in ((0, 0.05, 0.02, 0.008), (0, -0.006, 0.02, 0.008), (0.027, 0.022, 0.008, 0.02), (-0.027, 0.022, 0.008, 0.02)):
        hg.add(boxm(sx, sy, 0.24, cx, cy, -0.29, "gun_metal", 0.001))
        for i in range(14):
            dz = -0.18 - i * 0.016
            if sx > sy:
                hg.add(boxm(sx + 0.004, 0.004, 0.006, cx, cy + (0.005 if cy > 0.02 else -0.005), dz, "gun_metal", 0))
            else:
                hg.add(boxm(0.004, sy + 0.004, 0.006, cx + (0.005 if cx > 0 else -0.005), cy, dz, "gun_metal", 0))
    body.add(hg)
    # barrel, front sight post, flash hider
    body.add(barrel(0.0095, 0.34, "gun_metal", -0.16, 0.022))
    body.add(side([(0.0, 0.0), (0.03, 0.0), (0.025, 0.07), (0.018, 0.075), (0.01, 0.07)], 0.012, "gun_metal").translate(0, 0.02, -0.43))
    body.add(barrel(0.012, 0.05, "gun_metal", -0.5, 0.022))
    for i in range(4):
        a = i * math.pi / 2 + math.pi / 4
        body.add(boxm(0.004, 0.004, 0.035, math.cos(a) * 0.012, 0.022 + math.sin(a) * 0.012, -0.535, "coal", 0))
    body.add(barrel(0.008, 0.005, "coal", -0.551, 0.022))
    # buffer tube + collapsible stock (extends backwards, +Z)
    body.add(barrel(0.015, 0.2, "gun_metal", 0.28, 0.025))
    stock = mk.Mesh()
    stock.add(side([(0.0, 0.0), (-0.16, 0.0), (-0.2, -0.05), (-0.2, -0.075), (-0.17, -0.08), (-0.02, -0.03), (0.0, -0.03)], 0.04, "gun_polymer", bevel=0.004).translate(0, 0.045, 0))
    stock.add(side([(0.0, 0.0), (-0.17, 0.0), (-0.17, 0.042), (0.0, 0.042)], 0.042, "gun_polymer", bevel=0.004).translate(0, 0.006, 0))
    stock.add(boxm(0.045, 0.135, 0.02, 0, -0.008, 0.2, "gun_polymer", 0.003))
    body.add(stock.translate(0, 0, 0.12))
    # reflex sight: base, open hood frame, tinted glass and an emissive dot
    optic = mk.Mesh()
    optic.add(boxm(0.03, 0.012, 0.06, 0, 0.062, 0.0, "gun_metal", 0.002))
    for (sx, sy, cx, cy) in ((0.044, 0.006, 0, 0.112), (0.006, 0.044, -0.019, 0.09), (0.006, 0.044, 0.019, 0.09), (0.044, 0.006, 0, 0.068)):
        optic.add(boxm(sx, sy, 0.05, cx, cy, -0.005, "gun_metal", 0.001))
    optic.add(boxm(0.034, 0.038, 0.002, 0, 0.09, -0.02, "gun_lens", 0))
    optic.add(boxm(0.0016, 0.0016, 0.001, 0, 0.09, -0.0215, "glow_red", 0))
    body.add(optic.translate(0, 0, 0.03))

    mag = mk.Mesh()
    # curved STANAG magazine below the mag well (u 0.038..0.073)
    left = [(0.036 + 0.04 * (i / 6) ** 1.6, -0.015 - i / 6 * 0.17) for i in range(7)]
    right = [(x + 0.036, y) for (x, y) in left]
    mag.add(side(right + left[::-1], 0.024, "gun_metal", bevel=0.002))
    mag.add(boxm(0.028, 0.012, 0.042, 0, -0.19, -(0.054 + 0.04), "gun_polymer", 0.003))
    bolt = boxm(0.006, 0.014, 0.05, 0.016, 0.028, -0.02, "gun_metal", 0.001)

    s = mk.Scene()
    root = mk.Node("M4", body)
    root.children.append(mk.Node("Magazine", mag.translate(0, 0, 0.0)))
    root.children.append(mk.Node("Bolt", bolt))
    root.children.append(empty("Muzzle", (0, 0.022, -0.56)))
    root.children.append(empty("RightHand", (0, -0.016, 0.022), mk.quat_axis((1, 0, 0), math.radians(-15))))
    root.children.append(empty("LeftHand", (0, 0.022, -0.29)))
    root.children.append(empty("Sight", (0, 0.092, 0.03)))
    s.add(root)
    return s


# ----------------------------------------------------------------------------
# JUPITER - lightning wonder weapon
# ----------------------------------------------------------------------------

def jupiter():
    body = mk.Mesh()
    # main bronze housing: lathe body along Z (tapering forward)
    prof = [(0.001, 0.0), (0.045, 0.0), (0.055, 0.03), (0.058, 0.12), (0.05, 0.2), (0.042, 0.3), (0.036, 0.36), (0.001, 0.36)]
    hous = mk.lathe(prof, 20, "gun_bronze")
    hous.rotate((1, 0, 0), -math.pi / 2).translate(0, 0.03, 0.12)
    body.add(hous)
    # rings / coils along the barrel
    for i in range(5):
        r = 0.05 - i * 0.003
        t = mk.torus(r, 0.007, 20, 6, "gold").rotate((1, 0, 0), math.pi / 2).translate(0, 0.03, -0.02 - i * 0.05)
        body.add(t)
    # trident / thunderbolt prongs at the muzzle
    for (ang, L) in ((0, 0.16), (2.1, 0.12), (4.2, 0.12)):
        pts = []
        for k in range(5):
            z = -0.24 - k * L / 4
            zig = 0.018 * (1 if k % 2 else -1) * (k > 0)
            rr = 0.024 + 0.01 * k / 4
            pts.append((math.cos(ang) * rr + zig * math.cos(ang + math.pi / 2), 0.03 + math.sin(ang) * rr + zig * math.sin(ang + math.pi / 2), z))
        body.add(mk.tube(pts, [0.008, 0.007, 0.006, 0.005, 0.002], 6, "gold"))
    # stylised eagle wings: feathered fins flaring up and back from the housing
    wing = [(0.02, 0.0), (-0.01, 0.03), (-0.045, 0.05), (-0.085, 0.055), (-0.07, 0.04), (-0.1, 0.036), (-0.075, 0.025),
            (-0.09, 0.015), (-0.06, 0.007), (-0.04, 0.0)]
    for sx in (-1, 1):
        w = side(wing, 0.008, "gold", bevel=0.002)
        w.rotate((0, 0, 1), -sx * 0.5).rotate((0, 1, 0), sx * 0.1).translate(sx * 0.05, 0.045, 0.02)
        body.add(w)
    # eagle head at the top front
    head = mk.ellipsoid(0.025, 0.022, 0.035, 12, 8, "gold").translate(0, 0.09, -0.08)
    beak = mk.hull([(-0.008, 0.095, -0.11), (0.008, 0.095, -0.11), (0, 0.085, -0.135), (0, 0.1, -0.105)], "gold")
    body.add(head)
    body.add(beak)
    body.add(mk.box(0.02, 0.03, 0.05, bevel=0.005, material="gun_bronze").translate(0, 0.07, -0.06))
    for sx in (-1, 1):
        body.add(mk.sphere(0.004, 6, 4, "glow_blue").translate(sx * 0.017, 0.096, -0.095))
    # laurel wreath ring around the housing
    for i in range(14):
        a = 2 * math.pi * i / 14
        leaf = mk.ellipsoid(0.006, 0.018, 0.004, 6, 4, "gold").rotate((0, 0, 1), a + 0.6)
        leaf.translate(math.cos(a) * 0.062, 0.03 + math.sin(a) * 0.062, 0.1)
        body.add(leaf)
    # grip (wood) and trigger guard
    body.add(side([(-0.035, 0.0), (0.0, 0.0), (-0.025, -0.11), (-0.06, -0.11), (-0.055, -0.05)], 0.032, "gun_wood", bevel=0.004))
    body.add(side([(0.0, -0.005), (0.07, -0.005), (0.07, 0.0), (0.075, -0.015), (0.06, -0.05), (0.0, -0.05), (0.0, -0.042),
                   (0.055, -0.042), (0.064, -0.016), (0.0, -0.012)], 0.012, "gun_bronze"))
    body.add(side([(0.01, -0.01), (0.018, -0.01), (0.024, -0.035), (0.017, -0.036)], 0.006, "gold"))
    # stock: short curved bronze piece with a lightning engraving
    body.add(side([(-0.04, 0.06), (-0.22, 0.04), (-0.27, -0.02), (-0.27, -0.07), (-0.24, -0.08), (-0.2, -0.03), (-0.06, 0.0)], 0.036, "gun_bronze", bevel=0.004))
    bolt_poly = [(-0.2, 0.0), (-0.16, 0.025), (-0.15, 0.01), (-0.1, 0.03), (-0.13, 0.0), (-0.12, 0.012), (-0.17, -0.01)]
    for sx in (-1, 1):
        body.add(side(bolt_poly, 0.004, "glow_blue", x=sx * 0.019))

    # glowing core: glass tube on top with inner lightning filament
    core = mk.Mesh()
    core.add(mk.cylinder(0.011, 0.12, 12, "glow_blue").rotate((1, 0, 0), -math.pi / 2).translate(0, 0.078, 0.11))
    for i in range(3):
        core.add(mk.torus(0.014, 0.003, 12, 4, "gold").rotate((1, 0, 0), math.pi / 2).translate(0, 0.078, 0.1 - i * 0.045))
    core.add(mk.sphere(0.012, 10, 6, "gold").translate(0, 0.078, 0.115))
    # energy cell (magazine) below the housing
    cell = mk.Mesh()
    cell.add(mk.cylinder(0.022, 0.08, 12, "gun_bronze").translate(0, -0.1, 0.0).translate(0, 0, 0.0))
    cell.add(mk.cylinder(0.016, 0.07, 12, "glow_blue").translate(0, -0.095, 0.0))
    cell.add(mk.torus(0.022, 0.005, 12, 4, "gold").translate(0, -0.02, 0))
    cell.translate(0, 0.0, 0.07)

    s = mk.Scene()
    root = mk.Node("Jupiter", body)
    root.children.append(mk.Node("Core", core))
    root.children.append(mk.Node("Magazine", cell))
    root.children.append(empty("Muzzle", (0, 0.03, -0.4)))
    root.children.append(empty("RightHand", (0, -0.002, 0.02), mk.quat_axis((1, 0, 0), math.radians(-15))))
    root.children.append(empty("LeftHand", (0, -0.0, -0.11)))
    s.add(root)
    return s


# ----------------------------------------------------------------------------
# First-person gloved arms
# ----------------------------------------------------------------------------

def grip_hand(radius=0.016):
    """Right glove closed around a grip whose axis is local -Y, grip centre at
    the origin. Palm on +X side, fingers wrap round the front (-Z)."""
    m = mk.Mesh()
    r = radius
    palm = mk.hull([(r, 0.005, -0.022), (r, 0.005, 0.034), (r, -0.09, -0.02), (r, -0.09, 0.03),
                    (r + 0.024, 0.0, -0.02), (r + 0.026, 0.0, 0.03), (r + 0.022, -0.085, -0.018), (r + 0.024, -0.085, 0.028)], "glove")
    m.add(palm)
    for i in range(4):
        y = -0.012 - i * 0.022
        pts = [(r + 0.008, y, -0.016), (r * 0.6, y, -r - 0.018), (-r * 0.4, y, -r - 0.02), (-r - 0.008, y, -r * 0.6 - 0.004),
               (-r - 0.008, y, 0.002)]
        m.add(mk.tube(pts, [0.0108, 0.0104, 0.01, 0.0095, 0.0088], 7, "glove"))
    thumb = [(r + 0.01, 0.0, 0.012), (r * 0.2, 0.012, -0.002), (-r - 0.004, 0.01, -0.012), (-r - 0.01, -0.004, -0.024)]
    m.add(mk.tube(thumb, [0.013, 0.012, 0.0105, 0.009], 7, "glove"))
    return m


def sleeve(points, radii):
    m = mk.Mesh()
    m.add(mk.tube(points[:2], [radii[0] * 0.95, radii[0]], 12, "glove"))
    m.add(mk.tube(points[1:], radii[1:], 12, "sleeve"))
    # cuff seam
    return m


def arms():
    s = mk.Scene()
    right = grip_hand()
    right.add(sleeve([(0.026, 0.0, 0.028), (0.035, -0.03, 0.07), (0.06, -0.1, 0.13), (0.09, -0.2, 0.18), (0.12, -0.32, 0.22)],
                     [0.032, 0.037, 0.041, 0.045, 0.048]))
    s.add(mk.Node("RightArm", right))
    # left support hand around a horizontal (Z) axis: build vertical then rotate
    left = grip_hand(0.03).scale((-1, 1, 1))
    left.rotate((1, 0, 0), math.pi / 2).rotate((0, 0, 1), -0.4)
    left.add(sleeve([(-0.03, -0.04, 0.03), (-0.06, -0.1, 0.08), (-0.11, -0.2, 0.14), (-0.16, -0.32, 0.18), (-0.2, -0.44, 0.2)],
                    [0.032, 0.037, 0.041, 0.045, 0.048]))
    s.add(mk.Node("LeftArmRifle", left))
    # left hand for pistols: cups under/around the right hand
    lp = grip_hand(0.03).scale((-1, 1, 1))
    lp.add(sleeve([(-0.03, 0.0, 0.028), (-0.045, -0.04, 0.06), (-0.08, -0.12, 0.1), (-0.11, -0.24, 0.13), (-0.13, -0.36, 0.15)],
                  [0.032, 0.037, 0.041, 0.045, 0.048]))
    s.add(mk.Node("LeftArmPistol", lp))
    return s


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("weapon_pistol", pistol), ("weapon_m4", m4), ("weapon_jupiter", jupiter), ("viewmodel_arms", arms)):
        sc = fn()
        size = sc.write_glb(os.path.join(OUT, name + ".glb"))
        print(name, f"{size / 1e3:.0f} KB")


if __name__ == "__main__":
    main()
