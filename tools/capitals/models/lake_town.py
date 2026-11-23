"""Lake-town of Bard the Bowman (the town of the films' The Hobbit).

The Hobbit: "the town ... built on huge piles made of forest trees driven into the bottom
of the lake", "a great bridge of wood" to the shore, boats everywhere. Films: a crowded
town of steep-roofed, weathered timber houses standing over a web of canals and plank
walkways, Bard's house by the water, the dwarvish Windlance on its tower, from which Bard's
ancestor Girion shot at Smaug, fishing boats and nets, lanterns on poles.
(The city-state Esgaroth shows the walled town platform; Lake Town shows the canals.)
Modelled: rows of tall timber houses on piles separated by canals with boats, plank
bridges and walkways, the Master's great house, Bard's house, the windlance tower with its
huge bow and the Black Arrow, the long bridge to the shore, lanterns (animated torches).
The town faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, gable, hipped, cyl, cone, lathe, terrain_polar, blob, strut, sphere,
                  T, curve, window_row)
from city_common import (boat, fx, water_disc, barrel, crate, person, house, grow)


def ground(x, y):
    z = -1.6
    if y > 20.0:
        z = -1.6 + 3.2 * min(1.0, (y - 20.0) / 6.0)
    return z


def tall_house(b, x, y, pz, w, d, hh, rz, roof):
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(b, 'piling', x + sx * (w / 2 - 0.3), y + sy * (d / 2 - 0.3), -1.6, 0.18, pz + 1.6, n=5, top=False)
    box(b, 'plank', x, y, pz, w + 0.6, d + 0.6, 0.25, rz=rz)
    box(b, 'wood', x, y, pz + 0.25, w, d, hh, rz=rz)
    box(b, 'darkwood', x, y, pz + 0.25 + hh * 0.5, w + 0.3, d + 0.3, 0.2, rz=rz)    # jettied upper floor
    gable(b, roof, x, y, pz + 0.25 + hh, w + 0.3, d + 0.3, hh * 0.75, rz=rz, overhang=0.35)
    ca, sa = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    fx_, fy_ = x + sa * (d / 2 + 0.03), y - ca * (d / 2 + 0.03)
    for k in (-1, 1):
        box(b, 'window', fx_ + ca * k * w * 0.25, fy_ + sa * k * w * 0.25, pz + hh * 0.65, 0.5, 0.08, 0.7, rz=rz)
    box(b, 'darkwood', fx_, fy_, pz + 0.25, 0.7, 0.08, 1.3, rz=rz)


def build(b):
    material('lake', h('3a6276'), h('4a7286'), noise=1.0, ao=False, spec=0.7, refl=50)
    material('shore', h('7a7258'), h('6a6248'), noise=3.0)
    material('wood', h('7a6044'), h('6a5038'), noise=5.0, courses=0.35, course_dark=0.82)
    material('darkwood', h('3e2b1c'), h('4c3522'), noise=4.0)
    material('plank', h('8a6a44'), h('7a5a38'), noise=5.0)
    material('piling', h('4b3422'), h('3c291a'), noise=4.0)
    material('roofwood', h('5a4630'), h('4a3a26'), noise=4.0, courses=0.3, course_dark=0.75)
    material('roofslate', h('4a5056'), h('5a6066'), noise=3.0)
    material('window', h('f0b050'), emission=0.8)
    material('sail', h('c8bea2'), h('b0a68a'), noise=3.0)
    material('iron', h('3a3a3e'))
    material('blackarrow', h('121212'))
    material('cloth', h('5a5a6a'), h('6a5a4a'), noise=3.0)
    material('skin', h('e0b896'))
    material('rope', h('9c8a62'))

    terrain_polar(b, ground, lambda x, y, z, s: 'shore' if y > 21 else 'lake', R=31, cy=2, nr=30, na=110)
    water_disc(b, 'lake', z=0.12, R=30.4, cy=2.0)
    town = len(b.verts)
    PZ = 1.0
    rng = b.rng

    # --- blocks of tall houses between canals running north-south and east-west
    canals_x = (-7.0, 7.0)
    canal_y = 3.0
    for bx0, bx1 in ((-17.0, -9.0), (-5.0, 5.0), (9.0, 17.0)):
        for by0, by1 in ((-10.0, 1.0), (5.0, 15.0)):
            # a walkway around each block
            for (x, y, sx, sy) in (((bx0 + bx1) / 2, by0 - 0.6, bx1 - bx0, 1.2), ((bx0 + bx1) / 2, by1 + 0.6, bx1 - bx0, 1.2)):
                box(b, 'plank', x, y, PZ - 0.1, sx, sy, 0.22)
            nx = max(1, int((bx1 - bx0) / 3.4))
            ny = max(1, int((by1 - by0) / 4.8))
            for i in range(nx):
                for j in range(ny):
                    x = bx0 + (bx1 - bx0) * (i + 0.5) / nx
                    y = by0 + (by1 - by0) * (j + 0.5) / ny
                    if abs(x) < 4.5 and 5 < y < 15:
                        continue   # the Master's house goes here
                    tall_house(b, x + rng.uniform(-0.3, 0.3), y, PZ, w=rng.uniform(2.6, 3.0), d=rng.uniform(3.0, 3.8),
                               hh=rng.uniform(3.2, 4.6), rz=rng.choice((0, 0, 180)) + rng.uniform(-4, 4),
                               roof='roofwood' if rng.random() < 0.7 else 'roofslate')
    # plank bridges over the canals
    for cx in canals_x:
        for y in (-6.0, 0.5, 10.0):
            box(b, 'plank', cx, y, PZ + 0.3, 4.4, 1.6, 0.22)
    for x in (-13.0, 0.0, 13.0):
        box(b, 'plank', x, canal_y, PZ + 0.3, 1.6, 4.4, 0.22)

    # --- the Master's great house in the centre
    mx, my = 0.0, 10.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(b, 'piling', mx + sx * 3.5, my + sy * 2.5, -1.6, 0.25, PZ + 1.6, n=6, top=False)
    box(b, 'plank', mx, my, PZ, 9.0, 7.0, 0.3)
    box(b, 'wood', mx, my, PZ + 0.3, 8.0, 6.0, 5.0)
    hipped(b, 'roofslate', mx, my, PZ + 5.3, 8.4, 6.4, 3.2, overhang=0.5)
    for sd in (-1, 1):
        cone(b, 'roofslate', mx + sd * 4.2, my - 3.0, PZ + 5.3, 1.0, 3.6, n=6)
        cyl(b, 'wood', mx + sd * 4.2, my - 3.0, PZ + 0.3, 0.9, 5.0, n=6)
    window_row(b, 'window', mx - 3.0, my - 3.02, mx + 3.0, my - 3.02, PZ + 3.0, 4, w=0.6, h=0.9, out=0.0)
    fx(b, 'Smoke_Master', (mx + 2.0, my + 1.0, PZ + 9.2), 'SMOKE')

    # --- the windlance tower with its great dwarvish bow and the Black Arrow
    wx, wy = -12.5, 12.0
    lathe(b, 'darkwood', [(1.9, 0), (1.7, 9.0), (2.3, 9.2), (0, 9.2)], n=8, x=wx, y=wy, z=PZ, smooth=False)
    box(b, 'plank', wx, wy, PZ + 9.2, 4.6, 4.6, 0.3)
    curve(b, 'iron', [(wx - 3.0, wy - 0.6, PZ + 10.0), (wx, wy - 1.6, PZ + 10.6), (wx + 3.0, wy - 0.6, PZ + 10.0)],
          0.18, 0.18, n=6)
    strut(b, 'rope', (wx - 3.0, wy - 0.6, PZ + 10.0), (wx, wy + 1.2, PZ + 10.4), 0.04, 0.04, n=3)
    strut(b, 'rope', (wx + 3.0, wy - 0.6, PZ + 10.0), (wx, wy + 1.2, PZ + 10.4), 0.04, 0.04, n=3)
    strut(b, 'blackarrow', (wx, wy + 1.4, PZ + 10.4), (wx, wy - 3.0, PZ + 10.6), 0.08, 0.06, n=4)
    cone(b, 'iron', 0, 0, 0, 0.22, 0.6, n=5, M=T(wx, wy - 3.0, PZ + 10.6, rx=90))
    gable(b, 'roofwood', wx, wy, PZ + 12.4, 3.6, 3.6, 1.6, overhang=0.2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(b, 'darkwood', wx + sx * 1.7, wy + sy * 1.7, PZ + 9.5, 0.1, 2.9, n=4)

    # --- Bard's house by the open water, his barge and the fishing boats
    tall_house(b, 13.0, -14.0, PZ, w=3.4, d=3.6, hh=4.4, rz=0, roof='roofwood')
    for (x, y, rz, s) in ((-7.0, -16.0, 85, 1.0), (7.0, -17.0, 95, 0.9), (-7.0, 3.0, 90, 0.7), (7.0, 8.0, 90, 0.7),
                          (-20.0, -14.0, 30, 1.1), (20.0, -9.0, -40, 1.0), (-3.0, -20.0, 10, 1.0)):
        boat(b, x, y, 0.15, rz=rz, s=s, hull='darkwood', sail='sail', mast=s > 0.8, oars=s <= 0.8)
    # torches on the corners, nets, barrels
    for k, (x, y) in enumerate(((-9.0, -10.8), (9.0, -10.8), (-17.0, -10.8), (17.0, -10.8), (0.0, -11.0))):
        strut(b, 'darkwood', (x, y, PZ), (x, y, PZ + 2.8), 0.07, 0.06, n=4)
        fx(b, 'Lantern_%d' % k, (x, y, PZ + 3.1), 'TORCH')
    for k in range(5):
        barrel(b, 'wood', -2.0 + 0.9 * k, -11.6, PZ + 0.1, 0.38, 0.8)
    for (x, y) in ((-1.0, -11.4), (2.5, -11.0), (12.0, -11.6)):
        person(b, x, y, PZ + 0.1, s=0.9, robe='cloth', skin='skin')
    # the long bridge to the northern shore
    for k in range(10):
        y = 15.8 + 1.0 * k
        box(b, 'plank', 0.0, y, PZ - 0.1 + 0.06 * k, 2.4, 1.05, 0.22)
        for sd in (-1, 1):
            cyl(b, 'piling', sd * 1.1, y, -1.6, 0.15, PZ + 1.5 + 0.06 * k, n=5, top=False)
    grow(b, town, 1.18, 0.0, 2.0, 1.0)


PREVIEW = [((8, -34, 18), (0, 0, 5), 45)]
