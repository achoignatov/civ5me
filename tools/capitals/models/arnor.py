"""Annúminas, the Tower of the West, first city of Arnor.

Book/lore features modelled:
  * built by Elendil on the shores of Lake Evendim (Nenuial) beneath the Hills of
    Evendim; Númenórean architecture of pale stone like Gondor's, but older;
  * the tall tower that housed the chief palantír of the North (the Elendil-stone's
    sister), crowned by a domed chamber;
  * a domed rotunda (the kings' hall), colonnades, a walled city stepping down to the
    lake, a quay with a sea-wall and watch towers, and two great statues of kings
    guarding the harbour mouth, in the manner of the Argonath;
  * the blue-grey slate and green copper roofs, banners of Arnor (silver stars on blue).
"""
import math

from blib import (material, hexcol as h, box, ring, cyl, cone, lathe, terrain_polar, blob, strut, curve, prism,
                  conifer, crenels, dome, gable, hipped, sphere, window_row, tree)

SHORE_Y = -8.0


def ground(x, y):
    z = 0.6
    if y > SHORE_Y:
        t = min(1.0, (y - SHORE_Y) / 26.0)
        z = 0.6 + 3.0 * min(1.0, (y - SHORE_Y) / 3.0) + 16.0 * t ** 1.4
        z += 2.0 * math.sin(x * 0.3) * t
    else:
        z = -0.9
    # flattened city terraces
    for (y0, y1, tz) in ((-6.5, -1.0, 3.8), (-1.0, 5.0, 6.8), (5.0, 11.0, 9.8)):
        if y0 <= y < y1 and abs(x) < 15 - (y0 + 6.5) * 0.4:
            z = tz
    return z


def build(b):
    material('arnorstone', h('dcd8cc'), h('c9c4b6'), noise=2.0, courses=0.8, course_dark=0.87)
    material('slate2', h('546270'), h('617080'), noise=2.5)
    material('copper', h('5f9a86'), h('6fae98'), noise=3.0)
    material('evendim', h('4f7f9e'), h('5f90ae'), noise=0.8, ao=False)
    material('hills', h('6f9248'), zramp=[(0, h('6f9248')), (8, h('76964c')), (20, h('7f9a56'))],
             slope_color=h('8a877c'), slope_start=0.55)
    material('bluebanner', h('2b3f7a'))
    material('palantir', h('1f2430'))
    material('statue2', h('b8b3a6'), h('a49f92'), noise=3.0)

    terrain_polar(b, ground, lambda x, y, z, s: 'hills', R=31, cy=2, nr=34, na=110)
    # Lake Evendim
    lathe(b, 'evendim', [(30.0, 0), (0, 0)], n=48, x=0, y=2, z=0.12, smooth=False, a0=180, a1=360)

    # --- sea-wall and quay along the shore, watch towers
    box(b, 'arnorstone', 0, SHORE_Y + 0.6, -1.5, 34.0, 1.6, 5.6)
    for i in range(23):
        x = -16.5 + 1.5 * i
        box(b, 'arnorstone', x, SHORE_Y - 0.1, 4.1, 0.6, 0.4, 0.5)
    for x in (-17.5, -6.0, 6.0, 17.5):
        cyl(b, 'arnorstone', x, SHORE_Y + 0.6, -1.5, 1.4, 8.0, n=10)
        cone(b, 'slate2', x, SHORE_Y + 0.6, 6.5, 1.7, 2.6, n=10)
    # the quay jutting into the lake with a moored ship
    box(b, 'arnorstone', -11.0, SHORE_Y - 4.0, -1.5, 3.0, 8.0, 2.0)
    ship(b, -6.5, SHORE_Y - 6.0)

    # --- the two statues of the kings guarding the harbour mouth
    for s in (-1, 1):
        x, y = s * 4.0 + 6.0, SHORE_Y - 13.0
        box(b, 'statue2', x, y, -1.5, 3.0, 3.0, 2.6)
        lathe(b, 'statue2', [(1.4, 0), (1.2, 5.5), (1.5, 7.0), (0, 7.0)], n=6, x=x, y=y, z=1.1, smooth=False)
        sphere(b, 'statue2', x, y, 8.9, 0.85, n=8, rings=6)
        cone(b, 'statue2', x, y, 9.4, 0.9, 1.3, n=8)
        # the raised left hand (palm outward, as the Argonath)
        strut(b, 'statue2', (x - s * 1.3, y, 7.0), (x - s * 1.9, y - 0.6, 10.4), 0.4, 0.32, n=5)
        strut(b, 'statue2', (x + s * 1.3, y, 7.0), (x + s * 1.5, y - 0.8, 4.5), 0.35, 0.3, n=5)
        strut(b, 'statue2', (x + s * 1.5, y - 0.9, 1.4), (x + s * 1.5, y - 0.9, 9.0), 0.16, 0.16, n=4)

    # --- the city: houses on the terraces
    rng = b.rng
    for (y0, y1, tz) in ((-6.5, -1.0, 3.8), (-1.0, 5.0, 6.8), (5.0, 11.0, 9.8)):
        half = 15 - (y0 + 6.5) * 0.4 - 1.0
        x = -half
        while x < half:
            w = rng.uniform(1.8, 2.6)
            if abs(x) < 4.5 and y0 > -3:
                x += w
                continue
            for yy in (y0 + 1.2, (y0 + y1) / 2 + 0.6):
                if rng.random() < 0.15:
                    continue
                d = rng.uniform(1.6, 2.2)
                hh = rng.uniform(1.8, 3.2)
                box(b, 'arnorstone', x + w / 2, yy, tz, w - 0.2, d, hh)
                roof = 'slate2' if rng.random() < 0.75 else 'copper'
                hipped(b, roof, x + w / 2, yy, tz + hh, w - 0.2, d, 0.9, overhang=0.12)
                window_row(b, 'window', x + 0.3, yy - d / 2 - 0.02, x + w - 0.5, yy - d / 2 - 0.02, tz + hh * 0.45, 2,
                           w=0.25, h=0.5, out=0.0)
            x += w
        # terrace retaining wall
        box(b, 'arnorstone', 0, y0, tz - 3.2, 2 * half + 2.0, 0.8, 3.4)

    # --- the domed rotunda of the kings
    rx, ry, rz = 0.0, 1.5, 6.8
    ring(b, 'arnorstone', 0.05, 5.0, rz, 0.6, 0, 360, n=24, x=rx, y=ry, inner=False)
    lathe(b, 'arnorstone', [(3.6, 0), (3.6, 4.2), (0, 4.2)], n=16, x=rx, y=ry, z=rz + 0.6, smooth=False)
    for k in range(16):
        a = math.radians(360 * k / 16)
        cyl(b, 'arnorstone', rx + 4.4 * math.cos(a), ry + 4.4 * math.sin(a), rz + 0.6, 0.22, 4.0, n=6)
    ring(b, 'arnorstone', 3.5, 4.8, rz + 4.6, 0.5, 0, 360, n=24, x=rx, y=ry)
    dome(b, 'copper', rx, ry, rz + 4.8, 4.0, n=20, rings=6, h=3.6)
    lathe(b, 'arnorstone', [(0.6, 0), (0.6, 0.8), (0, 1.4)], n=8, x=rx, y=ry, z=rz + 8.3, smooth=False)

    # --- the tower of the palantír
    tx, ty, tz = 0.0, 8.5, 9.8
    lathe(b, 'arnorstone', [(2.6, 0), (2.2, 2.0), (1.9, 20.0), (2.5, 20.6), (2.5, 21.2), (0, 21.2)], n=12, x=tx, y=ty,
          z=tz, smooth=False)
    crenels(b, 'arnorstone', 2.35, tz + 21.2, 0, 360, size=0.35, h=0.4, step=0.9, x=tx, y=ty)
    # domed chamber of the seeing-stone, open on pillars
    for k in range(8):
        a = math.radians(45 * k)
        cyl(b, 'arnorstone', tx + 1.6 * math.cos(a), ty + 1.6 * math.sin(a), tz + 21.2, 0.16, 2.4, n=5)
    lathe(b, 'arnorstone', [(0.5, 0), (0.35, 0.8), (0, 0.8)], n=8, x=tx, y=ty, z=tz + 21.2, smooth=False)
    sphere(b, 'palantir', tx, ty, tz + 22.45, 0.45, n=10, rings=6)
    dome(b, 'copper', tx, ty, tz + 23.6, 2.1, n=14, rings=5, h=2.0)
    lathe(b, 'arnorstone', [(0.15, 0), (0.0, 2.2)], n=6, x=tx, y=ty, z=tz + 25.6, smooth=False)
    for zz in (6.0, 10.0, 14.0, 18.0):
        box(b, 'window', tx, ty - 2.05, tz + zz, 0.5, 0.1, 1.3)
    # banners of Arnor along the sea-wall
    for x in (-12.0, 0.0, 12.0):
        cyl(b, 'iron', x, SHORE_Y + 0.9, 4.1, 0.06, 4.0, n=4)
        box(b, 'bluebanner', x + 0.55, SHORE_Y + 0.9, 5.6, 1.0, 0.05, 2.2)
    # pines and trees on the Hills of Evendim
    for k in range(30):
        x, y = rng.uniform(-28, 28), rng.uniform(10, 30)
        if math.hypot(x, y - 2) > 29 or (abs(x) < 9 and y < 15):
            continue
        if rng.random() < 0.5:
            conifer(b, x, y, ground(x, y) - 0.2, h=5.0, r=1.3)
        else:
            tree(b, x, y, ground(x, y) - 0.2, h=4.0, r=1.5)


def ship(b, x, y):
    """A Númenórean ship: long white hull, single mast with a pale sail, swan prow."""
    hull = [(-3.6, 0.0), (-3.0, -0.9), (3.0, -0.9), (4.2, 0.0), (3.0, 0.9), (-3.0, 0.9)]
    prism(b, 'arnorstone', [(x + px, y + py) for px, py in hull], -0.6, 1.2)
    cyl(b, 'wood', x, y, 0.6, 0.1, 5.5, n=5)
    from blib import T
    box(b, 'statue2', 0, 0, 0, 0.08, 3.6, 3.2, M=T(x, y, 1.8, rz=90))
    strut(b, 'arnorstone', (x + 3.9, y, 0.5), (x + 4.6, y, 2.4), 0.25, 0.1, n=5)
