"""The Halls of the Elvenking in northern Mirkwood (Wood Elves).

Book/film features modelled:
  * "a great cave... a hill whose sides were covered with trees" in the eastern edge of
    Mirkwood: the Elvenking's halls delved into a forested hill;
  * the Forest River flowing past the hill's foot, crossed by the narrow stone bridge
    that is the only way to the great doors (book); the film's tall carved gate of pale
    stone with branching, tree-like arches;
  * the dense forest of great beeches and oaks of the Woodland Realm, dark Mirkwood
    firs behind;
  * the barrels drifting down the river from the water-gate (The Hobbit).
"""
import math

from blib import (material, hexcol as h, box, ring, cyl, cone, lathe, terrain_polar, blob, strut, curve, prism, tree,
                  conifer, T)

RIVER_Y = -9.5


def ground(x, y):
    z = 1.0 + 0.5 * math.sin(x * 0.3) * math.sin(y * 0.35)
    r = math.hypot(x / 1.3, (y - 9) / 1.0)
    z += 22.0 * math.exp(-(r / 13.0) ** 2)            # the Elvenking's hill
    if y < 0.5 and abs(x) < 7.0:                       # the cut terrace before the doors
        z = min(z, 1.6 + 0.0 * x)
    d = abs(y - RIVER_Y)                               # river channel
    if d < 3.2:
        z = min(z, -0.6 + 0.25 * d * d)
    return z


def build(b):
    material('elfcarve', h('b9b6a5'), h('a9a693'), noise=2.0, courses=0.9, course_dark=0.88)
    material('woodland', h('4f6b31'), zramp=[(-1, h('46603a')), (1, h('557236')), (10, h('4e6a30')), (22, h('48622c'))],
             slope_color=h('6d6a5d'), slope_start=0.55)
    material('beech', h('5f8a34'), h('77a03f'), noise=1.5)
    material('beechgold', h('9aa03a'), h('c2a83a'), noise=1.5)
    material('mirkfir', h('22371f'), h('2b4426'), noise=1.5)
    material('greybark', h('8a8a80'))
    material('forestriver', h('3b5e57'), h('4a7068'), noise=1.5, ao=False)
    material('barrel', h('7a5432'), h('5e3f24'), noise=6.0, courses=0.25, course_dark=0.6)
    material('gatedark2', h('1a1712'))

    terrain_polar(b, ground, lambda x, y, z, s: 'woodland', R=31, cy=2, nr=34, na=110)
    box(b, 'forestriver', 0, RIVER_Y, -0.4, 49, 5.8, 0.5)

    # --- the carved gate in the hill's face (pale stone, branching tree-arches)
    gy = 0.5
    prism(b, 'elfcarve', [(-7.5, gy), (7.5, gy), (7.5, gy + 6.0), (-7.5, gy + 6.0)], 1.0, 14.5)
    box(b, 'gatedark2', 0, gy - 0.05, 1.6, 4.2, 0.2, 9.0)
    # pointed arch over the doors
    for s in (-1, 1):
        curve(b, 'elfcarve', [(s * 2.6, gy - 0.4, 1.6), (s * 2.6, gy - 0.4, 8.4), (s * 1.8, gy - 0.4, 10.6),
                              (0.0, gy - 0.4, 12.0)], 0.45, 0.35, n=5, smooth=False)
    # tree-like carved pillars branching across the face
    for s in (-1, 1):
        x = s * 5.0
        curve(b, 'elfcarve', [(x, gy - 0.5, 1.6), (x * 1.02, gy - 0.5, 6.0), (x * 0.95, gy - 0.5, 10.0)], 0.55, 0.4, n=6,
              smooth=False)
        for (zz, dx, dz) in ((7.0, -1.8, 3.0), (9.0, 1.4, 3.6), (10.0, -0.6, 4.2), (5.5, 1.8, 2.0)):
            strut(b, 'elfcarve', (x, gy - 0.5, zz), (x + s * dx * -1, gy - 0.5, zz + dz), 0.25, 0.1, n=5)
    # steps up to the doors
    for i in range(4):
        box(b, 'elfcarve', 0, gy - 0.6 - 0.5 * i, 1.6 - 0.3 * (i + 1), 5.0 + 0.4 * i, 0.5, 0.3)

    # --- the narrow stone bridge over the Forest River to the doors
    for i in range(12):
        t = i / 11
        y = gy - 2.6 - 9.0 * t
        z = 1.6 + 1.3 * math.sin(math.pi * t) - 0.3 * t
        box(b, 'elfcarve', 0, y, z - 0.45, 2.0, 0.85, 0.55)
    for y in (RIVER_Y - 2.2, RIVER_Y + 2.2):
        box(b, 'elfcarve', 0, y, -1.0, 1.4, 0.8, 2.4)

    # --- barrels drifting down the river
    for x in (-14.0, -11.5, 9.0):
        lathe(b, 'barrel', [(0, 0), (0.42, 0), (0.55, 0.45), (0.42, 0.9), (0, 0.9)], n=8, M=T(x, RIVER_Y + 0.6, -0.05, rz=20, ry=90),
              smooth=True)

    # --- the forest: great beeches (grey trunks), golden-green crowns, dark firs behind
    rng = b.rng
    placed = []
    for k in range(400):
        if len(placed) >= 70:
            break
        x, y = rng.uniform(-28, 28), rng.uniform(-25, 30)
        if math.hypot(x, y - 2) > 29.5:
            continue
        if abs(y - RIVER_Y) < 3.6:
            continue
        if abs(x) < 9.0 and -13 < y < 6.5:
            continue
        if any(math.hypot(x - px, y - py) < 2.9 for px, py in placed):
            continue
        placed.append((x, y))
        z = ground(x, y) - 0.2
        if y > 14 and rng.random() < 0.55:
            conifer(b, x, y, z, h=7.0, r=1.7, leaves='mirkfir', tiers=3)
        else:
            hgt = rng.uniform(5.0, 7.5)
            cyl(b, 'greybark', x, y, z, 0.3, hgt * 0.6, n=6, r2=0.2)
            for c in range(3):
                blob(b, rng.choice(['beech', 'beech', 'beechgold']), x + rng.uniform(-0.8, 0.8),
                     y + rng.uniform(-0.8, 0.8), z + hgt * 0.45 + c * 0.6, rng.uniform(1.6, 2.2), n=7, rings=4)


PREVIEW = [((6, -24, 16), (0, 0, 7), 45)]
