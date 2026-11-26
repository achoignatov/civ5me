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
PILES = [(0.0, 9.0, 40.0, 37.0, 22.0), (-11.0, 11.0, 17.0, 14.0, 7.0), (13.0, 11.0, 16.0, 14.0, 6.0),
         (2.0, -16.0, 20.0, 13.0, 5.5), (-4.0, 20.0, 15.0, 12.0, 6.0), (0.0, 6.0, 66.0, 62.0, 3.2),     # the heap; a low floor of gold under all (-15.0, 15.0, 14.0, 12.0, 7.0), (17.0, 17.0, 13.0, 12.0, 6.0),
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
# v4 (2026-11-26): on the city's own tile. The Hobbit, ch. 12: "a vast red-golden dragon, fast asleep ... under all
# his limbs and his huge coiled tail ... Smaug lay, with wings folded like an immeasurable bat, turned partly on one
# side, so that the hobbit could see his underparts and his long pale belly crusted with gems and fragments of gold".
# The neck curls down the front-left of the heap to the head resting on the gold; the body lies over the summit,
# ROLLED towards the camera so the belly shows; the tail coils round the east side and the front, its tip by his snout.
SPINE_XY = [(-12.0, -21.0), (-20.0, -16.0), (-24.0, -7.0), (-20.0, 1.0), (-12.0, 4.0), (-1.0, 5.0), (10.0, 4.0),
            (18.0, 0.0), (24.0, -7.0), (25.0, -17.0), (19.0, -25.0), (11.0, -29.0), (5.0, -31.0)]
# (fraction of the length from the head, half-width, half-height)
SECT = [(0.0, 3.4, 3.5), (15.0, 4.2, 4.3), (30.0, 6.2, 5.8), (38.0, 8.4, 7.4), (50.0, 9.0, 7.8), (62.0, 7.6, 6.8),
        (70.0, 5.6, 5.0), (84.0, 3.2, 3.0), (94.0, 1.7, 1.6), (100.0, 0.4, 0.4)]
ROLL = 75.0                          # degrees the trunk is turned on its side (the belly towards the camera)
SINK = 0.5                           # how deep he lies in the coins (fraction of his height below the spine)
_SPINE = {}


def roll_at(sn):
    return math.radians(ROLL) * smooth((sn - 24.0) / 12.0) * smooth((76.0 - sn) / 12.0)


def spine():
    """[(point, tangent, side, up, s)] along the spine every ~0.42 units, the head end first; s in percent of the
    length. side/up are ROLLED about the tangent (roll_at): the belly (-up) turns towards side, i.e. towards the
    camera where he lies over the summit."""
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
        f = roll_at(sn)
        side, up = side * math.cos(f) + up * math.sin(f), up * math.cos(f) - side * math.sin(f)
        pts.append((p, t, side, up, sn))
    _SPINE['pts'] = pts
    _SPINE['length'] = total
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
        if not (DRAGON and under_left_wing(x, y, 0.9)):      # (after every draw: the others stay where they were)
            lathe(b, m, [(0.0, 0.0), (r, 0.0), (r, 0.1), (r * 0.82, 0.13), (0.0, 0.13)], 7, M=M, smooth=True)
        placed += 1


STATIC_PX = 2048
DRAGON = True                        # v4: Smaug on the heap (his own static models: STATIC_PARTS)


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
    M = head_frame()
    for xh in range(-4, 24, 2):
        c = M @ Vector((xh, 0.0, 0.0))
        if math.hypot(x - c.x, y - c.y) < 6.5 + margin:
            return False
    for p, t, side, up, sn in spine()[::3]:
        rw, rh = keyed(SECT, sn)
        if math.hypot(x - p.x, y - p.y) < rw + margin:
            return False
    return True


class _Null:
    def add(self, *a, **k):
        pass


_NULL = _Null()


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
    real = b
    for (x, y, _), kind in zip(spots, kinds):
        # under the left wing: built into nothing (the same random draws, so the other pieces stay where they were)
        b = _NULL if DRAGON and under_left_wing(x, y, 2.5) else real
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
    b = real
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
    # the tail's tip: closed, with a fan of three blades (the film's)
    p, t, side, up, sn = pts[-1]
    tube(b, 'scalecap', [tuple(p), tuple(p + t * 1.2)], [0.4, 0.05], n=8, tip=True)
    for k, (a, ln) in enumerate(((0.0, 3.2), (0.7, 2.4), (-0.7, 2.4))):
        d = (t + up * 0.35 + side * a).normalized()
        base = p - t * 1.5 * k
        tube(b, 'horn', [tuple(base), tuple(base + d * ln * 0.5 + up * 0.2), tuple(base + d * ln)],
             [0.45, 0.25, 0.02], n=7, tip=True)


# --------------------------------------------------------------------------- Smaug: the head (mesh 5)
HEAD = [(-1.5, 3.9, 4.1, -3.9), (1.2, 5.3, 4.9, -4.5), (4.6, 6.0, 5.4, -4.4), (8.0, 5.3, 4.8, -3.7),
        (11.5, 4.1, 3.5, -3.1), (16.0, 3.2, 2.7, -2.5), (20.6, 2.5, 2.0, -2.0), (23.2, 2.0, 1.5, -1.6),
        (24.4, 1.1, 0.7, -1.0)]
HEAD_LEN = 24.4


def head_frame():
    """The head's matrix: origin at the back of the skull (the neck's end), X along the snout, Z up: resting on the
    gold, chin down, turned towards the camera."""
    p, t, side, up, sn = spine()[0]
    fwd = Vector((-t.x, -t.y - 0.35, 0.0)).normalized()     # the neck's continuation, turned a little to the camera
    base = p - (-t) * 0.0
    z = max(height(base.x + fwd.x * 10, base.y + fwd.y * 10), 0.0)
    pitch = math.atan2((z + 2.4) - base.z, 10.0) * 0.6
    X = Vector((fwd.x * math.cos(pitch), fwd.y * math.cos(pitch), math.sin(pitch)))
    Y = Vector((0, 0, 1)).cross(X).normalized()
    Z = X.cross(Y).normalized()
    R = Matrix((X, Y, Z)).transposed().to_4x4()
    return Matrix.Translation(base) @ R @ Matrix.Rotation(math.radians(-14.0), 4, 'X') @ Matrix.Scale(HEAD_S, 4)


HEAD_S = 0.82                        # the head's scale (the profile below is authored for a bigger dragon)


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


def head_surface(th, x):
    """A point on the head's displaced surface (head space) and its outward direction."""
    y, z, d, c, s_ = head_point(th, x)
    nn = Vector((0.0, y, z))
    nn = nn.normalized() if nn.length > 1e-6 else Vector((0, 0, 1))
    return Vector((x, y, z)) + nn * d, nn


EYE_X = (5.7, 10.0)                  # the eye's corners along the head (head space)


def closed_eye(L, sgn):
    """His eye, shut in sleep: an almond slit slanting up to the back, sealed by a heavy upper lid rolled over the
    eyeball and a thinner lower lid; the dark seam where they meet; folds of hide over and under the socket."""
    def ang(x, off=0.0):                                     # the slit: higher (nearer the brow) towards the back
        a = 1.13 + 0.05 * (x - 7.85) / 2.15 + off
        return a if sgn > 0 else 2 * math.pi - a
    x0, x1 = EYE_X
    N = 24
    xs = [x0 + (x1 - x0) * i / N for i in range(N + 1)]
    bulge = [math.sin(math.pi * i / N) for i in range(N + 1)]
    # the eyeball under the lids: a low almond mound, mostly inside the head
    c, nn = head_surface(ang(7.85), 7.85)
    ax = (head_surface(ang(x1), x1)[0] - head_surface(ang(x0), x0)[0])          # along the slit
    ax = (ax - nn * ax.dot(nn)).normalized()
    R = Matrix((ax, nn.cross(ax), nn)).transposed().to_4x4()                   # x along the slit, z out of the head
    ellipsoid(L, 'lid', tuple(c - nn * 0.62), (2.05, 0.95, 1.0), n=16, rings=8, R=R)
    mound = [0.36 * bb ** 0.8 for bb in bulge]                # the lids' top over the head's surface
    # the upper lid, heavy, rolled down over the eye; the lower lid, thinner, rising to meet it
    for off, lift, r in ((-0.05, 1.0, 0.3), (0.05, 0.85, 0.2)):
        Q = []
        for x, bb, m in zip(xs, bulge, mound):
            p, n_ = head_surface(ang(x, off * bb ** 0.5), x)
            Q.append(tuple(p + n_ * (m * lift + 0.02)))
        tube(L, 'lid', Q, [0.04 + r * bb ** 0.7 for bb in bulge], n=10, tip=True)
    # the seam: the dark slit where they meet, in the groove between them
    P = [head_surface(ang(x), x) for x in xs]
    tube(L, 'nostril', [tuple(p + n_ * (m * 0.95 + 0.04)) for (p, n_), m in zip(P, mound)],
         [0.03 + 0.06 * bb for bb in bulge], n=6, tip=True)
    # a fold of hide arching over the socket under the brow, a softer one below the eye
    for off, lift, r, span in ((-0.19, 0.2, 0.12, (6.0, 9.7)), (0.18, 0.12, 0.08, (6.4, 9.4))):
        Q, rr = [], []
        for i in range(17):
            f = i / 16
            x = span[0] + (span[1] - span[0]) * f
            p, n_ = head_surface(ang(x, off), x)
            Q.append(tuple(p + n_ * (lift * math.sin(math.pi * f) + 0.01)))
            rr.append(0.02 + r * math.sin(math.pi * f) ** 0.8)
        tube(L, 'lid', Q, rr, n=6, tip=True)


def build_head(b):
    scale_palette()
    material('lid', h('561a0e'), h('48150b'), spec=0.5, refl=60)        # the eyelids: finer, folded hide
    blib.PALETTE['lid'].update(scale=8.0, vcracks=(6.0, 0.3), cavity=0.9,
                               speckle=[(6.0, 0.2, h('6e2614')), (3.0, 0.15, h('2e0e08'))])
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
    for sgn in (1, -1):
        closed_eye(L, sgn)
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


def wing(b, rng):
    """The folded wing on his upper side ('wings folded like an immeasurable bat'): the shoulder high on the turned-up
    flank, the elbow raised with its spur, the forearm down to the wrist planted on the gold before his chest, its
    thumb's claw hooked into the coins; four long knuckled fingers sweep back over the flank towards the hips and the
    membrane between them lies over his side in creased folds."""
    p, t, side, up, sn = at_s(37.0)
    rw, rh = keyed(SECT, sn)
    Z = Vector((0.0, 0.0, 1.0))
    shoulder = p + up * rh * 0.75 + side * rw * 0.25
    elbow = shoulder + Z * 10.0 + t * 6.5 - side * 1.0
    wrist = p - t * 8.0 + up * (rh + 1.5) + Z * 2.0
    hz = max(height(wrist.x, wrist.y), 0.0) + 1.2
    wrist.z = max(wrist.z, hz)
    arm = resample([tuple(shoulder), tuple((shoulder + elbow) / 2 + side * 1.0), tuple(elbow)], 0.5)
    ptube(b, 'scales', [tuple(q) for q in arm], [2.1 - 0.8 * i / (len(arm) - 1) for i in range(len(arm))], n=14)
    fore = resample([tuple(elbow), tuple((elbow + wrist) / 2 + side * 1.6 - t * 0.5), tuple(wrist)], 0.5)
    ptube(b, 'scales', [tuple(q) for q in fore], [1.35 - 0.45 * i / (len(fore) - 1) for i in range(len(fore))], n=12)
    psphere(b, 'scales', tuple(elbow), (1.6, 1.6, 1.6))
    claw(b, elbow + Z * 0.8, Z + t * 0.7, 3.6, 0.65)       # the spur on the elbow
    psphere(b, 'scales', tuple(wrist), (1.6, 1.6, 1.3))
    claw(b, wrist - t * 0.6, -t + Vector((0.0, 0.0, -0.6)), 3.4, 0.6)   # the thumb's hooked claw
    fingers = []
    for k in range(4):
        pp, tt, ss, uu, sk = at_s(46.0 + 7.5 * k)
        rwk, rhk = keyed(SECT, sk)
        end = pp + uu * (rhk * 1.0 + 0.8) + ss * (rwk * (0.45 - 0.3 * k))
        mid = wrist.lerp(end, 0.42) + uu * 2.4 + Z * (4.5 - 0.6 * k)
        P = resample([tuple(wrist), tuple(mid), tuple(end)], 0.55)
        fingers.append(P)
        n = len(P)
        rr = [0.8 - 0.62 * i / (n - 1) + 0.18 * (g(i / (n - 1) - 0.33, 0.04) + g(i / (n - 1) - 0.66, 0.04))
              for i in range(n)]                             # knuckles
        ptube(b, 'scales', [tuple(x) for x in P], rr, n=9)
        claw(b, Vector(P[-1]), (Vector(P[-1]) - Vector(P[-2])), 1.0, 0.18)
    # membranes between the forearm and the fingers, creased along their length, sagging between the bones
    edges = [fore[::-1]] + fingers
    for e, (A, B) in enumerate(zip(edges, edges[1:])):
        m = 16
        rowsA = [A[int(i * (len(A) - 1) / m)] for i in range(m + 1)]
        rowsB = [B[int(i * (len(B) - 1) / m)] for i in range(m + 1)]
        grid = []
        for i in range(m + 1):
            row = []
            for j in range(9):
                f = j / 8
                q = rowsA[i].lerp(rowsB[i], f)
                sag = math.sin(math.pi * f) * (0.55 + 0.45 * math.sin(math.pi * i / m))
                crease = 0.18 * math.sin(f * math.pi * 3 + e) * math.sin(math.pi * i / m)
                q = q - Z * (sag * 0.6) + up * (sag * 0.3 + crease)
                row.append(tuple(q))
            grid.append(row)
        thick_sheet(b, 'membrane', grid, 0.12)


def leg(b):
    """His upper hind leg: the thigh on the turned-up flank, the shin, the foot resting on the gold below his belly,
    four clawed toes spread over the coins."""
    p, t, side, up, sn = at_s(63.0)
    rw, rh = keyed(SECT, sn)
    Z = Vector((0.0, 0.0, 1.0))
    hip = p + side * rw * 0.5 + up * rh * 0.15
    knee = hip - t * 6.0 + side * 3.0 + Z * 1.0
    foot = p - t * 2.0 + side * (rw + 4.5)
    foot.z = max(height(foot.x, foot.y), 0.0) + 0.9
    thigh = resample([tuple(hip + t * 3.0), tuple(hip + side * 1.0), tuple(knee)], 0.6)
    ptube(b, 'scales', [tuple(q) for q in thigh],
          [2.8 + 1.2 * math.sin(math.pi * i / (len(thigh) - 1)) for i in range(len(thigh))], n=16)
    P = resample([tuple(knee), tuple((knee + foot) / 2 + side * 0.5), tuple(foot)], 0.5)
    ptube(b, 'scales', [tuple(q) for q in P], [2.4 - 1.2 * i / (len(P) - 1) for i in range(len(P))], n=14)
    psphere(b, 'scales', tuple(foot), (1.9, 1.5, 1.0))
    fwd = (side + (-t) * 0.3).normalized()
    for k in range(4):
        a = -0.75 + 0.5 * k
        d = (fwd * math.cos(a) + t.cross(Z).normalized() * math.sin(a)).normalized()
        d.z = 0.0
        d.normalize()
        base = foot + d * 1.3
        tip = base + d * 1.8
        tip.z = max(height(tip.x, tip.y), 0.0) + 0.5
        toe = resample([tuple(base), tuple(tip)], 0.4)
        ptube(b, 'scales', [tuple(q) for q in toe], [0.6] * (len(toe) - 1) + [0.45], n=8)
        claw(b, Vector(toe[-1]), d, 1.7, 0.42)


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
    wing(b, rng)
    leg(b)
    dorsal_spikes(b)


# --------------------------------------------------------------------------- Smaug: the left wing (mesh 7)
# The user (2026-11-26): "the left wing ... resting on top of the central tile pile of gold ... looking somewhat like a
# bat wing ... as if the dragon is just taking a nap in his bed ... in a natural sleeping, comfortable position".
# He lies rolled with the belly to the camera, the folded wing on the side turned to the sky. The other wing comes out from under his chest and lies spread, relaxed, over the gold inside his
# coil like a blanket: the arm runs down the heap beside his neck to the wrist near his jaw (the thumb's claw hooked
# into the coins), four fingers fan back towards his tail, the membrane between them drapes over the coins in loose
# folds, its trailing edge scalloped between the finger tips, the last panel hanging from his flank.
LW_ELBOW = (-12.0, -10.0)
LW_WRIST = (-4.0, -18.0)
LW_TIPS = [(3.0, -24.5), (15.0, -23.0), (17.5, -12.0), (10.0, -9.5)]   # fingers II..V (the third the longest)
LW_SHOULDER = (29.5, -0.55)          # (percent of the length, angle from the belly): the front of the chest where the
                                     # neck joins it (the user: from his SHOULDER, not his belly)
LW_FLANK = (33.0, 57.0)              # the membrane's attachment along his flank behind the armpit (percent)
LW_CLEAR = 0.32                      # the membrane's height over the coins
_LW = {}


def gz(x, y):
    return max(height(x, y), 0.0)


def flank_point(sn):
    """The lowest point of his belly-front still clear of the coins at sn (where the membrane joins the body)."""
    p, t, side, up, s2 = at_s(sn)
    best = None
    for k in range(40):
        th = math.pi - 0.2 + 1.7 * k / 39
        y, z = section(th, s2)
        q = p + side * y + up * z
        if q.z >= gz(q.x, q.y) + 0.6 and (best is None or q.z < best.z):
            best = q
    nrm = (-up + (-side) * 0.4).normalized()
    return best + nrm * 0.35


def shoulder_point():
    """The shoulder joint: on the front of his chest at the root of the neck, a little inside the hide (the shoulder's
    muscle swells out of it), with the outward normal there."""
    p, t, side, up, s2 = at_s(LW_SHOULDER[0])
    th = math.pi + LW_SHOULDER[1]
    y, z = section(th, s2)
    nrm = (side * math.sin(th) + up * math.cos(th)).normalized()
    return p + side * y + up * z - nrm * 0.6, nrm


def _arclen(P):
    L = [0.0]
    for a, c in zip(P, P[1:]):
        L.append(L[-1] + (c - a).length)
    return L


def _at(P, L, s):
    """The point at fraction s (0..1) of the length along the polyline P (cumulative lengths L)."""
    d = max(0.0, min(1.0, s)) * L[-1]
    i = 0
    while i < len(L) - 2 and L[i + 1] < d:
        i += 1
    return P[i].lerp(P[i + 1], (d - L[i]) / max(1e-6, L[i + 1] - L[i]))


def drape(P, r, sink=0.75):
    """Lay a path on the coins: z = the heap plus part of the bone's radius."""
    out = []
    for i, q in enumerate(P):
        rr = r[i] if isinstance(r, list) else r
        out.append(Vector((q.x, q.y, gz(q.x, q.y) + rr * sink)))
    return out


def lw_skeleton():
    """The bones of the left wing as paths: humerus+forearm (from the shoulder under his chest), fingers II..V, and
    the attachment line along his flank."""
    if _LW:
        return _LW
    S, Sn = shoulder_point()
    flank = [S] + [flank_point(sn) for sn in [LW_FLANK[0] + (LW_FLANK[1] - LW_FLANK[0]) * k / 23 for k in range(24)]]
    E = Vector((LW_ELBOW[0], LW_ELBOW[1], 0.0))
    W = Vector((LW_WRIST[0], LW_WRIST[1], 0.0))
    E.z = gz(E.x, E.y) + 1.5
    W.z = gz(W.x, W.y) + 1.1
    hum = resample([tuple(S), tuple(S + Sn * 2.0 + (E - S) * 0.15), tuple(S.lerp(E, 0.55) + Vector((-0.8, 0.0, 0.6))),
                    tuple(E)], 0.35)
    for i, q in enumerate(hum):                      # down from the chest onto the coins
        f = i / (len(hum) - 1)
        q.z = max(q.z, gz(q.x, q.y) + 1.5)
    fore = resample([tuple(E), tuple(E.lerp(W, 0.5) + Vector((-0.9, -0.6, 0.0))), tuple(W)], 0.35)
    fore = drape(fore, [1.35 - 0.3 * i / (len(fore) - 1) for i in range(len(fore))], 0.8)
    fingers = []
    for k, (tx, ty) in enumerate(LW_TIPS):
        T = Vector((tx, ty, 0.0))
        d = T - W
        n_ = Vector((-d.y, d.x, 0.0)).normalized()
        bow = (0.9, 1.3, 1.1, -0.8)[k]               # the fingers bowed a little, relaxed
        P = resample([tuple(W), tuple(W.lerp(T, 0.36) + n_ * bow * 0.6), tuple(W.lerp(T, 0.7) + n_ * bow),
                      tuple(T)], 0.3)
        n = len(P)
        rr = [0.85 - 0.62 * i / (n - 1) + 0.2 * (g(i / (n - 1) - 0.36, 0.035) + g(i / (n - 1) - 0.7, 0.03))
              for i in range(n)]                     # knuckles
        P = drape(P, rr, 0.7)
        for i in range(min(6, n)):                   # rising into the wrist
            P[i].z = max(P[i].z, W.z * (1 - i / 6) + P[i].z * i / 6)
        fingers.append((P, rr))
    _LW.update(flank=flank, S=S, Sn=Sn, E=E, W=W, hum=hum, fore=fore, fingers=fingers)
    return _LW


def _panel(b, A, B, m, nc, scallop, seed, veins=2, ends=(0.0, 1.0)):
    """A membrane panel between two edge paths A and B that start together (at the wrist, or at the shoulder for
    the last one): a grid lerped between them, the trailing edge between their ends scalloped towards the start,
    sagging off the bones onto the coins, lying in loose folds (always above the coins), with raised veins."""
    rng = random.Random(seed)
    LA, LB = _arclen(A), _arclen(B)
    ph = [rng.uniform(0, 6.3) for _ in range(4)]

    def point(r, f):
        re = r * (1.0 - scallop * max(0.0, math.sin(math.pi * f)) ** 1.3)
        a, c = _at(A, LA, ends[0] + (ends[1] - ends[0]) * re), _at(B, LB, re)
        q = a.lerp(c, f)
        span = (a - c).length
        floor_ = gz(q.x, q.y) + LW_CLEAR
        z = q.z - span * 0.35 * math.sin(math.pi * f)               # slack: it sags off the bones
        z = max(z, floor_)
        w = max(0.0, math.sin(math.pi * f)) ** 0.6 * smooth(re / 0.25)
        k = min(1.0, span / 8.0)                                     # wider panels lie in deeper slack folds
        fold = (0.75 * k + 0.2) * (0.5 + 0.5 * math.sin(2 * math.pi * ((1.6 + 1.6 * k) * f + 0.5 * re) + ph[0])) ** 2 + \
            0.22 * (0.5 + 0.5 * math.sin(2 * math.pi * ((4.5 + 3 * k) * f - 1.3 * re) + ph[1])) + \
            0.1 * (0.5 + 0.5 * math.sin(2 * math.pi * (11 * f + 2.5 * re) + ph[2]))
        curl = 0.45 * smooth((re - 0.8) / 0.2) * math.sin(math.pi * f)       # the free edge lifts a little
        return Vector((q.x, q.y, z + w * fold + curl * (0.5 + 0.5 * math.sin(9 * f + ph[2]))))
    grid = [[tuple(point(i / m, j / nc)) for j in range(nc + 1)] for i in range(m + 1)]
    # the outer face up (thick_sheet offsets the inner face against du x dv)
    i0, j0 = m // 2, nc // 2
    du = Vector(grid[i0][j0 + 1]) - Vector(grid[i0][j0 - 1])
    dv = Vector(grid[i0 + 1][j0]) - Vector(grid[i0 - 1][j0])
    if du.cross(dv).z < 0:
        grid = [row[::-1] for row in grid]
    thick_sheet(b, 'membrane', grid, 0.1)
    for v in range(veins):                                         # veins, with a branch or two
        f0 = (v + 0.5 + rng.uniform(-0.15, 0.15)) / veins
        P = [point(0.06 + 0.86 * k / 30, f0 + 0.05 * math.sin(k * 0.5 + ph[3] + v)) + Vector((0, 0, 0.06))
             for k in range(31)]
        tube(b, 'vein', [tuple(q) for q in P], [0.17 - 0.1 * k / 30 for k in range(31)], n=6, tip=True)
        for _ in range(3):
            k0 = rng.randint(6, 20)
            df = rng.choice((-1, 1)) * rng.uniform(0.08, 0.16)
            Q = [point(0.06 + 0.86 * (k0 + k) / 30, f0 + df * k / 8) + Vector((0, 0, 0.06)) for k in range(9)]
            tube(b, 'vein', [tuple(q) for q in Q], [0.1 - 0.06 * k / 8 for k in range(9)], n=4, tip=True)


def left_wing(b):
    sk = lw_skeleton()
    S, E, W, hum, fore, fingers, flank = sk['S'], sk['E'], sk['W'], sk['hum'], sk['fore'], sk['fingers'], sk['flank']
    Z = Vector((0.0, 0.0, 1.0))
    # bones: the humerus, the forearm, the wrist, the thumb and its claw, the elbow's spur
    # the shoulder: a heavy muscle swelling out of the chest at the root of the neck, the humerus out of it
    Sn = sk['Sn']
    dh = (hum[min(6, len(hum) - 1)] - S).normalized()
    sh = resample([tuple(S - Sn * 2.6), tuple(S + Sn * 0.4 + dh * 0.8), tuple(S + Sn * 0.8 + dh * 3.2)], 0.35)
    ptube(b, 'scales', [tuple(q) for q in sh],
          [3.0 + 0.5 * math.sin(math.pi * min(1.0, 1.4 * i / (len(sh) - 1))) - 0.9 * i / (len(sh) - 1)
           for i in range(len(sh))], n=16)
    ptube(b, 'scales', [tuple(q) for q in hum], [2.1 - 0.7 * i / (len(hum) - 1) for i in range(len(hum))], n=14)
    ptube(b, 'scales', [tuple(q) for q in fore], [1.35 - 0.3 * i / (len(fore) - 1) for i in range(len(fore))], n=12)
    psphere(b, 'scales', tuple(E), (1.7, 1.7, 1.4))
    d = (E - S).normalized()
    claw(b, E + Z * 0.6 - d * 0.3, (d + Z * 0.4), 2.6, 0.55)              # the spur at the elbow
    psphere(b, 'scales', tuple(W), (1.5, 1.5, 1.15))
    fd = (W - E).normalized()
    fwd = Vector((fd.y, -fd.x, 0.0))                                     # the leading side (towards his head)
    th0 = W + fwd * 0.8 + fd * 0.5
    th1 = th0 + (fwd * 0.6 + fd * 0.8).normalized() * 2.2
    th1.z = gz(th1.x, th1.y) + 0.7
    thumb = resample([tuple(th0), tuple(th0.lerp(th1, 0.5) + Z * 0.4), tuple(th1)], 0.3)
    ptube(b, 'scales', [tuple(q) for q in thumb], [0.62 - 0.15 * i / (len(thumb) - 1) for i in range(len(thumb))],
          n=9)
    claw(b, th1, (th1 - th0) + Vector((0, 0, -0.2)), 2.0, 0.42)          # hooked into the coins
    for P, rr in fingers:
        ptube(b, 'scales', [tuple(q) for q in P], rr, n=10)
        claw(b, P[-1], P[-1] - P[-3], 0.9, 0.16)
    # the membranes: in front of the arm (shoulder to wrist), between the fingers, and from finger V to his flank
    arm = hum + fore[1:]
    LA = _arclen(arm)
    front = []
    for i in range(len(arm)):
        s = LA[i] / LA[-1]
        dd = (arm[min(i + 1, len(arm) - 1)] - arm[max(i - 1, 0)])
        dd.z = 0.0
        dd.normalize()
        off = Vector((dd.y, -dd.x, 0.0)) * (2.2 * math.sin(math.pi * s) ** 0.8)
        q = arm[i] + off
        front.append(Vector((q.x, q.y, max(gz(q.x, q.y) + LW_CLEAR, arm[i].z - 0.4))))
    _panel(b, arm, front, 40, 5, 0.0, 71, veins=1)
    for k in range(3):
        _panel(b, fingers[k][0], fingers[k + 1][0], 40, 20, 0.22, 80 + k, veins=2)
    _panel(b, flank, arm + fingers[3][0][1:], 50, 28, 0.16, 90, veins=5)


def under_left_wing(x, y, margin=1.0):
    """Is (x, y) under the left wing (its outline: shoulder, elbow, wrist, the finger tips, back along the flank)?"""
    sk = lw_skeleton()
    if 'outline' not in sk:
        o = [sk['S'], sk['E'], sk['W'] + Vector((-1.5, -1.5, 0))] + [Vector((tx, ty, 0)) for tx, ty in LW_TIPS] + \
            sk['flank'][::-1]
        sk['outline'] = [(q.x, q.y) for q in o]
    poly = sk['outline']
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
        vx, vy = x2 - x1, y2 - y1
        tt = max(0.0, min(1.0, ((x - x1) * vx + (y - y1) * vy) / max(1e-9, vx * vx + vy * vy)))
        if math.hypot(x - x1 - tt * vx, y - y1 - tt * vy) < margin:
            return True
    return inside


def build_wing(b):
    scale_palette()
    material('vein', h('5a1c10'), h('4a160c'), spec=0.4, refl=40)
    blib.PALETTE['vein'].update(scale=3.0, cavity=0.5)
    b.tiny_px = 0
    b.ao_distance = 4.0
    b.emboss = dict(k=1.3)
    left_wing(b)


def build_crust(b):
    """His long pale belly 'crusted with gems and fragments of gold from his long lying on his costly bed' (the
    'waistcoat of fine diamonds'), but for the bare patch in the hollow of his left breast."""
    treasure_palette()
    coin_palette()
    b.tiny_px = 0
    b.ao_distance = 1.5
    rng = random.Random(1941)
    cam = Vector((0.0, -0.62, 0.78))
    patch = None
    for (p, t, side, up, sn) in spine():
        if not 22.0 <= sn <= 72.0 or rng.random() < 0.25:
            continue
        for _ in range(5):
            th = math.pi + rng.uniform(-1.15, 1.15)
            y, z = section(th, sn)
            q = p + side * y + up * z
            nrm = (side * math.sin(th) * 0.8 + up * math.cos(th)).normalized()
            if nrm.dot(cam) < 0.05 or q.z < height(q.x, q.y) + 0.3:
                continue
            if patch is None and 33.0 < sn < 35.0:
                y2, z2 = section(math.pi - 0.5, sn)          # the hollow of his LEFT breast (left = +side here)
                patch = p + side * y2 + up * z2
            if patch is not None and (q - patch).length < 2.2:
                continue
            R = nrm.to_track_quat('Z', 'X').to_matrix().to_4x4() @ Matrix.Rotation(rng.uniform(0, 6.3), 4, 'Z')
            if rng.random() < 0.62:
                r = rng.uniform(0.22, 0.5)
                ellipsoid(b, rng.choice(('gemR', 'gemR', 'gemG', 'gemB', 'gemP', 'arken')), tuple(q + nrm * r * 0.1),
                          (r, r * 0.8, r * 0.38), n=6, rings=3, R=R)
            else:
                r = rng.uniform(0.35, 0.6)
                lathe(b, rng.choice(('coin1', 'coin2', 'coin3')), [(0.0, 0.0), (r, 0.0), (r, 0.1), (0.0, 0.1)], 7,
                      M=Matrix.Translation(q - nrm * 0.02) @ R, smooth=True)


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

STATIC_PARTS = [('gold', build, 2048), ('body', build_body, 2048), ('head', build_head, 2048),
                ('limbs', build_limbs, 2048), ('wing', build_wing, 2048)]
# 2026-11-26: the belly crust (build_crust) is out: in game its gems and coin bits read as 'jelly beans' (the user).

PREVIEW = [((-4, -58, 38), (-4, -18, 18), 44),            # the head on the gold
           ((-14, -37, 15), (-9.4, -27.9, 7.2), 34),      # the closed eye, close
           ((10, -60, 50), (2, 2, 22), 38),               # the belly turned to the camera
           ((70, -45, 50), (8, 0, 20), 36),               # the wing and the hind leg from the south-east
           ((-70, -40, 55), (-6, 0, 18), 36),             # from the south-west
           ((2, -62, 46), (2, -12, 10), 40)]              # the left wing spread on the gold
PREVIEW_EYE = [((0, -220, 190), (0, 0, 10), 38)]
