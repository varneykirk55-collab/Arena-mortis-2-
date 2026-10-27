"""
Visual overhaul textures (phase 1): joint-free stone surfaces for modelled
ashlar blocks, marble, mortar, macro-variation and streak maps, and a richer
arena sand. Everything is original, seeded and tileable.

Run: python3 textures_v2.py <out_dir>
"""
import math
import os
import sys

import numpy as np
from PIL import Image

import textures as T   # reuse fbm / band / worley / normal_from_height helpers

OUT = sys.argv[1] if len(sys.argv) > 1 else "../../assets/textures"
T.OUT = OUT


def _save_rgb(a, n):
    T.save_rgb(a, n)


def limestone(size=1024, name="limestone", warm=1.0, seed=300, pal=None):
    """Weathered travertine/limestone: horizontal pores, soft strata, pitting,
    hairline cracks, subtle colour drift. No block joints (those are modelled)."""
    yy, xx = np.mgrid[0:size, 0:size] / size
    n_low = T.fbm(size, seed + 1, 2.4)
    n_mid = T.band(size, seed + 2, 6, 40)
    n_hi = T.band(size, seed + 3, 80, 300)
    # travertine pores: Worley cells squashed horizontally
    d, _ = T.worley(size, 2600, seed + 4)
    pores = np.clip(1 - d * 7.5, 0, 1) ** 2.2
    pores = pores * (T.fbm(size, seed + 5, 1.8) > 0.42)
    # elongate pores by blurring horizontally
    k = 9
    pores = sum(np.roll(pores, s, axis=1) for s in range(-k // 2, k // 2 + 1)) / k
    strata = T.band(size, seed + 6, 2, 7)
    layers = np.sin((yy * 22 + strata * 5 + n_low * 2.0) * math.pi) * 0.5 + 0.5
    cracks = T.worley(size, 30, seed + 7, second=True)[0]
    cracks = np.clip(1 - cracks * 60, 0, 1) * np.clip((T.fbm(size, seed + 8, 2.0) - 0.66) * 6, 0, 1)
    h = 0.55 + 0.18 * n_low + 0.12 * n_mid + 0.06 * n_hi + 0.04 * layers - 0.35 * pores - 0.3 * cracks
    t = np.clip(0.42 + 0.28 * n_low + 0.14 * layers + 0.1 * n_mid, 0, 1)
    pal = pal or [(0, (0.46, 0.41, 0.34)), (0.5, (0.65, 0.59, 0.49)), (1, (0.79, 0.74, 0.63))]
    alb = T.colorize(t, pal)
    alb *= (0.94 + 0.08 * n_hi)[..., None]
    alb *= (1 - 0.45 * pores)[..., None]
    alb *= (1 - 0.55 * cracks)[..., None]
    # faint lichen / mineral stains
    stain = np.clip((T.fbm(size, seed + 9, 2.6) - 0.62) * 3.0, 0, 1)[..., None]
    alb = alb * (1 - 0.35 * stain) + np.array([0.36, 0.33, 0.24]) * 0.35 * stain
    rough = np.clip(0.78 + 0.12 * pores + 0.06 * n_hi - 0.05 * n_low, 0, 1)
    _save_rgb(alb, f"{name}_albedo.png")
    T.save_normal(T.normal_from_height(h, 6.0), f"{name}_normal.png")
    T.save_gray(rough, f"{name}_rough.png")


def marble(size=1024, seed=400):
    """Aged white marble with grey veins and a dirty patina."""
    n1 = T.fbm(size, seed + 1, 2.2)
    warp = T.fbm(size, seed + 2, 2.0)
    yy, xx = np.mgrid[0:size, 0:size] / size
    v = np.sin((xx * 3 + yy * 5 + warp * 6.0) * math.pi * 2)
    veins = np.clip(1 - np.abs(v) * 9, 0, 1) ** 2 * (0.4 + 0.6 * T.fbm(size, seed + 3))
    fine = T.band(size, seed + 4, 60, 250)
    alb = T.colorize(0.5 + 0.3 * n1, [(0, (0.72, 0.70, 0.66)), (1, (0.90, 0.88, 0.84))])
    alb = alb * (1 - 0.45 * veins[..., None]) + np.array([0.35, 0.36, 0.37]) * 0.45 * veins[..., None]
    patina = np.clip((T.fbm(size, seed + 5, 2.6) - 0.45) * 2.0, 0, 1)[..., None]
    alb = alb * (1 - 0.35 * patina) + np.array([0.45, 0.40, 0.32]) * 0.35 * patina
    alb *= (0.96 + 0.05 * fine)[..., None]
    h = 0.6 + 0.1 * n1 + 0.05 * fine - 0.08 * veins
    _save_rgb(alb, "marble_albedo.png")
    T.save_normal(T.normal_from_height(h, 2.5), "marble_normal.png")
    T.save_gray(np.clip(0.45 + 0.25 * patina[..., 0] + 0.1 * fine, 0, 1), "marble_rough.png")


def mortar(size=512, seed=500):
    """Coarse lime mortar / rubble concrete core (opus caementicium)."""
    n1 = T.fbm(size, seed + 1, 2.0)
    d, idx = T.worley(size, 700, seed + 2)
    rng = np.random.default_rng(seed + 3)
    aggregate = (np.clip(1 - d * 6, 0, 1) ** 0.6) * (rng.random(700)[idx] > 0.35)
    agg_col = T.colorize(rng.random(700)[idx], [(0, (0.30, 0.27, 0.24)), (1, (0.55, 0.50, 0.44))])
    base = T.colorize(0.4 + 0.4 * n1, [(0, (0.24, 0.22, 0.20)), (1, (0.40, 0.37, 0.33))])
    a = np.clip(aggregate * 1.4, 0, 1)[..., None]
    alb = base * (1 - a) + agg_col * a
    h = 0.4 + 0.2 * n1 + 0.4 * aggregate
    _save_rgb(alb, "mortar_albedo.png")
    T.save_normal(T.normal_from_height(h, 5.0), "mortar_normal.png")
    T.save_gray(np.clip(0.9 + 0.05 * n1, 0, 1), "mortar_rough.png")


def macro(size=512, seed=600):
    """RGB = three independent low-frequency variation fields."""
    r = T.fbm(size, seed + 1, 2.8, lo=1.0)
    g = T.band(size, seed + 2, 2, 9)
    b = T.fbm(size, seed + 3, 2.2)
    _save_rgb(np.stack([r, g, b], axis=2), "macro_variation.png")


def streaks(size=512, seed=700):
    """Vertical rain/soot streaks (tile vertically stretched in the shader)."""
    rng = np.random.default_rng(seed)
    cols = T.band(size, seed + 1, 8, 60)
    cols = np.clip((cols - 0.55) * 3.0, 0, 1)
    yy = np.mgrid[0:size, 0:size][0] / size
    fade = T.band(size, seed + 2, 1, 4)
    row = cols[0:1, :]
    row = sum(np.roll(row, k, axis=1) for k in range(-6, 7)) / 13.0
    s = row * np.ones((size, 1))
    s = s * (0.4 + 0.6 * fade) * 0.8
    T.save_gray(np.clip(s, 0, 1), "streaks.png")


def sand_v2(size=1024, seed=800):
    """Arena sand: fine grain, raked ripples, footprints/drag marks, pebbles."""
    n1 = T.fbm(size, seed + 1, 2.3)
    n2 = T.band(size, seed + 2, 90, 400)
    n3 = T.fbm(size, seed + 3, 1.7)
    d, idx = T.worley(size, 3200, seed + 4)
    rng = np.random.default_rng(seed + 5)
    keep = rng.random(3200) < 0.28
    peb = np.clip(1 - d * 11, 0, 1) ** 0.6 * keep[idx]
    yy, xx = np.mgrid[0:size, 0:size] / size
    rip = np.sin((xx * 26 + T.fbm(size, seed + 6, 2.0) * 6) * math.pi * 2) * 0.5 + 0.5
    rip *= np.clip((T.fbm(size, seed + 7, 2.4) - 0.45) * 3, 0, 1)
    # scuffs: elongated depressions
    scuff = np.clip((T.band(size, seed + 8, 3, 12) - 0.6) * 4, 0, 1)
    h = 0.5 + 0.18 * n1 + 0.08 * n2 + 0.3 * peb + 0.05 * rip - 0.12 * scuff
    alb = T.colorize(0.35 + 0.4 * n1 + 0.2 * n3, [(0, (0.33, 0.26, 0.18)), (0.5, (0.50, 0.40, 0.29)), (1, (0.63, 0.53, 0.40))])
    alb *= (0.86 + 0.22 * n2)[..., None]
    pebc = T.colorize(rng.random(3200)[idx], [(0, (0.33, 0.31, 0.28)), (1, (0.58, 0.54, 0.48))])
    pm = np.clip(peb * 2, 0, 1)[..., None]
    alb = alb * (1 - pm) + pebc * pm
    alb *= (1 - 0.25 * scuff)[..., None]
    damp = np.clip((T.fbm(size, seed + 9, 2.6) - 0.58) * 3, 0, 1)[..., None]
    alb *= (1 - 0.3 * damp)
    _save_rgb(alb, "sand_v2_albedo.png")
    T.save_normal(T.normal_from_height(h, 3.5), "sand_v2_normal.png")
    T.save_gray(np.clip(0.95 - 0.2 * damp[..., 0] - 0.12 * peb, 0, 1), "sand_v2_rough.png")


def main():
    os.makedirs(OUT, exist_ok=True)
    limestone(1024, "limestone", 1.0, 300)
    limestone(1024, "limestone_warm", 1.0, 350, [(0, (0.50, 0.40, 0.29)), (0.5, (0.68, 0.56, 0.41)), (1, (0.80, 0.69, 0.53))])
    marble()
    mortar()
    macro()
    streaks()
    sand_v2()
    print("textures_v2 done")


if __name__ == "__main__":
    main()
