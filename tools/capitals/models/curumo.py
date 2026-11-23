"""Curumo: Saruman the White as he first came to Middle-earth.

Tolkien (Unfinished Tales, "The Istari"): Curumo, "of the people of Aulë the Smith", the
chief of the Istari, came first and was clad in white; he was "great in craft" and long
studied the lore of the Rings. This city-state shows his early dwelling in the West, before
the fall of Isengard: a slender white tower of fair stone with a balcony and a palantír
that glows white (animated), a smithy of Aulë's craft with a glowing forge (animated fire
and smoke), a library hall, a circle of orchards and green lawns, a stone bridge over a
clear stream, white banners, and the Istar himself in white.
The bridge and the tower door face the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, gable, hipped, cyl, cone, lathe, terrain_polar, blob, strut,
                  sphere, T, near_path, ring, crenels, window_row)
from city_common import (wizard, fx, tree, scatter_forest, banner, barrel, crate, person, fence, plate)


def ground(x, y):
    z = 0.8 + 0.4 * math.sin(x * 0.3) * math.cos(y * 0.25)
    z += 2.2 * math.exp(-((x) ** 2 + (y - 6) ** 2) / 140.0)
    if -13.0 < y < -9.0:                  # the stream
        z = min(z, 0.25)
    return z


PATH = [(0, -31), (0, -15), (0, -6), (0, 0)]


def build(b):
    material('lawn', h('6c9a42'), zramp=[(-1, h('6a963f')), (2, h('78a448'))], noise=0.4)
    material('road', h('c8c0aa'), h('b8b09a'), noise=2.0)
    material('whitestone', h('ecebe6'), h('dcdbd5'), noise=1.5, courses=0.7, course_dark=0.92)
    material('greystone', h('a6a49e'), h('94928c'), noise=2.0, courses=0.5, course_dark=0.85)
    material('slate', h('4c5560'), h('5a6370'), noise=2.0)
    material('stream', h('5a9ab8'), h('6aaac8'), noise=1.0, ao=False, spec=0.7, refl=50)
    material('whiterobe', h('f2f2ee'), h('e2e2dc'), noise=1.5)
    material('skin', h('d8ad8a'))
    material('beard', h('e2dfd8'))
    material('darkwood', h('3d2c1d'))
    material('orchard', h('4f7d2e'), h('5e8c36'), noise=1.5)
    material('apple', h('c0392b'))
    material('palantir', h('e8f4ff'), emission=2.5, ao=False)
    material('forgefire', h('ff8a2a'), emission=3.0, ao=False)
    material('banner', h('f4f4f0'), h('e4e4de'), noise=2.0)
    material('cloth', h('7a6a58'), h('8a7a66'), noise=3.0)
    material('iron', h('3a3a3e'))

    terrain_polar(b, ground, lambda x, y, z, s: 'road' if near_path(x, y, PATH, 1.4) else 'lawn',
                  R=31, cy=2, nr=36, na=120)
    # the stream across the front, above the ground plane
    pts = []
    for y in (-13.0, -9.0):
        hw = math.sqrt(max(0.0, 30.4 ** 2 - (y - 2.0) ** 2))
        pts.append(hw)
    plate(b, 'stream', [(-pts[0], -13.0), (pts[0], -13.0), (pts[1], -9.0), (-pts[1], -9.0)], -0.4, 0.62)
    # the bridge
    for i in range(11):
        y = -14.5 + 7.0 * i / 10
        z = 0.7 + 0.8 * math.sin(math.pi * i / 10)
        box(b, 'whitestone', 0, y, z - 0.3, 3.4, 0.75, 0.4)
        for s in (-1, 1):
            box(b, 'whitestone', s * 1.6, y, z + 0.1, 0.22, 0.75, 0.5)

    # --- the white tower
    TX, TY = 0.0, 6.0
    tz = ground(TX, TY) - 0.3
    lathe(b, 'whitestone', [(5.2, 0), (5.2, 1.5), (3.4, 2.4), (3.0, 20.0), (3.6, 20.6), (3.6, 21.4), (2.8, 21.4),
                            (2.6, 27.0), (0, 27.0)], n=24, x=TX, y=TY, z=tz, smooth=False)
    crenels(b, 'whitestone', 3.5, tz + 21.4, 0, 360, size=0.5, h=0.6, step=1.2, x=TX, y=TY, depth=0.4)
    lathe(b, 'slate', [(2.9, 0), (1.6, 3.0), (0.3, 6.2), (0, 6.6)], n=20, x=TX, y=TY, z=tz + 27.0, smooth=False)
    for k, zz in enumerate((5.0, 9.5, 14.0, 18.0, 24.0)):
        for a in (250, 290, 70, 160):
            ar = math.radians(a + 20 * k)
            r = 3.15 if zz < 21 else 2.75
            box(b, 'window', TX + r * math.cos(ar), TY + r * math.sin(ar), tz + zz, 0.55, 0.12, 1.4, rz=a + 20 * k + 90)
    box(b, 'window', TX, TY - 3.5, tz + 1.0, 1.6, 0.15, 3.0)
    # the palantír on a pedestal in the top room's balcony
    cyl(b, 'greystone', TX, TY - 3.0, tz + 21.4, 0.35, 1.0, n=8)
    sphere(b, 'palantir', TX, TY - 3.0, tz + 22.8, 0.55, n=10, rings=7)
    fx(b, 'Palantir', (TX, TY - 3.0, tz + 22.8), 'MAGIC_WHITE')
    for s in (-1, 1):
        banner(b, 'darkwood', 'banner', TX + s * 2.0, TY - 1.5, tz + 33.0, h=3.5, w=1.0, ch=2.0, rz=0)

    # --- Aulë's smithy: stone forge hall with a glowing hearth and anvil
    fxp, fyp = -10.0, -1.0
    fz = ground(fxp, fyp) - 0.2
    box(b, 'greystone', fxp, fyp, fz, 7.0, 5.0, 3.4)
    gable(b, 'slate', fxp, fyp, fz + 3.4, 7.0, 5.0, 2.2, overhang=0.4)
    box(b, 'greystone', fxp + 2.6, fyp + 1.4, fz, 1.6, 1.6, 8.0)
    fx(b, 'ForgeSmoke', (fxp + 2.6, fyp + 1.4, fz + 8.6), 'SMOKE')
    box(b, 'window', fxp, fyp - 2.52, fz, 2.4, 0.1, 2.4)
    box(b, 'forgefire', fxp - 0.2, fyp - 2.0, fz + 0.2, 1.4, 0.6, 0.6)
    fx(b, 'Forge', (fxp - 0.2, fyp - 2.6, fz + 0.9), 'BRAZIER')
    box(b, 'iron', fxp + 1.8, fyp - 3.8, fz + 0.6, 1.0, 0.45, 0.35)
    cyl(b, 'iron', fxp + 1.8, fyp - 3.8, fz, 0.2, 0.6, n=6)
    for k in range(3):
        barrel(b, 'darkwood', fxp - 3.0 + 0.9 * k, fyp - 3.6, fz + 0.2, 0.38, 0.75)

    # --- the library hall of lore
    lx, ly = 10.5, 0.0
    lz = ground(lx, ly) - 0.2
    box(b, 'whitestone', lx, ly, lz, 8.0, 5.0, 4.0)
    hipped(b, 'slate', lx, ly, lz + 4.0, 8.0, 5.0, 2.4, overhang=0.4)
    window_row(b, 'window', lx - 3.4, ly - 2.52, lx + 3.4, ly - 2.52, lz + 1.4, 5, w=0.6, h=1.6, out=0.0)
    for k in range(5):
        cyl(b, 'whitestone', lx - 3.6 + 1.8 * k, ly - 3.4, lz, 0.3, 4.0, n=8)
    box(b, 'whitestone', lx, ly - 3.4, lz + 4.0, 8.4, 1.2, 0.4)

    # --- Curumo in white on the bridge-head, his scholars, orchards in a ring
    wizard(b, 1.8, -5.0, ground(1.8, -5.0), s=1.45, robe='whiterobe', hat=None, beard='beard', staff='darkwood')
    for (x, y) in ((-6.5, -6.5), (8.0, -6.0)):
        person(b, x, y, ground(x, y), s=0.95, robe='cloth', skin='skin')
    for k in range(22):
        a = 2 * math.pi * k / 22
        if 245 < math.degrees(a) < 295:
            continue
        x, y = 19.5 * math.cos(a), 6.0 + 16.0 * math.sin(a)
        if not -14.5 < y:
            continue
        z = ground(x, y)
        tree(b, x, y, z - 0.2, h=5.0, r=1.8, leaves='orchard', trunk='darkwood', crowns=2)
        for j in range(3):
            sphere(b, 'apple', x + b.rng.uniform(-1.2, 1.2), y - 1.0, z + 3.0 + b.rng.uniform(0, 1.5), 0.18, n=6, rings=4)
    fence(b, 'whitestone', [(-14.0, -7.5), (-2.5, -7.5)], h=0.8, step=1.2)
    fence(b, 'whitestone', [(2.5, -7.5), (14.0, -7.5)], h=0.8, step=1.2)
    scatter_forest(b, 30, -31, 31, -29, 33, ground, avoid=((-22, 22, -14, 24),), min_dist=3.2, max_r=30.5,
                   h=(5.5, 8.0), r=(1.7, 2.4), leaves='orchard', trunk='darkwood', pines=0.3)


PREVIEW = [((8, -40, 26), (0, 2, 12), 45)]
