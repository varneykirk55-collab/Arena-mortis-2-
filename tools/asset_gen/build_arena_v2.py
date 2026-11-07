"""
Visual overhaul (phase 1): modular podium bays for the Colosseum.

Every podium bay has the same width (bays are spaced by equal arc length), so
one module mesh can be reused for every bay of its kind. Modules:

  PanelA  ashlar wall, framed marble plaque, engaged column
  PanelB  ashlar wall with a blind arch recess, engaged column
  PanelC  like A but storm-damaged: missing blocks, exposed rubble core, debris
  Niche   statue niche: apse with half-dome, voussoir arch, engaged column
  Gate    entrance arch, voussoirs, impost, ashlar-lined tunnel with ribbed
          vault, flagstone floor, iron portcullis, collapsed rubble at the end

All modules include the base course, cornice, parapet and a sand drift, and
are written to assets/models/podium_modules.glb (one node per module).
The Colosseum layout gains "podium_modules": per-bay module name, mirror flag
and transform, which scripts/colosseum/colosseum.gd instantiates.
Collision is unchanged (it lives in colosseum_podium.glb).
"""
import math
import os

import numpy as np

import arch_kit as ak
import meshkit as mk

WALL_TOP = 4.42      # top of masonry / bottom of cornice
CORNICE_H = 0.58     # cornice brings the wall to 5.0 (terrace level)
PARAPET_H = 1.12
BASE_H = 0.62
COL_R = 0.27
GATE_R, GATE_SPRING = 1.7, 2.4
NICHE_R, NICHE_SPRING, NICHE_DEPTH = 1.1, 2.6, 0.75


def _common(W, rng, with_column=False, drift=True, base_gaps=()):
    m = mk.Mesh()
    # base course (optionally interrupted by openings: list of (xa, xb))
    spans = [(-W / 2, W / 2)]
    for (ga, gb) in base_gaps:
        new = []
        for (a, b) in spans:
            if gb <= a or ga >= b:
                new.append((a, b))
            else:
                if ga > a:
                    new.append((a, ga))
                if gb < b:
                    new.append((gb, b))
        spans = new
    for (a, b) in spans:
        if b - a > 0.2:
            m.add(ak.base_course(b - a, rng).translate((a + b) / 2, 0, 0))
    m.add(ak.cornice(W, WALL_TOP, rng, height=CORNICE_H))
    m.add(ak.parapet(W, WALL_TOP + CORNICE_H, rng))
    if with_column:
        m.add(ak.column(COL_R, WALL_TOP - BASE_H, rng).translate(-W / 2 + 0.002, BASE_H, 0.0))
    if drift:
        spans_d = spans if base_gaps else [(-W / 2, W / 2)]
        for (a, b) in spans_d:
            if b - a > 0.4:
                m.add(ak.sand_drift(b - a, rng).translate((a + b) / 2, 0, 0))
    return m


def _wall(W, rng, keep=None, y0=BASE_H, y1=WALL_TOP, backing="mortar_v2", opening=None, extrados=None):
    """Ashlar wall; opening=(r, spring) cuts an arched opening whose masonry is
    clipped to the voussoirs' extrados radius."""
    if opening is None:
        if keep is not None:
            return ak.ashlar(-W / 2, W / 2, y0, y1, rng, keep=keep, backing=None)
        return ak.ashlar(-W / 2, W / 2, y0, y1, rng, backing=backing)
    clip = ak.arch_clipper(opening[0], opening[1], extrados or opening[0] + 0.4)
    m = ak.ashlar(-W / 2, W / 2, y0, y1, rng, backing=None, clipper=clip)
    m.add(ak.arched_backing(-W / 2, W / 2, y0, y1, opening[0], opening[1], material=backing))
    return m


def _not_opening(r, sp):
    """Backing cells allowed everywhere except the true arch opening."""
    def f(xa, xb, ya, yb):
        xm, ym = (xa + xb) / 2, (ya + yb) / 2
        if abs(xm) < r and ym < sp:
            return False
        return xm * xm + (ym - sp) ** 2 > r * r
    return f


def panel(W, variant, seed):
    rng = np.random.default_rng(seed)
    m = mk.Mesh()
    m.add(_common(W, rng))
    if variant in ("A", "C"):
        dmg = None
        if variant == "C":
            # damaged upper-right corner: a ragged notch of missing blocks
            x_c = W / 2 - 1.9

            def dmg(xa, xb, ya, yb):
                xm, ym = (xa + xb) / 2, (ya + yb) / 2
                return not (xm > x_c + 0.25 * math.sin(ym * 5) and ym > 3.0 - (xm - x_c) * 0.55)
        m.add(_wall(W, rng, keep=dmg))
        if variant == "C":
            m.add(mk.box(W - 2.0, WALL_TOP - BASE_H, 0.05, material="mortar_v2").translate(-1.0, (WALL_TOP + BASE_H) / 2, -0.07).tint((0.85, 0.85, 0.85)))
            m.add(mk.box(2.0, 2.6 - BASE_H, 0.05, material="mortar_v2").translate(W / 2 - 1.0, (2.6 + BASE_H) / 2, -0.07).tint((0.85, 0.85, 0.85)))
            core = ak.ashlar(W / 2 - 2.1, W / 2, 2.6, WALL_TOP, rng, depth=0.2, course_h=(0.3, 0.26, 0.34),
                             len_range=(0.3, 0.6), material="rubble_core", backing=None,
                             keep=lambda xa, xb, ya, yb: not dmg(xa, xb, ya, yb))
            m.add(core.translate(0, 0, -0.16))
            m.add(mk.box(2.1, WALL_TOP - 2.6, 0.06, material="rubble_core").translate(W / 2 - 1.05, (WALL_TOP + 2.6) / 2, -0.45)
                  .tint((0.5, 0.5, 0.5)))
            m.add(ak.rubble(14, (W / 2 - 1.1, 0.0, 0.9), (0.7, 0, 0.35), (0.1, 0.32), rng))
            m.add(ak.rubble(6, (W / 2 - 1.0, BASE_H, 0.12), (0.5, 0, 0.05), (0.06, 0.16), rng))
        # string course moulding across the bay + a small marble tablet below the banner
        sc = [(0.0, 0.0), (0.05, 0.02), (0.09, 0.06), (0.09, 0.14), (0.06, 0.17), (0.0, 0.2), (-0.1, 0.2), (-0.1, 0.0)]
        nseg = 4
        for i in range(nseg):
            sw = W / nseg
            band = ak.profile_extrude([(z, 2.05 + y) for (z, y) in sc], sw - 0.012, "lime_trim")
            m.add(ak.tint(ak.edge_wear(band.translate(-W / 2 + sw * (i + 0.5), 0, 0)), rng, var=0.1))
        tab = ak.chipped_block(0.95, 0.5, 0.06, rng, bevel=0.01, chips=1, chip=0.02, material="marble_v2")
        m.add(ak.tint(tab.translate(0, 1.08, 0.04), rng, var=0.05, base=0.82))
        for (sx, sy, cx, cy) in ((1.13, 0.09, 0, 1.375), (1.13, 0.09, 0, 0.785), (0.09, 0.5, -0.52, 1.08), (0.09, 0.5, 0.52, 1.08)):
            fr = ak.chipped_block(sx, sy, 0.12, rng, bevel=0.015, chips=0, material="lime_trim")
            m.add(ak.tint(fr.translate(cx, cy, 0.05), rng, var=0.08))
    else:  # B: blind arch recess
        r, sp, dep = 1.2, 2.55, 0.18

        def outside(xa, xb, ya, yb):
            if xb > -r and xa < r and ya < sp:
                return False
            return ak.rect_outside_circle(xa, xb, ya, yb, 0.0, sp, r + 0.38)

        def inside(xa, xb, ya, yb):
            return xa >= -r and xb <= r and (yb <= sp or not ak.rect_outside_circle(xa, xb, ya, yb, 0, sp, 0.0) and
                                             max((xa) ** 2, (xb) ** 2) + (yb - sp) ** 2 <= r * r)
        m.add(_wall(W, rng, opening=(r, sp), extrados=r + 0.375))
        back = ak.ashlar(-r, r, BASE_H, sp + r, rng, depth=0.2, course_h=(0.42, 0.38, 0.45), len_range=(0.45, 0.9),
                         keep=inside, backing=None)
        m.add(back.translate(0, 0, -dep))
        m.add(ak.voussoirs(r, r + 0.36, 0.32, 13, rng, spring=sp))
        m.add(ak.soffit(r, 0.0, -dep - 0.02).translate(0, sp, 0))
        for sx in (-1, 1):
            jamb = ak.chipped_block(0.1, sp - BASE_H, dep + 0.04, rng, bevel=0.01, chips=0, material="lime_trim")
            m.add(jamb.translate(sx * (r + 0.05), (sp + BASE_H) / 2, -dep / 2))
            imp = ak.chipped_block(0.42, 0.16, 0.3, rng, bevel=0.02, chips=1, chip=0.03, material="lime_trim")
            m.add(imp.translate(sx * (r + 0.12), sp - 0.08, 0.02))
        m.add(ak.chipped_block(2 * r, 0.1, dep + 0.1, rng, bevel=0.015, chips=1, material="lime_trim")
              .translate(0, BASE_H + 0.05, -dep / 2 + 0.04))
    m.color_fn(_under_cornice)
    return m


def _under_cornice(P, N):
    v = np.where(P[:, 1] > WALL_TOP - 0.25, 0.86, 1.0)
    return np.stack([v, v, v], axis=1)


def niche(W, seed):
    rng = np.random.default_rng(seed)
    m = mk.Mesh()
    m.add(_common(W, rng))
    r, sp = NICHE_R, NICHE_SPRING

    def outside(xa, xb, ya, yb):
        if xb > -r and xa < r and ya < sp:
            return False
        return ak.rect_outside_circle(xa, xb, ya, yb, 0.0, sp, r + 0.4)
    m.add(_wall(W, rng, opening=(r, sp), extrados=r + 0.375))
    m.add(ak.voussoirs(r, r + 0.36, 0.34, 11, rng, spring=sp))
    for sx in (-1, 1):
        imp = ak.chipped_block(0.4, 0.16, 0.3, rng, bevel=0.02, chips=1, chip=0.03, material="lime_trim")
        m.add(imp.translate(sx * (r + 0.12), sp - 0.08, 0.02))
    # apse: half cylinder + quarter-sphere dome (seen from inside -> flipped)
    zscale = NICHE_DEPTH / r
    apse = mk.lathe([(r, BASE_H), (r, sp)], 22, "lime_trim", angle0=math.pi, angle1=2 * math.pi)
    dome_prof = [(r * math.cos(f), sp + r * math.sin(f)) for f in np.linspace(0, math.pi / 2 - 0.02, 7)]
    dome_prof[-1] = (0.005, dome_prof[-1][1])
    dome = mk.lathe(dome_prof, 22, "lime_trim", angle0=math.pi, angle1=2 * math.pi)
    inner = mk.merge(apse, dome)
    for g in inner.groups.values():
        g["I"] = g["I"][:, ::-1].copy()
        g["N"] = -g["N"]
    inner.scale((1, 1, zscale))
    inner.color_fn(lambda P, N: np.stack([0.55 + 0.45 * np.clip(1 + P[:, 2] / NICHE_DEPTH, 0, 1)] * 3, axis=1))
    m.add(inner)
    floor = ak.chipped_block(2 * r + 0.1, 0.1, NICHE_DEPTH + 0.05, rng, bevel=0.015, chips=1, material="lime_trim")
    m.add(floor.translate(0, BASE_H - 0.05, -NICHE_DEPTH / 2 + 0.02))
    m.color_fn(_under_cornice)
    return m


def _side_wall(z0, z1, y0, y1, x, facing, rng, material="tunnel_stone", **kw):
    """Ashlar on a plane x = const, visible side facing +X (facing=1) or -X."""
    length = z1 - z0
    w = ak.ashlar(0.0, length, y0, y1, rng, depth=0.25, material=material, backing="mortar_v2", **kw)
    # local (x along wall, z out of wall) -> world: wall-x -> world -z, out -> world +x*facing
    if facing > 0:
        w.rotate((0, 1, 0), math.pi / 2)        # face +Z -> +X, run along -Z
        w.translate(x, 0, z1)
    else:
        w.rotate((0, 1, 0), -math.pi / 2)       # face +Z -> -X, run along +Z
        w.translate(x, 0, z0)
    return w


def gate(W, seed, thickness=1.2, depth=7.0):
    rng = np.random.default_rng(seed)
    m = mk.Mesh()
    r, sp = GATE_R, GATE_SPRING
    m.add(_common(W, rng, base_gaps=[(-r - 0.02, r + 0.02)]))

    def outside(xa, xb, ya, yb):
        if xb > -r and xa < r and ya < sp:
            return False
        return ak.rect_outside_circle(xa, xb, ya, yb, 0.0, sp, r + 0.47)
    m.add(_wall(W, rng, opening=(r, sp), extrados=r + 0.465))
    m.add(ak.voussoirs(r, r + 0.45, 0.45, 13, rng, spring=sp, key_scale=1.12))
    for sx in (-1, 1):
        imp = ak.chipped_block(0.5, 0.2, 0.36, rng, bevel=0.02, chips=1, chip=0.04, material="lime_trim")
        m.add(imp.translate(sx * (r + 0.15), sp - 0.1, 0.03))
    # passage through the wall and tunnel beyond
    z_wall = -thickness
    z_end = -thickness - depth
    tun = mk.Mesh()
    tun.add(ak.soffit(r, -0.44, z_wall).translate(0, sp, 0).material("tunnel_stone"))
    for sx in (-1, 1):
        tun.add(_side_wall(z_end + 0.3, 0.0, 0.0, sp, sx * r, -sx, rng))
    z = z_wall
    i = 0
    while z > z_end + 0.4:
        dz = 0.55
        ring = ak.voussoirs(r, r + 0.5, dz, 11 + (i % 2), rng, spring=sp, proud=0.0, key_scale=1.0,
                            gap=0.02, material="tunnel_stone")
        tun.add(ring.translate(0, 0, z))
        z -= dz
        i += 1
    tun.add(ak.flagstones(-r, r, z_end + 0.4, 0.55, rng, y=0.0))
    # collapsed end: rubble core wall + fallen blocks
    back = ak.ashlar(-r - 0.3, r + 0.3, 0.0, sp + r + 0.5, rng, depth=0.4, course_h=(0.35, 0.3, 0.4),
                     len_range=(0.3, 0.7), material="rubble_core", backing="rubble_core")
    tun.add(back.translate(0, 0, z_end + 0.25))
    tun.add(ak.rubble(22, (0.0, 0.0, z_end + 1.3), (0.9, 0, 0.6), (0.18, 0.6), rng, material="tunnel_stone"))
    tun.color_fn(lambda P, N: np.stack([np.clip(0.22 + 0.78 * np.clip((P[:, 2] - z_end) / (-z_end), 0, 1) ** 1.3, 0, 1)] * 3, axis=1))
    m.add(tun)
    # threshold slab
    m.add(ak.chipped_block(2 * r + 0.3, 0.14, 0.6, rng, bevel=0.03, chips=2, chip=0.05, material="paving")
          .translate(0, -0.05, 0.25))
    # iron portcullis, jammed half-raised
    pc = mk.Mesh()
    bottom = sp + 0.45
    zp = -0.62
    x = -r + 0.14
    while x < r - 0.1:
        top = sp + math.sqrt(max(r * r - x * x, 0)) - 0.03
        if top - bottom > 0.1:
            pc.add(mk.box(0.055, top - bottom, 0.055, material="iron").translate(x, (top + bottom) / 2, zp))
            spike = mk.hull([(x - 0.03, bottom, zp - 0.03), (x + 0.03, bottom, zp - 0.03), (x - 0.03, bottom, zp + 0.03),
                             (x + 0.03, bottom, zp + 0.03), (x, bottom - 0.16, zp)], "iron")
            pc.add(spike)
        x += 0.3
    for yy in (bottom + 0.12, bottom + 0.62, bottom + 1.12):
        half = math.sqrt(max(r * r - (yy - sp) ** 2, 0)) - 0.04
        if half > 0.2:
            pc.add(mk.box(half * 2, 0.07, 0.04, material="iron").translate(0, yy, zp + 0.05))
            for xx in np.arange(-half + 0.14, half, 0.3):
                pc.add(mk.box(0.03, 0.03, 0.02, material="iron").translate(xx, yy, zp + 0.08))
    m.add(pc)
    m.color_fn(_under_cornice)
    return m


def column_module(seed):
    """Engaged column placed at every bay boundary (separate so mirrored bays
    never double up or drop columns)."""
    rng = np.random.default_rng(seed)
    return ak.column(COL_R, WALL_TOP - BASE_H, rng).translate(0, BASE_H, 0.0)


MODULES = ["PanelA", "PanelB", "PanelC", "Niche", "Gate", "Column"]


def build_modules(W):
    return {
        "PanelA": panel(W, "A", 11),
        "PanelB": panel(W, "B", 12),
        "PanelC": panel(W, "C", 13),
        "Niche": niche(W, 14),
        "Gate": gate(W, 15),
        "Column": column_module(16),
    }


def write_modules(path, W):
    mods = build_modules(W * 1.012)
    s = mk.Scene()
    for name in MODULES:
        s.add(mk.Node(name, mods[name]))
    size = s.write_glb(path, lods=False)
    info = {k: v.tri_count() for k, v in mods.items()}
    print("podium_modules.glb", f"{size / 1e6:.1f} MB", info)
    return info


def assign_modules(bays):
    """bays: list of (k, t, kind). Returns {k: (module, mirror)} with variety."""
    out = {}
    panel_cycle = ["PanelA", "PanelB", "PanelA", "PanelC", "PanelB", "PanelA"]
    pi = 0
    for (k, t, kind) in bays:
        if kind == "gate":
            out[k] = ("Gate", False)
        elif kind == "niche":
            out[k] = ("Niche", k % 2 == 0)
        else:
            out[k] = (panel_cycle[pi % len(panel_cycle)], (k * 7) % 3 == 0)
            pi += 1
    return out


# ============================================================================
# CAVEA (stands): seat blocks, far arcade modules, attic
# ============================================================================

def seat_block(L, R, T, rng, chamfer=0.05, material="lime_seat"):
    """One seat slab: L long (X), R tall (Y, extended down), T deep (Z).
    Front face at z=+T/2, worn chamfer on the front-top edge."""
    drop = R * 1.6
    hx, ht, hz = L / 2, R / 2, T / 2
    c = chamfer * (0.6 + 0.8 * rng.random())
    pts = []
    for sx in (-1, 1):
        pts += [(sx * hx, ht, -hz), (sx * hx, -ht - drop, -hz), (sx * hx, -ht - drop, hz),
                (sx * hx, ht - c, hz), (sx * hx, ht, hz - c * 0.8)]
    P = np.array(pts) + rng.normal(size=(10, 3)) * 0.004
    if rng.random() < 0.35:   # chipped front corner
        k = int(rng.choice([3, 4, 8, 9]))
        P[k] += np.array([0, -1, -1]) * rng.uniform(0.03, 0.08)
    b = mk.hull(P, material)
    return ak.edge_wear(b, light=1.05)


def seat_rows(E, frame, equal_arc_ts, perimeter, d0, y0, steps, tread, rise, aisle_ts, n_sectors, seed,
              aisle_width=1.5):
    """Rows of individual seat slabs around the ellipse, split into angular
    sectors (separate meshes -> frustum culling). Aisles are left open."""
    rng = np.random.default_rng(seed)
    sectors = [mk.Mesh() for _ in range(n_sectors)]
    for i in range(steps):
        d = d0 + i * tread + tread / 2
        y_top = y0 + (i + 1) * rise
        # arc-length parametrisation of this row
        m_ = 3000
        ts = np.linspace(0, 2 * math.pi, m_ + 1)
        p = np.stack([np.cos(ts) * (E(d, 0)[0]), np.sin(ts) * (E(d, math.pi / 2)[2])], axis=1)
        s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
        Ltot = s[-1]
        aisle_s = [np.interp(t, ts, s) for t in aisle_ts]
        pos = rng.random() * 1.5
        while pos < Ltot - 0.3:
            L = rng.uniform(1.1, 2.1)
            a0_, b0_ = pos, min(pos + L, Ltot)
            pos += L
            # trim the slab at stair-aisle edges instead of dropping it whole
            pieces = [(a0_, b0_)]
            for sa in aisle_s:
                for off in (-Ltot, 0.0, Ltot):
                    lo, hi = sa + off - aisle_width / 2, sa + off + aisle_width / 2
                    nxt = []
                    for (pa, pb) in pieces:
                        if pb <= lo or pa >= hi:
                            nxt.append((pa, pb))
                            continue
                        if pa < lo:
                            nxt.append((pa, lo))
                        if pb > hi:
                            nxt.append((hi, pb))
                    pieces = nxt
            for (a, b) in pieces:
                if b - a < 0.3:
                    continue
                if rng.random() < 0.012:      # missing slab
                    continue
                mid = (a + b) / 2
                t = float(np.interp(mid % Ltot, s, ts))
                blk = seat_block(b - a - 0.025, rise, tread, rng)
                dy = rng.uniform(-0.015, 0.012)
                tilt = rng.normal() * 0.006
                blk.rotate((0, 0, 1), tilt).translate(0, dy, 0)
                ak.tint(blk, rng, var=0.16)
                F = frame(d, t, y_top - rise / 2)
                sec = int(t / (2 * math.pi) * n_sectors) % n_sectors
                sectors[sec].add(blk.transform(F))
    for m in sectors:
        m.color_fn(lambda P, N: np.stack([0.82 + 0.18 * np.clip((P[:, 1] - y0) / (steps * rise), 0, 1)] * 3, axis=1))
    return sectors


def column_simple(r, h, rng, seg=10, material="lime_trim"):
    """Low-cost engaged column for distant arcades (no flutes)."""
    a0, a1 = 0.0, math.pi
    m = mk.Mesh()
    m.add(mk.box(2.6 * r, 0.3, 1.3 * r, material=material).translate(0, 0.15, 0.65 * r))
    m.add(mk.lathe([(1.25 * r, 0.3), (1.25 * r, 0.42), (1.05 * r, 0.5), (1.0 * r, 0.55)], seg, material, angle0=a0, angle1=a1, smooth=False))
    m.add(mk.lathe([(r, 0.55), (r * 0.94, h * 0.5), (r * 0.86, h - 0.5)], seg, material, angle0=a0, angle1=a1))
    m.add(mk.lathe([(r * 0.86, h - 0.5), (r * 0.95, h - 0.42), (r * 1.25, h - 0.26)], seg, material, angle0=a0, angle1=a1, smooth=False))
    m.add(mk.box(2.6 * r, 0.24, 1.3 * r, material=material).translate(0, h - 0.12, 0.65 * r))
    return m


def arcade_far(w, height, ow, sp, th, seed, damaged=False, col_r=0.3, wall_mat="lime_ashlar"):
    """Arcade bay for the distant tiers: textured ashlar piers/spandrel
    (course texture), real voussoirs, impost blocks, soffit, engaged column."""
    import build_colosseum as bc
    rng = np.random.default_rng(seed)
    m = mk.Mesh()
    w2 = w * 1.012
    r = ow / 2
    pw = (w2 - ow) / 2
    for sx in (-1, 1):
        cx = sx * (r + pw / 2)
        m.add(mk.box(pw, sp, th, material=wall_mat).translate(cx, sp / 2, -th / 2))
        m.add(ak.chipped_block(pw * 0.55 + 0.1, 0.18, th + 0.12, rng, bevel=0.02, chips=1, material="lime_trim")
              .translate(sx * (r + (pw * 0.55 + 0.1) / 2 - 0.05), sp - 0.09, -th / 2))
    m.add(mk.extrude(bc.arch_poly(w2, ow + 0.02, sp, height), th, material=wall_mat).translate(0, 0, -th / 2))
    m.add(ak.soffit(r, 0.0, -th).translate(0, sp, 0))
    m.add(ak.voussoirs(r, r + 0.3, 0.12, 11, rng, spring=sp, proud=0.06, z_back=-0.04))
    m.add(column_simple(col_r, height - 0.05, rng).translate(-w / 2, 0, 0))
    if damaged:
        g = m.groups[wall_mat]
        hi = (g["P"][:, 1] > height - 0.6) & (g["P"][:, 0] > 0)
        g["P"][hi, 1] -= rng.uniform(0.4, 1.0)
        m.add(ak.rubble(5, (w / 4, sp + 0.02, 0.2), (0.4, 0, 0.1), (0.08, 0.2), rng, material="lime_trim"))
    m.color_fn(lambda P, N: np.stack([0.7 + 0.3 * np.clip(P[:, 1] / height, 0, 1)] * 3, axis=1))
    ak.tint(m, rng, var=0.06)
    return m


def attic_bay(wC, attic_h, seed, broken=False, mast=False):
    rng = np.random.default_rng(seed)
    bay = mk.Mesh()
    h = attic_h * (0.4 + 0.3 * rng.random()) if broken else attic_h
    poly = [(-wC * 1.012 / 2, 0), (wC * 1.012 / 2, 0), (wC * 1.012 / 2, h), (-wC * 1.012 / 2, h)]
    wall = mk.extrude(poly, 1.0, material="lime_ashlar").translate(0, 0, -0.5)
    if broken:
        g = wall.groups["lime_ashlar"]
        top = g["P"][:, 1] > h - 0.01
        g["P"][top, 1] += (rng.random(top.sum()) - 0.5) * 0.9
        bay.add(ak.rubble(4, (0, h, 0.0), (0.8, 0, 0.2), (0.15, 0.35), rng, material="lime_trim"))
    bay.add(wall)
    if not broken:
        bay.add(mk.box(0.85, 1.05, 0.06, material="void").translate(0, 1.6, 0.0))
        for (sx, sy, cx, cy) in ((1.1, 0.1, 0, 2.17), (1.1, 0.1, 0, 1.03), (0.1, 1.05, -0.5, 1.6), (0.1, 1.05, 0.5, 1.6)):
            bay.add(mk.box(sx, sy, 0.14, material="lime_trim").translate(cx, cy, 0.05))
        bay.add(ak.chipped_block(0.42, 0.36, 0.45, rng, bevel=0.03, chips=1, material="lime_trim").translate(-wC / 2, 0.35, 0.22))
        bay.add(ak.chipped_block(wC * 1.012, 0.26, 1.18, rng, bevel=0.02, chips=2, chip=0.05, material="lime_trim").translate(0, h + 0.13, 0))
        if mast:
            bay.add(mk.cylinder(0.12, 6.0, 8, "wood_box", r2=0.09).translate(-wC / 2, 0.5, 0.22))
            bay.add(ak.chipped_block(0.5, 0.25, 0.55, rng, bevel=0.03, chips=1, material="lime_trim").translate(-wC / 2, attic_h - 0.2, 0.22))
    bay.color_fn(lambda P, N: np.stack([0.75 + 0.25 * np.clip(P[:, 1] / attic_h, 0, 1)] * 3, axis=1))
    return bay
