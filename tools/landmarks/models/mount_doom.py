"""Mount Doom (Orodruin, Amon Amarth): the landmark of the city NAMED Mount Doom.

A new procedural volcano, built like Barad-dur (same palette of black stone, iron, ember and lava,
flat shading, world units) and wired the same way: a static model + an animated skinned part +
effects on bones (landmarks.EFFECTS), played by the United Nations decision tree.

Authored in WORLD units (see landmarks.ENVELOPE): origin = tile centre, ground z = 0, -Y = south =
towards the game camera. The city hexagon is pointy-top: flat sides east/west 24 units from the
centre, corners north/south 27.7. Everything stays inside the hexagon and under z = 48.

Lore cues (The Return of the King, "Mount Doom"):
  * "its huge base rose some three thousand feet above the plain, and above that, half as high
    again, its tall central cone, like a vast oast or chimney, capped with a jagged crater": a broad
    ash shoulder carrying a steep central cone, the crater jagged and breached;
  * the fires below, "great rivers of molten rock" running down its flanks, the "reek" and ash
    of the eruption (the stock Krakatoa eruption particles + fire in the crater);
  * Sauron's Road climbing from the east to the Sammath Naur, the Chambers of Fire: a dark door in
    the side of the cone, lit red from within;
  * the plain of Gorgoroth round about: black slag, cinder cones and smoking fissures;
  * the Nazgul on their winged steeds circling above (the animated part: three fell beasts).
"""
import math

from mathutils import Matrix, Vector

from blib import material, hexcol as h, box, lathe, strut, curve, blob, T

HEX_IN = 23.85                 # just inside the envelope's 24 (build_models.in_hex)
COS30 = math.cos(math.radians(30))
SOUTH = -90.0

# ------------------------------------------------------------------------------- the radial profile
# (r, z): crater floor, inner wall, jagged rim, central cone, the shoulder ("huge base"), the apron
PROFILE = [(0.0, 35.4), (2.6, 35.6), (3.5, 36.2), (4.1, 38.3), (4.7, 40.2), (5.3, 39.8), (6.2, 36.6),
           (7.6, 31.0), (9.0, 25.6), (10.0, 22.6), (11.0, 21.0), (12.4, 20.2), (13.8, 19.0), (15.2, 16.2),
           (16.8, 12.4), (18.4, 8.4), (19.9, 4.9), (21.2, 2.3), (22.4, 0.7), (23.3, 0.0), (24.0, -0.4), (40.0, -0.4)]
R_RIM = 4.7
BREACH = math.radians(-118.0)        # the rim is broken here: lava spills towards the camera's left
DOOR_A = math.radians(-28.0)         # the Sammath Naur faces east-south-east (towards the camera and Barad-dur)
DOOR_R = 10.5

RINGS = [0.0, 1.4, 2.6, 3.3, 3.8, 4.25, 4.7, 5.15, 5.7, 6.4, 7.2, 8.0, 8.8, 9.6, 10.4, 11.2, 12.0, 12.8,
         13.6, 14.5, 15.4, 16.3, 17.2, 18.1, 19.0, 19.9, 20.8, 21.7, 22.6, 23.4, 1e9]   # 1e9 = hexagon edge
NA = 84                               # spokes (multiple of 12: the hexagon's corners are vertices)


def hex_radius(a):
    """Centre -> hexagon edge along direction a (radians). Flat sides face 0, 60, ... degrees."""
    d = (math.degrees(a) + 30.0) % 60.0 - 30.0
    return HEX_IN / math.cos(math.radians(d))


def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def _profile(r):
    """Monotone (Fritsch-Carlson) cubic through PROFILE."""
    P = PROFILE
    if r <= P[0][0]:
        return P[0][1]
    for i in range(len(P) - 1):
        (x0, y0), (x1, y1) = P[i], P[i + 1]
        if r <= x1:
            def slope(k):
                if k == 0 or k == len(P) - 1:
                    return 0.0
                d0 = (P[k][1] - P[k - 1][1]) / (P[k][0] - P[k - 1][0])
                d1 = (P[k + 1][1] - P[k][1]) / (P[k + 1][0] - P[k][0])
                return 0.0 if d0 * d1 <= 0 else 2.0 / (1.0 / d0 + 1.0 / d1)
            hh = x1 - x0
            t = (r - x0) / hh
            m0, m1 = slope(i) * hh, slope(i + 1) * hh
            t2, t3 = t * t, t * t * t
            return ((2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * y1 +
                    (t3 - t2) * m1)
    return P[-1][1]


def _adiff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


# ------------------------------------------------------------------------------- lava rivers
# each: (start radius, end radius, start angle deg, drift deg over the run, wiggle amplitude deg,
#        width at the source, width at the foot, ends in a pool?)
RIVERS = [
    (4.9, 21.0, -118.0, -10.0, 5.0, 1.35, 1.0, True),     # out of the breach, down the camera-facing flank
    (8.8, 20.2, -68.0, 8.0, 4.0, 0.95, 0.85, True),        # from a flank vent below the door
    (9.4, 19.6, -165.0, -8.0, 4.5, 0.9, 0.75, True),       # west-south-west
    (5.6, 18.6, 145.0, 10.0, 4.0, 1.0, 0.7, False),        # behind, north-west (seen over the shoulder)
    (10.2, 19.2, 32.0, -6.0, 3.0, 0.8, 0.65, False),       # north-east
]


def river_angle(rv, r):
    r0, r1, a0, drift, wig, _, _, _ = rv
    t = (r - r0) / (r1 - r0)
    return math.radians(a0 + drift * t + wig * math.sin(0.9 * r + a0))


def river_width(rv, r):
    r0, r1, _, _, _, w0, w1, _ = rv
    t = min(1.0, max(0.0, (r - r0) / (r1 - r0)))
    return w0 + (w1 - w0) * t


def _river_dist(x, y):
    """(distance to the nearest river's centre line / its width, river) for carving the channels."""
    r, a = math.hypot(x, y), math.atan2(y, x)
    best = (99.0, None)
    for rv in RIVERS:
        if rv[0] - 0.3 <= r <= rv[1] + 0.5:
            d = abs(_adiff(a, river_angle(rv, r))) * r / max(0.3, river_width(rv, r))
            if d < best[0]:
                best = (d, rv)
    return best


# ------------------------------------------------------------------------------- the height field
def height(x, y):
    r, a = math.hypot(x, y), math.atan2(y, x)
    z = _profile(r)
    if r < 0.01:
        return z
    # the shoulder is lumpy: the "huge base" is not a perfect cone
    shoulder = _smooth((r - 7.0) / 3.0) * _smooth((23.0 - r) / 5.0)
    z += shoulder * (1.1 * math.sin(3 * a + 0.8) + 0.7 * math.sin(5 * a + 2.3) + 0.35 * math.sin(8 * a + 0.4))
    # radial gullies and ridges on the flanks
    flank = _smooth((r - 5.4) / 1.5) * _smooth((22.5 - r) / 3.0)
    g = 0.045 * math.sin(11 * a + 0.35 * r) + 0.025 * math.sin(17 * a + 1.7 + 0.2 * r)
    z += flank * g * max(0.0, z) * 0.9
    # the jagged rim, breached towards the lava river
    rimband = math.exp(-((r - R_RIM) / 1.0) ** 2)
    jag = 0.8 * math.sin(7 * a + 0.5) + 0.5 * math.sin(13 * a + 2.0) + 0.35 * math.sin(23 * a + 0.9)
    z += rimband * jag
    z -= 2.6 * math.exp(-(_adiff(a, BREACH) / 0.28) ** 2) * math.exp(-((r - R_RIM) / 1.3) ** 2)
    # the river channels
    d, rv = _river_dist(x, y)
    if rv is not None:
        z -= 0.45 * math.exp(-d * d) * _smooth((r - rv[0]) / 0.8)
    # a ledge for the Sammath Naur door
    dd = math.hypot(x - DOOR_R * math.cos(DOOR_A), y - DOOR_R * math.sin(DOOR_A))
    z = z + (_profile(DOOR_R + 0.6) + 0.2 - z) * math.exp(-(dd / 1.4) ** 2) * 0.6
    # sink below the game's ground at the tile edge
    re = hex_radius(a)
    z = -0.4 + (z + 0.4) * _smooth((re - r) / 1.5)
    return z


def _ring_r(rr, a):
    """Ring radius along direction a: circles in the middle, the hexagon at the edge."""
    re = hex_radius(a)
    if rr >= 1e8:
        return re
    s = _smooth((rr - 15.0) / 8.4)
    return rr * (1.0 - s) + min(rr * re / HEX_IN, re - 0.02) * s


def surface(b, matfn):
    """The volcano + plain as one polar height field over the hexagon (+ a skirt under the rim)."""
    rows, V = [], []
    for i, rr in enumerate(RINGS):
        row = []
        if rr == 0.0:
            V.append((0.0, 0.0, height(0.0, 0.0)))
            row = [0] * NA
        else:
            for j in range(NA):
                a = 2 * math.pi * j / NA
                r = _ring_r(rr, a)
                x, y = r * math.cos(a), r * math.sin(a)
                V.append((x, y, height(x, y)))
                row.append(len(V) - 1)
        rows.append(row)
    F, M = [], []
    for i in range(len(rows) - 1):
        for j in range(NA):
            j2 = (j + 1) % NA
            f = (rows[0][0], rows[1][j], rows[1][j2]) if i == 0 else \
                (rows[i][j], rows[i + 1][j], rows[i + 1][j2], rows[i][j2])
            ps = [V[k] for k in f]
            c = [sum(p[k] for p in ps) / len(ps) for k in range(3)]
            e1 = Vector(ps[1]) - Vector(ps[0])
            e2 = Vector(ps[-1]) - Vector(ps[0])
            n = e1.cross(e2)
            if n.z < 0:
                f = tuple(reversed(f))
                n = -n
            slope = math.hypot(n.x, n.y) / (abs(n.z) + 1e-6)
            F.append(f)
            M.append(matfn(c[0], c[1], c[2], slope))
    base = len(b.verts)
    b.verts.extend(V)
    for f, m in zip(F, M):
        b.faces.append(tuple(base + k for k in f))
        b.fmat.append(b._mi(m))
        b.fsmooth.append(False)
    last = rows[-1]
    for j in range(NA):
        p, q = V[last[j]], V[last[(j + 1) % NA]]
        b.add([p, q, (q[0], q[1], -3.0), (p[0], p[1], -3.0)], [(1, 0, 3, 2)], 'slag')


def ribbon(b, mat, pts, widths, lift):
    """A flat band draped on the height field along the polyline pts [(x, y)], facing up."""
    V, F = [], []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        p0 = pts[max(0, i - 1)]
        p1 = pts[min(n - 1, i + 1)]
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        ln = math.hypot(dx, dy) or 1.0
        lx, ly = -dy / ln, dx / ln
        w = widths[i] / 2
        for s in (1, -1):                       # left, right
            px, py = x + s * lx * w, y + s * ly * w
            V.append((px, py, height(px, py) + lift))
    for i in range(n - 1):
        F.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    b.add(V, F, mat)


def river_points(rv, step=0.55):
    r0, r1 = rv[0], rv[1]
    k = max(2, int((r1 - r0) / step))
    out = []
    for i in range(k + 1):
        r = r0 + (r1 - r0) * i / k
        a = river_angle(rv, r)
        out.append((r * math.cos(a), r * math.sin(a), r))
    return out


def pool(b, mat, x, y, rx, ry, rz, lift, n=12, rng=None):
    """A flat irregular lava pool draped on the ground."""
    V = [(x, y, height(x, y) + lift)]
    for k in range(n):
        a = 2 * math.pi * k / n
        f = 1.0 + (rng.uniform(-0.18, 0.18) if rng else 0.0)
        ca, sa = math.cos(a) * rx * f, math.sin(a) * ry * f
        c, s = math.cos(rz), math.sin(rz)
        px, py = x + ca * c - sa * s, y + ca * s + sa * c
        V.append((px, py, height(px, py) + lift))
    b.add(V, [(0, k + 1, (k + 1) % n + 1) for k in range(n)], mat)


# ------------------------------------------------------------------------------- the static volcano
def build(b, eye=True):
    rng = b.rng
    # --- palette: Barad-dur's black stone, iron and fire, plus the volcano's ash and slag
    material('ash', h('3f3934'), zramp=[(0.0, h('4b433b')), (6.0, h('433c36')), (14.0, h('38322e')),
                                        (21.0, h('3f3a36')), (26.0, h('2e2927')), (34.0, h('2a2524')),
                                        (38.0, h('3e2621')), (41.0, h('6a2c18'))],
             slope_color=h('221e1d'), slope_start=0.5)
    material('slag', h('2b2826'), h('1b1a19'), noise=2.0)                    # = Barad-dur's blackrock
    material('blackrock', h('2b2826'), h('1b1a19'), noise=2.0)
    material('darkstone', h('232226'), h('17161a'), noise=1.2, courses=1.6, course_dark=0.7)
    material('iron', h('34333a'), h('26252b'), noise=3.0, spec=0.55, refl=40)
    material('crust', h('3a1c12'), h('24120c'), noise=3.0, ao=False)          # cooling lava crust
    material('ember', h('c8360c'), h('8f1f06'), noise=2.5, ao=False)
    material('lava', h('ff7a1e'), h('e2400c'), noise=3.0, ao=False)
    material('lavahot', h('ffc04a'), h('ff9a2a'), noise=2.0, ao=False)
    material('core', h('fff0a0'), h('ffd24a'), noise=2.0, ao=False)

    def matfn(x, y, z, slope):
        r = math.hypot(x, y)
        if r < 3.3:
            return 'lava'                                      # the lava lake in the crater
        if r < 3.9:
            return 'ember'                                     # its glowing shore
        d, rv = _river_dist(x, y)
        if rv is not None and d < 1.6 and r > rv[0] + 0.2:
            return 'crust'                                     # scorched banks along every river
        return 'ash'

    # ================================================================ 1. the mountain and the plain
    surface(b, matfn)

    # ================================================================ 2. the crater: lava lake, floes, inner glow
    zl = height(0.0, 0.0) + 0.25
    lathe(b, 'lavahot', [(1.4, zl), (0.0, zl + 0.05)], n=14, smooth=False)
    for k in range(7):                                          # dark crust floes drifting on the lake
        a = math.radians(360.0 * k / 7 + rng.uniform(-15, 15))
        r = rng.uniform(1.6, 2.9)
        box(b, 'crust', r * math.cos(a), r * math.sin(a), zl - 0.12, rng.uniform(0.5, 0.9), rng.uniform(0.3, 0.6),
            0.25, rz=rng.uniform(0, 180))
    for k in range(12):                                         # glowing cracks on the inner crater wall
        a = math.radians(30 * k + rng.uniform(-8, 8))
        r0, r1 = 3.7, 4.35
        p0 = (r0 * math.cos(a), r0 * math.sin(a))
        p1 = (r1 * math.cos(a + 0.05), r1 * math.sin(a + 0.05))
        strut(b, 'ember', (p0[0], p0[1], height(*p0) + 0.05), (p1[0], p1[1], height(*p1) - 0.1), 0.16, 0.08,
              n=4, smooth=False)
    # jagged black spires on the rim
    for k in range(14):
        a = math.radians(360.0 * k / 14 + rng.uniform(-9, 9))
        if abs(_adiff(a, BREACH)) < 0.45:
            continue
        r = R_RIM + rng.uniform(-0.2, 0.4)
        x, y = r * math.cos(a), r * math.sin(a)
        z = height(x, y)
        strut(b, 'slag', (x, y, z - 0.5), (x * 1.04, y * 1.04, z + rng.uniform(1.0, 2.4)), rng.uniform(0.45, 0.75),
              0.0, n=4, smooth=False)

    # ================================================================ 3. the rivers of fire
    for rv in RIVERS:
        pts = river_points(rv)
        wid = [river_width(rv, p[2]) for p in pts]
        n = len(pts)
        fade = [min(1.0, (i + 1) / 3.0) for i in range(n)]
        ribbon(b, 'ember', [(p[0], p[1]) for p in pts], [w * 1.75 for w in wid], 0.12)
        ribbon(b, 'lava', [(p[0], p[1]) for p in pts], [w * 1.05 * f for w, f in zip(wid, fade)], 0.22)
        ribbon(b, 'lavahot', [(p[0], p[1]) for p in pts[:max(3, int(n * 0.55))]],
               [w * 0.38 * f for w, f in zip(wid, fade)], 0.3)
        if rv[7]:                                               # the river spreads into a pool on the plain
            x, y, r = pts[-1]
            a = math.atan2(y, x)
            pool(b, 'ember', x, y, 2.4, 1.6, a, 0.1, rng=rng)
            pool(b, 'lava', x, y, 1.7, 1.1, a, 0.2, rng=rng)
        # the vent the river comes from (not for the breach, which pours over the rim)
        if rv[0] > 6.0:
            x, y, _ = pts[0]
            z = height(x, y)
            lathe(b, 'slag', [(1.3, -0.3), (0.95, 0.9), (0.55, 1.05), (0.0, 0.7)], n=8, x=x, y=y, z=z, smooth=False)
            lathe(b, 'lavahot', [(0.5, 0.95), (0.0, 1.0)], n=8, x=x, y=y, z=z, smooth=False)

    # ================================================================ 4. the Sammath Naur and Sauron's Road
    door(b)
    road(b)

    # ================================================================ 5. Gorgoroth: cinder cones, slag, fissures
    for (r, adeg, s) in ((19.6, 118.0, 1.0), (20.2, -140.0, 0.8), (19.0, 62.0, 0.75), (20.6, -24.0, 0.7)):
        a = math.radians(adeg)
        x, y = r * math.cos(a), r * math.sin(a)
        z = height(x, y) - 0.4
        lathe(b, 'slag', [(2.4 * s, 0.0), (1.9 * s, 1.0 * s), (1.0 * s, 2.0 * s), (0.75 * s, 2.0 * s),
                          (0.5 * s, 1.4 * s), (0.0, 1.4 * s)], n=10, x=x, y=y, z=z, smooth=False, jitter=0.08)
        lathe(b, 'ember', [(0.55 * s, 1.5 * s), (0.0, 1.55 * s)], n=8, x=x, y=y, z=z, smooth=False)
    for k in range(26):                                           # black boulders and slag heaps
        a = rng.uniform(-math.pi, math.pi)
        r = rng.uniform(18.0, hex_radius(a) - 1.6)
        x, y = r * math.cos(a), r * math.sin(a)
        if _river_dist(x, y)[0] < 2.2:
            continue
        s = rng.uniform(0.45, 1.05)
        blob(b, 'slag' if k % 3 else 'blackrock', x, y, height(x, y) - 0.25 * s, s, n=6, rings=3, squash=0.7,
             jitter=0.25)
    for k in range(10):                                           # smoking fissures in the slag plain
        a = math.radians(rng.uniform(0, 360))
        r = rng.uniform(17.5, 20.5)
        x, y = r * math.cos(a), r * math.sin(a)
        heading = math.degrees(a) + 90 + rng.uniform(-30, 30)
        pts = [(x, y)]
        for _ in range(rng.randint(3, 5)):
            L = rng.uniform(0.9, 1.6)
            nx, ny = x + L * math.cos(math.radians(heading)), y + L * math.sin(math.radians(heading))
            if math.hypot(nx, ny) > hex_radius(math.atan2(ny, nx)) - 1.0 or _river_dist(nx, ny)[0] < 1.5:
                break
            pts.append((nx, ny))
            x, y = nx, ny
            heading += rng.uniform(-35, 35)
        if len(pts) >= 2:
            w = rng.uniform(0.12, 0.18)
            ribbon(b, 'crust', pts, [w * 4.0] * len(pts), 0.04)
            ribbon(b, 'ember', pts, [w * 2.2] * len(pts), 0.08)
            ribbon(b, 'lava', pts, [w] * len(pts), 0.12)

    # ================================================================ 6. the fell beasts (the animated part)
    if eye:
        build_eye(b)


def door(b):
    """The Sammath Naur: a black gate cut into the cone, red-lit from within, on a ledge of the road."""
    a = DOOR_A
    o = Vector((math.cos(a), math.sin(a), 0.0))           # outward
    t = Vector((-math.sin(a), math.cos(a), 0.0))          # along the slope
    c = Vector((DOOR_R * o.x, DOOR_R * o.y, 0.0))
    z = height(c.x, c.y)
    rz = math.degrees(a) + 90
    # the gate's frame: a jutting block of black stone with a pointed hood, buried in the slope behind
    p = c - o * 0.9
    box(b, 'darkstone', p.x, p.y, z - 0.8, 4.0, 3.0, 5.0, rz=rz)
    hood = c - o * 0.35
    for s in (-1, 1):
        q = hood + t * (s * 1.65)
        strut(b, 'darkstone', (q.x, q.y, z - 0.4), (q.x - o.x * 0.3, q.y - o.y * 0.3, z + 4.4), 0.55, 0.3, n=4,
              smooth=False)
        strut(b, 'iron', (q.x + o.x * 0.3, q.y + o.y * 0.3, z + 4.0), (q.x + o.x * 1.5 + t.x * s * 0.6,
              q.y + o.y * 1.5 + t.y * s * 0.6, z + 5.6), 0.28, 0.0, n=4, smooth=False)
    strut(b, 'darkstone', (hood.x - t.x * 1.9, hood.y - t.y * 1.9, z + 4.2),
          (hood.x + t.x * 1.9, hood.y + t.y * 1.9, z + 4.2), 0.5, 0.5, n=4, smooth=False)
    # the opening: a glowing doorway with a hot core (the Crack of Doom within)
    g = c + o * 0.62
    box(b, 'ember', g.x, g.y, z - 0.1, 2.3, 0.14, 3.6, rz=rz)
    g2 = c + o * 0.7
    box(b, 'lava', g2.x, g2.y, z - 0.1, 1.6, 0.12, 2.9, rz=rz)
    g3 = c + o * 0.77
    box(b, 'lavahot', g3.x, g3.y, z - 0.1, 0.8, 0.1, 1.9, rz=rz)
    # the ledge in front of the door
    ledge = c + o * 1.5
    box(b, 'darkstone', ledge.x, ledge.y, z - 1.2, 3.6, 2.2, 1.35, rz=rz)
    # two spiked iron posts flanking the approach
    for s in (-1, 1):
        q = c + o * 2.3 + t * (s * 1.5)
        zq = z + 0.1
        strut(b, 'iron', (q.x, q.y, zq - 0.3), (q.x, q.y, zq + 2.6), 0.24, 0.12, n=4, smooth=False)
        strut(b, 'iron', (q.x, q.y, zq + 2.6), (q.x + o.x * 0.3, q.y + o.y * 0.3, zq + 3.4), 0.2, 0.0, n=4,
              smooth=False)
        box(b, 'ember', q.x, q.y, zq + 2.2, 0.25, 0.25, 0.25, rz=rz)


# Sauron's Road: from the eastern edge of the tile, up the shoulder in a long switchback, to the door
ROAD = [(23.2, 6.0), (21.4, 1.0), (19.6, -5.0), (18.0, -12.0), (16.7, -21.0), (15.6, -31.0), (14.7, -41.0),
        (14.0, -47.0), (13.3, -44.0), (12.7, -37.0), (12.2, -31.0), (11.9, -28.0)]


def _road_points(step=0.6):
    pts = []
    for (r0, a0), (r1, a1) in zip(ROAD, ROAD[1:]):
        x0, y0 = r0 * math.cos(math.radians(a0)), r0 * math.sin(math.radians(a0))
        x1, y1 = r1 * math.cos(math.radians(a1)), r1 * math.sin(math.radians(a1))
        k = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for i in range(k):
            pts.append((x0 + (x1 - x0) * i / k, y0 + (y1 - y0) * i / k))
    r, a = ROAD[-1]
    pts.append((r * math.cos(math.radians(a)), r * math.sin(math.radians(a))))
    # Chaikin smoothing: no kinks at the switchback
    for _ in range(2):
        sm = [pts[0]]
        for p, q in zip(pts, pts[1:]):
            sm += [(0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]),
                   (0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1])]
        sm.append(pts[-1])
        pts = sm[::2] if len(sm) > 120 else sm
    return pts


def road(b):
    pts = _road_points()
    ribbon(b, 'blackrock', pts, [1.9] * len(pts), 0.16)           # the causeway's bed
    ribbon(b, 'darkstone', pts, [1.3] * len(pts), 0.28)           # the paved road
    # low parapet stones along the outer edge
    for i in range(2, len(pts) - 2, 4):
        x, y = pts[i]
        x2, y2 = pts[i + 1]
        r = math.hypot(x, y)
        dx, dy = x2 - x, y2 - y
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        if nx * x + ny * y < 0:                                   # the side away from the mountain
            nx, ny = -nx, -ny
        px, py = x + nx * 0.85, y + ny * 0.85
        box(b, 'darkstone', px, py, height(px, py), 0.45, 0.35, 0.55, rz=math.degrees(math.atan2(dy, dx)))


# ==================================================================== the fell beasts (the animated part)
# They circle the summit as ONE skinned part turned about the volcano's axis. Three identical beasts
# 120 degrees apart, so one 6 s loop turns the part by 120 degrees and the loop is seamless.
EYE_C = (0.0, 0.0, 43.5)            # the pivot: the volcano's axis, at the beasts' height
ORBIT_R = 14.8
BEASTS = 3
BANK = 24.0                         # degrees, inner wing down


def _beast(b, M, rng):
    """A fell beast with a Nazgul rider, heading +Y, up +Z, wingspan ~10, transformed by M."""
    def P(x, y, z):
        v = M @ Vector((x, y, z))
        return (v.x, v.y, v.z)

    # body, neck, head, tail
    curve(b, 'beast', [P(0, -1.6, 0.0), P(0, -0.4, 0.15), P(0, 0.7, 0.25)], 0.72, 0.5, n=6, smooth=False)
    curve(b, 'beast', [P(0, 0.7, 0.25), P(0, 1.7, 0.75), P(0, 2.6, 0.95)], 0.38, 0.24, n=5, smooth=False)
    strut(b, 'beast', P(0, 2.5, 0.95), P(0, 3.7, 0.7), 0.36, 0.0, n=5, smooth=False)          # beaked head
    strut(b, 'iron', P(0, 2.7, 1.1), P(0, 2.2, 1.7), 0.14, 0.0, n=4, smooth=False)            # crest horn
    curve(b, 'beast', [P(0, -1.6, 0.0), P(0, -3.2, -0.15), P(0.25, -4.6, -0.1), P(0.5, -5.6, 0.1)], 0.42, 0.0,
          n=5, smooth=False)
    # hind legs, tucked
    for s in (-1, 1):
        strut(b, 'beast', P(s * 0.4, -1.0, -0.3), P(s * 0.5, -2.2, -0.75), 0.2, 0.08, n=4, smooth=False)
    # wings: leathery membranes on finger bones, scalloped trailing edge; two-sided (the game culls back faces)
    for s in (-1, 1):
        shoulder = (s * 0.45, 0.35, 0.3)
        wrist = (s * 2.7, 0.85, 0.85)
        tip = (s * 5.4, -0.6, 1.25)
        f2 = (s * 4.0, -1.9, 0.85)
        f3 = (s * 2.4, -2.1, 0.5)
        root = (s * 0.45, -1.5, 0.2)
        mids = [(s * 4.6, -1.0, 1.0), (s * 3.1, -1.65, 0.6), (s * 1.3, -1.55, 0.3)]   # scallops (pulled in)
        ring_ = [shoulder, wrist, tip, mids[0], f2, mids[1], f3, mids[2], root]
        hub = (s * 1.9, -0.4, 0.55)
        V = [P(*hub)] + [P(*p) for p in ring_]
        n = len(ring_)
        F = [(0, k + 1, (k + 1) % n + 1) for k in range(n)]
        # orient the top face up (in the beast's own frame) and add the reversed copy underneath
        a_, b_, c_ = (Vector(V[f]) for f in F[0])
        up = (M.to_3x3() @ Vector((0, 0, 1)))
        if (b_ - a_).cross(c_ - a_).dot(up) < 0:
            F = [tuple(reversed(f)) for f in F]
        b.add(V, F, 'wing')
        dn = M.to_3x3() @ Vector((0, 0, -0.06))
        b.add([(v[0] + dn.x, v[1] + dn.y, v[2] + dn.z) for v in V], [tuple(reversed(f)) for f in F], 'wing')
        # the arm and finger bones along the leading edge and through the membrane
        curve(b, 'beast', [P(*shoulder), P(*wrist), P(*tip)], 0.2, 0.06, n=4, smooth=False)
        strut(b, 'beast', P(*wrist), P(*f2), 0.1, 0.03, n=4, smooth=False)
        strut(b, 'beast', P(*wrist), P(*f3), 0.1, 0.03, n=4, smooth=False)
        strut(b, 'iron', P(*wrist), P(s * 2.8, 1.5, 1.0), 0.12, 0.0, n=4, smooth=False)        # wrist claw
    # the Nazgul: a black hooded rider with a pale crown glint
    strut(b, 'cloak', P(0, 0.05, 0.55), P(0, 0.2, 1.95), 0.5, 0.16, n=6, smooth=False)
    strut(b, 'cloak', P(0, 0.2, 1.85), P(0, 0.35, 2.35), 0.24, 0.0, n=5, smooth=False)
    curve(b, 'cloak', [P(0, -0.15, 1.6), P(0, -0.9, 1.3), P(0.15, -1.5, 0.9)], 0.3, 0.05, n=4, smooth=False)  # cape
    box(b, 'crown', *P(0, 0.33, 2.05), 0.3, 0.3, 0.1)


def beast_matrix(k):
    yaw = 360.0 * k / BEASTS
    return (Matrix.Translation(EYE_C) @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @
            Matrix.Translation((ORBIT_R, 0.0, 0.0)) @ Matrix.Rotation(math.radians(-BANK), 4, 'Y') @
            Matrix.Rotation(math.radians(-6.0), 4, 'X'))                 # nose slightly down: gliding


def build_eye(b):
    """The animated part: three fell beasts on the orbit (the pipeline's 'eye' slot)."""
    import random
    rng = random.Random(1419)
    material('beast', h('2a2427'), h('1a1618'), noise=2.0)
    material('wing', h('3a2a2c'), h('241a1c'), noise=1.5)
    material('cloak', h('141215'), h('0a090b'), noise=1.0)
    material('iron', h('34333a'), h('26252b'), noise=3.0, spec=0.55, refl=40)
    material('crown', h('b8b2a6'), h('8c867a'), noise=1.0, spec=0.7, refl=60)
    for k in range(BEASTS):
        _beast(b, beast_matrix(k), rng)


def rig():
    """Effect bones, in world units: (name, parent, world position, effect key). All hang on the static
    'eyeroot' (they must not circle with the beasts); 'eyepivot' (EYE_C) is turned by the animation."""
    zc = height(0.0, 0.0)
    bones = [('fxerupt', 'eyeroot', (0.0, 0.0, zc + 1.0), 'DOOM_ERUPTION'),          # the ash column
             ('fxerupt2', 'eyeroot', (0.9, -0.6, zc + 0.6), 'DOOM_ERUPTION_SMALL'),  # a second, offset vent
             ('fxcrater', 'eyeroot', (0.0, 0.0, zc + 0.4), 'DOOM_CRATER_FIRE')]
    for k in range(3):                                                                # fire round the lake
        a = math.radians(120 * k + 30)
        bones.append(('fxlake%d' % k, 'eyeroot', (2.2 * math.cos(a), 2.2 * math.sin(a), zc + 0.3), 'DOOM_VENT_FIRE'))
    x, y = (R_RIM + 0.3) * math.cos(BREACH), (R_RIM + 0.3) * math.sin(BREACH)
    bones.append(('fxbreach', 'eyeroot', (x, y, height(x, y) + 0.4), 'DOOM_VENT_FIRE'))
    for i, rv in enumerate(RIVERS):
        if rv[0] > 6.0:                                                             # the flank vents
            x, y, _ = river_points(rv)[0]
            bones.append(('fxvent%d' % i, 'eyeroot', (x, y, height(x, y) + 1.0), 'DOOM_VENT_FIRE'))
    c = (DOOR_R + 0.9) * math.cos(DOOR_A), (DOOR_R + 0.9) * math.sin(DOOR_A)
    bones.append(('fxdoor', 'eyeroot', (c[0], c[1], height(*c) + 1.4), 'DOOM_DOOR_FIRE'))
    return bones


def _orbit(t):
    """Yaw of the beasts in degrees: a steady 120-degree turn per 6 s loop (3-fold symmetric: seamless)."""
    return 360.0 / BEASTS * t / 6.0


GAZE = dict(fn=_orbit, T=6.0, spans=24)

# extra preview views: the game camera's angle, and a close-up of the summit and the door
PREVIEW = [((0, -70, 62), (0, 0, 18), 35), ((22, -30, 40), (6, -4, 30), 42)]
