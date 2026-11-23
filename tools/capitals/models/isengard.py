"""Isengard: the tower of Orthanc inside the Ring of Isengard.

Book/film features modelled:
  * the Ring: a great circular wall of black rock with a single gate in the south,
    an avenue of stone pillars joined by chains running to the tower;
  * Orthanc in the middle: "a peak and isle of rock, black and gleaming hard": four
    mighty piers of many-sided stone welded into one, which near the summit open into
    gaping horns, their pinnacles sharp as spear-points, keen-edged as knives; a flat
    platform between them; a long stair up to its door;
  * Saruman's industry (films): the green plain torn up into pits and furnaces glowing
    with fire, smoke-blackened mud, felled stumps; the trees of Fangorn outside the wall.
"""
import math

from blib import (material, hexcol as h, box, ring, cyl, cone, lathe, terrain_polar, blob, strut, curve, tree,
                  crenels, prism)

RING_R = 23.0


def ground(x, y):
    r = math.hypot(x, y)
    if r < RING_R - 1.5:
        z = 0.4 + 0.25 * math.sin(x * 0.9) * math.sin(y * 0.7)
        return z
    if r < RING_R + 3.5:
        return 0.4 + 6.5 * math.sin(min(1.0, (r - (RING_R - 1.5)) / 5.0) * math.pi) ** 0.6
    return 0.6 + 0.6 * math.sin(x * 0.3 + y * 0.2)


def build(b):
    material('orthanc', h('1c1d22'), h('2a2c33'), noise=2.5)
    material('ringrock', h('2f2d2c'), h('403d3a'), noise=1.8)
    material('mud', h('3d3328'), h('4a3d2e'), noise=1.2)
    material('fire', h('ffb32e'), h('ff7a12'), noise=3.0)
    material('ember', h('c2410f'), h('8c2a0c'), noise=3.0)
    material('pillar', h('3a3a3e'))
    material('chain', h('222225'))
    material('scaffold', h('5e4632'))
    material('stump', h('6b5236'))
    material('steps', h('2b2c31'), h('35363c'), noise=3.0)

    def mat(x, y, z, s):
        r = math.hypot(x, y)
        if r > RING_R + 3.6:
            return 'grass'
        if r > RING_R - 1.4:
            return 'ringrock'
        return 'mud'
    terrain_polar(b, ground, mat, R=31, nr=34, na=110)

    # --- the Ring wall: black rock, flat walkway, gate in the south
    for seg in ((-76, 256),):
        ring(b, 'ringrock', RING_R - 0.8, RING_R + 1.2, 0.0, 6.6, seg[0], seg[1], n=120)
        crenels(b, 'ringrock', RING_R + 1.0, 6.6, seg[0] + 1, seg[1] - 1, size=0.5, h=0.5, step=1.4, depth=0.4)
    # gate towers and the dark arch
    for s in (-1, 1):
        a = math.radians(270 + s * 8.5)
        x, y = RING_R * math.cos(a), RING_R * math.sin(a)
        box(b, 'ringrock', x, y, 0, 3.0, 3.0, 8.0, rz=270 + s * 8.5 + 90)
        crenels(b, 'ringrock', 1.6, 8.0, 0, 360, size=0.45, h=0.45, step=1.0, x=x, y=y, depth=0.4)
    box(b, 'iron', 0, -RING_R + 0.3, 0, 5.5, 0.5, 5.0)
    box(b, 'ringrock', 0, -RING_R, 5.0, 6.5, 2.0, 1.6)

    # --- avenue of pillars with chains from the gate to the tower
    pts = []
    for i in range(6):
        y = -RING_R + 3.0 + i * 2.6
        for s in (-1, 1):
            x = s * 2.2
            cyl(b, 'pillar', x, y, 0.2, 0.28, 3.2, n=6)
            pts.append((x, y))
    for s in (-1, 1):
        for i in range(5):
            y0 = -RING_R + 3.0 + i * 2.6
            x = s * 2.2
            curve(b, 'chain', [(x, y0, 3.1), (x, y0 + 1.3, 2.3), (x, y0 + 2.6, 3.1)], 0.07, 0.07, n=4)

    # --- pits and furnaces of the industrialised plain
    rng = b.rng
    pits = []
    for k in range(60):
        if len(pits) >= 13:
            break
        a = rng.uniform(0, 360)
        r = rng.uniform(9.0, RING_R - 4.0)
        x, y = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
        if abs(x) < 4.0 and y < 0:
            continue
        if any(math.hypot(x - px, y - py) < 4.8 for px, py in pits):
            continue
        pits.append((x, y))
        pr = rng.uniform(1.3, 2.1)
        ring(b, 'ember', pr, pr + 0.55, 0.15, 0.55, 0, 360, n=14, x=x, y=y)
        ring(b, 'fire', 0.05, pr, 0.45, 0.02, 0, 360, n=14, x=x, y=y, inner=False)
        # crane / scaffold beside some pits
        if rng.random() < 0.6:
            hx, hy = x + pr + 0.9, y
            for dx, dy in ((-0.4, -0.4), (0.4, -0.4), (0.4, 0.4), (-0.4, 0.4)):
                strut(b, 'scaffold', (hx + dx, hy + dy, 0.3), (hx + dx * 0.4, hy + dy * 0.4, 3.6), 0.07, 0.07, n=4)
            strut(b, 'scaffold', (hx, hy, 3.6), (hx - pr - 0.6, hy, 4.4), 0.07, 0.07, n=4)
        # furnace chimney
        if rng.random() < 0.5:
            cx, cy = x - pr - 0.7, y + 0.4
            cyl(b, 'ringrock', cx, cy, 0.3, 0.45, 3.0, n=7, r2=0.3)
            ring(b, 'ember', 0.2, 0.32, 3.3, 0.06, 0, 360, n=7, x=cx, y=cy)
    for k in range(18):
        a = rng.uniform(0, 360)
        r = rng.uniform(6, RING_R - 2)
        x, y = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
        if any(math.hypot(x - px, y - py) < 2.8 for px, py in pits) or (abs(x) < 3.5 and y < 0):
            continue
        cyl(b, 'stump', x, y, 0.2, 0.32, 0.6, n=6)

    # --- Orthanc
    base_z = 0.3
    # broad stepped base and the stair (27 steps) on the south side
    lathe(b, 'steps', [(7.5, 0), (7.5, 0.6), (6.6, 0.6), (6.6, 1.2), (5.8, 1.2), (5.8, 1.8), (0, 1.8)], n=8,
          z=base_z - 0.2, smooth=False)
    for i in range(10):
        box(b, 'steps', 0, -7.6 - 0.55 * (9 - i) + 0.0, base_z - 0.2 + 0.0, 2.6, 0.6, 0.5 + 0.35 * i)
    top = 48.0

    # four piers of many-sided stone welded into one: a fluted core + four outer shafts
    lathe(b, 'orthanc', [(4.2, 0), (3.8, 4.0), (3.4, top - 6.0), (3.6, top - 3.0), (0, top - 3.0)], n=12,
          z=base_z + 1.8, smooth=False)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        ox, oy = math.cos(a), math.sin(a)
        # shaft
        lathe(b, 'orthanc', [(2.5, 0), (2.25, 6.0), (1.95, top - 6.0), (2.1, top - 2.0)], n=7,
              x=ox * 3.1, y=oy * 3.1, z=base_z + 1.8, smooth=False)
        # horn: opens outward then sweeps up to a knife-sharp point
        zz = base_z + 1.8 + top - 2.0
        p = [(ox * 3.1, oy * 3.1, zz), (ox * 4.3, oy * 4.3, zz + 3.0), (ox * 5.3, oy * 5.3, zz + 6.5),
             (ox * 5.5, oy * 5.5, zz + 9.5), (ox * 4.9, oy * 4.9, zz + 12.5), (ox * 4.2, oy * 4.2, zz + 14.0)]
        curve(b, 'orthanc', p, 2.1, 0.0, n=5, smooth=False)
        # smaller blade between the horns
        a2 = math.radians(90 * k)
        strut(b, 'orthanc', (math.cos(a2) * 3.6, math.sin(a2) * 3.6, zz - 2.0),
              (math.cos(a2) * 4.6, math.sin(a2) * 4.6, zz + 4.5), 0.8, 0.0, n=4)
        # ribs down the piers
        for zr in (12.0, 24.0, 36.0):
            ring(b, 'orthanc', 1.9, 2.5, base_z + zr, 0.5, 0, 360, n=7, x=ox * 3.1, y=oy * 3.1)
    # flat platform between the horns (Saruman's summit)
    ring(b, 'steps', 0.05, 3.9, base_z + 1.8 + top - 3.0, 0.3, 0, 360, n=12, inner=False)
    # door and a lit window high on the south face
    box(b, 'iron', 0, -4.05, base_z + 1.8, 1.4, 0.3, 3.2)
    box(b, 'fire', 0, -3.45, base_z + 1.8 + top - 10.0, 0.6, 0.2, 1.2)
    box(b, 'fire', 0, -3.55, base_z + 1.8 + top - 20.0, 0.5, 0.2, 1.0)

    # --- Fangorn's eaves outside the wall (to the north-west)
    for (x, y) in ((-26, 10), (-24, 15), (-20, 20), (-27, 4), (-15, 24), (25, 12), (22, 18)):
        tree(b, x, y, ground(x, y) - 0.2, h=5.5, r=2.0)


PREVIEW = [((16, -30, 64), (0, 0, 52), 45)]
