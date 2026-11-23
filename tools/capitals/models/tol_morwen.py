"""Tol Morwen, the isle of the Stone of the Hapless (after the drowning of Beleriand).

The Silmarillion / The Children of Húrin: Túrin was buried in Brethil "and they raised a
great grey stone" over him, the Stone of the Hapless, Talbor Hirion, carved in runes of
Doriath: "TÚRIN TURAMBAR DAGNIR GLAURUNGA" and beneath it "NÍENOR NÍNIEL"; Morwen died
beside it. "When Beleriand was broken, the stone stood still as an island in the sea,
Tol Morwen", and the seer Glirhuin sang that it would never be defiled by the sea.
Modelled: a green rocky isle rising from the sea, a ring of birches and a grassy mound with
the tall grey memorial stone and its pale runes on the summit, two lesser stones, the
remains of an Elvish wayside shrine, a cove with a small landing and an Elvish boat,
sea-spray against the rocks (animated) and gulls.
The stone faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, cyl, cone, lathe, terrain_polar, blob, strut, sphere, T, curve)
from city_common import (standing_stone, fx, tree, boat, spire, ruin_column, ruin_wall, eagle_flying)


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    r = math.hypot(x / 1.1, (y - 3.0) / 0.95)
    z = -1.2 + 8.5 * sm((21.0 - r) / 12.0) + 0.6 * math.sin(x * 0.5) * math.cos(y * 0.45)
    # the cove on the front-right
    z -= 3.0 * math.exp(-((x - 9.0) ** 2 + (y + 11.0) ** 2) / 20.0)
    return z


def build(b):
    material('isle', h('6a9a48'), zramp=[(-2, h('8a8a7a')), (0.6, h('b8ac88')), (1.6, h('6a9a48')), (6, h('5e8e42'))],
             slope_color=h('7a7a72'), slope_start=0.6, noise=0.8)
    material('sea', h('2e6a8a'), h('3a7a9a'), noise=1.0, ao=False, spec=0.8, refl=60)
    material('greystone', h('8e8c86'), h('7e7c76'), noise=2.5)
    material('rune', h('e8e4d0'), emission=0.3)
    material('birch', h('e0dcd0'), h('c8c4b8'), noise=6.0)
    material('birchleaf', h('8aa848'), h('9ab854'), noise=2.0)
    material('elfstone', h('d8d4c8'), h('c8c4b8'), noise=2.0)
    material('wood', h('8a6a44'))
    material('sail', h('e8e4d8'))
    material('eagle', h('e8e8e4'))       # gulls
    material('eaglehead', h('f2f2ee'))
    material('beak', h('e8b040'))

    terrain_polar(b, ground, lambda x, y, z, s: 'isle', R=31, cy=2, nr=40, na=130, edge=0.12)
    # the sea all around (above the ground plane)
    lathe(b, 'sea', [(30.0, -1.0), (30.4, 0.15), (0, 0.15)], n=96, y=2.0, smooth=False)

    # --- the Stone of the Hapless on the summit
    SX, SY = 0.0, 3.0
    sz = ground(SX, SY)
    box(b, 'greystone', SX, SY, sz - 0.6, 5.0, 3.0, 0.9)
    box(b, 'greystone', SX, SY, sz + 0.3, 3.2, 2.4, 8.0)                 # the great grey stone
    lathe(b, 'greystone', [(1.95, 0), (1.5, 1.4), (0.6, 2.4), (0, 2.6)], n=4, M=T(SX, SY, sz + 8.3, rz=45) @ T(0, 0, 0, s=(1.15, 0.85, 1.0)),
          smooth=False)
    for k in range(6):   # the runes on its face
        box(b, 'rune', SX + (-0.6 + 0.4 * (k % 4)), SY - 1.25, sz + 5.0 + 1.0 * (k // 4) + (k % 2) * 0.3,
            0.22, 0.1, 0.55)
    for k in range(4):
        box(b, 'rune', SX - 0.5 + 0.35 * k, SY - 1.25, sz + 2.4, 0.18, 0.1, 0.4)
    for (x, y, hh) in ((-3.8, SY + 1.5, 4.2), (3.6, SY + 1.8, 3.6)):
        standing_stone(b, 'greystone', x, y, ground(x, y) - 0.3, h=hh, w=0.8)
    # a ring of birches around the mound
    for k in range(12):
        a = 2 * math.pi * k / 12
        if 250 < math.degrees(a) < 290:
            continue
        x, y = SX + 8.5 * math.cos(a), SY + 7.5 * math.sin(a)
        z = ground(x, y) - 0.2
        cyl(b, 'birch', x, y, z, 0.22, 5.0, n=6, r2=0.14)
        for j in range(3):
            blob(b, 'birchleaf', x + b.rng.uniform(-0.6, 0.6), y + b.rng.uniform(-0.6, 0.6), z + 4.0 + 0.8 * j, 1.2,
                 n=7, rings=4, squash=0.9)
    # an Elvish wayside shrine, fallen
    for k in range(4):
        ruin_column(b, 'elfstone', -10.0 + 1.8 * k, -4.0, ground(-10 + 1.8 * k, -4) - 0.2, h=2.0 + (k % 2) * 1.2, r=0.4)
    ruin_wall(b, 'elfstone', -8.0, -1.5, ground(-8, -1.5) - 0.3, 5.0, 1.4, 0.5)

    # --- the shore: rocks, the cove with a landing and an Elvish boat, sea spray
    for k in range(26):
        a = 2 * math.pi * k / 26
        x, y = 21.0 * math.cos(a), 3.0 + 19.0 * math.sin(a)
        blob(b, 'greystone', x, y, -0.6, b.rng.uniform(1.0, 2.2), n=7, rings=4, squash=0.8, jitter=0.3)
    for k in range(5):
        box(b, 'wood', 8.0 + 0.0 * k, -8.0 - 1.1 * k, 0.4, 1.8, 1.0, 0.2)
    boat(b, 11.5, -13.0, 0.15, rz=60, s=1.1, hull='elfstone', sail='sail', mast=True)
    for k, (x, y) in enumerate(((-18.0, -10.0), (19.0, 12.0), (-19.0, 14.0))):
        fx(b, 'Spray_%d' % k, (x, y, 0.6), 'MIST')
    for (x, y, z, rz) in ((-8.0, -12.0, 13.0, 20), (6.0, 14.0, 16.0, -110), (14.0, -2.0, 12.0, 160)):
        eagle_flying(b, x, y, z, s=0.9, rz=rz, body='eagle', head='eaglehead', beak='beak')


PREVIEW = [((4, -34, 16), (0, 2, 5), 45)]
