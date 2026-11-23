"""Erebor, the Lonely Mountain (Dwarves of Durin's folk).

Book/film features modelled:
  * the Lonely Mountain standing alone, its peak snow-capped (film), long ridges
    (spurs) running south toward Dale;
  * the Front Gate in the southern face: a tall dark doorway in a great carved,
    flat-cut rock face with a stepped dwarven frame, out of which the River Running
    flows (book: "out of the Front Gate the river came");
  * the colossal statues of dwarf warriors flanking the gate (film), helmed, bearded,
    each holding a great war-axe before him;
  * the causeway/bridge across the river before the gate, the ruined watch-post on
    Ravenhill to one side, gold glinting in the carved frame.
"""
import math

from blib import (material, hexcol as h, box, ring, cyl, cone, lathe, terrain_polar, blob, strut, curve, prism,
                  pyramid, near_path, sphere)

GATE_Y = -5.0          # carved face plane (faces -Y)


def mountain(x, y):
    # main peak behind the gate, with long southern spurs
    r = math.hypot(x / 1.0, (y - 9) / 1.05)
    z = 58.0 * math.exp(-(r / 17.0) ** 1.5)
    for sx in (-1, 1):
        z = max(z, 22.0 * math.exp(-((x - sx * 15) / 5.5) ** 2) * math.exp(-((y + 2) / 16.0) ** 2))
    z += 2.2 * math.sin(x * 0.6 + y * 0.25) * math.sin(y * 0.5 - x * 0.2) * min(1.0, z / 12.0)
    # the carved, flat-cut terrace in front of the gate and the river valley
    if y < GATE_Y + 0.5 and abs(x) < 10.5:
        valley = 1.2 + 0.8 * (abs(x) / 10.5) ** 3
        z = min(z, valley)
    return max(z, 0.4)


def build(b):
    material('erebor', h('7b7468'), zramp=[(0, h('6f7f4a')), (5, h('7a7466')), (25, h('857e70')), (42, h('8f8b84')),
                                           (50, h('eef1f2'))], slope_color=h('7a7366'), slope_start=0.45)
    material('carved', h('9a9283'), h('8a8274'), noise=2.0, courses=1.4, course_dark=0.82)
    material('statue', h('8e877a'), h('7c7568'), noise=3.0)
    material('dwgold', h('e3b43e'), h('c8952a'), noise=3.0, spec=1.0, refl=200)
    # the great door: polished, shining gold
    material('doorgold', h('ffd45a'), h('ffe99a'), noise=5.0, spec=1.0, refl=235, ao=False)
    material('doorgold2', h('e0a83a'), h('f0c050'), noise=4.0, spec=1.0, refl=220, ao=False)
    material('river', h('4a7a94'), h('5d8ea7'), noise=1.0, ao=False)
    material('gatedark', h('141210'))

    def mat(x, y, z, s):
        return 'erebor'
    terrain_polar(b, mountain, mat, R=31, cy=4, nr=36, na=110)

    # --- the carved face: a great flat wall cut into the mountain
    prism(b, 'carved', [(-11, GATE_Y - 0.2), (11, GATE_Y - 0.2), (11, GATE_Y + 9.0), (-11, GATE_Y + 9.0)], 0.0, 26.0)
    # stepped dwarven frame around the doorway (gold inlay on the edges)
    for i, (w, hgt, d) in enumerate(((9.0, 17.0, 0.0), (7.6, 15.6, -0.5), (6.2, 14.2, -1.0))):
        box(b, 'carved', 0, GATE_Y - 0.6 - 0.4 * i, 1.0, w, 0.8, hgt)
        box(b, 'dwgold', 0, GATE_Y - 1.02 - 0.4 * i, 1.0 + hgt - 0.6, w, 0.06, 0.25)
    # angular dwarven lintel (a chevron)
    for s in (-1, 1):
        strut(b, 'carved', (s * 5.2, GATE_Y - 1.9, 16.5), (0, GATE_Y - 1.9, 21.0), 0.7, 0.7, n=4)
        strut(b, 'dwgold', (s * 4.6, GATE_Y - 2.4, 16.8), (0, GATE_Y - 2.4, 20.6), 0.18, 0.18, n=4)
    # --- the Front Gate itself: two great leaves of shining gold with dwarven relief
    DY = GATE_Y - 1.95            # door plane (faces -Y)
    DW, DH = 4.8, 12.8
    box(b, 'doorgold', 0, DY, 1.0, DW, 0.25, DH)
    box(b, 'doorgold2', 0, DY - 0.14, 1.0, 0.12, 0.06, DH)                     # the seam between the leaves
    for zz in (2.4, 6.0, 9.6, 12.6):                                          # horizontal bands
        box(b, 'doorgold2', 0, DY - 0.16, 1.0 + zz, DW - 0.3, 0.1, 0.28)
    for s in (-1, 1):                                                         # a diamond in each leaf panel
        for zc in (4.2, 7.8, 11.1):
            cx = s * DW / 4
            for (x0, z0, x1, z1) in ((0, -1.1, 0.8, 0), (0.8, 0, 0, 1.1), (0, 1.1, -0.8, 0), (-0.8, 0, 0, -1.1)):
                L = math.hypot(x1 - x0, z1 - z0)
                ang = math.degrees(math.atan2(z1 - z0, x1 - x0))
                from blib import T
                box(b, 'doorgold2', 0, 0, -0.09, L + 0.12, 0.1, 0.18,
                    M=T(cx + (x0 + x1) / 2, DY - 0.17, 1.0 + zc + (z0 + z1) / 2, ry=-ang))
        sphere(b, 'doorgold', s * 0.55, DY - 0.25, 1.0 + 5.6, 0.32, n=10, rings=6)   # door rings' bosses
    # glittering gold sparkles over the door
    for i, (x, z) in enumerate(((-1.4, 3.0), (1.3, 5.5), (-1.1, 8.5), (1.2, 11.0), (0.0, 13.0))):
        b.fx.append(('FX_Gold_%d' % i, (x, DY - 0.5, 1.0 + z), 'ART_DEF_VEFFECT_MEC_GOLD_GLITTER'))
    # the River Running issues from the gate and runs south
    box(b, 'river', 0, GATE_Y - 9.5, 0.95, 3.2, 15.0, 0.4)
    for i in range(2):
        y = GATE_Y - 17.5 - 1.0 * i
        box(b, 'river', 0, y, mountain(0, y) - 0.05 - 0.12 * i, 3.6 + 0.2 * i, 1.05, 0.3)
    # a stone bridge/causeway across the river in front of the gate
    for i in range(11):
        t = i / 10
        x = -6.0 + 12.0 * t
        z = 1.6 + 1.6 * math.sin(math.pi * t)
        box(b, 'carved', x, GATE_Y - 9.5, z - 0.6, 1.25, 3.4, 0.9)
    for s in (-1, 1):
        box(b, 'carved', s * 2.2, GATE_Y - 9.5, 0.4, 1.0, 2.6, 2.0)

    # --- the two colossal dwarf warriors flanking the gate
    for s in (-1, 1):
        dwarf_statue(b, s * 8.4, GATE_Y - 2.8, 1.0, scale=1.15, mirror=s)

    # --- the ruined watch-post on Ravenhill (south-west spur)
    rx, ry = -15.5, -8.0
    rz = mountain(rx, ry)
    box(b, 'carved', rx, ry, rz - 1.0, 4.0, 4.0, 4.5)
    box(b, 'carved', rx + 1.3, ry + 1.3, rz + 3.5, 1.4, 1.4, 2.2)
    for k in range(4):
        box(b, 'carved', rx - 2.0 + 1.3 * k, ry - 2.0, rz + 3.5, 0.6, 0.6, 0.8)


def dwarf_statue(b, x, y, z, scale=1.0, mirror=1):
    s = scale
    # plinth
    box(b, 'carved', x, y, z, 6.2 * s, 5.0 * s, 2.4 * s)
    z0 = z + 2.4 * s
    # legs (robe) and body: tapered blocks
    pts = [(-1.9, -1.4), (1.9, -1.4), (1.9, 1.4), (-1.9, 1.4)]
    from blib import T
    lathe(b, 'statue', [(2.6 * s, 0), (2.3 * s, 7.0 * s), (2.7 * s, 9.5 * s), (2.5 * s, 12.0 * s), (0, 12.0 * s)],
          n=4, M=T(x, y, z0, rz=45, s=(1.0, 0.8, 1.0)), smooth=False)
    # shoulders / pauldrons
    for sd in (-1, 1):
        box(b, 'statue', x + sd * 2.6 * s, y, z0 + 9.8 * s, 1.8 * s, 2.2 * s, 2.2 * s)
    # head with a pointed helm and a great braided beard
    box(b, 'statue', x, y, z0 + 12.0 * s, 2.4 * s, 2.4 * s, 2.4 * s)
    pyramid(b, 'statue', x, y, z0 + 14.4 * s, 2.8 * s, 2.8 * s, 1.8 * s)
    box(b, 'dwgold', x, y - 1.25 * s, z0 + 14.2 * s, 2.6 * s, 0.1 * s, 0.35 * s)
    prism(b, 'statue', [(x - 1.2 * s, y - 1.3 * s), (x + 1.2 * s, y - 1.3 * s), (x + 0.4 * s, y - 1.9 * s),
                        (x - 0.4 * s, y - 1.9 * s)][::-1], z0 + 7.0 * s, 5.6 * s)
    # arms holding a great axe upright before him
    ax_x = x - mirror * 0.9 * s
    for sd in (-1, 1):
        strut(b, 'statue', (x + sd * 2.6 * s, y, z0 + 10.5 * s), (ax_x + sd * 0.6 * s, y - 2.0 * s, z0 + 7.8 * s),
              0.65 * s, 0.55 * s, n=5)
    strut(b, 'statue', (ax_x, y - 2.3 * s, z0 - 1.5 * s), (ax_x, y - 2.3 * s, z0 + 15.0 * s), 0.3 * s, 0.3 * s, n=5)
    # double-bitted axe head
    for sd in (-1, 1):
        prism(b, 'statue', [(ax_x, y - 2.1 * s), (ax_x + sd * 2.6 * s, y - 2.1 * s), (ax_x + sd * 2.6 * s, y - 2.5 * s),
                            (ax_x, y - 2.5 * s)][::-sd], z0 + 11.0 * s, 3.2 * s)
