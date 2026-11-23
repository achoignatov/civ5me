"""Mithrandir: the Grey Pilgrim's camp.

Gandalf had no city and no home ("I am a wanderer"), so the city-state shows his camp on a
green road: from The Fellowship of the Ring and the films:
  * his horse-drawn cart, piled with crates of fireworks marked with a red G-rune;
  * Gandalf the Grey himself, pointed hat, grey robe, staff and pipe;
  * rockets on wooden racks and the great dragon firework, bursting in the sky
    (animated sparks), a campfire, his grey horse;
  * an old ring of standing stones and a milestone on the road, a broad oak, a pavilion
    of grey canvas and the green hills of Eriador around.
The cart faces the camera (-Y).
"""
import math

from mathutils import Vector

from blib import (material, hexcol as h, box, gable, cyl, cone, lathe, terrain_polar, blob, strut, sphere,
                  T, near_path, curve, dome)
from city_common import (wizard, horse, crate, barrel, campfire, standing_stone, tent, fx, plate, tree,
                         scatter_forest, fence, person)


def ground(x, y):
    z = 0.6 + 0.5 * math.sin(x * 0.18) * math.cos(y * 0.22)
    z += 3.5 * math.exp(-((x + 20) ** 2 + (y - 16) ** 2) / 90.0) + 2.8 * math.exp(-((x - 21) ** 2 + (y - 12) ** 2) / 80.0)
    return z


ROAD = [(-31, -14), (-14, -9), (0, -8.5), (14, -6), (31, -2)]


def build(b):
    material('meadow', h('6d9440'), zramp=[(-1, h('6a8f3c')), (2, h('78a046')), (5, h('6b9040'))], noise=0.4)
    material('road', h('a08c68'), h('8c7a5a'), noise=2.0)
    material('cartwood', h('7b5634'), h('6a4829'), noise=4.0)
    material('darkwood', h('3d2c1d'))
    material('crate', h('a8834f'), h('94723f'), noise=5.0)
    material('rune', h('b8302a'))
    material('greyrobe', h('8d8f92'), h('7d7f82'), noise=2.0)
    material('skin', h('d8ad8a'))
    material('beard', h('e8e6e0'))
    material('horse', h('c9c7c2'), h('b5b3ae'), noise=3.0)       # Shadowfax-grey cart horse
    material('mane', h('e8e6e2'))
    material('canvas', h('b7b3a6'), h('a39f92'), noise=3.0)
    material('stone', h('9c978a'), h('878275'), noise=3.0)
    material('rocket', h('c94a2a'), h('2a5aa8'), noise=9.0)
    material('flame', h('ffb040'), emission=4.0, ao=False)
    material('oak', h('486f2c'), h('5a8235'), noise=1.5)
    material('cloth', h('6a7a4a'), h('7a8a58'), noise=3.0)
    material('dragonfw', h('d8442a'), h('f0a030'), noise=6.0, emission=0.4)

    terrain_polar(b, ground, lambda x, y, z, s: 'road' if near_path(x, y, ROAD, 1.8) else 'meadow',
                  R=31, cy=2, nr=36, na=120)

    # --- the cart: bed, wheels, shafts, crates of fireworks
    cx, cy = -1.5, -2.0
    cz = ground(cx, cy)
    box(b, 'cartwood', cx, cy, cz + 1.2, 6.0, 3.0, 0.35)
    for s in (-1, 1):
        box(b, 'cartwood', cx, cy + s * 1.45, cz + 1.55, 6.0, 0.15, 0.7)
    box(b, 'cartwood', cx + 2.95, cy, cz + 1.55, 0.15, 3.0, 0.7)
    for (wx, s) in ((-1.7, -1), (-1.7, 1), (1.7, -1), (1.7, 1)):
        lathe(b, 'darkwood', [(1.05, -0.12), (1.05, 0.12), (0, 0.12)], n=14,
              M=T(cx + wx, cy + s * 1.65, cz + 1.05, rx=90 if s < 0 else -90))
    for s in (-1, 1):
        strut(b, 'cartwood', (cx - 3.0, cy + s * 0.75, cz + 1.4), (cx - 7.2, cy + s * 0.75, cz + 1.6), 0.09, 0.08, n=4)
    for i in range(3):
        for j in range(2):
            for k in range(2 if i != 1 else 3):
                x, y, z = cx - 1.9 + 1.4 * i, cy - 0.6 + 1.2 * j, cz + 1.55 + 0.95 * k
                crate(b, 'crate', x, y, z, s=0.95, rz=b.rng.uniform(-8, 8))
                box(b, 'rune', x, y - 0.49, z + 0.3, 0.42, 0.04, 0.42)
    # the grey horse in the shafts
    horse(b, cx - 6.0, cy, cz, s=1.5, body='horse', mane='mane', rz=90)

    # --- Gandalf, in front of his cart
    gx, gy = 2.8, -6.0
    wizard(b, gx, gy, ground(gx, gy), s=1.45, robe='greyrobe', hat='greyrobe', beard='beard', staff='darkwood')

    # --- rocket racks and the great dragon firework
    for (rx, ry) in ((9.0, 2.0), (11.0, -3.5), (-11.0, 5.0)):
        rz_ = ground(rx, ry)
        for k in range(5):
            strut(b, 'darkwood', (rx - 1.0 + 0.5 * k, ry, rz_), (rx - 1.0 + 0.5 * k, ry + 0.4, rz_ + 2.2), 0.05, 0.05, n=4)
            strut(b, 'rocket', (rx - 1.0 + 0.5 * k, ry + 0.4, rz_ + 2.2), (rx - 1.0 + 0.5 * k, ry + 0.7, rz_ + 3.6), 0.13, 0.0, n=6)
        box(b, 'darkwood', rx, ry + 0.2, rz_ + 1.2, 2.6, 0.12, 0.12)
    # the dragon firework, a red-gold wyrm of sparks rising over the camp
    pts = [Vector((6, 9, 9)), Vector((3, 10, 13)), Vector((-1, 9, 16)), Vector((-5, 8, 17)), Vector((-8, 7.5, 15.5))]
    curve(b, 'dragonfw', [tuple(p) for p in pts], 0.9, 0.15, n=8)
    sphere(b, 'dragonfw', -8.6, 7.4, 15.3, 0.9, n=8, rings=6)
    for sd in (-1, 1):
        plate(b, 'dragonfw', [(0, 0), (sd * 3.2, 1.5), (sd * 4.4, -1.0), (sd * 1.4, -1.2)], 0, 0.12,
              M=T(-1, 9, 15.5, rx=-20))
    fx(b, 'Fireworks_1', (-8.8, 7.0, 16.5), 'FIREWORKS')
    fx(b, 'Fireworks_2', (9.0, 4.0, 14.0), 'FIREWORKS')
    fx(b, 'Fireworks_3', (-12.0, 9.0, 12.0), 'FIREWORKS')
    fx(b, 'Fireworks_4', (11.5, -2.0, 7.0), 'FIREWORKS')

    # --- campfire with the pilgrim's kettle, a pavilion, a ring of stones and a milestone
    fxz = ground(6.5, -10.5)
    campfire(b, 6.5, -10.5, fxz, s=1.6, stone='stone', log='darkwood', flame='flame')
    fx(b, 'Campfire', (6.5, -10.5, fxz + 0.6), 'CAMPFIRE')
    for (x, y) in ((4.5, -12.5), (8.6, -12.0)):
        box(b, 'darkwood', x, y, ground(x, y), 1.5, 0.4, 0.45)
    tent(b, 'canvas', -9.5, -4.5, ground(-9.5, -4.5), r=2.8, h=3.8, n=10, door_mat='darkwood', pole='darkwood')
    for k in range(9):
        a = 2 * math.pi * k / 9
        x, y = 15.0 + 5.0 * math.cos(a), 14.0 + 4.0 * math.sin(a)
        standing_stone(b, 'stone', x, y, ground(x, y) - 0.2, h=2.6 + 0.8 * (k % 3), w=0.75, rz=math.degrees(a))
    box(b, 'stone', -16.0, -13.0, ground(-16, -13) - 0.2, 0.9, 0.5, 1.8)
    # hobbit children watching the show
    for (x, y) in ((-3.5, -9.0), (-2.0, -10.0), (-0.4, -9.4)):
        person(b, x, y, ground(x, y), s=0.62, robe='cloth', skin='skin')

    # --- the old oak and the woods of Eriador
    tree(b, -14.0, 9.0, ground(-14, 9), h=10.0, r=3.6, leaves='oak', trunk='darkwood', crowns=4)
    scatter_forest(b, 46, -31, 31, -29, 33, ground, avoid=((-15, 16, -14, 12), (8, 21, 8, 20)), min_dist=3.2,
                   max_r=30.5, h=(5.5, 8.0), r=(1.8, 2.6), leaves='oak', trunk='darkwood')


PREVIEW = [((4, -30, 14), (0, -2, 5), 45)]
