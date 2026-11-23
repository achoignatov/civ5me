"""A great city of Harad (Southrons / Haradrim).

Book/film features modelled:
  * the hot desert lands of the far South: sand, dunes and date palms;
  * a walled city of sun-baked sandstone with flat roofs, square towers and a palace
    under a great gilded dome flanked by slender towers;
  * a stepped temple-pyramid to the Dark Lord;
  * the Haradrim colours of the films: crimson and black with gold, the black serpent
    banner on scarlet ("the Black Serpent on scarlet", book);
  * a mûmak (oliphaunt) at the gate: a vast beast with many tusks bearing a red-canopied
    war-tower on its back.
"""
import math

from blib import (material, hexcol as h, box, ring, cyl, cone, lathe, terrain_polar, blob, strut, curve, prism,
                  crenels, dome, pyramid, sphere, window_row, T)


def ground(x, y):
    z = 0.7 + 0.4 * math.sin(x * 0.22 + y * 0.1) * math.sin(y * 0.27)
    # dunes rising behind the city
    if y > 12:
        t = min(1.0, (y - 12) / 14)
        z += 7.0 * t * (0.6 + 0.4 * math.sin(x * 0.28 + 1.3)) + 1.5 * math.sin(x * 0.6 + y * 0.4) * t
    return z


def build(b):
    material('sandstone', h('c9a46a'), h('b8925c'), noise=2.0, courses=0.75, course_dark=0.85)
    material('mudbrick', h('b68f5e'), h('a37f52'), noise=2.5)
    material('sand', h('d9bd84'), zramp=[(0, h('d4b67c')), (4, h('dcc08a')), (9, h('e0c793'))])
    material('crimson', h('9a1f1a'))
    material('blackserpent', h('141414'))
    material('dome', h('d6a63a'), h('c08f2c'), noise=3.0)
    material('palm', h('3f6b2a'), h('4f7f33'), noise=3.0)
    material('palmtrunk', h('7a5a3a'), h('6a4c30'), noise=6.0, courses=0.3, course_dark=0.75)
    material('mumak', h('6d625a'), h('5f554e'), noise=2.0)
    material('tusk', h('ece4d0'))
    material('oasis', h('3f8a8a'), ao=False)

    terrain_polar(b, ground, lambda x, y, z, s: 'sand', R=31, cy=0, nr=30, na=100)

    # --- city walls with square towers
    W, D, cy = 14.0, 11.0, 2.0
    corners = [(-W, cy - D), (W, cy - D), (W, cy + D), (-W, cy + D)]
    for i in range(4):
        (x0, y0), (x1, y1) = corners[i], corners[(i + 1) % 4]
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        if i == 0:
            for s in (-1, 1):
                seg = W - 2.4
                box(b, 'sandstone', s * (2.4 + seg / 2), y0, 0.0, seg, 1.4, 4.5)
        else:
            box(b, 'sandstone', (x0 + x1) / 2, (y0 + y1) / 2, 0.0, L, 1.4, 4.5, rz=ang)
        k = int(L / 1.1)
        for j in range(k + 1):
            t = j / k
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if i == 0 and abs(x) < 2.6:
                continue
            box(b, 'sandstone', x, y, 4.5, 0.5, 0.5, 0.6, rz=ang)
        box(b, 'sandstone', x0, y0, 0.0, 3.0, 3.0, 7.0)
        crenels(b, 'sandstone', 1.3, 7.0, 0, 360, size=0.5, h=0.6, step=1.1, x=x0, y=y0, depth=0.5)
    # gate towers and the gate arch, scarlet serpent banners
    for s in (-1, 1):
        box(b, 'sandstone', s * 2.9, cy - D, 0.0, 2.4, 2.6, 8.0)
        crenels(b, 'sandstone', 1.05, 8.0, 0, 360, size=0.45, h=0.55, step=1.0, x=s * 2.9, y=cy - D, depth=0.4)
        box(b, 'crimson', s * 2.9, cy - D - 1.33, 3.0, 1.4, 0.06, 4.0)
        box(b, 'blackserpent', s * 2.9, cy - D - 1.37, 4.0, 0.25, 0.04, 2.4)
        box(b, 'blackserpent', s * 2.9 + 0.25, cy - D - 1.37, 5.9, 0.6, 0.04, 0.25)
    box(b, 'sandstone', 0, cy - D, 4.2, 3.6, 2.0, 1.4)
    box(b, 'window', 0, cy - D - 0.7, 0.0, 3.4, 0.2, 4.2)

    # --- flat-roofed houses
    rng = b.rng
    for k in range(260):
        x, y = rng.uniform(-W + 2, W - 2), rng.uniform(cy - D + 2.2, cy + D - 2)
        if math.hypot(x - 0, y - (cy + 3.0)) < 7.5 or (abs(x) < 2.2 and y < cy):
            continue
        if math.hypot(x + 8.5, y - (cy + 4.5)) < 4.0:
            continue
        if rng.random() < 0.72:
            continue
        w, d, hh = rng.uniform(1.6, 2.6), rng.uniform(1.6, 2.6), rng.uniform(1.6, 3.4)
        m = rng.choice(['mudbrick', 'sandstone', 'mudbrick'])
        box(b, m, x, y, 0.2, w, d, hh)
        box(b, m, x, y, 0.2 + hh, w + 0.12, d + 0.12, 0.18)
        window_row(b, 'window', x - w / 2 + 0.3, y - d / 2 - 0.02, x + w / 2 - 0.3, y - d / 2 - 0.02, 0.2 + hh * 0.5,
                   max(1, int(w / 1.0)), w=0.25, h=0.45, out=0.0)
        if rng.random() < 0.25:
            box(b, 'crimson', x, y, 0.2 + hh + 0.18, w * 0.6, d * 0.6, 0.06)

    # --- the palace with its gilded dome and slender towers
    px, py = 0.0, cy + 3.0
    box(b, 'sandstone', px, py, 0.2, 10.0, 8.0, 5.0)
    box(b, 'sandstone', px, py, 5.2, 10.6, 8.6, 0.3)
    lathe(b, 'sandstone', [(3.3, 0), (3.3, 2.0), (0, 2.0)], n=16, x=px, y=py, z=5.5, smooth=False)
    lathe(b, 'dome', [(3.6, 0), (3.6, 0.5), (3.3, 2.4), (2.6, 4.0), (1.4, 5.2), (0.3, 6.0), (0.0, 6.6)], n=20, x=px,
          y=py, z=7.5, smooth=True)
    lathe(b, 'dome', [(0.15, 0), (0.0, 1.6)], n=6, x=px, y=py, z=14.1, smooth=False)
    for s in (-1, 1):
        tx, ty = px + s * 5.6, py - 3.6
        lathe(b, 'sandstone', [(0.9, 0), (0.75, 12.0), (1.15, 12.5), (1.15, 13.0), (0.6, 13.2), (0.6, 14.6)], n=10,
              x=tx, y=ty, z=0.2, smooth=False)
        dome(b, 'dome', tx, ty, 14.8, 0.8, n=10, rings=4, h=1.1)
        lathe(b, 'dome', [(0.08, 0), (0.0, 1.0)], n=5, x=tx, y=ty, z=15.9, smooth=False)
    for k in range(6):
        box(b, 'window', px - 3.8 + 1.52 * k, py - 4.03, 1.4, 0.55, 0.08, 2.4)
    box(b, 'crimson', px, py - 4.05, 4.0, 10.0, 0.06, 0.4)

    # --- stepped temple-pyramid
    tx, ty = -8.5, cy + 4.5
    for i in range(5):
        w = 7.0 - 1.3 * i
        box(b, 'sandstone', tx, ty, 0.2 + 1.3 * i, w, w, 1.3)
    box(b, 'blackserpent', tx, ty, 0.2 + 6.5, 1.6, 1.6, 1.6)
    for i in range(7):
        box(b, 'sandstone', tx, ty - 3.5 - 0.0 + 0.5 * i, 0.2 + 0.0 + 0.9 * i, 1.4, 0.6, 0.4)

    # --- palms and an oasis pool outside the walls
    ring(b, 'oasis', 0.05, 3.2, 0.62, 0.02, 0, 360, n=18, x=19.0, y=-8.0, inner=False)
    for (x, y) in ((16.0, -6.0), (21.5, -5.5), (22.0, -10.5), (16.5, -11.0), (-18.0, -9.0), (-20.5, -4.0),
                   (18.5, 9.0), (-19.0, 10.0), (-16.0, -13.0)):
        palm(b, x, y, ground(x, y) - 0.1, b.rng)

    # --- a mûmak with its war-tower at the gate
    mumak(b, 9.5, -16.0, ground(9.5, -16.0), rz=-25)


def palm(b, x, y, z, rng):
    hgt = rng.uniform(5.0, 7.0)
    lean = rng.uniform(-0.8, 0.8)
    curve(b, 'palmtrunk', [(x, y, z), (x + lean * 0.4, y, z + hgt * 0.5), (x + lean, y + 0.2, z + hgt)], 0.28, 0.18, n=6)
    tx, ty, tz = x + lean, y + 0.2, z + hgt
    for k in range(8):
        a = math.radians(45 * k + rng.uniform(-10, 10))
        ex, ey = tx + 2.4 * math.cos(a), ty + 2.4 * math.sin(a)
        mx_, my_ = tx + 1.3 * math.cos(a), ty + 1.3 * math.sin(a)
        # a frond: a thin bent blade
        for (p0, p1) in (((tx, ty, tz), (mx_, my_, tz + 0.5)), ((mx_, my_, tz + 0.5), (ex, ey, tz - 0.6))):
            L = math.dist(p0, p1)
            yaw = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
            pitch = math.degrees(math.atan2(p1[2] - p0[2], math.hypot(p1[0] - p0[0], p1[1] - p0[1])))
            box(b, 'palm', 0, 0, -0.04, L + 0.1, 0.7, 0.08,
                M=T((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2, rz=yaw, ry=-pitch))


def mumak(b, x, y, z, rz=0.0):
    """A war-oliphaunt of Harad: huge grey body, four pillar legs, a long trunk, many tusks, a war-tower."""
    M = T(x, y, z, rz=rz)

    def P(px, py, pz):
        v = M @ __import__('mathutils').Vector((px, py, pz))
        return (v.x, v.y, v.z)
    # legs
    for sx in (-1, 1):
        for sy in (-1, 1):
            strut(b, 'mumak', P(sx * 2.2, sy * 1.3, 0.0), P(sx * 2.2, sy * 1.3, 4.6), 0.85, 0.95, n=8)
    # body and head
    sphere(b, 'mumak', 0, 0, 0, 1.0, n=14, rings=8, M=M @ T(0, 0, 6.0, s=(4.6, 2.9, 2.8)))
    sphere(b, 'mumak', 0, 0, 0, 1.0, n=12, rings=8, M=M @ T(-4.6, 0, 6.6, s=(1.8, 1.7, 1.9)))
    # ears
    for sy in (-1, 1):
        box(b, 'mumak', 0, 0, -1.0, 0.25, 2.2, 2.0, M=M @ T(-4.2, sy * 1.6, 6.4, rz=sy * 25))
    # trunk
    curve(b, 'mumak', [P(-6.0, 0, 6.6), P(-7.0, 0, 5.2), P(-7.3, 0, 3.0), P(-6.9, 0, 1.4), P(-6.3, 0, 0.9)], 0.55, 0.22,
          n=7)
    # tusks: two great pairs curving forward and up
    for sy in (-1, 1):
        for (zz, L, spread) in ((5.6, 3.2, 0.7), (6.3, 2.4, 1.1)):
            curve(b, 'tusk', [P(-5.6, sy * spread, zz), P(-7.2, sy * (spread + 0.3), zz - 0.9),
                              P(-8.6, sy * (spread + 0.4), zz - 0.2), P(-9.0 - L * 0.2, sy * (spread + 0.3), zz + 1.0)],
                  0.3, 0.0, n=6)
    # war-tower (howdah) with a red canopy
    box(b, 'wood', 0, 0, 0, 3.4, 2.6, 2.0, M=M @ T(0.3, 0, 8.4))
    for sx in (-1, 1):
        for sy in (-1, 1):
            strut(b, 'wood', P(0.3 + sx * 1.5, sy * 1.1, 10.4), P(0.3 + sx * 1.5, sy * 1.1, 12.2), 0.1, 0.1, n=4)
    from blib import hipped
    v = M @ __import__('mathutils').Vector((0.3, 0, 12.2))
    hipped(b, 'crimson', v.x, v.y, v.z, 3.8, 3.0, 1.3, rz=rz, overhang=0.2)
    box(b, 'crimson', 0, 0, 0, 3.8, 3.0, 0.9, M=M @ T(0.3, 0, 7.9))

# the city is laid out in ~22 units; scaled to fill the tile (pipeline FILL)
FILL = 1.2
