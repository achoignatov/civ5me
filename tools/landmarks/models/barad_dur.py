"""Barad-dûr, the Dark Tower of Sauron: the landmark of the city named Barad-dûr.

v4 (2026-11-24, render-test model): redesigned to match the Moria model that draws in 80-90 % of cities, in every
technical respect (legacy city-art path; superseded by barad_dur_v5.py):
  * footprint within +-16 world units (the size that drew in 18/18 city-states and every major city), height <= 24;
  * ONE static model (the Eye is modelled, not animated; no effects), Wonder_DecisionTree, fScale 0.05;
  * no ground plate: a jagged outcrop of black rock rising from the game's own terrain;
  * smooth/finely built, textures baked in Blender (tools/landmarks/bake.py), tiny faces on solid colour swatches.
The old v3 (47 high, +-24 x +-27, skinned animated Eye + fire + beam) is in git history (drew in 2 of ~30 cities).

Authored in WORLD units: origin = tile centre, ground z = 0, -Y = south = towards the game camera. The city hexagon is
pointy-top (flat sides east/west).

Lore cues (The Lord of the Rings; the films for the crown and the Eye): a fortress of black stone and iron on immense
foundations, "battlement upon battlement", "tower upon tower"; spiked bastions and gates glowing with the fires
within; the topmost tower crowned with two great curved prongs cradling the Eye, "rimmed with fire ... yellow as a
cat's ... the black slit of its pupil".
"""
import math

from mathutils import Matrix, Vector

from blib import material, hexcol as h, box, lathe, strut, curve, terrain, T

HEX = 16.0             # footprint limit (flat sides E/W)
TOP = 24.0             # highest point (the proven height at this footprint, Moria +-20: 24.2)
FLOOR = -0.6           # below the game's ground
COS30 = math.cos(math.radians(30))
BAKE = True            # build_models: baked textures (tools/landmarks/bake.py)
TINY_PX = 40           # UV islands smaller than this (square pixels) go on their material's colour swatch


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


def corner_r(inr):
    return inr / COS30


def hex_lathe(b, mat, profile_in, z=0.0, smooth_=False):
    """Hexagonal 'lathe' aligned with the tile: profile radii are INRADII (flat sides E/W)."""
    lathe(b, mat, [(corner_r(r) if r > 0 else 0.0, hz) for r, hz in profile_in], n=6, z=z, smooth=smooth_,
          a0=30.0, a1=390.0)


def side_frame(k, inr):
    a = math.radians(60 * k)
    c = Vector((inr * math.cos(a), inr * math.sin(a), 0.0))
    d = Vector((-math.sin(a), math.cos(a), 0.0))
    return c, d, 2 * inr * math.tan(math.radians(30)), 60 * k + 90


def spline(pts, n=24):
    """Catmull-Rom curve through pts (smooth prongs instead of a chain of straight segments)."""
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


def outcrop(x, y):
    """The black rock the fortress stands on: a plinth under the walls, jagged spurs, sinking into the land."""
    r = math.hypot(x, y)
    z = 1.6 * smooth((13.8 - r) / 2.5) + 0.9 * fbm(x * 0.25, y * 0.25, 4, 2) + 0.5 * fbm(x * 0.9, y * 0.9, 3, 4)
    z = FLOOR + (z - FLOOR) * smooth((hex_dist(x, y) - 0.4 - 0.4 * fbm(x * 0.3, y * 0.3, 2, 6)) / 2.0)
    return z


def build(b):
    rng = b.rng
    b.tiny_px = TINY_PX
    # --- palette: black stone and iron with enough value range to read in the game's lighting
    material('blackrock', h('34302c'), h('211e1b'), slope_color=h('2a2724'), slope_start=0.6)
    material('blackstone', h('2f2d31'), h('1f1e22'))
    material('darkstone', h('29282c'), h('19181c'))
    material('iron', h('3a3940'), h('26252b'), spec=0.6, refl=50)
    material('lava', h('ff7a1e'), spec=0.2, ao=False)
    material('eyerim', h('e0380c'), spec=0.2, ao=False)
    material('eyeflame', h('ff6a16'), spec=0.2, ao=False)
    material('iris', h('ffa21c'), h('ff7a12'), spec=0.6, refl=60, ao=False)
    material('core', h('fff0a0'), spec=0.6, ao=False)
    material('pupil', h('050304'), ao=False)
    import blib
    for m, extra in (('blackrock', dict(scale=0.25, cracks=0.35, strata=0.0)),
                     ('blackstone', dict(scale=0.6, strata=2.4, strata_amp=0.18, cracks=0.5)),
                     ('darkstone', dict(scale=0.6, strata=3.0, strata_amp=0.2, cracks=0.6)),
                     ('iron', dict(scale=1.2)),
                     ('iris', dict(scale=1.5))):
        blib.PALETTE[m].update(extra)
    for m in ('lava', 'eyerim', 'eyeflame', 'core', 'pupil'):
        blib.PALETTE[m]['solid'] = True        # glowing colours: flat, crisp, never darkened

    # ================================================================ 1. the outcrop (no plate: rises from the land)
    terrain(b, outcrop, -HEX, HEX, -HEX / COS30, HEX / COS30, 54, 62, lambda x, y, z, s: 'blackrock',
            keep=lambda x, y: hex_dist(x, y) > 0.3 and outcrop(x, y) > FLOOR + 0.15, smooth=True, skirt=FLOOR - 0.9)

    # ================================================================ 2. the outer wall (follows the hexagon)
    WIN, WZ0, WZ1 = 12.4, 0.6, 3.6
    for k in range(6):
        c, d, L, rz = side_frame(k, WIN)
        box(b, 'darkstone', c.x, c.y, WZ0 - 1.0, L - 1.6, 1.2, WZ1 - WZ0 + 1.0, rz=rz)
        o = Vector((math.cos(math.radians(60 * k)), math.sin(math.radians(60 * k)), 0))
        n = 8
        for i in range(n):                                     # crenellations
            t = (i + 0.5) / n - 0.5
            p = c + d * (t * (L - 2.6)) + o * 0.4
            box(b, 'darkstone', p.x, p.y, WZ1, 0.7, 0.4, 0.6, rz=rz)
        for t in (-0.25, 0.25):                                # buttresses with iron spikes
            p = c + d * (t * L)
            strut(b, 'darkstone', tuple(p + o * 1.4 + Vector((0, 0, 0.2))), tuple(p + o * 0.5 + Vector((0, 0, WZ1 - 0.3))),
                  0.55, 0.35, n=4, smooth=False)
            strut(b, 'iron', tuple(p + o * 0.7 + Vector((0, 0, WZ1 - 1.0))), tuple(p + o * 2.2 + Vector((0, 0, WZ1 - 1.9))),
                  0.2, 0.0, n=4, smooth=False)
    # the gate on the south-east face (towards the camera), glowing with the forges within, between two gate towers
    c, d, L, rz = side_frame(5, WIN)
    o = Vector((math.cos(math.radians(300)), math.sin(math.radians(300)), 0))
    g = c + o * 0.62
    box(b, 'lava', g.x, g.y, WZ0, 1.6, 0.12, 2.1, rz=rz)
    for s in (-1, 1):
        p = c + d * (s * 1.6) + o * 0.9
        lathe(b, 'darkstone', [(0.95, 0.0), (0.78, 5.2), (1.05, 5.5), (1.05, 6.1), (0, 6.1)], n=8, x=p.x, y=p.y,
              z=WZ0 - 0.6, smooth=False)
        strut(b, 'iron', (p.x, p.y, WZ0 + 5.5), (p.x, p.y, WZ0 + 7.2), 0.6, 0.0, n=6, smooth=False)
    # corner bastions: squat spiked towers at the six corners of the wall
    for k in range(6):
        a = math.radians(30 + 60 * k)
        rr = corner_r(WIN) - 0.4
        x, y = rr * math.cos(a), rr * math.sin(a)
        top = 6.0 + 0.8 * (k % 2)
        lathe(b, 'darkstone', [(1.8, 0.0), (1.5, top - 1.2), (1.95, top - 0.7), (1.95, top), (0, top)], n=10,
              x=x, y=y, z=-0.4, smooth=False)
        for s in range(8):
            sa = math.radians(45 * s + 22.5)
            box(b, 'darkstone', x + 1.75 * math.cos(sa), y + 1.75 * math.sin(sa), top - 0.4, 0.5, 0.5, 0.6,
                rz=math.degrees(sa))
        strut(b, 'iron', (x, y, top - 0.4), (x, y, top + 2.2), 0.8, 0.0, n=6, smooth=False)

    # ================================================================ 3. the inner terrace and lesser towers
    lathe(b, 'blackrock', [(11.2, 0.0), (10.2, 2.4), (9.2, 4.0), (8.4, 5.0), (0, 5.0)], n=24, smooth=True, jitter=0.04)
    lathe(b, 'darkstone', [(8.6, 4.6), (8.3, 6.8), (8.8, 7.1), (8.8, 7.6), (0, 7.6)], n=24, smooth=False)
    for k in range(24):
        a = math.radians(15 * k)
        box(b, 'darkstone', 8.6 * math.cos(a), 8.6 * math.sin(a), 7.6, 0.45, 0.7, 0.5, rz=15 * k)
    for k in range(6):
        a = math.radians(60 * k + 30)
        x, y = 7.6 * math.cos(a), 7.6 * math.sin(a)
        top = 13.0 + 1.6 * (k % 2)
        lathe(b, 'blackstone', [(1.5, 0.0), (1.2, top - 6.6), (1.65, top - 6.2), (1.65, top - 5.5), (0, top - 5.5)],
              n=10, x=x, y=y, z=5.0, smooth=False)
        zt = 5.0 + top - 5.5
        lathe(b, 'iron', [(1.15, 0.0), (0.0, 3.0)], n=10, x=x, y=y, z=zt, smooth=False)      # spire
        for s in range(6):
            sa = math.radians(60 * s + 30 * k)
            strut(b, 'iron', (x + 1.45 * math.cos(sa), y + 1.45 * math.sin(sa), zt - 0.2),
                  (x + 2.2 * math.cos(sa), y + 2.2 * math.sin(sa), zt + 1.0), 0.18, 0.0, n=4, smooth=False)
        box(b, 'lava', x + 1.3 * math.cos(a), y + 1.3 * math.sin(a), zt - 3.0, 0.32, 0.16, 0.9, rz=math.degrees(a) + 90)
        ra = math.atan2(y, x)                                  # flying buttress to the great tower
        curve(b, 'darkstone', spline([(x - 1.05 * math.cos(ra), y - 1.05 * math.sin(ra), zt - 2.0),
                                      (5.4 * math.cos(ra), 5.4 * math.sin(ra), zt - 0.8),
                                      (4.6 * math.cos(ra), 4.6 * math.sin(ra), zt + 1.6)], 8), 0.36, 0.3, n=6,
              smooth=True)

    # ================================================================ 4. the great tower
    tiers = [(5.6, 5.0, 10.8), (4.6, 10.8, 15.0), (3.7, 15.0, 18.0), (2.9, 18.0, 19.6)]
    N = 12
    for i, (r, z0, z1) in enumerate(tiers):
        hgt = z1 - z0
        lathe(b, 'blackstone', [(r, 0.0), (r * 0.9, hgt - 0.9), (r * 1.12, hgt - 0.5), (r * 1.12, hgt), (0.0, hgt)],
              n=N * 2, z=z0, smooth=False)
        for k in range(N):                                     # battlement
            a = math.radians(360.0 * k / N + 15)
            box(b, 'darkstone', r * 1.09 * math.cos(a), r * 1.09 * math.sin(a), z1, 0.45, 0.6, 0.55, rz=math.degrees(a))
        for k in range(N):
            a = math.radians(360.0 * k / N + (15 if i % 2 else 0))
            c_, s_ = math.cos(a), math.sin(a)
            strut(b, 'iron', (r * 1.02 * c_, r * 1.02 * s_, z0), (r * 0.92 * c_, r * 0.92 * s_, z1 - 0.9),
                  0.28, 0.17, n=4, smooth=False)                # vertical ribs
            strut(b, 'iron', (r * 1.08 * c_, r * 1.08 * s_, z1 - 0.45), ((r + 1.7) * c_, (r + 1.7) * s_, z1 - 2.0),
                  0.2, 0.0, n=4, smooth=False)                  # down-turned spikes
        for k in range(N // 2 + 1):                            # fiery window slits on the side facing the camera
            a = math.radians(180.0 + 360.0 * k / N + 15)
            for zz in ((z0 + hgt * 0.35, z0 + hgt * 0.62) if hgt > 4 else (z0 + hgt * 0.45,)):
                rr = r * (1.0 - 0.1 * (zz - z0) / hgt) - 0.02
                box(b, 'lava', rr * math.cos(a), rr * math.sin(a), zz, 0.34, 0.15, 0.85, rz=math.degrees(a) + 90)

    # ================================================================ 5. the iron crown
    zc = 19.6
    for s in (-1, 1):
        pts = [(s * 2.2, 0.0, zc - 0.3), (s * 3.2, 0.2, zc + 1.2), (s * 3.5, 0.25, zc + 2.6),
               (s * 3.1, 0.2, zc + 3.6), (s * 2.2, 0.05, zc + 4.1), (s * 1.4, -0.05, zc + 4.2)]
        curve(b, 'iron', spline(pts, 20), 1.1, 0.0, n=8, smooth=True)       # the great prongs cradling the Eye
        for zz, out in ((zc + 1.0, 4.3), (zc + 2.0, 4.6), (zc + 3.0, 4.3)):
            strut(b, 'iron', (s * 3.3, 0.25, zz), (s * out, 0.3, zz + 0.8), 0.24, 0.0, n=4, smooth=False)
        curve(b, 'iron', spline([(s * 1.3, 1.2, zc - 0.2), (s * 1.9, 1.9, zc + 1.8), (s * 1.6, 2.0, zc + 3.2)], 16),
              0.55, 0.0, n=8, smooth=True)                      # lesser rear prongs
    lathe(b, 'iron', [(3.0, 0.0), (2.6, 0.5), (1.9, 0.75), (0, 0.75)], n=N * 2, z=zc, smooth=False)   # platform

    # ================================================================ 6. the Eye of Sauron (static)
    build_eye(b)
    assert max(v[2] for v in b.verts) <= TOP + 1e-6, max(v[2] for v in b.verts)


EYE_C = (0.0, -0.25, 21.3)         # centre of the Eye (its flames stay under TOP)
EYE_TILT = 16.0                    # tilted down, looking at the camera / the land
EX, EZ = 1.25, 1.75                # half-width / half-height of the Eye


def eye_matrix():
    return Matrix.Translation(EYE_C) @ Matrix.Rotation(math.radians(EYE_TILT), 4, 'X')


def eye_point(x, z, y=0.0):
    v = eye_matrix() @ Vector((x, y, z))
    return (v.x, v.y, v.z)


def build_eye(b):
    import random
    rng = random.Random(1616)
    eye = eye_matrix()

    def ellipsoid(mat, cy, sx, sy, sz, n=24, rings=16):
        prof = [(math.cos(math.pi * i / rings - math.pi / 2), math.sin(math.pi * i / rings - math.pi / 2))
                for i in range(rings + 1)]
        prof[0], prof[-1] = (0.0, -1.0), (0.0, 1.0)
        lathe(b, mat, prof, n, smooth=True, M=eye @ T(0.0, cy, 0.0, s=(sx, sy, sz)))

    ellipsoid('eyerim', 0.15, EX, 0.6, EZ)                   # the fiery outer shell
    ellipsoid('eyeflame', -0.06, EX * 0.86, 0.5, EZ * 0.88)
    ellipsoid('iris', -0.22, EX * 0.66, 0.4, EZ * 0.74)      # glazed yellow-orange iris
    ellipsoid('core', -0.38, EX * 0.36, 0.3, EZ * 0.56, n=16, rings=12)
    ellipsoid('pupil', -0.62, 0.14, 0.2, EZ * 0.62, n=10, rings=10)   # the black slit
    P = eye_point
    nfl = 18                                                  # tongues of fire licking out from the rim
    for k in range(nfl):
        phi = 2 * math.pi * k / nfl
        cx, cz = math.cos(phi), math.sin(phi)
        up = 0.6 + 0.4 * cz
        L = (0.5 + 0.45 * up) * rng.uniform(0.8, 1.15) * (1.0 - 0.4 * max(0.0, cz))
        base = (EX * 0.92 * cx, EZ * 0.92 * cz)
        mid = (base[0] + cx * L * 0.55, base[1] + cz * L * 0.45 + L * 0.35 * up)
        tip = (base[0] + cx * L * 0.85 + rng.uniform(-0.12, 0.12), base[1] + cz * L * 0.6 + L * 0.9 * up)
        curve(b, 'eyeflame' if k % 3 else 'lava', [P(*base, y=0.08), P(*mid, y=0.04), P(*tip, y=0.0)], 0.22, 0.0,
              n=6, smooth=True)
    for k in range(5):                                        # a crest of flame on top (kept under TOP)
        x = (k - 2) * 0.24
        curve(b, 'eyeflame' if k % 2 else 'lava', [P(x, EZ * 0.8, 0.04), P(x * 1.1, EZ + 0.15), P(x * 1.2, EZ + 0.3)],
              0.2, 0.0, n=6, smooth=True)


# extra preview views: the game camera's angle, and a close-up of the Eye
PREVIEW = [((0, -42, 34), (0, 0, 10), 35), ((3, -12, 23), (0, 0, 21), 40)]
