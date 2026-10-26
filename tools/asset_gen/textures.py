"""
Procedural, tileable PBR textures for Arena Mortis (albedo / normal / roughness).
All original - generated from seeded noise. Run: python3 textures.py <out_dir>
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.spatial import cKDTree

OUT = sys.argv[1] if len(sys.argv) > 1 else "../../assets/textures"


# ---------------------------------------------------------------- noise ---

def fbm(size, seed, beta=2.0, lo=1.0):
    """Periodic fractal noise via spectral synthesis, normalised to [0,1]."""
    rng = np.random.default_rng(seed)
    w = rng.normal(size=(size, size))
    F = np.fft.fft2(w)
    fx = np.fft.fftfreq(size) * size
    fy = np.fft.fftfreq(size) * size
    FX, FY = np.meshgrid(fx, fy)
    r = np.sqrt(FX ** 2 + FY ** 2)
    r[0, 0] = 1
    filt = 1.0 / np.maximum(r, lo) ** (beta / 2)
    filt[0, 0] = 0
    out = np.real(np.fft.ifft2(F * filt))
    out -= out.min()
    out /= out.max() + 1e-9
    return out


def band(size, seed, f0, f1):
    """Periodic noise limited to a frequency band (in cycles per tile)."""
    rng = np.random.default_rng(seed)
    F = np.fft.fft2(rng.normal(size=(size, size)))
    fx = np.fft.fftfreq(size) * size
    FX, FY = np.meshgrid(fx, fx)
    r = np.sqrt(FX ** 2 + FY ** 2)
    m = ((r >= f0) & (r <= f1)).astype(float)
    out = np.real(np.fft.ifft2(F * m))
    out -= out.min()
    return out / (out.max() + 1e-9)


def worley(size, n, seed, second=False):
    rng = np.random.default_rng(seed)
    pts = rng.random((n, 2)) * size
    tree = cKDTree(pts, boxsize=size)
    yy, xx = np.mgrid[0:size, 0:size]
    q = np.stack([xx.ravel() + 0.5, yy.ravel() + 0.5], axis=1) % size
    d, i = tree.query(q, k=2)
    if second:
        v = (d[:, 1] - d[:, 0])
    else:
        v = d[:, 0]
    v = v.reshape(size, size)
    return v / v.max(), i[:, 0].reshape(size, size)


def normal_from_height(h, strength=4.0):
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    nx = -dx * strength * h.shape[0] / 256
    ny = dy * strength * h.shape[0] / 256  # OpenGL-style green up
    nz = np.ones_like(h)
    l = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    n = np.stack([nx / l, ny / l, nz / l], axis=2)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def save_rgb(arr, name):
    a = np.clip(arr, 0, 1)
    Image.fromarray((a * 255).astype(np.uint8), "RGB").save(os.path.join(OUT, name), optimize=True)


def save_gray(arr, name):
    a = np.clip(arr, 0, 1)
    Image.fromarray((a * 255).astype(np.uint8), "L").save(os.path.join(OUT, name), optimize=True)


def save_normal(n, name):
    Image.fromarray(n, "RGB").save(os.path.join(OUT, name), optimize=True)


def lerp(a, b, t):
    t = t[..., None] if np.ndim(t) == 2 and np.ndim(a) == 1 else t
    return a + (b - a) * t


def colorize(t, stops):
    """t in [0,1] -> rgb via list of (pos, (r,g,b))."""
    t = np.clip(t, 0, 1)
    out = np.zeros(t.shape + (3,))
    pos = [s[0] for s in stops]
    cols = [np.array(s[1]) for s in stops]
    for k in range(len(stops) - 1):
        m = (t >= pos[k]) & (t <= pos[k + 1])
        u = ((t - pos[k]) / max(pos[k + 1] - pos[k], 1e-6))[m]
        out[m] = cols[k] + (cols[k + 1] - cols[k]) * u[:, None]
    return out


# ---------------------------------------------------------- materials ---

def stone_blocks(size=1024):
    """Travertine ashlar masonry. Texture spans 2.4m x 2.4m: 4 courses of 0.6m,
    blocks 1.2m wide (2 per course, staggered)."""
    rows = 4
    yy, xx = np.mgrid[0:size, 0:size] / size
    row = np.floor(yy * rows).astype(int)
    off = (row % 2) * 0.25
    bx = (xx + off) * 2.0
    col = np.floor(bx).astype(int) % 2
    fy = (yy * rows) % 1.0
    fx = bx % 1.0
    # per-block random values
    rng = np.random.default_rng(11)
    tint = rng.random((rows, 2))
    edge_dark = None
    blk_t = tint[row % rows, col]
    # mortar mask (rounded / eroded edges)
    edge = np.minimum(np.minimum(fx, 1 - fx) * 2.4 * 2, np.minimum(fy, 1 - fy) * 0.6 * 2 * 2)  # in metres-ish
    erosion = fbm(size, 5, 2.2) * 0.06
    mortar = np.clip((edge - 0.012 - erosion * 0.6) / 0.05, 0, 1)
    pits = worley(size, 900, 3)[0]
    pits = np.clip(1 - pits * 5, 0, 1) ** 3
    n1 = fbm(size, 1, 2.0)
    n2 = band(size, 2, 30, 120)
    strata = band(size, 4, 2, 6)
    streak = np.sin((yy * 40 + strata * 6) * math.pi) * 0.5 + 0.5
    h = mortar * (0.75 + 0.15 * n1 + 0.06 * n2 + 0.04 * streak) - pits * 0.12 * mortar
    base = colorize(0.35 + 0.3 * n1 + 0.35 * (blk_t[...] - 0.5) + 0.1 * streak,
                    [(0, (0.42, 0.35, 0.27)), (0.5, (0.66, 0.57, 0.45)), (1, (0.80, 0.72, 0.60))])
    stain = fbm(size, 9, 2.4)
    dirt = np.clip((stain - 0.55) * 2.5, 0, 1)[..., None]
    base = base * (1 - 0.45 * dirt) + np.array([0.20, 0.17, 0.13]) * 0.45 * dirt
    base = base * (0.92 + 0.08 * n2[..., None])
    mortar_col = np.array([0.40, 0.35, 0.28])
    m3 = mortar[..., None]
    alb = base * m3 + mortar_col * (1 - m3)
    alb *= (1 - 0.35 * pits[..., None])
    rough = 0.82 + 0.1 * (1 - mortar) + 0.06 * n2
    save_rgb(alb, "stone_blocks_albedo.png")
    save_normal(normal_from_height(h, 5.0), "stone_blocks_normal.png")
    save_gray(rough, "stone_blocks_rough.png")


def stone_plain(size=1024):
    """Weathered travertine without joints (columns, arches, seats, statues)."""
    n1 = fbm(size, 21, 2.0)
    n2 = band(size, 22, 25, 140)
    pits = worley(size, 1400, 23)[0]
    pits = np.clip(1 - pits * 6, 0, 1) ** 3
    cracks = worley(size, 40, 24, second=True)[0]
    cracks = np.clip(1 - cracks * 30, 0, 1) * (fbm(size, 25) > 0.55)
    yy = np.mgrid[0:size, 0:size][0] / size
    strata = band(size, 26, 2, 5)
    streak = np.sin((yy * 55 + strata * 8) * math.pi) * 0.5 + 0.5
    h = 0.7 + 0.2 * n1 + 0.08 * n2 - 0.2 * pits - 0.3 * cracks
    alb = colorize(0.35 + 0.4 * n1 + 0.1 * streak,
                   [(0, (0.45, 0.38, 0.30)), (0.5, (0.68, 0.60, 0.48)), (1, (0.82, 0.75, 0.63))])
    stain = np.clip((fbm(size, 27, 2.5) - 0.5) * 2.2, 0, 1)[..., None]
    alb = alb * (1 - 0.5 * stain) + np.array([0.18, 0.16, 0.12]) * 0.5 * stain
    alb *= (1 - 0.35 * pits[..., None]) * (1 - 0.5 * cracks[..., None])
    save_rgb(alb, "stone_plain_albedo.png")
    save_normal(normal_from_height(h, 4.0), "stone_plain_normal.png")
    save_gray(0.8 + 0.12 * n2, "stone_plain_rough.png")


def sand(size=1024):
    """Arena sand / packed dirt with pebbles (texture spans 4m)."""
    n1 = fbm(size, 31, 2.2)
    n2 = band(size, 32, 60, 300)
    n3 = fbm(size, 33, 1.6)
    peb_d, peb_i = worley(size, 2500, 34)
    rng = np.random.default_rng(35)
    keep = rng.random(2500) < 0.35
    peb = np.clip(1 - peb_d * 9, 0, 1) ** 0.7 * keep[peb_i]
    ripple = band(size, 36, 6, 14)
    h = 0.5 + 0.25 * n1 + 0.1 * n2 + 0.35 * peb + 0.08 * ripple
    alb = colorize(0.3 + 0.5 * n1 + 0.2 * n3,
                   [(0, (0.36, 0.27, 0.18)), (0.45, (0.55, 0.43, 0.30)), (1, (0.70, 0.58, 0.42))])
    alb *= (0.85 + 0.25 * n2[..., None])
    pebc = colorize(rng.random(2500)[peb_i], [(0, (0.35, 0.32, 0.29)), (1, (0.62, 0.57, 0.50))])
    pm = np.clip(peb * 2, 0, 1)[..., None]
    alb = alb * (1 - pm) + pebc * pm
    # dark damp patches
    damp = np.clip((fbm(size, 37, 2.6) - 0.6) * 3, 0, 1)[..., None]
    alb = alb * (1 - 0.35 * damp)
    save_rgb(alb, "sand_albedo.png")
    save_normal(normal_from_height(h, 3.0), "sand_normal.png")
    save_gray(np.clip(0.95 - 0.25 * damp[..., 0] - 0.1 * peb, 0, 1), "sand_rough.png")


def metal(size=512):
    """Dark gun steel / parkerised finish."""
    n1 = fbm(size, 41, 2.0)
    n2 = band(size, 42, 80, 250)
    xx = np.mgrid[0:size, 0:size][1] / size
    brushed = band(size, 43, 100, 250)
    wear = np.clip((fbm(size, 44, 2.2) - 0.62) * 4, 0, 1)
    v = 0.09 + 0.05 * n1 + 0.03 * n2
    alb = np.stack([v, v * 1.02, v * 1.06], axis=2)
    alb = alb * (1 - wear[..., None]) + np.array([0.42, 0.42, 0.44]) * wear[..., None]
    save_rgb(alb, "metal_albedo.png")
    save_gray(np.clip(0.48 - 0.25 * wear + 0.1 * n2 + 0.05 * brushed, 0, 1), "metal_rough.png")
    save_normal(normal_from_height(n2 * 0.3 + brushed * 0.1, 1.5), "metal_normal.png")


def polymer(size=512):
    n2 = band(size, 51, 120, 256)
    v = 0.055 + 0.02 * n2
    alb = np.stack([v, v, v * 1.05], axis=2)
    save_rgb(alb, "polymer_albedo.png")
    save_normal(normal_from_height(n2, 2.0), "polymer_normal.png")


def wood(size=512):
    """Dark oiled wood (gun furniture, Mystery Box planks). Grain along U."""
    yy, xx = np.mgrid[0:size, 0:size] / size
    warp = fbm(size, 61, 2.6) * 0.15
    rings = np.sin((yy * 18 + warp * 30 + band(size, 62, 1, 3) * 4) * math.pi * 2) * 0.5 + 0.5
    fine = band(size, 63, 60, 200)
    grain = np.clip(rings ** 3 * 0.6 + 0.4 * fine, 0, 1)
    alb = colorize(0.25 + 0.5 * grain + 0.25 * fbm(size, 64),
                   [(0, (0.18, 0.09, 0.04)), (0.5, (0.36, 0.19, 0.09)), (1, (0.52, 0.30, 0.15))])
    save_rgb(alb, "wood_albedo.png")
    save_normal(normal_from_height(grain * 0.5 + fine * 0.2, 2.5), "wood_normal.png")
    save_gray(0.55 + 0.25 * fine, "wood_rough.png")


def bronze(size=512):
    """Aged bronze / brass with verdigris in crevices."""
    n1 = fbm(size, 71, 2.0)
    n2 = band(size, 72, 40, 200)
    verd = np.clip((fbm(size, 73, 2.4) - 0.58) * 3.5, 0, 1)
    alb = colorize(0.4 + 0.4 * n1 + 0.2 * n2, [(0, (0.38, 0.24, 0.09)), (1, (0.78, 0.56, 0.24))])
    alb = alb * (1 - verd[..., None]) + np.array([0.24, 0.42, 0.34]) * verd[..., None]
    save_rgb(alb, "bronze_albedo.png")
    save_gray(np.clip(0.35 + 0.35 * verd + 0.15 * n2, 0, 1), "bronze_rough.png")
    save_gray(np.clip(1 - verd * 0.9, 0, 1), "bronze_metal.png")
    save_normal(normal_from_height(n2 * 0.3 + verd * 0.3, 2.0), "bronze_normal.png")


def iron(size=512):
    """Rusty wrought iron (gates, brackets, bands)."""
    n1 = fbm(size, 81, 2.1)
    rust = np.clip((fbm(size, 82, 2.3) - 0.4) * 2.2, 0, 1)
    n2 = band(size, 83, 60, 220)
    alb = np.array([0.12, 0.11, 0.10]) * (0.8 + 0.4 * n1[..., None])
    rc = colorize(n2, [(0, (0.25, 0.10, 0.04)), (1, (0.50, 0.24, 0.09))])
    alb = alb * (1 - rust[..., None]) + rc * rust[..., None]
    save_rgb(alb, "iron_albedo.png")
    save_gray(np.clip(0.55 + 0.4 * rust, 0, 1), "iron_rough.png")
    save_normal(normal_from_height(n2 * 0.4 + rust * 0.3, 3.0), "iron_normal.png")


def skin(size=1024):
    """Rotting undead skin: grey-green with bruises, veins, blood and wounds."""
    n1 = fbm(size, 91, 2.0)
    n2 = band(size, 92, 50, 250)
    veins = worley(size, 220, 93, second=True)[0]
    veins = np.clip(1 - veins * 40, 0, 1) * (fbm(size, 94) > 0.62)
    bruise = np.clip((fbm(size, 95, 2.3) - 0.5) * 2.5, 0, 1)
    wounds = np.clip((fbm(size, 96, 2.6) - 0.7) * 5, 0, 1)
    alb = colorize(0.3 + 0.5 * n1 + 0.2 * n2,
                   [(0, (0.30, 0.31, 0.25)), (0.5, (0.47, 0.46, 0.37)), (1, (0.60, 0.57, 0.46))])
    alb = alb * (1 - 0.6 * bruise[..., None]) + np.array([0.28, 0.20, 0.25]) * 0.6 * bruise[..., None]
    alb = alb * (1 - 0.5 * veins[..., None]) + np.array([0.18, 0.12, 0.16]) * 0.5 * veins[..., None]
    alb = alb * (1 - wounds[..., None]) + np.array([0.30, 0.04, 0.03]) * wounds[..., None]
    h = 0.5 + 0.2 * n1 + 0.1 * n2 - 0.25 * wounds + 0.08 * veins
    save_rgb(alb, "skin_albedo.png")
    save_normal(normal_from_height(h, 3.0), "skin_normal.png")
    save_gray(np.clip(0.75 - 0.45 * wounds, 0, 1), "skin_rough.png")


def cloth_red(size=512):
    """Weave + grime, tinted in-engine (used for tunics, banners)."""
    yy, xx = np.mgrid[0:size, 0:size]
    weave = (np.sin(xx * math.pi / 2) * np.sin(yy * math.pi / 2)) * 0.5 + 0.5
    n1 = fbm(size, 101, 2.2)
    grime = np.clip((fbm(size, 102, 2.5) - 0.45) * 2, 0, 1)
    alb = np.array([0.55, 0.06, 0.05]) * (0.75 + 0.25 * weave[..., None]) * (0.8 + 0.3 * n1[..., None])
    alb = alb * (1 - 0.6 * grime[..., None]) + np.array([0.15, 0.08, 0.05]) * 0.6 * grime[..., None]
    save_rgb(alb, "cloth_red_albedo.png")
    save_normal(normal_from_height(weave * 0.3 + n1 * 0.4, 2.0), "cloth_normal.png")


def leather(size=512):
    n1 = fbm(size, 111, 2.1)
    n2 = band(size, 112, 80, 250)
    cr = worley(size, 300, 113, second=True)[0]
    cr = np.clip(1 - cr * 15, 0, 1)
    alb = colorize(0.3 + 0.5 * n1, [(0, (0.14, 0.08, 0.04)), (1, (0.36, 0.22, 0.12))])
    alb *= (1 - 0.3 * cr[..., None])
    save_rgb(alb, "leather_albedo.png")
    save_normal(normal_from_height(n2 * 0.4 - cr * 0.3, 2.5), "leather_normal.png")


def blood_decal(size=512, seed=121, name="blood_decal.png"):
    """RGBA splatter for Decal nodes."""
    rng = np.random.default_rng(seed)
    img = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(img)
    c = size / 2
    r0 = size * 0.17
    d.ellipse([c - r0, c - r0 * 0.8, c + r0, c + r0 * 0.8], fill=255)
    for _ in range(60):
        ang = rng.random() * 2 * math.pi
        dist = r0 * (0.6 + rng.random() * 1.6)
        rr = size * (0.006 + rng.random() ** 2 * 0.05)
        x, y = c + math.cos(ang) * dist, c + math.sin(ang) * dist
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
        if rng.random() < 0.5:
            x2, y2 = c + math.cos(ang) * (dist + rr * 4), c + math.sin(ang) * (dist + rr * 4)
            d.line([x, y, x2, y2], fill=255, width=max(1, int(rr * 0.7)))
    img = img.filter(ImageFilter.GaussianBlur(2.5))
    a = np.asarray(img) / 255.0
    noise = fbm(size, seed + 1, 2.0)
    a = np.clip((a - 0.45) * 4 + (noise - 0.5) * 0.6, 0, 1)
    col = np.zeros((size, size, 4))
    shade = 0.6 + 0.4 * noise
    col[..., 0] = 0.32 * shade
    col[..., 1] = 0.02 * shade
    col[..., 2] = 0.02 * shade
    col[..., 3] = a * 0.92
    Image.fromarray((col * 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, name), optimize=True)


def scorch_decal(size=256):
    yy, xx = np.mgrid[0:size, 0:size] / size - 0.5
    r = np.sqrt(xx ** 2 + yy ** 2)
    n = fbm(size, 131, 2.0)
    a = np.clip((0.45 - r - (n - 0.5) * 0.2) * 4, 0, 1)
    col = np.zeros((size, size, 4))
    col[..., :3] = 0.03
    col[..., 3] = a * 0.9
    Image.fromarray((col * 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "scorch_decal.png"))


def bullet_hole(size=128):
    yy, xx = np.mgrid[0:size, 0:size] / size - 0.5
    r = np.sqrt(xx ** 2 + yy ** 2)
    a = np.clip((0.12 - r) * 40, 0, 1) + np.clip((0.3 - r) * 6, 0, 1) * 0.5 * (fbm(size, 141) > 0.4)
    col = np.zeros((size, size, 4))
    col[..., :3] = 0.06
    col[..., 3] = np.clip(a, 0, 1)
    Image.fromarray((col * 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "bullet_hole.png"))


def soft_particle(size=128):
    yy, xx = np.mgrid[0:size, 0:size] / size - 0.5
    r = np.sqrt(xx ** 2 + yy ** 2) * 2
    n = fbm(size, 151, 2.0)
    a = np.clip(1 - r, 0, 1) ** 2 * (0.6 + 0.4 * n)
    col = np.ones((size, size, 4))
    col[..., 3] = a
    Image.fromarray((col * 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "smoke_particle.png"))
    # flame sprite
    a2 = np.clip(1 - r * 1.1, 0, 1) ** 1.5
    Image.fromarray((np.dstack([np.ones_like(a2), np.ones_like(a2), np.ones_like(a2), a2]) * 255).astype(np.uint8), "RGBA").save(
        os.path.join(OUT, "glow_particle.png"))


def muzzle_flash(size=256):
    yy, xx = np.mgrid[0:size, 0:size] / size - 0.5
    ang = np.arctan2(yy, xx)
    r = np.sqrt(xx ** 2 + yy ** 2) * 2
    spikes = 0.55 + 0.45 * np.abs(np.cos(ang * 3.5)) ** 6
    a = np.clip(1 - r / spikes, 0, 1) ** 1.6
    core = np.clip(1 - r * 3, 0, 1)
    col = np.zeros((size, size, 4))
    col[..., 0] = 1.0
    col[..., 1] = 0.75 + 0.25 * core
    col[..., 2] = 0.35 + 0.65 * core
    col[..., 3] = np.clip(a + core, 0, 1)
    Image.fromarray((col * 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "muzzle_flash.png"))


def banner(w=512, h=1024):
    """Crimson banner with a gold laurel wreath + SPQR (historic, public domain)."""
    base = np.zeros((h, w, 3))
    n1 = fbm(512, 161, 2.2)
    n1 = np.tile(n1, (2, 1))[:h, :w]
    base[:] = np.array([0.50, 0.04, 0.035])
    base *= (0.8 + 0.3 * n1[..., None])
    img = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(img)
    gold = (214, 160, 60)
    # border bands
    d.rectangle([18, 18, w - 18, 34], fill=gold)
    d.rectangle([18, h - 120, w - 18, h - 104], fill=gold)
    # wreath
    cx, cy, R = w // 2, int(h * 0.38), int(w * 0.33)
    for side in (-1, 1):
        for k in range(14):
            t = 0.15 + k / 14 * 0.75
            ang = math.pi / 2 + side * t * math.pi
            x = cx + R * math.cos(ang)
            y = cy + R * math.sin(ang) * 1.05
            la = ang + side * math.pi / 2 + 0.6 * side
            lx, ly = math.cos(la) * 26, math.sin(la) * 26
            d.polygon([(x, y), (x + lx * 0.5 - ly * 0.25, y + ly * 0.5 + lx * 0.25), (x + lx, y + ly),
                       (x + lx * 0.5 + ly * 0.25, y + ly * 0.5 - lx * 0.25)], fill=gold)
        d.arc([cx - R, cy - R * 1.05, cx + R, cy + R * 1.05], 100 if side < 0 else -80, 260 if side < 0 else 80, fill=gold, width=5)
    # eagle (simple stylised: body, spread wings, head)
    ex, ey = cx, cy - 10
    d.polygon([(ex, ey - 60), (ex + 14, ey - 42), (ex + 10, ey + 40), (ex, ey + 70), (ex - 10, ey + 40), (ex - 14, ey - 42)], fill=gold)
    for s in (-1, 1):
        pts = [(ex + s * 10, ey - 30)]
        for i in range(6):
            pts.append((ex + s * (40 + i * 18), ey - 70 + i * 6 + (i % 2) * 10))
        pts.append((ex + s * 130, ey - 5))
        pts.append((ex + s * 12, ey + 15))
        d.polygon(pts, fill=gold)
    d.ellipse([ex - 12, ey - 82, ex + 12, ey - 56], fill=gold)
    d.polygon([(ex + 10, ey - 72), (ex + 26, ey - 66), (ex + 10, ey - 62)], fill=gold)
    # SPQR text using a drawn font if available
    try:
        from PIL import ImageFont
        fp = os.path.join(os.path.dirname(OUT), "fonts", "Cinzel-Variable.ttf")
        font = ImageFont.truetype(fp, 92)
        tw = d.textlength("SPQR", font=font)
        d.text(((w - tw) / 2, int(h * 0.64)), "SPQR", font=font, fill=gold)
    except Exception as e:  # pragma: no cover
        print("font fallback", e)
        d.text((w / 2 - 40, int(h * 0.64)), "SPQR", fill=gold)
    # tattered bottom fringe shading
    arr = np.asarray(img).astype(float) / 255
    grime = np.clip((fbm(512, 162, 2.4) - 0.5) * 1.8, 0, 1)
    grime = np.tile(grime, (2, 1))[:h, :w]
    arr = arr * (1 - 0.45 * grime[..., None])
    yy = np.mgrid[0:h, 0:w][0] / h
    arr *= (0.75 + 0.25 * (1 - yy))[..., None]
    save_rgb(arr, "banner_albedo.png")
    # alpha for ragged edge
    xx = np.mgrid[0:h, 0:w][1] / w
    edge = h - 60 - (np.sin(xx * 40) * 18 + fbm(512, 163)[0:1, :w] * 50)
    a = (np.mgrid[0:h, 0:w][0] < edge).astype(float)
    holes = (np.tile(fbm(512, 164, 1.8), (2, 1))[:h, :w] > 0.86)
    a[holes] = 0
    Image.fromarray((a * 255).astype(np.uint8), "L").save(os.path.join(OUT, "banner_alpha.png"))


def question_glow(size=256):
    """Emissive gradient used by the Mystery Box '?' glyphs."""
    yy, xx = np.mgrid[0:size, 0:size] / size
    v = 0.6 + 0.4 * np.sin(yy * math.pi)
    col = np.stack([np.ones_like(v), 0.55 + 0.3 * v, 0.15 * v], axis=2)
    save_rgb(col, "glow_gradient.png")


def sky_stars(w=2048, h=1024):
    rng = np.random.default_rng(171)
    img = np.zeros((h, w, 3))
    n = 5000
    xs = rng.integers(0, w, n)
    ys = (rng.random(n) ** 1.3 * h * 0.5).astype(int)
    br = rng.random(n) ** 6
    img[ys, xs] = br[:, None] * np.array([1.0, 0.97, 0.9])
    save_rgb(img, "stars.png")


def icon(size=256):
    from PIL import ImageFont
    img = Image.new("RGB", (size, size), (20, 8, 6))
    d = ImageDraw.Draw(img)
    d.ellipse([20, 40, size - 20, size - 40], outline=(200, 150, 70), width=10)
    try:
        font = ImageFont.truetype(os.path.join(os.path.dirname(OUT), "fonts", "Cinzel-Variable.ttf"), 120)
        tw = d.textlength("AM", font=font)
        d.text(((size - tw) / 2, 52), "AM", font=font, fill=(170, 20, 16))
    except Exception:
        pass
    img.save(os.path.join(OUT, "icon.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = [stone_blocks, stone_plain, sand, metal, polymer, wood, bronze, iron, skin, cloth_red, leather,
            blood_decal, lambda: blood_decal(512, 125, "blood_decal_2.png"), scorch_decal, bullet_hole,
            soft_particle, muzzle_flash, banner, question_glow, sky_stars, icon]
    for j in jobs:
        j()
        print("ok", getattr(j, "__name__", "job"))


if __name__ == "__main__":
    main()
