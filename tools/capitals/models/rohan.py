"""Edoras, the court of the Mark (Rohan).

Book/film features modelled:
  * a lone green hill before the White Mountains, its slopes crowded with timber houses
    of the Rohirrim under steep thatched roofs;
  * a dike and a mighty wall of sharp-pointed wooden stakes around the hill, with a gate
    at the foot, from which a paved road climbs to the summit;
  * Meduseld, the Golden Hall, on a stone terrace at the top: a long timber hall with a
    golden roof, crossed horse-head gable ends and a broad stair, the spring that gushes
    from a horse-head stone into a basin beside the stair;
  * green banners of the Mark, and the barrow-mounds of the kings white with
    simbelmynë beside the road;
  * snow-capped peaks of the Ered Nimrais behind (the hill faces the camera).
"""
import math

from blib import (material, hexcol as h, box, ring, cyl, cone, gable, terrain_polar, blob, strut, banner, prism, lathe,
                  window_row, tree, near_path)


def hill(x, y):
    r = math.hypot(x / 1.0, (y - 3) / 1.15)
    core = 13.5 * math.exp(-(r / 13.0) ** 2.2)
    # flattened summit for Meduseld
    core = min(core, 11.4) if r < 5 else core
    mtn = 0.0
    if y > 12:
        t = min(1.0, (y - 12) / 14.0)
        mtn = 27.0 * t ** 1.6 * (0.75 + 0.25 * math.sin(x * 0.25 + 1.0)) * math.exp(-(x / 40) ** 4)
        mtn += 3.0 * math.sin(x * 0.7) * math.sin(y * 0.5) * t
    return max(core, mtn) + 0.2


def build(b):
    material('thatch', h('a88a4c'), h('8e7440'), noise=3.5)
    material('goldroof', h('dcae3c'), h('c39229'), noise=4.0)
    material('timber', h('6b4b2e'), h('59401f'), noise=3.0)
    material('timberdark', h('3f2d1c'))
    material('stake', h('7a5c3a'), h('664b2e'), noise=4.0)
    material('stonestep', h('a39d8f'), h('8e897c'), noise=2.0, courses=0.5, course_dark=0.8)
    material('road', h('9a8c70'), h('857860'), noise=2.0)
    material('greenbanner', h('2f6d34'))
    material('simbelmyne', h('6f9a48'), h('eef2ea'), noise=9.0)
    material('meadow', h('6e9446'), zramp=[(0, h('7d9a4a')), (8, h('6b8c3f')), (14, h('6e8a45')),
                                           (20, h('7d7a6e')), (30, h('8e8b86')), (36, h('eef1f3'))],
             slope_color=h('7c776d'), slope_start=0.5)

    material('roadmat', h('a39472'), h('8c7f63'), noise=2.0)
    gy0 = 3 - 15.5 * 1.15
    PATH = [(0, gy0 - 9), (0, gy0), (-2.5, -6.5), (3.0, -2.0), (-1.5, 1.5), (0, -2.0)]

    def mat(x, y, z, s):
        return 'roadmat' if near_path(x, y, PATH, 1.0) else 'meadow'
    terrain_polar(b, hill, mat, R=31, sy=1.0, cy=2, nr=30, na=96)

    # --- dike + palisade of sharp stakes around the hill, gate to the south
    R = 15.5
    for k in range(150):
        a = 90 + 360 * (k + 0.5) / 150
        if abs(((a - 270) + 180) % 360 - 180) < 5.5:
            continue
        ar = math.radians(a)
        x, y = R * math.cos(ar), 3 + R * 1.15 * math.sin(ar)
        z = hill(x, y)
        hgt = 2.4 + 0.3 * math.sin(k * 1.7)
        strut(b, 'stake', (x, y, z - 0.5), (x, y, z + hgt), 0.28, 0.28, n=5)
        strut(b, 'stake', (x, y, z + hgt), (x, y, z + hgt + 0.6), 0.28, 0.0, n=5)
    # gate: two timber towers with a roofed gatehouse
    gy = 3 - R * 1.15
    gz = hill(0, gy)
    for s in (-1, 1):
        box(b, 'timber', s * 2.3, gy, gz - 0.5, 1.6, 1.6, 4.4)
        gable(b, 'thatch', s * 2.3, gy, gz + 3.9, 1.6, 1.6, 1.0, rz=90, overhang=0.25)
    box(b, 'timberdark', 0, gy, gz + 2.6, 3.0, 1.0, 0.6)
    gable(b, 'thatch', 0, gy, gz + 3.2, 3.2, 1.2, 0.8, overhang=0.2)
    box(b, 'timberdark', 0, gy - 0.3, gz - 0.4, 2.9, 0.3, 2.9)

    # --- the houses of Edoras on the slopes
    rng = b.rng
    placed = []
    for k in range(200):
        if len(placed) >= 44:
            break
        a = rng.uniform(0, 360)
        rr = rng.uniform(5.5, 14.0)
        x, y = rr * math.cos(math.radians(a)), 3 + rr * 1.15 * math.sin(math.radians(a))
        if any(math.hypot(x - px, y - py) < 3.0 for px, py in placed):
            continue
        if near_path(x, y, PATH, 2.6):   # keep the road free
            continue
        placed.append((x, y))
        z = min(hill(x + dx, y + dy) for dx in (-1, 1) for dy in (-1, 1)) - 0.3
        L, W = rng.uniform(2.6, 3.6), rng.uniform(1.6, 2.0)
        rz = a + 90 + rng.uniform(-15, 15)
        hh = rng.uniform(1.1, 1.5)
        box(b, 'timber', x, y, z, L, W, hh + 0.3, rz=rz)
        gable(b, 'thatch', x, y, z + hh + 0.3, L, W, 1.6, rz=rz, overhang=0.3)
        # dark doorway on the long side
        dx, dy = math.cos(math.radians(rz - 90)), math.sin(math.radians(rz - 90))
        box(b, 'timberdark', x + dx * (W / 2 + 0.02), y + dy * (W / 2 + 0.02), z + 0.3, 0.6, 0.06, 1.0, rz=rz)
        if rng.random() < 0.35:
            banner(b, 'timberdark', 'greenbanner', x + 1.2, y + 0.5, z, h=4.2, w=0.6, ch=1.5, rz=rz)

    # --- Meduseld on its terrace
    top = 12.2
    prism(b, 'stonestep', [(-7, -2.2), (7, -2.2), (7, 8.5), (-7, 8.5)], top - 3.0, 3.2)
    # the great stair down the south face of the terrace
    for i in range(7):
        box(b, 'stonestep', 0, -2.2 - 0.45 * i - 0.25, top + 0.2 - 0.45 * (i + 1) - 0.1, 4.5 - 0.1 * i, 0.5, 0.45)
    # the spring from the horse-head stone into a basin beside the stair
    ring(b, 'stonestep', 0.6, 0.9, top - 3.0, 0.5, 0, 360, n=12, x=3.6, y=-3.6)
    ring(b, 'water', 0.05, 0.6, top - 3.0, 0.42, 0, 360, n=12, x=3.6, y=-3.6, inner=False)
    box(b, 'stonestep', 3.6, -2.5, top - 3.0, 0.7, 0.5, 1.6)
    # the hall: long timber hall, posts, golden roof
    HL, HW, HH = 10.0, 5.0, 2.6
    hx, hy = 0.0, 3.6
    box(b, 'timber', hx, hy, top + 0.2, HW, HL, HH)
    gable(b, 'goldroof', hx, hy, top + 0.2 + HH, HL, HW, 3.4, rz=90, overhang=0.55)
    # porch and carved posts at the gable end facing south
    py = hy - HL / 2 - 1.2
    box(b, 'stonestep', hx, py + 0.4, top, HW + 0.6, 2.2, 0.2)
    for s in (-2.0, -0.7, 0.7, 2.0):
        cyl(b, 'timber', hx + s, py, top + 0.2, 0.18, HH, n=6)
    gable(b, 'goldroof', hx, py + 0.6, top + 0.2 + HH, 2.0, HW - 0.4, 2.7, rz=90, overhang=0.2)
    box(b, 'timberdark', hx, hy - HL / 2 - 0.02, top + 0.2, 1.6, 0.06, 2.2)
    # crossed horse-head beams at both gable apexes
    for ey, out in ((hy - HL / 2 - 0.55 - 0.6, -1), (hy + HL / 2 + 0.55, 1)):
        z0 = top + 0.2 + HH + 2.0
        for s in (-1, 1):
            strut(b, 'goldroof', (hx - s * 1.0, ey, z0), (hx + s * 0.9, ey, z0 + 2.0), 0.12, 0.1, n=4)
            box(b, 'goldroof', hx + s * 1.05, ey, z0 + 1.9, 0.5, 0.18, 0.4, rz=0)
    # windows along the hall
    window_row(b, 'timberdark', hx + HW / 2 + 0.02, hy - HL / 2 + 1, hx + HW / 2 + 0.02, hy + HL / 2 - 1, top + 1.2, 4,
               w=0.5, h=0.7, out=0.0)
    window_row(b, 'timberdark', hx - HW / 2 - 0.02, hy + HL / 2 - 1, hx - HW / 2 - 0.02, hy - HL / 2 + 1, top + 1.2, 4,
               w=0.5, h=0.7, out=0.0)
    # banners on the terrace
    for s in (-1, 1):
        banner(b, 'timberdark', 'greenbanner', s * 5.8, -1.6, top + 0.2, h=6.0, w=0.9, ch=2.6, rz=0)

    # --- barrow-mounds of the kings, white with simbelmynë, beside the road
    for i in range(4):
        for s in (-1, 1):
            x, y = s * (4.5 + 1.2 * (i % 2)), gy - 4.2 - i * 2.6
            blob(b, 'simbelmyne', x, y, hill(x, y) - 1.1, 1.5, n=10, rings=4, squash=0.42, jitter=0.03)
    # a few trees by the stream at the foot of the hill
    for (x, y) in ((-20, -8), (-23, -3), (21, -6), (24, -1), (18, -12)):
        tree(b, x, y, hill(x, y) - 0.3, h=4.5, r=1.7)


PREVIEW = [((10, -30, 30), (0, 2, 12), 45)]

# Edoras' hill is laid out in ~22 units; scaled to fill the tile (pipeline FILL)
FILL = 1.15
