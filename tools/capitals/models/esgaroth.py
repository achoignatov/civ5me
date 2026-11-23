"""Esgaroth upon the Long Lake (Lake-town before Smaug).

Book/film features modelled:
  * the town built entirely of wood on wooden pillars sunk into the Long Lake,
    south of the Lonely Mountain and east of Mirkwood;
  * a broad platform of planks on piles, with steep-roofed timber houses, a great
    hall, walkways, ladders and a stake palisade along the water edge;
  * piers and jetties reaching out into the lake, with boats and cargo;
  * the Lonely Mountain rising as a dark peak on the northern horizon;
  * the water everywhere below, with reflections and a few swans.
The town faces the camera (-Y); the mountain is behind it (+Y).
"""
import math

from blib import (material, hexcol as h, box, gable, hipped, cyl, cone, lathe, terrain_polar, blob,
                  strut, ring, window_row, banner, sphere, T)
from city_common import house, longhouse, watchtower, boat, barrel, crate, dock, grow, fx


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = -1.8 + 0.15 * math.sin(x * 0.4) * math.cos(y * 0.35)
    # rocky shore at the back and at the sides
    if y > 16.0:
        z = max(z, -1.8 + 3.4 * sm((y - 16.0) / 8.0))
    if abs(x) > 23.0:
        z = max(z, -1.8 + 2.4 * sm((abs(x) - 23.0) / 7.0))
    return z


def pile(b, x, y, z0, z1, mat='piling', r=0.20):
    cyl(b, mat, x, y, z0, r, z1 - z0, n=5, top=False)


def build(b):
    material('lake', h('3f667d'), h('507a91'), noise=1.0, ao=False)
    material('wood', h('6d4b2c'), h('5a3c22'), noise=4.0)
    material('darkwood', h('3e2b1c'), h('4c3522'), noise=4.0)
    material('plank', h('8a633c'), h('75512f'), noise=5.0)
    material('piling', h('4b3422'), h('3c291a'), noise=4.0)
    material('thatch', h('9c7c42'), h('856834'), noise=3.5)
    material('roofwood', h('5a4630'), h('493823'), noise=3.0)
    material('window', h('2a2118'))
    material('sail', h('d8cfb7'), h('bfb397'), noise=3.0)
    material('rope', h('9c8a62'), h('867650'), noise=6.0)
    material('mountain', h('77736c'), zramp=[(-1, h('4f5c48')), (4, h('6f6c64')), (14, h('85817a')),
                                            (22, h('e8ecef'))], slope_color=h('66625c'), slope_start=0.5)
    material('shore', h('8e856d'), h('776f59'), noise=3.0)
    material('fish', h('b7b0a0'), h('9b9485'), noise=5.0)

    def mat(x, y, z, s):
        if y > 16.0 or abs(x) > 23.0:
            return 'shore'
        return 'lake'

    terrain_polar(b, ground, mat, R=31, cy=2, nr=32, na=110)
    # the lake surface (a disc with a short skirt)
    # above z=0: the game's own terrain hides everything below the ground plane
    lathe(b, 'lake', [(30.2, -1.0), (30.6, 0.12), (0, 0.12)], n=96, smooth=False)
    town = len(b.verts)

    # --- the main platform on piles
    PZ = 0.85
    box(b, 'plank', 0, 2.0, PZ, 24.0, 18.0, 0.35)
    box(b, 'darkwood', 0, 2.0, PZ - 0.35, 24.2, 18.2, 0.25)
    for ix in range(-11, 12, 2):
        for iy in range(-6, 11, 2):
            if abs(ix) < 11 and -6 < iy < 10:
                continue
            pile(b, ix, iy + 2.0, -1.8, PZ - 0.35)
    # a lower deck in front for the piers
    box(b, 'plank', 0, -7.5, PZ - 0.25, 18.0, 3.2, 0.28)
    for ix in range(-8, 9, 2):
        pile(b, ix, -7.5, -1.8, PZ - 0.25)

    # --- stake palisade around the platform edge, gate at the south
    for k in range(74):
        a = 2 * math.pi * k / 74
        x, y = 11.4 * math.cos(a), 2.0 + 8.6 * math.sin(a)
        if abs(x) < 2.6 and y < 0:
            continue
        pile(b, x, y, PZ, PZ + 2.0, mat='darkwood', r=0.14)
        cone(b, 'darkwood', x, y, PZ + 2.0, 0.14, 0.4, n=4)
    for s in (-1, 1):
        box(b, 'darkwood', s * 2.5, -6.6, PZ, 0.55, 0.55, 3.2)
        box(b, 'darkwood', s * 2.5, -6.6, PZ + 3.0, 0.8, 0.8, 0.5)
    box(b, 'darkwood', 0, -6.6, PZ + 3.0, 5.8, 0.7, 0.45)
    box(b, 'plank', 0, -6.6, PZ + 2.1, 4.8, 0.2, 0.9)

    # --- the great hall at the back of the town
    longhouse(b, 0.0, 7.2, PZ, w=10.0, d=5.0, h=3.0, wall='wood', roof='thatch', roof_h=2.4,
              windows=6, base='darkwood', base_h=0.3, porch=True, posts=6, post_mat='darkwood')
    # carved gable ends
    for s in (-1, 1):
        box(b, 'darkwood', s * 5.0, 7.2, PZ + 5.4, 0.35, 5.0, 0.45)
        for k in range(3):
            sphere(b, 'plank', s * 5.0, 5.0 + 1.5 * k, PZ + 5.4, 0.18, n=6, rings=4)
    # a second hall and a storehouse
    longhouse(b, -7.0, 4.5, PZ, w=5.0, d=3.4, h=2.2, wall='wood', roof='roofwood', roof_h=1.6,
              windows=3, porch=False, posts=3)
    house(b, 7.6, 4.0, PZ, w=4.0, d=3.0, h=2.2, wall='wood', roof='roofwood', roof_h=1.5,
          windows=2, base='darkwood', base_h=0.25, chimney=False)

    # --- houses on the platform
    rng = b.rng
    spots = []
    for k in range(260):
        if len(spots) >= 18:
            break
        x, y = rng.uniform(-9.5, 9.5), rng.uniform(-4.5, 10.0)
        if math.hypot(x, y - 2.0) > 9.0:
            continue
        if math.hypot(x, y - 7.2) < 5.6 or math.hypot(x + 7.0, y - 4.5) < 3.5 or math.hypot(x - 7.6, y - 4.0) < 3.2:
            continue
        if any(math.hypot(x - px, y - py) < 2.3 for px, py in spots):
            continue
        spots.append((x, y))
        w, d, hh = rng.uniform(2.0, 3.0), rng.uniform(1.8, 2.5), rng.uniform(1.5, 2.4)
        rz = rng.choice([0, 90, rng.uniform(-12, 12)])
        house(b, x, y, PZ, w=w, d=d, h=hh, rz=rz, wall='wood',
              roof='thatch' if rng.random() < 0.7 else 'roofwood', roof_h=rng.uniform(0.9, 1.4),
              windows=2, base='darkwood', base_h=0.2, overhang=0.25)
        # a few houses stand on their own short piles at the platform edge
        if abs(x) > 7.0 or y < -2.5:
            for sx in (-1, 1):
                for sy in (-1, 1):
                    pile(b, x + sx * w * 0.4, y + sy * d * 0.4, -1.8, PZ)

    # --- walkways and ladders
    for (x, y, L, rz) in ((-10.0, -1.0, 5.0, 90), (10.2, -1.0, 5.0, 90), (0.0, -4.5, 5.0, 0)):
        box(b, 'plank', x, y, PZ + 0.1, L, 1.2, 0.18, rz=rz)
    for (x, y) in ((-6.5, -4.2), (6.5, -4.2)):
        for k in range(6):
            box(b, 'darkwood', x, y, PZ + 0.2 * k, 0.8, 0.12, 0.12)
        for s in (-1, 1):
            strut(b, 'darkwood', (x + s * 0.4, y, PZ), (x + s * 0.4, y, PZ + 1.6), 0.05, 0.05, n=3)

    # --- piers and boats
    for (x, y, rz) in ((-9.5, -9.5, 0), (9.5, -9.5, 0), (0.0, -12.0, 0)):
        dock(b, 'plank', x, y, PZ - 0.35, 3.0, 1.8, rz=rz, post_mat='piling', water_z=-1.7)
    for (x, y, rz, s) in ((-9.5, -12.0, 8, 0.9), (9.5, -12.5, -6, 0.85), (3.0, -14.0, 12, 0.8),
                          (-2.5, -15.5, -10, 0.75)):
        boat(b, x, y, 0.1, rz=rz, s=s, hull='darkwood', sail='sail', mast=True, oars=True)

    # --- fish racks, nets, barrels and crates
    for (x, y) in ((-3.5, -5.0), (4.0, -5.0)):
        for s in (-1, 1):
            strut(b, 'darkwood', (x + s * 0.8, y, PZ), (x + s * 0.8, y, PZ + 1.6), 0.05, 0.05, n=4)
        strut(b, 'darkwood', (x - 0.8, y, PZ + 1.5), (x + 0.8, y, PZ + 1.5), 0.05, 0.05, n=4)
        for k in range(3):
            sphere(b, 'fish', x - 0.4 + 0.4 * k, y, PZ + 1.1, 0.12, n=5, rings=4, squash=0.6)
    for (x, y) in ((-11.0, 6.0), (10.5, 7.0), (-10.0, 9.0)):
        barrel(b, 'wood', x, y, PZ, 0.38, 0.8)
        crate(b, 'plank', x + 0.7, y, PZ, 0.55)
    # a net hung on the palisade
    for k in range(5):
        strut(b, 'rope', (-2.5 + 1.2 * k, -6.7, PZ + 0.4), (-2.5 + 1.2 * k, -6.7, PZ + 2.4),
              0.02, 0.02, n=3)
    for k in range(4):
        strut(b, 'rope', (-2.5, -6.7, PZ + 0.6 + 0.5 * k), (2.3, -6.7, PZ + 0.6 + 0.5 * k),
              0.02, 0.02, n=3)

    # torches along the town front and on the Master's hall
    for k, (x, y, z) in enumerate(((-4.0, -9.4, PZ + 2.2), (4.0, -9.4, PZ + 2.2), (-9.0, -6.6, PZ + 2.6),
                                   (9.0, -6.6, PZ + 2.6))):
        strut(b, 'darkwood', (x, y, z - 2.2), (x, y, z), 0.07, 0.06, n=4)
        fx(b, 'Torch_%d' % k, (x, y, z + 0.3), 'TORCH')
    fx(b, 'Smoke_Hall', (0.0, 6.0, PZ + 8.0), 'SMOKE')
    # the town grows to fill the lake: everything since the lake surface, scaled about the centre
    grow(b, town, 1.38, 0.0, 1.0, 1.2)

    # --- the Lonely Mountain on the northern horizon (lumpy, snow-capped)
    lathe(b, 'mountain', [(9.0, -1.0), (8.4, 3.0), (6.2, 10.0), (3.8, 17.0), (1.8, 22.5), (0.6, 25.0), (0, 25.6)],
          n=14, x=0.0, y=25.0, z=-1.0, smooth=False, jitter=0.12)
    for sx in (-1, 1):
        lathe(b, 'mountain', [(5.5, -1.0), (4.0, 6.0), (1.6, 11.0), (0, 12.0)], n=10, x=sx * 8.5, y=24.0, z=-1.0,
              smooth=False, jitter=0.15)
    # a couple of swans on the lake
    for (x, y) in ((-21.0, -8.0), (22.0, -4.0)):
        sphere(b, 'sail', x, y, 0.1, 0.32, n=7, rings=4, squash=0.6)
        strut(b, 'sail', (x, y + 0.2, 0.2), (x, y + 0.7, 0.75), 0.07, 0.03, n=4)


PREVIEW = [((10, -34, 16), (0, 1, 5), 46), ((32, -12, 12), (0, 2, 4), 42)]
