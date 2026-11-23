"""Smaug's Lair: the desolated Front Gate of Erebor and the dragon on his hoard.

The Hobbit: Smaug "came down the mountain ... and wrecked the Front Gate"; he lay "on a
mighty heap of treasure", "a vast red-golden dragon", wreathed in smoke; around the
mountain stretched "the Desolation of the Dragon", bare and burnt, with the ruins of Dale.
Films: the colossal dwarf statues flanking the gate, the River Running issuing from it.
Modelled: the dark flank of the Lonely Mountain with the great square gate, its statues of
dwarf-kings broken; a river of gold spilling out of the gate onto a hoard where Smaug lies
coiled, smoke and embers rising from his nostrils (animated), gold glitter on the hoard
(animated); the scorched Desolation in front with dead trees, bones, a broken bridge.
The gate faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, gable, cyl, cone, lathe, terrain_polar, blob, strut, sphere,
                  T, near_path, curve)
from city_common import (great_dragon, fx, dead_tree, ruin_wall, ruin_column, spire, plate)


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = 0.6 + 0.4 * math.sin(x * 0.33) * math.cos(y * 0.3)
    # the mountain flank behind the gate
    if y > 2.0:
        t = sm((y - 2.0) / 22.0)
        z = max(z, 0.6 + 30.0 * t * math.exp(-(x / 26.0) ** 4))
    # the gate terrace in front of the doors
    if -4 < y < 6 and abs(x) < 9:
        z = min(z, 1.2)
    return z


def build(b):
    material('ash', h('5a5248'), zramp=[(-1, h('5a5046')), (2, h('6a6052')), (6, h('5c5650')), (16, h('7a7670')),
                                        (28, h('c8ccd0'))], slope_color=h('4a4642'), slope_start=0.5, noise=0.6)
    material('gatestone', h('6c6a66'), h('5a5854'), noise=2.0, courses=0.9, course_dark=0.82)
    material('darkstone', h('3a3836'), h('2e2c2a'), noise=2.0)
    material('gold', h('e0b040'), h('c8952c'), noise=3.0, spec=1.0, refl=60)
    material('gem', h('3ab0d8'), h('c8304a'), noise=12.0, spec=1.0, refl=80)
    material('dragon', h('9a2e1c'), h('b8442a'), noise=6.0, spec=0.5, refl=20)
    material('dragonbelly', h('c8902a'), h('b07a22'), noise=4.0, spec=0.7, refl=30)
    material('dragonwing', h('6a2014'), h('7a2a1a'), noise=4.0)
    material('horn', h('2a2420'))
    material('eye', h('ffd040'), emission=2.0, ao=False)
    material('bone', h('d8d0bc'), h('c8bea8'), noise=3.0)
    material('deadwood', h('2a2420'), h('3a3028'), noise=3.0)
    material('river', h('4a6a78'), h('5a7a88'), noise=1.0, ao=False)

    terrain_polar(b, ground, lambda x, y, z, s: 'ash', R=31, cy=2, nr=40, na=130)

    # --- the gate: a square portal in the cliff, lintel, flanking broken statues
    GY = 6.0
    box(b, 'gatestone', 0, GY + 2.0, 0.0, 22.0, 4.0, 18.0)          # cliff face block
    box(b, 'window', 0, GY - 0.05, 1.0, 8.0, 0.2, 10.5)             # the dark gate opening
    box(b, 'gatestone', 0, GY - 0.6, 11.5, 11.0, 1.4, 1.6)          # lintel
    box(b, 'gatestone', 0, GY - 0.7, 13.1, 12.0, 1.6, 0.8)
    for s in (-1, 1):
        box(b, 'gatestone', s * 4.8, GY - 0.5, 0.0, 1.6, 1.2, 11.5)  # jambs
        # a dwarf-king statue, broken off at the chest
        sx = s * 8.8
        box(b, 'gatestone', sx, GY - 1.0, 0.0, 4.0, 3.0, 2.0)
        lathe(b, 'gatestone', [(1.7, 0), (1.8, 3.0), (1.5, 6.5), (1.2, 7.4), (0, 7.4)], n=10, x=sx, y=GY - 1.0, z=2.0,
              smooth=False, jitter=0.08)
        lathe(b, 'gatestone', [(1.3, 0), (1.1, 1.6), (0.6, 3.6), (0, 4.0)], n=8, x=sx, y=GY - 2.2, z=7.0,
              smooth=False, jitter=0.1)                              # the stone beard
        strut(b, 'gatestone', (sx + s * 1.2, GY - 1.6, 7.6), (sx + s * 1.6, GY - 3.0, 3.5), 0.55, 0.45, n=6)
        for k in range(4):                                           # fallen pieces
            blob(b, 'gatestone', sx + s * b.rng.uniform(1.5, 4.0), GY - b.rng.uniform(3.5, 7.0), 0.4,
                 b.rng.uniform(0.6, 1.2), n=6, rings=4, squash=0.7, jitter=0.3)
    # the river Running issuing from the gate under a broken bridge
    plate(b, 'river', [(-2.2, GY - 1.0), (2.2, GY - 1.0), (3.4, -10.0), (5.5, -28.0), (1.0, -29.0), (-1.4, -10.0)],
          0.6, 0.62)
    for (y, hh) in ((-12.0, 1.8), (-15.5, 1.2)):
        box(b, 'gatestone', -1.0, y, 0.6, 1.2, 1.2, hh)
        box(b, 'gatestone', 4.3, y - 0.4, 0.6, 1.2, 1.2, hh * 0.7)
    box(b, 'gatestone', 1.6, -12.0, 2.4, 3.8, 1.6, 0.5, rz=8)

    # --- the hoard spilling out of the gate, and Smaug upon it
    for k in range(55):
        x, y = b.rng.uniform(-11, 11), b.rng.uniform(-11, 5)
        if math.hypot(x / 1.2, y + 3) > 9.5:
            continue
        r = b.rng.uniform(0.9, 2.2)
        blob(b, 'gold', x, y, 0.0, r, n=8, rings=4, squash=0.45, jitter=0.3)
    for k in range(120):
        x, y = b.rng.uniform(-11, 11), b.rng.uniform(-11, 5)
        sphere(b, 'gold' if k % 5 else 'gem', x, y, ground(x, y) + 0.3 + b.rng.uniform(0, 0.6), b.rng.uniform(0.15, 0.32),
               n=6, rings=4, squash=0.4 if k % 3 else 1.0)
    for k in range(10):                                              # cups, a crown, shields
        x, y = b.rng.uniform(-8, 8), b.rng.uniform(-9, 2)
        lathe(b, 'gold', [(0.2, 0), (0.08, 0.3), (0.08, 0.5), (0.35, 0.8), (0.3, 1.0), (0, 0.9)], n=8, x=x, y=y,
              z=ground(x, y) + 0.4)
    nose = great_dragon(b, 0.5, -3.0, 1.6, s=2.05, rz=-12)
    fx(b, 'DragonBreath', nose, 'DRAGON_SMOKE')
    for k, (x, y) in enumerate(((-7.0, -6.0), (6.5, -7.5), (-4.0, 1.5), (7.5, 0.0))):
        fx(b, 'Gold_%d' % k, (x, y, 1.6), 'GOLD_GLITTER')

    # --- the Desolation: dead trees, bones, ruins of Dale's outlying houses, spires of rock
    for (x, y) in ((-18, -8), (-22, -16), (-14, -20), (17, -10), (21, -18), (13, -22), (-25, 2), (25, 4)):
        dead_tree(b, 'deadwood', x, y, ground(x, y) - 0.2, h=b.rng.uniform(3.5, 5.5))
    for k in range(6):
        x, y = b.rng.uniform(-20, 20), b.rng.uniform(-24, -12)
        curve(b, 'bone', [(x, y, 0.5), (x + 1.2, y + 0.3, 1.1), (x + 2.4, y, 0.5)], 0.12, 0.08, n=5)
    for (x, y, rz) in ((-16.0, -24.0, 20), (14.0, -25.0, -15)):
        ruin_wall(b, 'gatestone', x, y, ground(x, y) - 0.3, 6.0, 2.6, 0.7, rz=rz)
        ruin_column(b, 'gatestone', x + 2.0, y + 2.0, ground(x, y), h=3.0)
    for (x, y, hh) in ((-26, -8, 6), (27, -6, 7), (-22, 14, 9), (23, 15, 8)):
        spire(b, 'darkstone', x, y, ground(x, y) - 0.5, hh, 2.0)


PREVIEW = [((6, -34, 20), (0, -1, 6), 45)]
