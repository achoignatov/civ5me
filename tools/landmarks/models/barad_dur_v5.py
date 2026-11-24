"""Barad-dûr v5, the Dark Tower as in the films: the landmark of Mordor's capital (an IMPROVEMENT, docs/LANDMARKS.md).

Reference: the user's film still (eye-as-it-should-be.png): one immensely tall, slender black spire on a jagged crag,
built of ribbed, buttressed stages bristling with down-turned iron spikes, lit from within by slits of fire; at the
top two great curved prongs cradle the Eye: a tall burning ellipse with a black cat's slit, wreathed in flame.

Boundary test of the improvement renderer (2026-11-24): about 125 units tall (2x the tallest proven improvement),
the crag filling the hex, baked 2048 textures, close to the 32k-vertex limit of one model part, a skinned Eye with
its 6 s look-around loop, a ring of fire and a blaze round the Eye, its searching beam, and braziers on the tower.

Authored in IN-GAME units (improvement Scale 0.25 with the writer's x4): origin = tile centre, ground z = 0,
-Y = south = towards the game camera. The hex is about +-34 to its flat sides (E/W).
"""
import math
import random

from mathutils import Matrix, Vector

import blib
from blib import material, hexcol as h, box, lathe, strut, curve, terrain, T

BAKE = True
BAKE_PX = 2048          # tower texture (DIFF 2048, SREF 1024); the Eye gets 512
TINY_PX = 48            # UV islands smaller than this (square pixels) go on their material's swatch
BEAM_TILT = 38.0        # degrees below horizontal: from the Eye (z 110) the beam reaches the land

HEX = 34.0              # the hex: centre -> flat side
COS30 = math.cos(math.radians(30))
FLOOR = -1.2            # below the game's ground
PLAT = 13.0             # the crag's summit plateau, where the tower stands

# the tower: (radius at the foot, radius at the top, z foot, z top, ribs)
STAGES = [(10.6, 9.2, PLAT - 0.6, 31.0, 16),
          (8.3, 7.1, 31.0, 50.0, 14),
          (6.5, 5.5, 50.0, 67.0, 12),
          (5.1, 4.3, 67.0, 83.0, 12),
          (4.0, 3.3, 83.0, 96.5, 10)]
CROWN_Z = 96.5

EYE_C = (0.0, -0.6, 110.0)         # centre of the Eye = the pivot it turns about (vertical axis)
EYE_TILT = 12.0                    # tilted down, towards the land and the camera
EX, EZ = 3.2, 5.4                  # half-width / half-height of the Eye (a tall cat's eye)


# ----------------------------------------------------------------------------------------------- helpers
def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def _hash(i, j, s):
    n = (i * 374761393 + j * 668265263 + s * 2147483647) & 0xffffffff
    n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
    return (n & 0xffff) / 65535.0


def fbm(x, y, octaves=4, s=0):
    tot, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        f = 2 ** o
        X, Y = x * f, y * f
        i, j = math.floor(X), math.floor(Y)
        fx, fy = X - i, Y - j
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a, b_ = _hash(i, j, s + o), _hash(i + 1, j, s + o)
        c, d = _hash(i, j + 1, s + o), _hash(i + 1, j + 1, s + o)
        tot += amp * (a + (b_ - a) * fx + (c - a) * fy + (a - b_ - c + d) * fx * fy)
        norm += amp
        amp *= 0.5
    return tot / norm - 0.5


def hex_dist(x, y, inr=HEX):
    return inr - max(abs(x * math.cos(math.radians(60 * k)) + y * math.sin(math.radians(60 * k))) for k in range(3))


def spline(pts, n=24):
    """Catmull-Rom curve through pts."""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = (Vector(P[k]) for k in (i - 1, i, i + 1, i + 2))
        steps = max(2, n // (len(pts) - 1))
        for j in range(steps):
            t = j / steps
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)))
    out.append(tuple(pts[-1]))
    return out


def crag(x, y):
    """The black crag: a summit plateau under the tower, jagged spurs and gullies falling to the plain."""
    r = math.hypot(x, y)
    th = math.atan2(y, x)
    body = PLAT * smooth((31.0 - r) / 17.0)                                   # PLAT inside r 14, 0 beyond r 31
    spur = 3.2 * max(0.0, math.cos(5 * th + 1.7 * fbm(x * 0.05, y * 0.05, 2, 9))) ** 3 * smooth((29 - r) / 9)
    jag = (2.4 * fbm(x * 0.09, y * 0.09, 4, 2) + 1.3 * fbm(x * 0.33, y * 0.33, 3, 5)) * smooth((r - 11.0) / 6.0)
    z = body + spur + jag
    if r < 14.0:                                                              # level summit (tower and walls)
        z = PLAT + (z - PLAT) * smooth((r - 11.5) / 2.5)
    return FLOOR + (z - FLOOR) * smooth((hex_dist(x, y) - 0.6 - 0.8 * fbm(x * 0.1, y * 0.1, 2, 6)) / 4.0)


def ring_pt(r, a, z):
    return (r * math.cos(a), r * math.sin(a), z)


# ----------------------------------------------------------------------------------------------- materials
def palette():
    material('blackrock', h('35302b'), h('1e1b18'), slope_color=h('2a2622'), slope_start=0.62)
    material('blackstone', h('2e2c30'), h('1c1b1f'))
    material('darkstone', h('282729'), h('161517'))
    material('iron', h('3c3b42'), h('222128'), spec=0.65, refl=60)
    material('lava', h('ff7418'), spec=0.2, ao=False)
    material('ember', h('d8400c'), spec=0.2, ao=False)
    for m, extra in (('blackrock', dict(scale=0.11, cracks=0.16, strata=0.0)),
                     ('blackstone', dict(scale=0.35, strata=1.2, strata_amp=0.2, cracks=0.28)),
                     ('darkstone', dict(scale=0.35, strata=1.6, strata_amp=0.22, cracks=0.34)),
                     ('iron', dict(scale=0.7))):
        blib.PALETTE[m].update(extra)
    for m in ('lava', 'ember'):
        blib.PALETTE[m]['solid'] = True        # glowing colours: flat, crisp, never darkened


def eye_palette():
    material('eyerim', h('b8220a'), spec=0.2, ao=False)
    material('eyeflame', h('ff5a12'), spec=0.2, ao=False)
    material('eyefire', h('ff8c1e'), spec=0.2, ao=False)
    material('iris', h('ffb424'), spec=0.6, refl=60, ao=False)
    material('core', h('fff2b0'), spec=0.6, ao=False)
    material('pupil', h('060304'), ao=False)
    material('ember', h('d8400c'), spec=0.2, ao=False)
    for m in ('eyerim', 'eyeflame', 'eyefire', 'iris', 'core', 'pupil', 'ember'):
        blib.PALETTE[m]['solid'] = True


# ----------------------------------------------------------------------------------------------- the model
def build(b, eye=True):
    b.tiny_px = TINY_PX
    palette()
    rng = random.Random(1937)

    # ===================================================================== 1. the crag
    terrain(b, crag, -HEX, HEX, -HEX / COS30, HEX / COS30, 64, 74, lambda x, y, z, s: 'blackrock',
            keep=lambda x, y: hex_dist(x, y) > 0.4 and crag(x, y) > FLOOR + 0.2 and math.hypot(x, y) > 9.5,
            smooth=True, skirt=FLOOR - 1.0)

    # ===================================================================== 2. the curtain wall on the summit
    WR = 13.4
    lathe(b, 'darkstone', [(WR + 0.6, -2.0), (WR, 2.6), (WR + 0.5, 2.9), (WR + 0.5, 3.4), (WR - 1.0, 3.4),
                           (WR - 1.0, 0.0)], n=36, z=PLAT, smooth=False)
    for k in range(36):                                                 # spiked merlons
        a = 2 * math.pi * k / 36
        p = ring_pt(WR + 0.2, a, PLAT + 3.4)
        box(b, 'darkstone', p[0], p[1], p[2], 0.8, 0.9, 0.7, rz=math.degrees(a))
        if k % 2 == 0:
            strut(b, 'iron', ring_pt(WR + 0.3, a, PLAT + 4.0), ring_pt(WR + 0.9, a, PLAT + 5.8), 0.16, 0.0, n=4,
                  smooth=False)
    for k in range(6):                                                  # bastions round the wall
        a = math.radians(60 * k + 30)
        x, y = (WR + 1.2) * math.cos(a), (WR + 1.2) * math.sin(a)
        top = 9.0 + 1.5 * (k % 2)
        lathe(b, 'darkstone', [(2.2, -2.5), (1.8, top - 1.4), (2.4, top - 0.8), (2.4, top), (0, top)], n=12,
              x=x, y=y, z=PLAT, smooth=False)
        strut(b, 'iron', (x, y, PLAT + top), (x, y, PLAT + top + 4.5), 1.1, 0.0, n=8, smooth=False)
        for s in range(6):
            sa = math.radians(60 * s + 30 * k)
            strut(b, 'iron', (x + 2.3 * math.cos(sa), y + 2.3 * math.sin(sa), PLAT + top - 0.3),
                  (x + 3.6 * math.cos(sa), y + 3.6 * math.sin(sa), PLAT + top - 1.8), 0.2, 0.0, n=4, smooth=False)
        box(b, 'lava', x + 2.0 * math.cos(a), y + 2.0 * math.sin(a), PLAT + top * 0.45, 0.45, 0.2, 1.4,
            rz=math.degrees(a) + 90)
    # the great gate on the south (towards the camera), blazing from the forges within
    box(b, 'lava', 0.0, -(WR + 0.55), PLAT - 0.2, 2.6, 0.2, 3.2)
    for s in (-1, 1):
        strut(b, 'iron', (s * 1.6, -(WR + 0.7), PLAT + 3.4), (s * 0.2, -(WR + 0.8), PLAT + 5.6), 0.5, 0.15, n=6,
              smooth=False)

    # ===================================================================== 3. the great buttresses at the foot
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        base = ring_pt(12.2, a, PLAT + 0.2)
        mid = ring_pt(11.4, a, PLAT + 9.0)
        top = ring_pt(9.6, a, PLAT + 17.0)
        curve(b, 'blackstone', spline([base, mid, top], 10), 1.7, 0.7, n=6, smooth=False)
        for j, zz in enumerate((PLAT + 4.0, PLAT + 9.0, PLAT + 14.0)):      # spikes along the buttress
            rr = 12.0 - 0.15 * j - 0.12 * (zz - PLAT)
            strut(b, 'iron', ring_pt(rr, a, zz), ring_pt(rr + 2.6, a, zz - 1.6), 0.3, 0.0, n=4, smooth=False)

    # ===================================================================== 4. the tower: five tapering stages
    for i, (r0, r1, z0, z1, nr) in enumerate(STAGES):
        hgt = z1 - z0
        fl = 1.16                                                         # flange flare
        lathe(b, 'blackstone', [(r0, 0.0), (r1 * 1.01, hgt - 1.6), (r1 * fl, hgt - 1.0), (r1 * fl, hgt - 0.3),
                                (r1 * 0.96, hgt), (0.0, hgt)], n=32, z=z0, smooth=False)
        rot = math.pi / nr if i % 2 else 0.0
        for k in range(nr):
            a = 2 * math.pi * k / nr + rot
            c_, s_ = math.cos(a), math.sin(a)
            # ribs: thick piers running up the stage, standing proud of the wall
            pr = 0.34 * r0 / 6.0 + 0.18
            strut(b, 'darkstone', (r0 * 1.0 * c_, r0 * 1.0 * s_, z0), (r1 * 0.99 * c_, r1 * 0.99 * s_, z1 - 1.6),
                  pr * 1.25, pr, n=4, smooth=False)
            # down-turned iron spikes under the flange
            if k % (1 if r1 > 6 else 2) == 0:
                ln = 1.2 + 0.22 * r1
                strut(b, 'iron', (r1 * fl * c_, r1 * fl * s_, z1 - 0.8),
                      ((r1 * fl + ln) * c_, (r1 * fl + ln) * s_, z1 - 1.6 - 0.18 * r1),
                      0.2 + 0.02 * r1, 0.0, n=4, smooth=False)
            # little upright spikes on the flange rim
            if k % 2 == 0:
                strut(b, 'iron', (r1 * fl * 0.97 * c_, r1 * fl * 0.97 * s_, z1 - 0.3),
                      (r1 * fl * 0.99 * c_, r1 * fl * 0.99 * s_, z1 + 1.1), 0.14, 0.0, n=4, smooth=False)
        # slits of fire between the ribs, two rows per stage (all round: the camera can turn)
        for k in range(nr):
            a = 2 * math.pi * (k + 0.5) / nr + rot
            for zz in (z0 + hgt * 0.3, z0 + hgt * 0.62):
                if rng.random() < 0.72:
                    rr = r0 + (r1 - r0) * (zz - z0) / (hgt - 1.6) - 0.04
                    box(b, 'lava', rr * math.cos(a), rr * math.sin(a), zz, 0.22 + 0.02 * r0, 0.14, 1.4 + 0.05 * hgt,
                        rz=math.degrees(a) + 90)
        # a gallery ring half way up the big stages, on brackets
        if hgt > 15:
            zg = z0 + hgt * 0.47
            rg = r0 + (r1 - r0) * 0.47
            lathe(b, 'darkstone', [(rg * 1.02, -0.5), (rg * 1.12, 0.0), (rg * 1.12, 0.45), (rg * 1.0, 0.45)],
                  n=32, z=zg, smooth=False)
    # clinging turrets: slim shafts bundled round the stages, rising past each flange to spiked caps (the film's
    # clustered silhouette instead of a stack of drums)
    for i, (r0, r1, z0, z1, nr) in enumerate(STAGES[:4]):
        hgt = z1 - z0
        n_t = (5, 4, 4, 3)[i]
        for k in range(n_t):
            a = 2 * math.pi * (k + 0.37 * i + 0.5 * rng.random()) / n_t
            tr = (1.9, 1.5, 1.2, 0.95)[i] * rng.uniform(0.85, 1.1)
            za = z0 + hgt * rng.uniform(0.05, 0.3)
            zb = z1 + rng.uniform(1.5, 5.5) * (1.0 - 0.15 * i)
            rr = (r0 + r1) / 2 + tr * 0.35
            x, y = rr * math.cos(a), rr * math.sin(a)
            lathe(b, 'blackstone', [(tr * 0.75, 0.0), (tr, 1.2), (tr * 0.92, zb - za - 1.0), (tr * 1.22, zb - za - 0.6),
                                    (tr * 1.22, zb - za), (0.0, zb - za)], n=10, x=x, y=y, z=za, smooth=False)
            lathe(b, 'iron', [(tr * 0.95, 0.0), (0.0, tr * 3.2 + 1.0)], n=10, x=x, y=y, z=zb, smooth=False)
            for s_ in range(4):
                sa = a + math.radians(90 * s_ + 45)
                strut(b, 'iron', (x + tr * 1.2 * math.cos(sa), y + tr * 1.2 * math.sin(sa), zb - 0.4),
                      (x + (tr * 1.2 + 1.3) * math.cos(sa), y + (tr * 1.2 + 1.3) * math.sin(sa), zb - 1.5),
                      0.16, 0.0, n=4, smooth=False)
            box(b, 'lava', x + tr * 0.97 * math.cos(a), y + tr * 0.97 * math.sin(a), za + (zb - za) * 0.55,
                0.2, 0.12, 1.2, rz=math.degrees(a) + 90)
    # flying spurs from the second stage, like the film's jutting blades
    for k in range(4):
        a = math.radians(45 + 90 * k)
        curve(b, 'iron', spline([ring_pt(7.4, a, 44.0), ring_pt(10.5, a, 41.0), ring_pt(12.2, a, 45.5)], 8),
              0.55, 0.0, n=4, smooth=False)

    # ===================================================================== 5. the crown: two great prongs
    zc = CROWN_Z
    lathe(b, 'iron', [(3.4, 0.0), (4.3, 1.0), (3.9, 1.7), (2.6, 2.1), (0, 2.1)], n=24, z=zc, smooth=False)
    for s in (-1, 1):
        pts = [(s * 2.4, 0.3, zc + 1.0), (s * 5.6, 0.5, zc + 4.0), (s * 7.0, 0.6, zc + 9.5),
               (s * 6.6, 0.5, zc + 15.5), (s * 4.6, 0.3, zc + 20.0), (s * 2.4, 0.1, zc + 22.6)]
        sp = spline(pts, 30)
        curve(b, 'iron', sp, 2.4, 0.05, n=10, smooth=True)                # the great horn
        for j in range(3, len(sp) - 4, 3):                                # serrations on its outer edge
            p, q = Vector(sp[j]), Vector(sp[j + 1])
            out = Vector((s, 0.0, 0.0))
            tip = p + out * (1.7 - 0.04 * j) + (q - p).normalized() * 0.9
            strut(b, 'iron', tuple(p + out * 0.6), tuple(tip), 0.32, 0.0, n=4, smooth=False)
        # lesser rear prong and a jagged front fang
        curve(b, 'iron', spline([(s * 1.8, 1.6, zc + 1.2), (s * 3.4, 2.6, zc + 6.0), (s * 3.0, 3.0, zc + 11.0)], 12),
              0.9, 0.0, n=6, smooth=True)
        curve(b, 'iron', spline([(s * 2.0, -1.4, zc + 1.2), (s * 3.2, -2.0, zc + 4.0), (s * 2.6, -2.4, zc + 7.0)], 10),
              0.6, 0.0, n=6, smooth=True)

    if eye:
        build_eye(b, palette_too=False)


def eye_matrix():
    return Matrix.Translation(EYE_C) @ Matrix.Rotation(math.radians(EYE_TILT), 4, 'X')


def eye_point(x, z, y=0.0):
    v = eye_matrix() @ Vector((x, y, z))
    return (v.x, v.y, v.z)


def build_eye(b, palette_too=True):
    """The Eye of Sauron: nested flame shells round a glazed iris and a black slit, tongues of fire streaming up."""
    rng = random.Random(1616)
    eye_palette()
    b.tiny_px = TINY_PX
    M = eye_matrix()

    def ellipsoid(mat, cy, sx, sy, sz, n=28, rings=18):
        prof = [(math.cos(math.pi * i / rings - math.pi / 2), math.sin(math.pi * i / rings - math.pi / 2))
                for i in range(rings + 1)]
        prof[0], prof[-1] = (0.0, -1.0), (0.0, 1.0)
        lathe(b, mat, prof, n, smooth=True, M=M @ T(0.0, cy, 0.0, s=(sx, sy, sz)))

    ellipsoid('eyerim', 0.7, EX, 1.6, EZ)                      # dark red outer shell
    ellipsoid('eyeflame', 0.15, EX * 0.9, 1.35, EZ * 0.93)
    ellipsoid('eyefire', -0.3, EX * 0.76, 1.1, EZ * 0.84)
    ellipsoid('iris', -0.75, EX * 0.58, 0.85, EZ * 0.72)       # glazed yellow iris
    ellipsoid('core', -1.15, EX * 0.3, 0.6, EZ * 0.6, n=20, rings=14)
    ellipsoid('pupil', -1.6, 0.32, 0.4, EZ * 0.66, n=12, rings=12)   # the black slit
    P = eye_point
    # tongues of fire licking out from the rim and sweeping UP (fire rises): broad at the root, curling to a point
    for layer, (nfl, rad, mats) in enumerate(((18, 0.95, ('eyeflame', 'eyefire', 'eyerim')),
                                             (12, 0.7, ('eyefire', 'eyeflame')))):
        for k in range(nfl):
            phi = 2 * math.pi * (k + 0.5 * layer) / nfl
            cx, cz = math.cos(phi), math.sin(phi)
            up = 0.5 + 0.5 * cz                               # 0 at the bottom of the Eye, 1 at the top
            L = (1.8 + 3.4 * up) * rng.uniform(0.8, 1.15) * (0.75 if layer else 1.0)
            base = (EX * 0.9 * cx, EZ * 0.9 * cz)
            p1 = (base[0] + cx * L * 0.35, base[1] + cz * L * 0.2 + L * 0.3)
            p2 = (base[0] + cx * L * 0.45 + rng.uniform(-0.3, 0.3), base[1] + cz * L * 0.15 + L * 0.75)
            tip = (base[0] + cx * L * 0.3 + rng.uniform(-0.5, 0.5), base[1] + cz * L * 0.1 + L * 1.15)
            curve(b, mats[k % len(mats)], spline([P(*base, y=0.5), P(*p1, y=0.35), P(*p2, y=0.2), P(*tip, y=0.1)],
                                                 9), rad, 0.0, n=6, smooth=True)
    for k in range(9):                                          # a crest of flame rising from the top
        x = (k - 4) * 0.55
        top = EZ + 3.2 + (1.0 - abs(k - 4) / 4.0) * 2.4
        curve(b, 'eyeflame' if k % 2 else 'eyefire',
              spline([P(x, EZ * 0.8, 0.3), P(x * 1.2, EZ + 1.4), P(x * 1.35 + rng.uniform(-0.4, 0.4), top)], 6),
              0.55, 0.0, n=5, smooth=True)
    for k in range(6):                                          # embers dripping onto the crown
        x = (k - 2.5) * 0.9
        strut(b, 'ember', P(x, -EZ * 0.85, 0.3), P(x * 1.15, -EZ * 1.12, 0.2), 0.42, 0.0, n=5, smooth=True)


def rig():
    """Bones of the skinned Eye part in in-game units: (name, parent, position, effect key or None).
    'eyeroot' (origin) and 'eyepivot' (EYE_C, turned by the animation) are added by the writer."""
    bones = []
    for k in range(8):                                  # a ring of fire round the rim, behind the Eye
        a = math.radians(45 * k + 22.5)
        bones.append(('fxfire%d' % k, 'eyepivot', eye_point(EX * 1.05 * math.cos(a), EZ * 1.0 * math.sin(a), 0.8),
                      'EYE_FIRE'))
    bones.append(('fxcore', 'eyepivot', eye_point(0.0, 1.2, 3.0), 'EYE_FIRE_BIG'))   # the blaze behind the Eye
    bones.append(('fxbeam', 'eyeroot', EYE_C, 'EYE_BEAM'))                          # static: the beam turns itself
    # braziers on the flanges of the tower (static), towards the camera
    for k, (si, deg) in enumerate(((0, 250), (0, 290), (1, 235), (1, 305), (2, 270), (3, 270))):
        r0, r1, z0, z1, _ = STAGES[si]
        a = math.radians(deg)
        bones.append(('fxtower%d' % k, 'eyeroot', ring_pt(r1 * 1.12, a, z1 + 0.2), 'TOWER_FIRE'))
    return bones


def _gaze(t):
    """Yaw of the Eye in degrees (+ = towards the screen's right) over one 6 s loop (as v3, proven in game):
    searches the right (with a flick further right), snaps left for a second, swings back."""
    keys = [(0.00, 40.0, 'lin'), (1.20, 44.0, 'ease'), (1.45, 54.0, 'lin'), (2.70, 50.0, 'ease'),
            (3.02, -42.0, 'lin'), (4.02, -47.0, 'ease'), (4.80, 38.0, 'lin'), (6.00, 40.0, None)]
    t = t % 6.0
    for (t0, a0, kind), (t1, a1, _) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0)
            if kind == 'ease':
                u = u * u * u * (u * (6 * u - 15) + 10)
            return a0 + (a1 - a0) * u
    return keys[-1][1]


GAZE = dict(fn=_gaze, T=6.0, spans=60)

# preview views: the game camera's angle on the whole tower, the crown and the Eye, the foot of the tower
PREVIEW = [((0, -150, 125), (0, 0, 52), 35), ((14, -42, 118), (0, 0, 108), 40), ((10, -60, 40), (0, 0, 20), 40)]
PREVIEW_EYE = [((0, -26, 116), (0, 0, 110), 40), ((16, -20, 112), (0, 0, 110), 40)]
