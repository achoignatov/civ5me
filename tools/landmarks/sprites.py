"""Painted cut-out sprites for landmark cards (bake.py SPRITES): leaf clusters and tufts of grass, made with numpy.

The stock game draws vegetation this way (the Hanging Gardens' palms and bushes are painted cut-outs on cards,
BuildingShader with AlphaMode 8 / AlphaRef 128): a few flat cards whose texture is a painting of MANY leaves or
blades with see-through gaps look far more real than solid blobs, for a fraction of the vertices.
Every image: HxWx4 uint8 sRGB, top row first; alpha = coverage (anti-aliased edges; the game cuts at 128).
Reproducible from the seed.
"""
import math

import numpy as np


def _over(img, rgb, cov, x0, y0):
    """Paint colour rgb (HxWx3 or 3) with coverage cov (HxW, 0..1) into img at (x0, y0), over what is there."""
    h, w = cov.shape
    H, W = img.shape[:2]
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    c = cov[ya - y0:yb - y0, xa - x0:xb - x0][..., None]
    col = rgb[ya - y0:yb - y0, xa - x0:xb - x0] if np.ndim(rgb) == 3 else np.asarray(rgb, np.float32)
    dst = img[ya:yb, xa:xb]
    dst[..., :3] = dst[..., :3] * (1 - c) + col * c
    dst[..., 3:4] = np.maximum(dst[..., 3:4], c)


def _hsv(rgb, dh=0.0, ds=0.0, dv=0.0):
    """Shift an RGB colour (0..1) in hue/saturation/value."""
    import colorsys
    hh, ss, vv = colorsys.rgb_to_hsv(*rgb)
    return np.array(colorsys.hsv_to_rgb((hh + dh) % 1.0, min(1, max(0, ss + ds)), min(1, max(0, vv + dv))), np.float32)


def leaf_cluster(seed, base=(0.30, 0.42, 0.16), light=0.0, px=512, n=950):
    """A cluster of oak leaves: an irregular rounded mass of lobed leaves (darker midribs, a lit and a shaded half,
    each leaf its own hue), lighter towards the top (sunlit) and darker at the bottom and inside; a few twigs.
    light: -0.15 (a cluster deep in the crown) .. +0.15 (sunlit top)."""
    rng = np.random.default_rng(seed)
    img = np.zeros((px, px, 4), np.float32)
    s = px / 512.0
    lobes = [(0.5, 0.55, 0.30)] + [(0.5 + 0.22 * math.cos(a), 0.52 + 0.2 * math.sin(a), rng.uniform(0.17, 0.23))
                                   for a in np.linspace(0, 2 * math.pi, 7)[:-1] + rng.uniform(0, 1)]

    def inside(x, y):
        return any((x - cx) ** 2 + (y - cy) ** 2 < r * r for cx, cy, r in lobes)
    # twigs: from the bottom middle towards the lobes
    bark = np.array((0.27, 0.21, 0.15), np.float32)
    for cx, cy, r in lobes[1:]:
        x0, y0 = 0.5 * px, 0.97 * px
        x1, y1 = cx * px, cy * px
        L = int(math.hypot(x1 - x0, y1 - y0))
        for t in np.linspace(0, 1, max(2, L // 2)):
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            rr = (2.6 - 1.9 * t) * s
            g = int(rr) + 2
            yy, xx = np.mgrid[-g:g + 1, -g:g + 1]
            cov = np.clip(rr - np.hypot(xx, yy) + 0.5, 0, 1)
            _over(img, bark, cov, int(x) - g, int(y) - g)
    # leaves, back (deep, dark) to front (outer, lit)
    pts = []
    while len(pts) < n:
        x, y = rng.uniform(0.04, 0.96), rng.uniform(0.04, 0.96)
        if inside(x, y):
            pts.append((x, y, rng.uniform()))
    pts.sort(key=lambda p: p[2])
    base = np.array(base, np.float32)
    for (x, y, depth) in pts:
        L = rng.uniform(20, 36) * s
        W = L * rng.uniform(0.38, 0.5)
        dx, dy = x - 0.5, y - 0.55
        ang = math.atan2(dy, dx) + rng.normal(0, 0.9)            # mostly pointing outwards
        g = int(L / 2 + 3)
        yy, xx = np.mgrid[-g:g + 1, -g:g + 1].astype(np.float32)
        ca, sa = math.cos(ang), math.sin(ang)
        u = xx * ca + yy * sa
        v = -xx * sa + yy * ca
        t = np.clip(u / L + 0.5, 0, 1)
        lobed = 1.0 + 0.16 * np.cos(t * 7 * math.pi)            # the oak's lobes
        half = 0.5 * W * np.clip(np.sin(np.pi * t), 0, 1) ** 0.75 * lobed
        d = np.abs(v) - half
        d = np.where((u < -L / 2) | (u > L / 2), 99.0, d)
        cov = np.clip(0.5 - d, 0, 1)
        # colour: its own hue; lighter at the top of the cluster and towards the front; lit half and shaded half
        shade = 0.72 + 0.42 * (1.0 - y) + 0.22 * depth + light
        col = _hsv(base, rng.normal(0, 0.025), rng.normal(0, 0.06), rng.normal(0, 0.04)) * shade
        rgbimg = np.broadcast_to(col, xx.shape + (3,)).copy()
        rgbimg *= np.where(v > 0, 1.08, 0.9)[..., None]
        rgbimg *= np.where(np.abs(v) < 0.9 * s, 0.75, 1.0)[..., None]      # the midrib
        _over(img, np.clip(rgbimg, 0, 1), cov, int(x * px) - g, int(y * px) - g)
    return np.clip(np.rint(img * 255), 0, 255).astype(np.uint8)


def grass_tuft(seed, px=512, n=300, dry=0.15, flowers=0, base=(0.22, 0.33, 0.12), tip=(0.52, 0.64, 0.30)):
    """A tuft of meadow grass: tapering, curving blades from the bottom edge, darker at the base and lighter at the
    tips, some dry and yellowish; flowers: that many daisies / buttercups / clover leaves among them."""
    rng = np.random.default_rng(seed)
    img = np.zeros((px, px, 4), np.float32)
    s = px / 512.0
    base, tip = np.array(base, np.float32), np.array(tip, np.float32)
    drycol = np.array((0.62, 0.58, 0.34), np.float32)
    blades = []
    for _ in range(n):
        x0 = rng.uniform(0.08, 0.92) ** 1.0
        h = rng.uniform(0.18, 1.0) ** 1.4 * 0.97 * (1.0 - 0.5 * abs(x0 - 0.5))   # many short, a few tall
        bend = rng.normal(0, 0.22) + (x0 - 0.5) * 0.5                 # leaning outwards
        w0 = rng.uniform(6.0, 12.0) * s
        blades.append((h, x0, bend, w0, rng.uniform() < dry))
    blades.sort(key=lambda b: -b[0])                                  # tall ones behind
    for (h, x0, bend, w0, is_dry) in blades:
        steps = int(h * px / 2.0)
        tcol = drycol if is_dry else _hsv(tip, rng.normal(0, 0.02), rng.normal(0, 0.05), rng.normal(0, 0.05))
        for i in range(steps):
            t = i / max(1, steps - 1)
            x = (x0 + bend * h * t * t) * px
            y = px - 1 - t * h * px
            r = max(0.6, w0 * 0.5 * (1.0 - t) ** 0.9)
            g = int(r) + 2
            yy, xx = np.mgrid[-g:g + 1, -g:g + 1]
            cov = np.clip(r - np.hypot(xx - (x - int(x)), yy - (y - int(y))) + 0.5, 0, 1)
            col = base * (1 - t) + tcol * t
            col = col * (0.9 + 0.2 * rng.uniform())
            _over(img, np.clip(col, 0, 1), cov, int(x) - g, int(y) - g)
    for k in range(flowers):                                          # daisies, buttercups, clover
        kind = k % 3
        x, y = rng.uniform(0.15, 0.85) * px, rng.uniform(0.35, 0.8) * px
        if kind == 2:                                                 # clover: three round leaflets
            for a in (0.0, 2.1, 4.2):
                cx, cy = x + 7 * s * math.cos(a), y + 7 * s * math.sin(a)
                g = int(8 * s) + 2
                yy, xx = np.mgrid[-g:g + 1, -g:g + 1]
                cov = np.clip(6.5 * s - np.hypot(xx, yy) + 0.5, 0, 1)
                _over(img, np.array((0.27, 0.42, 0.17), np.float32), cov, int(cx) - g, int(cy) - g)
            continue
        petal = np.array((0.95, 0.94, 0.9), np.float32) if kind == 0 else np.array((0.93, 0.78, 0.18), np.float32)
        for a in np.linspace(0, 2 * math.pi, 9)[:-1]:
            cx, cy = x + 7 * s * math.cos(a), y + 5 * s * math.sin(a)
            g = int(7 * s) + 2
            yy, xx = np.mgrid[-g:g + 1, -g:g + 1]
            cov = np.clip(4.6 * s - np.hypot((xx) * 0.8, yy * 1.2) + 0.5, 0, 1)
            _over(img, petal, cov, int(cx) - g, int(cy) - g)
        g = int(5 * s) + 2
        yy, xx = np.mgrid[-g:g + 1, -g:g + 1]
        cov = np.clip(3.6 * s - np.hypot(xx, yy) + 0.5, 0, 1)
        _over(img, np.array((0.9, 0.7, 0.15), np.float32) if kind == 0 else np.array((0.85, 0.6, 0.1), np.float32),
              cov, int(x) - g, int(y) - g)
    return np.clip(np.rint(img * 255), 0, 255).astype(np.uint8)
