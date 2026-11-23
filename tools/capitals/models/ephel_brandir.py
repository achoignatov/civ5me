"""Ephel Brandir, the fenced village of the Haladin on Amon Obel (Brethil, First Age).

From The Silmarillion / The Children of Húrin:
  * "the Folk of Haleth ... dwelt in the Forest of Brethil"; their chief Brandir the Lame
    had his house "upon Amon Obel in the midst of the forest", within a fence:
    Ephel Brandir, "the encircling fence of Brandir";
  * a wooded hill rising out of the oak forest of Brethil, its top girt with a stockade of
    stakes, timber halls and houses inside, the chieftain's hall on the summit;
  * a winding path up from the forest, a watch-post by the gate.
The gate faces the camera (-Y).
"""
import math

from blib import material, hexcol as h, box, gable, cyl, cone, terrain_polar, blob, strut, T, near_path
from city_common import (house, longhouse, palisade, gate, watchtower, scatter_forest, round_hut, fx,
                         person, barrel, crate)

CY = 3.0


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    r = math.hypot(x / 1.05, y - CY)
    z = 0.6 + 9.0 * sm((19.0 - r) / 12.0)          # Amon Obel
    z = z - 0.5 * sm((r - 22.0) / 6.0)
    # flatten the summit for the village
    if r < 11.0:
        z = 9.4 + 0.25 * math.sin(x * 0.7) * math.cos(y * 0.6)
    z += 0.25 * math.sin(x * 0.6) * math.sin(y * 0.5)
    return z


PATH = [(0.0, -30.0), (-3.0, -22.0), (3.0, -16.0), (0.0, -10.5), (0.0, -5.0)]


def build(b):
    material('forestfloor', h('4f6b2e'), zramp=[(-1, h('4b6430')), (4, h('5a7a35')), (9, h('6a8a3d'))],
             slope_color=h('6d6450'), slope_start=0.6)
    material('road', h('7a6648'), h('8a7553'), noise=2.0)
    material('stake', h('5b4129'), h('4a341f'), noise=4.0)
    material('timber', h('6b4a2c'), h('5a3c22'), noise=4.0)
    material('thatch', h('8f7a45'), h('7a6638'), noise=3.0)
    material('turfroof', h('5d7a35'), h('4d6a2c'), noise=3.0)
    material('daub', h('b8a27a'), h('a68f68'), noise=3.0)
    material('oak', h('3c5f26'), h('4d7230'), noise=1.5)
    material('cloth', h('6a5a3a'), h('7a6a48'), noise=3.0)
    material('skin', h('d0a07a'))
    material('flame', h('ffb040'), emission=4.0, ao=False)

    def mat(x, y, z, s):
        return 'road' if near_path(x, y, PATH, 1.2) else 'forestfloor'

    terrain_polar(b, ground, mat, R=31, cy=2, nr=40, na=128)
    TZ = 9.4

    # --- the encircling fence
    palisade(b, 'stake', 0, CY, 10.6, h=2.6, step=0.95, zfn=ground, gate=270, gate_w=14, rail='timber')
    gate(b, 'timber', 0, CY, 10.6, 270, z=TZ - 0.1, w=2.6, h=3.4, roof='thatch')
    watchtower(b, 'timber', 3.4, CY - 10.4, TZ - 0.2, r=0.9, h=5.5, roof='thatch', roof_h=1.6)
    fx(b, 'Torch_Gate_L', (-1.6, CY - 10.9, TZ + 3.0), 'TORCH')
    fx(b, 'Torch_Gate_R', (1.6, CY - 10.9, TZ + 3.0), 'TORCH')

    # --- Brandir's hall on the summit
    longhouse(b, 0.0, CY + 3.0, TZ, w=9.0, d=4.6, h=2.6, wall='timber', roof='turfroof', roof_h=2.6,
              windows=3, porch=True, posts=5, post_mat='timber')
    for s in (-1, 1):   # carved gable horns
        strut(b, 'timber', (s * 4.5, CY + 3.0, TZ + 4.9), (s * 5.1, CY + 2.6, TZ + 6.0), 0.12, 0.05, n=4)
    cyl(b, 'daub', 2.5, CY + 4.2, TZ + 3.2, 0.35, 2.6, n=6)
    fx(b, 'Smoke_Hall', (2.5, CY + 4.2, TZ + 6.0), 'SMOKE')

    # --- houses of the Haladin inside the fence
    spots = [(-6.5, CY - 1.5, 20), (6.5, CY - 1.0, -25), (-5.5, CY + 7.5, 10), (5.8, CY + 7.2, -10),
             (-7.8, CY + 3.5, 80), (7.9, CY + 3.0, -80), (-3.0, CY - 5.5, 5), (3.6, CY - 5.0, -5)]
    for k, (x, y, rz) in enumerate(spots):
        if k % 3 == 2:
            round_hut(b, x, y, TZ, r=1.6, h=1.5, roof_h=2.0, wall='daub', roof='thatch', door_mat='window')
        else:
            house(b, x, y, TZ, w=3.4, d=2.6, h=1.9, rz=rz, wall='timber', roof='thatch', roof_h=1.6,
                  windows=1, chimney=k % 2 == 0, chimney_mat='daub')
    fx(b, 'Smoke_H1', (-6.5 + 0.9, CY - 1.5, TZ + 3.4), 'SMOKE')
    # a well, wood pile and people in the yard
    cyl(b, 'stake', -1.5, CY - 2.0, TZ, 0.7, 0.8, n=10)
    for k in range(5):
        strut(b, 'timber', (2.0 + 0.3 * k, CY - 2.5, TZ + 0.2), (2.0 + 0.3 * k, CY - 1.0, TZ + 0.2), 0.14, 0.14, n=5)
    for (x, y) in ((-0.8, CY - 4.0), (1.2, CY - 3.4), (-3.4, CY + 0.2)):
        person(b, x, y, TZ, s=0.85, robe='cloth', skin='skin')
    barrel(b, 'timber', 4.0, CY - 2.8, TZ, 0.4, 0.8)
    crate(b, 'timber', 4.6, CY - 1.9, TZ, 0.6)

    # --- the forest of Brethil all around the hill
    scatter_forest(b, 120, -31, 31, -29, 33, ground, avoid=((-12, 12, -9, 16),), min_dist=2.5, max_r=30.0,
                   h=(5.0, 8.5), r=(1.6, 2.4), leaves='oak', pines=0.15)
    # trees along the hill top behind the hall
    for (x, y) in ((-3, CY + 9.5), (3.5, CY + 9.8), (-9.5, CY + 7.5), (9.2, CY + 7.0)):
        blob(b, 'oak', x, y, ground(x, y) + 2.6, 2.0, n=8, rings=5, squash=0.85)
        cyl(b, 'stake', x, y, ground(x, y), 0.25, 2.8, n=6)


PREVIEW = [((8, -34, 26), (0, 3, 10), 45)]
