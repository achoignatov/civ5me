"""Erebor, the Lonely Mountain: the landmark of the Dwarves' capital (an IMPROVEMENT, docs/LANDMARKS.md).

Built like Minas Tirith and Edoras (in-game units, improvement Scale 0.25 with the writer's x4; origin = tile centre,
ground z = 0, -Y = south = towards the game camera) and FITS ITS OWN HEX. The kingdom under the Mountain in its glory,
as in the prologue of The Hobbit films (2012-14) and the book ("the Front Gate... out of which the river came"):
  * the Lonely Mountain standing alone: one great snow-capped peak of cold grey rock with long spurs (arms) running out
    from it, dry heath on its feet; the two southern arms embrace the valley of the Front Gate;
  * the Front Gate at the head of that valley: a sheer dressed face cut into the mountain, a tall stepped dwarven
    portal with a gable-shaped head, the crown of Durin's folk with seven stars in gold relief, pilasters and a
    gallery of windows above; the great doors stand a little ajar and the gold light of the halls spills out (an
    additive glow, like Moria's ithildin, but warm), braziers burn before them;
  * the two colossal dwarf warriors that guard the gate (film): helmed, broad, great braided beards, leaning on
    their great axes;
  * long blue-and-gold banners of Erebor hanging on the face;
  * the River Running pouring from culverts under the gate's threshold down a stone channel, a dwarven bridge over it
    with braziers on its posts, the roads south towards Dale;
  * the guard-post of Ravenhill on the south-western arm, a watch-fire on its top; lit windows of the halls on the
    valley walls.
Muted, weathered, real (the user's rule, landmark-realism): cold greys, antique gold, no toy props.

Two parts: static = the mountain and everything carved in stone (face, portal, gallery, pilasters, threshold, stairs,
channel, bridge, Ravenhill); skinned = the statues, doors, banners, gold relief, braziers, boulders, lit windows, all
on the still bone (PIVOT_MATS is empty: nothing moves), plus the effect bones (glow, fires).
"""
import math
import random

from mathutils import Vector

import blib
from blib import material, hexcol as h, box, cyl, lathe, blob, T
from moria_v4 import smooth, fbm, ridged, tube, _spline as spline

BAKE = True
BAKE_PX = 2048
EYE_PX = 2048
EYE_AO = 16
TINY_PX = 32
PIVOT_MATS = set()                 # nothing moves: every skinned vertex on the still bone

HEX = 33.6
FLOOR = -1.0
PEAK = (0.0, 12.0)
Z_PEAK = 58.0
GATE_Y = -4.0                      # the dressed face of the Front Gate (faces -Y)
VW0 = 15.6                         # half-width of the valley at the face
ZG = 2.6                           # the threshold (top of the platform before the gate)
PLAT_D = 7.0                       # depth of the platform
GW, GH = 3.2, 12.0                 # half-width and height of the gate's opening
STATUE_X, STATUE_Y, STATUE_S = 13.2, GATE_Y - 3.6, 1.25
PIL_X = 8.0                        # pilasters
BAN_X = 6.6                        # banners
GAL_Z = 26.0                       # the gallery
BRIDGE_Y = -21.0
RAVEN = (-19.0, -13.0)
RIVER = [(0.0, GATE_Y - PLAT_D - 0.2, 0.0), (0.0, -14.0, 0.0), (0.6, -18.0, 0.0), (0.0, -22.0, 0.0),
         (-1.2, -27.0, 0.0), (-1.0, -32.0, 0.0), (0.5, -37.0, 0.0), (1.0, -41.0, 0.0)]
ROAD_E = [(6.75, GATE_Y - PLAT_D - 3.2), (6.0, -16.0), (4.6, BRIDGE_Y - 0.4), (6.0, -27.0), (8.0, -33.0),
          (9.5, -38.0)]
ROAD_W = [(-6.75, GATE_Y - PLAT_D - 3.2), (-6.0, -16.0), (-4.6, BRIDGE_Y - 0.4)]
SPURS = [  # (end x, end y, end height, width at the end)
    (-19.0, -13.0, 10.0, 5.0),     # SW: Ravenhill
    (19.0, -12.5, 7.0, 5.0),       # SE
    (31.0, 3.0, 4.0, 6.0),         # E
    (-31.0, 2.0, 4.0, 6.0),        # W
    (19.0, 33.0, 5.0, 6.0),        # NE
    (-18.0, 33.0, 5.0, 6.0),       # NW
]
EYE_C = (0.0, GATE_Y, ZG)          # pivot of the skinned part (nothing turns about it)


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


def river_pts():
    global _RP
    if _RP is None:
        _RP = [(p[0], p[1]) for p in spline(RIVER, 80)]
    return _RP


def river_d(x, y):
    return seg_dist(x, y, river_pts())


def zv(y):
    """The valley floor: just above the game's ground at the gate, sinking under it towards the south."""
    return 1.0 - 0.06 * max(0.0, GATE_Y - y)


def vw(y):
    return VW0 + 0.42 * max(0.0, GATE_Y - y)


def face_top(x):
    """The least height of the mountain right behind the dressed face (so the face is a tall clean cliff)."""
    return 32.0 - 4.0 * (abs(x) / VW0) ** 2


def mountain(x, y):
    """The Lonely Mountain alone (no valley cut): a broad massif under a steep crag-crowned summit, ribbed with
    gullies running down from the peak, its arms, domain-warped aretes, strata."""
    dx, dy = x - PEAK[0], (y - PEAK[1]) * 1.05
    r = math.hypot(dx, dy)
    c, s_ = (dx / r, dy / r) if r > 1e-6 else (1.0, 0.0)
    z = 40.0 * math.exp(-(r / 24.0) ** 2) + 20.0 * math.exp(-(r / 9.0) ** 1.4)
    for (cx, cy, ch, cr) in ((-4.5, 14.5, 6.0, 3.0), (4.0, 9.5, 5.0, 2.8), (1.5, 16.5, 4.0, 2.4), (-2.0, 7.0, 3.0, 2.6)):
        z += ch * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (cr * cr))           # the summit's crags
    for (ex, ey, ez, ew) in SPURS:                          # the arms, each a ridge falling from the peak
        vx, vy = ex - PEAK[0], ey - PEAK[1]
        L = math.hypot(vx, vy)
        t = ((x - PEAK[0]) * vx + (y - PEAK[1]) * vy) / (L * L)
        if t <= 0.0:
            continue
        d = abs((x - PEAK[0]) * vy - (y - PEAK[1]) * vx) / L
        d += 2.5 * fbm(x * 0.08 + ex, y * 0.08, 2, 11)       # the crest wanders
        w = 3.5 + ew * t
        zr = ez + (44.0 - ez) * max(0.0, 1.0 - t) ** 1.5
        zr *= 1.0 - smooth((t - 1.0) / 0.2)
        z = max(z, zr * math.exp(-(d / w) ** 2))
    z += 4.5 * math.exp(-((x - RAVEN[0]) ** 2 + (y - RAVEN[1]) ** 2) / 16.0)      # Ravenhill's knoll
    # gullies and ribs running down from the summit (noise sampled round the peak: no seam)
    K = 4.2
    rib = ridged(c * K + 0.025 * r, s_ * K - 0.02 * r, 4, 26)
    z += (rib - 0.42) * 9.0 * smooth((r - 2.5) / 6.0) * (1.0 - smooth((r - 28.0) / 6.0)) * smooth(z / 12.0)
    # behind the dressed face: the rock stands at least as high as the face
    if GATE_Y - 0.5 < y < GATE_Y + 9.0 and abs(x) < VW0 + 4.0:
        req = face_top(x) + 0.9 * (y - GATE_Y)
        k = 1.0 - smooth((abs(x) - VW0) / 4.0)
        if req > z:
            z += (req - z) * k
    # relief: domain-warped aretes and gullies, finer crags; stronger higher up
    m = smooth(z / 12.0)
    wx, wy = x + 6.0 * fbm(x * 0.04, y * 0.04, 3, 21), y + 6.0 * fbm(y * 0.04, x * 0.04, 3, 22)
    z += (12.0 * ridged(wx * 0.075, wy * 0.075, 5, 23) - 5.0) * m
    z += (3.6 * ridged(wx * 0.24, wy * 0.24, 4, 24) - 1.45) * m
    z += 0.9 * fbm(x * 0.7, y * 0.7, 3, 25) * m
    if z > 2.5:                                             # strata ledges
        st = 2.4
        q = z / st
        z += ((math.floor(q) + smooth((q - math.floor(q)) * 1.7)) * st - z) * 0.32
    if z > 52.0:                                            # the summit stays under the envelope (64)
        z = 52.0 + 8.0 * math.tanh((z - 52.0) / 8.0)
    return z


def valley_k(x, y):
    """0 on the valley floor, 1 in the full mountain (the valley walls between)."""
    if y > GATE_Y + 0.8:
        return 1.0
    wall = 2.6 + 0.16 * max(0.0, GATE_Y - y)
    edge = vw(y) + (2.0 * fbm(y * 0.15, 3.1, 2, 31) + 0.8 * fbm(y * 0.6, 7.7, 2, 32)) * smooth((GATE_Y - y) / 4.0)
    return smooth((abs(x) - edge) / wall)


def height(x, y):
    z = mountain(x, y)
    k = valley_k(x, y)
    floor = zv(y) + 0.25 * fbm(x * 0.3, y * 0.3, 2, 41)
    z = floor + (z - floor) * k
    if 0.0 < k < 1.0:                                       # crags and buttresses on the valley's walls
        z += 4.0 * k * (1.0 - k) * (5.0 * ridged(x * 0.22, y * 0.22, 3, 44) - 2.0)
    rd = river_d(x, y)
    if y < GATE_Y - PLAT_D + 0.5 and rd < 2.2:              # the river's bed
        z = min(z, zv(y) - 0.55 + 0.5 * smooth((rd - 1.4) / 0.8))
    return FLOOR + (z - FLOOR) * smooth((hex_dist(x, y) - 0.6) / 9.0)


def ground(x, y):
    return max(height(x, y), 0.0)


def ground_mat(x, y, z, s):
    if y < GATE_Y + 0.8 and valley_k(x, y) < 0.25:
        return 'bank' if river_d(x, y) < 2.6 else 'valley'
    return 'rock'


# ----------------------------------------------------------------------------------------------- materials
def stone_palette():
    rock_z = [(FLOOR, h('6a6650')), (4.0, h('6f6c5e')), (14.0, h('767570')), (28.0, h('7f7f7e')),
              (42.0, h('8c8d90')), (Z_PEAK, h('a3a5a9'))]
    material('rock', h('75736c'), h('5a5853'), zramp=rock_z, slope_color=h('615e58'), slope_start=0.6)
    blib.PALETTE['rock'].update(scale=0.1, strata=0.7, strata_amp=0.1, cracks=0.9, zjitter=0.05, cavity=0.55,
                                vcracks=(0.45, 0.25), snow=(40.0, 47.0, 0.3),
                                speckle=[(2.2, 0.08, h('5b5a46'))])                     # heath on the low slopes
    material('valley', h('6e6a55'), h('5b5848'))
    blib.PALETTE['valley'].update(scale=0.35, cracks=1.2, cavity=0.4, speckle=[(4.0, 0.12, h('8a8679'))])
    material('bank', h('69655b'), h('55524a'))
    blib.PALETTE['bank'].update(scale=0.6, cracks=1.4, cavity=0.4)
    material('face', h('6a6c67'), h('5b5d59'))                 # the dressed face: smooth dark grey-green stone
    blib.PALETTE['face'].update(scale=0.14, strata=0.45, strata_amp=0.05, cracks=0.22, cavity=0.5, glow=True,
                                glow_color=h('ffb35c'), uv_boost=1.6)
    material('carved', h('7a7b75'), h('66675f'))               # architecture cut from the same stone
    blib.PALETTE['carved'].update(scale=0.45, strata=1.8, strata_amp=0.05, cracks=1.1, cavity=0.65)
    material('paving', h('7c7a71'), h('68665e'))
    blib.PALETTE['paving'].update(scale=0.6, cracks=1.9, cavity=0.35)
    material('gatedark', h('120e0b'))
    blib.PALETTE['gatedark'].update(solid=True)
    material('dgold', h('b39046'), h('9a7a3a'), spec=0.85, refl=150, ao=False)
    blib.PALETTE['dgold'].update(solid=True)
    material('water', h('4c6672'), h('3e5560'), spec=0.9, refl=160, ao=False)
    blib.PALETTE['water'].update(scale=0.3)
    material('road', h('7f7867'), h('6a6455'))
    blib.PALETTE['road'].update(scale=0.7, cracks=1.6, cavity=0.3)


def life_palette():
    stone_palette()
    material('statue', h('7f7c74'), h('67645c'))
    blib.PALETTE['statue'].update(scale=0.5, cracks=0.7, cavity=0.9, strata=0.9, strata_amp=0.06,
                                  moss=(h('5d6147'), 3.0))
    material('doorstone', h('46443f'), h('393733'))
    blib.PALETTE['doorstone'].update(scale=0.4, cracks=0.6, cavity=0.5)
    material('banner', h('1d3049'), h('1a2b42'))
    blib.PALETTE['banner'].update(scale=2.0, glow=True, glow_color=h('c9a24e'), uv_boost=7.0)
    material('iron', h('2d2b29'), h('211f1d'), spec=0.5, refl=40)
    blib.PALETTE['iron'].update(solid=True)
    material('ember', h('ff9a3c'), ao=False)
    blib.PALETTE['ember'].update(solid=True)
    material('litwin', h('e9a14c'), ao=False)
    blib.PALETTE['litwin'].update(solid=True)
    material('boulder', h('6f6c65'), h('55524c'), slope_color=h('5c5953'), slope_start=0.7)
    blib.PALETTE['boulder'].update(scale=0.3, cracks=0.8, cavity=0.6)


# ----------------------------------------------------------------------------------------------- mesh helpers
def oriented(v, f, out):
    res = []
    for q in f:
        a, b_, c = (Vector(v[i]) for i in q[:3])
        n = (b_ - a).cross(c - a)
        res.append(q if n.dot(Vector(out)) >= 0 else q[::-1])
    return res


def slab_xz(b, mat, pts, y_back, depth, smooth_=False):
    """A convex polygon [(x, z)] on the wall plane extruded towards the camera: y from y_back - depth to y_back."""
    n = len(pts)
    cx, cz = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
    v = [(x, y_back - depth, z) for x, z in pts] + [(x, y_back, z) for x, z in pts]
    f = oriented(v, [tuple(range(n))], (0, -1, 0)) + oriented(v, [tuple(range(n, 2 * n))], (0, 1, 0))
    for i in range(n):
        j = (i + 1) % n
        mx, mz = (pts[i][0] + pts[j][0]) / 2 - cx, (pts[i][1] + pts[j][1]) / 2 - cz
        f += oriented(v, [(i, j, n + j, n + i)], (mx, 0, mz))
    b.add(v, f, mat, smooth=smooth_)


def bar_xz(b, mat, x0, z0, x1, z1, w, y_back, depth):
    """A straight bar from (x0, z0) to (x1, z1) of width w on the wall plane (any angle)."""
    L = math.hypot(x1 - x0, z1 - z0) or 1e-6
    nx, nz = -(z1 - z0) / L * w / 2, (x1 - x0) / L * w / 2
    slab_xz(b, mat, [(x0 - nx, z0 - nz), (x1 - nx, z1 - nz), (x1 + nx, z1 + nz), (x0 + nx, z0 + nz)], y_back, depth)


def loft(b, mat, rings, n=20, smooth_=True, a0=0.0):
    """A closed tube through rings [(cx, cy, z, rx, ry, shape)] bottom to top; shape(a) multiplies the radius.
    a0 (degrees) turns the sections (n = 8, a0 = 22.5: a flat side faces the camera)."""
    v, f = [], []
    for (cx, cy, z, rx, ry, sh) in rings:
        for k in range(n):
            a = 2 * math.pi * k / n + math.radians(a0)
            m = sh(a) if sh else 1.0
            v.append((cx + rx * m * math.cos(a), cy + ry * m * math.sin(a), z))
    for i in range(len(rings) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            f.append((i * n + k, i * n + k2, (i + 1) * n + k2, (i + 1) * n + k))
    bot, top = len(v), len(v) + 1
    v.append((rings[0][0], rings[0][1], rings[0][2]))
    v.append((rings[-1][0], rings[-1][1], rings[-1][2]))
    last = (len(rings) - 1) * n
    for k in range(n):
        k2 = (k + 1) % n
        f.append((k2, k, bot))
        f.append((last + k, last + k2, top))
    b.add(v, f, mat, smooth=smooth_)


def ribbon(b, mat, pts, half, zfn):
    v, f = [], []
    for i, p in enumerate(pts):
        q0, q1 = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        dx, dy = q1[0] - q0[0], q1[1] - q0[1]
        L = math.hypot(dx, dy) or 1.0
        for s in (-1, 1):
            x, y = p[0] - s * half(i) * dy / L, p[1] + s * half(i) * dx / L
            v.append((x, y, zfn(x, y, i)))
    for i in range(len(pts) - 1):
        f.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    b.add(v, oriented(v, f, (0, 0, 1)), mat, smooth=True)


# ----------------------------------------------------------------------------------------------- the face's layout
def frame_band(k):
    """Band k = 1..3 of the stepped portal, inside out: (inner half-width, top of the opening it frames, depth)."""
    return GW + 0.9 * (k - 1), ZG + GH + 0.9 * (k - 1), 0.5 + 0.4 * (3 - k)


PED_Z0 = ZG + GH + 2.7             # the gable head of the portal: base and apex
PED_Z1 = PED_Z0 + 4.4
PED_HW = 7.2


def glow_lines():
    """The gold light on the face: the crack between the doors and the gallery's windows [(x0, z0, x1, z1, w)]."""
    L = [(0.0, ZG + 0.2, 0.0, ZG + GH - 0.4, 0.42)]
    for i in range(7):
        x = -6.0 + 2.0 * i
        L.append((x, GAL_Z + 0.55, x, GAL_Z + 1.75, 0.5))
    return L


def banner_lines():
    """Gold on the banners: a border, the Mountain under the crown, a band of lozenges [(x0, z0, x1, z1, w)]."""
    L = []
    for s in (-1, 1):
        x = s * BAN_X
        hw, zt, zb = 0.6, 23.3, 12.4
        for (a, c) in (((x - hw + 0.12, zt - 0.12), (x + hw - 0.12, zt - 0.12)),
                       ((x - hw + 0.12, zt - 0.12), (x - hw + 0.12, zb + 0.95)),
                       ((x + hw - 0.12, zt - 0.12), (x + hw - 0.12, zb + 0.95)),
                       ((x - hw + 0.12, zb + 0.95), (x, zb + 0.2)), ((x + hw - 0.12, zb + 0.95), (x, zb + 0.2))):
            L.append((a[0], a[1], c[0], c[1], 0.07))
        zm = 17.6                                           # the Mountain: a broad chevron, a smaller one inside
        L += [(x - 0.42, zm, x, zm + 0.9, 0.11), (x, zm + 0.9, x + 0.42, zm, 0.11), (x - 0.42, zm, x + 0.42, zm, 0.09),
              (x - 0.2, zm + 0.25, x, zm + 0.55, 0.06), (x, zm + 0.55, x + 0.2, zm + 0.25, 0.06)]
        zc = zm + 1.35                                      # the crown above it
        L += [(x - 0.3, zc, x + 0.3, zc, 0.1), (x - 0.3, zc, x - 0.34, zc + 0.35, 0.06),
              (x, zc, x, zc + 0.42, 0.06), (x + 0.3, zc, x + 0.34, zc + 0.35, 0.06)]
        for zz in (21.6, 14.4):                              # bands of lozenges
            for k in range(3):
                cx = x - 0.32 + 0.32 * k
                L += [(cx - 0.12, zz, cx, zz + 0.16, 0.05), (cx, zz + 0.16, cx + 0.12, zz, 0.05),
                      (cx + 0.12, zz, cx, zz - 0.16, 0.05), (cx, zz - 0.16, cx - 0.12, zz, 0.05)]
    return L


# ----------------------------------------------------------------------------------------------- static part
def build(b, eye=False):
    b.tiny_px = 0
    b.ao_distance = 5.0
    stone_palette()
    blib.SKIRT_MAT[0] = 'rock'

    # ===================================================================== the Lonely Mountain
    X0, X1, Y0, Y1 = -HEX, HEX, -HEX / 0.866, HEX / 0.866
    blib.terrain(b, height, X0, X1, Y0, Y1, 126, 146, ground_mat,
                 keep=lambda x, y: hex_dist(x, y) > 0.35 and height(x, y) > -0.1, smooth=True, skirt=FLOOR - 1.0)

    # ===================================================================== the dressed face
    nx, nz = 52, 18
    W = VW0 + 0.4
    v, f = [], []
    for i in range(nx + 1):
        x = -W + 2 * W * i / nx
        top = mountain(x, GATE_Y + 0.9) - 0.6
        for k in range(nz + 1):
            v.append((x, GATE_Y, FLOOR + (top - FLOOR) * k / nz))
    for i in range(nx):
        for k in range(nz):
            a = i * (nz + 1) + k
            f.append((a, a + nz + 1, a + nz + 2, a + 1))
    b.add(v, oriented(v, f, (0, -1, 0)), 'face', smooth=True)
    b.glow = dict(lines=glow_lines(), box=(-VW0, VW0, FLOOR, 34.0), sigma=(0.5, 2.4))

    # ===================================================================== the threshold, its stairs, the culverts
    yf = GATE_Y - PLAT_D
    box(b, 'carved', 0.0, GATE_Y - PLAT_D / 2, FLOOR, 2 * VW0 + 1.4, PLAT_D, ZG - FLOOR)
    box(b, 'paving', 0.0, GATE_Y - PLAT_D / 2 + 0.05, ZG, 2 * VW0 + 1.3, PLAT_D - 0.3, 0.04)
    box(b, 'carved', 0.0, yf + 0.25, ZG, 2 * VW0 + 1.4, 0.5, 0.55)                 # a low parapet on its edge...
    rise = (ZG - zv(yf - 3.0)) / 5
    for s in (-1, 1):
        for i in range(5):                                                         # ...broken by the two stairs
            box(b, 'paving', s * 6.75, yf - (i + 0.5) * 0.62, FLOOR, 4.6, 0.62, ZG - FLOOR - (i + 1) * rise + 0.04)
        for e in (-1, 1):                                                          # stair cheeks
            box(b, 'carved', s * 6.75 + e * 2.55, yf - 1.6, FLOOR, 0.5, 3.3, ZG - FLOOR + 0.1)
    for cx in (-2.4, 0.0, 2.4):                                                    # three arched culverts
        pts = [(cx - 0.8, zv(yf) - 0.4), (cx + 0.8, zv(yf) - 0.4)]
        pts += [(cx + 0.8 * math.cos(math.radians(a)), ZG - 1.0 + 0.8 * math.sin(math.radians(a)))
                for a in range(0, 181, 30)]
        slab_xz(b, 'gatedark', pts, yf, 0.03)
        bar_xz(b, 'carved', cx - 1.0, ZG - 1.0, cx + 1.0, ZG - 1.0, 0.22, yf, 0.12)
    # the river's stone channel down the valley's head
    rp = [p for p in river_pts() if p[1] < yf - 0.2 and p[1] > -16.5]
    for s in (-1, 1):
        pts = rp[::2]
        for p, q in zip(pts, pts[1:]):
            mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
            L = math.hypot(q[0] - p[0], q[1] - p[1])
            ang = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
            box(b, 'carved', mx + s * 1.75 * math.sin(math.radians(ang)) * -1, my + s * 1.75 * math.cos(math.radians(ang)),
                zv(my) - 0.9, L + 0.1, 0.5, 1.4, rz=ang)

    # ===================================================================== the portal: stepped bands, the gable head
    for k in (3, 2, 1):
        iw, zt, d = frame_band(k)
        for s in (-1, 1):
            box(b, 'carved', s * (iw + 0.45), GATE_Y - d / 2, ZG - 0.2, 0.9, d, zt + 0.9 - ZG + 0.2)
            box(b, 'carved', s * (iw + 0.45), GATE_Y - d / 2, ZG - 0.2, 1.2, d + 0.2, 0.9)     # its foot
        box(b, 'carved', 0.0, GATE_Y - d / 2, zt, 2 * iw + 1.8, d, 0.9)                         # its lintel
    _, zt3, _ = frame_band(3)
    for s in (-1, 1):                                                                           # the gable head
        bar_xz(b, 'carved', s * PED_HW, PED_Z0, 0.0, PED_Z1, 1.1, GATE_Y, 0.9)
        bar_xz(b, 'carved', s * (PED_HW - 1.6), PED_Z0 + 0.15, 0.0, PED_Z1 - 1.3, 0.45, GATE_Y, 0.6)
    bar_xz(b, 'carved', -PED_HW - 0.4, PED_Z0 - 0.25, PED_HW + 0.4, PED_Z0 - 0.25, 0.7, GATE_Y, 1.0)
    # the crown of Durin's folk and the seven stars, gilded
    zc = PED_Z0 + 0.7
    bar_xz(b, 'dgold', -1.2, zc, 1.2, zc, 0.4, GATE_Y - 0.6, 0.14)
    for k in range(5):
        x = -1.1 + 0.55 * k
        hgt = 0.9 if k in (0, 4) else (1.25 if k == 2 else 1.05)
        slab_xz(b, 'dgold', [(x - 0.18, zc + 0.15), (x + 0.18, zc + 0.15), (x, zc + 0.2 + hgt)], GATE_Y - 0.6, 0.14)
    for k in range(7):
        a = math.radians(160 - 140 * k / 6)
        sx, sz = 2.15 * math.cos(a), zc + 0.6 + 1.25 * math.sin(a)
        slab_xz(b, 'dgold', [(sx, sz - 0.24), (sx + 0.24, sz), (sx, sz + 0.24), (sx - 0.24, sz)], GATE_Y - 0.6, 0.12)
    # gilded edges of the outermost band
    iw3, zt3, d3 = frame_band(3)
    for s in (-1, 1):
        bar_xz(b, 'dgold', s * (iw3 + 0.9), ZG + 0.8, s * (iw3 + 0.9), zt3 + 0.75, 0.12, GATE_Y - d3, 0.05)
    bar_xz(b, 'dgold', -(iw3 + 0.9), zt3 + 0.75, iw3 + 0.9, zt3 + 0.75, 0.12, GATE_Y - d3, 0.05)

    # ===================================================================== pilasters and the gallery
    for s in (-1, 1):
        x = s * PIL_X
        box(b, 'carved', x, GATE_Y - 0.6, ZG - 0.2, 2.1, 1.2, 1.4)                  # base
        box(b, 'carved', x, GATE_Y - 0.45, ZG, 1.4, 0.9, GAL_Z - 1.0 - ZG)          # shaft
        for zz in (ZG + 6.0, ZG + 12.0, ZG + 18.0):                                  # carved rings
            box(b, 'carved', x, GATE_Y - 0.55, zz, 1.6, 1.1, 0.35)
        box(b, 'carved', x, GATE_Y - 0.6, GAL_Z - 1.0, 2.0, 1.2, 0.5)               # capital
    box(b, 'carved', 0.0, GATE_Y - 0.7, GAL_Z - 0.5, 2 * PIL_X + 2.6, 1.4, 0.5)     # the gallery's floor
    for i in range(15):                                                              # its parapet: pierced
        x = -PIL_X + 2 * PIL_X * i / 14
        box(b, 'carved', x, GATE_Y - 1.25, GAL_Z, 0.36, 0.3, 0.75)
    box(b, 'carved', 0.0, GATE_Y - 1.25, GAL_Z + 0.75, 2 * PIL_X + 0.4, 0.34, 0.2)
    for i in range(7):                                                               # the windows behind it
        x = -6.0 + 2.0 * i
        slab_xz(b, 'gatedark', [(x - 0.42, GAL_Z), (x + 0.42, GAL_Z), (x + 0.42, GAL_Z + 1.9), (x, GAL_Z + 2.3),
                                (x - 0.42, GAL_Z + 1.9)], GATE_Y, 0.03)
    box(b, 'carved', 0.0, GATE_Y - 0.35, GAL_Z + 2.7, 2 * PIL_X + 2.0, 0.7, 0.45)   # a cornice over them

    # ===================================================================== the statues' plinths
    for s in (-1, 1):
        x, y = s * STATUE_X, STATUE_Y
        box(b, 'carved', x, y, ZG - 0.2, 7.4, 6.4, 1.0)
        box(b, 'carved', x, y, ZG + 0.8, 6.6, 5.6, 1.6)
        box(b, 'carved', x, y, ZG + 2.4, 7.0, 6.0, 0.35)

    # ===================================================================== the bridge over the River Running
    build_bridge(b)
    # ===================================================================== the guard-post of Ravenhill
    build_ravenhill(b)
    # ===================================================================== roads
    for rd in (ROAD_E, ROAD_W):
        rp = [p for p in spline([(x, y, 0.0) for x, y in rd], 40) if hex_dist(p[0], p[1]) > 1.2]
        ribbon(b, 'road', rp, lambda i: 0.85, lambda x, y, i: ground(x, y) + 0.06)
    # the River Running, from the culverts to the edge of the hex
    wp = [p for p in river_pts() if p[1] < GATE_Y - PLAT_D - 0.02 and hex_dist(p[0], p[1]) > 1.6]
    ribbon(b, 'water', wp, lambda i: 1.3 + 0.12 * math.sin(i * 0.5), lambda x, y, i: max(zv(y) - 0.3, 0.12))


BR_Z = 1.7                         # top of the bridge's deck


def build_bridge(b):
    y0, wd = BRIDGE_Y + 1.3, 2.6
    # the arch: trapezoids between the soffit curve and the deck
    n = 10
    R, zc = 2.2, BR_Z - 2.6
    for k in range(n):
        a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
        x0, x1 = -R * math.cos(a0), -R * math.cos(a1)
        z0, z1 = zc + R * math.sin(a0) + 0.25, zc + R * math.sin(a1) + 0.25
        slab_xz(b, 'carved', [(x0, z0), (x1, z1), (x1, BR_Z), (x0, BR_Z)], y0, wd)
    for s in (-1, 1):                                                   # abutments
        slab_xz(b, 'carved', [(s * R, FLOOR), (s * 5.2, FLOOR), (s * 5.2, BR_Z), (s * R, BR_Z)][::s], y0, wd)
        for e in (0, 1):                                                # parapet posts with braziers on the south
            box(b, 'carved', s * 4.6, y0 - 0.3 - e * (wd - 0.6), BR_Z, 0.8, 0.8, 1.45)
    for e in (0, 1):
        yy = y0 - 0.17 - e * (wd - 0.34)
        box(b, 'carved', 0.0, yy, BR_Z, 8.4, 0.34, 0.65)
        for k in range(9):                                              # angular dwarven crenels
            box(b, 'carved', -3.6 + 0.9 * k, yy, BR_Z + 0.65, 0.42, 0.36, 0.3)
    box(b, 'paving', 0.0, y0 - wd / 2, BR_Z - 0.01, 10.2, wd - 0.7, 0.04)


def build_ravenhill(b):
    rx, ry = RAVEN
    z0 = height(rx, ry)
    box(b, 'carved', rx, ry, z0 - 3.0, 5.4, 5.4, 3.6)                    # its footing in the rock
    box(b, 'carved', rx, ry, z0 + 0.6, 4.8, 4.8, 5.8)
    box(b, 'carved', rx, ry, z0 + 6.4, 5.3, 5.3, 0.4)                    # a string course
    box(b, 'carved', rx, ry, z0 + 6.8, 3.7, 3.7, 3.0)                    # the upper stage
    box(b, 'carved', rx, ry, z0 + 9.8, 4.2, 4.2, 0.3)
    for k in range(4):                                                   # crenels on the upper stage
        for e in (-1, 1):
            box(b, 'carved', rx - 1.65 + 1.1 * k, ry + e * 1.95, z0 + 10.1, 0.55, 0.3, 0.5)
            box(b, 'carved', rx + e * 1.95, ry - 1.65 + 1.1 * k, z0 + 10.1, 0.3, 0.55, 0.5)
    for k in range(5):                                                   # crenels on the lower roof
        for e in (-1, 1):
            box(b, 'carved', rx - 2.2 + 1.1 * k, ry + e * 2.5, z0 + 6.8, 0.55, 0.3, 0.55)
            box(b, 'carved', rx + e * 2.5, ry - 2.2 + 1.1 * k, z0 + 6.8, 0.3, 0.55, 0.55)
    for zz in (z0 + 2.4, z0 + 7.8):                                      # windows: slits facing the valley
        slab_xz(b, 'gatedark', [(rx - 0.25, zz), (rx + 0.25, zz), (rx + 0.25, zz + 1.2), (rx, zz + 1.45),
                                (rx - 0.25, zz + 1.2)], ry - (2.4 if zz < z0 + 6 else 1.85), 0.03)
    # a stair cut up the knoll from the valley
    for i in range(10):
        t = i / 10
        x, y = rx + 3.4 + 4.0 * t, ry - 1.5 - 3.6 * t
        zz = height(x, y)
        box(b, 'carved', x, y, zz - 1.0, 1.4, 1.0, 1.15, rz=-42)


# ----------------------------------------------------------------------------------------------- skinned part
def build_eye(b):
    b.tiny_px = TINY_PX
    life_palette()
    rng = random.Random(2941)

    for s in (-1, 1):
        statue(b, s * STATUE_X, STATUE_Y, ZG + 2.75, STATUE_S)

    # ===================================================================== the gate: the dark beyond, the doors ajar
    slab_xz(b, 'gatedark', [(-GW, ZG), (GW, ZG), (GW, ZG + GH), (-GW, ZG + GH)], GATE_Y - 0.02, 0.03)
    for s in (-1, 1):
        x0, x1 = s * 0.25, s * GW
        lo, hi = min(x0, x1), max(x0, x1)
        yb = GATE_Y - 0.08
        slab_xz(b, 'doorstone', [(lo, ZG), (hi, ZG), (hi, ZG + GH), (lo, ZG + GH)], yb, 0.5)
        yf = yb - 0.5
        cx = (lo + hi) / 2
        for zz in (ZG + 0.6, ZG + 4.4, ZG + 8.2, ZG + GH - 0.8):        # gold bands
            bar_xz(b, 'dgold', lo + 0.2, zz, hi - 0.2, zz, 0.2, yf, 0.08)
        for (zc_, r) in ((ZG + 2.5, 0.95), (ZG + 6.3, 1.1), (ZG + 10.1, 0.95)):   # lozenges between them
            P = [(cx, zc_ - r), (cx + r, zc_), (cx, zc_ + r), (cx - r, zc_)]
            for p, q in zip(P, P[1:] + P[:1]):
                bar_xz(b, 'dgold', p[0], p[1], q[0], q[1], 0.14, yf, 0.07)
            slab_xz(b, 'dgold', [(cx, zc_ - 0.28), (cx + 0.28, zc_), (cx, zc_ + 0.28), (cx - 0.28, zc_)], yf, 0.1)
        bar_xz(b, 'dgold', s * 0.32, ZG + 0.3, s * 0.32, ZG + GH - 0.3, 0.1, yf, 0.06)       # edge at the crack
        blob(b, 'dgold', s * 0.75, yf - 0.1, ZG + 5.6, 0.28, n=10, rings=5, squash=1.0, jitter=0.0)   # door rings

    # ===================================================================== the banners of Erebor
    for s in (-1, 1):
        x = s * BAN_X
        cyl(b, 'iron', x - 0.85, GATE_Y - 0.35, 23.4, 0.06, 0.06)
        blib.strut(b, 'dgold', (x - 0.8, GATE_Y - 0.3, 23.45), (x + 0.8, GATE_Y - 0.3, 23.45), 0.07, 0.07, n=6)
        slab_xz(b, 'banner', [(x - 0.6, 23.4), (x + 0.6, 23.4), (x + 0.6, 13.2), (x, 12.4), (x - 0.6, 13.2)],
                GATE_Y - 0.2, 0.06)
    b.glow = dict(lines=banner_lines(), box=(-BAN_X - 0.8, BAN_X + 0.8, 12.0, 23.8), sigma=(0.025, 0.04))

    # ===================================================================== braziers
    for (x, y, z) in brazier_spots():
        lathe(b, 'iron', [(0.12, 0.0), (0.5, 0.32), (0.62, 0.55), (0.55, 0.6), (0.0, 0.6)], 10, x, y, z - 0.6,
              smooth=True)
        blob(b, 'ember', x, y, z - 0.12, 0.42, n=8, rings=3, squash=0.4, jitter=0.1)
    for s in (-1, 1):                                                   # the pedestals before the gate
        x, y, z = brazier_spots()[0 if s < 0 else 1]
        box(b, 'statue', x, y, ZG, 0.9, 0.9, z - 0.6 - ZG)
        box(b, 'statue', x, y, ZG, 1.3, 1.3, 0.3)

    # ===================================================================== lit windows on the valley walls
    wall_windows(b, rng)

    # ===================================================================== boulders on the valley's sides
    n = 0
    for _ in range(6000):
        if n >= 44:
            break
        y = rng.uniform(-30.0, GATE_Y - PLAT_D - 1.0)
        x = rng.choice((-1, 1)) * rng.uniform(vw(y) - 3.0, vw(y) + 4.0)
        k = valley_k(x, y)
        if not (0.02 < k < 0.6) or hex_dist(x, y) < 2.0 or seg_dist(x, y, ROAD_E) < 1.4 or seg_dist(x, y, ROAD_W) < 1.4:
            continue
        r = rng.uniform(0.4, 1.2)
        blob(b, 'boulder', x, y, ground(x, y) - r * 0.45, r, n=7, rings=4, squash=rng.uniform(0.5, 0.8), jitter=0.28)
        n += 1


def brazier_spots():
    """(x, y, z) of each fire: before the gate (2), on the bridge's south posts (2), atop Ravenhill."""
    rx, ry = RAVEN
    return [(-3.9, GATE_Y - PLAT_D + 0.9, ZG + 1.9), (3.9, GATE_Y - PLAT_D + 0.9, ZG + 1.9),
            (-4.6, BRIDGE_Y + 1.3 - 0.3 - 2.0, BR_Z + 1.45 + 0.6), (4.6, BRIDGE_Y + 1.3 - 0.3 - 2.0, BR_Z + 1.45 + 0.6),
            (rx, ry, height(rx, ry) + 9.8 + 0.6)]


def wall_windows(b, rng):
    """Windows of the halls cut in the valley walls, lit from within, each with a lintel and a sill."""
    spots = [(-1, -6.5, 9.0), (-1, -7.5, 15.0), (-1, -11.0, 8.0), (-1, -12.5, 12.5), (-1, -16.0, 6.0),
             (1, -6.0, 11.0), (1, -8.5, 17.0), (1, -10.5, 7.5), (1, -13.0, 11.0), (1, -17.0, 5.5),
             (-1, -5.5, 20.0), (1, -5.5, 22.0)]
    for (s, y, z) in spots:
        x = vw(y)
        while abs(x) < 33 and height(s * x, y) < z:
            x += 0.08
        x *= s
        if hex_dist(x, y) < 4.0:
            continue                                    # the wall never gets that high here
        e = 0.3
        gx = (height(x + e, y) - height(x - e, y)) / (2 * e)
        gy = (height(x, y + e) - height(x, y - e)) / (2 * e)
        L = math.hypot(gx, gy) or 1.0
        nxv, nyv = -gx / L, -gy / L                     # outwards from the wall, towards the valley
        ang = math.degrees(math.atan2(nyv, nxv)) + 90.0  # the window's plane runs along the wall
        px, py = x + nxv * 0.25, y + nyv * 0.25
        box(b, 'statue', px, py, z - 0.35, 1.5, 0.9, 0.3, rz=ang)                 # sill
        box(b, 'litwin', px + nxv * 0.15, py + nyv * 0.15, z, 0.75, 0.6, 1.5, rz=ang)
        box(b, 'statue', px, py, z + 1.5, 1.6, 1.0, 0.35, rz=ang)                 # lintel


def statue(b, x, y, z, s):
    """A colossal dwarf warrior, facing -Y, carved in the hard geometric manner of the dwarves: lamellar skirt in
    three tiers over square boots, a faceted breastplate, stepped plate pauldrons, a long beard falling in strands to
    the belt with two bound braids below, a faceted pointed helm with nose and cheek guards; both fists on the
    pommel of a great double-bitted axe whose head rests between his feet."""
    def P(px, py, pz):
        return (x + px * s, y + py * s, z + pz * s)

    def R(rings):
        return [(x + cx * s, y + cy * s, z + cz * s, rx * s, ry * s, sh) for (cx, cy, cz, rx, ry, sh) in rings]

    def B(px, py, pz, sx, sy, sz, ry=0.0, rz=0.0):           # a box centred on P(px, py, pz)
        box(b, 'statue', 0, 0, -sz * s / 2, sx * s, sy * s, sz * s, M=T(*P(px, py, pz), rz=rz, ry=ry))

    strands = (lambda a: 1.0 + 0.09 * math.cos(11 * a) + 0.03 * math.cos(27 * a))
    for sd in (-1, 1):                                                  # square boots with toe caps
        B(sd * 1.25, -0.35, 0.7, 1.75, 2.6, 1.4)
        B(sd * 1.25, -1.55, 0.35, 1.6, 0.6, 0.7)
    for (z0, z1, r0, r1) in ((1.1, 3.6, 3.15, 2.85), (3.3, 5.8, 2.95, 2.65), (5.5, 7.6, 2.75, 2.5)):
        loft(b, 'statue', R([(0, 0, z0, r0, r0 * 0.78, None), (0, 0, z1, r1, r1 * 0.78, None)]), n=8, smooth_=False,
             a0=22.5)                                                   # the lamellar skirt
    loft(b, 'statue', R([(0, 0, 7.35, 2.7, 2.1, None), (0, 0, 8.45, 2.7, 2.1, None)]), n=8, smooth_=False, a0=22.5)
    loft(b, 'statue', R([(0, 0, 8.3, 2.55, 1.95, None), (0, 0, 10.8, 3.1, 2.25, None), (0, 0, 12.0, 2.95, 2.05, None),
                         (0, 0, 12.7, 2.1, 1.6, None), (0, -0.05, 13.05, 1.2, 1.1, None)]), n=8, smooth_=False, a0=22.5)
    for sd in (-1, 1):
        for k in range(3):                                              # stepped plate pauldrons
            B(sd * (2.5 + 0.38 * k), 0.0, 12.15 - 0.62 * k, 2.4 - 0.1 * k, 2.9 - 0.15 * k, 0.55, ry=sd * (16 + 9 * k))
        sh, el, wr = P(sd * 3.05, 0.0, 11.0), P(sd * 3.15, -0.85, 8.6), P(sd * 0.95, -3.2, 9.3)
        blib.strut(b, 'statue', sh, el, 0.82 * s, 0.78 * s, n=8, smooth=False)            # upper arm
        blib.sphere(b, 'statue', *el, 0.8 * s, n=8, rings=4)                             # elbow
        blib.strut(b, 'statue', el, wr, 0.76 * s, 0.7 * s, n=8, smooth=False)            # forearm
        f0 = tuple(el[i] + (wr[i] - el[i]) * 0.35 for i in range(3))
        f1 = tuple(el[i] + (wr[i] - el[i]) * 0.88 for i in range(3))
        blib.strut(b, 'statue', f0, f1, 0.9 * s, 0.88 * s, n=8, smooth=False)            # bracer
    for (dz, dx) in ((9.75, 0.08), (8.95, -0.08)):                      # the fists, one over the other
        B(dx, -3.45, dz - 0.05, 1.55, 1.15, 0.78)
        B(dx, -3.98, dz - 0.05, 1.45, 0.22, 0.6)                        # knuckles
    lathe(b, 'statue', [(0.3 * s, 0.0), (0.48 * s, 0.25 * s), (0.38 * s, 0.6 * s), (0.0, 0.75 * s)], 8,
          *P(0.0, -3.45, 10.15), smooth=False)                          # pommel
    cyl(b, 'statue', *P(0.0, -3.45, 0.2), 0.28 * s, 9.2 * s, n=8)       # haft
    for zz in (3.8, 5.6):
        cyl(b, 'statue', *P(0.0, -3.45, zz), 0.36 * s, 0.3 * s, n=8)    # bindings
    hy = y - 3.45 * s
    B(0.0, -3.45, 1.7, 0.9, 0.9, 2.5)                                   # the socket
    for sd in (-1, 1):
        blade = [(0.35, 0.95), (1.2, 0.55), (2.55, 0.05), (2.85, 1.7), (2.55, 3.35), (1.2, 2.85), (0.35, 2.45)]
        pts = [(x + sd * px * s, z + pz * s) for px, pz in blade]
        if sd < 0:
            pts = pts[::-1]
        slab_xz(b, 'statue', pts, hy + 0.17 * s, 0.34 * s)
    # the beard: broad, falling in strands to the belt; two braids bound in rings below it
    loft(b, 'statue', R([(0, -2.1, 7.9, 0.9, 0.4, strands), (0, -2.22, 8.4, 1.35, 0.55, strands),
                         (0, -2.35, 9.2, 1.7, 0.65, strands), (0, -2.42, 10.2, 1.95, 0.7, strands),
                         (0, -2.3, 11.2, 2.0, 0.75, strands), (0, -1.95, 12.2, 1.75, 0.75, strands),
                         (0, -1.4, 13.0, 1.25, 0.6, None)]), n=34)
    for sd in (-1, 1):
        braid = spline([P(sd * 0.55, -2.25, 8.3), P(sd * 0.6, -2.4, 7.0), P(sd * 0.55, -2.35, 5.6)], 12)
        nb = len(braid) - 1
        tube(b, 'statue', braid, [s * 0.34 * (1.0 + 0.2 * math.cos(i * math.pi)) for i in range(nb + 1)], n=8)
        for zz in (7.6, 5.2):
            cyl(b, 'statue', *P(sd * 0.56, -2.36, zz), 0.4 * s, 0.45 * s, n=8)          # braid rings
        tube(b, 'statue', spline([P(sd * 0.25, -1.78, 13.05), P(sd * 0.8, -1.95, 12.7), P(sd * 1.2, -2.05, 11.9)], 8),
             [s * r for r in (0.27, 0.25, 0.22, 0.19, 0.16, 0.13, 0.1, 0.08, 0.06)], n=8)     # moustache
    # the head and the faceted helm
    loft(b, 'statue', R([(0, -0.15, 12.9, 1.15, 1.05, None), (0, -0.1, 13.6, 1.3, 1.2, None),
                         (0, -0.05, 14.4, 1.32, 1.25, None), (0, 0.0, 15.0, 1.2, 1.15, None)]), n=12)
    B(0.0, -1.25, 14.2, 2.0, 0.45, 0.34)                                # brow
    B(0.0, -1.45, 13.55, 0.42, 0.5, 0.75)                               # nose
    loft(b, 'statue', R([(0, 0, 13.95, 1.66, 1.56, None), (0, 0, 14.55, 1.66, 1.56, None)]), n=8, smooth_=False,
         a0=22.5)                                                       # rim
    loft(b, 'statue', R([(0, 0, 14.5, 1.52, 1.44, None), (0, 0, 15.4, 1.4, 1.33, None), (0, 0, 16.2, 0.95, 0.9, None),
                         (0, 0, 16.95, 0.12, 0.12, None)]), n=8, smooth_=False, a0=22.5)
    B(0.0, -1.62, 13.4, 0.34, 0.26, 1.4)                                # nose guard
    for sd in (-1, 1):
        B(sd * 1.36, -0.45, 13.35, 0.28, 1.55, 1.5)                     # cheek guards
    B(0.0, -0.1, 15.9, 0.3, 2.6, 0.5, rz=0.0)                           # the crest, front to back


# ----------------------------------------------------------------------------------------------- rig
def rig():
    """Bones in in-game units: (name, parent, position, effect key or None)."""
    bones = [('fxglow', 'eyeroot', (0.0, GATE_Y - 0.7, GLOW_ZC), 'GATE_GLOW')]
    for i, p in enumerate(brazier_spots()):
        bones.append(('fire%d' % i, 'eyeroot', p, 'BRAZIER'))
    return bones


GLOW_BOX = (-8.5, 8.5, ZG - 0.6, GAL_Z + 3.2)
GLOW_ZC = (GLOW_BOX[2] + GLOW_BOX[3]) / 2


def glow_effect(k):
    """The additive gold light (tools/landmarks/glow.py): one quad in FILE units round the fxglow bone."""
    X0, X1, Z0_, Z1 = GLOW_BOX
    return dict(name='MEC_EreborGlow',
                quads=[(X0 * k, X1 * k, (Z0_ - GLOW_ZC) * k, (Z1 - GLOW_ZC) * k, 0.0)],
                tex_args=dict(lines=glow_lines(), box=GLOW_BOX, px=1024, color=(255, 176, 88), halo=0.42,
                              sigma=(0.3, 1.4)))


def _still(t):
    return 0.0


GAZE = dict(fn=_still, T=6.0, spans=60)

PREVIEW = [((0, -100, 85), (0, 6, 20), 34),                                      # the game's view
           ((12, -42, 16), (0, GATE_Y, 13), 38),                                 # the Front Gate
           ((-58, -52, 46), (0, 8, 22), 30),                                     # from the south-west, like a film still
           ((26, -26, 14), (STATUE_X, STATUE_Y, 14), 30)]                         # a guardian
PREVIEW_EYE = [((0, -40, 18), (0, GATE_Y, 13), 40)]
