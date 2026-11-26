"""The Balrog of Moria: the Goblins' capital landmark (an IMPROVEMENT, docs/LANDMARKS.md). 2026-11-26.

The user: "an entirely new huge model of the Balrog that looks like emerging from the ground, clawing its way out ...
only the upper half of the Balrog body as he is emerging from the mines. Big, impressive and very detailed: horns,
claws, face, hands and fire. The whole head and arms in flames. ANIMATED FLAMES! Not as tall as the Eye of Sauron.
His hands may occupy parts of the adjacent tiles. Realistic." References: screenshots/balrog1.webp (the film: ram
horns curling round a skull-like face, eyes and maw of fire, arms of black crust split by glowing seams, wings of
shadow), screenshots/balrog2.webp (cracked plates glowing in the seams, the head a torch of fire, fangs, a roaring
maw full of flame).

In-game units (improvement Scale 0.25, written x4), origin = the city's tile centre, ground z = 0, -Y = south =
towards the game camera. He rises from a rift of molten rock on his own hex, leaning towards the camera; his hands
claw the ground in the neighbouring hexes (west/south-west and east/south-east), his wings half-spread behind him.

Technique (new): SCULPTED in signed distance fields (tools/landmarks/sdf.py: smoothly blended muscles, skull, sinews,
rock-crust noise), meshed at 0.2-0.4 units, decimated to the game's budget; the full sculpt is the source of the
baked AO and relief shading (bake.py b.hires). The hide is a charred crust of plates with fire in the seams
(bake.py palette 'lava': Voronoi seams, a hot core, an orange rim and a red halo; the glowing part exempt from AO).
Horns, teeth and claws are lofted meshes (ridged horn rings, curved fangs).

Fire (the essence): our animated flame tongues (tools/landmarks/flames.py: additive cards that open, lick upwards,
sway and die, each out of phase; 4 effects x 30 cards: the crown of the head, the mane of the shoulders, each arm)
plus the stock Great Lighthouse fire (the Eye's proven fire) on the head, arms and the rift, and an additive glow of
the eyes and the maw (glow.py). The head turns slowly (the skinned part: everything above the neck).

Parts: static = the rift (rim, slabs, rubble, magma, glowing cracks); extra statics = the torso, the left arm, the
right arm, the wings; skinned (the Eye's proven layout) = neck, head, horns, teeth, with the effect bones.
"""
import math
import random
import zlib

import numpy as np
from mathutils import Matrix, Vector

import blib
import sdf
from blib import material, hexcol as h

BAKE = True
BAKE_PX = 2048              # the rift
EYE_PX = 512                # the skinned part: a few stones in the rift carrying the effect bones (v2)
EYE_AO = 24
PART_AO = 24
HEX = 33.6

# --------------------------------------------------------------------------- the body frame
LEAN = math.radians(13.0)                         # leaning towards the camera
W0 = Vector((0.0, 6.0, -4.0))                     # the waist (below the ground)
UP = Vector((0.0, -math.sin(LEAN), math.cos(LEAN)))
FWD = Vector((0.0, -math.cos(LEAN), -math.sin(LEAN)))
LAT = Vector((1.0, 0.0, 0.0))
BACK = -FWD
R_BODY = Matrix((LAT, BACK, UP)).transposed()     # columns: lateral, back, up (local -> world)


def P(x, s, d=0.0):
    """A point of the body: x lateral (+ = east), s up along the spine from the waist, d forwards (towards the camera)."""
    return W0 + LAT * x + UP * s + FWD * d


def body_ell(x, s, d, r, rot=None):
    """An ellipsoid in the body frame (radii: lateral, back-forward, along the spine)."""
    R = R_BODY if rot is None else R_BODY @ rot
    return sdf.ellipsoid(tuple(P(x, s, d)), r, np.array(R))


def rot(rx=0.0, ry=0.0, rz=0.0):
    return (Matrix.Rotation(math.radians(rz), 3, 'Z') @ Matrix.Rotation(math.radians(ry), 3, 'Y')
            @ Matrix.Rotation(math.radians(rx), 3, 'X'))


NECK_BASE = P(0, 62, -1)                          # the neck's root between the shoulders (the head's pivot)
HEAD_C = Vector((0.0, -21.0, 78.0))               # the centre of the skull
HEAD_S = 1.25                                     # the head's size (head space is authored at 1.0)
HEAD_PITCH = -24.0                                # degrees: the face raised a little, roaring up at the camera
SHOULDER = {s: P(31.0 * s, 50.0, -1.5) for s in (-1, 1)}

# the arms: shoulder -> elbow -> wrist -> the hand on the ground; fingers spread and dug in
ARMS = {
    -1: dict(elbow=Vector((-50.0, -20.0, 30.0)), wrist=Vector((-57.0, -38.0, 7.5)), palm=Vector((-58.5, -44.0, 3.2)),
             yaw=-118.0),
    1: dict(elbow=Vector((51.0, -10.0, 27.0)), wrist=Vector((61.0, -25.0, 7.5)), palm=Vector((63.5, -30.5, 3.2)),
            yaw=-55.0),
}

RIFT_C = (0.0, 4.0)
RIFT_A, RIFT_B = 27.0, 18.0


def head_frame():
    """Head space -> world: x lateral, y forwards is -y... (head-local: +y = back, -y = the face), pitched down."""
    return (Matrix.Translation(HEAD_C) @ Matrix.Rotation(math.radians(HEAD_PITCH), 4, 'X')
            @ Matrix.Diagonal((HEAD_S, HEAD_S, HEAD_S, 1.0)))


def HP(x, y, z):
    return head_frame() @ Vector((x, y, z))


def HR():
    return np.array(Matrix.Rotation(math.radians(HEAD_PITCH), 3, 'X'))


# --------------------------------------------------------------------------- materials
def palette():
    crust = dict(cold=h('090605'), warm=h('ff6410'), core=h('ffd47a'), halo_color=h('7a1c06'))
    material('hide', h('141010'), h('211915'), spec=0.22, refl=18)
    blib.PALETTE['hide'].update(scale=0.22, cavity=0.7, lava=dict(crust, scale=0.17, width=0.035, hot=0.6,
                                                                  mask_scale=0.035, halo=0.3, warp=0.55,
                                                                  fine=(0.7, 0.04, 0.12), bump=0.4))
    material('hideHot', h('151010'), h('221914'), spec=0.22, refl=18)
    blib.PALETTE['hideHot'].update(scale=0.25, cavity=0.7, lava=dict(crust, scale=0.21, width=0.04, hot=0.53,
                                                                     mask_scale=0.045, halo=0.4, warp=0.55,
                                                                     fine=(0.85, 0.04, 0.2), bump=0.35))
    material('face', h('17110f'), h('241a15'), spec=0.25, refl=20)
    blib.PALETTE['face'].update(scale=0.4, cavity=0.85, lava=dict(crust, scale=0.33, width=0.045, hot=0.55,
                                                                  mask_scale=0.07, halo=0.35, warp=0.5,
                                                                  fine=(1.2, 0.04, 0.15), bump=0.25))
    material('horn', h('201b18'), h('3a302a'), spec=0.4, refl=40)
    blib.PALETTE['horn'].update(scale=0.8, vcracks=(2.2, 0.3), cavity=0.9)
    material('claw', h('15110f'), h('241c17'), spec=0.75, refl=90)
    blib.PALETTE['claw'].update(scale=2.0, cavity=0.6)
    material('teeth', h('a88d62'), h('86704c'), spec=0.55, refl=50)
    blib.PALETTE['teeth'].update(scale=3.0, cavity=0.6)
    material('maw', h('ffb347'), h('ff8a1c'), spec=0.0, refl=0, ao=False)
    blib.PALETTE['maw'].update(scale=0.6)
    material('eye', h('ffb02e'), spec=0.0, refl=0, ao=False)
    blib.PALETTE['eye'].update(solid=True)
    material('rock', h('2b2622'), h('3b342e'), spec=0.12, refl=8)
    blib.PALETTE['rock'].update(scale=0.35, cavity=0.9, vcracks=(0.9, 0.35),
                                lava=dict(crust, scale=0.26, width=0.035, hot=0.7, mask_scale=0.04, halo=0.3,
                                          warp=0.55, bump=0.5))
    material('magma', h('ff9a2a'), h('ffd060'), spec=0.0, refl=0, ao=False)
    blib.PALETTE['magma'].update(scale=0.2, speckle=[(0.25, 0.22, h('8a2a08')), (1.6, 0.18, h('fff0b0'))])
    material('ember', h('ff7418'), h('d24a0c'), spec=0.0, refl=0, ao=False)       # the glowing cracks in the ground
    blib.PALETTE['ember'].update(scale=0.6)
    material('wing', h('150f0d'), h('201613'), spec=0.18, refl=12)
    blib.PALETTE['wing'].update(scale=0.3, cavity=0.6, lava=dict(crust, scale=0.16, width=0.035, hot=0.72,
                                                                 mask_scale=0.03, halo=0.4, warp=0.5, bump=0.2))
    material('wingbone', h('241b17'), h('34281f'), spec=0.25, refl=20)
    blib.PALETTE['wingbone'].update(scale=0.5, cavity=0.8, lava=dict(crust, scale=0.3, width=0.05, hot=0.5,
                                                                     mask_scale=0.05, halo=0.5, bump=0.2))


# --------------------------------------------------------------------------- helpers
def skin_noise(amp=1.0, f=1.0, seed=0):
    """Rock-crust displacement (positive = into the surface): broad lumps, plates, fine grain."""
    def fn(X, Y, Z):
        x, y, z = X * f, Y * f, Z * f
        return amp * (0.75 * sdf.fbm3(x * 0.16, y * 0.16, z * 0.16, 3, seed)
                      + 0.35 * sdf.fbm3(x * 0.55, y * 0.55, z * 0.55, 3, seed + 5)
                      - 0.45 * (sdf.ridged3(x * 0.1, y * 0.1, z * 0.1, 2, seed + 9) - 0.5)
                      + 0.12 * sdf.fbm3(x * 1.6, y * 1.6, z * 1.6, 2, seed + 13))
    return fn


def finish(b, field, target_tris, mat_fn, smooth_iters=2, min_tris=400):
    """Mesh a field, keep the full surface for the bake, decimate it for the game, add it to the builder."""
    v, t = field.mesh()
    v, t = sdf.drop_small(v, t, min_tris)
    v = sdf.smooth_mesh(v, t, smooth_iters, 0.5)
    hv, ht = sdf.decimate(v, t, min(len(t), 900000), 'hi')         # the bake's source (plenty of detail)
    gv, gt = sdf.decimate(v, t, target_tris, 'game')
    sdf.add_to_builder(b, gv, gt, mat_fn, hires=(hv, ht))
    print('sculpt: %d -> %d triangles (bake source %d)' % (len(t), len(gt), len(ht)))


def explicit(b, verts, faces, mat):
    """An explicit mesh (horns, teeth, claws...): to the game mesh and to the bake's source."""
    b.add(verts, faces, mat, smooth=True)
    tris = []
    for f in faces:
        for i in range(1, len(f) - 1):
            tris.append((f[0], f[i], f[i + 1]))
    if not hasattr(b, 'hires'):
        b.hires = []
    b.hires.append((np.array(verts, float), np.array(tris, int)))


def loft(b, mat, path, radii, n=16, flat=1.0, ridges=None, twist_ref=None):
    """A tube along path (Vectors) with radii; flat squashes the section along the frame's second axis; ridges =
    (per unit, depth) rings (horn growth rings). Closed in a point at the end when the last radius ~0."""
    P_ = [Vector(p) for p in path]
    m = len(P_)
    rows = []
    prev = None
    s_acc = 0.0
    for i, p in enumerate(P_):
        t = (P_[min(i + 1, m - 1)] - P_[max(i - 1, 0)]).normalized()
        if prev is None:
            a = (Vector(twist_ref) if twist_ref else t.orthogonal())
            a = (a - t * a.dot(t)).normalized()
        else:
            a = (prev - t * prev.dot(t)).normalized()
        prev = a
        c = t.cross(a)
        if i:
            s_acc += (P_[i] - P_[i - 1]).length
        r = radii[i]
        if ridges:
            r *= 1.0 + ridges[1] * (0.5 + 0.5 * math.cos(2 * math.pi * s_acc * ridges[0])) ** 3
        rows.append([p + a * (r * math.cos(2 * math.pi * j / n)) + c * (r * flat * math.sin(2 * math.pi * j / n))
                     for j in range(n)])
    verts = [tuple(q) for row in rows for q in row]
    faces = []
    for i in range(m - 1):
        for j in range(n):
            a_, b_ = i * n + j, i * n + (j + 1) % n
            faces.append((a_, b_, b_ + n, a_ + n))
    # winding outwards
    o = rows[1][0] - P_[1]
    f0 = faces[n]
    nrm = (Vector(verts[f0[1]]) - Vector(verts[f0[0]])).cross(Vector(verts[f0[3]]) - Vector(verts[f0[0]]))
    if nrm.dot(o) < 0:
        faces = [f[::-1] for f in faces]
    # caps
    k = len(verts)
    verts.append(tuple(P_[-1] + (P_[-1] - P_[-2]).normalized() * radii[-1] * 0.6))
    verts.append(tuple(P_[0]))
    last, first = (m - 1) * n, 0
    cap_e = [(last + j, last + (j + 1) % n, k) for j in range(n)]
    cap_s = [((j + 1) % n, j, k + 1) for j in range(n)]
    if nrm.dot(o) < 0:
        cap_e = [f[::-1] for f in cap_e]
        cap_s = [f[::-1] for f in cap_s]
    explicit(b, verts, faces + cap_e + cap_s, mat)


def spline(pts, n):
    """Catmull-Rom through pts, n points."""
    Pp = [Vector(p) for p in pts]
    Pp = [Pp[0]] + Pp + [Pp[-1]]
    out = []
    segs = len(pts) - 1
    for k in range(n):
        u = k / (n - 1) * segs
        i = min(int(u), segs - 1)
        t = u - i
        p0, p1, p2, p3 = Pp[i], Pp[i + 1], Pp[i + 2], Pp[i + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    return out


MOUND_H = 13.0       # v4: the rocky mound he rises from, 6.5 in game at Scale 0.125: above the stock houses (they draw
PIT_Z = 8.0          # at ground level; Bag End: ~6 hides them), full height to 36 from the centre, gone at 56
MAGMA_Z = 11.2


def ground_h(x, y):
    """The mound's height (numpy arrays or floats): a broad hill of broken rock, a raised lip round the rift, the pit
    in it (below the magma)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    r = np.hypot(x, (y - 2.0) * 1.05)
    u = np.clip((r - 27.0) / 19.0, 0.0, 1.0)
    base = (MOUND_H + 2.5) * (1.0 - u * u * (3 - 2 * u)) - 2.5         # the skirt sinks under the ground: a clean edge
    base = base + 1.6 * sdf.fbm3(x * 0.07, y * 0.07, np.zeros_like(x), 3, 41) * np.clip(base / MOUND_H, 0, 1)
    re = np.hypot((x - RIFT_C[0]) / RIFT_A, (y - RIFT_C[1]) / RIFT_B)
    h = base + 2.5 * np.exp(-((re - 1.15) / 0.15) ** 2) * np.clip(base / MOUND_H, 0, 1)
    v = np.clip((re - 0.95) / 0.13, 0.0, 1.0)
    return PIT_Z + (h - PIT_Z) * (v * v * (3 - 2 * v))


def gz(x, y):
    """The surface to stand things on: the mound, or the game's ground where the mound has sunk under it."""
    return max(0.0, float(ground_h(x, y)))


def ell_r(x, y):
    """The rift's ellipse measure (1 = its edge)."""
    return math.hypot((x - RIFT_C[0]) / RIFT_A, (y - RIFT_C[1]) / RIFT_B)


# --------------------------------------------------------------------------- the rift (static main part)
def build(b, eye=False):
    palette()
    rng = random.Random(7)
    f = sdf.Field((-84, -76, -1.0), (84, 62, 30.0), 0.36, far=3.0)
    cx, cy = RIFT_C

    def mound_fn(X, Y, Z):      # v4: the mound (hides the stock houses under it)
        return (Z - ground_h(X, Y)) * 0.75
    f.add((mound_fn, (np.array([-62.0, -60.0, -2.0]), np.array([62.0, 62.0, 22.0]))), k=0)
    # slabs of the broken ground, their inner edges heaved up and outwards
    n = 70
    for i in range(n):
        th = 2 * math.pi * (i + rng.uniform(-0.3, 0.3)) / n
        rr = rng.uniform(1.1, 2.0)
        x, y = cx + RIFT_A * rr * math.cos(th), cy + RIFT_B * rr * math.sin(th)
        # outward normal of the ellipse
        nx, ny = math.cos(th) / RIFT_A, math.sin(th) / RIFT_B
        L = math.hypot(nx, ny)
        nx, ny = nx / L, ny / L
        yaw = math.degrees(math.atan2(ny, nx)) - 90.0          # local +y = outwards
        tilt = rng.uniform(22, 62) * (1.25 - 0.5 * (rr - 1.1))
        hx, hy, hz = rng.uniform(3.5, 8.0), rng.uniform(3.0, 6.5), rng.uniform(0.9, 1.8)
        R = rot(rz=yaw) @ rot(rx=-tilt) @ rot(ry=rng.uniform(-12, 12))
        z = gz(x, y) + math.sin(math.radians(tilt)) * hy * 0.55
        f.add(sdf.rbox((x, y, z), (hx, hy, hz), np.array(R), rad=0.35), k=0.6)
    # rubble round the rim and the hands
    for i in range(170):
        th = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(1.15, 2.0)
        x, y = cx + RIFT_A * rr * math.cos(th), cy + RIFT_B * rr * math.sin(th)
        s = rng.uniform(0.6, 2.4) * (1.6 - 0.4 * rr)
        f.add(sdf.rbox((x, y, gz(x, y) + s * 0.3), (s, s * rng.uniform(0.5, 0.9), s * rng.uniform(0.4, 0.7)),
                       np.array(rot(rz=rng.uniform(0, 360), rx=rng.uniform(-30, 30), ry=rng.uniform(-30, 30))),
                       rad=0.15 * s), k=0.2)
    for sgn, arm in ARMS.items():
        pc = arm['palm']
        f.add(sdf.ellipsoid((pc.x, pc.y, -1.6), (13.0, 11.0, 3.2), np.array(rot(rz=arm['yaw'] + 90))), k=2.0)
        for i in range(26):
            a = rng.uniform(0, 2 * math.pi)
            r = rng.uniform(6, 15)
            s = rng.uniform(0.6, 2.0)
            f.add(sdf.rbox((pc.x + r * math.cos(a), pc.y + r * math.sin(a), s * 0.3), (s, s * 0.7, s * 0.55),
                           np.array(rot(rz=rng.uniform(0, 360), rx=rng.uniform(-35, 35))), rad=0.15 * s), k=0.2)
    f.displace(skin_noise(0.9, 0.9, 3), band=3.0)
    f.intersect((lambda X, Y, Z: -0.35 - Z, None))           # nothing below the ground
    f.F[:, :, :3] = np.maximum(f.F[:, :, :3], 0.5)          # (the grid's bottom layers empty: a closed, clean cut)

    def mats(cen):
        return ['rock'] * len(cen)
    finish(b, f, 20000, mats, smooth_iters=1)
    magma(b, rng)
    cracks(b, rng)


def magma(b, rng):
    """The molten pool in the rift round his waist, a little above the game's ground."""
    nr, na = 16, 96
    verts, faces = [], []
    cx, cy = RIFT_C
    for i in range(nr + 1):
        rr = 1.22 * i / nr
        for j in range(na):
            th = 2 * math.pi * j / na
            x, y = cx + RIFT_A * rr * math.cos(th), cy + RIFT_B * rr * math.sin(th)
            z = MAGMA_Z + 0.25 * math.sin(x * 0.5 + y * 0.3) * math.cos(y * 0.45)
            verts.append((x, y, z))
    for i in range(nr):
        for j in range(na):
            a, b_ = i * na + j, i * na + (j + 1) % na
            faces.append((a, a + na, b_ + na, b_))
    explicit(b, verts, faces, 'magma')


def cracks(b, rng):
    """Glowing fissures running out from the rift across the ground (into the neighbours), a hair above it."""
    cx, cy = RIFT_C
    for i in range(16):
        th = 2 * math.pi * (i + rng.uniform(-0.35, 0.35)) / 16
        L = rng.uniform(18, 42)
        _crack(b, rng, cx + RIFT_A * 1.3 * math.cos(th), cy + RIFT_B * 1.3 * math.sin(th), th, L, 1.5, 0)
    for sgn, arm in ARMS.items():               # the ground split under the clawing hands
        pc = arm['palm']
        for i in range(5):
            th = math.radians(arm['yaw'] + rng.uniform(-70, 70))
            _crack(b, rng, pc.x, pc.y, th, rng.uniform(10, 18), 1.0, 0)


def _crack(b, rng, x, y, th, L, w, depth):
    pts = [(x, y)]
    step = 1.6
    a = th
    for k in range(int(L / step)):
        a += rng.uniform(-0.35, 0.35)
        x, y = x + step * math.cos(a), y + step * math.sin(a)
        pts.append((x, y))
    if len(pts) < 3:
        return
    verts, faces = [], []
    m = len(pts)
    for i, (px, py) in enumerate(pts):
        j0, j1 = max(i - 1, 0), min(i + 1, m - 1)
        dx, dy = pts[j1][0] - pts[j0][0], pts[j1][1] - pts[j0][1]
        dl = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / dl, dx / dl
        ww = w * (1 - i / m) ** 0.8 * rng.uniform(0.7, 1.2) + 0.12
        p0, p1 = (px - nx * ww / 2, py - ny * ww / 2), (px + nx * ww / 2, py + ny * ww / 2)
        verts += [(p0[0], p0[1], gz(*p0) + 0.3 + 0.02 * depth),
                  (p1[0], p1[1], gz(*p1) + 0.3 + 0.02 * depth)]
    for i in range(m - 1):
        a = 2 * i
        faces.append((a, a + 2, a + 3, a + 1))          # counter-clockwise from above
    explicit(b, verts, faces, 'ember')
    if depth < 1 and L > 14:
        for k in range(rng.randint(1, 2)):
            i = rng.randint(m // 4, m * 3 // 4)
            _crack(b, rng, pts[i][0], pts[i][1], th + rng.choice((-1, 1)) * rng.uniform(0.5, 1.0),
                   L * rng.uniform(0.3, 0.5), w * 0.6, depth + 1)


# --------------------------------------------------------------------------- the torso (extra static)
def build_torso(b):
    palette()
    f = sdf.Field((-46, -44, -1.0), (46, 34, 72), 0.34, far=3.0)
    E = body_ell
    f.add(E(0, 8, -1, (18.0, 13.0, 13.0)), k=0)                    # belly / waist
    f.add(E(0, 22, 0, (21.0, 14.5, 14.0)), k=6)                    # lower ribs
    f.add(E(0, 36, 1, (25.0, 16.5, 16.0)), k=7)                    # the great ribcage
    for s in (-1, 1):
        f.add(E(11.5 * s, 41, 8.5, (12.5, 6.0, 9.5), rot(rz=-12 * s, rx=8)), k=4)      # pectorals
        f.add(E(17.0 * s, 30, -7, (12.0, 9.0, 19.0), rot(ry=12 * s)), k=6)             # lats
        f.add(E(12.0 * s, 54, -4, (15.0, 9.0, 8.0), rot(ry=-24 * s)), k=6)             # trapezius
        f.add(E(31.0 * s, 50, -1.5, (11.5, 12.0, 12.5)), k=6)                          # deltoids
        f.add(E(26.0 * s, 46, 5.0, (8.0, 7.0, 9.0), rot(ry=20 * s)), k=4)              # front deltoid
        for i in range(4):                                                             # serratus
            f.add(E(19.5 * s, 25 + 5.2 * i, 7.0, (3.6, 2.6, 2.4), rot(ry=-25 * s)), k=2.0)
        for i in range(3):                                                             # abdominals
            f.add(E(5.2 * s, 7 + 7.2 * i, 11.5, (4.8, 2.6, 3.4)), k=2.2)
        # the upper arms' roots (the arm parts start inside these)
        f.add(sdf.cone(tuple(SHOULDER[s]), tuple(SHOULDER[s].lerp(ARMS[s]['elbow'], 0.3)), 10.5, 9.8), k=4)
    f.add(sdf.cone(tuple(P(0, 50, -2)), tuple(NECK_BASE + UP * 6), 11.5, 10.0), k=5)    # the neck's root
    # the spine: a ridge of bony knobs down the back, and spurs on the shoulders
    for i in range(9):
        f.add(E(0, 18 + 5 * i, -15.5 + 0.06 * i * i, (2.4, 2.4, 2.0)), k=1.6)
    for s in (-1, 1):
        for i, (dx, ds, ln) in enumerate(((2, 6, 6.0), (6, 2, 5.0), (-3, 1, 4.0))):
            base = P(31.0 * s + dx * s, 56 + ds, -6)
            tip = base + Vector((0.4 * s, 0.25, 1.0)).normalized() * ln
            f.add(sdf.cone(tuple(base), tuple(tip), 2.0, 0.25), k=1.0)
    f.displace(skin_noise(1.15, 1.0, 11), band=3.0)
    f.intersect((lambda X, Y, Z: PIT_Z + 1.5 - Z, None))      # v4: from the pit's floor up

    def mats(cen):
        out = []
        for c in cen:
            out.append('hideHot' if c[1] < -8 and c[2] > 20 else 'hide')
        return out
    finish(b, f, 29000, mats)


# --------------------------------------------------------------------------- the arms (extra statics)
def finger_paths(sgn):
    """Long talon fingers of a hand on the ground: (k0 knuckle on the palm, k1, k2, k3 the fingertip, radius scale,
    claw direction). The knuckles arch high, the tips come down and the claws hook into the ground; the thumb on the
    inner side."""
    arm = ARMS[sgn]
    pc = arm['palm']
    out = []
    for i, (ang, L, rs) in enumerate(((-40, 0.86, 0.92), (-14, 1.0, 1.0), (12, 0.97, 1.0), (37, 0.8, 0.9))):
        a = math.radians(arm['yaw'] + ang)
        d = Vector((math.cos(a), math.sin(a), 0.0))
        k0 = pc + d * 6.4 + Vector((0, 0, 1.4))
        k1 = k0 + d * 7.0 * L + Vector((0, 0, 4.2 * L))
        k2 = k1 + d * 5.6 * L + Vector((0, 0, -0.4))
        k3 = k2 + d * 4.6 * L + Vector((0, 0, -3.6 * L))
        out.append((k0, k1, k2, k3, rs, d))
    a = math.radians(arm['yaw'] + (62 if sgn > 0 else -62))       # the thumb, towards the body
    d = Vector((math.cos(a), math.sin(a), 0.0))
    side = d
    k0 = pc + side * 5.2 + Vector((0, 0, 1.0))
    k1 = k0 + side * 5.0 + Vector((0, 0, 3.4))
    k2 = k1 + side * 4.2 + Vector((0, 0, -0.6))
    k3 = k2 + side * 3.6 + Vector((0, 0, -2.6))
    out.append((k0, k1, k2, k3, 1.05, side))
    return out


def build_arm(b, sgn):
    palette()
    arm = ARMS[sgn]
    J, E_, Wr, pc = SHOULDER[sgn], arm['elbow'], arm['wrist'], arm['palm']
    lo = [min(J.x, E_.x, Wr.x, pc.x) - 22, min(J.y, E_.y, Wr.y, pc.y) - 22, -1.0]
    hi = [max(J.x, E_.x, Wr.x, pc.x) + 22, max(J.y, E_.y, Wr.y, pc.y) + 20, J.z + 16]
    f = sdf.Field(lo, hi, 0.3, far=3.0)
    up_dir = (E_ - J).normalized()
    fo_dir = (Wr - E_).normalized()
    # the upper arm: bone + biceps (front) + triceps (back), the shoulder ball
    f.add(sdf.cone(tuple(J), tuple(E_), 12.5, 9.6), k=0)
    f.add(sdf.ellipsoid(tuple(J + Vector((0, 0, 1.0))), (13.0, 13.0, 13.5)), k=5)
    out = Vector((sgn, 0.0, 0.0))
    front = up_dir.cross(out).normalized()
    if front.y > 0:
        front = -front
    mid = J.lerp(E_, 0.5)

    def oriented_ell(c, axis, r_axis, r1, r2, k):
        z = axis.normalized()
        x = z.orthogonal().normalized()
        y = z.cross(x)
        R = np.array(Matrix((x, y, z)).transposed())
        f.add(sdf.ellipsoid(tuple(c), (r1, r2, r_axis), R), k=k)
    oriented_ell(mid + front * 5.0, up_dir, 13.0, 9.0, 8.6, 4.0)          # biceps
    oriented_ell(mid - front * 5.0 + Vector((0, 0, 1.5)), up_dir, 14.0, 9.4, 9.4, 4.0)   # triceps
    # the elbow and its bony spur
    f.add(sdf.ellipsoid(tuple(E_), (9.0, 9.0, 9.0)), k=3)
    spur_dir = (up_dir - fo_dir).normalized()
    f.add(sdf.cone(tuple(E_ + spur_dir * 5.0), tuple(E_ + spur_dir * 15.0 + Vector((0, 0, 3.0))), 3.6, 0.3), k=1.5)
    # the forearm: two bellies tapering to the wrist
    f.add(sdf.cone(tuple(E_), tuple(Wr), 9.4, 6.6), k=3)
    oriented_ell(E_.lerp(Wr, 0.32) + Vector((0, 0, 2.0)), fo_dir, 11.0, 8.4, 7.6, 3.0)
    oriented_ell(E_.lerp(Wr, 0.38) + front * 3.0, fo_dir, 10.0, 6.8, 6.6, 3.0)
    # spines along the forearm's ridge
    for i in range(4):
        base = E_.lerp(Wr, 0.22 + 0.17 * i) + Vector((0, 0, 6.6 - 0.6 * i))
        f.add(sdf.cone(tuple(base), tuple(base + (Vector((0, 0, 1)) - fo_dir * 0.8).normalized() * (4.6 - 0.6 * i)),
                       1.8, 0.2), k=0.8)
    # the hand: wrist, palm flat on the ground, fingers
    f.add(sdf.cone(tuple(Wr), tuple(pc), 6.8, 5.8), k=2.5)
    yaw = math.radians(arm['yaw'])
    f.add(sdf.ellipsoid(tuple(pc + Vector((math.cos(yaw), math.sin(yaw), 0)) * 2.0),
                        (10.0, 9.0, 3.6), np.array(rot(rz=arm['yaw']))), k=3.0)
    for (k0, k1, k2, k3, s, d) in finger_paths(sgn):
        f.add(sdf.cone(tuple(k0 - (k1 - k0) * 0.35), tuple(k1), 3.0 * s, 2.5 * s), k=1.6)
        f.add(sdf.ellipsoid(tuple(k1), (2.9 * s, 2.9 * s, 2.7 * s)), k=0.7)          # knuckles
        f.add(sdf.cone(tuple(k1), tuple(k2), 2.4 * s, 2.0 * s), k=0.7)
        f.add(sdf.ellipsoid(tuple(k2), (2.2 * s, 2.2 * s, 2.0 * s)), k=0.5)
        f.add(sdf.cone(tuple(k2), tuple(k3), 2.0 * s, 1.6 * s), k=0.6)
    f.displace(skin_noise(0.9, 1.25, 20 + sgn), band=3.0)
    f.intersect((lambda X, Y, Z: -0.3 - Z, None))

    def mats(cen):
        return ['hideHot'] * len(cen)
    finish(b, f, 26000, mats)
    # claws: curved, black, biting into the ground
    for (k0, k1, k2, k3, s, d) in finger_paths(sgn):
        down = Vector((0, 0, -1))
        base = k3 - d * 1.2 + Vector((0, 0, 0.6))
        pts = [base + d * (6.5 * s * math.sin(u * 1.35)) + down * ((base.z + 0.8) * u ** 1.6) for u in np.linspace(0, 1, 12)]
        loft(b, 'claw', pts, [1.75 * s * (1 - u) ** 0.75 + 0.03 for u in np.linspace(0, 1, 12)], n=12,
             flat=0.7, twist_ref=(0, 0, 1))


def build_arm_l(b):
    build_arm(b, -1)


def build_arm_r(b):
    build_arm(b, 1)


# --------------------------------------------------------------------------- the wings (extra static)
def wing_skeleton(sgn):
    root = P(13.0 * sgn, 53, -14)
    elbow = Vector((40.0 * sgn, 22.0, 74.0))
    wrist = Vector((56.0 * sgn, 30.0, 88.0))
    tips = [Vector((84.0 * sgn, 40.0, 78.0)), Vector((86.0 * sgn, 46.0, 52.0)), Vector((76.0 * sgn, 44.0, 28.0)),
            Vector((58.0 * sgn, 36.0, 14.0))]
    return root, elbow, wrist, tips


def build_wings(b):
    palette()
    rng = random.Random(5)
    for sgn in (-1, 1):
        root, elbow, wrist, tips = wing_skeleton(sgn)
        arm_pts = spline([root, root.lerp(elbow, 0.5) + Vector((0, 0, 3)), elbow, wrist], 18)
        loft(b, 'wingbone', arm_pts, list(np.linspace(4.2, 2.6, 18)), n=12)
        fingers = []
        for i, tip in enumerate(tips):
            mid = wrist.lerp(tip, 0.5) + Vector((0, 3.5, 2.0 - i))
            pts = spline([wrist, mid, tip], 16)
            loft(b, 'wingbone', pts, list(np.linspace(2.2, 0.35, 16)), n=8)
            fingers.append(pts)
        # a hooked claw on the wrist
        cpts = [wrist + Vector((0.5 * sgn, -1.0, 2.0)) * u * 3.5 + Vector((0, -u * u * 2, 0)) for u in np.linspace(0, 1, 6)]
        loft(b, 'claw', cpts, [1.4 * (1 - u) + 0.05 for u in np.linspace(0, 1, 6)], n=8)
        # membranes between the fingers, and from the last finger down to the back
        chains = fingers[:]
        back = spline([wrist, elbow, P(19.0 * sgn, 40, -15), P(16.0 * sgn, 22, -15)], 16)
        chains.append(back)
        for a_, b2 in zip(chains, chains[1:]):
            membrane(b, a_, b2, sgn, rng)


def membrane(b, A, B, sgn, rng, nu=22, nv=16, t=0.35):
    """A sail of skin between two bones: rows from A to B, sagging backwards (+y) in the middle, the free edge
    scalloped (curving in between the finger tips)."""
    A = spline(A, nv)
    B = spline(B, nv)
    rows = []
    for i in range(nv):
        a, c = A[i], B[i]
        v = i / (nv - 1)
        row = []
        for j in range(nu):
            u = j / (nu - 1)
            p = a.lerp(c, u)
            sag = math.sin(math.pi * u) * (2.0 + 4.5 * v)
            p = p + Vector((0.0, sag, -0.6 * sag))
            if i == nv - 1:                                   # the free edge curves in towards the wrist
                p = p.lerp(A[0].lerp(B[0], u), 0.22 * math.sin(math.pi * u))
            row.append(p)
        rows.append(row)
    # two faces back to back (thin sheet)
    verts, faces = [], []
    for row in rows:
        verts += [tuple(p) for p in row]
    off = len(verts)
    for i in range(nv - 1):
        for j in range(nu - 1):
            a_ = i * nu + j
            faces.append((a_, a_ + 1, a_ + nu + 1, a_ + nu))
    # orient the front face towards the camera (-y) and up
    f0 = faces[len(faces) // 2]
    nrm = (Vector(verts[f0[1]]) - Vector(verts[f0[0]])).cross(Vector(verts[f0[3]]) - Vector(verts[f0[0]]))
    if nrm.dot(Vector((0, -0.8, 0.6))) < 0:
        faces = [f[::-1] for f in faces]
    acc = [Vector((0.0, 0.0, 0.0)) for _ in verts]
    for f_ in faces:
        q = [Vector(verts[x]) for x in f_]
        nn = (q[1] - q[0]).cross(q[3] - q[0])
        for x in f_:
            acc[x] += nn
    back_v = [tuple(Vector(p) - (a.normalized() if a.length > 1e-9 else Vector((0, 1, 0))) * t)
              for p, a in zip(verts, acc)]
    faces2 = [tuple(off + x for x in f[::-1]) for f in faces]
    explicit(b, verts + back_v, faces + faces2, 'wing')


# --------------------------------------------------------------------------- the head (skinned part)
def horn_path(sgn):
    """v3 after screenshots/balrog1.webp: a massive horn from the top of the skull above the temple, rising up and out,
    sweeping over and curving forwards and down so its point frames the face beside the cheek."""
    pts_local = [(9.0, 1.5, 7.5), (13.5, 2.5, 13.5), (20.5, 1.5, 18.5), (28.0, -2.0, 18.5), (33.5, -8.0, 14.0),
                 (35.0, -14.0, 7.0), (32.5, -19.0, 0.5), (28.5, -21.5, -3.5)]
    return [HP(sgn * x, y, z) for (x, y, z) in pts_local]


EYES_L = (5.0, -8.4, 0.4)           # head space (the left eye; x mirrored for the right one)


def build_head(b):
    """The head and neck (a STATIC model since v2). v3 (2026-11-26, the user: "looks like a dragon head, not the
    Balrog; refer to my screenshots"): the film's Balrog: a BROAD, SHORT skull-like face, no snout; a massive brow
    shelf over deep sockets with burning eyes; broad cheekbones; a short bull's nose; a wide snarling maw full of fire
    with great fangs at its corners; a heavy jutting jaw; thick ridged horns rising from the top of the skull and
    sweeping out, over and forwards to frame the face."""
    palette()
    f = sdf.Field((-28, -60, 40), (28, -2, 100), 0.2, far=2.5)
    HRm = HR()

    def HE(x, y, z, r, extra=None):
        R = HRm if extra is None else HRm @ np.array(extra)
        return sdf.ellipsoid(tuple(HP(x, y, z)), tuple(c * HEAD_S for c in r), R)

    def HC(a, b_, ra, rb):
        return sdf.cone(a, b_, ra * HEAD_S, rb * HEAD_S)
    # the neck, from the shoulders up into the skull
    f.add(HC(tuple(NECK_BASE - UP * 4), tuple(HP(0, 4, -4)), 11.0, 8.5), k=0)
    f.add(sdf.ellipsoid(tuple(NECK_BASE.lerp(HP(0, 4, -4), 0.5) + Vector((0, 4, 0))), (9.5, 8.0, 9.0)), k=4)
    for s in (-1, 1):                                  # neck sinews
        f.add(HC(tuple(HP(5.5 * s, 2.0, -7.0)), tuple(NECK_BASE + Vector((7.5 * s, -6.0, 1.0))), 3.2, 3.6), k=2.5)
    # the skull: broad and low
    f.add(HE(0, 3.0, 2.5, (11.0, 10.0, 8.5)), k=4)                    # cranium
    f.add(HE(0, -4.0, 5.0, (9.0, 6.0, 5.0)), k=3)                     # the sloping forehead
    for s in (-1, 1):
        f.add(HE(5.4 * s, -8.2, 3.2, (6.6, 2.6, 1.5), rot(ry=-20 * s, rz=-8 * s)), k=0.6)  # the brow: a knife-edged
        f.add(HE(5.0 * s, -6.8, 4.0, (6.0, 2.6, 2.2), rot(ry=-18 * s)), k=0.8)        # shelf, inner ends low (scowl)
        f.add(HE(9.5 * s, 0.5, 6.5, (4.0, 4.2, 4.0)), k=1.8)                          # the horns' bosses
        f.add(HE(7.6 * s, -5.6, -1.8, (1.7, 5.0, 1.6), rot(rz=26 * s, ry=-30 * s)), k=0.9)   # blade cheekbones
        f.add(HE(8.8 * s, -0.5, -6.5, (2.4, 4.5, 4.6)), k=1.4)                        # jaw muscles
    f.add(HE(0, -9.0, 1.4, (2.4, 2.4, 2.0)), k=0.8)                   # the brow's middle, low (the scowl)
    f.add(HE(0, -7.6, -2.8, (6.4, 3.8, 3.8)), k=1.4)                  # the middle of the face (gaunt)
    f.add(HE(0, -11.0, -2.6, (3.2, 2.2, 2.2)), k=0.9)                 # a short, broad bull's nose
    f.add(HC(tuple(HP(0, -8.8, 1.2)), tuple(HP(0, -11.4, -1.6)), 1.6, 1.8), k=0.8)
    f.add(HE(0, -10.6, -6.2, (6.8, 3.0, 1.4)), k=0.8)                 # the upper lip, thin, drawn back in a snarl
    for s in (-1, 1):                                                  # snarl folds beside the nose
        f.add(HC(tuple(HP(2.4 * s, -11.0, -1.0)), tuple(HP(5.6 * s, -9.6, -6.6)), 0.9, 0.7), k=0.6)
    # the lower jaw: massive, jutting, wide open
    jaw = rot(rx=24)
    f.add(HE(0, -6.0, -13.0, (8.2, 7.6, 2.8), jaw), k=1.6)
    f.add(HE(0, -11.4, -15.6, (5.4, 2.8, 2.6), jaw), k=1.2)           # the chin
    for s in (-1, 1):
        f.add(HC(tuple(HP(8.0 * s, -0.5, -7.0)), tuple(HP(5.8 * s, -10.5, -15.0)), 2.4, 1.9), k=1.2)   # jaw bones
    # a few short spines on the crown, between the horns (the fire rises there)
    for i in range(4):
        for s in (-1, 1):
            c = HP(2.6 * s, 4.0 + 2.8 * i, 10.6 - 0.9 * i)
            tip = c + (HP(3.4 * s, 6.5 + 2.8 * i, 14.5 - 1.0 * i) - HP(2.6 * s, 4.0 + 2.8 * i, 10.6 - 0.9 * i))
            f.add(HC(tuple(c), tuple(tip), 1.3, 0.15), k=0.7)
    # carve: the maw, deep sockets under the brow, the nostrils, hollows under the cheekbones
    f.sub(HE(0, -10.0, -10.4, (6.6, 6.4, 2.8), rot(rx=12)), k=1.0)
    for s in (-1, 1):
        f.sub(HE(EYES_L[0] * s, -8.4, 0.3, (3.0, 2.8, 1.8), rot(rz=-10 * s)), k=0.5)
        f.sub(HE(10.0 * s, -3.0, 2.0, (1.6, 3.0, 2.2)), k=1.0)                       # temple hollows
        f.sub(HE(1.5 * s, -13.0, -2.6, (0.8, 1.2, 0.8), rot(rz=20 * s)), k=0.3)
        f.sub(HE(6.8 * s, -7.5, -5.2, (1.8, 2.6, 1.6)), k=1.0)
    f.displace(skin_noise(0.75, 1.7, 31), band=2.5)                  # craggy volcanic crust

    maw = HE(0, -10.0, -10.4, (7.6, 7.6, 3.6), rot(rx=12))[0]

    def mats(cen):
        X, Y, Z = cen[:, 0], cen[:, 1], cen[:, 2]
        inside = maw(X, Y, Z) < 0
        out = np.where(inside, 'maw', 'face')
        neck = np.array([c[2] < HEAD_C.z - 9 and c[1] > HEAD_C.y + 2 for c in cen])
        return np.where(neck & ~inside, 'hideHot', out)
    finish(b, f, 29000, mats, smooth_iters=1)
    # eyes of flame deep under the brow, slanted
    for s in (-1, 1):
        c = HP(EYES_L[0] * s, EYES_L[1], EYES_L[2])
        R = Matrix.Rotation(math.radians(HEAD_PITCH), 4, 'X') @ Matrix.Rotation(math.radians(-10 * s), 4, 'Y')
        ellipsoid_mesh(b, 'eye', c, tuple(x * HEAD_S for x in (2.1, 0.9, 0.75)), R)
    # the horns: thick, ridged
    for s in (-1, 1):
        pts = spline(horn_path(s), 120)
        n = len(pts)
        radii = [HEAD_S * (6.0 * (1 - i / (n - 1)) ** 0.75 + 0.1) for i in range(n)]
        loft(b, 'horn', pts, radii, n=24, flat=0.85, ridges=(0.32, 0.03), twist_ref=(0, 0, 1))
    # fangs: great ones at the corners of the maw, rows of lesser teeth
    teeth = []
    for s in (-1, 1):
        teeth.append((HP(5.0 * s, -10.6, -8.0), HP(4.7 * s, -11.4, -12.8), 1.25))      # upper fangs
        teeth.append((HP(4.2 * s, -12.0, -14.4), HP(4.0 * s, -12.6, -10.6), 1.0))      # lower fangs
    for x in (-3.0, -1.5, 0.0, 1.5, 3.0):
        teeth.append((HP(x, -12.0 + 0.3 * abs(x), -8.0), HP(x, -12.2 + 0.3 * abs(x), -9.8), 0.55))
        teeth.append((HP(x * 0.9, -12.4 + 0.3 * abs(x), -14.0), HP(x * 0.9, -12.6 + 0.3 * abs(x), -12.5), 0.5))
    for a, c, r in teeth:
        d = c - a
        bend = Vector((0, -0.15, 0)) * d.length
        pts = [a + d * u + bend * math.sin(math.pi * u) for u in np.linspace(0, 1, 7)]
        loft(b, 'teeth', pts, [HEAD_S * r * (1 - u) ** 0.7 + 0.03 for u in np.linspace(0, 1, 7)], n=8)


def ellipsoid_mesh(b, mat, c, r, R, n=16, rings=10):
    """A UV ellipsoid (explicit mesh) at c, radii r, rotation R (4x4)."""
    verts, faces = [], []
    for i in range(1, rings):
        a = math.pi * i / rings
        for j in range(n):
            t = 2 * math.pi * j / n
            v = Vector((r[0] * math.sin(a) * math.cos(t), r[1] * math.sin(a) * math.sin(t), r[2] * math.cos(a)))
            verts.append(tuple(Vector(c) + (R @ v.to_4d()).to_3d()))
    top, bot = len(verts), len(verts) + 1
    verts.append(tuple(Vector(c) + (R @ Vector((0, 0, r[2], 1))).to_3d()))
    verts.append(tuple(Vector(c) + (R @ Vector((0, 0, -r[2], 1))).to_3d()))
    for i in range(rings - 2):
        for j in range(n):
            a_, b_ = i * n + j, i * n + (j + 1) % n
            faces.append((a_, a_ + n, b_ + n, b_))
    for j in range(n):
        faces.append((top, j, (j + 1) % n))
        o = (rings - 2) * n
        faces.append((bot, o + (j + 1) % n, o + j))
    explicit(b, verts, faces, mat)


# --------------------------------------------------------------------------- fire: bones, effects
STONES = [(-21.0, -9.0), (19.0, -11.0), (3.0, -14.5)]     # in the rift, just inside its rim (the skinned part)
EYE_C = (STONES[2][0], STONES[2][1], MAGMA_Z)                 # the skinned part's pivot (nothing visible moves)
T_FLAME = 12.0                                            # v2: slow, persistent flames (whole cycles of 12 s)


def build_eye(b):
    """The SKINNED part, v2 (2026-11-26): the v1 head here never drew in game (only the effects on its bones did, like
    Smaug's skinned dragon), so the head is a static model now and this part is just three stones in the rift that
    carry the effect bones. If it fails to draw, nothing is lost."""
    palette()
    rng = random.Random(4)
    for (x, y) in STONES:
        s = rng.uniform(1.4, 2.0)
        ellipsoid_mesh(b, 'rock', (x, y, gz(x, y) + 0.6), (s * 1.3, s, s * 0.7),
                       Matrix.Rotation(math.radians(rng.uniform(0, 180)), 4, 'Z'), n=10, rings=6)


def _head_top():
    return HP(0.0, 5.0, 12.0)


def rig():
    """Bones of the skinned part (in-game units): (name, parent, position, effect key)."""
    bones = [('fxglow', 'eyeroot', tuple(HP(0.0, -11.8, EYES_L[2])), 'BALROG_GLOW'),
             ('fxcrown', 'eyeroot', tuple(_head_top()), 'BALROG_CROWN'),
             ('fxheadf', 'eyeroot', tuple(HP(0.0, 8.0, 4.0)), 'BALROG_HEAD')]
    # (v4: the stock Great Lighthouse fires on the head, arms and in the rift are gone: they flickered wildly when
    # zoomed in; our rest-pose flame tongues render right at every zoom)
    bones.append(('fxmane', 'eyeroot', tuple(P(0, 58, -6)), 'BALROG_MANE'))
    bones.append(('fxbody', 'eyeroot', tuple(P(0, 40, 0)), 'BALROG_BODY'))
    for s, key in ((-1, 'BALROG_ARML'), (1, 'BALROG_ARMR')):
        bones.append(('fxarm%s' % ('l' if s < 0 else 'r'), 'eyeroot', tuple(ARMS[s]['elbow']), key))
        bones.append(('fxfore%s' % ('l' if s < 0 else 'r'), 'eyeroot', tuple(ARMS[s]['wrist']),
                      'BALROG_FORE' + ('L' if s < 0 else 'R')))
    return bones


def _gaze(t):
    """v2: the head is static; the stones' bone keeps a real (tiny) curve, as a skinned part needs one."""
    return 0.3 * math.sin(2 * math.pi * t / 12.0)


GAZE = dict(fn=_gaze, T=12.0, spans=60)


def glow_effect(k):
    """The burning eyes: an additive quad just in front of them (glow.py; close, so the game camera's angle barely
    shifts the lines off the eyes); the maw glows by its own material."""
    pos = HP(0.0, -11.8, EYES_L[2])
    lift = math.tan(math.radians(52.0))         # seen from the game camera, a point behind the quad shows higher

    def onto(p):
        return Vector((p.x, pos.y, p.z + (p.y - pos.y) * lift))
    eyes = [onto(HP(EYES_L[0] * s, EYES_L[1], EYES_L[2])) for s in (-1, 1)]
    X0, X1, Z0_, Z1 = pos.x - 10, pos.x + 10, eyes[0].z - 5, eyes[0].z + 5
    sl = [0.35 if e.x < 0 else -0.35 for e in eyes]       # slanted: the inner ends low (a scowl)
    lines = [(e.x - 1.3, e.z + d, e.x + 1.3, e.z - d, 0.7, (255, 200, 90)) for e, d in zip(eyes, sl)]
    return dict(name='MEC_BalrogGlow',
                quads=[((X0 - pos.x) * k, (X1 - pos.x) * k, (Z0_ - pos.z) * k, (Z1 - pos.z) * k, 0.0)],
                tex_args=dict(lines=lines, box=(X0, X1, Z0_, Z1), px=1024, color=(255, 190, 90), halo=0.75,
                              core=0.9, sigma=(0.6, 1.8)))


# the flame tongues: emitters in in-game units (world), turned into file units relative to the effect's bone
def _crown_emitters():
    em = []
    for i in range(13):
        a = math.pi * (i / 12.0)
        x = 9.0 * math.cos(a)
        y = 3.0 + 5.0 * math.sin(a)
        z = 10.5 + 2.0 * math.sin(a)
        em.append((HP(x, y + 1.5, z), 1.0))
    for s in (-1, 1):                     # the horn roots and the brow's sides
        em.append((HP(10.5 * s, 2.5, 8.0), 0.8))
    return em


def _mane_emitters():
    em = []
    for i in range(9):                    # along the shoulders' tops
        x = -30 + 60 * i / 8
        s = 55.0 - 3.0 * abs(x) / 30
        em.append((P(x, s + 4.0, -5.0), 0.9 if abs(x) > 6 else 1.2))
    for i in range(6):                    # the back of the neck and the upper back
        em.append((P(0.0 + (i % 2 - 0.5) * 10, 60 - 4 * i, -12.0 - i), 1.0))
    return em


def _body_emitters():
    """The torso: the upper back between the shoulder blades, the flanks, the top of the chest beside the neck."""
    em = []
    for i in range(5):
        em.append((P((i - 2) * 6.0, 46 - 2.0 * abs(i - 2), -14.0), 1.0))       # the upper back
    for s in (-1, 1):
        for i in range(3):
            em.append((P(22.0 * s, 26 + 7 * i, -6.0), 0.8))                 # the flanks behind the arms
        em.append((P(13.0 * s, 52, 6.0), 0.75))                            # the top of the chest
    return em


def _head_emitters():
    """The sides and the back of the skull, behind the horns' roots, the top of the neck."""
    em = []
    for s in (-1, 1):
        for i in range(4):
            em.append((HP(10.0 * s, 1.0 + 3.5 * i, 7.0 - 1.5 * i), 0.85))
        em.append((HP(8.0 * s, 13.0, -2.0), 0.8))
        em.append((HP(6.0 * s, 10.0, 8.5), 1.0))
    for i in range(3):
        em.append((HP((i - 1) * 4.0, 15.0, 3.0), 0.9))
    return em


def _arm_emitters(sgn, part):
    """On the arm's surface facing the game camera (up and towards it): the axis + (radius + 1) along that direction
    (v2: v1's points lay inside the muscles, so the tongues, leaning back, were hidden in the arm)."""
    J, E_, Wr, pc = SHOULDER[sgn], ARMS[sgn]['elbow'], ARMS[sgn]['wrist'], ARMS[sgn]['palm']
    out_ = Vector((0.0, -0.5, 0.87)).normalized()
    em = []
    if part == 'upper':
        for i in range(4):                          # the top of the shoulder
            em.append((J + Vector((sgn * (i - 1.5) * 3.0, -2.0, 14.0)), 0.95))
        for i in range(9):
            u = i / 8
            r = 14.5 - 4.0 * u
            em.append((J.lerp(E_, 0.12 + 0.86 * u) + out_ * (r + 1.0), 0.9))
        em.append((E_ + out_ * 10.0, 1.0))
        em.append((E_ + out_ * 8.0 + Vector((sgn * 4.0, 0.0, 0.0)), 0.8))
    else:
        for i in range(11):
            u = i / 10
            r = 10.5 - 4.0 * u
            em.append((E_.lerp(Wr, 0.06 + 0.9 * u) + out_ * (r + 0.8), 0.9 - 0.3 * u))
        for i in range(4):                          # the back of the hand
            em.append((pc + Vector(((i - 1.5) * 3.0, -1.0, 4.2)), 0.55))
    return em


FLAME_SETS = {      # key -> (effect file, bone, emitters fn, tongue height (in-game units), per emitter, glow, lean back)
    'BALROG_CROWN': ('MEC_BalrogCrown', 'fxcrown', _crown_emitters, 32.0, 2, True, None),
    'BALROG_HEAD': ('MEC_BalrogHead', 'fxheadf', _head_emitters, 24.0, 2, False, None),
    'BALROG_MANE': ('MEC_BalrogMane', 'fxmane', _mane_emitters, 28.0, 2, False, None),
    'BALROG_BODY': ('MEC_BalrogBody', 'fxbody', _body_emitters, 22.0, 2, False, -30.0),
    'BALROG_ARML': ('MEC_BalrogArmL', 'fxarml', lambda: _arm_emitters(-1, 'upper'), 30.0, 2, False, -10.0),
    'BALROG_ARMR': ('MEC_BalrogArmR', 'fxarmr', lambda: _arm_emitters(1, 'upper'), 30.0, 2, False, -10.0),
    'BALROG_FOREL': ('MEC_BalrogForeL', 'fxforel', lambda: _arm_emitters(-1, 'fore'), 25.0, 2, False, -10.0),
    'BALROG_FORER': ('MEC_BalrogForeR', 'fxforer', lambda: _arm_emitters(1, 'fore'), 25.0, 2, False, -10.0),
}


def flame_tongues(key, k):
    import flames
    name, bone, emf, hgt, per, glow, tilt = FLAME_SETS[key]
    bw = Vector(next(r[2] for r in rig() if r[0] == bone))
    rng = random.Random(zlib.crc32(name.encode()) & 0xffff)
    em = [(((p - bw) * k).x, ((p - bw) * k).y, ((p - bw) * k).z, s) for p, s in emf()]
    tongues = flames.steady_tongues(em, T_FLAME, rng, per=per, size=hgt * k, tilt=tilt)
    if glow:      # a big soft heat glow behind the head, breathing
        tongues = tongues[:29]
        g = flames.Tongue(((0.0), (6.0 * k), (2.0 * k)), 46.0 * k, 52.0 * k, flames.GLOW_CELL, T_FLAME, 1, 0.0,
                          0.0, 0.0, glow=True, seed=3)
        tongues.append(g)
    return tongues[:30]


def model_effects(out_dir, k):
    import flames
    files = []
    for key, (name, bone, _, _, _, _, _) in FLAME_SETS.items():
        files += flames.write(out_dir, name, flame_tongues(key, k), T_FLAME)
    return files


def preview_overlays(out_dir):
    import os
    import flames
    out = []
    for key, (name, bone, _, _, _, _, _) in FLAME_SETS.items():
        bw = next(r[2] for r in rig() if r[0] == bone)
        out += flames.overlays(os.path.join(out_dir, name + '_DIFF.dds'), flame_tongues(key, 4.0), bw, 4.0, 1.37)
    return out


EXTRA_STATICS = [('torso', build_torso, 2048), ('arm_l', build_arm_l, 2048), ('arm_r', build_arm_r, 2048),
                 ('wings', build_wings, 2048), ('head', build_head, 2048)]

# preview views: the game's camera on the whole landmark, the head, a hand, the side
PREVIEW = [((0, -200, 250), (0, -8, 30), 38),
           ((0, -95, 120), (0, -24, 68), 34),
           ((-30, -100, 55), (-56, -42, 6), 30),
           ((150, -70, 90), (0, 0, 40), 36)]
PREVIEW_EYE = [((0, -70, 95), (0, -25, 68), 40), ((40, -60, 80), (0, -25, 68), 40)]
