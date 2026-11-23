"""Moria (Khazad-dûm), held by the Goblins: the West-gate, the Doors of Durin.

Book/film features modelled:
  * the sheer western Walls of Moria under the snowy peaks of the Misty Mountains
    (Caradhras, the Redhorn, behind);
  * the Doors of Durin drawn in shining ithildin on the smooth cliff face: two pillars
    with crescent-moon capitals under an arch of letters, the two trees, the crown and
    the seven stars, the anvil and hammer, and the star of the House of Fëanor;
  * the two great holly trees standing before the doors;
  * the dark dammed lake of the Sirannon with the tentacles of the Watcher in the Water;
  * goblin occupation: crude spiked palisade, red-black rag banners and a bone-pale skull
    totem by the path.
"""
import math

from blib import (material, hexcol as h, box, ring, cyl, cone, lathe, terrain_polar, blob, strut, curve, prism,
                  sphere, conifer)

CLIFF_Y = 2.0


def ground(x, y):
    # the Walls of Moria rise behind CLIFF_Y; peaks of the Misty Mountains behind them
    z = 0.6
    if y > CLIFF_Y:
        t = min(1.0, (y - CLIFF_Y) / 1.4)
        z = 0.6 + 30.0 * t
        ridge = 18.0 * math.exp(-((x - 6) / 10.0) ** 2) * min(1.0, max(0.0, (y - 12) / 10.0))
        ridge += 12.0 * math.exp(-((x + 16) / 8.0) ** 2) * min(1.0, max(0.0, (y - 14) / 10.0))
        z += ridge + 2.0 * math.sin(x * 0.7) * math.sin(y * 0.6) * t
    # the lake basin
    d = math.hypot((x + 1) / 1.5, (y + 9) / 1.0)
    if d < 9:
        z = min(z, -1.0 + 1.6 * (d / 9) ** 2)
    return z


def build(b):
    material('cliff', h('4a4847'), h('3f3d3c'), noise=1.2)
    material('moria', h('56534f'), zramp=[(-1, h('3d4a35')), (1, h('4c5640')), (8, h('57534f')), (34, h('5e5b58')),
                                          (44, h('e7ebee'))], slope_color=h('4a4847'), slope_start=0.5)
    # ithildin: shining moon-blue (plus blue glow / sparkle particles)
    material('ithildin', h('a8dcff'), h('d6f0ff'), noise=5.0, spec=1.0, refl=255, ao=False)
    material('lake', h('1e2b2a'), h('25352f'), noise=1.0, ao=False)
    material('tentacle', h('5f6b4d'), h('6f7a5a'), noise=4.0)
    material('holly', h('203d1f'), h('2b4d27'), noise=2.0)
    material('orcwood', h('4a3626'))
    material('ragred', h('6e1a14'))
    material('bone', h('d8d0b8'))

    def mat(x, y, z, s):
        return 'moria'
    terrain_polar(b, ground, mat, R=31, cy=2, nr=34, na=110)
    # dark water of the lake
    lathe(b, 'lake', [(13.0, 0), (0, 0.0)], n=36, x=-1, y=-9, z=0.1, smooth=False, M=None)

    # --- the Walls of Moria: a sheer natural rock face (no panel); flat where the doors are drawn,
    # broken further out, and turning back into the mountain at its ends
    pts = []
    for i in range(33):
        x = -17.0 + 34.0 * i / 32
        yo = 0.0 if abs(x) < 12.5 else b.rng.uniform(0.0, 0.9)
        if abs(x) > 15.5:
            yo = 2.6
        pts.append((x, CLIFF_Y + yo))
    verts, faces = [], []
    for (x, y) in pts:
        top = ground(x, y + 1.6) + 0.6 + (0.0 if abs(x) < 12.5 else b.rng.uniform(-0.8, 0.8))
        verts += [(x, y, -0.6), (x, y, top)]
    for i in range(len(pts) - 1):
        faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    b.add(verts, faces, 'cliff')

    DS = 1.75                      # the doors are drawn 1.75x larger than before
    F = CLIFF_Y - 0.07             # plane of the ithildin lines
    t = 0.12 * DS                  # line width
    z0 = 0.6

    def line(x0, za, x1, zb, w=0.12):
        x0, x1 = x0 * DS, x1 * DS
        za, zb = z0 + (za - z0) * DS, z0 + (zb - z0) * DS
        w = w * DS
        L = math.hypot(x1 - x0, zb - za)
        if L < 1e-6:
            return
        ang = math.degrees(math.atan2(zb - za, x1 - x0))
        from blib import T
        box(b, 'ithildin', 0, 0, -w / 2, L + w * 0.5, 0.06, w, M=T((x0 + x1) / 2, F, (za + zb) / 2, ry=-ang))
    # pillars with crescent capitals
    for s in (-1, 1):
        line(s * 4.0, z0, s * 4.0, z0 + 9.0)
        line(s * 3.4, z0, s * 3.4, z0 + 9.0)
        for k in range(6):
            a0 = math.pi * (k / 6)
            a1 = math.pi * ((k + 1) / 6)
            line(s * 3.7 + 0.8 * math.cos(a0), z0 + 9.6 - 0.6 * math.sin(a0),
                 s * 3.7 + 0.8 * math.cos(a1), z0 + 9.6 - 0.6 * math.sin(a1))
    # the arch (double line = band of lettering)
    for rr in (4.0, 3.4):
        for k in range(18):
            a0, a1 = math.pi * k / 18, math.pi * (k + 1) / 18
            line(rr * math.cos(a0), z0 + 10.0 + rr * math.sin(a0), rr * math.cos(a1), z0 + 10.0 + rr * math.sin(a1))
    for k in range(17):     # the letters between the two arch lines
        a = math.pi * (k + 0.5) / 17
        line(3.55 * math.cos(a), z0 + 10.0 + 3.55 * math.sin(a), 3.85 * math.cos(a), z0 + 10.0 + 3.85 * math.sin(a), 0.07)
    # the two trees growing from the pillar bases, branches arching over
    for s in (-1, 1):
        x = s * 2.4
        line(x, z0, x, z0 + 8.0)
        for k in range(5):
            zz = z0 + 3.0 + 1.3 * k
            line(x, zz, x - s * (1.2 - 0.15 * k), zz + 0.9)
            line(x, zz, x + s * 0.5, zz + 0.6)
    # crown and the seven stars, anvil and hammer
    line(-0.8, z0 + 12.2, 0.8, z0 + 12.2)
    for k in range(5):
        x = -0.8 + 0.4 * k
        line(x, z0 + 12.2, x, z0 + 12.8)
    for k in range(7):
        a = math.pi * (0.15 + 0.7 * k / 6)
        sx, sz = 2.0 * math.cos(a), z0 + 11.4 + 2.0 * math.sin(a)
        line(sx - 0.15, sz, sx + 0.15, sz, 0.1)
        line(sx, sz - 0.15, sx, sz + 0.15, 0.1)
    line(-0.6, z0 + 10.8, 0.6, z0 + 10.8, 0.22)
    line(-0.3, z0 + 10.3, 0.3, z0 + 10.3, 0.2)
    # the star of Fëanor in the middle of the doors
    cx, cz = 0.0, z0 + 6.2
    for k in range(8):
        a = math.pi * k / 4
        line(cx, cz, cx + 1.3 * math.cos(a), cz + 1.3 * math.sin(a), 0.1)
        line(cx, cz, cx + 0.7 * math.cos(a + math.pi / 8), cz + 0.7 * math.sin(a + math.pi / 8), 0.06)
    line(0, z0, 0, z0 + 4.9, 0.06)           # where the two leaves of the door meet

    # blue light: glows along the drawing, and faint sparkles drifting over it
    def P(x, z):
        return (x * DS, F - 0.35, z0 + (z - z0) * DS)
    glows = [(0.0, z0 + 14.0), (-2.83, z0 + 12.83), (2.83, z0 + 12.83), (-3.7, z0 + 9.6), (3.7, z0 + 9.6),
             (-3.7, z0 + 5.0), (3.7, z0 + 5.0), (-3.7, z0 + 0.8), (3.7, z0 + 0.8), (0.0, z0 + 6.2),
             (-2.4, z0 + 7.0), (2.4, z0 + 7.0), (0.0, z0 + 11.5)]
    for i, (x, z) in enumerate(glows):
        b.fx.append(('FX_Ithil_%d' % i, P(x, z), 'ART_DEF_VEFFECT_MEC_ITHILDIN_GLOW'))
    for i, (x, z) in enumerate(((0.0, z0 + 6.2), (-2.0, z0 + 11.4), (2.0, z0 + 11.4), (0.0, z0 + 13.6))):
        b.fx.append(('FX_IthilSpark_%d' % i, P(x, z), 'ART_DEF_VEFFECT_MEC_ITHILDIN_SPARKLE'))

    # --- the two holly trees before the doors
    for s in (-1, 1):
        x, y = s * 10.5, CLIFF_Y - 2.8
        cyl(b, 'bark', x, y, 0.4, 0.5, 3.6, n=6, r2=0.32)
        for k in range(4):
            blob(b, 'holly', x + b.rng.uniform(-0.5, 0.5), y + b.rng.uniform(-0.5, 0.5), 2.4 + 2.3 * k,
                 2.9 - 0.5 * k, n=8, rings=4, squash=0.8)
    # the ruined stair along the cliff foot
    for i in range(6):
        box(b, 'cliff', -14.0 + i * 0.1, CLIFF_Y - 1.6 - i * 0.9, 0.0, 2.2, 1.0, 0.8 - 0.1 * i)

    # --- the Watcher in the Water: tentacles writhing up out of the lake
    rng = b.rng
    for k in range(7):
        bx, by = -1 + rng.uniform(-6, 6), -10 + rng.uniform(-3.5, 3.5)
        hgt = rng.uniform(4.0, 8.0)
        ph = rng.uniform(0, 6.28)
        pts = []
        for i in range(8):
            t = i / 7
            pts.append((bx + 1.6 * math.sin(ph + t * 3.5) * t, by + 1.2 * math.cos(ph + t * 2.8) * t, -0.4 + hgt * t))
        curve(b, 'tentacle', pts, 0.55, 0.06, n=6)

    # --- goblin occupation: spiked palisade, rag banners, skull totem
    for k in range(22):
        x = 14.0 + (k % 11) * 0.55
        y = CLIFF_Y - 3.5 - (k // 11) * 4.0
        strut(b, 'orcwood', (x, y, 0.0), (x + 0.2, y - 0.3, 2.6 + 0.4 * math.sin(k)), 0.2, 0.0, n=4)
    for x in (-16.0, 16.0):
        cyl(b, 'orcwood', x, CLIFF_Y - 1.5, 0.3, 0.09, 6.0, n=4)
        prism(b, 'ragred', [(x, CLIFF_Y - 1.52), (x + 1.3, CLIFF_Y - 1.52), (x + 1.0, CLIFF_Y - 1.48), (x, CLIFF_Y - 1.48)],
              3.4, 2.4)
    tx, ty = 9.0, -7.0
    cyl(b, 'orcwood', tx, ty, ground(tx, ty) - 0.2, 0.15, 4.0, n=5)
    sphere(b, 'bone', tx, ty - 0.1, ground(tx, ty) + 4.1, 0.45, n=8, rings=6)
    strut(b, 'bone', (tx - 0.9, ty, ground(tx, ty) + 3.0), (tx + 0.9, ty, ground(tx, ty) + 3.0), 0.12, 0.12, n=4)
    # firs on the lower slopes
    for (x, y) in ((-20, -4), (-23, 1), (20, -6), (24, -1), (-17, -12), (18, -14)):
        conifer(b, x, y, ground(x, y) - 0.2, h=6.0, r=1.5)


PREVIEW = [((5, -36, 16), (0, CLIFF_Y, 12), 45)]
