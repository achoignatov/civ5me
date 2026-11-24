"""Minas Tirith, the Tower of Guard: the landmark of Gondor's capital (an IMPROVEMENT, docs/LANDMARKS.md).

Built like Moria v4 (in-game units, improvement Scale 0.25 with the writer's x4; origin = tile centre, ground z = 0,
-Y = south = towards the game camera) and, by the user's rule since Moria, it FITS ITS OWN HEX (the build envelope
refuses any vertex outside it). Started from the first-generation draft tools/capitals/models/gondor.py.

Lore and film cues (The Return of the King, "Minas Tirith"; the 2003 film):
  * seven circles, each walled and each higher than the last, cut into the knee of Mount Mindolluin, whose grey
    cliffs and snowy heights stand behind and embrace the city; white stone, blue-grey slate roofs;
  * the gates of the circles staggered left and right; the Great Gate in the first wall facing the plain;
  * the great prow of rock that splits every circle but the first, thrust out like the keel of a ship, its top level
    with the Citadel, its sheer point standing above the Great Gate, crowned with battlements;
  * the Citadel: the White Tower of Ecthelion, "shining like a spike of pearl and silver", with its silver spire and
    the banner of the King; the Court of the Fountain on the prow's root: green sward, the fountain, and the White
    Tree, here in blossom as at the end of the Third Age (white flowers, silver-green leaves, pale bark).

Two parts (the vertex limit is 32k per part): the static part holds the mountain and the city's stone (terraces,
walls, battlements, the prow); the skinned part holds everything built on it (houses, bastions, gates, the Citadel,
the White Tree) on the still bone, and the banner, which swings on its pole (PIVOT_MATS, GAZE).
"""
import math
import random

import blib
from blib import material, hexcol as h, box, cyl, lathe, blob, dome, T
from moria_v4 import smooth, fbm, ridged, tube, _spline as spline

BAKE = True
BAKE_PX = 2048           # static part: mountain + stone of the city
EYE_PX = 2048            # skinned part: houses, Citadel, the White Tree
EYE_AO = 16
TINY_PX = 48
PIVOT_MATS = {'flag'}

HEX = 33.6               # the hex, centre -> flat side (a little inside the game's ~34)
FLOOR = -1.0
CX, CY = 0.0, 4.0        # centre of the seven circles
RADII = [29.0, 25.2, 21.5, 17.9, 14.4, 11.0, 7.8]
ZT = [2.2 + 3.7 * k for k in range(7)]          # top of each circle's terrace (the Citadel at 24.4)
WALL_H = 1.0             # parapet above the terrace
WALL_T = 0.6             # wall thickness at the top
PROW_R0, PROW_R1 = 7.0, 27.0                     # the prow, from the Citadel out to its point over the Great Gate
GATES = [270.0, 237.0, 303.0, 236.0, 304.0, 241.0, 299.0]
TOWER = (0.0, CY + 2.4)                          # the Tower of Ecthelion
TREE = (0.9, CY - 10.2)                          # the White Tree, in the Court of the Fountain on the prow
TOWER_TOP = ZT[6] + 23.2                         # top of the tower's drum; the spire rises above it
FLAG_Z = TOWER_TOP + 8.3 + 1.2                   # the banner's middle
EYE_C = (TOWER[0], TOWER[1], FLAG_Z)             # the banner swings about its pole


# ----------------------------------------------------------------------------------------------- shape helpers
def hex_dist(x, y):
    return HEX - max(abs(x * math.cos(math.radians(60 * k)) + y * math.sin(math.radians(60 * k))) for k in range(3))


def polar(r, a_deg):
    a = math.radians(a_deg)
    return CX + r * math.cos(a), CY + r * math.sin(a)


def prow_half(r, top=True):
    """Half width of the prow at distance r from the centre (top edge or foot)."""
    t = min(1.0, max(0.0, (r - PROW_R0) / (PROW_R1 - PROW_R0)))
    ht = 3.5 - 3.25 * t ** 0.85
    return ht if top else ht + 0.5 + 1.2 * (1.0 - t) + 0.3


def in_prow(x, y, pad=0.0):
    """True when (x, y) is under the prow (its foot), widened by pad."""
    r = math.hypot(x - CX, y - CY)
    if r < PROW_R0 - 0.5 or r > PROW_R1 + 0.6 + pad or y > CY:
        return False
    return abs(x - CX) < prow_half(r, top=False) + pad


def mountain(x, y):
    """Mount Mindolluin: grey cliffs rising right behind the Citadel, curving forward round the city's sides."""
    v = (y - CY) + 0.0075 * x * x + 3.0 * fbm(x * 0.1, 0.5, 3, 86)             # the cliff foot wanders
    crest = 13.0 + 37.0 * math.exp(-(x / 15.0) ** 2)                              # high behind, low shoulders
    z = crest * smooth((v + 1.0) / 14.0)
    z += 10.0 * math.exp(-((x - 3.0) / 8.0) ** 2 - ((y - 26.0) / 6.0) ** 2)        # the summit
    z += 5.0 * math.exp(-((x + 13.0) / 6.0) ** 2 - ((y - 21.0) / 5.0) ** 2)
    th = math.atan2(y - 26.0, x - 3.0)                                            # spurs falling from the summit
    z += 4.0 * max(0.0, math.cos(7.0 * th + 2.0 * fbm(x * 0.05, y * 0.05, 2, 87))) ** 2 * smooth(z / 20.0)
    m = smooth(z / 14.0)
    wx, wy = x + 6.0 * fbm(x * 0.04, y * 0.04, 3, 81), y + 6.0 * fbm(y * 0.04, x * 0.04, 3, 82)
    z += (11.0 * ridged(wx * 0.07, wy * 0.07, 5, 83) - 4.5) * m
    z += (3.0 * ridged(wx * 0.22, wy * 0.22, 4, 84) - 1.2) * m
    z += 1.0 * fbm(x * 0.7, y * 0.7, 3, 85) * m
    if z > 2.0:                                  # rock strata
        st = 2.3
        t = z / st
        z += ((math.floor(t) + smooth((t - math.floor(t)) * 1.7)) * st - z) * 0.3
    z = FLOOR + (z - FLOOR) * smooth((hex_dist(x, y) - 0.6) / 8.5)
    return z


def tier_of(r):
    """Index of the circle whose terrace covers radius r (6 = the Citadel), or None outside the city."""
    if r >= RADII[0]:
        return None
    k = 0
    while k + 1 < 7 and r < RADII[k + 1]:
        k += 1
    return k


def city_h(x, y):
    k = tier_of(math.hypot(x - CX, y - CY))
    return -1e9 if k is None else ZT[k]


def buried(x, y, z, margin=0.4):
    return mountain(x, y) > z + margin


# ----------------------------------------------------------------------------------------------- materials
def palette():
    rock_z = [(FLOOR, h('5f6a4a')), (5.0, h('6f6e62')), (16.0, h('7d7b75')), (30.0, h('8b8984')),
              (44.0, h('9c9b98')), (62.0, h('b4b3b0'))]
    material('rock', h('7b7972'), h('5f5d57'), zramp=rock_z, slope_color=h('66645e'), slope_start=0.62)
    blib.PALETTE['rock'].update(scale=0.1, strata=0.6, strata_amp=0.1, cracks=0.9, zjitter=0.05, cavity=0.45,
                                moss=(h('55663a'), 10.0), snow=(36.0, 44.0, 0.38))
    material('prowrock', h('c4c0b5'), h('97938a'), slope_color=h('aaa69b'), slope_start=0.6)
    blib.PALETTE['prowrock'].update(scale=0.3, strata=0.7, strata_amp=0.22, cracks=0.8, cavity=0.7)
    material('wallstone', h('efebe1'), h('dcd6c8'), spec=0.35, refl=12)
    blib.PALETTE['wallstone'].update(scale=0.4, strata=2.6, strata_amp=0.05, cracks=1.6)
    material('paving', h('d3ccbb'), h('bdb5a2'))
    blib.PALETTE['paving'].update(scale=0.6, cracks=1.8)


def house_palette():
    material('housewall', h('f1ede3'), h('ddd6c6'))
    blib.PALETTE['housewall'].update(scale=0.8, windows=dict(fx=1.0 / 0.62, w=(0.3, 0.7), fz=1.0 / 1.05,
                                                             h=(0.38, 0.78), color=h('3a3530')))
    material('slate', h('56606e'), h('68727f'), spec=0.45, refl=30)
    blib.PALETTE['slate'].update(scale=0.9, strata=3.2, strata_amp=0.14)
    material('lead', h('8b949c'), h('7a838c'), spec=0.6, refl=60)
    material('wallstone', h('efebe1'), h('dcd6c8'), spec=0.35, refl=12)
    blib.PALETTE['wallstone'].update(scale=0.4, strata=2.6, strata_amp=0.05, cracks=1.6)
    material('towerstone', h('f7f5ef'), h('e8e4da'), spec=0.5, refl=40)        # the White Tower: the whitest
    blib.PALETTE['towerstone'].update(scale=0.5, strata=2.2, strata_amp=0.035)
    material('silver', h('f2f5f8'), spec=1.0, refl=220, ao=False)
    blib.PALETTE['silver'].update(solid=True)
    material('gatedark', h('1c1a18'))
    blib.PALETTE['gatedark'].update(solid=True)
    material('iron', h('2b2c31'), h('1e1f23'), spec=0.6, refl=50)
    material('window', h('2c2926'))
    blib.PALETTE['window'].update(solid=True)
    material('lawn', h('5f8f3e'), h('4d7a33'))
    blib.PALETTE['lawn'].update(scale=1.5)
    material('water', h('9cc6dc'), spec=0.9, refl=170, ao=False)
    blib.PALETTE['water'].update(solid=True)
    material('treebark', h('ebe8df'), h('cfcabd'), spec=0.4, refl=20)
    blib.PALETTE['treebark'].update(scale=2.5, cracks=4.0)
    material('blossom', h('fdfdfb'), spec=0.7, refl=110, ao=False)
    blib.PALETTE['blossom'].update(solid=True)
    material('leafsilver', h('b9c9b4'), h('8fa58a'), spec=0.6, refl=60)
    material('flag', h('121317'))
    blib.PALETTE['flag'].update(solid=True)


# ----------------------------------------------------------------------------------------------- geometry helpers
def arc_runs(r, z_top, step=2.0, pad=0.3):
    """Angle runs (a0, a1) of a wall at radius r that are neither buried in the mountain nor inside the prow."""
    runs, cur = [], None
    a = 0.0
    while a <= 360.0:
        x, y = polar(r, a)
        ok = not buried(x, y, z_top, 0.2) and not in_prow(x, y, -pad) and hex_dist(x, y) > 0.5
        if ok and cur is None:
            cur = a
        if not ok and cur is not None:
            runs.append((cur, a))
            cur = None
        a += step
    if cur is not None:
        runs.append((cur, 360.0))
    if len(runs) > 1 and runs[0][0] == 0.0 and runs[-1][1] == 360.0:       # join across 0 degrees
        runs = [(runs[-1][0], runs[0][1] + 360.0)] + runs[1:-1]
    return [(a0, a1) for a0, a1 in runs if a1 - a0 >= step]


def wall_arc(b, mat, r, z0, z1, a0, a1, thick=WALL_T, step=2.0):
    """A curved wall: smooth outer face (z0..z1), flat top, inner face; ends capped."""
    n = max(1, int(round((a1 - a0) / step)))
    v, f = [], []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        c, s = math.cos(a), math.sin(a)
        ro, ri = r, r - thick
        v += [(CX + ro * c, CY + ro * s, z0), (CX + ro * c, CY + ro * s, z1),
              (CX + ri * c, CY + ri * s, z1), (CX + ri * c, CY + ri * s, z0)]
    for i in range(n):
        a_, c_ = 4 * i, 4 * (i + 1)
        f.append((a_, c_, c_ + 1, a_ + 1))
    b.add(v, f, mat, smooth=True)                      # outer face, smooth along the curve
    vt, ft = [], []
    for i in range(n + 1):
        vt += [v[4 * i + 1], v[4 * i + 2]]
    for i in range(n):
        ft.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    b.add(vt, ft, mat)                                 # top
    vi, fi = [], []
    for i in range(n + 1):
        vi += [v[4 * i + 2], v[4 * i + 3]]
    for i in range(n):
        fi.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    b.add(vi, fi, mat, smooth=True)                    # inner face
    for i in (0, n):                                   # end caps
        q = v[4 * i:4 * i + 4]
        b.add(q, [(0, 1, 2, 3) if i == 0 else (3, 2, 1, 0)], mat)


def merlons(b, mat, pts, size=(0.5, 0.42, 0.45)):
    """Battlement teeth: [(x, y, z, facing degrees)]; boxes without bottom and back faces, one mesh."""
    w, d, hh = size
    v, f = [], []
    for (x, y, z, ang) in pts:
        k = len(v)
        M = T(x, y, z, ang)
        corners = [(-d / 2, -w / 2, 0), (d / 2, -w / 2, 0), (d / 2, w / 2, 0), (-d / 2, w / 2, 0),
                   (-d / 2, -w / 2, hh), (d / 2, -w / 2, hh), (d / 2, w / 2, hh), (-d / 2, w / 2, hh)]
        v += [tuple(M @ __import__('mathutils').Vector(c)) for c in corners]
        f += [(k + 1, k + 2, k + 6, k + 5),        # front (outward = local +x)
              (k + 0, k + 1, k + 5, k + 4), (k + 2, k + 3, k + 7, k + 6),   # sides
              (k + 4, k + 5, k + 6, k + 7),        # top
              (k + 3, k + 0, k + 4, k + 7)]        # back (seen across the Citadel)
    b.add(v, f, mat)


def merlon_ring(r, z, a0, a1, step=1.15):
    n = max(1, int(math.radians(a1 - a0) * r / step))
    out = []
    for i in range(n):
        a = a0 + (a1 - a0) * (i + 0.5) / n
        x, y = polar(r, a)
        out.append((x, y, z, a))
    return out


def roof(b, mat, x, y, z, L, W, hgt, ang, kind):
    """Roof without a bottom face: 'hip' or 'gable' (ridge along local X)."""
    o = 0.1
    Lh, Wh = L / 2 + o, W / 2 + o
    if kind == 'hip':
        r = max(0.0, Lh - Wh) * 0.6 + 0.01
        v = [(-Lh, -Wh, 0), (Lh, -Wh, 0), (Lh, Wh, 0), (-Lh, Wh, 0), (-r, 0, hgt), (r, 0, hgt)]
        f = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4)]
    else:
        v = [(-Lh, -Wh, 0), (Lh, -Wh, 0), (Lh, 0, hgt), (-Lh, 0, hgt), (-Lh, Wh, 0), (Lh, Wh, 0)]
        f = [(0, 1, 2, 3), (5, 4, 3, 2), (1, 5, 2), (4, 0, 3)]
    b.add(v, f, mat, M=T(x, y, z, ang))


def walls_box(b, mat, x, y, z, L, W, hgt, ang):
    """Four walls of a building (no floor, no ceiling: a roof sits on it)."""
    hx, hy = L / 2, W / 2
    v = [(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0), (-hx, -hy, hgt), (hx, -hy, hgt), (hx, hy, hgt),
         (-hx, hy, hgt)]
    f = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    b.add(v, f, mat, M=T(x, y, z, ang))


# ----------------------------------------------------------------------------------------------- static part
def build(b, eye=False):
    """The mountain and the stone of the city: terraces, walls with battlements, the prow."""
    b.tiny_px = 16
    b.ao_distance = 5.0
    palette()
    blib.SKIRT_MAT[0] = 'rock'

    # ===================================================================== Mount Mindolluin
    X0, X1, Y0, Y1 = -HEX, HEX, -HEX / 0.866, HEX / 0.866
    NX, NY = 124, 142                       # ~0.54 units: stock-mountain density
    blib.terrain(b, mountain, X0, X1, Y0, Y1, NX, NY, lambda x, y, z, s: 'rock',
                 keep=lambda x, y: hex_dist(x, y) > 0.35 and mountain(x, y) > FLOOR + 0.12
                 and mountain(x, y) > city_h(x, y) - 0.4, smooth=True, skirt=FLOOR - 1.0)

    # ===================================================================== the terraces (paved), circle by circle
    for k in range(7):
        r_out = RADII[k] - 0.3
        r_in = RADII[k + 1] - WALL_T - 0.1 if k < 6 else 0.0
        n_r = 2 if k < 6 else 5
        step = 2.0
        v, f = [], []
        rows = {}
        for i in range(int(360 / step)):
            a0, a1 = i * step, (i + 1) * step
            xm, ym = polar((r_out + r_in) / 2 + 0.5, (a0 + a1) / 2)
            if buried(xm, ym, ZT[k], 0.6) or hex_dist(xm, ym) < 0.5:
                continue
            for j in range(n_r):
                ra = r_in + (r_out - r_in) * j / n_r
                rb = r_in + (r_out - r_in) * (j + 1) / n_r
                ids = []
                for (rr, aa) in ((ra, a0), (rb, a0), (rb, a1), (ra, a1)):
                    key = (round(rr, 4), round(aa % 360, 4) if rr > 1e-6 else 0.0)
                    if key not in rows:
                        x, y = polar(rr, aa)
                        rows[key] = len(v)
                        v.append((x, y, ZT[k]))
                    ids.append(rows[key])
                if len(set(ids)) >= 3:
                    f.append(tuple(dict.fromkeys(ids)))
        b.add(v, f, 'paving')

    # ===================================================================== the seven walls with their battlements
    for k in range(7):          # (their battlements are in the skinned part: the vertex budget)
        r = RADII[k]
        z0 = FLOOR if k == 0 else ZT[k - 1] - 0.3
        z1 = ZT[k] + WALL_H
        for a0, a1 in arc_runs(r, z1):
            wall_arc(b, 'wallstone', r, z0, z1, a0, a1)
            # a moulded string course under the parapet
            wall_arc(b, 'wallstone', r + 0.14, ZT[k] - 0.35, ZT[k] - 0.05, a0, a1, thick=0.16)

    # ===================================================================== the prow
    build_prow(b)


def build_prow(b):
    st = 44
    rows = []
    for i in range(st + 1):
        t = i / st
        r = PROW_R0 + (PROW_R1 - PROW_R0) * t
        rows.append((r, prow_half(r, True), prow_half(r, False)))
    ztop = ZT[6] - 0.02
    nz = 18
    # the two rock sides: from the foot to the top edge, the rock bulging and fissured
    for side in (-1, 1):
        v, f = [], []
        for i, (r, ht, hb) in enumerate(rows):
            y = CY - r
            for j in range(nz + 1):
                u = j / nz
                z = FLOOR + (ztop - FLOOR) * u
                half = hb + (ht - hb) * u ** 0.7
                bulge = (0.35 * math.sin(math.pi * u) + 0.9 * fbm(r * 0.45, z * 0.45, 4, 91 + side)
                         + 0.35 * (fbm(r * 1.3, z * 0.25, 2, 93 + side))) * (half / 3.6 + 0.25)
                st_ = z / 1.6                                  # ledges of the strata
                bulge += 0.12 * smooth((st_ - math.floor(st_)) * 3.0) * (half / 3.6 + 0.2)
                if i == len(rows) - 1:
                    half, bulge = 0.0, 0.0                 # the point: both sides meet in one sharp edge
                v.append((CX + side * (half + bulge), y, z))
        for i in range(st):
            for j in range(nz):
                a = i * (nz + 1) + j
                q = (a, a + nz + 1, a + nz + 2, a + 1)
                f.append(q if side < 0 else q[::-1])
        b.add(v, f, 'prowrock', smooth=True)
    # the top: a paved terrace between battlements
    v, f = [], []
    for i, (r, ht, hb) in enumerate(rows):
        hw = 0.0 if i == len(rows) - 1 else ht
        v += [(CX - hw, CY - r, ztop), (CX + hw, CY - r, ztop)]
    for i in range(st):
        f.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2)[::-1])
    b.add(v, f, 'paving')
    # parapets along both edges and round the point, with battlements
    teeth = []
    for side in (-1, 1):
        v, f = [], []
        for i, (r, ht, hb) in enumerate(rows[:-1]):
            x, y = CX + side * ht, CY - r
            xi = CX + side * max(0.0, ht - 0.45)
            v += [(x, y, ztop - 0.6), (x, y, ztop + WALL_H), (xi, y, ztop + WALL_H), (xi, y, ztop)]
            if i % 2 == 1 and r > PROW_R0 + 1.5:
                teeth.append((x - side * 0.2, y, ztop + WALL_H, 0.0 if side > 0 else 180.0))
        for i in range(len(rows) - 2):
            a_, c_ = 4 * i, 4 * (i + 1)
            for q in ((a_, c_, c_ + 1, a_ + 1), (a_ + 1, c_ + 1, c_ + 2, a_ + 2), (a_ + 2, c_ + 2, c_ + 3, a_ + 3)):
                f.append(q[::-1] if side > 0 else q)
        for i in (0, len(rows) - 2):                  # close both ends of the parapet
            q = (4 * i, 4 * i + 1, 4 * i + 2, 4 * i + 3)
            f.append(q if (i == 0) == (side < 0) else q[::-1])
        b.add(v, f, 'wallstone')
    merlons(b, 'wallstone', teeth)


# ----------------------------------------------------------------------------------------------- skinned part
def build_eye(b):
    """Everything built on the stone: houses, bastions, gates, the Citadel, the White Tree, the banner."""
    b.tiny_px = TINY_PX
    house_palette()
    rng = random.Random(3019)

    # ===================================================================== the battlements of the seven walls
    teeth = []
    for k in range(7):
        z1 = ZT[k] + WALL_H
        for a0, a1 in arc_runs(RADII[k], z1):
            teeth += merlon_ring(RADII[k] - 0.2, z1, a0 + 0.6, a1 - 0.6)
    merlons(b, 'wallstone', teeth)

    # ===================================================================== bastions along the walls
    for k in range(7):
        r = RADII[k]
        z0 = FLOOR if k == 0 else ZT[k - 1] - 0.3
        z1 = ZT[k] + WALL_H
        n = max(2, int(r / 5.5))
        for i in range(n * 3):
            a = 180.0 + 360.0 * (i + 0.5 * (k % 2)) / (n * 3)
            if any(abs(((a - g) + 180) % 360 - 180) < 9 for g in GATES[k:k + 1]):
                continue
            x, y = polar(r + 0.55, a)
            if buried(x, y, z1 + 1.4, 0.0) or in_prow(x, y, 1.2) or hex_dist(x, y) < 1.8 or i % 3:
                continue
            top = z1 + 1.3
            box(b, 'wallstone', x, y, z0, 1.7, 1.7, top - z0, rz=a)
            if k % 2:
                lathe(b, 'slate', [(1.25, 0), (0.0, 1.6)], 4, x, y, top, smooth=False, a0=a + 45, a1=a + 405)
            else:
                pts = []
                for c in range(4):
                    ca = math.radians(a + 45 + 90 * c)
                    pts.append((x + 0.62 * math.cos(ca), y + 0.62 * math.sin(ca), top, a + 45 + 90 * c))
                merlons(b, 'wallstone', pts, size=(0.45, 0.4, 0.42))

    # ===================================================================== the gates, staggered from circle to circle
    for k, ga in enumerate(GATES):
        r = RADII[k]
        z0 = FLOOR if k == 0 else ZT[k - 1] - 0.3
        great = k == 0
        gw, gh = (3.4, 4.2) if great else (1.5, 2.3)
        x, y = polar(r + 0.03, ga)
        box(b, 'iron' if great else 'gatedark', x, y, max(z0, (ZT[k - 1] if k else 0.0)), 0.12, gw, gh, rz=ga)
        for s in (-1, 1):
            ta = ga + s * math.degrees((gw / 2 + 1.0) / r)
            tx, ty = polar(r + 0.6, ta)
            top = ZT[k] + WALL_H + (2.6 if great else 1.6)
            tw = 2.0 if great else 1.5
            box(b, 'wallstone', tx, ty, z0, tw, tw, top - z0, rz=ta)
            pts = []
            for c in range(4):
                ca = math.radians(ta + 45 + 90 * c)
                pts.append((tx + tw * 0.36 * math.cos(ca), ty + tw * 0.36 * math.sin(ca), top, ta + 45 + 90 * c))
            merlons(b, 'wallstone', pts, size=(0.45, 0.4, 0.45))
        if great:      # the arch over the Great Gate and its studded leaves
            bx, by = polar(r + 0.09, ga)
            box(b, 'wallstone', bx, by, gh, 0.2, gw + 0.6, 0.5, rz=ga)
            for s in (-0.8, 0.0, 0.8):
                box(b, 'silver', *polar(r + 0.1, ga + math.degrees(s / r)), 0.4, 0.06, 0.12, 3.2, rz=ga)

    # ===================================================================== the houses of the six lower circles
    for k in range(6):
        z = ZT[k]
        r_back = RADII[k + 1] + 0.05                 # the next wall: houses lean against it
        r_front = RADII[k] - WALL_T - 0.45            # the wall walk behind the parapet
        for row in (0, 1):
            depth = 1.35 if row == 0 else 0.95
            rr = r_back + depth / 2 + 0.05 if row == 0 else r_front - depth / 2
            if row == 1 and r_front - r_back < 3.0:
                continue
            a = 0.0
            while a < 360.0:
                wdt = rng.uniform(1.05, 1.75) if row == 0 else rng.uniform(0.9, 1.4)
                da = math.degrees((wdt + rng.uniform(0.08, 0.3)) / rr)
                am = a + da / 2
                a += da
                x, y = polar(rr, am)
                if buried(x, y, z + 1.0, 0.0) or in_prow(x, y, 0.5) or hex_dist(x, y) < 1.0:
                    continue
                if any(abs(((am - g) + 180) % 360 - 180) < math.degrees(1.6 / rr) for g in GATES[k:k + 2]):
                    continue                          # streets to the gates
                if rng.random() < (0.1 if row == 0 else 0.45):
                    continue                          # alleys and little squares
                ang = am + 90.0
                if row == 0:
                    hgt = rng.uniform(1.6, 3.2) if rng.random() < 0.8 else rng.uniform(3.3, ZT[k + 1] - z + 1.5)
                else:
                    hgt = rng.uniform(1.1, 1.8)
                tall = row == 0 and rng.random() < 0.07
                if tall:                             # a slender house-tower
                    tw = min(wdt, 1.1)
                    walls_box(b, 'housewall', x, y, z, tw, tw, hgt + 2.2, ang)
                    lathe(b, 'slate', [(tw * 0.78, 0), (0.0, 1.5)], 4, x, y, z + hgt + 2.2, smooth=False,
                          a0=ang + 45, a1=ang + 405)
                    continue
                walls_box(b, 'housewall', x, y, z, wdt, depth, hgt, ang)
                rmat = 'slate' if rng.random() < 0.85 else 'lead'
                roof(b, rmat, x, y, z + hgt, wdt, depth, rng.uniform(0.45, 0.75), ang,
                     'hip' if rng.random() < 0.55 else 'gable')
        # a hall with a dome on some circles (the Houses of Healing on the sixth)
        for am in ((228.0, 312.0) if k in (2, 4, 5) else ()):
            rr = (RADII[k] + RADII[k + 1]) / 2
            x, y = polar(rr, am)
            if buried(x, y, z + 2, 0.0) or in_prow(x, y, 1.0):
                continue
            walls_box(b, 'housewall', x, y, z, 2.4, 2.0, 2.4, am + 90)
            box(b, 'wallstone', x, y, z + 2.4, 2.5, 2.1, 0.25, rz=am + 90)
            dome(b, 'lead', x, y, z + 2.65, 0.95, n=14, rings=5)
            lathe(b, 'silver', [(0.12, 0), (0.0, 0.6)], 6, x, y, z + 3.55, smooth=False)

    build_citadel(b, rng)
    white_tree(b, rng, TREE[0], TREE[1], ZT[6])
    banner(b)


def build_citadel(b, rng):
    zc = ZT[6]
    tx, ty = TOWER
    # --- the Tower of Ecthelion: a white shaft in stages, galleries, a crowning drum and the silver spire
    prof = [(2.9, 0.0), (2.9, 1.6), (2.45, 2.0), (2.25, 2.4), (2.15, 8.0), (2.45, 8.3), (2.45, 8.75), (2.0, 9.05),
            (1.92, 14.6), (2.2, 14.9), (2.2, 15.35), (1.8, 15.6), (1.72, 20.0), (2.3, 20.35), (2.3, 21.1),
            (1.62, 21.3), (1.55, 23.2), (0.0, 23.2)]
    lathe(b, 'towerstone', prof, 28, tx, ty, zc, smooth=True)
    # gallery battlements on the three rings
    for zz, rr in ((8.75, 2.32), (15.35, 2.07), (21.1, 2.17)):
        merlons(b, 'towerstone', [(tx + rr * math.cos(math.radians(a)), ty + rr * math.sin(math.radians(a)),
                                   zc + zz, a) for a in range(0, 360, 360 // 20)], size=(0.36, 0.26, 0.34))
    # tall windows, every stage, all round
    for (z0, z1, rr) in ((3.6, 6.6, 2.2), (10.2, 13.4, 1.96), (16.6, 19.0, 1.76)):
        for k in range(8):
            a = 22.5 + 45 * k
            ar = math.radians(a)
            box(b, 'window', tx + (rr + 0.01) * math.cos(ar), ty + (rr + 0.01) * math.sin(ar), zc + z0,
                0.06, 0.38, z1 - z0, rz=a)
    # the spire: pearl and silver
    lathe(b, 'silver', [(1.5, 0.0), (1.2, 1.4), (0.55, 5.0), (0.16, 7.6), (0.0, 8.3)], 20, tx, ty, TOWER_TOP,
          smooth=True)
    # --- the Hall of the Kings (the White Hall) behind the tower, and the Citadel's other buildings
    hx, hy = tx, ty + 4.3
    walls_box(b, 'housewall', hx, hy, zc, 6.4, 2.6, 3.4, 0.0)
    roof(b, 'slate', hx, hy, zc + 3.4, 6.4, 2.6, 1.0, 0.0, 'gable')
    for i in range(7):
        cyl(b, 'towerstone', hx - 3.0 + i, hy - 1.55, zc, 0.17, 3.4, n=8, smooth=True)
    for s in (-1, 1):
        x, y = tx + s * 4.6, ty + 0.5
        walls_box(b, 'housewall', x, y, zc, 2.2, 3.2, 2.8, 0.0)
        roof(b, 'slate', x, y, zc + 2.8, 3.2, 2.2, 0.8, 90.0, 'hip')
    x, y = tx + 5.2, ty - 3.2
    walls_box(b, 'housewall', x, y, zc, 2.0, 2.0, 2.2, 0.0)
    dome(b, 'lead', x, y, zc + 2.2, 1.05, n=14, rings=5)
    # --- the Court of the Fountain on the prow's root: sward, fountain, paths
    cx_, cy_ = TREE
    lathe(b, 'lawn', [(2.35, 0.0), (2.35, 0.08), (0.0, 0.08)], 28, cx_ - 0.4, cy_ + 0.3, zc, smooth=False)
    fx, fy = cx_ - 1.9, cy_ + 2.4
    lathe(b, 'towerstone', [(0.95, 0.0), (0.95, 0.42), (0.78, 0.42), (0.78, 0.2), (0.0, 0.2)], 18, fx, fy, zc,
          smooth=False)
    lathe(b, 'water', [(0.79, 0.0), (0.79, 0.34), (0.0, 0.34)], 18, fx, fy, zc, smooth=False)
    lathe(b, 'towerstone', [(0.12, 0.0), (0.12, 0.9), (0.3, 1.0), (0.0, 1.1)], 8, fx, fy, zc + 0.3, smooth=False)


def white_tree(b, rng, x, y, z):
    """The White Tree in blossom: a gnarled pale trunk, limbs spreading wide like an open hand, clouds of white
    flowers and silver-green leaves."""
    trunk = spline([(x, y, z - 0.3), (x + 0.12, y + 0.05, z + 1.0), (x - 0.1, y + 0.12, z + 2.0),
                    (x + 0.06, y - 0.02, z + 2.9)], 12)
    tube(b, 'treebark', trunk, [0.5 - 0.26 * i / (len(trunk) - 1) for i in range(len(trunk))], n=10)
    for k in range(5):                                       # root flare
        a = 2 * math.pi * k / 5 + 0.4
        tube(b, 'treebark', [(x, y, z + 0.5), (x + 0.45 * math.cos(a), y + 0.45 * math.sin(a), z + 0.12),
                             (x + 0.85 * math.cos(a), y + 0.85 * math.sin(a), z - 0.05)], [0.24, 0.15, 0.07], n=6)
    tips = []

    def limb(p, yaw, pitch, length, rad, depth):
        yr, pr = math.radians(yaw), math.radians(pitch)
        d = (math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), math.sin(pr))
        mid = (p[0] + d[0] * length * 0.5 + rng.uniform(-0.1, 0.1), p[1] + d[1] * length * 0.5 + rng.uniform(-0.1, 0.1),
               p[2] + d[2] * length * 0.5 + 0.12 * length)
        end = (p[0] + d[0] * length, p[1] + d[1] * length, p[2] + d[2] * length)
        tube(b, 'treebark', spline([p, mid, end], 4), [rad, rad * 0.85, rad * 0.75, rad * 0.62, rad * 0.55][:5],
             n=7 if depth >= 2 else 5)
        if depth == 0:
            tips.append(end)
            return
        nk = 3 if depth == 2 else 2 + (rng.random() < 0.5)
        for j in range(nk):
            limb(end, yaw + rng.uniform(-55, 55), max(-5.0, pitch - rng.uniform(8, 22)) + (12 if depth == 1 else 0),
                 length * rng.uniform(0.62, 0.78), rad * 0.62, depth - 1)
        tips.append(end)

    top = trunk[-1]
    for k in range(5):
        limb(top, 72 * k + rng.uniform(-15, 15), rng.uniform(32, 48), 1.5, 0.22, 2)
    # the crown: clusters of blossom at the twig ends and along the limbs, silver-green leaves under them
    for i, p in enumerate(tips):
        for j in range(5 if i % 2 == 0 else 3):
            q = (p[0] + rng.uniform(-0.42, 0.42), p[1] + rng.uniform(-0.42, 0.42), p[2] + rng.uniform(-0.1, 0.4))
            blob(b, 'blossom', q[0], q[1], q[2] - 0.12, rng.uniform(0.13, 0.24), n=6, rings=3, squash=0.85, jitter=0.3)
        if i % 3 == 0:
            blob(b, 'leafsilver', p[0], p[1], p[2] - 0.45, rng.uniform(0.3, 0.42), n=7, rings=4, squash=0.6,
                 jitter=0.25)


def banner(b):
    """The banner of the King on a pole above the spire: black, swinging in the wind (the skinned part's pivot)."""
    tx, ty = TOWER
    z0 = TOWER_TOP + 8.0
    cyl(b, 'silver', tx, ty, z0, 0.07, 3.2, n=6)
    # the cloth: a thin slab from the pole towards +X, with a slight wave
    v, f = [], []
    nseg = 8
    for i in range(nseg + 1):
        u = i / nseg
        xx = tx + 0.08 + 2.2 * u
        yy = ty + 0.18 * math.sin(u * 5.0) * u
        for (zz, dy) in ((FLAG_Z + 0.65, -0.03), (FLAG_Z - 0.65 + 0.15 * u, -0.03), (FLAG_Z - 0.65 + 0.15 * u, 0.03),
                         (FLAG_Z + 0.65, 0.03)):
            v.append((xx, yy + dy, zz))
    for i in range(nseg):
        a, c = 4 * i, 4 * (i + 1)
        f += [(a, c, c + 1, a + 1), (a + 3, a + 2, c + 2, c + 3)]
    f.append((4 * nseg, 4 * nseg + 3, 4 * nseg + 2, 4 * nseg + 1))
    b.add(v, [q[::-1] for q in f], 'flag')


def rig():
    return []          # no effects: the White Tree shines by its own white


def _wind(t):
    """The banner swings with the wind on its pole: about 25 degrees either way, a gust inside each 6 s loop."""
    return 18.0 * math.sin(2 * math.pi * t / 6.0) + 7.0 * math.sin(4 * math.pi * t / 6.0 + 1.0)


GAZE = dict(fn=_wind, T=6.0, spans=60)

PREVIEW = [((0, -100, 88), (0, 4, 18), 34),                                     # the game's view
           ((12, -30, 42), (0.5, CY - 7.0, ZT[6] + 3.0), 36),                     # the Citadel and the prow
           ((5, -15.5, 31.5), (TREE[0], TREE[1], ZT[6] + 2.8), 40),              # the White Tree
           ((-58, -44, 46), (0, 6, 18), 32)]                                      # from the south-west
PREVIEW_EYE = [((0, -40, 40), (0, CY, ZT[6]), 34)]
