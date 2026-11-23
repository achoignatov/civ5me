"""Carn Dûm, the fortress of the Witch-king of Angmar.

Book/lore features modelled (Carn Dûm is described only briefly; the look follows the
canonical "chief city of Angmar at the northern end of the Misty Mountains" and its
popular depictions):
  * a dark fortress-city on a crag among the cold, snow-bound northern mountains;
  * jagged black walls with spiked battlements, a gatehouse reached by a causeway;
  * the Witch-king's keep: a tall, angular black tower crowned with iron spikes,
    lesser spired towers, a bridge spanning a chasm between crags;
  * snow lying on every ledge and roof, frozen pines, and the black-and-red banners
    of Angmar.
"""
import math

from blib import (material, hexcol as h, box, ring, cyl, cone, lathe, terrain_polar, blob, strut, curve, prism,
                  conifer, crenels, pyramid)


def ground(x, y):
    z = 1.0 + 0.8 * math.sin(x * 0.5) * math.sin(y * 0.4)
    # the crag on which the keep stands, and mountains behind
    r = math.hypot(x - 1, y - 2)
    z += 11.0 * math.exp(-(r / 9.0) ** 2.5)
    if y > 10:
        t = min(1.0, (y - 10) / 14)
        z += 30.0 * t * (0.7 + 0.3 * math.sin(x * 0.35 + 0.5)) + 4 * math.sin(x * 0.9) * t
    # a chasm between the crag and the eastern spur
    if 9.5 < x < 12.5 and -3 < y < 8:
        z = min(z, -1.0)
    z += 9.0 * math.exp(-((x - 18) ** 2 + (y - 3) ** 2) / 30.0)
    return z


def build(b):
    material('angstone', h('2b2a2e'), h('353439'), noise=2.5, courses=0.8, course_dark=0.75)
    material('angsnow', h('e8edf2'), zramp=[(-1, h('dfe6ec')), (10, h('e8edf2')), (40, h('f3f6f8'))],
             slope_color=h('57555b'), slope_start=0.62)
    material('icy', h('cfdbe5'))
    material('redbanner', h('7a1414'))
    material('roofsnow', h('dde5ec'), slope_color=h('25252a'), slope_start=0.75)

    material('trodden', h('8f969e'), h('a7aeb5'), noise=3.0)
    from blib import near_path
    road = [(0.0, -6.5), (-1.5, -12.0), (1.5, -18.0), (0.0, -26.0)]
    terrain_polar(b, ground, lambda x, y, z, s: 'trodden' if near_path(x, y, road, 1.2) else 'angsnow',
                  R=31, cy=2, nr=34, na=110)

    top = ground(1, 2) - 0.6
    # --- outer walls on the crag, spiked battlements
    wall = [(-8.0, -6.0), (8.5, -6.5), (9.0, 6.5), (-7.5, 8.0)]
    for i in range(4):
        (x0, y0), (x1, y1) = wall[i], wall[(i + 1) % 4]
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        zbase = min(ground(x0, y0), ground(x1, y1)) - 2.0
        box(b, 'angstone', (x0 + x1) / 2, (y0 + y1) / 2, zbase, L, 1.2, top - zbase + 3.6, rz=ang)
        k = int(L / 1.2)
        for j in range(k + 1):
            t = j / k
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            strut(b, 'angstone', (x, y, top + 3.6), (x, y, top + 4.6 + 0.4 * (j % 2)), 0.28, 0.0, n=4)
        # corner towers with steep spires
        cyl(b, 'angstone', x0, y0, zbase, 1.6, top - zbase + 6.0, n=7)
        lathe(b, 'roofsnow', [(2.0, 0), (0.0, 4.5)], n=7, x=x0, y=y0, z=top + 6.0, smooth=False)
    # gatehouse on the south wall with a causeway down the slope
    gx, gy = 0.0, -6.3
    box(b, 'angstone', gx, gy, top - 3.0, 4.6, 2.4, 9.0)
    for s in (-1, 1):
        strut(b, 'angstone', (gx + s * 2.3, gy - 1.2, top + 6.0), (gx + s * 2.9, gy - 1.8, top + 8.5), 0.4, 0.0, n=4)
    box(b, 'iron', gx, gy - 1.25, top - 0.5, 2.0, 0.2, 3.2)

    # --- the Witch-king's keep: tall angular tower crowned with iron spikes
    kx, ky = 1.0, 2.5
    lathe(b, 'angstone', [(4.2, 0), (3.8, 6.0), (3.0, 18.0), (3.6, 19.0), (3.6, 20.2), (0, 20.2)], n=6, x=kx, y=ky,
          z=top, smooth=False)
    for k in range(6):
        a = math.radians(60 * k + 30)
        strut(b, 'angstone', (kx + 3.4 * math.cos(a), ky + 3.4 * math.sin(a), top + 19.8),
              (kx + 4.4 * math.cos(a), ky + 4.4 * math.sin(a), top + 24.0), 0.55, 0.0, n=4)
    lathe(b, 'angstone', [(2.2, 0), (1.6, 3.0), (0.1, 12.0), (0, 12.2)], n=6, x=kx, y=ky, z=top + 20.2, smooth=False)
    # spurs and buttresses on the keep
    for k in range(3):
        a = math.radians(120 * k + 90)
        strut(b, 'angstone', (kx + 4.8 * math.cos(a), ky + 4.8 * math.sin(a), top - 1.0),
              (kx + 3.0 * math.cos(a), ky + 3.0 * math.sin(a), top + 13.0), 1.0, 0.4, n=4)
    # pale, cold windows
    for zz in (8.0, 13.0, 17.0):
        box(b, 'icy', kx, ky - 3.6 + zz * 0.04, top + zz, 0.5, 0.15, 1.3)
    # lesser spired towers inside the walls
    for (x, y, hgt) in ((-5.0, 4.5, 11.0), (6.0, -2.0, 9.0), (-4.5, -3.5, 8.0)):
        lathe(b, 'angstone', [(1.5, 0), (1.3, hgt), (1.7, hgt + 0.5), (0, hgt + 0.5)], n=6, x=x, y=y, z=top, smooth=False)
        lathe(b, 'roofsnow', [(1.8, 0), (0.0, 5.0)], n=6, x=x, y=y, z=top + hgt + 0.5, smooth=False)
    # snow-roofed halls inside
    from blib import gable
    for (x, y, L, rz) in ((-2.5, 6.0, 5.0, 0), (5.0, 3.0, 4.0, 90)):
        box(b, 'angstone', x, y, top, L, 2.6, 2.4, rz=rz)
        gable(b, 'roofsnow', x, y, top + 2.4, L, 2.6, 1.8, rz=rz, overhang=0.3)

    # --- a bridge over the chasm to the eastern spur, with an outpost tower
    for i in range(8):
        t = i / 7
        x = 9.0 + 5.0 * t
        box(b, 'angstone', x, 2.5, top + 1.0 - 0.2 * math.sin(math.pi * t), 0.75, 2.0, 0.6)
    ox, oy = 17.0, 3.0
    oz = ground(ox, oy) - 1.0
    lathe(b, 'angstone', [(2.0, 0), (1.6, 12.0), (2.1, 12.6), (0, 12.6)], n=6, x=ox, y=oy, z=oz, smooth=False)
    for k in range(6):
        a = math.radians(60 * k)
        strut(b, 'angstone', (ox + 1.8 * math.cos(a), oy + 1.8 * math.sin(a), oz + 12.4),
              (ox + 2.4 * math.cos(a), oy + 2.4 * math.sin(a), oz + 15.0), 0.35, 0.0, n=4)

    # --- banners of Angmar
    for (x, y) in ((-3.0, -6.6), (3.0, -6.6)):
        cyl(b, 'iron', x, y, top + 3.6, 0.07, 5.5, n=4)
        box(b, 'redbanner', x + 0.6, y, top + 6.2, 1.1, 0.05, 2.6)

    # --- frozen pines on the lower slopes
    rng = b.rng
    for k in range(22):
        a = rng.uniform(0, 360)
        r = rng.uniform(14, 27)
        x, y = 1 + r * math.cos(math.radians(a)), 2 + r * math.sin(math.radians(a))
        if y > 14 or (abs(x) < 3 and y < -6):
            continue
        conifer(b, x, y, ground(x, y) - 0.3, h=5.0, r=1.2, leaves='pine')
        cone(b, 'snow', x, y, ground(x, y) + 3.6, 0.6, 1.6, n=6)


PREVIEW = [((12, -26, 34), (1, 2, 20), 45)]
