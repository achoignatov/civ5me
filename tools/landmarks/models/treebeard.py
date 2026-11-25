"""Treebeard (Fangorn), the eldest of the Ents, with Merry and Pippin on his shoulders: the landmark of the
city-state of Entwood (an IMPROVEMENT, docs/LANDMARKS.md). 2026-11-25, the user's reference screenshots/treebeard.webp.

Look (Tolkien, The Two Towers III.4, and the 2002 film):
  * "at least fourteen foot high, very sturdy, with a tall head, and hardly any neck"; bark-like hide, "green and
    grey bark"; "the large feet had seven toes each"; long arms;
  * "a most extraordinary face ... a sweeping grey beard, bushy, almost twiggy at the roots, thin and mossy at the
    ends"; "deep eyes ... brown, shot with a green light", under a heavy brow;
  * the film's Ent (Weta: a 4.5 m animatronic + CG; the beard of twigs, the moss as wide hanging strands with a
    transparency map): long gnarled limbs of twisted cords, a tall head crowned with branches and sprigs of leaves;
  * the user's reference: massive and mossy, ram-like curling branches on the head, autumn touches in the crown.
  * Merry and Pippin ride on his shoulders in their grey-green Lorien cloaks with the green leaf brooches (one per
    shoulder: Pippin on the viewer's left = Treebeard's right shoulder, Merry on the right).

In-game units (improvement Scale 0.25, the writer's x4), origin = tile centre, ground z = 0, -Y = south = towards the
game camera. Fills its own hex; about 104 high.

Parts:
  * static: the forest floor round his feet, a low root mound (hides the stock houses in the middle), his seven
    toes on each foot running on as roots across the tile, ferns, grass, mossy stones;
  * ONE skinned model of five meshes (lmodel skins=, a 32k budget and its own texture each):
      'body'    the bark: legs, trunk, arms, hands (2048);
      'head'    the head and face at high resolution, eyes, lids, twig brows (2048);
      'crown'   the horns, the crown of branches, the branches behind the shoulders, their leaves (2048);
      'beard'   the lichen beard and moustache (two cut-out lichens, twigs, lichen clumps), hanging moss (2048);
      'riders'  Merry and Pippin, small (HOB_S): halflings on a HUGE Ent (1024).
    v2 (user, after the first in-game test: "size and animation perfect"): more detail in the face and the beard;
    the hobbits much more detailed (no dolls) and much smaller.
    Every vertex is weighted along a CHAIN of bones from the ankles up (eyepivot -> lean1..lean4 -> crown) and the
    arms on their own bones, so the whole Ent BENDS like a tree in the wind: the roots stay, the knees give a
    little, the top moves most (about 4.5 units), the crown and the hanging arms lag behind. The hobbits carry the
    weights of their seats, so they ride with the shoulders.
  * The idle loop (LOOP s) = MOTIONS: a slow lean back and forth (12 s) with a smaller side roll; nothing else.
"""
import math
import random

from mathutils import Matrix, Vector

import blib
import sprites
from blib import material, hexcol as h, blob, lathe
from moria_v4 import fbm, ridged, tube, smooth, _spline as spline
from erebor import hex_dist

BAKE = True
BAKE_PX = 2048
EYE_AO = 16
HEX = 33.6

LOOP = 24.0                 # s: two slow sways back and forth per loop, a side roll once
SPANS = 48

# --------------------------------------------------------------------------- the figure (in-game units)
LEG = [(8.8, 0.8, 1.5), (9.2, -0.8, 11.0), (8.9, -3.0, 20.5), (8.2, -1.0, 29.0), (7.0, 1.6, 38.5)]   # ankle -> hip
LEG_R = [6.0, 4.5, 4.9, 5.6, 6.6]
ARM = [(14.0, 1.5, 62.0), (17.8, 0.8, 54.0), (19.6, -0.6, 45.0), (19.9, -2.6, 37.0), (19.5, -4.6, 29.5)]
ARM_R = [5.2, 4.2, 3.9, 3.2, 2.7]
SHOULDER_J = (14.0, 1.5, 62.0)
SEAT = (13.2, -2.6, 67.0)            # where a hobbit sits (x mirrored): on the front of the shoulder's top
HOB_S = 11.0                         # in-game units per hobbit height: halflings on a HUGE Ent (user, 2026-11-25)
HEAD_Z = (60.5, 89.0)
HEAD_YC = -2.6

CHAIN = [('eyeroot', 0.0), ('eyepivot', 5.0), ('lean1', 21.0), ('lean2', 37.0), ('lean3', 52.0), ('lean4', 64.0),
         ('crown', 84.0)]
BONES = [('eyeroot', None, (0.0, 0.0, 0.0)), ('eyepivot', 'eyeroot', (0.0, 0.5, 5.0)),
         ('lean1', 'eyepivot', (0.0, -0.5, 21.0)), ('lean2', 'lean1', (0.0, 1.0, 37.0)),
         ('lean3', 'lean2', (0.0, 1.0, 52.0)), ('lean4', 'lean3', (0.0, 0.5, 64.0)),
         ('crown', 'lean4', (0.0, 0.0, 84.0)),
         ('arml', 'lean4', (-SHOULDER_J[0], SHOULDER_J[1], SHOULDER_J[2])),
         ('armr', 'lean4', SHOULDER_J)]
ARM_MATS = {'barkA', 'mossS'}


def _P(t):
    """The lean forward/back, degrees in all (+ = the top towards the camera): two slow sways per loop."""
    return 2.6 * math.sin(2 * math.pi * 2 * t / LOOP) + 0.6 * math.sin(2 * math.pi * 3 * t / LOOP + 0.8)


def _R(t):
    """The side roll, degrees in all."""
    return 1.0 * math.sin(2 * math.pi * t / LOOP + 1.9) + 0.3 * math.sin(2 * math.pi * 4 * t / LOOP + 0.3)


_SHARE = [('eyepivot', 0.22, 0.0), ('lean1', 0.22, 0.25), ('lean2', 0.20, 0.5), ('lean3', 0.18, 0.75),
          ('lean4', 0.18, 1.0)]       # (bone, share of the lean, lag s): a wave running up the body
MOTIONS = {bn: (lambda t, f=f, lag=lag: (f * _P(t - lag), f * _R(t - lag), 0.0)) for bn, f, lag in _SHARE}
MOTIONS['crown'] = lambda t: (0.3 * _P(t - 1.8) + 0.22 * math.sin(2 * math.pi * 6 * t / LOOP),
                              0.3 * _R(t - 1.8) + 0.18 * math.sin(2 * math.pi * 5 * t / LOOP + 1.0), 0.0)
MOTIONS['arml'] = lambda t: (-0.45 * _P(t - 1.3) + 0.3 * math.sin(2 * math.pi * 3 * t / LOOP + 0.4),
                             0.4 * math.sin(2 * math.pi * 2 * t / LOOP + 2.0), 0.0)
MOTIONS['armr'] = lambda t: (-0.45 * _P(t - 1.5) + 0.3 * math.sin(2 * math.pi * 3 * t / LOOP + 2.1),
                             0.4 * math.sin(2 * math.pi * 2 * t / LOOP + 0.7), 0.0)


def chain_w(z):
    if z <= CHAIN[0][1]:
        return [(CHAIN[0][0], 1.0)]
    for (b0, z0), (b1, z1) in zip(CHAIN, CHAIN[1:]):
        if z < z1:
            t = smooth((z - z0) / (z1 - z0))
            return [(b0, 1.0 - t), (b1, t)]
    return [(CHAIN[-1][0], 1.0)]


def weights(res, suffix):
    """Per vertex [(bone, weight)]: along the chain by height; the arms (and their moss) blend onto their own bone
    from the shoulder down; the hobbits carry the weights of their seats."""
    seat = chain_w(SEAT[2])
    out = []
    for v, m in zip(res.verts, res.vmat):
        p = v[0]
        if m.startswith('h_') or suffix == 'riders':
            out.append(seat)
            continue
        w = chain_w(p[2])
        if m in ARM_MATS:
            sj = Vector((math.copysign(SHOULDER_J[0], p[0]), SHOULDER_J[1], SHOULDER_J[2]))
            s = smooth((Vector(p) - sj).length / 8.0 - 0.2)
            arm = 'armr' if p[0] > 0 else 'arml'
            w = [(bn, x * (1.0 - s)) for bn, x in w] + [(arm, s)]
        out.append(w)
    return out


# --------------------------------------------------------------------------- helpers
class Local:
    """A builder proxy: everything added through it is placed by the matrix M."""
    def __init__(self, b, M):
        self.b, self.M = b, M

    def add(self, verts, faces, mat, smooth=False, M=None):
        self.b.add(verts, faces, mat, smooth=smooth, M=self.M @ M if M is not None else self.M)

    def __getattr__(self, k):
        return getattr(self.b, k)


def card(b, mat, c, facing, w, hgt, up=(0.0, 0.0, 1.0), roll=0.0, anchor_top=False):
    """A cut-out card (bake.py SPRITES), single-sided towards `facing`; anchor_top hangs it from c."""
    f = Vector(facing).normalized()
    U = Vector(up)
    ey = (U - f * f.dot(U)).normalized()
    ex = ey.cross(f)
    r = math.radians(roll)
    ex, ey = ex * math.cos(r) + ey * math.sin(r), -ex * math.sin(r) + ey * math.cos(r)
    ex, ey = ex * (w / 2), ey * (hgt / 2)
    C = Vector(c) - (ey if anchor_top else Vector())
    v = [tuple(C - ex - ey), tuple(C + ex - ey), tuple(C + ex + ey), tuple(C - ex + ey)]
    b.add(v, [(0, 1, 2, 3)], mat)
    if not hasattr(b, 'sprite_uv'):
        b.sprite_uv = {}
    b.sprite_uv[len(b.faces) - 1] = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


def resample(pts, step):
    """A Catmull-Rom path through pts, about `step` apart."""
    L = sum((Vector(a) - Vector(b_)).length for a, b_ in zip(pts, pts[1:]))
    return [Vector(p) for p in spline(pts, max(len(pts) * 2, int(L / step)))]


def frames(P):
    """Parallel-transport frames (tangent, a, c) along a path."""
    out, prev = [], None
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        a = t.orthogonal().normalized() if prev is None else (prev - t * prev.dot(t)).normalized()
        prev = a
        out.append((t, a, t.cross(a)))
    return out


def lerp_r(radii, f):
    x = f * (len(radii) - 1)
    i = min(int(x), len(radii) - 2)
    return radii[i] + (radii[i + 1] - radii[i]) * smooth(x - i)


def gnarl(b, mat, pts, radii, rng, cords=5, twist=0.6, core_n=12, cord_n=7, step=1.0, cap=True):
    """A limb of the Ent: a core wrapped in twisted cords of bark (like the film's ropey limbs and the
    reference's fibrous trunk). The cords taper into the core at both ends."""
    P = resample(pts, step)
    F = frames(P)
    n = len(P)
    fr = [i / (n - 1) for i in range(n)]
    seed = rng.uniform(0, 100)
    core = [lerp_r(radii, f) * (0.8 + 0.12 * fbm(f * 6 + seed, seed, 3)) for f in fr]
    tube(b, mat, [tuple(p) for p in P], core, n=core_n, tip=False)
    for k in range(cords):
        a0 = 2 * math.pi * k / cords + rng.uniform(-0.35, 0.35)
        w = rng.uniform(0.8, 1.2)
        s0, s1 = rng.uniform(0.0, 0.12), rng.uniform(0.86, 1.0)
        tw = twist * rng.uniform(0.8, 1.2)
        pk, rk = [], []
        for i in range(n):
            f = fr[i]
            if f < s0 or f > s1:
                continue
            env = smooth(min(1.0, (f - s0) / 0.1, (s1 - f) / 0.1))
            ang = a0 + tw * 2 * math.pi * f + 0.3 * math.sin(f * 9 + k)
            R = lerp_r(radii, f)
            _, a, c = F[i]
            off = R * (0.2 + 0.42 * env) * (1 + 0.15 * fbm(f * 8, k + seed, 2))
            pk.append(tuple(P[i] + off * (math.cos(ang) * a + math.sin(ang) * c)))
            rk.append(R * 0.4 * w * (0.45 + 0.55 * env) * (1 + 0.2 * fbm(f * 11, k * 3 + seed, 2)))
        if len(pk) > 2:
            tube(b, mat, pk, rk, n=cord_n, tip=False)


def ring_grid(b, mat, rows, cap_top=None, cap_bottom=None):
    """A closed surface from rings of points (each counter-clockwise seen from above, bottom to top)."""
    n = len(rows[0])
    verts = [tuple(p) for row in rows for p in row]
    faces = []
    for i in range(len(rows) - 1):
        for j in range(n):
            a, b_ = i * n + j, i * n + (j + 1) % n
            faces.append((a, b_, b_ + n, a + n))
    if cap_top is not None:
        c = len(verts)
        verts.append(tuple(cap_top))
        o = (len(rows) - 1) * n
        faces += [(o + j, o + (j + 1) % n, c) for j in range(n)]
    if cap_bottom is not None:
        c = len(verts)
        verts.append(tuple(cap_bottom))
        faces += [((j + 1) % n, j, c) for j in range(n)]
    b.add(verts, faces, mat, smooth=True)


def keyed(keys, z):
    """Interpolate a profile [(z, values...)] at z (smoothly)."""
    if z <= keys[0][0]:
        return keys[0][1:]
    for k0, k1 in zip(keys, keys[1:]):
        if z <= k1[0]:
            t = smooth((z - k0[0]) / (k1[0] - k0[0]))
            return tuple(a + (b_ - a) * t for a, b_ in zip(k0[1:], k1[1:]))
    return keys[-1][1:]


def g(x, s):
    return math.exp(-(x / s) ** 2)


# --------------------------------------------------------------------------- materials
def palette():
    material('bark', h('5c4c3c'), h('453a2f'))
    blib.PALETTE['bark'].update(scale=0.9, vcracks=(1.2, 0.5), cavity=0.9, moss=(h('5a6a30'), 300.0),
                                speckle=[(0.35, 0.3, h('72775c')), (0.9, 0.2, h('7b7f66')), (2.6, 0.12, h('8b8d76')),
                                         (1.6, 0.16, h('3e3328'))])
    blib.PALETTE['barkA'] = dict(blib.PALETTE['bark'])
    material('barkC', h('5f5141'), h('4a3f33'))
    blib.PALETTE['barkC'].update(scale=1.4, vcracks=(1.6, 0.5), cavity=0.85, moss=(h('5f6f35'), 300.0),
                                 speckle=[(1.5, 0.2, h('7f826a'))])
    material('face', h('6a5642'), h('574737'))
    blib.PALETTE['face'].update(scale=1.3, vcracks=(1.8, 0.4), cavity=1.0, moss=(h('5f6c36'), 300.0),
                                speckle=[(1.4, 0.14, h('7f7f68')), (3.2, 0.08, h('3e3328'))])
    material('eye', h('4f4422'), spec=0.95, refl=210, ao=False)       # "brown, shot with a green light"
    blib.PALETTE['eye'].update(solid=True)
    material('pupil', h('1d1a12'), spec=0.95, refl=230, ao=False)
    blib.PALETTE['pupil'].update(solid=True)


def crown_palette():
    palette()
    for name, img in (('leafS0', lambda: sprites.leaf_cluster(31, base=(0.27, 0.38, 0.15), light=-0.08, autumn=0.08)),
                      ('leafS1', lambda: sprites.leaf_cluster(32, base=(0.33, 0.42, 0.17), light=0.08, autumn=0.3))):
        material(name, h('5b6a40'), ao=False, spec=0.12, refl=5)
        blib.PALETTE[name].update(sprite=_sprite(name, img))


def head_palette():
    palette()
    blib.PALETTE['face'].update(scale=2.2, vcracks=(3.0, 0.35), cavity=1.1)
    material('iris', h('4d4a22'), h('5a5326'), spec=0.95, refl=200, ao=False)    # brown shot with green
    blib.PALETTE['iris'].update(scale=40.0, speckle=[(30.0, 0.3, h('5f6a2a')), (22.0, 0.2, h('3a2c14'))])
    material('glint', h('e8e4d0'), spec=1.0, refl=255, ao=False)
    blib.PALETTE['glint'].update(solid=True)
    material('twig', h('57534a'), h('48443b'))
    blib.PALETTE['twig'].update(scale=4.0, vcracks=(2.0, 0.3), cavity=0.6, speckle=[(3.0, 0.25, h('6f765a'))])


def beard_palette():
    palette()
    for name, img in (('beardS', lambda: sprites.hanging_moss(33)),
                      ('beardS2', lambda: sprites.hanging_moss(35, n=260, base=(0.35, 0.39, 0.26),
                                                               tip=(0.55, 0.58, 0.42), twigs=24, taper=0.45)),
                      ('mossS', lambda: sprites.hanging_moss(34, base=(0.33, 0.39, 0.2), tip=(0.47, 0.54, 0.3),
                                                             taper=0.2, twigs=4))):
        material(name, h('5b6a40'), ao=False, spec=0.12, refl=5)
        blib.PALETTE[name].update(sprite=_sprite(name, img))
    material('twig', h('6d675a'), h('5b5548'))
    blib.PALETTE['twig'].update(scale=4.0, vcracks=(2.0, 0.3), cavity=0.6)
    material('lichen', h('6c735a'), h('5a6249'))
    blib.PALETTE['lichen'].update(scale=6.0, cavity=1.0, speckle=[(8.0, 0.25, h('9a9d82')), (6.0, 0.2, h('4f5a34'))])


def riders_palette():
    """Merry and Pippin (film: Lorien cloaks grey-green, the green leaf brooch; Pippin darker hair, Merry lighter)."""
    palette()
    material('twig', h('6d675a'), h('5b5548'))
    blib.PALETTE['twig'].update(scale=30.0, cavity=0.6)
    material('h_skin', h('b08a6c'), h('aa8467'))
    blib.PALETTE['h_skin'].update(scale=10.0, cavity=0.7)
    material('h_lip', h('9a6a58'))
    blib.PALETTE['h_lip'].update(solid=True)
    material('h_eyew', h('d8d2c4'), spec=0.6, refl=80)
    blib.PALETTE['h_eyew'].update(solid=True)
    material('h_iris', h('3d3020'), spec=0.8, refl=120)
    blib.PALETTE['h_iris'].update(solid=True)
    material('h_cloak', h('6a6f57'), h('5c614b'))
    blib.PALETTE['h_cloak'].update(scale=25.0, cavity=0.9)
    for who, hair, coat, vest, breech in (('P', '4a3220', '3d4650', '6b3a2e', '4f4434'),
                                          ('M', '7a5030', '6e5a36', '5c6a3a', '5a4632')):
        for nm, c in (('h_hair' + who, hair), ('h_coat' + who, coat), ('h_vest' + who, vest),
                      ('h_breech' + who, breech)):
            material(nm, h(c), tuple(x * 0.88 for x in h(c)))
            blib.PALETTE[nm].update(scale=40.0, cavity=0.9 if nm.startswith('h_hair') else 0.7)
    material('h_shirt', h('d6cdb8'), h('c8bfaa'))
    blib.PALETTE['h_shirt'].update(scale=30.0, cavity=0.5)
    for nm in ('h_skin', 'h_hairP', 'h_hairM', 'h_lip'):           # faces and hair: more of the texture
        blib.PALETTE[nm]['uv_boost'] = 3.0
    material('h_brass', h('b9954a'), spec=0.9, refl=170)
    blib.PALETTE['h_brass'].update(solid=True)
    material('h_brooch', h('4f8a3a'), spec=0.9, refl=150)
    blib.PALETTE['h_brooch'].update(solid=True)
    material('h_silver', h('c8ccd0'), spec=1.0, refl=220)
    blib.PALETTE['h_silver'].update(solid=True)


def ground_palette():
    palette()
    material('soil', h('4f4433'), h('3f3628'))
    blib.PALETTE['soil'].update(scale=0.5, cavity=0.5, moss=(h('4f5f2b'), 30.0),
                                speckle=[(1.8, 0.2, h('6f5530')), (2.6, 0.13, h('86602f')), (1.2, 0.3, h('4c5a2a')),
                                         (3.6, 0.08, h('9a7a46'))])           # leaf litter, moss
    blib.PALETTE['barkR'] = dict(blib.PALETTE['bark'])
    material('rock', h('7b776c'), h('66625a'))
    blib.PALETTE['rock'].update(scale=0.8, cracks=1.2, cavity=0.8, moss=(h('56662f'), 30.0))
    for name, img in (('fernS', lambda: sprites.fern(41, fronds=12)),
                      ('grassS0', lambda: sprites.grass_tuft(42, base=(0.2, 0.28, 0.1), tip=(0.45, 0.52, 0.26), dry=0.3)),
                      ('grassS1', lambda: sprites.grass_tuft(43, base=(0.2, 0.27, 0.1), tip=(0.5, 0.5, 0.28), dry=0.5))):
        material(name, h('4b5f2a'), ao=False, spec=0.1, refl=4)
        blib.PALETTE[name].update(sprite=_sprite(name, img))


_SPRITES = {}


def _sprite(name, make):
    if name not in _SPRITES:
        _SPRITES[name] = make()
    return _SPRITES[name]


CROWN = dict(c=(0.0, 3.0, 90.0), r=(22.0, 13.0, 13.0))
CAM = Vector((0.0, -0.62, 0.78))


def normals(p, mat):
    """Leaves lit as one crown; beard and moss lit like a front face; ground cards like the ground."""
    if mat.startswith('leafS'):
        (cx, cy, cz), (rx, ry, rz) = CROWN['c'], CROWN['r']
        n = Vector(((p[0] - cx) / rx, (p[1] - cy) / ry, (p[2] - cz) / rz + 0.4))
        return tuple(n.normalized()) if n.length > 1e-6 else (0.0, 0.0, 1.0)
    if mat in ('beardS', 'beardS2', 'mossS'):
        return tuple(Vector((p[0] * 0.03, -1.0, 0.55)).normalized())
    if mat in ('fernS', 'grassS0', 'grassS1'):
        return (0.0, 0.0, 1.0)
    return None


# --------------------------------------------------------------------------- the ground (static)
def height(x, y):
    m = math.exp(-((x / 15.0) ** 2 + ((y - 0.5) / 11.5) ** 2))
    return 4.3 * m + 0.7 * fbm(x * 0.13, y * 0.13, 4, 7) * m - 0.15


def toe_angles(side):
    a = [-150.0, -126.0, -103.0, -80.0, -57.0, -33.0, 118.0]       # the left foot (x < 0): fanning out, one behind
    return a if side < 0 else [180.0 - x for x in a]


def foot_and_roots(b, rng, side):
    fx, fy = side * LEG[0][0], LEG[0][1]
    z0 = height(fx, fy)
    lathe(b, 'barkR', [(0.0, -0.8), (8.0, -0.8), (7.4, 0.9), (6.4, 2.8), (5.8, 5.0), (5.5, 7.2), (0.0, 7.2)], 22,
          fx, fy, z0 - 0.2, smooth=True, jitter=0.12)
    for k, a in enumerate(toe_angles(side)):
        a = math.radians(a + rng.uniform(-6, 6))
        ca, sa = math.cos(a), math.sin(a)
        L = rng.uniform(7.5, 10.0) if k < 6 else 6.0
        run = rng.uniform(6.0, 16.0) if k < 6 else 4.0
        pts = []
        for i in range(9):
            t = i / 8
            r = 2.8 + (L + run) * t
            px, py = fx + ca * r + 0.8 * math.sin(t * 5 + k) * -sa, fy + sa * r + 0.8 * math.sin(t * 5 + k) * ca
            knuckle = 1.6 * g(t - 0.32, 0.18)
            pz = height(px, py) + (4.0 - 3.4 * smooth(t / 0.45)) + knuckle - 1.3 * smooth((t - 0.6) / 0.4)
            pts.append((px, py, pz))
        P = resample(pts, 0.8)
        rad = [2.1 * (1.0 - 0.8 * (i / (len(P) - 1)) ** 0.8) + 0.25 for i in range(len(P))]
        tube(b, 'barkR', [tuple(p) for p in P], rad, n=10, tip=True)


def surface_roots(b, rng):
    for k in range(9):
        a = math.radians(-90 + 360.0 * k / 9 + rng.uniform(-12, 12))
        sx = math.copysign(LEG[0][0], math.cos(a)) * 0.8
        pts = []
        for i in range(10):
            t = i / 9
            r = 7.0 + 22.0 * t
            px, py = sx + math.cos(a) * r, 0.6 + math.sin(a) * r + 2.0 * math.sin(t * 4 + k)
            if hex_dist(px, py) < 3.0:
                break
            pts.append((px, py, max(height(px, py), 0.0) + 0.5 - 1.6 * t))
        if len(pts) > 3:
            P = resample(pts, 1.0)
            tube(b, 'barkR', [tuple(p) for p in P], [1.3 * (1 - 0.7 * i / len(P)) + 0.2 for i in range(len(P))],
                 n=8, tip=True)


def build(b, eye=False):
    """The static part: the forest floor, the root mound, the feet with seven toes each, roots, ferns, stones."""
    ground_palette()
    b.normal_fn = normals
    b.tiny_px = 0
    b.ao_distance = 5.0
    b.relief = dict(mats=['barkR', 'rock'], levels=2, scale=0.8, stretch=3.0, strength=0.4, emboss=0.8)
    rng = random.Random(2002)
    blib.SKIRT_MAT[0] = 'soil'
    X0, X1, Y0, Y1 = -HEX, HEX, -HEX / 0.866, HEX / 0.866
    blib.terrain(b, height, X0, X1, Y0, Y1, 96, 110, lambda x, y, z, s: 'soil',
                 keep=lambda x, y: hex_dist(x, y) > 0.3 and height(x, y) > -0.05, smooth=True, skirt=-1.0)
    for side in (-1, 1):
        foot_and_roots(b, rng, side)
    surface_roots(b, rng)
    for (x, y, r) in ((-24.0, -9.0, 2.6), (22.0, 14.0, 3.0), (-17.0, 20.0, 2.2), (25.0, -12.0, 1.8),
                      (6.0, 25.0, 2.0), (-27.0, 5.0, 1.6)):
        blob(b, 'rock', x, y, max(height(x, y), 0.0) - r * 0.35, r, n=9, rings=5, squash=0.7, jitter=0.25)
    # ferns and tufts over the floor (not on the feet)
    spots = []
    while len(spots) < 150:
        x, y = rng.uniform(-HEX, HEX), rng.uniform(-HEX / 0.866, HEX / 0.866)
        if hex_dist(x, y) < 4.8 or min(math.hypot(x - s * LEG[0][0], y - LEG[0][1]) for s in (-1, 1)) < 9.0:
            continue
        spots.append((x, y))
    for i, (x, y) in enumerate(spots):
        z = max(height(x, y), 0.0)
        if i % 3 != 2:                                  # a fern: three cards turned about the camera's direction
            s = rng.uniform(4.0, 7.0)
            for yaw in (-48.0, 0.0, 48.0):
                yy = math.radians(yaw + rng.uniform(-12, 12))
                f = Vector((math.sin(yy) * 0.9, -math.cos(yy) * 0.9, 0.42))
                card(b, 'fernS', (x, y, z + s * 0.42), tuple(f), s, s * 0.9, roll=rng.uniform(-8, 8))
        else:
            s = rng.uniform(2.6, 4.2)
            m = 'grassS0' if rng.random() < 0.5 else 'grassS1'
            for yaw in (-35.0, 35.0):
                yy = math.radians(yaw)
                card(b, m, (x, y, z + s * 0.45), (math.sin(yy) * 0.9, -math.cos(yy) * 0.9, 0.35), s * 1.2, s)


# --------------------------------------------------------------------------- the body (skinned, mesh 1)
TORSO = [(35.0, 11.4, 8.8, 2.0), (40.0, 11.2, 8.6, 2.2), (46.0, 12.2, 9.3, 1.8), (53.0, 14.0, 10.2, 1.0),
         (59.0, 15.6, 10.4, 0.2), (63.0, 15.8, 9.6, -0.3), (66.5, 12.8, 8.2, -1.0), (69.0, 8.6, 6.6, -1.8)]


def torso(b, rng):
    """The trunk: hunched (the shoulders and the neck forward of the hips), a hump of the back, deep vertical ridges
    and furrows of bark (periodic noise round the body: no seam), thick sinews converging on the shoulders."""
    rows = []
    nz, nu = 56, 76
    for i in range(nz):
        z = 35.0 + (69.0 - 35.0) * i / (nz - 1)
        rx, ry, yc = keyed(TORSO, z)
        row = []
        for j in range(nu):
            th = 2 * math.pi * j / nu
            c_, s_ = math.cos(th), math.sin(th)
            d = 0.9 * fbm(c_ * 1.6, s_ * 1.6 + z * 0.07, 3, 11) + \
                1.5 * (ridged(c_ * 3.2 + 5.0, s_ * 3.2 + z * 0.03, 4, 14) - 0.45) + \
                0.3 * fbm(c_ * 9.0, s_ * 9.0 + z * 0.4, 2, 13)
            d += 1.8 * max(0.0, s_) ** 2 * g(z - 58.0, 5.0)                     # the hump of the back
            row.append((c_ * (rx + d), yc + s_ * (ry + d * 0.85), z))
        rows.append(row)
    ring_grid(b, 'bark', rows, cap_top=(0.0, -1.8, 69.2), cap_bottom=(0.0, 2.0, 35.0))
    for k in range(9):                                       # sinews, converging on the shoulders and the neck
        th0 = 2 * math.pi * k / 9 + rng.uniform(-0.2, 0.2)
        pts = []
        for i in range(9):
            t = i / 8
            z = 36.5 + 30.0 * t
            rx, ry, yc = keyed(TORSO, z)
            th = th0 + 0.4 * math.sin(t * 3.0 + k) * (1 if k % 2 else -1)
            pts.append((math.cos(th) * (rx + 0.9), yc + math.sin(th) * (ry + 0.8), z))
        P = resample(pts, 1.1)
        rr = [rng.uniform(1.1, 1.6) * (0.45 + 0.55 * math.sin(math.pi * i / (len(P) - 1))) + 0.15
              for i in range(len(P))]
        tube(b, 'bark', [tuple(p) for p in P], rr, n=7, tip=True)
    for side in (-1, 1):                                    # the knotted shoulders the hobbits sit on
        blob(b, 'bark', side * 13.2, 0.0, 60.0, 5.0, n=14, rings=8, squash=0.76, jitter=0.14)
        blob(b, 'bark', side * 15.6, 2.0, 58.2, 3.6, n=10, rings=6, squash=0.9, jitter=0.22)


def head_shape(th, z):
    """A point of the head: an ellipse per height, the face on its front: the heavy overhanging brow (rising
    outwards, stern), deep sockets, the long knotted nose, furrowed bark; the top rough like broken wood."""
    keys = [(60.5, 9.0, 7.8), (64.0, 8.0, 7.5), (67.0, 7.4, 7.3), (72.0, 7.1, 7.4), (78.0, 6.8, 7.2), (81.5, 6.2, 6.7),
            (84.5, 5.0, 5.6), (87.0, 3.0, 3.6), (89.0, 1.2, 1.5)]
    rx, ry = keyed(keys, z)
    c_, s_ = math.cos(th), math.sin(th)
    u = rx * c_
    front = max(0.0, -s_) ** 1.3
    au = abs(u)
    d = 0.0
    if front > 0:
        zb = 79.0 + 0.18 * au
        d += 2.0 * g(z - zb, 1.3) * g(max(0.0, au - 4.8), 1.1) * (1 + 0.4 * fbm(u * 0.8, 3.0, 2, 5))   # brow
        d -= 0.8 * g(u, 0.9) * g(z - 78.4, 1.3)                                                         # frown
        d -= 2.6 * g(au - 2.55, 1.25) * g(z - 76.3, 1.05)                                               # sockets
        f = min(1.0, max(0.0, (78.0 - z) / 7.5))
        d += (1.0 + 2.6 * f) * g(u, 0.7 + 0.8 * f) * smooth((z - 70.2) / 0.8) * smooth((78.6 - z) / 0.9)  # nose
        d += 1.9 * g(u, 1.45) * g(z - 71.0, 1.2) + 0.6 * g(u - 0.3, 0.6) * g(z - 74.5, 0.7)          # its knots
        d -= 0.6 * g(au - 1.55, 0.45) * g(z - 70.4, 0.55)                                              # nostrils
        d += 0.8 * g(au - 4.4, 2.0) * g(z - 73.4, 2.0)                                                 # cheeks
        d -= 0.9 * g(au - (2.8 + (73.0 - z) * 0.35), 0.45) * smooth((73.5 - z) / 0.6) * smooth((z - 67.5) / 0.8)
        env = smooth((z - 80.0) / 0.8) * smooth((86.0 - z) / 1.5)
        d += 0.3 * math.sin((z - 80.0) * 2.6 + 4.0 * fbm(u * 0.3, z * 0.15, 2, 6)) * env * max(0.0, 0.3 + 1.4 * fbm(u * 0.5 + 3, z * 0.3, 2, 7))
        d += 0.3 * math.sin((z - 74.5) * 4.0 + u) * g(au - 4.0, 1.4) * g(z - 74.2, 1.2)               # under the eyes
        d -= 1.2 * g(z - 68.6, 0.8) * g(u, 3.2)                                                        # mouth
        d += 0.55 * g(z - 67.9, 0.35) * g(u, 1.7) + 0.3 * g(z - 69.3, 0.3) * g(u, 1.9)                 # lips
        d += 0.9 * g(z - 66.5, 1.5) * g(u, 4.2)                                                        # chin
        d -= 0.45 * g(au - 0.75, 0.22) * g(z - 78.4, 1.0)                                              # frown lines
        dx, dz = au - 3.85, z - 76.3                                                                   # crow's feet
        if dx > -0.6:
            ang = math.atan2(dz, dx + 0.6)
            d -= 0.22 * (0.5 + 0.5 * math.cos(ang * 9.0)) * g(math.hypot(dx + 0.6, dz) - 1.4, 0.8)
        d -= 0.35 * g(au - 2.55, 1.5) * g(z - 74.6, 0.35)                                             # eye bags
        d += 0.25 * g(au - 2.55, 1.5) * g(z - 74.1, 0.35)
        for (ku, kz, kr) in ((-4.7, 81.6, 0.7), (5.3, 71.8, 0.6), (3.6, 82.6, 0.45)):                  # knots
            r_ = math.hypot(u - ku, z - kz)
            d += 0.7 * g(r_, kr) - 0.35 * g(r_ - kr * 1.5, 0.22)
        d += 0.35 * (ridged(u * 0.9 + 2.0, z * 0.33, 3, 31) - 0.5) * (1.0 - g(u, 1.2))               # bark plates
        d *= front
    d += 0.55 * fbm(c_ * 3.0, s_ * 3.0 + z * 0.12, 3, 21) + 0.35 * fbm(c_ * 10.0, s_ * 10.0 + z * 0.45, 2, 22)
    d += 0.15 * fbm(c_ * 30.0, s_ * 30.0 + z * 0.9, 2, 24)                                          # fibrous grain
    d += 0.9 * fbm(c_ * 4.0, s_ * 4.0 + z * 0.5, 3, 23) * smooth((z - 84.0) / 3.0)                  # broken top
    nx, ny = c_ / rx, s_ / ry
    nl = math.hypot(nx, ny)
    return (rx * c_ + d * nx / nl, HEAD_YC + ry * s_ + d * ny / nl, z)


def front_y(u, z):
    """The face's surface y at lateral u (front half) and height z."""
    best = None
    for i in range(121):
        th = -math.pi + math.pi * i / 120
        p = head_shape(th, z)
        if best is None or abs(p[0] - u) < abs(best[0] - u):
            best = p
    return best[1]


def ellipsoid(b, mat, c, radii, n=10, rings=6, R=None):
    """An ellipsoid at c with radii (x, y, z), turned by the rotation matrix R (4x4) if given."""
    M = Matrix.Translation(c) @ (R if R is not None else Matrix.Identity(4)) @ \
        Matrix.Diagonal((radii[0], radii[1], radii[2], 1.0)) @ Matrix.Translation((0.0, 0.0, -1.0))
    blob(b, mat, 0.0, 0.0, 0.0, 1.0, n=n, rings=rings, squash=1.0, jitter=0.0, M=M)


def head(b, rng):
    """The head at high resolution (its own mesh and texture): the face with every wrinkle in the geometry; the eyes
    (amber-brown ball, brown iris shot with green, a wet black pupil and a glint) under hooded bark lids; twig
    brows."""
    rows = []
    nz, nu = 112, 124
    for i in range(nz):
        z = HEAD_Z[0] + (HEAD_Z[1] - 0.3 - HEAD_Z[0]) * i / (nz - 1)
        rows.append([head_shape(2 * math.pi * j / nu, z) for j in range(nu)])
    ring_grid(b, 'face', rows, cap_top=(0.0, HEAD_YC, HEAD_Z[1]))
    for side in (-1, 1):
        ex, ez = side * 2.55, 76.3
        ey = front_y(ex, ez) + 0.8
        ellipsoid(b, 'eye', (ex, ey, ez), (0.92, 0.92, 0.88), n=16, rings=10)
        ellipsoid(b, 'iris', (ex + side * 0.04, ey - 0.86, ez - 0.05), (0.5, 0.12, 0.5), n=14, rings=6)
        ellipsoid(b, 'pupil', (ex + side * 0.04, ey - 0.95, ez - 0.05), (0.22, 0.07, 0.24), n=10, rings=5)
        ellipsoid(b, 'glint', (ex + side * 0.04 - 0.18, ey - 0.98, ez + 0.2), (0.07, 0.03, 0.07), n=6, rings=3)
        for (r, zo, rad, a0, a1) in ((1.15, 0.08, 0.42, 190.0, 350.0), (1.05, -0.05, 0.28, 15.0, 165.0)):
            pts = [(ex + side * r * math.cos(math.radians(a)), 0.0, ez + zo + r * math.sin(math.radians(a)) * -1)
                   for a in [a0 + (a1 - a0) * i / 12 for i in range(13)]]
            pts = [(x, front_y(x, z) + 0.2, z) for x, y, z in pts]
            P = resample(pts, 0.18)
            tube(b, 'face', [tuple(p) for p in P],
                 [rad * (0.45 + 0.55 * math.sin(math.pi * i / (len(P) - 1))) + 0.05 for i in range(len(P))], n=8)
    for side in (-1, 1):                                       # bristling twig brows over the eyes
        for k in range(14):
            u = side * (0.7 + 0.38 * k)
            zb = 79.2 + 0.18 * abs(u) + rng.uniform(-0.25, 0.35)
            p0 = Vector((u, front_y(u, zb) - 0.05, zb))
            d = Vector((side * 0.55, -0.75, 0.6 + 0.07 * k + rng.uniform(-0.25, 0.3))).normalized()
            L = rng.uniform(1.4, 3.2)
            P = resample([tuple(p0), tuple(p0 + d * L * 0.5 + Vector((side * 0.2, -0.2, 0.15))), tuple(p0 + d * L)],
                         0.25)
            tube(b, 'twig', [tuple(p) for p in P],
                 [0.13 * (1 - 0.75 * i / (len(P) - 1)) + 0.03 for i in range(len(P))], n=5)
            if k % 3 == 1:                                     # a forked sprig
                q = P[len(P) // 2]
                e = q + (d + Vector((0, 0, 0.8))).normalized() * L * 0.4
                tube(b, 'twig', [tuple(q), tuple((q + e) / 2), tuple(e)], [0.09, 0.07, 0.04], n=4)


def hand(b, rng, side):
    w = Vector((side * ARM[-1][0], ARM[-1][1], ARM[-1][2]))
    palm = w + Vector((0.0, -0.6, -2.4))
    blob(b, 'barkA', palm.x, palm.y, palm.z - 2.3, 2.6, n=10, rings=6, squash=0.95, jitter=0.15)
    for f in range(4):                                       # four long twig fingers, knuckled, curling in
        o = (f - 1.5) * 1.05
        p0 = palm + Vector((side * 0.35 * o, -0.4 + 0.5 * abs(o), -2.2))
        spread = Vector((side * 0.22 * o, -0.15, -1.0)).normalized()
        curl = Vector((-side * 0.35, -0.55, -0.4)).normalized()
        L = (4.2, 3.4, 2.6) if f in (1, 2) else (3.7, 3.0, 2.2)
        p1 = p0 + spread * L[0]
        p2 = p1 + (spread * 0.6 + curl * 0.4).normalized() * L[1]
        p3 = p2 + (spread * 0.2 + curl * 0.8).normalized() * L[2]
        P = resample([tuple(p0), tuple(p1), tuple(p2), tuple(p3)], 0.45)
        rr = []
        for i in range(len(P)):
            t = i / (len(P) - 1)
            knuck = 0.18 * (g(t - 0.36, 0.06) + g(t - 0.7, 0.06))
            rr.append(0.62 * (1 - 0.55 * t) + knuck)
        tube(b, 'barkA', [tuple(p) for p in P], rr, n=7, tip=True)
    t0 = palm + Vector((-side * 1.7, -1.2, -0.8))            # the thumb, towards the body and forward
    t1 = t0 + Vector((-side * 0.8, -1.8, -1.6))
    t2 = t1 + Vector((-side * 0.2, -0.8, -1.6))
    P = resample([tuple(t0), tuple(t1), tuple(t2)], 0.45)
    tube(b, 'barkA', [tuple(p) for p in P], [0.7 * (1 - 0.5 * i / (len(P) - 1)) for i in range(len(P))], n=7)


def branch_tree(b, rng, mat, p0, d0, L, r0, depth, tips, up=0.5):
    """A branch with forks: a curving tapering tube, two or three side branches, recursing; tips collected."""
    d = Vector(d0).normalized()
    p = Vector(p0)
    bend = Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.3, 0.4), up)).normalized()
    e = p + (d * 0.7 + bend * 0.3).normalized() * L
    m1 = p + (e - p) * 0.33 + Vector((rng.uniform(-0.12, 0.12) * L, rng.uniform(-0.1, 0.12) * L, 0.05 * L))
    m2 = p + (e - p) * 0.66 + Vector((rng.uniform(-0.12, 0.12) * L, rng.uniform(-0.1, 0.12) * L, 0.08 * L))
    P = resample([tuple(p), tuple(m1), tuple(m2), tuple(e)], max(0.45, L / 12))
    r1 = r0 * 0.35
    tube(b, mat, [tuple(q) for q in P], [r0 + (r1 - r0) * i / (len(P) - 1) for i in range(len(P))],
         n=max(5, min(9, int(r0 * 6))), tip=True)
    tips.append((e, d))
    if depth > 0:
        for j, t in enumerate((0.45, 0.75, 0.95)[:2 + (depth > 1)]):
            q = P[int(t * (len(P) - 1))]
            a = rng.uniform(0.5, 1.0) * (1 if j % 2 else -1)
            dd = (P[-1] - P[0]).normalized()
            side = dd.cross(Vector((0, 0, 1)))
            if side.length < 1e-3:
                side = Vector((1, 0, 0))
            nd = (dd + side.normalized() * a + Vector((0, 0, 0.35))).normalized()
            branch_tree(b, rng, mat, q, nd, L * rng.uniform(0.45, 0.62), r0 * 0.45, depth - 1, tips, up)


def crown(b, rng, tips):
    """Ram-like curling branches from the temples (the reference), and the crown of branches on the head; the
    branches rising behind his shoulders."""
    for side in (-1, 1):
        pts = [(side * 4.4, HEAD_YC + 0.4, 82.8), (side * 7.6, 0.3, 88.0), (side * 11.8, 1.8, 92.6),
               (side * 16.0, 3.4, 93.4), (side * 18.6, 2.4, 90.0), (side * 18.2, 0.6, 87.2)]
        gnarl(b, 'barkC', pts, [2.4, 2.0, 1.6, 1.2, 0.85, 0.5], rng, cords=4, twist=0.9, core_n=10, cord_n=5,
              step=0.6)
        tips.append((Vector(pts[3]), Vector((side, 0.2, 0.4))))
        branch_tree(b, rng, 'barkC', pts[2], (side * 0.4, 0.3, 1.0), 7.0, 0.55, 1, tips)
    for k in range(7):                                        # the crown of branches
        a = math.radians(-60 + 300.0 * k / 7 + rng.uniform(-10, 10))
        p0 = (2.4 * math.cos(a), HEAD_YC + 2.6 * math.sin(a) + 0.8, 87.0)
        d0 = (0.5 * math.cos(a), 0.45 * math.sin(a) + 0.2, 1.0)
        branch_tree(b, rng, 'barkC', p0, d0, rng.uniform(8.5, 12.0), rng.uniform(0.7, 0.95), 2, tips, up=0.7)
    for side in (-1, 1):                                      # behind the shoulders (the hobbits hold on to them)
        p0 = (side * 15.6, 4.6, 62.5)
        branch_tree(b, rng, 'barkC', p0, (side * 0.3, 0.35, 1.0), 15.0, 1.4, 2, tips, up=0.8)
        p0 = (side * 6.5, 7.0, 60.0)
        branch_tree(b, rng, 'barkC', p0, (side * 0.45, 0.6, 1.0), 17.0, 1.6, 2, tips, up=0.8)


def build_body(b):
    palette()
    b.normal_fn = normals
    b.tiny_px = 0
    b.ao_distance = 6.0
    b.relief = dict(mats=['bark', 'barkA'], levels=3, scale=0.9, stretch=4.0, strength=0.45, emboss=0.9)
    rng = random.Random(1954)
    for side in (-1, 1):
        gnarl(b, 'bark', [(side * x, y, z) for x, y, z in LEG], LEG_R, rng, cords=6, twist=0.45, core_n=14,
              cord_n=7, step=0.9)
        kx, ky, kz = LEG[2]
        blob(b, 'bark', side * kx, ky - 1.9, kz - 2.6, 3.1, n=10, rings=6, squash=0.9, jitter=0.25)   # the knee
        gnarl(b, 'barkA', [(side * x, y, z) for x, y, z in ARM], ARM_R, rng, cords=5, twist=0.55, core_n=12,
              cord_n=6, step=0.9)
        ex, ey, ez = ARM[2]
        blob(b, 'barkA', side * ex, ey + 0.6, ez - 2.6, 2.7, n=10, rings=6, squash=0.95, jitter=0.25)  # the elbow
        hand(b, rng, side)
    torso(b, rng)


def build_head(b):
    """Mesh 2: the head and face at high resolution, the eyes, lids and twig brows."""
    head_palette()
    b.normal_fn = normals
    b.tiny_px = 0
    b.ao_distance = 3.0
    b.relief = dict(mats=['face'], levels=2, scale=0.35, stretch=2.5, strength=0.18, emboss=0.9)
    head(b, random.Random(1957))


def build_crown(b):
    """Mesh 3: the horns, the crown of branches, the branches behind the shoulders and their leaves."""
    crown_palette()
    b.normal_fn = normals
    b.tiny_px = 0
    b.ao_distance = 4.0
    b.relief = dict(mats=['barkC'], levels=3, scale=0.5, stretch=3.0, strength=0.25, emboss=0.8)
    rng = random.Random(1956)
    tips = []
    crown(b, rng, tips)
    leaves(b, rng, tips)


# --------------------------------------------------------------------------- the beard (mesh 4), the hobbits (mesh 5)
def beard(b, rng):
    """'A sweeping grey beard, bushy, almost twiggy at the roots, thin and mossy at the ends' (its own mesh):
    clumps of lichen along the jaw; a thicket of twigs (some forked) from the jaw and cheeks; long thin twigs
    running down through the beard; then two kinds of lichen (cut-out cards) in five shells round the jaw, every card
    hanging towards the beard's point below the chest, turned a little this way and that for volume; tufts at the
    jaw; the moustache."""
    tip = Vector((0.0, -13.8, 39.0))

    def jaw(s_):
        return 7.2 * math.sin(s_ * math.pi / 2), 67.4 + 5.2 * s_ * s_
    for i in range(22):                                        # lichen clumps on the jaw
        u, z = jaw(rng.uniform(-1.0, 1.0))
        z += rng.uniform(-0.8, 1.2)
        r = rng.uniform(0.3, 0.6)
        blob(b, 'lichen', u, front_y(u, z) - r * 0.3, z - r * 0.6, r, n=8, rings=5, squash=0.75, jitter=0.3)
    for i in range(150):                                       # the twiggy roots
        u, z = jaw(rng.uniform(-1.0, 1.0))
        z += rng.uniform(-1.5, 1.5)
        p0 = Vector((u, front_y(u, z) + 0.3, z))
        L = rng.uniform(3.0, 10.0)
        d = ((tip - p0).normalized() + Vector((rng.uniform(-0.3, 0.3), -0.35, 0.0))).normalized()
        p1 = p0 + d * L * 0.35 + Vector((rng.uniform(-0.5, 0.5), -0.5, 0))
        p2 = p0 + d * L * 0.7 + Vector((rng.uniform(-0.6, 0.6), -0.2, 0))
        p3 = p0 + d * L + Vector((rng.uniform(-0.8, 0.8), 0.2, rng.uniform(-0.3, 0.3)))
        P = resample([tuple(p0), tuple(p1), tuple(p2), tuple(p3)], 0.7)
        r0 = rng.uniform(0.14, 0.32)
        tube(b, 'twig', [tuple(p) for p in P], [r0 * (1 - 0.75 * k / (len(P) - 1)) + 0.04 for k in range(len(P))],
             n=5, tip=True)
        if rng.random() < 0.35:                                 # a fork
            q = P[len(P) // 2]
            e = q + (d + Vector((rng.uniform(-0.8, 0.8), -0.3, 0.2))).normalized() * L * 0.35
            tube(b, 'twig', [tuple(q), tuple((q + e) / 2), tuple(e)], [r0 * 0.5, r0 * 0.35, 0.04], n=4)
    for i in range(22):                                        # long thin twigs down through the beard
        u, z = jaw(rng.uniform(-0.8, 0.8))
        p0 = Vector((u, front_y(u, z) - 1.0 - rng.uniform(0, 2.0), z - 1.0))
        e = tip + Vector((rng.uniform(-3, 3), rng.uniform(-0.5, 1.5), rng.uniform(0, 6)))
        mid = (p0 + e) / 2 + Vector((rng.uniform(-1.2, 1.2), -1.2, 0))
        P = resample([tuple(p0), tuple(mid), tuple(e)], 1.0)
        tube(b, 'twig', [tuple(p) for p in P], [0.17 * (1 - 0.7 * k / (len(P) - 1)) + 0.03 for k in range(len(P))],
             n=4, tip=True)
    cam = Vector((0.0, -1.0, 0.3))
    for shell in range(5):                                     # the lichen, back shell first
        n = 17 - 2 * shell
        for i in range(n):
            s_ = -1.0 + 2.0 * (i + rng.uniform(0.2, 0.8)) / n
            u, za = jaw(s_)
            u *= 1.0 - 0.07 * shell
            za += -shell * 0.8 + rng.uniform(-0.6, 0.6)
            A = Vector((u, front_y(u, za) - 0.2 - 0.7 * shell, za))
            T_ = tip + Vector((rng.uniform(-2.5, 2.5), 0.0, rng.uniform(-2.0, 3.0) + shell * 2.2))
            dvec = T_ - A
            L = dvec.length * rng.uniform(0.7, 1.05)
            w = rng.uniform(2.8, 4.2) * (1.0 - 0.06 * shell)
            yaw = math.radians(rng.uniform(-25, 25) + u * 2.5)
            f = Vector((cam.x * math.cos(yaw) - cam.y * math.sin(yaw), cam.x * math.sin(yaw) + cam.y * math.cos(yaw),
                        cam.z))
            m = 'beardS' if (i + shell) % 3 else 'beardS2'
            card(b, m, tuple(A), tuple(f), w, L, up=tuple(-dvec.normalized()), anchor_top=True)
    for k in range(30):                                        # short bushy tufts at the jaw
        u, za = jaw(rng.uniform(-1.0, 1.0))
        za += rng.uniform(0.2, 1.4)
        A = Vector((u, front_y(u, za) - 0.6, za))
        card(b, 'beardS2' if k % 2 else 'beardS', tuple(A), (u * 0.08, -1.0, 0.3), rng.uniform(2.6, 3.8),
             rng.uniform(4.0, 7.0), up=(-u * 0.05 + rng.uniform(-0.2, 0.2), 0.25, 1.0), anchor_top=True)
    for side in (-1, 1):                                       # the moustache, from under the nose
        for k in range(5):
            u = side * (0.7 + 0.75 * k)
            A = Vector((u, front_y(u, 70.6) - 0.8 - 0.1 * k, 70.9 - 0.3 * k))
            card(b, 'beardS', tuple(A), (side * 0.25, -1.0, 0.35), 2.6, 8.5 - 0.7 * k,
                 up=(-side * (0.3 + 0.1 * k), 0.15, 1.0), anchor_top=True)


def leaves(b, rng, tips):
    """Sprigs of leaves round the branch tips (cut-out clusters turned to the game's camera)."""
    spots = []
    for (p, d) in tips:
        for _ in range(4):
            spots.append(p + Vector((rng.gauss(0, 1.4), rng.gauss(0, 1.1), rng.gauss(0.3, 1.0))))
    for _ in range(30):                                        # sprigs on the top of the head
        a = rng.uniform(0, 2 * math.pi)
        spots.append(Vector((3.6 * math.cos(a), HEAD_YC + 3.8 * math.sin(a) + 0.8, rng.uniform(86.5, 90.5))))
    for p in spots:
        rel = (p.z - 80.0) / 22.0
        m = 'leafS1' if rng.random() < 0.35 + 0.3 * rel else 'leafS0'
        yaw = math.radians(rng.uniform(-40, 40))
        f = Vector((CAM.x * math.cos(yaw) - CAM.y * math.sin(yaw), CAM.x * math.sin(yaw) + CAM.y * math.cos(yaw),
                    CAM.z))
        s = rng.uniform(2.6, 4.2)
        card(b, m, tuple(p), tuple(f), s, s, roll=rng.uniform(-30, 30))


def hanging_moss(b, rng):
    """Moss hanging from the forearms and the shoulders, like the reference's drapery."""
    for side in (-1, 1):
        for k in range(10):
            f = rng.uniform(0.15, 0.95)
            i = f * (len(ARM) - 1)
            a, c = ARM[int(i)], ARM[min(int(i) + 1, len(ARM) - 1)]
            t = i - int(i)
            p = Vector([a[j] + (c[j] - a[j]) * t for j in range(3)])
            p.x *= side
            p += Vector((side * rng.uniform(-0.8, 1.4), -lerp_r(ARM_R, f) * 0.9, -lerp_r(ARM_R, f) * 0.3))
            card(b, 'mossS', tuple(p), (side * 0.3, -1.0, 0.3), rng.uniform(2.5, 4.0), rng.uniform(5.0, 9.0),
                 anchor_top=True, roll=rng.uniform(-8, 8))


# ---- the hobbits: built in hobbit units (standing height 1), origin = the seat, facing -Y; their own mesh
def hob_tube(b, mat, pts, r0, r1, n=8, step=0.012):
    P = resample(pts, step)
    tube(b, mat, [tuple(p) for p in P], [r0 + (r1 - r0) * i / (len(P) - 1) for i in range(len(P))], n=n, tip=False)


def grid_mats(b, rows, matfn):
    """A closed surface from rings of points (like ring_grid); matfn(i, j) -> the material of quad (i, j)."""
    n = len(rows[0])
    verts = [tuple(p) for row in rows for p in row]
    groups = {}
    for i in range(len(rows) - 1):
        for j in range(n):
            a, b_ = i * n + j, i * n + (j + 1) % n
            groups.setdefault(matfn(i, j), []).append((a, b_, b_ + n, a + n))
    for m, faces in groups.items():
        b.add(verts, faces, m, smooth=True)


def thick_sheet(b, mat, rows, t):
    """An open sheet of cloth from rows of points (each row an open strip running counter-clockwise seen from above,
    rows from top to bottom or bottom to top like ring_grid), with thickness t: outer face, inner face, edges."""
    n = len(rows[0])
    outer = [[Vector(p) for p in row] for row in rows]
    m = len(rows)
    inner = []
    for i, row in enumerate(outer):
        nr = []
        for j, p in enumerate(row):
            du = row[min(j + 1, n - 1)] - row[max(j - 1, 0)]
            dv = outer[min(i + 1, m - 1)][j] - outer[max(i - 1, 0)][j]
            nn = du.cross(dv)
            nn = nn.normalized() if nn.length > 1e-12 else Vector((0, 0, 1))
            nr.append(p - nn * t)
        inner.append(nr)
    verts = [tuple(p) for row in outer for p in row] + [tuple(p) for row in inner for p in row]
    o = m * n
    faces = []
    for i in range(m - 1):
        for j in range(n - 1):
            a, b_ = i * n + j, i * n + j + 1
            faces.append((a, b_, b_ + n, a + n))
            faces.append((o + a, o + a + n, o + b_ + n, o + b_))
    for j in range(n - 1):                                     # first and last rows' edges
        faces.append((j + 1, j, o + j, o + j + 1))
        a, b_ = (m - 1) * n + j, (m - 1) * n + j + 1
        faces.append((a, b_, o + b_, o + a))
    for i in range(m - 1):                                     # the two side edges
        a, c = i * n, (i + 1) * n
        faces.append((a, c, o + c, o + a))
        a, c = i * n + n - 1, (i + 1) * n + n - 1
        faces.append((a, o + a, o + c, c))
    b.add(verts, faces, mat, smooth=True)


HOB_HEAD = [(0.385, 0.02), (0.395, 0.042), (0.41, 0.058), (0.43, 0.067), (0.455, 0.074), (0.485, 0.079),
            (0.515, 0.078), (0.545, 0.07), (0.568, 0.052), (0.582, 0.024)]
HOB_HC = (0.0, -0.012)


def hob_head_pt(th, z):
    r, = keyed(HOB_HEAD, z)
    c_, s_ = math.cos(th), math.sin(th)
    u = r * c_
    au = abs(u)
    front = max(0.0, -s_) ** 1.5
    d = 0.0
    if front > 0:
        d -= 0.008 * g(au - 0.028, 0.012) * g(z - 0.498, 0.009)                  # sockets
        d += 0.005 * g(z - 0.513, 0.006) * g(max(0.0, au - 0.03), 0.02)           # brow
        d += 0.017 * g(u, 0.011) * g(z - 0.472, 0.014) + 0.006 * g(u, 0.013) * g(z - 0.462, 0.007)   # nose
        d += 0.008 * g(au - 0.038, 0.014) * g(z - 0.457, 0.012)                  # cheeks
        d -= 0.004 * g(z - 0.441, 0.0035) * g(u, 0.018)                         # mouth
        d += 0.0025 * g(z - 0.435, 0.004) * g(u, 0.014)                         # lower lip
        d += 0.006 * g(z - 0.414, 0.011) * g(u, 0.02)                           # chin
        d *= front
    return (u + d * c_, HOB_HC[1] + r * 1.08 * s_ + d * s_, z)


def hob_head(b, rng, hair):
    """The head: a face shaped in the geometry (sockets, brow, nose, cheeks, lips, chin), eyes, brows, pointed ears,
    and a cap of hair with spiral curls over the top and the back."""
    z0, z1 = HOB_HEAD[0][0], HOB_HEAD[-1][0]
    rows = [[hob_head_pt(2 * math.pi * j / 36, z0 + (z1 - z0) * i / 29) for j in range(36)] for i in range(30)]

    def mat(i, j):
        z = z0 + (z1 - z0) * (i + 0.5) / 29
        th = 2 * math.pi * (j + 0.5) / 36
        return 'h_lip' if abs(math.cos(th)) < 0.3 and math.sin(th) < 0 and 0.437 < z < 0.445 else 'h_skin'
    grid_mats(b, rows, mat)
    b.add([tuple(rows[-1][j]) for j in range(36)] + [(0.0, HOB_HC[1], z1 + 0.003)],
          [(j, (j + 1) % 36, 36) for j in range(36)], 'h_skin', smooth=True)
    for s in (-1, 1):                                          # eyes, brows, ears
        ex, ez = s * 0.028, 0.498
        ey = hob_head_pt(-math.pi / 2 + s * 0.36, ez)[1] + 0.004
        ellipsoid(b, 'h_eyew', (ex, ey, ez), (0.0105, 0.008, 0.008), n=8, rings=5)
        ellipsoid(b, 'h_iris', (ex, ey - 0.0072, ez), (0.0058, 0.002, 0.0058), n=8, rings=4)
        tube(b, hair, [(s * 0.012, -0.081, 0.513), (s * 0.03, -0.083, 0.517), (s * 0.047, -0.077, 0.512)],
             [0.004, 0.005, 0.003], n=5)
        hob_tube(b, 'h_skin', [(s * 0.074, 0.0, 0.475), (s * 0.088, 0.008, 0.5), (s * 0.097, 0.016, 0.527)], 0.017,
                 0.003, n=8, step=0.006)
    cap = []                                                   # the cap of hair: hairline high over the brow
    for i in range(14):
        z = 0.47 + (0.6 - 0.47) * i / 13
        row = []
        for j in range(30):
            th = 2 * math.pi * j / 30
            hl = 0.535 + 0.03 * max(0.0, -math.sin(th)) - 0.07 * max(0.0, math.sin(th))
            zz = max(z, hl) if z < 0.585 else z
            x, y, _ = hob_head_pt(th, min(zz, z1 - 0.004))
            k = 1.0 + 0.16 * (0.5 + 0.5 * math.sin(th * 7 + z * 90))
            row.append((x * k, HOB_HC[1] + (y - HOB_HC[1]) * k, zz + 0.004))
        cap.append(row)
    ring_grid(b, hair, cap, cap_top=(0.0, HOB_HC[1], 0.598))
    for k in range(52):                                        # curls
        th = rng.uniform(0, 2 * math.pi)
        if math.sin(th) < -0.6:
            continue
        z = rng.uniform(0.47 if math.sin(th) > -0.2 else 0.53, 0.59)
        x, y, _ = hob_head_pt(th, min(z, z1 - 0.004))
        c = Vector((x * 1.14, HOB_HC[1] + (y - HOB_HC[1]) * 1.14, z + 0.004))
        nrm = (c - Vector((0.0, HOB_HC[1], 0.48))).normalized()
        ax = (nrm * 0.5 + Vector((0, 0, -0.5))).normalized()
        e1 = ax.orthogonal().normalized()
        e2 = ax.cross(e1)
        ph = rng.uniform(0, 6.3)
        pts = [tuple(c + ax * (0.016 * t) + 0.009 * (math.cos(ph + t * 8.5) * e1 + math.sin(ph + t * 8.5) * e2))
               for t in [i / 7 for i in range(8)]]
        tube(b, hair, pts, [0.0068 * (1 - 0.4 * i / 7) for i in range(8)], n=4)


def hob_hand(b, wrist, toward, size=0.03, grip=0.7):
    """A small hand: palm, four fingers curling by `grip`, a thumb."""
    W, T_ = Vector(wrist), Vector(toward)
    d = (T_ - W).normalized()
    side = d.cross(Vector((0, 0, 1)))
    side = side.normalized() if side.length > 1e-3 else Vector((1, 0, 0))
    up = side.cross(d)
    palm = W + d * size * 0.5
    ellipsoid(b, 'h_skin', tuple(palm), (size * 0.42, size * 0.42, size * 0.3), n=8, rings=5)
    for f in range(4):
        o = side * (f - 1.5) * size * 0.2
        p0 = palm + d * size * 0.35 + o
        p1 = p0 + d * size * 0.3 - up * size * 0.25 * grip
        p2 = p1 + (d * (1 - grip) - up * grip) * size * 0.28
        tube(b, 'h_skin', [tuple(p0), tuple(p1), tuple(p2)], [size * 0.09, size * 0.08, size * 0.065], n=5)
    t0 = palm + side * size * 0.36
    tube(b, 'h_skin', [tuple(t0), tuple(t0 + (d + up * 0.3) * size * 0.35)], [size * 0.1, size * 0.075], n=5)


def hobbit(b, rng, who, reach):
    """A hobbit sitting on Treebeard's shoulder (who = 'P' Pippin / 'M' Merry; reach = the side of the twig he
    holds). His Lorien cloak, grey-green, falls open from the leaf brooch at his throat over the shoulders and the
    back to the bark; under it the jacket, the waistcoat with brass buttons, the shirt collar; breeches to the knee,
    bare calves, big hobbit feet with their toes and curly hair on top; one hand round the twig growing out of the
    shoulder, the other on his knee; the face (eyes, brows, nose, cheeks, lips, pointed ears) and the curly head."""
    hair, coat, vest, breech = 'h_hair' + who, 'h_coat' + who, 'h_vest' + who, 'h_breech' + who
    for s in (-1, 1):                                          # legs
        hob_tube(b, breech, [(s * 0.058, 0.0, 0.066), (s * 0.066, -0.11, 0.07), (s * 0.07, -0.2, 0.06)], 0.056, 0.046,
                 n=9)
        ellipsoid(b, breech, (s * 0.07, -0.205, 0.058), (0.046, 0.05, 0.048), n=10, rings=6)
        hob_tube(b, breech, [(s * 0.07, -0.215, 0.035), (s * 0.072, -0.222, 0.012)], 0.047, 0.045, n=9, step=0.008)
        P = resample([(s * 0.07, -0.218, 0.02), (s * 0.075, -0.236, -0.05), (s * 0.078, -0.246, -0.12),
                      (s * 0.079, -0.248, -0.165)], 0.008)
        rr = [0.032 + 0.008 * math.sin(math.pi * min(1.0, i / (len(P) - 1) * 1.5)) - 0.01 * (i / (len(P) - 1)) ** 2
              for i in range(len(P))]
        tube(b, 'h_skin', [tuple(p) for p in P], rr, n=9, tip=False)
        fx = s * 0.08
        ellipsoid(b, 'h_skin', (fx, -0.255, -0.182), (0.03, 0.04, 0.022), n=10, rings=6)          # heel and sole
        ellipsoid(b, 'h_skin', (fx + s * 0.004, -0.298, -0.186), (0.036, 0.04, 0.019), n=10, rings=6)
        for k in range(5):                                     # toes, the big one inside
            tx = fx - s * 0.022 + s * 0.011 * k
            ellipsoid(b, 'h_skin', (tx, -0.336 + 0.003 * k, -0.19), ((0.011 if k == 0 else 0.0085), 0.011, 0.008),
                      n=6, rings=4)
        for k in range(6):                                     # curly hair on the tops of the feet
            c = Vector((fx + rng.uniform(-0.018, 0.018), rng.uniform(-0.31, -0.255), -0.172))
            ph = rng.uniform(0, 6.3)
            pts = [tuple(c + Vector((0.004 * math.cos(ph + t * 9), 0.004 * math.sin(ph + t * 9), 0.006 * t)))
                   for t in [i / 6 for i in range(7)]]
            tube(b, hair, pts, [0.0035] * 7, n=4)
    # the body: jacket at the sides and back, the waistcoat in front with brass buttons, lapels, the shirt collar
    keys = [(0.04, 0.118, 0.092, 0.0), (0.12, 0.112, 0.086, -0.004), (0.22, 0.12, 0.09, -0.006),
            (0.3, 0.125, 0.088, 0.0), (0.345, 0.112, 0.08, 0.004), (0.375, 0.07, 0.055, 0.004)]
    rows = []
    for i in range(18):
        z = 0.04 + (0.375 - 0.04) * i / 17
        rx, ry, yc = keyed(keys, z)
        rows.append([(math.cos(2 * math.pi * j / 32) * rx, yc + math.sin(2 * math.pi * j / 32) * ry, z)
                     for j in range(32)])
    grid_mats(b, rows, lambda i, j: vest if math.sin(2 * math.pi * (j + 0.5) / 32) < -0.8 else coat)
    for k in range(4):
        zb = 0.12 + 0.055 * k
        _, ry, yc = keyed(keys, zb)
        ellipsoid(b, 'h_brass', (0.0, yc - ry - 0.002, zb), (0.007, 0.004, 0.007), n=6, rings=4)
    for s in (-1, 1):
        hob_tube(b, coat, [(s * 0.048, -0.084, 0.06), (s * 0.05, -0.088, 0.2), (s * 0.045, -0.083, 0.3),
                           (s * 0.028, -0.065, 0.36)], 0.01, 0.008, n=6)
    hob_tube(b, 'h_shirt', [(-0.045, -0.02, 0.37), (-0.03, -0.055, 0.378), (0.0, -0.064, 0.382), (0.03, -0.055, 0.378),
                            (0.045, -0.02, 0.37)], 0.012, 0.012, n=6)
    hob_tube(b, 'h_skin', [(0.0, -0.004, 0.37), (0.0, -0.008, 0.41)], 0.034, 0.032, n=8)
    hob_head(b, rng, hair)
    # the cloak: an open sheet from the shoulders round the back to the bark, folds deepening downwards
    ph = rng.uniform(0, 6.3)
    rows = []
    for i in range(16):
        t = i / 15
        z = 0.385 - 0.375 * t
        rx = 0.1 + 0.11 * t ** 0.8
        ry = 0.075 + 0.105 * t ** 0.8
        yc = 0.008 + 0.02 * t
        row = []
        for j in range(30):
            a = math.radians(-58.0 + 288.0 * j / 29)            # from the front right round the back to the left
            fold = 1.0 + (0.06 * math.sin(11 * a + ph) + 0.03 * math.sin(23 * a + 2 * ph)) * t
            row.append((math.cos(a) * rx * fold, yc + math.sin(a) * ry * fold, z))
        rows.append(row)
    thick_sheet(b, 'h_cloak', rows[::-1], 0.006)
    ph2 = rng.uniform(0, 6.3)
    hood = [(math.cos(a) * 0.09, 0.01 + math.sin(a) * 0.07, 0.392 + 0.012 * math.sin(a))
            for a in [math.radians(-20 + 220 * i / 14) for i in range(15)]]
    tube(b, 'h_cloak', hood, [0.024 + 0.012 * math.sin(math.pi * i / 14) + 0.004 * math.sin(i * 1.7 + ph2)
                              for i in range(15)], n=10, tip=False)
    ellipsoid(b, 'h_brooch', (0.0, -0.085, 0.36), (0.011, 0.004, 0.022), n=10, rings=6,
              R=Matrix.Rotation(math.radians(12.0 * reach), 4, 'Y'))       # the brooch: a green enamel leaf
    hob_tube(b, 'h_silver', [(0.0, -0.09, 0.34), (0.0, -0.09, 0.382)], 0.0018, 0.0012, n=4, step=0.006)
    # arms: one hand round the twig at his side, the other on his knee
    twig = [(reach * 0.205, 0.035, -0.04), (reach * 0.215, 0.05, 0.16), (reach * 0.205, 0.07, 0.36),
            (reach * 0.235, 0.08, 0.52)]
    hob_tube(b, 'twig', twig, 0.017, 0.006, n=7)
    hob_tube(b, 'twig', [(reach * 0.21, 0.065, 0.32), (reach * 0.27, 0.05, 0.42), (reach * 0.3, 0.035, 0.47)], 0.008,
             0.003, n=5)
    sh, el, wr = (reach * 0.112, -0.005, 0.335), (reach * 0.175, -0.04, 0.24), (reach * 0.19, 0.005, 0.27)
    hob_tube(b, coat, [sh, el], 0.034, 0.028, n=8)
    hob_tube(b, coat, [el, wr], 0.028, 0.024, n=8)
    hob_tube(b, 'h_shirt', [wr, (reach * 0.193, 0.012, 0.275)], 0.024, 0.023, n=10, step=0.004)
    hob_hand(b, (reach * 0.193, 0.014, 0.276), (reach * 0.205, 0.06, 0.29), grip=0.9)
    sh2, el2, wr2 = (-reach * 0.112, -0.005, 0.335), (-reach * 0.135, -0.07, 0.2), (-reach * 0.09, -0.15, 0.115)
    hob_tube(b, coat, [sh2, el2], 0.034, 0.028, n=8)
    hob_tube(b, coat, [el2, wr2], 0.028, 0.024, n=8)
    hob_tube(b, 'h_shirt', [wr2, (-reach * 0.085, -0.158, 0.108)], 0.024, 0.023, n=10, step=0.004)
    hob_hand(b, (-reach * 0.083, -0.16, 0.106), (-reach * 0.075, -0.21, 0.08), grip=0.5)


def hobbits(b, rng):
    for side, who in ((-1, 'P'), (1, 'M')):
        M = (Matrix.Translation((side * SEAT[0], SEAT[1], SEAT[2])) @ Matrix.Rotation(math.radians(side * 12.0), 4, 'Z')
             @ Matrix.Scale(HOB_S, 4))
        hobbit(Local(b, M), rng, who, reach=side)


def build_riders(b):
    """Mesh 5: Merry and Pippin (their own small texture)."""
    riders_palette()
    b.normal_fn = normals
    b.tiny_px = 0
    b.ao_distance = 0.8
    hobbits(b, random.Random(1958))


def build_beard(b):
    """Mesh 4: the beard, the moustache and the moss hanging from the arms."""
    beard_palette()
    b.normal_fn = normals
    b.tiny_px = 8
    b.ao_distance = 3.0
    rng = random.Random(1955)
    beard(b, rng)
    hanging_moss(b, rng)


SKIN_PARTS = [('body', build_body, 2048), ('head', build_head, 2048), ('crown', build_crown, 2048),
              ('beard', build_beard, 2048), ('riders', build_riders, 1024)]

PREVIEW = [((0, -40, 80), (0, -7, 74), 50),                  # the face and the beard
           ((130, -10, 60), (0, 0, 52), 38),                 # from the east (the lean is front/back)
           ((-21, -22, 75), (-13.2, -4.0, 70.0), 70),        # Pippin on the right shoulder
           ((19, -21, 74), (13.2, -4.0, 70.0), 70)]          # Merry on the left shoulder
PREVIEW_EYE = [((0, -150, 120), (0, 0, 50), 40)]
