"""Minas Morgul, the Tower of Sorcery: the city of the Witch-king (an IMPROVEMENT, docs/LANDMARKS.md). 2026-11-26.

The user: "a custom city model for Minas Morgul, the capital of the Witch King ... very realistic, detailed and
impressive ... more detailed and big and tall and impressive and glowing in ghoulish green ... true to the lore. IMPRESS
ME!" References: screenshots/minas-morgul1.webp (thorn-crenellated walls of pale glowing fluted stone between huge
black curved blade-buttresses, spiked towers), screenshots/minas-morgul2.webp (the slender many-tiered tower crowned
with spikes, the whole city lit from within by a sick green light rising into the sky).

Lore (The Two Towers IV.8 "The Stairs of Cirith Ungol", The Return of the King, the Appendices):
  * Minas Ithil, the Tower of the Moon, built of white marble upon a high shelf of rock on the dark knees of the Ephel
    Duath; taken by the Nazgul and become Minas Morgul.
  * "its walls and tower glowed ... a corpse-light, a light that illuminated nothing"; the windows "like countless
    black holes looking inward into emptiness"; "the topmost course of the tower revolved slowly, first one way and
    then another, a huge ghostly head leering into the night".
  * the gate "shaped like an open mouth with gleaming teeth"; the road crossing the Morgulduin on a white bridge, at
    its head "figures carved in cunning forms human and bestial, but all corrupt and loathsome"; in the meads beside
    the stream pale flowers, "luminous these were too, beautiful and yet horrible of shape".
  * when the host marches out, livid flame springs from the tower into the clouds; in the film a great pillar of green
    light rises from its top (John Howe's design, Weta's miniature: a glowing green spectre of a city).
  * the emblem of Minas Morgul: the Moon defaced with a ghastly face of death.

In-game units (improvement Scale 0.25, written x4), origin = the city's tile centre, ground z = 0, -Y = south =
towards the game camera; the whole city fits its own hex (hex_in 33.6). The tower rises 128 high, its revolving crown
to 140; the pillar of light far above.

Parts (the Balrog's proven layout: everything visible in STATIC models; the skinned part carries the effect bones):
  static      the rock shelf and the knees of the mountains (SDF), the Morgulduin, the meads and their flowers, the
              long white bridge rising to the gate, lined with its statues
  walls       the outer wall (pale fluted stone, thorn crenellations), the curved black blade-buttresses, the wall
              towers, the gatehouse with the Mouth and its teeth, the defaced Moon
  city        the two inner terraces with their parapets, ~250 tall dark houses, the lesser spired towers
  tower       the Tower of Sorcery: clawed roots, the ribbed shaft with five thorned galleries, lancet windows of
              corpse-light; a black spire core (still there if the crown should not draw)
  skinned     THE REVOLVING CROWN (the Eye of Barad-dur's proven mechanism: eyepivot turns, all its vertices on it):
              a leering head with slanted glowing eyes under a jagged brow, a crown of curved spikes, the great horns
Effects (bones of the skinned part): green witch-fire (the Balrog's shader fire, tinted: flames.fire_textures tint)
on the crown, the beacons and in the Mouth; slow rising green vapour over the city (soft masks, slow scroll); the
glow of the Mouth and the defaced Moon (glow.py); the PILLAR of green light from the top (a still additive model).
"""
import math
import random
import zlib

import numpy as np
from mathutils import Vector

import blib
import sdf
from blib import material, hexcol as h

BAKE = True
BAKE_PX = 2048
EYE_PX = 1024
EYE_AO = 24
PART_AO = 24
HEX = 33.6

# --------------------------------------------------------------------------- the plan
Z1, Z2, Z3 = 8.0, 14.0, 20.0                  # the outer shelf, the second terrace, the tower's court
C1, A1, B1, P1 = (0.0, 5.0), 26.5, 20.5, 3.2  # the outer wall's superellipse (y -15.5 .. 25.5)
C2, A2, B2, P2 = (0.0, 9.5), 17.0, 13.0, 3.0  # the second terrace (y -3.5 .. 22.5)
TC = (0.0, 9.5)                               # the tower's axis
R3 = 9.2                                      # the tower's court
H1 = 11.0                                     # the outer wall's height above the shelf
GATE_X = 4.6                                  # half-width of the gap in the outer wall at the gate
GATE_Y = C1[1] - B1                           # -15.5: the front of the city (the wall's line)
TOWER_Z0, TOWER_Z1 = Z3, 104.0                # the shaft
CROWN_Z = TOWER_Z1                            # the revolving top course
SPIRE_TOP = 140.0
EYE_C = (TC[0], TC[1], CROWN_Z)               # the crown's pivot (vertical axis through the tower)


def hex_d(x, y):
    """Distance measure of the pointy-top hexagon (33.6 = the flat sides east/west)."""
    ax, ay = abs(x), abs(y)
    return max(ax, 0.5 * ax + 0.8660254 * ay)


def se_pt(c, A, B, p, t):
    ct, st = math.cos(t), math.sin(t)
    return (c[0] + A * math.copysign(abs(ct) ** (2.0 / p), ct), c[1] + B * math.copysign(abs(st) ** (2.0 / p), st))


def se_s(x, y, c, A, B, p):
    return (np.abs((x - c[0]) / A) ** p + np.abs((y - c[1]) / B) ** p) ** (1.0 / p)


def ring_pts(c, A, B, p, n):
    """n points evenly spaced by length along a superellipse, counter-clockwise from the front (south)."""
    m = 4000
    fine = [se_pt(c, A, B, p, -math.pi / 2 + 2 * math.pi * i / m) for i in range(m)]
    L = [0.0]
    for i in range(1, m + 1):
        a, b_ = fine[i - 1], fine[i % m]
        L.append(L[-1] + math.hypot(b_[0] - a[0], b_[1] - a[1]))
    tot = L[-1]
    out, j = [], 0
    for k in range(n):
        s = tot * k / n
        while L[j + 1] < s:
            j += 1
        u = (s - L[j]) / max(1e-9, L[j + 1] - L[j])
        a, b_ = fine[j], fine[(j + 1) % m]
        out.append((a[0] + (b_[0] - a[0]) * u, a[1] + (b_[1] - a[1]) * u))
    return out


def normals2(pts, closed=True):
    """Outward normals of a counter-clockwise polyline (miter-averaged)."""
    n = len(pts)
    out = []
    for i in range(n):
        if closed:
            a, c = pts[i - 1], pts[(i + 1) % n]
        else:
            a, c = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        tx, ty = c[0] - a[0], c[1] - a[1]
        L = math.hypot(tx, ty) or 1.0
        out.append((ty / L, -tx / L))
    return out


# --------------------------------------------------------------------------- materials
WITCH = h('b4ffd2')


def palette():
    # the corpse-lit marble of Ithil: pale, cold green-grey, fluted (vertical grooves), darker in the joints
    material('ghost', h('6fa08b'), h('557f6e'), spec=0.35, refl=30)
    blib.PALETTE['ghost'].update(scale=0.5, cavity=0.8, vcracks=(1.6, 0.35))
    material('ghostDim', h('557f6f'), h('44685a'), spec=0.3, refl=24)          # the terraces, in shadow
    blib.PALETTE['ghostDim'].update(scale=0.5, cavity=0.8, vcracks=(1.1, 0.3))
    # the crown: the same stone split by seams of corpse-light
    material('crownstone', h('5f9480'), h('4a7666'), spec=0.35, refl=30)
    blib.PALETTE['crownstone'].update(scale=0.6, cavity=0.8, lava=dict(
        cold=h('1a2a24'), warm=h('46d68c'), core=h('dcffe8'), halo_color=h('1f6a49'), scale=0.45, width=0.05,
        hot=0.5, mask_scale=0.08, halo=0.45, warp=0.4, bump=0.15))
    # black glossy iron-stone: blades, thorns, spires, roofs
    material('spike', h('121614'), h('1c2320'), spec=0.55, refl=60)
    blib.PALETTE['spike'].update(scale=0.8, cavity=0.6)
    material('roof', h('171d1b'), h('222a27'), spec=0.4, refl=35)
    blib.PALETTE['roof'].update(scale=1.4, cavity=0.7)
    # houses: dimmer stone, their windows burning with the green light
    material('house', h('4f7466'), h('3f5e53'), spec=0.25, refl=18)
    blib.PALETTE['house'].update(scale=0.9, cavity=0.7, windows=dict(fx=1.15, fz=1.25, w=(0.35, 0.6),
                                                                      h=(0.3, 0.75), color=h('9dffc4')))
    # the light itself (no AO: it shines)
    material('witch', WITCH, h('8cf5b8'), spec=0.0, refl=0, ao=False)
    blib.PALETTE['witch'].update(scale=1.0)
    material('maw', h('0c1813'), h('12241c'), spec=0.0, refl=0, ao=False)
    blib.PALETTE['maw'].update(scale=1.0)
    material('teeth', h('d6e2d3'), h('b7c7b4'), spec=0.85, refl=110)             # "gleaming teeth"
    blib.PALETTE['teeth'].update(scale=3.0, cavity=0.5)
    material('marble', h('aebcb2'), h('97a89c'), spec=0.45, refl=40)            # the white bridge, the statues
    blib.PALETTE['marble'].update(scale=0.9, cavity=0.8)
    material('carving', h('9aa99f'), h('7f8f84'), spec=0.4, refl=35)
    blib.PALETTE['carving'].update(scale=2.0, cavity=0.9)
    material('pave', h('3c4f47'), h('31423b'), spec=0.2, refl=12)
    blib.PALETTE['pave'].update(scale=0.7, cavity=0.6)
    material('rock', h('222826'), h('2f3734'), spec=0.12, refl=8)
    blib.PALETTE['rock'].update(scale=0.3, cavity=0.9, vcracks=(0.8, 0.35))
    material('water', h('08140f'), h('0e2219'), spec=0.9, refl=140)
    blib.PALETTE['water'].update(scale=0.4)
    material('mead', h('3b4a3a'), h('2c382d'), spec=0.1, refl=6)                # the Poisoned Meads
    blib.PALETTE['mead'].update(scale=0.8, cavity=0.4, speckle=[(1.4, 0.16, h('cfeedd')), (2.6, 0.12, h('8fd9b0'))])
    material('flower', h('bff2d4'), h('9fe6be'), spec=0.0, refl=0, ao=False)
    blib.PALETTE['flower'].update(scale=1.0)


# --------------------------------------------------------------------------- mesh helpers
def newell(v, f):
    n = Vector((0.0, 0.0, 0.0))
    for i in range(len(f)):
        a, c = Vector(v[f[i]]), Vector(v[f[(i + 1) % len(f)]])
        n.x += (a.y - c.y) * (a.z + c.z)
        n.y += (a.z - c.z) * (a.x + c.x)
        n.z += (a.x - c.x) * (a.y + c.y)
    return n


def oriented(v, f, out):
    """The face, wound so its normal points along `out`."""
    return tuple(f) if newell(v, f).dot(Vector(out)) >= 0 else tuple(f[::-1])


def loft(b, mat, secs, apex=None, cap0=True, cap1=True, smooth=False):
    """A closed solid through sections (lists of 3D points, the same count each, in order round the axis); the end
    closes in a flat cap or in a point. Every face wound outwards (from its section's centre)."""
    n = len(secs[0])
    v = [tuple(p) for s in secs for p in s]
    cen = [Vector(tuple(sum(p[i] for p in s) / n for i in range(3))) for s in secs]
    f = []
    for i in range(len(secs) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            q = (i * n + k, i * n + k2, (i + 1) * n + k2, (i + 1) * n + k)
            fc = sum((Vector(v[x]) for x in q), Vector()) / 4
            f.append(oriented(v, q, fc - (cen[i] + cen[i + 1]) / 2))
    last = (len(secs) - 1) * n
    if apex is not None:
        v.append(tuple(apex))
        a = len(v) - 1
        for k in range(n):
            t = (last + k, last + (k + 1) % n, a)
            fc = sum((Vector(v[x]) for x in t), Vector()) / 3
            f.append(oriented(v, t, fc - cen[-1]))
    elif cap1:
        f.append(oriented(v, tuple(last + k for k in range(n)), cen[-1] - cen[-2]))
    if cap0:
        down = cen[0] - cen[1] if len(secs) > 1 else cen[0] - Vector(apex)      # (one ring + apex: a cone)
        f.append(oriented(v, tuple(range(n)), down))
    b.add(v, f, mat, smooth=smooth)


def frame(t):
    t = Vector(t).normalized()
    a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
    a = (a - t * a.dot(t)).normalized()
    return a, t.cross(a)


def tube(b, mat, pts, radii, sides=5, smooth=True, flat=1.0):
    """A tapering tube along pts closing in a point (spikes, thorns, horns, fangs)."""
    P = [Vector(p) for p in pts]
    secs = []
    prev = None
    for i, p in enumerate(P[:-1]):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        if prev is None:
            a, c = frame(t)
        else:
            a = (prev - t * prev.dot(t)).normalized()
            c = t.cross(a)
        prev = a
        r = radii[i]
        secs.append([p + a * (r * math.cos(2 * math.pi * j / sides)) + c * (r * flat * math.sin(2 * math.pi * j / sides))
                     for j in range(sides)])
    loft(b, mat, secs, apex=P[-1], smooth=smooth)


def thorn(b, mat, base, out, h, r, curl=0.35, lean=0.15, sides=4, n=4):
    """A thorn: rising from base, leaning out and curling outwards towards its tip."""
    base, out = Vector(base), Vector((out[0], out[1], 0.0)).normalized()
    up = Vector((0, 0, 1))
    pts = [base - up * r * 0.6 + up * 0.0]
    for i in range(1, n + 1):
        u = i / n
        pts.append(base + up * (h * u) + out * (h * (lean * u + curl * u ** 2.5)))
    radii = [r * (1 - (i / n)) ** 0.9 + 0.02 for i in range(n + 1)]
    tube(b, mat, pts, radii, sides=sides)


def blade(b, mat, p0, nrm, z0, height, o0=2.2, w0=3.3, t0=1.0, curl=2.3, belly=1.25, n=10, smooth=True):
    """A great curved black blade-buttress (the references' fins): rooted outside a wall at p0 (on its line, nrm =
    outward), sweeping up against the wall, then free above it, the hooked tip curling outwards. Sections are
    diamonds: the wall side, the flanks, the outer edge."""
    nx, ny = nrm
    N = Vector((nx, ny, 0.0)).normalized()
    Tn = Vector((-ny, nx, 0.0)).normalized()
    secs = []
    tip = None
    for i in range(n + 1):
        u = i / n
        o = o0 - belly * math.sin(math.pi * u * 0.8) + curl * u ** 3
        z = z0 + height * u
        w = w0 * (1 - u) ** 0.8 + 0.12
        t = t0 * (1 - u) ** 0.7 + 0.1
        c = Vector((p0[0], p0[1], z)) + N * o
        if i == n:
            tip = c + N * (w * 0.5) + Vector((0, 0, 0.6))
            break
        secs.append([c - N * (w * 0.5), c + Tn * (t * 0.5), c + N * (w * 0.5), c - Tn * (t * 0.5)])
    loft(b, mat, secs, apex=tip, smooth=smooth)


def arch_pts(w, h, k=0.62, n=7):
    """A pointed (lancet) arch outline [(s, z)] counter-clockwise: half-width w, height h."""
    spring = h - w * 2 * k
    pts = [(-w, 0.0), (w, 0.0), (w, spring)]
    R = 2 * w * k * 1.2
    for i in range(1, n):
        t = i / n
        pts.append((w - w * t ** 0.65, spring + (h - spring) * math.sin(t * math.pi / 2)))
    pts.append((0.0, h))
    for i in range(n - 1, 0, -1):
        t = i / n
        pts.append((-w + w * t ** 0.65, spring + (h - spring) * math.sin(t * math.pi / 2)))
    pts.append((-w, spring))
    del R
    return pts


def panel(b, mat, c, nrm, pts, depth=0.12, scale=(1.0, 1.0)):
    """A flat slab of outline pts [(s, z)] standing on a wall at c (x, y, z), facing nrm (2D), proud by depth."""
    N = Vector((nrm[0], nrm[1], 0.0)).normalized()
    Tn = Vector((-nrm[1], nrm[0], 0.0)).normalized()
    m = len(pts)
    C = Vector(c)
    front = [C + Tn * (s * scale[0]) + Vector((0, 0, z * scale[1])) + N * depth for s, z in pts]
    back = [C + Tn * (s * scale[0]) + Vector((0, 0, z * scale[1])) - N * 0.05 for s, z in pts]
    v = [tuple(p) for p in front + back]
    f = [oriented(v, tuple(range(m)), N), oriented(v, tuple(range(m, 2 * m)), -N)]
    cs = sum(front, Vector()) / m
    for i in range(m):
        j = (i + 1) % m
        q = (i, j, m + j, m + i)
        mid = (front[i] + front[j]) / 2
        f.append(oriented(v, q, mid - cs))
    b.add(v, f, mat)


def ngon(cx, cy, z, r, n, a0=0.0):
    return [Vector((cx + r * math.cos(a0 + 2 * math.pi * k / n), cy + r * math.sin(a0 + 2 * math.pi * k / n), z))
            for k in range(n)]


def to_hires(b, f0):
    """Every face added to the builder from index f0 on joins the bake's source (b.hires), so the selected-to-active
    AO/relief bake of a part sculpted in SDF also finds the explicit meshes (see balrog.explicit)."""
    used = sorted({i for f in b.faces[f0:] for i in f})
    if not used:
        return
    remap = {i: k for k, i in enumerate(used)}
    tris = []
    for f in b.faces[f0:]:
        for i in range(1, len(f) - 1):
            tris.append((remap[f[0]], remap[f[i]], remap[f[i + 1]]))
    if not hasattr(b, 'hires'):
        b.hires = []
    b.hires.append((np.array([b.verts[i] for i in used], float), np.array(tris, int)))


# --------------------------------------------------------------------------- the ground: the shelf and the knees
KNEES = [(-31.0, 3.0, 13.0, 4.5), (31.0, 3.0, 13.0, 4.5), (-30.5, 13.5, 19.0, 4.8), (30.5, 13.5, 19.0, 4.8),
         (-26.5, 22.0, 24.0, 5.0), (26.5, 22.0, 24.0, 5.0), (-12.0, 30.5, 23.0, 5.0), (12.0, 30.5, 23.0, 5.0),
         (0.0, 33.0, 26.0, 4.5), (-31.5, -7.0, 8.0, 3.5), (31.5, -7.0, 8.0, 3.5)]


def ground_h(x, y):
    """The shelf (just under the paving inside the outer wall), its cliffs, and the knees of the Ephel Duath rising
    behind and beside the city; everything sinks under the game's ground towards the hex's edge."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    s = se_s(x, y, C1, A1, B1, P1)
    d = (s - 1.0) * 21.0
    cliff = (Z1 - 0.4) * (1.0 - np.clip((d - 1.7) / 3.4, 0, 1) ** 1.25)     # a plinth of rock round the wall's foot
    outside = np.clip((d - 0.6) / 2.5, 0, 1)
    k = np.zeros_like(x)
    for (kx, ky, a, r) in KNEES:
        k = np.maximum(k, a * np.exp(-((x - kx) ** 2 + (y - ky) ** 2) / (r * r)))
    k = k * outside
    hd = np.maximum(np.abs(x), 0.5 * np.abs(x) + 0.8660254 * np.abs(y))
    edge = np.clip((HEX - 0.9 - hd) / 2.8, 0, 1)
    hh = np.maximum(cliff, k)
    return np.where(s < 1.0, Z1 - 0.4, hh * edge + (edge - 1.0) * 2.5)


def rock_noise(amp, f, seed):
    def fn(X, Y, Z):
        x, y, z = X * f, Y * f, Z * f
        return amp * (0.7 * sdf.fbm3(x * 0.18, y * 0.18, z * 0.18, 3, seed)
                      - 0.5 * (sdf.ridged3(x * 0.09, y * 0.09, z * 0.22, 2, seed + 7) - 0.5)
                      + 0.25 * sdf.fbm3(x * 0.7, y * 0.7, z * 0.7, 2, seed + 3))
    return fn


def build(b, eye=False):
    """The static part: the rock shelf and the knees of the mountains, the shelf's paving, the Morgulduin and its
    meads with the pale flowers, the long white bridge rising to the Mouth, lined with its statues."""
    palette()
    rng = random.Random(11)
    f = sdf.Field((-35, -40, -1.0), (35, 40, 28.0), 0.38, far=3.0)

    def shelf(X, Y, Z):
        return (Z - ground_h(X, Y)) * 0.7
    f.add((shelf, (np.array([-35.0, -40.0, -1.0]), np.array([35.0, 40.0, 28.0]))), k=0)
    # the knees: broken buttresses of rock leaning on the shelf
    for i in range(46):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(22, 31)
        x, y = 1.12 * r * math.cos(a), 5.0 + r * math.sin(a)
        if y < -12 or hex_d(x, y) > HEX - 3.5:
            continue
        z = float(ground_h(x, y))
        if z < 2.0:
            continue
        s = rng.uniform(2.0, 4.5)
        f.add(sdf.rbox((x, y, z - s * 0.4), (s, s * rng.uniform(0.6, 1.0), s * rng.uniform(1.0, 2.2)),
                       np.array(blib.T(rz=rng.uniform(0, 360), rx=rng.uniform(-18, 18)).to_3x3()), rad=0.3), k=1.2)
    f.displace(rock_noise(1.1, 1.0, 5), band=3.0)
    def keep(X, Y, Z):          # inside the hexagon, above the ground
        return np.maximum(np.maximum(np.abs(X), 0.5 * np.abs(X) + 0.8660254 * np.abs(Y)) - (HEX - 0.4), -0.3 - Z)
    f.intersect((keep, None))
    f.F[:, :, :3] = np.maximum(f.F[:, :, :3], 0.5)
    sdf_finish(b, f, 16000)
    f0 = len(b.faces)
    paving(b)
    river(b, rng)
    bridge(b)
    flowers(b, rng)
    to_hires(b, f0)


def sdf_finish(b, field, target_tris, mat='rock'):
    v, t = field.mesh()
    v, t = sdf.drop_small(v, t, 300)
    v = sdf.smooth_mesh(v, t, 1, 0.5)
    hv, ht = sdf.decimate(v, t, min(len(t), 700000), 'hi')
    gv, gt = sdf.decimate(v, t, target_tris, 'game')
    sdf.add_to_builder(b, gv, gt, mat, hires=(hv, ht))
    print('sculpt: %d -> %d triangles (bake source %d)' % (len(t), len(gt), len(ht)))


def paving(b):
    """The outer shelf's floor (the stock houses lie under it)."""
    pts = ring_pts(C1, A1 - 0.3, B1 - 0.3, P1, 96)
    blib.prism(b, 'pave', pts, Z1 - 1.2, 1.2)


# --------------------------------------------------------------------------- the Morgulduin, the meads, the bridge
def river_y(x):
    return -26.4 + 1.5 * math.sin(x * 0.16 + 0.7) + 0.5 * math.sin(x * 0.41)


def xlim(y, margin=0.6):
    """Half-width of the hexagon at row y."""
    ay = abs(y)
    return min(HEX, (HEX - 0.8660254 * ay) / 0.5) - margin


def ribbon(b, mat, x0, x1, yfn, half, z, n=60):
    v, f = [], []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        y = yfn(x)
        ylo = -(HEX - 0.5 * abs(x)) / 0.8660254 + 0.5          # the hexagon's southern edge at this x
        v += [(x, max(y - half(x), ylo), z), (x, max(y + half(x), ylo + 0.3), z)]
    for i in range(n):
        a = 2 * i
        f.append(oriented(v, (a, a + 2, a + 3, a + 1), (0, 0, 1)))
    b.add(v, f, mat)


def river(b, rng):
    """The Morgulduin: dark, cold water a little above the game's ground, between the Poisoned Meads."""
    x0 = -xlim(-31.5, 1.2)
    x1 = xlim(-31.5, 1.2)
    ribbon(b, 'mead', x0, x1, lambda x: river_y(x), lambda x: 5.6 + 0.8 * math.sin(x * 0.3), 0.07)
    ribbon(b, 'water', x0, x1, lambda x: river_y(x), lambda x: 2.1 + 0.35 * math.sin(x * 0.23 + 1.0), 0.14)


def flowers(b, rng):
    """The pale luminous flowers of the meads: little rosettes on the banks."""
    n = 0
    tries = 0
    while n < 130 and tries < 4000:
        tries += 1
        x = rng.uniform(-20, 20)
        y = river_y(x) + rng.choice((-1, 1)) * rng.uniform(2.4, 6.0)
        if hex_d(x, y) > HEX - 1.0 or abs(x) < 2.8:
            continue
        r = rng.uniform(0.16, 0.3)
        z = 0.16
        v = [(x, y, z + 0.06)]
        a0 = rng.uniform(0, 6.3)
        for k in range(5):
            a = a0 + 2 * math.pi * k / 5
            v.append((x + r * math.cos(a), y + r * math.sin(a), z))
        fcs = [oriented(v, (0, 1 + k, 1 + (k + 1) % 5), (0, 0, 1)) for k in range(5)]
        b.add(v, fcs, 'flower')
        n += 1


BR_Y0, BR_Y1 = -33.2, -19.6        # the white bridge, from the valley's floor up to the Mouth's landing
BR_W = 3.2


def deck_z(y):
    u = min(1.0, max(0.0, (y - BR_Y0) / (BR_Y1 - BR_Y0)))
    return 0.8 + (Z1 - 0.8) * u ** 1.25


def bridge(b):
    """The white bridge (the film: long, rising straight to the gate over the stream): a marble deck climbing on
    pointed arches, parapets with pinnacles, and along it the carved figures, "human and bestial, but all corrupt and
    loathsome"; the landing before the Mouth."""
    n = 20
    secs = []
    for i in range(n + 1):
        y = BR_Y0 + (BR_Y1 - BR_Y0) * i / n
        z = deck_z(y)
        secs.append([Vector((-BR_W / 2, y, z - 1.0)), Vector((BR_W / 2, y, z - 1.0)),
                     Vector((BR_W / 2, y, z)), Vector((-BR_W / 2, y, z))])
    loft(b, 'marble', secs)
    for sx in (-1, 1):            # parapets
        secs = []
        for i in range(n + 1):
            y = BR_Y0 + (BR_Y1 - BR_Y0) * i / n
            z = deck_z(y)
            x0 = sx * BR_W / 2
            secs.append([Vector((x0 - 0.18, y, z - 0.2)), Vector((x0 + 0.18, y, z - 0.2)),
                         Vector((x0 + 0.18, y, z + 0.75)), Vector((x0 - 0.18, y, z + 0.75))])
        loft(b, 'marble', secs)
        for i in range(1, 8):
            y = BR_Y0 + (BR_Y1 - BR_Y0) * i / 8
            z = deck_z(y) + 0.75
            blib.box(b, 'marble', sx * BR_W / 2, y, z, 0.42, 0.42, 0.35)
            blib.pyramid(b, 'marble', sx * BR_W / 2, y, z + 0.35, 0.42, 0.42, 1.0)
    # piers on pointed arches (the stream runs under the middle ones)
    piers = [-30.6, -28.2, -24.6, -22.0]
    for y in piers:
        top = deck_z(y) - 0.95
        blib.box(b, 'marble', 0, y, -0.3, BR_W + 0.3, 1.1, top + 0.3)
        for sy in (-1, 1):                    # cutwaters
            blib.pyramid(b, 'marble', 0, y + sy * 0.75, -0.3, BR_W + 0.3, 0.45, min(top, 2.0))
    for (ya, yb) in zip([BR_Y0] + piers, piers + [BR_Y1]):
        za = deck_z((ya + yb) / 2) - 1.0
        if za < 1.4:
            continue
        w = (yb - ya) / 2 - 0.5
        arch = arch_pts(max(0.4, w), max(0.8, za - 0.1))
        for sx in (-1, 1):
            c = (sx * (BR_W / 2 + 0.16), (ya + yb) / 2, 0.0)
            panel(b, 'maw', c, (sx, 0), arch, depth=0.04)
    # the landing before the Mouth
    blib.box(b, 'pave', 0.0, GATE_FACE_Y - 0.6, 0.0, 7.4, 3.0, Z1)
    # the carved figures along the bridge, facing the road
    for i, y in enumerate((-32.4, -28.9, -25.6, -21.6)):
        for sx in (-1, 1):
            kind = ('wraith', 'beast')[(i + (sx > 0)) % 2]
            statue(b, sx * (BR_W / 2 + 0.75), y, kind, sx, z0=deck_z(y) - 0.6)


def statue(b, x, y, kind, sx, z0=0.0):
    blib.box(b, 'marble', x, y, -0.3, 1.3, 1.3, z0 + 1.2)
    z = z0 + 0.9
    if kind == 'wraith':      # a tall hooded, robed figure, bent forwards, clawed hands raised
        tube(b, 'carving', [(x, y, z), (x, y - 0.1, z + 1.2), (x, y - 0.35, z + 2.2), (x, y - 0.5, z + 2.9)],
             [0.62, 0.48, 0.35, 0.0], sides=7)
        tube(b, 'carving', [(x, y - 0.35, z + 2.2), (x, y - 0.55, z + 2.55), (x, y - 0.75, z + 3.05),
                            (x, y - 0.6, z + 3.4)], [0.34, 0.33, 0.25, 0.0], sides=6)          # the hood
        for s in (-1, 1):
            tube(b, 'carving', [(x + s * 0.35, y - 0.3, z + 2.0), (x + s * 0.75, y - 0.7, z + 2.4),
                                (x + s * 0.9, y - 0.9, z + 2.95)], [0.13, 0.1, 0.0], sides=4)
    else:                     # a crouching beast, its head low and its spine spiked
        tube(b, 'carving', [(x, y + 0.5, z + 0.3), (x, y, z + 0.8), (x, y - 0.6, z + 0.75), (x, y - 1.0, z + 0.5)],
             [0.55, 0.6, 0.45, 0.0], sides=7)
        tube(b, 'carving', [(x, y - 0.6, z + 0.8), (x, y - 1.0, z + 1.1), (x, y - 1.35, z + 0.9)],
             [0.3, 0.26, 0.0], sides=6)
        for i in range(3):
            thorn(b, 'carving', (x, y + 0.3 - 0.35 * i, z + 1.1), (0, 1), 0.6, 0.1, curl=0.2, sides=4, n=2)
        for s in (-1, 1):
            tube(b, 'carving', [(x + s * 0.35, y - 1.2, z + 0.9), (x + s * 0.55, y - 1.35, z + 1.4),
                                (x + s * 0.4, y - 1.2, z + 1.75)], [0.08, 0.06, 0.0], sides=4)      # horns


# --------------------------------------------------------------------------- the outer wall, the gate (extra static)
def outer_ring(n=118):
    return ring_pts(C1, A1, B1, P1, n)


def wall_strip(b, mat, pts, nrms, z_in, z_top, thick, batter, z_out=None, closed=False):
    """A wall along a counter-clockwise polyline: its outer face battered (wider at the foot), the wall-walk on top,
    the inner face down to z_in. Open ends are capped."""
    z_out = z_in - 3.0 if z_out is None else z_out
    m = len(pts)
    v = []
    for (x, y), (nx, ny) in zip(pts, nrms):
        v += [(x + nx * (thick / 2 + batter), y + ny * (thick / 2 + batter), z_out),
              (x + nx * thick / 2, y + ny * thick / 2, z_top),
              (x - nx * thick / 2, y - ny * thick / 2, z_top),
              (x - nx * thick / 2, y - ny * thick / 2, z_in)]
    f = []
    segs = m if closed else m - 1
    for i in range(segs):
        j = (i + 1) % m
        nx, ny = nrms[i][0] + nrms[j][0], nrms[i][1] + nrms[j][1]
        a, c = 4 * i, 4 * j
        f.append(oriented(v, (a, c, c + 1, a + 1), (nx, ny, 0.25)))
        f.append(oriented(v, (a + 1, c + 1, c + 2, a + 2), (0, 0, 1)))
        f.append(oriented(v, (a + 2, c + 2, c + 3, a + 3), (-nx, -ny, 0)))
    if not closed:
        for i, sgn in ((0, -1), (m - 1, 1)):
            j = i + sgn if 0 <= i + sgn < m else i - sgn
            tx, ty = pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]
            a = 4 * i
            f.append(oriented(v, (a, a + 1, a + 2, a + 3), (tx, ty, 0)))
    b.add(v, f, mat)


def gate_gap(p):
    return p[1] < GATE_Y + 3.0 and abs(p[0]) < GATE_X


def front_clear(p):
    """No blades beside the gatehouse (its towers have their own)."""
    return p[1] < GATE_Y + 4.0 and abs(p[0]) < 12.0


def build_walls(b):
    palette()
    rng = random.Random(21)
    pts = outer_ring()
    nrm = normals2(pts)
    m = len(pts)
    # the ring, opened at the gate: start just east of the gap and run round to just west of it
    keep = [i for i in range(m) if not gate_gap(pts[i])]
    start = next(i for i in range(m) if not gate_gap(pts[i]) and gate_gap(pts[i - 1]))
    order = [(start + k) % m for k in range(m) if not gate_gap(pts[(start + k) % m])]
    del keep
    run = [pts[i] for i in order]
    rn = [nrm[i] for i in order]
    wall_strip(b, 'ghost', run, rn, Z1, Z1 + H1, 2.0, 1.0, z_out=Z1 - 2.2)
    # the parapet: thorns along the outer edge, tall and short in turn, and a lesser row inside
    L = 0.0
    for k in range(1, len(run)):
        (x0, y0), (x1, y1) = run[k - 1], run[k]
        seg = math.hypot(x1 - x0, y1 - y0)
        nx, ny = rn[k]
        steps = max(1, int(seg / 1.15))
        for s in range(steps):
            u = (s + 0.5) / steps
            x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
            big = (int((L + seg * u) / 1.15) % 2) == 0
            hh = rng.uniform(2.3, 3.0) if big else rng.uniform(1.2, 1.6)
            thorn(b, 'spike', (x + nx * 0.75, y + ny * 0.75, Z1 + H1), (nx, ny), hh, 0.34 if big else 0.24,
                  curl=0.28, lean=0.12)
        L += seg
    # the great blades along the walls, and the wall towers
    tower_at = []
    acc = 0.0
    next_tower = 6.0
    for k in range(1, len(run) - 1):
        (x0, y0), (x1, y1) = run[k - 1], run[k]
        acc += math.hypot(x1 - x0, y1 - y0)
        if acc >= next_tower:
            tower_at.append(k)
            next_tower += rng.uniform(15.5, 18.0)
    bl = 0.0
    nxt = 3.0
    for k in range(1, len(run) - 1):
        (x0, y0), (x1, y1) = run[k - 1], run[k]
        bl += math.hypot(x1 - x0, y1 - y0)
        if bl < nxt:
            continue
        nxt = bl + rng.uniform(4.6, 5.6)
        p = run[k]
        if front_clear(p) or any(abs(k - t) <= 1 for t in tower_at):
            continue
        hgt = rng.uniform(22.0, 27.0) * (0.85 if p[1] > 15 else 1.0)
        n_ = rn[k]
        base = (p[0] + n_[0] * 1.0, p[1] + n_[1] * 1.0)
        if hex_d(base[0] + n_[0] * 4.5, base[1] + n_[1] * 4.5) > HEX - 0.3:
            continue
        blade(b, 'spike', base, n_, Z1 - 4.0, hgt, o0=2.3, w0=3.4, t0=1.1, curl=2.0 + rng.uniform(-0.3, 0.4))
    for k in tower_at:
        p, n_ = run[k], rn[k]
        wall_tower(b, rng, p[0] + n_[0] * 0.6, p[1] + n_[1] * 0.6, Z1 - 3.0, Z1 + H1 + rng.uniform(9, 12),
                   rng.uniform(2.2, 2.6), n_)
    gatehouse(b, rng)


TOWER_TOPS = []          # (x, y, z) beacon positions, filled while building (for the fire effect)


def wall_tower(b, rng, x, y, z0, z1, r, out, beacon=True, spire=True):
    """A slender octagonal wall tower: battered foot, fluted shaft, thorned crown, a black spire with horns, lancet
    slits of witch-light facing the outside."""
    n = 8
    L_ = math.hypot(out[0], out[1]) or 1.0
    out = (out[0] / L_, out[1] / L_)
    secs = [ngon(x, y, z0, r * 1.35, n, math.pi / 8), ngon(x, y, z0 + 3.5, r, n, math.pi / 8),
            ngon(x, y, z1 - 1.4, r * 0.92, n, math.pi / 8), ngon(x, y, z1 - 1.0, r * 1.3, n, math.pi / 8),
            ngon(x, y, z1, r * 1.3, n, math.pi / 8)]
    loft(b, 'ghost', secs)
    for k in range(10):                       # thorned crown
        a = 2 * math.pi * k / 10
        ca, sa = math.cos(a), math.sin(a)
        thorn(b, 'spike', (x + ca * r * 1.15, y + sa * r * 1.15, z1), (ca, sa),
              rng.uniform(1.5, 2.2) if k % 2 else rng.uniform(0.9, 1.2), 0.24, curl=0.4, lean=0.15)
    if spire:
        hs = rng.uniform(8.0, 11.0)
        loft(b, 'spike', [ngon(x, y, z1, r * 0.85, n, math.pi / 8), ngon(x, y, z1 + hs * 0.35, r * 0.45, n, math.pi / 8)],
             apex=(x, y, z1 + hs), cap0=False)
        for s in (-1, 1):                     # two horns from the spire's foot
            ox, oy = -out[1] * s, out[0] * s
            tube(b, 'spike', [(x + ox * r * 0.6, y + oy * r * 0.6, z1 + 0.5), (x + ox * r * 1.1, y + oy * r * 1.1, z1 + 2.5),
                              (x + ox * r * 1.25, y + oy * r * 1.25, z1 + 4.6)], [0.3, 0.2, 0.0], sides=4)
    a_out = math.atan2(out[1], out[0])
    for da in (-0.55, 0.0, 0.55):             # lancet slits of light towards the outside
        a = a_out + da
        c = (x + math.cos(a) * r * 0.97, y + math.sin(a) * r * 0.97, z0 + 6.0 + rng.uniform(-0.5, 0.5))
        panel(b, 'witch', c, (math.cos(a), math.sin(a)), arch_pts(0.28, 2.4), depth=0.08)
        c2 = (c[0], c[1], c[2] + 5.0)
        panel(b, 'witch', c2, (math.cos(a), math.sin(a)), arch_pts(0.22, 1.7), depth=0.08)
    if beacon:
        TOWER_TOPS.append((x, y, z1 + 0.3))


GATE_W, GATE_H = 3.1, 9.6        # the Mouth: half-width, height (from the shelf)
GATE_FACE_Y = GATE_Y - 2.3       # the gatehouse's front face


def mouth_outline(w=GATE_W, hh=GATE_H, n=22):
    """The Mouth's opening: a tall pointed arch, a little pinched at the corners like jaws (x, z) from the threshold,
    counter-clockwise (seen from the front), starting bottom left."""
    pts = []
    for i in range(n + 1):                    # the right side up to the apex
        t = i / n
        z = hh * t
        if t < 0.55:
            x = w * (1.0 - 0.1 * math.sin(math.pi * t / 0.55))
        else:
            s = (t - 0.55) / 0.45
            x = w * (1.0 - s ** 1.6) * (1 - 0.1 * s)
        pts.append((x, z))
    right = pts
    left = [(-x, z) for x, z in reversed(right[:-1])]
    return [(-w, 0.0)] + right + left[:-1]


def gatehouse(b, rng):
    """The gatehouse: two great flanking towers and the front between them, pierced by the Mouth (dark, burning
    green deep inside), lipped, fanged above and below ("an open mouth with gleaming teeth"); above it the defaced
    Moon (its light is the glow effect)."""
    y0 = GATE_FACE_Y
    # the front block between the towers: a thick slab, the Mouth a dark recess set into it
    zt = Z1 + 17.5
    blib.box(b, 'ghost', 0.0, GATE_Y - 0.2, Z1 - 4.0, 2 * (GATE_X + 0.5), 4.2, zt - (Z1 - 4.0))
    # a jagged gable over the front
    for i in range(-3, 4):
        x = i * 1.25
        hh = 2.6 + 3.2 * math.cos(i / 3.0 * math.pi / 2)
        thorn(b, 'spike', (x, y0 + 1.2, zt), (0, -1), hh, 0.36, curl=0.18, lean=0.1)
    # the Mouth: the dark throat, the burning light deep inside (low, like a fire within), the lips round it
    out = mouth_outline()
    c = (0.0, y0 - 0.02, Z1)
    panel(b, 'maw', c, (0, -1), out, depth=0.06)
    inner = [(x * 0.62, z * 0.55) for x, z in out]
    panel(b, 'witch', (0.0, y0 - 0.05, Z1), (0, -1), inner, depth=0.06)
    lips = [Vector((x * 1.1, y0 - 0.25, Z1 + z * 1.04)) for x, z in out]
    lip_pts = lips + [lips[0]]
    for i in range(len(lip_pts) - 1):
        blib.strut(b, 'ghost', lip_pts[i], lip_pts[i + 1], 0.55, 0.55, n=6)
    # fangs: hanging from the upper jaw, rising from the threshold; the corners' great ones
    upper = [(x, z) for x, z in out if z > GATE_H * 0.45]
    for i, (x, z) in enumerate(upper[1:-1:2]):
        L = 1.4 + 1.2 * (1 - abs(x) / GATE_W)
        tip = (x * 0.8, y0 - 0.35, Z1 + z - L)
        tube(b, 'teeth', [(x, y0 - 0.35, Z1 + z + 0.2), ((x + tip[0]) / 2, y0 - 0.5, Z1 + z - L * 0.5), tip],
             [0.32, 0.22, 0.0], sides=5)
    for x in (-2.3, -1.4, -0.5, 0.5, 1.4, 2.3):
        L = 1.2 + 0.7 * (abs(x) > 1.5)
        tube(b, 'teeth', [(x, y0 - 0.35, Z1 - 0.1), (x * 0.95, y0 - 0.5, Z1 + L * 0.5), (x * 0.88, y0 - 0.4, Z1 + L)],
             [0.3, 0.2, 0.0], sides=5)
    for s in (-1, 1):
        tube(b, 'teeth', [(s * 2.9, y0 - 0.4, Z1 + GATE_H * 0.62), (s * 2.6, y0 - 0.8, Z1 + GATE_H * 0.45),
                          (s * 2.1, y0 - 0.6, Z1 + GATE_H * 0.3)], [0.5, 0.33, 0.0], sides=6)
        tube(b, 'teeth', [(s * 2.8, y0 - 0.4, Z1 + 0.1), (s * 2.6, y0 - 0.75, Z1 + 1.8), (s * 2.2, y0 - 0.5, Z1 + 3.0)],
             [0.45, 0.3, 0.0], sides=6)
    # the Moon's disc above the Mouth (the death's face on it is light: MORGUL_GLOW)
    disc = [(2.2 * math.cos(2 * math.pi * k / 24), 2.2 * math.sin(2 * math.pi * k / 24)) for k in range(24)]
    panel(b, 'marble', (0.0, y0 - 0.02, Z1 + GATE_H + 4.4), (0, -1), disc, depth=0.15)
    # the flanking towers: square, buttressed, much taller than the wall
    for s in (-1, 1):
        x = s * (GATE_X + 2.6)
        zt2 = Z1 + 26.0
        secs = [[Vector((x - 3.4, GATE_Y - 3.6, Z1 - 4.0)), Vector((x + 3.4, GATE_Y - 3.6, Z1 - 4.0)),
                 Vector((x + 3.4, GATE_Y + 2.6, Z1 - 4.0)), Vector((x - 3.4, GATE_Y + 2.6, Z1 - 4.0))],
                [Vector((x - 2.7, GATE_Y - 2.9, Z1 + 4.0)), Vector((x + 2.7, GATE_Y - 2.9, Z1 + 4.0)),
                 Vector((x + 2.7, GATE_Y + 2.4, Z1 + 4.0)), Vector((x - 2.7, GATE_Y + 2.4, Z1 + 4.0))],
                [Vector((x - 2.3, GATE_Y - 2.5, zt2)), Vector((x + 2.3, GATE_Y - 2.5, zt2)),
                 Vector((x + 2.3, GATE_Y + 2.2, zt2)), Vector((x - 2.3, GATE_Y + 2.2, zt2))]]
        loft(b, 'ghost', secs)
        loft(b, 'ghost', [[Vector((x - 3.0, GATE_Y - 3.1, zt2)), Vector((x + 3.0, GATE_Y - 3.1, zt2)),
                           Vector((x + 3.0, GATE_Y + 2.8, zt2)), Vector((x - 3.0, GATE_Y + 2.8, zt2))],
                          [Vector((x - 3.0, GATE_Y - 3.1, zt2 + 1.0)), Vector((x + 3.0, GATE_Y - 3.1, zt2 + 1.0)),
                           Vector((x + 3.0, GATE_Y + 2.8, zt2 + 1.0)), Vector((x - 3.0, GATE_Y + 2.8, zt2 + 1.0))]])
        # thorned crown and a tall black spire with four horns
        for k in range(14):
            a = 2 * math.pi * k / 14
            ca, sa = math.cos(a), math.sin(a)
            thorn(b, 'spike', (x + ca * 2.7, GATE_Y - 0.15 + sa * 2.7, zt2 + 1.0), (ca, sa),
                  2.4 if k % 2 else 1.3, 0.3, curl=0.35)
        loft(b, 'spike', [ngon(x, GATE_Y - 0.15, zt2 + 1.0, 2.0, 8, math.pi / 8),
                          ngon(x, GATE_Y - 0.15, zt2 + 6.0, 1.0, 8, math.pi / 8)],
             apex=(x, GATE_Y - 0.15, zt2 + 15.0), cap0=False)
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            ca, sa = math.cos(a), math.sin(a)
            tube(b, 'spike', [(x + ca * 1.5, GATE_Y - 0.15 + sa * 1.5, zt2 + 2.0),
                              (x + ca * 2.6, GATE_Y - 0.15 + sa * 2.6, zt2 + 4.5),
                              (x + ca * 2.9, GATE_Y - 0.15 + sa * 2.9, zt2 + 8.0)], [0.35, 0.22, 0.0], sides=4)
        TOWER_TOPS.append((x, GATE_Y - 0.15, zt2 + 1.3))
        # lancet windows on the front, a blade up each outer corner
        for zz in (Z1 + 6.0, Z1 + 12.5, Z1 + 19.0):
            for dx in (-1.1, 1.1):
                panel(b, 'witch', (x + dx, GATE_Y - 2.9 + (zz - Z1 - 4) / (22.0) * 0.4 - 0.02, zz), (0, -1),
                      arch_pts(0.34, 3.0), depth=0.1)
        blade(b, 'spike', (x + s * 3.0, GATE_Y - 3.0), (s * 0.7, -0.7), Z1 - 4.5, 33.0, o0=2.0, w0=3.6, t0=1.2,
              curl=2.6)


# --------------------------------------------------------------------------- the city (extra static)
def build_city(b):
    palette()
    rng = random.Random(31)
    # the second terrace: a fluted retaining wall with a thorned parapet; a narrow inner gate at the front
    p2 = ring_pts(C2, A2, B2, P2, 90)
    blib.prism(b, 'ghostDim', p2, Z1 - 1.0, Z2 - Z1 + 1.0)
    n2 = normals2(p2)
    run = [p for p in p2]
    wall_strip(b, 'ghostDim', run + [run[0]], n2 + [n2[0]], Z2, Z2 + 4.2, 1.2, 0.0, z_out=Z2 - 0.5)
    for k, ((x, y), (nx, ny)) in enumerate(zip(p2, n2)):
        if y < C2[1] - B2 + 1.0 and abs(x) < 1.4:
            continue
        thorn(b, 'spike', (x + nx * 0.4, y + ny * 0.4, Z2 + 4.2), (nx, ny), 1.7 if k % 2 else 1.0, 0.22, curl=0.3)
    for k in range(0, len(p2), 11):
        (x, y), n_ = p2[k], n2[k]
        if y < C2[1] - B2 + 2.5 and abs(x) < 3.0:
            continue
        blade(b, 'spike', (x + n_[0] * 0.4, y + n_[1] * 0.4), n_, Z1 + 0.5, 17.0, o0=1.5, w0=2.3, t0=0.8, curl=1.4,
              belly=0.8)
    # the tower's court: a round bastion with its own thorned parapet
    c3 = ngon(TC[0], TC[1], Z2 - 0.5, R3, 40)
    blib.prism(b, 'ghost', [(p.x, p.y) for p in c3], Z2 - 0.5, Z3 - Z2 + 0.5)
    p3 = [(p.x, p.y) for p in ngon(TC[0], TC[1], 0, R3 - 0.3, 40)]
    n3 = normals2(p3)
    wall_strip(b, 'ghost', p3 + [p3[0]], n3 + [n3[0]], Z3, Z3 + 3.4, 1.0, 0.4, z_out=Z3 - 1.0)
    for k, ((x, y), (nx, ny)) in enumerate(zip(p3, n3)):
        thorn(b, 'spike', (x + nx * 0.35, y + ny * 0.35, Z3 + 3.4), (nx, ny), 1.8 if k % 2 else 1.1, 0.22, curl=0.3)
    # houses: dense, tall and narrow, steep black roofs, windows of witch-light
    placed = []
    houses(b, rng, placed, lambda x, y: (se_s(x, y, C1, A1, B1, P1) < 1 - 2.6 / 21 and
                                         se_s(x, y, C2, A2, B2, P2) > 1 + 1.6 / 15 and
                                         not (abs(x) < 2.0 and y < C2[1] - B2 + 0.5)), Z1, 9000)
    houses(b, rng, placed, lambda x, y: (se_s(x, y, C2, A2, B2, P2) < 1 - 1.8 / 15 and
                                         math.hypot(x - TC[0], y - TC[1]) > R3 + 1.4), Z2, 6000)
    # lesser towers: slender, spired, thorned (the references' forest of spikes round the great tower)
    for (x, y, z0, hh) in ((-14.5, -3.0, Z1, 22.0), (14.0, -4.0, Z1, 20.0), (-19.0, 9.0, Z1, 18.0),
                           (19.5, 8.0, Z1, 19.0), (-9.5, 19.5, Z2, 20.0), (9.5, 19.0, Z2, 22.0),
                           (-8.5, -1.5, Z2, 14.0), (8.0, -1.0, Z2, 15.0)):
        wall_tower(b, rng, x, y, z0 - 0.5, z0 + hh, 1.6, (x - TC[0], y - TC[1]), beacon=True)


def houses(b, rng, placed, inside, z, tries):
    n = 0
    for _ in range(tries):
        x, y = rng.uniform(-25, 25), rng.uniform(-14, 25)
        if not inside(x, y):
            continue
        w, d = rng.uniform(1.5, 2.7), rng.uniform(1.5, 2.6)
        r_ = 0.41 * math.hypot(w, d)
        if any(math.hypot(x - px, y - py) < r_ + pr + 0.05 for px, py, pr in placed):
            continue
        placed.append((x, y, r_))
        a = math.degrees(math.atan2(y - TC[1], x - TC[0]))      # facing the tower
        hh = rng.uniform(3.2, 7.0) * (1.25 if rng.random() < 0.2 else 1.0)
        blib.box(b, 'house', x, y, z - 0.6, w, d, hh + 0.6, rz=a)
        top = z + hh
        kind = rng.random()
        if kind < 0.55:
            blib.gable(b, 'roof', x, y, top, w, d, rng.uniform(2.4, 3.8), rz=a + rng.choice((0, 90)), overhang=0.18)
        else:
            blib.pyramid(b, 'roof', x, y, top, w + 0.3, d + 0.3, rng.uniform(3.0, 4.8), rz=a)
        if rng.random() < 0.18:              # a corner turret with a needle spire
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            tx, ty = x + ca * w * 0.45 - sa * d * 0.45, y + sa * w * 0.45 + ca * d * 0.45
            blib.cyl(b, 'house', tx, ty, z, 0.55, hh + 1.6, n=6)
            blib.cone(b, 'roof', tx, ty, z + hh + 1.6, 0.7, rng.uniform(3.0, 4.5), n=6)
        n += 1
    print('  houses on terrace z %.0f: %d' % (z, n))


# --------------------------------------------------------------------------- the Tower of Sorcery (extra static)
BALCONIES = [46.0, 60.0, 74.0, 88.0, 100.0]
STAGES = [(TOWER_Z0 - 1.0, 5.4), (44.0, 5.0), (46.5, 4.3), (72.5, 4.0), (75.0, 3.5), (TOWER_Z1, 3.2)]


def tower_a(z):
    """Half-width of the shaft (a square with chamfered corners) at height z: three stages stepping in, the steps
    under the galleries at 46 and 74."""
    for (z0, a0), (z1, a1) in zip(STAGES, STAGES[1:]):
        if z <= z1:
            return a0 + (a1 - a0) * max(0.0, z - z0) / (z1 - z0)
    return STAGES[-1][1]


def tower_sec(z, grow=0.0):
    """The shaft's section: a square (faces N/E/S/W) with deep chamfers, counter-clockwise."""
    a = tower_a(z) + grow
    c = a * 0.42
    cx, cy = TC
    pts = [(a, -a + c), (a, a - c), (a - c, a), (-a + c, a), (-a, a - c), (-a, -a + c), (-a + c, -a), (a - c, -a)]
    return [Vector((cx + x, cy + y, z)) for x, y in pts]


def build_tower(b):
    palette()
    rng = random.Random(41)
    cx, cy = TC
    zs = sorted(set([z for z, _ in STAGES] + BALCONIES))
    loft(b, 'ghost', [tower_sec(z) for z in zs])
    # the clawed roots: four great diagonal blades gripping the court, ribs running on up the corners
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        n_ = (math.cos(a), math.sin(a))
        a0 = tower_a(TOWER_Z0) * 1.12
        base = (cx + n_[0] * a0, cy + n_[1] * a0)
        blade(b, 'spike', base, n_, TOWER_Z0 - 1.0, 40.0, o0=1.7, w0=3.1, t0=1.4, curl=-0.8, belly=1.0, n=12)
        for z0, z1 in ((46.0, 99.0),):           # the corner rib with thorns
            secs = []
            for z in (z0, z1):
                a_ = tower_a(z) * 1.0 + 0.2
                c = Vector((cx + n_[0] * a_ * 1.0, cy + n_[1] * a_ * 1.0, z))
                N = Vector((n_[0], n_[1], 0))
                T = Vector((-n_[1], n_[0], 0))
                secs.append([c - N * 0.6 - T * 0.45, c + N * 0.7 - T * 0.25, c + N * 0.7 + T * 0.25, c - N * 0.6 + T * 0.45])
            loft(b, 'spike', secs)
            for z in np.arange(z0 + 3.0, z1, 4.0):
                if any(abs(z - zb) < 1.5 for zb in BALCONIES):
                    continue
                a_ = tower_a(z) + 0.6
                thorn(b, 'spike', (cx + n_[0] * a_, cy + n_[1] * a_, z), n_, 1.8, 0.25, curl=0.9, lean=0.6)
    # lesser blades on the faces' feet
    for k in range(4):
        a = k * math.pi / 2
        n_ = (math.cos(a), math.sin(a))
        a0 = tower_a(TOWER_Z0)
        blade(b, 'spike', (cx + n_[0] * a0, cy + n_[1] * a0), n_, TOWER_Z0 - 0.5, 24.0, o0=1.5, w0=2.7, t0=0.9,
              curl=0.6, belly=0.9)
    # the galleries: a jutting thorned balcony on corbels at each stage
    for i, zb in enumerate(BALCONIES):
        ring_ = tower_sec(zb, grow=1.7)
        loft(b, 'ghost', [[p + Vector((0, 0, -0.9)) for p in ring_], ring_])
        loft(b, 'spike', [tower_sec(zb - 2.4, grow=0.05), [p + Vector((0, 0, -0.9)) for p in tower_sec(zb, grow=1.5)]],
             cap0=False, cap1=False)
        for k, p in enumerate(ring_):
            q = ring_[(k + 1) % 8]
            for u in np.linspace(0.08, 0.92, 4 if k % 2 == 0 else 2):
                pp = p.lerp(q, u)
                d = Vector((pp.x - cx, pp.y - cy, 0)).normalized()
                thorn(b, 'spike', (pp.x - d.x * 0.25, pp.y - d.y * 0.25, zb), (d.x, d.y),
                      1.6 if (k + int(u * 4)) % 2 else 1.0, 0.2, curl=0.4)
        big = zb in (46.0, 74.0, 100.0)
        for k in range(4):                   # gothic pinnacles on the gallery's corners (the references' spires)
            a = math.pi / 4 + k * math.pi / 2
            ca, sa = math.cos(a), math.sin(a)
            r0 = (tower_a(zb) + 1.7) * 1.08 - 0.5
            px, py = cx + ca * r0, cy + sa * r0
            pr = 0.75 if big else 0.55
            loft(b, 'ghost', [ngon(px, py, zb, pr, 8, math.pi / 8), ngon(px, py, zb + (2.6 if big else 1.8), pr, 8,
                                                                                math.pi / 8)])
            hs = 7.5 if big else 4.5
            zp = zb + (2.6 if big else 1.8)
            loft(b, 'spike', [ngon(px, py, zp, pr * 1.15, 8, math.pi / 8),
                              ngon(px, py, zp + hs * 0.25, pr * 0.6, 8, math.pi / 8)], apex=(px, py, zp + hs))
            for s_ in (-1, 1):
                thorn(b, 'spike', (px, py, zp), (ca - s_ * sa, sa + s_ * ca), 1.4, 0.16,
                      curl=0.6, lean=0.4)
        if big:                              # green beacons on the gallery's faces
            for k in range(4):
                a = k * math.pi / 2
                r0 = tower_a(zb) + 1.2
                TOWER_TOPS.append((cx + math.cos(a) * r0, cy + math.sin(a) * r0, zb + 0.1))
        if not big:                          # great horns from the faces of the lesser galleries
            for k in range(4):
                a = k * math.pi / 2
                ca, sa = math.cos(a), math.sin(a)
                r0 = tower_a(zb) * 1.25
                tube(b, 'spike', [(cx + ca * r0, cy + sa * r0, zb - 0.4), (cx + ca * (r0 + 2.4), cy + sa * (r0 + 2.4), zb + 0.6),
                                  (cx + ca * (r0 + 3.6), cy + sa * (r0 + 3.6), zb + 3.0),
                                  (cx + ca * (r0 + 3.9), cy + sa * (r0 + 3.9), zb + 6.0)], [0.5, 0.38, 0.22, 0.0], sides=5)
    # windows: tall lancets of corpse-light on each face between the galleries ("countless")
    stages = [(TOWER_Z0 + 2.0, 40.0)] + [(46.0, BALCONIES[0])] + list(zip(BALCONIES, BALCONIES[1:])) + \
             [(BALCONIES[-1], TOWER_Z1)]
    for (z0, z1) in stages:
        hgt = z1 - z0
        for k in range(4):
            a = -math.pi / 2 + k * math.pi / 2
            n_ = (math.cos(a), math.sin(a))
            zc = z0 + 1.2
            aa = tower_a(zc + hgt * 0.4)
            cols = 3 if z0 < 45 else 2
            for j in range(cols):
                s = (j - (cols - 1) / 2) * (aa * 0.55)
                c = (cx + n_[0] * aa - n_[1] * s, cy + n_[1] * aa + n_[0] * s, zc + 0.6)
                wh = min(hgt - 3.6, 6.0)
                if wh < 2.0:
                    continue
                panel(b, 'witch', c, n_, arch_pts(0.42 if cols == 2 else 0.5, wh), depth=0.1)
                if hgt > 9:
                    c2 = (c[0], c[1], c[2] + wh + 0.9)
                    panel(b, 'witch', c2, n_, [(0.3 * math.cos(t), 0.3 + 0.3 * math.sin(t))
                                               for t in np.linspace(0, 2 * math.pi, 9)[:-1]], depth=0.1)
    # the great door to the court
    panel(b, 'maw', (cx, cy - tower_a(TOWER_Z0 + 1) - 0.02, TOWER_Z0), (0, -1), arch_pts(1.6, 6.5), depth=0.08)
    # the cornice under the crown and the black spire core (stands alone if the crown should not draw)
    loft(b, 'ghost', [tower_sec(TOWER_Z1 - 1.5, grow=0.0), tower_sec(TOWER_Z1, grow=0.9)])
    loft(b, 'spike', [ngon(cx, cy, TOWER_Z1, 2.8, 8, math.pi / 8), ngon(cx, cy, TOWER_Z1 + 10.0, 1.2, 8, math.pi / 8)],
         apex=(cx, cy, 126.0), cap0=False)


# --------------------------------------------------------------------------- the revolving crown (skinned)
CR = [(CROWN_Z, 4.4), (CROWN_Z + 1.8, 5.8), (CROWN_Z + 10.5, 6.3), (CROWN_Z + 12.0, 5.6)]


def crown_r(z):
    for (z0, r0), (z1, r1) in zip(CR, CR[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return CR[-1][1]


def build_eye(b):
    """The topmost course: "a huge ghostly head leering into the night". A flared drum (a helmet) of crown-stone
    seamed with corpse-light; on its face two slanted eyes of witch-light under a jagged brow, a grinning row of
    slits below; a crown of curved thorns, four great horns and the needle spire. Turns slowly, one way, then the
    other (GAZE)."""
    palette()
    rng = random.Random(51)
    cx, cy = TC
    n = 16
    secs = [ngon(cx, cy, z, r, n, -math.pi / 2) for z, r in CR]
    loft(b, 'crownstone', secs)
    zt = CR[-1][0]
    # the face (towards the camera at rest)
    rf = crown_r(CROWN_Z + 6.5)
    for s in (-1, 1):
        a = -math.pi / 2 + s * math.radians(21)
        n_ = (math.cos(a), math.sin(a))
        c = (cx + n_[0] * (rf - 0.05), cy + n_[1] * (rf - 0.05), CROWN_Z + 6.8)
        eye = [(1.75 * math.cos(t), 0.72 * math.sin(t) * (1.0 if math.sin(t) > 0 else 0.6)) for t in
               np.linspace(0, 2 * math.pi, 17)[:-1]]
        eye = [(x, z + 0.32 * x * s) for x, z in eye]            # slanted: the inner ends low (a scowl)
        panel(b, 'witch', c, n_, eye, depth=0.16)
        # the jagged brow over each eye
        bx, by = cx + n_[0] * (rf + 0.1), cy + n_[1] * (rf + 0.1)
        T = Vector((-n_[1], n_[0], 0))
        p0 = Vector((bx, by, CROWN_Z + 8.9)) + T * 2.2 * s
        p1 = Vector((bx, by, CROWN_Z + 7.4)) - T * 2.0 * s
        tube(b, 'spike', [p0 - Vector((n_[0], n_[1], 0)) * 0.3, p0.lerp(p1, 0.5) + Vector((n_[0], n_[1], 0.05)) * 0.6,
                          p1 + Vector((n_[0], n_[1], 0)) * 0.9 + Vector((0, 0, -0.5))], [0.55, 0.4, 0.0], sides=5)
    # the grin: a row of narrow slits of light with dark teeth between
    for j in range(9):
        a = -math.pi / 2 + math.radians((j - 4) * 7.5)
        n_ = (math.cos(a), math.sin(a))
        r_ = crown_r(CROWN_Z + 3.5)
        c = (cx + n_[0] * (r_ - 0.05), cy + n_[1] * (r_ - 0.05), CROWN_Z + 2.4 + 0.08 * abs(j - 4) ** 1.6)
        panel(b, 'witch', c, n_, [(-0.2, 0.0), (0.2, 0.0), (0.2, 1.4), (0.0, 1.9), (-0.2, 1.4)], depth=0.12)
    # windows round the back and sides (it is a tower course: it looks every way)
    for k in range(n):
        a = -math.pi / 2 + 2 * math.pi * (k + 0.5) / n
        if abs(math.sin(a) + 1.0) < 0.35:
            continue
        n_ = (math.cos(a), math.sin(a))
        r_ = crown_r(CROWN_Z + 6.0)
        panel(b, 'witch', (cx + n_[0] * (r_ - 0.05), cy + n_[1] * (r_ - 0.05), CROWN_Z + 4.0), n_,
              arch_pts(0.3, 3.4), depth=0.1)
    # the rim: a thorned crown
    for k in range(20):
        a = 2 * math.pi * k / 20
        ca, sa = math.cos(a), math.sin(a)
        r_ = crown_r(zt) - 0.3
        thorn(b, 'spike', (cx + ca * r_, cy + sa * r_, zt - 0.3), (ca, sa), 4.2 if k % 2 else 2.6, 0.42,
              curl=0.5, lean=0.25, sides=5, n=5)
    # four great horns rising from the diagonals, curving out, then up
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        r0 = crown_r(zt) - 1.2
        pts = [(cx + ca * r0, cy + sa * r0, zt - 1.0), (cx + ca * (r0 + 1.8), cy + sa * (r0 + 1.8), zt + 2.5),
               (cx + ca * (r0 + 2.4), cy + sa * (r0 + 2.4), zt + 7.0), (cx + ca * (r0 + 2.0), cy + sa * (r0 + 2.0), zt + 11.5),
               (cx + ca * (r0 + 2.4), cy + sa * (r0 + 2.4), zt + 15.0)]
        tube(b, 'spike', pts, [0.95, 0.75, 0.55, 0.3, 0.0], sides=6)
    # the roof and the needle spire with its own thorns
    loft(b, 'spike', [ngon(cx, cy, zt, 5.3, n, -math.pi / 2), ngon(cx, cy, zt + 3.0, 2.6, n, -math.pi / 2),
                      ngon(cx, cy, zt + 10.0, 1.6, n, -math.pi / 2)], apex=(cx, cy, SPIRE_TOP), cap0=True, smooth=True)
    for k in range(6):
        a = 2 * math.pi * k / 6
        z = zt + 5.0 + 1.6 * (k % 3)
        r_ = 3.0 - 0.6 * (z - zt - 3.0) / 3.5
        thorn(b, 'spike', (cx + math.cos(a) * r_, cy + math.sin(a) * r_, z), (math.cos(a), math.sin(a)), 2.4, 0.28,
              curl=0.8, lean=0.5)
    del rng


def _sway(t):
    """The crown's turn (degrees): slowly one way and then the other, with a pause at each end."""
    s = math.sin(2 * math.pi * t / 24.0)
    return 38.0 * math.copysign(abs(s) ** 0.7, s)


GAZE = dict(fn=_sway, T=24.0, spans=96)


# --------------------------------------------------------------------------- effects: bones, fire, light
GATE_C = (0.0, GATE_FACE_Y - 0.4, Z1 + GATE_H * 0.45)


def rig():
    return [('fxglow', 'eyeroot', (0.0, GATE_FACE_Y - 0.9, Z1 + GATE_H * 0.7), 'MORGUL_GLOW'),
            ('fxbeam', 'eyeroot', (TC[0], TC[1], SPIRE_TOP - 6.0), 'MORGUL_BEAM'),
            ('fxcrown', 'eyeroot', (TC[0], TC[1], CR[-1][0]), 'MORGUL_CROWN'),
            ('fxgate', 'eyeroot', (0.0, GATE_FACE_Y - 0.5, Z1), 'MORGUL_GATE'),
            ('fxbeacon', 'eyeroot', (0.0, 0.0, Z1 + H1), 'MORGUL_BEACONS'),
            ('fxmist', 'eyeroot', (0.0, 0.0, Z1), 'MORGUL_MIST')]


def glow_effect(k):
    """The light of the Mouth and the defaced Moon over it (glow.py): one quad just in front of the gatehouse; points
    behind it are lifted as the game camera sees them."""
    pos = Vector(rig()[0][2])
    lift = math.tan(math.radians(52.0))

    def onto(x, y, z):
        return (x, z + (y - pos.y) * lift)
    y0 = GATE_FACE_Y
    lines = []
    # the throat: soft vertical strokes of light, brightest low
    for i in range(7):
        x = (i - 3) * 0.75
        hgt = GATE_H * (0.75 - 0.08 * abs(i - 3))
        x0, z0 = onto(x, y0 + 0.4, Z1 + 0.3)
        x1, z1 = onto(x * 0.8, y0 + 0.4, Z1 + hgt)
        lines.append((x0, z0, x1, z1, 0.35, (120, 255, 170)))
    # the Moon defaced: a ring, two hollow eyes, the nose, a grin of teeth
    mz = Z1 + GATE_H + 4.4
    seg = 28
    for j in range(seg):
        a0, a1 = 2 * math.pi * j / seg, 2 * math.pi * (j + 1) / seg
        p0 = onto(2.2 * math.cos(a0), y0 - 0.2, mz + 2.2 * math.sin(a0))
        p1 = onto(2.2 * math.cos(a1), y0 - 0.2, mz + 2.2 * math.sin(a1))
        lines.append((p0[0], p0[1], p1[0], p1[1], 0.16, (205, 255, 225)))
    for s in (-1, 1):
        cx_, cz_ = onto(s * 0.75, y0 - 0.2, mz + 0.45)
        lines.append((cx_ - 0.35, cz_ - 0.1 * s, cx_ + 0.35, cz_ + 0.1 * s, 0.5, (150, 255, 190)))
    nx_, nz_ = onto(0.0, y0 - 0.2, mz - 0.3)
    lines.append((nx_, nz_ + 0.25, nx_, nz_ - 0.15, 0.18, (150, 255, 190)))
    for i in range(5):
        x = (i - 2) * 0.42
        tx, tz = onto(x, y0 - 0.2, mz - 1.05)
        lines.append((tx, tz + 0.22, tx, tz - 0.22, 0.13, (180, 255, 210)))
    X0, X1 = pos.x - 6.0, pos.x + 6.0
    Z0_, Z1_ = Z1 - 1.0, mz + 3.2
    return dict(name='MEC_MorgulGlow',
                quads=[((X0 - pos.x) * k, (X1 - pos.x) * k, (Z0_ - pos.z) * k, (Z1_ - pos.z) * k, 0.0)],
                tex_args=dict(lines=lines, box=(X0, X1, Z0_, Z1_), px=1024, color=(130, 255, 180), halo=0.6,
                              core=0.85, sigma=(0.35, 1.4)))


# fire: the Balrog's shader fire (the stock fire pit's FireGrafix material), tinted to corpse-light green
FIRE_STOPS = [(0.0, (0, 14, 8)), (0.3, (10, 95, 55)), (0.62, (70, 230, 140)), (0.85, (165, 255, 200)),
              (1.0, (235, 255, 240))]
MIST_STOPS = [(0.0, (0, 10, 7)), (0.45, (16, 90, 60)), (0.8, (80, 205, 145)), (1.0, (170, 245, 205))]
T_FLAME = 12.0


def _crown_emitters():
    em = []
    zt = CR[-1][0]
    for k in range(14):
        a = 2 * math.pi * k / 14
        r_ = crown_r(zt) - 0.6
        em.append((Vector((TC[0] + math.cos(a) * r_, TC[1] + math.sin(a) * r_, zt + 0.3)), 0.9 + 0.3 * (k % 2)))
    return em


def _gate_emitters():
    return [(Vector((x, GATE_FACE_Y - 0.15, Z1 + 0.1)), s) for x, s in
            ((-1.8, 0.8), (-0.9, 1.0), (0.0, 1.15), (0.9, 1.0), (1.8, 0.8))]


def _beacon_emitters():
    seen = sorted({(round(x, 2), round(y, 2), round(z, 2)) for x, y, z in TOWER_TOPS})
    return [(Vector(p), 1.0) for p in seen]


def _mist_emitters():
    rng = random.Random(77)
    em = []
    for i in range(22):                       # over the terraces
        for _ in range(200):
            x, y = rng.uniform(-22, 22), rng.uniform(-11, 22)
            if se_s(x, y, C1, A1, B1, P1) < 0.93 and math.hypot(x - TC[0], y - TC[1]) > 6.0:
                break
        z = Z2 if se_s(x, y, C2, A2, B2, P2) < 1 else Z1
        em.append((Vector((x, y, z + 0.5)), rng.uniform(0.85, 1.2)))
    for i in range(7):                        # over the stream
        x = -14 + 28 * i / 6 + rng.uniform(-1.5, 1.5)
        em.append((Vector((x, river_y(x), 0.4)), rng.uniform(0.55, 0.75)))
    return em


FIRE_SETS = {     # key -> (effect name, bone, emitters fn, tongue height, tongues per emitter, kind)
    'MORGUL_CROWN': ('MEC_MorgulCrown', 'fxcrown', _crown_emitters, 9.0, 2, 'fire'),
    'MORGUL_GATE': ('MEC_MorgulGate', 'fxgate', _gate_emitters, 6.0, 2, 'fire'),
    'MORGUL_BEACONS': ('MEC_MorgulBeacons', 'fxbeacon', _beacon_emitters, 4.2, 2, 'fire'),
    'MORGUL_MIST': ('MEC_MorgulMist', 'fxmist', _mist_emitters, 21.0, 1, 'mist'),
}


def _ensure_tops():
    """The beacons' places are found while the walls/city/tower are built; a fresh process (the effects are written
    after the parts) rebuilds them here without a builder."""
    if TOWER_TOPS:
        return

    class Null:
        def __init__(self):
            self.verts, self.faces, self.fmat, self.fsmooth, self.mat_names = [], [], [], [], []
            self.rng = random.Random(0)

        def add(self, *a, **kw):
            pass

        def _mi(self, n):
            return 0
    build_walls(Null())
    build_city(Null())
    build_tower(Null())


def flame_tongues(key, k):
    import flames
    name, bone, emf, hgt, per, kind = FIRE_SETS[key]
    _ensure_tops()
    bw = Vector(next(r[2] for r in rig() if r[0] == bone))
    rng = random.Random(zlib.crc32(name.encode()) & 0xffff)
    em = [(((p - bw) * k).x, ((p - bw) * k).y, ((p - bw) * k).z, s) for p, s in emf()]
    tg = flames.steady_tongues(em, T_FLAME, rng, per=per, size=hgt * k)
    if kind == 'mist':                       # broad, soft columns of vapour
        for t in tg:
            t.w = t.h * rng.uniform(0.75, 1.0)
    return tg


def _beam_texture(path, W=128, H=1024):
    """The pillar of light: a narrow bright core in a wide soft column, a flare at its foot round the crown, fading
    upwards into the sky (colour constant, the shape in alpha; row 0 = the top)."""
    import dds
    u = (np.arange(W) + 0.5) / W * 2 - 1
    v = 1.0 - (np.arange(H) + 0.5) / H                   # 1 at the top
    U, V = np.meshgrid(u, v)
    zf = BEAM_FOOT / (BEAM_TOP + BEAM_FOOT)            # where the bone is (the crown's top), from the bottom
    core = np.exp(-(U / 0.05) ** 2)
    col = np.exp(-(U / 0.22) ** 2)
    along = np.clip((V - zf * 0.6) / (zf * 0.6 + 1e-6), 0, 1) * (1 - V) ** 0.55
    flare = np.exp(-((U / 0.45) ** 2 + ((V - zf) / 0.035) ** 2))
    a = np.clip(along * (0.6 * core + 0.28 * col) + 0.3 * flare, 0, 1)
    a *= np.clip((1 - np.abs(U)) / 0.1, 0, 1)
    # DXT3 keeps 4 bits of alpha: dither the soft gradients so they don't show as bands
    a = np.clip(a + (np.random.default_rng(3).random(a.shape) - 0.5) / 15.0 * (a > 0.004), 0, 1)
    img = np.zeros((H, W, 4), np.float32)
    img[..., 0] = 150 + 90 * core
    img[..., 1] = 255
    img[..., 2] = 190 + 50 * core
    img[..., 3] = 255 * a
    dds.write_dxt3(path, np.clip(img, 0, 255).astype(np.uint8), alpha_keep=0.3)


BEAM_W = 15.0          # half-width of the light's quad (in-game units)
BEAM_FOOT = 22.0       # below the bone (the flare round the crown)
BEAM_TOP = 210.0       # above it


def model_effects(out_dir, k):
    """The fires (shader fire tinted green; the vapour slow and soft) and the pillar of light."""
    import os
    import flames
    import glow
    files = []
    bases, masks = flames.fire_textures(out_dir, 'MEC_Morgul', tint=FIRE_STOPS)
    files += bases + masks + ['MEC_Morgul_FireUV.dds', 'MEC_Morgul_EmberUV.dds', 'MEC_Morgul_Ember.dds']
    mb, mm = flames.fire_textures(out_dir, 'MEC_MorgulV', tint=MIST_STOPS, speed=70, ember_speed=60, soft=True)
    files += mb + mm + ['MEC_MorgulV_FireUV.dds', 'MEC_MorgulV_EmberUV.dds', 'MEC_MorgulV_Ember.dds']
    for key, (name, bone, _, _, _, kind) in FIRE_SETS.items():
        tg = flame_tongues(key, k)
        files += flames.write_fire(out_dir, name, tg, *((mb, mm) if kind == 'mist' else (bases, masks)))
    # the pillar: glow.py's still additive quad, its own long texture
    q = [(-BEAM_W * k, BEAM_W * k, -BEAM_FOOT * k, BEAM_TOP * k, 0.0)]
    files += glow.write(out_dir, 'MEC_MorgulBeam', q, dict(lines=[], box=(0, 1, 0, 1), px=64))
    _beam_texture(os.path.join(out_dir, 'MEC_MorgulBeam_DIFF.dds'))
    return files


def preview_overlays(out_dir):
    """The preview: the fire cards with one frame of their fire, and the pillar of light (additive)."""
    import os
    import dds
    import flames
    out = []
    for key, (name, bone, _, _, _, kind) in FIRE_SETS.items():
        pre = 'MEC_MorgulV' if kind == 'mist' else 'MEC_Morgul'
        b_ = dds.decode_dxt3(os.path.join(out_dir, pre + '_FireB0.dds')).astype(np.float32)
        m_ = dds.decode_dxt3(os.path.join(out_dir, pre + '_FireM0.dds')).astype(np.float32)
        img = b_.copy()
        img[..., 3] = b_[..., 3] * m_[..., 3] / 255.0
        img = np.clip(img, 0, 255).astype(np.uint8)
        bw = next(r[2] for r in rig() if r[0] == bone)
        for tg in flame_tongues(key, 4.0):
            qq = flames.rest_quat(tg)
            hw = tg.w / 2
            P = []
            for (x, z) in ((-hw, -0.06 * tg.h), (hw, -0.06 * tg.h), (hw, 0.94 * tg.h), (-hw, 0.94 * tg.h)):
                rx, ry, rz = flames.qrotate(qq, (x, 0.0, z))
                P.append((bw[0] + (tg.base[0] + rx) / 4.0, bw[1] + (tg.base[1] + ry) / 4.0,
                          bw[2] + (tg.base[2] + rz) / 4.0))
            out.append((P, [(0, 1, 2, 3)], [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)], img))
    bp = next(r[2] for r in rig() if r[0] == 'fxbeam')
    P = [(bp[0] - BEAM_W, bp[1], bp[2] - BEAM_FOOT), (bp[0] + BEAM_W, bp[1], bp[2] - BEAM_FOOT),
         (bp[0] + BEAM_W, bp[1], bp[2] + BEAM_TOP), (bp[0] - BEAM_W, bp[1], bp[2] + BEAM_TOP)]
    out.append((P, [(0, 1, 2, 3)], [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)],
                dds.decode_dxt3(os.path.join(out_dir, 'MEC_MorgulBeam_DIFF.dds'))))
    return out


EXTRA_STATICS = [('walls', build_walls, 2048), ('city', build_city, 2048), ('tower', build_tower, 2048)]

# preview views: the game's camera on the whole city, the Mouth, the crown, the side
PREVIEW = [((0, -230, 300), (0, 0, 55), 44),
           ((0, -95, 75), (0, -15, 16), 34),
           ((0, -110, 175), (0, 9, 112), 30),
           ((170, -110, 140), (0, 4, 55), 40),
           ((0, -160, 120), (0, 0, 45), 42)]
PREVIEW_EYE = [((0, -60, 150), (0, 9.5, 114), 40), ((45, -50, 140), (0, 9.5, 114), 40)]
