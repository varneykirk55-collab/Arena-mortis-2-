"""
Arena Mortis - props and machines: Mystery Box, Pack-a-Punch, braziers,
torch sconces, banners, floor debris.
"""
import math
import os
import sys

import numpy as np

import meshkit as mk
import build_characters as bc

OUT = sys.argv[1] if len(sys.argv) > 1 else "../../assets/models"


def empty(name, pos, rot=(0, 0, 0, 1)):
    return mk.Node(name, None, tuple(pos), tuple(rot))


# ----------------------------------------------------------------------------
# Mystery Box
# ----------------------------------------------------------------------------

def question_mark(size=0.22, mat="glow_question", thick=0.025):
    """'?' glyph built from a square-section tube (centred, in the XY plane)."""
    s = size
    path = []
    for i in range(15):
        a = math.radians(170 - i * 200 / 14)
        path.append((math.cos(a) * s * 0.32, s * 0.25 + math.sin(a) * s * 0.3, 0))
    path += [(-s * 0.02, -s * 0.05, 0), (0.0, -s * 0.18, 0)]
    m = mk.tube(path, thick * s * 3.2, 4, mat)
    m.add(mk.box(thick * s * 6.5, thick * s * 6.5, thick * s * 6.5, bevel=0.005, material=mat).translate(0, -s * 0.38, 0))
    return m


def mystery_box():
    W, D, H = 1.15, 0.58, 0.5
    body = mk.Mesh()
    # planked walls: 4 sides made of horizontal planks
    planks = 4
    for i in range(planks):
        y = 0.04 + (H - 0.06) * (i + 0.5) / planks
        ph = (H - 0.06) / planks * 0.94
        for (sx, sz, cx, cz) in ((W, 0.04, 0, D / 2 - 0.02), (W, 0.04, 0, -D / 2 + 0.02), (0.04, D - 0.08, W / 2 - 0.02, 0), (0.04, D - 0.08, -W / 2 + 0.02, 0)):
            p = mk.box(sx, ph, sz, bevel=0.008, material="wood_box").translate(cx, y, cz)
            p.jitter(0.002, i * 7 + int(cx * 10 + 5))
            body.add(p)
    body.add(mk.box(W - 0.06, 0.03, D - 0.06, material="wood_box").translate(0, 0.03, 0))
    # iron corner brackets + bands + feet
    for sx in (-1, 1):
        for sz in (-1, 1):
            body.add(mk.box(0.07, H + 0.01, 0.07, bevel=0.01, material="iron").translate(sx * (W / 2 - 0.02), H / 2, sz * (D / 2 - 0.02)))
            body.add(mk.box(0.1, 0.05, 0.1, bevel=0.01, material="iron").translate(sx * (W / 2 - 0.02), 0.0, sz * (D / 2 - 0.02)))
    for x in (-W * 0.3, W * 0.3):
        for (sz,) in ((1,), (-1,)):
            body.add(mk.box(0.07, H, 0.014, bevel=0.004, material="iron").translate(x, H / 2, sz * (D / 2 + 0.002)))
    # rivets
    for x in (-W * 0.3, W * 0.3):
        for k in range(4):
            for sz in (-1, 1):
                body.add(mk.sphere(0.008, 6, 4, "iron").translate(x, 0.08 + k * 0.12, sz * (D / 2 + 0.01)))
    # bronze ring handles on the ends
    for sx in (-1, 1):
        body.add(mk.torus(0.06, 0.009, 16, 6, "bronze").rotate((0, 0, 1), math.pi / 2).translate(sx * (W / 2 + 0.035), H * 0.55, 0))
        body.add(mk.box(0.03, 0.06, 0.06, bevel=0.008, material="bronze").translate(sx * (W / 2 + 0.01), H * 0.68, 0))
    # glowing question marks on front/back and ends
    for sz in (-1, 1):
        q = question_mark(0.34)
        if sz < 0:
            q.rotate((0, 1, 0), math.pi)
        body.add(q.translate(0, H * 0.5, sz * (D / 2 + 0.012)))
    for sx in (-1, 1):
        q = question_mark(0.2).rotate((0, 1, 0), sx * math.pi / 2)
        body.add(q.translate(sx * (W / 2 + 0.012), H * 0.5, 0.0) if False else mk.Mesh())
    # inner glow plane (visible when the lid is open)
    body.add(mk.box(W - 0.12, 0.02, D - 0.12, material="glow_orange").translate(0, H - 0.12, 0))
    body.color_fn(lambda P, N: 0.75 + 0.25 * np.clip(P[:, 1] / H, 0, 1))

    lid = mk.Mesh()
    # barrel-vaulted lid: half-ellipse profile in (z, y) extruded across the box width
    LH = 0.2
    arc = [((D / 2 + 0.02) * math.cos(math.pi * i / 16), LH * math.sin(math.pi * i / 16)) for i in range(17)]
    inner = [((D / 2 - 0.02) * math.cos(math.pi * i / 16), (LH - 0.035) * math.sin(math.pi * i / 16)) for i in range(16, -1, -1)]
    shell = mk.extrude(arc + inner, W + 0.02, "wood_box")
    shell.rotate((0, 1, 0), math.pi / 2)  # extrusion along X; profile x -> -z
    lid.add(shell)
    cap_poly = [((D / 2 - 0.02) * math.cos(math.pi * i / 16), (LH - 0.035) * math.sin(math.pi * i / 16)) for i in range(17)]
    for sx in (-1, 1):
        lid.add(mk.extrude(cap_poly, 0.025, "wood_box").rotate((0, 1, 0), math.pi / 2).translate(sx * (W / 2 - 0.0125), 0, 0))
    for x in (-W * 0.3, W * 0.3, -W / 2 + 0.02, W / 2 - 0.02):
        oarc = [((D / 2 + 0.032) * math.cos(math.pi * i / 16), (LH + 0.012) * math.sin(math.pi * i / 16)) for i in range(17)]
        iarc = [((D / 2 + 0.012) * math.cos(math.pi * i / 16), (LH - 0.004) * math.sin(math.pi * i / 16)) for i in range(16, -1, -1)]
        band = mk.extrude(oarc + iarc, 0.06, "iron").rotate((0, 1, 0), math.pi / 2).translate(x, 0, 0)
        lid.add(band)
    q = question_mark(0.22).rotate((1, 0, 0), -math.pi / 2 + 0.0).translate(0, LH + 0.006, 0)
    lid.add(q)
    # move lid so its pivot (back edge) is at the origin
    lid.translate(0, 0, D / 2)

    s = mk.Scene()
    root = mk.Node("MysteryBox-convcol", body)
    root.children.append(mk.Node("Lid", lid, translation=(0, H, -D / 2)))
    root.children.append(empty("WeaponAnchor", (0, H + 0.35, 0)))
    s.add(root)
    return s


# ----------------------------------------------------------------------------
# Pack-a-Punch: the "Forge of Vulcan"
# ----------------------------------------------------------------------------

def gear(r, teeth, depth, mat):
    pts = []
    for i in range(teeth * 2):
        a0 = 2 * math.pi * i / (teeth * 2)
        rr = r if i % 2 == 0 else r * 0.82
        for k in range(2):
            a = a0 + (k * 0.6 + 0.2) * math.pi / teeth
            pts.append((rr * math.cos(a), rr * math.sin(a)))
    g = mk.extrude(pts, depth, mat)
    g.add(mk.cylinder(r * 0.3, depth * 1.4, 12, mat).rotate((1, 0, 0), math.pi / 2).translate(0, 0, -depth * 0.7))
    return g


def pack_a_punch():
    m = mk.Mesh()
    # stepped stone base
    m.add(mk.box(2.6, 0.2, 1.9, bevel=0.03, material="stone_plain").translate(0, 0.1, 0))
    m.add(mk.box(2.3, 0.2, 1.6, bevel=0.03, material="stone_plain").translate(0, 0.3, 0))
    # main bronze housing (chamfered)
    m.add(mk.box(1.8, 1.3, 1.1, bevel=0.08, material="bronze").translate(0, 1.05, 0))
    m.add(mk.box(1.9, 0.12, 1.2, bevel=0.03, material="gold").translate(0, 0.45, 0))
    m.add(mk.box(1.9, 0.12, 1.2, bevel=0.03, material="gold").translate(0, 1.72, 0))
    # side pillars (fluted bronze columns with capitals)
    for sx in (-1, 1):
        col = mk.lathe([(0.13, 0.4), (0.11, 0.5), (0.1, 1.7), (0.13, 1.8), (0.16, 1.86)], 14, "bronze")
        m.add(col.translate(sx * 1.0, 0, 0.45))
        m.add(mk.box(0.36, 0.1, 0.36, bevel=0.02, material="gold").translate(sx * 1.0, 1.9, 0.45))
    # front: weapon slot (dark) with rollers
    m.add(mk.box(0.9, 0.16, 0.06, material="void").translate(0, 0.75, 0.53))
    m.add(mk.box(1.0, 0.26, 0.05, bevel=0.02, material="iron").translate(0, 0.75, 0.52).scale((1, 1, 1)) if False else mk.Mesh())
    for sy in (0.66, 0.84):
        m.add(mk.cylinder(0.03, 0.96, 10, "iron").rotate((0, 0, 1), math.pi / 2).translate(0.48, sy, 0.56))
    # chimney stacks with grills
    for sx in (-0.55, 0.55):
        m.add(mk.cylinder(0.12, 0.7, 12, "iron", r2=0.1).translate(sx, 1.75, -0.3))
        m.add(mk.torus(0.12, 0.025, 12, 5, "bronze").translate(sx, 2.43, -0.3))
        m.add(mk.cylinder(0.08, 0.04, 10, "glow_ember").translate(sx, 2.42, -0.3))
    # pipes along the sides
    for sx in (-1, 1):
        pts = [(sx * 0.9, 0.6, -0.3), (sx * 1.08, 0.7, -0.3), (sx * 1.1, 1.3, -0.25), (sx * 0.95, 1.55, -0.1)]
        m.add(mk.tube(pts, 0.045, 10, "bronze"))
        for p in pts[1:3]:
            m.add(mk.torus(0.05, 0.012, 10, 4, "gold").translate(*p))
    # anvil on top
    anv = mk.Mesh()
    anv.add(mk.box(0.5, 0.15, 0.25, bevel=0.02, material="iron").translate(0, 0.075, 0))
    anv.add(mk.tapered_box((0.3, 0.2), (0.18, 0.14), 0.15, material="iron").translate(0, 0.15, 0))
    anv.add(mk.box(0.7, 0.12, 0.26, bevel=0.03, material="iron").translate(0.05, 0.36, 0))
    anv.add(mk.hull([(0.4, 0.3, -0.1), (0.4, 0.42, -0.1), (0.4, 0.3, 0.1), (0.4, 0.42, 0.1), (0.62, 0.4, 0)], "iron"))
    m.add(anv.translate(0, 1.78, 0.1))
    # hammer resting on the anvil
    m.add(mk.cylinder(0.025, 0.55, 8, "wood_box").rotate((0, 0, 1), 1.2).translate(-0.05, 2.25, 0.1))
    m.add(mk.box(0.12, 0.2, 0.12, bevel=0.02, material="iron").rotate((0, 0, 1), 1.2).translate(-0.35, 2.33, 0.1))
    m.color_fn(lambda P, N: 0.7 + 0.3 * np.clip(P[:, 1] / 2.0, 0, 1))

    # front medallion: ring + glowing disc + crossed hammers (animated "Disc")
    medal = mk.Mesh()
    medal.add(mk.torus(0.42, 0.06, 32, 8, "gold").rotate((1, 0, 0), math.pi / 2))
    for i in range(16):
        a = 2 * math.pi * i / 16
        medal.add(mk.box(0.05, 0.08, 0.05, bevel=0.01, material="gold").rotate((0, 0, 1), a).translate(math.cos(a) * 0.5, math.sin(a) * 0.5, 0))
    disc = mk.Mesh()
    disc.add(mk.cylinder(0.38, 0.03, 32, "glow_orange").rotate((1, 0, 0), math.pi / 2))
    for sgn in (-1, 1):
        h = mk.Mesh()
        h.add(mk.box(0.05, 0.5, 0.04, bevel=0.01, material="iron"))
        h.add(mk.box(0.2, 0.1, 0.06, bevel=0.015, material="iron").translate(0, 0.25, 0))
        disc.add(h.rotate((0, 0, 1), sgn * 0.7).translate(0, -0.02, 0.04))
    # lightning bolt over the hammers
    bolt = [(-0.04, 0.2), (0.06, 0.03), (0.0, 0.03), (0.05, -0.2), (-0.06, -0.01), (0.0, -0.01)]
    disc.add(mk.extrude(bolt, 0.03, "gold").translate(0, 0, 0.07))

    s = mk.Scene()
    root = mk.Node("PackAPunch-convcol", m)
    root.children.append(mk.Node("Medallion", medal, translation=(0, 1.15, 0.58)))
    root.children.append(mk.Node("Disc", disc, translation=(0, 1.15, 0.58)))
    root.children.append(mk.Node("GearL", gear(0.28, 12, 0.06, "gold").rotate((0, 1, 0), math.pi / 2), translation=(-0.94, 1.15, -0.15)))
    root.children.append(mk.Node("GearR", gear(0.22, 10, 0.06, "gold").rotate((0, 1, 0), math.pi / 2), translation=(0.94, 1.0, -0.2)))
    root.children.append(empty("WeaponSlot", (0, 0.75, 0.75)))
    s.add(root)
    return s


# ----------------------------------------------------------------------------
# lighting props
# ----------------------------------------------------------------------------

def brazier_tall():
    """Arena brazier: fluted stone pedestal with a bronze fire bowl."""
    m = mk.Mesh()
    m.add(mk.box(0.9, 0.25, 0.9, bevel=0.03, material="stone_plain").translate(0, 0.125, 0))
    m.add(mk.box(0.75, 0.15, 0.75, bevel=0.03, material="stone_plain").translate(0, 0.32, 0))
    shaft = mk.lathe([(0.26, 0.4), (0.24, 0.5), (0.2, 1.2), (0.22, 1.35), (0.3, 1.45)], 16, "stone_plain")
    g = shaft.groups["stone_plain"]
    ang = np.arctan2(g["P"][:, 2], g["P"][:, 0])
    band = (g["P"][:, 1] > 0.55) & (g["P"][:, 1] < 1.25)
    g["P"][band, 0] *= 1 - 0.05 * (np.cos(ang[band] * 16) * 0.5 + 0.5)
    g["P"][band, 2] *= 1 - 0.05 * (np.cos(ang[band] * 16) * 0.5 + 0.5)
    m.add(shaft)
    m.add(mk.box(0.7, 0.1, 0.7, bevel=0.02, material="stone_plain").translate(0, 1.5, 0))
    bowl = mk.lathe([(0.15, 1.55), (0.3, 1.6), (0.48, 1.75), (0.55, 1.9), (0.57, 1.95), (0.5, 1.93), (0.42, 1.8), (0.001, 1.75)], 24, "bronze")
    m.add(bowl)
    m.add(mk.torus(0.56, 0.025, 24, 6, "gold").translate(0, 1.94, 0))
    # embers / coals
    r = np.random.default_rng(4)
    for i in range(16):
        a, d = r.random() * 6.28, r.random() * 0.33
        c = mk.hull(r.normal(size=(7, 3)) * 0.05, "glow_ember" if i % 3 == 0 else "coal")
        m.add(c.translate(math.cos(a) * d, 1.82 + r.random() * 0.04, math.sin(a) * d))
    # lion-paw feet / decorative handles
    for i in range(3):
        a = 2 * math.pi * i / 3
        m.add(mk.torus(0.07, 0.015, 10, 4, "bronze").rotate((1, 0, 0), math.pi / 2).rotate((0, 1, 0), -a).translate(math.cos(a) * 0.56, 1.85, math.sin(a) * 0.56))
    m.color_fn(lambda P, N: 0.7 + 0.3 * np.clip(P[:, 1] / 1.5, 0, 1))
    s = mk.Scene()
    root = mk.Node("Brazier-convcol", m)
    root.children.append(empty("FirePoint", (0, 1.9, 0)))
    s.add(root)
    return s


def brazier_tripod():
    """Small bronze tripod brazier for the podium terrace."""
    m = mk.Mesh()
    for i in range(3):
        a = 2 * math.pi * i / 3
        foot = (math.cos(a) * 0.35, 0.0, math.sin(a) * 0.35)
        top = (math.cos(a) * 0.22, 0.85, math.sin(a) * 0.22)
        mid = (math.cos(a) * 0.12, 0.45, math.sin(a) * 0.12)
        m.add(mk.tube([foot, mid, top], [0.025, 0.02, 0.022], 6, "bronze"))
        m.add(mk.sphere(0.04, 8, 6, "bronze").translate(*foot))
    m.add(mk.torus(0.14, 0.015, 12, 4, "bronze").translate(0, 0.45, 0))
    m.add(mk.lathe([(0.05, 0.82), (0.25, 0.86), (0.36, 1.0), (0.38, 1.03), (0.33, 1.02), (0.001, 0.92)], 18, "bronze"))
    r = np.random.default_rng(8)
    for i in range(9):
        a, d = r.random() * 6.28, r.random() * 0.2
        m.add(mk.hull(r.normal(size=(6, 3)) * 0.04, "glow_ember" if i % 3 == 0 else "coal").translate(math.cos(a) * d, 0.97, math.sin(a) * d))
    s = mk.Scene()
    root = mk.Node("Tripod", m)
    root.children.append(empty("FirePoint", (0, 1.02, 0)))
    s.add(root)
    return s


def torch_sconce():
    """Wall torch: iron bracket + wrapped wooden torch. Wall is at z=0, +z out."""
    m = mk.Mesh()
    m.add(mk.box(0.14, 0.3, 0.03, bevel=0.01, material="iron").translate(0, 0, 0.015))
    m.add(mk.tube([(0, -0.1, 0.03), (0, -0.08, 0.15), (0, 0.0, 0.2)], 0.015, 6, "iron"))
    m.add(mk.torus(0.05, 0.012, 10, 4, "iron").translate(0, 0.0, 0.2))
    m.add(mk.torus(0.045, 0.012, 10, 4, "iron").translate(0, 0.12, 0.22))
    torch = mk.Mesh()
    torch.add(mk.cylinder(0.022, 0.55, 8, "wood_box", r2=0.03).translate(0, -0.2, 0))
    torch.add(mk.cylinder(0.042, 0.13, 10, "rope", r2=0.05).translate(0, 0.32, 0))
    torch.add(mk.cylinder(0.035, 0.03, 10, "glow_ember").translate(0, 0.45, 0))
    m.add(torch.rotate((1, 0, 0), 0.3).translate(0, 0.0, 0.2))
    s = mk.Scene()
    root = mk.Node("Torch", m)
    root.children.append(empty("FirePoint", (0, 0.52, 0.36)))
    s.add(root)
    return s


def banner(w=1.4, h=3.4):
    """Hanging crimson banner (UV mapped) on a gilded crossbar. Hang point at origin."""
    nx, ny = 6, 14
    P, UV = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x = (u - 0.5) * w
            y = -v * h
            z = 0.05 * math.sin(u * math.pi * 2.0 + v * 2.0) * v + 0.04 * v * v
            P.append((x, y, z))
            UV.append((u, v))
    idx = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            b, c, d = a + 1, a + nx + 1, a + nx + 2
            idx += [(a, c, b), (b, c, d)]
    cloth = mk.Mesh.from_arrays(np.array(P), np.zeros((len(P), 3)), np.array(idx), np.array(UV), "banner")
    cloth.recompute_normals_smooth()
    g = cloth.groups["banner"]
    if g["N"][:, 2].mean() < 0:
        g["I"] = g["I"][:, ::-1].copy()
        g["N"] = -g["N"]
    m = mk.Mesh()
    m.add(cloth)
    m.add(mk.cylinder(0.025, w + 0.25, 8, "gold").rotate((0, 0, 1), math.pi / 2).translate((w + 0.25) / 2, 0.02, 0.0))
    for sx in (-1, 1):
        m.add(mk.sphere(0.045, 8, 6, "gold").translate(sx * (w / 2 + 0.14), 0.02, 0))
    s = mk.Scene()
    s.add(mk.Node("Banner", m))
    return s


def floor_debris():
    """A few battle leftovers: helmet, shield, swords, bones (single GLB, nodes)."""
    s = mk.Scene()
    helm = bc.galea("bronze", crest=False)
    for g in helm.groups.values():
        g["J"][:] = 0
    helm.translate(0, -1.73, 0).rotate((1, 0, 0), 1.9).translate(0, 0.08, 0)
    s.add(mk.Node("Helmet", helm.material("bronze")))
    shield = bc.parma().rotate((1, 0, 0), -math.pi / 2 + 0.12).translate(0, 0.06, 0)
    s.add(mk.Node("Shield", shield))
    sw = bc.gladius().rotate((1, 0, 0), math.pi / 2).rotate((0, 1, 0), 0.6).translate(0, 0.02, 0)
    s.add(mk.Node("Sword", sw))
    bones = mk.Mesh()
    r = np.random.default_rng(12)
    for i in range(5):
        L = 0.25 + r.random() * 0.2
        b = mk.tube([(0, 0, -L / 2), (0, 0, L / 2)], [0.02, 0.02], 6, "bone")
        b.add(mk.sphere(0.03, 6, 4, "bone").translate(0, 0, -L / 2))
        b.add(mk.sphere(0.03, 6, 4, "bone").translate(0, 0, L / 2))
        bones.add(b.rotate((0, 1, 0), r.random() * 6).translate(r.normal() * 0.3, 0.02, r.normal() * 0.3))
    skull = mk.sphere(0.09, 12, 8, "bone").scale((0.9, 1, 1.1)).translate(0.2, 0.08, 0.1)
    bones.add(skull)
    s.add(mk.Node("Bones", bones))
    return s


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("mystery_box", mystery_box), ("pack_a_punch", pack_a_punch), ("brazier_tall", brazier_tall),
                     ("brazier_tripod", brazier_tripod), ("torch_sconce", torch_sconce), ("banner", banner),
                     ("floor_debris", floor_debris)):
        sc = fn()
        size = sc.write_glb(os.path.join(OUT, name + ".glb"))
        print(name, f"{size / 1e3:.0f} KB")


if __name__ == "__main__":
    main()
