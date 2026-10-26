"""
meshkit.py - a small procedural modelling kit that writes binary glTF (GLB).

Blender could not be installed in the build environment (no network route to
blender.org / PyPI), so Arena Mortis' 3D assets are authored as Python code
with this module instead. It supports the operations the assets need:

  * primitives: chamfered boxes / convex hulls, cylinders, lathes, lofts,
    extruded 2D profiles (with ear-clipping), sweeps along paths, grids
  * transforms, merging, per-vertex colours (used for baked-in dirt / AO)
  * multiple materials per mesh, named nodes in a hierarchy
  * skinning (JOINTS_0 / WEIGHTS_0 + inverse bind matrices)
  * keyframed node animations (rotation / translation / scale)

Everything is plain numpy; output is standards-compliant glTF 2.0 binary.
"""
from __future__ import annotations

import json
import math
import os
import struct
from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import ConvexHull

# --------------------------------------------------------------------------
# math helpers
# --------------------------------------------------------------------------

def v3(*a):
    return np.array(a, dtype=np.float64)


def mat_translate(t):
    m = np.eye(4)
    m[:3, 3] = t
    return m


def mat_scale(s):
    if np.isscalar(s):
        s = (s, s, s)
    m = np.eye(4)
    m[0, 0], m[1, 1], m[2, 2] = s
    return m


def mat_rot_axis(axis, ang):
    axis = np.asarray(axis, dtype=np.float64)
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    c, s = math.cos(ang), math.sin(ang)
    C = 1 - c
    r = np.array([
        [c + x * x * C, x * y * C - z * s, x * z * C + y * s],
        [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
        [z * x * C - y * s, z * y * C + x * s, c + z * z * C],
    ])
    m = np.eye(4)
    m[:3, :3] = r
    return m


def rx(a):
    return mat_rot_axis((1, 0, 0), a)


def ry(a):
    return mat_rot_axis((0, 1, 0), a)


def rz(a):
    return mat_rot_axis((0, 0, 1), a)


def quat_axis(axis, ang):
    axis = np.asarray(axis, dtype=np.float64)
    axis = axis / np.linalg.norm(axis)
    s = math.sin(ang / 2)
    return np.array([axis[0] * s, axis[1] * s, axis[2] * s, math.cos(ang / 2)])


def quat_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ])


def quat_euler(x=0.0, y=0.0, z=0.0):
    """Euler (radians) applied in X, then Y, then Z order (q = qz*qy*qx)."""
    q = quat_axis((1, 0, 0), x)
    q = quat_mul(quat_axis((0, 1, 0), y), q)
    q = quat_mul(quat_axis((0, 0, 1), z), q)
    return q


def mat_from_quat(q):
    x, y, z, w = q
    m = np.eye(4)
    m[:3, :3] = [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]
    return m


def look_basis(direction, up=(0, 1, 0)):
    """4x4 that maps +Y onto `direction` (used to orient tubes / lofts)."""
    d = np.asarray(direction, dtype=np.float64)
    d = d / np.linalg.norm(d)
    upv = np.asarray(up, dtype=np.float64)
    if abs(np.dot(d, upv)) > 0.99:
        upv = np.array([1.0, 0, 0])
    x = np.cross(upv, d)
    x /= np.linalg.norm(x)
    z = np.cross(x, d)
    m = np.eye(4)
    m[:3, 0] = x
    m[:3, 1] = d
    m[:3, 2] = z
    return m


# --------------------------------------------------------------------------
# Mesh container
# --------------------------------------------------------------------------

class Mesh:
    """A triangle mesh with one or more material groups ("surfaces")."""

    def __init__(self):
        self.groups: dict[str, dict] = {}

    # -- construction ----------------------------------------------------
    @staticmethod
    def from_arrays(pos, nrm, idx, uv=None, material="default", color=None):
        m = Mesh()
        n = len(pos)
        if uv is None:
            uv = np.zeros((n, 2))
        if color is None:
            color = np.ones((n, 4))
        m.groups[material] = {
            "P": np.asarray(pos, dtype=np.float64).reshape(-1, 3),
            "N": np.asarray(nrm, dtype=np.float64).reshape(-1, 3),
            "UV": np.asarray(uv, dtype=np.float64).reshape(-1, 2),
            "C": np.asarray(color, dtype=np.float64).reshape(-1, 4),
            "J": np.zeros((n, 4), dtype=np.int64),
            "W": np.tile(np.array([1.0, 0, 0, 0]), (n, 1)),
            "I": np.asarray(idx, dtype=np.int64).reshape(-1, 3),
        }
        return m

    def copy(self):
        m = Mesh()
        for k, g in self.groups.items():
            m.groups[k] = {kk: vv.copy() for kk, vv in g.items()}
        return m

    def is_empty(self):
        return all(len(g["P"]) == 0 for g in self.groups.values())

    def add(self, other: "Mesh"):
        for k, g in other.groups.items():
            if k not in self.groups:
                self.groups[k] = {kk: vv.copy() for kk, vv in g.items()}
            else:
                s = self.groups[k]
                off = len(s["P"])
                for kk in ("P", "N", "UV", "C", "J", "W"):
                    s[kk] = np.concatenate([s[kk], g[kk]])
                s["I"] = np.concatenate([s["I"], g["I"] + off])
        return self

    __iadd__ = add

    # -- modifiers ---------------------------------------------------------
    def transform(self, m):
        m = np.asarray(m, dtype=np.float64)
        nm = np.linalg.inv(m[:3, :3]).T
        flip = np.linalg.det(m[:3, :3]) < 0
        for g in self.groups.values():
            p = g["P"]
            g["P"] = p @ m[:3, :3].T + m[:3, 3]
            n = g["N"] @ nm.T
            ln = np.linalg.norm(n, axis=1, keepdims=True)
            ln[ln == 0] = 1
            g["N"] = n / ln
            if flip:
                g["I"] = g["I"][:, ::-1].copy()
        return self

    def translate(self, x, y=None, z=None):
        if y is None:
            x, y, z = x
        return self.transform(mat_translate((x, y, z)))

    def scale(self, s):
        return self.transform(mat_scale(s))

    def rotate(self, axis, ang):
        return self.transform(mat_rot_axis(axis, ang))

    def material(self, name):
        """Move every group into a single material."""
        out = Mesh()
        for g in self.groups.values():
            t = Mesh()
            t.groups[name] = g
            out.add(t)
        self.groups = out.groups
        return self

    def tint(self, rgb, a=1.0):
        c = np.array([rgb[0], rgb[1], rgb[2], a])
        for g in self.groups.values():
            g["C"] = g["C"] * c
        return self

    def color_fn(self, fn):
        """fn(P, N) -> (n,3) multiplier applied to vertex colours."""
        for g in self.groups.values():
            mul = np.asarray(fn(g["P"], g["N"]))
            g["C"][:, :3] *= mul.reshape(-1, 3) if mul.ndim > 1 else mul[:, None]
        return self

    def skin(self, joint: int):
        for g in self.groups.values():
            n = len(g["P"])
            g["J"] = np.tile(np.array([joint, 0, 0, 0]), (n, 1))
            g["W"] = np.tile(np.array([1.0, 0, 0, 0]), (n, 1))
        return self

    def skin_fn(self, fn):
        """fn(P) -> (J (n,4) int, W (n,4) float)."""
        for g in self.groups.values():
            j, w = fn(g["P"])
            g["J"] = np.asarray(j, dtype=np.int64)
            w = np.asarray(w, dtype=np.float64)
            w = w / np.maximum(w.sum(axis=1, keepdims=True), 1e-9)
            g["W"] = w
        return self

    def jitter(self, amount, seed=0):
        """Displace vertices with a smooth-ish hash noise (weathering)."""
        seed = abs(int(seed))
        for g in self.groups.values():
            p = g["P"]
            # quantise so coincident verts (split normals) move together
            key = np.round(p * 1000).astype(np.int64)
            h = (key[:, 0] * 73856093) ^ (key[:, 1] * 19349663) ^ (key[:, 2] * 83492791)
            h = h + seed * 2654435761
            r = np.stack([
                ((h * 1103515245 + 12345) >> 8) & 0xFFFF,
                ((h * 22695477 + 1) >> 8) & 0xFFFF,
                ((h * 134775813 + 7) >> 8) & 0xFFFF,
            ], axis=1) / 65535.0 - 0.5
            g["P"] = p + r * 2 * amount
        return self

    def bounds(self):
        ps = [g["P"] for g in self.groups.values() if len(g["P"])]
        allp = np.concatenate(ps)
        return allp.min(axis=0), allp.max(axis=0)

    def tri_count(self):
        return sum(len(g["I"]) for g in self.groups.values())

    def recompute_normals_smooth(self, weld=1e-4):
        for g in self.groups.values():
            p, idx = g["P"], g["I"]
            key = np.round(p / weld).astype(np.int64)
            _, inv = np.unique(key, axis=0, return_inverse=True)
            inv = inv.reshape(-1)
            fn = np.cross(p[idx[:, 1]] - p[idx[:, 0]], p[idx[:, 2]] - p[idx[:, 0]])
            acc = np.zeros((inv.max() + 1, 3))
            for k in range(3):
                np.add.at(acc, inv[idx[:, k]], fn)
            n = acc[inv]
            ln = np.linalg.norm(n, axis=1, keepdims=True)
            ln[ln == 0] = 1
            g["N"] = n / ln
        return self


def merge(*meshes):
    out = Mesh()
    for m in meshes:
        if m is not None:
            out.add(m)
    return out


# --------------------------------------------------------------------------
# UV helpers
# --------------------------------------------------------------------------

def box_uv(p, n, scale=1.0):
    a = np.abs(n)
    uv = np.zeros((len(p), 2))
    mx = (a[:, 0] >= a[:, 1]) & (a[:, 0] >= a[:, 2])
    my = (a[:, 1] > a[:, 0]) & (a[:, 1] >= a[:, 2])
    mz = ~(mx | my)
    uv[mx] = p[mx][:, [2, 1]]
    uv[my] = p[my][:, [0, 2]]
    uv[mz] = p[mz][:, [0, 1]]
    return uv * scale


def flat_from_tris(tris, material="default", uv_scale=1.0):
    """tris: (m,3,3) array of triangles -> flat-shaded Mesh."""
    tris = np.asarray(tris, dtype=np.float64)
    p = tris.reshape(-1, 3)
    fn = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(fn, axis=1, keepdims=True)
    ln[ln == 0] = 1
    fn = fn / ln
    n = np.repeat(fn, 3, axis=0)
    idx = np.arange(len(p)).reshape(-1, 3)
    return Mesh.from_arrays(p, n, idx, box_uv(p, n, uv_scale), material)


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------

def hull(points, material="default", uv_scale=1.0):
    pts = np.asarray(points, dtype=np.float64)
    h = ConvexHull(pts)
    tris = []
    c = pts.mean(axis=0)
    for s, eq in zip(h.simplices, h.equations):
        a, b, d = pts[s]
        nrm = np.cross(b - a, d - a)
        if np.dot(nrm, eq[:3]) < 0:
            a, b = b, a
        tris.append([a, b, d])
    return flat_from_tris(tris, material, uv_scale)


def box(sx, sy, sz, bevel=0.0, material="default", center=(0, 0, 0)):
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    if bevel <= 0:
        pts = [(x, y, z) for x in (-hx, hx) for y in (-hy, hy) for z in (-hz, hz)]
    else:
        b = min(bevel, hx * 0.9, hy * 0.9, hz * 0.9)
        pts = []
        for sxn in (-1, 1):
            for syn in (-1, 1):
                for szn in (-1, 1):
                    pts.append((sxn * hx, syn * (hy - b), szn * (hz - b)))
                    pts.append((sxn * (hx - b), syn * hy, szn * (hz - b)))
                    pts.append((sxn * (hx - b), syn * (hy - b), szn * hz))
    m = hull(pts, material)
    return m.translate(*center)


def tapered_box(bottom, top, h, bevel=0.0, material="default"):
    """bottom/top = (sx, sz); y from 0..h"""
    (bx, bz), (tx, tz) = bottom, top
    pts = []
    for (sx, sz, y) in ((bx, bz, 0.0), (tx, tz, h)):
        for a in (-1, 1):
            for c in (-1, 1):
                if bevel > 0:
                    pts.append((a * sx / 2, y, c * (sz / 2 - bevel)))
                    pts.append((a * (sx / 2 - bevel), y, c * sz / 2))
                else:
                    pts.append((a * sx / 2, y, c * sz / 2))
    return hull(pts, material)


def lathe(profile, segments=24, material="default", cap_top=False, cap_bottom=False,
          smooth=True, angle0=0.0, angle1=2 * math.pi, uv_v_scale=1.0):
    """Revolve [(r, y), ...] around the Y axis."""
    prof = np.asarray(profile, dtype=np.float64)
    full = abs(angle1 - angle0 - 2 * math.pi) < 1e-6
    ns = segments if full else segments + 1
    angs = angle0 + (angle1 - angle0) * np.arange(ns) / segments
    P, N, UV = [], [], []
    m = len(prof)
    # profile tangents for normals
    tang = np.zeros((m, 2))
    for i in range(m):
        a = prof[max(i - 1, 0)]
        b = prof[min(i + 1, m - 1)]
        d = b - a
        tang[i] = d / (np.linalg.norm(d) + 1e-12)
    vlen = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(prof, axis=0), axis=1))])
    for j, a in enumerate(angs):
        ca, sa = math.cos(a), math.sin(a)
        for i in range(m):
            r, y = prof[i]
            P.append((r * ca, y, r * sa))
            tr, ty = tang[i]
            # normal in (r, y) plane is (ty, -tr)
            nr, ny = ty, -tr
            N.append((nr * ca, ny, nr * sa))
            UV.append((j / segments * 2 * math.pi * max(prof[:, 0].max(), 0.01), vlen[i] * uv_v_scale))
    P, N, UV = np.array(P), np.array(N), np.array(UV)
    idx = []
    cols = ns if not full else ns
    for j in range(cols if not full else ns):
        jn = j + 1
        if full:
            jn = (j + 1) % ns
        elif j == ns - 1:
            break
        for i in range(m - 1):
            a = j * m + i
            b = jn * m + i
            idx.append((a, a + 1, b))
            idx.append((b, a + 1, b + 1))
    mesh = Mesh.from_arrays(P, N, np.array(idx), UV, material)
    # orientation check: profile listed bottom->top with r>0 gives outward normals
    if not smooth:
        mesh = _flatten(mesh)
    if cap_top:
        mesh.add(disk(prof[-1][0], segments, material).translate(0, prof[-1][1], 0))
    if cap_bottom:
        mesh.add(disk(prof[0][0], segments, material).rotate((1, 0, 0), math.pi).translate(0, prof[0][1], 0))
    return mesh


def _flatten(mesh):
    out = Mesh()
    for k, g in mesh.groups.items():
        tris = g["P"][g["I"]]
        f = flat_from_tris(tris, k)
        f.groups[k]["UV"] = g["UV"][g["I"]].reshape(-1, 2)
        f.groups[k]["C"] = g["C"][g["I"]].reshape(-1, 4)
        out.add(f)
    return out


def flatten(mesh):
    return _flatten(mesh)


def disk(r, segments=24, material="default"):
    angs = 2 * math.pi * np.arange(segments) / segments
    P = [(0, 0, 0)] + [(r * math.cos(a), 0, r * math.sin(a)) for a in angs]
    N = [(0, 1, 0)] * (segments + 1)
    idx = []
    for i in range(segments):
        idx.append((0, 1 + (i + 1) % segments, 1 + i))
    P = np.array(P)
    return Mesh.from_arrays(P, N, idx, P[:, [0, 2]], material)


def cylinder(r, h, segments=16, material="default", r2=None, caps=True, smooth=True):
    r2 = r if r2 is None else r2
    return lathe([(r, 0), (r2, h)], segments, material, cap_top=caps, cap_bottom=caps, smooth=smooth)


def sphere(r, segments=16, rings=10, material="default"):
    prof = [(r * math.sin(math.pi * i / rings), -r * math.cos(math.pi * i / rings)) for i in range(rings + 1)]
    prof[0] = (1e-4, prof[0][1])
    prof[-1] = (1e-4, prof[-1][1])
    return lathe(prof, segments, material)


def ellipsoid(rx_, ry_, rz_, segments=16, rings=10, material="default"):
    return sphere(1.0, segments, rings, material).scale((rx_, ry_, rz_))


def torus(R, r, seg=24, rseg=8, material="default", arc=2 * math.pi):
    prof = [(R + r * math.cos(2 * math.pi * i / rseg), r * math.sin(2 * math.pi * i / rseg)) for i in range(rseg + 1)]
    return lathe(prof, seg, material, angle1=arc)


# ---- 2D polygons -------------------------------------------------------------

def _area2(poly):
    p = np.asarray(poly)
    return 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])


def triangulate(poly):
    """Ear clipping. poly: list of (x, y). Returns list of index triples (CCW)."""
    pts = [tuple(map(float, p)) for p in poly]
    n = len(pts)
    idx = list(range(n))
    if _area2(pts) < 0:
        idx.reverse()
    tris = []

    def is_convex(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 1e-12

    def in_tri(p, a, b, c):
        d1 = (p[0] - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (p[1] - b[1])
        d2 = (p[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (p[1] - c[1])
        d3 = (p[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (p[1] - a[1])
        neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        return not (neg and pos)

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        found = False
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if not is_convex(a, b, c):
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                if in_tri(pts[j], a, b, c):
                    ok = False
                    break
            if ok:
                tris.append((i0, i1, i2))
                idx.pop(k)
                found = True
                break
        if not found:
            # degenerate; fan the rest
            for k in range(1, len(idx) - 1):
                tris.append((idx[0], idx[k], idx[k + 1]))
            idx = idx[:0]
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris


def extrude(poly, depth, material="default", bevel=0.0, center=True, uv_scale=1.0):
    """Extrude a 2D polygon (XY plane) along +Z by depth (centred on Z=0).
    bevel > 0 adds a chamfer by insetting the cap outlines (approximate)."""
    poly = [tuple(map(float, p)) for p in poly]
    if _area2(poly) < 0:
        poly = poly[::-1]
    z0, z1 = (-depth / 2, depth / 2) if center else (0, depth)
    tris_idx = triangulate(poly)
    T = []
    outer = np.array(poly)
    if bevel > 0:
        inner = _inset(outer, bevel)
        rings = [(inner, z0), (outer, z0 + bevel), (outer, z1 - bevel), (inner, z1)]
    else:
        rings = [(outer, z0), (outer, z1)]
    # caps (use inner outline if bevelled)
    cap0, capz0 = rings[0]
    cap1, capz1 = rings[-1]
    for (a, b, c) in tris_idx:
        T.append([(*cap1[a], capz1), (*cap1[b], capz1), (*cap1[c], capz1)])
        T.append([(*cap0[a], capz0), (*cap0[c], capz0), (*cap0[b], capz0)])
    n = len(outer)
    for (ra, za), (rb, zb) in zip(rings[:-1], rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            p0 = (*ra[i], za)
            p1 = (*ra[j], za)
            p2 = (*rb[j], zb)
            p3 = (*rb[i], zb)
            T.append([p0, p1, p2])
            T.append([p0, p2, p3])
    return flat_from_tris(T, material, uv_scale)


def _inset(poly, d):
    p = np.asarray(poly, dtype=np.float64)
    n = len(p)
    out = np.zeros_like(p)
    for i in range(n):
        a, b, c = p[i - 1], p[i], p[(i + 1) % n]
        e1 = b - a
        e2 = c - b
        n1 = np.array([-e1[1], e1[0]]) / (np.linalg.norm(e1) + 1e-12)
        n2 = np.array([-e2[1], e2[0]]) / (np.linalg.norm(e2) + 1e-12)
        bis = n1 + n2
        l = np.linalg.norm(bis)
        if l < 1e-6:
            bis = n1
        else:
            bis /= l
        cosh = max(np.dot(bis, n1), 0.3)
        out[i] = b + bis * d / cosh  # CCW polygon: left normal points inward
    return out


def arc_points(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def rounded_rect(w, h, r, n=4):
    pts = []
    for (cx, cy, a0) in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, math.pi / 2),
                         (-w / 2 + r, -h / 2 + r, math.pi), (w / 2 - r, -h / 2 + r, 1.5 * math.pi)):
        pts += arc_points(cx, cy, r, a0, a0 + math.pi / 2, n)
    return pts


# ---- lofts / sweeps ------------------------------------------------------------

def loft(rings, material="default", cap_start=True, cap_end=True, smooth=True):
    """rings: list of (n,3) arrays with equal vertex count, ordered along the
    loft. Ring vertices should wind counter-clockwise when looking from the
    end towards the start for outward normals."""
    R = [np.asarray(r, dtype=np.float64) for r in rings]
    k = len(R[0])
    P = np.concatenate(R)
    idx = []
    for s in range(len(R) - 1):
        for i in range(k):
            j = (i + 1) % k
            a = s * k + i
            b = s * k + j
            c = (s + 1) * k + j
            d = (s + 1) * k + i
            idx.append((a, b, c))
            idx.append((a, c, d))
    idx = np.array(idx)
    uv = np.zeros((len(P), 2))
    for s in range(len(R)):
        uv[s * k:(s + 1) * k, 0] = np.arange(k) / k
        uv[s * k:(s + 1) * k, 1] = s / max(len(R) - 1, 1)
    m = Mesh.from_arrays(P, np.zeros_like(P), idx, uv, material)
    m.recompute_normals_smooth()
    # orientation check: normals should point away from ring centroids
    g = m.groups[material]
    cen = np.repeat(np.array([r.mean(axis=0) for r in R]), k, axis=0)
    if np.mean(np.sum((g["P"] - cen) * g["N"], axis=1)) < 0:
        g["I"] = g["I"][:, ::-1].copy()
        g["N"] = -g["N"]
    if not smooth:
        m = _flatten(m)
    if cap_start:
        m.add(_cap(R[0], R[1], material))
    if cap_end:
        m.add(_cap(R[-1], R[-2], material))
    return m


def _cap(ring, neighbour, material):
    c = ring.mean(axis=0)
    outward = c - neighbour.mean(axis=0)
    if np.linalg.norm(outward) < 1e-9:
        outward = np.array([0, 1.0, 0])
    outward /= np.linalg.norm(outward)
    tris = []
    k = len(ring)
    for i in range(k):
        a, b = ring[i], ring[(i + 1) % k]
        t = [c, a, b]
        if np.dot(np.cross(a - c, b - c), outward) < 0:
            t = [c, b, a]
        tris.append(t)
    return flat_from_tris(tris, material)


def ellipse_ring(center, rx_, rz_, n=12, basis=None, phase=0.0, shape=None):
    """Ellipse in a plane; basis is a 4x4 whose X/Z columns span the plane."""
    a = phase + 2 * math.pi * np.arange(n) / n
    if shape is not None:
        rad = np.array([shape(t) for t in a])
    else:
        rad = np.ones(n)
    pts = np.stack([rx_ * np.cos(a) * rad, np.zeros(n), rz_ * np.sin(a) * rad], axis=1)
    if basis is not None:
        pts = pts @ basis[:3, :3].T
    return pts + np.asarray(center)


def tube(path, radii, n=8, material="default", caps=True, up=(0, 0, 1)):
    """Sweep a circle along a polyline path. radii: scalar or per-point list."""
    path = np.asarray(path, dtype=np.float64)
    if np.isscalar(radii):
        radii = [radii] * len(path)
    rings = []
    prev_x = None
    for i, p in enumerate(path):
        if i == 0:
            d = path[1] - path[0]
        elif i == len(path) - 1:
            d = path[-1] - path[-2]
        else:
            d = path[i + 1] - path[i - 1]
        d = d / (np.linalg.norm(d) + 1e-12)
        if prev_x is None:
            u = np.asarray(up, dtype=np.float64)
            if abs(np.dot(u, d)) > 0.95:
                u = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
            x = np.cross(u, d)
        else:
            x = prev_x - d * np.dot(prev_x, d)
        x /= np.linalg.norm(x)
        z = np.cross(x, d)
        prev_x = x
        a = 2 * math.pi * np.arange(n) / n
        ring = p + radii[i] * (np.outer(np.cos(a), x) + np.outer(np.sin(a), z))
        rings.append(ring)
    return loft(rings, material, caps, caps)


def grid(sx, sz, nx, nz, height_fn=None, material="default", uv_scale=1.0):
    xs = np.linspace(-sx / 2, sx / 2, nx + 1)
    zs = np.linspace(-sz / 2, sz / 2, nz + 1)
    X, Z = np.meshgrid(xs, zs, indexing="xy")
    Y = np.zeros_like(X) if height_fn is None else height_fn(X, Z)
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    idx = []
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            b = a + 1
            c = a + (nx + 1)
            d = c + 1
            idx.append((a, c, b))
            idx.append((b, c, d))
    m = Mesh.from_arrays(P, np.zeros_like(P), idx, P[:, [0, 2]] * uv_scale, material)
    m.recompute_normals_smooth()
    g = m.groups[material]
    if np.mean(g["N"][:, 1]) < 0:
        g["I"] = g["I"][:, ::-1].copy()
        g["N"] = -g["N"]
    return m


def quad(w, h, material="default", double_sided=False):
    P = np.array([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)])
    N = np.array([(0, 0, 1)] * 4)
    UV = np.array([(0, 1), (1, 1), (1, 0), (0, 0)])
    m = Mesh.from_arrays(P, N, [(0, 1, 2), (0, 2, 3)], UV, material)
    if double_sided:
        b = Mesh.from_arrays(P, -N, [(0, 2, 1), (0, 3, 2)], UV, material)
        m.add(b)
    return m


# --------------------------------------------------------------------------
# Scene / GLB export
# --------------------------------------------------------------------------

@dataclass
class MaterialDef:
    name: str
    color: tuple = (0.8, 0.8, 0.8, 1.0)
    metallic: float = 0.0
    roughness: float = 0.8
    emissive: tuple = (0.0, 0.0, 0.0)
    double_sided: bool = False
    alpha_blend: bool = False


@dataclass
class Node:
    name: str
    mesh: Mesh | None = None
    translation: tuple = (0.0, 0.0, 0.0)
    rotation: tuple = (0.0, 0.0, 0.0, 1.0)
    scale: tuple = (1.0, 1.0, 1.0)
    children: list = field(default_factory=list)
    skinned: bool = False


@dataclass
class Skeleton:
    """joints: list of (name, parent_index or -1, head position in model space)."""
    joints: list


@dataclass
class Animation:
    name: str
    # channels: list of (joint_or_node_name, path, times, values)
    channels: list = field(default_factory=list)


class Scene:
    def __init__(self, materials: list[MaterialDef] | None = None):
        self.roots: list[Node] = []
        self.materials = {m.name: m for m in (materials or [])}
        self.skeleton: Skeleton | None = None
        self.animations: list[Animation] = []

    def add(self, node: Node):
        self.roots.append(node)
        return node

    # ----------------------------------------------------------------
    def write_glb(self, path):
        gl = {
            "asset": {"version": "2.0", "generator": "ArenaMortis meshkit"},
            "scene": 0,
            "scenes": [{"nodes": []}],
            "nodes": [],
            "meshes": [],
            "materials": [],
            "accessors": [],
            "bufferViews": [],
            "buffers": [],
        }
        blob = bytearray()

        def add_view(data: bytes, target=None):
            while len(blob) % 4:
                blob.append(0)
            off = len(blob)
            blob.extend(data)
            bv = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
            if target:
                bv["target"] = target
            gl["bufferViews"].append(bv)
            return len(gl["bufferViews"]) - 1

        def add_acc(arr, ctype, atype, target=None, minmax=False, normalized=False):
            arr = np.ascontiguousarray(arr)
            view = add_view(arr.tobytes(), target)
            acc = {"bufferView": view, "componentType": ctype, "count": int(arr.shape[0]), "type": atype}
            if normalized:
                acc["normalized"] = True
            if minmax:
                a2 = arr.reshape(arr.shape[0], -1)
                acc["min"] = [float(x) for x in a2.min(axis=0)]
                acc["max"] = [float(x) for x in a2.max(axis=0)]
            gl["accessors"].append(acc)
            return len(gl["accessors"]) - 1

        mat_index = {}

        def get_mat(name):
            if name in mat_index:
                return mat_index[name]
            md = self.materials.get(name, MaterialDef(name))
            m = {
                "name": name,
                "pbrMetallicRoughness": {
                    "baseColorFactor": list(md.color),
                    "metallicFactor": md.metallic,
                    "roughnessFactor": md.roughness,
                },
            }
            if any(md.emissive):
                m["emissiveFactor"] = list(md.emissive)
            if md.double_sided:
                m["doubleSided"] = True
            if md.alpha_blend:
                m["alphaMode"] = "BLEND"
            gl["materials"].append(m)
            mat_index[name] = len(gl["materials"]) - 1
            return mat_index[name]

        def write_mesh(mesh: Mesh, name, skinned):
            prims = []
            for mname, g in mesh.groups.items():
                if len(g["I"]) == 0:
                    continue
                attrs = {
                    "POSITION": add_acc(g["P"].astype(np.float32), 5126, "VEC3", 34962, minmax=True),
                    "NORMAL": add_acc(g["N"].astype(np.float32), 5126, "VEC3", 34962),
                    "TEXCOORD_0": add_acc(g["UV"].astype(np.float32), 5126, "VEC2", 34962),
                    "COLOR_0": add_acc(np.clip(g["C"], 0, 1).astype(np.float32), 5126, "VEC4", 34962),
                }
                if skinned:
                    attrs["JOINTS_0"] = add_acc(g["J"].astype(np.uint16), 5123, "VEC4", 34962)
                    attrs["WEIGHTS_0"] = add_acc(g["W"].astype(np.float32), 5126, "VEC4", 34962)
                ind = add_acc(g["I"].astype(np.uint32).reshape(-1), 5125, "SCALAR", 34963)
                prims.append({"attributes": attrs, "indices": ind, "material": get_mat(mname)})
            gl["meshes"].append({"name": name, "primitives": prims})
            return len(gl["meshes"]) - 1

        node_index = {}
        skin_nodes = []

        def emit(node: Node):
            nd = {"name": node.name}
            if any(abs(t) > 1e-9 for t in node.translation):
                nd["translation"] = [float(x) for x in node.translation]
            if tuple(node.rotation) != (0.0, 0.0, 0.0, 1.0):
                nd["rotation"] = [float(x) for x in node.rotation]
            if tuple(node.scale) != (1.0, 1.0, 1.0):
                nd["scale"] = [float(x) for x in node.scale]
            if node.mesh is not None and not node.mesh.is_empty():
                nd["mesh"] = write_mesh(node.mesh, node.name, node.skinned)
            gl["nodes"].append(nd)
            idx = len(gl["nodes"]) - 1
            node_index[node.name] = idx
            if node.skinned:
                skin_nodes.append(idx)
            kids = [emit(c) for c in node.children]
            if kids:
                gl["nodes"][idx]["children"] = kids
            return idx

        root_ids = [emit(n) for n in self.roots]

        # skeleton
        if self.skeleton is not None:
            js = self.skeleton.joints
            jidx = []
            for i, (jname, parent, head) in enumerate(js):
                ph = np.zeros(3) if parent < 0 else np.asarray(js[parent][2])
                t = np.asarray(head) - ph
                gl["nodes"].append({"name": jname, "translation": [float(x) for x in t]})
                jidx.append(len(gl["nodes"]) - 1)
                node_index[jname] = jidx[-1]
            for i, (jname, parent, head) in enumerate(js):
                if parent >= 0:
                    gl["nodes"][jidx[parent]].setdefault("children", []).append(jidx[i])
                else:
                    root_ids.append(jidx[i])
            ibm = []
            for (jname, parent, head) in js:
                m = np.eye(4)
                m[:3, 3] = -np.asarray(head)
                ibm.append(m.T.reshape(-1))  # column-major
            ibm_acc = add_acc(np.array(ibm, dtype=np.float32), 5126, "MAT4")
            gl["skins"] = [{"joints": jidx, "inverseBindMatrices": ibm_acc, "skeleton": jidx[0]}]
            for sn in skin_nodes:
                gl["nodes"][sn]["skin"] = 0

        gl["scenes"][0]["nodes"] = root_ids

        # animations
        if self.animations:
            gl["animations"] = []
            for anim in self.animations:
                samplers, channels = [], []
                for (target, path_, times, values) in anim.channels:
                    if target not in node_index:
                        raise KeyError(f"animation target {target} missing")
                    t = np.asarray(times, dtype=np.float32)
                    v = np.asarray(values, dtype=np.float32)
                    ti = add_acc(t.reshape(-1), 5126, "SCALAR", minmax=True)
                    vi = add_acc(v, 5126, "VEC4" if path_ == "rotation" else "VEC3")
                    samplers.append({"input": ti, "output": vi, "interpolation": "LINEAR"})
                    channels.append({"sampler": len(samplers) - 1, "target": {"node": node_index[target], "path": path_}})
                gl["animations"].append({"name": anim.name, "samplers": samplers, "channels": channels})

        if not gl["materials"]:
            del gl["materials"]
        if not gl["meshes"]:
            del gl["meshes"]
        gl["buffers"] = [{"byteLength": len(blob)}]
        while len(blob) % 4:
            blob.append(0)
        gl["buffers"][0]["byteLength"] = len(blob)
        js_ = json.dumps(gl, separators=(",", ":")).encode()
        while len(js_) % 4:
            js_ += b" "
        out = bytearray()
        total = 12 + 8 + len(js_) + 8 + len(blob)
        out += struct.pack("<III", 0x46546C67, 2, total)
        out += struct.pack("<II", len(js_), 0x4E4F534A) + js_
        out += struct.pack("<II", len(blob), 0x004E4942) + blob
        with open(path, "wb") as f:
            f.write(out)
        write_import_file(path)
        return total


# --------------------------------------------------------------------------
# colour helpers for baked weathering
# --------------------------------------------------------------------------

def hash01(p, seed=0):
    key = np.round(np.asarray(p) * 37).astype(np.int64)
    h = (key[..., 0] * 73856093) ^ (key[..., 1] * 19349663) ^ (key[..., 2] * 83492791) ^ (seed * 2654435761)
    return ((h * 1103515245 + 12345) & 0x7FFFFFFF) / float(0x7FFFFFFF)


def value_noise3(p, freq=1.0, seed=0):
    """Smooth 3D value noise in [0,1]."""
    q = np.asarray(p) * freq
    i = np.floor(q)
    f = q - i
    f = f * f * (3 - 2 * f)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                c = i + np.array([dx, dy, dz])
                h = hash01(c / 37.0 + 0.0001, seed)
                w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * (f[..., 2] if dz else 1 - f[..., 2])
                out = out + h * w
    return out


def grime(p, n, base=1.0, low_y=0.0, high_y=3.0, dark=0.55, noise_amt=0.25, seed=1):
    """Darken towards the ground and add blotchy variation (vertex colour AO)."""
    t = np.clip((p[:, 1] - low_y) / max(high_y - low_y, 1e-6), 0, 1)
    ao = dark + (1 - dark) * t
    nz = value_noise3(p, 0.7, seed) * 0.6 + value_noise3(p, 2.3, seed + 3) * 0.4
    v = base * ao * (1 - noise_amt / 2 + noise_amt * nz)
    return np.stack([v, v, v], axis=1)


def write_import_file(glb_path, extra_params=""):
    """Write a minimal Godot .import so every generated GLB runs the
    material-remap post-import script. Godot fills in the remaining keys."""
    imp = glb_path + ".import"
    if os.path.exists(imp):
        txt = open(imp).read()
        if "material_remap.gd" in txt:
            return
    with open(imp, "w") as f:
        f.write('[remap]\n\nimporter="scene"\nimporter_version=1\ntype="PackedScene"\n\n'
                '[params]\n\nimport_script/path="res://tools/import/material_remap.gd"\n'
                'meshes/generate_lods=true\nmeshes/ensure_tangents=true\nanimation/fps=30\n' + extra_params)
