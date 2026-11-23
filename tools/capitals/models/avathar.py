"""Avathar, "the Shadows": the dark coast where Ungoliant dwelt (Elder Days).

The Silmarillion: "In Avathar, between the sea and the mountains, the shadows were
deepest and thickest in the world; and there secretly and unknown Ungoliant made her
abode. ... she wove webs of black ... and sucked up all light". A narrow, cold, lightless
land between the Pelóri and the sea.
Modelled: a sliver of black, barren shore between the sea and towering dark mountains,
cold mist creeping over it (animated), sheets of black web hung between the crags, a
ravine where the vast shape of Ungoliant crouches with faint red eyes (animated), pale
drained husks, and the leaden sea lapping at the strand.
The ravine faces the camera (-Y); the sea is in front, the mountains behind.
"""
import math

from blib import (material, hexcol as h, box, cyl, cone, lathe, terrain_polar, blob, strut, sphere, T, curve)
from city_common import (spider, web, fx, spire, dead_tree, plate)


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = 0.8 + 0.5 * math.sin(x * 0.45) * math.cos(y * 0.5)
    z += 22.0 * sm((y - 6.0) / 20.0) * (0.8 + 0.2 * math.sin(x * 0.3))       # the Pelóri behind
    if y < -12.0:                                                           # the strand dips to the sea
        z = min(z, max(0.15, 0.8 - 0.16 * (-12.0 - y)))
    return z


def build(b):
    material('blackshore', h('262422'), zramp=[(-1, h('2e2c2a')), (2, h('22201e')), (10, h('2c2a28')),
                                               (22, h('3a3836'))], slope_color=h('1c1b1a'), slope_start=0.5, noise=1.2)
    material('sea', h('2a3238'), h('343e44'), noise=1.0, ao=False, spec=0.6, refl=40)
    material('crag', h('1e1d1c'), h('2a2826'), noise=3.0)
    material('blackweb', h('3a3a3e'), h('4a4a50'), noise=2.0, ao=False)
    material('spider', h('0e0d0c'), h('1a1816'), noise=3.0, spec=0.5, refl=20)
    material('spiderleg', h('121110'))
    material('spidereye', h('c02018'), emission=1.5, ao=False)
    material('husk', h('8a8a86'), h('7a7a76'), noise=4.0)
    material('bone', h('a8a49a'))
    material('deadwood', h('141312'))

    # the leaden sea in front is the flat part of the base itself (kept above z=0)
    terrain_polar(b, ground, lambda x, y, z, s: 'sea' if z < 0.2 and y < -14 else 'blackshore', R=31, cy=2,
                  nr=40, na=130, edge=0.12)

    # --- crags and a ravine opening in the middle
    for k in range(16):
        s = -1 if k % 2 else 1
        x = s * (5.0 + 1.6 * (k // 2)) + b.rng.uniform(-0.6, 0.6)
        y = 2.0 + b.rng.uniform(-3.0, 8.0)
        spire(b, 'crag', x, y, ground(x, y) - 0.5, b.rng.uniform(8.0, 16.0), b.rng.uniform(1.8, 3.0),
              lean=s * b.rng.uniform(-10, 4), jitter=0.25)
    for k in range(8):
        x, y = b.rng.uniform(-26, 26), b.rng.uniform(-12, -4)
        if abs(x) < 6:
            continue
        spire(b, 'crag', x, y, ground(x, y) - 0.4, b.rng.uniform(3.0, 6.0), b.rng.uniform(1.0, 1.8), jitter=0.25)

    # --- the black webs: sheets and strands between the crags
    for (x, y, z, r) in ((-6.5, 3.0, 6.0, 4.5), (6.5, 4.0, 6.5, 4.5), (0.0, 9.0, 9.0, 5.5), (-12.0, 6.0, 9.0, 3.8),
                         (12.0, 6.5, 9.5, 3.8)):
        web(b, 'blackweb', (x, y, ground(x, y) + z), (1, 0.15, 0), (0, 0.2, 1), r=r, n=12, rings=4, thickness=0.06)
    for k in range(20):
        x0, y0 = b.rng.uniform(-16, -3), b.rng.uniform(-4, 10)
        x1, y1 = b.rng.uniform(3, 16), b.rng.uniform(-4, 10)
        strut(b, 'blackweb', (x0, y0, ground(x0, y0) + b.rng.uniform(2, 7)),
              (x1, y1, ground(x1, y1) + b.rng.uniform(2, 7)), 0.05, 0.05, n=3)

    # --- Ungoliant in the ravine
    UZ = ground(0, 1.5)
    spider(b, 0.0, 1.5, UZ - 0.3, s=4.4, body='spider', leg='spiderleg', eye='spidereye')
    fx(b, 'Eyes', (0.0, 1.5 - 0.78 * 4.4, UZ + 1.02 * 4.4), 'RED_EYES')
    # cold mist creeping over the shore
    for k, (x, y) in enumerate(((-14.0, -10.0), (14.0, -9.0), (0.0, -12.0), (-22.0, -4.0), (22.0, -3.0))):
        fx(b, 'Mist_%d' % k, (x, y, ground(x, y) + 0.8), 'MIST')

    # --- drained husks, bones and dead driftwood on the strand
    for (x, y) in ((-5.0, -7.0), (5.5, -6.0), (-9.0, -12.0), (9.5, -13.0), (2.0, -10.5)):
        z = ground(x, y)
        sphere(b, 'husk', x, y, z + 0.5, 0.55, n=8, rings=6, squash=0.7)
    for k in range(10):
        x, y = b.rng.uniform(-20, 20), b.rng.uniform(-15, -6)
        z = ground(x, y)
        curve(b, 'bone', [(x, y, z + 0.1), (x + 0.8, y + 0.4, z + 0.5), (x + 1.6, y, z + 0.1)], 0.11, 0.07, n=4)
    for (x, y) in ((-18.0, -10.0), (17.0, -11.0), (-24.0, -2.0), (24.0, 0.0)):
        dead_tree(b, 'deadwood', x, y, ground(x, y) - 0.2, h=b.rng.uniform(3.0, 5.0), r=0.2)


PREVIEW = [((4, -34, 16), (0, 0, 6), 45)]
