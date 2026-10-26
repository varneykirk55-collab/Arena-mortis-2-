"""
Arena Mortis - Colosseum generator.

Produces the elliptical amphitheatre as several GLBs plus a layout file that
the Godot scene generator uses to place props / gameplay markers.

Coordinate conventions
  * Y up, metres.  Arena floor at y = 0, centre at origin.
  * The arena floor is the ellipse x^2/A^2 + z^2/B^2 = 1.
  * Every structural ring is an "offset ellipse" with semi-axes (A+d, B+d),
    parametrised by angle t:  E(d,t) = ((A+d) cos t, y, (B+d) sin t).
  * Local "bay" frames: X = tangent, Y = up, Z = towards the arena.
"""
import json
import math
import os
import sys

import numpy as np

import meshkit as mk

A, B = 30.0, 20.0              # arena floor semi-axes
PODIUM_H = 5.0                 # podium wall height
PODIUM_T = 1.2                 # podium wall thickness
N_PODIUM_BAYS = 30             # divisible by 6 (gates)
GATE_EVERY = 5
OUT = sys.argv[1] if len(sys.argv) > 1 else "../../assets/models"
LAYOUT = sys.argv[2] if len(sys.argv) > 2 else "../../resources/colosseum_layout.json"

rng = np.random.default_rng(1977)


# ----------------------------------------------------------------------------
# ellipse helpers
# ----------------------------------------------------------------------------

def E(d, t, y=0.0):
    return np.array([(A + d) * math.cos(t), y, (B + d) * math.sin(t)])


def n_out(d, t):
    n = np.array([(B + d) * math.cos(t), 0.0, (A + d) * math.sin(t)])
    return n / np.linalg.norm(n)


def tangent(d, t):
    v = np.array([-(A + d) * math.sin(t), 0.0, (B + d) * math.cos(t)])
    return v / np.linalg.norm(v)


def frame(d, t, y=0.0):
    """4x4 local frame. X=tangent, Y=up, Z=inward (towards arena)."""
    m = np.eye(4)
    m[:3, 0] = tangent(d, t)
    m[:3, 1] = (0, 1, 0)
    m[:3, 2] = -n_out(d, t)
    m[:3, 3] = E(d, t, y)
    return m


def perimeter(d, n=2000):
    ts = np.linspace(0, 2 * math.pi, n + 1)
    p = np.stack([(A + d) * np.cos(ts), (B + d) * np.sin(ts)], axis=1)
    return float(np.sum(np.linalg.norm(np.diff(p, axis=0), axis=1)))


def equal_arc_ts(d, n, phase=0.0):
    """n parameter values evenly spaced by arc length; phase in bay units."""
    m = 4000
    ts = np.linspace(0, 2 * math.pi, m + 1)
    p = np.stack([(A + d) * np.cos(ts), (B + d) * np.sin(ts)], axis=1)
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
    L = s[-1]
    targets = (np.arange(n) + phase) / n * L
    return np.interp(targets % L, s, ts)


def bay_width(d, n):
    return perimeter(d) / n


# ----------------------------------------------------------------------------
# sweeps (continuous ring geometry)
# ----------------------------------------------------------------------------

def sweep(profile, d0, n=240, material="stone_plain", t0=0.0, t1=2 * math.pi, grime_cfg=None):
    """Sweep a (dd, y) polyline around the offset ellipse at base offset d0.
    Visible side = left of the walking direction (toward arena / up)."""
    closed = abs(t1 - t0 - 2 * math.pi) < 1e-6
    nt = n if closed else n + 1
    ts = t0 + (t1 - t0) * np.arange(nt) / n
    out = mk.Mesh()
    prof = np.asarray(profile, dtype=np.float64)
    for i in range(len(prof) - 1):
        (da, ya), (db, yb) = prof[i], prof[i + 1]
        sx, sy = db - da, yb - ya
        L = math.hypot(sx, sy)
        if L < 1e-6:
            continue
        n2 = np.array([-sy, sx]) / L
        P, N, UV = [], [], []
        for j, t in enumerate(ts):
            no = n_out(d0, t)
            for (dd, yy, v) in ((da, ya, 0.0), (db, yb, L)):
                P.append(E(d0 + dd, t, yy))
                nn = no * n2[0] + np.array([0, 1.0, 0]) * n2[1]
                N.append(nn / np.linalg.norm(nn))
                UV.append((t * (A + d0), v))
        idx = []
        for j in range(nt - (0 if closed else 1)):
            jn = (j + 1) % nt
            a, b = 2 * j, 2 * j + 1
            c, d = 2 * jn, 2 * jn + 1
            idx += [(a, b, c), (c, b, d)]
        m = mk.Mesh.from_arrays(np.array(P), np.array(N), np.array(idx), np.array(UV), material)
        g = m.groups[material]
        tri = g["P"][g["I"]]
        fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        vn = g["N"][g["I"][:, 0]]
        flip = np.sum(fn * vn, axis=1) < 0
        g["I"][flip] = g["I"][flip][:, ::-1]
        out.add(m)
    if grime_cfg is not None:
        lo, hi, dark = grime_cfg
        out.color_fn(lambda p, n_: mk.grime(p, n_, low_y=lo, high_y=hi, dark=dark))
    return out


def place(mesh, d, t, y=0.0):
    return mesh.copy().transform(frame(d, t, y))


# ----------------------------------------------------------------------------
# architectural pieces (built in local bay space)
# ----------------------------------------------------------------------------

def arch_poly(w, ow, spring, top, seg=14):
    pts = [(-w / 2, spring), (-ow / 2, spring)]
    r = ow / 2
    for i in range(1, seg):
        a = math.pi - math.pi * i / seg
        pts.append((r * math.cos(a), spring + r * math.sin(a)))
    pts += [(ow / 2, spring), (w / 2, spring), (w / 2, top), (-w / 2, top)]
    return pts


def half_annulus(r0, r1, seg=14):
    outer = [(r1 * math.cos(math.pi * i / seg), r1 * math.sin(math.pi * i / seg)) for i in range(seg + 1)]
    inner = [(r0 * math.cos(math.pi * i / seg), r0 * math.sin(math.pi * i / seg)) for i in range(seg, -1, -1)]
    return outer + inner


def arcade_bay(w, height, ow, spring, th, mat="stone_blocks", trim="stone_plain",
               column=True, col_r=0.3, archivolt=True, keystone=True, damaged=0.0, seed=0):
    """One bay of an arcade wall; face at z=0, wall extends to z=-th."""
    m = mk.Mesh()
    w2 = w * 1.012
    # piers
    pw = (w2 - ow) / 2
    for sgn in (-1, 1):
        cx = sgn * (ow / 2 + pw / 2)
        m.add(mk.box(pw, spring, th, bevel=0.03, material=mat).translate(cx, spring / 2, -th / 2))
        # impost moulding
        m.add(mk.box(pw + 0.1, 0.22, th + 0.16, bevel=0.04, material=trim).translate(cx, spring - 0.11, -th / 2))
    # spandrel with arch cut
    sp = mk.extrude(arch_poly(w2, ow, spring, height), th, material=mat).translate(0, 0, -th / 2)
    m.add(sp)
    if archivolt:
        av = mk.extrude(half_annulus(ow / 2, ow / 2 + 0.28), 0.16, material=trim, bevel=0.03).translate(0, spring, 0.06)
        m.add(av)
        if keystone:
            ks = mk.tapered_box((0.34, 0.3), (0.46, 0.3), 0.5, bevel=0.03, material=trim).translate(0, spring + ow / 2 - 0.08, 0.12)
            m.add(ks)
    if column:
        ch = height - 0.05
        shaft = mk.lathe([(col_r * 1.0, 0.45), (col_r * 0.97, ch * 0.5), (col_r * 0.88, ch - 0.5)], 12, trim,
                         angle0=0, angle1=math.pi)
        base = mk.lathe([(col_r * 1.35, 0.0), (col_r * 1.35, 0.18), (col_r * 1.2, 0.28), (col_r * 1.05, 0.45)], 12, trim,
                        angle0=0, angle1=math.pi, smooth=False)
        cap = mk.lathe([(col_r * 0.88, ch - 0.5), (col_r * 1.05, ch - 0.38), (col_r * 1.3, ch - 0.25)], 12, trim,
                       angle0=0, angle1=math.pi, smooth=False)
        abacus = mk.box(col_r * 2.8, 0.25, col_r * 1.5, bevel=0.03, material=trim).translate(0, ch - 0.12, col_r * 0.6)
        plinth = mk.box(col_r * 2.9, 0.4, col_r * 1.6, bevel=0.03, material=trim).translate(0, 0.2, col_r * 0.6)
        col = mk.merge(shaft, base, cap, abacus, plinth)
        m.add(col.translate(-w / 2, 0, 0))
    if damaged > 0:
        m.jitter(damaged, seed)
    return m


def corridor(d_face, th, depth, y0, h, n, t0=0.0, t1=2 * math.pi):
    """Dark ambulatory behind an arcade: floor, back wall, ceiling."""
    d1 = d_face + th
    d2 = d_face + th + depth
    prof_floor = [(0, y0), (d2 - d_face, y0)]
    prof_back = [(d2 - d_face, y0), (d2 - d_face, y0 + h)]
    prof_ceil = [(d2 - d_face, y0 + h), (th, y0 + h)]
    m = mk.merge(
        sweep(prof_floor, d_face, n, "stone_dark", t0, t1),
        sweep(prof_back, d_face, n, "stone_dark", t0, t1),
        sweep(prof_ceil, d_face, n, "stone_dark", t0, t1),
    )
    m.color_fn(lambda p, n_: np.full((len(p), 3), 0.45))
    return m


def entablature(d_face, y, n=240, depth=0.35, h=0.7, mat="stone_plain"):
    """Cornice band (profile protrudes toward arena, i.e. negative dd)."""
    prof = [(0, y), (-depth * 0.4, y), (-depth * 0.4, y + h * 0.45), (-depth * 0.7, y + h * 0.55),
            (-depth, y + h * 0.8), (-depth, y + h), (0.0, y + h)]
    return sweep(prof, d_face, n, mat)


def rubble(n, center_fn, spread=1.2, size=(0.15, 0.6), mat="stone_plain", seed=0):
    r = np.random.default_rng(seed)
    m = mk.Mesh()
    for i in range(n):
        s = size[0] + (size[1] - size[0]) * r.random() ** 2
        pts = r.normal(size=(9, 3)) * np.array([s, s * 0.6, s])
        rock = mk.hull(pts, mat)
        c = center_fn(r)
        off = r.normal(size=3) * spread
        off[1] = 0
        rock.rotate((0, 1, 0), r.random() * 6.28).translate(*(c + off + np.array([0, s * 0.25, 0])))
        m.add(rock)
    return m


# ----------------------------------------------------------------------------
# PODIUM (arena wall with gates and niches)
# ----------------------------------------------------------------------------

GATE_W, GATE_SPRING, GATE_DEPTH = 3.4, 2.7, 7.0
NICHE_W, NICHE_SPRING, NICHE_DEPTH = 2.2, 2.6, 0.75


def build_podium(layout):
    vis = mk.Mesh()
    col = mk.Mesh()      # collision (trimesh, invisible)
    ts = equal_arc_ts(0.0, N_PODIUM_BAYS)
    w = bay_width(0.0, N_PODIUM_BAYS)
    layout["podium_bay_width"] = w
    th = PODIUM_T
    bays = []
    for k, t in enumerate(ts):
        kind = "gate" if k % GATE_EVERY == 0 else ("niche" if k % GATE_EVERY in (1, 4) else "panel")
        bays.append((k, t, kind))
    for (k, t, kind) in bays:
        bay = mk.Mesh()
        w2 = w * 1.012
        if kind == "gate":
            ow, spring = GATE_W, GATE_SPRING
            bay.add(arcade_bay(w, PODIUM_H - 0.55, ow, spring, th, column=False, archivolt=True))
            # tunnel: side walls, vault, floor, rubble back wall
            r = ow / 2
            tunnel = mk.Mesh()
            for sgn in (-1, 1):
                tunnel.add(mk.box(0.6, spring, GATE_DEPTH, material="stone_blocks").translate(sgn * (r + 0.3), spring / 2, -th - GATE_DEPTH / 2 + 0.01))
            vault = mk.extrude(half_annulus(r, r + 0.5), GATE_DEPTH, material="stone_blocks").translate(0, spring, -th - GATE_DEPTH / 2 + 0.01)
            tunnel.add(vault)
            tunnel.add(mk.box(ow + 1.2, 0.2, GATE_DEPTH + th, material="sand").translate(0, -0.1, -(GATE_DEPTH + th) / 2))
            backwall = mk.box(ow + 1.2, spring + r + 0.5, 0.5, material="stone_dark").translate(0, (spring + r + 0.5) / 2, -th - GATE_DEPTH + 0.2)
            tunnel.add(backwall)
            tunnel.color_fn(lambda p, n_: np.clip(0.25 + 0.75 * np.clip((p[:, 2] + th + GATE_DEPTH) / GATE_DEPTH, 0, 1), 0, 1) * np.ones(len(p)))
            bay.add(tunnel)
            # rubble pile at tunnel end (zombies "emerge" from it)
            bay.add(rubble(14, lambda r_: np.array([0, 0, -th - GATE_DEPTH + 1.2]), 0.9, (0.2, 0.7), "stone_plain", seed=k))
            # raised, bent portcullis hanging in the arch
            pc = mk.Mesh()
            bars = 7
            for i in range(bars):
                x = -r + 0.25 + i * (ow - 0.5) / (bars - 1)
                ytop = spring + math.sqrt(max(r * r - x * x, 0)) - 0.05
                ybot = spring + 0.35 + (0.25 if i % 2 else 0) + rng.random() * 0.2
                pc.add(mk.cylinder(0.045, ytop - ybot, 6, "iron").translate(x, ybot, -0.35))
                pc.add(mk.cylinder(0.07, 0.2, 6, "iron", r2=0.01).rotate((1, 0, 0), math.pi).translate(x, ybot, -0.35))
            for yy in (spring + 0.6, spring + 1.2):
                half = math.sqrt(max(r * r - (yy - spring) ** 2, 0)) - 0.05
                pc.add(mk.box(half * 2, 0.08, 0.08, material="iron").translate(0, yy, -0.35))
            bay.add(pc)
            # collision: piers + tunnel walls (so the player can walk in the tunnel)
            cb = mk.Mesh()
            for sgn in (-1, 1):
                cb.add(mk.box((w2 - ow) / 2, PODIUM_H, th, material="col").translate(sgn * (ow / 2 + (w2 - ow) / 4), PODIUM_H / 2, -th / 2))
                cb.add(mk.box(0.6, PODIUM_H, GATE_DEPTH, material="col").translate(sgn * (r + 0.3), PODIUM_H / 2, -th - GATE_DEPTH / 2 + 0.01))
            cb.add(mk.box(ow, PODIUM_H - spring, th, material="col").translate(0, spring + (PODIUM_H - spring) / 2, -th / 2))
            cb.add(mk.box(ow + 1.2, PODIUM_H, 0.5, material="col").translate(0, PODIUM_H / 2, -th - GATE_DEPTH + 0.2))
            cb.add(mk.box(ow + 1.2, 1.0, GATE_DEPTH, material="col").translate(0, spring + r + 0.5, -th - GATE_DEPTH / 2))
            cb.add(mk.box(ow + 1.2, 0.2, GATE_DEPTH + th, material="col").translate(0, -0.1, -(GATE_DEPTH + th) / 2))
            col.add(place(cb, 0.0, t))
            spawn = frame(0.0, t) @ np.array([0, 0.05, -th - GATE_DEPTH + 2.4, 1.0])
            inner = frame(0.0, t) @ np.array([0, 0.05, 1.5, 1.0])
            layout.setdefault("gates", []).append({
                "index": len(layout.get("gates", [])), "t": t,
                "spawn": spawn[:3].tolist(), "mouth": inner[:3].tolist(),
                "basis": frame(0.0, t)[:3, :3].T.tolist(),
            })
            # torches either side of each gate
            for sgn in (-1, 1):
                p = frame(0.0, t) @ np.array([sgn * (ow / 2 + 0.75), 3.0, 0.12, 1.0])
                layout.setdefault("torches", []).append({"pos": p[:3].tolist(), "basis": frame(0.0, t)[:3, :3].T.tolist()})
        elif kind == "niche":
            # front layer with arched opening + back panel
            front_t = NICHE_DEPTH
            bay.add(arcade_bay(w, PODIUM_H - 0.55, NICHE_W, NICHE_SPRING, front_t, column=True, col_r=0.26))
            bay.add(mk.box(w2, PODIUM_H - 0.55, th - front_t, material="stone_blocks").translate(0, (PODIUM_H - 0.55) / 2, -front_t - (th - front_t) / 2))
            bay.add(mk.box(NICHE_W + 0.1, 0.5, NICHE_DEPTH - 0.05, bevel=0.04, material="stone_plain").translate(0, 0.25, -NICHE_DEPTH / 2))
            cb = mk.box(w2, PODIUM_H, th, material="col").translate(0, PODIUM_H / 2, -th / 2)
            col.add(place(cb, 0.0, t))
            sp = frame(0.0, t) @ np.array([0, 0.5, -NICHE_DEPTH / 2, 1.0])
            layout.setdefault("niches", []).append({"pos": sp[:3].tolist(), "basis": frame(0.0, t)[:3, :3].T.tolist(), "bay": k})
        else:
            # panel bay: plain wall with framed marble panel and pilaster
            bay.add(mk.box(w2, PODIUM_H - 0.55, th, bevel=0.02, material="stone_blocks").translate(0, (PODIUM_H - 0.55) / 2, -th / 2))
            panel = mk.box(w * 0.62, 2.4, 0.08, bevel=0.03, material="marble").translate(0, 2.3, 0.04)
            frame_ = mk.Mesh()
            for (sx, sy, cx, cy) in ((w * 0.7, 0.14, 0, 3.57), (w * 0.7, 0.14, 0, 1.03), (0.14, 2.68, -w * 0.35, 2.3), (0.14, 2.68, w * 0.35, 2.3)):
                frame_.add(mk.box(sx, sy, 0.16, bevel=0.03, material="stone_plain").translate(cx, cy, 0.06))
            bay.add(panel)
            bay.add(frame_)
            # pilaster at bay edge
            pil = mk.box(0.6, PODIUM_H - 0.55, 0.22, bevel=0.03, material="stone_plain").translate(-w / 2, (PODIUM_H - 0.55) / 2, 0.08)
            bay.add(pil)
            cb = mk.box(w2, PODIUM_H, th, material="col").translate(0, PODIUM_H / 2, -th / 2)
            col.add(place(cb, 0.0, t))
            p = frame(0.0, t) @ np.array([0, 0.0, 1.6, 1.0])
            layout.setdefault("panels", []).append({"pos": p[:3].tolist(), "basis": frame(0.0, t)[:3, :3].T.tolist(), "bay": k})
            bp = frame(0.0, t) @ np.array([0, PODIUM_H - 0.2, 0.25, 1.0])
            layout.setdefault("banners_low", []).append({"pos": bp[:3].tolist(), "basis": frame(0.0, t)[:3, :3].T.tolist()})
        bay.color_fn(lambda p, n_: mk.grime(p, n_, low_y=0.0, high_y=3.0, dark=0.5, seed=k))
        vis.add(place(bay, 0.0, t))

    # continuous parts: plinth, cornice, terrace, parapet
    n = 360
    plinth = sweep([(0.0, 0.0), (-0.18, 0.0), (-0.18, 0.45), (-0.06, 0.6), (0.0, 0.6)], 0.0, n, "stone_plain")
    plinth_mask = plinth  # (gates cut through visually - acceptable: plinth stops at gate bays)
    vis.add(_cut_gates(plinth_mask, ts, bays, w))
    cornice = sweep([(0.0, PODIUM_H - 0.55), (-0.1, PODIUM_H - 0.55), (-0.1, PODIUM_H - 0.35), (-0.35, PODIUM_H - 0.2),
                     (-0.35, PODIUM_H), (0.3, PODIUM_H)], 0.0, n, "stone_plain")
    vis.add(cornice)
    terrace = sweep([(0.3, PODIUM_H), (4.0, PODIUM_H)], 0.0, n, "stone_seat")
    vis.add(terrace)
    parapet = sweep([(-0.05, PODIUM_H), (-0.05, PODIUM_H + 0.95), (-0.15, PODIUM_H + 1.0), (-0.15, PODIUM_H + 1.12),
                     (0.45, PODIUM_H + 1.12), (0.45, PODIUM_H + 1.0), (0.35, PODIUM_H + 0.95), (0.35, PODIUM_H)], 0.0, n, "stone_plain")
    vis.add(parapet)
    vis.color_fn(lambda p, n_: np.where(p[:, 1] > PODIUM_H - 0.6, 0.95, 1.0) * np.ones(len(p)))

    # collision for the full wall top (prevents climbing / jumping out)
    col.add(sweep([(0.0, PODIUM_H), (0.0, PODIUM_H + 30.0)], 0.0, 96, "col"))
    return vis, col, bays


def _cut_gates(mesh, ts, bays, w):
    """Remove triangles of a continuous sweep that fall inside gate openings."""
    for g in mesh.groups.values():
        P = g["P"]
        tri_c = P[g["I"]].mean(axis=1)
        keep = np.ones(len(g["I"]), dtype=bool)
        for (k, t, kind) in bays:
            if kind != "gate":
                continue
            c = E(0.0, t)
            tg = tangent(0.0, t)
            along = (tri_c - c) @ tg
            dist = np.linalg.norm((tri_c - c) * np.array([1, 0, 1]), axis=1)
            keep &= ~((np.abs(along) < GATE_W / 2 + 0.05) & (dist < GATE_W))
        g["I"] = g["I"][keep]
    return mesh


# ----------------------------------------------------------------------------
# CAVEA (seating, tier walls, galleries)
# ----------------------------------------------------------------------------

TREAD, RISE = 0.8, 0.45


def seat_steps(d0, y0, steps, n=360):
    prof = [(0.0, y0)]
    d, y = 0.0, y0
    for i in range(steps):
        prof.append((d, y + RISE))
        y += RISE
        prof.append((d + TREAD, y))
        d += TREAD
    m = sweep(prof, d0, n, "stone_seat")
    # subtle per-step darkening of risers + grime
    m.color_fn(lambda p, n_: (0.78 + 0.22 * (n_[:, 1] > 0.5)) * mk.grime(p, n_, low_y=y0, high_y=y0 + steps * RISE, dark=0.8, noise_amt=0.35)[:, 0])
    return m, d0 + steps * TREAD, y0 + steps * RISE


def stair_aisles(d0, y0, steps, count, phase=0.5, width=1.3):
    m = mk.Mesh()
    ts = equal_arc_ts(d0, count, phase)
    for t in ts:
        for i in range(steps):
            d = d0 + i * TREAD + TREAD / 2
            y = y0 + (i + 1) * RISE
            blk = mk.box(width, RISE / 2, TREAD / 2, material="stone_plain")
            blk.translate(0, RISE / 4, -TREAD / 4)
            fr = frame(d, t, y)
            m.add(blk.transform(fr))
        # side curbs (low walls along the aisle)
        for sgn in (-1, 1):
            for i in range(steps):
                d = d0 + i * TREAD
                y = y0 + i * RISE
                curb = mk.box(0.18, RISE + 0.25, TREAD, material="stone_plain")
                curb.translate(sgn * (width / 2 + 0.09), (RISE + 0.25) / 2, -TREAD / 2)
                m.add(curb.transform(frame(d, t, y)))
    m.color_fn(lambda p, n_: mk.grime(p, n_, low_y=y0, high_y=y0 + steps * RISE, dark=0.8))
    return m


def arcade_ring(d_face, y0, height, bay_target, ow, spring, th, column=True, corridor_depth=2.5,
                damaged_bays=(), mat="stone_blocks", seed=0, layout_key=None, layout=None, phase=0.5):
    n = max(6, int(round(perimeter(d_face) / bay_target)))
    ts = equal_arc_ts(d_face, n, phase)
    w = bay_width(d_face, n)
    m = mk.Mesh()
    for k, t in enumerate(ts):
        bay = arcade_bay(w, height, ow, spring, th, mat=mat, column=column, damaged=0.02, seed=seed + k)
        if k in damaged_bays:
            # knock a chunk out of the spandrel top
            g = bay.groups.get(mat)
            if g is not None:
                hi = g["P"][:, 1] > height - 0.4
                g["P"][hi, 1] -= rng.random() * 0.8 + 0.3
        bay.color_fn(lambda p, n_, k=k: mk.grime(p, n_, low_y=0.0, high_y=height, dark=0.7, seed=seed + k))
        m.add(place(bay, d_face, t, y0))
        if layout is not None and layout_key:
            p = frame(d_face, t, y0) @ np.array([-w / 2, height - 0.9, 0.35, 1.0])
            layout.setdefault(layout_key, []).append({"pos": p[:3].tolist(), "basis": frame(d_face, t)[:3, :3].T.tolist()})
    m.add(corridor(d_face, th, corridor_depth, y0, height - 0.3, 240))
    return m, n


def build_cavea(layout):
    vis = mk.Mesh()
    # --- seats I ---
    s1, d_end1, y_end1 = seat_steps(4.0, PODIUM_H, 14)
    vis.add(s1)
    vis.add(stair_aisles(4.0, PODIUM_H, 14, 20))
    # praecinctio walkway
    d_wall2 = d_end1 + 1.0
    vis.add(sweep([(d_end1, y_end1), (d_wall2, y_end1)], 0.0, 360, "stone_seat"))
    # --- tier wall II (arcade) ---
    h2 = 4.0
    ar2, n2 = arcade_ring(d_wall2, y_end1, h2, 4.2, 2.0, 1.9, 0.8, column=True, corridor_depth=2.2,
                          seed=100, layout=layout, layout_key="tier2_bays")
    vis.add(ar2)
    y2 = y_end1 + h2
    vis.add(entablature(d_wall2, y2 - 0.55, 360, 0.3, 0.55))
    # parapet ledge on top of tier wall
    vis.add(sweep([(0.0, y2), (0.8, y2)], d_wall2, 360, "stone_seat"))
    # --- seats II ---
    s2, d_end2, y_end2 = seat_steps(d_wall2 + 0.8, y2, 11)
    vis.add(s2)
    vis.add(stair_aisles(d_wall2 + 0.8, y2, 11, 24, phase=0.25))
    d_top = d_end2 + 1.0
    vis.add(sweep([(d_end2, y_end2), (d_top, y_end2)], 0.0, 360, "stone_seat"))
    # --- top gallery: two arcade storeys + attic ---
    hA, hB = 6.0, 5.0
    arA, nA = arcade_ring(d_top, y_end2, hA, 4.8, 2.8, 3.9, 1.0, column=True, corridor_depth=3.0, seed=200,
                          damaged_bays=(), layout=layout, layout_key="galleryA_bays", phase=0.0)
    vis.add(arA)
    vis.add(entablature(d_top, y_end2 + hA - 0.6, 360, 0.4, 0.75))
    arB, nB = arcade_ring(d_top, y_end2 + hA + 0.15, hB, 4.8, 2.4, 3.1, 1.0, column=True, corridor_depth=2.4,
                          seed=300, phase=0.0)
    vis.add(arB)
    yC = y_end2 + hA + 0.15 + hB
    vis.add(entablature(d_top, yC - 0.6, 360, 0.4, 0.75))
    # attic: solid wall with small windows and corbels, jagged broken top in places
    attic = mk.Mesh()
    nC = nA
    tsC = equal_arc_ts(d_top, nC, 0.0)
    wC = bay_width(d_top, nC)
    attic_h = 3.6
    broken = set(int(x) for x in rng.choice(nC, size=max(3, nC // 7), replace=False))
    for k, t in enumerate(tsC):
        bay = mk.Mesh()
        h = attic_h
        if k in broken:
            h = attic_h * (0.35 + rng.random() * 0.4)
        win_poly = [(-wC * 1.012 / 2, 0), (wC * 1.012 / 2, 0), (wC * 1.012 / 2, h), (-wC * 1.012 / 2, h)]
        wall = mk.extrude(win_poly, 1.0, material="stone_blocks").translate(0, 0, -0.5)
        if k in broken:
            g = wall.groups["stone_blocks"]
            top = g["P"][:, 1] > h - 0.01
            g["P"][top, 1] += (rng.random(top.sum()) - 0.5) * 0.9
        bay.add(wall)
        if k not in broken:
            # small rectangular window (dark inset) + corbels (velarium mast supports)
            bay.add(mk.box(0.9, 1.1, 0.06, material="void").translate(0, 1.6, 0.02))
            for yy in (1.0, 2.2):
                bay.add(mk.box(1.2, 0.12, 0.2, bevel=0.02, material="stone_plain").translate(0, yy, 0.08))
            bay.add(mk.box(0.4, 0.35, 0.45, bevel=0.03, material="stone_plain").translate(-wC / 2, 0.35, 0.22))
            if k % 2 == 0:
                # velarium mast
                bay.add(mk.cylinder(0.12, 6.0, 8, "wood_box", r2=0.09).translate(-wC / 2, 0.5, 0.22))
                bay.add(mk.box(0.5, 0.25, 0.55, bevel=0.03, material="stone_plain").translate(-wC / 2, attic_h - 0.2, 0.22))
        bay.add(mk.box(wC * 1.012, 0.25, 1.15, bevel=0.03, material="stone_plain").translate(0, h + 0.12, 0) if k not in broken else mk.Mesh())
        bay.color_fn(lambda p, n_, k=k: mk.grime(p, n_, low_y=0, high_y=attic_h, dark=0.75, seed=400 + k))
        attic.add(place(bay, d_top, t, yC))
    vis.add(attic)
    layout["top_height"] = yC + attic_h
    layout["tiers"] = {"seats1": [4.0, PODIUM_H, d_end1, y_end1], "wall2": [d_wall2, y_end1, y2],
                       "seats2": [d_wall2 + 0.8, y2, d_end2, y_end2], "gallery": [d_top, y_end2, yC]}
    # banner hang points on the tier-2 wall entablature and gallery
    return vis


# ----------------------------------------------------------------------------
# FLOOR
# ----------------------------------------------------------------------------

def build_floor(layout):
    rings, segs = 48, 240
    P = []
    for i in range(rings + 1):
        r = i / rings
        for j in range(segs):
            t = 2 * math.pi * j / segs
            ex = 1.0 + (PODIUM_T + 0.6) / A * (r ** 8) * 0  # floor ends under the wall
            x = (A * r + (0.8 if i == rings else 0)) * math.cos(t)
            z = (B * r + (0.8 if i == rings else 0)) * math.sin(t)
            P.append((x, 0.0, z))
    P = np.array(P)
    # gentle undulation + ruts
    nz = mk.value_noise3(P * np.array([1, 0, 1]), 0.12, 5) - 0.5
    nz2 = mk.value_noise3(P * np.array([1, 0, 1]), 0.6, 6) - 0.5
    rr = np.sqrt((P[:, 0] / A) ** 2 + (P[:, 2] / B) ** 2)
    P[:, 1] = (nz * 0.18 + nz2 * 0.04) * np.clip((1.0 - rr) * 6, 0, 1)
    idx = []
    for i in range(rings):
        for j in range(segs):
            jn = (j + 1) % segs
            a = i * segs + j
            b = i * segs + jn
            c = (i + 1) * segs + j
            d = (i + 1) * segs + jn
            idx += [(a, b, c), (b, d, c)]
    m = mk.Mesh.from_arrays(P, np.zeros_like(P), np.array(idx), P[:, [0, 2]] * 0.25, "sand")
    m.recompute_normals_smooth()
    g = m.groups["sand"]
    if g["N"][:, 1].mean() < 0:
        g["I"] = g["I"][:, ::-1].copy()
        g["N"] = -g["N"]
    # darker near the wall, scuffed centre
    m.color_fn(lambda p, n_: np.clip(0.7 + 0.3 * (1 - rr ** 4) + 0.25 * (mk.value_noise3(p, 0.35, 9) - 0.5), 0.5, 1.1) * np.ones(len(p)))
    floor = m

    # hypogeum grates (iron grilles flush with the sand) - 4 in a cross
    grates = mk.Mesh()
    for (gx, gz, rot) in ((-14.0, 0.0, 0.0), (14.0, 0.0, 0.0), (0.0, -9.5, math.pi / 2), (0.0, 9.5, math.pi / 2)):
        gm = mk.Mesh()
        gm.add(mk.box(3.2, 0.12, 2.2, bevel=0.02, material="stone_plain").translate(0, -0.02, 0))
        gm.add(mk.box(2.8, 0.05, 1.8, material="void").translate(0, 0.02, 0))
        for i in range(9):
            gm.add(mk.box(0.07, 0.08, 1.8, material="iron").translate(-1.3 + i * 2.6 / 8, 0.06, 0))
        for i in range(4):
            gm.add(mk.box(2.7, 0.06, 0.06, material="iron").translate(0, 0.07, -0.75 + i * 0.5))
        grates.add(gm.rotate((0, 1, 0), rot).translate(gx, 0.05, gz))
    layout["grates"] = [[-14.0, 0, 0.0], [14.0, 0, 0.0], [0.0, 0, -9.5], [0.0, 0, 9.5]]

    # collision: coarse floor disk (flat at y=0)
    col = mk.Mesh()
    cP = [(0, 0, 0)] + [((A + 2.5) * math.cos(2 * math.pi * j / 64), 0, (B + 2.5) * math.sin(2 * math.pi * j / 64)) for j in range(64)]
    cI = [(0, 1 + (j + 1) % 64, 1 + j) for j in range(64)]
    col.add(mk.Mesh.from_arrays(np.array(cP, dtype=float), np.tile([0, 1.0, 0], (65, 1)), np.array(cI), None, "col"))
    return floor, grates, col


# ----------------------------------------------------------------------------
# arena obstacles (cover / navigation obstacles)
# ----------------------------------------------------------------------------

def column_drum(r=0.55, h=0.9, fluted=True, mat="stone_plain"):
    seg = 20
    prof = []
    m = mk.lathe([(r, 0), (r, h)], seg, mat, cap_top=True, cap_bottom=True)
    if fluted:
        g = m.groups[mat]
        ang = np.arctan2(g["P"][:, 2], g["P"][:, 0])
        rad = np.linalg.norm(g["P"][:, [0, 2]], axis=1)
        side = rad > r * 0.98
        fl = 1 - 0.05 * (np.cos(ang * seg) * 0.5 + 0.5)
        g["P"][side, 0] *= fl[side]
        g["P"][side, 2] *= fl[side]
    return m


def build_obstacles(layout):
    """Returns dict name -> (visual mesh, collision mesh) placed in world space."""
    vis = mk.Mesh()
    col = mk.Mesh()
    obs = []

    def add(m, c, info):
        vis.add(m)
        col.add(c)
        obs.append(info)

    # 1. fallen column (3 drums rolled apart) + standing broken column base
    for (cx, cz, yaw, seed) in ((-9.0, 8.0, 0.4, 1), (10.5, -7.5, 2.2, 2)):
        m = mk.Mesh()
        c = mk.Mesh()
        base = mk.box(1.8, 0.6, 1.8, bevel=0.05, material="stone_plain").translate(0, 0.3, 0)
        stand = column_drum(0.55, 1.6).translate(0, 0.6, 0)
        stand_top = stand.groups["stone_plain"]
        top = stand_top["P"][:, 1] > 2.1
        stand_top["P"][top, 1] += (np.random.default_rng(seed).random(top.sum()) - 0.5) * 0.5
        m.add(base)
        m.add(stand)
        c.add(mk.box(1.8, 2.3, 1.8, material="col").translate(0, 1.15, 0))
        for i in range(3):
            drum = column_drum(0.55, 0.9).rotate((0, 0, 1), math.pi / 2).rotate((0, 1, 0), 0.3 * i)
            drum.translate(2.0 + i * 1.05, 0.55, -0.4 + 0.5 * i)
            m.add(drum)
            c.add(mk.box(0.95, 1.1, 1.15, material="col").rotate((0, 1, 0), 0.3 * i).translate(2.0 + i * 1.05 - 0.45, 0.55, -0.4 + 0.5 * i))
        m.jitter(0.015, seed)
        m.color_fn(lambda p, n_: mk.grime(p, n_, low_y=0, high_y=1.5, dark=0.6))
        T = mk.mat_translate((cx, 0, cz)) @ mk.ry(yaw)
        add(m.transform(T), c.transform(T), {"type": "fallen_column", "pos": [cx, 0, cz]})

    # 2. ruined wall fragment with arch (cover)
    for (cx, cz, yaw) in ((-16.0, -6.5, 1.1), (17.0, 7.0, 4.2)):
        m = mk.Mesh()
        frag = arcade_bay(4.6, 4.2, 2.2, 2.2, 0.9, column=False, damaged=0.04, seed=abs(int(cx)))
        g = frag.groups["stone_blocks"]
        hi = g["P"][:, 1] > 3.0
        xs = g["P"][hi, 0]
        g["P"][hi, 1] -= np.clip(xs + 1.5, 0, 3) * 0.45 + np.random.default_rng(3).random(hi.sum()) * 0.4
        frag.translate(0, 0, 0.45)
        m.add(frag)
        m.add(rubble(10, lambda r_: np.array([1.4, 0, 1.2]), 0.9, (0.15, 0.5), seed=abs(int(cz * 10))))
        m.color_fn(lambda p, n_: mk.grime(p, n_, low_y=0, high_y=3, dark=0.55))
        c = mk.Mesh()
        c.add(mk.box(1.2, 4.0, 0.9, material="col").translate(-1.7, 2.0, 0))
        c.add(mk.box(1.2, 3.0, 0.9, material="col").translate(1.7, 1.5, 0))
        c.add(mk.box(2.2, 1.6, 0.9, material="col").translate(0, 3.0, 0))
        T = mk.mat_translate((cx, 0, cz)) @ mk.ry(yaw)
        add(m.transform(T), c.transform(T), {"type": "ruin_wall", "pos": [cx, 0, cz]})

    # 3. stone altar with steps at centre-north/south (low cover; dais for statue)
    for (cx, cz, yaw) in ((0.0, 0.0, 0.0),):
        m = mk.Mesh()
        m.add(mk.box(4.6, 0.3, 3.2, bevel=0.04, material="stone_plain").translate(0, 0.15, 0))
        m.add(mk.box(3.8, 0.3, 2.4, bevel=0.04, material="stone_plain").translate(0, 0.45, 0))
        m.add(mk.box(2.4, 1.0, 1.2, bevel=0.05, material="marble").translate(0, 1.1, 0))
        m.add(mk.box(2.7, 0.2, 1.45, bevel=0.04, material="stone_plain").translate(0, 1.7, 0))
        m.add(mk.box(2.6, 0.15, 1.35, bevel=0.03, material="stone_plain").translate(0, 0.65, 0))
        m.color_fn(lambda p, n_: mk.grime(p, n_, low_y=0, high_y=1.8, dark=0.65))
        c = mk.Mesh()
        c.add(mk.box(4.6, 0.3, 3.2, material="col").translate(0, 0.15, 0))
        c.add(mk.box(3.8, 0.3, 2.4, material="col").translate(0, 0.45, 0))
        c.add(mk.box(2.7, 1.2, 1.45, material="col").translate(0, 1.2, 0))
        T = mk.mat_translate((cx, 0, cz)) @ mk.ry(yaw)
        add(m.transform(T), c.transform(T), {"type": "altar", "pos": [cx, 0, cz]})
        layout["altar_top"] = [cx, 1.8, cz]

    # 4. scattered rubble clusters near the wall (no collision; small)
    for i in range(10):
        t = rng.random() * 2 * math.pi
        cpos = E(-1.2 - rng.random() * 1.5, t)
        vis.add(rubble(8, lambda r_, c=cpos: c, 0.7, (0.08, 0.35), seed=50 + i).color_fn(
            lambda p, n_: mk.grime(p, n_, 0, 0.6, 0.6)))
    layout["obstacles"] = obs
    return vis, col


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def write(name, nodes):
    s = mk.Scene()
    for nm, mesh in nodes:
        if mesh is None or mesh.is_empty():
            continue
        s.add(mk.Node(nm, mesh))
    sz = s.write_glb(os.path.join(OUT, name + ".glb"))
    tris = sum(m.tri_count() for _, m in nodes if m is not None)
    print(f"{name}.glb  {sz / 1e6:.1f} MB  {tris} tris")


def main():
    os.makedirs(OUT, exist_ok=True)
    layout = {"A": A, "B": B, "podium_h": PODIUM_H, "podium_t": PODIUM_T}
    floor, grates, floor_col = build_floor(layout)
    write("colosseum_floor", [("Floor", floor), ("Grates", grates), ("FloorCollision-colonly", floor_col)])
    pod, pod_col, bays = build_podium(layout)
    write("colosseum_podium", [("Podium", pod), ("PodiumCollision-colonly", pod_col)])
    cav = build_cavea(layout)
    write("colosseum_cavea", [("Cavea", cav)])
    obs, obs_col = build_obstacles(layout)
    write("colosseum_obstacles", [("Obstacles", obs), ("ObstacleCollision-colonly", obs_col)])
    with open(LAYOUT, "w") as f:
        json.dump(layout, f, indent=1)
    print("layout ->", LAYOUT)


if __name__ == "__main__":
    main()
