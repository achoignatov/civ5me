"""Barad-dûr, the Dark Tower (Mordor).

Book/film features modelled:
  * "rising black, blacker and darker than the vast shades amid which it stood, the cruel
    pinnacles and iron crown of the topmost tower of Barad-dûr": a colossal black
    fortress of iron and stone on jagged foundations, battlement upon battlement;
  * buttressed, spiked tiers and lesser towers clustered about its base;
  * the film's crown of two great curved prongs at the summit cradling the Eye of
    Sauron: a lidless eye wreathed in flame with a black slit pupil, facing the camera;
  * the ash-grey, cracked plain of Gorgoroth with glowing fissures.
"""
import math

from blib import (material, hexcol as h, box, ring, cyl, cone, lathe, terrain_polar, blob, strut, curve, sphere,
                  crenels)


def ground(x, y):
    r = math.hypot(x, y)
    z = 0.8 + 0.5 * math.sin(x * 0.4) * math.sin(y * 0.33)
    # jagged rock foundations around the tower base
    if r < 15:
        z += 4.5 * (1 - r / 15) ** 1.3 * (0.75 + 0.25 * math.sin(math.atan2(y, x) * 7))
    return z


def build(b):
    material('blackiron', h('17171a'), h('232328'), noise=3.0)
    material('ashrock', h('3a3632'), h('2b2826'), noise=1.5)
    material('ash', h('514a43'), h('453f39'), noise=1.0)
    material('lava', h('ff5a12'), h('c23008'), noise=3.0)
    material('eyefire', h('ffcf3a'), h('ff8a1a'), noise=4.0)
    material('eyeouter', h('ff6a12'), h('d2380c'), noise=3.0)
    material('pupil', h('050505'))

    rng = b.rng
    cracks = [[(rng.uniform(-28, 28), rng.uniform(-28, 0))] for _ in range(7)]

    def mat(x, y, z, s):
        r = math.hypot(x, y)
        if r < 15:
            return 'ashrock'
        # glowing fissures in the plain
        return 'ash'
    terrain_polar(b, ground, mat, R=31, nr=36, na=120)

    # glowing fissures across the plain of Gorgoroth
    for k in range(9):
        a = rng.uniform(0, 360)
        r = rng.uniform(17, 26)
        x, y = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
        heading = rng.uniform(0, 360)
        for step in range(rng.randint(5, 9)):
            heading += rng.uniform(-40, 40)
            L = rng.uniform(1.0, 2.2)
            nx, ny = x + L * math.cos(math.radians(heading)), y + L * math.sin(math.radians(heading))
            if math.hypot(nx, ny) > 28 or math.hypot(nx, ny) < 15:
                break
            box(b, 'lava', (x + nx) / 2, (y + ny) / 2, ground((x + nx) / 2, (y + ny) / 2) - 0.15, L + 0.15,
                rng.uniform(0.18, 0.4), 0.3, rz=heading)
            x, y = nx, ny

    # jagged rocks round the base
    for k in range(26):
        a = rng.uniform(0, 360)
        r = rng.uniform(10, 18)
        x, y = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
        hgt = rng.uniform(2.5, 6.5)
        strut(b, 'ashrock', (x, y, ground(x, y) - 1.0), (x * 0.92, y * 0.92, ground(x, y) + hgt), rng.uniform(1.0, 1.8),
              0.0, n=5)

    # --- foundation tier: broad, buttressed
    lathe(b, 'blackiron', [(13.0, 0), (12.0, 3.0), (10.2, 3.6), (9.6, 8.0), (8.4, 8.6), (0, 8.6)], n=10, z=0.0,
          smooth=False)
    for k in range(10):
        a = 36 * k + 18
        ar = math.radians(a)
        strut(b, 'blackiron', (12.8 * math.cos(ar), 12.8 * math.sin(ar), 0.0),
              (8.6 * math.cos(ar), 8.6 * math.sin(ar), 14.0), 1.3, 0.5, n=4)
        # downward-pointing spikes off the buttresses
        strut(b, 'blackiron', (10.6 * math.cos(ar), 10.6 * math.sin(ar), 7.5),
              (14.0 * math.cos(ar), 14.0 * math.sin(ar), 5.0), 0.45, 0.0, n=4)
    crenels(b, 'blackiron', 8.6, 8.6, 0, 360, size=0.8, h=1.2, step=2.2)

    # --- lesser towers about the base
    for k in range(5):
        a = 72 * k + 54
        ar = math.radians(a)
        x, y = 9.6 * math.cos(ar), 9.6 * math.sin(ar)
        lathe(b, 'blackiron', [(2.2, 0), (2.0, 15.0 + 2 * (k % 2)), (2.6, 16.0 + 2 * (k % 2)), (0, 16.0 + 2 * (k % 2))],
              n=6, x=x, y=y, z=4.0, smooth=False)
        for s in range(4):
            sa = math.radians(90 * s + a)
            zt = 20.0 + 2 * (k % 2)
            strut(b, 'blackiron', (x + 1.8 * math.cos(sa), y + 1.8 * math.sin(sa), zt),
                  (x + 2.8 * math.cos(sa), y + 2.8 * math.sin(sa), zt + 4.5), 0.5, 0.0, n=4)

    # --- the great tower: stacked tiers narrowing upward, each with spikes and a battlement
    tiers = [(8.0, 8.6, 20.0), (6.6, 20.0, 32.0), (5.4, 32.0, 43.0), (4.4, 43.0, 52.0)]
    for i, (r, z0, z1) in enumerate(tiers):
        lathe(b, 'blackiron', [(r, 0), (r * 0.9, z1 - z0 - 1.5), (r * 1.12, z1 - z0 - 0.8), (r * 1.12, z1 - z0),
                               (0, z1 - z0)], n=8, z=z0, smooth=False)
        crenels(b, 'blackiron', r * 1.08, z1, 0, 360, size=0.6, h=1.0, step=1.9)
        n = 8
        for k in range(n):
            a = math.radians(360 * k / n + 22.5 * (i % 2))
            zz = z1 - 0.8
            strut(b, 'blackiron', (r * 1.05 * math.cos(a), r * 1.05 * math.sin(a), zz),
                  ((r + 3.2) * math.cos(a), (r + 3.2) * math.sin(a), zz - 2.6), 0.5, 0.0, n=4)
            # vertical ribs
            strut(b, 'blackiron', (r * 0.98 * math.cos(a), r * 0.98 * math.sin(a), z0),
                  (r * 0.9 * math.cos(a), r * 0.9 * math.sin(a), z1 - 1.5), 0.5, 0.35, n=4)
    # fiery windows
    for zz in (24.0, 36.0, 46.0):
        box(b, 'lava', 0, -tiers[1][0] * 0.92 if zz < 32 else -tiers[2][0] * 0.88 if zz < 43 else -tiers[3][0] * 0.88,
            zz, 0.7, 0.3, 1.6)

    # --- the crown: two curved prongs rising from east and west, the Eye between them
    zc = 52.0
    for s in (-1, 1):
        pts = [(s * 3.2, 0.0, zc - 1.0), (s * 4.4, 0.4, zc + 4.0), (s * 4.6, 0.6, zc + 9.0), (s * 4.0, 0.5, zc + 13.5),
               (s * 2.6, 0.2, zc + 17.0), (s * 1.6, 0.0, zc + 18.5)]
        curve(b, 'blackiron', pts, 2.3, 0.0, n=6, smooth=False)
        # spines on the outside of each prong
        for (zz, out) in ((zc + 4, 5.8), (zc + 8.5, 6.4), (zc + 12.5, 5.6)):
            strut(b, 'blackiron', (s * 4.2, 0.4, zz), (s * out + s * 1.4, 0.5, zz + 2.6), 0.45, 0.0, n=4)
        # a smaller fork behind
        curve(b, 'blackiron', [(s * 2.0, 2.0, zc), (s * 2.6, 3.2, zc + 6.0), (s * 1.8, 3.4, zc + 10.0)], 1.0, 0.0, n=5,
              smooth=False)
    # the Eye of Sauron: a lidless eye wreathed in flame, a cat-like slit pupil facing south
    ez = zc + 9.0
    from blib import T
    sphere(b, 'eyeouter', 0, 0, 0, 1.0, n=14, rings=10, M=T(0, 0.3, ez, s=(2.3, 1.1, 3.4)))
    sphere(b, 'eyefire', 0, 0, 0, 1.0, n=14, rings=10, M=T(0, -0.25, ez, s=(1.75, 0.9, 2.6)))
    sphere(b, 'pupil', 0, 0, 0, 1.0, n=10, rings=8, M=T(0, -0.75, ez, s=(0.32, 0.5, 2.1)))
    # animated flames engulfing the Eye: a ring of fire around its rim and a burning core
    for k in range(10):
        a = 2 * math.pi * k / 10
        b.fx.append(('FX_EyeFlame_%d' % k, (2.2 * math.cos(a), 0.1 + 0.4 * math.sin(a * 2), ez + 3.2 * math.sin(a)),
                     'ART_DEF_VEFFECT_MEC_EYE_FLAMES'))
    b.fx.append(('FX_EyeCore', (0.0, -0.4, ez + 1.4), 'ART_DEF_VEFFECT_MEC_EYE_CORE'))
    b.fx.append(('FX_EyeTop', (0.0, 0.3, ez + 3.6), 'ART_DEF_VEFFECT_MEC_EYE_CORE'))
    # tongues of flame licking up from the eye
    for k in range(7):
        a = math.radians(360 * k / 7)
        x, y = 1.6 * math.cos(a), 0.3 + 1.0 * math.sin(a)
        strut(b, 'eyeouter', (x, y, ez + 2.0), (x * 1.3, y * 1.2, ez + 4.6 + (k % 3)), 0.55, 0.0, n=4)


PREVIEW = [((14, -30, 58), (0, 0, 55), 45)]
