"""Shelob's Lair (Torech Ungol) in the pass of Cirith Ungol.

The Two Towers: the stair climbs the Ephel Dúath to "a black opening ... a great cave",
Torech Ungol, full of "a stench" and webs; Shelob, "most like a spider, but huger than the
great hunting beasts", with "clustered eyes" that shone; above the pass stood the Tower of
Cirith Ungol. Everything black and jagged, the red glow of Mordor beyond.
Modelled: jagged black crags of the Mountains of Shadow with the dark tunnel mouth, webs
strung across the rocks, bones and husks of prey, Shelob herself crouched before her lair
with glowing red eyes (animated), the winding stair, and the small orc tower of Cirith
Ungol on the ridge.
The lair faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, gable, cyl, cone, lathe, terrain_polar, blob, strut, sphere,
                  T, near_path, curve, crenels)
from city_common import (spider, web, fx, spire, dead_tree)


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = 0.8 + 0.6 * math.sin(x * 0.5) * math.cos(y * 0.45)
    # the mountains close in at the sides and behind: a pass climbing to the lair
    z += 8.0 * sm((abs(x) - 10.0) / 12.0) + 9.0 * sm((y - 6.0) / 16.0)
    return z


STAIR = [(2, -31), (-1, -20), (2, -12), (0, -5)]


def build(b):
    material('blackrock', h('2e2c2a'), zramp=[(-1, h('35322e')), (4, h('2c2a28')), (14, h('3a3634'))],
             slope_color=h('24221f'), slope_start=0.45, noise=1.5)
    material('stair', h('4a4642'), h('3e3a36'), noise=2.0)
    material('crag', h('2a2826'), h('353230'), noise=3.0)
    material('spider', h('1c1a18'), h('2a2420'), noise=3.0, spec=0.6, refl=25)
    material('spiderleg', h('241f1c'))
    material('spidereye', h('ff3020'), emission=2.5, ao=False)
    material('web', h('d8dcdc'), h('b8bcbc'), noise=2.0, ao=False)
    material('bone', h('c8c0aa'), h('b8ae98'), noise=3.0)
    material('husk', h('a8a294'), h('988f80'), noise=4.0)
    material('towerstone', h('4a4744'), h('3c3936'), noise=2.0, courses=0.6, course_dark=0.85)
    material('deadwood', h('1e1c1a'))

    terrain_polar(b, ground, lambda x, y, z, s: 'stair' if near_path(x, y, STAIR, 1.1) and z < 6 else 'blackrock',
                  R=31, cy=2, nr=40, na=130)
    # the stair: steps along the path
    for k in range(18):
        t = k / 17
        i = min(len(STAIR) - 2, int(t * (len(STAIR) - 1)))
        u = t * (len(STAIR) - 1) - i
        x = STAIR[i][0] + (STAIR[i + 1][0] - STAIR[i][0]) * u
        y = STAIR[i][1] + (STAIR[i + 1][1] - STAIR[i][1]) * u
        box(b, 'stair', x, y, ground(x, y) - 0.3, 2.2, 0.8, 0.45)

    # --- the cave mouth: a dark maw between leaning crags
    CY = 7.0
    lathe(b, 'window', [(0, 0), (5.0, 0), (5.0, 0.3), (0, 0.3)], n=22, a0=0, a1=180, M=T(0, CY, 2.0, rx=90))
    box(b, 'window', 0, CY - 0.15, 0.0, 10.0, 0.3, 2.0)
    for s in (-1, 1):
        for k in range(4):
            spire(b, 'crag', s * (5.5 + 1.6 * k), CY + 0.5 + k, 0.0, 9.0 + 3.0 * k, 2.4, lean=s * -8, jitter=0.22)
    blob(b, 'crag', 0, CY + 3.0, 7.0, 7.0, n=10, rings=6, squash=0.6, jitter=0.25)
    # webs across the cave mouth and between the crags
    web(b, 'web', (0, CY - 0.6, 3.6), (1, 0, 0), (0, 0, 1), r=4.2, n=12, rings=4)
    for (x, y, z, r) in ((-8.0, 2.0, 4.0, 3.0), (8.5, 3.0, 4.5, 3.2), (-5.0, -6.0, 3.0, 2.4), (6.0, -9.0, 3.5, 2.6),
                         (-12.0, -3.0, 6.0, 2.8), (12.0, -2.0, 6.5, 2.8)):
        web(b, 'web', (x, y, ground(x, y) + z), (1, 0.3, 0), (0, 0, 1), r=r, n=10, rings=3)
    for k in range(14):   # strands from rock to rock
        x0, y0 = b.rng.uniform(-14, -4), b.rng.uniform(-12, 6)
        x1, y1 = b.rng.uniform(4, 14), b.rng.uniform(-12, 6)
        strut(b, 'web', (x0, y0, ground(x0, y0) + 2.0), (x1, y1, ground(x1, y1) + 2.5), 0.03, 0.03, n=3)

    # --- Shelob before her lair
    spider(b, 0.0, -1.0, ground(0, -1) - 0.2, s=3.4, body='spider', leg='spiderleg', eye='spidereye')
    fx(b, 'Eyes', (0.0, -1.0 - 0.78 * 3.4, ground(0, -1) + 1.02 * 3.4), 'RED_EYES')
    # the husks of her prey wrapped in silk, and bones
    for (x, y) in ((-4.5, -4.0), (4.8, -3.0), (-6.0, 1.5), (3.0, -8.0)):
        z = ground(x, y)
        sphere(b, 'husk', x, y, z + 0.6, 0.5, n=8, rings=6, M=T(x, y, z + 0.6, ry=70) @ T(-x, -y, -z - 0.6),
               squash=2.0)
    for k in range(12):
        x, y = b.rng.uniform(-9, 9), b.rng.uniform(-14, 2)
        z = ground(x, y)
        curve(b, 'bone', [(x, y, z + 0.1), (x + 0.6, y + 0.3, z + 0.4), (x + 1.2, y, z + 0.1)], 0.09, 0.06, n=4)
    for (x, y) in ((-3.5, -14.0), (4.0, -18.0), (-6.0, -22.0)):
        dead_tree(b, 'deadwood', x, y, ground(x, y) - 0.2, h=3.0, r=0.15)

    # --- the tower of Cirith Ungol on the ridge
    tx, ty = 10.5, 12.5          # on the ridge above the pass, clear of the tile edge
    tz = ground(tx, ty) - 0.5
    box(b, 'towerstone', tx, ty, tz, 5.0, 4.0, 5.0)
    box(b, 'towerstone', tx - 0.5, ty + 0.3, tz + 5.0, 3.6, 3.0, 4.0)
    box(b, 'towerstone', tx - 0.9, ty + 0.5, tz + 9.0, 2.4, 2.0, 3.5)
    crenels(b, 'towerstone', 1.5, tz + 12.5, 0, 360, size=0.4, h=0.5, step=0.9, x=tx - 0.9, y=ty + 0.5, depth=0.35)
    box(b, 'spidereye', tx - 0.9, ty - 0.52, tz + 10.5, 0.4, 0.1, 0.6)
    fx(b, 'TowerTorch', (tx - 0.9, ty - 0.8, tz + 13.2), 'TORCH')


PREVIEW = [((4, -32, 18), (0, 0, 5), 45)]

# Torech Ungol's crags fill the tile; the lair itself is laid out in ~18 units; scaled to fill the tile (pipeline FILL)
FILL = 1.3
