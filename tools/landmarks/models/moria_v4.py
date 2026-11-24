"""Moria v4, the West-gate of Khazad-dûm: the landmark of the Goblins' capital (an IMPROVEMENT, docs/LANDMARKS.md).

Built for the improvement path like Barad-dûr v5: authored in IN-GAME units (improvement Scale 0.25 with the
writer's x4), origin = tile centre, ground z = 0, -Y = south = towards the game camera; the hex is about +-34 to its
flat sides (E/W). The massif spills into the neighbouring hexes like a stock mountain range.

Lore and film cues (The Fellowship of the Ring, "A Journey in the Dark"; the 2001 film):
  * the Walls of Moria: sheer cliffs round a bay at the feet of the Misty Mountains, the three Mountains of Moria
    behind: Caradhras the Redhorn (red rock, snow), Celebdil the White / Zirakzigil (a silver spike) and
    Fanuidhol the Grey / Cloudyhead (broad, blue-grey);
  * the Doors of Durin on a smooth face at the back of the bay, drawn in shining ithildin: two pillars crowned with
    crescent moons, the arch with its band of Feanorian letters, the two trees of the Eldar under it, Durin's crown
    with the seven stars, the anvil and hammer, the star of the House of Feanor; a stone threshold before them;
  * two great holly trees flanking the doors ("their roots ran out to the water");
  * the dark lake of the dammed Sirannon in the bay, the Watcher in the Water's tentacles rising from it;
  * the old road along the shore, boulders and scree under the cliffs, pines on the lower slopes.

The ithildin glows two ways: a soft halo baked into the wall texture (as v3), and a real additive glow: a model
effect (tools/landmarks/glow.py) hung on a bone in front of the doors, drawn by the game's FX shader like the Eye's
beam. The Watcher's tentacles are the skinned part (they sway slowly about the lake's centre: GAZE), which also
carries the glow's bone.
"""
import math
import random

import blib
from blib import material, hexcol as h, box, cyl, terrain, blob, curve, prism, lathe, T

BAKE = True
BAKE_PX = 2048           # the massif (static part): DIFF 2048 / SREF 1024 (as Barad-dur v5)
EYE_PX = 2048            # the skinned part holds everything else (doors, trees, lake, rocks, the Watcher): 2048 too
EYE_AO = 24
PIVOT_MATS = {'tentacle', 'sucker'}  # only the Watcher sways; the rest of the skinned part is on the still bone
TINY_PX = 48             # UV islands smaller than this go on their material's swatch (bake.py)

HEX = 34.0
FLOOR = -1.0             # below the game's ground: what is lower is not modelled
DOOR_Y = 15.0            # the smooth wall of the doors (faces -Y)
RECESS = 12.8            # half-width of the niche the doors are cut in
Z0 = 1.0                 # top of the threshold = foot of the doors
LAKE = (-4.0, -17.0, 13.0, 7.0)      # the Watcher's lake: centre x, y, radii x, y
TOP = 80.0
EYE_C = (LAKE[0], LAKE[1], 0.0)      # pivot of the skinned part (the tentacles turn about the lake's centre)
GLOW_BOX = (-9.0, 9.0, Z0 - 1.0, Z0 + 25.6)   # the glow's quad (x0, x1, z0, z1) on the wall
GLOW_ZC = (GLOW_BOX[2] + GLOW_BOX[3]) / 2       # the glow's bone: in front of the doors' centre
PEAKS = [  # (x, y, height, radius, sharpness): Caradhras, Celebdil, Fanuidhol
    (4.0, 39.0, 36.0, 27.0, 1.45),
    (31.0, 31.0, 30.0, 17.0, 1.9),
    (-29.0, 33.0, 26.0, 24.0, 1.25),
]


# ----------------------------------------------------------------------------------------------- noise
def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def _hash(i, j, s):
    n = (i * 374761393 + j * 668265263 + s * 2147483647) & 0xffffffff
    n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
    return (n & 0xffff) / 65535.0


def vnoise(x, y, s=0):
    i, j = math.floor(x), math.floor(y)
    fx, fy = x - i, y - j
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b_ = _hash(i, j, s), _hash(i + 1, j, s)
    c, d = _hash(i, j + 1, s), _hash(i + 1, j + 1, s)
    return a + (b_ - a) * fx + (c - a) * fy + (a - b_ - c + d) * fx * fy


def fbm(x, y, octaves=4, s=0):
    tot, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        tot += amp * vnoise(x * 2 ** o, y * 2 ** o, s + o)
        norm += amp
        amp *= 0.5
    return tot / norm - 0.5          # about -0.5 .. 0.5


def ridged(x, y, octaves=5, s=0):
    """Ridged multifractal: sharp crests and gullies (arêtes), 0 .. 1."""
    tot, amp, norm, w = 0.0, 1.0, 0.0, 1.0
    for o in range(octaves):
        n = 1.0 - abs(2.0 * vnoise(x * 2 ** o + 0.37 * o, y * 2 ** o - 0.21 * o, s + o) - 1.0)
        n = n * n * w
        w = min(1.0, n * 1.6)
        tot += amp * n
        norm += amp
        amp *= 0.5
    return tot / norm


# ----------------------------------------------------------------------------------------------- the land
def bay_d(x, y):
    """Signed distance-like field: < 0 in the open bay (game ground shows), > 0 in the rock."""
    if y <= 4.0:
        du = abs(x) - (15.0 + 0.3 * (4.0 - y))
    else:
        du = (math.hypot(x / 15.0, (y - 4.0) / 8.0) - 1.0) * 10.0
    # buttresses and gullies along the walls (the outline wobbles; a height field's cliffs are its outline)
    du += (3.2 * fbm(x * 0.1, y * 0.1, 3, 4) + 1.4 * fbm(x * 0.38, y * 0.38, 3, 5)) * \
        smooth((abs(x) - RECESS - 1.0) / 3.0)
    dr = max(y - DOOR_Y, abs(x) - RECESS)            # the niche of the doors
    return min(du, dr)


def cliff_top(x, y):
    return 7.0 + 25.0 * smooth((y + 30.0) / 44.0) + 3.0 * fbm(x * 0.08, y * 0.08, 4, 21)


def footprint(x, y):
    """1 inside the massif, falling to 0 at its ragged outline (a rounded box +-54 x -36..56)."""
    e = ((abs(x) / 54.0) ** 3 + (abs(y - 10.0) / 46.0) ** 3) ** (1.0 / 3.0)
    e += 0.12 * fbm(x * 0.06, y * 0.06, 3, 8)
    return smooth((1.0 - e) / 0.4) ** 0.8


def height(x, y):
    d = bay_d(x, y)
    in_niche = abs(x) < RECESS + 2.5 and y > DOOR_Y - 9.0
    # scree under the cliffs (none in the doors' niche: the threshold is clear)
    S = (3.4 + 1.6 * fbm(x * 0.2, y * 0.2, 3, 31)) * smooth((abs(x) - RECESS + 1.0) / 3.0 if y > 2 else 1.0)
    scree = FLOOR + (S - FLOOR) * smooth((d + 4.5) / 4.5)
    ct = cliff_top(x, y)
    rise = smooth(d / (0.9 if in_niche else 1.4 + 2.4 * (0.5 + fbm(x * 0.07, y * 0.07, 2, 71))))
    z = ct * rise
    # the mountains above and behind the walls
    up = 14.0 * smooth((y - 8.0) / 30.0)
    for (px, py, ph, pr, ps) in PEAKS:
        wx = px + 4.0 * fbm(y * 0.05, x * 0.05, 2, 41)
        r = math.hypot(x - wx, (y - py) * 1.15)
        th = math.atan2(y - py, x - wx)
        spur = 1.0 + 0.3 * math.cos(5.0 * th + 3.0 * fbm(x * 0.04, y * 0.04, 2, 43)) * smooth(r / 6.0)
        up += ph * max(0.0, 1.0 - r / (pr * spur)) ** ps
    beyond = smooth((d - 1.5) / 16.0)
    z += up * beyond
    # relief: domain-warped arêtes and gullies, then finer crags; stronger higher up
    m = smooth(z / 16.0)
    wx_, wy_ = x + 7.0 * fbm(x * 0.03, y * 0.03, 3, 51), y + 7.0 * fbm(y * 0.03, x * 0.03, 3, 52)
    z += (17.0 * ridged(wx_ * 0.05, wy_ * 0.05, 5, 3) - 6.5) * m * beyond
    z += (4.0 * ridged(wx_ * 0.16, wy_ * 0.16, 4, 61) - 1.6) * m * (0.25 + 0.75 * beyond)
    z += 1.5 * fbm(x * 0.6, y * 0.6, 3, 13) * m
    # ledges: rock strata stepped into the cliffs
    if z > 2.0:
        st = 2.7
        t = z / st
        ter = (math.floor(t) + smooth((t - math.floor(t)) * 1.6)) * st
        z += (ter - z) * 0.5 * (1.0 - beyond * 0.6)
    z = max(z, scree)
    if z > TOP - 10.0:
        z = TOP - 10.0 + 10.0 * math.tanh((z - TOP + 10.0) / 10.0)
    return FLOOR + (z - FLOOR) * footprint(x, y)


# ----------------------------------------------------------------------------------------------- the doors
# the doors' layout (in-game units on the wall): pillars at +-PX, PH high, the arch round (0, AZ) with radius AR
PX, PH = 6.6, 15.0
AZ = Z0 + PH + 1.0
AR = PX + 0.4


def door_lines():
    """The Doors of Durin as ithildin line segments on the wall: [(x0, z0, x1, z1, width)] in in-game units.

    After the film and Tolkien's own drawing (The Fellowship of the Ring, book II ch. 4): two tall pillars crowned
    with crescent moons; a horseshoe arch carrying a band of Feanorian letters; under it Durin's crown with the seven
    stars in an arc above it and the anvil and hammer below it; the two trees of the High-elves rising inside the
    pillars, their branches fanning up and inwards with crescent leaves; the many-rayed star of the House of Feanor
    in the middle. Strokes are bold (0.4 - 0.75) so the picture still reads at the landmark's in-game size; the
    letters and leaves are fine strokes that only glow (too small to model)."""
    L = []

    def line(x0, za, x1, zb, w):
        if math.hypot(x1 - x0, zb - za) > 1e-6:
            L.append((x0, za, x1, zb, w))

    def arc(cx, cz, r, a0, a1, n, w):
        for k in range(n):
            p0 = math.radians(a0 + (a1 - a0) * k / n)
            p1 = math.radians(a0 + (a1 - a0) * (k + 1) / n)
            line(cx + r * math.cos(p0), cz + r * math.sin(p0), cx + r * math.cos(p1), cz + r * math.sin(p1), w)

    def path(pts, w):
        for a, b_ in zip(pts, pts[1:]):
            line(a[0], a[1], b_[0], b_[1], w)

    # --- the pillars: shaft, bases, crescent-moon capitals
    for s in (-1, 1):
        line(s * PX, Z0 + 0.9, s * PX, Z0 + PH, 0.72)
        for k, (hw, zz) in enumerate(((1.1, Z0 + 0.25), (0.85, Z0 + 0.75))):
            line(s * PX - hw, zz, s * PX + hw, zz, 0.34)
        line(s * PX - 0.85, Z0 + PH + 0.1, s * PX + 0.85, Z0 + PH + 0.1, 0.3)          # abacus
        arc(s * PX, Z0 + PH + 1.25, 1.05, 198, 342, 14, 0.42)                         # the crescent, horns up
        arc(s * PX, Z0 + PH + 1.5, 0.62, 215, 325, 8, 0.16)
    # --- the arch and its band of letters
    arc(0.0, AZ, AR, 0, 180, 56, 0.72)
    arc(0.0, AZ, AR - 1.45, 4, 176, 48, 0.3)
    rng = random.Random(7)
    n = 34
    for k in range(n):                       # Tengwar-like glyphs: a stem (telco) with one or two bows (luva)
        a = math.radians(10 + 160 * (k + 0.5) / n)
        c, s_ = math.cos(a), math.sin(a)
        tx, tz = -s_, c                      # along the band (anticlockwise)
        r0, r1 = AR - 1.2, AR - 0.35

        def P(r, t):
            return (r * c + t * tx, AZ + r * s_ + t * tz)
        kind = rng.randrange(4)
        stem = (r0 - 0.15, r1) if kind == 3 else (r0, r1 - 0.2)
        path([P(stem[0], 0.0), P(stem[1], 0.0)], 0.12)
        nb = 1 if kind < 2 else 2
        side = 1 if kind % 2 == 0 else -1
        for j in range(nb):
            rr = r0 + 0.22 + 0.38 * j
            path([P(rr, 0.0), P(rr + 0.12, 0.17 * side), P(rr + 0.3, 0.2 * side), P(rr + 0.42, 0.06 * side)], 0.11)
        if rng.random() < 0.35:              # a tehta above
            path([P(r1 - 0.02, -0.1), P(r1 + 0.1, 0.12)], 0.09)
    # --- the two trees: trunks inside the pillars, branches fanning up and inwards, crescent leaves
    for s in (-1, 1):
        x = s * 3.5
        line(x, Z0 + 0.4, x, Z0 + 14.2, 0.42)
        for k in range(7):
            z = Z0 + 4.0 + 1.45 * k
            reach_in = 2.6 - 0.22 * k             # towards the middle, then up
            pts_in = [(x, z), (x - s * reach_in * 0.55, z + 0.55), (x - s * reach_in * 0.9, z + 1.35),
                      (x - s * reach_in, z + 2.3)]
            path(pts_in, 0.24)
            pts_out = [(x, z + 0.5), (x + s * 1.0, z + 1.0), (x + s * 1.5, z + 1.9)]      # towards the pillar
            path(pts_out, 0.2)
            for (bx, bz), up in ((pts_in[-1], 1), (pts_out[-1], 1), (pts_in[1], 0)):    # crescent leaves
                arc(bx - s * 0.05, bz + 0.35 * up + 0.25, 0.3, 200 if s > 0 else -20, 340 if s > 0 else 120, 4, 0.1)
        arc(x, Z0 + 14.2, 0.8, 30, 150, 6, 0.18)                                       # the crown of the tree
    # --- Durin's crown, the seven stars above it, the anvil and hammer below it
    CZ = AZ + 0.8
    line(-1.4, CZ, 1.4, CZ, 0.42)
    path([(-1.4, CZ), (-1.5, CZ + 1.1), (-0.75, CZ + 0.55), (0.0, CZ + 1.35), (0.75, CZ + 0.55), (1.5, CZ + 1.1),
          (1.4, CZ)], 0.26)
    for k in range(7):
        a = math.radians(32 + 116 * k / 6)
        sx, sz = 3.7 * math.cos(a), CZ + 0.2 + 3.15 * math.sin(a)
        for r in range(4):
            q = math.pi * r / 4
            ln = 0.48 if r % 2 == 0 else 0.3
            line(sx - ln * math.cos(q), sz - ln * math.sin(q), sx + ln * math.cos(q), sz + ln * math.sin(q),
                 0.2 if r % 2 == 0 else 0.12)
    AV = CZ - 1.3
    line(-1.0, AV, 1.0, AV, 0.36)                                     # anvil: face, waist, foot
    line(-0.3, AV - 0.45, 0.3, AV - 0.45, 0.28)
    line(-0.75, AV - 0.9, 0.75, AV - 0.9, 0.3)
    line(0.85, AV + 0.35, 1.6, AV + 1.15, 0.16)                       # hammer: handle and head
    line(1.3, AV + 1.45, 1.95, AV + 0.85, 0.32)
    # --- the star of the House of Feanor: 8 long rays, 8 shorter, 16 fine; a small bright heart (no ring)
    SZ = Z0 + 8.6
    for k in range(32):
        a = math.pi * k / 16
        if k % 4 == 0:
            r, w = 2.7, 0.4
        elif k % 2 == 0:
            r, w = 1.75, 0.24
        else:
            r, w = 1.05, 0.11
        line(0.18 * math.cos(a), SZ + 0.18 * math.sin(a), r * math.cos(a), SZ + r * math.sin(a), w)
    # --- where the two leaves of the doors meet, below the star
    line(0.0, Z0 + 0.4, 0.0, SZ - 3.0, 0.12)
    return L


# ----------------------------------------------------------------------------------------------- materials
def palette():
    rock_z = [(FLOOR, h('57554d')), (6.0, h('5f5a52')), (18.0, h('6a655e')), (34.0, h('76726c')),
              (52.0, h('8c8985')), (TOP, h('a3a19e'))]
    material('rock', h('68625a'), h('4b4740'), zramp=rock_z, slope_color=h('4c4843'), slope_start=0.6)
    blib.PALETTE['rock'].update(scale=0.09, strata=0.55, strata_amp=0.1, cracks=0.3, zjitter=0.05, cavity=0.45,
                                moss=(h('4e5a35'), 14.0),
                                tints=[(4.0, 42.0, 20.0, h('8a4c3c'), 0.7),       # Caradhras the Redhorn
                                       (31.0, 31.0, 13.0, h('a3abb5'), 0.55),     # Celebdil the White
                                       (-29.0, 33.0, 17.0, h('5d6672'), 0.5)],    # Fanuidhol the Grey
                                snow=(36.0, 45.0, 0.38))
    # the dressed face of the doors: smooth dark grey stone, the ithildin's halo painted on it
    material('wall', h('45433f'), h('383633'))
    blib.PALETTE['wall'].update(scale=0.12, strata=0.6, strata_amp=0.07, cracks=0.18, glow=True,
                                glow_color=h('9fdcff'), uv_boost=2.6)
    material('ithildin', h('e9f8ff'), spec=1.0, refl=255, ao=False)
    blib.PALETTE['ithildin'].update(solid=True)
    material('stone', h('66625b'), h('4f4b45'))
    blib.PALETTE['stone'].update(scale=0.5, cracks=0.6)
    material('boulder', h('67625a'), h('4a4640'), slope_color=h('514d47'), slope_start=0.7)
    blib.PALETTE['boulder'].update(scale=0.3, cracks=0.35, moss=(h('4e5a35'), 1.2))
    material('lake', h('0d1916'), h('16241f'), spec=0.9, refl=140, ao=False)
    blib.PALETTE['lake'].update(scale=0.22)
    material('holly', h('1a381c'), h('2b5428'), spec=0.5, refl=40)
    blib.PALETTE['holly'].update(scale=0.9)
    material('berry', h('b3121a'), spec=0.6, ao=False)
    blib.PALETTE['berry'].update(solid=True)
    material('bark', h('46382b'), h('2e241b'))
    blib.PALETTE['bark'].update(scale=1.5)
    material('pine', h('1d3322'), h('2d4a30'))
    blib.PALETTE['pine'].update(scale=1.1)


def watcher_palette():
    material('tentacle', h('3e4733'), h('242b1e'), spec=0.7, refl=60)
    blib.PALETTE['tentacle'].update(scale=0.9)
    material('sucker', h('a59c7c'), spec=0.4)
    blib.PALETTE['sucker'].update(solid=True)


# ----------------------------------------------------------------------------------------------- the model
def tube(b, mat, pts, radii, n=10, tip=True):
    """A smooth swept tube through pts (shared vertices, no seams between segments); the end closes in a point."""
    import mathutils
    V = [mathutils.Vector(p) for p in pts]
    verts, faces = [], []
    prev = None
    for i, p in enumerate(V):
        t = (V[min(i + 1, len(V) - 1)] - V[max(i - 1, 0)]).normalized()
        if prev is None:
            a = t.orthogonal().normalized()
        else:   # parallel transport: no twisting
            a = (prev - t * prev.dot(t)).normalized()
        prev = a
        c = t.cross(a)
        for j in range(n):
            ang = 2 * math.pi * j / n
            verts.append(tuple(p + radii[i] * (math.cos(ang) * a + math.sin(ang) * c)))
    for i in range(len(V) - 1):
        for j in range(n):
            a0, a1 = i * n + j, i * n + (j + 1) % n
            faces.append((a0, a1, a1 + n, a0 + n))
    end = len(verts)
    verts.append(tuple(V[-1] + (V[-1] - V[-2]).normalized() * radii[-1] * (2.0 if tip else 0.0)))
    for j in range(n):
        faces.append(((len(V) - 1) * n + j, (len(V) - 1) * n + (j + 1) % n, end))
    start = len(verts)
    verts.append(tuple(V[0] - (V[1] - V[0]).normalized() * radii[0] * 0.3))
    for j in range(n):
        faces.append(((j + 1) % n, j, start))
    b.add(verts, faces, mat, smooth=True)


def holly(b, rng, x, y, s, size=1.0):
    """A great holly: a stout leaning trunk, limbs, and a tall, dense, pyramidal crown of small glossy clumps
    sprinkled with red berries."""
    lean = (0.5 * s, -0.25)
    trunk = _spline([(x, y, FLOOR), (x + lean[0] * 0.2, y + lean[1] * 0.2, 2.5), (x + lean[0] * 0.6, y + lean[1] * 0.6, 6.0),
                     (x + lean[0], y + lean[1], 10.0)], 10)
    tube(b, 'bark', trunk, [0.85 - 0.5 * i / (len(trunk) - 1) for i in range(len(trunk))], n=10)
    cx0, cy0 = x + lean[0] * 0.6, y + lean[1] * 0.6
    for k in range(6):
        a = 2 * math.pi * k / 6 + rng.uniform(-0.3, 0.3)
        z = 3.5 + 1.0 * k
        o = (x + lean[0] * z / 10, y + lean[1] * z / 10, z)
        tube(b, 'bark', _spline([o, (o[0] + 1.4 * math.cos(a), o[1] + 1.2 * math.sin(a), z + 1.0),
                                 (o[0] + 2.6 * math.cos(a), o[1] + 2.2 * math.sin(a), z + 2.4)], 5),
             [0.3, 0.26, 0.22, 0.18, 0.14, 0.1][:6], n=6)
    for k in range(52):
        u = rng.random() ** 0.8
        a = rng.uniform(0, 2 * math.pi)
        zz = 3.2 + 12.5 * u
        rr = size * (4.6 * (1.0 - u) ** 0.85 * rng.uniform(0.6, 1.0) + 0.4)
        cx, cy = cx0 + rr * math.cos(a), cy0 + rr * 0.85 * math.sin(a)
        rad = size * rng.uniform(1.0, 1.6) * (1.0 - 0.45 * u)
        blob(b, 'holly', cx, cy, zz - rad * 0.8, rad, n=8, rings=5, squash=0.8, jitter=0.2)
        if k % 4 == 0:
            ba = a + rng.uniform(-0.5, 0.5)
            blob(b, 'berry', cx + rad * 0.95 * math.cos(ba), cy + rad * 0.95 * math.sin(ba), zz - 0.4,
                 0.14, n=5, rings=3, squash=1.0, jitter=0.0)


def pine(b, rng, x, y, z, hgt):
    cyl(b, 'bark', x, y, z - 0.6, 0.22, hgt * 0.3 + 0.6, n=5, r2=0.12, top=False)
    r = hgt * 0.3
    for k in range(3):
        zz = z + hgt * (0.2 + 0.24 * k)
        rr = r * (1.0 - 0.25 * k) * rng.uniform(0.9, 1.1)
        lathe(b, 'pine', [(0.0, 0.0), (rr, 0.0), (0.0, hgt * 0.45)], 8, x, y, zz, smooth=True, jitter=0.06)


def build(b, eye=False):
    """The static part: the massif alone (one height field, up to the 32k-vertex limit of a part)."""
    b.tiny_px = 0
    b.ao_distance = 7.0
    palette()
    blib.SKIRT_MAT[0] = 'rock'

    # ===================================================================== 1. the massif: one height field
    X0, X1, Y0, Y1 = -56.0, 56.0, -36.0, 58.0
    NX, NY = 168, 141                       # 0.667 units: as fine as a stock mountain's 128-sample height map
    terrain(b, height, X0, X1, Y0, Y1, NX, NY, lambda x, y, z, s: 'rock',
            keep=lambda x, y: height(x, y) > FLOOR + 0.12, smooth=True, skirt=FLOOR - 1.0)
    if eye:
        build_eye(b)


def build_eye(b):
    """The skinned part: the doors and everything before them on the still bone (eyeroot), and the Watcher's
    tentacles on eyepivot (PIVOT_MATS), which sways about the lake's centre."""
    b.tiny_px = TINY_PX
    palette()
    rng = random.Random(1999)

    # ===================================================================== 2. the smooth face of the doors
    nx, nz = 48, 14
    verts, faces = [], []
    W = RECESS + 0.35
    for i in range(nx + 1):
        x = -W + 2 * W * i / nx
        top = 29.0 + 1.2 * fbm(x * 0.4, 3.3, 3, 17) - 6.0 * (abs(x) / W) ** 6
        for k in range(nz + 1):
            z = FLOOR - 0.5 + (top - FLOOR + 0.5) * k / nz
            verts.append((x, DOOR_Y - 0.02, z))
    for i in range(nx):
        for k in range(nz):
            a = i * (nz + 1) + k
            faces.append((a, a + nz + 1, a + nz + 2, a + 1))
    b.add(verts, faces, 'wall', smooth=True)

    # ===================================================================== 3. the ithildin
    lines = door_lines()
    for n, (x0, za, x1, zb, w) in enumerate(lines):
        if w < 0.2:               # fine detail (letters, leaves, small rays): painted and glowing only
            continue
        L = math.hypot(x1 - x0, zb - za)
        ang = math.degrees(math.atan2(zb - za, x1 - x0))
        dy = 0.006 * (n % 5)      # overlapping strokes must not share a plane (z-fighting)
        box(b, 'ithildin', 0, 0, -w / 2, L + w * 0.55, 0.12, w,
            M=T((x0 + x1) / 2, DOOR_Y - 0.08 - dy, (za + zb) / 2, ry=-ang))
    b.glow = dict(lines=lines, box=(-RECESS - 0.5, RECESS + 0.5, FLOOR, 31.0), sigma=(0.2, 0.7))

    # ===================================================================== 4. threshold and the old road
    for k, (dz, dy) in enumerate(((Z0, 0.0), (Z0 * 0.66, 1.0), (Z0 * 0.33, 2.0))):
        box(b, 'stone', 0.0, DOOR_Y - 1.6 - dy, FLOOR, 19.5 - 1.4 * k, 3.2, dz - FLOOR)
    road = [(4.5, DOOR_Y - 5.5), (8.0, 4.0), (10.5, -6.0), (12.0, -16.0), (13.0, -26.0), (14.5, -33.0)]
    for i in range(len(road) - 1):
        (ax, ay), (bx, by) = road[i], road[i + 1]
        n = int(math.hypot(bx - ax, by - ay) / 1.45)
        for j in range(n):
            t = (j + 0.5) / n
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            if rng.random() < 0.18:           # broken, missing stones
                continue
            ang = math.degrees(math.atan2(by - ay, bx - ax))
            for side in (-0.8, 0.8):
                box(b, 'stone', x + side * math.sin(math.radians(ang)) + rng.uniform(-0.1, 0.1),
                    y - side * math.cos(math.radians(ang)) + rng.uniform(-0.1, 0.1), FLOOR,
                    rng.uniform(1.0, 1.35), rng.uniform(1.25, 1.45), -FLOOR + rng.uniform(0.12, 0.3),
                    rz=ang + rng.uniform(-8, 8))

    # ===================================================================== 5. the holly trees
    for s in (-1, 1):
        holly(b, rng, s * 11.8, DOOR_Y - 4.2, s, size=0.72)

    # ===================================================================== 6. the lake
    lx, ly, rx, ry = LAKE
    rim = []
    for k in range(72):
        a = 2 * math.pi * k / 72
        r = 1.0 + 0.09 * math.sin(a * 3 + 0.7) + 0.05 * math.sin(a * 7 + 2.0) + 0.03 * math.sin(a * 13)
        rim.append((lx + rx * r * math.cos(a), ly + ry * r * math.sin(a)))
    prism(b, 'lake', rim, -0.6, 0.78)

    # ===================================================================== 7. boulders, pines
    placed = 0
    for _ in range(4000):
        if placed >= 46:
            break
        x, y = rng.uniform(-24, 24), rng.uniform(-34, 13)
        d = bay_d(x, y)
        if not (-7.0 < d < -2.5) or (abs(x) < RECESS + 2 and y > DOOR_Y - 8):
            continue
        if ((x - lx) / (rx + 1.5)) ** 2 + ((y - ly) / (ry + 1.5)) ** 2 < 1.0 or abs(x - 11) < 3 and y < 8:
            continue
        r = rng.uniform(0.55, 1.5)
        blob(b, 'boulder', x, y, FLOOR + 0.6, r, n=8, rings=5, squash=rng.uniform(0.55, 0.85), jitter=0.24)
        placed += 1
    planted = 0
    for _ in range(20000):
        if planted >= 56:
            break
        x, y = rng.uniform(-54, 54), rng.uniform(-34, 50)
        z = height(x, y)
        if not (0.4 < z < 16.0) or bay_d(x, y) < 8.0:
            continue
        sl = math.hypot(height(x + 0.5, y) - z, height(x, y + 0.5) - z) / 0.5
        if sl > 0.75:
            continue
        pine(b, rng, x, y, z, rng.uniform(4.0, 7.0))
        planted += 1

    # ===================================================================== 8. the Watcher in the Water
    watcher_palette()
    b.tiny_px = TINY_PX
    rng = random.Random(1419)
    lx, ly, rx, ry = LAKE
    import blib as _b
    spline = _spline
    for k in range(9):
        a = math.radians(-160 + 140 * k / 8 + rng.uniform(-8, 8)) if k < 8 else math.radians(70)
        far = 0.55 if k < 8 else 0.25
        bx, by = lx + far * rx * math.cos(a), ly + far * ry * math.sin(a)
        hgt = rng.uniform(5.0, 9.0) if k < 8 else 4.0
        r0 = rng.uniform(0.75, 1.05)
        ph = rng.uniform(0, 2 * math.pi)
        if k < 8:
            pts = []
            for i in range(9):
                t = i / 8
                sw = 1.4 * math.sin(ph + t * 3.2) * t
                curl = 1.6 * smooth((t - 0.7) / 0.3)
                pts.append((bx + sw * math.cos(a + 1.57) + curl * math.cos(a + 2.4) * t,
                            by + sw * math.sin(a + 1.57) + curl * math.sin(a + 2.4) * t,
                            -0.4 + hgt * math.sin(t * 1.5) / math.sin(1.5) - curl * 0.8))
        else:   # the long one, reaching north out of the water towards the doors
            pts = [(bx, by, -0.4), (bx + 1.0, by + 3.0, 3.0), (bx + 2.0, by + 7.0, 4.5), (bx + 2.6, by + 11.0, 3.6),
                   (bx + 3.0, by + 14.0, 1.6), (bx + 2.4, by + 15.6, 0.8)]
        sp = spline(pts, 28)
        n = len(sp) - 1
        radii = [r0 * (1.0 - 0.9 * (i / n) ** 0.8) for i in range(n + 1)]
        tube(b, 'tentacle', sp, radii, n=10)
        for i in range(3, n - 3, 2):             # suckers along the inner side
            p, q = sp[i], sp[i + 1]
            dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
            Ld = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
            sx, sy = -dy / Ld, dx / Ld           # a horizontal side vector, perpendicular to the tentacle
            sl = math.hypot(sx, sy) or 1.0
            ri = radii[i]
            blob(b, 'sucker', p[0] + sx / sl * ri * 0.85, p[1] + sy / sl * ri * 0.85, p[2] - ri * 0.25,
                 max(0.07, ri * 0.3), n=6, rings=3, squash=0.55, jitter=0.0)


def _spline(pts, n=24):
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        steps = max(2, n // (len(pts) - 1))
        for j in range(steps):
            t = j / steps
            out.append(tuple(0.5 * ((2 * p1[c]) + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t
                                    + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t * t * t) for c in range(3)))
    out.append(tuple(pts[-1]))
    return out


def rig():
    """Bones of the skinned part in in-game units: (name, parent, position, effect key or None)."""
    return [('fxglow', 'eyeroot', (0.0, DOOR_Y - 0.3, GLOW_ZC), 'DOOR_GLOW')]


def glow_effect(k):
    """The additive ithildin glow (tools/landmarks/glow.py): quads in FILE units (k = file units per in-game unit)
    around the fxglow bone."""
    X0, X1, Z0_, Z1 = GLOW_BOX
    return dict(name='MEC_DurinGlow',
                quads=[(X0 * k, X1 * k, (Z0_ - GLOW_ZC) * k, (Z1 - GLOW_ZC) * k, 0.0)],
                tex_args=dict(lines=door_lines(), box=GLOW_BOX, px=1024))


def _sway(t):
    """The tentacles stir: a slow swing of 6 degrees either way about the lake's centre, once per 6 s loop."""
    return 6.0 * math.sin(2 * math.pi * t / 6.0)


GAZE = dict(fn=_sway, T=6.0, spans=60)

PREVIEW = [((0, -120, 95), (0, 8, 18), 32),          # the game's view of the whole massif
           ((14, -44, 22), (0, DOOR_Y, 10), 36),     # the doors
           ((-60, -40, 50), (0, 12, 20), 30)]         # from the south-west
PREVIEW_EYE = [((LAKE[0], LAKE[1] - 30, 16), (LAKE[0], LAKE[1], 4), 40)]
