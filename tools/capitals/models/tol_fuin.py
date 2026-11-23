"""Tol Fuin, the isle that was once the highlands of Dorthonion (Taur-nu-Fuin).

The Silmarillion: Dorthonion, "a great forest of pines" on the northern highlands, became
Taur-nu-Fuin, "the Forest under Nightshade", after the Dagor Bragollach; when Beleriand
was drowned "the highlands of Dorthonion" remained as an island in the sea, Tol Fuin.
Modelled: a steep, high island of dark granite clad in black-green pines, its crest bare
rock with tarns, a few gaunt dead pines from the days of Nightshade, a waterfall spilling
off the cliffs into the sea (animated spray), mist about the summit (animated), a grey
seal-strewn skerry and the wreck of an old Edain boat on the shingle.
The island's southern cliffs face the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, cyl, cone, lathe, terrain_polar, blob, strut, sphere, T, curve)
from city_common import (fx, conifer, dead_tree, spire, plate, scatter_forest)


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    r = math.hypot(x / 1.15, (y - 4.0))
    z = -1.4 + 17.0 * sm((23.0 - r) / 13.0) + 1.2 * math.sin(x * 0.4) * math.cos(y * 0.35)
    z += 3.0 * math.exp(-((x + 4) ** 2 + (y - 7) ** 2) / 18.0)
    return z


def build(b):
    material('isle', h('3e5034'), zramp=[(-2, h('8a8478')), (0.6, h('9a9282')), (1.8, h('3e5232')), (12, h('42523a')),
                                         (16, h('6a6862'))], slope_color=h('5a5650'), slope_start=0.65, noise=1.0)
    material('sea', h('2a5a78'), h('346684'), noise=1.0, ao=False, spec=0.8, refl=60)
    material('granite', h('5e5c58'), h('4e4c48'), noise=2.5)
    material('pine', h('1e3a26'), h('26442c'), noise=1.5)
    material('bark', h('3a2e24'))
    material('deadwood', h('2a2622'))
    material('tarn', h('3a5a6a'), ao=False, spec=0.8, refl=60)
    material('falls', h('d0e4ee'), h('b8d4e2'), noise=3.0, ao=False)
    material('seal', h('6a6660'))
    material('wood', h('5a4630'), h('4a3a26'), noise=4.0)

    terrain_polar(b, ground, lambda x, y, z, s: 'isle', R=31, cy=2, nr=42, na=130, edge=0.12)
    lathe(b, 'sea', [(30.0, -1.0), (30.4, 0.15), (0, 0.15)], n=96, y=2.0, smooth=False)

    # --- the crags and cliffs
    for k in range(18):
        a = 2 * math.pi * k / 18
        x, y = 15.5 * math.cos(a), 4.0 + 13.0 * math.sin(a)
        spire(b, 'granite', x, y, ground(x, y) - 3.0, b.rng.uniform(5.0, 9.0), b.rng.uniform(2.0, 3.0), jitter=0.25)
    for (x, y, hh) in ((-4.0, 7.0, 9.0), (1.0, 9.5, 7.0), (-8.0, 4.0, 6.0)):
        spire(b, 'granite', x, y, ground(x, y) - 1.0, hh, 2.4, jitter=0.2)
    # tarns on the crest
    for (x, y, r) in ((3.5, 2.0, 1.8), (-1.5, 0.5, 1.3)):
        lathe(b, 'tarn', [(r, -0.4), (r, 0.15), (0, 0.15)], n=16, x=x, y=y, z=ground(x, y))
    fx(b, 'Mist_Summit', (-4.0, 7.0, ground(-4, 7) + 9.0), 'MIST')
    # a waterfall down the southern cliff into the sea
    fz = ground(6.0, -6.0)
    plate(b, 'falls', [(5.3, -8.6), (6.7, -8.6), (6.7, -8.0), (5.3, -8.0)], 0.1, fz + 0.4)
    fx(b, 'Falls', (6.0, -9.5, 0.8), 'MIST')

    # --- the pine forest of old Dorthonion, and the gaunt dead pines of Nightshade
    rng = b.rng
    placed = []
    for k in range(600):
        if len(placed) >= 120:
            break
        x, y = rng.uniform(-24, 24), rng.uniform(-18, 26)
        z = ground(x, y)
        if z < 1.6 or z > 15.5:
            continue
        if any(math.hypot(x - px, y - py) < 1.9 for px, py in placed):
            continue
        placed.append((x, y))
        if k % 9 == 0:
            dead_tree(b, 'deadwood', x, y, z - 0.2, h=rng.uniform(4.0, 6.0), r=0.18)
        else:
            conifer(b, x, y, z - 0.2, h=rng.uniform(4.5, 7.5), r=rng.uniform(1.0, 1.4), leaves='pine', trunk='bark')

    # --- the shore: a skerry with seals, the wreck on the shingle
    for k in range(5):
        blob(b, 'granite', -16.0 + 2.0 * k, -19.0 + (k % 2), -0.5, 1.4, n=7, rings=4, squash=0.6, jitter=0.3)
    for (x, y) in ((-15.0, -19.5), (-11.5, -18.8)):
        sphere(b, 'seal', x, y, 0.75, 0.55, n=8, rings=5, M=T(x, y, 0.75) @ T(0, 0, 0, s=(1.8, 0.8, 0.7)) @ T(-x, -y, -0.75))
    for k in range(6):
        strut(b, 'wood', (12.0 + 0.6 * k, -15.0, 0.3), (12.5 + 0.6 * k, -14.0, 1.6 + 0.3 * (k % 2)), 0.12, 0.08, n=4)
    box(b, 'wood', 13.5, -15.6, 0.15, 4.5, 1.0, 0.35, rz=12)


PREVIEW = [((4, -40, 22), (0, 3, 7), 45)]
