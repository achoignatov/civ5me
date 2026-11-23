"""Shared procedural helpers for the 26 Middle-earth city-state models.

These are deliberately simple, low-poly versions of the same ideas used by the capital
models: timber halls, palisades, lake-town piers, eagles, spiders, Ents, a dragon, and
small figures.  Everything is built with blib primitives so the atlas/UV/AO pipeline can
consume it unchanged.

Conventions (same as the capitals): Z is up, the camera looks from -Y, models are about
60 units across and sit on a terrain_polar base that fills the city hexagon
(blib.HEX_IN = 31.2 to the flat sides, HEX_OUT = 36 to the corners, origin = tile centre).
"""
import math

from mathutils import Vector

from blib import (box, gable, hipped, cyl, cone, lathe, sphere, dome, blob, ring, crenels,
                  strut, curve, prism, tree, conifer, window_row, banner, near_path, T,
                  HEX_IN, HEX_OUT, in_hex, hex_radius, FILL)


# --------------------------------------------------------------------------- geometry
def ccw(pts):
    """Return the polygon in counter-clockwise order (prism needs CCW for outward faces)."""
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
            for i in range(len(pts)))
    return pts if a >= 0 else pts[::-1]


def plate(b, mat, pts, z, h, M=None, smooth=False):
    """Flat polygon extruded from z to z+h (wings, tails, roof boards)."""
    prism(b, mat, ccw(pts), z, h, M=M, smooth=smooth)


def house(b, x, y, z, w=3.0, d=2.2, h=1.8, rz=0.0, wall='wood', roof='thatch', roof_h=1.3,
          door=True, door_mat='window', windows=0, window_mat='window', base=None, base_h=0.0,
          chimney=False, chimney_mat='stone', overhang=0.3, roof_style='gable', porch=False,
          porch_mat=None):
    """A small rectangular house with a pitched roof and its door on the -Y (camera) side."""
    # the lowest box reaches 1.2 below the given ground level, so houses on a slope don't show
    # a floating foundation on their downhill side
    if base and base_h:
        box(b, base, x, y, z - 1.2, w + 0.14, d + 0.14, base_h + 1.2, rz=rz)
        z += base_h
        box(b, wall, x, y, z, w, d, h, rz=rz)
    else:
        box(b, wall, x, y, z - 1.2, w, d, h + 1.2, rz=rz)
    if roof_style == 'hip':
        hipped(b, roof, x, y, z + h, w, d, roof_h, rz=rz, overhang=overhang)
    elif roof_style == 'flat':
        box(b, roof, x, y, z + h, w + 0.15, d + 0.15, 0.16, rz=rz)
    else:
        gable(b, roof, x, y, z + h, w, d, roof_h, rz=rz, overhang=overhang)
    ca, sa = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    fx, fy = x + sa * (d / 2 + 0.03), y - ca * (d / 2 + 0.03)
    if door:
        box(b, door_mat, fx, fy, z, 0.64, 0.08, min(1.12, h * 0.72), rz=rz)
    if windows:
        p0 = (x - ca * (w / 2 - 0.5) + sa * (d / 2 + 0.02),
              y - sa * (w / 2 - 0.5) - ca * (d / 2 + 0.02))
        p1 = (x + ca * (w / 2 - 0.5) + sa * (d / 2 + 0.02),
              y + sa * (w / 2 - 0.5) - ca * (d / 2 + 0.02))
        window_row(b, window_mat, p0[0], p0[1], p1[0], p1[1], z + h * 0.55, windows,
                   w=0.24, h=0.34, out=0.0)
    if chimney:
        cx = x + ca * (w * 0.26) + sa * (d * 0.05)
        cy = y + sa * (w * 0.26) - ca * (d * 0.05)
        box(b, chimney_mat, cx, cy, z + h, 0.42, 0.42, roof_h * 0.9, rz=rz)
    if porch:
        pm = porch_mat or wall
        # two posts and a lean-to roof over the door
        for s in (-1, 1):
            px = fx + ca * s * 0.9
            py = fy + sa * s * 0.9
            cyl(b, pm, px, py, z, 0.10, 1.9, n=5)
        gable(b, roof, x, y - d / 2 - 0.7, z + 1.8, 2.4, 1.5, 0.55, rz=rz, overhang=0.1)


def longhouse(b, x, y, z, w=7.0, d=3.0, h=2.2, rz=0.0, wall='wood', roof='thatch', roof_h=1.8,
              door_mat='window', windows=0, window_mat='window', base=None, base_h=0.0,
              porch=True, posts=4, post_mat=None):
    """A large hall; the ridge runs along local X."""
    house(b, x, y, z, w, d, h, rz=rz, wall=wall, roof=roof, roof_h=roof_h, door_mat=door_mat,
          windows=windows, window_mat=window_mat, base=base, base_h=base_h, overhang=0.45,
          porch=porch, porch_mat=post_mat or wall)
    if posts:
        ca, sa = math.cos(math.radians(rz)), math.sin(math.radians(rz))
        for i in range(posts):
            lx = -w / 2 + w * (i + 0.5) / posts
            px = x + ca * lx + sa * (d / 2 + 0.25)
            py = y + sa * lx - ca * (d / 2 + 0.25)
            cyl(b, post_mat or wall, px, py, z, 0.12, h, n=5, top=False)


def round_hut(b, x, y, z, r=1.5, h=1.4, roof_h=1.8, wall='daub', roof='thatch',
              door_mat='window', n=10):
    cyl(b, wall, x, y, z, r, h, n=n)
    cone(b, roof, x, y, z + h, r * 1.18, roof_h, n=n)
    box(b, door_mat, x, y - r - 0.03, z, 0.62, 0.09, min(1.05, h * 0.78))


def tent(b, mat, x, y, z, r=1.8, h=2.6, n=8, door_mat=None, pole=None, hide=False):
    cone(b, mat, x, y, z, r, h, n=n)
    if door_mat:
        box(b, door_mat, x, y - r * 0.55, z, 0.9, 0.08, h * 0.42)
    if pole:
        strut(b, pole, (x, y, z + h * 0.9), (x, y, z + h + 0.7), 0.06, 0.03, n=4)
    if hide:
        # a couple of dark patches / seams on the tent
        for s in (-1, 1):
            box(b, door_mat or mat, x + s * r * 0.45, y, z + h * 0.28, 0.5, 0.06, 0.7,
                rz=90)


def yurt(b, mat, x, y, z, r=1.7, h=1.2, roof_mat=None, door_mat=None, n=12):
    cyl(b, mat, x, y, z, r, h, n=n)
    dome(b, roof_mat or mat, x, y, z + h, r * 1.06, n=n, rings=4, h=r * 0.72)
    if door_mat:
        box(b, door_mat, x, y - r - 0.03, z, 0.7, 0.09, 1.1)


def palisade(b, mat, cx, cy, r, a0=0.0, a1=360.0, h=2.2, step=1.15, zfn=None,
             gate=None, gate_w=10.0, rail=None, tip=True):
    """Pointed stakes around an arc. gate is an angle (degrees) where an opening is left."""
    n = max(3, int(abs(a1 - a0) / 360.0 * 2 * math.pi * r / step))
    posts = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        if gate is not None:
            da = abs(((a - gate) + 180.0) % 360.0 - 180.0)
            if da < gate_w / 2:
                posts.append(None)
                continue
        ar = math.radians(a)
        x, y = cx + r * math.cos(ar), cy + r * math.sin(ar)
        z = zfn(x, y) if zfn else 0.0
        strut(b, mat, (x, y, z - 0.35), (x, y, z + h), 0.20, 0.16, n=4)
        if tip:
            strut(b, mat, (x, y, z + h), (x, y, z + h + 0.45), 0.16, 0.0, n=4)
        posts.append((x, y, z))
    if rail:
        # rounded rails between neighbouring stakes (closed geometry, no back faces)
        for p, q in zip(posts, posts[1:]):
            if p is None or q is None:
                continue
            for zz in (h * 0.35, h * 0.7):
                strut(b, rail, (p[0], p[1], p[2] + zz), (q[0], q[1], q[2] + zz), 0.09, 0.09, n=4)


def gate(b, mat, cx, cy, r, angle, z=0.0, w=2.2, h=3.2, roof=None, roof_mat=None):
    """Gate posts and lintel on a palisade ring."""
    ar = math.radians(angle)
    gx, gy = cx + r * math.cos(ar), cy + r * math.sin(ar)
    tx, ty = -math.sin(ar), math.cos(ar)
    for s in (-1, 1):
        box(b, mat, gx + tx * s * w / 2, gy + ty * s * w / 2, z - 0.3, 0.5, 0.5, h + 0.3,
            rz=angle + 90)
    box(b, mat, gx, gy, z + h, w + 0.55, 0.55, 0.42, rz=angle + 90)
    if roof:
        gable(b, roof_mat or roof, gx, gy, z + h + 0.4, w + 0.9, 1.25, 0.65, rz=angle + 90,
              overhang=0.2)


def fence(b, mat, pts, h=1.3, step=1.2, rail=True, post_r=0.10):
    """A simple post-and-rail fence along a polyline [(x,y), ...]."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(L / step))
        for i in range(n + 1):
            t = i / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            cyl(b, mat, x, y, 0.0, post_r, h, n=4, top=False)
        if rail:
            for zz in (h * 0.35, h * 0.75):
                strut(b, mat, (x0, y0, zz), (x1, y1, zz), 0.07, 0.07, n=4)


def dock(b, mat, x, y, z, length, width, rz=0.0, post_mat=None, water_z=-0.35):
    ca, sa = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    box(b, mat, x, y, z, length, width, 0.24, rz=rz)
    n = max(1, int(length / 2.0))
    for i in range(n + 1):
        lx = -length / 2 + length * i / n
        for s in (-1, 1):
            wx = x + ca * lx - sa * s * width / 2
            wy = y + sa * lx + ca * s * width / 2
            cyl(b, post_mat or mat, wx, wy, water_z, 0.13, z - water_z, n=5, top=False)
    # a few crates / barrels on the quay
    if b.rng.random() < 0.7:
        barrel(b, mat, x + ca * (length * 0.3) - sa * (width * 0.2),
               y + sa * (length * 0.3) + ca * (width * 0.2), z + 0.24, 0.38, 0.75)


def boat(b, x, y, z, rz=0.0, s=1.0, hull='wood', sail='sail', mast=True, oars=False):
    M = T(x, y, z, rz=rz, s=s)
    P = lambda px, py, pz: tuple(M @ Vector((px, py, pz)))
    hull_pts = [(-2.2, 0.0), (-1.6, -0.8), (1.6, -0.8), (2.3, 0.0), (1.6, 0.8), (-1.6, 0.8)]
    plate(b, hull, hull_pts, -0.22, 0.52, M=M)
    box(b, hull, 0, 0, 0.30, 1.0, 1.35, 0.42, M=M @ T(-1.55, 0, 0))
    strut(b, hull, P(2.1, 0, 0.1), P(2.55, 0, 0.9), 0.18, 0.06, n=4)
    if mast:
        strut(b, hull, P(0.0, 0, 0.4), P(0.0, 0, 3.8), 0.10, 0.07, n=5)
        box(b, sail, 0, 0, 1.35, 0.07, 1.65, 2.05, M=M @ T(0.10, 0, 0))
        strut(b, hull, P(0, -0.85, 3.15), P(0, 0.85, 3.15), 0.05, 0.05, n=4)
    if oars:
        for side in (-1, 1):
            for k in range(3):
                ox = -0.8 + 0.8 * k
                strut(b, hull, P(ox, side * 0.7, 0.35), P(ox - 0.3, side * 1.7, -0.15),
                      0.04, 0.04, n=3)


def watchtower(b, mat, x, y, z, r=1.0, h=5.0, roof=None, roof_h=1.4, top_mat=None,
               crenellated=False):
    lathe(b, mat, [(r * 1.2, 0), (r * 1.1, 0.5), (r * 0.85, h), (r * 1.15, h + 0.3), (0, h + 0.3)],
          n=8, x=x, y=y, z=z, smooth=False)
    if roof:
        cone(b, roof, x, y, z + h + 0.3, r * 1.3, roof_h, n=8)
    if crenellated:
        crenels(b, top_mat or mat, r * 1.1, z + h + 0.3, 0, 360, size=0.3, h=0.4, step=0.8,
                x=x, y=y, depth=0.3)


def standing_stone(b, mat, x, y, z, h=3.0, w=0.7, rz=0.0, lean=0.0):
    M = T(x, y, z, rz=rz, rx=lean)
    lathe(b, mat, [(w, 0), (w * 0.86, h * 0.62), (w * 0.52, h), (0, h)], n=5, M=M,
          smooth=False, jitter=0.14)


def ruin_wall(b, mat, x, y, z, L, H, T_, rz=0.0, seed=0):
    """A broken wall: segments of random height with a ragged top."""
    rng = b.rng
    n = max(1, int(L / 1.1))
    ca, sa = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    for i in range(n):
        hh = H * (0.28 + 0.72 * rng.random())
        lx = -L / 2 + L * (i + 0.5) / n
        box(b, mat, x + ca * lx, y + sa * lx, z, T_, L / n + 0.05, hh, rz=rz)


def ruin_column(b, mat, x, y, z, h=3.0, r=0.45, broken=True):
    lathe(b, mat, [(r * 1.25, 0), (r * 1.1, 0.35), (r, h), (0, h)], n=8, x=x, y=y, z=z,
          smooth=False, jitter=0.06 if broken else 0.0)


def person(b, x, y, z, s=1.0, robe='cloth', skin='skin', hat=None, hat_mat=None, staff=None,
           beard=None, arms=True):
    lathe(b, robe, [(0.42 * s, 0), (0.50 * s, 0.08 * s), (0.34 * s, 1.02 * s),
                    (0.22 * s, 1.36 * s), (0, 1.36 * s)], n=8, x=x, y=y, z=z, smooth=False)
    sphere(b, skin, x, y, z + 1.55 * s, 0.22 * s, n=8, rings=6)
    if arms:
        for side in (-1, 1):
            strut(b, robe, (x + side * 0.24 * s, y, z + 1.18 * s),
                  (x + side * 0.43 * s, y - 0.10 * s, z + 0.65 * s), 0.09 * s, 0.07 * s, n=4)
    if beard:
        cone(b, beard, 0, 0, 0, 0.17 * s, 0.55 * s, n=6,
             M=T(x, y, z + 1.40 * s, rx=180))
    if hat:
        cone(b, hat_mat or hat, x, y, z + 1.70 * s, 0.27 * s, 0.65 * s, n=8)
        cyl(b, hat_mat or hat, x, y, z + 1.68 * s, 0.38 * s, 0.06 * s, n=10)
    if staff:
        strut(b, staff, (x + 0.34 * s, y - 0.12 * s, z - 0.05), (x + 0.40 * s, y - 0.16 * s,
              z + 1.9 * s), 0.06 * s, 0.05 * s, n=4)
        sphere(b, staff, x + 0.40 * s, y - 0.16 * s, z + 1.95 * s, 0.09 * s, n=6, rings=4)


def wizard(b, x, y, z, s=1.0, robe='greyrobe', skin='skin', hat='greyrobe', staff='wood',
           beard='beard', trim=None):
    person(b, x, y, z, s=s, robe=robe, skin=skin, hat=hat, staff=staff, beard=beard)
    if trim:
        lathe(b, trim, [(0.50 * s, 0.08 * s), (0.52 * s, 0.16 * s), (0.46 * s, 0.22 * s), (0, 0.22 * s)],
              n=8, x=x, y=y, z=z, smooth=False)


# --------------------------------------------------------------------------- creatures
def eagle(b, x, y, z, s=1.0, body='eagle', head='eaglehead', beak='beak', leg='beak',
          eye='eye', rz=0.0):
    """A perched eagle facing -Y (the camera)."""
    M = T(x, y, z, rz=rz, s=s)
    P = lambda px, py, pz: tuple(M @ Vector((px, py, pz)))
    sphere(b, body, 0, 0, 0, 0.55, n=10, rings=7,
           M=M @ T(0, 0, 1.0) @ T(0, 0, 0, s=(0.9, 1.35, 1.0)), squash=1.0)
    # folded wings, slightly proud of the body
    for side in (-1, 1):
        sphere(b, body, 0, 0, 0, 0.34, n=8, rings=5,
               M=M @ T(side * 0.46, 0.02, 1.0) @ T(0, 0, 0, s=(0.45, 1.65, 1.35)), squash=1.0)
    # white head and neck
    sphere(b, head, 0, -0.55, 1.55, 0.30, n=9, rings=6, M=M)
    strut(b, head, P(0, -0.25, 1.35), P(0, -0.55, 1.5), 0.20, 0.18, n=6)
    # beak, eyes
    strut(b, beak, P(0, -0.76, 1.55), P(0, -1.12, 1.45), 0.13, 0.0, n=5)
    for side in (-1, 1):
        sphere(b, eye, 0, 0, 0, 0.035, n=5, rings=4,
               M=M @ T(side * 0.13, -0.77, 1.62))
    # tail
    plate(b, head, [(-0.32, 0.45), (0.32, 0.45), (0.52, 1.35), (-0.52, 1.35)], 0.52, 0.10, M=M)
    # legs and talons
    for side in (-1, 1):
        strut(b, leg, P(side * 0.22, 0.02, 0.55), P(side * 0.24, 0.02, 0.08), 0.07, 0.05, n=4)
        for k in (-1, 1):
            strut(b, leg, P(side * 0.24, 0.02, 0.08), P(side * 0.24 + k * 0.10, -0.16, 0.02),
                  0.035, 0.0, n=3)


def eagle_flying(b, x, y, z, s=1.0, rz=0.0, body='eagle', head='eaglehead', beak='beak'):
    """A spread-wing eagle silhouette, useful above crags and eyries."""
    M = T(x, y, z, rz=rz, s=s)
    P = lambda px, py, pz: tuple(M @ Vector((px, py, pz)))
    for side in (-1, 1):
        pts = [(0.12 * side, 0.20), (0.8 * side, 0.58), (2.1 * side, 0.66),
               (2.8 * side, 0.28), (2.35 * side, -0.12), (1.1 * side, -0.25),
               (0.12 * side, -0.12)]
        plate(b, body, pts, 0.0, 0.10, M=M)
    sphere(b, body, 0, 0, 0.20, 0.30, n=8, rings=5, M=M @ T(0, 0, 0, s=(0.8, 1.5, 0.8)),
           squash=1.0)
    sphere(b, head, 0, -0.55, 0.28, 0.20, n=8, rings=5, M=M)
    strut(b, beak, P(0, -0.72, 0.27), P(0, -0.98, 0.22), 0.08, 0.0, n=4)
    plate(b, head, [(-0.25, 0.35), (0.25, 0.35), (0.35, 0.85), (-0.35, 0.85)], 0.16, 0.07, M=M)


def spider(b, x, y, z, s=1.0, body='spider', leg='spiderleg', eye='spidereye'):
    """A big spider (Shelob / Ungoliant), facing -Y."""
    M = T(x, y, z, s=s)
    P = lambda px, py, pz: tuple(M @ Vector((px, py, pz)))
    sphere(b, body, 0, 0.85, 1.15, 0.95, n=12, rings=8, M=M, squash=1.25)
    sphere(b, body, 0, -0.35, 0.88, 0.58, n=10, rings=7, M=M, squash=0.85)
    # eyes
    for dx in (-0.18, 0.18):
        sphere(b, eye, dx, -0.78, 1.02, 0.075, n=6, rings=4, M=M)
    # fangs
    for dx in (-0.12, 0.12):
        strut(b, body, P(dx, -0.68, 0.72), P(dx, -0.98, 0.30), 0.06, 0.0, n=4)
    # eight jointed legs
    for side in (-1, 1):
        for k, dy in enumerate((-0.62, -0.22, 0.28, 0.70)):
            root = (side * 0.36, dy, 0.90)
            knee = (side * (1.20 + 0.16 * k), dy * 1.20, 1.55 + 0.20 * (k % 2))
            foot = (side * (2.05 + 0.22 * k), dy * 1.85, 0.05)
            curve(b, leg, [P(*root), P(*knee), P(*foot)], 0.09, 0.04, n=5)
            sphere(b, leg, *P(*knee), 0.10, n=6, rings=4)
    # spinnerets
    sphere(b, body, 0, 1.75, 1.0, 0.25, n=7, rings=5, M=M)


def ent(b, x, y, z, h=6.0, bark='entbark', leaf='entleaf', moss='entmoss', eye='window'):
    """A tree-man: trunk legs, a gnarled body, branch arms and a leafy crown."""
    # legs
    for side in (-1, 1):
        curve(b, bark, [(x + side * 0.55, y, z), (x + side * 0.75, y - 0.08, z + h * 0.24),
                        (x + side * 0.45, y, z + h * 0.44)], 0.34, 0.29, n=6)
        # root toes
        for k in (-1, 0, 1):
            strut(b, bark, (x + side * 0.55, y, z + 0.08),
                  (x + side * 0.55 + k * 0.35, y - 0.55, z + 0.02), 0.12, 0.04, n=4)
    # trunk body
    lathe(b, bark, [(0.92, 0), (1.02, h * 0.14), (0.78, h * 0.40), (0.66, h * 0.55), (0, h * 0.55)],
          n=8, x=x, y=y, z=z + h * 0.34, smooth=False, jitter=0.07)
    # arms
    for side in (-1, 1):
        pts = [(x + side * 0.55, y, z + h * 0.78), (x + side * 1.35, y - 0.18, z + h * 0.82),
               (x + side * 2.15, y - 0.48, z + h * 0.63), (x + side * 2.45, y - 0.78, z + h * 0.40)]
        curve(b, bark, pts, 0.28, 0.10, n=6)
        for k in range(3):
            strut(b, bark, pts[-1], (pts[-1][0] + side * 0.45, pts[-1][1] - 0.18 + 0.18 * k,
                                     pts[-1][2] - 0.35), 0.07, 0.0, n=4)
    # head and face
    sphere(b, bark, x, y - 0.08, z + h * 0.98, 0.52, n=10, rings=7, M=None, squash=1.2)
    for side in (-1, 1):
        sphere(b, eye, x + side * 0.19, y - 0.56, z + h * 1.0, 0.065, n=5, rings=4)
    # leafy crown
    for k in range(5):
        blob(b, leaf, x + b.rng.uniform(-0.8, 0.8), y + b.rng.uniform(-0.5, 0.5),
             z + h * 1.05 + b.rng.uniform(0.0, 0.7), b.rng.uniform(0.7, 1.15), n=8, rings=4,
             squash=0.65)
    # moss beard
    for k in range(4):
        strut(b, moss, (x - 0.24 + 0.16 * k, y - 0.45, z + h * 0.96),
              (x - 0.24 + 0.16 * k, y - 0.52, z + h * 0.74), 0.07, 0.02, n=4)


def dragon(b, x, y, z, s=1.0, body='dragon', belly='dragonbelly', wing='dragonwing',
           gold='gold', eye='eye'):
    """A dragon coiled on a mound of treasure, facing -Y."""
    M = T(x, y, z, s=s)
    P = lambda px, py, pz: tuple(M @ Vector((px, py, pz)))
    # hoard
    sphere(b, gold, 0, 0, 0.0, 4.0, n=18, rings=9, M=M, squash=0.34)
    for k in range(50):
        a = b.rng.uniform(0, 2 * math.pi)
        rr = b.rng.uniform(0.4, 4.4)
        sphere(b, gold, 0, 0, 0, b.rng.uniform(0.06, 0.16), n=5, rings=4,
               M=M @ T(rr * math.cos(a), rr * math.sin(a), 0.9 + b.rng.uniform(-0.15, 0.25)))
    # gems
    for k in range(14):
        a = b.rng.uniform(0, 2 * math.pi)
        rr = b.rng.uniform(0.8, 3.8)
        sphere(b, 'gem', 0, 0, 0, b.rng.uniform(0.07, 0.14), n=6, rings=4,
               M=M @ T(rr * math.cos(a), rr * math.sin(a), 1.05))
    # body and neck
    sphere(b, body, 0, 0.75, 1.7, 1.55, n=14, rings=9, M=M, squash=0.95)
    sphere(b, belly, 0, 0.45, 1.55, 1.10, n=12, rings=7, M=M, squash=0.75)
    curve(b, body, [P(0, -0.65, 1.9), P(0.25, -1.55, 2.6), P(0.45, -2.35, 3.7),
                    P(0.25, -2.95, 4.65)], 0.72, 0.36, n=8)
    # head, snout, jaw, horns, eyes
    sphere(b, body, 0.20, -3.10, 4.75, 0.55, n=10, rings=7, M=M, squash=1.15)
    strut(b, body, P(0.20, -3.35, 4.75), P(0.20, -4.15, 4.55), 0.38, 0.18, n=6)
    strut(b, belly, P(0.20, -3.45, 4.50), P(0.20, -3.95, 4.38), 0.22, 0.10, n=5)
    for side in (-1, 1):
        strut(b, 'horn', P(0.20 + side * 0.28, -3.0, 5.05), P(0.20 + side * 0.48, -2.65, 5.55),
              0.12, 0.0, n=5)
        sphere(b, eye, 0.20 + side * 0.30, -3.32, 4.88, 0.07, n=5, rings=4, M=M)
    # folded wings rising behind the shoulders
    for side in (-1, 1):
        pts = [(0.2 * side, 0.2), (1.1 * side, 0.7), (2.7 * side, 2.0), (3.8 * side, 3.5),
               (2.1 * side, 2.7), (0.9 * side, 1.4)]
        plate(b, wing, pts, 0.0, 0.12, M=M @ T(0, 0, 2.0, rx=-62))
    # tail curling around the hoard
    curve(b, body, [P(0, 2.1, 1.25), P(1.6, 3.1, 0.85), P(3.0, 3.9, 0.55),
                    P(4.0, 4.6, 0.85), P(4.35, 5.2, 1.35)], 0.46, 0.07, n=6)
    # legs and claws
    for side in (-1, 1):
        curve(b, body, [P(side * 0.9, -0.2, 1.2), P(side * 1.45, -0.85, 0.75),
                        P(side * 1.55, -1.25, 0.20)], 0.28, 0.16, n=6)
        for k in (-1, 0, 1):
            strut(b, 'horn', P(side * 1.55, -1.25, 0.20),
                  P(side * 1.55 + k * 0.18, -1.60, 0.08), 0.05, 0.0, n=4)
    # dorsal spines
    for k in range(7):
        t = k / 6.0
        strut(b, 'horn', P(0.02, 0.25 + 2.2 * t, 2.55 + 0.55 * math.sin(math.pi * t)),
              P(0.02, 0.25 + 2.2 * t, 3.05 + 0.55 * math.sin(math.pi * t)), 0.10, 0.0, n=4)


def horse(b, x, y, z, s=1.0, body='horse', mane='mane', rz=0.0):
    M = T(x, y, z, rz=rz, s=s)
    P = lambda px, py, pz: tuple(M @ Vector((px, py, pz)))
    sphere(b, body, 0, 0, 1.0, 0.55, n=10, rings=7, M=M, squash=1.2)
    strut(b, body, P(0, -0.30, 1.30), P(0, -0.72, 1.95), 0.22, 0.16, n=6)
    sphere(b, body, 0, -0.82, 2.02, 0.25, n=8, rings=6, M=M, squash=1.3)
    strut(b, body, P(0, -0.98, 2.02), P(0, -1.22, 1.88), 0.13, 0.08, n=5)
    for side in (-1, 1):
        for sy in (-1, 1):
            strut(b, body, P(side * 0.30, sy * 0.35, 0.95), P(side * 0.36, sy * 0.46, 0.0),
                  0.10, 0.07, n=5)
    curve(b, mane, [P(0, 0.48, 1.10), P(0, 0.92, 0.70), P(0.10, 1.05, 0.18)], 0.12, 0.03, n=5)
    for k in range(4):
        strut(b, mane, P(0, -0.45 + 0.18 * k, 1.55), P(0, -0.50 + 0.18 * k, 1.28), 0.06, 0.03, n=4)


def cow(b, x, y, z, s=1.0, body='cow', horn='horn', rz=0.0):
    M = T(x, y, z, rz=rz, s=s)
    P = lambda px, py, pz: tuple(M @ Vector((px, py, pz)))
    sphere(b, body, 0, 0, 0.85, 0.55, n=10, rings=7, M=M, squash=0.9)
    sphere(b, body, 0, -0.55, 0.95, 0.30, n=8, rings=5, M=M)
    for side in (-1, 1):
        strut(b, horn, P(side * 0.20, -0.72, 1.12), P(side * 0.35, -0.80, 1.35), 0.06, 0.0, n=4)
        for sy in (-1, 1):
            strut(b, body, P(side * 0.28, sy * 0.28, 0.70), P(side * 0.32, sy * 0.35, 0.0),
                  0.08, 0.05, n=4)


# --------------------------------------------------------------------------- props
def barrel(b, mat, x, y, z, r=0.45, h=0.9, rz=0.0):
    lathe(b, mat, [(r * 0.78, 0), (r, h * 0.25), (r, h * 0.75), (r * 0.78, h), (0, h)],
          n=10, x=x, y=y, z=z, smooth=True, M=T(0, 0, 0, rz=rz))


def crate(b, mat, x, y, z, s=0.7, rz=0.0):
    box(b, mat, x, y, z, s, s, s, rz=rz)
    box(b, mat, x, y, z + s * 0.45, s * 1.04, s * 0.16, s * 0.12, rz=rz)


def beehive(b, mat, x, y, z, s=1.0):
    for i in range(3):
        rr = (0.55 - 0.10 * i) * s
        lathe(b, mat, [(rr, 0), (rr * 1.1, 0.18 * s), (rr * 0.85, 0.34 * s), (0, 0.34 * s)],
              n=10, x=x, y=y, z=z + 0.30 * s * i, smooth=True)


def birdhouse(b, mat, post, x, y, z, h=2.4, s=1.0):
    cyl(b, post, x, y, z, 0.08 * s, h, n=4, top=False)
    box(b, mat, x, y, z + h, 0.55 * s, 0.45 * s, 0.55 * s)
    gable(b, mat, x, y, z + h + 0.55 * s, 0.62 * s, 0.52 * s, 0.25 * s, overhang=0.04)
    sphere(b, 'window', x, y - 0.24 * s, z + h + 0.28 * s, 0.08 * s, n=6, rings=4)


def campfire(b, x, y, z, s=1.0, stone='rock', log='bark', flame='flame'):
    for k in range(8):
        a = 2 * math.pi * k / 8
        sphere(b, stone, x + 0.55 * s * math.cos(a), y + 0.55 * s * math.sin(a), z + 0.08 * s,
               0.14 * s, n=5, rings=4)
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.4
        strut(b, log, (x + 0.35 * s * math.cos(a), y + 0.35 * s * math.sin(a), z + 0.10 * s),
              (x - 0.35 * s * math.cos(a), y - 0.35 * s * math.sin(a), z + 0.10 * s),
              0.07 * s, 0.07 * s, n=4)
    for k in range(3):
        cone(b, flame, x, y, z + 0.12 * s, (0.32 - 0.07 * k) * s, (0.8 - 0.12 * k) * s, n=6)


def web(b, mat, center, u, v, r=3.0, n=10, rings=3, thickness=0.035):
    """A radial spider web in the plane spanned by u and v."""
    C, U, V = Vector(center), Vector(u).normalized(), Vector(v).normalized()
    rim = []
    for i in range(n):
        a = 2 * math.pi * i / n
        p = C + U * (r * math.cos(a)) + V * (r * math.sin(a))
        rim.append(p)
        strut(b, mat, C, p, thickness, thickness * 0.7, n=4)
    for k in range(1, rings + 1):
        rr = r * k / (rings + 1)
        pts = [C + U * (rr * math.cos(2 * math.pi * i / n)) + V * (rr * math.sin(2 * math.pi * i / n))
               for i in range(n)]
        for i in range(n):
            strut(b, mat, pts[i], pts[(i + 1) % n], thickness * 0.7, thickness * 0.7, n=4)
    # a few slack anchor lines
    for i in range(0, n, 3):
        p = rim[i]
        strut(b, mat, C + U * (r * 0.55 * math.cos(2 * math.pi * i / n)) +
              V * (r * 0.55 * math.sin(2 * math.pi * i / n)), p + Vector((0, 0, -0.5)),
              thickness * 0.5, thickness * 0.5, n=3)


def sea(b, mat, z=0.0, r=32.0, n=64):
    """A flat disc of water with a short skirt, for the island city-states."""
    lathe(b, mat, [(r, -2.5), (r, z), (0, z)], n=n, smooth=False)


def path_material(default, path, width, mat='road'):
    def f(x, y, z, s):
        return mat if near_path(x, y, path, width) else default
    return f


def scatter_forest(b, n, x0, x1, y0, y1, zfn, avoid=(), min_dist=2.6, max_r=29.0,
                   kind='tree', h=(4.0, 7.0), r=(1.3, 2.1), leaves='leaves', trunk='bark',
                   pines=0.0, pine_leaves='pine'):
    """Place n trees with a minimum spacing, skipping rectangles in `avoid`."""
    placed = []
    for _ in range(n * 5):
        if len(placed) >= n:
            break
        x, y = b.rng.uniform(x0, x1), b.rng.uniform(y0, y1)
        if math.hypot(x, y) > max_r:
            continue
        if any(math.hypot(x - px, y - py) < min_dist for px, py in placed):
            continue
        if any(ax0 - 1.0 < x < ax1 + 1.0 and ay0 - 1.0 < y < ay1 + 1.0
               for ax0, ax1, ay0, ay1 in avoid):
            continue
        placed.append((x, y))
        z = zfn(x, y) - 0.25
        if b.rng.random() < pines:
            conifer(b, x, y, z, h=b.rng.uniform(*h) * 1.15, r=b.rng.uniform(*r) * 0.8,
                    leaves=pine_leaves)
        elif kind == 'conifer':
            conifer(b, x, y, z, h=b.rng.uniform(*h), r=b.rng.uniform(*r), leaves=pine_leaves)
        else:
            tree(b, x, y, z, h=b.rng.uniform(*h), r=b.rng.uniform(*r), leaves=leaves, trunk=trunk)


# --------------------------------------------------------------------------- effects / water / rock
def fx(b, name, pos, effect):
    """An FX_ bone that plays a VisEffect from capitals.EFFECTS ('ART_DEF_VEFFECT_MEC_<effect>')."""
    full = effect if effect.startswith('ART_DEF') else 'ART_DEF_VEFFECT_MEC_' + effect
    b.fx.append(('FX_' + name, tuple(pos), full))


def water_disc(b, mat, z=0.12, R=30.4, cy=2.0, n=96):
    """Water surface just above z=0 over the whole city hexagon (the game's terrain hides
    everything below the ground plane). R, cy, n are kept for the models' signatures."""
    ro = HEX_OUT * 0.985 / FILL[0]
    pts = [(ro * math.cos(math.radians(30 + 60 * k)), ro * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    prism(b, mat, pts, -1.0, z + 1.0)


def hex_fill(x, y, R=None, cy=None, margin=0.0):
    """True when (x, y) lies on the model's base (the city hexagon)."""
    return in_hex(x, y, margin)


def spire(b, mat, x, y, z, h, r, n=7, lean=0.0, rz=0.0, jitter=0.12):
    """A jagged rock needle."""
    lathe(b, mat, [(r, 0), (r * 0.82, h * 0.35), (r * 0.55, h * 0.7), (r * 0.18, h * 0.95), (0, h)],
          n=n, M=T(x, y, z, rz=rz, rx=lean), smooth=False, jitter=jitter)


def dead_tree(b, mat, x, y, z, h=4.0, r=0.22):
    """Bare, twisted tree (Dimholt, Avathar, Dunland moors)."""
    pts = [(x, y, z), (x + 0.15, y, z + h * 0.45), (x - 0.1, y + 0.1, z + h * 0.75), (x + 0.05, y, z + h)]
    curve(b, mat, pts, r, r * 0.35, n=5)
    for k in range(4):
        a = 2 * math.pi * k / 4 + b.rng.uniform(-0.4, 0.4)
        p0 = pts[1 + k % 3]
        L = h * b.rng.uniform(0.25, 0.4)
        p1 = (p0[0] + L * math.cos(a), p0[1] + L * math.sin(a), p0[2] + L * 0.6)
        strut(b, mat, p0, p1, r * 0.45, 0.0, n=4)


def grow(b, start, s, cx=0.0, cy=2.0, sz=None):
    """Scale everything built since vertex index `start` (and the FX bones) about (cx, cy),
    e.g. to make a town fill more of the hexagon. Ground level z=0 stays put."""
    sz = s if sz is None else sz
    for i in range(start, len(b.verts)):
        x, y, z = b.verts[i]
        b.verts[i] = (cx + (x - cx) * s, cy + (y - cy) * s, z * sz)
    b.fx[:] = [(n, (cx + (p[0] - cx) * s, cy + (p[1] - cy) * s, p[2] * sz), e) for n, p, e in b.fx]


def great_dragon(b, x, y, z, s=1.0, body='dragon', belly='dragonbelly', wing='dragonwing', horn='horn',
                 eye='eye', rz=0.0):
    """A long-bodied dragon lying on its belly, neck raised, head towards -Y, wings half spread.
    Returns the world position of the nostrils (for a smoke effect). Length about 14*s."""
    M = T(x, y, z, rz=rz, s=s)
    P = lambda px, py, pz: tuple(M @ Vector((px, py, pz)))
    # spine from the tail tip (+Y) over the back to the head (-Y)
    spine = [(3.2, 9.5, 0.25), (2.4, 7.6, 0.35), (0.9, 5.6, 0.55), (0.0, 3.4, 0.95), (0.0, 1.2, 1.35),
             (0.0, -1.0, 1.45), (0.0, -2.8, 1.6), (0.0, -3.8, 2.6), (0.0, -4.5, 3.6), (0.0, -5.2, 4.2)]
    radii = [0.08, 0.22, 0.42, 0.7, 1.05, 1.15, 0.85, 0.55, 0.45, 0.42]
    for i in range(len(spine) - 1):
        strut(b, body, P(*spine[i]), P(*spine[i + 1]), radii[i], radii[i + 1], n=9, smooth=True)
        sphere(b, body, *P(*spine[i + 1]), radii[i + 1] * s, n=9, rings=6)
    # belly plates along the underside of the trunk
    for k in range(6):
        t = k / 5
        py = 3.0 - 6.0 * t
        sphere(b, belly, 0, 0, 0, 0.9, n=8, rings=5, M=M @ T(0, py, 0.75) @ T(0, 0, 0, s=(1.05, 0.55, 0.45)))
    # head: skull, long snout, jaw, horns, eyes, nostrils
    hx, hy, hz = spine[-1]
    sphere(b, body, 0, 0, 0, 0.62, n=10, rings=7, M=M @ T(hx, hy - 0.1, hz + 0.1) @ T(0, 0, 0, s=(0.9, 1.1, 0.8)))
    strut(b, body, P(hx, hy - 0.4, hz + 0.05), P(hx, hy - 2.0, hz - 0.35), 0.46, 0.2, n=8)
    strut(b, belly, P(hx, hy - 0.4, hz - 0.35), P(hx, hy - 1.7, hz - 0.62), 0.3, 0.12, n=6)
    for sd in (-1, 1):
        curve(b, horn, [P(hx + sd * 0.35, hy + 0.1, hz + 0.45), P(hx + sd * 0.6, hy + 0.7, hz + 0.9),
                        P(hx + sd * 0.7, hy + 1.4, hz + 1.0)], 0.13, 0.0, n=5)
        sphere(b, eye, *P(hx + sd * 0.36, hy - 0.45, hz + 0.32), 0.1 * s, n=6, rings=4)
    # dorsal spines along the back and tail
    for i in range(1, len(spine) - 2):
        px, py, pz = spine[i]
        r = radii[i]
        strut(b, horn, P(px, py, pz + r * 0.8), P(px, py + 0.35, pz + r * 0.8 + 0.4 + r * 0.5), 0.12 + r * 0.08, 0.0, n=4)
    # four legs with claws, splayed over the hoard
    for (ly, sd) in ((-1.8, -1), (-1.8, 1), (2.6, -1), (2.6, 1)):
        hip = P(sd * 0.9, ly, 1.1)
        knee = P(sd * 2.0, ly - 0.3, 0.9)
        foot = P(sd * 2.3, ly - 0.9, 0.1)
        curve(b, body, [hip, knee, foot], 0.38, 0.22, n=7)
        for k in (-1, 0, 1):
            strut(b, horn, foot, P(sd * 2.3 + k * 0.25, ly - 1.45, 0.02), 0.08, 0.0, n=4)
    # wings: arm bones, finger ribs and membrane panels, half raised
    for sd in (-1, 1):
        sh = (sd * 0.8, -0.6, 2.2)
        elbow = (sd * 3.6, 0.4, 4.6)
        wrist = (sd * 5.6, 1.8, 3.8)
        curve(b, wing, [P(*sh), P(*elbow), P(*wrist)], 0.22, 0.12, n=6)
        tips = [(sd * 8.6, 3.0, 1.6), (sd * 7.6, 5.2, 0.9), (sd * 5.4, 6.4, 0.6), (sd * 2.6, 5.6, 1.0)]
        for t in tips:
            strut(b, wing, P(*wrist), P(*t), 0.1, 0.02, n=4)
        poly = [elbow, wrist] + tips + [(sd * 0.9, 3.4, 1.6), sh]
        # membrane: fan of thin triangles from the wrist (double-sided via two windings)
        for i in range(len(poly) - 1):
            a, c = poly[i], poly[i + 1]
            for tri in ((wrist, a, c), (wrist, c, a)):
                b.add([P(*tri[0]), P(*tri[1]), P(*tri[2])], [(0, 1, 2)], wing)
    return P(hx, hy - 2.0, hz - 0.3)
