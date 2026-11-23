"""Bag End, Hobbiton (the Shire).

Modelled after the film set (reference photos shire1/shire2.webp in the repo root):
  * one big, round, grass-covered Hill;
  * the front of Bag End set into it: a yellow plaster face under a turf overhang,
    timber posts and a small shingled canopy;
  * "a perfectly round door like a porthole, painted green, with a shiny yellow brass knob
    in the exact middle", in a red-brick arch;
  * round, many-paned windows on both sides, each with its own timber frame and canopy;
  * a stone doorstep and a few pumpkins in front. Nothing else.
The front faces the camera (-Y).
"""
import math

from blib import material, hexcol as h, box, ring, lathe, terrain_polar, blob, strut, gable, sphere, T

FY = -6.5           # plane of the façade
CUT = 14.5          # half width of the flat lawn cut into the hill
S = 1.4             # size of the door / windows / timberwork


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def hill(x, y):
    r = math.hypot(x / 1.35, y - 4.0)
    z = 0.4 + 23.0 * math.exp(-(r / 16.5) ** 2.0)
    # the cut for the façade: flat lawn in front of FY, the hill's shoulders sloping down
    # gently on both sides; the transition behind FY is hidden inside the façade block
    f = smooth((CUT - abs(x)) / 5.0) * smooth((FY + 3.0 - y) / 1.5)
    return z + (0.5 - z) * f


def build(b):
    material('hillgrass', h('5f9a35'), h('74ad42'), noise=1.6)
    material('turf', h('4f8a2e'), h('64a03a'), noise=3.0)
    material('plaster', h('d9b35a'), h('cba44c'), noise=3.0)
    material('brick2', h('9b5638'), h('82462e'), noise=5.0, courses=0.32, course_dark=0.7)
    material('doorgreen', h('2f7a4a'), h('2a6f43'), noise=2.0)
    material('doorplanks', h('2a6c41'))
    material('brass', h('f2cf5a'))
    material('timber2', h('6b4a2c'), h('5c3f25'), noise=4.0)
    material('shingle', h('5a4636'), h('4a3a2d'), noise=4.0, courses=0.25, course_dark=0.7)
    # warm candle-lit window panes (they also get flickering candle-flame particles)
    material('glass', h('ffd36e'), h('ffb347'), noise=6.0, spec=1.0, refl=40)
    material('pumpkin', h('e07a1f'), h('c9661a'), noise=5.0)
    material('stem', h('4d6b2a'))
    material('stone2', h('a39a88'), h('8f877a'), noise=3.0)

    terrain_polar(b, hill, lambda x, y, z, s: 'hillgrass', R=30, cy=2, nr=40, na=140)

    # --- the face of Bag End, set into the hill (a thick block reaching back into the turf)
    W, H = 2 * 10.5 * S * 0.95, 8.6 * S
    box(b, 'plaster', 0, FY + 3.0, -0.5, W, 6.0, H + 0.5)
    # turf overhang along the top of the face, rolling back into the hill
    for k in range(13):
        x = -W / 2 - 0.5 + (W + 1.0) * k / 12
        rr = b.rng.uniform(1.4, 2.1)
        blob(b, 'turf', x, FY + 0.3 + b.rng.uniform(-0.3, 0.3), H - 1.0, rr, n=8, rings=4, squash=0.6, jitter=0.12)
        blob(b, 'turf', x + 0.8, FY + 3.0, H - 0.8, 2.2, n=8, rings=4, squash=0.6, jitter=0.1)

    def into_face(x, zc):
        """Local Z points out of the façade (toward -Y) at (x, FY, zc)."""
        return T(x, FY, zc, rx=90)

    # --- the round green door in its brick arch
    R = 3.0 * S
    zc = R + 0.25
    M = into_face(0.0, zc)
    lathe(b, 'brick2', [(0, 0), (R + 0.75, 0), (R + 0.75, 0.35), (R, 0.35), (R, 0.1), (0, 0.1)], n=28, M=M, smooth=False)
    lathe(b, 'doorgreen', [(R, 0.1), (R, 0.3), (0, 0.3)], n=28, M=M, smooth=False)
    # planks: thin vertical slats on the door
    for k in range(-3, 4):
        x = k * 0.8 * S
        hh = math.sqrt(max(0.0, R * R - x * x)) * 0.92
        box(b, 'doorplanks', x, FY - 0.32, zc - hh, 0.08, 0.06, 2 * hh)
    sphere(b, 'brass', 0.0, FY - 0.55, zc, 0.42, n=10, rings=6)
    # the doorstep
    box(b, 'stone2', 0, FY - 1.2, 0.0, 6.4, 2.4, 0.3)

    # timber posts either side of the door, a beam and a small shingled canopy above it
    for s in (-1, 1):
        box(b, 'timber2', s * (R + 1.5), FY - 0.25, 0.0, 0.6, 0.6, 7.4 * S)
    box(b, 'timber2', 0, FY - 0.25, 7.0 * S, 2 * R + 4.2, 0.6, 0.6)
    gable(b, 'shingle', 0, FY - 1.1, 7.4 * S, 2 * R + 4.6, 2.0, 1.2, overhang=0.15)

    # --- round windows on both sides, each with a timber frame, mullions and a canopy
    for s in (-1, 1):
        wx = s * 7.0 * S
        wr = 1.5 * S
        wz = 3.9 * S
        Mw = into_face(wx, wz)
        lathe(b, 'timber2', [(0, 0), (wr + 0.45, 0), (wr + 0.45, 0.3), (wr, 0.3), (wr, 0.05), (0, 0.05)], n=20, M=Mw,
              smooth=False)
        lathe(b, 'glass', [(wr, 0.05), (wr, 0.12), (0, 0.12)], n=20, M=Mw, smooth=False)
        box(b, 'timber2', wx, FY - 0.17, wz - wr, 0.14, 0.08, 2 * wr)
        box(b, 'timber2', wx, FY - 0.17, wz - 0.07, 2 * wr, 0.08, 0.14)
        ring(b, 'timber2', wr * 0.48, wr * 0.56, 0, 0.08, 0, 360, n=16, M=T(wx, FY - 0.13, wz, rx=90))
        for t in (-1, 1):
            box(b, 'timber2', wx + t * (wr + 0.9), FY - 0.2, 0.0, 0.4, 0.5, 6.2 * S)
        gable(b, 'shingle', wx, FY - 0.9, 6.1 * S, 2 * wr + 2.8, 1.5, 0.9, overhang=0.1)
        # candles inside: two flickering flames behind each window
        for k, dx in enumerate((-0.45, 0.45)):
            b.fx.append(('FX_Candle_%s%d' % ('L' if s < 0 else 'R', k), (wx + dx * wr, FY - 0.25, wz - 0.35 * wr),
                         'ART_DEF_VEFFECT_MEC_CANDLE'))

    # --- three pumpkins in front
    for (x, y, r) in ((6.2, FY - 3.4, 1.0), (7.9, FY - 2.6, 0.8), (5.0, FY - 4.6, 0.75)):
        pumpkin(b, x, y, 0.45, r)


def pumpkin(b, x, y, z, r):
    """Ribbed, squat pumpkin with a stalk."""
    prof = []
    for i in range(7):
        t = math.pi * i / 6 - math.pi / 2
        prof.append((r * math.cos(t), r * 0.72 * (math.sin(t) + 1)))
    n = 16
    verts, faces, rows = [], [], []
    for i, (pr, pz) in enumerate(prof):
        if i in (0, len(prof) - 1):
            verts.append((x, y, z + pz))
            rows.append([len(verts) - 1] * n)
            continue
        row = []
        for k in range(n):
            a = 2 * math.pi * k / n
            rr = pr * (1.0 if k % 2 == 0 else 0.88)
            verts.append((x + rr * math.cos(a), y + rr * math.sin(a), z + pz))
            row.append(len(verts) - 1)
        rows.append(row)
    for i in range(len(rows) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            q = [rows[i][k], rows[i][k2], rows[i + 1][k2], rows[i + 1][k]]
            u = []
            for v in q:
                if v not in u:
                    u.append(v)
            faces.append(tuple(u))
    b.add(verts, faces, 'pumpkin', smooth=True)
    strut(b, 'stem', (x, y, z + r * 1.4), (x + 0.12, y, z + r * 1.4 + 0.35), 0.1, 0.07, n=5)


PREVIEW = [((6, -34, 14), (0, FY, 6), 45)]
