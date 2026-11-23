"""Rivendell (Imladris), the Last Homely House east of the Sea (High Elves).

Book/film features modelled:
  * a deep, narrow valley under steep cliffs, the river Bruinen rushing below, many
    waterfalls pouring down the rock walls;
  * the Last Homely House and its many halls built on terraces against the cliff:
    pale stone, slender pillars, tall arched windows and the film's steep, curving
    art-nouveau roofs of weathered bronze;
  * open pavilions with domed roofs (the porch where the Council of Elrond met),
    a slender watch tower with an elven spire, graceful arched bridges;
  * autumn woods of gold and russet with dark pines.
"""
import math

from blib import (material, hexcol as h, box, ring, cyl, cone, lathe, terrain_polar, blob, strut, curve, prism, tree,
                  conifer, dome, window_row, gable)


def ground(x, y):
    # valley floor along X at the front; cliffs rising behind (+Y) and on the left
    z = 1.0 + 0.4 * math.sin(x * 0.5)
    if y > -6:
        t = min(1.0, (y + 6) / 22.0)
        z = 1.0 + 34.0 * t ** 0.8
    # terraces cut into the slope for the buildings
    for (ty, tz, tx0, tx1) in ((-2.5, 6.0, -14, 14), (4.0, 12.0, -10, 12), (10.0, 18.0, -4, 10)):
        if tx0 < x < tx1 and ty - 3.5 < y < ty + 3.5:
            z = tz
    z += 1.8 * math.sin(x * 0.4 + y * 0.3) * math.sin(y * 0.5) * min(1.0, max(0.0, (y + 6) / 8))
    # the river gorge in front
    if -13 < y < -8:
        z = min(z, -0.5 + 0.4 * abs(y + 10.5))
    return z


def build(b):
    material('elfstone', h('e9e1cc'), h('d7ceb6'), noise=2.0, courses=0.7, course_dark=0.9)
    material('bronzeroof', h('6e5034'), h('5c432b'), noise=3.0)
    material('verdigris', h('557a66'), h('4a6b59'), noise=3.0)
    material('valley', h('6f7c4a'), zramp=[(-1, h('4b6b3a')), (2, h('638a3f')), (12, h('6a8442')), (24, h('7b8150')),
                                           (34, h('8a8a72'))], slope_color=h('858072'), slope_start=0.32)
    material('falls', h('e8f1f5'), h('c9dde6'), noise=6.0, ao=False)
    material('autumn1', h('c98a2a'), h('d9a63a'), noise=2.0)
    material('autumn2', h('a6522a'), h('c46b2f'), noise=2.0)
    material('autumn3', h('cfb03a'), h('b5952c'), noise=2.0)
    material('elfglass', h('2b3a45'))
    material('river2', h('6a98ab'), h('8fb8c8'), noise=2.0, ao=False)

    terrain_polar(b, ground, lambda x, y, z, s: 'valley', R=31, cy=2, nr=34, na=110)
    # river Bruinen in the gorge
    box(b, 'river2', 0, -10.5, -0.3, 47, 4.2, 0.42)

    # --- waterfalls pouring down the cliffs into the valley (draped on the rock face)
    from blib import T
    for (x, top, w) in ((-12.0, 26.0, 1.6), (4.5, 31.0, 2.2), (15.0, 24.0, 1.4), (-4.0, 22.0, 1.0), (-19.0, 20.0, 1.2)):
        pts = []
        y = 22.0
        while y > -8.0:
            z = ground(x, y)
            if z <= top:
                pts.append((y, z + 0.25))
            y -= 0.7
        for (y0, z0), (y1, z1) in zip(pts, pts[1:]):
            L = math.hypot(y1 - y0, z1 - z0)
            ang = math.degrees(math.atan2(z1 - z0, y1 - y0))
            box(b, 'falls', 0, 0, -0.1, w, L + 0.1, 0.2, M=T(x, (y0 + y1) / 2, (z0 + z1) / 2, rx=ang))
        if pts:
            blob(b, 'falls', x, pts[-1][0] - 0.8, pts[-1][1] - 0.9, w * 0.9, n=8, rings=3, squash=0.5)

    # --- the Last Homely House: halls on three terraces
    def hall(x, y, z, L, W, H, rz=0.0, roof='bronzeroof'):
        box(b, 'elfstone', x, y, z, L, W, H, rz=rz)
        # steep curving roof: a gable whose eaves sweep out (two stacked gables)
        # steep, curving elven roof: flared eaves, a steep upper pitch and a ridge crest
        gable(b, roof, x, y, z + H, L, W, 0.9, rz=rz, overhang=0.75)
        gable(b, roof, x, y, z + H + 0.5, L * 0.92, W * 0.7, 3.4, rz=rz, overhang=0.15)
        gable(b, roof, x, y, z + H + 3.4, L * 0.5, W * 0.12, 0.9, rz=rz, overhang=0.0)
        # tall arched windows on the front
        ca, sa = math.cos(math.radians(rz)), math.sin(math.radians(rz))
        fx, fy = x + sa * (W / 2 + 0.03), y - ca * (W / 2 + 0.03)
        window_row(b, 'elfglass', fx - ca * (L / 2 - 0.6), fy - sa * (L / 2 - 0.6), fx + ca * (L / 2 - 0.6),
                   fy + sa * (L / 2 - 0.6), z + 0.8, max(2, int(L / 1.3)), w=0.45, h=H * 0.55, out=0.0)

    hall(-6.0, -2.5, 6.0, 9.0, 4.0, 3.0)
    hall(6.5, -1.8, 6.0, 7.0, 3.6, 2.6, rz=-8)
    hall(1.0, 4.4, 12.0, 11.0, 4.4, 3.4, roof='bronzeroof')          # Elrond's house
    hall(-6.5, 4.0, 12.0, 5.0, 3.6, 2.6, rz=10, roof='verdigris')
    hall(5.0, 10.2, 18.0, 7.0, 3.4, 2.8, roof='verdigris')
    # colonnaded terraces (slender pillars along the terrace edges)
    for (y, z, x0, x1) in ((-6.2, 6.0, -12, 12), (0.6, 12.0, -9, 11), (6.6, 18.0, -3, 9)):
        n = int((x1 - x0) / 1.4)
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            cyl(b, 'elfstone', x, y, z, 0.12, 1.4, n=6)
        box(b, 'elfstone', (x0 + x1) / 2, y, z + 1.4, x1 - x0 + 0.3, 0.3, 0.15)

    # --- open pavilions with domed roofs (the porch of the Council)
    for (x, y, z, r) in ((-11.5, -3.0, 6.0, 1.7), (11.5, -2.5, 6.0, 1.5), (8.5, 4.5, 12.0, 1.4)):
        ring(b, 'elfstone', 0.05, r + 0.2, z, 0.3, 0, 360, n=16, x=x, y=y, inner=False)
        for k in range(8):
            a = math.radians(45 * k)
            cyl(b, 'elfstone', x + r * math.cos(a), y + r * math.sin(a), z + 0.3, 0.1, 2.4, n=5)
        dome(b, 'verdigris', x, y, z + 2.7, r + 0.35, n=16, rings=5, h=(r + 0.35) * 1.3)
        lathe(b, 'verdigris', [(0.12, 0), (0.0, 1.2)], n=6, x=x, y=y, z=z + 2.7 + (r + 0.35) * 1.3, smooth=False)

    # --- slender watch tower with an elven spire
    tx, ty, tz = -2.0, 11.0, ground(-2.0, 11.0) - 0.5
    lathe(b, 'elfstone', [(1.4, 0), (1.1, 1.0), (0.95, 11.0), (1.35, 11.6), (1.35, 12.2), (0, 12.2)], n=10, x=tx, y=ty,
          z=tz, smooth=False)
    # concave curving spire
    lathe(b, 'bronzeroof', [(1.55, 0), (1.0, 1.2), (0.55, 2.8), (0.25, 4.6), (0.05, 6.4), (0, 6.6)], n=10, x=tx, y=ty,
          z=tz + 12.2, smooth=False)
    for k in range(4):
        a = math.radians(90 * k + 45)
        box(b, 'elfglass', tx + 1.0 * math.cos(a), ty + 1.0 * math.sin(a), tz + 8.5, 0.35, 0.08, 1.5, rz=90 * k + 135)

    # --- graceful arched bridges over the river and a ravine
    for (x, w) in ((-2.0, 1.2), (12.0, 1.0)):
        pts = []
        for i in range(9):
            t = i / 8
            y = -13.5 + 7.0 * t
            pts.append((x, y, 1.2 + 2.2 * math.sin(math.pi * t) + 4.8 * t))
        for p0, p1 in zip(pts, pts[1:]):
            L = math.dist(p0[1:], p1[1:])
            ang = math.degrees(math.atan2(p1[2] - p0[2], p1[1] - p0[1]))
            from blib import T
            box(b, 'elfstone', 0, 0, -0.15, w, L + 0.05, 0.3,
                M=T(x, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2, rx=ang))

    # --- autumn woods and pines
    rng = b.rng
    for k in range(80):
        if k > 46:
            break
        x, y = rng.uniform(-28, 28), rng.uniform(-24, 24)
        if math.hypot(x, y - 2) > 29:
            continue
        if -15 < x < 15 and -7 < y < 13:
            continue
        if -13 < y < -8:
            continue
        z = ground(x, y)
        if rng.random() < 0.3:
            conifer(b, x, y, z - 0.2, h=5.5, r=1.4)
        else:
            tree(b, x, y, z - 0.2, h=4.0, r=1.7, leaves=rng.choice(['autumn1', 'autumn2', 'autumn3', 'leaves']))


PREVIEW = [((6, -26, 22), (0, 2, 10), 45)]
