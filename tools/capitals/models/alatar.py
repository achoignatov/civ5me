"""Alatar, one of the two Blue Wizards (Ithryn Luin) who went into the East.

Tolkien (Unfinished Tales, letters): the Blue Wizards, Alatar and Pallando, "went east with
Curunír, but never returned"; they were clad in sea-blue and were to stir up rebellion
against Sauron among the peoples of the East.
There is no description of a dwelling, so the city-state is an eastern sanctuary in the
steppes of Rhûn: a sea-blue tower on a rocky table-mountain, reached by a stair, its top
crowned by a blue lantern of light (animated glow); round felt tents of the Easterling
tribes he swayed, horse lines, prayer-flag lines, braziers and the steppe all around.
The stair faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, gable, cyl, cone, lathe, terrain_polar, blob, strut, sphere,
                  T, near_path, dome, ring, crenels)
from city_common import (wizard, yurt, horse, fx, standing_stone, person, fence, spire, banner)

MX, MY = 0.0, 6.0


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = 0.5 + 0.45 * math.sin(x * 0.25) * math.cos(y * 0.2)
    r = math.hypot((x - MX) / 1.15, y - MY)
    z += 8.5 * sm((10.5 - r) / 3.0)                 # the table mountain (mesa)
    return z


STAIR = [(0, -30), (0, -9), (0, -3.6)]


def build(b):
    material('steppe', h('9c9a5e'), zramp=[(-1, h('9a985c')), (2, h('a6a266')), (6, h('8e8a68'))],
             slope_color=h('8d7a5e'), slope_start=0.6, noise=0.5)
    material('road', h('b09c74'), h('9c8a64'), noise=2.0)
    material('mesa', h('9a7c5e'), h('86684c'), noise=3.0, courses=0.9, course_dark=0.85)
    material('bluetile', h('2f62a8'), h('3a78c0'), noise=4.0, spec=0.7, refl=30)
    material('whitestone', h('ddd6c6'), h('cbc3b0'), noise=2.0, courses=0.6, course_dark=0.88)
    material('felt', h('d6c9a8'), h('c4b694'), noise=3.0)
    material('feltblue', h('3a5f9a'), h('4a70ac'), noise=3.0)
    material('darkwood', h('3d2c1d'))
    material('bluerobe', h('2c56a0'), h('3a66b0'), noise=2.0)
    material('skin', h('d8ad8a'))
    material('beard', h('d8d4cc'))
    material('horse', h('6a4a30'), h('5a3c24'), noise=3.0)
    material('mane', h('2a1e16'))
    material('cloth', h('8a3a2a'), h('a04a30'), noise=3.0)
    material('flag', h('3a78c0'), h('e0c050'), noise=9.0)
    material('gold', h('d6ac45'), h('c09434'), noise=2.0, spec=0.9, refl=40)
    material('lantern', h('a8d8ff'), emission=3.0, ao=False)

    def mat(x, y, z, s):
        if near_path(x, y, STAIR, 1.4) and z < 8.8:
            return 'road'
        return 'steppe'

    terrain_polar(b, ground, mat, R=31, cy=2, nr=40, na=128)
    # mesa cliffs: a ring of rock blocks around the table
    for k in range(34):
        a = 2 * math.pi * k / 34
        if abs(math.degrees(a) - 270) < 12:
            continue
        x, y = MX + 10.6 * 1.15 * math.cos(a), MY + 10.6 * math.sin(a)
        hh = 8.6 + b.rng.uniform(-0.8, 0.9)
        lathe(b, 'mesa', [(1.9, -0.5), (1.7, hh * 0.4), (1.55, hh * 0.85), (1.1, hh), (0, hh + 0.1)], n=6,
              x=x, y=y, z=0.0, smooth=False, jitter=0.22)
    TZ = 9.0
    # the stair up the mesa
    for i in range(16):
        y = MY - 15.0 + i * 0.62
        box(b, 'whitestone', 0, y, 0.0, 2.8, 0.7, 0.4 + 0.57 * i)

    # --- the blue tower: tiers of white stone banded with sea-blue tile, onion dome, lantern
    lathe(b, 'whitestone', [(5.0, 0), (5.0, 1.2), (4.2, 1.2), (4.2, 0)], n=24, x=MX, y=MY, z=TZ, smooth=False)
    tiers = [(3.6, 5.0), (2.9, 4.5), (2.3, 4.0)]
    z = TZ + 1.2
    for i, (r, hh) in enumerate(tiers):
        cyl(b, 'whitestone', MX, MY, z, r, hh, n=16)
        ring(b, 'bluetile', r, r + 0.12, z + hh * 0.55, 0.6, 0, 360, n=32, x=MX, y=MY)
        for k in range(8):
            a = 2 * math.pi * k / 8 + 0.2 * i
            box(b, 'window', MX + r * math.cos(a), MY + r * math.sin(a), z + hh * 0.2, 0.5, 0.1, 1.1,
                rz=math.degrees(a) + 90)
        z += hh
        ring(b, 'bluetile', r - 0.2, r + 0.5, z, 0.35, 0, 360, n=32, x=MX, y=MY)
        z += 0.35
    lathe(b, 'bluetile', [(2.5, 0), (2.9, 0.9), (2.6, 2.2), (1.5, 3.4), (0.4, 4.3), (0.1, 5.2), (0, 5.4)],
          n=20, x=MX, y=MY, z=z, smooth=True)
    cyl(b, 'gold', MX, MY, z + 5.4, 0.08, 1.6, n=5)
    sphere(b, 'lantern', MX, MY, z + 7.2, 0.55, n=10, rings=6)
    fx(b, 'Lantern', (MX, MY, z + 7.2), 'MAGIC_BLUE')
    # the blue wizard on the stair landing, braziers at the stair foot and top
    wizard(b, 1.6, MY - 5.0, TZ, s=1.3, robe='bluerobe', hat='bluerobe', beard='beard', staff='darkwood')
    for (x, y, zz) in ((-2.2, -9.4, ground(-2.2, -9.4)), (2.2, -9.4, ground(2.2, -9.4)), (-2.2, MY - 5.6, TZ),
                       (2.2, MY - 5.6, TZ)):
        cyl(b, 'whitestone', x, y, zz, 0.35, 1.4, n=8)
        lathe(b, 'gold', [(0.15, 0), (0.6, 0.4), (0.6, 0.55), (0, 0.55)], n=10, x=x, y=y, z=zz + 1.4)
        fx(b, 'Brazier_%d_%d' % (int(x * 10), int(y * 10)), (x, y, zz + 2.0), 'BRAZIER')

    # --- the camp of the Easterlings on the steppe below
    for k, (x, y) in enumerate(((-15, -6), (-19, 2), (-11, -14), (15, -7), (19, 1), (12, -15), (-21, -9),
                                 (22, -9), (-6, -19), (6, -20))):
        yurt(b, 'felt' if k % 3 else 'feltblue', x, y, ground(x, y) - 0.1, r=2.0, h=1.4, roof_mat='feltblue' if k % 2 else 'felt',
             door_mat='cloth')
    for k in range(6):
        horse(b, -6.0 + 2.4 * k, -24.0 + (k % 2), ground(-6.0 + 2.4 * k, -24.0), s=1.15, rz=90 + b.rng.uniform(-15, 15))
    fence(b, 'darkwood', [(-8.0, -26.0), (8.0, -26.0)], h=1.1, step=1.6)
    # prayer-flag lines from the mesa to poles in the camp
    for (x1, y1) in ((-15.0, -1.0), (15.0, -1.0), (-11.0, 15.0), (11.0, 15.0)):
        z1 = ground(x1, y1)
        cyl(b, 'darkwood', x1, y1, z1, 0.12, 5.0, n=5)
        x0, y0 = MX + 0.45 * x1, MY + 0.45 * (y1 - MY)
        z0 = TZ + 3.0
        for k in range(8):
            t = (k + 0.5) / 8
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            pz = z0 + (z1 + 5.0 - z0) * t - 1.2 * math.sin(math.pi * t)
            box(b, 'flag', px, py, pz - 0.6, 0.55, 0.04, 0.6, rz=math.degrees(math.atan2(y1 - y0, x1 - x0)))
    for (x, y) in ((-6, -12), (5, -13), (-3, -16)):
        person(b, x, y, ground(x, y), s=0.95, robe='cloth', skin='skin')
    for (x, y, hh) in ((-25, 12, 5.5), (25, 13, 4.5), (-27, -2, 3.5), (26, 4, 3.0)):
        spire(b, 'mesa', x, y, ground(x, y) - 0.5, hh, 2.2)


PREVIEW = [((10, -38, 24), (0, 4, 10), 45)]
