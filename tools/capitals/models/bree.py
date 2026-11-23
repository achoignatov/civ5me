"""Bree, the chief village of Bree-land (Eriador).

Book/film features modelled:
  * Bree-hill, "a big hill crowned with a hedge", with the village clustered at its
    southern foot and hobbit-holes cut into the lower slopes;
  * the Great East Road running east-west in front of the hill and the Greenway
    climbing north through the village, meeting at the famous crossroads;
  * the Prancing Pony: a large stone-and-plaster inn with a courtyard, stables and a
    hanging sign, where the Hobbits met Strider;
  * timber and plaster houses under thatch, a market stall, a well and a hedged
    boundary with a gate;
  * a few Men and Hobbits going about their business.
The village faces the camera (-Y); Bree-hill rises behind it.
"""
import math

from blib import (material, hexcol as h, box, gable, cyl, cone, lathe, terrain_polar, blob, sphere,
                  strut, ring, window_row, banner, T, near_path)
from city_common import house, person, barrel, crate


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    r = math.hypot(x / 1.35, (y - 9.0) / 1.0)
    z = 0.5 + 12.8 * math.exp(-(r / 11.0) ** 2.0)
    # the village shelf at the south foot of the hill
    shelf = sm((4.0 - y) / 3.0) * sm((y + 8.0) / 3.0) * sm((18.0 - abs(x)) / 4.0)
    z = z * (1.0 - shelf) + 1.05 * shelf
    # a shallow dip where the Greenway passes the hill
    z -= 0.35 * sm((2.5 - abs(x)) / 2.0) * sm((10.0 - y) / 8.0)
    return z


def build(b):
    material('breegrass', h('6b8f3e'), zramp=[(-1, h('6d8b43')), (2, h('759746')), (8, h('67883a')),
                                              (14, h('728b45'))], slope_color=h('6a7d45'), slope_start=0.85)   # a grassy hill, not a crag
    material('road', h('a08e6e'), h('8b7a5c'), noise=2.0)
    material('plaster', h('d8c79e'), h('c9b68b'), noise=3.0)
    material('timber', h('62432a'), h('52371f'), noise=4.0)
    material('thatch', h('a38446'), h('8c6e37'), noise=3.5)
    material('stone', h('9a9384'), h('867f71'), noise=2.0, courses=0.45, course_dark=0.8)
    material('window', h('2a2118'))
    material('hobbithill', h('5f8a35'), h('74a042'), noise=2.0)
    material('hedge', h('3d6427'), h('4b7530'), noise=2.5)
    material('sign', h('d9c27a'), h('c2a85d'), noise=2.0)
    material('wellwater', h('5a8a9a'), ao=False)
    material('flower', h('c85a6a'), h('e0b04a'), noise=8.0)
    material('pumpkin2', h('d97a24'), h('c4681c'), noise=5.0)

    PATH_E = [(-31.0, -8.0), (31.0, -8.0)]
    PATH_N = [(0.0, -31.0), (0.0, -8.0), (0.0, 7.0)]

    def mat(x, y, z, s):
        if near_path(x, y, PATH_E, 1.4) or near_path(x, y, PATH_N, 1.2):
            return 'road'
        return 'breegrass'

    terrain_polar(b, ground, mat, R=31, cy=2, nr=38, na=124)

    # --- the hedge and its gate at the south of the village
    for k in range(54):
        a = math.radians(18 + 324 * (k + 0.5) / 54)
        x, y = 15.0 * math.cos(a), 2.0 + 12.0 * math.sin(a)
        z = ground(x, y)
        if abs(x) < 2.2 and y < -8:
            continue
        blob(b, 'hedge', x, y, z - 0.5, 1.15, n=7, rings=4, squash=0.65, jitter=0.15)
    for s in (-1, 1):
        box(b, 'timber', s * 2.4, -9.7, ground(s * 2.4, -9.7) - 0.4, 0.7, 0.7, 3.6)
        box(b, 'timber', s * 2.4, -9.7, ground(s * 2.4, -9.7) + 3.2, 1.0, 1.0, 0.5)
    box(b, 'timber', 0, -9.7, ground(0, -9.7) + 3.2, 5.6, 0.6, 0.45)

    # --- the Prancing Pony and its courtyard
    ix, iy = 5.2, -1.5
    iz = ground(ix, iy) - 0.3
    box(b, 'stone', ix, iy, iz, 7.2, 5.2, 2.0)
    box(b, 'plaster', ix, iy, iz + 2.0, 7.0, 5.0, 2.5)
    gable(b, 'thatch', ix, iy, iz + 4.5, 7.2, 5.2, 2.1, overhang=0.45)
    # windows on both floors, front and side
    window_row(b, 'window', ix - 3.0, iy - 2.62, ix + 3.0, iy - 2.62, iz + 2.8, 5, w=0.3, h=0.45, out=0.0)
    window_row(b, 'window', ix - 3.0, iy - 2.62, ix + 3.0, iy - 2.62, iz + 1.0, 4, w=0.28, h=0.35, out=0.0)
    box(b, 'timber', ix, iy - 2.66, iz, 1.15, 0.10, 1.8)
    # the hanging sign on an iron bracket
    strut(b, 'timber', (ix - 3.8, iy - 2.7, iz + 4.1), (ix - 5.2, iy - 2.7, iz + 4.1), 0.06, 0.05, n=4)
    strut(b, 'timber', (ix - 5.0, iy - 2.7, iz + 4.1), (ix - 5.0, iy - 2.7, iz + 3.5), 0.04, 0.04, n=3)
    box(b, 'sign', ix - 5.0, iy - 2.7, iz + 2.9, 1.15, 0.08, 0.65)
    # courtyard, stable and a cart
    box(b, 'dirt', ix + 5.4, iy + 0.3, iz - 0.05, 5.5, 5.5, 0.1)
    house(b, ix + 6.2, iy + 2.0, iz, w=3.4, d=2.4, h=1.4, wall='timber', roof='thatch',
          roof_h=1.0, windows=2, door=False)
    for (cx, cy) in ((ix + 3.4, iy - 2.2), (ix + 4.0, iy + 2.4)):
        barrel(b, 'timber', cx, cy, ground(cx, cy), 0.42, 0.8)
    crate(b, 'timber', ix + 7.2, iy - 0.6, ground(ix + 7.2, iy - 0.6), 0.65)

    # --- village houses around the foot of the hill
    houses = [(-9.5, -4.5, 4.4, 3.0, 1.7, 6), (-13.0, -1.0, 3.6, 2.8, 1.6, -12),
              (-7.0, 1.8, 3.2, 2.6, 1.6, 8), (-12.5, 3.2, 3.0, 2.4, 1.5, 18),
              (-2.0, -4.8, 3.8, 2.6, 1.7, -4), (10.8, -4.0, 3.6, 2.6, 1.7, 12),
              (12.5, 1.0, 3.0, 2.4, 1.5, 22), (-2.5, 3.4, 3.0, 2.4, 1.5, -6),
              (8.8, 4.2, 3.4, 2.5, 1.6, -16), (2.8, 4.8, 3.0, 2.3, 1.4, 5)]
    for (x, y, w, d, hh, rz) in houses:
        z = ground(x, y) - 0.25
        house(b, x, y, z, w=w, d=d, h=hh, rz=rz, wall='plaster', roof='thatch', roof_h=1.25,
              base='stone', base_h=0.35, windows=2, chimney=True, chimney_mat='stone',
              overhang=0.35)
    # a market stall near the crossroads
    sx, sy = -4.5, -7.0
    box(b, 'timber', sx, sy, ground(sx, sy), 2.6, 1.8, 0.25)
    for s in (-1, 1):
        for t in (-1, 1):
            cyl(b, 'timber', sx + s * 1.0, sy + t * 0.7, ground(sx, sy), 0.08, 2.0, n=4)
    gable(b, 'thatch', sx, sy, ground(sx, sy) + 2.0, 2.8, 2.1, 0.55, overhang=0.1)
    for k, (dx, dy) in enumerate(((-0.7, -0.3), (0.0, 0.1), (0.7, -0.2))):
        sphere(b, 'pumpkin2', sx + dx, sy + dy, ground(sx, sy) + 0.45, 0.22, n=6, rings=4)

    # --- hobbit-holes cut into the south-west slope of Bree-hill
    for (hx, hy, hs) in ((-9.0, 5.6, 1.0), (-12.0, 6.8, 0.85), (10.8, 6.0, 0.9)):
        hz = ground(hx, hy) - 0.15
        M = T(hx, hy, hz, rx=90)
        r = 1.25 * hs
        lathe(b, 'stone', [(0, 0), (r + 0.45, 0), (r + 0.45, 0.3), (r, 0.3), (r, 0.08), (0, 0.08)],
              n=20, M=M, smooth=False)
        lathe(b, 'window', [(r, 0.08), (r, 0.14), (0, 0.14)], n=20, M=M, smooth=False)
        # turf lip over the door
        blob(b, 'hobbithill', hx, hy - 0.4, hz + r + 0.35, r * 1.15, n=8, rings=4, squash=0.55)
        # a small round window beside the door
        box(b, 'timber', hx + r + 0.55, hy - 0.12, hz + 0.55, 0.12, 0.1, 0.75)
        lathe(b, 'window', [(0.22, 0), (0.22, 0.05), (0, 0.05)], n=10,
              M=T(hx + r + 0.55, hy - 0.2, hz + 0.95, rx=90), smooth=False)

    # --- the well and a few trees
    wx, wy = -1.5, 1.0
    wz = ground(wx, wy)
    ring(b, 'stone', 0.55, 0.8, wz, 0.8, 0, 360, n=14, x=wx, y=wy)
    ring(b, 'wellwater', 0.05, 0.55, wz + 0.55, 0.05, 0, 360, n=14, x=wx, y=wy, inner=False)
    for s in (-1, 1):
        cyl(b, 'timber', wx + s * 0.7, wy, wz, 0.07, 1.8, n=4)
    gable(b, 'thatch', wx, wy, wz + 1.8, 1.8, 1.0, 0.45, overhang=0.1)
    for (x, y) in ((-17, -7), (18, -6), (-16, 8), (16, 9), (-5, 10), (7, 11)):
        z = ground(x, y)
        cyl(b, 'timber', x, y, z, 0.25, 3.2, n=6, r2=0.18)
        for k in range(3):
            blob(b, 'hedge' if k == 0 else 'breegrass', x + b.rng.uniform(-0.7, 0.7),
                 y + b.rng.uniform(-0.7, 0.7), z + 2.6 + 0.45 * k, 1.35, n=7, rings=4, squash=0.8)

    # --- people at the crossroads and outside the inn
    person(b, -1.2, -8.4, ground(-1.2, -8.4), s=0.95, robe='timber', skin='sign', arms=True)
    person(b, 1.6, -7.4, ground(1.6, -7.4), s=0.65, robe='plaster', skin='sign', arms=True)
    person(b, 8.0, -5.0, ground(8.0, -5.0), s=0.95, robe='hedge', skin='sign', arms=True)
    person(b, 3.4, 1.2, ground(3.4, 1.2), s=0.95, robe='thatch', skin='sign', arms=True)

    # --- a signpost at the crossroads
    px, py = -0.8, -7.2
    pz = ground(px, py)
    cyl(b, 'timber', px, py, pz, 0.10, 3.0, n=5)
    box(b, 'sign', px + 0.55, py, pz + 2.3, 1.3, 0.08, 0.38)
    box(b, 'sign', px, py - 0.55, pz + 1.75, 0.08, 1.1, 0.35)


# the village is laid out at the foot of the hill in a ~20 unit radius; scaled to fill the tile
FILL = 1.45

PREVIEW = [((8, -32, 22), (0, 2, 7), 46), ((28, -18, 12), (0, 3, 5), 42)]
