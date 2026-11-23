"""Crissaegrim, the eyries of Thorondor (First Age).

The Silmarillion: "the peaks of the Crissaegrim", south of the Encircling Mountains about
Gondolin, "where Thorondor had his eyrie"; from there the Eagles kept watch for Turgon
and bore Fingolfin's body and Beren and Lúthien. Sharp, snow-clad pinnacles.
Modelled: a cluster of needle-sharp, snow-capped peaks rising from icy screes, great nests
of branches on the ledges with eagles perched, two great eagles soaring between the
spires, clouds and spray drifting about the summits (animated mist), a glimpse of the
green vale below at the front.
The highest spire stands in the centre; the vale is towards the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, cyl, cone, lathe, terrain_polar, blob, strut, sphere, T, curve)
from city_common import (eagle, eagle_flying, fx, spire, scatter_forest)


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    r = math.hypot(x, (y - 4.0) / 1.1)
    z = 0.8 + 10.0 * sm((22.0 - r) / 14.0) + 0.8 * math.sin(x * 0.5) * math.cos(y * 0.4)
    return z


PEAKS = [(0.0, 5.0, 34.0, 4.6), (-7.0, 1.5, 24.0, 3.6), (7.5, 2.0, 26.0, 3.8), (-4.0, 11.0, 27.0, 3.8),
         (5.0, 12.0, 22.0, 3.4), (-12.5, 8.0, 18.0, 3.2), (13.0, 9.0, 19.0, 3.2), (-2.0, -4.0, 15.0, 3.0),
         (3.5, -5.5, 12.0, 2.6), (-14.0, -2.0, 11.0, 2.8), (15.0, -1.0, 12.0, 2.8)]


def build(b):
    material('scree', h('8a8a86'), zramp=[(-1, h('5f7a3c')), (2.5, h('6e8040')), (5, h('8a8884')), (10, h('b8bcc0')),
                                          (12, h('e8eef2'))], slope_color=h('7a7a78'), slope_start=0.55, noise=1.2)
    material('peak', h('7c7c7c'), zramp=[(0, h('6a6a6a')), (10, h('7e7e80')), (18, h('a0a2a6')), (24, h('eef2f6'))],
             slope_color=h('6a6a6c'), slope_start=0.6, noise=1.5)
    material('nest', h('6a5232'), h('54402a'), noise=6.0)
    material('eagle', h('6a4a2a'), h('7a5634'), noise=4.0)
    material('eaglehead', h('c89a4a'), h('d8aa58'), noise=3.0)       # golden-brown, not bald-eagle white
    material('beak', h('3a3028'))
    material('eye', h('e8c040'))
    material('vale', h('5e8a36'), h('6e9a40'), noise=1.5)
    material('snow', h('f2f6f8'))

    terrain_polar(b, ground, lambda x, y, z, s: 'scree', R=31, cy=2, nr=40, na=130)

    # --- the needle peaks
    for k, (x, y, hh, r) in enumerate(PEAKS):
        z = ground(x, y) - 1.0
        lathe(b, 'peak', [(r, 0), (r * 0.8, hh * 0.3), (r * 0.55, hh * 0.6), (r * 0.3, hh * 0.85), (r * 0.08, hh), (0, hh + 0.2)],
              n=8, x=x, y=y, z=z, smooth=False, jitter=0.16)
        cone(b, 'snow', x, y, z + hh * 0.78, r * 0.36, hh * 0.24, n=8)
    # ledges with nests and perched eagles on the main spires
    for k, (x, y, hh, r) in enumerate(PEAKS[:5]):
        z = ground(x, y) - 1.0 + hh * 0.55
        rr = r * 0.6
        nx, ny = x, y - rr - 1.2
        box(b, 'peak', nx, ny + 0.6, z - 1.0, 3.6, 2.6, 1.2)
        lathe(b, 'nest', [(0.6, 0), (1.9, 0.1), (2.1, 0.7), (1.6, 0.8), (0.8, 0.4), (0, 0.4)], n=12, x=nx, y=ny, z=z + 0.2,
              smooth=False, jitter=0.12)
        for j in range(8):
            a = 2 * math.pi * j / 8
            strut(b, 'nest', (nx + 1.6 * math.cos(a), ny + 1.6 * math.sin(a), z + 0.7),
                  (nx + 2.5 * math.cos(a + 0.5), ny + 2.5 * math.sin(a + 0.5), z + 0.5), 0.09, 0.04, n=3)
        eagle(b, nx + 0.5, ny, z + 0.6, s=1.6 if k == 0 else 1.25, body='eagle', head='eaglehead', beak='beak',
              leg='beak', eye='eye', rz=b.rng.uniform(-25, 25))
        if k in (0, 1, 2):
            fx(b, 'Cloud_%d' % k, (x, y, ground(x, y) + hh * 0.9), 'MIST')
    # Thorondor and another soaring between the spires
    eagle_flying(b, -9.0, -6.0, 22.0, s=4.2, rz=30, body='eagle', head='eaglehead', beak='beak')
    eagle_flying(b, 11.0, 15.0, 30.0, s=3.0, rz=-140, body='eagle', head='eaglehead', beak='beak')

    # --- the green vale below, in front
    for k in range(40):
        x, y = b.rng.uniform(-28, 28), b.rng.uniform(-29, -14)
        if math.hypot(x, y - 2) > 29.5:
            continue
        z = ground(x, y)
        cone(b, 'vale', x, y, z - 0.2, b.rng.uniform(1.0, 1.5), b.rng.uniform(3.5, 5.0), n=7)
    for k in range(30):
        x, y = b.rng.uniform(-30, 30), b.rng.uniform(-14, 30)
        if math.hypot(x, y - 2) > 29.5 or math.hypot(x, (y - 4) / 1.1) < 17:
            continue
        blob(b, 'peak', x, y, ground(x, y) - 0.5, b.rng.uniform(1.0, 2.2), n=6, rings=4, squash=0.7, jitter=0.3)


PREVIEW = [((6, -40, 26), (0, 4, 12), 45)]
