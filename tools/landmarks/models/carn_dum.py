"""Carn Dûm, the Red Halls of Angmar: the Witch-king's capital (an IMPROVEMENT, docs/LANDMARKS.md). 2026-11-26.

The user: "MAKE THE MOST IMPRESSIVE CARN DUM AS YOU CAN IMAGINE ... consistent in look and feel with the works of
Tolkien"; the starting reference screenshots/carn-dum.webp: two colossal jagged spires of rock, the fortress built into
their feet and glowing red from within, long arched causeways across a snowy range, a cold light in the storm between
the peaks. (The Minas Morgul model made first for this city is kept: models/minas_morgul.py, on Minas Morgul.)

Research (2026-11-26):
  * Tolkien (Appendix A; the place-names): the Witch-king's capital lay "beneath the northernmost peak" of the
    Mountains of Angmar, the cold northern arc of the Misty Mountains on the border of the Northern Waste (Forodwaith).
    Angmar = "Iron Home"; Carn Dûm most likely "Red Halls" (carn 'red' + dûm 'halls', as in Khazad-dûm) - a mountain
    fortress, not a valley.
  * The Lord of the Rings Online: "a massive fortified city" on the slopes of the mountain, "accessed by winding
    streets"; iron gates in the cliff faces; trolls mining the cliffs on ledges; "scaffolding outside the tower"; the
    castle above with a balcony looking out over the city (the Witch-king's Watch) and his seat by a pit of lava;
    poisonous green "fell-water" in the pits below; ruined towers.
  * The Battle for Middle-earth II, The Rise of the Witch-king: the Angmar fortress "resembles a crown, as well as the
    apex of Carn Dûm"; dark iron everywhere.

The landmark (in-game units, Scale 0.25 written x4; origin = the tile centre, ground z 0, -Y = south = the camera;
the whole fits its own hex): the northernmost peak split into TWO great spires of dark, snow-ledged rock (132 and 116
high) rising from the massif; the Red Halls carved into their faces (rows of fire-lit windows, galleries, iron
walkways, iron scaffolding and mining ledges); between them the Witch-king's keep with its CROWN of iron tines and the
Watch; below, the city of red stone climbing four walled terraces by a grand stair through gate after gate; houses
under steep snow-laden roofs, their windows red; arched causeways leaving east and west; the outer gate of iron; a
pool of fell-water. Fire (the Balrog's proven shader fire, red): forges and braziers; the crown burning; cold clouds
wrapping the spires; a pale light between their tips.
"""
import math
import random
import zlib

import numpy as np
from mathutils import Vector

import blib
import sdf
from blib import material, hexcol as h
from minas_morgul import (loft, tube, thorn, panel, arch_pts, ngon, normals2, wall_strip, oriented, to_hires,
                          sdf_finish, hex_d)

BAKE = True
BAKE_PX = 2048
EYE_PX = 512
EYE_AO = 16
PART_AO = 24
HEX = 33.6

# --------------------------------------------------------------------------- the plan
CC = (0.0, 20.0)                       # the centre of the terraces' arcs (under the castle)
TERR = [(46.0, 7.0), (34.0, 15.0), (24.0, 24.0), (14.0, 33.0)]   # (radius of the front wall, floor level)
CITY_W = 22.0                          # the city's half-width (the massif's shoulders flank it)
KEEP_C = (0.0, 14.5)
KEEP_Z0 = 33.0
KEEP_TOP = 82.0
CROWN_TOP = 100.0
WATCH_Z = 62.0

SPIRES = [  # axis points (x, y, z) and radii: the west spire taller, both leaning in a little
    dict(axis=[(-13.0, 23.0, 14.0), (-12.0, 23.0, 40.0), (-10.0, 23.5, 70.0), (-7.8, 24.0, 100.0), (-5.6, 24.5, 132.0)],
         radii=[11.0, 8.5, 6.2, 3.8, 0.4]),
    dict(axis=[(13.5, 24.0, 14.0), (12.5, 24.0, 38.0), (10.8, 24.5, 64.0), (9.0, 25.0, 92.0), (7.4, 25.5, 116.0)],
         radii=[10.0, 7.8, 5.6, 3.2, 0.4]),
]


def terrace_z(x, y):
    """The city's floor level at (x, y) (arrays): the terraces step up towards the peaks; 0 outside the city."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    d = np.hypot(x - CC[0], y - CC[1])
    z = np.zeros_like(d)
    for R, lv in TERR:
        z = np.where(d <= R, lv, z)
    inside = (np.abs(x) <= CITY_W) & (y <= CC[1] + 2.0) & (d <= TERR[0][0])
    return np.where(inside, z, -1.0)


# --------------------------------------------------------------------------- materials
def palette():
    # the peaks: dark, cold granite; snow on the ledges
    material('peak', h('2a2d31'), h('363a40'), spec=0.15, refl=10)
    blib.PALETTE['peak'].update(scale=0.25, cavity=0.9, vcracks=(0.7, 0.4), snow=(26.0, 44.0, 0.5))
    material('rock', h('2c2b2c'), h('393637'), spec=0.12, refl=8)
    blib.PALETTE['rock'].update(scale=0.3, cavity=0.9, vcracks=(0.8, 0.35), snow=(10.0, 26.0, 0.55))
    # the Red Halls: dark red-brown stone, coursed
    material('red', h('4f2b25'), h('3d221d'), spec=0.2, refl=14, courses=0.0)
    blib.PALETTE['red'].update(scale=0.6, cavity=0.85, vcracks=(1.2, 0.25))
    material('redDim', h('4a2822'), h('3a1f1a'), spec=0.18, refl=12)
    blib.PALETTE['redDim'].update(scale=0.6, cavity=0.85, vcracks=(0.9, 0.25))
    material('house', h('4c2c25'), h('3b231e'), spec=0.18, refl=12)
    blib.PALETTE['house'].update(scale=0.9, cavity=0.7, windows=dict(fx=1.1, fz=1.3, w=(0.35, 0.62), h=(0.3, 0.72),
                                                                      color=h('ff9a3c')))
    # iron: black, a little rust, glossy
    material('iron', h('17171a'), h('231f1d'), spec=0.6, refl=70)
    blib.PALETTE['iron'].update(scale=1.2, cavity=0.6, speckle=[(1.8, 0.12, h('4a2a1a'))])
    material('roof', h('1c1c1f'), h('26262a'), spec=0.35, refl=30)
    blib.PALETTE['roof'].update(scale=1.4, cavity=0.7, snow=(0.0, 4.0, 0.8))
    material('pave', h('3a3432'), h('2e2927'), spec=0.15, refl=10)
    blib.PALETTE['pave'].update(scale=0.7, cavity=0.6, snow=(0.0, 4.0, 0.92))
    material('step', h('2f2a28'), h('262220'), spec=0.15, refl=10)
    blib.PALETTE['step'].update(scale=0.9, cavity=0.7)
    # fire-light (no AO: it shines)
    material('fire', h('ff8a3a'), h('e8551c'), spec=0.0, refl=0, ao=False)
    material('ember', h('ff6a1e'), h('c93f10'), spec=0.0, refl=0, ao=False)
    material('fell', h('5fd17a'), h('2e8c4b'), spec=0.6, refl=90, ao=False)      # the fell-water
    material('dark', h('0b0908'), h('120e0c'), spec=0.0, refl=0, ao=False)


def mats_for(name):
    return lambda cen: [name] * len(cen)


# --------------------------------------------------------------------------- the massif (static main part)
KNOBS = [(-31.0, 2.0, 27.0, 4.2), (31.0, 2.0, 27.0, 4.2), (-28.0, 14.0, 34.0, 5.5), (28.0, 14.0, 32.0, 5.5),
         (-20.0, 28.0, 40.0, 6.0), (20.0, 28.0, 38.0, 6.0), (0.0, 33.0, 42.0, 5.0)]


def massif_h(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    t = np.clip((y + 8.0) / 34.0, 0, 1)
    base = 46.0 * t * t * (3 - 2 * t) * (1.0 - 0.25 * np.clip(np.abs(x) / 30.0, 0, 1))
    k = np.zeros_like(x)
    for (kx, ky, a, r) in KNOBS:
        k = np.maximum(k, a * np.exp(-((x - kx) ** 2 + (y - ky) ** 2) / (r * r)))
    hh = np.maximum(base, k)
    tz = terrace_z(x, y)
    hh = np.where(tz >= 0, tz - 0.4, hh)                                         # the city's floors
    hd = np.maximum(np.abs(x), 0.5 * np.abs(x) + 0.8660254 * np.abs(y))
    edge = np.clip((HEX - 0.9 - hd) / 2.8, 0, 1)
    return hh * edge + (edge - 1.0) * 2.5


def rock_noise(amp, f, seed, zs=1.0, flute=0.0):
    def fn(X, Y, Z):
        x, y, z = X * f, Y * f, Z * f * zs
        v = amp * (0.6 * sdf.fbm3(x * 0.16, y * 0.16, z * 0.16, 3, seed)
                   - 0.6 * (sdf.ridged3(x * 0.12, y * 0.12, z * 0.035, 3, seed + 7) - 0.5)
                   + 0.25 * sdf.fbm3(x * 0.7, y * 0.7, z * 0.7, 2, seed + 3))
        if flute:          # sharp vertical fluting (columns of rock), broken by ledges
            v = v - flute * (sdf.ridged3(X * 0.3, Y * 0.3, Z * 0.025, 2, seed + 11) - 0.5) \
                + flute * 0.5 * np.clip(sdf.fbm3(X * 0.05, Y * 0.05, Z * 0.35, 2, seed + 13) - 0.55, 0, 1)
        return v
    return fn


def build(b, eye=False):
    """The static main part: the massif under the peaks (its shoulders flanking the city, the knobs the causeways
    land on), the city's rock floors, the terraces' paving and fronts, the fell-water."""
    palette()
    rng = random.Random(5)
    f = sdf.Field((-35, -40, -1.0), (35, 40, 46.0), 0.4, far=3.0)

    def m(X, Y, Z):
        return (Z - massif_h(X, Y)) * 0.7
    f.add((m, (np.array([-35.0, -40.0, -1.0]), np.array([35.0, 40.0, 46.0]))), k=0)
    for i in range(40):                                     # broken buttresses on the shoulders
        a = rng.uniform(0, 2 * math.pi)
        x, y = rng.uniform(-31, 31), rng.uniform(-6, 33)
        if hex_d(x, y) > HEX - 3.0 or float(terrace_z(x, y)) >= 0:
            continue
        z = float(massif_h(x, y))
        if z < 3.0:
            continue
        s = rng.uniform(2.0, 4.5)
        f.add(sdf.rbox((x, y, z - s * 0.4), (s, s * rng.uniform(0.6, 1.0), s * rng.uniform(1.2, 2.4)),
                       np.array(blib.T(rz=math.degrees(a), rx=rng.uniform(-15, 15)).to_3x3()), rad=0.3), k=1.0)
    f.displace(rock_noise(1.2, 1.0, 9), band=3.0)

    def keep(X, Y, Z):
        return np.maximum(np.maximum(np.abs(X), 0.5 * np.abs(X) + 0.8660254 * np.abs(Y)) - (HEX - 0.4), -0.3 - Z)
    f.intersect((keep, None))
    f.F[:, :, :3] = np.maximum(f.F[:, :, :3], 0.5)
    sdf_finish(b, f, 17000, 'rock')
    f0 = len(b.faces)
    terraces(b)
    fellwater(b)
    to_hires(b, f0)


def sector_poly(R, n=48, back=None):
    """The terrace of radius R: the front arc (|x| <= CITY_W) closed along the line y = back, counter-clockwise."""
    back = CC[1] + 2.0 if back is None else back
    pts = []
    for i in range(n + 1):
        a = math.pi + math.pi * i / n
        x, y = CC[0] + R * math.cos(a), CC[1] + R * math.sin(a)
        if abs(x) <= CITY_W and y <= back:
            pts.append((x, y))
    if pts[0][1] < back - 0.01:                         # the arc ends at |x| = CITY_W: up the sides to the back line
        xl, xr = pts[0][0], pts[-1][0]
        pts = pts + [(xr, back), (xl, back)]
    return pts


def terraces(b):
    """Paved floors (rock under them is the massif); their fronts are the walls (walls part)."""
    for R, lv in TERR:
        blib.prism(b, 'pave', sector_poly(R - 0.3), -1.0, lv + 1.0)


def fellwater(b):
    """The fell-water: a sickly green pool in the pits below the west shoulder, fed by a falling stream."""
    cx, cy = -23.0, -11.0
    pts = [(cx + 4.2 * math.cos(a) * (1 + 0.15 * math.sin(3 * a)), cy + 2.8 * math.sin(a)) for a in
           np.linspace(0, 2 * math.pi, 25)[:-1]]
    blib.prism(b, 'fell', pts, -0.3, 0.45)
    v, fc = [], []
    for i in range(12):                                 # the stream falling from the shoulder
        t = i / 11
        x = cx - 1.0 + 0.6 * math.sin(t * 5)
        y = cy + 2.6 + 6.0 * t
        z = float(massif_h(x, y + 0.8)) + 0.25
        v += [(x - 0.45, y, z), (x + 0.45, y, z)]
    for i in range(11):
        a = 2 * i
        fc.append(oriented(v, (a, a + 1, a + 3, a + 2), (0, -1, 1)))
    b.add(v, fc, 'fell')


# --------------------------------------------------------------------------- the peaks (extra static)
_FIELD = {}


NEEDLES = [(-16.0, 28.0, 30.0, 64.0, 3.4), (16.5, 29.0, 30.0, 58.0, 3.2), (-22.5, 15.0, 22.0, 52.0, 3.4),
           (22.5, 16.0, 22.0, 48.0, 3.2), (-25.0, 6.0, 18.0, 38.0, 2.6), (25.0, 7.0, 18.0, 36.0, 2.6),
           (-3.0, 31.0, 34.0, 70.0, 3.0)]


def peaks_field():
    """The two spires as one SDF field (cached: other parts find the rock faces in it)."""
    if 'f' in _FIELD:
        return _FIELD['f']
    f = sdf.Field((-30, -2, 12.0), (28, 37, 135.0), 0.42, far=3.0)
    for sp in SPIRES:
        A, R = sp['axis'], sp['radii']
        for (p, q), (ra, rb) in zip(zip(A, A[1:]), zip(R, R[1:])):
            f.add(sdf.cone(p, q, ra * 0.72, rb * 0.72), k=1.5)          # the core (the ribs make the surface)
        # knife-edged ribs round each spire, ending at different heights in points of their own: the ragged,
        # many-pointed silhouette of the reference
        rng = random.Random(int(A[0][0] * 10) & 0xffff)
        ztop = A[-1][2]
        for j in range(9):
            ang = 2 * math.pi * j / 9 + rng.uniform(-0.25, 0.25)
            off = rng.uniform(0.72, 0.9)
            scl = rng.uniform(0.36, 0.52)
            top = ztop * (rng.uniform(0.9, 0.99) if j in (2, 6) else rng.uniform(0.38, 0.85))
            pts, rr = [], []
            for z in np.linspace(A[0][2], top, 7):
                c, r = axis_at(sp, z)
                fall = 1.0 - ((z - A[0][2]) / (top - A[0][2])) ** 1.6
                pts.append((c.x + math.cos(ang) * r * off, c.y + math.sin(ang) * r * off, z))
                rr.append(max(0.25, r * scl * (0.35 + 0.65 * fall)))
            for (p, q), (ra, rb) in zip(zip(pts, pts[1:]), zip(rr, rr[1:])):
                f.add(sdf.cone(p, q, ra, rb), k=0.5)
            tip = (pts[-1][0] + math.cos(ang) * 0.8, pts[-1][1] + math.sin(ang) * 0.8, top + rr[-1] * 4.0)
            f.add(sdf.cone(pts[-1], tip, rr[-1], 0.2), k=0.8)
    for (x, y, z0, z1, r) in NEEDLES:                  # lesser needles of rock on the shoulders
        f.add(sdf.cone((x, y, z0), ((x * 0.97), y + 0.5, z1), r, 0.25), k=1.5)
    f.displace(rock_noise(1.6, 1.0, 17, zs=0.55, flute=1.6), band=3.6)

    def keep(X, Y, Z):
        return np.maximum(np.maximum(np.abs(X), 0.5 * np.abs(X) + 0.8660254 * np.abs(Y)) - (HEX - 0.5), 13.0 - Z)
    f.intersect((keep, None))
    f.sub(sdf.cone((KEEP_C[0], KEEP_C[1], 20.0), (KEEP_C[0], KEEP_C[1], 100.0), 8.0, 6.0), k=1.0)   # room for the keep
    _FIELD['f'] = f
    return f


def field_at(f, P):
    """Trilinear sample of a field's grid at points P (N x 3)."""
    P = np.atleast_2d(np.asarray(P, float))
    g = (P - f.lo) / f.step
    i0 = np.clip(np.floor(g).astype(int), 0, f.n - 2)
    t = np.clip(g - i0, 0, 1)
    out = np.zeros(len(P))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (t[:, 0] if dx else 1 - t[:, 0]) * (t[:, 1] if dy else 1 - t[:, 1]) * (t[:, 2] if dz else 1 - t[:, 2])
                out += w * f.F[i0[:, 0] + dx, i0[:, 1] + dy, i0[:, 2] + dz]
    return out


def rock_face(start, direction, max_d=30.0):
    """March from start along direction until the peaks' rock: the point on the face (Vector) and the face's normal
    (2D, outwards), or None."""
    f = peaks_field()
    d = Vector(direction).normalized()
    p = Vector(start)
    prev = field_at(f, [tuple(p)])[0]
    s = 0.0
    while s < max_d:
        q = p + d * s
        v = field_at(f, [tuple(q)])[0]
        if v < 0 and prev >= 0:
            e = 0.3
            gx = field_at(f, [tuple(q + Vector((e, 0, 0)))])[0] - field_at(f, [tuple(q - Vector((e, 0, 0)))])[0]
            gy = field_at(f, [tuple(q + Vector((0, e, 0)))])[0] - field_at(f, [tuple(q - Vector((0, e, 0)))])[0]
            L = math.hypot(gx, gy) or 1.0
            return q - d * 0.15, (gx / L, gy / L)
        prev = v
        s += 0.15
    return None


def axis_at(sp, z):
    A, R = sp['axis'], sp['radii']
    for (p, q), (ra, rb) in zip(zip(A, A[1:]), zip(R, R[1:])):
        if p[2] <= z <= q[2]:
            t = (z - p[2]) / (q[2] - p[2])
            return Vector(p).lerp(Vector(q), t), ra + (rb - ra) * t
    return Vector(A[-1]), R[-1]


def build_peaks(b):
    """The two spires of the northernmost peak (SDF, ridged, snow on the ledges)."""
    palette()
    sdf_finish(b, peaks_field(), 27000, 'peak')


# --------------------------------------------------------------------------- the Red Halls in the peaks (extra static)
FIRES = []          # (x, y, z, scale): the forges and braziers (red fire), found while building
CROWN_FIRES = []


def build_halls(b):
    """What is cut into and hung on the peaks: rows of fire-lit windows (the Red Halls inside the mountain), carved
    galleries with iron walkways, the iron scaffolding and the mining ledges (LOTRO), the flying bridges to the keep."""
    palette()
    rng = random.Random(23)
    for si, sp in enumerate(SPIRES):
        ztop = sp['axis'][-1][2]
        for z in np.arange(44.0, ztop - 26.0, 7.5):
            c, r = axis_at(sp, z)
            n_win = 4 if z < 80 else 2
            for j in range(n_win):
                ang = -math.pi / 2 + (j - (n_win - 1) / 2) * (0.32 if z < 80 else 0.4) + (0.25 if si else -0.25)
                hit = rock_face(c + Vector((math.cos(ang), math.sin(ang), 0)) * (r + 6.0),
                                (-math.cos(ang), -math.sin(ang), 0), max_d=r + 8.0)
                if not hit:
                    continue
                p, nrm = hit
                if rng.random() < 0.35:
                    continue
                p = p + Vector((0, 0, rng.uniform(-2.0, 2.0)))
                hgt = rng.uniform(1.3, 2.2) * (1.25 if z < 60 else 1.0)
                panel(b, 'dark', (p.x - nrm[0] * 0.05, p.y - nrm[1] * 0.05, p.z - hgt * 0.4), nrm,
                      arch_pts(0.42 * hgt / 2.2 + 0.1, hgt + 0.6), depth=0.25)
                panel(b, 'fire', (p.x + nrm[0] * 0.05, p.y + nrm[1] * 0.05, p.z - hgt * 0.4), nrm,
                      arch_pts(0.3 * hgt / 2.2 + 0.07, hgt), depth=0.25)
        # galleries: ledges cut round the south faces with iron railings, every so often
        for z in ((52.0, 78.0, 98.0) if si == 0 else (48.0, 72.0)):
            gallery(b, sp, z, rng)
    scaffold(b, rng)
    for s, sp in ((-1, SPIRES[0]), (1, SPIRES[1])):            # flying bridges from the keep to the spires
        c, r = axis_at(sp, 66.0)
        hit = rock_face(Vector((KEEP_C[0] + s * 4.0, KEEP_C[1] + 1.0, 66.0)), (s, 0.15, 0), max_d=30)
        if not hit:
            continue
        p, nrm = hit
        a = Vector((KEEP_C[0] + s * 5.2, KEEP_C[1] + 0.5, 64.6))
        flying_bridge(b, a, p + Vector((0, 0, -1.4)))


def gallery(b, sp, z, rng):
    """A ledge carved round a spire's south face: a slab walk on iron brackets with a railing and posts."""
    c, r = axis_at(sp, z)
    pts = []
    for k in range(13):
        ang = -math.pi / 2 + (k - 6) * 0.17
        hit = rock_face(c + Vector((math.cos(ang), math.sin(ang), 0)) * (r + 6.0), (-math.cos(ang), -math.sin(ang), 0),
                        max_d=r + 8.0)
        if hit:
            pts.append(hit)
    if len(pts) < 4:
        return
    secs = []
    for p, nrm in pts:
        N = Vector((nrm[0], nrm[1], 0))
        secs.append((p - N * 0.6, p + N * 1.4))
    for (a0, a1), (b0, b1) in zip(secs, secs[1:]):
        v = [tuple(a0), tuple(a1), tuple(b1), tuple(b0)]
        v += [tuple(Vector(q) - Vector((0, 0, 0.45))) for q in v]
        fcs = [oriented(v, (0, 1, 2, 3), (0, 0, 1)), oriented(v, (4, 5, 6, 7), (0, 0, -1)),
               oriented(v, (1, 2, 6, 5), (a1 - a0).normalized()), oriented(v, (0, 3, 7, 4), (a0 - a1).normalized())]
        b.add(v, fcs, 'red')
    rail = [s1 + Vector((0, 0, 1.0)) for _, s1 in secs]
    for q0, q1 in zip(rail, rail[1:]):
        blib.strut(b, 'iron', q0, q1, 0.07, 0.07, n=4)
    for _, s1 in secs[::2]:
        blib.strut(b, 'iron', s1, s1 + Vector((0, 0, 1.05)), 0.09, 0.09, n=4)
        blib.strut(b, 'iron', s1 - Vector((0, 0, 0.4)), s1 - Vector((0, 0, 2.2)) - (s1 - secs[0][0]) * 0.0, 0.08, 0.05, n=4)
    mid = secs[len(secs) // 2][1]
    FIRES.append((mid.x, mid.y, mid.z + 0.2, 0.7))


def scaffold(b, rng):
    """Iron scaffolding on the east spire's flank (LOTRO: "scaffolding outside the tower"): uprights, ledgers,
    braces, plank decks; and the mining ledges below it with heaps of spoil."""
    sp = SPIRES[1]
    for z0 in (38.0, 46.0, 54.0, 62.0):
        c, r = axis_at(sp, z0)
        for k in range(5):
            ang = -0.25 - k * 0.2
            hit = rock_face(c + Vector((math.cos(ang), math.sin(ang), 0)) * (r + 7.0),
                            (-math.cos(ang), -math.sin(ang), 0), max_d=r + 9.0)
            if not hit:
                continue
            p, nrm = hit
            N = Vector((nrm[0], nrm[1], 0))
            out = p + N * 2.2
            blib.strut(b, 'iron', out, out + Vector((0, 0, 8.0)), 0.12, 0.12, n=4)
            blib.strut(b, 'iron', out, p + N * 0.2 + Vector((0, 0, 3.0)), 0.07, 0.07, n=4)
            blib.strut(b, 'iron', out + Vector((0, 0, 4.0)), p + N * 0.2 + Vector((0, 0, 7.0)), 0.07, 0.07, n=4)
            T = Vector((-N.y, N.x, 0))
            v = [tuple(out + T * 1.1 + Vector((0, 0, 4.0))), tuple(out - T * 1.1 + Vector((0, 0, 4.0))),
                 tuple(p - T * 1.1 + Vector((0, 0, 4.0))), tuple(p + T * 1.1 + Vector((0, 0, 4.0)))]
            b.add(v, [oriented(v, (0, 1, 2, 3), (0, 0, 1))], 'pave')
            if k == 2 and z0 == 46.0:
                FIRES.append((out.x, out.y, out.z + 4.2, 0.6))


def flying_bridge(b, a, c):
    """A narrow arched bridge of red stone with an iron rail, from the keep to a spire's face."""
    n = 10
    d = c - a
    side = Vector((-d.y, d.x, 0)).normalized()
    secs = []
    for i in range(n + 1):
        t = i / n
        p = a.lerp(c, t) + Vector((0, 0, -2.2 * math.sin(math.pi * t) * 0 + 0.0))
        under = 1.6 + 2.2 * (1 - math.sin(math.pi * t))
        secs.append([p - side * 0.9 - Vector((0, 0, under)), p + side * 0.9 - Vector((0, 0, under)), p + side * 0.9,
                     p - side * 0.9])
    loft(b, 'red', secs)
    for s in (-1, 1):
        blib.strut(b, 'iron', a + side * 0.85 * s + Vector((0, 0, 0.9)), c + side * 0.85 * s + Vector((0, 0, 0.9)),
                   0.06, 0.06, n=4)


# --------------------------------------------------------------------------- the city: walls, gates, houses, stair
def arc_pts(R, z=None, step=1.2):
    """The front wall of a terrace: its arc within |x| <= CITY_W, counter-clockwise (west to east)."""
    n = max(8, int(math.pi * R / step))
    out = []
    for i in range(n + 1):
        a = math.pi + math.pi * i / n
        x, y = CC[0] + R * math.cos(a), CC[1] + R * math.sin(a)
        if abs(x) <= CITY_W and y <= CC[1] + 2.0:
            out.append((x, y))
    return out


def iron_crenels(b, pts, nrms, z, rng, big=1.0):
    """Crenellations of Angmar: blocky merlons with an iron spike on each."""
    for k in range(0, len(pts), 2):
        (x, y), (nx, ny) = pts[k], nrms[k]
        blib.box(b, 'red', x + nx * 0.45, y + ny * 0.45, z, 0.75, 0.75, 0.9, rz=math.degrees(math.atan2(ny, nx)))
        thorn(b, 'iron', (x + nx * 0.45, y + ny * 0.45, z + 0.9), (nx, ny), rng.uniform(0.9, 1.5) * big, 0.13,
              curl=0.1, lean=0.05, sides=4, n=2)


def tower(b, rng, x, y, z0, z1, r, roof=True, fire=True, n=8):
    """A square-ish (octagonal) tower of red stone: battered foot, machicolated top with iron spikes, a steep iron
    roof under snow, slit windows of fire."""
    secs = [ngon(x, y, z0, r * 1.3, n, math.pi / n), ngon(x, y, z0 + 2.5, r, n, math.pi / n),
            ngon(x, y, z1 - 1.0, r * 0.95, n, math.pi / n), ngon(x, y, z1 - 0.6, r * 1.22, n, math.pi / n),
            ngon(x, y, z1 + 0.6, r * 1.22, n, math.pi / n)]
    loft(b, 'red', secs)
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        thorn(b, 'iron', (x + math.cos(a) * r * 1.15, y + math.sin(a) * r * 1.15, z1 + 0.6), (math.cos(a), math.sin(a)),
              1.1, 0.12, curl=0.15, sides=4, n=2)
    if roof:
        hr = rng.uniform(1.6, 2.4) * r
        loft(b, 'roof', [ngon(x, y, z1 + 0.6, r * 1.05, n, math.pi / n)], apex=(x, y, z1 + 0.6 + hr), cap0=False)
        tube(b, 'iron', [(x, y, z1 + 0.6 + hr - 0.3), (x, y, z1 + 0.6 + hr + 1.6)], [0.12, 0.0], sides=4)
    for k in range(3):
        a = -math.pi / 2 + (k - 1) * 0.7
        c = (x + math.cos(a) * r * 0.97, y + math.sin(a) * r * 0.97, z0 + 3.0 + (z1 - z0 - 5) * rng.uniform(0.2, 0.8))
        panel(b, 'fire', c, (math.cos(a), math.sin(a)), [(-0.18, 0.0), (0.18, 0.0), (0.18, 1.1), (0.0, 1.35),
                                                          (-0.18, 1.1)], depth=0.06)
    if fire and not roof:
        FIRES.append((x, y, z1 + 0.7, 0.8))


def build_city(b):
    """The four terraces' walls (red stone, battered, spiked), gatehouses at the grand stair, the stair itself,
    the outer gate of iron, ~170 houses and halls under snowy roofs, forge yards."""
    palette()
    rng = random.Random(31)
    prev = 0.0
    for i, (R, lv) in enumerate(TERR):
        pts = arc_pts(R)
        nrm = normals2(pts, closed=False)
        gap = 2.4 if i else 3.2
        west = [(p, q) for p, q in zip(pts, nrm) if p[0] < -gap]
        east = [(p, q) for p, q in zip(pts, nrm) if p[0] > gap]
        for run in (west, east):
            if len(run) < 2:
                continue
            P = [p for p, _ in run]
            Nn = [q for _, q in run]
            wall_strip(b, 'red', P, Nn, lv, lv + 3.2, 1.6, 1.2, z_out=prev - 1.2)
            iron_crenels(b, P, Nn, lv + 3.2, rng, 1.0 + 0.2 * i)
            # wall towers at the ends and in between
            for k in sorted({0, len(P) - 1} | set(range(6, len(P) - 4, 9))):
                (x, y), (nx, ny) = P[k], Nn[k]
                tower(b, rng, x + nx * 0.6, y + ny * 0.6, prev - 0.5, lv + rng.uniform(6.5, 9.5), 1.6,
                      roof=rng.random() < 0.6)
        # the gatehouse on the stair
        gy = CC[1] - R
        for s in (-1, 1):
            tower(b, rng, s * (gap + 1.6), gy, prev - 0.5, lv + 9.0 + 2.0 * i, 2.0, roof=False)
        blib.box(b, 'red', 0, gy, lv + 4.5, 2 * gap + 1.0, 2.2, 3.0 + i)                   # the arch's lintel
        panel(b, 'dark', (0, gy - 1.12, prev), (0, -1), arch_pts(gap * 0.8, lv - prev + 3.8), depth=0.04)
        panel(b, 'ember', (0, gy - 1.14, prev), (0, -1), arch_pts(gap * 0.45, (lv - prev + 3.8) * 0.55), depth=0.04)
        if i == 0:
            outer_gate(b, gy, rng)
        prev = lv
    stair(b)


def build_town(b):
    """The houses and halls of the terraces under snowy roofs, and the forge yards."""
    palette()
    rng = random.Random(37)
    placed = [(0.0, 0.0, 0.0)]
    for (x, y) in ((-12.0, -4.0), (12.0, -5.0), (-8.0, 7.0), (9.0, 6.0)):
        forge(b, x, y, float(terrace_z(x, y)))
        placed.append((x, y, 2.4))
    for i in range(len(TERR)):
        R0, lv = TERR[i]
        R1 = TERR[i + 1][0] if i + 1 < len(TERR) else 0.0
        if i == len(TERR) - 1:
            break
        houses(b, rng, placed, R0, R1, lv, 12000)


def outer_gate(b, gy, rng):
    """The outer gate: two great iron doors studded and spiked, a portcullis half raised, the fire beyond it."""
    for s in (-1, 1):
        v = [(s * 0.1, gy - 1.3, 0.0), (s * 2.9, gy - 1.3, 0.0), (s * 2.9, gy - 1.3, 6.3), (s * 0.1, gy - 1.3, 8.2)]
        v += [(x, y + 0.35, z) for x, y, z in v]
        fcs = [oriented(v, (0, 1, 2, 3), (0, -1, 0)), oriented(v, (4, 5, 6, 7), (0, 1, 0)),
               oriented(v, (1, 2, 6, 5), (s, 0, 0)), oriented(v, (2, 3, 7, 6), (0, 0, 1))]
        b.add(v, fcs, 'iron')
        for zz in (1.4, 3.4, 5.4):
            for xx in (0.7, 1.5, 2.3):
                thorn(b, 'iron', (s * xx, gy - 1.35, zz), (0, -1), 0.6, 0.12, curl=0.0, lean=0.0, sides=4, n=1)
    FIRES.append((0.0, gy + 1.2, 7.0, 0.9))


def stair(b):
    """The grand stair up the middle, from the outer gate to the keep's court."""
    prev = 0.0
    for R, lv in TERR:
        y1 = CC[1] - R                         # the wall's line (top of this flight)
        y0 = y1 - (lv - prev) * 1.05 - 0.6    # foot of the flight
        n = max(4, int((lv - prev) / 0.55))
        for k in range(n):
            t0 = k / n
            z = prev + (lv - prev) * (k + 1) / n
            ya = y0 + (y1 - y0) * t0
            blib.box(b, 'step', 0, ya + (y1 - y0) / n / 2 + 0.6, prev - 0.5, 3.4, (y1 - y0) / n + 1.2, z - prev + 0.5)
        for s in (-1, 1):                      # balustrade walls
            v = [(s * 1.9, y0, prev - 0.5), (s * 1.9, y1 + 1.5, prev - 0.5), (s * 1.9, y1 + 1.5, lv + 1.0),
                 (s * 1.9, y0, prev + 1.0)]
            v += [(x + s * 0.4, y, z) for x, y, z in v]
            fcs = [oriented(v, (0, 1, 2, 3), (-s, 0, 0)), oriented(v, (4, 5, 6, 7), (s, 0, 0)),
                   oriented(v, (2, 3, 7, 6), (0, -0.5, 1)), oriented(v, (0, 3, 7, 4), (0, -1, 0))]
            b.add(v, fcs, 'red')
        prev = lv


def houses(b, rng, placed, R0, R1, lv, tries):
    n = 0
    for _ in range(tries):
        x, y = rng.uniform(-CITY_W, CITY_W), rng.uniform(CC[1] - R0, CC[1] + 2)
        d = math.hypot(x - CC[0], y - CC[1])
        if not (R1 + 2.0 < d < R0 - 1.8) or abs(x) < 2.6 or abs(x) > CITY_W - 1.0 or y > CC[1] - 1.0:
            continue
        if math.hypot(x + 23, y + 11) < 6:
            continue
        big = rng.random() < 0.12
        w, dd = (rng.uniform(3.2, 4.6), rng.uniform(2.4, 3.2)) if big else (rng.uniform(1.6, 2.7), rng.uniform(1.6, 2.5))
        r_ = 0.42 * math.hypot(w, dd)
        if any(math.hypot(x - px, y - py) < r_ + pr + 0.05 for px, py, pr in placed):
            continue
        placed.append((x, y, r_))
        a = math.degrees(math.atan2(y - CC[1], x - CC[0])) + 90.0       # along the terrace
        hh = rng.uniform(2.6, 5.0) * (1.4 if big else 1.0)
        blib.box(b, 'house', x, y, lv - 0.6, w, dd, hh + 0.6, rz=a)
        blib.gable(b, 'roof', x, y, lv + hh, w, dd, rng.uniform(2.0, 3.2) * (1.3 if big else 1.0), rz=a, overhang=0.2)
        if rng.random() < 0.3:                   # a chimney
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            cx, cy = x + ca * w * 0.3, y + sa * w * 0.3
            blib.box(b, 'red', cx, cy, lv + hh, 0.45, 0.45, 2.6)
        n += 1
    print('  houses on terrace %.0f: %d' % (lv, n))


def forge(b, x, y, z):
    """A forge yard: a stone hearth ringed with iron, its fire (red shader fire), an anvil."""
    pts = [(x + 1.3 * math.cos(a), y + 1.3 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 13)[:-1]]
    blib.prism(b, 'red', pts, z - 0.2, 0.8)
    inner = [(x + 0.95 * math.cos(a), y + 0.95 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 13)[:-1]]
    blib.prism(b, 'ember', inner, z - 0.2, 0.84)
    blib.box(b, 'iron', x + 2.0, y, z, 0.5, 0.9, 0.7)
    FIRES.append((x, y, z + 0.8, 1.1))


# --------------------------------------------------------------------------- the causeways (with the city part)
def causeways(b, rng):
    """Two long arched causeways leaving the third terrace east and west to the knobs at the hex's edge."""
    lv = TERR[2][1]
    for s in (-1, 1):
        x0, x1 = s * 13.0, s * 31.0
        y = 3.0
        n_arch = 4
        deck = []
        for i in range(n_arch + 1):
            x = x0 + (x1 - x0) * i / n_arch
            deck.append(x)
            ground = float(massif_h(x, y))
            if 0 < i < n_arch:
                blib.box(b, 'red', x, y, min(ground, 2.0) - 1.0, 1.6, 2.8, lv - min(ground, 2.0) - 0.4)
                blib.box(b, 'red', x, y, min(ground, 2.0) - 1.0, 2.4, 3.4, 2.0)
        # deck + parapets
        blib.box(b, 'red', (x0 + x1) / 2, y, lv - 1.4, abs(x1 - x0), 2.6, 1.4)
        for sy in (-1, 1):
            blib.box(b, 'red', (x0 + x1) / 2, y + sy * 1.15, lv, abs(x1 - x0), 0.3, 0.8)
        # the arches: a pointed rib of stone springing from pier to pier under the deck, a spandrel band over it
        for i in range(n_arch):
            xa, xb = deck[i], deck[i + 1]
            top = lv - 1.4
            spring = top - 6.5
            half = (xb - xa) / 2
            pts = []
            for t in np.linspace(0, 1, 13):
                u = 2 * t - 1                                   # -1 .. 1 across the span
                z = spring + 5.4 * (1 - abs(u) ** 1.6)           # pointed at the crown
                pts.append(Vector(((xa + xb) / 2 + u * half, y, z)))
            for q0, q1 in zip(pts, pts[1:]):
                blib.strut(b, 'red', q0, q1, 0.75, 0.75, n=6)
            blib.box(b, 'red', (xa + xb) / 2, y, top - 1.6, abs(xb - xa), 2.5, 1.6)
        for i in range(1, n_arch):
            x = deck[i]
            FIRES.append((x, y - 1.15, lv + 0.9, 0.55)) if i % 2 else None


# --------------------------------------------------------------------------- the castle (extra static)
def keep_r(z):
    t = (z - KEEP_Z0) / (KEEP_TOP - KEEP_Z0)
    return 6.2 - 1.9 * t + 1.0 * math.exp(-max(0.0, z - KEEP_Z0) / 3.0)


def build_castle(b):
    """The Witch-king's keep between the spires: the court and its wall, a tall octagonal keep of red stone with
    great buttresses, lancets of fire, the Watch (a balcony over the city), and the CROWN: a ring of curved iron
    tines round a black spire (BFME: "resembles a crown, the apex of Carn Dum"); flanking towers; the causeways."""
    palette()
    rng = random.Random(41)
    cx, cy = KEEP_C
    n = 8
    zs = [KEEP_Z0 - 1.0, KEEP_Z0 + 3.0, 50.0, 66.0, KEEP_TOP]
    loft(b, 'red', [ngon(cx, cy, z, keep_r(z), n, math.pi / n) for z in zs])
    for k in range(n):                                    # buttresses on the corners, stepped
        a = 2 * math.pi * k / n
        ca, sa = math.cos(a), math.sin(a)
        for (z0, z1, o) in ((KEEP_Z0 - 1, 54.0, 2.6), (54.0, 74.0, 1.5)):
            r0, r1 = keep_r(z0) / math.cos(math.pi / n), keep_r(z1) / math.cos(math.pi / n)
            secs = []
            for z, rr, oo in ((z0, r0, o), (z1, r1, 0.2)):
                c = Vector((cx + ca * (rr + oo * 0.5 - 0.4), cy + sa * (rr + oo * 0.5 - 0.4), z))
                N = Vector((ca, sa, 0))
                T = Vector((-sa, ca, 0))
                secs.append([c - N * (oo * 0.5 + 0.4) - T * 0.7, c + N * (oo * 0.5) - T * 0.7,
                             c + N * (oo * 0.5) + T * 0.7, c - N * (oo * 0.5 + 0.4) + T * 0.7])
            loft(b, 'redDim', secs)
            tube(b, 'iron', [tuple(secs[-1][1] * 0.5 + secs[-1][2] * 0.5 + Vector((0, 0, 0.0))),
                             tuple(secs[-1][1] * 0.5 + secs[-1][2] * 0.5 + Vector((ca * 0.6, sa * 0.6, 2.4)))],
                 [0.3, 0.0], sides=4)
    # lancets of fire on the faces (three tiers)
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        if math.sin(a) > 0.6:
            continue
        for z0, hgt in ((38.0, 6.0), (52.0, 5.0), (68.0, 5.0), (74.0, 5.5)):
            r_ = keep_r(z0 + hgt / 2) * 0.99
            c = (cx + math.cos(a) * r_, cy + math.sin(a) * r_, z0)
            panel(b, 'dark', c, (math.cos(a), math.sin(a)), arch_pts(0.75, hgt + 0.5), depth=0.08)
            panel(b, 'fire', c, (math.cos(a), math.sin(a)), arch_pts(0.48, hgt), depth=0.1)
    # the Watch: a balcony on great iron corbels, over the city
    r_ = keep_r(WATCH_Z)
    by = cy - r_
    blib.box(b, 'red', cx, by - 1.6, WATCH_Z - 0.8, 6.4, 3.6, 0.8)
    for s in (-1, 0, 1):
        blib.strut(b, 'iron', (cx + s * 2.4, by - 0.1, WATCH_Z - 4.0), (cx + s * 2.4, by - 3.2, WATCH_Z - 0.8), 0.25, 0.25,
                   n=4)
    for s in (-1, 1):
        blib.strut(b, 'iron', (cx + s * 3.1, by - 3.3, WATCH_Z), (cx + s * 3.1, by + 0.1, WATCH_Z), 0.07, 0.07, n=4)
        blib.strut(b, 'iron', (cx + s * 3.1, by - 3.3, WATCH_Z + 1.1), (cx + s * 3.1, by + 0.1, WATCH_Z + 1.1), 0.07, 0.07, n=4)
        CROWN_FIRES.append((cx + s * 2.7, by - 3.0, WATCH_Z + 0.2, 0.6))
    blib.strut(b, 'iron', (cx - 3.1, by - 3.3, WATCH_Z + 1.1), (cx + 3.1, by - 3.3, WATCH_Z + 1.1), 0.07, 0.07, n=4)
    panel(b, 'dark', (cx, by - 0.02, WATCH_Z), (0, -1), arch_pts(1.0, 3.2), depth=0.06)
    # the top: a machicolated ring, then the CROWN of iron tines round a black spire
    zt = KEEP_TOP
    rt = keep_r(zt)
    loft(b, 'red', [ngon(cx, cy, zt, rt, n, math.pi / n), ngon(cx, cy, zt + 1.2, rt + 1.0, n, math.pi / n),
                    ngon(cx, cy, zt + 2.4, rt + 1.0, n, math.pi / n)])
    for k in range(16):
        a = 2 * math.pi * k / 16
        ca, sa = math.cos(a), math.sin(a)
        r0 = rt + 0.6
        tall = 11.0 if k % 2 == 0 else 7.0
        if k % 4 == 0:
            tall = 16.0
        pts = [(cx + ca * r0, cy + sa * r0, zt + 1.5), (cx + ca * (r0 + 1.0), cy + sa * (r0 + 1.0), zt + 2.4 + tall * 0.3),
               (cx + ca * (r0 + 1.3), cy + sa * (r0 + 1.3), zt + 2.4 + tall * 0.65),
               (cx + ca * (r0 + 0.9), cy + sa * (r0 + 0.9), zt + 2.4 + tall)]
        tube(b, 'iron', pts, [0.55, 0.42, 0.26, 0.0], sides=5)
    loft(b, 'roof', [ngon(cx, cy, zt + 2.4, rt * 0.85, n, math.pi / n), ngon(cx, cy, zt + 6.0, rt * 0.42, n, math.pi / n)],
         apex=(cx, cy, CROWN_TOP), smooth=False)
    for k in range(8):
        a = 2 * math.pi * k / 8
        CROWN_FIRES.append((cx + math.cos(a) * (rt - 0.4), cy + math.sin(a) * (rt - 0.4), zt + 2.5, 1.0))
    # the flanking towers in the court
    for s in (-1, 1):
        tower(b, rng, s * 9.5, cy - 4.0, KEEP_Z0 - 1.0, 60.0, 2.4, roof=True)
        tower(b, rng, s * 5.5, 8.5, KEEP_Z0 - 1.0, 46.0, 1.7, roof=True)
    causeways(b, rng)


# --------------------------------------------------------------------------- skinned part: stones carrying the bones
EYE_C = (0.0, 6.5, TERR[3][1])


def build_eye(b):
    """The skinned part (the Balrog v2's way): a few stones on the court that carry the effect bones."""
    palette()
    rng = random.Random(4)
    for (x, y) in ((-3.0, 6.8), (3.0, 7.0), (0.0, 8.5)):
        s = rng.uniform(0.5, 0.8)
        blib.sphere(b, 'rock', x, y, TERR[3][1], s, n=8, rings=5, squash=0.7)


def _still(t):
    return 0.3 * math.sin(2 * math.pi * t / 12.0)


GAZE = dict(fn=_still, T=12.0, spans=60)


def rig():
    return [('fxglow', 'eyeroot', (0.0, CC[1] - TERR[0][0] - 1.5, 4.0), 'CARN_GLOW'),
            ('fxfire', 'eyeroot', (0.0, 0.0, 10.0), 'CARN_FIRE'),
            ('fxcrown', 'eyeroot', (KEEP_C[0], KEEP_C[1], KEEP_TOP), 'CARN_CROWN'),
            ('fxcloud', 'eyeroot', (0.0, 20.0, 60.0), 'CARN_CLOUD'),
            ('fxfog', 'eyeroot', (0.0, -10.0, 2.0), 'CARN_FOG'),
            ('fxhalo', 'eyeroot', (0.5, 21.0, 112.0), 'CARN_HALO')]


def glow_effect(k):
    """The outer gate: firelight pouring between the iron doors and from the arch above them."""
    pos = Vector(rig()[0][2])
    lines = []
    for i in range(5):
        x = (i - 2) * 0.35
        lines.append((x, 0.2, x * 0.6, 7.6 - abs(i - 2) * 0.8, 0.28, (255, 150, 60)))
    for s in (-1, 1):
        lines.append((s * 0.1, 7.9, s * 2.6, 6.4, 0.22, (255, 120, 40)))
    X0, X1, Z0_, Z1_ = -4.0, 4.0, -0.5, 10.0
    return dict(name='MEC_CarnDumGlow',
                quads=[((X0 - pos.x) * k, (X1 - pos.x) * k, (Z0_ - pos.z) * k, (Z1_ - pos.z) * k, 0.0)],
                tex_args=dict(lines=lines, box=(X0, X1, Z0_, Z1_), px=512, color=(255, 140, 50), halo=0.6, core=0.9,
                              sigma=(0.3, 1.3)))


T_FLAME = 12.0
FOG_STOPS = [(0.0, (8, 9, 12)), (0.5, (44, 49, 62)), (0.85, (86, 93, 110)), (1.0, (120, 128, 146))]   # dim: layers add up
FOG_DRIFT = 10           # sideways scroll speed (the fire's upward scroll is 184): barely moving, never rising   # dim: a veil


def _ensure():
    if FIRES and CROWN_FIRES:
        return

    class Null:
        def __init__(self):
            self.verts, self.faces, self.fmat, self.fsmooth, self.mat_names = [], [], [], [], []
            self.rng = random.Random(0)

        def add(self, *a, **kw):
            pass

        def _mi(self, n):
            return 0
    FIRES.clear()
    CROWN_FIRES.clear()
    build_halls(Null())
    build_city(Null())
    build_town(Null())
    build_castle(Null())


def _fire_em():
    seen = sorted({(round(x, 2), round(y, 2), round(z, 2), s) for x, y, z, s in FIRES})
    return [(Vector((x, y, z)), s) for x, y, z, s in seen]


def _crown_em():
    seen = sorted({(round(x, 2), round(y, 2), round(z, 2), s) for x, y, z, s in CROWN_FIRES})
    return [(Vector((x, y, z)), s) for x, y, z, s in seen]


def _cloud_em():
    """v2 (user: "more fog and mist, dark and creepy"): cloud wrapping both spires all round and up their whole
    height, and the needles on the shoulders."""
    rng = random.Random(9)
    em = []
    for sp, zs in ((SPIRES[0], np.arange(44.0, 118.0, 11.0)), (SPIRES[1], np.arange(42.0, 104.0, 11.0))):
        for z in zs:
            c, r = axis_at(sp, z)
            n = 4 if z < 90 else 3
            for j in range(n):                   # on the camera's side (cards behind the rock never show)
                a = -math.pi + 0.35 + (math.pi - 0.7) * (j + rng.uniform(-0.25, 0.25)) / (n - 1)
                em.append((c + Vector((math.cos(a), math.sin(a), 0)) * (r + 2.6) + Vector((0, 0, -5.0)),
                           rng.uniform(0.75, 1.15) * (0.8 if z > 95 else 1.0)))
    for (x, y, z0, z1, r) in NEEDLES:
        em.append((Vector((x, y - r - 2.0, (z0 + z1) / 2 - 6.0)), rng.uniform(0.6, 0.8)))
    for j in range(9):                       # v3: a belt of fog across the upper city, veiling the keep's foot
        x = -16.0 + 32.0 * j / 8 + rng.uniform(-1.0, 1.0)
        em.append((Vector((x, 2.0 + rng.uniform(-1.5, 1.5), TERR[2][1] + rng.uniform(2.0, 6.0))),
                   rng.uniform(0.6, 0.8)))
    return em


def surface_z(x, y):
    tz = float(terrace_z(x, y))
    return tz if tz >= 0 else max(0.0, float(massif_h(x, y)))


def _fog_em():
    """v3 (the user: "much more fog and mist ... dense, suffocating, as if it was there forever; not steam; not moving
    up at all"): a BLANKET of lying fog over the whole tile in two layers (near-flat banks, tilted back almost onto
    the ground), through the terraces and round the foot of the massif, and a ring spilling a little past the tile's
    edge round the city. Emitters (point, scale, height above the surface)."""
    rng = random.Random(13)
    em = []
    step = 7.0
    for layer, (dz, off, keep_p) in enumerate(((0.9, 0.0, 1.0), (4.2, 0.5, 0.75))):
        for gy in np.arange(-36.0, 36.0, step):
            for gx in np.arange(-31.0, 31.5, step):
                x = gx + off * step + rng.uniform(-1.5, 1.5)
                y = gy + off * step + rng.uniform(-1.5, 1.5)
                if hex_d(x, y) > HEX - 1.5 or rng.random() > keep_p:
                    continue
                z = surface_z(x, y)
                if z > 30.0:                         # (the cloud banks cover the heights)
                    continue
                em.append((Vector((x, y, z + dz)), rng.uniform(0.85, 1.15)))
    for k in range(16):                              # round the city, spilling past the tile's edge
        a = 2 * math.pi * (k + rng.uniform(-0.2, 0.2)) / 16
        r = rng.uniform(34.0, 38.0)
        em.append((Vector((r * math.cos(a), r * math.sin(a), 0.8)), rng.uniform(0.9, 1.2)))
    return em


FIRE_SETS = {
    'CARN_FIRE': ('MEC_CarnDumFire', 'fxfire', _fire_em, 3.6, 2, 'fire'),
    'CARN_CROWN': ('MEC_CarnDumCrown', 'fxcrown', _crown_em, 5.0, 2, 'fire'),
    'CARN_CLOUD': ('MEC_CarnDumCloud', 'fxcloud', _cloud_em, 18.0, 1, 'cloud'),
    'CARN_FOG': ('MEC_CarnDumFog', 'fxfog', _fog_em, 11.0, 1, 'fog'),
}
FX_TEX = {'fire': 'MEC_CarnDum', 'cloud': 'MEC_CarnDumF', 'fog': 'MEC_CarnDumF'}      # v3: one fog for both


def flame_tongues(key, k):
    import flames
    _ensure()
    name, bone, emf, hgt, per, kind = FIRE_SETS[key]
    bw = Vector(next(r[2] for r in rig() if r[0] == bone))
    rng = random.Random(zlib.crc32(name.encode()) & 0xffff)
    em = [(((p - bw) * k).x, ((p - bw) * k).y, ((p - bw) * k).z, s) for p, s in emf()]
    # v3: fog lies almost flat on the ground (tilted back 76 degrees); cloud banks stand facing the camera
    tg = flames.steady_tongues(em, T_FLAME, rng, per=per, size=hgt * k, tilt=-76.0 if kind == 'fog' else None,
                               sink=0.0 if kind == 'fog' else 0.04)
    if kind == 'cloud':
        for t in tg:
            t.w = t.h * rng.uniform(1.4, 1.9)
    elif kind == 'fog':
        for t in tg:
            t.w = t.h * rng.uniform(1.6, 2.1)
    return tg


HALO_W, HALO_H = 16.0, 30.0


def _halo_texture(path, W=256, H=512):
    """The pale cold light between the peaks' tips (the reference's storm-light): a soft elongated glow."""
    import dds
    u = (np.arange(W) + 0.5) / W * 2 - 1
    v = (np.arange(H) + 0.5) / H * 2 - 1
    U, V = np.meshgrid(u, v)
    r = np.hypot(U / 0.8, V / 1.0)
    a = 0.2 * np.exp(-(r / 0.5) ** 2) + 0.08 * np.exp(-(r / 0.2) ** 2)
    a *= np.clip((1 - r) / 0.2, 0, 1)
    a = np.clip(a + (np.random.default_rng(5).random(a.shape) - 0.5) / 15.0 * (a > 0.004), 0, 1)
    img = np.zeros((H, W, 4), np.float32)
    img[..., 0] = 200
    img[..., 1] = 215
    img[..., 2] = 255
    img[..., 3] = 255 * a
    dds.write_dxt3(path, np.clip(img, 0, 255).astype(np.uint8), alpha_keep=0.2)


def model_effects(out_dir, k):
    import os
    import flames
    import glow
    files = []
    bases, masks = flames.fire_textures(out_dir, 'MEC_CarnDum')
    files += bases + masks + ['MEC_CarnDum_FireUV.dds', 'MEC_CarnDum_EmberUV.dds']
    fb, fm, other = flames.fog_textures(out_dir, 'MEC_CarnDumF', FOG_STOPS, hspeed=FOG_DRIFT)
    files += fb + fm + other
    tex = {'fire': (bases, masks), 'cloud': (fb, fm), 'fog': (fb, fm)}
    for key, (name, bone, _, _, _, kind) in FIRE_SETS.items():
        files += flames.write_fire(out_dir, name, flame_tongues(key, k), *tex[kind])
    q = [(-HALO_W * k, HALO_W * k, -HALO_H * k, HALO_H * k, 0.0)]
    files += glow.write(out_dir, 'MEC_CarnDumHalo', q, dict(lines=[], box=(0, 1, 0, 1), px=64))
    _halo_texture(os.path.join(out_dir, 'MEC_CarnDumHalo_DIFF.dds'))
    return files


def preview_overlays(out_dir):
    import os
    import dds
    import flames
    out = []
    for key, (name, bone, _, _, _, kind) in FIRE_SETS.items():
        pre = FX_TEX[kind]
        b_ = dds.decode_dxt3(os.path.join(out_dir, pre + '_FireB0.dds')).astype(np.float32)
        m_ = dds.decode_dxt3(os.path.join(out_dir, pre + '_FireM0.dds')).astype(np.float32)
        img = b_.copy()
        img[..., 3] = b_[..., 3] * m_[..., 3] / 255.0
        img = np.clip(img, 0, 255).astype(np.uint8)
        bw = next(r[2] for r in rig() if r[0] == bone)
        for tg in flame_tongues(key, 4.0):
            qq = flames.rest_quat(tg)
            hw = tg.w / 2
            P = []
            for (x, z) in ((-hw, -0.06 * tg.h), (hw, -0.06 * tg.h), (hw, 0.94 * tg.h), (-hw, 0.94 * tg.h)):
                rx, ry, rz = flames.qrotate(qq, (x, 0.0, z))
                P.append((bw[0] + (tg.base[0] + rx) / 4.0, bw[1] + (tg.base[1] + ry) / 4.0,
                          bw[2] + (tg.base[2] + rz) / 4.0))
            out.append((P, [(0, 1, 2, 3)], [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)], img))
    hp = next(r[2] for r in rig() if r[0] == 'fxhalo')
    P = [(hp[0] - HALO_W, hp[1], hp[2] - HALO_H), (hp[0] + HALO_W, hp[1], hp[2] - HALO_H),
         (hp[0] + HALO_W, hp[1], hp[2] + HALO_H), (hp[0] - HALO_W, hp[1], hp[2] + HALO_H)]
    out.append((P, [(0, 1, 2, 3)], [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)],
                dds.decode_dxt3(os.path.join(out_dir, 'MEC_CarnDumHalo_DIFF.dds'))))
    return out


EXTRA_STATICS = [('peaks', build_peaks, 2048), ('halls', build_halls, 2048), ('city', build_city, 2048),
                 ('town', build_town, 2048), ('castle', build_castle, 2048)]

PREVIEW = [((0, -230, 300), (0, 4, 50), 44),
           ((0, -110, 95), (0, -10, 20), 36),
           ((0, -120, 150), (0, 15, 75), 34),
           ((170, -110, 140), (0, 8, 55), 40),
           ((-150, -140, 160), (0, 8, 55), 40)]
PREVIEW_EYE = [((0, -60, 70), (0, 7, 33), 40)]
