"""Dunland: the hill-country of the Dunlendings west of the Misty Mountains.

The Lord of the Rings / Unfinished Tales: the Dunlendings were "a remnant of the peoples
that had dwelt in the vales of the White Mountains", a wild hill-folk of herdsmen, hostile
to the Rohirrim; their land "a country of hills and dales" at the feet of the mountains.
Films: shaggy, wild-haired men in hides, crude round huts.
Modelled: a hill-fort of the old peoples on a knoll, its earth bank and stake fence, round
huts of wattle and turf with conical thatch, a chieftain's larger round-house with smoke
(animated), a ring of standing stones on the next hill, sheep and goats grazing, fire-pits
(animated), heather and gorse, and the foothills of the Misty Mountains rising behind.
The gate faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, gable, cyl, cone, lathe, terrain_polar, blob, strut, sphere,
                  T, near_path, ring)
from city_common import (round_hut, palisade, gate, standing_stone, campfire, fx, person, cow, dead_tree,
                         scatter_forest, spire)

CX, CY = 0.0, 1.0


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = 0.7 + 0.6 * math.sin(x * 0.3) * math.cos(y * 0.27)
    r = math.hypot(x - CX, (y - CY) / 1.1)
    z += 4.0 * sm((14.0 - r) / 5.0)                                      # the knoll
    z += 5.0 * math.exp(-((x - 19) ** 2 + (y - 12) ** 2) / 50.0)         # stone-circle hill
    if y > 18:                                                          # the foothills behind
        z += 12.0 * sm((y - 18) / 14.0) * (0.75 + 0.25 * math.sin(x * 0.25))
    return z


PATH = [(-4, -31), (-2, -18), (0, -12)]


def build(b):
    material('heath', h('6e7a3c'), zramp=[(-1, h('6a7438')), (3, h('7a7a40')), (8, h('7c7458')), (16, h('8a8682'))],
             slope_color=h('7a705a'), slope_start=0.55, noise=1.2)
    material('road', h('7a6a4a'), h('6a5a3e'), noise=3.0)
    material('daub', h('9a8662'), h('8a7654'), noise=4.0)
    material('thatch', h('8a7440'), h('766234'), noise=3.0)
    material('stake', h('4a3624'), h('3c2b1c'), noise=4.0)
    material('stone', h('8a877c'), h('77746a'), noise=3.0)
    material('gorse', h('8a8a30'), h('c8b030'), noise=8.0)
    material('heather', h('7a4a6a'), h('8a5a7a'), noise=6.0)
    material('hide', h('6a5038'), h('5a4230'), noise=5.0)
    material('skin', h('d8b090'))
    material('cow', h('d8d2c4'), h('c8c0b0'), noise=4.0)              # sheep
    material('horn', h('6a5a48'))
    material('flame', h('ffb040'), emission=4.0, ao=False)
    material('deadwood', h('3a3028'))

    terrain_polar(b, ground, lambda x, y, z, s: 'road' if near_path(x, y, PATH, 1.2) else 'heath',
                  R=31, cy=2, nr=40, na=128)
    TZ = 4.7

    # --- the hill-fort: earth bank, stake fence, gate
    ring(b, 'heath', 11.0, 13.0, TZ - 1.4, 1.6, 0, 360, n=64, x=CX, y=CY)
    palisade(b, 'stake', CX, CY, 12.0, h=2.2, step=1.1, zfn=lambda x, y: TZ + 0.2, gate=270, gate_w=12, rail=None)
    gate(b, 'stake', CX, CY, 12.0, 270, z=TZ, w=2.6, h=3.0)

    # --- the chieftain's round-house and the huts
    cyl(b, 'daub', CX, CY + 2.5, TZ, 4.2, 2.4, n=18)
    cone(b, 'thatch', CX, CY + 2.5, TZ + 2.4, 5.0, 5.2, n=18)
    box(b, 'window', CX, CY + 2.5 - 4.25, TZ, 1.2, 0.1, 1.8)
    strut(b, 'stake', (CX, CY + 2.5, TZ + 7.2), (CX, CY + 2.5, TZ + 8.2), 0.1, 0.05, n=4)
    fx(b, 'Smoke_Chief', (CX, CY + 2.5, TZ + 8.0), 'SMOKE')
    huts = [(-6.5, CY - 3.0), (6.8, CY - 2.5), (-7.5, CY + 4.5), (7.4, CY + 5.0), (-3.5, CY + 8.5), (3.8, CY + 8.8),
            (-3.0, CY - 7.0), (4.0, CY - 7.2)]
    for k, (x, y) in enumerate(huts):
        round_hut(b, x, y, TZ, r=b.rng.uniform(1.6, 2.1), h=1.5, roof_h=2.4, wall='daub', roof='thatch',
                  door_mat='window', n=12)
    fz = TZ
    campfire(b, CX, CY - 3.5, fz, s=1.5, stone='stone', log='stake', flame='flame')
    fx(b, 'Firepit', (CX, CY - 3.5, fz + 0.6), 'CAMPFIRE')
    for (x, y) in ((-1.8, CY - 5.0), (1.9, CY - 4.6), (2.6, CY - 2.6), (-2.4, CY - 2.0)):
        person(b, x, y, TZ, s=0.95, robe='hide', skin='skin')
    # drying hides on frames
    for (x, y) in ((-9.0, CY), (9.2, CY + 1.0)):
        for s in (-1, 1):
            strut(b, 'stake', (x + s * 0.8, y, TZ), (x + s * 0.8, y, TZ + 2.2), 0.06, 0.05, n=4)
        box(b, 'hide', x, y, TZ + 0.8, 1.5, 0.08, 1.3)

    # --- the ring of standing stones on the next hill
    for k in range(11):
        a = 2 * math.pi * k / 11
        x, y = 19.0 + 4.5 * math.cos(a), 12.0 + 4.0 * math.sin(a)
        standing_stone(b, 'stone', x, y, ground(x, y) - 0.3, h=2.4 + (k % 3) * 0.9, w=0.8, rz=math.degrees(a))
    standing_stone(b, 'stone', 19.0, 12.0, ground(19, 12) - 0.3, h=4.4, w=1.1)

    # --- herds, heather and gorse, a few bent thorn trees
    for k in range(14):
        x, y = b.rng.uniform(-26, 26), b.rng.uniform(-26, -12)
        if math.hypot(x, y - 2) > 29 or abs(x + 3) < 3:
            continue
        sp = b.rng.uniform(0.75, 0.95)
        cow(b, x, y, ground(x, y), s=sp, body='cow', horn='horn', rz=b.rng.uniform(0, 360))
    for k in range(70):
        x, y = b.rng.uniform(-30, 30), b.rng.uniform(-29, 25)
        if math.hypot(x, y - 2) > 29.5 or math.hypot(x - CX, y - CY) < 14:
            continue
        blob(b, 'gorse' if k % 2 else 'heather', x, y, ground(x, y) - 0.15, b.rng.uniform(0.5, 1.0), n=6, rings=3,
             squash=0.6, jitter=0.25)
    for (x, y) in ((-20, -6), (22, -4), (-16, 14), (-24, 10)):
        dead_tree(b, 'deadwood', x, y, ground(x, y) - 0.2, h=4.0)
    scatter_forest(b, 18, -31, 31, 16, 33, ground, min_dist=3.0, max_r=30.5, h=(5.0, 7.0), r=(1.4, 1.9),
                   leaves='pine', kind='conifer')
    for (x, y, hh) in ((-12, 26, 7), (2, 29, 6), (13, 27, 7)):
        spire(b, 'stone', x, y, ground(x, y) - 1.0, hh, 3.0)


PREVIEW = [((6, -34, 22), (0, 1, 6), 45)]
