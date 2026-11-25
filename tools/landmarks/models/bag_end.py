"""Bag End: the landmark of the Hobbits' capital, The Shire (an IMPROVEMENT, docs/LANDMARKS.md).

v2 (2026-11-25, the user: "focused on Bilbo's house in the hill"; reference screenshots/bag-end.webp, the painting of
Gandalf at Bilbo's gate). Built like Erebor and Orthanc (in-game units, improvement Scale 0.25 with the writer's x4;
origin = tile centre, ground z = 0, -Y = south = towards the game camera) and FITS ITS OWN HEX.
  * The Hill, green and round, filling the back of the hex; the great tree stands on it above the door, its roots
    running down over the turf; a tall brick chimney smokes on the hill's shoulder;
  * Bag End's front cut into the Hill's foot: a curved wall of field stone under a thick turf lip, "a perfectly round
    door like a porthole, painted green, with a shiny yellow brass knob in the exact middle" in a timber ring and an
    arch of stones, a round many-paned window either side with a warm light in it;
  * the garden: stepping stones from the door to the white picket gate, tall sunflowers by the windows, a few clumps
    of flowers along the wall; the lane past the gate;
  * Bilbo and Gandalf sitting on the grass before the door, smoking their pipes (small smoke plumes on the bowls):
    Gandalf in grey with the blue-grey cloak and the tall pointed hat, his long beard and long pipe, the staff leaning
    on his shoulder; Bilbo in white shirt, red waistcoat and brown breeches, curly-haired and bare-footed;
  * the meadow round it, a few trees at the hex's edges.
Natural and real (the user's rule, landmark-realism): muted greens, weathered stone and timber, faded paint.

Two parts: static = the land (hill, garden, lane), the stone front, the chimney, the stepping stones, the edge trees;
skinned = the door, windows, the great tree, the garden, the fence, Bilbo and Gandalf, on the still bone (PIVOT_MATS
empty: nothing moves), plus the effect bones (the windows' glow, the chimney's and the pipes' smoke).
(v1 modelled the whole of Hobbiton; the user found it over-engineered.)
v3 (user, 2026-11-25): no trees round the tile, Bag End bigger and filling the whole tile with the fence round the
tile's edge, Bilbo and Gandalf much bigger, the hill covered in tufts of grass.
v4 (user, 2026-11-25): no raised base ("a hexagonal pile of dirt"): the garden is the tile itself, the fence stands
on it near its edge; Bag End and the two friends 50% bigger again; the pipes puff: one-shot musket-smoke bursts timed
in the 8 s idle loop (Gandalf twice, then Bilbo), the chimney smokes and billows (see rig()). The big Hill covers the
tile's middle, where the city's stock houses stand (they can't be removed for one city; whatever stands in the open
garden still shows).
"""
import math
import os
import random

from mathutils import Vector

import blib
import sprites
from blib import material, hexcol as h, box, cyl, lathe, blob, ring, T
from moria_v4 import smooth, fbm, tube, _spline as spline
from erebor import oriented, ribbon, hex_dist, seg_dist, slab_xz, bar_xz, loft

BAKE = True
BAKE_PX = 2048
EYE_PX = 2048
EYE_AO = 16
TINY_PX = 12
PIVOT_MATS = set()                 # nothing moves

HEX = 33.6
FLOOR = -1.0
G0 = 0.55                          # the meadow (just above the game's ground; it sinks under it at the hex's edge)
PLAT = 0.0                         # v3 raised the garden 6.5 (it hid the stock houses); v4: on the tile itself
HILL = (0.0, 17.0)
HH = 25.0

# Bag End's front: centre, facing (270 = south), half-width W, curvature c, garden depth D, least front height HW
BAG = dict(x=0.0, y=-9.0, deg=270, W=19.5, c=0.017, D=14.0, HW=15.8)
DOOR_R = 5.4
DOOR_ZC = DOOR_R + 0.3
WIN_X, WIN_Z, WIN_R = 12.9, 6.0, 3.0
FENCE_IN = 2.4                     # the fence runs round the tile this far inside its edge
TREE = (-10.5, 14.5)               # local position of the great tree (l, back)
CHIM = (12.8, 12.0, 8.5)           # local (l, back), height above the turf
BILBO = (-9.5, -8.2, 15.0)         # local (l, y, turn): sitting on the grass, a little turned towards Gandalf
GANDALF = (10.0, -9.2, -18.0)
FIG_S = 3.0                        # both figures: heroic scale, to read from the game's camera
TUFTS = 1600                       # cut-out grass tufts (two crossed cards each), all in the static part
# v8 (user: "the grass and the tree look bland... branches and leaves... astonishing, like it is made in 2026"):
# the foliage and the grass are painted cut-out sprites on cards (tools/landmarks/sprites.py, bake.py SPRITES), the
# way the stock Hanging Gardens draw their plants: many leaves / blades per card, see-through gaps, custom normals.
CROWN = {}                         # the great tree's crown (centre, radii), for the leaves' normals
LOOP = 24.0                        # the idle loop (s), = the puff effect's own loop
# The pipes (user: "every 4-6 seconds a roundish cloud of smoke in front of their faces, dissipating gradually into
# nothingness in 1-2 seconds; not at the same time"): our own model effect (tools/landmarks/puffs.py), six soft cloud
# cards per friend. Puff times in the 24 s loop: irregular gaps of 4.3-5.5 s each, the two never overlapping.
# (v4's musket smoke flashed and jetted "like ballistic missiles"; v5's ship smoke, 0.8 s at a time, did not show.)
PUFF_TIMES = dict(gandalf=(0.6, 5.4, 10.9, 15.6, 20.3), bilbo=(2.9, 8.1, 13.2, 17.9, 22.4))
PUFF_LIFE = 1.6                    # s from the first wisp to the last one gone
MOUTHS = dict(gandalf=(0.0, -0.95, 2.5), bilbo=(0.0, -0.5, 1.42))   # just in front of the face (figure units)
PUFF_FX = (0.0, -26.0)             # world (x, y) of the effect's bone, at the ground between the two


# ----------------------------------------------------------------------------------------------- frames
def frame(hd):
    a = math.radians(hd['deg'])
    d = (math.cos(a), math.sin(a))
    return d, (-d[1], d[0])


def to_local(hd, x, y):
    d, t = frame(hd)
    px, py = x - hd['x'], y - hd['y']
    return px * t[0] + py * t[1], -(px * d[0] + py * d[1])        # (l, back): back > 0 = into the hill


def to_world(hd, l, back):
    d, t = frame(hd)
    return hd['x'] + l * t[0] - back * d[0], hd['y'] + l * t[1] - back * d[1]


def M_of(hd):
    return T(hd['x'], hd['y'], hd['z'], rz=hd['deg'] + 90)


class Local:
    """A builder proxy: everything added through it is placed by the matrix M."""
    def __init__(self, b, M):
        self.b, self.M = b, M

    def add(self, verts, faces, mat, smooth=False, M=None):
        self.b.add(verts, faces, mat, smooth=smooth, M=self.M @ M if M is not None else self.M)

    def __getattr__(self, k):
        return getattr(self.b, k)


# ----------------------------------------------------------------------------------------------- the land
def base_h(x, y):
    dx, dy = x - HILL[0], (y - HILL[1]) * 1.1
    r = math.hypot(dx, dy)
    z = HH * math.exp(-(r / 21.0) ** 2.2)
    z += 0.6 * fbm(x * 0.08, y * 0.08, 3, 71) + 0.12 * fbm(x * 0.5, y * 0.5, 2, 72)
    return G0 + PLAT + z


def raw_h(x, y):
    """The land with the mound over Bag End's front (no cut)."""
    z = base_h(x, y)
    hd = BAG
    l, back = to_local(hd, x, y)
    if -2.0 < back < 27.0 and abs(l) < hd['W'] + 8.0:
        req = hd['z'] + hd['HW'] * smooth((26.0 - back) / 14.0) * smooth((hd['W'] + 5.0 - abs(l)) / 13.0) * \
            smooth((back + 1.5) / 1.5)
        if req > z:
            z = req + 0.25 * fbm(x * 0.5, y * 0.5, 2, 73) * smooth((req - z) / 1.0)
    return z


def height(x, y):
    z = raw_h(x, y)
    hd = BAG
    l, back = to_local(hd, x, y)                                    # the garden: a level lawn before the front
    if back < hd['c'] * l * l + 0.4 and back > -hd['D'] - 12.0 and abs(l) < hd['W'] + 8.0:
        w = smooth((hd['W'] + 7.0 - abs(l)) / 7.0) * smooth((hd['D'] + 11.0 + back) / 11.0)
        if z > hd['z']:
            w *= 1.0 - 0.2 * smooth((abs(l) - hd['W']) / 4.0)
        z = z + (hd['z'] - z) * w
    return FLOOR + (z - FLOOR) * smooth((hex_dist(x, y) - 0.2) / 2.0)


def ground(x, y):
    return max(height(x, y), 0.0)


def lground(l, y):
    """The land's height at a local point (l, y) of Bag End's frame (y < 0 = in front), relative to its garden."""
    return ground(*to_world(BAG, l, y)) - BAG['z']


def ground_mat(x, y, z, s):
    return 'earth' if s > 3.2 else 'grass'


def setup():
    x, y = to_world(BAG, 0.0, -2.0)
    BAG['z'] = base_h(x, y) - 0.1


setup()


# ----------------------------------------------------------------------------------------------- sprites and cards
_SPRITES = {}


def _sprite(name, make):
    if name not in _SPRITES:
        _SPRITES[name] = make()
    return _SPRITES[name]


def card(b, mat, c, facing, w, hgt, up=(0.0, 0.0, 1.0), roll=0.0):
    """A cut-out card (bake.py SPRITES) centred on c, its face towards `facing` (single-sided: the game's camera never
    turns), w x hgt, the sprite's top towards `up`, turned by roll degrees in its plane."""
    f = Vector(facing).normalized()
    U = Vector(up)
    ey = (U - f * f.dot(U)).normalized()
    ex = ey.cross(f)
    r = math.radians(roll)
    ex, ey = ex * math.cos(r) + ey * math.sin(r), -ex * math.sin(r) + ey * math.cos(r)
    ex, ey = ex * (w / 2), ey * (hgt / 2)
    C = Vector(c)
    v = [tuple(C - ex - ey), tuple(C + ex - ey), tuple(C + ex + ey), tuple(C - ex + ey)]
    b.add(v, [(0, 1, 2, 3)], mat)
    if not hasattr(b, 'sprite_uv'):
        b.sprite_uv = {}
    b.sprite_uv[len(b.faces) - 1] = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


def normals(p, mat):
    """Custom normals (bake.py): grass lit like the lawn (up); leaves lit as one soft crown (out from its middle)."""
    if mat.startswith('grassS'):
        return (0.0, 0.0, 1.0)
    if mat.startswith('leafS') and CROWN:
        (cx, cy, cz), (rx, ry, rz) = CROWN['c'], CROWN['r']
        n = Vector(((p[0] - cx) / rx, (p[1] - cy) / ry, (p[2] - cz) / rz + 0.35))
        return tuple(n.normalized()) if n.length > 1e-6 else (0.0, 0.0, 1.0)
    return None


# ----------------------------------------------------------------------------------------------- materials
def land_palette():
    material('grass', h('6c8a3f'), h('5b7a35'), zramp=[(FLOOR, h('667f3b')), (6.0, h('6c8a40')), (18.0, h('76914a'))],
             slope_color=h('5f7a3a'), slope_start=0.8)
    blib.PALETTE['grass'].update(scale=0.35, cavity=0.45,
                                 speckle=[(3.5, 0.05, h('dcd8c0')), (2.6, 0.04, h('c9ad3e')), (1.6, 0.22, h('4f6c2b')),
                                          (2.2, 0.16, h('82a052'))])
    for name, img in (('grassS0', lambda: sprites.grass_tuft(21)), ('grassS1', lambda: sprites.grass_tuft(22, flowers=9)),
                      ('grassS2', lambda: sprites.grass_tuft(23, dry=0.45))):
        material(name, h('5b7a35'), ao=False, spec=0.12, refl=4)
        blib.PALETTE[name].update(sprite=_sprite(name, img))
    material('earth', h('6d5e45'), h('5a4d39'))
    blib.PALETTE['earth'].update(scale=0.6, cracks=0.8, cavity=0.4, speckle=[(2.5, 0.2, h('5f7a3a'))])
    material('path', h('8f7b58'), h('7e6b4a'))
    blib.PALETTE['path'].update(scale=0.8, cracks=0.5, cavity=0.3, speckle=[(4.0, 0.1, h('6f603f')), (3.0, 0.06, h('5f7a3a'))])
    material('stone', h('948670'), h('7f735f'))                       # mortared field stone, warm
    blib.PALETTE['stone'].update(scale=1.3, cracks=3.4, cavity=0.85, strata=3.0, strata_amp=0.16,
                                 moss=(h('6a7a45'), 2.0), speckle=[(4.0, 0.12, h('a89a80')), (5.0, 0.08, h('6e6556'))])
    material('dstone', h('9a9282'), h('857d6e'))                      # flags, steps, the arch
    blib.PALETTE['dstone'].update(scale=0.9, cracks=1.6, cavity=0.6, moss=(h('6b7848'), 2.5))
    material('brick', h('8a5642'), h('7a4a38'))
    blib.PALETTE['brick'].update(scale=0.5, strata=6.0, strata_amp=0.16, cracks=1.4, cavity=0.6)
    material('bark', h('544638'), h('42382e'))
    blib.PALETTE['bark'].update(scale=0.9, vcracks=(0.7, 0.45), cavity=0.7, moss=(h('5e6b3c'), 2.0))
    for name, c1, c2 in (('leafA', '4d6b2c', '435f27'), ('leafB', '5b7a33', '51702e'), ('leafC', '6a8439', '5f7833')):
        material(name, h(c1), h(c2))
        blib.PALETTE[name].update(scale=2.5, cavity=0.8, speckle=[(6.0, 0.15, h('33491f')), (5.0, 0.08, h('7e9447'))])


def life_palette():
    land_palette()
    for name, img in (('leafS0', lambda: sprites.leaf_cluster(11, light=-0.12)),
                      ('leafS1', lambda: sprites.leaf_cluster(12)),
                      ('leafS2', lambda: sprites.leaf_cluster(13, light=0.12, base=(0.34, 0.46, 0.17)))):
        material(name, h('4f6c2b'), ao=False, spec=0.15, refl=6)
        blib.PALETTE[name].update(sprite=_sprite(name, img))
    material('door_green', h('2f5a33'), h('2a5230'), spec=0.45, refl=40)
    blib.PALETTE['door_green'].update(scale=3.0, vcracks=(0.5, 0.15), cavity=0.5)
    material('brass', h('c8a34e'), spec=0.9, refl=170, ao=False)
    blib.PALETTE['brass'].update(solid=True)
    material('timber', h('5c4835'), h('4c3c2d'))
    blib.PALETTE['timber'].update(scale=1.6, vcracks=(0.6, 0.35), cavity=0.55)
    material('paint', h('dedad0'), h('d0ccc0'))                       # the white fence, weathered
    blib.PALETTE['paint'].update(scale=1.2, vcracks=(0.5, 0.1), cavity=0.45)
    material('litwin', h('c98d47'), ao=False)
    blib.PALETTE['litwin'].update(solid=True)
    material('iron', h('2c2a28'), spec=0.5, refl=40)
    blib.PALETTE['iron'].update(solid=True)
    for name, c in (('flowR', 'b4503f'), ('flowY', 'd2b04a'), ('flowP', '8f70a0'), ('flowW', 'e2ddd0')):
        material(name, h('557532'), h('4b6a2d'))              # a green clump, dotted with blossoms
        blib.PALETTE[name].update(scale=5.0, cavity=0.7, speckle=[(9.0, 0.34, h(c)), (6.0, 0.12, h(c))])
    material('stalk', h('5d7434'), h('4f6630'))
    blib.PALETTE['stalk'].update(scale=3.0, cavity=0.5)
    material('petal', h('d9a92e'), h('c99a28'))
    blib.PALETTE['petal'].update(scale=4.0, cavity=0.4)
    material('seed', h('4a3423'))
    blib.PALETTE['seed'].update(solid=True)
    # the figures
    material('skin', h('c99d80'), h('b98d72'))
    blib.PALETTE['skin'].update(solid=True)
    material('g_robe', h('8a8782'), h('7c7974'))
    blib.PALETTE['g_robe'].update(scale=3.0, cavity=0.75, vcracks=(0.4, 0.15))
    material('g_cloak', h('5a636c'), h('505862'))
    blib.PALETTE['g_cloak'].update(scale=3.0, cavity=0.75, vcracks=(0.4, 0.15))
    material('g_hat', h('55606c'), h('4c5662'))
    blib.PALETTE['g_hat'].update(scale=3.0, cavity=0.7)
    material('g_beard', h('c6c3bb'), h('b5b2aa'))
    blib.PALETTE['g_beard'].update(scale=6.0, vcracks=(0.6, 0.3), cavity=0.5)
    material('boot', h('3d3128'), h('33291f'))
    blib.PALETTE['boot'].update(solid=True)
    material('b_shirt', h('ddd5c3'), h('cfc7b5'))
    blib.PALETTE['b_shirt'].update(scale=3.0, cavity=0.7)
    material('b_coat', h('8c3b2c'), h('7c3427'))
    blib.PALETTE['b_coat'].update(scale=3.0, cavity=0.6)
    material('b_breech', h('6b5338'), h('5e4931'))
    blib.PALETTE['b_breech'].update(scale=3.0, cavity=0.6)
    material('b_hair', h('5a3d24'), h('4b321d'))
    blib.PALETTE['b_hair'].update(scale=6.0, cavity=0.8)
    material('pipe', h('4a3524'), spec=0.5, refl=50)
    blib.PALETTE['pipe'].update(solid=True)
    material('ember', h('ff8a32'), ao=False)
    blib.PALETTE['ember'].update(solid=True)


# ----------------------------------------------------------------------------------------------- shared shapes
def wall_top(l):
    hd = BAG
    back = hd['c'] * l * l
    x, y = to_world(hd, l, back + 1.4)
    return max(raw_h(x, y), hd['z'] + 1.0) - hd['z'] + 0.1


def win_turn(e):
    """The windows lie along the curved front (its tangent at their centre: y = c l^2, slope 2 c l), so no part of the
    round window sinks behind the wall (v9: the inner half was hidden). e = -1 left, +1 right; degrees about z."""
    return e * math.degrees(math.atan(2 * BAG['c'] * WIN_X))


def win_light_y():
    """The plane of the windows' light: just before the front at the windows' inner edges (the nearest part of the
    wall round them), so the glow is never clipped by the wall."""
    return BAG['y'] + BAG['c'] * (WIN_X - WIN_R) ** 2 - 0.4


def disc(b, mat, x, y, z, r, depth, n=24):
    cyl(b, mat, 0, 0, 0, r, depth, n=n, M=T(x, y, z, rx=90))


def round_window(b, x, y, z, r, lit=True):
    k = r / 1.3
    disc(b, 'litwin' if lit else 'iron', x, y + 0.02, z, r, 0.05, n=32)
    ring(b, 'timber', r - 0.02, r + 0.22 * k, 0.0, 0.26 * k, n=32, M=T(x, y + 0.02, z, rx=90))
    for (x0, z0, x1, z1) in ((x - r, z, x + r, z), (x, z - r, x, z + r)):                  # the panes
        bar_xz(b, 'timber', x0, z0, x1, z1, 0.09 * k, y - 0.03, 0.07 * k)
    for e in (-1, 1):
        q = r * 0.5
        hz = math.sqrt(r * r - q * q)
        bar_xz(b, 'timber', x + e * q, z - hz, x + e * q, z + hz, 0.06 * k, y - 0.03, 0.06 * k)
        bar_xz(b, 'timber', x - hz, z + e * q, x + hz, z + e * q, 0.06 * k, y - 0.03, 0.06 * k)


def round_door(b, y, zc, r):
    k = r / 2.4
    disc(b, 'door_green', 0.0, y + 0.03, zc, r, 0.16 * k, n=48)
    ring(b, 'timber', r, r + 0.26 * k, 0.0, 0.32 * k, n=48, M=T(0, y + 0.03, zc, rx=90))  # its frame
    for i in range(-4, 5):                                                               # the planks
        x = i * r / 4.6
        hz = math.sqrt(max(0.0, r * r - x * x)) * 0.95
        bar_xz(b, 'door_green', x - 0.015 * k, zc - hz, x + 0.015 * k, zc + hz, 0.035 * k, y - 0.13 * k, 0.03 * k)
    blib.sphere(b, 'brass', 0.0, y - 0.26 * k, zc, 0.17 * k, n=12, rings=8)            # in the exact middle
    cyl(b, 'brass', 0, 0, 0, 0.09 * k, 0.12 * k, n=10, M=T(0.0, y - 0.13 * k, zc, rx=90))
    for zz in (zc - r * 0.5, zc + r * 0.5):                                             # hinges
        bar_xz(b, 'iron', -r * 0.97, zz, -r * 0.3, zz, 0.11 * k, y - 0.13 * k, 0.04 * k)
        blib.sphere(b, 'iron', -r * 0.3, y - 0.18 * k, zz, 0.07 * k, n=6, rings=4)


def sunflower(b, rng, x, y, z, hgt):
    """A tall sunflower: a stalk, broad leaves, the head of petals round a dark seed disc, turned to the south."""
    top = (x + rng.uniform(-0.15, 0.15), y - 0.25, z + hgt)
    tube(b, 'stalk', spline([(x, y, z - 0.1), (x, y - 0.05, z + hgt * 0.5), top], 6), [0.07] * 7, n=5, tip=False)
    for k in range(4):                                       # leaves: drooping blades on both sides
        zz = z + hgt * (0.25 + 0.17 * k)
        s = 1 if k % 2 else -1
        p0 = (x, y, zz)
        p1 = (x + s * 0.45, y - 0.1, zz + 0.12)
        p2 = (x + s * 0.8, y - 0.15, zz - 0.15)
        tube(b, 'stalk', spline([p0, p1, p2], 5), [0.05, 0.15, 0.2, 0.18, 0.12, 0.02], n=5)
    tx, ty, tz = top
    M = T(tx, ty, tz, rx=72)                                 # the head faces south, a little down
    for k in range(14):
        a = 2 * math.pi * k / 14
        box(b, 'petal', 0, 0, -0.03, 0.17, 0.42, 0.06,
            M=M @ T(0.42 * math.cos(a), 0.42 * math.sin(a), 0, rz=math.degrees(a) + 90))
    cyl(b, 'seed', 0, 0, 0, 0.3, 0.12, n=12, M=M)
    cyl(b, 'stalk', 0, 0, 0, 0.32, 0.08, n=12, M=M @ T(0, 0, -0.08))


def fence_corners():
    """The fence's corners: the tile's hexagon (pointy-top: corners S, SE, NE, N, NW, SW) FENCE_IN inside its edge."""
    R = (HEX - FENCE_IN) / math.cos(math.radians(30))
    return [(R * math.cos(math.radians(a)), R * math.sin(math.radians(a))) for a in (270, 330, 30, 90, 150, 210)]


def gate_pos():
    """The gate: a quarter of the way along the fence's south-east side (its middle, the side's direction)."""
    c = fence_corners()
    (ax, ay), (bx, by) = c[0], c[1]
    t = 0.3
    return (ax + (bx - ax) * t, ay + (by - ay) * t), math.atan2(by - ay, bx - ax)


def picket(b, x, y, z, ang, w, hgt):
    """One white picket: a flat board with a pointed top, both faces (its edges are too thin to see)."""
    ca, sa = math.cos(ang), math.sin(ang)
    pts = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, hgt), (0.0, hgt + w * 0.9), (-w / 2, hgt)]
    for e in (-1, 1):
        v = [(x + u * ca - e * 0.03 * sa, y + u * sa + e * 0.03 * ca, z + q) for u, q in pts]
        b.add(v, oriented(v, [(0, 1, 2, 3, 4)], (-sa * e, ca * e, 0.0)), 'paint')


def picket_fence(b):
    """The white fence round the whole tile (the painting): pickets with pointed tops on two rails, posts with round
    finials every few units, the gate open in the south-east."""
    c = fence_corners()
    (gx, gy), _ = gate_pos()
    hgt, step = 1.6, 0.55
    for (ax, ay), (bx, by) in zip(c, c[1:] + c[:1]):
        L = math.hypot(bx - ax, by - ay)
        ang = math.atan2(by - ay, bx - ax)
        nposts = max(2, int(L / 4.0))
        for i in range(int(L / step)):
            t = (i + 0.5) / int(L / step)
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            if math.hypot(x - gx, y - gy) < 1.3:
                continue
            picket(b, x, y, ground(x, y) - 0.1, ang, 0.22, hgt)
        for k in range(nposts):
            t0, t1 = k / nposts, (k + 1) / nposts
            p = (ax + (bx - ax) * t0, ay + (by - ay) * t0)
            q = (ax + (bx - ax) * t1, ay + (by - ay) * t1)
            for hz in (0.45, hgt - 0.35):                                   # the rails, behind the pickets
                segs = [(p, q)]
                if min(math.hypot(p[0] - gx, p[1] - gy), math.hypot(q[0] - gx, q[1] - gy)) < L / nposts:
                    segs = []                                               # the gate's bay: rails only on the gate
                for (u, w_) in segs:
                    mx, my = (u[0] + w_[0]) / 2, (u[1] + w_[1]) / 2
                    box(b, 'paint', mx + 0.08 * math.sin(ang), my - 0.08 * math.cos(ang) * -1,
                        (ground(*u) + ground(*w_)) / 2 + hz, math.hypot(w_[0] - u[0], w_[1] - u[1]), 0.08, 0.12,
                        rz=math.degrees(ang))
            z = ground(*p)
            box(b, 'paint', p[0], p[1], z - 0.2, 0.36, 0.36, hgt + 0.55)
            blib.sphere(b, 'paint', p[0], p[1], z + hgt + 0.55, 0.26, n=8, rings=5)
    # the gate: two posts, the gate swung open inwards
    _, ang = gate_pos()
    ca, sa = math.cos(ang), math.sin(ang)
    for e in (-1, 1):
        x, y = gx + e * 1.25 * ca, gy + e * 1.25 * sa
        z = ground(x, y)
        box(b, 'paint', x, y, z - 0.2, 0.4, 0.4, hgt + 0.75)
        blib.sphere(b, 'paint', x, y, z + hgt + 0.75, 0.3, n=8, rings=5)
    hx, hy = gx - 1.1 * ca, gy - 1.1 * sa                                   # hinge side; swung 70 degrees inwards
    ga = ang + math.radians(70)
    for k in range(4):
        u = 0.3 + 0.5 * k
        x, y = hx + u * math.cos(ga), hy + u * math.sin(ga)
        picket(b, x, y, ground(x, y) - 0.05, ga, 0.24, hgt - 0.1)
    for hz in (0.5, hgt - 0.4):
        box(b, 'paint', hx + 1.0 * math.cos(ga), hy + 1.0 * math.sin(ga), ground(hx, hy) + hz, 2.0, 0.08, 0.12,
            rz=math.degrees(ga))


def grass_tufts(b, rng, n):
    """Tufts of meadow grass: two crossed cut-out cards each (painted blades, sprites.grass_tuft), turned towards the
    game's camera and leaning back a little; plain, flowering or dry. Dense on the hill, sparser in the garden, none on
    the path, at the wall's foot or round Bilbo and Gandalf."""
    hd = BAG
    path = path_pts()
    made = tries = 0
    while made < n and tries < n * 60:
        tries += 1
        x, y = rng.uniform(-HEX, HEX), rng.uniform(-HEX / 0.866, HEX / 0.866)
        if hex_dist(x, y) < FENCE_IN + 1.0:
            continue
        l, back = to_local(hd, x, y)
        if abs(l) < hd['W'] + 0.5 and -2.5 < back < hd['c'] * l * l + 1.0:
            continue                                               # the flower beds and the wall's foot
        if seg_dist(x, y, path) < 1.6:
            continue
        if any(math.hypot(l - fx, back - fy) < 6.5 for fx, fy, _ in (BILBO, GANDALF)):
            continue
        hill = smooth((raw_h(x, y) - (G0 + PLAT) - 0.6) / 3.0)
        if rng.random() > 0.35 + 0.65 * hill:
            continue
        z = ground(x, y) - 0.12
        s = rng.uniform(0.8, 1.2) * (1.0 + 0.25 * hill)
        w, hgt = 3.0 * s, 1.9 * s
        r = rng.random()
        m = 'grassS1' if r < 0.22 else ('grassS2' if r < 0.37 else 'grassS0')
        yaw = rng.uniform(-15, 15)
        for e in (-1, 1):                                          # crossed, both facing the camera's side
            a = math.radians(-90 + yaw + e * 38)
            f = (math.cos(a), math.sin(a), 0.32)                   # leaning back: seen from above too
            card(b, m, (x, y, z + hgt / 2), f, w, hgt)
        made += 1
    return made


def path_pts():
    """The stepping stones' line, from the door to the gate (world)."""
    (gx, gy), _ = gate_pos()
    x0, y0 = to_world(BAG, 0.0, -1.6)
    return [(p[0], p[1]) for p in spline([(x0, y0, 0.0), (x0 + 1.5, y0 - 6.0, 0.0), (gx - 2.0, gy + 5.0, 0.0),
                                          (gx, gy + 0.6, 0.0)], 40)]


def great_tree(b, rng, x, y, z, hgt, spread):
    """The great tree above Bag End: a stout trunk whose roots run down over the turf; seven limbs from a third of
    its height, two branches on each, two twigs on each branch (tapering bark tubes); a broad crown of cut-out leaf
    clusters (sprites.leaf_cluster) round the branches' ends and over the crown's dome, shade clusters low and on the
    far side, sunlit ones on top, all turned towards the game's camera; their normals make the crown one soft mass."""
    tr = hgt * 0.06
    trunk = [(x, y, z - 0.6), (x + 0.25, y + 0.1, z + hgt * 0.16), (x + 0.45, y + 0.15, z + hgt * 0.32)]
    tube(b, 'bark', spline(trunk, 8), [tr * 1.45, tr * 1.2, tr * 1.05, tr, tr * 0.95, tr * 0.9, tr * 0.86, tr * 0.82,
                                       tr * 0.8], n=12, tip=False)
    for k in range(5):                                       # roots: over the turf, down the slope, into it
        a = math.radians(-90 + (k - 2) * 34 + rng.uniform(-8, 8))
        pts = []
        for i in range(7):
            t = i / 6
            px, py = x + math.cos(a) * (0.5 + 6.0 * t), y + math.sin(a) * (0.5 + 6.0 * t) + 0.4 * math.sin(t * 6 + k)
            pts.append((px, py, ground(px, py) + 0.3 * (1.0 - t) + 0.8 * math.exp(-t * 5) - 0.05))
        tube(b, 'bark', spline(pts, 12), [tr * 0.6 * (1.0 - 0.85 * i / 12) + 0.06 for i in range(13)], n=7)
    cz, cr = z + hgt * 0.6, (spread, spread * 0.95, hgt * 0.34)
    CROWN.update(c=(x + 0.3, y, cz), r=cr)
    top = Vector(trunk[-1])
    tips = []

    def branch(p0, p1, p2, r0, r1, n):
        pts = spline([p0, p1, p2], 8)
        tube(b, 'bark', pts, [r0 + (r1 - r0) * i / (len(pts) - 1) for i in range(len(pts))], n=n)
        return pts
    for k in range(7):                                       # the limbs
        a = 2 * math.pi * k / 7 + rng.uniform(-0.25, 0.25)
        rr = spread * rng.uniform(0.6, 0.82)
        h0 = top + Vector((0, 0, rng.uniform(-1.2, 0.6)))
        p1 = Vector((x + math.cos(a) * rr * 0.42, y + math.sin(a) * rr * 0.42, z + hgt * rng.uniform(0.42, 0.5)))
        p2 = Vector((x + math.cos(a) * rr, y + math.sin(a) * rr, z + hgt * rng.uniform(0.56, 0.7)))
        pts = branch(tuple(h0), tuple(p1), tuple(p2), tr * 0.62, tr * 0.16, 7)
        tips.append(p2)
        for j, t in enumerate((0.45, 0.72)):                # branches off each limb
            q = Vector(pts[int(t * (len(pts) - 1))])
            b_ = a + (0.7 if j == 0 else -0.7) + rng.uniform(-0.3, 0.3)
            L = spread * rng.uniform(0.28, 0.4)
            e = q + Vector((math.cos(b_) * L, math.sin(b_) * L, L * rng.uniform(0.35, 0.7)))
            mid = (q + e) / 2 + Vector((0, 0, L * 0.15))
            bp = branch(tuple(q), tuple(mid), tuple(e), tr * 0.24, tr * 0.07, 5)
            tips.append(e)
            for t2 in (0.55, 1.0):                            # twigs
                q2 = Vector(bp[int(t2 * (len(bp) - 1))])
                c_ = b_ + rng.uniform(-1.2, 1.2)
                L2 = L * rng.uniform(0.35, 0.55)
                e2 = q2 + Vector((math.cos(c_) * L2, math.sin(c_) * L2, L2 * rng.uniform(0.2, 0.6)))
                branch(tuple(q2), tuple((q2 + e2) / 2 + Vector((0, 0, 0.1))), tuple(e2), tr * 0.08, tr * 0.03, 4)
                tips.append(e2)
    cam = Vector((0.0, -0.62, 0.78))                          # towards the game's camera
    spots = []
    for tp in tips:                                          # clusters round the branches' ends
        for _ in range(4):
            spots.append(tp + Vector((rng.gauss(0, 1.4), rng.gauss(0, 1.4), rng.gauss(0.4, 1.0))))
    for _ in range(110):                                     # and over the dome of the crown
        a = rng.uniform(0, 2 * math.pi)
        el = rng.uniform(-0.25, 1.0)
        u = math.cos(el * math.pi / 2)
        spots.append(Vector((x + 0.3 + cr[0] * 0.92 * u * math.cos(a), y + cr[1] * 0.92 * u * math.sin(a),
                             cz + cr[2] * 0.95 * math.sin(el * math.pi / 2))))
    spots.sort(key=lambda p: p.y)                            # (no effect on the game: cut-outs need no sorting)
    for p in spots:
        rel = (p.z - (cz - cr[2])) / (2 * cr[2]) + 0.25 * (p.y - y) / cr[1] * -1
        m = 'leafS0' if rel < 0.38 else ('leafS2' if rel > 0.72 else 'leafS1')
        yaw = math.radians(rng.uniform(-40, 40))
        f = Vector((cam.x * math.cos(yaw) - cam.y * math.sin(yaw), cam.x * math.sin(yaw) + cam.y * math.cos(yaw), cam.z))
        sz = rng.uniform(4.6, 6.6)
        card(b, m, tuple(p), tuple(f), sz, sz, roll=rng.uniform(-30, 30))


# ----------------------------------------------------------------------------------------------- static part
def build(b, eye=False):
    b.normal_fn = normals
    b.tiny_px = 0
    b.ao_distance = 4.0
    land_palette()
    blib.SKIRT_MAT[0] = 'earth'
    X0, X1, Y0, Y1 = -HEX, HEX, -HEX / 0.866, HEX / 0.866
    blib.terrain(b, height, X0, X1, Y0, Y1, 108, 126, ground_mat,
                 keep=lambda x, y: hex_dist(x, y) > 0.3 and height(x, y) > -0.1, smooth=True, skirt=FLOOR - 1.0)
    hd = BAG
    L = Local(b, M_of(hd))
    W, c = hd['W'], hd['c']
    # the curved front of field stone
    n, nz = 44, 12
    v, f = [], []
    for i in range(n + 1):
        l = -W + 2 * W * i / n
        top = wall_top(l)
        for k in range(nz + 1):
            v.append((l, c * l * l, -0.6 + (top + 0.6) * k / nz))
    for i in range(n):
        for k in range(nz):
            a = i * (nz + 1) + k
            f.append((a, a + nz + 1, a + nz + 2, a + 1))
    L.add(v, oriented(v, f, (0, -1, 0)), 'stone', smooth=True)
    # the turf lip: a thick rounded edge of sod hanging over the top of the front
    P = [(l, c * l * l - 0.35, wall_top(max(-W, min(W, l))) + 0.05) for l in [-W - 0.6 + (2 * W + 1.2) * i / 48
                                                                                for i in range(49)]]
    tube(L, 'grass', P, [1.2] * len(P), n=8, tip=False)
    for e in (-1, 1):                                       # rough stone ends where the front meets the banks
        l = e * W
        for k in range(5):
            blob(L, 'stone', l + e * 0.45, c * l * l - 0.3 + 0.6 * k, 0.7 + 2.2 * k, 1.6, n=7, rings=4, squash=0.8,
                 jitter=0.25)
    # the doorstep, the arch of stones round the door and round the windows
    slab_xz(L, 'dstone', [(-4.5, -0.8), (4.5, -0.8), (4.5, 0.35), (-4.5, 0.35)], -0.05, 2.2)
    ring(L, 'dstone', DOOR_R + 0.5, DOOR_R + 1.95, 0.0, 0.3, n=23, M=T(0, 0.02, DOOR_ZC, rx=90))
    for e in (-1, 1):
        ring(L, 'dstone', WIN_R + 0.45, WIN_R + 1.25, 0.0, 0.2, n=17,
             M=T(e * WIN_X, c * WIN_X ** 2 - 0.03, WIN_Z, rz=win_turn(e), rx=90))
    # stepping stones from the door to the gate
    path = path_pts()
    for i in range(0, len(path), 2):
        x, y = path[i]
        r = 1.15 + 0.15 * math.sin(i * 1.7)
        lathe(b, 'dstone', [(0.0, 0.0), (r, 0.0), (r * 0.92, 0.16), (0.0, 0.19)], 9, x, y, ground(x, y) - 0.08,
              smooth=False)
    # the chimney on the hill's shoulder
    cl, cb, ch = CHIM
    x, y = to_world(hd, cl, cb)
    z = raw_h(x, y)
    lathe(b, 'brick', [(1.6, -2.0), (1.6, ch * 0.6), (1.3, ch), (1.6, ch + 0.05), (1.6, ch + 0.7),
                       (1.15, ch + 0.7), (0.0, ch + 0.7)], 12, x, y, z, smooth=False)
    cyl(b, 'brick', x, y, z + ch + 0.7, 0.6, 1.0, n=10)
    # tufts of long grass over the hill and the garden
    grass_tufts(b, random.Random(1954), TUFTS)


# ----------------------------------------------------------------------------------------------- skinned part
def build_eye(b):
    b.normal_fn = normals
    b.tiny_px = TINY_PX
    life_palette()
    rng = random.Random(1937)
    hd = BAG
    L = Local(b, M_of(hd))
    W, c = hd['W'], hd['c']
    round_door(L, 0.0, DOOR_ZC, DOOR_R)
    for e in (-1, 1):
        Wn = Local(b, M_of(hd) @ T(e * WIN_X, c * WIN_X ** 2 - 0.05, 0.0, rz=win_turn(e)))   # along the wall
        round_window(Wn, 0.0, 0.0, WIN_Z, WIN_R)
        box(Wn, 'timber', 0.0, -0.65, WIN_Z - WIN_R - 1.55, 5.1, 1.05, 0.4)                     # the sill
    # the great tree on the hill above the door, its roots running down over the turf
    tx, ty = to_world(hd, *TREE)
    great_tree(b, rng, tx, ty, raw_h(tx, ty), 24.0, 12.0)
    # the garden: sunflowers by the windows, clumps of flowers along the wall
    for (l, yy, hg) in ((-16.5, -2.7, 8.7), (-18.4, -5.1, 7.2), (-15.0, -5.1, 9.6), (16.5, -3.0, 8.1),
                        (18.3, -5.4, 9.3)):
        sunflower(Local(b, M_of(hd) @ T(l, yy, lground(l, yy), s=1.5)), rng, 0.0, 0.0, 0.0, hg / 1.5)
    for l in (-8.4, -6.9, 7.2, 8.7, -17.4, 17.7, -5.4, 5.7):
        m = rng.choice(('flowR', 'flowY', 'flowP', 'flowW'))
        blob(L, m, l, c * l * l - 1.35, -0.15, rng.uniform(1.05, 1.4), n=8, rings=4, squash=0.6, jitter=0.3)
    picket_fence(b)
    # Bilbo and Gandalf on the grass before the door
    for spot, fn in ((BILBO, bilbo), (GANDALF, gandalf)):
        fn(Local(b, fig_M(spot)))


def fig_M(spot):
    fx, fy_, rz = spot
    return M_of(BAG) @ T(fx, fy_, lground(fx, fy_) - 0.02, rz=rz) @ T(s=FIG_S)


# ----------------------------------------------------------------------------------------------- the figures
# Built facing -Y (towards the camera), origin = where they sit on the grass, z up.
def limb(b, mat, pts, radii, n=8, tip=False):
    P = spline(pts, 3 * (len(pts) - 1))
    r = [radii[0] + (radii[-1] - radii[0]) * i / (len(P) - 1) for i in range(len(P))]
    tube(b, mat, P, r, n=n, tip=tip)


def pipe(b, mouth, bowl, stem=0.035):
    mid = ((mouth[0] + bowl[0]) / 2, (mouth[1] + bowl[1]) / 2, min(mouth[2], bowl[2]) - 0.08)
    limb(b, 'pipe', [mouth, mid, bowl], [stem, stem * 1.2], n=5)
    lathe(b, 'pipe', [(0.0, 0.0), (0.08, 0.02), (0.11, 0.1), (0.12, 0.24), (0.09, 0.24), (0.0, 0.2)], 10, *bowl,
          smooth=True)
    cyl(b, 'ember', bowl[0], bowl[1], bowl[2] + 0.19, 0.085, 0.04, n=8)


GANDALF_BOWL = (-0.38, -1.45, 2.0)
BILBO_BOWL = (-0.22, -0.72, 1.12)


def gandalf(b):
    """Gandalf the Grey sitting on the grass: legs stretched out under the grey robe, the blue-grey cloak spread
    behind him on the ground, his long beard, the tall pointed hat with its wide brim and bent tip, the long pipe at
    his mouth in his right hand, the left hand on his knee, the staff leaning on his left shoulder."""
    folds = (lambda a: 1.0 + 0.06 * math.cos(7 * a))
    # the cloak, spread on the grass behind him and over his shoulders
    loft(b, 'g_cloak', [(0, 0.75, 0.04, 1.15, 0.6, folds), (0, 0.55, 0.6, 0.95, 0.48, folds),
                        (0, 0.4, 1.5, 0.82, 0.42, folds), (0, 0.32, 2.15, 0.78, 0.38, None),
                        (0, 0.28, 2.35, 0.5, 0.3, None)], n=20)
    # the body in the robe, leaning back a little
    loft(b, 'g_robe', [(0, 0.1, 0.05, 0.85, 0.72, folds), (0, 0.1, 0.5, 0.8, 0.62, folds),
                       (0, 0.14, 1.2, 0.64, 0.46, None), (0, 0.2, 1.8, 0.66, 0.44, None),
                       (0, 0.24, 2.15, 0.7, 0.42, None), (0, 0.24, 2.38, 0.36, 0.3, None)], n=18)
    # legs stretched out, knees a little up; the robe draped over them; boots
    for e in (-1, 1):
        limb(b, 'g_robe', [(e * 0.36, -0.1, 0.38), (e * 0.4, -1.3, 0.82), (e * 0.4, -2.35, 0.34)], [0.42, 0.3], n=10)
        loft(b, 'boot', [(e * 0.4, -2.45, 0.05, 0.2, 0.32, None), (e * 0.4, -2.5, 0.35, 0.2, 0.3, None),
                         (e * 0.4, -2.55, 0.5, 0.12, 0.2, None)], n=8)
    # arms: the right raises the long pipe to his mouth, the left rests on his knee
    limb(b, 'g_robe', [(-0.66, 0.22, 2.1), (-0.85, -0.3, 1.45), (-0.32, -0.62, 2.02)], [0.22, 0.34], n=9)
    blob(b, 'skin', -0.24, -0.68, 1.98, 0.13, n=8, rings=4, squash=1.1, jitter=0.0)
    limb(b, 'g_robe', [(0.66, 0.22, 2.1), (0.86, -0.4, 1.35), (0.5, -1.15, 1.02)], [0.22, 0.34], n=9)
    blob(b, 'skin', 0.45, -1.32, 0.92, 0.14, n=8, rings=4, squash=0.8, jitter=0.0)
    pipe(b, (-0.02, -0.4, 2.52), GANDALF_BOWL)
    # the head, the beard and the long grey hair
    loft(b, 'skin', [(0, 0.0, 2.36, 0.2, 0.22, None), (0, -0.01, 2.55, 0.25, 0.27, None),
                     (0, 0.0, 2.78, 0.26, 0.28, None), (0, 0.02, 2.95, 0.2, 0.22, None)], n=14)
    box(b, 'skin', 0, 0, -0.07, 0.08, 0.14, 0.2, M=T(0.0, -0.28, 2.66))                 # the nose
    box(b, 'g_beard', 0, 0, -0.03, 0.4, 0.09, 0.07, M=T(0.0, -0.25, 2.78))               # brows
    beard = (lambda a: 1.0 + 0.1 * math.cos(9 * a))
    loft(b, 'g_beard', [(0, -0.42, 1.45, 0.05, 0.04, None), (0, -0.44, 1.75, 0.2, 0.1, beard),
                        (0, -0.4, 2.1, 0.3, 0.14, beard), (0, -0.3, 2.42, 0.3, 0.15, beard),
                        (0, -0.18, 2.6, 0.27, 0.15, beard)], n=14)
    loft(b, 'g_beard', [(0, 0.3, 1.95, 0.42, 0.12, None), (0, 0.24, 2.35, 0.42, 0.18, None),
                        (0, 0.1, 2.8, 0.32, 0.26, None), (0, 0.04, 2.95, 0.25, 0.25, None)], n=14)
    # the hat: a wide brim, the tall cone bending back at its tip
    lathe(b, 'g_hat', [(0.0, 0.0), (0.98, -0.04), (1.0, 0.0), (0.4, 0.07), (0.0, 0.07)], 24, 0.0, 0.02, 2.9,
          smooth=True)
    tube(b, 'g_hat', spline([(0.0, 0.02, 2.92), (0.0, 0.06, 3.35), (0.0, 0.14, 3.85), (0.04, 0.34, 4.3),
                             (0.1, 0.7, 4.55)], 12),
         [0.4, 0.38, 0.35, 0.31, 0.27, 0.23, 0.19, 0.15, 0.11, 0.08, 0.05, 0.03, 0.02], n=12)
    # the staff, leaning on his left shoulder
    limb(b, 'timber', [(1.2, -0.05, 0.0), (1.08, 0.2, 2.2), (0.95, 0.42, 4.35)], [0.07, 0.055], n=6)
    blob(b, 'timber', 0.93, 0.44, 4.3, 0.15, n=7, rings=4, squash=1.2, jitter=0.3)


def bilbo(b):
    """Bilbo sitting on the grass, knees up: white shirt with full sleeves, the red waistcoat, brown breeches to the
    knee, bare hairy feet, curly brown hair, his pipe in his right hand."""
    for e in (-1, 1):
        limb(b, 'b_breech', [(e * 0.2, 0.0, 0.25), (e * 0.24, -0.38, 0.6), (e * 0.26, -0.66, 0.82)], [0.17, 0.14],
             n=8)
        limb(b, 'skin', [(e * 0.26, -0.68, 0.8), (e * 0.27, -0.85, 0.45), (e * 0.28, -0.95, 0.15)], [0.1, 0.085],
             n=7)
        loft(b, 'skin', [(e * 0.28, -0.95, 0.02, 0.12, 0.2, None), (e * 0.28, -1.05, 0.12, 0.13, 0.22, None),
                         (e * 0.28, -1.1, 0.2, 0.09, 0.15, None)], n=8)          # the big hobbit feet
        blob(b, 'b_hair', e * 0.28, -1.02, 0.15, 0.1, n=6, rings=3, squash=0.6, jitter=0.4)   # ...and their hair
    loft(b, 'b_breech', [(0, 0.02, 0.05, 0.36, 0.32, None), (0, 0.02, 0.32, 0.38, 0.3, None)], n=12)
    loft(b, 'b_coat', [(0, 0.03, 0.3, 0.37, 0.29, None), (0, 0.04, 0.7, 0.36, 0.27, None),
                       (0, 0.06, 1.02, 0.36, 0.25, None)], n=14)                  # the waistcoat
    loft(b, 'b_shirt', [(0, 0.06, 1.0, 0.35, 0.24, None), (0, 0.07, 1.16, 0.38, 0.24, None),
                        (0, 0.07, 1.25, 0.18, 0.15, None)], n=14)
    box(b, 'b_shirt', 0, 0, -0.06, 0.2, 0.06, 0.32, M=T(0.0, -0.22, 1.02))             # the open collar
    for pts in ([(-0.34, 0.07, 1.15), (-0.46, -0.22, 0.78), (-0.16, -0.4, 1.12)],
                [(0.34, 0.07, 1.15), (0.44, -0.3, 0.8), (0.27, -0.66, 0.9)]):
        limb(b, 'b_shirt', pts, [0.13, 0.15], n=8)
    blob(b, 'skin', -0.14, -0.45, 1.1, 0.08, n=6, rings=4, squash=1.1, jitter=0.0)
    blob(b, 'skin', 0.25, -0.73, 0.86, 0.08, n=6, rings=4, squash=1.0, jitter=0.0)
    loft(b, 'skin', [(0, 0.0, 1.23, 0.12, 0.13, None), (0, -0.01, 1.35, 0.2, 0.21, None),
                     (0, 0.0, 1.52, 0.21, 0.22, None), (0, 0.01, 1.66, 0.16, 0.17, None)], n=12)
    box(b, 'skin', 0, 0, -0.04, 0.06, 0.08, 0.1, M=T(0.0, -0.22, 1.47))
    for e in (-1, 1):                                                             # pointed ears
        blib.strut(b, 'skin', (e * 0.19, 0.02, 1.47), (e * 0.29, 0.06, 1.6), 0.05, 0.0, n=5)
    rng = random.Random(3)
    for k in range(16):                                                           # the curls
        a = 2 * math.pi * k / 16
        zz = 1.5 + 0.17 * rng.uniform(0.3, 1.0)
        rr = 0.17 if zz > 1.58 else 0.2
        blob(b, 'b_hair', rr * math.cos(a), 0.03 + rr * math.sin(a) * 0.95 + (0.04 if math.sin(a) > 0 else 0.0), zz,
             0.08, n=6, rings=3, squash=1.0, jitter=0.35)
    blob(b, 'b_hair', 0.0, 0.03, 1.6, 0.18, n=8, rings=4, squash=0.6, jitter=0.25)
    pipe(b, (-0.02, -0.21, 1.42), BILBO_BOWL, stem=0.028)


# ----------------------------------------------------------------------------------------------- rig
def glow_frame():
    hd = BAG
    return (hd['x'], win_light_y(), hd['z'] + WIN_Z), (hd['x'] - WIN_X - WIN_R - 2.0,
                                                                           hd['x'] + WIN_X + WIN_R + 2.0,
                                                                           hd['z'] + WIN_Z - WIN_R - 2.0,
                                                                           hd['z'] + WIN_Z + WIN_R + 2.0)


def glow_lines():
    hd = BAG
    return [(hd['x'] + e * WIN_X, hd['z'] + WIN_Z - 0.01, hd['x'] + e * WIN_X, hd['z'] + WIN_Z + 0.01, WIN_R * 1.3)
            for e in (-1, 1)]


def smoke_spots():
    """The chimney's pot: continuous smoke (bone, position, effect key)."""
    cl, cb, ch = CHIM
    x, y = to_world(BAG, cl, cb)
    return [('smoke0', (x, y, raw_h(x, y) + ch + 1.8), 'CHIMNEY_SMOKE')]


def mouth(who):
    from mathutils import Vector
    return tuple(fig_M(GANDALF if who == 'gandalf' else BILBO) @ Vector(MOUTHS[who]))


def puff_cards(k):
    """[(half size, fn(t) -> FILE-unit position relative to the effect's bone, yaw_fn(t) -> degrees)]: six cards per
    friend. Each puff: the cards open from edge-on slivers in a small cluster before the face (staggered by 40 ms),
    drift apart, up and a little downwind, and close to slivers again between 0.9 s and PUFF_LIFE (each at its own
    time). A card is edge-on (90 degrees: no width from the game's camera) whenever it is not puffing, and it travels
    between its hiding place deep under the ground and a puff only while edge-on, PARK s before and after the puff,
    so nothing visible ever crosses between the ground and the faces (v6: "the smoke rushes to the ground")."""
    PARK = 0.6
    bx, by = PUFF_FX
    bz = ground(bx, by)
    cards = []
    for who, s in (('gandalf', 1.0), ('bilbo', 0.68)):
        mx, my, mz = mouth(who)
        for c in range(6):
            a = 2 * math.pi * c / 6 + (0.5 if who == 'bilbo' else 0.0)
            ox, oz = math.cos(a), math.sin(a) * 0.8                # a ring of wisps round the cloud's middle
            t_on = 0.04 * c
            t_off = 0.9 + (PUFF_LIFE - 0.9) * ((c * 4) % 6) / 5.0   # vanish order scrambled
            hidden = (mx - bx, my - by, -30.0)

            def path(u, mx=mx, my=my, mz=mz, ox=ox, oz=oz, s=s, c=c):
                w = u / PUFF_LIFE
                spread = (0.45 + 1.9 * math.sqrt(w)) * s
                x = mx + ox * spread + 1.2 * s * w                     # downwind, to the east
                y = my - 0.3 * s - 0.5 * s * w - 0.02 * c              # a little towards the camera
                z = mz + 0.4 * s + oz * spread + 3.0 * s * w ** 0.8    # rising
                return x, y, z

            def phase(t, who=who):
                """(u = time into the puff, or None) for the puff whose window (with its parking margins) holds t."""
                for t0 in PUFF_TIMES[who]:
                    for base in (t0, t0 - LOOP, t0 + LOOP):            # puffs late in the loop run over its start
                        u = t - base
                        if -PARK <= u <= PUFF_LIFE + PARK:
                            return u
                return None

            def fn(t, path=path, phase=phase, t_on=t_on, t_off=t_off, hidden=hidden):
                u = phase(t)
                if u is None:
                    x, y, z = hidden[0] + bx, hidden[1] + by, hidden[2] + bz
                else:
                    x, y, z = path(min(max(u, t_on), t_off))           # parked at the start / the end, edge-on
                return ((x - bx) * k, (y - by) * k, (z - bz) * k)

            def yaw_fn(t, phase=phase, t_on=t_on, t_off=t_off):
                u = phase(t)
                return 0.0 if (u is not None and t_on <= u <= t_off) else 90.0

            cards.append(((1.45 if who == 'gandalf' else 1.0) * k, fn, yaw_fn))
    return cards


def preview_overlays(out_dir):
    """The puffs for the preview (in-game units, additive): each friend's cards half a second into a puff."""
    import dds
    img = dds.decode_dxt3(os.path.join(out_dir, 'MEC_BagEndPuffs_DIFF.dds'))
    bx, by = PUFF_FX
    bz = ground(bx, by)
    out = []
    for i, (hs, fn, _) in enumerate(puff_cards(1.0)):
        t = (PUFF_TIMES['gandalf'][0] if i < 6 else PUFF_TIMES['bilbo'][0]) + 0.5
        x, y, z = fn(t)
        if z < -5:
            continue
        x, y, z = x + bx, y + by, z + bz
        P = [(x - hs, y, z - hs), (x + hs, y, z - hs), (x + hs, y, z + hs), (x - hs, y, z + hs)]
        out.append((P, [(0, 1, 2, 3)], [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)], img))
    # the candlelight at 0.3 s into the loop (its width = its light)
    gimg = dds.decode_dxt3(os.path.join(out_dir, 'MEC_BagEndFlicker_DIFF.dds'))
    fx, fy, fz = flick_pos()
    for hs, fn, yaw_fn in flicker_cards(1.0):
        x, y, z = fn(0.3)
        x, y, z = x + fx, y + fy, z + fz
        wv = hs * math.cos(math.radians(yaw_fn(0.3)))
        P = [(x - wv, y, z - hs), (x + wv, y, z - hs), (x + wv, y, z + hs), (x - wv, y, z + hs)]
        out.append((P, [(0, 1, 2, 3)], [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)], gimg))
    return out


def candle(seed):
    """Brightness 0.3..1 of a candle in a window over the loop: slow breathing, quicker wavering, a fast shimmer and
    a few brief gutterings (frequencies rounded so the loop is seamless)."""
    rng = random.Random(seed)
    waves = [(round(rng.uniform(lo, hi) * LOOP) / LOOP, rng.uniform(0, 2 * math.pi), amp)
             for lo, hi, amp in ((0.25, 0.5, 0.06), (1.2, 2.2, 0.10), (4.0, 6.0, 0.07), (8.0, 11.0, 0.05))]
    dips = [(rng.uniform(0, LOOP), rng.uniform(0.25, 0.4), rng.uniform(0.08, 0.16)) for _ in range(4)]

    def b(t):
        v = 0.74 + sum(a * math.sin(2 * math.pi * f * t + p) for f, p, a in waves)
        for (t0, depth, w) in dips:
            d = min(abs(t - t0), LOOP - abs(t - t0))
            v -= depth * math.exp(-(d / w) ** 2)
        return min(1.0, max(0.3, v))
    return b


def flicker_cards(k):
    """[(half size, fn, yaw_fn)]: three warm glow layers before each window's panes (puffs.write). The width of a
    card is its light (additive): yaw = acos(brightness). The wide halo breathes slowly, the core flickers and drifts
    a little as a flame does; each window has its own candle."""
    hd = BAG
    bx, by, bz = flick_pos()
    out = []
    for e, seed in ((-1, 31), (1, 47)):
        wx, wy, wz = hd['x'] + e * WIN_X, win_light_y() - 0.1, hd['z'] + WIN_Z
        slow, fast = candle(seed), candle(seed + 1)
        for li, (hs, br, jig) in enumerate(((WIN_R * 1.5, slow, 0.0), (WIN_R * 1.05, fast, 0.08))):
            def fn(t, wx=wx, wy=wy, wz=wz, jig=jig, li=li, seed=seed):
                dz = jig * math.sin(2 * math.pi * round(1.3 * LOOP) / LOOP * t + seed)
                dx = jig * 0.6 * math.sin(2 * math.pi * round(0.7 * LOOP) / LOOP * t + 2 * seed)
                return ((wx + dx - bx) * k, (wy - 0.05 * li - by) * k, (wz + dz - bz) * k)

            def yaw_fn(t, br=br):
                return math.degrees(math.acos(br(t)))
            out.append((hs * k, fn, yaw_fn))
    return out


def flick_pos():
    hd = BAG
    return (hd['x'], win_light_y() - 0.1, hd['z'] + WIN_Z)


def model_effects(out_dir, k):
    """Our animated model effects besides the glow (build_models.py): the puffs of the pipes, the candlelight."""
    import puffs
    files = puffs.write(out_dir, 'MEC_BagEndPuffs', puff_cards(k), LOOP, tex_args=dict(strength=0.62))
    files += puffs.write(out_dir, 'MEC_BagEndFlicker', flicker_cards(k), LOOP, tex_fn=puffs.glow_texture,
                         yaw_spans=1200)
    return files


def rig():
    """Bones in in-game units: (name, parent, position, effect key or None)."""
    bones = [('fxglow', 'eyeroot', glow_frame()[0], 'WINDOW_GLOW')]
    for name, p, key in smoke_spots():
        bones.append((name, 'eyeroot', p, key))
    bones.append(('fxpuff', 'eyeroot', (PUFF_FX[0], PUFF_FX[1], ground(*PUFF_FX)), 'PIPE_PUFFS'))
    bones.append(('fxflick', 'eyeroot', flick_pos(), 'WINDOW_FLICKER'))
    return bones


def glow_effect(k):
    """The warm light of Bag End's windows (tools/landmarks/glow.py): one quad in FILE units."""
    pos, (X0, X1, Z0_, Z1) = glow_frame()
    return dict(name='MEC_BagEndGlow',
                quads=[((X0 - pos[0]) * k, (X1 - pos[0]) * k, (Z0_ - pos[2]) * k, (Z1 - pos[2]) * k, 0.0)],
                tex_args=dict(lines=glow_lines(), box=(X0, X1, Z0_, Z1), px=1024, color=(255, 170, 84), halo=0.1,
                              core=0.0, sigma=(0.3, 0.7)))


def _still(t):
    return 0.0


GAZE = dict(fn=_still, T=LOOP, spans=60)
EYE_C = (BAG['x'], BAG['y'], BAG['z'])

PREVIEW = [((0, -95, 80), (0, 0, 10), 34),                                         # the game's view
           ((7, -58, BAG['z'] + 20), (0, BAG['y'] - 7.0, BAG['z'] + 5.0), 40),     # Bag End and the two friends
           ((-58, -50, 50), (0, 0, 10), 32),                                        # from the south-west
           ((-13, -33, BAG['z'] + 9), (0, BAG['y'] - 8.0, BAG['z'] + 4.5), 40)]     # close: Bilbo and Gandalf
PREVIEW_EYE = [((3.0, -36.0, BAG['z'] + 8.0), (0.3, BAG['y'] - 8.0, BAG['z'] + 4.8), 42)]
