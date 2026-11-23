"""Dale, the city of the Men of the North under the Lonely Mountain.

Book/film features modelled:
  * the rebuilt city of Dale on the south bank of the River Running, in the shadow of
    Erebor (the Lonely Mountain), with the river and its bridge in front;
  * a strong grey stone wall with round towers, battlements and the great south gate;
  * steep slate and red-tiled roofs, a tall bell tower, a market square and a broad
    stone hall, all crowded inside the wall;
  * the blue-and-gold banners of Dale, the mountain's snowy shoulder behind;
  * a few boats on the Running and a road climbing from the bridge to the gate.
The city faces the camera (-Y); Erebor rises behind it (+Y).
"""
import math

from blib import (material, hexcol as h, box, gable, hipped, cyl, cone, lathe, terrain_polar, blob,
                  strut, ring, crenels, window_row, banner, sphere, T, near_path)
from city_common import house, longhouse, watchtower, barrel, crate, boat


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = 0.5 + 0.35 * math.sin(x * 0.4) * math.sin(y * 0.35)
    # the river channel
    if -15.0 < y < -6.0:
        z = min(z, -0.9 + 0.16 * abs(y + 10.5))
    # the city terrace
    terr = sm((y + 4.0) / 3.0) * sm((14.0 - y) / 4.0) * sm((19.0 - abs(x)) / 4.0)
    z = z * (1.0 - terr) + 2.15 * terr
    # Erebor behind
    if y > 12.0:
        t = min(1.0, (y - 12.0) / 19.0)
        m = 40.0 * t ** 1.55 * math.exp(-(x / 30.0) ** 4)
        m += 2.0 * math.sin(x * 0.35 + 0.5) * math.sin(y * 0.3) * t
        z = max(z, 0.5 + m)
    return z


def build(b):
    material('dalegrass', h('6d8d43'), zramp=[(-1, h('708d48')), (2, h('66863d')), (10, h('6f8746'))],
             slope_color=h('7b7667'), slope_start=0.55)
    material('road', h('a49373'), h('8d7d60'), noise=2.0)
    material('dalestone', h('b9b3a4'), h('a19b8d'), noise=1.8, courses=0.65, course_dark=0.84)
    material('darkstone', h('6d6b66'), h('5b5954'), noise=2.0, courses=0.5, course_dark=0.8)
    material('slate', h('53616c'), h('65737f'), noise=2.5)
    material('redroof', h('8d5a48'), h('774a3b'), noise=3.0)
    material('timber', h('5c3f28'), h('4b321e'), noise=4.0)
    material('window', h('241f19'))
    material('blue', h('2f4f7a'), h('3b5f8c'), noise=3.0)
    material('goldtrim', h('d3aa45'), h('b88d31'), noise=2.0, spec=0.8, refl=30)
    material('river', h('4d7387'), h('5f879b'), noise=1.5, ao=False)
    material('mountain', h('8a8780'), zramp=[(0, h('5f6f4a')), (8, h('77736a')), (22, h('8d8981')),
                                             (36, h('74706a')), (48, h('e8ecef'))],
             slope_color=h('6d6962'), slope_start=0.45)
    material('sail', h('d9d2bd'), h('c3b99f'), noise=3.0)

    PATH = [(0.0, -30.0), (0.0, -15.0), (0.0, -6.0), (0.0, 2.0)]

    def mat(x, y, z, s):
        if near_path(x, y, PATH, 1.5):
            return 'road'
        if y > 12 and z > 8:
            return 'mountain'
        return 'dalegrass'

    terrain_polar(b, ground, mat, R=31, cy=2, nr=38, na=124)
    box(b, 'river', 0, -10.5, -0.65, 60, 8.0, 0.55)

    # --- the bridge over the Running (three piers, stone deck, low parapets)
    for i in range(13):
        y = -16.5 + 11.0 * i / 12
        z = 1.1 + 0.9 * math.sin(math.pi * i / 12)
        box(b, 'dalestone', 0, y, z - 0.35, 4.0, 0.95, 0.42)
        for s in (-1, 1):
            box(b, 'dalestone', s * 1.9, y, z + 0.05, 0.25, 0.95, 0.45)
    for y in (-14.8, -11.0, -7.2):
        box(b, 'darkstone', 0, y, -0.8, 3.2, 1.0, 2.2)
        # pointed cutwater
        for s in (-1, 1):
            box(b, 'darkstone', s * 1.1, y - 0.7, -0.8, 0.8, 0.8, 2.2, rz=45)

    # --- the wall of Dale
    WY = 4.0
    R = 17.0
    for a0, a1 in ((150, 255), (285, 390)):
        ring(b, 'dalestone', R - 0.9, R, 2.0, 3.8, a0, a1, n=72, x=0, y=WY, top=False)
        ring(b, 'dalestone', R - 1.0, R + 0.1, 5.8, 0.8, a0, a1, n=72, x=0, y=WY)
        crenels(b, 'dalestone', R - 0.45, 6.6, a0 + 1, a1 - 1, size=0.5, h=0.55, step=1.5, x=0, y=WY, depth=0.5)
    # gatehouse at the south
    for s in (-1, 1):
        tx = s * 3.6
        ty = WY - R
        cyl(b, 'dalestone', tx, ty, 1.8, 1.6, 7.8, n=10)
        crenels(b, 'dalestone', 1.45, 9.6, 0, 360, size=0.45, h=0.5, step=1.0, x=tx, y=ty, depth=0.4)
        cone(b, 'slate', tx, ty, 10.1, 1.7, 2.0, n=10)
    box(b, 'dalestone', 0, WY - R, 2.0, 4.8, 1.8, 5.4)
    box(b, 'window', 0, WY - R - 0.92, 2.0, 2.4, 0.10, 3.8)
    box(b, 'goldtrim', 0, WY - R - 1.0, 5.7, 5.4, 0.25, 0.25)
    # flanking wall towers
    for a in (150, 210, 330, 390):
        ar = math.radians(a)
        tx, ty = R * math.cos(ar), WY + R * math.sin(ar)
        cyl(b, 'dalestone', tx, ty, 2.0, 1.3, 6.8, n=10)
        crenels(b, 'dalestone', 1.2, 8.8, 0, 360, size=0.4, h=0.45, step=0.9, x=tx, y=ty, depth=0.35)

    # --- the bell tower (tall, square, with a slender spire)
    tx, ty = -5.2, 5.2
    tz = 2.15
    box(b, 'dalestone', tx, ty, tz, 3.0, 3.0, 13.0)
    box(b, 'dalestone', tx, ty, tz + 13.0, 3.6, 3.6, 0.5)
    for k in range(4):
        a = math.radians(90 * k + 45)
        box(b, 'window', tx + 1.52 * math.cos(a), ty + 1.52 * math.sin(a), tz + 10.0, 0.55, 0.08, 1.8, rz=90 * k + 45)
        box(b, 'window', tx + 1.52 * math.cos(a), ty + 1.52 * math.sin(a), tz + 5.0, 0.45, 0.08, 1.3, rz=90 * k + 45)
    cone(b, 'slate', tx, ty, tz + 13.5, 2.0, 5.5, n=8)
    cyl(b, 'goldtrim', tx, ty, tz + 18.8, 0.08, 2.0, n=4, top=False)
    box(b, 'blue', tx + 0.5, ty, tz + 20.2, 1.0, 0.05, 0.7)

    # --- the great hall / market square
    longhouse(b, 5.6, 7.0, tz, w=7.0, d=4.4, h=3.2, wall='dalestone', roof='slate', roof_h=2.2,
              windows=5, base=None, porch=True, posts=5, post_mat='dalestone')
    # market stalls around the square
    for (sx, sy, rz) in ((-1.5, -1.5, 10), (2.5, -2.5, -15), (0.0, 2.0, 5), (-3.5, 2.5, 20)):
        box(b, 'timber', sx, sy, tz, 2.2, 1.5, 0.22, rz=rz)
        for s in (-1, 1):
            for t in (-1, 1):
                cyl(b, 'timber', sx + s * 0.9 * math.cos(math.radians(rz)) - t * 0.6 * math.sin(math.radians(rz)),
                    sy + s * 0.9 * math.sin(math.radians(rz)) + t * 0.6 * math.cos(math.radians(rz)),
                    tz, 0.06, 1.8, n=4)
        gable(b, 'redroof', sx, sy, tz + 1.8, 2.5, 1.8, 0.45, rz=rz, overhang=0.1)
        for k in range(3):
            sphere(b, 'goldtrim', sx - 0.6 + 0.6 * k, sy - 0.3, tz + 0.4, 0.14, n=6, rings=4)

    # --- houses inside the wall
    spots = []
    rng = b.rng
    for k in range(400):
        if len(spots) >= 28:
            break
        x, y = rng.uniform(-14.0, 14.0), rng.uniform(-9.0, 15.0)
        if math.hypot(x, y - WY) > 14.5:
            continue
        if math.hypot(x - 5.6, y - 7.0) < 4.5 or math.hypot(x + 5.2, y - 5.2) < 3.5:
            continue
        if math.hypot(x, y - WY) > 12.0 and y < WY:
            continue
        if any(math.hypot(x - px, y - py) < 2.7 for px, py in spots):
            continue
        spots.append((x, y))
        w, d, hh = rng.uniform(2.4, 3.4), rng.uniform(2.0, 2.8), rng.uniform(2.0, 3.2)
        rz = rng.choice([0, 90, rng.uniform(-20, 20)])
        house(b, x, y, tz, w=w, d=d, h=hh, rz=rz, wall='dalestone',
              roof='slate' if rng.random() < 0.7 else 'redroof', roof_h=rng.uniform(1.0, 1.5),
              windows=2, base=None, chimney=rng.random() < 0.4, chimney_mat='dalestone',
              overhang=0.25)
    # a couple of taller townhouses
    for (x, y, hh) in ((-9.5, 0.0, 5.0), (10.0, 1.0, 4.6), (2.0, 11.0, 4.4)):
        box(b, 'dalestone', x, y, tz, 2.8, 2.6, hh)
        hipped(b, 'redroof', x, y, tz + hh, 2.8, 2.6, 1.3, overhang=0.15)
        window_row(b, 'window', x - 1.0, y - 1.32, x + 1.0, y - 1.32, tz + hh * 0.55, 2, w=0.3, h=0.5, out=0.0)

    # --- banners on the gate and towers
    for (x, y) in ((-3.6, WY - R), (3.6, WY - R), (-5.2, 5.2)):
        banner(b, 'timber', 'blue', x + 1.2, y, 2.2 if y < 0 else tz, h=5.5, w=0.9, ch=2.3, rz=0)

    # --- a few boats on the river
    for (x, y, rz) in ((-9.0, -9.5, 8), (8.5, -12.0, -12)):
        boat(b, x, y, -0.45, rz=rz, s=0.8, hull='timber', sail='sail', mast=False, oars=True)

    # --- trees outside the wall
    for (x, y) in ((-22, -5), (22, -4), (-21, 10), (21, 11), (-14, 18), (15, 18)):
        z = ground(x, y)
        cyl(b, 'timber', x, y, z, 0.25, 3.0, n=6, r2=0.16)
        for k in range(3):
            blob(b, 'dalegrass', x + b.rng.uniform(-0.8, 0.8), y + b.rng.uniform(-0.8, 0.8),
                 z + 2.5 + 0.5 * k, 1.4, n=7, rings=4, squash=0.85)


PREVIEW = [((10, -34, 24), (0, 2, 9), 46), ((30, -18, 15), (0, 5, 7), 42)]

# the walled town is laid out in ~14 units before the mountain; scaled to fill the tile (pipeline FILL)
FILL = 1.2
