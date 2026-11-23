"""The Entwood: Fangorn Forest and the Ents.

The Two Towers: Fangorn, "old, very old", dark and tangled, "the hall of the Ents";
Derndingle, "a great bowl ... with steep sides" where the Entmoot gathered; Wellinghall,
Treebeard's house "at the foot of a high cliff" with a spring falling in a stream; the Ents
"fourteen foot high", bark-skinned, with deep eyes and leafy hair.
Modelled: a deep forest of huge, mossy, twisted trees around a green dell (Derndingle) where
several Ents stand in council, Treebeard tallest among them; at the back the cliff of
Wellinghall with the spring tumbling down in a fall (animated spray) into a pool and a
stream that runs out of the wood; great roots, mossy boulders and ferns.
The dell opens towards the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, cyl, cone, lathe, terrain_polar, blob, strut, sphere, T, curve)
from city_common import (ent, fx, scatter_forest, spire, plate, tree)

DX, DY = 0.0, 0.0


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    r = math.hypot(x - DX, (y - DY) / 1.05)
    z = 1.4 + 2.8 * sm((r - 8.0) / 9.0) + 0.5 * math.sin(x * 0.4) * math.cos(y * 0.35)
    if y > 14.0:                                   # the cliff of Wellinghall
        z += 14.0 * sm((y - 14.0) / 6.0) * (0.85 + 0.15 * math.sin(x * 0.6))
    return z


def big_tree(b, x, y, z, hh=12.0, r=0.9):
    """A gnarled, buttressed giant of the old forest."""
    lathe(b, 'oldbark', [(r * 1.9, 0), (r * 1.2, hh * 0.12), (r, hh * 0.5), (r * 0.75, hh * 0.8), (0, hh * 0.82)],
          n=8, x=x, y=y, z=z, smooth=True, jitter=0.12)
    for k in range(4):
        a = 2 * math.pi * k / 4 + b.rng.uniform(-0.4, 0.4)
        strut(b, 'oldbark', (x, y, z + hh * 0.15), (x + 2.4 * r * math.cos(a), y + 2.4 * r * math.sin(a), z - 0.3),
              r * 0.55, r * 0.15, n=5)
    for k in range(5):
        a = 2 * math.pi * k / 5 + b.rng.uniform(-0.3, 0.3)
        p0 = (x, y, z + hh * (0.55 + 0.05 * k))
        p1 = (x + hh * 0.3 * math.cos(a), y + hh * 0.3 * math.sin(a), z + hh * (0.78 + 0.04 * k))
        strut(b, 'oldbark', p0, p1, r * 0.4, r * 0.15, n=5)
        blob(b, 'oldleaf' if k % 2 else 'darkleaf', *p1, hh * 0.17, n=8, rings=5, squash=0.7, jitter=0.2)
    blob(b, 'darkleaf', x, y, z + hh * 0.85, hh * 0.22, n=9, rings=5, squash=0.7, jitter=0.2)
    for k in range(3):   # hanging moss
        a = b.rng.uniform(0, 2 * math.pi)
        p = (x + r * 1.1 * math.cos(a), y + r * 1.1 * math.sin(a), z + hh * 0.55)
        strut(b, 'entmoss', p, (p[0], p[1], p[2] - 1.6), 0.12, 0.03, n=4)


def build(b):
    material('forestfloor', h('3f5a2a'), zramp=[(-1, h('46622e')), (2, h('3e5828')), (5, h('3a5226')), (8, h('5a5850')),
                                                 (18, h('6a6862'))], slope_color=h('5a564c'), slope_start=0.6, noise=1.0)
    material('dellgrass', h('6a9440'), h('78a04a'), noise=0.8)
    material('oldbark', h('4a3e30'), h('5a4c3a'), noise=6.0)
    material('oldleaf', h('34552a'), h('3e6230'), noise=1.5)
    material('darkleaf', h('26401e'), h('2e4a24'), noise=1.5)
    material('entbark', h('6a5a44'), h('5a4a36'), noise=7.0)
    material('entleaf', h('4a7a30'), h('5a8a38'), noise=3.0)
    material('entmoss', h('6a7a3a'), h('7a8a44'), noise=4.0)
    material('cliff', h('6a665c'), h('5a564e'), noise=2.5, courses=1.0, course_dark=0.86)
    material('water', h('5a8aa0'), h('6a9ab0'), noise=1.0, ao=False, spec=0.7, refl=50)
    material('fern', h('4a7a2e'), h('5a8a36'), noise=4.0)
    material('boulder', h('7a786e'), h('6a685e'), noise=3.0)
    material('window', h('0e100c'))

    terrain_polar(b, ground, lambda x, y, z, s: 'dellgrass' if math.hypot(x, y) < 9.5 else 'forestfloor',
                  R=31, cy=2, nr=40, na=130)

    # --- the Entmoot: Treebeard and his fellows in the dell
    ents = [(0.0, 2.5, 14.0, 'entbark'), (-5.0, 0.0, 11.0, 'entbark'), (5.2, 0.5, 11.5, 'oldbark'),
            (-3.0, -5.0, 10.0, 'oldbark'), (3.5, -5.5, 10.5, 'entbark'), (-7.0, 5.0, 10.0, 'entbark'),
            (7.2, 5.5, 9.5, 'oldbark')]
    for (x, y, hh, bark) in ents:
        ent(b, x, y, ground(x, y) - 0.1, h=hh, bark=bark, leaf='entleaf', moss='entmoss', eye='window')

    # --- Wellinghall: the cliff, the spring falling into a pool, the stream out of the wood
    for k in range(8):
        x = -12 + 3.4 * k
        spire(b, 'cliff', x, 18.5 + (k % 2), ground(x, 18.5) - 2.0, 10.0 + 2.0 * (k % 3), 2.6, jitter=0.18)
    fz = ground(3.0, 15.0)
    plate(b, 'water', [(2.2, 14.6), (3.8, 14.6), (3.8, 15.2), (2.2, 15.2)], fz, 13.0)       # the falling water
    lathe(b, 'water', [(3.0, -0.5), (3.0, fz + 0.15), (0, fz + 0.15)], n=20, x=3.0, y=12.5)
    fx(b, 'Spring', (3.0, 13.0, fz + 1.5), 'MIST')
    stream = [(3.0, 10.0), (1.0, 6.0), (-2.0, 2.0), (-1.0, -4.0), (1.5, -10.0), (0.0, -18.0), (-2.5, -30.0)]
    for (x0, y0), (x1, y1) in zip(stream, stream[1:]):
        z0, z1 = ground(x0, y0) + 0.12, ground(x1, y1) + 0.12
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * 0.9, dx / L * 0.9
        b.add([(x0 + nx, y0 + ny, z0), (x0 - nx, y0 - ny, z0), (x1 - nx, y1 - ny, z1), (x1 + nx, y1 + ny, z1)],
              [(0, 1, 2, 3)], 'water')

    # --- the old forest all around
    rng = b.rng
    placed = []
    for k in range(400):
        if len(placed) >= 32:
            break
        x, y = rng.uniform(-30, 30), rng.uniform(-29, 17)
        if math.hypot(x, y - 2) > 26.0 or math.hypot(x, y) < 14.0 or (y < 2.0 and abs(x) < 15.0):
            continue
        if any(math.hypot(x - px, y - py) < 4.8 for px, py in placed):
            continue
        if abs(x - (-1.0 if y < -4 else 1.0)) < 2.2 and y < -10:
            continue
        placed.append((x, y))
        big_tree(b, x, y, ground(x, y) - 0.3, hh=rng.uniform(9.0, 13.0), r=rng.uniform(0.7, 1.0))
    for k in range(50):
        x, y = rng.uniform(-28, 28), rng.uniform(-28, 16)
        if math.hypot(x, y - 2) > 29.5:
            continue
        if math.hypot(x, y) < 9.0:
            continue
        if k % 3:
            for j in range(5):
                a = 2 * math.pi * j / 5
                strut(b, 'fern', (x, y, ground(x, y)), (x + 0.9 * math.cos(a), y + 0.9 * math.sin(a), ground(x, y) + 0.7),
                      0.12, 0.02, n=3)
        else:
            blob(b, 'boulder', x, y, ground(x, y) - 0.4, rng.uniform(0.8, 1.6), n=7, rings=4, squash=0.7, jitter=0.25)


PREVIEW = [((3, -30, 14), (0, 1, 7), 45)]
