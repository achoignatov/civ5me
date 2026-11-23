"""Himling, the isle that was once the hill of Himring (after the drowning of Beleriand).

The Silmarillion: Maedhros, eldest son of Fëanor, held "the great hill of Himring", "bare
of trees, wide and flat upon its summit, and surrounded by many lesser hills", with his
fortress upon it, the Hill of Ever-cold; after the War of Wrath its top remained above the
sea as the isle of Himling. Maps of the Third Age show it off the coast of Lindon.
Modelled: a broad, bare, flat-topped isle of cold grey-green turf rising from the sea, the
ruined fortress of Maedhros on its summit: broken curtain walls and towers of pale stone,
the stump of the great keep with a beacon still burning (animated), the eight-rayed star of
Fëanor's house carved on the gate, a stair down to a sheltered quay, and spray on the rocks.
The gate faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, cyl, cone, lathe, terrain_polar, blob, strut, sphere, T, crenels, ring)
from city_common import (fx, ruin_wall, ruin_column, boat, standing_stone, plate)


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    r = math.hypot(x / 1.1, (y - 3.0))
    z = -1.4 + 11.0 * sm((22.0 - r) / 7.0) + 0.5 * math.sin(x * 0.5) * math.cos(y * 0.5)
    for (hx, hy) in ((-18, -8), (18, -6), (-14, 16), (15, 17)):          # lesser hills
        z = max(z, -1.4 + 5.0 * math.exp(-((x - hx) ** 2 + (y - hy) ** 2) / 14.0))
    return z


def build(b):
    material('isle', h('6a7a5a'), zramp=[(-2, h('8a8678')), (0.6, h('9a9484')), (1.8, h('6a7a58')), (9, h('7a866a'))],
             slope_color=h('7a7870'), slope_start=0.55, noise=1.0)
    material('sea', h('2c5e7c'), h('366a88'), noise=1.0, ao=False, spec=0.8, refl=60)
    material('palestone', h('cfcabc'), h('bdb8aa'), noise=2.0, courses=0.6, course_dark=0.86)
    material('rock', h('7e7c76'), h('6e6c66'), noise=2.5)
    material('star', h('e8d070'), spec=0.9, refl=40)
    material('wood', h('6a5034'))
    material('sail', h('e0dcd0'))
    material('flame', h('ffb040'), emission=4.0, ao=False)

    terrain_polar(b, ground, lambda x, y, z, s: 'isle', R=31, cy=2, nr=42, na=130, edge=0.12)
    lathe(b, 'sea', [(30.0, -1.0), (30.4, 0.15), (0, 0.15)], n=96, y=2.0, smooth=False)
    TZ = 9.5
    CX, CY = 0.0, 3.0

    # --- the curtain wall: broken ring with towers
    R = 11.0
    for a0, a1 in ((285, 340), (350, 420), (440, 500), (515, 555)):
        ring(b, 'palestone', R - 1.0, R, TZ - 1.0, 4.2, a0, a1, n=24, x=CX, y=CY, top=True)
        crenels(b, 'palestone', R - 0.5, TZ + 3.2, a0 + 2, a1 - 2, size=0.5, h=0.5, step=1.4, x=CX, y=CY, depth=0.5)
    for k, a in enumerate((290, 345, 30, 90, 150, 210)):
        ar = math.radians(a)
        x, y = CX + R * math.cos(ar), CY + R * math.sin(ar)
        hh = 6.5 if k % 2 else 3.5
        cyl(b, 'palestone', x, y, TZ - 1.0, 1.7, hh, n=10)
        if k % 2:
            crenels(b, 'palestone', 1.6, TZ - 1.0 + hh, 0, 360, size=0.4, h=0.45, step=0.9, x=x, y=y, depth=0.4)
    for k in range(10):   # rubble from the broken stretches
        a = math.radians(b.rng.choice((345, 425, 505, 270)) + b.rng.uniform(-6, 6))
        rr = R + b.rng.uniform(-2.0, 2.5)
        blob(b, 'palestone', CX + rr * math.cos(a), CY + rr * math.sin(a), ground(CX + rr * math.cos(a), CY + rr * math.sin(a)) - 0.3,
             b.rng.uniform(0.6, 1.1), n=6, rings=4, squash=0.6, jitter=0.25)
    # the gate with the star of Fëanor
    gy = CY - R
    for s in (-1, 1):
        box(b, 'palestone', s * 2.4, gy, TZ - 1.0, 2.4, 2.4, 7.5)
    box(b, 'palestone', 0, gy, TZ + 4.5, 7.2, 2.4, 1.4)
    for k in range(8):
        a = math.pi * 2 * k / 8
        strut(b, 'star', (0, gy - 1.25, TZ + 5.2), (1.0 * math.cos(a), gy - 1.25, TZ + 5.2 + 1.0 * math.sin(a)), 0.1, 0.0, n=4)
    # --- the stump of the great keep, the beacon on its top
    box(b, 'palestone', CX, CY + 2.0, TZ - 0.5, 8.0, 7.0, 9.0)
    for (x, y, hh) in ((-3.2, CY + 5.0, 13.0), (3.0, CY + 5.2, 11.5), (-3.6, CY - 1.2, 10.5)):
        box(b, 'palestone', x, y, TZ + 8.5, 1.6, 1.6, hh - 8.5)
    ruin_wall(b, 'palestone', CX, CY - 1.3, TZ + 8.5, 6.5, 2.4, 0.8)
    lathe(b, 'rock', [(0.9, 0), (1.1, 0.6), (0.4, 0.8), (0, 0.8)], n=10, x=CX + 1.0, y=CY + 2.0, z=TZ + 8.5)
    fx(b, 'Beacon', (CX + 1.0, CY + 2.0, TZ + 9.6), 'BRAZIER')
    for k in range(5):
        ruin_column(b, 'palestone', -6.0 + 3.0 * k, CY - 5.5, TZ - 0.3, h=2.0 + (k % 3), r=0.45)

    # --- the stair down to the quay, the quay, a grey ship, rocks and spray
    for k in range(14):
        t = k / 13
        x, y = 0.0 + 3.0 * t, gy - 2.0 - 9.0 * t
        box(b, 'palestone', x, y, ground(x, y) - 0.3, 2.6, 1.0, 0.6)
    box(b, 'palestone', 4.5, -19.5, -0.2, 9.0, 3.0, 0.9)
    boat(b, 4.0, -23.0, 0.15, rz=0, s=1.6, hull='palestone', sail='sail', mast=True)
    for k in range(22):
        a = 2 * math.pi * k / 22
        x, y = 23.0 * math.cos(a), 3.0 + 21.0 * math.sin(a)
        blob(b, 'rock', x, y, -0.6, b.rng.uniform(1.0, 2.0), n=7, rings=4, squash=0.8, jitter=0.3)
    for k, (x, y) in enumerate(((-20.0, -12.0), (21.0, 10.0), (-18.0, 18.0))):
        fx(b, 'Spray_%d' % k, (x, y, 0.6), 'MIST')


PREVIEW = [((4, -40, 24), (0, 2, 8), 45)]
