"""Rhosgobel, the home of Radagast the Brown on the western eaves of Mirkwood.

Books: Radagast "dwelt at Rhosgobel, near the borders of Mirkwood", a friend of beasts and
birds. Films (The Hobbit): a ramshackle wooden cottage with a mossy, overgrown roof and a
great tree growing up right through it, birdhouses everywhere, his sledge drawn by the
Rhosgobel rabbits, mushrooms and the dark trunks of Mirkwood all around.
Modelled: the cottage with the tree through its roof in a mossy clearing, a stone chimney
with smoke, birdhouses on poles, the rabbit sledge, a herb garden, Radagast with his staff,
and the gloomy, cobwebbed trees of Mirkwood closing in at the back.
The door faces the camera (-Y).
"""
import math

from mathutils import Vector

from blib import (material, hexcol as h, box, gable, cyl, cone, lathe, terrain_polar, blob, strut, sphere,
                  curve, T, near_path)
from city_common import (fence, birdhouse, wizard, scatter_forest, fx, plate, web, house, barrel)


def ground(x, y):
    z = 0.5 + 0.35 * math.sin(x * 0.45) * math.cos(y * 0.4)
    z += 1.6 * math.exp(-((x + 16) ** 2 + (y - 14) ** 2) / 60.0) + 1.3 * math.exp(-((x - 18) ** 2 + (y - 10) ** 2) / 50)
    return z


def rabbit(b, x, y, z, s=1.0, rz=0.0):
    M = T(x, y, z, rz=rz, s=s)
    sphere(b, 'rabbit', 0, 0, 0, 0.5, n=8, rings=6, M=M @ T(0, 0.1, 0.45) @ T(0, 0, 0, s=(0.8, 1.2, 0.9)))
    sphere(b, 'rabbit', 0, -0.55, 0.85, 0.28, n=8, rings=5, M=M)
    for sd in (-1, 1):
        strut(b, 'rabbit', tuple(M @ Vector((sd * 0.1, -0.5, 1.05))),
              tuple(M @ Vector((sd * 0.16, -0.42, 1.65))), 0.07, 0.04, n=4)
    sphere(b, 'rabbittail', 0, 0.62, 0.55, 0.14, n=6, rings=4, M=M)


def build(b):
    material('moss', h('51702c'), zramp=[(-1, h('4c6a2a')), (2, h('5a7a30'))], noise=2.0)
    material('road', h('6e5a3e'), h('5e4c33'), noise=3.0)
    material('oldwood', h('6a5134'), h('5a4329'), noise=5.0)
    material('darkwood', h('3c2c1e'), h('2e2217'), noise=4.0)
    material('mossroof', h('5f7a33'), h('6f8a3c'), noise=6.0)
    material('stone', h('8a8577'), h('76716a'), noise=3.0, courses=0.4, course_dark=0.8)
    material('mirk', h('243820'), h('2e4426'), noise=1.5)
    material('mirkbark', h('2b241d'))
    material('bigtree', h('4d3d2b'), h('5c4a34'), noise=5.0)
    material('crown', h('3f6328'), h('4c7330'), noise=1.5)
    material('mushroom', h('c9b8a0'), h('d8c8ae'), noise=3.0)
    material('redcap', h('a8382c'), h('c04a3a'), noise=6.0)
    material('greyrobe', h('6a5236'), h('5c4630'), noise=3.0)      # Radagast's brown robe
    material('skin', h('d6a985'))
    material('beard', h('d7d2c6'))
    material('rabbit', h('9a8466'), h('8a7458'), noise=4.0)
    material('rabbittail', h('e8e2d6'))
    material('web', h('d8dcdc'), ao=False)
    material('window', h('f0c060'), emission=1.0)
    material('herb', h('6b8a3a'), h('8a9a4a'), noise=6.0)
    material('flower', h('c070b0'), h('e0d060'), noise=9.0)

    PATH = [(0, -31), (1, -18), (0, -8), (0, -4)]
    terrain_polar(b, ground, lambda x, y, z, s: 'road' if near_path(x, y, PATH, 1.3) else 'moss',
                  R=31, cy=2, nr=36, na=120)

    # --- the cottage: crooked walls of old timber, a lean-to, mossy roofs
    hz = ground(0, 2) - 0.1
    box(b, 'stone', 0, 2.0, hz - 0.3, 11.2, 7.2, 0.6)
    box(b, 'oldwood', 0, 2.0, hz + 0.3, 10.0, 6.0, 3.6, rz=2)
    gable(b, 'mossroof', 0, 2.0, hz + 3.9, 10.6, 6.6, 3.6, rz=2, overhang=0.7)
    box(b, 'oldwood', 6.5, 3.2, hz + 0.3, 3.4, 4.0, 2.4, rz=-6)        # lean-to
    gable(b, 'mossroof', 6.5, 3.2, hz + 2.7, 3.8, 4.4, 1.4, rz=84, overhang=0.4)
    for k in range(9):                                               # moss clumps on the roof
        blob(b, 'mossroof', b.rng.uniform(-4.5, 4.5), b.rng.uniform(0.2, 3.6), hz + 4.6 + b.rng.uniform(0, 1.6),
             b.rng.uniform(0.6, 1.1), n=7, rings=4, squash=0.5)
    # round door and lit windows
    lathe(b, 'darkwood', [(1.0, 0), (1.0, 0.12), (0, 0.12)], n=14, M=T(-1.2, -1.05, hz + 1.25, rx=90))
    for x in (1.6, 3.6, -3.7):
        box(b, 'window', x, -1.04, hz + 1.6, 0.8, 0.1, 0.9)
        box(b, 'darkwood', x, -1.1, hz + 1.55, 1.0, 0.1, 0.1)
    # the stone chimney
    box(b, 'stone', -4.6, 3.2, hz, 1.3, 1.3, 9.0)
    fx(b, 'Smoke', (-4.6, 3.2, hz + 9.6), 'SMOKE')
    # the great tree growing through the house
    tx, ty = 1.6, 3.2
    lathe(b, 'bigtree', [(1.7, 0), (1.25, 1.5), (1.0, 6.0), (0.9, 10.5), (0, 11.0)], n=10, x=tx, y=ty, z=hz,
          smooth=False, jitter=0.08)
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        p0 = (tx, ty, hz + 8.5 + 0.4 * k)
        p1 = (tx + 4.5 * math.cos(a), ty + 4.0 * math.sin(a), hz + 11.0 + 0.6 * (k % 3))
        strut(b, 'bigtree', p0, p1, 0.45, 0.15, n=6)
        blob(b, 'crown', p1[0], p1[1], p1[2] - 0.6, 2.4, n=8, rings=5, squash=0.7)
    blob(b, 'crown', tx, ty, hz + 12.0, 3.4, n=10, rings=6, squash=0.7)
    for k in range(5):   # roots spilling over the stone footing
        a = 2 * math.pi * k / 5
        strut(b, 'bigtree', (tx, ty, hz + 1.5), (tx + 2.6 * math.cos(a), ty + 2.6 * math.sin(a), hz - 0.2), 0.45, 0.1, n=5)

    # --- birdhouses all around, a herb garden and a fence
    for (x, y, hh) in ((-7.5, -3.0, 2.8), (-9.0, 1.5, 3.4), (8.6, -2.6, 3.0), (10.2, 6.5, 2.4), (-6.0, 8.5, 3.2),
                       (4.0, -6.0, 2.2)):
        birdhouse(b, 'oldwood', 'darkwood', x, y, ground(x, y), h=hh, s=1.3)
    for row in range(4):
        for k in range(7):
            x, y = -12.5 + k * 1.0, -6.5 + row * 1.0
            blob(b, 'herb' if (k + row) % 3 else 'flower', x, y, ground(x, y), 0.42, n=6, rings=3, squash=0.8)
    fence(b, 'darkwood', [(-14.0, -8.0), (-5.5, -8.0), (-5.5, -2.0)], h=1.1, step=1.4)

    # --- Radagast and his rabbit sledge
    wizard(b, 3.0, -5.0, ground(3, -5), s=1.25, robe='greyrobe', hat='greyrobe', beard='beard', staff='darkwood')
    sx, sy = 9.5, -9.5
    sz = ground(sx, sy)
    box(b, 'oldwood', sx, sy + 1.5, sz + 0.35, 2.0, 3.6, 0.35)
    for s in (-1, 1):
        curve(b, 'darkwood', [(sx + s * 0.9, sy + 3.2, sz + 0.1), (sx + s * 0.9, sy - 0.2, sz + 0.1),
                              (sx + s * 0.9, sy - 0.6, sz + 0.7)], 0.08, 0.08, n=4)
    barrel(b, 'oldwood', sx, sy + 2.4, sz + 0.7, 0.4, 0.7)
    for k in range(4):
        for s in (-1, 1):
            rabbit(b, sx + s * 0.9, sy - 2.0 - 1.6 * k, sz, s=1.0)

    # --- mushrooms, cobwebs and the dark wood of Mirkwood at the back
    for k in range(26):
        x, y = b.rng.uniform(-20, 20), b.rng.uniform(-14, 12)
        if abs(x) < 7 and -3 < y < 8:
            continue
        z = ground(x, y)
        cyl(b, 'mushroom', x, y, z, 0.12, 0.45, n=6)
        sphere(b, 'redcap' if k % 3 else 'mushroom', x, y, z + 0.45, 0.32, n=8, rings=4, squash=0.55)
    scatter_forest(b, 70, -31, 31, 6, 33, ground, avoid=((-8, 9, -2, 9),), min_dist=2.4, max_r=30.5,
                   h=(7.0, 11.0), r=(1.6, 2.5), leaves='mirk', trunk='mirkbark', pines=0.0)
    scatter_forest(b, 34, -31, 31, -29, 6, ground, avoid=((-15, 15, -12, 9),), min_dist=3.0, max_r=30.5,
                   h=(6.0, 9.0), r=(1.5, 2.2), leaves='crown', trunk='mirkbark')
    for (x, y) in ((-15.0, 12.0), (14.0, 13.5)):
        web(b, 'web', (x, y, ground(x, y) + 3.2), (1, 0.2, 0), (0, 0, 1), r=2.2, n=10, rings=3)


PREVIEW = [((6, -30, 16), (2, 0, 4), 45)]
