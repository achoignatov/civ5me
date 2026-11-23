"""The Eagles' Eyrie in the eastern Misty Mountains.

The Hobbit, "Out of the Frying-Pan into the Fire": the eagles bore Thorin's company to
"their eyries ... a wide shelf of rock on the mountain-side", where "a great fire" was lit
and they feasted on mutton; the Lord of the Eagles; the pine woods below, where the wargs
had their glade. Films: a lone rock pinnacle above the trees, the eagles setting the
company down at dawn.
Modelled: one mighty pinnacle of grey rock rising out of the pine forest, a broad shelf
near the top with the Eagle-lord's great nest of branches, a fire burning on the ledge
(animated), eagles perched along the ledges and two soaring overhead, the dwarves' small
figures by the fire, wisps of cloud about the summit (animated), and the burnt clearing of
the wargs below.
The shelf faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, cyl, cone, lathe, terrain_polar, blob, strut, sphere, T, curve)
from city_common import (eagle, eagle_flying, fx, spire, scatter_forest, campfire, person, dead_tree)

PX, PY = 0.0, 5.0


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = 0.8 + 0.6 * math.sin(x * 0.35) * math.cos(y * 0.3)
    z += 5.0 * math.exp(-((x - PX) ** 2 + (y - PY) ** 2) / 120.0)
    return z


def build(b):
    material('forest', h('3f5a2e'), zramp=[(-1, h('3e582c')), (3, h('4a6232')), (5, h('6a6e5a'))],
             slope_color=h('5a5a52'), slope_start=0.6, noise=1.0)
    material('rock', h('8a8780'), zramp=[(0, h('6e6c66')), (12, h('8a8780')), (24, h('9a9892')), (30, h('d8dcdf'))],
             slope_color=h('7a7872'), slope_start=0.7, noise=2.0, courses=1.2, course_dark=0.88)
    material('shelf', h('8f8c84'), h('7f7c74'), noise=2.5)
    material('nest', h('6a5232'), h('54402a'), noise=6.0)
    material('eagle', h('5e4026'), h('6e4c2e'), noise=4.0)
    material('eaglehead', h('c8a050'), h('d8b060'), noise=3.0)
    material('beak', h('3a3028'))
    material('eye', h('e8c040'))
    material('pine', h('284430'), h('30503a'), noise=1.5)
    material('ash', h('3a3632'), h('4a4440'), noise=3.0)
    material('deadwood', h('1e1c1a'))
    material('flame', h('ffb040'), emission=4.0, ao=False)
    material('cloth', h('5a4a8a'), h('8a3a3a'), noise=8.0)
    material('skin', h('e0b896'))
    material('dwarfhood', h('3a6a3a'), h('8a6a2a'), noise=8.0)

    terrain_polar(b, ground, lambda x, y, z, s: 'ash' if math.hypot(x + 14, y + 12) < 6 else 'forest',
                  R=31, cy=2, nr=40, na=130)

    # --- the pinnacle
    pz = ground(PX, PY) - 1.0
    prof = [(11.0, 0), (9.2, 4.0), (7.6, 10.0), (6.6, 16.0), (6.2, 20.0), (7.4, 20.8), (7.6, 21.6), (5.2, 22.4),
            (4.4, 27.0), (2.6, 31.0), (0.8, 33.5), (0, 34.0)]
    lathe(b, 'rock', prof, n=16, x=PX, y=PY, z=pz, smooth=False, jitter=0.1)
    for k in range(9):
        a = 2 * math.pi * k / 9 + 0.3
        spire(b, 'rock', PX + 9.0 * math.cos(a), PY + 8.0 * math.sin(a), pz, b.rng.uniform(8, 14), 2.4,
              lean=b.rng.uniform(-6, 6), jitter=0.2)
    # the shelf: a broad flat ledge on the front
    SZ = pz + 21.6
    lathe(b, 'shelf', [(0, 0), (9.2, 0), (9.4, 0.8), (0, 0.8)], n=20, a0=200, a1=340, x=PX, y=PY + 1.0, z=SZ - 0.8)
    # the great nest of the Lord of the Eagles
    nx, ny = PX + 3.5, PY - 5.5
    lathe(b, 'nest', [(1.0, 0), (3.0, 0.2), (3.3, 1.1), (2.6, 1.3), (1.4, 0.6), (0, 0.6)], n=16, x=nx, y=ny, z=SZ,
          smooth=False, jitter=0.14)
    for j in range(14):
        a = 2 * math.pi * j / 14
        strut(b, 'nest', (nx + 2.6 * math.cos(a), ny + 2.6 * math.sin(a), SZ + 1.1),
              (nx + 3.8 * math.cos(a + 0.4), ny + 3.8 * math.sin(a + 0.4), SZ + 0.7), 0.12, 0.05, n=3)
    eagle(b, nx, ny + 0.5, SZ + 0.9, s=2.3, body='eagle', head='eaglehead', beak='beak', leg='beak', eye='eye')
    # the fire on the ledge and the dwarves (and a hobbit) around it
    fxp, fyp = PX - 3.5, PY - 6.0
    campfire(b, fxp, fyp, SZ, s=1.4, stone='shelf', log='deadwood', flame='flame')
    fx(b, 'Fire', (fxp, fyp, SZ + 0.6), 'CAMPFIRE')
    for k in range(7):
        a = 2 * math.pi * k / 7
        person(b, fxp + 1.8 * math.cos(a), fyp + 1.5 * math.sin(a), SZ, s=0.55 if k else 0.45, robe='cloth',
               skin='skin', hat='dwarfhood' if k else None)
    # eagles along the ledges and soaring
    for k in range(6):
        a = math.radians(205 + 26 * k)
        r = 8.4
        if k == 3:
            continue
        eagle(b, PX + r * math.cos(a), PY + 1.0 + r * math.sin(a), SZ, s=1.4, body='eagle', head='eaglehead', beak='beak',
              leg='beak', eye='eye', rz=math.degrees(a) + 90 + 180)
    eagle_flying(b, -12.0, -4.0, 30.0, s=4.0, rz=40, body='eagle', head='eaglehead', beak='beak')
    eagle_flying(b, 13.0, 12.0, 36.0, s=3.2, rz=-130, body='eagle', head='eaglehead', beak='beak')
    fx(b, 'Cloud_0', (PX - 2.0, PY + 2.0, pz + 33.0), 'MIST')
    fx(b, 'Cloud_1', (PX + 4.0, PY + 3.0, pz + 28.0), 'MIST')

    # --- the pine woods below, and the burnt glade of the wargs
    scatter_forest(b, 120, -31, 31, -29, 33, ground, avoid=((-10, 10, -4, 14), (-20, -8, -18, -6)), min_dist=2.3,
                   max_r=30.5, h=(6.0, 9.0), r=(1.3, 1.8), leaves='pine', kind='conifer')
    for (x, y) in ((-15, -10), (-12, -14), (-17, -13), (-13, -9)):
        dead_tree(b, 'deadwood', x, y, ground(x, y) - 0.2, h=5.0, r=0.22)


PREVIEW = [((6, -46, 30), (0, 2, 16), 45)]
