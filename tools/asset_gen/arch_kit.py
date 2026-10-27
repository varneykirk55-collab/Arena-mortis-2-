"""
arch_kit.py - modular Roman architecture for the Arena Mortis visual overhaul.

Building blocks (all in a local "bay" frame: X along the wall, Y up from the
arena floor, Z towards the arena; the wall face is the plane z = 0 and
masonry extends into -Z):

  chipped_block   individual stone with chamfered, randomly chipped corners
  ashlar          courses of staggered blocks of varied length over a recessed
                  mortar backing (real joints, real shadows) with per-block tint
  voussoirs       wedge-stone arch ring with a projecting keystone
  column          engaged (half) Tuscan-Doric column: plinth, torus base,
                  fluted shaft with entasis, astragal, echinus, abacus
  cornice         dentilled cornice profile segment
  parapet         pluteus with moulded panel and coping
  base_course     projecting rusticated plinth course with moulding
  sand_drift      wind-blown sand banked against the wall foot
  rubble          loose fallen stones

Bay modules (podium wall) are composed from these in build_arena_v2.py.
"""
import math

import numpy as np

import meshkit as mk


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def tint(m, rng, var=0.14, warm=0.05, base=1.0):
    t = base * (1 - var / 2 + rng.random() * var)
    w = (rng.random() - 0.5) * warm
    return m.tint((t * (1 + w), t, t * (1 - w * 1.5)))


def edge_wear(m, light=1.06, dark=0.9):
    """Bevel/chip faces (non axis-aligned normals) slightly lighter -> worn edges."""
    for g in m.groups.values():
        n = np.abs(g["N"])
        axis = n.max(axis=1) > 0.97
        f = np.where(axis, 1.0, light)
        g["C"][:, :3] *= f[:, None]
    return m


def chipped_block(sx, sy, sz, rng, bevel=0.025, chips=1, chip=0.05, jitter=0.004, material="lime_block"):
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    b = min(bevel, hx * 0.45, hy * 0.45, hz * 0.45)
    pts = []
    for sxn in (-1, 1):
        for syn in (-1, 1):
            for szn in (-1, 1):
                pts.append([[sxn * hx, syn * (hy - b), szn * (hz - b)],
                            [sxn * (hx - b), syn * hy, szn * (hz - b)],
                            [sxn * (hx - b), syn * (hy - b), szn * hz]])
    pts = np.array(pts, dtype=np.float64)
    front = [k for k in range(8) if pts[k].mean(axis=0)[2] > 0]
    for _ in range(chips):
        k = int(rng.choice(front)) if rng.random() < 0.85 else int(rng.integers(0, 8))
        corner = np.sign(pts[k].mean(axis=0))
        depth = chip * (0.4 + rng.random())
        pts[k] -= corner * depth * (0.4 + 0.8 * rng.random(3))
    P = pts.reshape(-1, 3) + rng.normal(size=(24, 3)) * jitter
    m = mk.hull(P, material)
    return edge_wear(m)


def rect_outside_circle(xa, xb, ya, yb, cx, cy, r):
    nx = min(max(cx, xa), xb)
    ny = min(max(cy, ya), yb)
    return (nx - cx) ** 2 + (ny - cy) ** 2 >= r * r


# ----------------------------------------------------------------------------
# masonry
# ----------------------------------------------------------------------------

def ashlar(x0, x1, y0, y1, rng, depth=0.32, course_h=(0.56, 0.6, 0.52, 0.62), len_range=(0.75, 1.55),
           gap=0.016, proud=0.012, rustic=False, chips=1, material="lime_block", keep=None,
           backing="mortar_v2", backing_depth=0.05, tint_var=0.16, backing_keep=None, clipper=None):
    """Courses of staggered blocks filling the rectangle [x0,x1]x[y0,y1].
    keep(xa, xb, ya, yb) -> bool decides whether a block may be placed;
    blocks that fail are split in two (twice) before being dropped, which
    produces a natural stepped edge around arches."""
    m = mk.Mesh()
    y = y0
    row = 0
    while y < y1 - 0.06:
        h = course_h[row % len(course_h)] * (0.94 + 0.12 * rng.random())
        if y + h > y1 - 0.2:
            h = y1 - y
        x = x0 - rng.random() * len_range[0] * 0.8
        while x < x1 - 0.02:
            L = rng.uniform(*len_range)
            xa, xb = max(x, x0), min(x + L, x1)
            if x1 - xb < 0.25:          # avoid slivers at the end of a course
                xb = x1
                L = xb - x
            if clipper is not None:
                for piece in clipper(xa, xb, y, y + h):
                    if piece[0] == "rect":
                        _, pa, pb, qa, qb = piece
                        if qb - qa > 0.1:
                            _place_block(m, pa, pb, qa, qb - qa, depth, gap, proud, rustic, chips, material, rng, tint_var)
                    else:
                        _place_poly_block(m, piece[1], depth, proud, material, rng, tint_var)
                x += L
                continue
            pieces = [(xa, xb)]
            for level in range(3):
                nxt = []
                for (pa, pb) in pieces:
                    if keep is None or keep(pa, pb, y, y + h):
                        _place_block(m, pa, pb, y, h, depth, gap, proud, rustic, chips, material, rng, tint_var)
                    elif level < 2 and pb - pa > 0.3:
                        mid = (pa + pb) / 2
                        nxt += [(pa, mid), (mid, pb)]
                pieces = nxt
            x += L
        y += h
        row += 1
    if backing:
        bk = mk.box(x1 - x0, y1 - y0, backing_depth, material=backing).translate((x0 + x1) / 2, (y0 + y1) / 2, -0.045 - backing_depth / 2)
        bkeep = backing_keep if backing_keep is not None else keep
        if bkeep is not None:
            # backing must not cover openings: build it from coarse cells
            bk = mk.Mesh()
            ny = max(1, int((y1 - y0) / 0.1))
            nx = max(1, int((x1 - x0) / 0.1))
            for j in range(ny):
                for i in range(nx):
                    ca, cb = x0 + (x1 - x0) * i / nx, x0 + (x1 - x0) * (i + 1) / nx
                    ya, yb = y0 + (y1 - y0) * j / ny, y0 + (y1 - y0) * (j + 1) / ny
                    if bkeep(ca, cb, ya, yb):
                        bk.add(mk.box(cb - ca + 0.002, yb - ya + 0.002, backing_depth, material=backing)
                               .translate((ca + cb) / 2, (ya + yb) / 2, -0.045 - backing_depth / 2))
        m.add(bk.tint((0.85, 0.85, 0.85)))
    return m


def _place_block(m, xa, xb, y, h, depth, gap, proud, rustic, chips, material, rng, tint_var):
    bw, bh = xb - xa - gap, h - gap
    if bw < 0.08 or bh < 0.08:
        return
    d = depth + rng.random() * proud * (3.0 if rustic else 1.0)
    nchip = chips if rng.random() < 0.65 else 0
    blk = chipped_block(bw, bh, d, rng, bevel=0.04 if rustic else 0.022, chips=nchip,
                        chip=0.07 if rustic else 0.045, material=material)
    blk.translate((xa + xb) / 2, y + h / 2, -d / 2 + proud * rng.random() * (2.5 if rustic else 1.0))
    tint(blk, rng, var=tint_var)
    m.add(blk)


def arched_backing(x0, x1, y0, y1, r, sp, material="mortar_v2", depth=0.05, z=-0.045, seg=16):
    """Recessed mortar plane behind masonry, with a semicircular-headed opening
    of radius r springing at sp (centred on x = 0)."""
    m = mk.Mesh()
    for (a, b) in ((x0, -r), (r, x1)):
        m.add(mk.box(b - a, sp - y0, depth, material=material).translate((a + b) / 2, (y0 + sp) / 2, z - depth / 2))
    pts = [(x0, sp), (-r, sp)]
    for i in range(1, seg):
        a = math.pi - math.pi * i / seg
        pts.append((r * math.cos(a), sp + r * math.sin(a)))
    pts += [(r, sp), (x1, sp), (x1, y1), (x0, y1)]
    m.add(mk.extrude(pts, depth, material).translate(0, 0, z - depth / 2))
    return m.tint((0.85, 0.85, 0.85))


def _place_poly_block(m, poly, depth, proud, material, rng, tint_var, gap=0.008):
    P = np.asarray(poly)
    if len(P) < 3:
        return
    area = 0.5 * abs(np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]))
    if area < 0.02:
        return
    c = P.mean(axis=0)
    P = c + (P - c) * (1 - gap / max(np.ptp(P[:, 0]), np.ptp(P[:, 1]), 0.1))
    d = depth + rng.random() * proud
    blk = mk.extrude([tuple(p) for p in P], d, material, bevel=0.012)
    blk.translate(0, 0, -d / 2 + proud * rng.random())
    blk.jitter(0.003, int(rng.integers(0, 1 << 30)))
    tint(blk, rng, var=tint_var)
    m.add(edge_wear(blk))


def _notch_poly(xa, xb, ya, yb, cx, cy, R, n=10):
    """Rectangle with the part inside the circle removed (radial projection)."""
    pts = []
    corners = [(xa, ya), (xb, ya), (xb, yb), (xa, yb)]
    for i in range(4):
        (x0, y0), (x1, y1) = corners[i], corners[(i + 1) % 4]
        for k in range(n):
            t = k / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy)
            if d < R:
                if d < 1e-6:
                    continue
                x, y = cx + dx / d * R, cy + dy / d * R
            pts.append((x, y))
    # drop consecutive duplicates
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) > 1e-4:
            out.append(p)
    return out


def arch_clipper(r, sp, R):
    """Clip masonry around an opening: jambs at |x| = r below the springing,
    a circle of radius R (extrados of the voussoirs) above it."""
    def clip(xa, xb, ya, yb):
        out = []
        if ya < sp:
            yb2 = min(yb, sp)
            for (a, b) in ((xa, min(xb, -r)), (max(xa, r), xb)):
                if b - a > 0.1 and yb2 - ya > 0.1:
                    out.append(("rect", a, b, ya, yb2))
        if yb > sp:
            ya2 = max(ya, sp)
            if yb - ya2 < 0.1:
                return out
            if rect_outside_circle(xa, xb, ya2, yb, 0.0, sp, R):
                out.append(("rect", xa, xb, ya2, yb))
            else:
                inside = all((x * x + (y - sp) ** 2) < R * R for x in (xa, xb) for y in (ya2, yb))
                if not inside:
                    out.append(("poly", _notch_poly(xa, xb, ya2, yb, 0.0, sp, R)))
        return out
    return clip


def voussoirs(r_in, r_out, depth, n, rng, spring=0.0, cx=0.0, proud=0.035, key_scale=1.14,
              gap=0.014, material="lime_trim", z_back=None):
    """Semicircular ring of wedge stones (n odd -> centred keystone)."""
    m = mk.Mesh()
    z_back = -depth if z_back is None else z_back
    for i in range(n):
        a0 = math.pi * i / n
        a1 = math.pi * (i + 1) / n
        g = gap / r_in
        ro = r_out
        zf = proud
        if i == n // 2:
            ro = r_in + (r_out - r_in) * key_scale
            zf = proud + 0.05
        pts = []
        for a in (a0 + g, a1 - g):
            for r in (r_in, ro):
                for z in (zf, z_back):
                    pts.append((cx + r * math.cos(a), spring + r * math.sin(a), z))
        # extra mid points on the extrados keep the outer edge curved
        am = (a0 + a1) / 2
        for z in (zf, z_back):
            pts.append((cx + ro * 1.004 * math.cos(am), spring + ro * 1.004 * math.sin(am), z))
        P = np.array(pts) + rng.normal(size=(len(pts), 3)) * 0.003
        stone = edge_wear(mk.hull(P, material))
        tint(stone, rng, var=0.1)
        m.add(stone)
    return m


def soffit(r, z0, z1, seg=18, material="lime_trim"):
    """Smooth underside of an arch passing through the wall (from z0 to z1)."""
    P, N, idx = [], [], []
    for i in range(seg + 1):
        a = math.pi * i / seg
        x, y = r * math.cos(a), r * math.sin(a)
        n = (-math.cos(a), -math.sin(a), 0.0)
        for z in (z0, z1):
            P.append((x, y, z))
            N.append(n)
    for i in range(seg):
        a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3
        idx += [(a, c, b), (b, c, d)]
    m = mk.Mesh.from_arrays(np.array(P), np.array(N), np.array(idx), None, material)
    g = m.groups[material]
    tri = g["P"][g["I"]]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    flip = np.sum(fn * g["N"][g["I"][:, 0]], axis=1) < 0
    g["I"][flip] = g["I"][flip][:, ::-1]
    return m


# ----------------------------------------------------------------------------
# orders and mouldings
# ----------------------------------------------------------------------------

def _fluted_lathe(profile, flutes, seg_per_flute, depth, a0, a1, material):
    """Lathe whose radius is modulated by concave Doric flutes."""
    seg = flutes * seg_per_flute
    m = mk.lathe(profile, seg, material, angle0=a0, angle1=a1)
    g = m.groups[material]
    ang = np.arctan2(g["P"][:, 2], g["P"][:, 0])
    phase = (ang - a0) / (a1 - a0) * flutes
    f = 1.0 - depth * (0.5 - 0.5 * np.cos(phase * 2 * math.pi)) ** 0.7
    g["P"][:, 0] *= f
    g["P"][:, 2] *= f
    m.recompute_normals_smooth()
    return m


def column(r, h, rng, half=True, flutes=10, material="lime_trim", damage=0.0):
    """Engaged Tuscan-Doric column standing at y=0, axis through the origin,
    the visible half facing +Z. Height h includes base and capital."""
    a0, a1 = (0.0, math.pi) if half else (0.0, 2 * math.pi)
    seg_half = 20
    m = mk.Mesh()
    depth = 1.4 * r if half else 2.8 * r
    zc = depth / 2 if half else 0.0
    # square plinth
    m.add(chipped_block(2.75 * r, 0.24, depth, rng, bevel=0.02, chips=1, chip=0.03, material=material).translate(0, 0.12, zc))
    # attic-style base: torus, scotia, torus
    base = mk.lathe([(1.32 * r, 0.24), (1.36 * r, 0.29), (1.32 * r, 0.35), (1.18 * r, 0.37), (1.14 * r, 0.41),
                     (1.2 * r, 0.44), (1.18 * r, 0.48), (1.06 * r, 0.5), (1.0 * r, 0.56)], seg_half, material, angle0=a0, angle1=a1)
    m.add(base)
    # fluted shaft with entasis
    y0s, y1s = 0.56, h - 0.62
    prof = []
    for i in range(9):
        t = i / 8
        rr = r * (1.0 - 0.13 * t ** 1.6 + 0.012 * math.sin(t * math.pi))
        prof.append((rr, y0s + (y1s - y0s) * t))
    m.add(_fluted_lathe(prof, flutes if half else flutes * 2, 4, 0.06, a0, a1, material))
    # astragal + necking
    rt = r * 0.87
    m.add(mk.lathe([(rt, y1s), (rt * 1.07, y1s + 0.03), (rt * 1.07, y1s + 0.07), (rt, y1s + 0.1), (rt, y1s + 0.24)], seg_half, material, angle0=a0, angle1=a1))
    # echinus (quarter round flaring out)
    ech = []
    for i in range(6):
        t = i / 5
        ech.append((rt + (1.3 * r - rt) * math.sin(t * math.pi / 2), y1s + 0.24 + 0.16 * (1 - math.cos(t * math.pi / 2))))
    m.add(mk.lathe(ech, seg_half, material, angle0=a0, angle1=a1))
    # abacus
    m.add(chipped_block(2.75 * r, 0.22, depth, rng, bevel=0.018, chips=1, chip=0.03, material=material).translate(0, h - 0.11, zc))
    if damage > 0:
        m.jitter(damage, int(rng.integers(0, 1 << 30)))
    tint(m, rng, var=0.08)
    return m


def profile_extrude(profile_zy, length, material, x0=None):
    """Extrude a (z, y) moulding profile along X over `length` (centred)."""
    poly = [(-z, y) for (z, y) in profile_zy]
    m = mk.extrude(poly, length, material)
    m.rotate((0, 1, 0), math.pi / 2)
    return m


def cornice(width, y0, rng, material="lime_trim", dentils=True, height=0.58, proj=0.42):
    """Podium cornice segment from y0 to y0+height, projecting `proj` into +Z.
    Built from short extruded segments with hairline gaps so it reads as cut stone."""
    s = height / 0.58
    prof = [(0.0, 0.0), (0.06, 0.0), (0.06, 0.1 * s), (0.09, 0.12 * s), (0.09, 0.2 * s), (0.12, 0.22 * s),
            (0.12, 0.3 * s), (proj * 0.85, 0.36 * s), (proj * 0.85, 0.37 * s), (proj, 0.38 * s), (proj, 0.48 * s),
            (proj * 0.93, 0.5 * s), (proj * 0.97, 0.55 * s), (proj * 0.9, height), (-0.35, height), (-0.35, 0.0)]
    prof = [(z, y0 + y) for (z, y) in prof]
    m = mk.Mesh()
    nseg = max(2, int(round(width / 1.35)))
    seg_w = width / nseg
    for i in range(nseg):
        piece = profile_extrude(prof, seg_w - 0.012, material).translate(-width / 2 + seg_w * (i + 0.5), 0, 0)
        piece.jitter(0.004, int(rng.integers(0, 1 << 30)))
        tint(piece, rng, var=0.1)
        m.add(edge_wear(piece))
    if dentils:
        k = 0
        x = -width / 2 + 0.05
        while x < width / 2 - 0.08:
            d = mk.box(0.075, 0.075 * s, 0.07, material=material).translate(x + 0.0375, y0 + 0.265 * s, 0.155)
            if rng.random() > 0.06:     # a few missing dentils
                m.add(tint(d, rng, var=0.12))
            x += 0.125
            k += 1
    return m


def parapet(width, y0, rng, material="lime_trim", z_front=0.05, thick=0.4, h=1.12):
    """Low pluteus wall on top of the podium with a moulded panel and coping."""
    m = mk.Mesh()
    zc = z_front - thick / 2
    # body
    m.add(chipped_block(width - 0.01, h - 0.14, thick, rng, bevel=0.015, chips=1, chip=0.03, material=material)
          .translate(0, y0 + (h - 0.14) / 2, zc))
    # coping with overhang
    m.add(chipped_block(width, 0.14, thick + 0.12, rng, bevel=0.02, chips=2, chip=0.04, material=material)
          .translate(0, y0 + h - 0.07, zc))
    # moulded panel frame on the arena face
    fw, fh = width * 0.72, h * 0.5
    fy = y0 + 0.2 + fh / 2
    for (sx, sy_, cx, cy) in ((fw, 0.05, 0, fy + fh / 2), (fw, 0.05, 0, fy - fh / 2),
                              (0.05, fh, -fw / 2, fy), (0.05, fh, fw / 2, fy)):
        m.add(mk.box(sx, sy_, 0.035, material=material).translate(cx, cy, z_front + 0.015))
    tint(m, rng, var=0.08)
    return m


def base_course(width, rng, h=0.62, proj=0.2, material="lime_trim"):
    """Projecting plinth at the foot of the wall: rusticated blocks + moulding."""
    m = mk.Mesh()
    x = -width / 2
    while x < width / 2 - 0.05:
        L = min(rng.uniform(1.0, 1.6), width / 2 - x)
        if width / 2 - (x + L) < 0.3:
            L = width / 2 - x
        b = chipped_block(L - 0.016, h * 0.68, 0.45 + proj, rng, bevel=0.045, chips=2, chip=0.07, material=material)
        b.translate(x + L / 2, h * 0.34, proj - (0.45 + proj) / 2)
        m.add(tint(b, rng, var=0.14, base=0.94))
        x += L
    mould = [(proj, 0.0), (proj, 0.02), (proj * 0.7, 0.06), (proj * 0.55, 0.1), (0.04, 0.16)]
    prof = [(proj - 0.02, h * 0.68), (proj - 0.02, h * 0.74), (proj * 0.55, h * 0.82), (proj * 0.3, h * 0.9),
            (0.02, h), (-0.1, h), (-0.1, h * 0.68)]
    nseg = max(2, int(round(width / 1.4)))
    for i in range(nseg):
        sw = width / nseg
        p = profile_extrude(prof, sw - 0.012, material).translate(-width / 2 + sw * (i + 0.5), 0, 0)
        m.add(tint(edge_wear(p), rng, var=0.1))
    return m


def sand_drift(width, rng, z0=0.2, z1=1.7, peak=0.24, nx=18, nz=7, material="sand_v2"):
    """Wind-blown sand banked against the wall foot; fades into the floor."""
    xs = np.linspace(-width / 2, width / 2, nx + 1)
    zs = np.linspace(z0, z1, nz + 1)
    phase = rng.random() * 10
    P, C = [], []
    for z in zs:
        u = (z - z0) / (z1 - z0)
        for x in xs:
            wav = 0.65 + 0.35 * math.sin(x * 1.3 + phase) + 0.15 * math.sin(x * 3.7 + phase * 2)
            hgt = peak * (1 - u) ** 1.8 * wav
            P.append((x, max(hgt, 0.0) + 0.012, z))
            C.append(0.78 + 0.22 * u)
    idx = []
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            b, c, d = a + 1, a + nx + 1, a + nx + 2
            idx += [(a, c, b), (b, c, d)]
    m = mk.Mesh.from_arrays(np.array(P), np.zeros((len(P), 3)), np.array(idx), None, material)
    m.recompute_normals_smooth()
    g = m.groups[material]
    if g["N"][:, 1].mean() < 0:
        g["I"] = g["I"][:, ::-1].copy()
        g["N"] = -g["N"]
    g["C"][:, :3] *= np.array(C)[:, None]
    return m


def rubble(n, center, spread, size, rng, material="lime_block"):
    m = mk.Mesh()
    for i in range(n):
        s = size[0] + (size[1] - size[0]) * rng.random() ** 2
        pts = rng.normal(size=(10, 3)) * np.array([s, s * 0.55, s])
        rock = mk.hull(pts, material)
        off = rng.normal(size=3) * np.array(spread)
        off[1] = 0
        rock.rotate((0, 1, 0), rng.random() * 6.28).translate(*(np.asarray(center) + off + np.array([0, s * 0.22, 0])))
        m.add(tint(rock, rng, var=0.2, base=0.9))
    return m


def flagstones(x0, x1, z0, z1, rng, y=0.0, material="paving", thick=0.12):
    """Irregular rectangular paving slabs (top surface at y)."""
    m = mk.Mesh()
    z = z0
    while z < z1 - 0.05:
        dz = min(rng.uniform(0.55, 0.85), z1 - z)
        x = x0 - rng.random() * 0.4
        while x < x1 - 0.05:
            dx = rng.uniform(0.6, 1.1)
            xa, xb = max(x, x0), min(x + dx, x1)
            if xb - xa > 0.15:
                s = chipped_block(xb - xa - 0.02, thick, dz - 0.02, rng, bevel=0.02, chips=1, chip=0.03, material=material)
                s.translate((xa + xb) / 2, y - thick / 2 + rng.uniform(-0.012, 0.008), z + dz / 2)
                m.add(tint(s, rng, var=0.2))
            x += dx
        z += dz
    return m
