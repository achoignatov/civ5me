"""Umbar, the haven of the Corsairs.

Book/film features modelled:
  * the great cape and firth of Umbar: a fortified haven on a rocky headland above a
    landlocked harbour (the Bay of Belfalas coast);
  * the city of white-washed and sandstone houses with flat roofs and domes climbing the
    slope, a citadel with sea towers, a mole and a lighthouse at the harbour mouth;
  * the monument raised by Ar-Pharazôn on the highest hill of the haven: a great white
    pillar crowned with a crystal globe that took the light of the sun (book);
  * the Corsair fleet: long dark-hulled ships with black sails (film) and banks of oars.
"""
import math

from blib import (material, hexcol as h, box, ring, cyl, cone, lathe, terrain_polar, blob, strut, curve, prism,
                  crenels, dome, sphere, window_row, T, hipped)

SHORE = -4.0


def ground(x, y):
    # headland rising to the north-west, harbour basin to the south-east
    z = 1.0 + 10.0 * max(0.0, min(1.0, (y - SHORE) / 18.0)) ** 1.2
    z += 9.0 * math.exp(-((x + 12) ** 2 + (y - 12) ** 2) / 70.0)          # the monument hill
    z += 1.2 * math.sin(x * 0.4) * math.sin(y * 0.5)
    if y < SHORE:
        d = SHORE - y
        z = 1.0 - 2.2 * min(1.0, d / 2.0)
    # rocky cape running out to the lighthouse on the west
    if x < -12 and y < SHORE:
        z = max(z, 3.0 - 0.15 * (SHORE - y) + 1.0 * math.sin(y * 0.8))
    return z


def build(b):
    material('umbarstone', h('d8cdb6'), h('c6b99d'), noise=2.0, courses=0.75, course_dark=0.86)
    material('whitewash', h('ebe6da'), h('ddd6c6'), noise=2.0)
    material('terracotta', h('9c5a3c'), h('8a4e33'), noise=3.0)
    material('umbardome', h('7a8fa0'), h('6a7f90'), noise=2.0)
    material('coast', h('a0926e'), zramp=[(-1, h('b8a77c')), (2, h('8f8a5a')), (8, h('9a8f6a')), (18, h('a69a78'))],
             slope_color=h('8e8170'), slope_start=0.55)
    material('sea', h('2f5f78'), h('3d6f88'), noise=0.6, ao=False)
    material('hull', h('1c1a18'), h('26221e'), noise=3.0)
    material('blacksail', h('1e1c1c'), h('2a2626'), noise=4.0)
    material('crystal', h('dff3ff'))
    material('pillarwhite', h('f2efe6'))
    material('flagred', h('7a1a16'))

    terrain_polar(b, ground, lambda x, y, z, s: 'coast', R=31, cy=2, nr=34, na=110)
    lathe(b, 'sea', [(30.0, 0), (0, 0)], n=48, x=0, y=2, z=0.1, smooth=False, a0=180, a1=360)

    # --- harbour quay and sea wall with towers
    box(b, 'umbarstone', 4.0, SHORE + 0.3, -1.0, 30.0, 1.6, 3.6)
    for x in (-9.0, 2.0, 13.0):
        cyl(b, 'umbarstone', x, SHORE + 0.3, -1.0, 1.4, 7.0, n=10)
        crenels(b, 'umbarstone', 1.25, 6.0, 0, 360, size=0.4, h=0.5, step=0.9, x=x, y=SHORE + 0.3, depth=0.35)
    # the mole running out to the lighthouse
    for i in range(9):
        box(b, 'umbarstone', -16.0 + 0.2 * i, SHORE - 2.0 - 2.0 * i, -1.0, 2.2, 2.1, 3.0)
    lx, ly = -14.5, SHORE - 20.0
    lathe(b, 'umbarstone', [(2.0, 0), (1.6, 10.0), (2.0, 10.5), (2.0, 11.0), (0, 11.0)], n=10, x=lx, y=ly, z=-1.0,
          smooth=False)
    for k in range(6):
        a = math.radians(60 * k)
        cyl(b, 'umbarstone', lx + 1.3 * math.cos(a), ly + 1.3 * math.sin(a), 10.0, 0.15, 2.0, n=4)
    cone(b, 'terracotta', lx, ly, 12.0, 1.8, 1.8, n=10)
    sphere(b, 'flagred', lx, ly, 11.0, 0.7, n=8, rings=5)

    # --- city on the slope: flat roofs, some domes, terracotta
    rng = b.rng
    for k in range(320):
        x, y = rng.uniform(-10, 20), rng.uniform(SHORE + 2.0, 18)
        if math.hypot(x - 8, y - 8) < 5.5:
            continue
        if rng.random() < 0.7:
            continue
        z = min(ground(x + dx, y + dy) for dx in (-0.8, 0.8) for dy in (-0.8, 0.8)) - 0.3
        w, d, hh = rng.uniform(1.6, 2.4), rng.uniform(1.6, 2.4), rng.uniform(1.6, 3.0)
        m = rng.choice(['whitewash', 'whitewash', 'umbarstone'])
        box(b, m, x, y, z, w, d, hh)
        if rng.random() < 0.35:
            hipped(b, 'terracotta', x, y, z + hh, w, d, 0.8, overhang=0.12)
        elif rng.random() < 0.15:
            dome(b, 'umbardome', x, y, z + hh, min(w, d) * 0.45, n=10, rings=4)
        else:
            box(b, m, x, y, z + hh, w + 0.1, d + 0.1, 0.15)
        window_row(b, 'window', x - w / 2 + 0.3, y - d / 2 - 0.02, x + w / 2 - 0.3, y - d / 2 - 0.02, z + hh * 0.5,
                   max(1, int(w)), w=0.25, h=0.4, out=0.0)

    # --- the citadel of the Corsair lords
    cx, cy = 8.0, 8.0
    cz = ground(cx, cy) - 0.5
    box(b, 'umbarstone', cx, cy, cz - 1.0, 8.0, 7.0, 6.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = cx + sx * 4.0, cy + sy * 3.5
            cyl(b, 'umbarstone', x, y, cz - 1.0, 1.1, 8.0, n=10)
            dome(b, 'umbardome', x, y, cz + 7.0, 1.15, n=10, rings=4)
    dome(b, 'umbardome', cx, cy, cz + 5.0, 2.8, n=16, rings=5)
    for k in range(5):
        box(b, 'window', cx - 2.8 + 1.4 * k, cy - 3.53, cz + 1.5, 0.45, 0.08, 1.6)
    cyl(b, 'iron', cx, cy, cz + 7.8, 0.06, 4.0, n=4)
    box(b, 'flagred', cx + 0.6, cy, cz + 10.3, 1.1, 0.05, 1.3)

    # --- the monument of Ar-Pharazôn: white pillar crowned with a crystal globe
    mx, my = -12.0, 12.0
    mz = ground(mx, my) - 0.3
    box(b, 'pillarwhite', mx, my, mz - 0.5, 3.4, 3.4, 1.8)
    lathe(b, 'pillarwhite', [(1.0, 0), (0.85, 1.0), (0.75, 17.0), (1.1, 17.6), (0, 17.6)], n=12, x=mx, y=my, z=mz + 1.3,
          smooth=False)
    sphere(b, 'crystal', mx, my, mz + 19.9, 1.4, n=14, rings=10)

    # --- the Corsair fleet
    for (x, y, rz) in ((6.0, -11.0, 10), (-3.0, -15.5, -5), (14.0, -17.0, 20)):
        corsair(b, x, y, rz)


def corsair(b, x, y, rz):
    M = T(x, y, 0.0, rz=rz)
    hull = [(-5.5, 0.0), (-4.5, -1.2), (4.0, -1.2), (6.2, 0.0), (4.0, 1.2), (-4.5, 1.2)]
    prism(b, 'hull', hull, -0.6, 1.8, M=M)
    # raised stern castle and the curving prow
    prism(b, 'hull', [(-5.2, -1.0), (-3.0, -1.0), (-3.0, 1.0), (-5.2, 1.0)], 1.2, 1.2, M=M)
    from mathutils import Vector
    P = lambda px, py, pz: tuple(M @ Vector((px, py, pz)))
    strut(b, 'hull', P(5.9, 0, 0.8), P(7.0, 0, 2.6), 0.35, 0.12, n=5)
    # two masts with black square sails
    for mxp, H in ((1.8, 8.0), (-1.8, 7.0)):
        strut(b, 'wood', P(mxp, 0, 1.2), P(mxp, 0, 1.2 + H), 0.13, 0.09, n=5)
        box(b, 'blacksail', 0, 0, 0, 0.1, 4.2, H * 0.55, M=M @ T(mxp + 0.12, 0, 1.2 + H * 0.35, rz=0))
        strut(b, 'wood', P(mxp, -2.2, 1.2 + H * 0.9), P(mxp, 2.2, 1.2 + H * 0.9), 0.06, 0.06, n=4)
    box(b, 'flagred', 0, 0, 0, 0.05, 0.9, 0.5, M=M @ T(1.8, 0.45, 9.3))
    # banks of oars
    for sy in (-1, 1):
        for k in range(7):
            ox = -3.2 + 1.1 * k
            strut(b, 'wood', P(ox, sy * 1.2, 0.8), P(ox - 0.4, sy * 3.0, -0.2), 0.05, 0.05, n=3)
