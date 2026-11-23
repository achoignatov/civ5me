"""Dorwinion, the land of wine in the vales of the Celduin.

Book/film features modelled:
  * the fertile, south-facing slopes northwest of the Sea of Rhûn, cut into terraces
    and planted with long rows of vines;
  * a prosperous manor of white plaster and red tiles, with an arched porch, a
    courtyard and a wine press;
  * a stone winery with great barrels, vats and a hoard of amphorae;
  * gardens, cypress trees and flowers, a stream in front and a blue strip of the
    Sea of Rhûn on the horizon;
  * a few workers with baskets among the vines.
The estate faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, gable, hipped, cyl, cone, lathe, terrain_polar, blob,
                  strut, ring, window_row, sphere, T, near_path)
from city_common import house, longhouse, barrel, crate, person, fence, plate, fx, boat


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = 1.0 + 0.6 * math.sin(x * 0.22) * math.cos(y * 0.28)
    # vineyard hills left and right
    z += 4.2 * math.exp(-((x + 17.0) ** 2 + (y - 5.0) ** 2) / 110.0)
    z += 3.8 * math.exp(-((x - 17.0) ** 2 + (y - 2.0) ** 2) / 95.0)
    # the stream in front
    if -12.5 < y < -7.0:
        z = min(z, -0.55 + 0.14 * abs(y + 9.7))
    # the shore of the Sea of Rhûn at the far back
    if y > 21.0:
        z = min(z, -0.35)
    return z


def vine(b, x, y, z, s=1.0):
    cyl(b, 'wood', x, y, z, 0.07 * s, 1.5 * s, n=4, top=False)
    # two full leaf masses and two hanging bunches (enough to read as a dense row from above)
    for k in range(2):
        blob(b, 'vine', x + b.rng.uniform(-0.4, 0.4) * s, y + b.rng.uniform(-0.4, 0.4) * s,
             z + 1.15 * s + 0.3 * k * s, 0.62 * s, n=6, rings=4, squash=0.8)
    for k in range(2):
        sphere(b, 'grape', x + b.rng.uniform(-0.35, 0.35) * s, y + b.rng.uniform(-0.35, 0.35) * s,
               z + 1.2 * s + 0.25 * k * s, 0.13 * s, n=5, rings=3)


def build(b):
    material('dorngrass', h('7c9448'), zramp=[(-1, h('7d944b')), (2, h('8a9c50')), (8, h('7d9047'))],
             slope_color=h('8a8068'), slope_start=0.55)
    material('vine', h('4e7a2f'), h('5f8d38'), noise=2.0)
    material('grape', h('5a3a6a'), h('7a4a7a'), noise=4.0)
    material('plaster', h('e2d6bb'), h('d2c4a7'), noise=2.5)
    material('terracotta', h('a45a3d'), h('8e4a33'), noise=3.0)
    material('stonetile', h('b7ab92'), h('a39780'), noise=2.0, courses=0.5, course_dark=0.85)
    material('wood', h('6c4b2d'), h('5a3d24'), noise=4.0)
    material('window', h('2a2118'))
    material('flower', h('d06a6a'), h('e0b84a'), noise=8.0)
    material('cypress', h('2f4a2a'), h('3c5a32'), noise=2.0)
    material('water', h('4a7085'), h('5c8398'), noise=1.2, ao=False)
    material('stone', h('a79f8d'), h('918a78'), noise=2.0, courses=0.5, course_dark=0.82)
    material('amphora', h('b5794e'), h('9d6440'), noise=3.0)
    material('cloth', h('b9a45a'), h('c9b46a'), noise=3.0)

    terrain_polar(b, ground, lambda x, y, z, s: 'dorngrass', R=31, cy=2, nr=38, na=124)
    # water above z=0 (the game's terrain hides anything below), clipped to the round base
    def strip(y0, y1, z):
        pts = []
        for y in (y0, y1):
            hw = math.sqrt(max(0.0, 30.4 ** 2 - (y - 2.0) ** 2))
            pts.append((y, hw))
        poly = [(-pts[0][1], y0), (pts[0][1], y0), (pts[1][1], y1), (-pts[1][1], y1)]
        plate(b, 'water', poly, z - 0.6, 0.6)
    strip(-12.3, -7.3, 0.12)
    strip(23.5, 31.0, 0.10)

    # --- vineyard terraces on both slopes
    for side in (-1, 1):
        for row in range(6):
            y = -4.5 + row * 2.9
            x0 = side * (9.0 + row * 0.8)
            for k in range(9):
                x = x0 + side * k * 1.55
                z = ground(x, y)
                if z < 0.1 or abs(x) > 27:
                    continue
                vine(b, x, y, z - 0.1, s=b.rng.uniform(0.8, 1.05))
            # low stone retaining wall between the rows
            if row < 5:
                yy = y + 1.45
                for k in range(10):
                    x = side * (8.0 + row * 0.8) + side * k * 1.55
                    z = ground(x, yy)
                    if 0.0 < z < 20 and abs(x) < 28:
                        box(b, 'stone', x, yy, z - 0.6, 1.7, 0.45, 0.8, rz=side * 2)

    # --- the manor house
    mx, my = -1.0, 2.0
    mz = ground(mx, my) - 0.3
    box(b, 'plaster', mx, my, mz, 10.0, 6.0, 4.0)
    box(b, 'stone', mx, my, mz - 0.6, 10.4, 6.4, 0.8)
    hipped(b, 'terracotta', mx, my, mz + 4.0, 10.2, 6.2, 2.2, overhang=0.55, ridge=0.55)
    # arched porch on the front
    for s in (-1, 1):
        box(b, 'plaster', mx + s * 3.2, my - 3.25, mz, 0.8, 0.8, 3.4)
    box(b, 'plaster', mx, my - 3.25, mz + 3.4, 7.2, 0.8, 0.7)
    lathe(b, 'stone', [(0, 0), (1.25, 0), (1.25, 0.35), (1.05, 0.35), (1.05, 0.08), (0, 0.08)],
          n=20, M=T(mx, my - 3.3, mz + 1.2, rx=90), smooth=False)
    box(b, 'window', mx, my - 3.3, mz, 1.8, 0.10, 2.4)
    # windows and a vine over the door
    for s in (-1, 1):
        for k in range(3):
            box(b, 'window', mx + s * (1.8 + 1.2 * k), my - 3.03, mz + 2.0, 0.5, 0.10, 0.9)
    for k in range(6):
        blob(b, 'vine', mx - 4.5 + 1.8 * k, my - 3.1, mz + 3.3, 0.45, n=6, rings=4, squash=0.7)
    # chimney
    box(b, 'stone', mx + 3.4, my + 0.8, mz + 5.8, 0.7, 0.7, 1.8)
    # a tower-like dovecote at the east end
    cyl(b, 'plaster', mx + 5.8, my + 0.5, mz, 1.0, 5.0, n=10)
    cone(b, 'terracotta', mx + 5.8, my + 0.5, mz + 5.0, 1.2, 1.5, n=10)

    # --- the winery and its barrels
    wx, wy = -8.0, 7.5
    wz = ground(wx, wy) - 0.35
    box(b, 'stone', wx, wy, wz, 5.0, 4.0, 2.8)
    gable(b, 'stonetile', wx, wy, wz + 2.8, 5.2, 4.2, 1.4, overhang=0.3)
    box(b, 'wood', wx, wy - 2.03, wz, 1.6, 0.10, 2.1)
    for k in range(3):
        barrel(b, 'wood', wx + 3.5 + 0.9 * k, wy - 1.4, wz - 0.1, 0.45, 0.9)
    for k in range(3):
        sphere(b, 'amphora', wx - 2.2 + 0.55 * k, wy - 2.2, wz + 0.3, 0.24, n=7, rings=5, squash=1.4)
    # wine press
    box(b, 'wood', wx + 1.0, wy + 2.4, wz, 1.2, 1.2, 0.9)
    strut(b, 'wood', (wx + 1.0, wy + 2.4, wz + 0.9), (wx + 1.0, wy + 2.4, wz + 2.2), 0.10, 0.08, n=4)
    box(b, 'wood', wx + 1.0, wy + 2.4, wz + 2.2, 1.4, 0.3, 0.3)

    # --- garden, hedges, flowers and cypress trees
    for k in range(14):
        x = -6.0 + 1.0 * k
        blob(b, 'flower', x, -3.2 + 0.3 * math.sin(k), ground(x, -3.2) + 0.1, 0.28, n=5, rings=3)
    for (x, y) in ((-12, -2), (-14, 2), (-11, 6), (10, 8), (13, 4), (8, -2), (16, 11)):
        z = ground(x, y)
        cyl(b, 'wood', x, y, z, 0.12, 2.0, n=4, top=False)
        for k in range(3):
            cone(b, 'cypress', x, y, z + 0.8 + 1.2 * k, 1.0 - 0.2 * k, 2.2, n=6)
    # a low hedge along the front garden
    for k in range(12):
        x = -5.0 + 1.0 * k
        blob(b, 'vine', x, -3.8, ground(x, -3.8) + 0.2, 0.5, n=6, rings=3, squash=0.6)
    # a bench and a table under the trees
    box(b, 'wood', 8.5, 3.5, ground(8.5, 3.5) + 0.5, 2.2, 0.6, 0.2)
    for s in (-1, 1):
        box(b, 'wood', 8.5 + s * 0.9, 3.5, ground(8.5, 3.5), 0.2, 0.5, 0.55)

    # --- workers in the vines
    person(b, 12.0, 1.0, ground(12.0, 1.0), s=0.9, robe='cloth', skin='plaster', arms=True)
    person(b, -12.0, 4.0, ground(-12.0, 4.0), s=0.9, robe='vine', skin='plaster', arms=True)
    person(b, 4.5, -4.0, ground(4.5, -4.0), s=0.9, robe='terracotta', skin='plaster', arms=True)

    # --- a small dock on the Sea of Rhûn
    for i in range(5):
        box(b, 'wood', -7.0 + i * 1.2, 24.0, 0.25, 1.1, 3.0, 0.2)
    for s in (-1, 1):
        cyl(b, 'wood', -7.0 + s * 2.6, 24.0, -1.5, 0.12, 2.0, n=4, top=False)

    fx(b, 'Smoke_Manor', (mx + 3.4, my + 0.8, mz + 8.0), 'SMOKE')
    boat(b, 4.0, 27.0, 0.12, rz=10, s=1.0, hull='wood', sail='cloth', mast=True)

    # --- the bridge over the stream and the village of the vintners in front
    for i in range(9):
        y = -13.6 + 7.6 * i / 8
        z = 1.0 + 0.7 * math.sin(math.pi * i / 8)
        box(b, 'stone', 0, y, z - 0.35, 3.0, 0.95, 0.45)
        for sd in (-1, 1):
            box(b, 'stone', sd * 1.4, y, z + 0.1, 0.22, 0.95, 0.45)
    rng = b.rng
    spots = []
    for k in range(300):
        if len(spots) >= 15:
            break
        x, y = rng.uniform(-20, 20), rng.uniform(-27, -14.5)
        if math.hypot(x, y - 2.0) > 28.5 or abs(x) < 2.2:
            continue
        if any(math.hypot(x - px, y - py) < 4.2 for px, py in spots):
            continue
        spots.append((x, y))
        house(b, x, y, ground(x, y) - 0.2, w=rng.uniform(3.0, 4.2), d=rng.uniform(2.4, 3.0), h=rng.uniform(2.0, 2.8),
              rz=rng.choice([0, 0, 90, rng.uniform(-15, 15)]), wall='plaster', roof='terracotta', roof_h=1.2,
              windows=2, chimney=k % 3 == 0, chimney_mat='stone', roof_style='hip', overhang=0.35)
    for k, (x, y) in enumerate(spots[:3]):
        fx(b, 'Smoke_V%d' % k, (x + 1.0, y, ground(x, y) + 4.4), 'SMOKE')
    # a wine market: stalls with barrels and amphorae by the bridge
    for (x, y, rz) in ((-4.5, -17.0, 10), (4.5, -17.5, -10), (0.0, -21.0, 0)):
        z = ground(x, y)
        box(b, 'wood', x, y, z + 0.9, 2.4, 1.6, 0.15, rz=rz)
        for sd in (-1, 1):
            cyl(b, 'wood', x + sd * 1.0, y, z, 0.07, 2.0, n=4)
        gable(b, 'terracotta', x, y, z + 2.0, 2.7, 1.9, 0.5, rz=rz, overhang=0.1)
        for j in range(3):
            sphere(b, 'amphora', x - 0.7 + 0.7 * j, y - 0.3, z + 1.25, 0.22, n=7, rings=5, squash=1.4)
        barrel(b, 'wood', x + 1.5, y - 0.8, z, 0.4, 0.8)
    for (x, y) in ((-2.0, -19.0), (2.5, -15.0), (-1.0, -24.0)):
        person(b, x, y, ground(x, y), s=0.9, robe='cloth', skin='plaster', arms=True)
    # more vines in the foreground, between the houses
    for k in range(90):
        x, y = rng.uniform(-27, 27), rng.uniform(-28, -14)
        if math.hypot(x, y - 2.0) > 29.0 or abs(x) < 3.0:
            continue
        if any(math.hypot(x - px, y - py) < 3.0 for px, py in spots):
            continue
        vine(b, x, y, ground(x, y) - 0.1, s=rng.uniform(0.75, 0.95))


PREVIEW = [((8, -32, 18), (0, 2, 6), 46), ((30, -12, 14), (0, 2, 5), 42)]
