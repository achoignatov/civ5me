"""Minas Tirith, the Tower of Guard (Gondor).

Book/film features modelled:
  * seven concentric walled circles cut into the eastern shoulder of Mount Mindolluin,
    each about 100 ft above the last, gates staggered from circle to circle;
  * the great rock prow (keel) that splits every circle except the first and juts out
    toward the Pelennor, crowned by a battlement level with the Citadel;
  * the Great Gate of iron in the first wall, facing the plain;
  * the Citadel: the White Tower of Ecthelion, "shining like a spike of pearl and silver",
    the Court of the Fountain with its green sward and the withered White Tree;
  * white stone city with grey-blue slate roofs, Mindolluin rising behind.
The city faces the camera (south, -Y), the mountain is behind it (+Y).
"""
import math

from blib import (material, hexcol as h, box, ring, crenels, lathe, cyl, cone, hipped, gable, terrain_polar,
                  prism, blob, sphere, window_row)

CX, CY = 0.0, 9.0                       # centre of the circles (inside the mountain flank)
RADII = [27.0, 23.6, 20.3, 17.1, 14.0, 11.0, 8.0]
TIER_H = 4.3
A0, A1 = 150.0, 390.0                   # arc of the walls (degrees, 270 = facing the camera)


def tier_top(k):
    return 2.2 + TIER_H * k


def build(b):
    material('whitestone', h('e6e3da'), h('cfccc2'), noise=0.6, courses=0.9, course_dark=0.86)
    material('paving', h('d2cdbf'), h('bdb8aa'), noise=1.5)
    material('slate', h('5f6773'), h('707986'), noise=2.5)
    material('roofred', h('8a6a5a'), h('77594b'), noise=2.0)
    material('silver', h('f4f6f8'), h('dfe4ea'), noise=3.0)
    material('treewhite', h('f2f1ea'), h('dddcd2'), noise=4.0)
    material('lawn', h('5d8a3a'), h('6e9a45'), noise=1.0)
    material('mountain', h('8b8780'), h('6f6c66'), noise=0.12)
    material('blackflag', h('15161a'))
    material('fountainwater', h('8fb7d0'), ao=False)

    # ---- Mount Mindolluin's shoulder behind the city (a broad massif, snow on the heights)
    material('mindolluin', h('8b8780'), zramp=[(0, h('6c8a3e')), (6, h('7f7a6c')), (20, h('8e8a83')),
                                               (38, h('77736c')), (46, h('e8ecef'))],
             slope_color=h('6f6b65'), slope_start=0.45)

    def mount(x, y):
        dy = y - (CY - 6)
        if dy <= 0:
            return 0.3
        t = min(1.0, dy / 24.0)
        prof = (3 * t * t - 2 * t * t * t)                    # smoothstep rise behind the city
        width = math.exp(-((x + 3) / 34.0) ** 4)              # broad, flat-topped massif
        rough = 2.2 * math.sin(x * 0.45 + y * 0.2) * math.sin(y * 0.33 - x * 0.12) + 1.4 * math.sin(x * 1.1 + 2 * y * 0.3)
        peak = 9.0 * math.exp(-((x - 5) / 9.0) ** 2 - ((y - 29) / 6.0) ** 2)
        return 0.3 + (44.0 * prof + rough * prof + peak) * width

    terrain_polar(b, mount, lambda x, y, z, s: 'mindolluin', R=31, sy=1.0, cy=4, nr=30, na=96)

    # ---- the seven circles (solid stepped sectors with white walls)
    for k, r in enumerate(RADII):
        z = tier_top(k)
        ring(b, 'whitestone', 0.05, r, -3.0, z + 3.0, A0, A1, n=96, x=CX, y=CY, inner=False, top=False)
        # paved top of the circle (annulus out to the wall)
        inner = RADII[k + 1] if k + 1 < len(RADII) else 0.05
        ring(b, 'paving', inner - 0.2, r, z - 0.02, 0.02, A0, A1, n=96, x=CX, y=CY, inner=False)
        # parapet + battlements
        ring(b, 'whitestone', r - 0.45, r, z, 0.8, A0, A1, n=96, x=CX, y=CY)
        crenels(b, 'whitestone', r - 0.22, z + 0.8, A0 + 2, A1 - 2, size=0.45, h=0.45, step=1.3, x=CX, y=CY, depth=0.4)
        # a band of darker mouldings at the foot of each wall reads as layered stone
        ring(b, 'paving', r, r + 0.15, z - TIER_H - 0.1 if k else -1.0, 0.5, A0, A1, n=96, x=CX, y=CY, inner=False)

    # ---- gates: the Great Gate faces the plain; the others alternate north-east / south-east
    gate_angles = [270, 235, 300, 240, 296, 248, 285]
    for k, (r, ga) in enumerate(zip(RADII, gate_angles)):
        z0 = tier_top(k - 1) if k else -0.5
        a = math.radians(ga)
        gx, gy = CX + (r + 0.05) * math.cos(a), CY + (r + 0.05) * math.sin(a)
        w = 3.0 if k == 0 else 1.6
        hh = 4.0 if k == 0 else 2.3
        box(b, 'iron' if k == 0 else 'window', gx, gy, z0, w, 0.35, hh, rz=ga + 90)
        # gatehouse towers beside each gate
        for s in (-1, 1):
            ta = math.radians(ga + s * (w * 0.75 + 0.9) / r * 57.3)
            tx, ty = CX + r * math.cos(ta), CY + r * math.sin(ta)
            box(b, 'whitestone', tx, ty, z0, 1.6, 1.6, tier_top(k) - z0 + 2.0, rz=ga + 90)
            crenels(b, 'whitestone', 0.62, tier_top(k) + 2.0, 0, 360, size=0.35, h=0.4, step=0.9, x=tx, y=ty, depth=0.3)

    # ---- the prow: a keel of rock from the Citadel out over the Great Gate. Its ridge is crowned
    # with a battlement level with the Citadel and falls away only at the outer point.
    tip = RADII[0] + 2.0
    root = RADII[-1] - 1.5
    pa = math.radians(270)
    ux, uy = math.cos(pa), math.sin(pa)       # outward direction (toward the camera)
    px, py = -uy, ux                          # sideways

    def P(r, s_):
        return (CX + ux * r + px * s_, CY + uy * r + py * s_)
    steps = 14
    rows = []
    for i in range(steps + 1):
        t = i / steps
        r = root + (tip - root) * t
        base_half = 3.6 * (1 - t) ** 0.7 + 0.25
        top_half = 0.7 * (1 - t) + 0.15
        ztop = tier_top(6) + 0.4 - 3.5 * max(0.0, (t - 0.55) / 0.45) ** 1.6
        rows.append((r, base_half, top_half, ztop))
    verts, faces = [], []
    for (r, bh, th, zt) in rows:
        for s_, z_ in ((-bh, -2.0), (bh, -2.0), (th, zt), (-th, zt)):
            x, y = P(r, s_)
            verts.append((x, y, z_))
    for i in range(steps):
        a_, c = 4 * i, 4 * (i + 1)
        faces += [(a_ + 0, c + 0, c + 3, a_ + 3), (c + 1, a_ + 1, a_ + 2, c + 2), (a_ + 3, c + 3, c + 2, a_ + 2)]
    e = 4 * steps
    faces.append((e + 0, e + 1, e + 2, e + 3))
    b.add(verts, faces, 'whitestone')
    for i in range(0, steps + 1, 2):
        r, bh, th, zt = rows[i]
        for s_ in (-1, 1):
            x, y = P(r, s_ * (th - 0.1))
            box(b, 'whitestone', x, y, zt, 0.32, 0.32, 0.5)

    # ---- houses on the circles 1..6
    for k in range(6):
        z = tier_top(k)
        r_out, r_in = RADII[k] - 0.7, RADII[k + 1] + 0.6
        rows = 2 if r_out - r_in > 3.2 else 1
        for row in range(rows):
            rr = r_out - 0.9 - row * 1.7
            n = int((A1 - A0 - 16) / 360 * 2 * math.pi * rr / 1.75)
            for i in range(n):
                a = A0 + 8 + (A1 - A0 - 16) * (i + 0.5) / n
                if abs(((a - 270) + 180) % 360 - 180) < 8 and k >= 1:
                    continue  # the prow passes here
                if b.rng.random() < 0.12:
                    continue
                ar = math.radians(a)
                x, y = CX + rr * math.cos(ar), CY + rr * math.sin(ar)
                w = b.rng.uniform(1.2, 1.6)
                d = b.rng.uniform(1.1, 1.4)
                hh = b.rng.uniform(1.4, 2.6) + (0.6 if row else 0)
                box(b, 'whitestone', x, y, z, w, d, hh, rz=a + 90, top=False)
                roof = 'slate' if b.rng.random() < 0.8 else 'roofred'
                hipped(b, roof, x, y, z + hh, w, d, 0.7, rz=a + 90, overhang=0.12)
                if b.rng.random() < 0.6:
                    window_row(b, 'window', x - 0.4 * math.cos(math.radians(a + 90)) - 0.5 * math.cos(ar) * 0 + d / 2 * math.cos(ar),
                               y - 0.4 * math.sin(math.radians(a + 90)) + d / 2 * math.sin(ar),
                               x + 0.4 * math.cos(math.radians(a + 90)) + d / 2 * math.cos(ar),
                               y + 0.4 * math.sin(math.radians(a + 90)) + d / 2 * math.sin(ar),
                               z + hh * 0.45, 2, w=0.22, h=0.42, out=0.0)
        # a few taller towers / halls with domes on the middle circles
        if 2 <= k <= 5:
            for a in (A0 + 30 + 17 * k, A1 - 35 - 13 * k):
                ar = math.radians(a)
                rr = (RADII[k] + RADII[k + 1]) / 2
                x, y = CX + rr * math.cos(ar), CY + rr * math.sin(ar)
                cyl(b, 'whitestone', x, y, z, 0.8, 5.0, n=10)
                cone(b, 'slate', x, y, z + 5.0, 1.0, 1.6, n=10)

    # ---- the Citadel (seventh circle)
    zc = tier_top(6)
    # White Tower of Ecthelion, at the back of the citadel
    tx, ty = CX + 0.0, CY + 1.2
    lathe(b, 'whitestone', [(2.1, 0), (2.1, 3.0), (1.55, 3.4), (1.45, 17.5), (1.75, 18.0), (1.75, 19.3),
                            (1.35, 19.6), (1.25, 22.0)], n=8, x=tx, y=ty, z=zc, smooth=False)
    # balcony battlement at the top of the shaft
    crenels(b, 'whitestone', 1.7, zc + 19.3, 0, 360, size=0.3, h=0.35, step=0.8, x=tx, y=ty)
    # silver pinnacle
    lathe(b, 'silver', [(1.3, 0), (0.95, 1.2), (0.35, 4.2), (0.08, 7.0), (0.0, 7.6)], n=8, x=tx, y=ty, z=zc + 22.0,
          smooth=False)
    # tall windows up the tower
    for k in range(4):
        a = 270 + 90 * k
        ar = math.radians(a)
        for zz in (6.0, 10.5, 15.0):
            box(b, 'window', tx + 1.46 * math.cos(ar), ty + 1.46 * math.sin(ar), zc + zz, 0.45, 0.1, 1.4, rz=a + 90)
    # black banner of the Stewards on top
    cyl(b, 'iron', tx, ty, zc + 29.4, 0.05, 2.4, n=4, top=False)
    box(b, 'blackflag', tx + 0.75, ty, zc + 30.6, 1.4, 0.05, 0.9)
    # the White Hall (Hall of the Kings) beside the tower
    hx, hy = CX + 0.0, CY + 4.5
    box(b, 'whitestone', hx, hy, zc, 6.0, 3.0, 3.6)
    gable(b, 'slate', hx, hy, zc + 3.6, 6.0, 3.0, 1.2, overhang=0.15)
    for i in range(6):
        cyl(b, 'whitestone', hx - 2.5 + i, hy - 1.75, zc, 0.18, 3.6, n=6, top=False)
    # citadel battlement ring (towers at the corners)
    for a in (200, 240, 300, 340):
        ar = math.radians(a)
        x, y = CX + (RADII[6] - 0.7) * math.cos(ar), CY + (RADII[6] - 0.7) * math.sin(ar)
        cyl(b, 'whitestone', x, y, zc, 0.8, 3.0, n=8)
        cone(b, 'slate', x, y, zc + 3.0, 0.95, 1.3, n=8)

    # Court of the Fountain: green sward, fountain and the White Tree
    fx, fy = CX + 0.0, CY - 4.6
    ring(b, 'lawn', 0.05, 3.0, zc, 0.06, 0, 360, n=24, x=fx, y=fy, inner=False)
    ring(b, 'whitestone', 0.7, 0.95, zc, 0.35, 0, 360, n=16, x=fx + 1.6, y=fy + 0.6)
    ring(b, 'fountainwater', 0.05, 0.7, zc, 0.28, 0, 360, n=16, x=fx + 1.6, y=fy + 0.6, inner=False)
    white_tree(b, fx - 0.5, fy - 0.3, zc + 0.06)


PREVIEW = [((14, -16, 46), (0, CY - 3, tier_top(6) + 3), 50)]


def white_tree(b, x, y, z):
    """The withered White Tree of Gondor (Nimloth's line): pale, leafless, wide-spreading."""
    rng = b.rng

    def branch(x0, y0, z0, length, rad, yaw, pitch, depth):
        yr, pr = math.radians(yaw), math.radians(pitch)
        dx, dy, dz = math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), math.sin(pr)
        x1, y1, z1 = x0 + dx * length, y0 + dy * length, z0 + dz * length
        # oriented tapered cylinder from p0 to p1
        from mathutils import Vector, Matrix
        d = Vector((dx, dy, dz))
        q = d.to_track_quat('Z', 'Y')
        M = Matrix.Translation((x0, y0, z0)) @ q.to_matrix().to_4x4()
        lathe(b, 'treewhite', [(rad, 0), (rad * 0.62, length)], n=5, M=M, smooth=False)
        if depth > 0:
            for k in range(2 if depth < 3 else 3):
                branch(x1, y1, z1, length * rng.uniform(0.62, 0.78), rad * 0.62,
                       yaw + rng.uniform(-70, 70) + (120 * k if depth >= 3 else 0), max(5, pitch - rng.uniform(5, 30)), depth - 1)
        else:
            blob(b, 'treewhite', x1, y1, z1 - 0.12, 0.24, n=5, rings=3)

    lathe(b, 'treewhite', [(0.6, 0), (0.4, 0.5), (0.32, 2.6)], n=6, x=x, y=y, z=z, smooth=False)
    for k in range(3):
        branch(x, y, z + 2.5, 1.9, 0.26, 30 + 120 * k + rng.uniform(-15, 15), rng.uniform(35, 55), 3)
