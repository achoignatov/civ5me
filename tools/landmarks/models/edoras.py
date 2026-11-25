"""Edoras, the courts of the Mark: the landmark of Rohan's capital (an IMPROVEMENT, docs/LANDMARKS.md).

v2 (2026-11-25), after the user's film still (edoras.jpg) and the verdict on v1 ("cartoonish... not a child's toy"):
muted, weathered, proud. Built like Minas Tirith (in-game units, Scale 0.25 with the writer's x4; origin = tile
centre, ground z = 0, -Y = south = towards the game camera) and FITS ITS OWN HEX.

What the still shows, and Tolkien confirms ("a green hill... A dike and mighty wall and thorny fence encircled it.
Within, the roofs of houses rose; and in the midst, set upon a green terrace, there stood aloft a great hall of Men"):
  * a great crag, not a dome: a sheer, fractured grey rock face (here south-east, towards the camera), ledges and
    fallen boulders, and dry tussock slopes of olive and tan with rock breaking through;
  * a dense town of weathered dark timber under heavy, steep, deep-eaved thatch, crowded on the lower slopes, gables
    carved with crossed boards; rail fences along the road that climbs between them;
  * a mighty wall of dark logs at the foot with a wall-walk, towers and a gatehouse;
  * on the summit, a compound: Meduseld's great hall, its steep roof thatched with antique gold, gold-bound posts,
    tall gables with crossed horse-heads and finials, lesser halls and a spired hall beside it, a fence on the edge;
    a long stone stair climbs a spur of the hill to it;
  * outside the gate, the barrows of the kings white with simbelmynë; the Snowbourn; the green banner of the Mark
    with the white horse, swinging on its pole (the only moving part).
The open plain round the hill is the game's own ground.

Two parts: static = the land and everything of stone, logs and rails that belongs to it (hill, crag, boulders,
barrows, river, road, stair, palisade, fences); skinned = the buildings (town, gatehouse, towers, Meduseld's
compound) on the still bone, and the banner on the moving one (PIVOT_MATS, GAZE).
"""
import math
import random

from mathutils import Vector

import blib
from blib import material, hexcol as h, box, cyl, lathe, blob, T
from moria_v4 import smooth, fbm, ridged, _spline as spline

BAKE = True
BAKE_PX = 2048
EYE_PX = 2048
EYE_AO = 16
TINY_PX = 24
PIVOT_MATS = {'flag'}

HEX = 33.6
FLOOR = -1.0
HC = (2.0, 6.0)                 # centre of the hill
HR = (21.0, 23.0)               # its radii (normalised radius 1 = the foot of the slopes)
Z_TOP = 22.0                    # the summit terrace
PLAT = 0.34                     # normalised radius of the summit
KNEE = 0.58                     # where the steep crag meets the gentle lower slopes (the town)
Z_KNEE = 6.5
PAL = 1.08                      # the palisade's normalised radius
CLIFF_DIR = -35.0               # the sheer face looks south-east, towards the camera
SPUR_DIR = -100.0               # the stair climbs a spur on the south
ROAD_IN = [(2.0, -17.0), (-3.0, -15.0), (-8.0, -11.5), (-11.0, -6.5), (-8.5, -3.5), (-3.0, -6.0), (0.4, -9.0)]
ROAD_OUT = [(9.5, -33.0), (6.5, -27.5), (3.5, -22.5), (2.0, -18.5)]
RIVER = [(14.0, 33.0), (21.0, 22.0), (27.5, 9.0), (28.5, -2.0), (25.0, -14.0), (17.0, -24.0), (10.0, -30.0),
         (4.0, -36.0)]
RIVER3 = [(x, y, 0.0) for x, y in RIVER]
BARROWS = [(-5.5, -24.5), (-9.0, -28.5), (-12.5, -24.0), (-15.5, -29.0), (-10.5, -33.0),
           (8.5, -20.5), (12.5, -24.5), (6.5, -30.5)]
POLE = (8.2, 3.0)
FLAG_Z = Z_TOP + 9.5
EYE_C = (POLE[0], POLE[1], FLAG_Z)


# ----------------------------------------------------------------------------------------------- shape helpers
def hex_dist(x, y):
    return HEX - max(abs(x * math.cos(math.radians(60 * k)) + y * math.sin(math.radians(60 * k))) for k in range(3))


def seg_dist(x, y, pts):
    best = 1e9
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        vx, vy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy or 1e-9)))
        best = min(best, math.hypot(x - ax - t * vx, y - ay - t * vy))
    return best


_RP = None


def river_d(x, y):
    global _RP
    if _RP is None:
        _RP = [(p[0], p[1]) for p in spline(RIVER3, 70)]
    return seg_dist(x, y, _RP)


def polar(x, y):
    dx, dy = (x - HC[0]) / HR[0], (y - HC[1]) / HR[1]
    return math.hypot(dx, dy), math.atan2(dy, dx)


def dir_mask(th, deg, width):
    """1 in the direction deg (within width degrees), falling to 0."""
    d = abs(((math.degrees(th) - deg) + 180.0) % 360.0 - 180.0)
    return 1.0 - smooth((d - width * 0.5) / (width * 0.5 + 1e-9))


def stair_line():
    """The stair up the spur: (y foot, y top) on x = HC[0]."""
    return HC[1] - HR[1] * (KNEE + 0.14) - 1.0, HC[1] - HR[1] * PLAT + 0.6


def hill(x, y):
    nr, th = polar(x, y)
    cm = dir_mask(th, CLIFF_DIR, 110.0)                     # the sheer face
    sm = dir_mask(th, SPUR_DIR, 34.0)                       # the stair's spur
    c2, s2 = math.cos(th), math.sin(th)
    # the outline wobbles: buttresses and gullies round the crag
    nre = nr * (1.0 + 0.06 * fbm(c2 * 2.0 + 3, s2 * 2.0 + 3, 3, 141)
                + cm * 0.07 * (ridged(c2 * 3.5 + 7, s2 * 3.5 + 7, 4, 142) - 0.5)
                + 0.035 * (ridged(c2 * 9.0 + 3, s2 * 9.0 + 3, 3, 150) - 0.5) * smooth((nr - PLAT) / 0.05)
                * (1.0 - sm))                                                                   # ribs
    knee = KNEE + 0.14 * sm + 0.08 * cm
    zk = Z_KNEE - 2.0 * cm
    if nre < PLAT:
        z = Z_TOP
    elif nre < knee:
        t = (nre - PLAT) / (knee - PLAT)
        a, w = 0.02 + 0.08 * (1 - cm), 0.2 + 0.75 * (1 - cm)  # sheer on the cliff side, a steep slope elsewhere
        prof = 1.0 - smooth((t - a) / w)
        prof = prof * (1 - sm) + (1.0 - t) * sm               # the spur: an even climb for the stair
        z = zk + (Z_TOP - zk) * prof
    else:
        t = (nre - knee) / (1.05 - knee)
        z = zk * max(0.0, 1.0 - min(1.0, t)) ** 2.1       # concave: gentle at the foot, where the town is
    # rock: fractured relief on the crag, ledges of strata, outcrops on the slopes
    crag = smooth((z - 5.0) / 6.0) * (1.0 - 0.85 * sm * (abs(x - HC[0]) < 3.0))
    wx, wy = x + 4.0 * fbm(x * 0.06, y * 0.06, 3, 143), y + 4.0 * fbm(y * 0.06, x * 0.06, 3, 144)
    if nre >= PLAT * 0.92:
        z += (6.5 * ridged(wx * 0.16, wy * 0.16, 4, 145) - 2.6) * crag * (0.6 + 0.8 * cm)
        z += (2.2 * ridged(wx * 0.5, wy * 0.5, 3, 146) - 0.8) * crag
        if z > 3.0:
            st_ = 1.5
            q = z / st_
            z += ((math.floor(q) + smooth((q - math.floor(q)) * 2.6)) * st_ - z) * 0.55 * crag
    z += 0.35 * fbm(x * 0.4, y * 0.4, 3, 147) * (1.0 - smooth((nr - 1.0) / 0.1))
    if nre < PLAT:                                         # the summit is level (paved terrace on it)
        z = Z_TOP + (z - Z_TOP) * smooth((nre - PLAT * 0.85) / (PLAT * 0.15))
    # the dike under the palisade, its ditch outside
    z += 1.0 * math.exp(-((nr - PAL) / 0.03) ** 2) - 0.5 * math.exp(-((nr - PAL - 0.07) / 0.025) ** 2)
    return z


def height(x, y):
    z = hill(x, y) - 0.35 + 0.15 * fbm(x * 0.08, y * 0.08, 3, 148)
    for (bx, by) in BARROWS:
        d = math.hypot(x - bx, (y - by) * 1.3)
        z += 1.25 * max(0.0, 1.0 - (d / 2.0) ** 2) ** 0.8
    rd = river_d(x, y)
    bank = 0.3 * math.exp(-((rd - 1.95) / 0.5) ** 2)
    if bank > 0.03:
        z = max(z, bank + 0.08 * fbm(x * 1.2, y * 1.2, 2, 149))
    if rd < 1.55:
        z = min(z, -0.5)
    return FLOOR + (z - FLOOR) * smooth((hex_dist(x, y) - 0.3) / 3.0)


def ground(x, y):
    return max(height(x, y), 0.0)


def ground_mat(x, y, z, s):
    if any(math.hypot(x - bx, (y - by) * 1.3) < 1.95 for bx, by in BARROWS):
        return 'barrow'
    if seg_dist(x, y, ROAD_IN) < 0.85:
        return 'road'
    if river_d(x, y) < 2.4:
        return 'bank'
    return 'hill'


# ----------------------------------------------------------------------------------------------- materials
def land_palette():
    material('hill', h('8a7d58'), h('6d6344'), slope_color=h('6a655b'), slope_start=0.6,
             zramp=[(FLOOR, h('7a7650')), (4.0, h('857a54')), (12.0, h('7f7656')), (Z_TOP + 2, h('8a8266'))])
    blib.PALETTE['hill'].update(scale=0.16, cracks=0.85, cavity=0.85, zjitter=0.06, strata=0.8, strata_amp=0.1,
                                vcracks=(0.55, 0.3),
                                speckle=[(3.0, 0.16, h('5d573c')), (1.7, 0.1, h('a39b78'))],    # tussocks, dry tops
                                tints=[(-12.0, -2.0, 14.0, h('6e7547'), 0.45)])                   # greener west slope
    material('rock', h('77716a'), h('55514b'), slope_color=h('615c55'), slope_start=0.6)   # boulders
    blib.PALETTE['rock'].update(scale=0.3, cracks=0.9, cavity=0.6, strata=0.9, strata_amp=0.12,
                                speckle=[(5.0, 0.12, h('a29d8c'))])                               # lichen
    material('barrow', h('7d7b52'), h('686843'))
    blib.PALETTE['barrow'].update(scale=0.5, speckle=[(6.0, 0.17, h('f2f3ec')), (3.5, 0.12, h('ffffff'))])
    material('road', h('8f8064'), h('776a52'))
    blib.PALETTE['road'].update(scale=0.7, cracks=1.6, cavity=0.3)
    material('bank', h('7d7666'), h('625c4f'))
    blib.PALETTE['bank'].update(scale=0.6, cracks=1.0)
    material('water', h('4d6470'), h('3d525d'), spec=0.9, refl=160, ao=False)
    blib.PALETTE['water'].update(scale=0.3)
    material('stone', h('8e877a'), h('6f695e'))
    blib.PALETTE['stone'].update(scale=0.5, strata=2.2, strata_amp=0.12, cracks=1.6, cavity=0.4)
    material('logs', h('4d3c2b'), h('372b1f'))
    blib.PALETTE['logs'].update(scale=1.2, cracks=2.2, cavity=0.3)
    material('rails', h('5c4a36'), h('45372a'))
    blib.PALETTE['rails'].update(scale=1.5)


def town_palette():
    material('timber', h('4f3f2f'), h('3b2f23'))
    blib.PALETTE['timber'].update(scale=1.1, cavity=0.3, windows=dict(fx=4.0, w=(0.0, 0.1), fz=1.0, h=(-0.1, 1.1),
                                                                      color=h('2a2119')))   # plank seams
    for name, c1, c2 in (('thatch', '6e604a', '574b3a'), ('thatch2', '7a6a4e', '5f523e'), ('thatch3', '625a4b', '4c4539')):
        material(name, h(c1), h(c2))
        blib.PALETTE[name].update(scale=0.9, strata=4.2, strata_amp=0.14, cavity=0.4, cracks=2.5)
    material('goldthatch', h('a8894c'), h('8a6f3c'), spec=0.55, refl=70)
    blib.PALETTE['goldthatch'].update(scale=0.8, strata=4.0, strata_amp=0.12, cavity=0.35)
    material('gold', h('c9a24e'), spec=0.85, refl=150, ao=False)
    blib.PALETTE['gold'].update(solid=True)
    material('footing', h('6d665a'), h('545047'))
    blib.PALETTE['footing'].update(scale=0.9, cracks=2.0, cavity=0.4)
    material('dark', h('231b14'))
    blib.PALETTE['dark'].update(solid=True)
    material('stone', h('8e877a'), h('6f695e'))
    blib.PALETTE['stone'].update(scale=0.5, strata=2.2, strata_amp=0.12, cracks=1.6, cavity=0.4)
    material('logs', h('4d3c2b'), h('372b1f'))
    blib.PALETTE['logs'].update(scale=1.2, cracks=2.2, cavity=0.3)
    material('rails', h('5c4a36'), h('45372a'))
    blib.PALETTE['rails'].update(scale=1.5)
    material('flag', h('2c5a31'), h('285229'))
    blib.PALETTE['flag'].update(scale=2.0, glow=True, glow_color=h('efece2'), uv_boost=8.0)


# ----------------------------------------------------------------------------------------------- static part
def ribbon(b, mat, pts, half, zfn):
    v, f = [], []
    for i, p in enumerate(pts):
        q0, q1 = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        dx, dy = q1[0] - q0[0], q1[1] - q0[1]
        L = math.hypot(dx, dy) or 1.0
        for s in (-1, 1):
            x, y = p[0] - s * half(i) * dy / L, p[1] + s * half(i) * dx / L
            v.append((x, y, zfn(x, y)))
    for i in range(len(pts) - 1):
        f.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    b.add(v, [q if _up(v, q) else q[::-1] for q in f], mat, smooth=True)


def _up(v, q):
    a, b_, c = v[q[0]], v[q[1]], v[q[2]]
    return (b_[0] - a[0]) * (c[1] - a[1]) - (b_[1] - a[1]) * (c[0] - a[0]) > 0


def oriented(v, f, out):
    """Flip each face of f so its normal points along out."""
    res = []
    for q in f:
        a, b_, c = (Vector(v[i]) for i in q[:3])
        n = (b_ - a).cross(c - a)
        res.append(q if n.dot(Vector(out)) >= 0 else q[::-1])
    return res


def build(b, eye=False):
    b.tiny_px = 0
    b.ao_distance = 4.0
    land_palette()
    blib.SKIRT_MAT[0] = 'hill'
    rng = random.Random(2759)

    # ===================================================================== the hill (fine grid: stock-mountain density)
    BX0, BX1, BY0, BY1 = -24.0, 29.0, -21.5, 33.0
    blib.terrain(b, height, BX0, BX1, BY0, BY1, 120, 124, ground_mat,
                 keep=lambda x, y: hex_dist(x, y) > 0.6 and (height(x, y) > -0.1 or river_d(x, y) < 1.7),
                 smooth=True, skirt=FLOOR - 1.0)

    # the plain beyond the hill's box: barrows, the river's banks (a second, coarser field)
    def far(x, y):
        return not (BX0 < x < BX1 and BY0 < y < BY1)
    blib.terrain(b, height, -HEX, HEX, -HEX / 0.866, HEX / 0.866, 100, 116, ground_mat,
                 keep=lambda x, y: far(x, y) and hex_dist(x, y) > 0.6 and (height(x, y) > -0.1 or river_d(x, y) < 1.7),
                 smooth=True, skirt=FLOOR - 1.0)
    # the Snowbourn and the road to the ford
    sp = [p for p in spline(RIVER3, 90) if hex_dist(p[0], p[1]) > 3.4]
    ribbon(b, 'water', sp, lambda i: 1.45 + 0.25 * math.sin(i * 0.37), lambda x, y: 0.12)
    rp = [p for p in spline([(x, y, 0.0) for x, y in ROAD_OUT], 50) if hex_dist(p[0], p[1]) > 1.6]
    ribbon(b, 'road', rp, lambda i: 0.85, lambda x, y: ground(x, y) + 0.05)

    # ===================================================================== boulders fallen from the crag
    n = 0
    for _ in range(5000):
        if n >= 60:
            break
        x, y = HC[0] + rng.uniform(-23, 23), HC[1] + rng.uniform(-24, 24)
        nr, th = polar(x, y)
        if not (KNEE - 0.08 < nr < 1.0) or seg_dist(x, y, ROAD_IN) < 1.5:
            continue
        if dir_mask(th, CLIFF_DIR, 140.0) < 0.3 and rng.random() < 0.7:
            continue
        r = rng.uniform(0.35, 1.1)
        blob(b, 'rock', x, y, ground(x, y) - r * 0.5, r, n=7, rings=4, squash=rng.uniform(0.5, 0.8), jitter=0.3)
        n += 1

    # ===================================================================== the stone stair up the spur, the summit's paving
    y0, y1 = stair_line()
    steps = 40
    for i in range(steps):                                   # each step laid on the spur's own ground
        ya = y0 + (y1 - y0) * i / steps
        yb = y0 + (y1 - y0) * (i + 1) / steps
        zz = max(hill(HC[0], yb), hill(HC[0], ya)) - 0.25
        box(b, 'stone', HC[0], (ya + yb) / 2, zz - 1.8, 3.0, abs(yb - ya) + 0.04, 1.8 + 0.05)
        for s_ in (-1, 1):                                   # the low walls each side
            box(b, 'stone', HC[0] + s_ * 1.72, (ya + yb) / 2, zz - 1.8, 0.35, abs(yb - ya) + 0.04, 2.55)
    v, f = [], []
    for i in range(41):                                      # paving of the summit terrace (an ellipse)
        a = 2 * math.pi * i / 40
        v.append((HC[0] + HR[0] * PLAT * 0.97 * math.cos(a), HC[1] + HR[1] * PLAT * 0.97 * math.sin(a), Z_TOP + 0.06))
    v.append((HC[0], HC[1], Z_TOP + 0.06))
    b.add(v, oriented(v, [(i, i + 1, 41) for i in range(40)], (0, 0, 1)), 'stone')

    # ===================================================================== rail fences along the climbing road
    rp = spline([(x, y, 0.0) for x, y in ROAD_IN], 60)
    for side in (-1, 1):
        prev = None
        for i in range(0, len(rp), 3):
            p = rp[i]
            j0, j1 = max(0, i - 1), min(len(rp) - 1, i + 1)
            dx, dy = rp[j1][0] - rp[j0][0], rp[j1][1] - rp[j0][1]
            L = math.hypot(dx, dy) or 1.0
            x, y = p[0] - side * 1.25 * dy / L, p[1] + side * 1.25 * dx / L
            z = ground(x, y)
            cyl(b, 'rails', x, y, z - 0.3, 0.06, 1.25, n=4)
            if prev:
                for zz in (0.5, 0.95):
                    blib.strut(b, 'rails', (prev[0], prev[1], prev[2] + zz), (x, y, z + zz), 0.04, 0.04, n=4,
                               smooth=False)
            prev = (x, y, z)


# ----------------------------------------------------------------------------------------------- skinned part
def palisade(b, rng):
    """The wall of logs on the dike, with its wall-walk on posts behind it."""
    n = 300
    pv, pf = [], []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        x, y = HC[0] + PAL * HR[0] * math.cos(a), HC[1] + PAL * HR[1] * math.sin(a)
        if abs(x - HC[0]) < 3.2 and y < HC[1]:
            continue                                         # the gate
        z = ground(x, y)
        hgt = 3.3 + 0.3 * math.sin(k * 2.7) + 0.2 * rng.random()
        r = 0.3
        base = len(pv)
        for j in range(6):
            ja = 2 * math.pi * j / 6 + k * 0.7
            for zz in (z - 0.9, z + hgt):
                pv.append((x + r * math.cos(ja), y + r * math.sin(ja), zz))
        pv.append((x, y, z + hgt + 0.7))
        for j in range(6):
            a0, a1 = base + 2 * j, base + 2 * ((j + 1) % 6)
            pf += [(a0, a1, a1 + 1, a0 + 1), (a0 + 1, a1 + 1, base + 12)]
    b.add(pv, pf, 'logs', smooth=True)
    for k in range(0, n - 3, 3):                             # the wall-walk boards on posts behind the logs
        a0, a1 = 2 * math.pi * (k + 0.5) / n, 2 * math.pi * (k + 3.5) / n
        p0 = (HC[0] + (PAL * HR[0] - 0.9) * math.cos(a0), HC[1] + (PAL * HR[1] - 0.9) * math.sin(a0))
        p1 = (HC[0] + (PAL * HR[0] - 0.9) * math.cos(a1), HC[1] + (PAL * HR[1] - 0.9) * math.sin(a1))
        if (abs(p0[0] - HC[0]) < 3.6 and p0[1] < HC[1]) or (abs(p1[0] - HC[0]) < 3.6 and p1[1] < HC[1]):
            continue
        z0, z1 = ground(*p0) + 2.2, ground(*p1) + 2.2
        L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
        box(b, 'rails', (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (z0 + z1) / 2 - 0.12, L + 0.05, 1.0, 0.12, rz=ang)
        blib.strut(b, 'rails', (p0[0], p0[1], z0 - 2.6), (p0[0], p0[1], z0), 0.09, 0.09, n=4, smooth=False)



def thatch_roof(b, mat, x, y, z, L, W, rh, ang, eave=0.45, over=0.35, t=0.26):
    """A heavy thatched gable roof: thick slabs with deep eaves and overhanging gable edges, and a ridge roll.
    Local X = the ridge; z = the wall top."""
    Lh, Wh = L / 2 + over, W / 2
    k = rh / Wh                                  # rise per unit
    ze = -eave * k                               # the eave hangs below the wall top
    v, f = [], []
    for s in (-1, 1):
        base = len(v)
        v += [(-Lh, 0.0, rh), (Lh, 0.0, rh), (Lh, s * (Wh + eave), ze), (-Lh, s * (Wh + eave), ze),
              (-Lh, 0.0, rh - t * 1.3), (Lh, 0.0, rh - t * 1.3), (Lh, s * (Wh + eave), ze - t),
              (-Lh, s * (Wh + eave), ze - t)]
        f += oriented(v, [(base + 0, base + 1, base + 2, base + 3)], (0, s * 0.6, 1.0))
        f += oriented(v, [(base + 7, base + 6, base + 5, base + 4)], (0, -s * 0.6, -1.0))
        f += oriented(v, [(base + 3, base + 2, base + 6, base + 7)], (0, s, 0))
        f += oriented(v, [(base + 0, base + 3, base + 7, base + 4)], (-1, 0, 0))
        f += oriented(v, [(base + 1, base + 5, base + 6, base + 2)], (1, 0, 0))
    b.add(v, f, mat, M=T(x, y, z, ang))
    # the ridge: a rounded roll of thatch along the top
    lathe(b, mat, [(0.0, -Lh), (0.2, -Lh), (0.2, Lh), (0.0, Lh)], 6,
          M=T(x, y, z + rh + 0.02, ang) @ T(0, 0, 0, ry=90.0), smooth=True)


def gable_wall(b, x, y, z, L, W, rh, ang):
    """The triangular timber gables under the roof (both ends)."""
    v, f = [], []
    for s in (-1, 1):
        base = len(v)
        v += [(s * L / 2, -W / 2, 0.0), (s * L / 2, W / 2, 0.0), (s * L / 2, 0.0, rh)]
        f += oriented(v, [(base, base + 1, base + 2)], (s, 0, 0))
    b.add(v, f, 'timber', M=T(x, y, z, ang))


def crossed_gable(b, x, y, z, ang, rh, span, mat='timber', heads=True):
    """Barge-boards crossing above a gable's apex, ending in carved horse-heads. (x, y) = the gable's foot centre;
    ang = the direction ALONG the gable (across the ridge)."""
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    for s in (-1, 1):
        p0 = (x - s * span * 0.7 * ca, y - s * span * 0.7 * sa, z + rh - span * 0.7 * 0.9)
        p1 = (x + s * span * 0.38 * ca, y + s * span * 0.38 * sa, z + rh + span * 0.38 * 0.9)
        blib.strut(b, mat, p0, p1, 0.07 + 0.03 * span, 0.06 + 0.02 * span, n=4, smooth=True)
        if heads:
            hx, hy = p1[0] + s * 0.16 * span * ca, p1[1] + s * 0.16 * span * sa
            box(b, mat, hx, hy, p1[2] - 0.05, 0.36 * span, 0.12, 0.17 * span, rz=ang)


def walls_box4(b, mat, x, y, z, L, W, hgt, ang):
    """Four walls (no floor or ceiling): L along the local X (rotated by ang)."""
    hx, hy = L / 2, W / 2
    v = [(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0), (-hx, -hy, hgt), (hx, -hy, hgt), (hx, hy, hgt),
         (-hx, hy, hgt)]
    f = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    b.add(v, f, mat, M=T(x, y, z, ang))


def house(b, rng, x, y, ang, L, W, big=False):
    """A Rohirric longhouse: stone footing on the slope, plank walls, a heavy steep thatch, carved gables."""
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    corners = [(x + dx * ca * L / 2 - dy * sa * W / 2, y + dx * sa * L / 2 + dy * ca * W / 2)
               for dx in (-1, 1) for dy in (-1, 1)]
    zs = [ground(*c) for c in corners]
    z, zf = min(zs) - 0.05, max(zs) + 0.05
    box(b, 'footing', x, y, z - 1.4, L + 0.3, W + 0.3, zf - z + 1.6, rz=ang)
    zw = zf + 0.2
    wh = rng.uniform(0.9, 1.15) + (0.25 if big else 0.0)
    walls_box4(b, 'timber', x, y, zw, L, W, wh, ang)
    rh = W * rng.uniform(0.95, 1.2)                      # steep: 45-55 degrees
    gable_wall(b, x, y, zw + wh, L, W, rh, ang)
    thatch_roof(b, rng.choice(('thatch', 'thatch', 'thatch2', 'thatch3')), x, y, zw + wh, L, W, rh, ang,
                eave=0.32, over=0.26, t=0.2)
    if big or rng.random() < 0.4:
        for s in (-1, 1):
            gx, gy = x + s * (L / 2 + 0.28) * ca, y + s * (L / 2 + 0.28) * sa
            crossed_gable(b, gx, gy, zw + wh, ang + 90.0, rh, 0.55 + 0.25 * big, heads=big)
    # the door in the downhill gable end
    s = 1 if ground(x + ca * L, y + sa * L) < ground(x - ca * L, y - sa * L) else -1
    dxo, dyo = x + s * (L / 2 + 0.02) * ca, y + s * (L / 2 + 0.02) * sa
    dv = [(dxo - 0.24 * sa, dyo + 0.24 * ca, zw), (dxo + 0.24 * sa, dyo - 0.24 * ca, zw),
          (dxo + 0.24 * sa, dyo - 0.24 * ca, zw + 0.8), (dxo - 0.24 * sa, dyo + 0.24 * ca, zw + 0.8)]
    b.add(dv, oriented(dv, [(0, 1, 2, 3)], (s * ca, s * sa, 0)), 'dark')          # the door
    if big:                                                # a porch on two posts before the door
        for t_ in (-1, 1):
            px_ = x + s * (L / 2 + 0.8) * ca - t_ * 0.6 * sa
            py_ = y + s * (L / 2 + 0.8) * sa + t_ * 0.6 * ca
            zg = ground(px_, py_)
            cyl(b, 'timber', px_, py_, zg - 0.3, 0.09, zw + wh - zg + 0.3, n=6)


def tower(b, x, y, hgt, w=2.2):
    z = ground(x, y)
    box(b, 'footing', x, y, z - 1.0, w + 0.3, w + 0.3, 1.4)
    walls_box4(b, 'timber', x, y, z + 0.4, w, w, hgt, 0.0)
    box(b, 'timber', x, y, z + 0.4 + hgt, w + 0.5, w + 0.5, 0.2)                 # the lookout floor
    for (cx, cy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        cyl(b, 'timber', x + cx * w * 0.5, y + cy * w * 0.5, z + 0.6 + hgt, 0.09, 1.3, n=5)
    lathe(b, 'thatch', [(w * 0.92, 0.0), (0.0, w * 1.15)], 4, x, y, z + 1.9 + hgt, smooth=False, a0=45, a1=405)


def build_eye(b):
    b.tiny_px = TINY_PX
    town_palette()
    rng = random.Random(1350)

    palisade(b, rng)

    # ===================================================================== the gatehouse and the towers of the wall
    gy = HC[1] - PAL * HR[1]
    gz = ground(HC[0], gy)
    for s in (-1, 1):
        tower(b, HC[0] + s * 2.9, gy, 5.2, w=2.3)
    box(b, 'timber', HC[0], gy, gz + 3.6, 3.8, 1.9, 0.5)                             # the bridge over the gate
    walls_box4(b, 'timber', HC[0], gy, gz + 4.1, 3.6, 1.7, 1.2, 0.0)
    gable_wall(b, HC[0], gy, gz + 5.3, 3.6, 1.7, 1.4, 0.0)
    thatch_roof(b, 'thatch2', HC[0], gy, gz + 5.3, 3.6, 1.7, 1.4, 0.0, eave=0.35, over=0.3)
    box(b, 'dark', HC[0], gy - 0.4, gz - 0.3, 3.4, 0.08, 3.6)
    for s in (-1, 1):                                                                # the gate's leaves, open
        box(b, 'timber', HC[0] + s * 1.75, gy - 1.5, gz - 0.3, 0.22, 1.7, 3.4, rz=s * 22)
    for a in (-160, -120, -40, 0, 40, 80, 125, 165):                                  # watchtowers on the wall
        ar = math.radians(a)
        x, y = HC[0] + (PAL * HR[0] - 0.3) * math.cos(ar), HC[1] + (PAL * HR[1] - 0.3) * math.sin(ar)
        if hex_dist(x, y) > 2.0:
            tower(b, x, y, 4.6, w=1.9)

    # ===================================================================== the town: dense on the lower slopes
    placed = []
    tries = 0
    while len(placed) < 150 and tries < 80000:
        tries += 1
        x, y = HC[0] + rng.uniform(-22.5, 22.5), HC[1] + rng.uniform(-24.5, 24.5)
        nr, th = polar(x, y)
        if not (KNEE - 0.06 < nr < PAL - 0.1):
            continue
        if dir_mask(th, CLIFF_DIR, 80.0) > 0.5 and nr < 0.85:
            continue                                                         # under the sheer face: scree
        if seg_dist(x, y, ROAD_IN) < 2.1 or (abs(x - HC[0]) < 2.8 and y < HC[1] - HR[1] * 0.5 and nr < 0.8):
            continue
        big = rng.random() < 0.12
        L = rng.uniform(2.6, 3.4) if big else rng.uniform(1.8, 2.6)          # small beside the crag, as in the still
        W = rng.uniform(1.6, 1.9) if big else rng.uniform(1.2, 1.55)
        zz = [ground(x + dx, y + dy) for dx in (-L / 2, L / 2) for dy in (-L / 2, L / 2)]
        if max(zz) - min(zz) > 2.3:
            continue                                                         # too steep to build on
        if any(math.hypot(x - px, y - py) < 0.5 * (L + pl) + 0.1 for px, py, pl in placed):
            continue
        # gables down the slope (as in the still) or along the contour
        ang = math.degrees(th) + (0.0 if rng.random() < 0.6 else 90.0) + rng.uniform(-14, 14)
        house(b, rng, x, y, ang, L, W, big)
        placed.append((x, y, L))

    print('Edoras: %d houses' % len(placed))
    meduseld(b)
    banner(b)


def meduseld(b):
    """Meduseld and its compound on the summit."""
    zt = Z_TOP + 0.06
    hx, hy = HC[0], HC[1] + 1.6
    HW, HL, WH = 5.8, 12.0, 3.2
    box(b, 'stone', hx, hy, zt - 0.6, HW + 1.0, HL + 1.0, 1.0)                       # the hall's stone dais
    zw = zt + 0.4
    walls_box4(b, 'timber', hx, hy, zw, HL, HW, WH, 90.0)
    for zz in (0.5, WH - 0.15):                                                       # gold-carved bands
        box(b, 'gold', hx, hy, zw + zz, HW + 0.06, HL + 0.06, 0.12)
    rh = 5.6                                                                          # the great steep roof
    gable_wall(b, hx, hy, zw + WH, HL, HW, rh, 90.0)
    thatch_roof(b, 'goldthatch', hx, hy, zw + WH, HL, HW, rh, 90.0, eave=0.7, over=0.6, t=0.35)
    lathe(b, 'gold', [(0.0, -(HL / 2 + 0.6)), (0.12, -(HL / 2 + 0.6)), (0.12, HL / 2 + 0.6), (0.0, HL / 2 + 0.6)], 6,
          M=T(hx, hy, zw + WH + rh + 0.25, 90.0) @ T(0, 0, 0, ry=90.0), smooth=True)  # the gilded ridge
    for s in (-1, 1):                                                                 # gables: crossed horse-heads
        gy = hy + s * (HL / 2 + 0.65)
        crossed_gable(b, hx, gy, zw + WH, 0.0, rh, 1.3, mat='gold')
        lathe(b, 'gold', [(0.08, 0.0), (0.04, 0.8), (0.0, 0.9)], 6, hx, gy, zw + WH + rh + 0.4, smooth=False)
    # the porch: posts bound in gold under its own steep gable
    py = hy - HL / 2 - 1.6
    box(b, 'stone', hx, py + 0.3, zt - 0.3, HW + 0.4, 3.4, 0.7)
    for s in (-2.3, -0.8, 0.8, 2.3):
        cyl(b, 'timber', hx + s, py - 0.7, zw, 0.22, WH, n=10, smooth=True)
        for zz in (0.15, WH * 0.45, WH - 0.3):
            cyl(b, 'gold', hx + s, py - 0.7, zw + zz, 0.26, 0.16, n=10, smooth=True)
    gable_wall(b, hx, py, zw + WH, 3.4, HW, 3.4, 90.0)
    thatch_roof(b, 'goldthatch', hx, py, zw + WH, 3.4, HW, 3.4, 90.0, eave=0.5, over=0.4, t=0.3)
    crossed_gable(b, hx, py - 2.1, zw + WH, 0.0, 3.4, 1.0, mat='gold')
    box(b, 'dark', hx, hy - HL / 2 - 0.02, zw, 2.2, 0.05, 2.7)                        # the great doors
    for s in (-1, 1):                                                                 # high windows
        for k in range(4):
            box(b, 'dark', hx + s * (HW / 2 + 0.01), hy - HL / 2 + 2.2 + 2.6 * k, zw + 1.7, 0.04, 0.6, 0.9)
    # lesser halls beside it
    for (dx, dy, L, W, rh_, ang, mat) in ((-6.0, 1.0, 6.0, 3.2, 3.4, 90.0, 'thatch3'),
                                          (6.0, 3.0, 5.0, 3.0, 3.2, 90.0, 'thatch'),
                                          (5.6, -3.6, 3.6, 2.6, 2.8, 0.0, 'thatch2')):
        x, y = HC[0] + dx, HC[1] + dy
        fx, fy = (L, W) if ang == 0 else (W, L)
        box(b, 'stone', x, y, zt - 0.4, fx + 0.5, fy + 0.5, 0.6)
        walls_box4(b, 'timber', x, y, zt + 0.2, L, W, 2.4, ang)
        gable_wall(b, x, y, zt + 2.6, L, W, rh_, ang)
        thatch_roof(b, mat, x, y, zt + 2.6, L, W, rh_, ang)
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        for s in (-1, 1):
            crossed_gable(b, x + s * (L / 2 + 0.36) * ca, y + s * (L / 2 + 0.36) * sa, zt + 2.6, ang + 90.0, rh_, 1.0,
                          mat='gold' if s < 0 else 'timber')
    # the spired hall (the still's tall roof on the left)
    sx, sy = HC[0] - 5.8, HC[1] - 4.6
    box(b, 'stone', sx, sy, zt - 0.4, 3.0, 3.0, 0.6)
    walls_box4(b, 'timber', sx, sy, zt + 0.2, 2.6, 2.6, 4.2, 0.0)
    lathe(b, 'thatch3', [(2.1, 0.0), (0.0, 5.6)], 4, sx, sy, zt + 4.4, smooth=False, a0=45, a1=405)
    lathe(b, 'gold', [(0.12, 0.0), (0.0, 1.4)], 6, sx, sy, zt + 9.95, smooth=False)
    # the fence along the summit's edge (open at the head of the stair)
    for k in range(48):
        a0, a1 = 2 * math.pi * k / 48, 2 * math.pi * (k + 1) / 48
        if abs(((math.degrees(a0) - SPUR_DIR) + 180) % 360 - 180) < 16:
            continue
        p0 = (HC[0] + HR[0] * PLAT * 0.95 * math.cos(a0), HC[1] + HR[1] * PLAT * 0.95 * math.sin(a0))
        p1 = (HC[0] + HR[0] * PLAT * 0.95 * math.cos(a1), HC[1] + HR[1] * PLAT * 0.95 * math.sin(a1))
        cyl(b, 'timber', p0[0], p0[1], zt - 0.1, 0.06, 1.15, n=4)
        for zz in (0.55, 1.0):
            blib.strut(b, 'timber', (p0[0], p0[1], zt + zz), (p1[0], p1[1], zt + zz), 0.045, 0.045, n=4, smooth=False)


def horse_lines(x0, z0, L, H):
    """The white horse of Rohan running left, painted on the banner: [(x0, z0, x1, z1, width)]."""
    pts = [((0.36, 0.5), (0.66, 0.52), 0.17), ((0.38, 0.56), (0.26, 0.76), 0.11), ((0.26, 0.76), (0.13, 0.68), 0.08),
           ((0.27, 0.74), (0.37, 0.6), 0.05),
           ((0.4, 0.46), (0.3, 0.32), 0.055), ((0.3, 0.32), (0.22, 0.27), 0.05), ((0.44, 0.45), (0.42, 0.24), 0.05),
           ((0.63, 0.46), (0.72, 0.32), 0.06), ((0.72, 0.32), (0.79, 0.22), 0.05), ((0.6, 0.46), (0.56, 0.25), 0.05),
           ((0.67, 0.56), (0.8, 0.64), 0.06), ((0.8, 0.64), (0.87, 0.52), 0.045)]
    return [(x0 + a[0] * L, z0 + a[1] * H, x0 + c[0] * L, z0 + c[1] * H, w * H) for a, c, w in pts]


def banner(b):
    px, py = POLE
    zb = Z_TOP
    cyl(b, 'timber', px, py, zb - 0.3, 0.1, FLAG_Z + 1.5 - zb, n=6)
    lathe(b, 'gold', [(0.2, 0.0), (0.0, 0.5)], 6, px, py, FLAG_Z + 1.2, smooth=False)
    L, H = 3.0, 1.9
    v, f = [], []
    nseg = 8
    for i in range(nseg + 1):
        u = i / nseg
        xx = px + 0.1 + L * u
        yy = py + 0.2 * math.sin(u * 5.0) * u
        for (zz, dy) in ((FLAG_Z + H / 2, -0.03), (FLAG_Z - H / 2 + 0.18 * u, -0.03), (FLAG_Z - H / 2 + 0.18 * u, 0.03),
                         (FLAG_Z + H / 2, 0.03)):
            v.append((xx, yy + dy, zz))
    for i in range(nseg):
        a, c = 4 * i, 4 * (i + 1)
        f += [(a, c, c + 1, a + 1), (a + 3, a + 2, c + 2, c + 3)]
    f.append((4 * nseg, 4 * nseg + 3, 4 * nseg + 2, 4 * nseg + 1))
    b.add(v, [q[::-1] for q in f], 'flag')
    b.glow = dict(lines=horse_lines(px + 0.1, FLAG_Z - H / 2, L, H),
                  box=(px + 0.1, px + 0.1 + L, FLAG_Z - H / 2, FLAG_Z + H / 2), sigma=(0.035, 0.05))


def rig():
    return []


def _wind(t):
    return 16.0 * math.sin(2 * math.pi * t / 6.0) + 8.0 * math.sin(4 * math.pi * t / 6.0 + 0.7)


GAZE = dict(fn=_wind, T=6.0, spans=60)

PREVIEW = [((0, -100, 80), (2, 4, 10), 34),                                      # the game's view
           ((-30, -40, 16), (4, 4, 12), 32),                                     # like the still: low, from the south-west
           ((14, -24, Z_TOP + 12), (HC[0], HC[1], Z_TOP + 3), 36),               # Meduseld
           ((-14, -34, 14), (-4, -10, 4), 36)]                                   # the town and the gate
PREVIEW_EYE = [((POLE[0] + 1.5, POLE[1] - 9, FLAG_Z + 0.5), (POLE[0] + 1.6, POLE[1], FLAG_Z), 40)]
