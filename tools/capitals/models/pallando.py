"""Pallando, the second Blue Wizard, who journeyed far into the South and East.

Tolkien (Unfinished Tales, "The Istari"; Peoples of Middle-earth): Pallando went with
Alatar "into the East" and "to the South"; their work was to bring help to the few who
rebelled against Sauron. No dwelling is described, so this city-state is a refuge in the
dry lands beyond Harad: a walled oasis around a spring-fed pool, a domed sanctuary of
white stone with a sea-blue dome and a lamp of blue light (animated), a colonnade,
date palms and the striped pavilions of the caravans that come to him.
The gate faces the camera (-Y).
"""
import math

from mathutils import Vector

from blib import (material, hexcol as h, box, gable, cyl, cone, lathe, terrain_polar, blob, strut, sphere,
                  T, near_path, dome, ring, crenels, curve)
from city_common import (wizard, tent, fx, person, plate, barrel, crate, water_disc)

CX, CY = 0.0, 4.0


def ground(x, y):
    z = 1.2 + 0.7 * math.sin(x * 0.17 + 1.0) * math.cos(y * 0.15)
    # dunes at the back and the sides
    z += 3.5 * math.exp(-((x + 22) ** 2 + (y - 20) ** 2) / 120.0) + 3.0 * math.exp(-((x - 23) ** 2 + (y - 18) ** 2) / 110.0)
    # the oasis hollow
    r = math.hypot(x - 7.0, y + 6.0)
    z -= 0.6 * math.exp(-(r / 4.5) ** 2)
    return z


def palm(b, x, y, z, hh=7.0, lean=8.0, rz=0.0):
    M = T(x, y, z, rz=rz)
    pts = []
    for k in range(7):
        t = k / 6
        pts.append(tuple(M @ Vector((math.sin(math.radians(lean)) * hh * t * t, 0, hh * t))))
    curve(b, 'palmtrunk', pts, 0.32, 0.2, n=6)
    top = pts[-1]
    for k in range(9):
        a = 2 * math.pi * k / 9
        p1 = (top[0] + 3.0 * math.cos(a), top[1] + 3.0 * math.sin(a), top[2] - 1.0)
        mid = (top[0] + 1.6 * math.cos(a), top[1] + 1.6 * math.sin(a), top[2] + 0.4)
        curve(b, 'palmleaf', [top, mid, p1], 0.38, 0.05, n=4)
    sphere(b, 'date', top[0], top[1], top[2] - 0.4, 0.45, n=7, rings=5)


def build(b):
    material('sand', h('d8b97a'), zramp=[(-1, h('cdb070')), (1, h('dbbd7e')), (4, h('e2c78a'))], noise=0.5)
    material('oasisgrass', h('7c9a40'), h('8aa84a'), noise=1.5)
    material('pool', h('2d8aa0'), h('3aa0b4'), noise=1.0, ao=False, spec=0.8, refl=60)
    material('whitestone', h('e8e0cc'), h('d6ccb6'), noise=2.0, courses=0.6, course_dark=0.9)
    material('mudbrick', h('c4a070'), h('b08c5e'), noise=3.0, courses=0.5, course_dark=0.85)
    material('bluetile', h('2a5fae'), h('3a76c4'), noise=4.0, spec=0.7, refl=30)
    material('gold', h('d6ac45'), h('c09434'), noise=2.0, spec=0.9, refl=40)
    material('palmtrunk', h('7a6040'), h('6a5034'), noise=6.0)
    material('palmleaf', h('4e7a2c'), h('5e8a34'), noise=3.0)
    material('date', h('8a4a22'))
    material('stripe', h('c8442a'), h('e8d8b0'), noise=12.0)
    material('canvas', h('e6dcc0'), h('d4c8a6'), noise=3.0)
    material('bluerobe', h('2a50a0'), h('3860b0'), noise=2.0)
    material('skin', h('b8835a'))
    material('beard', h('d8d4cc'))
    material('cloth', h('e0d2b0'), h('c8b890'), noise=3.0)
    material('darkwood', h('3d2c1d'))
    material('lantern', h('a8d8ff'), emission=3.0, ao=False)

    terrain_polar(b, ground, lambda x, y, z, s: 'oasisgrass' if math.hypot(x - 7, y + 6) < 7.5 else 'sand',
                  R=31, cy=2, nr=38, na=124)
    # the pool
    lathe(b, 'pool', [(4.6, -0.6), (4.6, 0.75), (0, 0.75)], n=32, x=7.0, y=-6.0, smooth=False)
    ring(b, 'whitestone', 4.6, 5.2, 0.2, 0.75, 0, 360, n=40, x=7.0, y=-6.0)
    fx(b, 'Spring', (7.0, -6.0, 0.6), 'MIST')

    # --- the sanctuary: square base, drum, blue dome, lamp
    bz = ground(CX, CY + 2) + 0.0
    box(b, 'whitestone', CX, CY + 2, bz - 0.4, 13.0, 11.0, 1.4)
    box(b, 'whitestone', CX, CY + 2, bz + 1.0, 10.0, 8.0, 6.0)
    for s in (-1, 1):
        for t in (-1, 1):
            cyl(b, 'whitestone', CX + s * 5.0, CY + 2 + t * 4.0, bz + 1.0, 0.9, 9.0, n=10)
            lathe(b, 'bluetile', [(1.0, 0), (1.0, 0.4), (0.6, 1.4), (0, 2.2)], n=10, x=CX + s * 5.0, y=CY + 2 + t * 4.0,
                  z=bz + 10.0, smooth=True)
    cyl(b, 'whitestone', CX, CY + 2, bz + 7.0, 4.2, 2.2, n=24)
    for k in range(12):
        a = 2 * math.pi * k / 12
        box(b, 'window', CX + 4.2 * math.cos(a), CY + 2 + 4.2 * math.sin(a), bz + 7.5, 0.6, 0.1, 1.2, rz=math.degrees(a) + 90)
    lathe(b, 'bluetile', [(4.4, 0), (4.5, 1.2), (4.0, 3.0), (2.8, 4.6), (1.0, 5.6), (0, 5.8)], n=28, x=CX, y=CY + 2,
          z=bz + 9.2, smooth=True)
    cyl(b, 'gold', CX, CY + 2, bz + 15.0, 0.1, 1.8, n=5)
    sphere(b, 'lantern', CX, CY + 2, bz + 17.2, 0.6, n=10, rings=6)
    fx(b, 'Lamp', (CX, CY + 2, bz + 17.2), 'MAGIC_BLUE')
    # pointed-arch portal and a colonnade in front
    box(b, 'bluetile', CX, CY + 2 - 4.05, bz + 1.0, 3.0, 0.15, 4.2)
    box(b, 'window', CX, CY + 2 - 4.12, bz + 1.0, 2.0, 0.1, 3.2)
    for k in range(7):
        x = CX - 6.0 + 2.0 * k
        cyl(b, 'whitestone', x, CY - 4.5, bz - 0.4, 0.35, 4.4, n=8)
    box(b, 'whitestone', CX, CY - 4.5, bz + 4.0, 13.4, 1.2, 0.6)
    wizard(b, CX + 2.4, CY - 6.0, ground(CX + 2.4, CY - 6.0), s=1.3, robe='bluerobe', hat='bluerobe', beard='beard',
           staff='darkwood')

    # --- the mud-brick enclosure with its gate, palms, pavilions
    R = 18.5
    for k in range(48):
        a0 = 360.0 * k / 48
        if abs(a0 - 270) < 9:
            continue
        ar = math.radians(a0)
        x, y = CX + R * math.cos(ar), CY + R * 0.92 * math.sin(ar)
        box(b, 'mudbrick', x, y, ground(x, y) - 0.4, 2.55, 0.9, 2.8, rz=a0 + 90)
        if k % 2 == 0:
            box(b, 'mudbrick', x, y, ground(x, y) + 2.4, 0.9, 0.95, 0.6, rz=a0 + 90)
    for s in (-1, 1):
        gx, gy = CX + s * 2.6, CY - R * 0.92
        box(b, 'mudbrick', gx, gy, ground(gx, gy) - 0.4, 1.8, 1.8, 5.0)
        dome(b, 'bluetile', gx, gy, ground(gx, gy) + 4.6, 1.0, n=10, rings=4)
    for (x, y, lean, rz) in ((2.5, -10.0, 10, 30), (11.5, -9.5, 12, -40), (12.5, -2.5, 6, 160), (3.0, -2.0, 9, 200),
                             (-8.5, -10.0, 8, 80), (-12.0, 8.0, 10, 120), (11.0, 11.0, 7, -60), (-4.0, -13.5, 11, 10),
                             (15.0, -12.0, 9, -20), (-15.0, -3.0, 10, 140)):
        palm(b, x, y, ground(x, y) - 0.1, hh=b.rng.uniform(6.0, 8.5), lean=lean, rz=rz)
    for k, (x, y) in enumerate(((-10, -5), (-12.5, 1.5), (-6, -12), (14.5, 4.5), (-22, -12), (22, -11), (-25, 4))):
        tent(b, 'stripe' if k % 2 else 'canvas', x, y, ground(x, y), r=2.4, h=2.9, n=8, door_mat='darkwood',
             pole='darkwood')
    for (x, y) in ((-3, -11), (-5, -9.5), (9.5, -12)):
        person(b, x, y, ground(x, y), s=0.95, robe='cloth', skin='skin')
    for k in range(6):
        barrel(b, 'darkwood', -8.0 + 0.9 * k, -15.0, ground(-8 + 0.9 * k, -15), 0.4, 0.8)
    for k in range(3):
        crate(b, 'canvas', 8.0 + k * 1.0, 13.0, ground(8 + k, 13), 0.8)


PREVIEW = [((8, -34, 18), (0, 0, 6), 45)]

# the walled oasis is laid out in ~20 units; scaled to fill the tile (pipeline FILL)
FILL = 1.3
