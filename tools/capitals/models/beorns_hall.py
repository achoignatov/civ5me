"""Beorn's Hall in the Vale of Anduin.

The Hobbit, "Queer Lodgings": "a belt of tall and very ancient oaks ... a tall thorn-hedge",
"a wide gate", "a garden and a cluster of low wooden buildings, some thatched and made of
unshaped tree-trunks: barns, stables, sheds, and a long low wooden house", "great hives
of straw", bees "bigger than hornets", "a wide hall with a fire-place in the middle";
ponies, dogs, sheep and cattle; Beorn himself, a skin-changer who becomes a great black bear.
Modelled: the long hall of tree-trunks with a turf-and-thatch roof and smoke from the
central fire-hole (animated), barns, stables and byres around a yard, the rows of great
straw bee-hives among clover and flowers, the thorn hedge with its wide gate, the belt of
huge oaks, ponies, sheep, a hound, and the great black bear by the hall.
The gate faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, gable, cyl, cone, lathe, terrain_polar, blob, strut, sphere,
                  T, near_path)
from city_common import (longhouse, house, beehive, horse, cow, fx, tree, fence, barrel, crate, person)

CY = 3.0


def ground(x, y):
    z = 0.7 + 0.35 * math.sin(x * 0.3) * math.cos(y * 0.28)
    z += 1.2 * math.exp(-((x) ** 2 + (y - CY) ** 2) / 200.0)
    return z


PATH = [(0, -31), (0, -17), (0, -6)]


def bear(b, x, y, z, s=1.0, rz=0.0):
    M = T(x, y, z, rz=rz, s=s)
    sphere(b, 'bear', 0, 0, 0, 1.0, n=10, rings=7, M=M @ T(0, 0.2, 1.1) @ T(0, 0, 0, s=(0.9, 1.4, 0.85)))
    sphere(b, 'bear', 0, 0, 0, 0.55, n=9, rings=6, M=M @ T(0, -1.35, 1.45))
    sphere(b, 'bear', 0, 0, 0, 0.28, n=7, rings=5, M=M @ T(0, -1.85, 1.35) @ T(0, 0, 0, s=(0.8, 1.2, 0.8)))
    for sd in (-1, 1):
        sphere(b, 'bear', 0, 0, 0, 0.17, n=6, rings=4, M=M @ T(sd * 0.36, -1.35, 1.95))
        for ly in (-0.6, 1.0):
            lathe(b, 'bear', [(0.32, 0), (0.36, 0.7), (0, 0.9)], n=7, M=M @ T(sd * 0.48, ly, 0.0))
    sphere(b, 'beareye', 0, 0, 0, 0.07, n=5, rings=4, M=M @ T(0, -2.1, 1.4))


def build(b):
    material('clover', h('6a9a3e'), zramp=[(-1, h('66963a')), (2, h('74a244'))], noise=0.5)
    material('road', h('8a7654'), h('7a6648'), noise=2.0)
    material('logs', h('6e4a2a'), h('5a3c22'), noise=6.0, courses=0.45, course_dark=0.7)
    material('thatch', h('b0924c'), h('9a7c3e'), noise=3.0)
    material('turf', h('5e7e34'), h('6e8e3c'), noise=4.0)
    material('straw', h('d2b25a'), h('c09e48'), noise=4.0)
    material('thorn', h('2e4a24'), h('3a5a2c'), noise=3.0)
    material('oak', h('3e6428'), h('4e7430'), noise=1.5)
    material('oakbark', h('4a3a2a'))
    material('flower', h('e0d050'), h('c870c0'), noise=10.0)
    material('bear', h('1e1a18'), h('2a2420'), noise=3.0)
    material('beareye', h('e8b040'))
    material('horse', h('9a6a3a'), h('7a5230'), noise=4.0)          # ponies
    material('mane', h('3a2a1e'))
    material('cow', h('e8e4dc'), h('d8d2c6'), noise=3.0)            # sheep
    material('horn', h('6a5a48'))
    material('cloth', h('6a5a3a'), h('7a6a48'), noise=3.0)
    material('skin', h('e0b896'))
    material('stone', h('8a8678'))

    terrain_polar(b, ground, lambda x, y, z, s: 'road' if near_path(x, y, PATH, 1.4) else 'clover',
                  R=31, cy=2, nr=36, na=120)

    # --- the long hall of tree-trunks with its fire-hole
    hz = ground(0, CY + 4) - 0.2
    longhouse(b, 0.0, CY + 4.0, hz, w=16.0, d=6.4, h=3.2, wall='logs', roof='thatch', roof_h=4.0, windows=0,
              porch=True, posts=7, post_mat='oakbark')
    gable(b, 'turf', 0.0, CY + 4.0, hz + 6.5, 4.0, 2.4, 0.9, overhang=0.1)      # louvre over the fire-hole
    fx(b, 'Smoke_Hearth', (0.0, CY + 4.0, hz + 7.8), 'SMOKE')
    for sd in (-1, 1):   # carved bear posts at the doors
        cyl(b, 'oakbark', sd * 1.6, CY + 0.3, hz, 0.3, 3.6, n=8)
        sphere(b, 'bear', sd * 1.6, CY + 0.2, hz + 3.8, 0.38, n=7, rings=5)
    # barns, stables and sheds about the yard
    for (x, y, rz, w, roof) in ((-11.5, CY - 1.0, 80, 7.5, 'thatch'), (11.5, CY - 1.0, -80, 7.5, 'turf'),
                                (-10.0, CY + 11.0, 15, 6.0, 'turf'), (10.5, CY + 11.0, -15, 6.0, 'thatch')):
        longhouse(b, x, y, ground(x, y) - 0.2, w=w, d=3.6, h=2.3, rz=rz, wall='logs', roof=roof, roof_h=2.0,
                  windows=0, porch=False, posts=0)

    # --- the great straw hives in rows among the flowers
    for row in range(3):
        for k in range(6):
            for sd in (-1, 1):
                x, y = sd * (6.5 + 1.9 * k), -8.5 - 2.6 * row
                if math.hypot(x, y - 2) > 27:
                    continue
                beehive(b, 'straw', x, y, ground(x, y), s=1.25)
    for k in range(80):
        x, y = b.rng.uniform(-24, 24), b.rng.uniform(-18, -5)
        if abs(x) < 3:
            continue
        blob(b, 'flower', x, y, ground(x, y) - 0.05, 0.3, n=5, rings=3, squash=0.6)

    # --- the thorn hedge with its wide gate, and the belt of ancient oaks
    for k in range(60):
        a = 2 * math.pi * k / 60
        if abs(math.degrees(a) - 270) < 7:
            continue
        x, y = 21.0 * math.cos(a), CY + 19.0 * math.sin(a)
        blob(b, 'thorn', x, y, ground(x, y) - 0.3, 1.4, n=7, rings=4, squash=1.1, jitter=0.25)
    for sd in (-1, 1):
        cyl(b, 'oakbark', sd * 2.6, CY - 19.0, ground(0, CY - 19) - 0.2, 0.4, 4.0, n=8)
    box(b, 'oakbark', 0, CY - 19.0, ground(0, CY - 19) + 3.8, 6.0, 0.6, 0.5)
    for k in range(26):
        a = 2 * math.pi * (k + 0.5) / 26
        x, y = 26.0 * math.cos(a), CY + 25.0 * math.sin(a) - 1.0
        if math.hypot(x, y - 2) > 30.0:
            x, y = x * 0.95, (y - 2) * 0.95 + 2
        if abs(math.degrees(a) - 270) < 10:
            continue
        tree(b, x, y, ground(x, y) - 0.2, h=b.rng.uniform(8.0, 10.5), r=b.rng.uniform(2.6, 3.2), leaves='oak',
             trunk='oakbark', crowns=3)

    # --- animals and Beorn
    bear(b, 5.5, CY - 2.5, ground(5.5, CY - 2.5), s=1.6, rz=-20)
    for k in range(5):
        x, y = -15.0 + 2.4 * k, CY + 6.5 + (k % 2) * 1.6
        horse(b, x, y, ground(x, y), s=1.05, body='horse', mane='mane', rz=b.rng.uniform(60, 120))
    fence(b, 'oakbark', [(-17.0, CY + 4.5), (-9.0, CY + 4.5)], h=1.1, step=1.6)
    for k in range(7):
        x, y = b.rng.uniform(8, 17), b.rng.uniform(CY + 4, CY + 9)
        cow(b, x, y, ground(x, y), s=0.85, body='cow', horn='horn', rz=b.rng.uniform(0, 360))
    for k in range(3):
        barrel(b, 'logs', -3.5 + 0.9 * k, CY - 1.0, ground(-3.5, CY - 1), 0.42, 0.85)
    person(b, -2.0, -4.0, ground(-2, -4), s=0.6, robe='cloth', skin='skin')       # a visiting hobbit


PREVIEW = [((6, -34, 18), (0, 2, 5), 45)]
