"""The Lossoth, the Snowmen of Forochel.

The Return of the King, Appendix A: "the Lossoth, the Snowmen of Forochel ... a strange
unfriendly people ... they build their houses in the snow"; they "have no iron", go on the
ice "with skates of bone" and have "carts without wheels" (sledges); King Arvedui sheltered
with them in the Ice Bay of Forochel, where the ship from Círdan was crushed by the ice.
Modelled: a camp on the shore of the frozen Ice Bay: domed snow-houses with entrance tunnels,
skin tents, a seal-oil fire (animated) with smoke, sledges and dog teams, racks of drying
fish, kayaks and holes in the ice, floes and pressure ridges of blue ice, a few stunted
firs and snowy hills behind, and the wreck of the Elvish ship locked in the ice.
The camp faces the camera (-Y).
"""
import math

from mathutils import Vector

from blib import (material, hexcol as h, box, gable, cyl, cone, lathe, terrain_polar, blob, strut, sphere, T,
                  dome, curve, near_path)
from city_common import (fx, tent, campfire, person, conifer, plate, spire)


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = 0.5 + 0.35 * math.sin(x * 0.35) * math.cos(y * 0.3)
    if y > 8:
        z += 7.0 * sm((y - 8) / 16.0) * (0.8 + 0.2 * math.sin(x * 0.3))     # snowy hills behind
    if y < -8:                                                             # the frozen bay
        z = max(0.2, z - 0.06 * (-8 - y))
    return z


def igloo(b, x, y, z, r=2.0, rz=0.0):
    dome(b, 'snowblock', x, y, z, r, n=14, rings=5, h=r * 0.85)
    ca, sa = math.cos(math.radians(rz - 90)), math.sin(math.radians(rz - 90))
    tx, ty = x + ca * r * 0.95, y + sa * r * 0.95
    lathe(b, 'snowblock', [(0.75, 0), (0.75, 0.55), (0.4, 0.95), (0, 1.0)], n=8, a0=0, a1=180,
          M=T(tx, ty, z, rz=rz - 90, rx=90))
    box(b, 'window', tx + ca * 0.6, ty + sa * 0.6, z, 0.8, 0.1, 0.8, rz=rz)
    box(b, 'ice', x, y - r * 0.7, z + r * 0.55, 0.45, 0.1, 0.35)


def build(b):
    material('snow', h('eef2f6'), zramp=[(-1, h('e6ecf0')), (2, h('eef2f6')), (6, h('f4f6f8'))],
             slope_color=h('c8d2da'), slope_start=0.6, noise=0.4)
    material('snowblock', h('e2eaf0'), h('d0dce6'), noise=3.0, courses=0.45, course_dark=0.9)
    material('seaice', h('b8d4e2'), h('a8c8da'), noise=1.5, spec=0.8, refl=70)
    material('ice', h('9cc8e0'), h('8ab8d4'), noise=2.0, spec=0.9, refl=80)
    material('water', h('2a4a5e'), ao=False, spec=0.8, refl=60)
    material('hide', h('8a6a4a'), h('7a5a3c'), noise=5.0)
    material('fur', h('d8ccb8'), h('c8baa4'), noise=4.0)
    material('bone', h('e8e0cc'))
    material('wood', h('6a5236'), h('5a4430'), noise=4.0)
    material('dog', h('6a6460'), h('d8d2c8'), noise=6.0)
    material('fish', h('a8b0b4'))
    material('skin', h('c89a70'))
    material('flame', h('ffb040'), emission=4.0, ao=False)
    material('stone', h('7a7a7a'))
    material('fir', h('2a4430'), h('344e38'), noise=1.5)
    material('elfwood', h('c8bca0'), h('b8ac90'), noise=3.0)
    material('sail', h('e0dcd0'))

    terrain_polar(b, ground, lambda x, y, z, s: 'seaice' if y < -9 else 'snow', R=31, cy=2, nr=38, na=124)

    # --- snow-houses and skin tents
    houses = [(-7.0, 2.0, 2.4, 10), (0.0, 5.0, 2.8, 0), (7.5, 2.5, 2.4, -10), (-12.0, -3.0, 2.0, 25), (12.5, -2.0, 2.0, -25),
              (-3.5, -3.5, 1.8, 5), (4.5, -4.0, 1.8, -5), (-14.0, 7.0, 2.0, 30), (14.0, 8.0, 2.0, -30)]
    for (x, y, r, rz) in houses:
        igloo(b, x, y, ground(x, y) - 0.2, r=r, rz=rz)
    for (x, y) in ((-3.0, 11.0), (4.5, 11.5), (10.0, 13.0)):
        tent(b, 'hide', x, y, ground(x, y), r=2.0, h=3.2, n=8, door_mat='fur', pole='bone')
    # the seal-oil fire, smoke, people in furs
    fz = ground(0, -1)
    campfire(b, 0.0, -1.0, fz, s=1.4, stone='stone', log='bone', flame='flame')
    fx(b, 'Fire', (0.0, -1.0, fz + 0.6), 'CAMPFIRE')
    fx(b, 'Smoke', (0.0, 5.0, ground(0, 5) + 3.0), 'SMOKE')
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        person(b, 2.2 * math.cos(a), -1.0 + 1.8 * math.sin(a), fz, s=0.95, robe='fur', skin='skin', hat='fur')
    # drying racks of fish
    for (x, y) in ((-9.0, -7.0), (9.5, -7.5)):
        for sd in (-1, 1):
            strut(b, 'bone', (x + sd * 1.2, y, ground(x, y)), (x + sd * 1.2, y, ground(x, y) + 2.2), 0.07, 0.05, n=4)
        strut(b, 'bone', (x - 1.2, y, ground(x, y) + 2.0), (x + 1.2, y, ground(x, y) + 2.0), 0.05, 0.05, n=4)
        for k in range(5):
            box(b, 'fish', x - 1.0 + 0.5 * k, y, ground(x, y) + 1.1, 0.16, 0.08, 0.8)

    # --- sledges and dog teams heading out onto the ice
    for (sx, sy, rz) in ((-5.0, -13.0, 10), (6.0, -15.0, -15)):
        sz = ground(sx, sy)
        M = T(sx, sy, sz, rz=rz)
        box(b, 'wood', 0, 0.0, 0.4, 1.4, 3.2, 0.2, M=M)
        for sd in (-1, 1):
            curve(b, 'bone', [tuple(M @ Vector(p)) for p in
                              ((sd * 0.6, 1.6, 0.05), (sd * 0.6, -1.4, 0.05), (sd * 0.6, -1.9, 0.6))], 0.06, 0.06, n=4)
        box(b, 'hide', 0, 0.5, 0.6, 1.2, 1.6, 0.5, M=M)
        for k in range(3):
            for sd in (-1, 1):
                p = M @ Vector((sd * 0.5, -3.2 - 1.3 * k, 0))
                sphere(b, 'dog', p[0], p[1], p[2] + 0.45, 0.32, n=7, rings=5, squash=0.8)
                sphere(b, 'dog', p[0], p[1] - 0.45, p[2] + 0.6, 0.18, n=6, rings=4)

    # --- the frozen bay: floes, pressure ridges, fishing holes, kayaks, the crushed Elvish ship
    for k in range(18):
        x, y = b.rng.uniform(-24, 24), b.rng.uniform(-27, -12)
        if math.hypot(x, y - 2) > 28.5:
            continue
        plate(b, 'ice', [(x - 1.5, y - 1.0), (x + 1.8, y - 0.8), (x + 1.2, y + 1.2), (x - 1.4, y + 0.9)],
              ground(x, y) - 0.1, 0.35)
    for k in range(10):
        x = -20 + 4.4 * k
        y = -22.0 + 2.0 * math.sin(k)
        if math.hypot(x, y - 2) > 28.5:
            continue
        spire(b, 'ice', x, y, ground(x, y) - 0.3, b.rng.uniform(1.5, 3.0), b.rng.uniform(1.0, 1.6), lean=b.rng.uniform(-25, 25),
              jitter=0.25)
    for (x, y) in ((-12.0, -17.0), (13.0, -19.0)):
        cyl(b, 'water', x, y, ground(x, y) + 0.02, 1.0, 0.05, n=12)
        box(b, 'hide', x + 2.2, y + 0.4, ground(x, y) + 0.05, 3.6, 0.6, 0.4, rz=40)       # a kayak
    # the ship of Círdan, crushed and tilted in the ice
    M = T(-15.0, -22.0, ground(-15, -22) - 0.3, rz=25, ry=12)
    for side in (-1, 1):
        plate(b, 'elfwood', [(-4.5, 0), (-3.0, side * 1.4), (3.0, side * 1.4), (4.8, 0)], 0.0, 1.4, M=M)
    strut(b, 'elfwood', tuple(M @ Vector((0, 0, 1.0))),
          tuple(M @ Vector((0.6, 0.3, 6.5))), 0.16, 0.1, n=5)
    box(b, 'sail', 0, 0, 3.0, 0.08, 2.0, 2.4, M=M @ T(0.4, 0.15, 0, ry=8))

    # --- stunted firs and rocks on the hills behind
    for k in range(26):
        x, y = b.rng.uniform(-26, 26), b.rng.uniform(12, 28)
        if math.hypot(x, y - 2) > 29.0:
            continue
        conifer(b, x, y, ground(x, y) - 0.2, h=b.rng.uniform(3.0, 4.5), r=0.9, leaves='fir', trunk='wood', tiers=3)


PREVIEW = [((4, -34, 18), (0, -2, 3), 45)]
