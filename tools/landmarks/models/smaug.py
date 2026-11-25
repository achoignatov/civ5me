"""Smaug's Lair: the landmark of the city-state of Smaug's Lair (an IMPROVEMENT, docs/LANDMARKS.md). 2026-11-25.

The user: "a huge pile of golden coins, some of the coin piles covering adjacent tiles; on the top a sleeping dragon;
dragon scales on its model, coins and treasures on the pile; big and impressive". First the detailed model; subtle
animations later.

Look: The Hobbit (Smaug "a vast red-golden dragon", asleep on the hoard of Erebor, the belly crusted with gems) and the
film The Desolation of Smaug (Weta: a wyvern, the wings his forelimbs with a thumb and fingers; hard tortoise-like
scales on the back, smaller snake-like scales on the belly; cracked, scarred scales).

In-game units (improvement Scale 0.25, the writer's x4), origin = the city's tile centre, ground z = 0, -Y = south =
towards the game camera. THE FIRST LANDMARK THAT USES THE NEIGHBOURING TILES: the hoard spills into the six hexes
round it (lobes fading into their ground, loose coins on it), so its envelope is about 2.3 hexes wide.

Techniques (new, bake.py): PAINTED RELIEF (treasure.py): the gold is a painted heap of coins mapped from above, the
hide a painted sheet of scales in BODY COORDINATES (b.param_uv: u along the body in rows of scales, v round it), both
with a height map baked as relief lighting (bump -> object-space normals, compared with the unbumped ones) and darker
hollows; real coins, treasure, horns, spikes, wings on top.

Parts: static = the spills outside the city's own hex; ONE skinned model of six meshes, all on the still bone for
now (animation later): the main pile, the treasure, loose coins, Smaug's body (neck, body, tail), his head (horns,
teeth), his limbs (wings, legs, claws, dorsal spikes).
"""
import math
import random

from mathutils import Matrix, Vector

import blib
import treasure
from blib import material, hexcol as h, blob, lathe, cyl
from moria_v4 import fbm, tube, smooth, _spline as spline
from erebor import hex_dist
from treebeard import ellipsoid, ring_grid, keyed, g, resample, frames, thick_sheet, Local

BAKE = True
BAKE_PX = 2048
EYE_AO = 16
HEX = 33.6
LOOP = 10.0
SPANS = 10

ROWS, NV = 8, 32                     # the scale sheet: rows per tile along the body, scales round it
LIMB_V = (0.04, 0.36)                # limbs use the spine-to-flank part of the sheet (no belly plates)

# --------------------------------------------------------------------------- the hoard
# piles: (x, y, rx, ry, height); the first is the main heap on the city's own hex, the rest spill into the neighbours
PILES = [(0.0, 3.0, 40.0, 35.0, 24.0), (-11.0, 9.0, 17.0, 14.0, 9.0), (13.0, 11.0, 16.0, 14.0, 8.0),
         (2.0, -13.0, 16.0, 11.0, 6.0), (-4.0, 18.0, 15.0, 12.0, 7.0), (0.0, 6.0, 66.0, 62.0, 3.2),     # the heap; a low floor of gold under all (-15.0, 15.0, 14.0, 12.0, 7.0), (17.0, 17.0, 13.0, 12.0, 6.0),
         # flows of gold out of the heap into the neighbouring hexes: chains of overlapping lobes, lower outwards
         (-30.0, 6.0, 20.0, 17.0, 9.0), (-48.0, 2.0, 18.0, 15.0, 6.5), (-62.0, 9.0, 12.0, 10.0, 3.5),
         (-20.0, 32.0, 17.0, 14.0, 8.0), (-33.0, 48.0, 15.0, 13.0, 5.5),
         (20.0, 33.0, 18.0, 15.0, 9.0), (32.0, 50.0, 17.0, 14.0, 6.5), (44.0, 62.0, 10.0, 9.0, 3.0),
         (34.0, 4.0, 18.0, 16.0, 8.0), (52.0, -2.0, 17.0, 15.0, 6.0), (63.0, 10.0, 10.0, 9.0, 3.0),
         (18.0, -34.0, 15.0, 11.0, 4.5), (28.0, -48.0, 10.0, 8.0, 2.5),
         (-20.0, -33.0, 15.0, 12.0, 5.0), (-30.0, -47.0, 11.0, 9.0, 3.0)]
REACH = 76.0                          # nothing beyond this (in-game units from the centre, hexagon measure)


def _dome(x, y, p):
    cx, cy, rx, ry, hh = p
    a = math.atan2(y - cy, x - cx)
    wob = 1.0 + 0.22 * fbm(math.cos(a) * 1.3 + cx * 0.05, math.sin(a) * 1.3 + cy * 0.05, 3, 53)   # ragged outlines
    r2 = (((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2) / (wob * wob)
    return hh * max(0.0, 1.0 - r2) ** 1.5


def height(x, y):
    hs = [_dome(x, y, p) for p in PILES]
    m = max(hs)
    H = m + 0.18 * (sum(hs) - m)
    H += (0.9 * fbm(x * 0.09, y * 0.09, 4, 51) + 0.35 * fbm(x * 0.35, y * 0.35, 2, 52)) * min(1.0, H / 3.0)
    return H - 0.35


def hex_measure(x, y):
    return max(abs(x * math.cos(math.radians(60 * k)) + y * math.sin(math.radians(60 * k))) for k in range(3))


def in_own_hex(x, y):
    return hex_dist(x, y) > 0.0


# --------------------------------------------------------------------------- Smaug's spine (from the head to the tail)
SPINE_XY = [(-8.0, -17.0), (-17.0, -12.0), (-22.0, -2.0), (-19.0, 9.0), (-9.0, 14.0), (3.0, 15.0), (14.0, 12.0),
            (24.0, 18.0), (34.0, 20.0), (43.0, 11.0), (45.0, -1.0), (40.0, -11.0), (32.0, -15.0), (27.0, -11.0)]
SECT = [(0.0, 4.0, 4.1), (18.0, 5.7, 5.6), (40.0, 8.6, 7.9), (58.0, 11.4, 9.8), (78.0, 12.2, 10.2), (96.0, 10.4, 9.0),
        (112.0, 8.0, 7.0), (140.0, 5.2, 4.6), (175.0, 3.0, 2.8), (205.0, 1.5, 1.4), (222.0, 0.4, 0.4)]
SINK = 0.5                           # how deep he lies in the coins (fraction of his height below the spine)
_SPINE = {}


def spine():
    """[(point, tangent, side, up, s)] along the spine every ~0.6 units; the head end first."""
    if _SPINE:
        return _SPINE['pts']
    P = [Vector((x, y, 0.0)) for x, y in SPINE_XY]
    P = resample([tuple(p) for p in P], 0.3)
    L = [0.0]
    for a, b_ in zip(P, P[1:]):
        L.append(L[-1] + (b_ - a).length)
    total = L[-1]
    k = SECT[-1][0] / total
    out = []
    step = 0.42
    s, i = 0.0, 0
    while s <= total:
        while i < len(L) - 2 and L[i + 1] < s:
            i += 1
        t = (s - L[i]) / max(1e-6, L[i + 1] - L[i])
        p = P[i].lerp(P[i + 1], t)
        sn = s * k
        rw, rh = keyed(SECT, sn)
        p.z = max(height(p.x, p.y), 0.0) + rh * SINK
        out.append((p, sn))
        s += step
    pts = []
    for j, (p, sn) in enumerate(out):
        a, c = out[max(0, j - 2)][0], out[min(len(out) - 1, j + 2)][0]
        t = (c - a).normalized()
        side = t.cross(Vector((0.0, 0.0, 1.0))).normalized()
        up = side.cross(t).normalized()
        pts.append((p, t, side, up, sn))
    _SPINE['pts'] = pts
    return pts


def at_s(sn):
    pts = spine()
    best = min(pts, key=lambda q: abs(q[4] - sn))
    return best


def section(th, sn):
    """(lateral, vertical) of the body's cross-section at angle th (0 = the spine's top, pi = the belly): rounder
    above, flatter below (he lies on his belly), a ridge along the spine."""
    rw, rh = keyed(SECT, sn)
    c, s_ = math.cos(th), math.sin(th)
    z = rh * (abs(c) ** 0.85) * (1 if c >= 0 else -0.72)
    y = rw * math.copysign(abs(s_) ** 0.85, s_)
    ridge = 0.12 * rh * math.exp(-(th if th < math.pi else 2 * math.pi - th) ** 2 / 0.03)
    return y, z + ridge


def loft_param(b, mat, rows, frames_, nv_scales=NV, closed_top=None, v0=0.0, v1=1.0):
    """A lofted tube (rows of ring points, the ring starting at the top and going round) with body coordinates for
    the painted scales: u grows by one scale row per (perimeter / nv) of length, v = angle / 2pi."""
    n = len(rows[0])
    verts = [tuple(p) for row in rows for p in row]
    faces, uvs = [], []
    us = [0.0]
    for i in range(1, len(rows)):
        per = sum((Vector(rows[i][j]) - Vector(rows[i][(j + 1) % n])).length for j in range(n))
        ds = (Vector(frames_[i]) - Vector(frames_[i - 1])).length
        us.append(us[-1] + ds / max(1e-3, per / (nv_scales * (v1 - v0))) / ROWS)
    # winding: outwards
    c0, r0 = Vector(frames_[0]), rows
    test = (Vector(r0[1][1]) - Vector(r0[0][0])).cross(Vector(r0[0][1]) - Vector(r0[0][0]))
    out = (Vector(r0[0][0]) - c0)
    flip = test.dot(out) > 0
    base = len(b.faces)
    for i in range(len(rows) - 1):
        for j in range(n):
            a, b_ = i * n + j, i * n + (j + 1) % n
            f = (a, b_, b_ + n, a + n)
            va, vb = v0 + (v1 - v0) * j / n, v0 + (v1 - v0) * (j + 1) / n
            uv = [(us[i], va), (us[i], vb), (us[i + 1], vb), (us[i + 1], va)]
            if flip:
                f, uv = f[::-1], uv[::-1]
            faces.append(f)
            uvs.append(uv)
    b.add(verts, faces, mat, smooth=True)
    bb = b.b if isinstance(b, Local) else b                 # the builder itself (not a placing proxy)
    if not hasattr(bb, 'param_uv'):
        bb.param_uv = {}
    for k, uv in enumerate(uvs):
        bb.param_uv[base + k] = uv
    return us


def ptube(b, mat, pts, radii, n=12):
    """A tube with body coordinates (painted scales that follow it; closed ends with small caps)."""
    P = [Vector(p) for p in pts]
    F = frames(P)
    rows = []
    for p, (t, a, c), r in zip(P, F, radii):
        rows.append([tuple(p + r * (math.cos(2 * math.pi * j / n) * c + math.sin(2 * math.pi * j / n) * a))
                     for j in range(n)])
    loft_param(b, mat, rows, [tuple(p) for p in P], v0=LIMB_V[0], v1=LIMB_V[1])
    for end, d in ((P[-1], (P[-1] - P[-2]).normalized()), (P[0], (P[0] - P[1]).normalized())):
        r = radii[-1] if end is P[-1] else radii[0]
        tube(b, 'scalecap', [tuple(end - d * 0.01), tuple(end + d * r * 0.6)], [r, r * 0.3], n=n, tip=True)


def psphere(b, mat, c, radii, n=14, rings=9):
    """An ellipsoid with body coordinates (a loft of rings along its z axis)."""
    C = Vector(c)
    rows, cents = [], []
    for i in range(1, rings):
        a = math.pi * i / rings - math.pi / 2
        z = math.sin(a) * radii[2]
        k = math.cos(a)
        rows.append([tuple(C + Vector((radii[0] * k * math.cos(2 * math.pi * j / n),
                                       radii[1] * k * math.sin(2 * math.pi * j / n), z))) for j in range(n)])
        cents.append(tuple(C + Vector((0, 0, z))))
    loft_param(b, mat, rows, cents, v0=LIMB_V[0], v1=LIMB_V[1])
    for row, zc, sgn in ((rows[-1], C.z + radii[2], 1), (rows[0], C.z - radii[2], -1)):
        verts = [tuple(p) for p in row] + [(C.x, C.y, zc)]
        faces = [(j, (j + 1) % n, n) if sgn > 0 else ((j + 1) % n, j, n) for j in range(n)]
        b.add(verts, faces, mat, smooth=True)


# --------------------------------------------------------------------------- materials
def gold_palette():
    hh, alb = _tex('coins', lambda: treasure.coin_heap(7, px=2048, period=10.0))
    material('gold', h('c9993a'), h('b5862e'), spec=0.85, refl=170)
    blib.PALETTE['gold'].update(heightimg=dict(key='coins', height=hh, albedo=alb, map='top', period=10.0, bump=0.12,
                                               cavity=0.5), scale=0.2, ao=True)


def scale_palette():
    hh, alb = _tex('scales', lambda: treasure.dragon_scales(11, rows=ROWS, nv=NV))
    material('scales', h('7a2414'), h('6a1e10'), spec=0.5, refl=70)
    blib.PALETTE['scales'].update(heightimg=dict(key='scales', height=hh, albedo=alb, map='param', bump=0.09,
                                                 cavity=0.55))
    material('horn', h('3e3329'), h('2e261f'), spec=0.45, refl=50)
    blib.PALETTE['horn'].update(scale=3.0, vcracks=(4.0, 0.35), cavity=0.8)
    material('claw', h('2b241e'), h('221c17'), spec=0.7, refl=110)
    blib.PALETTE['claw'].update(scale=4.0, cavity=0.6)
    material('teeth', h('d8cdb0'), h('c4b896'), spec=0.6, refl=60)
    blib.PALETTE['teeth'].update(scale=6.0, cavity=0.5)
    material('membrane', h('4d1a10'), h('3b140c'), spec=0.35, refl=30)
    blib.PALETTE['membrane'].update(scale=1.4, vcracks=(1.6, 0.4), cavity=0.7,
                                    speckle=[(0.6, 0.25, h('5e2414')), (2.0, 0.1, h('2a0d08'))])
    material('scalecap', h('5e1a0e'), h('521609'), spec=0.5, refl=70)     # tube ends (no body coordinates)
    blib.PALETTE['scalecap'].update(scale=3.0, cavity=0.6)
    material('nostril', h('1e0d08'))
    blib.PALETTE['nostril'].update(solid=True)


def treasure_palette():
    gold_palette()
    material('goldp', h('d9ac48'), h('c99a38'), spec=0.95, refl=220)        # polished gold: cups, crowns
    blib.PALETTE['goldp'].update(scale=3.0, cavity=0.7)
    material('goldd', h('a87a2a'), h('94691f'), spec=0.85, refl=170)       # darker, worked gold
    blib.PALETTE['goldd'].update(scale=4.0, cavity=0.8)
    material('silver', h('bcc0c4'), h('a9adb2'), spec=0.95, refl=210)
    blib.PALETTE['silver'].update(scale=3.0, cavity=0.6)
    material('steel', h('9aa0a8'), h('878d95'), spec=0.9, refl=190)
    blib.PALETTE['steel'].update(scale=6.0, vcracks=(3.0, 0.15), cavity=0.5)
    material('wood', h('4c3626'), h('3e2c1f'))
    blib.PALETTE['wood'].update(scale=2.0, vcracks=(2.5, 0.4), cavity=0.7)
    material('iron', h('35363a'), h('2b2c30'), spec=0.5, refl=60)
    blib.PALETTE['iron'].update(scale=4.0, cavity=0.7)
    material('leather', h('4a3121'), h('3d2819'))
    blib.PALETTE['leather'].update(scale=5.0, cavity=0.6)
    for nm, c in (('gemR', '9a1022'), ('gemG', '157a3c'), ('gemB', '1c3c9c'), ('gemP', '6a2a8a')):
        material(nm, h(c), spec=1.0, refl=255, ao=False)
        blib.PALETTE[nm].update(solid=True)
    material('arken', h('eef4ff'), spec=1.0, refl=255, ao=False)           # the Arkenstone
    blib.PALETTE['arken'].update(solid=True)


def coin_palette():
    for nm, c1, c2 in (('coin1', 'd8aa48', 'c99a3c'), ('coin2', 'c39234', 'b0822a'), ('coin3', 'e6bd5c', 'd6ad4e')):
        material(nm, h(c1), h(c2), spec=0.95, refl=210)
        blib.PALETTE[nm].update(scale=8.0, cavity=0.5)
    material('coinS', h('c2c4c6'), h('b0b2b4'), spec=0.95, refl=200)
    blib.PALETTE['coinS'].update(scale=8.0, cavity=0.5)


_TEX = {}


def _tex(key, make):
    if key not in _TEX:
        _TEX[key] = make()
    return _TEX[key]


# --------------------------------------------------------------------------- the gold (static = spills; mesh = main heap)
GRID = dict(x0=-REACH - 6, x1=REACH + 6, y0=-REACH / 0.866 - 4, y1=REACH / 0.866 + 4)


def _terrain(b, keep, step=1.15):
    nx = int((GRID['x1'] - GRID['x0']) / step)
    ny = int((GRID['y1'] - GRID['y0']) / step)
    blib.SKIRT_MAT[0] = 'gold'
    blib.terrain(b, height, GRID['x0'], GRID['x1'], GRID['y0'], GRID['y1'], nx, ny, lambda x, y, z, s: 'gold',
                 keep=keep, smooth=True, skirt=-1.0)


def scatter_coins(b, rng, n, region):
    """Loose coins: lying on the pile (tilted with it, half sunk), sliding down its edges and on the bare ground."""
    placed = 0
    while placed < n:
        x, y = rng.uniform(-REACH, REACH), rng.uniform(-REACH / 0.866, REACH / 0.866)
        if hex_measure(x, y) > REACH - 2 or not region(x, y):
            continue
        z = height(x, y)
        if z < -0.2 and rng.random() < 0.6:
            continue
        if z > 1.0 and rng.random() < 0.5:
            continue
        r = rng.uniform(0.5, 0.78)
        zz = max(z, 0.0)
        e = 0.6
        gx = (height(x + e, y) - height(x - e, y)) / (2 * e) if z > 0 else 0.0
        gy = (height(x, y + e) - height(x, y - e)) / (2 * e) if z > 0 else 0.0
        nrm = Vector((-gx, -gy, 1.0)).normalized()
        tilt = Vector((rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), 0.0))
        nrm = (nrm + tilt * (0.6 if rng.random() < 0.8 else 2.5)).normalized()
        R = nrm.to_track_quat('Z', 'X').to_matrix().to_4x4() @ Matrix.Rotation(rng.uniform(0, 6.3), 4, 'Z')
        M = Matrix.Translation((x, y, zz - 0.06)) @ R
        m = 'coinS' if rng.random() < 0.06 else rng.choice(('coin1', 'coin2', 'coin3'))
        lathe(b, m, [(0.0, 0.0), (r, 0.0), (r, 0.1), (r * 0.82, 0.13), (0.0, 0.13)], 7, M=M, smooth=True)
        placed += 1


STATIC_PX = 2048
DRAGON = False                       # v3 (2026-11-26): the gold alone, as ONE static mesh (the dragon comes later)


def build(b, eye=False):
    """v3: THE WHOLE HOARD AS ONE STATIC MESH (the proven path; the skinned model drew nothing in two in-game tests):
    the central heap and the spills into the six neighbours are one height field, one coin texture, no seam; loose
    coins; treasure on the heap."""
    treasure_palette()
    coin_palette()
    b.tiny_px = 10
    b.ao_distance = 6.0
    b.emboss = dict(k=1.2)
    _terrain(b, lambda x, y: height(x, y) > -0.05 and hex_measure(x, y) < REACH, step=STEP)
    scatter_coins(b, random.Random(301), N_COINS, lambda x, y: True)
    build_treasure(b, n=N_TREASURE)


STEP, N_COINS, N_TREASURE = 0.92, 120, 26


def build_pile(b):
    """Mesh 1: the main heap on the city's own hex (its own texture: the coins at twice the density)."""
    gold_palette()
    coin_palette()
    b.tiny_px = 0
    b.ao_distance = 6.0
    b.emboss = dict(k=1.2)
    _terrain(b, lambda x, y: in_own_hex(x, y) and height(x, y) > -0.05, step=0.68)
    scatter_coins(b, random.Random(302), 330, lambda x, y: True)


def build_coins(b):
    """Mesh 6: loose coins everywhere (their own small texture)."""
    coin_palette()
    b.tiny_px = 0
    b.ao_distance = 1.0
    scatter_coins(b, random.Random(303), 640, lambda x, y: True)


# --------------------------------------------------------------------------- treasure (mesh 2)
def place(x, y, sink=0.3, tilt=0.25, rng=None, yaw=None):
    """A matrix standing a prop on the pile at (x, y): leaning with the slope, a little random, partly buried."""
    z = max(height(x, y), 0.0)
    e = 0.8
    gx = (height(x + e, y) - height(x - e, y)) / (2 * e)
    gy = (height(x, y + e) - height(x, y - e)) / (2 * e)
    nrm = Vector((-gx, -gy, 1.0)).normalized()
    nrm = (nrm + Vector((rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt), 0.0))).normalized()
    R = nrm.to_track_quat('Z', 'X').to_matrix().to_4x4() @ \
        Matrix.Rotation(yaw if yaw is not None else rng.uniform(0, 6.3), 4, 'Z')
    return Matrix.Translation((x, y, z - sink)) @ R


def goblet(b, mat, M, s=1.0):
    lathe(b, mat, [(0.0, 0.0), (0.9 * s, 0.0), (0.9 * s, 0.12 * s), (0.3 * s, 0.3 * s), (0.16 * s, 0.6 * s),
                   (0.28 * s, 0.8 * s), (0.16 * s, 1.0 * s), (0.2 * s, 1.15 * s), (0.75 * s, 1.5 * s),
                   (0.95 * s, 2.2 * s), (0.88 * s, 2.25 * s), (0.7 * s, 1.7 * s), (0.0, 1.6 * s)], 16, M=M)
    for k in range(4):                                       # gems round the cup
        a = 2 * math.pi * k / 4
        ellipsoid(b, ('gemR', 'gemG', 'gemB', 'gemP')[k], tuple(M @ Vector((0.86 * s * math.cos(a),
                                                                             0.86 * s * math.sin(a), 1.75 * s))),
                  (0.13 * s, 0.13 * s, 0.13 * s), n=6, rings=4)


def crown(b, M, s=1.0, rng=None):
    for zc in (0.08, 0.38):                                   # the band: two rolled rims and a plate between
        ring_pts = [tuple(M @ Vector((1.0 * s * math.cos(a), 1.0 * s * math.sin(a), zc * s)))
                    for a in [2 * math.pi * i / 24 for i in range(25)]]
        tube(b, 'goldp', ring_pts, [0.09 * s] * 25, n=6, tip=False)
    band = [[tuple(M @ Vector((1.0 * s * math.cos(a), 1.0 * s * math.sin(a), z * s)))
             for a in [2 * math.pi * i / 24 for i in range(24)]] for z in (0.08, 0.38)]
    thick_sheet(b, 'goldp', band, 0.05 * s)
    for k in range(8):
        a = 2 * math.pi * k / 8
        p = Vector((1.03 * s * math.cos(a), 1.03 * s * math.sin(a), 0.4 * s))
        tube(b, 'goldp', [tuple(M @ p), tuple(M @ (p + Vector((0, 0, 0.45 * s)))),
                          tuple(M @ (p + Vector((0, 0, 0.7 * s))))], [0.12 * s, 0.07 * s, 0.03 * s], n=5, tip=True)
        ellipsoid(b, ('gemR', 'gemG', 'gemB')[k % 3], tuple(M @ Vector((1.1 * s * math.cos(a + 0.39),
                                                                           1.1 * s * math.sin(a + 0.39), 0.22 * s))),
                  (0.1 * s, 0.1 * s, 0.1 * s), n=6, rings=4)


def sword(b, M, s=1.0, gem='gemR'):
    """Stuck point-down in the gold: blade (fuller), crossguard, grip, pommel."""
    blade = [(0.0, 0.0, -3.5 * s), (0.0, 0.0, 3.0 * s)]
    v = []
    for z, w in ((-3.5 * s, 0.0), (-3.0 * s, 0.22 * s), (2.9 * s, 0.26 * s)):
        v += [(-w, 0.0, z), (0.0, -0.05 * s, z), (w, 0.0, z), (0.0, 0.05 * s, z)]
    f = []
    for i in range(2):
        for j in range(4):
            a, c = i * 4 + j, i * 4 + (j + 1) % 4
            f.append((a, c, c + 4, a + 4))
    f.append((8, 9, 10, 11))
    b.add(v, f, 'steel', smooth=False, M=M)
    blib.box(Local(b, M), 'goldd', 0.0, 0.0, 3.0 * s, 1.6 * s, 0.22 * s, 0.22 * s)
    cyl(b, 'leather', 0.0, 0.0, 3.2 * s, 0.11 * s, 1.0 * s, n=8, M=M)
    ellipsoid(b, gem, tuple(M @ Vector((0.0, 0.0, 4.35 * s))), (0.2 * s, 0.2 * s, 0.2 * s), n=8, rings=5)


def shield(b, M, s=1.0, mat='goldd', boss='goldp'):
    lathe(b, mat, [(0.0, -0.1 * s), (1.75 * s, -0.12 * s), (1.75 * s, 0.0), (1.6 * s, 0.05 * s), (0.0, 0.25 * s)], 24,
          M=M)
    lathe(b, boss, [(0.0, 0.2 * s), (0.5 * s, 0.22 * s), (0.4 * s, 0.35 * s), (0.0, 0.55 * s)], 12, M=M)
    for k in range(12):                                     # rivets on the rim
        a = 2 * math.pi * k / 12
        ellipsoid(b, boss, tuple(M @ Vector((1.5 * s * math.cos(a), 1.5 * s * math.sin(a), 0.1 * s))),
                  (0.09 * s, 0.09 * s, 0.06 * s), n=5, rings=3)


def helm(b, M, s=1.0):
    lathe(b, 'goldd', [(1.0 * s, 0.0), (1.05 * s, 0.05 * s), (1.0 * s, 0.7 * s), (0.8 * s, 1.15 * s),
                       (0.4 * s, 1.4 * s), (0.0, 1.45 * s)], 18, M=M)
    blib.box(Local(b, M), 'goldp', 0.0, -1.0 * s, 0.2 * s, 0.2 * s, 0.12 * s, 1.1 * s)          # nasal
    ellipsoid(b, 'gemB', tuple(M @ Vector((0.0, -0.95 * s, 1.0 * s))), (0.14 * s, 0.08 * s, 0.14 * s), n=6, rings=4)


def chest(b, M, s=1.0, rng=None):
    L = Local(b, M)
    blib.box(L, 'wood', 0.0, 0.0, 0.0, 3.0 * s, 2.0 * s, 1.6 * s)
    for x in (-1.2, 0.0, 1.2):                              # iron bands
        blib.box(L, 'iron', x * s, 0.0, -0.02, 0.18 * s, 2.06 * s, 1.66 * s)
    # the open lid, leaning back
    Ml = M @ Matrix.Translation((0.0, 1.0 * s, 1.6 * s)) @ Matrix.Rotation(math.radians(-105), 4, 'X')
    blib.box(Local(b, Ml), 'wood', 0.0, -1.0 * s, 0.0, 3.0 * s, 2.0 * s, 0.25 * s, bottom=True)
    lathe(b, 'gold', [(0.0, 1.5 * s), (1.4 * s, 1.5 * s), (0.9 * s, 1.68 * s), (0.0, 1.75 * s)], 14,
          M=M @ Matrix.Diagonal((1.0, 0.65, 1.0, 1.0)))   # heaped with coins
    for k in range(5):
        ellipsoid(b, ('gemR', 'gemG', 'gemB', 'gemP', 'gemR')[k],
                  tuple(M @ Vector((rng.uniform(-1.0, 1.0) * s, rng.uniform(-0.5, 0.5) * s, 1.75 * s))),
                  (0.18 * s, 0.18 * s, 0.15 * s), n=6, rings=4)


def gem_cluster(b, rng, M, s=1.0):
    for k in range(rng.randint(3, 6)):
        m = rng.choice(('gemR', 'gemG', 'gemB', 'gemP'))
        p = M @ Vector((rng.uniform(-0.6, 0.6) * s, rng.uniform(-0.6, 0.6) * s, rng.uniform(0.0, 0.3) * s))
        r = rng.uniform(0.2, 0.42) * s
        ellipsoid(b, m, tuple(p), (r, r, r * 1.2), n=6, rings=3)


def plate(b, M, s=1.0, mat='silver'):
    lathe(b, mat, [(0.0, 0.0), (1.2 * s, 0.0), (1.4 * s, 0.18 * s), (1.32 * s, 0.2 * s), (1.1 * s, 0.06 * s),
                   (0.0, 0.06 * s)], 20, M=M)


def candlestick(b, M, s=1.0):
    lathe(b, 'goldp', [(0.0, 0.0), (0.6 * s, 0.0), (0.55 * s, 0.15 * s), (0.15 * s, 0.4 * s), (0.12 * s, 2.0 * s),
                       (0.25 * s, 2.2 * s), (0.35 * s, 2.4 * s), (0.0, 2.4 * s)], 12, M=M)


def necklace(b, rng, x0, y0, n=14):
    """A string of gold beads with a pendant gem, lying on the pile."""
    a = rng.uniform(0, 6.3)
    pts = []
    for k in range(n):
        t = k / (n - 1)
        x = x0 + 1.6 * math.cos(a + t * 3.6)
        y = y0 + 1.1 * math.sin(a + t * 3.6) + 0.6 * t
        pts.append((x, y, max(height(x, y), 0.0) + 0.05))
    for p in pts:
        ellipsoid(b, 'goldp', p, (0.11, 0.11, 0.11), n=6, rings=3)
    mid = pts[n // 2]
    ellipsoid(b, rng.choice(('gemR', 'gemG', 'gemB')), (mid[0], mid[1], mid[2] + 0.05), (0.3, 0.22, 0.12), n=8,
              rings=4)


def clear_of_dragon(x, y, margin=1.5):
    for p, t, side, up, sn in spine()[::3]:
        rw, rh = keyed(SECT, sn)
        if math.hypot(x - p.x, y - p.y) < rw + margin:
            return False
    return True


def build_treasure(b, n=95):
    if n == 95:                                              # as its own mesh (the dragon version)
        treasure_palette()
        b.tiny_px = 10
        b.ao_distance = 3.0
        b.emboss = dict(k=1.2)
    rng = random.Random(1937)
    spots = []
    tries = 0
    while len(spots) < n and tries < 20000:
        tries += 1
        x, y = rng.uniform(-62, 62), rng.uniform(-62, 62)
        if hex_measure(x, y) > REACH - 6 or height(x, y) < 1.2 or (DRAGON and not clear_of_dragon(x, y, 2.5)):
            continue
        if any(math.hypot(x - a, y - c) < 4.2 for a, c, _ in spots):
            continue
        spots.append((x, y, rng.random()))
    kinds = ['goblet'] * 16 + ['sword'] * 10 + ['shield'] * 10 + ['crown'] * 7 + ['helm'] * 7 + ['chest'] * 6 + \
        ['gems'] * 14 + ['plate'] * 8 + ['candle'] * 5 + ['necklace'] * 9 + ['goblet2'] * 3
    rng.shuffle(kinds)
    for (x, y, _), kind in zip(spots, kinds):
        s = rng.uniform(0.9, 1.25)
        if kind == 'goblet':
            goblet(b, rng.choice(('goldp', 'goldp', 'silver')), place(x, y, 0.5, 0.45, rng), s)
        elif kind == 'goblet2':                              # tipped over
            goblet(b, 'goldp', place(x, y, 0.2, 0.2, rng) @ Matrix.Translation((0, 0, 0.9)) @
                   Matrix.Rotation(math.radians(80), 4, 'X'), s)
        elif kind == 'sword':
            M = place(x, y, 0.0, 0.0, rng) @ Matrix.Rotation(math.radians(rng.uniform(8, 30)), 4, 'X')
            sword(b, M, s * 1.1, rng.choice(('gemR', 'gemB', 'gemG')))
        elif kind == 'shield':
            M = place(x, y, 0.4, 0.2, rng) @ Matrix.Rotation(math.radians(rng.uniform(25, 75)), 4, 'X')
            shield(b, M, s, rng.choice(('goldd', 'silver', 'goldd')))
        elif kind == 'crown':
            crown(b, place(x, y, 0.15, 0.35, rng), s, rng)
        elif kind == 'helm':
            helm(b, place(x, y, 0.4, 0.5, rng), s)
        elif kind == 'chest':
            chest(b, place(x, y, 0.5, 0.12, rng, yaw=rng.uniform(-0.7, 0.7)), s, rng)
        elif kind == 'gems':
            gem_cluster(b, rng, place(x, y, 0.15, 0.2, rng), s)
        elif kind == 'plate':
            M = place(x, y, 0.3, 0.2, rng) @ Matrix.Rotation(math.radians(rng.uniform(0, 70)), 4, 'X')
            plate(b, M, s, rng.choice(('silver', 'goldp')))
        elif kind == 'candle':
            candlestick(b, place(x, y, 0.3, 0.6, rng), s)
        elif kind == 'necklace':
            necklace(b, rng, x, y)
    # the Arkenstone, the Heart of the Mountain, half buried below the dragon's head
    x, y = 4.0, -27.0
    M = place(x, y, 0.2, 0.1, rng)
    ellipsoid(b, 'arken', tuple(M @ Vector((0.0, 0.0, 0.7))), (0.75, 0.75, 0.9), n=8, rings=5)


# --------------------------------------------------------------------------- Smaug: the body (mesh 4)
def build_body(b):
    scale_palette()
    b.tiny_px = 0
    b.ao_distance = 6.0
    b.emboss = dict(k=1.3)
    pts = spine()
    rows, centres = [], []
    n = 60
    for (p, t, side, up, sn) in pts:
        row = []
        for j in range(n):
            th = 2 * math.pi * j / n
            y, z = section(th, sn)
            row.append(tuple(p + side * y + up * z))
        rows.append(row)
        centres.append(tuple(p))
    loft_param(b, 'scales', rows, centres)
    # close the tail tip
    p, t, side, up, sn = pts[-1]
    tube(b, 'scales', [tuple(p), tuple(p + t * 1.2)], [0.35, 0.05], n=8, tip=True)


# --------------------------------------------------------------------------- Smaug: the head (mesh 5)
HEAD = [(-1.5, 3.9, 4.1, -3.9), (1.2, 5.3, 4.9, -4.5), (4.6, 6.0, 5.4, -4.4), (8.0, 5.3, 4.8, -3.7),
        (11.5, 4.2, 3.6, -3.1), (16.0, 3.5, 2.9, -2.6), (20.6, 3.0, 2.3, -2.3), (23.2, 2.5, 1.7, -1.8),
        (24.4, 1.1, 0.7, -1.0)]
HEAD_LEN = 24.4


def head_frame():
    """The head's matrix: origin at the back of the skull (the neck's end), X along the snout, Z up: resting on the
    gold, chin down, turned towards the camera."""
    p, t, side, up, sn = spine()[0]
    fwd = Vector((0.62, -0.78, 0.0)).normalized()          # the snout: towards the camera and a little east
    base = p - (-t) * 0.0
    z = max(height(base.x + fwd.x * 10, base.y + fwd.y * 10), 0.0)
    pitch = math.atan2((z + 2.4) - base.z, 10.0) * 0.6
    X = Vector((fwd.x * math.cos(pitch), fwd.y * math.cos(pitch), math.sin(pitch)))
    Y = Vector((0, 0, 1)).cross(X).normalized()
    Z = X.cross(Y).normalized()
    R = Matrix((X, Y, Z)).transposed().to_4x4()
    return Matrix.Translation(base) @ R


def head_point(th, x):
    hw, top, bot = keyed([(k[0], k[1], k[2], k[3]) for k in HEAD], x)
    c, s_ = math.cos(th), math.sin(th)
    y = hw * math.copysign(abs(s_) ** 0.62, s_)
    z = (top if c >= 0 else -bot) * math.copysign(abs(c) ** 0.7, c)
    ay = abs(s_)
    d = 0.0
    up_side = c > 0
    # brow ridges over the eyes, the eyes shut (lid bulge and crease), nostrils, the mouth's line, cheek ridge
    for sgn in (1, -1):
        a = (th if sgn > 0 else 2 * math.pi - th) % (2 * math.pi)
        d += 1.6 * g(x - 6.8, 1.6) * g(a - 0.72, 0.22) + 0.8 * g(x - 3.0, 2.2) * g(a - 0.62, 0.2)   # brow, to the horns
        d -= 0.7 * g(x - 7.8, 1.6) * g(a - 1.1, 0.3)                            # the socket round the eye
        d += 0.75 * g(x - 7.8, 0.9) * g(a - 1.12, 0.2)                          # the lid
        d -= 0.45 * g(x - 7.8, 1.0) * g(a - 1.14, 0.03)                         # the closed eye's line
        d += 0.45 * g(x - 10.5, 6.0) * g(a - 0.55, 0.06)                        # a ridge from the brow to the nose
        d += 0.5 * g(x - 21.9, 0.8) * g(a - 0.45, 0.2) - 0.6 * g(x - 22.1, 0.4) * g(a - 0.45, 0.09)   # nostril
        d -= 0.45 * g(a - 1.72, 0.06) * smooth((x - 3.0) / 1.5) * smooth((20.6 - x) / 0.5)              # mouth line
        d += 0.7 * g(x - 2.5, 2.0) * g(a - 2.1, 0.3)                            # jaw muscle
        d += 0.25 * g(x - 13.0, 5.0) * g(a - 0.3, 0.12) * (0.5 + 0.5 * math.sin(x * 2.2))   # snout ridges
    d += 0.25 * fbm(x * 0.6, math.cos(th) * 2.0 + math.sin(th) * 1.3, 2, 61)
    return y, z, d, c, s_


def build_head(b):
    scale_palette()
    b.tiny_px = 0
    b.ao_distance = 3.0
    b.emboss = dict(k=1.3)
    M = head_frame()
    L = Local(b, M)
    rows, centres = [], []
    n = 72
    xs = [HEAD[0][0] + (HEAD_LEN - HEAD[0][0]) * i / 139 for i in range(140)]
    for x in xs:
        row = []
        for j in range(n):
            th = 2 * math.pi * j / n
            y, z, d, c, s_ = head_point(th, x)
            nn = Vector((0.0, y, z))
            nn = nn.normalized() if nn.length > 1e-6 else Vector((0, 0, 1))
            row.append(tuple(Vector((x, y, z)) + nn * d))
        rows.append(row)
        centres.append((x, 0.0, 0.0))
    # the param loft in head space, then placed by M
    loft_param(L, 'scales', rows, centres, nv_scales=NV)
    tube(L, 'scales', [(HEAD_LEN - 0.2, 0.0, -0.1), (HEAD_LEN + 0.4, 0.0, -0.2)], [0.9, 0.2], n=12, tip=True)
    for sgn in (1, -1):                                       # the nostrils: dark slits in the nose's bulbs
        a = 0.45
        y, z, d, c, s_ = head_point(sgn * a if sgn > 0 else 2 * math.pi - a, 22.1)
        ellipsoid(L, 'nostril', (22.15, y * 0.98, z * 0.98), (0.55, 0.22, 0.28), n=8, rings=4,
                  R=Matrix.Rotation(sgn * 0.5, 4, 'X'))
    for sgn in (1, -1):
        # the great horns sweeping back, a lesser pair below them, spikes along the jaw
        hp = [(1.5, sgn * 2.8, 3.6), (-3.0, sgn * 4.8, 6.0), (-9.0, sgn * 6.6, 7.6), (-14.5, sgn * 7.8, 7.4),
              (-18.0, sgn * 8.3, 5.8)]
        P = resample(hp, 0.35)
        tube(L, 'horn', [tuple(p) for p in P], [1.6 * (1 - 0.92 * (i / (len(P) - 1)) ** 0.9) + 0.05
                                                for i in range(len(P))], n=12, tip=True)
        for i in range(0, len(P) - 3, 3):                   # growth rings on the horns
            q = P[i]
            nxt = P[i + 1] - q
            r = 1.6 * (1 - 0.92 * (i / (len(P) - 1)) ** 0.9) + 0.12
            tube(L, 'horn', [tuple(q - nxt.normalized() * 0.08), tuple(q + nxt.normalized() * 0.08)], [r, r], n=12,
                 tip=False)
        for k in range(7):                                  # the crest: spikes radiating back round the skull
            a = math.radians(18 + 22 * k)                     # from beside the top down to the jaw's corner
            base = Vector((0.6 - 0.25 * k, sgn * 4.4 * math.sin(a), 4.4 * math.cos(a)))
            out = Vector((-1.0, sgn * math.sin(a) * 0.9, math.cos(a) * 0.9)).normalized()
            ln = 4.8 - 0.35 * abs(k - 2)
            tipv = base + out * ln
            tube(L, 'horn', [tuple(base), tuple(base + out * ln * 0.55 + Vector((-0.3, 0, 0.15))), tuple(tipv)],
                 [0.55, 0.3, 0.03], n=7, tip=True)
        hp2 = [(0.5, sgn * 4.0, 1.4), (-4.0, sgn * 6.4, 2.2), (-8.5, sgn * 7.6, 1.6)]
        P = resample(hp2, 0.35)
        tube(L, 'horn', [tuple(p) for p in P], [0.9 * (1 - 0.9 * i / (len(P) - 1)) + 0.04 for i in range(len(P))], n=9,
             tip=True)
        for k in range(6):                                  # cheek and jaw spikes, pointing back and out
            x = 6.0 - 1.4 * k
            base = Vector((x, sgn * (keyed([(q[0], q[1]) for q in HEAD], x)[0] * 0.95), -2.6 + 0.2 * k))
            tipv = base + Vector((-2.2 - 0.3 * k, sgn * (1.4 + 0.2 * k), -0.6))
            tube(L, 'horn', [tuple(base), tuple((base + tipv) / 2 + Vector((0, 0, 0.2))), tuple(tipv)],
                 [0.45, 0.25, 0.03], n=7, tip=True)
        for k in range(11):                                 # the upper teeth over the lip, a fang near the front
            x = 9.8 + 1.27 * k
            hw = keyed([(q[0], q[1]) for q in HEAD], x)[0]
            fang = k == 8
            ln = 1.6 if fang else 0.55 + 0.25 * math.sin(k * 2.1)
            base = Vector((x, sgn * hw * 0.93, -0.35))
            tube(L, 'teeth', [tuple(base), tuple(base + Vector((0.15, sgn * 0.05, -ln)))],
                 [0.32 if fang else 0.2, 0.02], n=6, tip=True)
        for k in range(7):                                  # ridge spikes along the top of the snout
            x = 10.4 + 1.8 * k
            top = keyed([(q[0], q[2]) for q in HEAD], x)[0]
            base = Vector((x, sgn * 1.1, top * 0.92))
            tube(L, 'horn', [tuple(base), tuple(base + Vector((-0.5, sgn * 0.2, 0.55 - 0.04 * k)))], [0.25, 0.02], n=6,
                 tip=True)


# --------------------------------------------------------------------------- Smaug: wings, legs, spikes (mesh 6)
def claw(b, base, direction, length, r):
    d = Vector(direction).normalized()
    down = Vector((0, 0, -1))
    pts = [base, base + d * length * 0.5 + down * length * 0.1, base + d * length * 0.8 + down * length * 0.45]
    tube(b, 'claw', [tuple(p) for p in pts], [r, r * 0.6, 0.02], n=7, tip=True)


def wing(b, rng, sgn):
    """A folded wing (the forelimb): the shoulder high on the flank, the elbow raised above the back, the forearm down
    to the wrist planted on the gold beside the chest with the thumb's hooked claw; four long fingers sweep back along
    the flank and the membrane between them falls in a fan over his side."""
    p, t, side, up, sn = at_s(58.0)
    rw, rh = keyed(SECT, sn)
    S = side * sgn
    shoulder = p + S * rw * 0.85 + up * rh * 0.35 - t * 2.0
    elbow = shoulder + up * 6.0 + t * 8.0 + S * 2.8
    wrist = p - t * 8.0 + S * (rw + 4.0)
    wrist.z = max(height(wrist.x, wrist.y), 0.0) + 1.0
    arm = resample([tuple(shoulder), tuple((shoulder + elbow) / 2 + S * 1.0), tuple(elbow)], 0.5)
    ptube(b, 'scales', [tuple(q) for q in arm], [1.9 - 0.7 * i / (len(arm) - 1) for i in range(len(arm))], n=14)
    fore = resample([tuple(elbow), tuple((elbow + wrist) / 2 + S * 1.5 - t * 1.0), tuple(wrist)], 0.5)
    ptube(b, 'scales', [tuple(q) for q in fore], [1.25 - 0.4 * i / (len(fore) - 1) for i in range(len(fore))], n=12)
    psphere(b, 'scales', tuple(elbow), (1.5, 1.5, 1.5))
    claw(b, elbow, up + t * 0.6, 3.5, 0.6)                 # the spur on the elbow
    psphere(b, 'scales', tuple(wrist), (1.5, 1.5, 1.2))
    claw(b, wrist + S * 0.5, -t + S * 0.3, 3.2, 0.55)        # the thumb, hooked into the coins
    # fingers: from the wrist back along the flank, stacked from the gold up to near the spine
    fingers = []
    for k in range(4):
        q = at_s(78.0 + 16.0 * k)
        pp, tt, ss, uu, sk = q
        rwk, rhk = keyed(SECT, sk)
        end = pp + ss * sgn * (rwk * 0.98 + 0.9) + uu * (rhk * (-0.25 + 0.28 * k))
        mid = wrist.lerp(end, 0.45) + ss * sgn * 1.6 + uu * (1.5 + 1.6 * k)
        P = resample([tuple(wrist), tuple(mid), tuple(end)], 0.6)
        fingers.append(P)
        ptube(b, 'scales', [tuple(x) for x in P], [0.75 - 0.6 * i / (len(P) - 1) for i in range(len(P))], n=8)
    # the membranes: between the forearm/elbow line and finger 4, and between neighbouring fingers
    edges = [fore[::-1]] + fingers[::-1]
    for A, B in zip(edges, edges[1:]):
        m = 14
        rowsA = [A[int(i * (len(A) - 1) / m)] for i in range(m + 1)]
        rowsB = [B[int(i * (len(B) - 1) / m)] for i in range(m + 1)]
        grid = []
        for i in range(m + 1):
            row = []
            for j in range(8):
                f = j / 7
                q = rowsA[i].lerp(rowsB[i], f)
                sag = math.sin(math.pi * f) * (0.6 + 0.5 * math.sin(math.pi * i / m))
                q = q + S * sag * 0.5 - Vector((0, 0, sag * 0.3))
                row.append(tuple(q))
            grid.append(row)
        thick_sheet(b, 'membrane', grid, 0.12)


def leg(b, sgn):
    """A hind leg tucked under him: the thigh bulging on the flank, the foot on the gold with four clawed toes."""
    p, t, side, up, sn = at_s(108.0)
    rw, rh = keyed(SECT, sn)
    S = side * sgn
    hip = p + S * rw * 0.62 - up * rh * 0.35
    knee = hip + S * 3.5 - t * 5.0 - up * 1.0
    foot = hip + S * 4.5 + t * 2.0
    foot.z = max(height(foot.x, foot.y), 0.0) + 0.8
    thigh = resample([tuple(hip - t * 4.0 - S * 1.0 + up * 1.5), tuple(hip + S * 1.5 + up * 0.5),
                      tuple(knee + up * 0.5)], 0.6)
    ptube(b, 'scales', [tuple(q) for q in thigh],
          [2.6 + 0.9 * math.sin(math.pi * i / (len(thigh) - 1)) for i in range(len(thigh))], n=16)
    P = resample([tuple(hip), tuple(knee), tuple(foot)], 0.5)
    ptube(b, 'scales', [tuple(q) for q in P], [3.6 - 2.2 * i / (len(P) - 1) for i in range(len(P))], n=14)
    psphere(b, 'scales', tuple(foot), (1.8, 1.4, 1.0))
    for k in range(4):
        a = -0.6 + 0.4 * k
        d = (-t * math.cos(a) + S * math.sin(a) * 1.2).normalized()
        base = foot + d * 1.2
        toe = resample([tuple(base), tuple(base + d * 1.6 + Vector((0, 0, 0.2)))], 0.4)
        ptube(b, 'scales', [tuple(q) for q in toe], [0.55] * (len(toe) - 1) + [0.42], n=8)
        claw(b, Vector(toe[-1]), d, 1.6, 0.4)


def dorsal_spikes(b):
    """Spikes along the spine from the nape to the tail's tip, biggest over the shoulders, raked back."""
    pts = spine()
    sn = 2.0
    while sn < SECT[-1][0] - 2:
        p, t, side, up, s2 = at_s(sn)
        rw, rh = keyed(SECT, s2)
        top = p + up * (rh * 1.08)
        hgt = max(0.4, 0.55 * rh) * (1.0 + 0.25 * math.sin(sn * 0.7))
        tipp = top + up * hgt + t * hgt * 0.7
        tube(b, 'horn', [tuple(top - up * 0.3), tuple(top + up * hgt * 0.5 + t * hgt * 0.15), tuple(tipp)],
             [max(0.18, 0.28 * rh), max(0.1, 0.14 * rh), 0.02], n=7, tip=True)
        sn += max(1.3, 0.45 * rh + 0.9)


def build_limbs(b):
    scale_palette()
    b.tiny_px = 0
    b.ao_distance = 4.0
    b.emboss = dict(k=1.3)
    rng = random.Random(2013)
    for sgn in (1, -1):
        wing(b, rng, sgn)
        leg(b, sgn)
    dorsal_spikes(b)


# --------------------------------------------------------------------------- the rig (still for now)
# 2026-11-26: the first in-game test drew the static part but NOT the skinned model when every mesh was bound only to
# the root of a one-bone skeleton with no curve. Now exactly Treebeard's proven layout: a root and a child bone that
# carries every vertex, driven by a real rotation curve (held still until the animations come).
BONES = [('eyeroot', None, (0.0, 0.0, 0.0)), ('eyepivot', 'eyeroot', (0.0, 8.0, 26.0))]
MOTIONS = {'eyepivot': lambda t: (0.0, 0.0, 0.0)}


def weights(res, suffix):
    return [[('eyepivot', 1.0)] for _ in res.verts]


DRAGON_PARTS = [                     # the dragon version's skinned meshes (kept for later)
    ('pile', build_pile, 2048), ('treasure', build_treasure, 2048), ('body', build_body, 2048),
              ('head', build_head, 2048), ('limbs', build_limbs, 2048)]

PREVIEW = [((-2, -62, 42), (-2, -18, 16), 42),            # the head on the gold
           ((60, -30, 40), (14, 2, 18), 40),              # the flank: wing, hind leg
           ((95, -95, 75), (0, 0, 12), 38),               # the hoard from the south-east
           ((18, -45, 20), (14, -28, 6), 45)]             # treasure close up
PREVIEW_EYE = [((0, -220, 190), (0, 0, 10), 38)]
