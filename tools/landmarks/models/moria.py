"""Moria (Khazad-dûm), held by the Goblins: the West-gate, the Doors of Durin. Landmark of the city named Moria.

v3 (2026-11-24): high fidelity. Same layout and size as v2, but
  * smooth, finely subdivided rock (multi-octave noise relief) instead of large flat facets;
  * textures baked in Blender (tools/landmarks/bake.py: real UV unwrap, procedural rock with height/slope colour,
    strata, snow, ambient occlusion) instead of the blocky swatch atlas;
  * the ithildin glow: a soft blue halo painted around every line of the Doors of Durin (b.glow).
v2: NO ground plate (the model stands on the game's terrain); only mountains, doors, lake and trees.
Size limit found in game (docs/CITY_MODELS.md §12): footprint within +-20 world units in major civ cities (Moria is
always a major civ's city). Laid out in DESIGN units inside a +-10.5 hexagon, grown uniformly by GROW = 20 / 10.5:
the box of the "+-20" test model that drew in every major civ city (+-20 x +-23.1, 24.2 high).

Authored in design units: origin = tile centre, ground z = 0, -Y = south = towards the game camera.

Lore cues (The Fellowship of the Ring, "A Journey in the Dark"): the West-gate lies at the end of a bay of sheer cliffs
under the Misty Mountains (Caradhras behind), the dark lake of the dammed Sirannon fills the bay before it, the Doors
of Durin are drawn in shining ithildin on the smooth rock (pillars with crescent moons, arch, the two trees, crown and
seven stars, anvil and hammer, the star of Fëanor), two great holly trees stand before them, and the tentacles of the
Watcher in the Water rise from the lake.
"""
import math

import blib
from blib import material, hexcol as h, box, cyl, terrain, blob, curve, prism, T

HEX_IN = 10.5           # design hexagon (flat sides E/W); GROW scales it to the in-game size
GROW = 20.0 / HEX_IN    # -> +-20 world units (the proven limit for major civ cities)
TOP = 12.7              # highest design point (x GROW = 24.2, the proven height at this footprint)
CLIFF_Y = 1.0           # the cliff face with the doors, facing the camera (-Y)
FLOOR = -0.6            # below the game's ground: what is lower than this is not modelled
LAKE = (0.0, -3.2, 2.7)  # the Watcher's lake in the bay: centre x, y and radius
BAKE = True             # build_models: textures baked by tools/landmarks/bake.py (smooth shading kept)


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


def hex_dist(x, y):
    """Distance from (x, y) to the design hexagon's edge (positive inside)."""
    return HEX_IN - max(abs(x * math.cos(math.radians(60 * k)) + y * math.sin(math.radians(60 * k))) for k in range(3))


def back(x, y):
    """The Walls of Moria and the mountains behind them (north of the cliff)."""
    t = min(1.0, (y - CLIFF_Y) / 0.6)
    z = 0.25 + 8.6 * t
    z += 3.8 * math.exp(-((x - 2.5) / 3.2) ** 2) * smooth((y - 3.0) / 3.0)        # Caradhras, right of the doors
    z += 2.6 * math.exp(-((x + 5.0) / 2.6) ** 2) * smooth((y - 3.5) / 3.0)        # a lower peak to the left
    z += 1.6 * fbm(x * 0.35, y * 0.35, 5, 3) * t                                 # rocky relief
    z += 0.7 * fbm(x * 1.3, y * 1.3, 4, 13) * t                                  # crags
    return z


def soft_top(z):
    k = TOP - 1.6
    return z if z <= k else k + 1.6 * math.tanh((z - k) / 1.6)


def height(x, y):
    if y >= CLIFF_Y:
        z = back(x, y)
    else:
        # the bay: a floor below the ground between two cliff ridges that run towards the camera and get lower
        w = 4.6 + 0.35 * (CLIFF_Y - y) + 0.35 * fbm(y * 0.6, 1.7, 3, 9)
        ridge = 2.8 + 6.2 * smooth((y + 7.5) / (CLIFF_Y + 7.5))
        ridge += 1.3 * fbm(x * 0.4, y * 0.4, 5, 5) + 0.6 * fbm(x * 1.4, y * 1.4, 4, 15)
        z = FLOOR + (ridge - FLOOR) * smooth((abs(x) - w) / 1.1)
        z = FLOOR + (z - FLOOR) * smooth((y + 9.0) / 2.6)      # the ridges end in the south
    # irregular outline: everything sinks into the game's ground well inside the hexagon's edge
    a = math.atan2(y, x)
    edge = 0.35 + 0.3 * math.sin(a * 5 + 1.3) + 0.2 * math.sin(a * 11) + 0.3 * fbm(math.cos(a) * 3, math.sin(a) * 3, 3, 7)
    z = FLOOR + (z - FLOOR) * smooth((hex_dist(x, y) - edge) / 2.4)
    return soft_top(z)


def build(b, grow_xy=GROW, grow_z=GROW):
    """grow_xy / grow_z: scale of the finished model (default: the in-game size, see GROW)."""
    blib.SKIRT_MAT[0] = 'cliff'
    # the wall of the doors: the same dark rock as the cliffs around it, smoother (the doors' rock is "smooth")
    material('cliff', h('4f4c47'), h('3e3b37'), noise=1.2)
    blib.PALETTE['cliff'].update(scale=0.3, strata=1.2, strata_amp=0.08, cracks=0.12, glow=True,
                                 glow_color=h('8fd0ff'), uv_boost=2.2)     # more texture for the doors' wall
    # colours by height: evaluated on the finished (scaled) model, so the heights scale too
    material('rock', h('615b53'), h('45413b'),
             zramp=[(z * grow_z, c) for z, c in ((FLOOR, h('4d4a43')), (3.0, h('5b564e')), (8.0, h('68645d')),
                                                  (10.9, h('86837e')), (11.9, h('dde3e8')), (TOP, h('f4f7fa')))],
             slope_color=h('4a4743'), slope_start=0.6)
    blib.PALETTE['rock'].update(scale=0.14, strata=0.7, strata_amp=0.1, cracks=0.18,
                                moss=(h('4f5a36'), 3.0 * grow_z))
    # the ithildin lines: one solid colour (a swatch, see bake.py), the glow around them is painted on the wall
    material('ithildin', h('e6f6ff'), spec=1.0, refl=255, ao=False)
    blib.PALETTE['ithildin'].update(solid=True)
    material('lake', h('122019'), h('1c2c27'), spec=0.8, refl=90, ao=False)
    blib.PALETTE['lake'].update(scale=0.3)
    material('tentacle', h('5b6648'), h('3f4733'))
    blib.PALETTE['tentacle'].update(scale=1.2)
    material('holly', h('1d3a1c'), h('2f5a2a'))
    blib.PALETTE['holly'].update(scale=1.4)
    material('bark', h('4b3a2b'), h('33271c'))
    blib.PALETTE['bark'].update(scale=2.0)
    rng = b.rng

    # --- the mountains: one smooth height field; quads that stay under the game's ground are not modelled
    terrain(b, height, -HEX_IN, HEX_IN, -HEX_IN, HEX_IN / 0.8660254, 92, 98,
            lambda x, y, z, s: 'rock', keep=lambda x, y: hex_dist(x, y) > 0.3 and height(x, y) > FLOOR + 0.15,
            smooth=True, skirt=FLOOR - 0.9)

    # --- the Walls of Moria at the back of the bay: smooth rock (as in the book) where the doors are drawn,
    # with a little relief towards its ends
    nx, nz = 48, 16
    verts, faces = [], []
    for i in range(nx + 1):
        x = -6.2 + 12.4 * i / nx              # its ends are buried in the ridges, so no straight edge shows
        top = height(x, CLIFF_Y + 0.8) + 0.2
        for k in range(nz + 1):
            z = FLOOR - 0.4 + (top - FLOOR + 0.4) * k / nz
            rel = smooth((abs(x) - 3.4) / 1.2) * 0.25 * fbm(x * 0.9, z * 0.9, 3, 11)
            verts.append((x, CLIFF_Y + rel, z))
    for i in range(nx):
        for k in range(nz):
            a = i * (nz + 1) + k
            faces.append((a, a + nz + 1, a + nz + 2, a + 1))
    b.add(verts, faces, 'cliff', smooth=True)

    # --- the Doors of Durin in ithildin; every line is also painted as a soft glow (b.glow, see bake.py)
    F = CLIFF_Y - 0.05
    z0 = 0.3
    lines = []

    def line(x0, za, x1, zb, w=0.22):
        L = math.hypot(x1 - x0, zb - za)
        if L < 1e-6:
            return
        lines.append((x0, za, x1, zb, w))
        if w < 0.1:          # fine detail (letters, stars, small rays): painted only, too small to model
            return
        ang = math.degrees(math.atan2(zb - za, x1 - x0))
        # overlapping segments must not lie in one plane (they would flicker, "z-fighting"): each one a bit deeper
        dy = 0.004 * (len(lines) % 5)
        box(b, 'ithildin', 0, 0, -w / 2, L + w * 0.6, 0.08, w, M=T((x0 + x1) / 2, F + dy, (za + zb) / 2, ry=-ang))

    def arc(cx, cz, r, a0, a1, n, w=0.22):
        for k in range(n):
            p0 = math.radians(a0 + (a1 - a0) * k / n)
            p1 = math.radians(a0 + (a1 - a0) * (k + 1) / n)
            line(cx + r * math.cos(p0), cz + r * math.sin(p0), cx + r * math.cos(p1), cz + r * math.sin(p1), w)

    PX, PH = 2.3, 5.0
    for s in (-1, 1):
        line(s * PX, z0, s * PX, z0 + PH, 0.24)                       # pillars
        arc(s * PX, z0 + PH + 0.35, 0.42, 200, 340, 8, 0.16)          # crescent-moon capitals
    arc(0.0, z0 + PH + 0.5, PX + 0.15, 0, 180, 24, 0.24)                # the arch
    arc(0.0, z0 + PH + 0.5, PX - 0.35, 8, 172, 20, 0.12)                # band of letters
    for k in range(22):                                                  # the letters between the two arch lines
        a = math.radians(10 + 160 * (k + 0.5) / 22)
        r0, r1 = PX - 0.25, PX + 0.05
        line(r0 * math.cos(a), z0 + PH + 0.5 + r0 * math.sin(a), r1 * math.cos(a), z0 + PH + 0.5 + r1 * math.sin(a), 0.06)
    for s in (-1, 1):                                                    # the two trees
        x = s * 1.45
        line(x, z0, x, z0 + 4.6, 0.16)
        for k in range(4):
            zz = z0 + 1.6 + 0.8 * k
            line(x, zz, x - s * (0.8 - 0.15 * k), zz + 0.5, 0.1)
            line(x, zz + 0.3, x + s * 0.35, zz + 0.65, 0.08)
    line(-0.45, z0 + 6.85, 0.45, z0 + 6.85, 0.14)                         # crown
    for k in range(5):
        line(-0.45 + 0.225 * k, z0 + 6.85, -0.45 + 0.225 * k, z0 + 7.15 + 0.08 * (k % 2), 0.08)
    for k in range(7):                                                   # the seven stars
        a = math.radians(30 + 120 * k / 6)
        sx, sz = 1.25 * math.cos(a), z0 + 6.35 + 1.25 * math.sin(a)
        for r in range(4):
            q = math.pi * r / 4
            line(sx - 0.13 * math.cos(q), sz - 0.13 * math.sin(q), sx + 0.13 * math.cos(q), sz + 0.13 * math.sin(q), 0.05)
    line(-0.35, z0 + 5.95, 0.35, z0 + 5.95, 0.18)                         # anvil and hammer
    line(-0.15, z0 + 5.65, 0.15, z0 + 5.65, 0.14)
    line(0.25, z0 + 6.1, 0.45, z0 + 6.4, 0.08)
    for k in range(16):                                                  # the star of Fëanor (8 long, 8 short rays)
        a = math.pi * k / 8
        r = 0.85 if k % 2 == 0 else 0.5
        line(0.0, z0 + 3.4, r * math.cos(a), z0 + 3.4 + r * math.sin(a), 0.11 if k % 2 == 0 else 0.07)
    line(0.0, z0, 0.0, z0 + 2.5, 0.06)                                    # where the two leaves meet
    b.glow = dict(lines=lines, box=(-4.4, 4.4, FLOOR, 9.6), sigma=(0.22, 0.9))

    # --- the two holly trees before the doors, at the head of the lake: dense clusters of rounded foliage
    for s in (-1, 1):
        x, y = s * 3.5, CLIFF_Y - 1.2
        cyl(b, 'bark', x, y, FLOOR, 0.3, 2.2 - FLOOR, n=10, r2=0.16, smooth=True)
        for k in range(9):
            hgt = 1.4 + 3.4 * (k / 8)
            rr = 1.35 * (1.0 - 0.6 * k / 8)
            a = rng.uniform(0, 6.28)
            blob(b, 'holly', x + 0.35 * rr * math.cos(a), y + 0.35 * rr * math.sin(a), hgt, rr * 0.75,
                 n=12, rings=7, squash=0.85, jitter=0.12)

    # --- the dark lake filling the bay, and the Watcher's tentacles rising from it (at its sides, clear of the doors)
    rim = []
    for k in range(40):
        a = 2 * math.pi * k / 40
        r = LAKE[2] * (1.0 + 0.08 * math.sin(a * 3 + 0.7) + 0.05 * math.sin(a * 7))
        rim.append((LAKE[0] + 1.25 * r * math.cos(a), LAKE[1] + r * math.sin(a)))
    prism(b, 'lake', rim, -0.4, 0.5)
    for k, a in enumerate((200, 228, 256, 284, 312, 340)):
        a = math.radians(a + rng.uniform(-6, 6))
        bx, by = LAKE[0] + 2.5 * math.cos(a), LAKE[1] + 1.8 * math.sin(a)
        hgt = rng.uniform(2.0, 3.4)
        ph = rng.uniform(0, 6.28)
        pts = [(bx + 0.8 * math.sin(ph + t * 3.5) * t, by + 0.6 * math.cos(ph + t * 2.8) * t, -0.3 + hgt * t)
               for t in (i / 12 for i in range(13))]
        curve(b, 'tentacle', pts, 0.3, 0.03, n=10, smooth=True)

    # the finished model at its in-game size (before texturing, so normals follow the scaled shape)
    b.verts = [(x * grow_xy, y * grow_xy, z * grow_z) for (x, y, z) in b.verts]
    g = b.glow
    g['lines'] = [(x0 * grow_xy, za * grow_z, x1 * grow_xy, zb * grow_z, w * grow_xy) for x0, za, x1, zb, w in g['lines']]
    g['box'] = (g['box'][0] * grow_xy, g['box'][1] * grow_xy, g['box'][2] * grow_z, g['box'][3] * grow_z)
    g['sigma'] = tuple(s * grow_xy for s in g['sigma'])


PREVIEW = [((3 * GROW, -26 * GROW, 11 * GROW), (0, CLIFF_Y * GROW, 5 * GROW), 40)]
