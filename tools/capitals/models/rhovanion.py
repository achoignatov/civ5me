"""The Kingdom of Rhovanion: the Northmen of Vidugavia (Third Age).

Appendix A / Unfinished Tales: Vidugavia "called himself King of Rhovanion"; the Northmen
of the plains between Mirkwood and the Running were horse-breeders and the forefathers of
the Éothéod and the Rohirrim; their great halls were of timber.
Modelled: the king's hall on a grassy mound, timber with carved crossed gable-boards in the
shape of horse heads, a porch of painted posts and a high-pitched thatched roof; a ring of
lesser halls and byres, a stake palisade with a gatehouse, horse paddocks and grazing herds
on the open grassland, banners with a running horse, torches at the gate (animated) and
smoke from the hall.
The gate faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, gable, cyl, cone, lathe, terrain_polar, blob, strut, sphere,
                  T, near_path)
from city_common import (house, longhouse, palisade, gate, watchtower, horse, fence, fx, person, banner,
                         scatter_forest, barrel, crate, cow)

CY = 4.0


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = 0.6 + 0.4 * math.sin(x * 0.2) * math.cos(y * 0.25)
    r = math.hypot(x / 1.2, y - CY)
    z += 3.2 * sm((15.0 - r) / 6.0)
    if r < 6.0:
        z = max(z, 3.6)
    return z


PATH = [(0, -31), (0, -14), (0, -10), (0, -3)]


def build(b):
    material('plains', h('86a24c'), zramp=[(-1, h('80994a')), (2, h('8eaa52')), (4, h('86a04c'))], noise=0.4)
    material('road', h('9c8762'), h('8a7652'), noise=2.0)
    material('timber', h('6e4a2a'), h('5c3c20'), noise=4.0)
    material('darktimber', h('46301c'), h('3a2716'), noise=4.0)
    material('thatch', h('b08f4c'), h('9a7a3e'), noise=3.0)
    material('gold', h('d6ac45'), h('c09434'), noise=2.0, spec=0.9, refl=40)
    material('paint', h('a83a28'), h('2c5a8a'), noise=10.0)
    material('banner', h('2a6a3a'), h('3a7a46'), noise=3.0)
    material('horse', h('8a5a34'), h('6a4426'), noise=4.0)
    material('greyhorse', h('c8c4bc'), h('b0aca4'), noise=3.0)
    material('mane', h('2a1e16'))
    material('cow', h('7a5a40'), h('6a4a30'), noise=4.0)
    material('horn', h('d8ccb0'))
    material('cloth', h('5a6a3a'), h('6a7a48'), noise=3.0)
    material('skin', h('e0b896'))
    material('stone', h('8a8678'))
    material('daub', h('b8a27a'), h('a68f68'), noise=3.0)

    terrain_polar(b, ground, lambda x, y, z, s: 'road' if near_path(x, y, PATH, 1.5) else 'plains',
                  R=31, cy=2, nr=38, na=124)
    HZ = 3.6

    # --- the king's hall on the mound
    longhouse(b, 0.0, CY + 1.0, HZ, w=13.0, d=6.0, h=3.4, wall='timber', roof='thatch', roof_h=4.4,
              windows=0, porch=True, posts=6, post_mat='paint')
    for s in (-1, 1):
        # crossed gable boards ending in horse heads
        for sd in (-1, 1):
            strut(b, 'darktimber', (s * 6.6, CY + 1.0 + sd * 2.2, HZ + 5.6), (s * 6.6, CY + 1.0 - sd * 1.0, HZ + 8.9),
                  0.13, 0.13, n=4)
            sphere(b, 'darktimber', s * 6.6, CY + 1.0 - sd * 1.15, HZ + 9.1, 0.32, n=6, rings=4, squash=1.4)
    box(b, 'gold', 0, CY - 2.05, HZ + 3.0, 2.2, 0.15, 0.5)
    fx(b, 'Smoke_Hall', (2.5, CY + 1.5, HZ + 8.6), 'SMOKE')
    # the stair up the mound
    for i in range(6):
        box(b, 'stone', 0, CY - 7.5 + 0.7 * i, ground(0, CY - 7.5 + 0.7 * i) - 0.4, 3.4, 0.8, 0.5)

    # --- lesser halls, byres, smithy around the mound
    for (x, y, rz, w) in ((-9.5, CY - 5.0, 70, 7.0), (9.5, CY - 5.5, -70, 7.0), (-11.0, CY + 5.0, 100, 6.0),
                          (11.0, CY + 5.0, -100, 6.0), (-5.0, CY + 10.5, 10, 6.5), (5.5, CY + 10.5, -10, 6.5)):
        longhouse(b, x, y, ground(x, y) - 0.2, w=w, d=3.6, h=2.2, rz=rz, wall='timber', roof='thatch', roof_h=2.4,
                  windows=0, porch=False, posts=0)

    # --- palisade and gatehouse
    palisade(b, 'darktimber', 0, CY, 16.5, h=2.8, step=1.05, zfn=ground, gate=270, gate_w=10, rail='timber')
    gate(b, 'darktimber', 0, CY, 16.5, 270, z=ground(0, CY - 16.5), w=3.2, h=4.0, roof='thatch')
    for s in (-1, 1):
        watchtower(b, 'darktimber', s * 3.6, CY - 16.6, ground(s * 3.6, CY - 16.6) - 0.2, r=1.0, h=6.5,
                   roof='thatch', roof_h=1.8)
        fx(b, 'Torch_Gate_%s' % ('L' if s < 0 else 'R'), (s * 2.0, CY - 17.4, ground(0, CY - 16.5) + 3.6), 'TORCH')
        banner(b, 'darktimber', 'banner', s * 3.6, CY - 18.0, ground(s * 3.6, CY - 18.0) + 8.0, h=3.5, w=1.0, ch=2.0)

    # --- paddocks and herds on the plains
    fence(b, 'timber', [(-28.0, -6.0), (-18.0, -12.0), (-12.0, -24.0)], h=1.2, step=1.6)
    fence(b, 'timber', [(28.0, -6.0), (18.0, -12.0), (12.0, -24.0)], h=1.2, step=1.6)
    rng = b.rng
    for k in range(16):
        side = -1 if k % 2 else 1
        x, y = side * rng.uniform(17, 27), rng.uniform(-22, -4)
        if math.hypot(x, y - 2) > 29:
            continue
        horse(b, x, y, ground(x, y), s=1.3, body='greyhorse' if k % 5 == 0 else 'horse', mane='mane',
              rz=rng.uniform(0, 360))
    for k in range(5):
        x, y = rng.uniform(-24, -14), rng.uniform(12, 22)
        cow(b, x, y, ground(x, y), s=1.3, rz=rng.uniform(0, 360))
    for (x, y) in ((-3, -12), (3.5, -13), (1.5, CY - 4.5), (-14, -14)):
        person(b, x, y, ground(x, y), s=0.95, robe='cloth', skin='skin')
    for k in range(4):
        barrel(b, 'timber', 6.5 + 0.9 * k, CY - 9.5, ground(6.5, CY - 9.5), 0.4, 0.8)
    # the eaves of Mirkwood far behind (north-east)
    scatter_forest(b, 26, 6, 31, 18, 33, ground, min_dist=2.8, max_r=30.5, h=(6.0, 8.5), r=(1.7, 2.3),
                   leaves='pine', kind='conifer')


PREVIEW = [((6, -36, 20), (0, 2, 6), 45)]
