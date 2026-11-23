"""Barad-dûr, the Dark Tower of Sauron: the landmark of the city named Barad-dûr.

Authored in WORLD units (see landmarks.ENVELOPE): origin = tile centre, ground z = 0, -Y = south =
towards the game camera. The city hexagon is pointy-top: flat sides east/west 24 units from the
centre, corners north/south 27.7. The whole model must stay inside the hexagon and under z = 48.

Lore cues (The Lord of the Rings; the films for the crown and the Eye):
  * "rising black, blacker and darker than the vast shades amid which it stood, the cruel pinnacles
    and iron crown of the topmost tower of Barad-dûr": a fortress of black stone and iron on
    immense foundations, "battlement upon battlement", "tower upon tower";
  * the walls of Barad-dûr, with spiked bastions, and its gates glowing with the fires within;
  * the crown of two great curved prongs cradling the Eye: "the Eye was rimmed with fire, but
    was itself glazed, yellow as a cat's, watchful and intent, and the black slit of its pupil
    opened on a pit, a window into nothing".
"""
import math

from mathutils import Matrix, Vector

from blib import material, hexcol as h, box, lathe, strut, curve, T

HEX_IN = 24.0
COS30 = math.cos(math.radians(30))


def corner_r(inr):
    """Radius of a hexagon corner for a given inradius."""
    return inr / COS30


def hex_lathe(b, mat, profile_in, z=0.0):
    """Hexagonal 'lathe' aligned with the tile: profile radii are INRADII (flat sides E/W)."""
    lathe(b, mat, [(corner_r(r) if r > 0 else 0.0, hz) for r, hz in profile_in], n=6, z=z, smooth=False,
          a0=30.0, a1=390.0)


def side_frame(k, inr):
    """Centre, direction along the wall and wall length of hexagon side k (outward normal at 60k deg)."""
    a = math.radians(60 * k)
    c = Vector((inr * math.cos(a), inr * math.sin(a), 0.0))
    d = Vector((-math.sin(a), math.cos(a), 0.0))
    return c, d, 2 * inr * math.tan(math.radians(30)), 60 * k + 90


def build(b, eye=True):
    rng = b.rng
    # --- palette: black stone and iron with enough value range to read in the game's lighting
    material('ashplain', h('3b3631'), h('2a2622'), noise=1.4)
    material('blackrock', h('2b2826'), h('1b1a19'), noise=2.0)
    material('blackstone', h('2c2b2e'), h('1c1b1e'), noise=1.0, courses=1.2, course_dark=0.62)
    material('darkstone', h('232226'), h('17161a'), noise=1.2, courses=1.6, course_dark=0.7)
    material('iron', h('34333a'), h('26252b'), noise=3.0, spec=0.55, refl=40)
    material('lava', h('ff7a1e'), h('e2400c'), noise=3.0)
    material('ember', h('c8360c'), h('8f1f06'), noise=2.5)
    material('eyerim', h('d8300a'), h('9c1a04'), noise=3.0)
    material('eyeflame', h('ff6414'), h('f23c0a'), noise=3.5)
    material('iris', h('ffa21c'), h('ff7a12'), noise=2.5)
    material('core', h('fff0a0'), h('ffd24a'), noise=2.0)
    material('pupil', h('050304'))

    # ================================================================ 1. the ground: Gorgoroth plinth
    # covers the whole tile; its rim sinks below the game's ground so slopes never show a gap
    hex_lathe(b, 'ashplain', [(0, -3.0), (23.6, -3.0), (23.2, 0.3), (22.2, 1.2), (0, 1.2)])
    # glowing fissures in the ash between the outer wall and the tile edge
    for k in range(12):
        a = math.radians(rng.uniform(0, 360))
        r = rng.uniform(20.6, 21.6)
        x, y = r * math.cos(a), r * math.sin(a)
        heading = math.degrees(a) + 90 + rng.uniform(-25, 25)
        for _ in range(rng.randint(3, 5)):
            L = rng.uniform(1.0, 1.8)
            nx, ny = x + L * math.cos(math.radians(heading)), y + L * math.sin(math.radians(heading))
            if not (19.8 < math.hypot(nx, ny) < 21.8):
                break
            box(b, 'lava', (x + nx) / 2, (y + ny) / 2, 1.05, L + 0.1, rng.uniform(0.18, 0.32), 0.25, rz=heading)
            x, y = nx, ny
            heading += rng.uniform(-35, 35)

    # ================================================================ 2. the outer wall (follows the hexagon)
    WIN, WZ0, WZ1 = 19.0, 1.2, 6.2
    hex_lathe(b, 'blackrock', [(20.8, 0.0), (19.8, 1.2), (0, 1.2)])            # battered footing
    for k in range(6):
        c, d, L, rz = side_frame(k, WIN)
        box(b, 'darkstone', c.x, c.y, WZ0, L - 2.0, 1.6, WZ1 - WZ0, rz=rz)
        # crenellations
        n = 9
        for i in range(n):
            t = (i + 0.5) / n - 0.5
            p = c + d * (t * (L - 3.0)) + Vector((math.cos(math.radians(60 * k)), math.sin(math.radians(60 * k)), 0)) * 0.55
            box(b, 'darkstone', p.x, p.y, WZ1, 0.9, 0.5, 0.9, rz=rz)
        # wall buttresses with spikes
        for t in (-0.25, 0.25):
            p = c + d * (t * L)
            o = Vector((math.cos(math.radians(60 * k)), math.sin(math.radians(60 * k)), 0))
            strut(b, 'darkstone', tuple(p + o * 1.9 + Vector((0, 0, 0.4))), tuple(p + o * 0.6 + Vector((0, 0, WZ1 - 0.4))),
                  0.75, 0.45, n=4, smooth=False)
            strut(b, 'iron', tuple(p + o * 0.9 + Vector((0, 0, WZ1 - 1.4))), tuple(p + o * 2.9 + Vector((0, 0, WZ1 - 2.6))),
                  0.28, 0.0, n=4, smooth=False)
    # the gate on the south-east face (towards the camera): a black arch glowing with the forges within
    c, d, L, rz = side_frame(5, WIN)
    o = Vector((math.cos(math.radians(300)), math.sin(math.radians(300)), 0))
    g = c + o * 0.85
    box(b, 'lava', g.x, g.y, WZ0, 2.4, 0.2, 3.0, rz=rz)
    for s in (-1, 1):
        p = c + d * (s * 2.2) + o * 1.2
        lathe(b, 'darkstone', [(1.3, 0.0), (1.05, 7.2), (1.4, 7.6), (1.4, 8.4), (0, 8.4)], n=6, x=p.x, y=p.y,
              z=WZ0, smooth=False)
        strut(b, 'iron', (p.x, p.y, WZ0 + 8.4), (p.x, p.y, WZ0 + 10.6), 0.8, 0.0, n=6, smooth=False)
    # corner bastions: squat spiked towers at the six corners of the wall
    for k in range(6):
        a = math.radians(30 + 60 * k)
        rr = corner_r(WIN) - 0.6
        x, y = rr * math.cos(a), rr * math.sin(a)
        top = 8.6 + 1.2 * (k % 2)
        lathe(b, 'darkstone', [(2.5, 0.0), (2.1, top - 1.6), (2.7, top - 1.0), (2.7, top), (0, top)], n=8,
              x=x, y=y, z=0.6, smooth=False)
        for s in range(8):
            sa = math.radians(45 * s + 22.5)
            box(b, 'darkstone', x + 2.45 * math.cos(sa), y + 2.45 * math.sin(sa), 0.6 + top, 0.7, 0.7, 0.8,
                rz=math.degrees(sa))
        strut(b, 'iron', (x, y, 0.6 + top), (x, y, 0.6 + top + 3.4), 1.1, 0.0, n=6, smooth=False)
        for s in range(4):
            sa = math.radians(90 * s + 45 + 60 * k)
            zt = 0.6 + top - 0.8
            strut(b, 'iron', (x + 2.4 * math.cos(sa), y + 2.4 * math.sin(sa), zt),
                  (x + 3.5 * math.cos(sa), y + 3.5 * math.sin(sa), zt - 1.3), 0.3, 0.0, n=4, smooth=False)

    # ================================================================ 3. the foundations and inner terrace
    lathe(b, 'blackrock', [(17.5, 0.8), (16.2, 3.2), (14.6, 5.4), (13.4, 7.0), (0, 7.0)], n=14, smooth=False,
          jitter=0.06)
    for k in range(16):                                   # jagged rock spurs breaking through the terrace
        a = math.radians(360.0 * k / 16 + rng.uniform(-7, 7))
        r = rng.uniform(15.2, 16.8)
        x, y = r * math.cos(a), r * math.sin(a)
        strut(b, 'blackrock', (x, y, 0.8), (x * 0.92, y * 0.92, rng.uniform(5.0, 8.0)), rng.uniform(0.9, 1.4), 0.0,
              n=5, smooth=False)
    # inner wall ring
    lathe(b, 'darkstone', [(13.6, 6.6), (13.2, 10.0), (13.9, 10.4), (13.9, 11.0), (0, 11.0)], n=18, smooth=False)
    for k in range(30):
        a = math.radians(12 * k)
        box(b, 'darkstone', 13.6 * math.cos(a), 13.6 * math.sin(a), 11.0, 0.6, 0.9, 0.7, rz=12 * k)
    # lesser towers about the foot of the great tower, joined to it by flying buttresses
    for k in range(6):
        a = math.radians(60 * k + 30)
        x, y = 12.2 * math.cos(a), 12.2 * math.sin(a)
        top = 20.0 + 3.0 * (k % 2)
        lathe(b, 'blackstone', [(2.3, 0.0), (1.85, top - 9.5), (2.5, top - 9.0), (2.5, top - 8.0), (0, top - 8.0)],
              n=8, x=x, y=y, z=7.0, smooth=False)
        zt = 7.0 + top - 8.0
        lathe(b, 'iron', [(1.7, 0.0), (0.0, 4.6)], n=8, x=x, y=y, z=zt, smooth=False)       # spire
        for s in range(6):
            sa = math.radians(60 * s + 30 * k)
            strut(b, 'iron', (x + 2.2 * math.cos(sa), y + 2.2 * math.sin(sa), zt - 0.3),
                  (x + 3.3 * math.cos(sa), y + 3.3 * math.sin(sa), zt + 1.6), 0.28, 0.0, n=4, smooth=False)
        box(b, 'lava', x + 1.95 * math.cos(a), y + 1.95 * math.sin(a), zt - 4.5, 0.5, 0.25, 1.4,
            rz=math.degrees(a) + 90)
        # flying buttress to the great tower
        ra = math.atan2(y, x)
        curve(b, 'darkstone', [(x - 1.6 * math.cos(ra), y - 1.6 * math.sin(ra), zt - 3.0),
                               (8.6 * math.cos(ra), 8.6 * math.sin(ra), zt - 1.2),
                               (7.4 * math.cos(ra), 7.4 * math.sin(ra), zt + 2.4)], 0.55, 0.45, n=4, smooth=False)

    # ================================================================ 4. the great tower
    tiers = [(9.4, 7.0, 16.8), (7.6, 16.8, 25.0), (6.1, 25.0, 31.2), (4.7, 31.2, 35.0)]
    N = 12
    for i, (r, z0, z1) in enumerate(tiers):
        hgt = z1 - z0
        lathe(b, 'blackstone', [(r, 0.0), (r * 0.9, hgt - 1.4), (r * 1.12, hgt - 0.8), (r * 1.12, hgt), (0.0, hgt)],
              n=N, z=z0, smooth=False)
        # battlement
        for k in range(N):
            a = math.radians(360.0 * k / N + 15)
            box(b, 'darkstone', r * 1.09 * math.cos(a), r * 1.09 * math.sin(a), z1, 0.6, 0.9, 0.8,
                rz=math.degrees(a))
        for k in range(N):
            a = math.radians(360.0 * k / N + (15 if i % 2 else 0))
            c, s = math.cos(a), math.sin(a)
            # vertical ribs, flaring at the foot
            strut(b, 'iron', (r * 1.02 * c, r * 1.02 * s, z0), (r * 0.92 * c, r * 0.92 * s, z1 - 1.3),
                  0.42, 0.26, n=4, smooth=False)
            # down-turned spikes under the battlement
            strut(b, 'iron', (r * 1.08 * c, r * 1.08 * s, z1 - 0.7), ((r + 2.6) * c, (r + 2.6) * s, z1 - 3.0),
                  0.3, 0.0, n=4, smooth=False)
        # fiery window slits all round, more of them on the side facing the camera
        for k in range(N // 2 + 1):                     # the half facing the camera (south)
            a = math.radians(180.0 + 360.0 * k / N + 15)
            for zz in (z0 + hgt * 0.35, z0 + hgt * 0.62) if hgt > 6 else (z0 + hgt * 0.45,):
                rr = r * (1.0 - 0.1 * (zz - z0) / hgt) - 0.02
                box(b, 'lava', rr * math.cos(a), rr * math.sin(a), zz, 0.5, 0.22, 1.25, rz=math.degrees(a) + 90)

    # ================================================================ 5. the iron crown
    zc = 35.0
    for s in (-1, 1):
        # the great prongs: rise outward, then curve inward over the Eye
        pts = [(s * 3.6, 0.0, zc - 0.5), (s * 5.4, 0.3, zc + 3.0), (s * 6.0, 0.4, zc + 6.5),
               (s * 5.4, 0.3, zc + 9.2), (s * 3.9, 0.1, zc + 11.0), (s * 2.5, -0.1, zc + 11.8)]
        curve(b, 'iron', pts, 1.9, 0.0, n=6, smooth=False)
        # serrated spines on the outer edge
        for zz, out in ((zc + 2.6, 7.4), (zc + 5.0, 8.1), (zc + 7.4, 7.8), (zc + 9.4, 6.6)):
            inner = Vector((s * (5.6 if zz < zc + 8 else 4.8), 0.3, zz))
            strut(b, 'iron', tuple(inner), (s * out, 0.35, zz + 1.6), 0.38, 0.0, n=4, smooth=False)
        # lesser rear prongs
        curve(b, 'iron', [(s * 2.2, 2.0, zc - 0.3), (s * 3.2, 3.2, zc + 4.5), (s * 2.6, 3.4, zc + 8.0)], 0.9, 0.0,
              n=5, smooth=False)
        # front talons
        curve(b, 'iron', [(s * 2.6, -1.6, zc - 0.3), (s * 3.6, -2.6, zc + 2.6), (s * 3.0, -3.0, zc + 4.6)], 0.6,
              0.0, n=4, smooth=False)
    lathe(b, 'iron', [(5.0, 0.0), (4.4, 0.8), (3.2, 1.2), (0, 1.2)], n=N, z=zc, smooth=False)       # crown platform

    # ================================================================ 6. the Eye of Sauron
    if eye:
        build_eye(b)


# ==================================================================== the Eye (a separate, animated part)
EYE_C = (0.0, -0.4, 41.0)           # centre of the Eye = the pivot it turns about (vertical axis)
EYE_TILT = 16.0                      # tilted down, looking at the camera / the land
EX, EZ = 3.1, 4.6                    # half-width / half-height of the Eye


def eye_matrix():
    return Matrix.Translation(EYE_C) @ Matrix.Rotation(math.radians(EYE_TILT), 4, 'X')


def eye_point(x, z, y=0.0):
    v = eye_matrix() @ Vector((x, y, z))
    return (v.x, v.y, v.z)


def build_eye(b):
    import random
    rng = random.Random(1616)
    material('eyerim', h('d8300a'), h('9c1a04'), noise=3.0)
    material('eyeflame', h('ff6414'), h('f23c0a'), noise=3.5)
    material('lava', h('ff7a1e'), h('e2400c'), noise=3.0)
    material('ember', h('c8360c'), h('8f1f06'), noise=2.5)
    material('iris', h('ffa21c'), h('ff7a12'), noise=2.5)
    material('core', h('fff0a0'), h('ffd24a'), noise=2.0)
    material('pupil', h('050304'))
    eye = eye_matrix()

    def ellipsoid(mat, cy, sx, sy, sz, n=16, rings=12):
        prof = [(math.cos(math.pi * i / rings - math.pi / 2), math.sin(math.pi * i / rings - math.pi / 2))
                for i in range(rings + 1)]
        prof[0], prof[-1] = (0.0, -1.0), (0.0, 1.0)
        lathe(b, mat, prof, n, smooth=False, M=eye @ T(0.0, cy, 0.0, s=(sx, sy, sz)))

    ellipsoid('eyerim', 0.35, EX, 1.5, EZ)                  # the fiery outer shell
    ellipsoid('eyeflame', -0.15, EX * 0.86, 1.25, EZ * 0.88)
    ellipsoid('iris', -0.55, EX * 0.66, 1.0, EZ * 0.74)      # glazed yellow-orange iris
    ellipsoid('core', -0.95, EX * 0.36, 0.75, EZ * 0.56, n=12, rings=10)
    ellipsoid('pupil', -1.55, 0.34, 0.5, EZ * 0.62, n=8, rings=8)   # the black slit

    P = eye_point
    # tongues of fire licking out from the rim and streaming upward
    nfl = 22
    for k in range(nfl):
        phi = 2 * math.pi * k / nfl
        cx, cz = math.cos(phi), math.sin(phi)
        up = 0.6 + 0.4 * cz                                   # flames lick upward
        L = (1.3 + 1.1 * up) * rng.uniform(0.8, 1.15) * (1.0 - 0.4 * max(0.0, cz))   # the crest is added below
        base = (EX * 0.92 * cx, EZ * 0.92 * cz)
        mid = (base[0] + cx * L * 0.55, base[1] + cz * L * 0.45 + L * 0.35 * up)
        tip = (base[0] + cx * L * 0.85 + rng.uniform(-0.3, 0.3), base[1] + cz * L * 0.6 + L * 0.9 * up)
        mat = 'eyeflame' if k % 3 else 'lava'
        curve(b, mat, [P(*base, y=0.2), P(*mid, y=0.1), P(*tip, y=0.0)], 0.55, 0.0, n=4, smooth=False)
    # a crest of flame rising from the top of the Eye
    for k in range(7):
        x = (k - 3) * 0.55
        top = EZ + 0.9 + (1.0 - abs(k - 3) / 3.0) * 0.6
        curve(b, 'eyeflame' if k % 2 else 'lava', [P(x, EZ * 0.8, 0.1), P(x * 1.15, EZ + 0.6), P(x * 1.25, top)],
              0.5, 0.0, n=4, smooth=False)
    # embers falling from the Eye onto the crown
    for k in range(5):
        x = (k - 2) * 0.9
        strut(b, 'ember', P(x, -EZ * 0.85, 0.2), P(x * 1.2, -EZ * 1.05, 0.1), 0.35, 0.0, n=4, smooth=False)


def rig():
    """Bones of the animated Eye, in world units: (name, parent, world position, effect key or None).
    'eyeroot' (origin) and 'eyepivot' (EYE_C, turned by the animation) are added by the writer.
    Effect keys are defined in landmarks.EFFECTS."""
    bones = []
    for k in range(8):                                    # a ring of fire round the rim, behind the Eye
        a = math.radians(45 * k + 22.5)
        bones.append(('fxfire%d' % k, 'eyepivot', eye_point(EX * 1.02 * math.cos(a), EZ * 0.98 * math.sin(a), 0.35),
                      'EYE_FIRE'))
    bones.append(('fxcore', 'eyepivot', eye_point(0.0, 0.4, 1.3), 'EYE_FIRE_BIG'))   # the blaze behind it
    bones.append(('fxbeam', 'eyeroot', EYE_C, 'EYE_BEAM'))  # static: the beam effect turns by itself
    return bones


def _gaze(t):
    """Yaw of the Eye in degrees (+ = towards the screen's right) over one 6 s loop:
    searches the right (with a flick further right), snaps left for a second, swings back."""
    keys = [(0.00, 40.0, 'lin'), (1.20, 44.0, 'ease'), (1.45, 54.0, 'lin'), (2.70, 50.0, 'ease'),
            (3.02, -42.0, 'lin'), (4.02, -47.0, 'ease'), (4.80, 38.0, 'lin'), (6.00, 40.0, None)]
    t = t % 6.0
    for (t0, a0, kind), (t1, a1, _) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0)
            if kind == 'ease':
                u = u * u * u * (u * (6 * u - 15) + 10)      # smootherstep
            return a0 + (a1 - a0) * u
    return keys[-1][1]


# one loop = 6 s: the same length as the stock decision trees' animation sequences
GAZE = dict(fn=_gaze, T=6.0, spans=60)


# extra preview views: the game camera's angle, and a close-up of the Eye
PREVIEW = [((0, -70, 62), (0, 0, 20), 35), ((6, -22, 44), (0, 0, 42), 40)]
