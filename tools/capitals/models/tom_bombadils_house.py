"""Tom Bombadil's House, at the eastern edge of the Old Forest.

The Fellowship of the Ring, "In the House of Tom Bombadil": the path from the Withywindle
climbs to "a long low house" of stone "under the brow of a hill", with "a shoulder of grey
rock" behind; Goldberry sits "surrounded by bowls of water-lilies"; candles burn in every
window; hedges, flowers, a lawn "close-trimmed"; down by the river, Old Man Willow, the
great grey willow of the Old Forest; and the Barrow-downs rising beyond.
Modelled: the long low stone house with its golden lit windows (animated candles) and smoke,
set against a grassy hill with a grey rock shoulder, gardens and hedges, a lily pool, the
winding Withywindle with Old Man Willow leaning over it, the Old Forest at the sides, and
Tom himself in his blue jacket and yellow boots with a feather in his hat.
The house faces the camera (-Y).
"""
import math

from blib import (material, hexcol as h, box, gable, hipped, cyl, cone, lathe, terrain_polar, blob, strut, sphere,
                  T, near_path, curve, window_row)
from city_common import (person, fx, scatter_forest, fence, plate, tree, dead_tree)


def sm(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ground(x, y):
    z = 0.8 + 0.3 * math.sin(x * 0.3) * math.cos(y * 0.25)
    z += 8.0 * sm((y - 6.0) / 14.0) * math.exp(-(x / 22.0) ** 2)        # the hill behind
    return z


RIVER = [(-22.0, -17.5), (-18.0, -20.0), (-6.0, -17.0), (6.0, -20.5), (18.0, -18.0), (22.5, -16.5)]
PATH = [(0, -16), (1, -10), (0, -2)]


def build(b):
    material('lawn', h('6c9c40'), zramp=[(-1, h('689a3e')), (3, h('74a046')), (8, h('7a9a4c'))], noise=0.5)
    material('road', h('a8946a'), h('968460'), noise=2.0)
    material('greystone', h('a29e92'), h('908c80'), noise=2.0, courses=0.5, course_dark=0.85)
    material('rock', h('8a877e'), h('7a776e'), noise=2.5)
    material('thatch', h('b49a52'), h('a08844'), noise=3.0)
    material('window', h('ffc860'), emission=1.2)
    material('door', h('3a6a3a'))
    material('river', h('4a7a8a'), h('5a8a9a'), noise=1.0, ao=False, spec=0.7, refl=50)
    material('lily', h('f0f0e8'), h('f0d8e8'), noise=6.0)
    material('lilypad', h('3a7a34'))
    material('willow', h('7a8a4a'), h('8a9a52'), noise=2.0)
    material('willowbark', h('5a5448'), h('4a463c'), noise=5.0)
    material('oldforest', h('2e4a24'), h('385a2c'), noise=1.5)
    material('bark', h('3e3226'))
    material('hedge', h('3e6a2c'), h('4a7a34'), noise=2.0)
    material('flower', h('e8d040'), h('d86070'), noise=10.0)
    material('blue', h('2a5aa8'))
    material('yellow', h('e8c030'))
    material('skin', h('e0a888'))
    material('beard', h('8a5a30'))
    material('feather', h('2a6aa8'))

    def mat(x, y, z, s):
        if near_path(x, y, PATH, 1.2):
            return 'road'
        return 'lawn'

    terrain_polar(b, ground, mat, R=31, cy=2, nr=38, na=124)

    # --- the Withywindle across the front, above the ground plane
    for (x0, y0), (x1, y1) in zip(RIVER, RIVER[1:]):
        z0, z1 = ground(x0, y0) + 0.1, ground(x1, y1) + 0.1
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * 2.2, dx / L * 2.2
        b.add([(x0 - nx, y0 - ny, z0), (x1 - nx, y1 - ny, z1), (x1 + nx, y1 + ny, z1), (x0 + nx, y0 + ny, z0)],
              [(0, 1, 2, 3)], 'river')
    for k in range(9):
        y = -19.5 + 7.0 * k / 8
        box(b, 'greystone', 0.0, y, 1.0 + 0.5 * math.sin(math.pi * k / 8) - 0.3, 2.4, 0.9, 0.35)
    # --- Old Man Willow leaning over the river
    wx, wy = -14.0, -16.5
    wz = ground(wx, wy)
    curve(b, 'willowbark', [(wx, wy, wz - 0.3), (wx + 0.6, wy - 0.8, wz + 3.0), (wx + 2.0, wy - 2.6, wz + 6.0),
                            (wx + 3.0, wy - 4.0, wz + 7.5)], 1.3, 0.5, n=8)
    for k in range(9):
        a = 2 * math.pi * k / 9
        top = (wx + 3.0 + 3.6 * math.cos(a), wy - 4.0 + 3.0 * math.sin(a), wz + 8.0)
        strut(b, 'willowbark', (wx + 3.0, wy - 4.0, wz + 7.5), top, 0.3, 0.1, n=4)
        for j in range(3):   # drooping fronds
            p = (top[0] + 0.6 * (j - 1), top[1], top[2])
            strut(b, 'willow', (p[0], p[1] - 0.2, p[2] - 4.5 + j), p, 0.08, 0.35, n=4)
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.4
        strut(b, 'willowbark', (wx, wy, wz + 0.3), (wx + 2.6 * math.cos(a), wy + 2.6 * math.sin(a), wz - 0.2), 0.5, 0.12, n=5)

    # --- the long low house, under the brow of the hill
    HX, HY = 0.0, 4.0
    hz = ground(HX, HY) - 0.4
    box(b, 'greystone', HX, HY, hz, 15.0, 5.2, 3.4)
    hipped(b, 'thatch', HX, HY, hz + 3.4, 15.0, 5.2, 2.6, overhang=0.6, ridge=0.6)
    box(b, 'greystone', HX - 5.0, HY + 1.0, hz + 3.0, 1.2, 1.2, 4.2)
    fx(b, 'Smoke', (HX - 5.0, HY + 1.0, hz + 7.8), 'SMOKE')
    box(b, 'door', HX, HY - 2.63, hz + 0.3, 1.4, 0.1, 2.3)
    gable(b, 'thatch', HX, HY - 3.4, hz + 2.8, 3.0, 1.8, 0.8, overhang=0.15)
    for sd in (-1, 1):
        cyl(b, 'greystone', HX + sd * 1.2, HY - 4.0, hz + 0.3, 0.18, 2.5, n=6)
    for k, x in enumerate((-6.0, -4.0, -2.2, 2.2, 4.0, 6.0)):
        box(b, 'window', HX + x, HY - 2.62, hz + 1.4, 0.9, 0.1, 1.0)
        if k in (1, 4):
            fx(b, 'Candle_%d' % k, (HX + x, HY - 2.9, hz + 1.6), 'CANDLE')
    # the grey rock shoulder behind
    for k in range(6):
        blob(b, 'rock', -9.0 + 3.0 * k, HY + 7.0 + (k % 2), ground(-9 + 3 * k, HY + 7) - 1.0, 2.6 + (k % 3) * 0.5,
             n=8, rings=5, squash=0.8, jitter=0.25)

    # --- gardens, hedges, the lily pool, Goldberry's bowls
    for row in range(3):
        for k in range(12):
            x, y = -11.0 + 2.0 * k, -3.5 - 1.6 * row
            if abs(x) < 1.6:
                continue
            blob(b, 'flower' if (k + row) % 2 else 'hedge', x, y, ground(x, y) - 0.1, 0.55, n=6, rings=3, squash=0.7)
    for sd in (-1, 1):
        for k in range(10):
            x = sd * (2.0 + 1.1 * k)
            blob(b, 'hedge', x, -9.5, ground(x, -9.5) - 0.1, 0.8, n=6, rings=4, squash=0.9)
    px, py = 9.0, -11.0
    lathe(b, 'river', [(2.6, -0.4), (2.6, ground(px, py) + 0.15), (0, ground(px, py) + 0.15)], n=20, x=px, y=py)
    for k in range(10):
        a = 2 * math.pi * k / 10
        x, y = px + 1.7 * math.cos(a), py + 1.4 * math.sin(a)
        cyl(b, 'lilypad', x, y, ground(px, py) + 0.16, 0.45, 0.04, n=8)
        sphere(b, 'lily', x, y, ground(px, py) + 0.3, 0.2, n=6, rings=4, squash=0.7)

    # --- Tom Bombadil: blue jacket, yellow boots, battered hat with a long blue feather
    tx, ty = 3.0, -6.0
    tz = ground(tx, ty)
    for sd in (-1, 1):
        cyl(b, 'yellow', tx + sd * 0.25, ty, tz, 0.2, 0.7, n=6)
    person(b, tx, ty, tz + 0.5, s=1.25, robe='blue', skin='skin', hat='bark', beard='beard')
    strut(b, 'feather', (tx + 0.2, ty, tz + 0.5 + 2.6), (tx + 0.9, ty + 0.3, tz + 0.5 + 3.6), 0.07, 0.01, n=4)

    # --- the Old Forest at the sides, the downs behind
    scatter_forest(b, 70, -31, 31, -29, 33, ground, avoid=((-13, 13, -14, 12), (-19, -8, -24, -12)), min_dist=2.6,
                   max_r=30.5, h=(6.0, 9.5), r=(1.6, 2.4), leaves='oldforest', trunk='bark')


PREVIEW = [((4, -32, 16), (0, -2, 4), 45)]
