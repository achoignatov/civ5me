"""Isengard: the tower of Orthanc in the Ring of Isengard, with Saruman on its summit (an IMPROVEMENT,
docs/LANDMARKS.md). The landmark of Isengard's capital.

Built like Erebor (in-game units, improvement Scale 0.25 with the writer's x4; origin = tile centre, ground z = 0,
-Y = south = towards the game camera) and FITS ITS OWN HEX. Isengard under Saruman, as in the films (2001-02) and
the book ("a peak and island of rock, black and gleaming hard: four mighty piers of many-sided stone were welded into
one, but near the summit they opened into gaping horns, their pinnacles sharp as the points of spears, keen-edged as
knives. Between them was a narrow space, and there upon a floor of polished stone...").
  * Orthanc: black, glossy, hard-edged stone; four faceted piers welded round an octagonal core, with deep channels
    between them where the narrow windows are; the piers flare into knife-edged roots at the foot and open near the
    summit into four great horns; smaller blades between them; a balcony over the door, a stair to the door, a
    stepped plinth;
  * Saruman the White on the summit floor between the horns, facing the camera (after the user's reference,
    screenshots/saruman.webp): white robes, long white hair and a long beard, his black staff in his right hand with
    its open claw round a white light (an additive glow), the palantir raised in his left;
  * the Ring of Isengard: a circle of rugged dark rock, higher in the north where the feet of Methedras rise behind,
    cut in the south by the gate: two dark pylons, an arch, iron doors, banners of the White Hand;
  * the plain within (films): blackened mud torn into fiery pits with timber scaffolds, treadwheel cranes, furnace
    chimneys, felled trees of Fangorn; a paved road with pillars and chains from the gate to the stair.
Muted, real (the user's rule, landmark-realism): black stone, dark rock, smoke-stained mud, weathered timber.

Two parts: static = the land, the Ring and its gate, Orthanc; skinned = Saruman, the industry, pillars, gates,
banners, all on the still bone (PIVOT_MATS is empty: nothing moves), plus the effect bones (the staff's glow, fires).
"""
import math
import random

from mathutils import Vector

import blib
from blib import material, hexcol as h, box, cyl, lathe, blob, ring
from moria_v4 import smooth, fbm, ridged, tube, _spline as spline
from erebor import oriented, loft, ribbon, hex_dist

BAKE = True
BAKE_PX = 2048
EYE_PX = 2048
EYE_AO = 16
TINY_PX = 24
PIVOT_MATS = set()                 # nothing moves: every skinned vertex on the still bone

HEX = 33.6
FLOOR = -1.0
FZ = 1.0                           # the plain within the Ring (just above the game's ground: the pits sink into it)
RW = 27.0                          # the Ring's crest
GATE_HW = 3.0                      # half-width of the cut of the gate
ZP = FZ + 2.4                      # top of Orthanc's plinth (the door's sill)
Z_TOP = 50.0                       # the summit floor between the horns
SAR = (0.0, -1.5)                  # where Saruman stands
SAR_H = 7.8                        # his height (heroic scale: he must read from the game's camera; user: bigger)
HORN = 7.0                         # height of the horns above the summit floor (user: smaller and thinner)
ROAD_Y0, ROAD_Y1 = -RW - 4.0, -10.6

# pits of the industry: (radius from the centre, angle in degrees, pit radius)
PITS = [(14.0, 12, 2.3), (20.5, 36, 1.9), (13.0, 62, 2.1), (19.5, 88, 2.0), (13.5, 118, 2.2), (20.0, 145, 1.8),
        (13.5, 168, 2.1), (20.0, 196, 2.0), (13.5, 222, 2.0), (19.5, 246, 1.7), (14.0, 318, 2.2), (20.5, 296, 1.8),
        (21.5, 340, 1.6)]
CHIMNEYS = [(17.5, 75, 8.5), (16.5, 132, 7.0), (22.0, 210, 7.5), (17.0, 25, 6.5)]
FIRE_PITS = (0, 2, 4, 8, 10, 6)


def polar(r, deg):
    a = math.radians(deg)
    return r * math.cos(a), r * math.sin(a)


def pit_list():
    return [(*polar(r, a), pr) for (r, a, pr) in PITS]


# ----------------------------------------------------------------------------------------------- the land
def crest(a):
    """Height of the Ring's crest at angle a (radians): higher in the north (the feet of Methedras)."""
    north = max(0.0, math.sin(a)) ** 2
    c, s = math.cos(a), math.sin(a)
    return 6.0 + 7.5 * north + 2.2 * fbm(c * 2.6 + 3.0, s * 2.6 - 1.0, 3, 51) + 1.6 * fbm(c * 7 + 1, s * 7, 2, 52)


def ring_h(x, y):
    r = math.hypot(x, y)
    a = math.atan2(y, x)
    north = max(0.0, math.sin(a)) ** 2
    cz = crest(a)
    if r < RW:                                             # the inner face: a steep cliff
        p = smooth((r - (RW - 3.2)) / 3.2) ** 0.8
    else:                                                  # the outer side falls away more gently
        p = 1.0 - smooth((r - RW) / (4.2 + 3.0 * north))
    z = cz * p
    if p > 0.02:                                           # crags, gullies, ledges
        wx, wy = x + 3.0 * fbm(x * 0.1, y * 0.1, 2, 53), y + 3.0 * fbm(y * 0.1, x * 0.1, 2, 54)
        z += (3.2 * ridged(wx * 0.22, wy * 0.22, 4, 55) - 1.3) * p
        z += 0.6 * fbm(x * 0.9, y * 0.9, 2, 56) * p
        if z > 2.0:
            q = z / 1.6
            z += ((math.floor(q) + smooth((q - math.floor(q)) * 1.8)) * 1.6 - z) * 0.3
    return z


def gate_k(x, y):
    """1 in the cut of the gate, 0 outside it."""
    if y > -RW + 7.0:
        return 0.0
    return 1.0 - smooth((abs(x) - GATE_HW) / 1.2)


def pit_d(x, y):
    """(distance to the nearest pit's rim as a fraction of its radius, that pit) - < 1 inside."""
    best, bp = 9.0, None
    for (px, py, pr) in pit_list():
        d = math.hypot(x - px, y - py) / pr
        if d < best:
            best, bp = d, (px, py, pr)
    return best, bp


def height(x, y):
    r = math.hypot(x, y)
    plain = FZ + 0.12 * fbm(x * 0.35, y * 0.35, 3, 61) + 0.06 * fbm(x * 1.4, y * 1.4, 2, 62)
    if r > RW - 1.0:
        plain -= (r - RW + 1.0) * 0.55                       # outside the Ring: down under the game's ground
    z = max(plain, ring_h(x, y))
    g = gate_k(x, y)
    if g > 0:
        road = FZ + 0.02 - max(0.0, -RW - 3.0 - y) * 0.5
        z = road + (z - road) * (1.0 - g)
    d, p = pit_d(x, y)
    if d < 1.25:                                           # the pits: a raised lip, then down to the embers
        lip = 0.18 * math.exp(-((d - 1.05) / 0.12) ** 2)
        z += lip
        if d < 1.0:
            z = min(z, FZ - 0.78 + 0.78 * smooth((d - 0.55) / 0.45))
    return FLOOR + (z - FLOOR) * smooth((hex_dist(x, y) - 0.4) / 5.0)


def ground(x, y):
    return max(height(x, y), 0.0)


def ground_mat(x, y, z, s):
    d, _ = pit_d(x, y)
    if d < 0.6:
        return 'embers'
    if d < 1.0:
        return 'pitwall'
    r = math.hypot(x, y)
    if r > RW - 4.5 and z > FZ + 0.5 and gate_k(x, y) < 0.5:
        return 'ringrock'
    if r > RW + 0.5:
        return 'ringrock'
    return 'mud'


# ----------------------------------------------------------------------------------------------- materials
def stone_palette():
    material('ringrock', h('4d4a45'), h('3d3b37'), slope_color=h('45423d'), slope_start=0.6,
             zramp=[(FLOOR, h('4a463f')), (6.0, h('4f4c47')), (14.0, h('5a5853'))])
    blib.PALETTE['ringrock'].update(scale=0.14, strata=0.8, strata_amp=0.1, cracks=0.9, cavity=0.6,
                                    vcracks=(0.45, 0.25), speckle=[(2.5, 0.06, h('5b5544'))])
    material('mud', h('3b352e'), h('2f2a25'))
    blib.PALETTE['mud'].update(scale=0.4, cracks=1.3, cavity=0.45,
                               speckle=[(3.0, 0.1, h('4a4136')), (6.0, 0.05, h('221e1b'))])
    material('pitwall', h('2a2420'), h('1f1a17'))
    blib.PALETTE['pitwall'].update(scale=0.6, cracks=1.2, cavity=0.5, speckle=[(4.0, 0.12, h('6a2a12'))])
    material('embers', h('d2541a'), h('8f2a10'), ao=False)
    blib.PALETTE['embers'].update(scale=0.8, cracks=2.0, speckle=[(5.0, 0.25, h('ffb347'))])
    # Orthanc: black, hard, faintly glossy; long vertical joints
    material('orthanc', h('242529'), h('1b1c20'), spec=0.6, refl=80)
    blib.PALETTE['orthanc'].update(scale=0.12, strata=0.35, strata_amp=0.05, cracks=0.25, cavity=0.55,
                                   vcracks=(0.5, 0.18))
    material('obsid', h('25262b'), h('1d1e22'), spec=0.6, refl=90)          # dressed surfaces: plinth, stair
    blib.PALETTE['obsid'].update(scale=0.5, cracks=0.9, cavity=0.5)
    material('gatestone', h('3a3936'), h('2f2e2b'))
    blib.PALETTE['gatestone'].update(scale=0.4, strata=1.4, strata_amp=0.06, cracks=1.0, cavity=0.6)
    material('road', h('4f4b44'), h('3f3c36'))
    blib.PALETTE['road'].update(scale=0.8, cracks=2.2, cavity=0.4)
    material('dark', h('0c0b0b'))
    blib.PALETTE['dark'].update(solid=True)
    material('litwin', h('9a5a2c'), ao=False)
    blib.PALETTE['litwin'].update(solid=True)


def life_palette():
    stone_palette()
    material('robe', h('dcd7c9'), h('cbc5b5'))
    blib.PALETTE['robe'].update(scale=3.0, cavity=0.7)
    material('hair', h('e2ded4'), h('cfcac0'))
    blib.PALETTE['hair'].update(scale=4.0, vcracks=(0.6, 0.3), cavity=0.5)
    material('skin', h('c9a48b'), h('b89079'))
    blib.PALETTE['skin'].update(solid=True)
    material('staff', h('1b1b1e'), h('141416'), spec=0.6, refl=90)
    blib.PALETTE['staff'].update(solid=True)
    material('orb', h('f4f6ff'), ao=False)
    blib.PALETTE['orb'].update(solid=True)
    material('palantir', h('ffa040'), h('ff8a2a'), spec=0.95, refl=220, ao=False)   # glowing (+ the additive glow)
    blib.PALETTE['palantir'].update(solid=True)
    material('clasp', h('8b8370'), spec=0.6, refl=80)
    blib.PALETTE['clasp'].update(solid=True)
    material('timber', h('4b3d2f'), h('3b3026'))
    blib.PALETTE['timber'].update(scale=1.5, vcracks=(0.7, 0.4), cavity=0.5)
    material('iron', h('29282a'), h('1e1d1f'), spec=0.5, refl=40)
    blib.PALETTE['iron'].update(solid=True)
    material('rust', h('4a3328'), h('3a2820'))
    blib.PALETTE['rust'].update(scale=1.0, cracks=0.8)
    material('brick', h('4a3e36'), h('3d332d'))
    blib.PALETTE['brick'].update(scale=0.5, strata=3.5, strata_amp=0.12, cracks=1.0, cavity=0.6)
    material('ember', h('ff8a32'), ao=False)
    blib.PALETTE['ember'].update(solid=True)
    material('log', h('5a4936'), h('4a3c2c'))
    blib.PALETTE['log'].update(scale=2.0, vcracks=(0.6, 0.3))
    material('banner', h('1a1817'), h('141312'))
    blib.PALETTE['banner'].update(scale=2.0, glow=True, glow_color=h('ebe8e0'), uv_boost=7.0)


# ----------------------------------------------------------------------------------------------- mesh helpers
def loft_poly(b, mat, secs, apex=None, cap0=True, smooth_=False):
    """Closed solid through horizontal sections (lists of 3D points, counter-clockwise seen from above, the same
    count each); the top closes in a flat cap or in the point `apex`."""
    n = len(secs[0])
    v, f = [], []
    for s in secs:
        v += [tuple(p) for p in s]
    for i in range(len(secs) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            f.append((i * n + k, i * n + k2, (i + 1) * n + k2, (i + 1) * n + k))
    last = (len(secs) - 1) * n
    if apex is not None:
        v.append(tuple(apex))
        a = len(v) - 1
        for k in range(n):
            f.append((last + k, last + (k + 1) % n, a))
    else:
        f.append(tuple(last + k for k in range(n)))
    if cap0:
        f.append(tuple(range(n))[::-1])
    b.add(v, f, mat, smooth=smooth_)


def wall_poly(b, mat, phi, R, pts, depth, z0=0.0):
    """A convex polygon [(s, z)] on the vertical plane at distance R from the axis, facing direction phi (degrees),
    s along the wall (to the right seen from outside), extruded outwards by depth."""
    a = math.radians(phi)
    er, et = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
    n = len(pts)

    def P(s, z, rr):
        return (rr * er[0] + s * et[0], rr * er[1] + s * et[1], z + z0)
    v = [P(s, z, R + depth) for s, z in pts] + [P(s, z, R) for s, z in pts]
    out = (er[0], er[1], 0.0)
    f = oriented(v, [tuple(range(n))], out)
    cs, cz = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
    for i in range(n):
        j = (i + 1) % n
        ms, mz = (pts[i][0] + pts[j][0]) / 2 - cs, (pts[i][1] + pts[j][1]) / 2 - cz
        f += oriented(v, [(i, j, n + j, n + i)], (et[0] * ms, et[1] * ms, mz))
    b.add(v, f, mat)


def arch_pts(w, h, k=0.55):
    """A pointed (lancet) arch: half-width w, total height h, the springing at h - k * 2w."""
    spring = h - 2 * w * k * 1.8
    pts = [(-w, 0.0), (w, 0.0), (w, spring)]
    R = 2 * w * 0.9
    for i in range(1, 6):                                  # right half of the point
        t = i / 6
        pts.append((w - (w) * t ** 0.7, spring + (h - spring) * math.sin(t * math.pi / 2)))
    pts.append((0.0, h))
    for i in range(5, 0, -1):
        t = i / 6
        pts.append((-w + (w) * t ** 0.7, spring + (h - spring) * math.sin(t * math.pi / 2)))
    pts.append((-w, spring))
    del R
    return pts


# ----------------------------------------------------------------------------------------------- Orthanc's form
def core_ap(z):
    """Apothem of the octagonal core (flat faces N/E/S/W)."""
    t = (z - ZP) / (Z_TOP - ZP)
    return 3.2 - 0.35 * t + 1.3 * math.exp(-max(0.0, z - ZP) / 2.6)


def pier(z):
    """(distance of the pier's axis, half-width, outer tip, inner reach) at height z."""
    t = max(0.0, (z - ZP) / (Z_TOP - ZP))
    e = math.exp(-max(0.0, z - FZ) / 3.4)
    lean = 1.3 * smooth((z - 38.0) / 12.0)                 # near the summit the piers part (into the horns)
    thin = 1.0 - 0.42 * smooth((z - 40.0) / 10.0)          # ...and slim down into the horns
    d = 3.7 + 2.8 * e + lean - 0.3 * t
    w = (1.75 - 0.3 * t + 0.55 * e) * thin
    tip = (2.05 + 1.7 * e - 0.2 * t) * thin
    return d, w, tip, -2.4


def pier_sec(phi, z, scale=1.0, d=None):
    dd, w, tip, uin = pier(z)
    if d is not None:
        dd = d
    w, tip, uin = w * scale, tip * scale, uin * scale
    a = math.radians(phi)
    er, et = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
    shape = [(uin, -0.72 * w), (-0.9 * w, -w), (0.15 * tip, -w * 0.98), (0.62 * tip, -0.62 * w), (tip, 0.0),
             (0.62 * tip, 0.62 * w), (0.15 * tip, w * 0.98), (-0.9 * w, w), (uin, 0.72 * w)]
    return [(dd * er[0] + u * er[0] + v * et[0], dd * er[1] + u * er[1] + v * et[1], z) for u, v in shape]


def oct_sec(ap, z, a0=22.5):
    R = ap / math.cos(math.radians(22.5))
    return [(R * math.cos(math.radians(a0 + 45 * k)), R * math.sin(math.radians(a0 + 45 * k)), z) for k in range(8)]


# ----------------------------------------------------------------------------------------------- static part
def build(b, eye=False):
    b.tiny_px = 0
    b.ao_distance = 5.0
    stone_palette()
    blib.SKIRT_MAT[0] = 'ringrock'

    # ===================================================================== the Ring and the plain
    X0, X1, Y0, Y1 = -HEX, HEX, -HEX / 0.866, HEX / 0.866
    blib.terrain(b, height, X0, X1, Y0, Y1, 108, 126, ground_mat,
                 keep=lambda x, y: hex_dist(x, y) > 0.3 and height(x, y) > -0.1, smooth=True, skirt=FLOOR - 1.0)

    build_gate(b)
    build_orthanc(b)
    # the road from the gate to the stair
    rp = [(0.0, y) for y in [ROAD_Y0 + 0.5 * i for i in range(int((ROAD_Y1 - ROAD_Y0) / 0.5) + 1)]]
    ribbon(b, 'road', rp, lambda i: 1.45, lambda x, y, i: ground(x, y) + 0.05)


def build_gate(b):
    """The gate of Isengard: two dark pylons in the cut of the Ring, an arch between them."""
    yg = -RW
    for s in (-1, 1):
        x = s * (GATE_HW + 1.7)
        z0 = FZ - 1.6
        secs = []
        for (zz, hx, hy) in ((z0, 1.9, 3.0), (FZ + 2.0, 1.75, 2.8), (FZ + 7.5, 1.45, 2.4), (FZ + 9.0, 1.4, 2.3)):
            secs.append([(x - hx, yg - hy, zz), (x + hx, yg - hy, zz), (x + hx, yg + hy, zz), (x - hx, yg + hy, zz)])
        loft_poly(b, 'gatestone', secs, apex=(x, yg, FZ + 12.0))
        for zz in (FZ + 2.0, FZ + 7.5):                                     # string courses
            box(b, 'gatestone', x, yg, zz - 0.15, 3.8 - (zz - FZ) * 0.06, 6.0 - (zz - FZ) * 0.1, 0.3)
        wall_poly(b, 'dark', 270, -(yg - 2.75), arch_pts(0.32, 2.4), 0.02, z0=FZ + 4.0)   # arrow slits
        x_in = s * (GATE_HW + 0.1)
        # the cut's walls behind the pylons, dressed
        box(b, 'gatestone', s * (GATE_HW + 0.6), yg + 4.5, FZ - 1.0, 1.2, 6.0, 5.5)
        del x_in
    # the arch over the gate
    pts = [(-GATE_HW - 0.2, FZ + 6.4), (GATE_HW + 0.2, FZ + 6.4), (GATE_HW + 0.2, FZ + 8.4), (-GATE_HW - 0.2, FZ + 8.4)]
    for e in (0, 1):
        wall_poly(b, 'gatestone', 270, RW + 1.1 - e * 2.2, pts, 0.9 if e == 0 else 0.9)
    box(b, 'gatestone', 0.0, yg, FZ + 8.4, 2 * GATE_HW + 0.6, 3.6, 0.5)
    for k in range(7):                                                      # spikes along its top
        x = -GATE_HW + 2 * GATE_HW * k / 6
        blib.cone(b, 'gatestone', x, yg - 1.2, FZ + 8.9, 0.22, 1.0, n=4)


def build_orthanc(b):
    # ---- the plinth: three steps of dressed black stone (octagons), broken by the stair on the south
    for (ap, z0, z1) in ((9.2, FZ - 0.6, FZ + 0.8), (8.2, FZ + 0.8, FZ + 1.6), (7.2, FZ + 1.6, ZP)):
        loft_poly(b, 'obsid', [oct_sec(ap, z0), oct_sec(ap, z1)])
    n_st = 14
    for i in range(n_st):                                                   # the stair (27 steps in the book)
        t = (i + 1) / n_st
        y = -10.6 + 4.2 * i / n_st
        box(b, 'obsid', 0.0, y + 0.15, FZ - 0.4, 2.8, 0.32, (ZP - FZ + 0.4) * t)
        del y
    for s in (-1, 1):                                                       # its cheeks
        for k in range(4):
            box(b, 'obsid', s * 1.65, -10.6 + 1.1 * k + 0.55, FZ - 0.4, 0.5, 1.1, (ZP - FZ + 0.9) * (k + 1) / 4 + 0.2)

    # ---- the core: an octagon from the plinth to the summit floor
    zs = [FZ - 0.5] + [ZP + 10.0 * (i / 8) ** 1.5 for i in range(9)] + [ZP + 10.0 + (Z_TOP - ZP - 10.0) * i / 8
                                                                       for i in range(1, 9)]
    loft_poly(b, 'orthanc', [oct_sec(core_ap(z), z) for z in zs])

    # ---- the four piers: faceted, flaring into knife-edged roots at the foot, parting near the summit into horns
    zs = ([FZ - 0.6] + [FZ + 13.0 * (i / 12) ** 1.6 for i in range(13)] + [FZ + 13.0 + 4.0 * i for i in range(1, 7)]
          + [38.0 + 1.5 * i for i in range(1, 9)] + [Z_TOP + 1.0])
    for k in range(4):
        phi = 45 + 90 * k
        secs = [pier_sec(phi, z) for z in zs]
        # the horn: the pier goes on, sweeping out and up to a knife point
        d0, _, _, _ = pier(Z_TOP + 1.0)
        nh = 12
        for i in range(1, nh):
            t = i / nh
            z = Z_TOP + 1.0 + HORN * t
            d = d0 + 1.2 * t ** 0.75 - 0.6 * t ** 2.6
            secs.append(pier_sec(phi, z, scale=(1.0 - t) ** 1.1 * (1.0 + 0.08 * math.sin(t * math.pi)), d=d))
        a = math.radians(phi)
        dtip = d0 + 1.2 - 0.6 + 0.1
        loft_poly(b, 'orthanc', secs, apex=(dtip * math.cos(a), dtip * math.sin(a), Z_TOP + 1.0 + HORN + 0.6))
        # bands: a slightly larger collar of the pier at three heights
        for zb in (16.5, 29.0, 40.5):
            loft_poly(b, 'orthanc', [pier_sec(phi, zb, 1.07), pier_sec(phi, zb + 0.55, 1.07)])
        # a keen fin down the outer edge of each pier, from the summit to the roots
        er, et = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        secs = []
        for i in range(18):
            z = FZ + 0.5 + (Z_TOP - FZ - 2.0) * (i / 17) ** 1.3
            dd, w, tip, _ = pier(z)
            r = dd + tip
            secs.append([((r + u) * er[0] + v * et[0], (r + u) * er[1] + v * et[1], z)
                         for u, v in ((-0.05, -0.1), (0.38, 0.0), (-0.05, 0.1), (-0.3, 0.0))])
        loft_poly(b, 'orthanc', secs)

    # ---- the summit floor and the smaller blades between the horns (none on the south: Saruman stands there)
    loft_poly(b, 'obsid', [oct_sec(core_ap(Z_TOP) + 0.6, Z_TOP - 0.4), oct_sec(core_ap(Z_TOP) + 0.6, Z_TOP + 0.25)])
    for phi in (0, 90, 180):
        a = math.radians(phi)
        er, et = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        r0 = core_ap(Z_TOP) + 0.3
        secs = []
        for (zz, sc) in ((Z_TOP - 2.0, 0.7), (Z_TOP + 0.8, 0.55), (Z_TOP + 2.2, 0.35)):
            shape = [(-0.6 * sc, -0.55 * sc), (0.6 * sc, -0.35 * sc), (1.2 * sc, 0.0), (0.6 * sc, 0.35 * sc),
                     (-0.6 * sc, 0.55 * sc)]
            secs.append([((r0 + u) * er[0] + v * et[0], (r0 + u) * er[1] + v * et[1], zz) for u, v in shape])
        rt = r0 + 0.6
        loft_poly(b, 'orthanc', secs, apex=(rt * er[0], rt * er[1], Z_TOP + 3.8))

    # ---- windows: narrow lancets in the deep channels between the piers
    lit = {(270, 27.0), (0, 34.0)}
    for phi in (0, 90, 180, 270):
        for zw in (10.5, 16.0, 22.0, 27.0, 34.0, 40.0, 45.0):
            if phi == 270 and zw in (16.0,):
                continue                                                    # the balcony's door is there
            w_, h_ = (0.32, 2.2) if zw < 44 else (0.28, 1.6)
            ap = core_ap(zw + h_ / 2)
            wall_poly(b, 'litwin' if (phi, zw) in lit else 'dark', phi, ap, arch_pts(w_, h_), 0.03, z0=zw)
            wall_poly(b, 'orthanc', phi, ap, [(-w_ - 0.18, -0.3), (w_ + 0.18, -0.3), (w_ + 0.18, 0.0),
                                              (-w_ - 0.18, 0.0)], 0.22, z0=zw)                     # sill

    # ---- the door at the head of the stair, and the balcony above it
    apd = core_ap(ZP + 2.5)
    wall_poly(b, 'dark', 270, apd, arch_pts(1.0, 4.6), 0.04, z0=ZP)
    for s in (-1, 1):                                                       # its jambs, deep and sharp
        wall_poly(b, 'obsid', 270, apd, [(s * 1.0, 0.0), (s * 1.55, 0.0), (s * 1.3, 4.4), (s * 1.0, 3.6)][::s], 0.5,
                  z0=ZP)
    zb = 16.0
    apb = core_ap(zb)
    secs = []
    for (zz, out, hw) in ((zb - 2.6, 0.05, 0.6), (zb - 0.9, 1.4, 1.5), (zb, 2.1, 1.8), (zb + 0.35, 2.1, 1.8)):
        y0 = -apb + 0.3
        secs.append([(-hw, y0 - out, zz), (-hw * 0.3, y0 - out - 0.35, zz), (hw * 0.3, y0 - out - 0.35, zz),
                     (hw, y0 - out, zz), (hw, y0 + 0.2, zz), (-hw, y0 + 0.2, zz)])
    loft_poly(b, 'obsid', secs[:])
    wall_poly(b, 'dark', 270, apb, arch_pts(0.55, 2.8), 0.04, z0=zb + 0.35)
    for i in range(11):                                                     # a railing of spikes round the balcony
        t = i / 10
        x = -1.75 + 3.5 * t
        y = -apb + 0.3 - 2.0 - 0.35 * (1.0 - abs(2 * t - 1)) + 0.15
        blib.cone(b, 'obsid', x, y, zb + 0.35, 0.07, 1.25, n=4)
    v = []
    pts = [(-1.8, -apb + 0.3 - 2.0), (-0.55, -apb + 0.3 - 2.35), (0.55, -apb + 0.3 - 2.35), (1.8, -apb + 0.3 - 2.0)]
    for (p, q) in zip(pts, pts[1:]):
        blib.strut(b, 'obsid', (p[0], p[1] + 0.15, zb + 1.05), (q[0], q[1] + 0.15, zb + 1.05), 0.06, 0.06, n=4)
    del v


# ----------------------------------------------------------------------------------------------- skinned part
def build_eye(b):
    b.tiny_px = TINY_PX
    life_palette()
    rng = random.Random(1717)

    saruman(b, SAR[0], SAR[1], Z_TOP + 0.25, SAR_H)

    # ===================================================================== the gate: iron doors, banners
    yg = -RW
    for s in (-1, 1):
        x0, x1 = s * 0.05, s * GATE_HW
        lo, hi = min(x0, x1), max(x0, x1)
        pts = [(lo, FZ), (hi, FZ), (hi, FZ + 6.3), (lo, FZ + 6.3)]
        slab = [(x, z) for x, z in pts]
        from erebor import slab_xz, bar_xz
        slab_xz(b, 'iron', slab, yg + 0.3, 0.35)
        for k in range(5):                                                   # vertical ribs
            xx = lo + (hi - lo) * (k + 0.5) / 5
            bar_xz(b, 'rust', xx, FZ + 0.2, xx, FZ + 6.1, 0.14, yg - 0.05, 0.1)
            blib.cone(b, 'iron', xx, yg + 0.12, FZ + 6.3, 0.1, 0.8, n=4)    # spikes on top
        for zz in (FZ + 1.2, FZ + 3.2, FZ + 5.2):
            bar_xz(b, 'rust', lo + 0.1, zz, hi - 0.1, zz, 0.2, yg - 0.05, 0.1)
    # banners of the White Hand on the pylons
    for s in (-1, 1):
        x = s * (GATE_HW + 1.7)
        yb = yg - 2.85
        cyl(b, 'iron', x - 0.85, yb, FZ + 8.5, 0.05, 0.05)
        blib.strut(b, 'iron', (x - 0.85, yb, FZ + 8.4), (x + 0.85, yb, FZ + 8.4), 0.06, 0.06, n=5)
        from erebor import slab_xz
        slab_xz(b, 'banner', [(x - 0.8, FZ + 8.35), (x + 0.8, FZ + 8.35), (x + 0.8, FZ + 3.4), (x, FZ + 2.7),
                              (x - 0.8, FZ + 3.4)], yb, 0.06)
    b.glow = dict(lines=hand_lines(), box=(-GATE_HW - 3.0, GATE_HW + 3.0, FZ + 2.5, FZ + 8.6), sigma=(0.02, 0.04))

    # ===================================================================== pillars and chains along the road
    posts = []
    for i in range(7):
        y = -RW + 3.0 + i * 2.35
        for s in (-1, 1):
            x = s * 1.95
            z = ground(x, y)
            box(b, 'gatestone', x, y, z - 0.2, 0.55, 0.55, 0.3)
            loft_poly(b, 'gatestone', [[(x - 0.2, y - 0.2, z), (x + 0.2, y - 0.2, z), (x + 0.2, y + 0.2, z),
                                        (x - 0.2, y + 0.2, z)],
                                       [(x - 0.16, y - 0.16, z + 2.6), (x + 0.16, y - 0.16, z + 2.6),
                                        (x + 0.16, y + 0.16, z + 2.6), (x - 0.16, y + 0.16, z + 2.6)]],
                      apex=(x, y, z + 3.1))
            posts.append((x, y, z + 2.5))
    for s in (-1, 1):
        row = [p for p in posts if p[0] * s > 0]
        for p, q in zip(row, row[1:]):
            m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2 - 0.6)
            pts = spline([p, m, q], 8)
            tube(b, 'iron', pts, [0.06] * len(pts), n=4, tip=False)

    # ===================================================================== the industry: pits, scaffolds, cranes
    pits = pit_list()
    for i, (px, py, pr) in enumerate(pits):
        pit_works(b, rng, i, px, py, pr)
    for (r, a, hc) in CHIMNEYS:
        cx, cy = polar(r, a)
        z = ground(cx, cy)
        box(b, 'brick', cx, cy, z - 0.3, 2.2, 2.2, 1.6)                     # the furnace
        lathe(b, 'brick', [(0.75, 0.0), (0.62, hc * 0.5), (0.5, hc), (0.62, hc + 0.2), (0.62, hc + 0.5),
                           (0.42, hc + 0.5), (0.42, hc + 0.2)], 10, cx, cy, z + 1.2, smooth=False)
        cyl(b, 'ember', cx, cy, z + 1.2 + hc + 0.15, 0.43, 0.06, n=10)
        box(b, 'ember', cx, cy - 1.12, z + 0.1, 0.8, 0.04, 0.7)            # the furnace's glowing mouth
    # felled trees of Fangorn in heaps by the Ring's foot
    for (r, a) in ((22.0, 60), (22.5, 120), (23.0, 160), (22.5, 15), (23.5, 228)):
        cx, cy = polar(r, a)
        ang = a + 90
        for k in range(9):
            row_ = k // 4 if k < 8 else 2
            off = (k % 4 - 1.5) * 0.42 if k < 8 else 0.0
            zz = ground(cx, cy) + 0.2 + row_ * 0.36
            ox, oy = -math.sin(math.radians(ang)) * off, math.cos(math.radians(ang)) * off
            L = rng.uniform(3.6, 4.4)
            dx, dy = math.cos(math.radians(ang)) * L / 2, math.sin(math.radians(ang)) * L / 2
            blib.strut(b, 'log', (cx + ox - dx, cy + oy - dy, zz), (cx + ox + dx, cy + oy + dy, zz), 0.2, 0.17, n=6)
    # stumps and debris scattered on the plain
    n = 0
    for _ in range(3000):
        if n >= 40:
            break
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(9.5, RW - 3.0)
        x, y = r * math.cos(a), r * math.sin(a)
        if abs(x) < 3.0 and y < 0:
            continue
        if pit_d(x, y)[0] < 1.6:
            continue
        z = ground(x, y)
        if rng.random() < 0.6:
            cyl(b, 'log', x, y, z - 0.1, rng.uniform(0.18, 0.3), rng.uniform(0.3, 0.6), n=6)
        else:
            blob(b, 'pitwall', x, y, z - 0.15, rng.uniform(0.3, 0.6), n=6, rings=3, squash=0.5, jitter=0.3)
        n += 1


def pit_works(b, rng, i, px, py, pr):
    """Timber about a pit: a frame of posts and beams on its lip; some have a treadwheel crane or a hoist."""
    z = FZ + 0.1
    ang = math.degrees(math.atan2(py, px))
    a = math.radians(ang)
    er, et = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
    R = pr + 0.35
    corners = []
    for k in range(4):
        c = math.radians(45 + 90 * k) + a
        corners.append((px + R * math.cos(c), py + R * math.sin(c)))
    for (cx, cy) in corners:
        blib.strut(b, 'timber', (cx, cy, z - 0.3), (cx, cy, z + 1.6), 0.1, 0.09, n=4)
    for p, q in zip(corners, corners[1:] + corners[:1]):
        blib.strut(b, 'timber', (p[0], p[1], z + 1.5), (q[0], q[1], z + 1.5), 0.08, 0.08, n=4)
        blib.strut(b, 'timber', (p[0], p[1], z + 0.5), (q[0], q[1], z + 0.5), 0.06, 0.06, n=4)
    kind = i % 3
    if kind == 0:                    # a treadwheel crane on the outer side
        wx, wy = px + er[0] * (R + 1.2), py + er[1] * (R + 1.2)
        rz = math.degrees(a)
        M = blib.T(wx, wy, z + 1.45, rz=rz, rx=90)
        rim = [(wx + 1.25 * math.cos(math.radians(30 * j)) * et[0], wy + 1.25 * math.cos(math.radians(30 * j)) * et[1],
                z + 1.45 + 1.25 * math.sin(math.radians(30 * j))) for j in range(12)]
        for p_, q_ in zip(rim, rim[1:] + rim[:1]):
            for e in (-0.3, 0.3):
                blib.strut(b, 'timber', (p_[0] + e * er[0], p_[1] + e * er[1], p_[2]),
                           (q_[0] + e * er[0], q_[1] + e * er[1], q_[2]), 0.07, 0.07, n=4)
        del M, rz
        for k in range(4):
            c = math.radians(45 * k)
            blib.strut(b, 'timber', (wx + 1.2 * math.cos(c) * et[0], wy + 1.2 * math.cos(c) * et[1],
                                     z + 1.45 + 1.2 * math.sin(c)),
                       (wx - 1.2 * math.cos(c) * et[0], wy - 1.2 * math.cos(c) * et[1], z + 1.45 - 1.2 * math.sin(c)),
                       0.05, 0.05, n=4)
        for e in (-1, 1):            # its A-frame
            blib.strut(b, 'timber', (wx + e * 0.9 * er[0] + 0.0, wy + e * 0.9 * er[1], z - 0.2),
                       (wx, wy, z + 1.5), 0.08, 0.07, n=4)
        top = (wx - er[0] * 0.5, wy - er[1] * 0.5, z + 4.6)  # the jib, out over the pit
        blib.strut(b, 'timber', (wx, wy, z + 1.5), top, 0.11, 0.09, n=4)
        tipp = (px, py, z + 4.4)
        blib.strut(b, 'timber', top, tipp, 0.08, 0.06, n=4)
        blib.strut(b, 'iron', tipp, (px, py, z + 1.2), 0.025, 0.025, n=3)
        box(b, 'rust', px, py, z + 0.6, 0.6, 0.6, 0.6)
    elif kind == 1:                  # a tall hoist: four legs to a head over the pit
        hz = z + 4.2 + rng.uniform(-0.4, 0.6)
        for (cx, cy) in corners:
            blib.strut(b, 'timber', (cx, cy, z + 1.5), (px + (cx - px) * 0.25, py + (cy - py) * 0.25, hz), 0.08,
                       0.07, n=4)
        box(b, 'timber', px, py, hz - 0.1, 0.9, 0.9, 0.35)
        blib.strut(b, 'iron', (px, py, hz), (px, py, z + 0.4), 0.03, 0.03, n=3)
    else:                            # a walkway of planks across the pit
        for e in (-0.35, 0.35):
            p0 = (px - er[0] * R + et[0] * e, py - er[1] * R + et[1] * e)
            p1 = (px + er[0] * R + et[0] * e, py + er[1] * R + et[1] * e)
            blib.strut(b, 'timber', (p0[0], p0[1], z + 0.55), (p1[0], p1[1], z + 0.55), 0.09, 0.09, n=4)
        box(b, 'timber', px, py, z + 0.6, 2 * R, 0.9, 0.08, rz=math.degrees(a))


def hand_lines():
    """The White Hand on the banners [(x0, z0, x1, z1, w)]: palm, four fingers, thumb."""
    L = []
    for s in (-1, 1):
        cx = s * (GATE_HW + 1.7)
        zp = FZ + 5.0
        L.append((cx + 0.02, zp, cx + 0.02, zp + 0.55, 0.62))                 # the palm
        for k, (dx, ln) in enumerate(((-0.21, 0.5), (-0.07, 0.68), (0.07, 0.66), (0.21, 0.5))):
            L.append((cx + dx * 1.05, zp + 0.45, cx + dx * 1.15, zp + 0.45 + ln, 0.13))
        L.append((cx - 0.27, zp + 0.18, cx - 0.55, zp + 0.55, 0.13))          # the thumb
    return L


# ----------------------------------------------------------------------------------------------- Saruman
def saruman(b, x, y, z, H):
    """Saruman the White, facing -Y (the camera), after the user's painting: white robes with a mantle, long white
    hair falling over his shoulders and down his back, a long beard; his black staff in his right hand (to -X), its
    open claw round a white light; the palantir raised in his left hand."""
    s = H / 5.2

    def P(px, py, pz):
        return (x + px * s, y + py * s, z + pz * s)

    def R(rings):
        return [(x + cx * s, y + cy * s, z + cz * s, rx * s, ry * s, sh) for (cx, cy, cz, rx, ry, sh) in rings]

    folds = (lambda a: 1.0 + 0.07 * math.cos(9 * a) + 0.03 * math.cos(17 * a + 0.5))
    soft = (lambda a: 1.0 + 0.03 * math.cos(9 * a))
    # the robe, from the hem (pooling a little on the floor) to the neck
    loft(b, 'robe', R([(0, 0.05, 0.0, 1.02, 0.86, folds), (0, 0.04, 0.35, 0.98, 0.8, folds),
                       (0, 0.02, 1.3, 0.84, 0.64, folds), (0, 0.0, 2.3, 0.72, 0.52, folds),
                       (0, 0.0, 3.05, 0.68, 0.48, soft), (0, 0.0, 3.6, 0.74, 0.5, soft),
                       (0, 0.02, 3.95, 0.8, 0.48, None), (0, 0.04, 4.15, 0.62, 0.42, None),
                       (0, 0.03, 4.3, 0.3, 0.3, None)]), n=28)
    # the mantle over his shoulders, falling behind to the floor
    loft(b, 'robe', R([(0, 0.22, 0.02, 0.98, 0.7, folds), (0, 0.2, 1.4, 0.86, 0.6, folds),
                       (0, 0.14, 3.0, 0.82, 0.55, soft), (0, 0.1, 3.85, 0.86, 0.52, None),
                       (0, 0.08, 4.15, 0.6, 0.42, None)]), n=24)
    # frog clasps down his chest (the painting)
    for k, zz in enumerate((3.75, 3.4, 3.05, 2.7)):
        box(b, 'clasp', 0, 0, -0.04 * s, 0.22 * s, 0.06 * s, 0.09 * s, M=blib.T(*P(0.0, -0.53 if zz > 3.3 else -0.5, zz)))

    # --- the right arm (-X), down at his side, the hand on the staff
    staff_x, staff_y = -1.2, -0.5
    sh, el, wr = P(-0.72, 0.0, 3.92), P(-1.02, -0.18, 3.05), P(-1.18, -0.45, 2.75)
    tube(b, 'robe', spline([sh, el, wr], 8), [s * r for r in (0.3, 0.3, 0.3, 0.31, 0.33, 0.36, 0.4, 0.44, 0.46)],
         n=10, tip=False)
    blob(b, 'skin', *P(staff_x + 0.02, staff_y + 0.02, 2.55), 0.15 * s, n=8, rings=4, squash=1.3, jitter=0.0)
    # --- the left arm (+X), raised, the palantir in his hand
    sh, el, wr = P(0.72, 0.0, 3.92), P(1.18, -0.42, 4.05), P(1.3, -0.88, 4.6)
    tube(b, 'robe', spline([sh, el, wr], 8), [s * r for r in (0.3, 0.3, 0.29, 0.29, 0.3, 0.33, 0.37, 0.4, 0.42)],
         n=10, tip=False)
    # the wide sleeve hangs from the raised forearm
    loft(b, 'robe', R([(1.28, -0.7, 3.55, 0.12, 0.18, None), (1.26, -0.72, 3.95, 0.3, 0.33, None),
                       (1.25, -0.8, 4.45, 0.34, 0.36, None), (1.3, -0.88, 4.62, 0.2, 0.25, None)]), n=10)
    blob(b, 'skin', *P(1.33, -0.98, 4.66), 0.15 * s, n=8, rings=4, squash=1.0, jitter=0.0)
    blib.sphere(b, 'palantir', *P(1.36, -1.02, 5.05), 0.3 * s, n=14, rings=8)
    for k in range(3):                                                       # fingers round the stone
        c = math.radians(200 + 50 * k)
        tube(b, 'skin', [P(1.36 + 0.18 * math.cos(c), -1.02 + 0.12, 4.74),
                         P(1.36 + 0.29 * math.cos(c), -1.02 - 0.05, 4.92 + 0.04 * k)], [0.045 * s, 0.035 * s], n=5)

    # --- head, hair, beard
    loft(b, 'skin', R([(0, -0.02, 4.32, 0.2, 0.22, None), (0, -0.02, 4.5, 0.27, 0.3, None),
                       (0, 0.0, 4.75, 0.3, 0.32, None), (0, 0.02, 4.98, 0.29, 0.31, None),
                       (0, 0.03, 5.13, 0.2, 0.22, None), (0, 0.03, 5.2, 0.05, 0.05, None)]), n=14)
    box(b, 'skin', 0, 0, -0.06 * s, 0.09 * s, 0.14 * s, 0.22 * s, M=blib.T(*P(0.0, -0.32, 4.72)))       # nose
    box(b, 'hair', 0, 0, -0.025 * s, 0.4 * s, 0.08 * s, 0.05 * s, M=blib.T(*P(0.0, -0.29, 4.86)))       # brows
    # the hair: a mantle of it from the crown down his back, and two long locks over the shoulders
    loft(b, 'hair', R([(0, 0.32, 2.6, 0.5, 0.12, None), (0, 0.3, 3.3, 0.6, 0.16, None),
                       (0, 0.24, 4.05, 0.52, 0.22, None), (0, 0.12, 4.75, 0.36, 0.3, None),
                       (0, 0.04, 5.1, 0.33, 0.33, None), (0, 0.04, 5.27, 0.2, 0.22, None)]), n=16)
    for sd in (-1, 1):
        pts = spline([P(sd * 0.3, -0.05, 5.05), P(sd * 0.38, -0.1, 4.55), P(sd * 0.47, -0.22, 4.0),
                      P(sd * 0.45, -0.38, 3.45), P(sd * 0.4, -0.45, 3.0)], 12)
        tube(b, 'hair', pts, [s * (0.12 + 0.03 * math.sin(math.pi * i / (len(pts) - 1))) for i in range(len(pts))],
             n=8)
    # the beard, long and parted a little, falling to his belt
    beard = (lambda a: 1.0 + 0.08 * math.cos(7 * a))
    loft(b, 'hair', R([(0, -0.18, 4.52, 0.26, 0.15, beard), (0, -0.3, 4.38, 0.3, 0.15, beard),
                       (0, -0.42, 4.0, 0.28, 0.13, beard), (0, -0.5, 3.5, 0.22, 0.11, beard),
                       (0, -0.53, 3.0, 0.14, 0.08, beard), (0, -0.53, 2.65, 0.04, 0.03, None)])[::-1], n=14)
    for sd in (-1, 1):                                                       # the moustache
        tube(b, 'hair', [P(sd * 0.04, -0.33, 4.58), P(sd * 0.15, -0.34, 4.5), P(sd * 0.22, -0.35, 4.3)],
             [s * 0.05, s * 0.045, s * 0.03], n=5)

    # --- the staff: tall and black, its head an open claw round a white light
    top = 6.55
    cyl(b, 'staff', *P(staff_x, staff_y, 0.0), 0.075 * s, top * s, n=8)
    for zz in (2.95, 6.1):
        cyl(b, 'staff', *P(staff_x, staff_y, zz), 0.11 * s, 0.14 * s, n=8)
    oc = P(staff_x, staff_y, top + 0.42)
    blib.sphere(b, 'orb', *oc, 0.17 * s, n=10, rings=6)
    for k in range(5):
        c = math.radians(90 + 72 * k)
        pts = [P(staff_x + 0.05 * math.cos(c), staff_y + 0.05 * math.sin(c), top),
               P(staff_x + 0.24 * math.cos(c), staff_y + 0.24 * math.sin(c), top + 0.25),
               P(staff_x + 0.27 * math.cos(c), staff_y + 0.27 * math.sin(c), top + 0.6),
               P(staff_x + 0.14 * math.cos(c), staff_y + 0.14 * math.sin(c), top + 0.98)]
        tube(b, 'staff', spline(pts, 8), [s * r for r in (0.05, 0.05, 0.048, 0.044, 0.04, 0.035, 0.03, 0.024, 0.018)],
             n=5)


def staff_tip():
    s = SAR_H / 5.2
    return (SAR[0] - 1.2 * s, SAR[1] - 0.5 * s, Z_TOP + 0.25 + (6.55 + 0.42) * s)


def palantir_c():
    s = SAR_H / 5.2
    return (SAR[0] + 1.36 * s, SAR[1] - 1.02 * s, Z_TOP + 0.25 + 5.05 * s)


def glow_frame():
    """(bone position, quad box (X0, X1, Z0, Z1) in in-game units): one quad in front of the staff and the stone."""
    (tx, ty, tz), (px, py, pz) = staff_tip(), palantir_c()
    bx = (tx - GLOW_R, px + GLOW_R, min(tz, pz) - GLOW_R, max(tz, pz) + GLOW_R)
    pos = ((bx[0] + bx[1]) / 2, min(ty, py) - 0.6, (bx[2] + bx[3]) / 2)
    return pos, bx


# ----------------------------------------------------------------------------------------------- rig
def fire_spots():
    pits = pit_list()
    spots = [(pits[i][0], pits[i][1], FZ - 0.55) for i in FIRE_PITS]
    return spots


def rig():
    """Bones in in-game units: (name, parent, position, effect key or None)."""
    bones = [('fxglow', 'eyeroot', glow_frame()[0], 'STAFF_GLOW')]
    for i, p in enumerate(fire_spots()):
        bones.append(('fire%d' % i, 'eyeroot', p, 'TOWER_FIRE'))
    return bones


GLOW_R = 2.0


def glow_effect(k):
    """The white light of the staff and the orange fire of the palantir (tools/landmarks/glow.py): one quad in FILE
    units round the fxglow bone, each light in its own colour."""
    s = SAR_H / 5.2
    (pos, box_), (tx, _, tz), (px, _, pz) = glow_frame(), staff_tip(), palantir_c()
    X0, X1, Z0_, Z1 = box_
    return dict(name='MEC_OrthancGlow',
                quads=[((X0 - pos[0]) * k, (X1 - pos[0]) * k, (Z0_ - pos[2]) * k, (Z1 - pos[2]) * k, 0.0)],
                tex_args=dict(lines=[(tx, tz - 0.02, tx, tz + 0.02, 0.3 * s, (226, 234, 255)),
                                     (px, pz - 0.02, px, pz + 0.02, 0.5 * s, (255, 140, 40))],
                              box=box_, px=1024, color=(226, 234, 255), halo=0.8, sigma=(0.3, 0.9)))


def _still(t):
    return 0.0


GAZE = dict(fn=_still, T=6.0, spans=60)
EYE_C = (SAR[0], SAR[1], Z_TOP)    # pivot of the skinned part (nothing turns about it)

PREVIEW = [((0, -100, 85), (0, 4, 22), 34),                                       # the game's view
           ((6, -20, 62), (0, -1.0, 55.0), 34),                                   # Saruman on the summit
           ((-58, -52, 46), (0, 0, 26), 32),                                      # from the south-west
           ((12, -46, 14), (0, -14, 6), 40)]                                      # the gate and the plain
PREVIEW_EYE = [((3.5, -14.0, 58.0), (0, -1.5, 54.5), 36)]
