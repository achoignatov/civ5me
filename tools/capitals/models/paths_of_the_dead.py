"""The Paths of the Dead: the Dark Door of the Dwimorberg.

The Return of the King: beyond Dunharrow "a double line of standing stones" leads through
the Dimholt, "a wood of black trees", to "a sheer wall of rock, and in the wall the Dark
Door gaped before them like the mouth of night"; "signs and figures were carved above its
wide arch"; "the Dead are following" with a pale light. Films: a skull-strewn cavern mouth
and the ghostly green host of the Oathbreakers.
Modelled: the cliff of the Dwimorberg (Haunted Mountain) rising behind, the arched Dark Door
with carved figures, a road between two lines of weathered standing stones through a grove
of black dead trees, skulls and the bones of Baldor's day, the green ghost-light of the Dead
in the doorway and along the stones (animated).
The door faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, gable, cyl, cone, lathe, terrain_polar, blob, strut, sphere,
                  T, near_path, curve)
from city_common import (standing_stone, dead_tree, fx, spire, person)


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = 0.6 + 0.35 * math.sin(x * 0.4) * math.cos(y * 0.33)
    if y > 6.0:                       # the cliff of the Dwimorberg
        t = sm((y - 6.0) / 5.0)
        z = max(z, 0.6 + 34.0 * t * (0.85 + 0.15 * math.sin(x * 0.45)))
    return z


PATH = [(0, -31), (0, -10), (0, 5)]


def build(b):
    material('greygrass', h('5c6448'), zramp=[(-1, h('596046')), (2, h('606a4a')), (6, h('5a5a54')), (20, h('6a6864')),
                                              (34, h('8a8884'))], slope_color=h('4e4c48'), slope_start=0.45, noise=0.8)
    material('road', h('6a665c'), h('5a564e'), noise=2.0)
    material('cliff', h('4e4c48'), h('3e3c3a'), noise=2.5, courses=1.4, course_dark=0.86)
    material('stone', h('7a7870'), h('686660'), noise=3.0)
    material('carving', h('5e5c56'), h('6e6c66'), noise=6.0)
    material('blackwood', h('1c1a18'), h('2a2622'), noise=3.0)
    material('bone', h('d8d0bc'), h('c8bea8'), noise=3.0)
    material('ghost', h('8af0a0'), emission=1.6, ao=False)
    material('rust', h('6a4a30'), h('5a3a24'), noise=5.0)

    terrain_polar(b, ground, lambda x, y, z, s: 'road' if near_path(x, y, PATH, 1.8) and z < 3 else 'greygrass',
                  R=31, cy=2, nr=40, na=130)

    # --- the cliff face and the Dark Door
    DY = 8.6
    box(b, 'cliff', 0, DY + 1.6, 0.0, 26.0, 3.0, 22.0)
    for k in range(9):
        x = -12 + 3.0 * k
        lathe(b, 'cliff', [(2.0, 0), (1.8, 8.0), (1.4, 16.0), (0.8, 22.0 + (k % 3) * 2), (0, 24.0 + (k % 3) * 2)],
              n=6, x=x, y=DY + 0.6 + 0.4 * (k % 2), z=0.0, smooth=False, jitter=0.18)
    # the arch: a dark half-disc opening with a carved surround
    lathe(b, 'window', [(0, 0), (4.4, 0), (4.4, 0.25), (0, 0.25)], n=24, a0=0, a1=180,
          M=T(0, DY - 1.2, 5.0, rx=90))
    box(b, 'window', 0, DY - 1.32, 0.0, 8.8, 0.25, 5.0)
    lathe(b, 'carving', [(4.4, 0), (5.6, 0), (5.6, 0.7), (4.4, 0.7)], n=24, a0=0, a1=180, M=T(0, DY - 1.0, 5.0, rx=90),
          smooth=False)
    for s in (-1, 1):
        box(b, 'carving', s * 5.0, DY - 1.35, 0.0, 1.2, 0.7, 5.0)
    for k in range(7):                                                # signs and figures above the arch
        a = math.radians(15 + 25 * k)
        box(b, 'carving', 6.3 * math.cos(a), DY - 1.45, 5.0 + 6.3 * math.sin(a), 0.7, 0.3, 1.2,
            rz=0)
    for k in range(5):
        fx(b, 'Ghost_Door_%d' % k, (-3.2 + 1.6 * k, DY - 2.0, 1.5 + (k % 2) * 1.6), 'GHOST')
    # the Dead: pale shapes in the doorway
    for k, x in enumerate((-2.6, -0.8, 1.0, 2.8)):
        lathe(b, 'ghost', [(0.42, 0), (0.48, 0.1), (0.36, 1.1), (0.22, 1.45), (0, 1.45)], n=8, x=x, y=DY - 2.2 - 0.5 * (k % 2),
              z=0.6, smooth=True)
        sphere(b, 'ghost', x, DY - 2.2 - 0.5 * (k % 2), 2.3, 0.26, n=8, rings=5)
        strut(b, 'ghost', (x + 0.35, DY - 2.3, 0.7), (x + 0.4, DY - 2.4, 2.9), 0.05, 0.05, n=4)

    # --- the double line of standing stones along the road
    for k in range(8):
        y = -27.0 + 4.0 * k
        for s in (-1, 1):
            x = s * (3.4 + 0.3 * math.sin(k))
            standing_stone(b, 'stone', x, y, ground(x, y) - 0.3, h=2.6 + 0.6 * ((k + (s > 0)) % 3), w=0.75,
                           rz=b.rng.uniform(-20, 20), lean=b.rng.uniform(-6, 6))
            if k % 3 == 1:
                fx(b, 'Ghost_Stone_%d_%s' % (k, 'L' if s < 0 else 'R'), (x, y, ground(x, y) + 3.3), 'GHOST')

    # --- the Dimholt: black, dead trees all around, skulls and Baldor's bones
    for k in range(60):
        x, y = b.rng.uniform(-30, 30), b.rng.uniform(-29, 7)
        if math.hypot(x, y - 2) > 29.5 or abs(x) < 6:
            continue
        dead_tree(b, 'blackwood', x, y, ground(x, y) - 0.3, h=b.rng.uniform(4.5, 8.0), r=b.rng.uniform(0.2, 0.32))
    for k in range(18):
        x, y = b.rng.uniform(-6, 6), b.rng.uniform(-6, 6)
        z = ground(x, y)
        sphere(b, 'bone', x, y, z + 0.25, 0.28, n=7, rings=5, squash=1.15)
        box(b, 'window', x, y - 0.24, z + 0.25, 0.22, 0.06, 0.14)
    # Baldor, son of Brego, who went in and never came out: a skeleton in rusted mail at the door
    curve(b, 'bone', [(1.5, DY - 3.0, 0.7), (1.9, DY - 3.4, 1.0), (2.6, DY - 3.6, 1.1)], 0.18, 0.12, n=5)
    box(b, 'rust', 1.7, DY - 3.2, 0.6, 1.0, 0.6, 0.5)
    sphere(b, 'bone', 2.8, DY - 3.6, 1.25, 0.28, n=7, rings=5)
    strut(b, 'rust', (0.6, DY - 3.0, 0.65), (0.0, DY - 4.2, 0.65), 0.05, 0.05, n=4)  # his sword
    for (x, y, hh) in ((-24, 2, 10), (24, 3, 11), (-27, -8, 6), (27, -6, 7)):
        spire(b, 'cliff', x, y, ground(x, y) - 0.5, hh, 2.6)


PREVIEW = [((4, -32, 16), (0, 4, 6), 45)]
